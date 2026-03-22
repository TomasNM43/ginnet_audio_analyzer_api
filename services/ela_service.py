import cv2
import numpy as np
import base64
from typing import List, Dict


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


def analyze_image_bytes(image_bytes: bytes) -> Dict:
    """
    Analiza una imagen recibida como bytes (upload HTTP).
    Retorna metadatos y la imagen ELA en base64.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return {'error': 'No se pudo decodificar la imagen'}

    ela_img = ela_analysis(frame)

    _, buffer = cv2.imencode('.png', ela_img)
    ela_b64 = base64.b64encode(buffer).decode('utf-8')

    h, w = frame.shape[:2]
    return {
        'width': w,
        'height': h,
        'ela_image_base64': ela_b64,
        'ela_image_format': 'png'
    }
