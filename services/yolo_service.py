"""
Servicio para análisis de audio con YOLO
"""
import os
import shutil
import cv2
from ultralytics import YOLO
from typing import Dict

class YOLOAnalysisService:
    """Servicio para análisis de espectrogramas con YOLO"""
    
    @staticmethod
    def run_yolo_analysis(model_path: str, input_dir: str, output_dir: str) -> Dict[str, any]:
        """
        Ejecuta análisis YOLO sobre espectrogramas
        
        Args:
            model_path: Ruta al modelo YOLO (.pt)
            input_dir: Directorio con espectrogramas a analizar
            output_dir: Directorio para guardar resultados
            
        Returns:
            Diccionario con detecciones organizadas por archivo
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
        
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Directorio de entrada no encontrado: {input_dir}")
        
        model = YOLO(model_path)
        os.makedirs(output_dir, exist_ok=True)
        
        detections_by_file = {}
        processed_files = 0
        total_detections = 0
        
        for img_name in os.listdir(input_dir):
            if not img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            
            img_path = os.path.join(input_dir, img_name)
            
            try:
                img = cv2.imread(img_path)
                if img is None:
                    print(f"No se pudo cargar la imagen: {img_name}")
                    continue
                
                results = model(img)
                processed_files += 1
                
                # Extraer información del archivo
                parts = img_name.split('_')
                
                # Buscar la palabra "spectrogram"
                spectrogram_index = -1
                for i, part in enumerate(parts):
                    if part == 'spectrogram':
                        spectrogram_index = i
                        break
                
                if spectrogram_index >= 0 and len(parts) >= spectrogram_index + 3:
                    file_prefix = '_'.join(parts[:spectrogram_index])
                    try:
                        start_time = int(parts[spectrogram_index + 1])
                        end_time_str = parts[spectrogram_index + 2].replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
                        end_time = int(end_time_str)
                    except (ValueError, IndexError) as e:
                        print(f"Error al parsear tiempos del archivo {img_name}: {e}")
                        file_prefix = 'unknown'
                        start_time = 0
                        end_time = 0
                else:
                    print(f"Formato de archivo no reconocido: {img_name}")
                    file_prefix = 'unknown'
                    start_time = 0
                    end_time = 0
                
                if file_prefix not in detections_by_file:
                    detections_by_file[file_prefix] = {
                        'segments': [], 
                        'detections': [],
                        'total_segments': 0,
                        'total_detections': 0
                    }
                
                # Información del segmento
                has_detection = len(results[0].boxes) > 0
                detections_by_file[file_prefix]['segments'].append({
                    'start': start_time,
                    'end': end_time,
                    'has_detection': has_detection,
                    'image_path': img_path,
                    'image_name': img_name
                })
                detections_by_file[file_prefix]['total_segments'] += 1
                
                if has_detection:
                    shutil.copy(img_path, os.path.join(output_dir, img_name))
                    detections_by_file[file_prefix]['detections'].append({
                        'start': start_time,
                        'end': end_time,
                        'image_path': img_path,
                        'image_name': img_name
                    })
                    detections_by_file[file_prefix]['total_detections'] += 1
                    total_detections += 1
                    
            except Exception as e:
                print(f"Error procesando archivo {img_name}: {e}")
                continue
        
        return {
            'detections_by_file': detections_by_file,
            'total_files_processed': processed_files,
            'total_detections': total_detections,
            'model_used': os.path.basename(model_path)
        }
