# Documentación de Endpoints - Ginnet Audio Analyzer API

## Base URL
```
http://localhost:8000
```

## Endpoints Disponibles

### 1. ESPECTROGRAMAS

#### 1.1 Generar Espectrogramas
Genera espectrogramas para uno o más archivos de audio.

**Endpoint:** `POST /api/spectrograms/generate`

**Parámetros:**
- `files` (form-data, required): Archivo(s) de audio (WAV, MP3, FLAC, M4A)
- `segment_length` (form-data, optional): Duración de cada segmento en segundos (default: 3)

**Ejemplo C#:**
```csharp
using var form = new MultipartFormDataContent();
var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync("audio.wav"));
form.Add(fileContent, "files", "audio.wav");
form.Add(new StringContent("3"), "segment_length");

var response = await httpClient.PostAsync("/api/spectrograms/generate", form);
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Espectrogramas generados para 1 archivos",
  "total_files": 1,
  "segment_length": 3,
  "results": [
    {
      "filename": "audio.wav",
      "file_index": 1,
      "total_spectrograms": 10,
      "duration": 30.5,
      "spectrograms": [...]
    }
  ]
}
```

---

#### 1.2 Generar Espectrogramas por Rango
Genera espectrogramas en un rango de tiempo específico.

**Endpoint:** `POST /api/spectrograms/generate-by-range`

**Parámetros:**
- `files` (form-data, required): Archivo(s) de audio
- `start_time` (form-data, required): Tiempo inicial en segundos
- `end_time` (form-data, required): Tiempo final en segundos
- `segment_length` (form-data, optional): Duración de cada segmento (default: 3)
- `mode` (form-data, optional): "complete" o "combined" (default: "complete")
- `time_jump` (form-data, optional): Salto de tiempo para modo combinado (default: 3)

**Ejemplo C#:**
```csharp
form.Add(new StringContent("10"), "start_time");
form.Add(new StringContent("30"), "end_time");
form.Add(new StringContent("complete"), "mode");
```

---

#### 1.3 Generar Espectrogramas por Saltos
Genera espectrogramas con saltos de tiempo específicos.

**Endpoint:** `POST /api/spectrograms/generate-by-jumps`

**Parámetros:**
- `files` (form-data, required): Archivo(s) de audio
- `time_jump` (form-data, optional): Salto de tiempo en segundos (default: 3)
- `segment_length` (form-data, optional): Duración de cada segmento (default: 3)

---

#### 1.4 Listar Espectrogramas
Lista los espectrogramas generados.

**Endpoint:** `GET /api/spectrograms/list/{directory_type}`

**Parámetros URL:**
- `directory_type`: "normal", "range" o "jumps"

**Ejemplo C#:**
```csharp
var response = await httpClient.GetAsync("/api/spectrograms/list/normal");
```

**Respuesta:**
```json
{
  "success": true,
  "spectrograms": ["audio_1_spectrogram_0_3.png", "audio_1_spectrogram_3_6.png"],
  "total": 2,
  "directory": "path/to/spectrograms"
}
```

---

#### 1.5 Descargar Espectrograma
Descarga un espectrograma específico.

**Endpoint:** `GET /api/spectrograms/download/{directory_type}/{filename}`

**Ejemplo C#:**
```csharp
var bytes = await httpClient.GetByteArrayAsync(
    "/api/spectrograms/download/normal/audio_1_spectrogram_0_3.png");
await File.WriteAllBytesAsync("spectrogram.png", bytes);
```

---

### 2. TRANSCRIPCIÓN

#### 2.1 Transcribir Múltiples Archivos
Transcribe uno o más archivos de audio.

**Endpoint:** `POST /api/transcription/transcribe`

**Parámetros:**
- `files` (form-data, required): Archivo(s) de audio
- `language` (form-data, optional): Código de idioma (default: "es-ES")

**Idiomas soportados:**
- `es-ES`: Español (España)
- `es-MX`: Español (México)
- `en-US`: Inglés (Estados Unidos)
- `fr-FR`: Francés
- `it-IT`: Italiano
- `pt-PT`: Portugués
- `de-DE`: Alemán

**Ejemplo C#:**
```csharp
form.Add(fileContent, "files", "audio.wav");
form.Add(new StringContent("es-ES"), "language");
var response = await httpClient.PostAsync("/api/transcription/transcribe", form);
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Transcripción completada para 1 archivos",
  "total_files": 1,
  "language": "es-ES",
  "transcriptions": [
    {
      "file": "audio.wav",
      "path": "/path/to/audio.wav",
      "duration": "0:30",
      "transcription": "texto transcrito...",
      "method": "Google Speech Recognition",
      "index": 1
    }
  ]
}
```

---

#### 2.2 Transcribir Un Solo Archivo
Transcribe un solo archivo de audio.

**Endpoint:** `POST /api/transcription/transcribe-single`

**Parámetros:**
- `file` (form-data, required): Archivo de audio
- `language` (form-data, optional): Código de idioma (default: "es-ES")
- `max_duration` (form-data, optional): Duración máxima en segundos (default: 300)

---

#### 2.3 Generar Reporte de Transcripción
Transcribe archivos y genera un reporte en formato TXT.

**Endpoint:** `POST /api/transcription/generate-report`

**Parámetros:**
- `files` (form-data, required): Archivo(s) de audio
- `language` (form-data, optional): Código de idioma (default: "es-ES")

**Respuesta:**
```json
{
  "success": true,
  "message": "Reporte de transcripción generado",
  "transcription_result": {...},
  "report_info": {
    "report_name": "Transcripcion_20260306_153045.txt",
    "report_path": "/path/to/report.txt",
    "total_files": 1,
    "timestamp": "20260306_153045"
  }
}
```

---

#### 2.4 Descargar Reporte de Transcripción
Descarga un reporte de transcripción.

**Endpoint:** `GET /api/transcription/download-report/{report_name}`

**Ejemplo C#:**
```csharp
var bytes = await httpClient.GetByteArrayAsync(
    "/api/transcription/download-report/Transcripcion_20260306_153045.txt");
await File.WriteAllBytesAsync("transcripcion.txt", bytes);
```

---

### 3. ANÁLISIS YOLO

#### 3.1 Ejecutar Análisis YOLO
Ejecuta análisis YOLO sobre espectrogramas generados.

**Endpoint:** `POST /api/analysis/run-yolo`

**Parámetros:**
- `input_directory_type` (form-data, optional): "normal", "range" o "jumps" (default: "normal")
- `segment_length` (form-data, optional): Duración del segmento en segundos para seleccionar modelo (default: 3)

**Ejemplo C#:**
```csharp
using var form = new MultipartFormDataContent();
form.Add(new StringContent("normal"), "input_directory_type");
form.Add(new StringContent("3"), "segment_length");

var response = await httpClient.PostAsync("/api/analysis/run-yolo", form);
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Análisis YOLO completado",
  "detections_by_file": {
    "audio_1_filename": {
      "segments": [...],
      "detections": [...],
      "total_segments": 10,
      "total_detections": 3
    }
  },
  "total_files_processed": 10,
  "total_detections": 3,
  "model_used": "best.pt"
}
```

---

#### 3.2 Ejecutar Análisis YOLO Personalizado
Ejecuta análisis YOLO con configuración personalizada.

**Endpoint:** `POST /api/analysis/run-yolo-custom`

**Parámetros:**
- `input_directory` (form-data, required): Ruta al directorio con espectrogramas
- `model_type` (form-data, optional): "normal" o "grayscale" (default: "normal")

---

#### 3.3 Obtener Resultados del Análisis
Obtiene el listado de archivos con detecciones.

**Endpoint:** `GET /api/analysis/results`

**Ejemplo C#:**
```csharp
var response = await httpClient.GetAsync("/api/analysis/results");
```

**Respuesta:**
```json
{
  "success": true,
  "detections": ["audio_1_spectrogram_0_3.png", "audio_1_spectrogram_6_9.png"],
  "total": 2,
  "directory": "/path/to/results"
}
```

---

### 4. REPORTES

#### 4.1 Generar Reporte Consolidado
Genera un reporte consolidado en formato Word.

**Endpoint:** `POST /api/reports/generate-consolidated`

**Parámetros:**
- `detections_data` (form-data, required): JSON con datos de detecciones
- `audio_files` (form-data, required): Lista de nombres de archivos procesados

**Ejemplo C#:**
```csharp
var detectionsJson = JsonSerializer.Serialize(detections);
form.Add(new StringContent(detectionsJson), "detections_data");
form.Add(new StringContent(JsonSerializer.Serialize(audioFiles)), "audio_files");

var response = await httpClient.PostAsync("/api/reports/generate-consolidated", form);
```

---

#### 4.2 Generar Gráfico Resumen
Genera un gráfico resumen de detecciones.

**Endpoint:** `POST /api/reports/generate-chart`

**Parámetros:**
- `detections_data` (form-data, required): JSON con datos de detecciones

---

#### 4.3 Listar Reportes
Lista todos los reportes generados.

**Endpoint:** `GET /api/reports/list`

**Respuesta:**
```json
{
  "success": true,
  "reports": ["Reporte_20260306_153045.docx", "Transcripcion_20260306_153045.txt"],
  "reports_by_type": {
    "word": ["Reporte_20260306_153045.docx"],
    "text": ["Transcripcion_20260306_153045.txt"],
    "images": ["summary_chart.png"]
  },
  "total": 3
}
```

---

#### 4.4 Descargar Reporte
Descarga un reporte específico.

**Endpoint:** `GET /api/reports/download/{report_name}`

**Ejemplo C#:**
```csharp
var bytes = await httpClient.GetByteArrayAsync(
    "/api/reports/download/Reporte_20260306_153045.docx");
await File.WriteAllBytesAsync("reporte.docx", bytes);
```

---

#### 4.5 Eliminar Reporte
Elimina un reporte específico.

**Endpoint:** `DELETE /api/reports/delete/{report_name}`

**Ejemplo C#:**
```csharp
var response = await httpClient.DeleteAsync(
    "/api/reports/delete/Reporte_20260306_153045.docx");
```

---

### 5. INFORMACIÓN GENERAL

#### 5.1 Endpoint Raíz
Información básica de la API.

**Endpoint:** `GET /`

**Respuesta:**
```json
{
  "message": "Ginnet Audio Analyzer API",
  "version": "1.0.0",
  "status": "online",
  "docs": "/docs",
  "redoc": "/redoc",
  "endpoints": {
    "spectrograms": "/api/spectrograms",
    "transcription": "/api/transcription",
    "analysis": "/api/analysis",
    "reports": "/api/reports"
  }
}
```

---

#### 5.2 Health Check
Verificación del estado del servicio.

**Endpoint:** `GET /health`

**Respuesta:**
```json
{
  "status": "healthy",
  "service": "Ginnet Audio Analyzer API",
  "version": "1.0.0"
}
```

---

#### 5.3 Información de la API
Información detallada sobre la API.

**Endpoint:** `GET /api/info`

---

## Flujo de Trabajo Recomendado

1. **Subir archivos de audio y generar espectrogramas**
   ```
   POST /api/spectrograms/generate
   ```

2. **Ejecutar análisis YOLO**
   ```
   POST /api/analysis/run-yolo
   ```

3. **Generar reporte consolidado**
   ```
   POST /api/reports/generate-consolidated
   ```

4. **Descargar reporte**
   ```
   GET /api/reports/download/{report_name}
   ```

5. **Opcionalmente, transcribir archivos**
   ```
   POST /api/transcription/transcribe
   ```

---

## Documentación Interactiva

Acceda a la documentación interactiva Swagger UI en:
```
http://localhost:8000/docs
```

O a la documentación ReDoc en:
```
http://localhost:8000/redoc
```

---

## Códigos de Respuesta HTTP

- `200 OK`: Solicitud exitosa
- `400 Bad Request`: Parámetros inválidos
- `404 Not Found`: Recurso no encontrado
- `500 Internal Server Error`: Error en el servidor

---

## Tipos de Contenido

- **Subida de archivos:** `multipart/form-data`
- **Respuestas JSON:** `application/json`
- **Descarga de archivos:** 
  - Imágenes: `image/png`
  - Word: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - Texto: `text/plain`
