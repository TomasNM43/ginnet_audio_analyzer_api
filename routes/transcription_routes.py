"""
Rutas/Endpoints para transcripción de audio
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import List
import os
import shutil
from services.transcription_service import TranscriptionService
from services.report_service import ReportService
from config import TEMP_FILES_DIR, REPORTS_DIR

router = APIRouter(prefix="/api/transcription", tags=["Transcription"])

@router.post("/transcribe")
async def transcribe_audio(
    files: List[UploadFile] = File(...),
    language: str = Form("es-ES")
):
    """
    Transcribe uno o más archivos de audio
    
    - **files**: Archivos de audio (WAV, MP3, FLAC, M4A)
    - **language**: Código de idioma (es-ES, en-US, fr-FR, etc.)
    """
    try:
        audio_paths = []
        
        # Guardar archivos temporales
        for file in files:
            file_path = os.path.join(TEMP_FILES_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            audio_paths.append(file_path)
        
        # Transcribir archivos
        result = TranscriptionService.transcribe_multiple_files(audio_paths, language)
        
        return JSONResponse(content={
            'success': True,
            'message': f'Transcripción completada para {len(files)} archivos',
            **result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en transcripción: {str(e)}")


@router.post("/transcribe-single")
async def transcribe_single_audio(
    file: UploadFile = File(...),
    language: str = Form("es-ES"),
    max_duration: int = Form(300)
):
    """
    Transcribe un solo archivo de audio
    
    - **file**: Archivo de audio
    - **language**: Código de idioma
    - **max_duration**: Duración máxima en segundos
    """
    try:
        # Guardar archivo temporal
        file_path = os.path.join(TEMP_FILES_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Transcribir
        transcription, method = TranscriptionService.transcribe_audio(
            file_path, language, max_duration
        )
        
        return JSONResponse(content={
            'success': True,
            'filename': file.filename,
            'transcription': transcription,
            'method': method,
            'language': language
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en transcripción: {str(e)}")


@router.post("/generate-report")
async def generate_transcription_report(
    files: List[UploadFile] = File(...),
    language: str = Form("es-ES")
):
    """
    Transcribe archivos y genera un reporte en formato TXT
    
    - **files**: Archivos de audio
    - **language**: Código de idioma
    """
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        audio_paths = []
        for file in files:
            file_path = os.path.join(TEMP_FILES_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            audio_paths.append(file_path)
        
        # Transcribir archivos
        transcription_result = TranscriptionService.transcribe_multiple_files(audio_paths, language)
        
        # Generar reporte
        report_result = ReportService.generate_transcription_report(
            transcription_result['transcriptions'],
            REPORTS_DIR
        )
        
        return JSONResponse(content={
            'success': True,
            'message': 'Reporte de transcripción generado',
            'transcription_result': transcription_result,
            'report_info': report_result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}")


@router.get("/download-report/{report_name}")
async def download_transcription_report(report_name: str):
    """
    Descarga un reporte de transcripción
    
    - **report_name**: Nombre del archivo de reporte
    """
    try:
        report_path = os.path.join(REPORTS_DIR, report_name)
        
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        
        return FileResponse(
            report_path,
            media_type="text/plain",
            filename=report_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando reporte: {str(e)}")
