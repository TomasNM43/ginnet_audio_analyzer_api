import cv2
import numpy as np
import os
import zipfile
import io
from typing import List, Dict
from datetime import datetime


def convert_to_grayscale_bytes(image_bytes: bytes, original_filename: str) -> Dict:
    """
    Convierte una imagen (bytes) a escala de grises.
    Retorna dict con metadatos y la imagen convertida en bytes.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return {'error': f'No se pudo decodificar: {original_filename}'}

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    original_name, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    output_filename = f"{original_name}_gray.png" if ext != '.png' else f"{original_name}_gray{ext}"

    _, buf = cv2.imencode('.png', gray)
    gray_bytes = buf.tobytes()

    h, w = gray.shape
    orig_h, orig_w = image.shape[:2]

    return {
        'original_name': original_filename,
        'output_name': output_filename,
        'original_size': (orig_w, orig_h),
        'grayscale_size': (w, h),
        'original_channels': 3 if len(image.shape) == 3 else 1,
        'original_file_size': len(image_bytes),
        'grayscale_file_size': len(gray_bytes),
        'gray_bytes': gray_bytes
    }


def batch_convert_to_grayscale(images: List[Dict]) -> Dict:
    """
    Convierte múltiples imágenes a escala de grises.

    images: lista de dicts con keys 'filename' (str) y 'bytes' (bytes)

    Retorna dict con resultados y un ZIP en bytes con todas las imágenes.
    """
    converted = []
    errors = []
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for img_data in images:
            result = convert_to_grayscale_bytes(img_data['bytes'], img_data['filename'])

            if 'error' in result:
                errors.append(result['error'])
            else:
                zf.writestr(result['output_name'], result['gray_bytes'])
                converted.append({
                    'original_name': result['original_name'],
                    'output_name': result['output_name'],
                    'original_size': result['original_size'],
                    'original_file_size_kb': result['original_file_size'] / 1024,
                    'grayscale_file_size_kb': result['grayscale_file_size'] / 1024,
                    'size_reduction_pct': (
                        (result['original_file_size'] - result['grayscale_file_size'])
                        / result['original_file_size'] * 100
                        if result['original_file_size'] > 0 else 0
                    )
                })

    zip_buffer.seek(0)

    total_original = sum(c['original_file_size_kb'] for c in converted)
    total_gray = sum(c['grayscale_file_size_kb'] for c in converted)

    return {
        'total_files': len(images),
        'converted_count': len(converted),
        'error_count': len(errors),
        'errors': errors,
        'converted': converted,
        'total_original_size_kb': total_original,
        'total_grayscale_size_kb': total_gray,
        'avg_size_reduction_pct': (
            (total_original - total_gray) / total_original * 100
            if total_original > 0 else 0
        ),
        'zip_bytes': zip_buffer.read(),
        'converted_at': datetime.now().isoformat()
    }
