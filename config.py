"""
Archivo de configuración para el API
"""
import os

# Directorio base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directorios de trabajo
TEMP_FILES_DIR = os.path.join(BASE_DIR, 'temp_files')
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
SPECTROGRAMS_DIR = os.path.join(BASE_DIR, 'spectrograms')
SPECTROGRAMS_RANGE_DIR = os.path.join(BASE_DIR, 'spectrograms_time_range')
SPECTROGRAMS_JUMPS_DIR = os.path.join(BASE_DIR, 'spectrograms_jumps')
RESULTS_DIR = os.path.join(BASE_DIR, 'resultados_normal')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# Crear directorios si no existen
for directory in [TEMP_FILES_DIR, UPLOADS_DIR, SPECTROGRAMS_DIR, 
                  SPECTROGRAMS_RANGE_DIR, SPECTROGRAMS_JUMPS_DIR, 
                  RESULTS_DIR, REPORTS_DIR, MODELS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Configuración de la API
API_TITLE = "Ginnet Audio Analyzer API"
API_DESCRIPTION = """
API para análisis de archivos de audio mediante generación de espectrogramas y detección con YOLO.

## Funcionalidades principales:

* **Generación de Espectrogramas**: Convierte archivos de audio en espectrogramas
* **Transcripción de Audio**: Convierte voz a texto usando múltiples métodos
* **Análisis YOLO**: Detecta cortes y anomalías en espectrogramas
* **Reportes**: Genera reportes consolidados en formato Word y TXT

## Flujo de trabajo recomendado:

1. Subir archivos de audio y generar espectrogramas
2. Ejecutar análisis YOLO sobre los espectrogramas
3. Generar reportes consolidados
4. Opcionalmente, transcribir archivos de audio
"""
API_VERSION = "1.0.0"
API_CONTACT = {
    "name": "Ginnet Audio Analyzer",
    "email": "info@ginnet.com"
}

# Configuración de CORS (para permitir llamadas desde .NET)
CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:5001",
    "http://localhost:8080",
    "https://localhost",
    "https://localhost:3000",
    "https://localhost:5000",
    "https://localhost:5001",
    "https://localhost:8080",
    "*"  # Permitir todos los orígenes (solo para desarrollo)
]

# Configuración de archivos
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
ALLOWED_AUDIO_EXTENSIONS = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']

# Configuración de modelos YOLO
YOLO_MODELS = {
    'normal': os.path.join(MODELS_DIR, 'normal', 'best.pt'),
    'grayscale': os.path.join(MODELS_DIR, 'grayscale', 'best.pt')
}

# Configuración de transcripción
SUPPORTED_LANGUAGES = {
    'es-ES': 'Español (España)',
    'es-MX': 'Español (México)',
    'en-US': 'Inglés (Estados Unidos)',
    'en-GB': 'Inglés (Reino Unido)',
    'fr-FR': 'Francés',
    'it-IT': 'Italiano',
    'pt-PT': 'Portugués',
    'de-DE': 'Alemán'
}
