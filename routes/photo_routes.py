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
    Realiza análisis de fotos usando filtro Sobel color y detección de manchas con modelos de brillo.
    Proceso:
    1. Aplica filtro Sobel por canal BGR (conservando color), igual que ejemplo.png
    2. Ejecuta los modelos de modelos_brightness (best_20, best_30, best_40) para detectar manchas
    3. Guarda imágenes con las detecciones marcadas

    La ruta puede ser un archivo individual o un directorio con múltiples imágenes.
    Crea carpeta Analisis_Fotos/Resultados para almacenar los resultados localmente.
    Retorna JSON con información del proceso y rutas de los archivos guardados.

    - **file_path**: Ruta completa del archivo o directorio con imágenes
    - **paquete_id**: ID del paquete para actualizar en base de datos (opcional)
    """
    import cv2
    import numpy as np
    from ultralytics import YOLO
    from services.grayscale_conversion_service import apply_sobel_color_filter
    from config import MODELS_BRIGHTNESS_DIR

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
        if path.suffix.lower() in supported_extensions:
            image_files.append(path)
            file_dir = path.parent
        else:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo no tiene una extensión de imagen soportada: {path.suffix}"
            )
    elif path.is_dir():
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

    # Cargar los modelos de brightness con su nivel de brillo correspondiente
    # Cada modelo fue entrenado con imágenes a las que se aplicó ese nivel de brillo
    # antes del filtro Sobel, igual que en el pipeline de extracción de fotogramas
    model_configs = [
        ('best_20.pt', 20),
        ('best_30.pt', 30),
        ('best_40.pt', 40),
    ]
    loaded_models = []
    for mf, brightness_val in model_configs:
        mp = os.path.join(MODELS_BRIGHTNESS_DIR, mf)
        if os.path.exists(mp):
            loaded_models.append((YOLO(mp), brightness_val))
            print(f"Modelo cargado: {mf} (brillo +{brightness_val})")

    if not loaded_models:
        raise HTTPException(
            status_code=500,
            detail="No se encontraron modelos en la carpeta modelos_brightness"
        )

    # Crear estructura de carpetas Analisis_Fotos/Resultados
    analysis_dir = file_dir / "Analisis_Fotos"
    if analysis_dir.exists():
        shutil.rmtree(analysis_dir)
    analysis_dir.mkdir(exist_ok=True)

    resultados_dir = analysis_dir / "Resultados"
    resultados_dir.mkdir(exist_ok=True)

    # Analizar cada imagen
    processed_files = []
    error_count = 0
    total_detections = 0

    for image_path in image_files:
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                print(f"No se pudo leer la imagen: {image_path.name}")
                error_count += 1
                continue

            # Original oscurecido para el blend (preserva colores como las manchas azules)
            darkened_original = np.clip(img.astype(np.float32) * 0.3, 0, 255).astype(np.uint8)

            # Imagen base para dibujar: brillo +30 → Sobel → blend con original oscurecido
            base_brightened = np.clip(img.astype(np.float32) + 30, 0, 255).astype(np.uint8)
            base_sobel = apply_sobel_color_filter(base_brightened)
            output_img = cv2.addWeighted(base_sobel, 0.8, darkened_original, 0.2, 0)

            # Para cada modelo: brillo específico → Sobel → blend con original oscurecido
            # El blend conserva las manchas de color (azules) visibles para la detección
            file_detections = 0

            for model, brightness_val in loaded_models:
                brightened = np.clip(img.astype(np.float32) + brightness_val, 0, 255).astype(np.uint8)
                sobel = apply_sobel_color_filter(brightened)
                filtered = cv2.addWeighted(sobel, 0.8, darkened_original, 0.2, 0)

                results = model(filtered)
                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        label = f"{result.names[cls]} {conf:.2f}"
                        cv2.rectangle(output_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(output_img, label, (x1, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                        file_detections += 1

            total_detections += file_detections

            # Guardar imagen resultado en la carpeta de resultados
            out_filename = f"Analisis_{image_path.stem}.png"
            out_path = resultados_dir / out_filename
            cv2.imwrite(str(out_path), output_img)
            processed_files.append(out_path)

        except Exception as e:
            import traceback
            print(f"Error procesando {image_path.name}: {e}")
            traceback.print_exc()
            error_count += 1

    # Crear archivo ZIP con todas las imágenes analizadas
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for result_file in processed_files:
            zip_file.write(result_file, result_file.name)

    zip_bytes = zip_buffer.getvalue()

    # Guardar el ZIP en la carpeta Analisis_Fotos
    zip_filename = "analisis_fotos.zip"
    zip_path = analysis_dir / zip_filename
    with open(zip_path, 'wb') as zip_f:
        zip_f.write(zip_bytes)

    # Actualizar base de datos con la ruta del ZIP
    db_update_result = None
    if paquete_id is not None:
        from services.database_service import DatabaseService
        zip_path_windows = str(zip_path).replace('\\', '/')
        print(f"Actualizando base de datos con ruta del ZIP: {zip_path_windows}, paquete_id: {paquete_id}")
        db_update_result = DatabaseService.update_paquete_proceso_informe_3(
            zip_path_windows, paquete_id
        )

    response = {
        "success": True,
        "images_processed": len(processed_files),
        "images_failed": error_count,
        "total_detections": total_detections,
        "message": f"Análisis completado. {len(processed_files)} imágenes procesadas, {total_detections} detecciones encontradas."
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
    grayscale: bool = Form(False, description="Guardar frames en escala de grises con filtro Sobel"),
    paquete_id: Optional[int] = Form(None, description="ID del paquete para actualizar en base de datos")
):
    """
    Extrae fotogramas de un video según los parámetros indicados.
    Si se selecciona grayscale=True, los fotogramas se convierten a escala de grises
    y se les aplica un filtro Sobel para detección de bordes.
    
    Crea carpeta Fotogramas_Extraidos/ y guarda el ZIP localmente.
    Retorna JSON con información del proceso y rutas de los archivos guardados.
    
    - **file_path**: Ruta completa del archivo de video
    - **grayscale**: Si es True, aplica conversión a escala de grises + filtro Sobel
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
    Convierte imágenes a escala de grises, aplica filtro Sobel para detección de bordes,
    y genera automáticamente el informe PDF.
    
    Proceso:
    1. Convierte las imágenes a escala de grises
    2. Aplica filtro Sobel (magnitud de gradiente) para detección de bordes
    3. Genera informe PDF con los resultados
    
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
