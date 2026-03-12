# Script de PowerShell para instalar dependencias de Ginnet Audio Analyzer API

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Instalación - Ginnet Audio Analyzer API" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
Write-Host "Verificando Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python no está instalado o no está en el PATH." -ForegroundColor Red
    Write-Host "Por favor, instale Python 3.8 o superior desde https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Crear entorno virtual
Write-Host ""
Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "El entorno virtual ya existe. Eliminando..." -ForegroundColor Yellow
    Remove-Item -Path "venv" -Recurse -Force
}

python -m venv venv
Write-Host "Entorno virtual creado." -ForegroundColor Green

# Activar entorno virtual
Write-Host ""
Write-Host "Activando entorno virtual..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Actualizar pip
Write-Host ""
Write-Host "Actualizando pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Instalar dependencias
Write-Host ""
Write-Host "Instalando dependencias desde requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt

# Verificar instalación
Write-Host ""
Write-Host "Verificando instalación..." -ForegroundColor Yellow
$packages = @("fastapi", "uvicorn", "librosa", "ultralytics", "python-docx")
$allInstalled = $true

foreach ($package in $packages) {
    $installed = pip list | Select-String -Pattern $package
    if ($installed) {
        Write-Host "  ✓ $package instalado" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $package NO instalado" -ForegroundColor Red
        $allInstalled = $false
    }
}

# Verificar FFmpeg
Write-Host ""
Write-Host "Verificando FFmpeg..." -ForegroundColor Yellow
try {
    $ffmpegVersion = ffmpeg -version 2>$null
    if ($ffmpegVersion) {
        Write-Host "  ✓ FFmpeg instalado" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ FFmpeg NO encontrado" -ForegroundColor Yellow
    Write-Host "    FFmpeg es necesario para el procesamiento de audio." -ForegroundColor Yellow
    Write-Host "    Descárguelo desde: https://ffmpeg.org/download.html" -ForegroundColor Yellow
}

# Verificar modelos YOLO
Write-Host ""
Write-Host "Verificando modelos YOLO..." -ForegroundColor Yellow
$modelNormal = Test-Path "models\normal\best.pt"
$modelGrayscale = Test-Path "models\grayscale\best.pt"

if ($modelNormal) {
    Write-Host "  ✓ Modelo normal encontrado" -ForegroundColor Green
} else {
    Write-Host "  ✗ Modelo normal NO encontrado" -ForegroundColor Yellow
    Write-Host "    Copie best.pt a: models\normal\best.pt" -ForegroundColor Yellow
}

if ($modelGrayscale) {
    Write-Host "  ✓ Modelo grayscale encontrado" -ForegroundColor Green
} else {
    Write-Host "  ✗ Modelo grayscale NO encontrado" -ForegroundColor Yellow
    Write-Host "    Copie best.pt a: models\grayscale\best.pt" -ForegroundColor Yellow
}

# Resumen
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Resumen de Instalación" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

if ($allInstalled -and $modelNormal -and $modelGrayscale) {
    Write-Host "✓ Instalación completada exitosamente" -ForegroundColor Green
    Write-Host ""
    Write-Host "Para iniciar el servidor, ejecute:" -ForegroundColor White
    Write-Host "  .\start_server.ps1" -ForegroundColor Cyan
} else {
    Write-Host "⚠ Instalación completada con advertencias" -ForegroundColor Yellow
    Write-Host "Por favor, revise los errores anteriores." -ForegroundColor Yellow
}

Write-Host ""
