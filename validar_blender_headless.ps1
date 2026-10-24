# ================================================================
# VALIDACIÓN BLENDER HEADLESS – CON EXIT CODE
# ================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  VALIDACIÓN DE BLENDER (HEADLESS)" -ForegroundColor Cyan
Write-Host "  STATE AUDITOR R1.3" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$blenderPath = "C:\Tools\UPBGE\upbge-0.50-windows-x64\blender.exe"
if (-not (Test-Path $blenderPath)) {
    Write-Host "❌ Blender no encontrado en: $blenderPath" -ForegroundColor Red
    Write-Host "Por favor, actualiza la ruta en el script." -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}
Write-Host "✅ Blender encontrado: $blenderPath" -ForegroundColor Green

Write-Host "Ejecutando Blender headless..." -ForegroundColor Yellow
$pythonScript = "scripts/validate_blender_headless.py"
$output = & $blenderPath --background --python $pythonScript 2>&1
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "SALIDA DE BLENDER:" -ForegroundColor Yellow
Write-Host $output
Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  ✅ VALIDACIÓN EXITOSA" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Archivo generado: builds/tests/validation.blend" -ForegroundColor Cyan
    Write-Host "Puedes abrirlo en Blender y usar:" -ForegroundColor Yellow
    Write-Host "  from character_engine.infrastructure.blender import status, diff, snapshot" -ForegroundColor Cyan
    Write-Host "  status()" -ForegroundColor Cyan
    Write-Host "  diff()" -ForegroundColor Cyan
    Write-Host "  snapshot()" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "  ❌ VALIDACIÓN FALLIDA" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "El script de validación falló con código: $exitCode" -ForegroundColor Yellow
    Write-Host "Revisa la salida de error anterior." -ForegroundColor Yellow
    exit 1
}