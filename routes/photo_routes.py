"""
Rutas/Endpoints para análisis de fotos e imágenes
"""
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import os
import io
import shutil
import base64
import zipfile
from pathlib import Path

router = APIRouter(prefix="/api/photo", tags=["Photo Analysis"])


# ─────────────────────────────────────────────────────────────────────────────
# AUTENTICIDAD DE FOTOS (ELA)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/analizar")
async def analizar_fotos(
    file_path: str = Form(...),
    paquete_id: Optional[int] = Form(None, description="ID del paquete para actualizar en base de datos")
):
    """
    Realiza análisis ELA sobre las imágenes encontradas en la ruta especificada.
    La ruta puede ser un archivo individual o un directorio con múltiples imágenes.
    Crea carpeta ELA_Analysis/Resultados para almacenar los resultados localmente.
    Retorna JSON con información del proceso y rutas de los archivos guardados.
    
    - **file_path**: Ruta completa del archivo o directorio con imágenes
    - **paquete_id**: ID del paquete para actualizar en base de datos (opcional)
    """
    from services.ela_service import analyze_image_bytes
    
    path = Path(file_path)
    
    # Validar que la ruta existe
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"La ruta especificada no existe: {file_path}"
        )
    
    # Recopilar archivos a analizar
    image_files = []
    supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    if path.is_file():
        # Es un archivo individual
        if path.suffix.lower() in supported_extensions:
            image_files.append(path)
            file_dir = path.parent
        else:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo no tiene una extensión de imagen soportada: {path.suffix}"
            )
    elif path.is_dir():
        # Es un directorio - buscar todas las imágenes
        file_dir = path
        for ext in supported_extensions:
            image_files.extend(path.glob(f'*{ext}'))
            image_files.extend(path.glob(f'*{ext.upper()}'))
    else:
        raise HTTPException(
            status_code=400,
            detail="La ruta no es un archivo ni un directorio válido"
        )
    
    if not image_files:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron imágenes en la ruta especificada"
        )
    
    # Crear estructura de carpetas ELA_Analysis/Resultados
    ela_dir = file_dir / "ELA_Analysis"
    if ela_dir.exists():
        shutil.rmtree(ela_dir)
    ela_dir.mkdir(exist_ok=True)
    
    resultados_dir = ela_dir / "Resultados"
    resultados_dir.mkdir(exist_ok=True)
    
    # Analizar cada imagen y guardar resultados
    processed_files = []
    error_count = 0
    
    for image_path in image_files:
        try:
            with open(image_path, 'rb') as f:
                content = f.read()
            result = analyze_image_bytes(content)
            
            # Guardar imagen ELA en la carpeta de resultados
            if 'ela_image_base64' in result:
                ela_filename = f"ELA_{image_path.stem}.png"
                ela_path = resultados_dir / ela_filename
                
                # Decodificar y guardar la imagen ELA
                ela_img_data = base64.b64decode(result['ela_image_base64'])
                with open(ela_path, 'wb') as ela_f:
                    ela_f.write(ela_img_data)
                
                processed_files.append(ela_path)
        except Exception as e:
            print(f"Error procesando {image_path.name}: {e}")
            error_count += 1
    
    # Crear archivo ZIP con todas las imágenes ELA
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for ela_file in processed_files:
            zip_file.write(ela_file, ela_file.name)
    
    zip_bytes = zip_buffer.getvalue()
    
    # Guardar el ZIP en la carpeta ELA_Analysis
    zip_filename = "analisis_ela.zip"
    zip_path = ela_dir / zip_filename
    with open(zip_path, 'wb') as zip_f:
        zip_f.write(zip_bytes)
    
    # Actualizar base de datos con la ruta del ZIP
    db_update_result = None
    if paquete_id is not None:
        from services.database_service import DatabaseService
        # Convertir todas las barras \\ a /
        zip_path_windows = str(zip_path).replace('\\', '/')
        print(f"Actualizando base de datos con ruta del ZIP ELA: {zip_path_windows}, paquete_id: {paquete_id}")
        db_update_result = DatabaseService.update_paquete_proceso_informe_3(
            zip_path_windows, paquete_id
        )
    
    response = {
        "success": True,
        "images_processed": len(processed_files),
        "images_failed": error_count,
        "message": f"Análisis ELA completado. {len(processed_files)} imágenes procesadas exitosamente."
    }
    
    if db_update_result:
        response["database_update"] = "success"

    return JSONResponse(content=response)


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACCIÓN DE FOTOGRAMAS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/extraer-fotogramas")
async def extraer_fotogramas(
    file_path: str = Form(...),
    all_frames: bool = Form(True, description="Extraer todos los fotogramas"),
    start_frame: int = Form(1, description="Frame inicial (1-based)"),
    end_frame: int = Form(-1, description="Frame final (-1 = último)"),
    skip_frames: int = Form(1, description="Salto entre frames"),
    brightness: int = Form(20, description="Ajuste de brillo (-100 a 100)"),
    color: bool = Form(True, description="Guardar frames en color"),
    grayscale: bool = Form(False, description="Guardar frames en escala de grises"),
    paquete_id: Optional[int] = Form(None, description="ID del paquete para actualizar en base de datos")
):
    """
    Extrae fotogramas de un video según los parámetros indicados.
    Crea carpeta Fotogramas_Extraidos/ y guarda el ZIP localmente.
    Retorna JSON con información del proceso y rutas de los archivos guardados.
    
    - **file_path**: Ruta completa del archivo de video
    - **paquete_id**: ID del paquete para actualizar en base de datos (opcional)
    """
    if not color and not grayscale:
        raise HTTPException(
            status_code=400,
            detail="Debe seleccionar al menos una opción: color=true o grayscale=true"
        )
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"El archivo no existe: {file_path}")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"La ruta no corresponde a un archivo: {file_path}")

    from services.frame_extractor import extract_frames

    try:
        config = {
            'all_frames': all_frames,
            'start_frame': start_frame,
            'end_frame': end_frame if end_frame > 0 else None,
            'skip_frames': skip_frames,
            'brightness_adjustment': brightness,
            'color_frames': color,
            'grayscale_frames': grayscale
        }

        result = extract_frames(file_path, config)
        zip_bytes = result.pop('zip_bytes')
        
        # Obtener rutas guardadas
        zip_saved_path = result.get('zip_path', None)
        fotogramas_dir = result.get('fotogramas_directory', None)
        
        # Actualizar base de datos con la ruta del ZIP
        db_update_result = None
        if paquete_id is not None and zip_saved_path:
            from services.database_service import DatabaseService
            # Convertir todas las barras \\ a /
            zip_path_windows = zip_saved_path.replace('\\', '/')
            print(f"Actualizando base de datos con ruta del ZIP de fotogramas: {zip_path_windows}, paquete_id: {paquete_id}")
            db_update_result = DatabaseService.update_paquete_proceso_informe_3(
                zip_path_windows, paquete_id
            )

        response = {
            "success": True,
            "frames_extracted": result['frames_extracted'],
            "brightness_applied": result['brightness_applied'],
            "message": f"Extracción completada. {result['frames_extracted']} fotogramas extraídos exitosamente."
        }
        
        if db_update_result:
            response["database_update"] = "success"

        return JSONResponse(content=response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSIÓN A ESCALA DE GRISES
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/escala-grises")
async def convertir_escala_grises(
    file_path: str = Form(...),
    paquete_id: Optional[int] = Form(None, description="ID del paquete para actualizar en base de datos")
):
    """
    Convierte imágenes a escala de grises y genera automáticamente el informe PDF.
    La ruta puede ser un archivo individual o un directorio con múltiples imágenes.
    Crea carpeta Escala_Grises/Convertidas/ para el ZIP y Escala_Grises/Reporte/ para el informe PDF.
    Guarda todos los archivos localmente y retorna JSON con información del proceso.
    
    - **file_path**: Ruta completa del archivo o directorio con imágenes
    - **paquete_id**: ID del paquete para actualizar en base de datos (opcional)
    """
    from services.grayscale_conversion_service import batch_convert_to_grayscale
    from utils.video_report_generator import generate_grayscale_report_pdf
    
    path = Path(file_path)
    
    # Validar que la ruta existe
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"La ruta especificada no existe: {file_path}"
        )
    
    # Recopilar archivos a procesar
    image_files = []
    supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    if path.is_file():
        # Es un archivo individual
        if path.suffix.lower() in supported_extensions:
            image_files.append(path)
            file_dir = path.parent
        else:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo no tiene una extensión de imagen soportada: {path.suffix}"
            )
    elif path.is_dir():
        # Es un directorio - buscar todas las imágenes
        file_dir = path
        for ext in supported_extensions:
            image_files.extend(path.glob(f'*{ext}'))
            image_files.extend(path.glob(f'*{ext.upper()}'))
    else:
        raise HTTPException(
            status_code=400,
            detail="La ruta no es un archivo ni un directorio válido"
        )
    
    if not image_files:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron imágenes en la ruta especificada"
        )
    
    # Crear estructura de carpetas Escala_Grises/Convertidas y Escala_Grises/Reporte
    escala_dir = file_dir / "Escala_Grises"
    if escala_dir.exists():
        shutil.rmtree(escala_dir)
    escala_dir.mkdir(exist_ok=True)
    
    convertidas_dir = escala_dir / "Convertidas"
    convertidas_dir.mkdir(exist_ok=True)
    
    reporte_dir = escala_dir / "Reporte"
    reporte_dir.mkdir(exist_ok=True)
    
    # Leer todas las imágenes
    images = []
    for image_path in image_files:
        try:
            with open(image_path, 'rb') as f:
                images.append({
                    'filename': image_path.name,
                    'bytes': f.read()
                })
        except Exception as e:
            print(f"Error leyendo {image_path}: {e}")

    result = batch_convert_to_grayscale(images)
    zip_bytes = result.get('zip_bytes')
    
    # Guardar el ZIP en la carpeta Convertidas
    zip_filename = "imagenes_escala_grises.zip"
    zip_path = convertidas_dir / zip_filename
    with open(zip_path, 'wb') as zip_f:
        zip_f.write(zip_bytes)
    
    # Generar y guardar el informe PDF en la carpeta Reporte
    informe_filename = "Informe_Escala_Grises.pdf"
    informe_path = reporte_dir / informe_filename
    
    try:
        # Crear una copia del resultado sin zip_bytes para el reporte
        result_for_report = result.copy()
        result_for_report.pop('zip_bytes', None)
        
        pdf_bytes = generate_grayscale_report_pdf(result_for_report)
        with open(informe_path, 'wb') as informe_f:
            informe_f.write(pdf_bytes)
        
        print(f"Informe PDF generado exitosamente: {informe_path}")
    except Exception as rep_err:
        print(f"ADVERTENCIA: No se pudo generar el informe PDF: {rep_err}")
        informe_path = None
    
    # Actualizar base de datos con las rutas
    db_update_informe = None
    db_update_zip = None
    
    if paquete_id is not None:
        from services.database_service import DatabaseService
        
        # Actualizar INFORME_1 con la ruta del PDF
        if informe_path:
            informe_path_windows = str(informe_path).replace('\\', '/')
            print(f"Actualizando base de datos con ruta del informe PDF: {informe_path_windows}, paquete_id: {paquete_id}")
            db_update_informe = DatabaseService.update_paquete_proceso_informe_1(
                informe_path_windows, paquete_id
            )
        
        # Actualizar INFORME_3 con la ruta del ZIP
        zip_path_windows = str(zip_path).replace('\\', '/')
        print(f"Actualizando base de datos con ruta del ZIP: {zip_path_windows}, paquete_id: {paquete_id}")
        db_update_zip = DatabaseService.update_paquete_proceso_informe_3(
            zip_path_windows, paquete_id
        )

    response = {
        "success": True,
        "converted_count": result['converted_count'],
        "error_count": result['error_count'],
        "message": f"Conversión completada. {result['converted_count']} imágenes convertidas a escala de grises."
    }
    
    if informe_path:
        response["report_generated"] = True
    
    if db_update_informe or db_update_zip:
        response["database_update"] = "success"

    return JSONResponse(content=response)


@router.get("/status")
async def photo_status():
    """
    Retorna el estado del servicio de análisis de fotos.
    """
    return {
        "service": "Photo Analysis API",
        "ela_available": True,
        "grayscale_available": True,
        "frame_extraction_available": True
    }
