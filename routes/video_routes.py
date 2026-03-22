"""
Rutas/Endpoints para análisis de videos e imágenes
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional
import os
import tempfile
import shutil
import io
from datetime import datetime

router = APIRouter(prefix="/api/video", tags=["Video Analysis"])

# Variables globales para YOLO
_yolo_models = {}
YOLO_AVAILABLE = False
TORCH_AVAILABLE = False
DEVICE = 'cpu'

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    pass

try:
    import torch
    TORCH_AVAILABLE = True
    DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
except Exception:
    pass


def _get_yolo_model(brightness: int = 20):
    """Carga y cachea el modelo YOLO según el brillo seleccionado."""
    if not YOLO_AVAILABLE:
        return None

    from config import MODELS_BRIGHTNESS_DIR
    
    model_files = {20: 'best_20.pt', 30: 'best_30.pt', 40: 'best_40.pt'}
    filename = model_files.get(brightness, 'best_20.pt')
    model_path = os.path.join(MODELS_BRIGHTNESS_DIR, filename)

    if brightness not in _yolo_models:
        if not os.path.exists(model_path):
            print(f"ADVERTENCIA: Modelo no encontrado en {model_path}")
            return None
        model = YOLO(model_path)
        if TORCH_AVAILABLE and torch.cuda.is_available():
            model.to('cuda')
        _yolo_models[brightness] = model
        print(f"Modelo YOLO cargado: {model_path}")

    return _yolo_models.get(brightness)


# ─────────────────────────────────────────────────────────────────────────────
# AUTENTICIDAD DE VIDEO (YOLO)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/autenticidad")
async def autenticidad_video(
    file_path: str = Form(...),
    brightness: int = Form(20, description="Brillo aplicado: 20, 30 o 40"),
    paquete_id: Optional[int] = Form(None, description="ID del paquete para actualizar en base de datos")
):
    """
    Analiza un video con YOLOv8 detectando rectángulos negros.
    Procesa un frame por segundo con el brillo indicado.
    Retorna JSON con las detecciones encontradas.
    
    - **file_path**: Ruta completa del archivo de video
    - **brightness**: Brillo aplicado (20, 30 o 40)
    - **paquete_id**: ID del paquete para actualizar en base de datos (opcional)
    """
    if brightness not in (20, 30, 40):
        raise HTTPException(status_code=400, detail="brightness debe ser 20, 30 o 40")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"El archivo no existe: {file_path}")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"La ruta no corresponde a un archivo: {file_path}")

    yolo_model = _get_yolo_model(brightness)
    if yolo_model is None:
        raise HTTPException(
            status_code=503,
            detail="Modelo YOLO no disponible. Verifique que los archivos .pt estén en modelos_brightness/."
        )

    from services.video_service import analyze_video
    from services.database_service import DatabaseService
    from config import MODELS_BRIGHTNESS_DIR

    try:
        # Crear estructura de carpetas dentro del directorio del video
        file_dir = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Crear carpeta Autenticidad/Reporte
        autenticidad_dir = os.path.join(file_dir, "Autenticidad")
        if os.path.exists(autenticidad_dir):
            shutil.rmtree(autenticidad_dir)
        os.makedirs(autenticidad_dir, exist_ok=True)
        
        reporte_dir = os.path.join(autenticidad_dir, "Reporte")
        os.makedirs(reporte_dir, exist_ok=True)
        
        # Carpeta temporal para resultados del análisis
        output_dir = os.path.join(autenticidad_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        model_path = os.path.join(MODELS_BRIGHTNESS_DIR, f'best_{brightness}.pt')

        result = analyze_video(
            video_path=file_path,
            yolo_model=yolo_model,
            brightness_applied=brightness,
            output_dir=output_dir,
            model_path=model_path
        )

        # Serializar coords a listas (JSON-serializable)
        for det in result.get('detections', []):
            det['bbox'] = list(det['bbox'])
            det['center'] = list(det['center'])
            det['relative_position'] = list(det['relative_position'])
            det['relative_size'] = list(det['relative_size'])
            det['frame_size'] = list(det['frame_size'])

        # Quitar campos no serializables
        result.pop('output_dir', None)
        result.pop('video_path', None)

        # Generar y guardar el informe PDF en la carpeta Reporte
        nombre_informe = None
        informe_path = None
        try:
            from utils.video_report_generator import generate_yolo_report_pdf
            pdf_bytes = generate_yolo_report_pdf([result], device=DEVICE)
            nombre_informe = f"Informe_Autenticidad_{filename_without_ext}.pdf"
            informe_path = os.path.join(reporte_dir, nombre_informe)
            with open(informe_path, 'wb') as inf_f:
                inf_f.write(pdf_bytes)
        except Exception as rep_err:
            print(f"ADVERTENCIA: No se pudo generar el informe PDF: {rep_err}")

        # Actualizar base de datos con la ruta del reporte
        db_update_result = None
        if paquete_id is not None and informe_path:
            # Convertir todas las barras \\ a /
            informe_path_windows = informe_path.replace('\\', '/')
            print(f"Actualizando base de datos con ruta del reporte: {informe_path_windows}, paquete_id: {paquete_id}")
            db_update_result = DatabaseService.update_paquete_proceso_informe_1(
                informe_path_windows, paquete_id
            )
        
        response = {
            **result,
            "autenticidad_directory": autenticidad_dir,
            "reporte_directory": reporte_dir,
            "informe_path": informe_path
        }
        
        if db_update_result:
            response["database_update"] = db_update_result

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# CONTINUIDAD DE VIDEO
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/continuidad")
async def continuidad_video(
    file_path: str = Form(...),
    paquete_id: Optional[int] = Form(None, description="ID del paquete para actualizar en base de datos")
):
    """
    Analiza la continuidad de un video. Detecta cortes o ediciones abruptas.
    Retorna JSON con discontinuidades y el gráfico en base64.
    
    - **file_path**: Ruta completa del archivo de video
    - **paquete_id**: ID del paquete para actualizar en base de datos (opcional)
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"El archivo no existe: {file_path}")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"La ruta no corresponde a un archivo: {file_path}")
    
    from services.continuity_service import analyze_continuity
    from services.database_service import DatabaseService

    try:
        # Crear estructura de carpetas dentro del directorio del video
        file_dir = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Crear carpeta Continuidad/Reporte
        continuidad_dir = os.path.join(file_dir, "Continuidad")
        if os.path.exists(continuidad_dir):
            shutil.rmtree(continuidad_dir)
        os.makedirs(continuidad_dir, exist_ok=True)
        
        reporte_dir = os.path.join(continuidad_dir, "Reporte")
        os.makedirs(reporte_dir, exist_ok=True)

        result = analyze_continuity(file_path)

        # No retornar euclidean_distances completo (puede ser muy grande), solo resumen
        result.pop('euclidean_distances', None)
        # No retornar images de comparación en la respuesta JSON principal
        for disc in result.get('discontinuities', []):
            disc.pop('comparison_image_base64', None)

        # Generar y guardar el informe PDF en la carpeta Reporte
        nombre_informe = None
        informe_path = None
        try:
            from utils.video_report_generator import generate_continuity_report_pdf
            pdf_bytes = generate_continuity_report_pdf([result])
            nombre_informe = f"Informe_Continuidad_{filename_without_ext}.pdf"
            informe_path = os.path.join(reporte_dir, nombre_informe)
            with open(informe_path, 'wb') as inf_f:
                inf_f.write(pdf_bytes)
        except Exception as rep_err:
            print(f"ADVERTENCIA: No se pudo generar el informe PDF: {rep_err}")

        # Actualizar base de datos con la ruta del reporte
        db_update_result = None
        if paquete_id is not None and informe_path:
            # Convertir todas las barras \\ a /
            informe_path_windows = informe_path.replace('\\', '/')
            print(f"Actualizando base de datos con ruta del reporte: {informe_path_windows}, paquete_id: {paquete_id}")
            db_update_result = DatabaseService.update_paquete_proceso_informe_3(
                informe_path_windows, paquete_id
            )
        
        response = {
            **result,
            "continuidad_directory": continuidad_dir,
            "reporte_directory": reporte_dir,
            "informe_path": informe_path
        }
        
        if db_update_result:
            response["database_update"] = db_update_result

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def video_status():
    """
    Retorna el estado del servicio de análisis de video.
    """
    return {
        "service": "Video Analysis API",
        "yolo_available": YOLO_AVAILABLE,
        "torch_available": TORCH_AVAILABLE,
        "device": DEVICE,
        "models_loaded": list(_yolo_models.keys())
    }
