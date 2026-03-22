# Migración de API de Video Completada

## Resumen

Se ha migrado exitosamente la API de análisis de video desde el proyecto original a **ginnet_audio_analyzer_api**. Ahora el proyecto unificado incluye tanto análisis de audio como de video e imágenes.

## Nuevos Endpoints de Video

### 📹 Autenticidad de Video (YOLO)

- **POST** `/api/video/autenticidad`
  - Analiza videos detectando rectángulos negros con YOLOv8
  - Parámetros:
    - `file`: archivo de video
    - `brightness`: nivel de brillo (20, 30 o 40)
    - `id_paquete_proceso_video`: (opcional) ID para actualizar BD
  - Retorna: JSON con detecciones y metadata

- **POST** `/api/video/autenticidad/reporte`
  - Igual que el anterior pero retorna directamente el informe DOCX

### 🎞️ Continuidad de Video

- **POST** `/api/video/continuidad`
  - Analiza continuidad temporal detectando cortes/ediciones
  - Parámetros:
    - `file`: archivo de video
    - `id_paquete_proceso_video`: (opcional) ID para actualizar BD
  - Retorna: JSON con discontinuidades y gráfico en base64

- **POST** `/api/video/continuidad/reporte`
  - Igual que el anterior pero retorna directamente el informe DOCX

### 🖼️ Extracción de Fotogramas

- **POST** `/api/video/extraer-fotogramas`
  - Extrae fotogramas de un video
  - Parámetros:
    - `file`: archivo de video
    - `all_frames`: extraer todos (true/false)
    - `start_frame`: frame inicial
    - `end_frame`: frame final
    - `skip_frames`: salto entre frames
    - `brightness`: ajuste de brillo (-100 a 100)
    - `color`: guardar en color
    - `grayscale`: guardar en escala de grises
  - Retorna: archivo ZIP con los frames

### 📸 Autenticidad de Fotos (ELA)

- **POST** `/api/video/fotos/analizar`
  - Realiza análisis ELA (Error Level Analysis) en imágenes
  - Parámetros:
    - `files`: lista de archivos de imagen
  - Retorna: JSON con imágenes ELA en base64

### ⚫⚪ Conversión a Escala de Grises

- **POST** `/api/video/imagenes/escala-grises`
  - Convierte imágenes a escala de grises
  - Parámetros:
    - `files`: lista de archivos de imagen
  - Retorna: archivo ZIP con imágenes convertidas

- **POST** `/api/video/imagenes/escala-grises/reporte`
  - Igual que el anterior pero retorna informe DOCX

### ℹ️ Estado del Servicio

- **GET** `/api/video/status`
  - Retorna información sobre el estado del servicio de video
  - Incluye disponibilidad de YOLO, torch, dispositivo (CPU/GPU), modelos cargados

## Archivos Migrados

### Services (en `/services/`)
- `video_service.py` - Análisis de autenticidad con YOLO
- `continuity_service.py` - Análisis de continuidad temporal
- `ela_service.py` - Análisis ELA para imágenes
- `frame_extractor.py` - Extracción de fotogramas
- `grayscale_conversion_service.py` - Conversión a escala de grises
- `video_db_service.py` - Actualización de base de datos Oracle

### Utils (en `/utils/`)
- `video_report_generator.py` - Generación de reportes DOCX para análisis de video

### Routes (en `/routes/`)
- `video_routes.py` - Todos los endpoints de video e imágenes

## Configuración Actualizada

### config.py
- Se agregó `MODELS_BRIGHTNESS_DIR` para modelos YOLO de video
- Se actualizó la descripción del API incluyendo funcionalidades de video

### main.py
- Se importó y registró el router `video_routes`

## Estructura de Directorios

```
ginnet_audio_analyzer_api/
├── services/
│   ├── video_service.py (NUEVO)
│   ├── continuity_service.py (NUEVO)
│   ├── ela_service.py (NUEVO)
│   ├── frame_extractor.py (NUEVO)
│   ├── grayscale_conversion_service.py (NUEVO)
│   └── video_db_service.py (NUEVO)
├── utils/
│   └── video_report_generator.py (NUEVO)
├── routes/
│   └── video_routes.py (NUEVO)
├── modelos_brightness/ (NUEVO - vacío, copiar modelos .pt aquí)
│   ├── best_20.pt (por copiar)
│   ├── best_30.pt (por copiar)
│   └── best_40.pt (por copiar)
├── reports/ (informes DOCX se guardan aquí)
└── main.py (ACTUALIZADO)
```

## Pendientes

### ⚠️ IMPORTANTE: Copiar Modelos YOLO

Los modelos YOLO de video NO se copiaron automáticamente. Debes copiarlos manualmente:

**Origen:** 
- `C:\Users\user\Documents\Proyectos\Ginnet\ginnet-audio-video\Video\Ejecutable\ginnet_video_analyzer_01092025\modelos_brightness\`  
  (o la ubicación donde estén los archivos .pt)

**Destino:**
- `C:\Users\user\Documents\ginnet_audio_analyzer_api\modelos_brightness\`

**Archivos a copiar:**
- `best_20.pt` (modelo para brillo 20%)
- `best_30.pt` (modelo para brillo 30%)
- `best_40.pt` (modelo para brillo 40%)

### Variables de Entorno

Asegúrate de tener en `.env`:

```env
# Oracle Database (para actualizaciones de PAQUETE_PROCESO_VIDEO)
ORACLE_USER=tu_usuario
ORACLE_PASSWORD=tu_password
ORACLE_DSN=host:puerto/servicio

# O usar DB_USER, DB_PASSWORD, DB_DSN (según database_service.py)
DB_USER=tu_usuario
DB_PASSWORD=tu_password
DB_DSN=host:puerto/servicio
```

## Prueba de la Migración

1. **Instalar dependencias** (si es necesario):
   ```powershell
   pip install ultralytics torch opencv-python python-docx matplotlib
   ```

2. **Copiar modelos YOLO** (ver sección Pendientes arriba)

3. **Iniciar el servidor**:
   ```powershell
   cd C:\Users\user\Documents\ginnet_audio_analyzer_api
   .\start_server.ps1
   # O manualmente:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Verificar endpoints**:
   - Ver documentación: http://localhost:8000/docs
   - Probar endpoint de estado: http://localhost:8000/api/video/status

5. **Probar análisis de video**:
   - Usar Swagger UI en `/docs` para subir un video de prueba
   - O usar curl/Postman/cliente .NET

## Notas Técnicas

- Los modelos YOLO se cargan bajo demanda y se cachean en memoria
- Los informes DOCX se guardan automáticamente en `/reports/`
- Los archivos temporales se limpian después de cada request
- Soporta GPU (CUDA) si está disponible, de lo contrario usa CPU
- Compatible con las actualizaciones de base de datos Oracle existentes

## Endpoints de Audio (ya existentes)

El proyecto mantiene todos los endpoints de audio:
- `/api/spectrograms/*` - Generación de espectrogramas
- `/api/transcription/*` - Transcripción de audio
- `/api/analysis/*` - Análisis YOLO de espectrogramas
- `/api/reports/*` - Generación de reportes de audio
- `/api/pipeline/*` - Pipelines completos de análisis

## Soporte

Para más información, consulta la documentación interactiva en `/docs` después de iniciar el servidor.
