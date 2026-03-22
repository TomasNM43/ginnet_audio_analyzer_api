"""
Rutas/Endpoints de pipeline global
"""
import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import shutil

from services.spectrogram_service import SpectrogramService
from services.yolo_service import YOLOAnalysisService
from services.report_service import ReportService
from services.transcription_service import TranscriptionService
from services.database_service import DatabaseService
from config import (
    TEMP_FILES_DIR, SPECTROGRAMS_DIR, SPECTROGRAMS_RANGE_DIR,
    SPECTROGRAMS_JUMPS_DIR, RESULTS_DIR, REPORTS_DIR, MODELS_DIR
)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


@router.post("/analyze")
async def full_analysis_pipeline(
    file_path: str = Form(...),
    segment_length: int = Form(3),
    paquete_id: Optional[int] = Form(None),
):
    """
    Pipeline completo: generación de espectrogramas → análisis YOLO → reporte

    - **file_path**: Ruta completa del archivo de audio (WAV, MP3, FLAC, M4A)
    - **segment_length**: Duración de cada segmento en segundos (afecta selección de modelo)
    - **paquete_id**: ID del paquete para actualizar en base de datos (opcional)
    """
    try:
        # ── Validaciones de parámetros ────────────────────────────────────────
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"El archivo no existe: {file_path}"
            )
        
        if not os.path.isfile(file_path):
            raise HTTPException(
                status_code=400,
                detail=f"La ruta no corresponde a un archivo: {file_path}"
            )

        # ── Paso 1: Crear estructura de carpetas para análisis ─
        file_dir = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Crear carpeta principal de análisis
        analysis_dir = os.path.join(file_dir, "Analisis_Audio")
        if os.path.exists(analysis_dir):
            shutil.rmtree(analysis_dir)
        os.makedirs(analysis_dir, exist_ok=True)
        
        # Crear subcarpetas dentro de Analisis_Audio
        spec_dir = os.path.join(analysis_dir, "spectrograms")
        os.makedirs(spec_dir, exist_ok=True)

        spectrogram_results = []
        audio_filenames = [filename]

        # ── Paso 1a: Generar espectrogramas ─────────────────────────────────
        file_prefix = f"audio_{filename_without_ext}"
        result = SpectrogramService.generate_spectrograms_for_file(
            file_path, file_prefix, spec_dir, segment_length
        )

        spectrogram_results.append({
            "filename": filename,
            "file_index": 1,
            **result
        })

        # ── Paso 2: Seleccionar modelo YOLO ───────────────────────────────────
        if segment_length == 1:
            model_path = os.path.join(MODELS_DIR, "grayscale", "best.pt")
        else:
            model_path = os.path.join(MODELS_DIR, "normal", "best.pt")

        if not os.path.exists(model_path):
            raise HTTPException(
                status_code=404,
                detail=f"Modelo YOLO no encontrado: {model_path}"
            )

        if not os.path.exists(spec_dir) or not os.listdir(spec_dir):
            raise HTTPException(
                status_code=400,
                detail="No se generaron espectrogramas; verifique el archivo de audio."
            )

        # ── Paso 3: Crear carpeta de resultados dentro de Analisis_Audio ─
        results_dir = os.path.join(analysis_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        # ── Paso 4: Análisis YOLO ─────────────────────────────────────────────
        yolo_result = YOLOAnalysisService.run_yolo_analysis(
            model_path, spec_dir, results_dir
        )

        # ── Paso 5: Crear carpeta de reportes dentro de Analisis_Audio ───
        reports_dir = os.path.join(analysis_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        detections_data = yolo_result.get("detections_by_file", {})
        report_result = ReportService.generate_consolidated_report(
            detections_data, audio_filenames, reports_dir
        )

        # ── Paso 6: Actualizar base de datos con la ruta del reporte ─────────
        db_update_result = None
        print(f"Paquete ID recibido: {paquete_id}")
        if paquete_id is not None:
            report_file_path = report_result.get("report_path")  # Ruta completa del reporte
            if report_file_path:
                # Convertir todas las barras / a \ para Windows
                report_file_path_windows = report_file_path.replace('\\', '/')
                print(f"Actualizando base de datos con ruta del reporte: {report_file_path_windows}, paquete_id: {paquete_id}")
                db_update_result = DatabaseService.update_paquete_proceso_informe_1(
                    report_file_path_windows, paquete_id
                )

        # ── Respuesta final ───────────────────────────────────────────────────
        response_content = {
            "success": True,
            "message": "Pipeline de análisis completo ejecutado correctamente",
            "file_directory": file_dir,
            "analysis_directory": analysis_dir,
            "pipeline_steps": {
                "1_spectrograms": {
                    "segment_length": segment_length,
                    "directory": spec_dir,
                    "results": spectrogram_results
                },
                "2_yolo_analysis": {
                    **yolo_result,
                    "results_directory": results_dir
                },
                "3_report": {
                    **report_result,
                    "report_directory": reports_dir
                }
            }
        }
        
        if db_update_result:
            response_content["database_update"] = db_update_result
        
        return JSONResponse(content=response_content)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el pipeline de análisis: {str(e)}"
        )


@router.post("/transcribe")
async def transcription_pipeline(
    file_path: str = Form(...),
    paquete_id: Optional[int] = Form(None),
):
    """
    Pipeline de transcripción: transcripción de audio → reporte TXT

    - **file_path**: Ruta completa del archivo de audio (WAV, MP3, FLAC, M4A)
    - **paquete_id**: ID del paquete para actualizar en base de datos (opcional)
    
    Nota: La transcripción siempre se realiza en español (es-ES) y genera reporte automáticamente
    """
    try:
        # ── Validaciones de parámetros ────────────────────────────────────────
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"El archivo no existe: {file_path}"
            )
        
        if not os.path.isfile(file_path):
            raise HTTPException(
                status_code=400,
                detail=f"La ruta no corresponde a un archivo: {file_path}"
            )

        # ── Paso 1: Transcribir (siempre en español) ──────────────────────────
        language = "es-ES"
        audio_paths = [file_path]
        transcription_result = TranscriptionService.transcribe_multiple_files(
            audio_paths, language
        )

        # ── Paso 2: Crear estructura de carpetas para transcripción ───────────
        file_dir = os.path.dirname(file_path)
        
        # Crear carpeta principal de transcripción
        transcription_dir = os.path.join(file_dir, "Transcripcion")
        if os.path.exists(transcription_dir):
            shutil.rmtree(transcription_dir)
        os.makedirs(transcription_dir, exist_ok=True)
        
        # Carpeta de reportes dentro de Transcripcion
        reports_dir = os.path.join(transcription_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        report_result = ReportService.generate_transcription_report(
            transcription_result.get("transcriptions", []),
            reports_dir
        )

        # ── Paso 3: Actualizar base de datos con la ruta del reporte ─────────
        db_update_result = None
        if paquete_id is not None:
            report_file_path = report_result.get("report_path")  # Ruta completa del reporte
            if report_file_path:
                # Convertir todas las barras / a \\ para Windows
                report_file_path_windows = report_file_path.replace('\\', '/')
                print(f"Actualizando base de datos con ruta del reporte transcripción: {report_file_path_windows}, paquete_id: {paquete_id}")
                db_update_result = DatabaseService.update_paquete_proceso_informe_3(
                    report_file_path_windows, paquete_id
                )

        response = {
            "success": True,
            "message": "Transcripción completada y reporte generado",
            "file_directory": file_dir,
            "transcription_directory": transcription_dir,
            "pipeline_steps": {
                "1_transcription": transcription_result,
                "2_report": {
                    **report_result,
                    "report_directory": reports_dir
                }
            }
        }
        
        if db_update_result:
            response["database_update"] = db_update_result

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el pipeline de transcripción: {str(e)}"
        )
