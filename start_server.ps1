# Script de PowerShell para iniciar el servidor de Ginnet Audio Analyzer API

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Ginnet Audio Analyzer API" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si existe el entorno virtual
if (-not (Test-Path "venv")) {
    Write-Host "No se encontró el entorno virtual. Creándolo..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "Entorno virtual creado." -ForegroundColor Green
}

# Activar entorno virtual
Write-Host "Activando entorno virtual..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Verificar si están instaladas las dependencias
Write-Host "Verificando dependencias..." -ForegroundColor Yellow
$installed = pip list

if ($installed -notmatch "fastapi") {
    Write-Host "Instalando dependencias..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host "Dependencias instaladas." -ForegroundColor Green
}

# Verificar modelos YOLO
Write-Host "Verificando modelos YOLO..." -ForegroundColor Yellow
$modelNormal = Test-Path "models\normal\best.pt"
$modelGrayscale = Test-Path "models\grayscale\best.pt"

if (-not $modelNormal -or -not $modelGrayscale) {
    Write-Host "ADVERTENCIA: No se encontraron todos los modelos YOLO." -ForegroundColor Red
    Write-Host "  - Modelo normal: $modelNormal" -ForegroundColor Yellow
    Write-Host "  - Modelo grayscale: $modelGrayscale" -ForegroundColor Yellow
    Write-Host "Por favor, copie los archivos best.pt a las carpetas correspondientes." -ForegroundColor Yellow
} else {
    Write-Host "Modelos YOLO encontrados correctamente." -ForegroundColor Green
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Iniciando servidor..." -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "El servidor estará disponible en:" -ForegroundColor Green
Write-Host "  - API: http://localhost:8000" -ForegroundColor White
Write-Host "  - Documentación: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - ReDoc: http://localhost:8000/redoc" -ForegroundColor White
Write-Host ""
Write-Host "Presione Ctrl+C para detener el servidor" -ForegroundColor Yellow
Write-Host ""

# Iniciar servidor usando el Python del entorno virtual
& "venv\Scripts\python.exe" main.py
