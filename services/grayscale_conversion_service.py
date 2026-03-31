import cv2
import numpy as np
import os
import zipfile
import io
from typing import List, Dict
from datetime import datetime


def apply_laplacian_filter(gray_image: np.ndarray) -> np.ndarray:
    """
    Aplica un filtro Laplaciano a una imagen en escala de grises.
    Retorna la imagen con el filtro aplicado.
    """
    laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
    # Convertir a escala 0-255
    laplacian = np.absolute(laplacian)
    laplacian = np.uint8(laplacian)
    return laplacian


def apply_sobel_filter(gray_image: np.ndarray) -> np.ndarray:
    """
    Aplica el filtro Sobel (magnitud) a una imagen en escala de grises.
    Retorna la imagen con el filtro aplicado.
    """
    sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
    # Calcular la magnitud
    magnitude = np.sqrt(sobelx**2 + sobely**2)
    magnitude = np.uint8(magnitude)
    return magnitude


def apply_sobel_color_filter(image: np.ndarray) -> np.ndarray:
    """
    Aplica el filtro Sobel por canal BGR conservando el color.
    Produce una imagen oscura con bordes brillantes de color,
    equivalente al filtro de ejemplo.png. Las manchas negras (zonas
    sin bordes) son las que detecta el modelo de deteccion.
    """
    channels = cv2.split(image)
    filtered_channels = []
    for ch in channels:
        sx = cv2.Sobel(ch, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(ch, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sx**2 + sy**2)
        magnitude = np.clip(magnitude, 0, 255).astype(np.uint8)
        filtered_channels.append(magnitude)
    return cv2.merge(filtered_channels)


def convert_to_grayscale_bytes(image_bytes: bytes, original_filename: str, filter_type: str = 'sobel') -> Dict:
    """
    Convierte una imagen (bytes) a escala de grises y aplica filtro Laplaciano o Sobel.
    Retorna dict con metadatos y la imagen convertida en bytes.
    
    filter_type: 'laplacian' o 'sobel' (por defecto 'sobel')
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return {'error': f'No se pudo decodificar: {original_filename}'}

    # Paso 1: Convertir a escala de grises
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Paso 2: Aplicar filtro (Laplaciano o Sobel)
    if filter_type == 'laplacian':
        gray_filtered = apply_laplacian_filter(gray)
    else:  # sobel por defecto
        gray_filtered = apply_sobel_filter(gray)

    original_name, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    output_filename = f"{original_name}_gray_sobel.png" if filter_type == 'sobel' else f"{original_name}_gray_laplacian.png"

    _, buf = cv2.imencode('.png', gray_filtered)
    gray_bytes = buf.tobytes()

    h, w = gray_filtered.shape
    orig_h, orig_w = image.shape[:2]

    return {
        'original_name': original_filename,
        'output_name': output_filename,
        'original_size': (orig_w, orig_h),
        'grayscale_size': (w, h),
        'original_channels': 3 if len(image.shape) == 3 else 1,
        'original_file_size': len(image_bytes),
        'grayscale_file_size': len(gray_bytes),
        'filter_applied': filter_type,
        'gray_bytes': gray_bytes
    }


def batch_convert_to_grayscale(images: List[Dict], filter_type: str = 'sobel') -> Dict:
    """
    Convierte múltiples imágenes a escala de grises y aplica filtro Laplaciano o Sobel.

    images: lista de dicts con keys 'filename' (str) y 'bytes' (bytes)
    filter_type: 'laplacian' o 'sobel' (por defecto 'sobel')

    Retorna dict con resultados y un ZIP en bytes con todas las imágenes.
    """
    converted = []
    errors = []
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for img_data in images:
            result = convert_to_grayscale_bytes(img_data['bytes'], img_data['filename'], filter_type)

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
                    'filter_applied': result['filter_applied'],
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
        'filter_type': filter_type,
        'total_original_size_kb': total_original,
        'total_grayscale_size_kb': total_gray,
        'avg_size_reduction_pct': (
            (total_original - total_gray) / total_original * 100
            if total_original > 0 else 0
        ),
        'zip_bytes': zip_buffer.read(),
        'converted_at': datetime.now().isoformat()
    }
