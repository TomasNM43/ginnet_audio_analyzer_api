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


def analyze_continuity(video_path: str) -> Dict:
    """
    Analiza la continuidad de un video usando un score combinado de 3 métricas:
      1. Distancia de correlación de histograma (clamped a [0, 1])
      2. Chi-cuadrado alternativo normalizado (range [0, 1])
      3. Diferencia absoluta media de píxeles normalizada (range [0, 1])

    El score final es el promedio de las 3 métricas.
    El umbral de detección es adaptativo: media + 2.5 * desviación estándar,
    con un piso mínimo de 0.15. Incluye debounce de 15 frames para evitar
    detecciones duplicadas del mismo corte.

    Usa dos pasadas sobre el video para evitar guardar todos los frames
    en memoria (solo se almacenan scores en la primera pasada).
    """
    FLOOR_THRESHOLD = 0.15
    MIN_GAP_FRAMES = 15

    # ── Pasada 1: solo scores, sin guardar frames ─────────────────────────────
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames_meta = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames_meta / fps if fps > 0 else 0

    scores = []
    frame_count = 0
    prev_gray = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            scores.append(_compute_frame_score(prev_gray, curr_gray))
        prev_gray = curr_gray
        frame_count += 1

    cap.release()

    # Umbral adaptativo
    if scores:
        arr = np.array(scores)
        adaptive_threshold = float(np.mean(arr) + 2.5 * np.std(arr))
        threshold = max(adaptive_threshold, FLOOR_THRESHOLD)
    else:
        threshold = FLOOR_THRESHOLD

    # Identificar frames candidatos con debounce
    candidate_frames = []      # índices de frame (1-based, como en la lógica original)
    last_detection = -MIN_GAP_FRAMES

    for idx, score in enumerate(scores):
        frame_idx = idx + 1    # scores[idx] corresponde a la transición frame idx → idx+1
        if score > threshold and (frame_idx - last_detection) >= MIN_GAP_FRAMES:
            candidate_frames.append(frame_idx)
            last_detection = frame_idx

    # ── Pasada 2: recoger imágenes solo de los frames candidatos ──────────────
    candidate_set = set(candidate_frames)
    discontinuities_map = {}   # frame_idx → discontinuity dict (sin imagen aún)

    for frame_idx in candidate_frames:
        time_seconds = frame_idx / fps if fps > 0 else frame_idx
        discontinuities_map[frame_idx] = {
            'frame': frame_idx,
            'time': time_seconds,
            'time_formatted': f"{int(time_seconds // 60):02d}:{int(time_seconds % 60):02d}",
            'distance': scores[frame_idx - 1],
            'comparison_image_base64': None
        }

    if candidate_set:
        cap2 = cv2.VideoCapture(video_path)
        prev_frame_color = None
        idx2 = 0

        while True:
            ret, frame = cap2.read()
            if not ret:
                break
            if idx2 in candidate_set and prev_frame_color is not None:
                comb_img = np.concatenate((prev_frame_color, frame), axis=1)
                _, buf = cv2.imencode('.jpg', comb_img)
                discontinuities_map[idx2]['comparison_image_base64'] = \
                    base64.b64encode(buf).decode('utf-8')
            prev_frame_color = frame
            idx2 += 1

        cap2.release()

    discontinuities = [discontinuities_map[f] for f in sorted(discontinuities_map)]

    plot_b64 = _generate_plot(scores, discontinuities, os.path.basename(video_path), threshold)

    return {
        'video_path': video_path,
        'video_name': os.path.basename(video_path),
        'total_frames': frame_count,
        'fps': fps,
        'duration': duration,
        'discontinuities': discontinuities,
        'discontinuity_count': len(discontinuities),
        'max_distance': float(max(scores)) if scores else 0.0,
        'avg_distance': float(np.mean(scores)) if scores else 0.0,
        'adaptive_threshold': threshold,
        'euclidean_distances': scores,
        'plot_base64': plot_b64,
        'analyzed_at': datetime.now().isoformat()
    }


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
