# GINNET AUDIO ANALYZER API - Documentación Completa para .NET

Base URL: http://localhost:8000

## ENDPOINTS GENERALES

### GET / - Root Endpoint
Información básica de la API
Respuesta: { "message": "Ginnet Audio Analyzer API", "version": "1.0.0", "status": "online", "docs": "/docs", "redoc": "/redoc" }

### GET /health - Health Check
Verifica el estado de la API
Respuesta: { "status": "healthy", "service": "Ginnet Audio Analyzer API", "version": "1.0.0" }

### GET /api/info - API Info
Información detallada de la API y endpoints disponibles

---

## ESPECTROGRAMAS - /api/spectrograms

### POST /api/spectrograms/generate
Genera espectrogramas para archivos de audio
Content-Type: multipart/form-data

Parámetros:
- files (List<IFormFile>) REQUERIDO - Archivos de audio (WAV, MP3, FLAC, M4A)
- segment_length (int) OPCIONAL default=3 - Duración de cada segmento en segundos

Ejemplo C#:
```csharp
using var formData = new MultipartFormDataContent();
formData.Add(new StreamContent(audioStream), "files", "audio.wav");
formData.Add(new StringContent("3"), "segment_length");
var response = await httpClient.PostAsync("http://localhost:8000/api/spectrograms/generate", formData);
```

Respuesta:
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
      "output_directory": "spectrograms/"
    }
  ]
}
```

### POST /api/spectrograms/generate-by-range
Genera espectrogramas en un rango de tiempo específico
Content-Type: multipart/form-data

Parámetros:
- files (List<IFormFile>) REQUERIDO - Archivos de audio
- start_time (float) REQUERIDO - Tiempo inicial en segundos
- end_time (float) REQUERIDO - Tiempo final en segundos
- segment_length (int) OPCIONAL default=3 - Duración del segmento en segundos
- mode (string) OPCIONAL default="complete" - "complete" o "combined"
- time_jump (float) OPCIONAL default=3 - Salto de tiempo para modo combinado

Ejemplo C#:
```csharp
using var formData = new MultipartFormDataContent();
formData.Add(new StreamContent(audioStream), "files", "audio.wav");
formData.Add(new StringContent("10.5"), "start_time");
formData.Add(new StringContent("30.0"), "end_time");
formData.Add(new StringContent("3"), "segment_length");
formData.Add(new StringContent("complete"), "mode");
var response = await httpClient.PostAsync("http://localhost:8000/api/spectrograms/generate-by-range", formData);
```

### POST /api/spectrograms/generate-by-jumps
Genera espectrogramas con saltos de tiempo específicos
Content-Type: multipart/form-data

Parámetros:
- files (List<IFormFile>) REQUERIDO - Archivos de audio
- time_jump (float) REQUERIDO - Salto de tiempo en segundos
- segment_length (int) OPCIONAL default=3 - Duración del segmento

Ejemplo C#:
```csharp
using var formData = new MultipartFormDataContent();
formData.Add(new StreamContent(audioStream), "files", "audio.wav");
formData.Add(new StringContent("5.0"), "time_jump");
formData.Add(new StringContent("3"), "segment_length");
var response = await httpClient.PostAsync("http://localhost:8000/api/spectrograms/generate-by-jumps", formData);
```

### GET /api/spectrograms/list/{directory_type}
Lista los espectrogramas generados

Parámetros de Ruta:
- directory_type (string) - "normal", "range" o "jumps"

Ejemplo:
```csharp
var response = await httpClient.GetAsync("http://localhost:8000/api/spectrograms/list/normal");
```

Respuesta:
```json
{
  "success": true,
  "spectrograms": ["audio_1_segment_0.png", "audio_1_segment_1.png"],
  "total": 2,
  "directory": "spectrograms/"
}
```

### GET /api/spectrograms/download/{directory_type}/{filename}
Descarga un espectrograma específico

Parámetros de Ruta:
- directory_type (string) - "normal", "range" o "jumps"
- filename (string) - Nombre del archivo

Ejemplo:
```csharp
var response = await httpClient.GetAsync("http://localhost:8000/api/spectrograms/download/normal/audio_1_segment_0.png");
var imageBytes = await response.Content.ReadAsByteArrayAsync();
```

---

## TRANSCRIPCIÓN - /api/transcription

### POST /api/transcription/transcribe
Transcribe múltiples archivos de audio
Content-Type: multipart/form-data

Parámetros:
- files (List<IFormFile>) REQUERIDO - Archivos de audio (WAV, MP3, FLAC, M4A)
- language (string) OPCIONAL default="es-ES" - Código de idioma

Idiomas soportados:
- es-ES (Español)
- en-US (Inglés)
- fr-FR (Francés)
- de-DE (Alemán)
- it-IT (Italiano)
- pt-BR (Portugués)

Ejemplo C#:
```csharp
using var formData = new MultipartFormDataContent();
formData.Add(new StreamContent(audioStream), "files", "audio.wav");
formData.Add(new StringContent("es-ES"), "language");
var response = await httpClient.PostAsync("http://localhost:8000/api/transcription/transcribe", formData);
```

Respuesta:
```json
{
  "success": true,
  "message": "Transcripción completada para 1 archivos",
  "transcriptions": [
    {
      "filename": "audio.wav",
      "transcription": "Texto transcrito aquí...",
      "method": "whisper"
    }
  ],
  "total_files": 1,
  "language": "es-ES"
}
```

### POST /api/transcription/transcribe-single
Transcribe un solo archivo de audio
Content-Type: multipart/form-data

Parámetros:
- file (IFormFile) REQUERIDO - Archivo de audio
- language (string) OPCIONAL default="es-ES" - Código de idioma
- max_duration (int) OPCIONAL default=300 - Duración máxima en segundos

Ejemplo C#:
```csharp
using var formData = new MultipartFormDataContent();
formData.Add(new StreamContent(audioStream), "file", "audio.wav");
formData.Add(new StringContent("es-ES"), "language");
formData.Add(new StringContent("300"), "max_duration");
var response = await httpClient.PostAsync("http://localhost:8000/api/transcription/transcribe-single", formData);
```

Respuesta:
```json
{
  "success": true,
  "filename": "audio.wav",
  "transcription": "Texto transcrito aquí...",
  "method": "whisper",
  "language": "es-ES"
}
```

### POST /api/transcription/generate-report
Transcribe archivos y genera un reporte en formato TXT
Content-Type: multipart/form-data

Parámetros:
- files (List<IFormFile>) REQUERIDO - Archivos de audio
- language (string) OPCIONAL default="es-ES" - Código de idioma

Ejemplo C#:
```csharp
using var formData = new MultipartFormDataContent();
formData.Add(new StreamContent(audioStream), "files", "audio.wav");
formData.Add(new StringContent("es-ES"), "language");
var response = await httpClient.PostAsync("http://localhost:8000/api/transcription/generate-report", formData);
```

Respuesta:
```json
{
  "success": true,
  "message": "Reporte de transcripción generado",
  "transcription_result": { ... },
  "report_info": {
    "report_path": "reports/transcription_report.txt",
    "report_name": "transcription_report.txt"
  }
}
```

### GET /api/transcription/download-report/{report_name}
Descarga un reporte de transcripción

Parámetros de Ruta:
- report_name (string) - Nombre del archivo de reporte

Ejemplo:
```csharp
var response = await httpClient.GetAsync("http://localhost:8000/api/transcription/download-report/transcription_report.txt");
var reportText = await response.Content.ReadAsStringAsync();
```

---

## ANÁLISIS YOLO - /api/analysis

### POST /api/analysis/run-yolo
Ejecuta análisis YOLO sobre espectrogramas generados
Content-Type: application/x-www-form-urlencoded

Parámetros:
- input_directory_type (string) OPCIONAL default="normal" - "normal", "range" o "jumps"
- segment_length (int) OPCIONAL default=3 - Duración del segmento (para seleccionar modelo)

Modelos YOLO:
- segment_length = 1 → modelo grayscale
- segment_length >= 3 → modelo normal

Ejemplo C#:
```csharp
var formData = new FormUrlEncodedContent(new[]
{
    new KeyValuePair<string, string>("input_directory_type", "normal"),
    new KeyValuePair<string, string>("segment_length", "3")
});
var response = await httpClient.PostAsync("http://localhost:8000/api/analysis/run-yolo", formData);
```

Respuesta:
```json
{
  "success": true,
  "message": "Análisis YOLO completado",
  "total_detections": 15,
  "files_with_detections": 8,
  "output_directory": "resultados_normal/"
}
```

### POST /api/analysis/run-yolo-custom
Ejecuta análisis YOLO con configuración personalizada
Content-Type: application/x-www-form-urlencoded

Parámetros:
- input_directory (string) REQUERIDO - Ruta al directorio con espectrogramas
- model_type (string) OPCIONAL default="normal" - "normal" o "grayscale"

Ejemplo C#:
```csharp
var formData = new FormUrlEncodedContent(new[]
{
    new KeyValuePair<string, string>("input_directory", "C:/spectrograms/"),
    new KeyValuePair<string, string>("model_type", "normal")
});
var response = await httpClient.PostAsync("http://localhost:8000/api/analysis/run-yolo-custom", formData);
```

### GET /api/analysis/results
Obtiene el listado de archivos con detecciones

Ejemplo:
```csharp
var response = await httpClient.GetAsync("http://localhost:8000/api/analysis/results");
```

Respuesta:
```json
{
  "success": true,
  "detections": ["audio_1_segment_0.png", "audio_1_segment_2.png"],
  "total": 2,
  "directory": "resultados_normal/"
}
```

---

## REPORTES - /api/reports

### POST /api/reports/generate-consolidated
Genera un reporte consolidado en formato Word (DOCX)
Content-Type: application/x-www-form-urlencoded

Parámetros:
- detections_data (string JSON) REQUERIDO - Datos de detecciones por archivo
- audio_files (List<string>) REQUERIDO - Lista de nombres de archivos de audio

Ejemplo C#:
```csharp
var detectionsData = new Dictionary<string, object>
{
    ["audio_1.wav"] = new { detections = 5, segments = new[] { 1, 3, 5, 7, 9 } },
    ["audio_2.wav"] = new { detections = 3, segments = new[] { 2, 4, 6 } }
};
var detectionsJson = JsonSerializer.Serialize(detectionsData);

var formData = new FormUrlEncodedContent(new[]
{
    new KeyValuePair<string, string>("detections_data", detectionsJson),
    new KeyValuePair<string, string>("audio_files", "audio_1.wav"),
    new KeyValuePair<string, string>("audio_files", "audio_2.wav")
});
var response = await httpClient.PostAsync("http://localhost:8000/api/reports/generate-consolidated", formData);
```

Respuesta:
```json
{
  "success": true,
  "message": "Reporte consolidado generado",
  "report_path": "reports/consolidated_report.docx",
  "report_name": "consolidated_report.docx"
}
```

### POST /api/reports/generate-chart
Genera un gráfico resumen de detecciones (PNG)
Content-Type: application/x-www-form-urlencoded

Parámetros:
- detections_data (string JSON) REQUERIDO - Datos de detecciones por archivo

Ejemplo C#:
```csharp
var detectionsData = new Dictionary<string, object>
{
    ["audio_1.wav"] = new { detections = 5 },
    ["audio_2.wav"] = new { detections = 3 }
};
var detectionsJson = JsonSerializer.Serialize(detectionsData);

var formData = new FormUrlEncodedContent(new[]
{
    new KeyValuePair<string, string>("detections_data", detectionsJson)
});
var response = await httpClient.PostAsync("http://localhost:8000/api/reports/generate-chart", formData);
```

Respuesta:
```json
{
  "success": true,
  "message": "Gráfico generado",
  "chart_path": "reports/summary_chart.png",
  "chart_name": "summary_chart.png"
}
```

### GET /api/reports/list
Lista todos los reportes generados

Ejemplo:
```csharp
var response = await httpClient.GetAsync("http://localhost:8000/api/reports/list");
```

Respuesta:
```json
{
  "success": true,
  "reports": ["report1.docx", "chart.png", "transcription.txt"],
  "reports_by_type": {
    "word": ["report1.docx"],
    "text": ["transcription.txt"],
    "images": ["chart.png"]
  },
  "total": 3
}
```

### GET /api/reports/download/{report_name}
Descarga un reporte específico

Parámetros de Ruta:
- report_name (string) - Nombre del archivo de reporte

Ejemplo:
```csharp
var response = await httpClient.GetAsync("http://localhost:8000/api/reports/download/consolidated_report.docx");
var fileBytes = await response.Content.ReadAsByteArrayAsync();
await File.WriteAllBytesAsync("downloaded_report.docx", fileBytes);
```

### DELETE /api/reports/delete/{report_name}
Elimina un reporte específico

Parámetros de Ruta:
- report_name (string) - Nombre del archivo de reporte

Ejemplo:
```csharp
var response = await httpClient.DeleteAsync("http://localhost:8000/api/reports/delete/report1.docx");
```

Respuesta:
```json
{
  "success": true,
  "message": "Reporte report1.docx eliminado"
}
```

---

## EJEMPLO COMPLETO DE CLIENTE .NET

```csharp
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.IO;
using System.Threading.Tasks;
using System.Text.Json;

public class GinnetAudioAnalyzerClient
{
    private readonly HttpClient _httpClient;
    private const string BaseUrl = "http://localhost:8000";

    public GinnetAudioAnalyzerClient()
    {
        _httpClient = new HttpClient { BaseAddress = new Uri(BaseUrl) };
    }

    // Generar espectrogramas
    public async Task<string> GenerateSpectrogramsAsync(string audioFilePath, int segmentLength = 3)
    {
        using var formData = new MultipartFormDataContent();
        using var fileStream = File.OpenRead(audioFilePath);
        using var streamContent = new StreamContent(fileStream);
        
        streamContent.Headers.ContentType = new MediaTypeHeaderValue("audio/wav");
        formData.Add(streamContent, "files", Path.GetFileName(audioFilePath));
        formData.Add(new StringContent(segmentLength.ToString()), "segment_length");

        var response = await _httpClient.PostAsync("/api/spectrograms/generate", formData);
        return await response.Content.ReadAsStringAsync();
    }

    // Ejecutar análisis YOLO
    public async Task<string> RunYoloAnalysisAsync(string directoryType = "normal", int segmentLength = 3)
    {
        var formData = new FormUrlEncodedContent(new[]
        {
            new KeyValuePair<string, string>("input_directory_type", directoryType),
            new KeyValuePair<string, string>("segment_length", segmentLength.ToString())
        });

        var response = await _httpClient.PostAsync("/api/analysis/run-yolo", formData);
        return await response.Content.ReadAsStringAsync();
    }

    // Transcribir audio
    public async Task<string> TranscribeAudioAsync(string audioFilePath, string language = "es-ES")
    {
        using var formData = new MultipartFormDataContent();
        using var fileStream = File.OpenRead(audioFilePath);
        using var streamContent = new StreamContent(fileStream);
        
        streamContent.Headers.ContentType = new MediaTypeHeaderValue("audio/wav");
        formData.Add(streamContent, "files", Path.GetFileName(audioFilePath));
        formData.Add(new StringContent(language), "language");

        var response = await _httpClient.PostAsync("/api/transcription/transcribe", formData);
        return await response.Content.ReadAsStringAsync();
    }

    // Generar reporte consolidado
    public async Task<string> GenerateConsolidatedReportAsync(Dictionary<string, object> detectionsData, List<string> audioFiles)
    {
        var detectionsJson = JsonSerializer.Serialize(detectionsData);
        var formValues = new List<KeyValuePair<string, string>>
        {
            new KeyValuePair<string, string>("detections_data", detectionsJson)
        };
        
        foreach (var file in audioFiles)
        {
            formValues.Add(new KeyValuePair<string, string>("audio_files", file));
        }

        var formData = new FormUrlEncodedContent(formValues);
        var response = await _httpClient.PostAsync("/api/reports/generate-consolidated", formData);
        return await response.Content.ReadAsStringAsync();
    }

    // Descargar reporte
    public async Task<byte[]> DownloadReportAsync(string reportName)
    {
        var response = await _httpClient.GetAsync($"/api/reports/download/{reportName}");
        return await response.Content.ReadAsByteArrayAsync();
    }

    // Health check
    public async Task<bool> IsHealthyAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/health");
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }
}

// Ejemplo de uso
public class Program
{
    public static async Task Main(string[] args)
    {
        var client = new GinnetAudioAnalyzerClient();

        // Verificar salud de la API
        if (!await client.IsHealthyAsync())
        {
            Console.WriteLine("API no disponible");
            return;
        }

        // 1. Generar espectrogramas
        var spectrogramResult = await client.GenerateSpectrogramsAsync("audio.wav", 3);
        Console.WriteLine(spectrogramResult);

        // 2. Ejecutar análisis YOLO
        var yoloResult = await client.RunYoloAnalysisAsync("normal", 3);
        Console.WriteLine(yoloResult);

        // 3. Transcribir audio
        var transcriptionResult = await client.TranscribeAudioAsync("audio.wav", "es-ES");
        Console.WriteLine(transcriptionResult);

        // 4. Generar reporte
        var detections = new Dictionary<string, object>
        {
            ["audio.wav"] = new { detections = 5, segments = new[] { 1, 3, 5, 7, 9 } }
        };
        var reportResult = await client.GenerateConsolidatedReportAsync(detections, new List<string> { "audio.wav" });
        Console.WriteLine(reportResult);

        // 5. Descargar reporte
        var reportBytes = await client.DownloadReportAsync("consolidated_report.docx");
        await File.WriteAllBytesAsync("reporte_descargado.docx", reportBytes);
    }
}
```

---

## FLUJO DE TRABAJO TÍPICO

1. **Generar espectrogramas**: POST /api/spectrograms/generate
2. **Ejecutar análisis YOLO**: POST /api/analysis/run-yolo
3. **Obtener resultados**: GET /api/analysis/results
4. **Generar reporte consolidado**: POST /api/reports/generate-consolidated
5. **Descargar reporte**: GET /api/reports/download/{report_name}

Opcionalmente:
- **Transcribir audio**: POST /api/transcription/transcribe
- **Generar gráfico**: POST /api/reports/generate-chart

---

## NOTAS IMPORTANTES

- Todos los endpoints devuelven JSON con un campo "success" (true/false)
- Los errores incluyen "error" y "message" en la respuesta
- Los archivos de audio soportados son: WAV, MP3, FLAC, M4A
- Los modelos YOLO se seleccionan automáticamente según segment_length
- CORS está habilitado para permitir llamadas desde .NET
- El servidor corre en puerto 8000 por defecto
