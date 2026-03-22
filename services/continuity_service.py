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


def analyze_continuity(video_path: str) -> Dict:
    """
    Analiza la continuidad de un video mediante correlación de histogramas.
    Detecta cortes o ediciones abruptas (distancia > 1.0).
    Retorna diccionario con resultados, distancias y el gráfico en base64.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video: {video_path}")

    frame_count = 0
    euclidean_distance = []
    discontinuities = []
    prev_frame = None

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    discontinuity_images = []  # pares de frames en discontinuidades (base64)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if prev_frame is not None:
            A = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            B = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            histA = cv2.calcHist([A], [0], None, [256], [0, 256])
            cv2.normalize(histA, histA, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            histB = cv2.calcHist([B], [0], None, [256], [0, 256])
            cv2.normalize(histB, histB, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

            value = float(1 - cv2.compareHist(histA, histB, cv2.HISTCMP_CORREL))

            if value > 1.0:
                time_seconds = frame_count / fps if fps > 0 else frame_count

                # Guardar par de frames en base64
                comb = np.concatenate((prev_frame, frame), axis=1)
                _, buf = cv2.imencode('.jpg', comb)
                comb_b64 = base64.b64encode(buf).decode('utf-8')

                discontinuities.append({
                    'frame': frame_count,
                    'time': time_seconds,
                    'time_formatted': f"{int(time_seconds // 60):02d}:{int(time_seconds % 60):02d}",
                    'distance': value,
                    'comparison_image_base64': comb_b64
                })

            euclidean_distance.append(value)

        prev_frame = frame
        frame_count += 1

    cap.release()

    # Generar gráfico
    plot_b64 = _generate_plot(
        euclidean_distance,
        discontinuities,
        os.path.basename(video_path)
    )

    return {
        'video_path': video_path,
        'video_name': os.path.basename(video_path),
        'total_frames': frame_count,
        'fps': fps,
        'duration': duration,
        'discontinuities': discontinuities,
        'discontinuity_count': len(discontinuities),
        'max_distance': float(max(euclidean_distance)) if euclidean_distance else 0.0,
        'avg_distance': float(np.mean(euclidean_distance)) if euclidean_distance else 0.0,
        'euclidean_distances': euclidean_distance,
        'plot_base64': plot_b64,
        'analyzed_at': datetime.now().isoformat()
    }


def _generate_plot(distances: List[float], discontinuities: List[Dict],
                   video_name: str) -> str:
    """Genera el gráfico de continuidad y lo retorna en base64 (PNG)."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(distances, linewidth=1.5, color='blue', alpha=0.8)
    ax.set_xlabel('Número de Frame', fontsize=12, fontweight='bold')
    ax.set_ylabel('Distancia de Correlación', fontsize=12, fontweight='bold')
    ax.set_title(f'Análisis de Continuidad - {video_name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=1.0, color='orange', linestyle=':', alpha=0.7, linewidth=2,
               label='Umbral de Discontinuidad (1.0)')

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
                      video_name: str, output_path: str) -> str:
    """Genera y guarda el gráfico en disco. Retorna la ruta del archivo."""
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.plot(distances, linewidth=1.5, color='blue', alpha=0.8)
    ax.set_xlabel('Número de Frame', fontsize=12, fontweight='bold')
    ax.set_ylabel('Distancia de Correlación', fontsize=12, fontweight='bold')
    ax.set_title(f'Análisis de Continuidad - {video_name}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=1.0, color='orange', linestyle=':', alpha=0.7, linewidth=2,
               label='Umbral de Discontinuidad (1.0)')

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
