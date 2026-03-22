# Script de verificacion para la migracion de API de Video
# Ejecutar este script para verificar que todo esta correctamente configurado

Write-Host "=== Verificacion de Migracion de API de Video ===" -ForegroundColor Cyan
Write-Host ""

$baseDir = "C:\Users\user\Documents\ginnet_audio_analyzer_api"
$errores = 0
$advertencias = 0

# Verificar estructura de directorios
Write-Host "1. Verificando estructura de directorios..." -ForegroundColor Yellow

$directoriosRequeridos = @(
    "$baseDir\services",
    "$baseDir\utils",
    "$baseDir\routes",
    "$baseDir\modelos_brightness",
    "$baseDir\reports"
)

foreach ($dir in $directoriosRequeridos) {
    if (Test-Path $dir) {
        Write-Host "  [OK] $dir" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] $dir - NO EXISTE" -ForegroundColor Red
        $errores++
    }
}

Write-Host ""

# Verificar archivos de services
Write-Host "2. Verificando archivos de services..." -ForegroundColor Yellow

$servicesRequeridos = @(
    "video_service.py",
    "continuity_service.py",
    "ela_service.py",
    "frame_extractor.py",
    "grayscale_conversion_service.py",
    "video_db_service.py"
)

foreach ($file in $servicesRequeridos) {
    $path = "$baseDir\services\$file"
    if (Test-Path $path) {
        Write-Host "  [OK] $file" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] $file - NO EXISTE" -ForegroundColor Red
        $errores++
    }
}

Write-Host ""

# Verificar archivos de utils
Write-Host "3. Verificando archivos de utils..." -ForegroundColor Yellow

$utilsRequeridos = @(
    "video_report_generator.py"
)

foreach ($file in $utilsRequeridos) {
    $path = "$baseDir\utils\$file"
    if (Test-Path $path) {
        Write-Host "  [OK] $file" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] $file - NO EXISTE" -ForegroundColor Red
        $errores++
    }
}

Write-Host ""

# Verificar archivos de routes
Write-Host "4. Verificando archivos de routes..." -ForegroundColor Yellow

$routesRequeridos = @(
    "video_routes.py"
)

foreach ($file in $routesRequeridos) {
    $path = "$baseDir\routes\$file"
    if (Test-Path $path) {
        Write-Host "  [OK] $file" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] $file - NO EXISTE" -ForegroundColor Red
        $errores++
    }
}

Write-Host ""

# Verificar modelos YOLO
Write-Host "5. Verificando modelos YOLO..." -ForegroundColor Yellow

$modelosRequeridos = @(
    "best_20.pt",
    "best_30.pt",
    "best_40.pt"
)

foreach ($file in $modelosRequeridos) {
    $path = "$baseDir\modelos_brightness\$file"
    if (Test-Path $path) {
        $size = (Get-Item $path).Length / 1MB
        Write-Host "  [OK] $file - $([math]::Round($size, 2)) MB" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] $file - NO ENCONTRADO (debe copiarse manualmente)" -ForegroundColor Yellow
        $advertencias++
    }
}

Write-Host ""

# Verificar main.py actualizado
Write-Host "6. Verificando main.py..." -ForegroundColor Yellow

$mainPath = "$baseDir\main.py"
if (Test-Path $mainPath) {
    $contenido = Get-Content $mainPath -Raw
    
    if ($contenido -match "video_routes") {
        Write-Host "  [OK] Import de video_routes encontrado" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Import de video_routes NO encontrado" -ForegroundColor Red
        $errores++
    }
    
    if ($contenido -match "app.include_router\(video_routes.router\)") {
        Write-Host "  [OK] Router de video registrado" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Router de video NO registrado" -ForegroundColor Red
        $errores++
    }
} else {
    Write-Host "  [ERROR] main.py NO EXISTE" -ForegroundColor Red
    $errores++
}

Write-Host ""

# Verificar config.py actualizado
Write-Host "7. Verificando config.py..." -ForegroundColor Yellow

$configPath = "$baseDir\config.py"
if (Test-Path $configPath) {
    $contenido = Get-Content $configPath -Raw
    
    if ($contenido -match "MODELS_BRIGHTNESS_DIR") {
        Write-Host "  [OK] MODELS_BRIGHTNESS_DIR configurado" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] MODELS_BRIGHTNESS_DIR NO configurado" -ForegroundColor Red
        $errores++
    }
} else {
    Write-Host "  [ERROR] config.py NO EXISTE" -ForegroundColor Red
    $errores++
}

Write-Host ""

# Verificar variables de entorno
Write-Host "8. Verificando variables de entorno (.env)..." -ForegroundColor Yellow

$envPath = "$baseDir\.env"
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    
    $varsEsperadas = @("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN", "DB_USER", "DB_PASSWORD", "DB_DSN")
    $varsEncontradas = 0
    
    foreach ($var in $varsEsperadas) {
        if ($envContent -match $var) {
            $varsEncontradas++
        }
    }
    
    if ($varsEncontradas -ge 3) {
        Write-Host "  [OK] Variables de BD configuradas" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Solo $varsEncontradas variables de BD encontradas" -ForegroundColor Yellow
        $advertencias++
    }
} else {
    Write-Host "  [WARN] Archivo .env no encontrado" -ForegroundColor Yellow
    $advertencias++
}

Write-Host ""
Write-Host "=== Resumen de Verificacion ===" -ForegroundColor Cyan
Write-Host ""

if ($errores -eq 0 -and $advertencias -eq 0) {
    Write-Host "[OK] TODO CORRECTO - Migracion completada exitosamente" -ForegroundColor Green
    Write-Host ""
    Write-Host "Proximos pasos:" -ForegroundColor Cyan
    Write-Host "1. Copiar modelos YOLO a modelos_brightness/" -ForegroundColor White
    Write-Host "2. Configurar variables de entorno en .env" -ForegroundColor White
    Write-Host "3. Iniciar servidor: .\start_server.ps1" -ForegroundColor White
    Write-Host "4. Probar endpoints en http://localhost:8000/docs" -ForegroundColor White
} elseif ($errores -eq 0) {
    Write-Host "[WARN] MIGRACION COMPLETADA CON ADVERTENCIAS" -ForegroundColor Yellow
    Write-Host "Advertencias: $advertencias" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Revisa las advertencias anteriores y completa las tareas pendientes." -ForegroundColor White
} else {
    Write-Host "[ERROR] ERRORES ENCONTRADOS" -ForegroundColor Red
    Write-Host "Errores: $errores" -ForegroundColor Red
    Write-Host "Advertencias: $advertencias" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Revisa los errores anteriores antes de continuar." -ForegroundColor White
}

Write-Host ""
Write-Host "Consulta VIDEO_MIGRATION_README.md para mas informacion." -ForegroundColor Cyan
