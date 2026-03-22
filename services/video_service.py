import cv2
import numpy as np
import os
from typing import List, Dict, Optional
from datetime import datetime


def adjust_brightness(image: np.ndarray, brightness_value: int) -> np.ndarray:
    """Ajusta el brillo de una imagen. brightness_value: -100 a 100."""
    if brightness_value == 0:
        return image
    image_float = image.astype(np.float32)
    brightened = np.clip(image_float + brightness_value, 0, 255)
    return brightened.astype(np.uint8)


def detect_black_rectangles(yolo_model, frame: np.ndarray) -> List[Dict]:
    """Detecta rectángulos negros en un frame usando YOLOv8."""
    if yolo_model is None:
        return []

    try:
        if len(frame.shape) == 2:
            frame_input = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        else:
            frame_input = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = yolo_model(frame_input, verbose=False)
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                xyxy = boxes.xyxy.cpu().numpy()
                conf = boxes.conf.cpu().numpy()
                cls = boxes.cls.cpu().numpy()

                for i in range(len(xyxy)):
                    x1, y1, x2, y2 = xyxy[i]
                    confidence = float(conf[i])
                    class_id = int(cls[i])

                    if confidence > 0.5:
                        x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)
                        class_name = yolo_model.names[class_id] if hasattr(yolo_model, 'names') else f'class_{class_id}'
                        detections.append({
                            'bbox': (x, y, w, h),
                            'confidence': confidence,
                            'class_id': class_id,
                            'class_name': class_name
                        })

        return detections

    except Exception as e:
        print(f"Error en detección YOLOv8: {e}")
        return []


def annotate_frame(frame: np.ndarray, detections: List[Dict], frame_count: int,
                   fps: float, brightness_applied: int) -> np.ndarray:
    """Dibuja las anotaciones YOLO sobre un frame."""
    detection_frame = frame.copy()
    frame_height, frame_width = frame.shape[:2]

    for det_idx, detection in enumerate(detections):
        x, y, w, h = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class_name']

        cv2.rectangle(detection_frame, (x, y), (x + w, y + h), (0, 0, 255), 3)

        corner_size = 10
        for cx, cy in [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]:
            dx = corner_size if cx == x else -corner_size
            dy = corner_size if cy == y else -corner_size
            cv2.line(detection_frame, (cx, cy), (cx + dx, cy), (0, 255, 255), 3)
            cv2.line(detection_frame, (cx, cy), (cx, cy + dy), (0, 255, 255), 3)

        center_x, center_y = x + w // 2, y + h // 2
        cv2.circle(detection_frame, (center_x, center_y), 5, (255, 0, 255), -1)

        rel_x = (x / frame_width) * 100
        rel_y = (y / frame_height) * 100
        rel_w = (w / frame_width) * 100
        rel_h = (h / frame_height) * 100
        time_seconds = frame_count / fps if fps > 0 else frame_count

        info_texts = [
            f"YOLO DETECCION: {class_name.upper()}",
            f"Confianza: {confidence:.3f} | Frame: {frame_count}",
            f"Tiempo: {time_seconds:.2f}s | Brillo: +{brightness_applied}",
            f"Posicion absoluta: ({x}, {y})",
            f"Dimensiones: {w} x {h} pixels",
            f"Centro: ({center_x}, {center_y})",
            f"Posicion relativa: ({rel_x:.1f}%, {rel_y:.1f}%)",
        ]

        y_offset = 25 + (det_idx * 240)
        for i, text in enumerate(info_texts):
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            bg_color = (0, 100, 0) if i == 0 else (100, 0, 100) if i == 1 else (50, 50, 50)
            text_color = (255, 255, 255) if i < 2 else (0, 255, 0)
            cv2.rectangle(detection_frame,
                          (10, y_offset + i * 30 - 20),
                          (15 + text_size[0], y_offset + i * 30 + 5),
                          bg_color, -1)
            cv2.putText(detection_frame, text, (12, y_offset + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)

    return detection_frame


def analyze_video(video_path: str, yolo_model, brightness_applied: int,
                  output_dir: str, model_path: str) -> Dict:
    """
    Analiza un video con YOLOv8 buscando rectángulos negros.
    Retorna diccionario con resultados y metadatos.
    """
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video: {video_path}")

    frame_count = 0
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    detections_for_video = []

    video_name = os.path.basename(video_path)
    print(f"Procesando video: {video_name} | Total frames: {total_frames} | FPS: {fps}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % max(1, int(fps)) == 0:
            brightened = adjust_brightness(frame, brightness_applied)
            gray = cv2.cvtColor(brightened, cv2.COLOR_BGR2GRAY)

            gray_path = os.path.join(output_dir, f"gray_frame_{frame_count}.png")
            cv2.imwrite(gray_path, gray)

            gray_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            detections = detect_black_rectangles(yolo_model, gray_rgb)

            if detections:
                detection_frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                annotated = annotate_frame(detection_frame, detections, frame_count,
                                           fps, brightness_applied)
                img_path = os.path.join(output_dir, f"yolo_detection_frame_{frame_count}.png")
                cv2.imwrite(img_path, annotated)

                frame_h, frame_w = frame.shape[:2]
                time_seconds = frame_count / fps if fps > 0 else frame_count

                for det in detections:
                    x, y, w, h = det['bbox']
                    rel_x = (x / frame_w) * 100
                    rel_y = (y / frame_h) * 100
                    rel_w = (w / frame_w) * 100
                    rel_h = (h / frame_h) * 100
                    center_x, center_y = x + w // 2, y + h // 2

                    detections_for_video.append({
                        'frame': frame_count,
                        'time': time_seconds,
                        'bbox': (x, y, w, h),
                        'center': (center_x, center_y),
                        'confidence': det['confidence'],
                        'class_name': det['class_name'],
                        'class_id': det['class_id'],
                        'relative_position': (rel_x, rel_y),
                        'relative_size': (rel_w, rel_h),
                        'area_pixels': w * h,
                        'area_percentage': (rel_w * rel_h / 100),
                        'frame_size': (frame_w, frame_h),
                        'brightness_applied': brightness_applied,
                        'detection_image': f"yolo_detection_frame_{frame_count}.png"
                    })

        frame_count += 1
        if frame_count % 100 == 0:
            pct = (frame_count / total_frames * 100) if total_frames > 0 else 0
            print(f"  Progreso: {pct:.1f}% ({frame_count}/{total_frames})")

    cap.release()

    return {
        'video_path': video_path,
        'video_name': video_name,
        'output_dir': output_dir,
        'total_frames': frame_count,
        'fps': fps,
        'duration': frame_count / fps if fps > 0 else 0,
        'detections': detections_for_video,
        'detection_count': len(detections_for_video),
        'brightness_applied': brightness_applied,
        'model_path': model_path,
        'modelo_usado': os.path.basename(model_path),
        'analyzed_at': datetime.now().isoformat()
    }
