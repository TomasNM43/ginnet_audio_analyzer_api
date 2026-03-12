"""
Rutas/Endpoints para generación de espectrogramas
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional
import os
import shutil
from services.spectrogram_service import SpectrogramService
from config import TEMP_FILES_DIR, SPECTROGRAMS_DIR, SPECTROGRAMS_RANGE_DIR, SPECTROGRAMS_JUMPS_DIR

router = APIRouter(prefix="/api/spectrograms", tags=["Spectrograms"])

@router.post("/generate")
async def generate_spectrograms(
    files: List[UploadFile] = File(...),
    segment_length: int = Form(3)
):
    """
    Genera espectrogramas para uno o más archivos de audio
    
    - **files**: Archivos de audio (WAV, MP3, FLAC, M4A)
    - **segment_length**: Duración de cada segmento en segundos
    """
    try:
        # Limpiar directorio de espectrogramas
        if os.path.exists(SPECTROGRAMS_DIR):
            shutil.rmtree(SPECTROGRAMS_DIR)
        os.makedirs(SPECTROGRAMS_DIR, exist_ok=True)
        
        results = []
        
        for i, file in enumerate(files):
            # Guardar archivo temporal
            file_path = os.path.join(TEMP_FILES_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Generar prefijo para nombrar archivos
            file_prefix = f"audio_{i+1}_{os.path.splitext(file.filename)[0]}"
            
            # Generar espectrogramas
            result = SpectrogramService.generate_spectrograms_for_file(
                file_path, file_prefix, SPECTROGRAMS_DIR, segment_length
            )
            
            results.append({
                'filename': file.filename,
                'file_index': i + 1,
                **result
            })
        
        return JSONResponse(content={
            'success': True,
            'message': f'Espectrogramas generados para {len(files)} archivos',
            'total_files': len(files),
            'segment_length': segment_length,
            'results': results
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando espectrogramas: {str(e)}")


@router.post("/generate-by-range")
async def generate_spectrograms_by_range(
    files: List[UploadFile] = File(...),
    start_time: float = Form(...),
    end_time: float = Form(...),
    segment_length: int = Form(3),
    mode: str = Form("complete"),
    time_jump: Optional[float] = Form(3)
):
    """
    Genera espectrogramas en un rango de tiempo específico
    
    - **files**: Archivos de audio
    - **start_time**: Tiempo inicial en segundos
    - **end_time**: Tiempo final en segundos
    - **segment_length**: Duración de cada segmento en segundos
    - **mode**: "complete" o "combined"
    - **time_jump**: Salto de tiempo para modo combinado (opcional)
    """
    try:
        # Validaciones
        if start_time < 0:
            raise HTTPException(status_code=400, detail="El tiempo inicial debe ser mayor o igual a 0")
        if start_time >= end_time:
            raise HTTPException(status_code=400, detail="El tiempo inicial debe ser menor que el tiempo final")
        
        # Limpiar directorio
        if os.path.exists(SPECTROGRAMS_RANGE_DIR):
            shutil.rmtree(SPECTROGRAMS_RANGE_DIR)
        os.makedirs(SPECTROGRAMS_RANGE_DIR, exist_ok=True)
        
        results = []
        
        for i, file in enumerate(files):
            # Guardar archivo temporal
            file_path = os.path.join(TEMP_FILES_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_prefix = f"audio_{i+1}_{os.path.splitext(file.filename)[0]}"
            
            # Generar espectrogramas por rango
            result = SpectrogramService.generate_spectrograms_by_time_range(
                file_path, file_prefix, SPECTROGRAMS_RANGE_DIR,
                start_time, end_time, segment_length, mode, time_jump
            )
            
            results.append({
                'filename': file.filename,
                'file_index': i + 1,
                **result
            })
        
        return JSONResponse(content={
            'success': True,
            'message': f'Espectrogramas por rango generados para {len(files)} archivos',
            'total_files': len(files),
            'start_time': start_time,
            'end_time': end_time,
            'mode': mode,
            'results': results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando espectrogramas por rango: {str(e)}")


@router.post("/generate-by-jumps")
async def generate_spectrograms_by_jumps(
    files: List[UploadFile] = File(...),
    time_jump: float = Form(3),
    segment_length: int = Form(3)
):
    """
    Genera espectrogramas con saltos de tiempo específicos
    
    - **files**: Archivos de audio
    - **time_jump**: Salto de tiempo en segundos
    - **segment_length**: Duración de cada segmento en segundos
    """
    try:
        if time_jump <= 0:
            raise HTTPException(status_code=400, detail="El salto de tiempo debe ser mayor que 0")
        
        # Limpiar directorio
        if os.path.exists(SPECTROGRAMS_JUMPS_DIR):
            shutil.rmtree(SPECTROGRAMS_JUMPS_DIR)
        os.makedirs(SPECTROGRAMS_JUMPS_DIR, exist_ok=True)
        
        results = []
        
        for i, file in enumerate(files):
            # Guardar archivo temporal
            file_path = os.path.join(TEMP_FILES_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_prefix = f"audio_{i+1}_{os.path.splitext(file.filename)[0]}"
            
            # Generar espectrogramas por saltos
            result = SpectrogramService.generate_spectrograms_by_jumps(
                file_path, file_prefix, SPECTROGRAMS_JUMPS_DIR,
                time_jump, segment_length
            )
            
            results.append({
                'filename': file.filename,
                'file_index': i + 1,
                **result
            })
        
        return JSONResponse(content={
            'success': True,
            'message': f'Espectrogramas por saltos generados para {len(files)} archivos',
            'total_files': len(files),
            'time_jump': time_jump,
            'results': results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando espectrogramas por saltos: {str(e)}")


@router.get("/list/{directory_type}")
async def list_spectrograms(directory_type: str):
    """
    Lista los espectrogramas generados
    
    - **directory_type**: "normal", "range" o "jumps"
    """
    try:
        if directory_type == "normal":
            directory = SPECTROGRAMS_DIR
        elif directory_type == "range":
            directory = SPECTROGRAMS_RANGE_DIR
        elif directory_type == "jumps":
            directory = SPECTROGRAMS_JUMPS_DIR
        else:
            raise HTTPException(status_code=400, detail="Tipo de directorio inválido")
        
        if not os.path.exists(directory):
            return JSONResponse(content={
                'success': True,
                'spectrograms': [],
                'total': 0
            })
        
        files = [f for f in os.listdir(directory) if f.endswith(('.png', '.jpg', '.jpeg'))]
        
        return JSONResponse(content={
            'success': True,
            'spectrograms': files,
            'total': len(files),
            'directory': directory
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando espectrogramas: {str(e)}")


@router.get("/download/{directory_type}/{filename}")
async def download_spectrogram(directory_type: str, filename: str):
    """
    Descarga un espectrograma específico
    
    - **directory_type**: "normal", "range" o "jumps"
    - **filename**: Nombre del archivo
    """
    try:
        if directory_type == "normal":
            directory = SPECTROGRAMS_DIR
        elif directory_type == "range":
            directory = SPECTROGRAMS_RANGE_DIR
        elif directory_type == "jumps":
            directory = SPECTROGRAMS_JUMPS_DIR
        else:
            raise HTTPException(status_code=400, detail="Tipo de directorio inválido")
        
        file_path = os.path.join(directory, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        return FileResponse(
            file_path,
            media_type="image/png",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error descargando espectrograma: {str(e)}")
