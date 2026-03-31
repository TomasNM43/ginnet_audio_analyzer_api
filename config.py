"""
Archivo de configuración para el API
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Directorio base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directorios de trabajo
TEMP_FILES_DIR = os.path.join(BASE_DIR, 'temp_files')
SPECTROGRAMS_DIR = os.path.join(BASE_DIR, 'spectrograms')
SPECTROGRAMS_RANGE_DIR = os.path.join(BASE_DIR, 'spectrograms_time_range')
SPECTROGRAMS_JUMPS_DIR = os.path.join(BASE_DIR, 'spectrograms_jumps')
RESULTS_DIR = os.path.join(BASE_DIR, 'resultados_normal')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
MODELS_BRIGHTNESS_DIR = os.path.join(BASE_DIR, 'modelos_brightness')

# Crear directorios si no existen
for directory in [TEMP_FILES_DIR, SPECTROGRAMS_DIR, 
                  SPECTROGRAMS_RANGE_DIR, SPECTROGRAMS_JUMPS_DIR, 
                  RESULTS_DIR, REPORTS_DIR, MODELS_DIR, MODELS_BRIGHTNESS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Configuración de la API
API_TITLE = "Ginnet Audio Analyzer API"
API_DESCRIPTION = """
API para análisis de archivos de audio mediante generación de espectrogramas y detección con YOLO.

## Funcionalidades principales:

### Audio:
* **Generación de Espectrogramas**: Convierte archivos de audio en espectrogramas
* **Transcripción de Audio**: Convierte voz a texto usando múltiples métodos
* **Análisis YOLO de Audio**: Detecta cortes y anomalías en espectrogramas
* **Reportes de Audio**: Genera reportes consolidados en formato Word y TXT

### Video e Imágenes:
* **Autenticidad de Video (YOLO)**: Detecta rectángulos negros y manipulaciones en videos
* **Continuidad de Video**: Analiza la continuidad temporal detectando cortes y ediciones
* **Extracción de Fotogramas**: Extrae frames de videos con ajuste de brillo
* **Autenticidad de Fotos (ELA)**: Análisis ELA (Error Level Analysis) para detectar manipulaciones
* **Conversión a Escala de Grises**: Procesa imágenes convirtiéndolas a escala de grises

## Flujo de trabajo recomendado:

### Audio:
1. Subir archivos de audio y generar espectrogramas
2. Ejecutar análisis YOLO sobre los espectrogramas
3. Generar reportes consolidados
4. Opcionalmente, transcribir archivos de audio

### Video:
1. Análisis de autenticidad con YOLO (detectar rectángulos negros)
2. Análisis de continuidad (detectar cortes/ediciones)
3. Extracción de fotogramas para análisis detallado
4. Análisis ELA de imágenes/fotogramas extraídos
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

# Configuración de Base de Datos (Oracle SQL)
DB_CONFIG = {
    'user': os.getenv('DB_USER', 'system'),
    'password': os.getenv('DB_PASSWORD', ''),
    'dsn': os.getenv('DB_DSN', 'localhost:1521/XEPDB1')  # format: host:port/service_name
}
