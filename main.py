"""
Aplicación principal FastAPI para Ginnet Audio Analyzer
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

# Importar configuración
from config import (
    API_TITLE, API_DESCRIPTION, API_VERSION, API_CONTACT,
    CORS_ORIGINS, RESULTS_DIR, REPORTS_DIR, SPECTROGRAMS_DIR
)

# Importar routes
from routes import spectrogram_routes, transcription_routes, analysis_routes, report_routes, pipeline_routes, video_routes, photo_routes

# Crear aplicación FastAPI
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    contact=API_CONTACT
)

# Configurar CORS para permitir llamadas desde .NET
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(spectrogram_routes.router)
app.include_router(transcription_routes.router)
app.include_router(analysis_routes.router)
app.include_router(report_routes.router)
app.include_router(pipeline_routes.router)
app.include_router(video_routes.router)
app.include_router(photo_routes.router)

# Servir archivos estáticos (resultados, reportes, espectrogramas)
if os.path.exists(RESULTS_DIR):
    app.mount("/static/results", StaticFiles(directory=RESULTS_DIR), name="results")
if os.path.exists(REPORTS_DIR):
    app.mount("/static/reports", StaticFiles(directory=REPORTS_DIR), name="reports")
if os.path.exists(SPECTROGRAMS_DIR):
    app.mount("/static/spectrograms", StaticFiles(directory=SPECTROGRAMS_DIR), name="spectrograms")

# Manejador de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "message": "Error interno del servidor"
        }
    )

# Endpoint raíz
@app.get("/", tags=["General"])
async def root():
    """
    Endpoint raíz - Información básica de la API
    """
    return {
        "message": "Ginnet Audio Analyzer API",
        "version": API_VERSION,
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "spectrograms": "/api/spectrograms",
            "transcription": "/api/transcription",
            "analysis": "/api/analysis",
            "reports": "/api/reports",
            "pipeline": "/api/pipeline"
        }
    }

# Endpoint de salud
@app.get("/health", tags=["General"])
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "service": "Ginnet Audio Analyzer API",
        "version": API_VERSION
    }

# Endpoint de información
@app.get("/api/info", tags=["General"])
async def get_api_info():
    """
    Información detallada de la API
    """
    from config import SUPPORTED_LANGUAGES, YOLO_MODELS
    
    return {
        "api_name": API_TITLE,
        "version": API_VERSION,
        "description": "API para análisis de audio mediante espectrogramas y YOLO",
        "supported_languages": SUPPORTED_LANGUAGES,
        "available_models": {
            "normal": os.path.exists(YOLO_MODELS['normal']),
            "grayscale": os.path.exists(YOLO_MODELS['grayscale'])
        },
        "endpoints": {
            "spectrograms": {
                "generate": "POST /api/spectrograms/generate",
                "generate_by_range": "POST /api/spectrograms/generate-by-range",
                "generate_by_jumps": "POST /api/spectrograms/generate-by-jumps",
                "list": "GET /api/spectrograms/list/{directory_type}",
                "download": "GET /api/spectrograms/download/{directory_type}/{filename}"
            },
            "transcription": {
                "transcribe": "POST /api/transcription/transcribe",
                "transcribe_single": "POST /api/transcription/transcribe-single",
                "generate_report": "POST /api/transcription/generate-report",
                "download_report": "GET /api/transcription/download-report/{report_name}"
            },
            "analysis": {
                "run_yolo": "POST /api/analysis/run-yolo",
                "run_yolo_custom": "POST /api/analysis/run-yolo-custom",
                "get_results": "GET /api/analysis/results"
            },
            "reports": {
                "generate_consolidated": "POST /api/reports/generate-consolidated",
                "generate_chart": "POST /api/reports/generate-chart",
                "list": "GET /api/reports/list",
                "download": "GET /api/reports/download/{report_name}",
                "delete": "DELETE /api/reports/delete/{report_name}"
            },
            "pipeline": {
                "full_analysis": "POST /api/pipeline/analyze",
                "transcription": "POST /api/pipeline/transcribe"
            }
        }
    }

# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    # Ejecutar servidor con uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Recarga automática en desarrollo
        log_level="info"
    )
