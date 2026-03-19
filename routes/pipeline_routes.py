"""
Rutas/Endpoints de pipeline global
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import shutil

from services.spectrogram_service import SpectrogramService
from services.yolo_service import YOLOAnalysisService
from services.report_service import ReportService
from services.transcription_service import TranscriptionService
from config import (
    TEMP_FILES_DIR, SPECTROGRAMS_DIR, SPECTROGRAMS_RANGE_DIR,
    SPECTROGRAMS_JUMPS_DIR, RESULTS_DIR, REPORTS_DIR, MODELS_DIR
)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


@router.post("/analyze")
async def full_analysis_pipeline(
    files: List[UploadFile] = File(...),
    spectrogram_mode: str = Form("normal"),
    segment_length: int = Form(3),
    start_time: Optional[float] = Form(None),
    end_time: Optional[float] = Form(None),
    time_jump: Optional[float] = Form(None),
    range_mode: str = Form("complete"),
):
    """
    Pipeline completo: generación de espectrogramas → análisis YOLO → reporte

    - **files**: Archivos de audio (WAV, MP3, FLAC, M4A)
    - **spectrogram_mode**: Modo de generación: `"normal"`, `"range"` o `"jumps"`
    - **segment_length**: Duración de cada segmento en segundos (afecta selección de modelo)
    - **start_time**: *(solo mode=range)* Tiempo inicial en segundos
    - **end_time**: *(solo mode=range)* Tiempo final en segundos
    - **time_jump**: *(solo mode=jumps o range+combined)* Salto de tiempo en segundos
    - **range_mode**: *(solo mode=range)* `"complete"` o `"combined"`
    """
    try:
        # ── Validaciones de parámetros ────────────────────────────────────────
        if spectrogram_mode not in ("normal", "range", "jumps"):
            raise HTTPException(
                status_code=400,
                detail="spectrogram_mode debe ser 'normal', 'range' o 'jumps'"
            )

        if spectrogram_mode == "range":
            if start_time is None or end_time is None:
                raise HTTPException(
                    status_code=400,
                    detail="start_time y end_time son requeridos para mode=range"
                )
            if start_time < 0:
                raise HTTPException(status_code=400, detail="start_time debe ser >= 0")
            if start_time >= end_time:
                raise HTTPException(
                    status_code=400,
                    detail="start_time debe ser menor que end_time"
                )

        if spectrogram_mode == "jumps":
            if time_jump is None or time_jump <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="time_jump debe ser un valor positivo para mode=jumps"
                )

        # ── Paso 1: Guardar archivos y seleccionar directorio de espectrogramas ─
        if spectrogram_mode == "normal":
            spec_dir = SPECTROGRAMS_DIR
        elif spectrogram_mode == "range":
            spec_dir = SPECTROGRAMS_RANGE_DIR
        else:
            spec_dir = SPECTROGRAMS_JUMPS_DIR

        if os.path.exists(spec_dir):
            shutil.rmtree(spec_dir)
        os.makedirs(spec_dir, exist_ok=True)
        os.makedirs(TEMP_FILES_DIR, exist_ok=True)

        spectrogram_results = []
        audio_filenames = []

        for i, file in enumerate(files):
            file_path = os.path.join(TEMP_FILES_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_prefix = f"audio_{i + 1}_{os.path.splitext(file.filename)[0]}"
            audio_filenames.append(file.filename)

            # ── Paso 1a: Generar espectrogramas ─────────────────────────────
            if spectrogram_mode == "normal":
                result = SpectrogramService.generate_spectrograms_for_file(
                    file_path, file_prefix, spec_dir, segment_length
                )
            elif spectrogram_mode == "range":
                result = SpectrogramService.generate_spectrograms_by_time_range(
                    file_path, file_prefix, spec_dir,
                    start_time, end_time, segment_length, range_mode,
                    time_jump if time_jump else segment_length
                )
            else:  # jumps
                result = SpectrogramService.generate_spectrograms_by_jumps(
                    file_path, file_prefix, spec_dir, time_jump, segment_length
                )

            spectrogram_results.append({
                "filename": file.filename,
                "file_index": i + 1,
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
                detail="No se generaron espectrogramas; verifique los archivos de audio."
            )

        # ── Paso 3: Análisis YOLO ─────────────────────────────────────────────
        os.makedirs(RESULTS_DIR, exist_ok=True)
        yolo_result = YOLOAnalysisService.run_yolo_analysis(
            model_path, spec_dir, RESULTS_DIR
        )

        # ── Paso 4: Generar reporte consolidado ───────────────────────────────
        os.makedirs(REPORTS_DIR, exist_ok=True)
        detections_data = yolo_result.get("detections_by_file", {})
        report_result = ReportService.generate_consolidated_report(
            detections_data, audio_filenames, REPORTS_DIR
        )

        # ── Respuesta final ───────────────────────────────────────────────────
        return JSONResponse(content={
            "success": True,
            "message": "Pipeline de análisis completo ejecutado correctamente",
            "pipeline_steps": {
                "1_spectrograms": {
                    "mode": spectrogram_mode,
                    "segment_length": segment_length,
                    "files_processed": len(files),
                    "results": spectrogram_results
                },
                "2_yolo_analysis": yolo_result,
                "3_report": report_result
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el pipeline de análisis: {str(e)}"
        )


@router.post("/transcribe")
async def transcription_pipeline(
    files: List[UploadFile] = File(...),
    language: str = Form("es-ES"),
    generate_report: bool = Form(True),
):
    """
    Pipeline de transcripción: transcripción de audio → (opcional) reporte TXT

    - **files**: Archivos de audio (WAV, MP3, FLAC, M4A)
    - **language**: Código de idioma (es-ES, en-US, fr-FR, etc.)
    - **generate_report**: Si es `true`, genera un reporte TXT con la transcripción
    """
    try:
        os.makedirs(TEMP_FILES_DIR, exist_ok=True)

        # ── Paso 1: Guardar archivos temporales ───────────────────────────────
        audio_paths = []
        for file in files:
            file_path = os.path.join(TEMP_FILES_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            audio_paths.append(file_path)

        # ── Paso 2: Transcribir ───────────────────────────────────────────────
        transcription_result = TranscriptionService.transcribe_multiple_files(
            audio_paths, language
        )

        response = {
            "success": True,
            "message": f"Transcripción completada para {len(files)} archivo(s)",
            "pipeline_steps": {
                "1_transcription": transcription_result
            }
        }

        # ── Paso 3: Generar reporte (opcional) ───────────────────────────────
        if generate_report:
            os.makedirs(REPORTS_DIR, exist_ok=True)
            report_result = ReportService.generate_transcription_report(
                transcription_result.get("transcriptions", []),
                REPORTS_DIR
            )
            response["pipeline_steps"]["2_report"] = report_result
            response["message"] += " y reporte generado"

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en el pipeline de transcripción: {str(e)}"
        )
