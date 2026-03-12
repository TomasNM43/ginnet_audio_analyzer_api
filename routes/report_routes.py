"""
Rutas/Endpoints para generación de reportes
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict
import os
import shutil
from services.report_service import ReportService
from config import REPORTS_DIR

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.post("/generate-consolidated")
async def generate_consolidated_report(
    detections_data: Dict = Form(...),
    audio_files: List[str] = Form(...)
):
    """
    Genera un reporte consolidado en formato Word
    
    - **detections_data**: JSON con datos de detecciones por archivo
    - **audio_files**: Lista de nombres de archivos de audio procesados
    """
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        # Si detections_data viene como string JSON, parsearlo
        if isinstance(detections_data, str):
            import json
            detections_data = json.loads(detections_data)
        
        # Generar reporte
        result = ReportService.generate_consolidated_report(
            detections_data,
            audio_files,
            REPORTS_DIR
        )
        
        return JSONResponse(content={
            'success': True,
            'message': 'Reporte consolidado generado',
            **result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}")


@router.post("/generate-chart")
async def generate_summary_chart(
    detections_data: Dict = Form(...)
):
    """
    Genera un gráfico resumen de detecciones
    
    - **detections_data**: JSON con datos de detecciones por archivo
    """
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        # Si detections_data viene como string JSON, parsearlo
        if isinstance(detections_data, str):
            import json
            detections_data = json.loads(detections_data)
        
        # Generar gráfico
        chart_path = os.path.join(REPORTS_DIR, 'summary_chart.png')
        ReportService.create_summary_chart(detections_data, chart_path)
        
        return JSONResponse(content={
            'success': True,
            'message': 'Gráfico generado',
            'chart_path': chart_path,
            'chart_name': 'summary_chart.png'
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando gráfico: {str(e)}")


@router.get("/list")
async def list_reports():
    """
    Lista todos los reportes generados
    """
    try:
        if not os.path.exists(REPORTS_DIR):
            return JSONResponse(content={
                'success': True,
                'reports': [],
                'total': 0
            })
        
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(('.docx', '.txt', '.png'))]
        
        reports_by_type = {
            'word': [f for f in files if f.endswith('.docx')],
            'text': [f for f in files if f.endswith('.txt')],
            'images': [f for f in files if f.endswith('.png')]
        }
        
        return JSONResponse(content={
            'success': True,
            'reports': files,
            'reports_by_type': reports_by_type,
            'total': len(files)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando reportes: {str(e)}")


@router.get("/download/{report_name}")
async def download_report(report_name: str):
    """
    Descarga un reporte específico
    
    - **report_name**: Nombre del archivo de reporte
    """
    try:
        report_path = os.path.join(REPORTS_DIR, report_name)
        
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        
        # Determinar tipo de contenido
        if report_name.endswith('.docx'):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif report_name.endswith('.txt'):
            media_type = "text/plain"
        elif report_name.endswith('.png'):
            media_type = "image/png"
        else:
            media_type = "application/octet-stream"
        
        return FileResponse(
            report_path,
            media_type=media_type,
            filename=report_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando reporte: {str(e)}")


@router.delete("/delete/{report_name}")
async def delete_report(report_name: str):
    """
    Elimina un reporte específico
    
    - **report_name**: Nombre del archivo de reporte
    """
    try:
        report_path = os.path.join(REPORTS_DIR, report_name)
        
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        
        os.remove(report_path)
        
        return JSONResponse(content={
            'success': True,
            'message': f'Reporte {report_name} eliminado'
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando reporte: {str(e)}")
