/**
 * Clase cliente en C# para consumir Ginnet Audio Analyzer API
 * 
 * Uso desde una aplicación .NET Core / .NET 5+
 */

using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;

namespace GinnetAudioAnalyzer.Client
{
    /// <summary>
    /// Cliente para interactuar con Ginnet Audio Analyzer API
    /// </summary>
    public class GinnetAudioAnalyzerClient : IDisposable
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;

        public GinnetAudioAnalyzerClient(string baseUrl = "http://localhost:8000")
        {
            _baseUrl = baseUrl;
            _httpClient = new HttpClient
            {
                BaseAddress = new Uri(baseUrl),
                Timeout = TimeSpan.FromMinutes(10) // Timeout largo para procesamiento
            };
        }

        #region Espectrogramas

        /// <summary>
        /// Genera espectrogramas para uno o más archivos de audio
        /// </summary>
        public async Task<ApiResponse> GenerateSpectrogramsAsync(
            List<string> audioFilePaths, 
            int segmentLength = 3)
        {
            using var form = new MultipartFormDataContent();
            
            foreach (var filePath in audioFilePaths)
            {
                var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync(filePath));
                fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
                form.Add(fileContent, "files", Path.GetFileName(filePath));
            }
            
            form.Add(new StringContent(segmentLength.ToString()), "segment_length");

            var response = await _httpClient.PostAsync("/api/spectrograms/generate", form);
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<ApiResponse>(jsonResponse);
        }

        /// <summary>
        /// Genera espectrogramas en un rango de tiempo específico
        /// </summary>
        public async Task<ApiResponse> GenerateSpectrogramsByRangeAsync(
            List<string> audioFilePaths,
            double startTime,
            double endTime,
            int segmentLength = 3,
            string mode = "complete",
            double? timeJump = null)
        {
            using var form = new MultipartFormDataContent();
            
            foreach (var filePath in audioFilePaths)
            {
                var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync(filePath));
                fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
                form.Add(fileContent, "files", Path.GetFileName(filePath));
            }
            
            form.Add(new StringContent(startTime.ToString()), "start_time");
            form.Add(new StringContent(endTime.ToString()), "end_time");
            form.Add(new StringContent(segmentLength.ToString()), "segment_length");
            form.Add(new StringContent(mode), "mode");
            
            if (timeJump.HasValue)
                form.Add(new StringContent(timeJump.Value.ToString()), "time_jump");

            var response = await _httpClient.PostAsync("/api/spectrograms/generate-by-range", form);
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<ApiResponse>(jsonResponse);
        }

        /// <summary>
        /// Genera espectrogramas con saltos de tiempo
        /// </summary>
        public async Task<ApiResponse> GenerateSpectrogramsByJumpsAsync(
            List<string> audioFilePaths,
            double timeJump = 3,
            int segmentLength = 3)
        {
            using var form = new MultipartFormDataContent();
            
            foreach (var filePath in audioFilePaths)
            {
                var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync(filePath));
                fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
                form.Add(fileContent, "files", Path.GetFileName(filePath));
            }
            
            form.Add(new StringContent(timeJump.ToString()), "time_jump");
            form.Add(new StringContent(segmentLength.ToString()), "segment_length");

            var response = await _httpClient.PostAsync("/api/spectrograms/generate-by-jumps", form);
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<ApiResponse>(jsonResponse);
        }

        /// <summary>
        /// Lista los espectrogramas generados
        /// </summary>
        public async Task<SpectrogramListResponse> ListSpectrogramsAsync(string directoryType = "normal")
        {
            var response = await _httpClient.GetAsync($"/api/spectrograms/list/{directoryType}");
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<SpectrogramListResponse>(jsonResponse);
        }

        /// <summary>
        /// Descarga un espectrograma específico
        /// </summary>
        public async Task<byte[]> DownloadSpectrogramAsync(
            string directoryType, 
            string filename)
        {
            var response = await _httpClient.GetAsync(
                $"/api/spectrograms/download/{directoryType}/{filename}");
            
            return await response.Content.ReadAsByteArrayAsync();
        }

        #endregion

        #region Transcripción

        /// <summary>
        /// Transcribe múltiples archivos de audio
        /// </summary>
        public async Task<TranscriptionResponse> TranscribeMultipleAudioAsync(
            List<string> audioFilePaths,
            string language = "es-ES")
        {
            using var form = new MultipartFormDataContent();
            
            foreach (var filePath in audioFilePaths)
            {
                var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync(filePath));
                fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
                form.Add(fileContent, "files", Path.GetFileName(filePath));
            }
            
            form.Add(new StringContent(language), "language");

            var response = await _httpClient.PostAsync("/api/transcription/transcribe", form);
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<TranscriptionResponse>(jsonResponse);
        }

        /// <summary>
        /// Transcribe un solo archivo de audio
        /// </summary>
        public async Task<SingleTranscriptionResponse> TranscribeSingleAudioAsync(
            string audioFilePath,
            string language = "es-ES",
            int maxDuration = 300)
        {
            using var form = new MultipartFormDataContent();
            
            var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync(audioFilePath));
            fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
            form.Add(fileContent, "file", Path.GetFileName(audioFilePath));
            form.Add(new StringContent(language), "language");
            form.Add(new StringContent(maxDuration.ToString()), "max_duration");

            var response = await _httpClient.PostAsync("/api/transcription/transcribe-single", form);
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<SingleTranscriptionResponse>(jsonResponse);
        }

        /// <summary>
        /// Genera reporte de transcripción
        /// </summary>
        public async Task<TranscriptionReportResponse> GenerateTranscriptionReportAsync(
            List<string> audioFilePaths,
            string language = "es-ES")
        {
            using var form = new MultipartFormDataContent();
            
            foreach (var filePath in audioFilePaths)
            {
                var fileContent = new ByteArrayContent(await File.ReadAllBytesAsync(filePath));
                fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("audio/wav");
                form.Add(fileContent, "files", Path.GetFileName(filePath));
            }
            
            form.Add(new StringContent(language), "language");

            var response = await _httpClient.PostAsync("/api/transcription/generate-report", form);
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<TranscriptionReportResponse>(jsonResponse);
        }

        #endregion

        #region Análisis YOLO

        /// <summary>
        /// Ejecuta análisis YOLO sobre espectrogramas
        /// </summary>
        public async Task<YoloAnalysisResponse> RunYoloAnalysisAsync(
            string inputDirectoryType = "normal",
            int segmentLength = 3)
        {
            using var form = new MultipartFormDataContent();
            form.Add(new StringContent(inputDirectoryType), "input_directory_type");
            form.Add(new StringContent(segmentLength.ToString()), "segment_length");

            var response = await _httpClient.PostAsync("/api/analysis/run-yolo", form);
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<YoloAnalysisResponse>(jsonResponse);
        }

        /// <summary>
        /// Obtiene resultados del análisis YOLO
        /// </summary>
        public async Task<YoloResultsResponse> GetYoloResultsAsync()
        {
            var response = await _httpClient.GetAsync("/api/analysis/results");
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<YoloResultsResponse>(jsonResponse);
        }

        #endregion

        #region Reportes

        /// <summary>
        /// Lista todos los reportes generados
        /// </summary>
        public async Task<ReportListResponse> ListReportsAsync()
        {
            var response = await _httpClient.GetAsync("/api/reports/list");
            var jsonResponse = await response.Content.ReadAsStringAsync();
            
            return JsonSerializer.Deserialize<ReportListResponse>(jsonResponse);
        }

        /// <summary>
        /// Descarga un reporte específico
        /// </summary>
        public async Task<byte[]> DownloadReportAsync(string reportName)
        {
            var response = await _httpClient.GetAsync($"/api/reports/download/{reportName}");
            return await response.Content.ReadAsByteArrayAsync();
        }

        #endregion

        public void Dispose()
        {
            _httpClient?.Dispose();
        }
    }

    #region Modelos de Respuesta

    public class ApiResponse
    {
        public bool Success { get; set; }
        public string Message { get; set; }
        public object Results { get; set; }
    }

    public class SpectrogramListResponse
    {
        public bool Success { get; set; }
        public List<string> Spectrograms { get; set; }
        public int Total { get; set; }
    }

    public class TranscriptionResponse
    {
        public bool Success { get; set; }
        public string Message { get; set; }
        public int TotalFiles { get; set; }
        public string Language { get; set; }
        public List<Transcription> Transcriptions { get; set; }
    }

    public class SingleTranscriptionResponse
    {
        public bool Success { get; set; }
        public string Filename { get; set; }
        public string Transcription { get; set; }
        public string Method { get; set; }
        public string Language { get; set; }
    }

    public class TranscriptionReportResponse
    {
        public bool Success { get; set; }
        public string Message { get; set; }
        public object TranscriptionResult { get; set; }
        public object ReportInfo { get; set; }
    }

    public class Transcription
    {
        public string File { get; set; }
        public string Path { get; set; }
        public string Duration { get; set; }
        public string TranscriptionText { get; set; }
        public string Method { get; set; }
        public int Index { get; set; }
    }

    public class YoloAnalysisResponse
    {
        public bool Success { get; set; }
        public string Message { get; set; }
        public object DetectionsByFile { get; set; }
        public int TotalFilesProcessed { get; set; }
        public int TotalDetections { get; set; }
        public string ModelUsed { get; set; }
    }

    public class YoloResultsResponse
    {
        public bool Success { get; set; }
        public List<string> Detections { get; set; }
        public int Total { get; set; }
    }

    public class ReportListResponse
    {
        public bool Success { get; set; }
        public List<string> Reports { get; set; }
        public int Total { get; set; }
    }

    #endregion

    #region Ejemplo de Uso

    public class Program
    {
        public static async Task Main(string[] args)
        {
            using var client = new GinnetAudioAnalyzerClient("http://localhost:8000");

            try
            {
                // 1. Generar espectrogramas
                Console.WriteLine("Generando espectrogramas...");
                var spectrogramResult = await client.GenerateSpectrogramsAsync(
                    new List<string> { "ruta/al/audio1.wav", "ruta/al/audio2.wav" },
                    segmentLength: 3
                );
                Console.WriteLine($"Espectrogramas generados: {spectrogramResult.Message}");

                // 2. Ejecutar análisis YOLO
                Console.WriteLine("\nEjecutando análisis YOLO...");
                var analysisResult = await client.RunYoloAnalysisAsync("normal", 3);
                Console.WriteLine($"Análisis completado: {analysisResult.TotalDetections} detecciones");

                // 3. Transcribir audio
                Console.WriteLine("\nTranscribiendo audio...");
                var transcriptionResult = await client.TranscribeSingleAudioAsync(
                    "ruta/al/audio.wav",
                    language: "es-ES"
                );
                Console.WriteLine($"Transcripción: {transcriptionResult.Transcription}");

                // 4. Listar reportes
                Console.WriteLine("\nListando reportes...");
                var reports = await client.ListReportsAsync();
                Console.WriteLine($"Total de reportes: {reports.Total}");
                
                foreach (var report in reports.Reports)
                {
                    Console.WriteLine($"  - {report}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error: {ex.Message}");
            }
        }
    }

    #endregion
}
