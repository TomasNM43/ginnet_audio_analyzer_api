import cv2
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')  # Backend sin pantalla para servidor
import matplotlib.pyplot as plt
import base64
import io
from typing import List, Dict
from datetime import datetime


def _compute_frame_score(prev_gray: np.ndarray, curr_gray: np.ndarray) -> float:
    """Calcula el score combinado de cambio entre dos frames en escala de grises."""
    histA = cv2.calcHist([prev_gray], [0], None, [256], [0, 256])
    cv2.normalize(histA, histA, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    histB = cv2.calcHist([curr_gray], [0], None, [256], [0, 256])
    cv2.normalize(histB, histB, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    corr_dist = float(max(0.0, min(1.0,
        1.0 - cv2.compareHist(histA, histB, cv2.HISTCMP_CORREL)
    )))
    chisq = float(max(0.0, min(1.0,
        cv2.compareHist(histA, histB, cv2.HISTCMP_CHISQR_ALT)
    )))
    mad = float(np.mean(np.abs(
        prev_gray.astype(np.float32) - curr_gray.astype(np.float32)
    ))) / 255.0

    return (corr_dist + chisq + mad) / 3.0


def _compute_diff_pct(prev_gray: np.ndarray, curr_gray: np.ndarray) -> float:
    """Calcula la diferencia absoluta media entre dos frames como porcentaje (0–100)."""
    return float(np.mean(np.abs(
        prev_gray.astype(np.float32) - curr_gray.astype(np.float32)
    ))) / 255.0 * 100.0


def analyze_continuity(video_path: str) -> Dict:
    """
    Analiza la continuidad de un video usando un score combinado de 3 métricas:
      1. Distancia de correlación de histograma (clamped a [0, 1])
      2. Chi-cuadrado alternativo normalizado (range [0, 1])
      3. Diferencia absoluta media de píxeles normalizada (range [0, 1])

    El score final es el promedio de las 3 métricas.
    El umbral de detección es adaptativo: media + 2.5 * desviación estándar,
    con un piso mínimo de 0.15. Incluye debounce de 15 segundos para evitar
    detecciones duplicadas del mismo corte.

    Usa seeking por tiempo (1 frame/segundo) — evita decodificar todos los
    frames intermedios, crítico para videos de gran tamaño.
    """
    FLOOR_THRESHOLD = 0.15
    MIN_GAP_SECONDS = 15

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    total_seconds = int(duration)

    print(f"Analizando continuidad: {os.path.basename(video_path)} | "
          f"Duración: {total_seconds}s | FPS: {fps:.2f}")

    scores = []          # score combinado por cada segundo analizado
    diff_pcts = []       # diferencia absoluta media como porcentaje (gráfico principal)
    frames_color = {}    # segundo → frame BGR (solo para candidatos, guardado en 2da pasada)

    # ── Pasada única: seeking 1 frame/segundo, score entre segundos consecutivos ──
    prev_gray = None
    second = 0

    while second <= total_seconds:
        cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
        ret, frame = cap.read()
        if not ret:
            break

        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            scores.append(_compute_frame_score(prev_gray, curr_gray))
            diff_pcts.append(_compute_diff_pct(prev_gray, curr_gray))

        prev_gray = curr_gray
        second += 1

        if second % 300 == 0:
            pct = (second / total_seconds * 100) if total_seconds > 0 else 0
            print(f"  Progreso continuidad: {pct:.1f}% ({second}/{total_seconds}s)")

    cap.release()

    # Umbral adaptativo
    if scores:
        arr = np.array(scores)
        adaptive_threshold = float(np.mean(arr) + 2.5 * np.std(arr))
        threshold = max(adaptive_threshold, FLOOR_THRESHOLD)
    else:
        threshold = FLOOR_THRESHOLD

    # Identificar segundos candidatos con debounce
    candidate_seconds = []
    last_detection = -MIN_GAP_SECONDS

    for idx, score in enumerate(scores):
        sec = idx + 1   # scores[idx] = transición entre segundo idx y idx+1
        if score > threshold and (sec - last_detection) >= MIN_GAP_SECONDS:
            candidate_seconds.append(sec)
            last_detection = sec

    # Recolectar imágenes solo para los candidatos (seeking puntual)
    discontinuities = []
    if candidate_seconds:
        cap2 = cv2.VideoCapture(video_path)
        for sec in candidate_seconds:
            time_seconds = float(sec)
            score_val = scores[sec - 1]

            # Frame anterior (sec-1) y frame actual (sec) para imagen comparativa
            img_b64 = None
            try:
                cap2.set(cv2.CAP_PROP_POS_MSEC, max(0, (sec - 1)) * 1000)
                ret_prev, frame_prev = cap2.read()
                cap2.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
                ret_curr, frame_curr = cap2.read()
                if ret_prev and ret_curr:
                    comb_img = np.concatenate((frame_prev, frame_curr), axis=1)
                    _, buf = cv2.imencode('.jpg', comb_img)
                    img_b64 = base64.b64encode(buf).decode('utf-8')
            except Exception:
                pass

            discontinuities.append({
                'frame': sec,
                'time': time_seconds,
                'time_formatted': f"{int(time_seconds // 60):02d}:{int(time_seconds % 60):02d}",
                'distance': score_val,
                'comparison_image_base64': img_b64
            })
        cap2.release()

    plot_b64 = _generate_plot(scores, discontinuities, os.path.basename(video_path), threshold)

    # Gráfico principal: diferencia frame a frame en porcentaje
    PRIMARY_THRESHOLD_PCT = 10.0
    primary_discontinuities = [
        {
            'second': idx + 1,
            'time': float(idx + 1),
            'time_formatted': f"{int((idx + 1) // 60):02d}:{int((idx + 1) % 60):02d}",
            'diff_pct': round(pct, 4)
        }
        for idx, pct in enumerate(diff_pcts)
        if pct > PRIMARY_THRESHOLD_PCT
    ]
    primary_plot_b64 = _generate_primary_plot(
        diff_pcts, os.path.basename(video_path), PRIMARY_THRESHOLD_PCT
    )

    return {
        'video_path': video_path,
        'video_name': os.path.basename(video_path),
        'total_frames': total_frames,
        'fps': fps,
        'duration': duration,
        'discontinuities': discontinuities,
        'discontinuity_count': len(discontinuities),
        'max_distance': float(max(scores)) if scores else 0.0,
        'avg_distance': float(np.mean(scores)) if scores else 0.0,
        'adaptive_threshold': threshold,
        'euclidean_distances': scores,
        'plot_base64': plot_b64,
        'diff_pcts': diff_pcts,
        'primary_discontinuities': primary_discontinuities,
        'primary_discontinuity_count': len(primary_discontinuities),
        'primary_plot_base64': primary_plot_b64,
        'analyzed_at': datetime.now().isoformat()
    }


def _generate_primary_plot(diff_pcts: List[float], video_name: str,
                            threshold_pct: float = 10.0) -> str:
    """Genera el gráfico principal: diferencia frame a frame en % con umbral de fallo al 10%."""
    fig, ax = plt.subplots(figsize=(12, 8))
    x = np.arange(1, len(diff_pcts) + 1)
    arr = np.array(diff_pcts)

    ax.plot(x, arr, linewidth=1.2, color='steelblue', alpha=0.85, zorder=2)
    ax.fill_between(x, arr, threshold_pct,
                    where=(arr > threshold_pct),
                    color='red', alpha=0.35, zorder=1,
                    label='Posible fallo de continuidad (>10%)')
    ax.axhline(y=threshold_pct, color='red', linestyle='--', linewidth=2,
               alpha=0.85, label=f'Umbral de fallo ({threshold_pct:.0f}%)')

    ax.set_xlabel('Segundo', fontsize=12, fontweight='bold')
    ax.set_ylabel('Diferencia frame a frame (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Diferencia Frame a Frame (Gráfico Principal) - {video_name}',
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def _generate_plot(distances: List[float], discontinuities: List[Dict],
                   video_name: str, threshold: float = 0.15) -> str:
    """Genera el gráfico de continuidad y lo retorna en base64 (PNG)."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(distances, linewidth=1.5, color='blue', alpha=0.8)
    ax.set_xlabel('Número de Frame', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score combinado (0–1)', fontsize=12, fontweight='bold')
    ax.set_title(f'Análisis de Continuidad - {video_name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=threshold, color='orange', linestyle=':', alpha=0.7, linewidth=2,
               label=f'Umbral adaptativo ({threshold:.3f})')

    for disc in discontinuities:
        idx = disc['frame'] - 1
        if 0 <= idx < len(distances):
            ax.axvline(x=idx, color='red', linestyle='--', alpha=0.8, linewidth=2)
            ax.annotate(
                f'Frame {disc["frame"]}',
                xy=(idx, distances[idx]),
                xytext=(10, 10),
                textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                fontsize=8, color='white', fontweight='bold'
            )

    ax.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def save_plot_to_file(distances: List[float], discontinuities: List[Dict],
                      video_name: str, output_path: str,
                      threshold: float = 0.15) -> str:
    """Genera y guarda el gráfico en disco. Retorna la ruta del archivo."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(distances, linewidth=1.5, color='blue', alpha=0.8)
    ax.set_xlabel('Número de Frame', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score combinado (0–1)', fontsize=12, fontweight='bold')
    ax.set_title(f'Análisis de Continuidad - {video_name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=threshold, color='orange', linestyle=':', alpha=0.7, linewidth=2,
               label=f'Umbral adaptativo ({threshold:.3f})')

    for disc in discontinuities:
        idx = disc['frame'] - 1
        if 0 <= idx < len(distances):
            ax.axvline(x=idx, color='red', linestyle='--', alpha=0.8, linewidth=2)
            ax.annotate(
                f'Frame {disc["frame"]}',
                xy=(idx, distances[idx]),
                xytext=(10, 10),
                textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                fontsize=8, color='white', fontweight='bold'
            )

    ax.legend()
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    return output_path
