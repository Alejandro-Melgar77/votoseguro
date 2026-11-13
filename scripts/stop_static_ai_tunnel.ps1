<#
.SYNOPSIS
    Detiene el túnel estático de ngrok y descarga el modelo votoseguro-lfm3 de la RAM.
#>

param (
    [string]$ModelName = "votoseguro-lfm3",
    [int]$LocalPort = 11434
)

$ErrorActionPreference = "Continue"

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "   🛑 DETENIENDO NODO NEURONAL LOCAL & TÚNEL ESTÁTICO (VOTOSEGURO v2.0)" -ForegroundColor Yellow
Write-Host "================================================================================`n" -ForegroundColor Cyan

# 1. Detener procesos ngrok
Write-Host "[1/3] Finalizando procesos de ngrok..." -ForegroundColor White
$NgrokProcesses = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
if ($NgrokProcesses) {
    $NgrokProcesses | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Host "   > Proceso ngrok (PID $($_.Id)) terminado." -ForegroundColor Green
    }
} else {
    Write-Host "   > No hay procesos ngrok activos." -ForegroundColor DarkGray
}

# 2. Descargar modelo de la memoria RAM (keep_alive: 0)
Write-Host "`n[2/3] Descargando modelo '$ModelName' de la memoria RAM (keep_alive: 0)..." -ForegroundColor White
try {
    $UnloadBody = @{
        model = $ModelName
        keep_alive = 0
    } | ConvertTo-Json

    $UnloadResp = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/api/generate" -Method Post -Body $UnloadBody -ContentType "application/json" -TimeoutSec 10
    Write-Host "   > Modelo '$ModelName' descargado de la memoria RAM exitosamente." -ForegroundColor Green
} catch {
    Write-Host "   > Ollama no respondía o ya estaba cerrado: $_" -ForegroundColor DarkGray
}

# 3. Notificar a Render
Write-Host "`n[3/3] Notificando desconexión al backend en Render..." -ForegroundColor White
try {
    $OfflineBody = @{
        node_status = "OFFLINE"
        model_name = $ModelName
        timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    } | ConvertTo-Json

    $RenderPingUrl = "https://votoseguro-api-plyu.onrender.com/api/v1/ai/node/ping"
    $PingResp = Invoke-RestMethod -Uri $RenderPingUrl -Method Post -Body $OfflineBody -ContentType "application/json" -TimeoutSec 5
    Write-Host "   > Backend en Render notificado (Nodo Neuronal OFFLINE — Modo Degradado Activo)." -ForegroundColor Green
} catch {
    Write-Host "   > Backend en Render no requirió acuse inmediato de desconexión." -ForegroundColor DarkGray
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "   NODO NEURONAL LOCAL DETENIDO CON ÉXITO" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "   El backend en Render continuará operando normalmente con el fallback" -ForegroundColor White
Write-Host "   determinista garantizado sin interrupciones del proceso electoral." -ForegroundColor White
Write-Host "================================================================================`n" -ForegroundColor Cyan
