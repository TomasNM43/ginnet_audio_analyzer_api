# Ginnet Audio Analyzer API

API REST para análisis de archivos de audio mediante generación de espectrogramas, transcripción y detección de anomalías con YOLO.

## 🚀 Características

- **Generación de Espectrogramas**: Convierte archivos de audio en espectrogramas visuales
- **Transcripción de Audio**: Convierte voz a texto usando múltiples métodos de reconocimiento
- **Análisis YOLO**: Detecta cortes y anomalías en espectrogramas usando modelos de deep learning
- **Reportes Consolidados**: Genera reportes en formato Word y TXT con análisis detallados

## 📋 Requisitos

- Python 3.8 o superior
- FFmpeg (para procesamiento de audio)
- Modelos YOLO entrenados (copiar a la carpeta `models/`)

## 🔧 Instalación

1. Crear un entorno virtual:
```bash
python -m venv venv
```

2. Activar el entorno virtual:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Copiar modelos YOLO:
Copiar los archivos `best.pt` a las carpetas correspondientes:
- `models/normal/best.pt`
- `models/grayscale/best.pt`

## ▶️ Ejecución

Iniciar el servidor:
```bash
python main.py
```

O usando uvicorn directamente:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

El servidor estará disponible en:
- API: http://localhost:8000
- Documentación interactiva (Swagger): http://localhost:8000/docs
- Documentación alternativa (ReDoc): http://localhost:8000/redoc

## 📚 Endpoints Principales

### Espectrogramas

- `POST /api/spectrograms/generate` - Generar espectrogramas para archivos de audio
- `POST /api/spectrograms/generate-by-range` - Generar espectrogramas en un rango de tiempo
- `POST /api/spectrograms/generate-by-jumps` - Generar espectrogramas con saltos de tiempo
- `GET /api/spectrograms/list/{directory_type}` - Listar espectrogramas generados
- `GET /api/spectrograms/download/{directory_type}/{filename}` - Descargar un espectrograma

### Transcripción

- `POST /api/transcription/transcribe` - Transcribir múltiples archivos de audio
- `POST /api/transcription/transcribe-single` - Transcribir un solo archivo
- `POST /api/transcription/generate-report` - Generar reporte de transcripción
- `GET /api/transcription/download-report/{report_name}` - Descargar reporte

### Análisis YOLO

- `POST /api/analysis/run-yolo` - Ejecutar análisis YOLO sobre espectrogramas
- `POST /api/analysis/run-yolo-custom` - Análisis YOLO con configuración personalizada
- `GET /api/analysis/results` - Obtener resultados del análisis

### Reportes

- `POST /api/reports/generate-consolidated` - Generar reporte consolidado (Word)
- `POST /api/reports/generate-chart` - Generar gráfico resumen
- `GET /api/reports/list` - Listar reportes generados
- `GET /api/reports/download/{report_name}` - Descargar un reporte
- `DELETE /api/reports/delete/{report_name}` - Eliminar un reporte

## 🔌 Integración con .NET

### Ejemplo en C# usando HttpClient

```csharp
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;

public class GinnetAudioAnalyzerClient
{
    private readonly HttpClient _httpClient;
    private const string BaseUrl = "http://localhost:8000";

    public GinnetAudioAnalyzerClient()
    {
        _httpClient = new HttpClient();
        _httpClient.BaseAddress = new Uri(BaseUrl);
    }

    // Generar espectrogramas
    public async Task<string> GenerateSpectrogramsAsync(string audioFilePath, int segmentLength = 3)
    {
        using var form = new MultipartFormDataContent();
        using var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync(audioFilePath));
        fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
        form.Add(fileContent, "files", Path.GetFileName(audioFilePath));
        form.Add(new StringContent(segmentLength.ToString()), "segment_length");

        var response = await _httpClient.PostAsync("/api/spectrograms/generate", form);
        return await response.Content.ReadAsStringAsync();
    }

    // Transcribir audio
    public async Task<string> TranscribeAudioAsync(string audioFilePath, string language = "es-ES")
    {
        using var form = new MultipartFormDataContent();
        using var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync(audioFilePath));
        fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
        form.Add(fileContent, "file", Path.GetFileName(audioFilePath));
        form.Add(new StringContent(language), "language");

        var response = await _httpClient.PostAsync("/api/transcription/transcribe-single", form);
        return await response.Content.ReadAsStringAsync();
    }

    // Ejecutar análisis YOLO
    public async Task<string> RunYoloAnalysisAsync(string directoryType = "normal", int segmentLength = 3)
    {
        using var form = new MultipartFormDataContent();
        form.Add(new StringContent(directoryType), "input_directory_type");
        form.Add(new StringContent(segmentLength.ToString()), "segment_length");

        var response = await _httpClient.PostAsync("/api/analysis/run-yolo", form);
        return await response.Content.ReadAsStringAsync();
    }
}
```

### Ejemplo de uso

```csharp
var client = new GinnetAudioAnalyzerClient();

// 1. Generar espectrogramas
var spectrogramResult = await client.GenerateSpectrogramsAsync("audio.wav", segmentLength: 3);
Console.WriteLine(spectrogramResult);

// 2. Ejecutar análisis YOLO
var analysisResult = await client.RunYoloAnalysisAsync("normal", 3);
Console.WriteLine(analysisResult);

// 3. Transcribir audio
var transcriptionResult = await client.TranscribeAudioAsync("audio.wav", "es-ES");
Console.WriteLine(transcriptionResult);
```

## 📁 Estructura del Proyecto

```
ginnet_audio_analyzer_api/
├── main.py                 # Aplicación principal FastAPI
├── config.py              # Configuración
├── requirements.txt       # Dependencias
├── README.md             # Este archivo
├── services/             # Lógica de negocio
│   ├── __init__.py
│   ├── spectrogram_service.py
│   ├── transcription_service.py
│   ├── yolo_service.py
│   └── report_service.py
├── routes/               # Endpoints de la API
│   ├── __init__.py
│   ├── spectrogram_routes.py
│   ├── transcription_routes.py
│   ├── analysis_routes.py
│   └── report_routes.py
├── models/               # Modelos YOLO
│   ├── normal/
│   │   └── best.pt
│   └── grayscale/
│       └── best.pt
├── temp_files/           # Archivos temporales
├── uploads/              # Archivos subidos
├── spectrograms/         # Espectrogramas generados
├── reports/              # Reportes generados
└── resultados_normal/    # Resultados del análisis YOLO
```

## 🌐 CORS y Seguridad

La API está configurada para permitir peticiones CORS desde cualquier origen en modo desarrollo. 
Para producción, modifique la configuración en `config.py`:

```python
CORS_ORIGINS = [
    "https://tu-dominio.com",
    "https://www.tu-dominio.com"
]
```

## 🐛 Solución de Problemas

### Error: "Modelo YOLO no encontrado"
Asegúrese de copiar los archivos `best.pt` a las carpetas `models/normal/` y `models/grayscale/`

### Error: "FFmpeg no encontrado"
Instale FFmpeg:
- Windows: Descargar de https://ffmpeg.org/download.html
- Linux: `sudo apt-get install ffmpeg`
- Mac: `brew install ffmpeg`

### Error de transcripción
La transcripción requiere conexión a internet para usar Google Speech Recognition API.

## 📝 Licencia

Este proyecto es privado y confidencial.

## 👥 Contacto

Para más información, contacte al equipo de desarrollo.
