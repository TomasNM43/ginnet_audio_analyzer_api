import cv2
import numpy as np
import base64
from typing import List, Dict


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


def ela_analysis(frame: np.ndarray, scale: int = 50, quality: int = 200) -> np.ndarray:
    """
    Realiza análisis ELA (Error Level Analysis) sobre un frame/imagen.
    Retorna la imagen ELA procesada.
    """
    _, compressed_buffer = cv2.imencode(
        '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    )
    compressed = cv2.imdecode(compressed_buffer, 1)

    diff = np.abs(frame.astype(np.float32) - compressed.astype(np.float32)) * scale
    output = diff.astype(np.uint8)

    gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        if cv2.contourArea(contour) > 40:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 0, 255), 2)

    return output


def analyze_images(image_paths: List[str]) -> List[Dict]:
    """
    Analiza una lista de imágenes con ELA.
    Retorna lista de resultados con metadatos y la imagen ELA en base64.
    """
    results = []

    for path in image_paths:
        frame = cv2.imread(path)
        if frame is None:
            results.append({
                'path': path,
                'error': 'No se pudo leer la imagen'
            })
            continue

        ela_img = ela_analysis(frame)

        _, buffer = cv2.imencode('.png', ela_img)
        ela_b64 = base64.b64encode(buffer).decode('utf-8')

        h, w = frame.shape[:2]
        results.append({
            'path': path,
            'width': w,
            'height': h,
            'ela_image_base64': ela_b64,
            'ela_image_format': 'png'
        })

    return results


def analyze_image_bytes(image_bytes: bytes, filter_type: str = 'sobel') -> Dict:
    """
    Analiza una imagen recibida como bytes (upload HTTP).
    Primero convierte a escala de grises y aplica filtro Laplaciano o Sobel.
    Luego realiza análisis ELA sobre la imagen procesada.
    Retorna metadatos y la imagen ELA en base64.
    
    filter_type: 'laplacian' o 'sobel' (por defecto 'sobel')
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return {'error': 'No se pudo decodificar la imagen'}

    # Paso 1: Convertir a escala de grises
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Paso 2: Aplicar filtro (Laplaciano o Sobel)
    if filter_type == 'laplacian':
        filtered = apply_laplacian_filter(gray)
    else:  # sobel por defecto
        filtered = apply_sobel_filter(gray)
    
    # Convertir de vuelta a BGR para el análisis ELA
    frame_processed = cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)
    
    # Paso 3: Realizar análisis ELA
    ela_img = ela_analysis(frame_processed)

    _, buffer = cv2.imencode('.png', ela_img)
    ela_b64 = base64.b64encode(buffer).decode('utf-8')

    h, w = frame.shape[:2]
    return {
        'width': w,
        'height': h,
        'filter_applied': filter_type,
        'ela_image_base64': ela_b64,
        'ela_image_format': 'png'
    }
