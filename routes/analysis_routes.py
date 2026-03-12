"""
Rutas/Endpoints para análisis YOLO
"""
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import os
from services.yolo_service import YOLOAnalysisService
from config import MODELS_DIR, SPECTROGRAMS_DIR, SPECTROGRAMS_RANGE_DIR, SPECTROGRAMS_JUMPS_DIR, RESULTS_DIR

router = APIRouter(prefix="/api/analysis", tags=["YOLO Analysis"])

@router.post("/run-yolo")
async def run_yolo_analysis(
    input_directory_type: str = Form("normal"),
    segment_length: int = Form(3)
):
    """
    Ejecuta análisis YOLO sobre espectrogramas generados
    
    - **input_directory_type**: "normal", "range" o "jumps"
    - **segment_length**: Duración del segmento (para seleccionar el modelo correcto)
    """
    try:
        # Seleccionar directorio de entrada
        if input_directory_type == "normal":
            input_dir = SPECTROGRAMS_DIR
        elif input_directory_type == "range":
            input_dir = SPECTROGRAMS_RANGE_DIR
        elif input_directory_type == "jumps":
            input_dir = SPECTROGRAMS_JUMPS_DIR
        else:
            raise HTTPException(status_code=400, detail="Tipo de directorio inválido")
        
        # Verificar que existan espectrogramas
        if not os.path.exists(input_dir) or not os.listdir(input_dir):
            raise HTTPException(
                status_code=400, 
                detail="No hay espectrogramas para analizar. Genere espectrogramas primero."
            )
        
        # Seleccionar modelo según duración del segmento
        if segment_length == 1:
            model_path = os.path.join(MODELS_DIR, 'grayscale', 'best.pt')
        else:
            model_path = os.path.join(MODELS_DIR, 'normal', 'best.pt')
        
        if not os.path.exists(model_path):
            raise HTTPException(
                status_code=404,
                detail=f"Modelo YOLO no encontrado: {model_path}"
            )
        
        # Crear directorio de resultados
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # Ejecutar análisis
        result = YOLOAnalysisService.run_yolo_analysis(
            model_path, input_dir, RESULTS_DIR
        )
        
        return JSONResponse(content={
            'success': True,
            'message': 'Análisis YOLO completado',
            **result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis YOLO: {str(e)}")


@router.post("/run-yolo-custom")
async def run_yolo_analysis_custom(
    input_directory: str = Form(...),
    model_type: str = Form("normal")
):
    """
    Ejecuta análisis YOLO con configuración personalizada
    
    - **input_directory**: Ruta al directorio con espectrogramas
    - **model_type**: "normal" o "grayscale"
    """
    try:
        # Verificar directorio
        if not os.path.exists(input_directory):
            raise HTTPException(status_code=404, detail="Directorio no encontrado")
        
        # Seleccionar modelo
        if model_type == "grayscale":
            model_path = os.path.join(MODELS_DIR, 'grayscale', 'best.pt')
        else:
            model_path = os.path.join(MODELS_DIR, 'normal', 'best.pt')
        
        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail=f"Modelo no encontrado: {model_path}")
        
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # Ejecutar análisis
        result = YOLOAnalysisService.run_yolo_analysis(
            model_path, input_directory, RESULTS_DIR
        )
        
        return JSONResponse(content={
            'success': True,
            'message': 'Análisis YOLO completado',
            **result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis YOLO: {str(e)}")


@router.get("/results")
async def get_analysis_results():
    """
    Obtiene el listado de archivos con detecciones
    """
    try:
        if not os.path.exists(RESULTS_DIR):
            return JSONResponse(content={
                'success': True,
                'detections': [],
                'total': 0
            })
        
        files = [f for f in os.listdir(RESULTS_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
        
        return JSONResponse(content={
            'success': True,
            'detections': files,
            'total': len(files),
            'directory': RESULTS_DIR
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo resultados: {str(e)}")
