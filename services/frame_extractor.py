import cv2
import numpy as np
import os
import zipfile
import io
from typing import Dict, List
from datetime import datetime


def adjust_brightness(image: np.ndarray, brightness_value: int) -> np.ndarray:
    """Ajusta el brillo de una imagen. brightness_value: -100 a 100."""
    if brightness_value == 0:
        return image
    brightened = np.clip(image.astype(np.float32) + brightness_value, 0, 255)
    return brightened.astype(np.uint8)


def extract_frames(video_path: str, config: Dict) -> Dict:
    """
    Extrae fotogramas de un video según la configuración.

    config keys:
        all_frames (bool): extraer todos los frames
        start_frame (int): frame inicial (1-based)
        end_frame (int): frame final (1-based)
        skip_frames (int): salto entre frames
        brightness_adjustment (int): -100 a 100
        color_frames (bool): guardar en color
        grayscale_frames (bool): guardar en escala de grises

    Retorna dict con metadatos y un ZIP en bytes con los frames.
    También guarda el ZIP en disco en una carpeta Fotogramas_Extraidos/
    """
    import shutil
    from pathlib import Path
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Determinar rango de frames
    if config.get('all_frames', True):
        start_frame = 1
        end_frame = total_frames
    else:
        start_frame = max(1, config.get('start_frame', 1))
        end_frame = min(total_frames, config.get('end_frame', total_frames))

    skip = max(1, config.get('skip_frames', 1))
    brightness_value = config.get('brightness_adjustment', 20)
    save_color = config.get('color_frames', True)
    save_gray = config.get('grayscale_frames', False)

    frames_to_extract = list(range(start_frame, end_frame + 1, skip))

    extraction_info = []
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        video_name = os.path.splitext(os.path.basename(video_path))[0]

        for frame_number in frames_to_extract:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number - 1)
            ret, frame = cap.read()

            if not ret:
                continue

            time_seconds = (frame_number - 1) / fps if fps > 0 else 0
            brightened = adjust_brightness(frame, brightness_value)

            if save_color:
                filename = (f"color/frame_{frame_number:06d}"
                            f"_t{time_seconds:.2f}s_bright{brightness_value:+d}.png")
                _, buf = cv2.imencode('.png', brightened)
                zf.writestr(filename, buf.tobytes())

            if save_gray:
                gray = cv2.cvtColor(brightened, cv2.COLOR_BGR2GRAY)
                filename = (f"grayscale/frame_{frame_number:06d}"
                            f"_t{time_seconds:.2f}s_bright{brightness_value:+d}_gray.png")
                _, buf = cv2.imencode('.png', gray)
                zf.writestr(filename, buf.tobytes())

            extraction_info.append({
                'frame_number': frame_number,
                'time_seconds': time_seconds,
                'time_formatted': f"{int(time_seconds // 60):02d}m{int(time_seconds % 60):02d}s",
                'brightness_applied': brightness_value,
                'color_saved': save_color,
                'grayscale_saved': save_gray
            })

    cap.release()
    zip_buffer.seek(0)
    zip_bytes = zip_buffer.read()
    
    # Guardar el ZIP en disco
    video_dir = Path(video_path).parent
    fotogramas_dir = video_dir / "Fotogramas_Extraidos"
    
    # Si la carpeta existe, eliminarla y recrearla
    if fotogramas_dir.exists():
        shutil.rmtree(fotogramas_dir)
    fotogramas_dir.mkdir(exist_ok=True)
    
    # Guardar el ZIP
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    zip_filename = f"{video_name}_frames.zip"
    zip_path = fotogramas_dir / zip_filename
    
    with open(zip_path, 'wb') as zip_f:
        zip_f.write(zip_bytes)

    return {
        'video_name': os.path.basename(video_path),
        'total_frames_in_video': total_frames,
        'fps': fps,
        'frames_extracted': len(extraction_info),
        'start_frame': start_frame,
        'end_frame': end_frame,
        'skip_frames': skip,
        'brightness_applied': brightness_value,
        'color_frames_saved': save_color,
        'grayscale_frames_saved': save_gray,
        'extraction_info': extraction_info,
        'zip_bytes': zip_bytes,
        'zip_path': str(zip_path),
        'fotogramas_directory': str(fotogramas_dir),
        'extracted_at': datetime.now().isoformat()
    }
