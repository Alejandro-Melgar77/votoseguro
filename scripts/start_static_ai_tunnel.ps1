<#
.SYNOPSIS
    Lanzador en 1 Clic del Nodo Neuronal Local y Túnel Estático HTTPS de VotoSeguro v2.
.DESCRIPTION
    1. Habilita CORS amplio (OLLAMA_ORIGINS="*") y Host (127.0.0.1:11434) para Ollama.
    2. Asegura que el modelo especializado 'votoseguro-lfm3' esté compilado y disponible.
    3. Pre-carga el modelo en memoria RAM/VRAM con keep_alive: -1 (Cero Cold-Start).
    4. Levanta el túnel estático HTTPS de ngrok resolviendo la ruta binaria real de ngrok.exe.
    5. Realiza un test de salud con cabecera 'ngrok-skip-browser-warning: true' (hasta 12 intentos).
    6. Notifica al backend en Render y Supabase que el nodo neuronal está ONLINE.
    7. Muestra el panel interactivo de telemetría y estado verificado.
#>

param (
    [string]$StaticDomain = "",
    [switch]$UseCloudflare,
    [string]$CloudflareToken = ""
)

$ErrorActionPreference = "Continue"

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "   🧠 VOTOSEGURO v2.0 — NODO NEURONAL LOCAL & TÚNEL ESTÁTICO PERMANENTE" -ForegroundColor Yellow
Write-Host "   Soberanía Cívica Criptográfica y Puente Nube (Render <-> PC Local)" -ForegroundColor Cyan
Write-Host "================================================================================`n" -ForegroundColor Cyan

# 1. Configurar variables de entorno de CORS y Host para Ollama
$env:OLLAMA_ORIGINS = "*"
$env:OLLAMA_HOST = "127.0.0.1:11434"
[Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "Process")
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "Process")

# 2. Resolver rutas del proyecto
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
if (!(Test-Path "$ProjectRoot\services\llm\Modelfile.votoseguro")) {
    $ProjectRoot = Get-Location
}

# 3. Cargar variables de entorno del archivo .env
$EnvFiles = @("$ProjectRoot\.env", "$ScriptDir\ai_tunnel.env")
$LoadedDomain = ""
foreach ($ef in $EnvFiles) {
    if (Test-Path $ef) {
        Get-Content $ef | ForEach-Object {
            $line = $_.Trim()
            if ($line -and !$line.StartsWith("#") -and $line.Contains("=")) {
                $parts = $line.Split("=", 2)
                $k = $parts[0].Trim()
                $v = $parts[1].Trim()
                if ($k -eq "NGROK_STATIC_DOMAIN" -and !$LoadedDomain) { $LoadedDomain = $v }
                if ($k -eq "LLM_MODEL_NAME" -and !$ModelName) { $ModelName = $v }
            }
        }
    }
}

if ($StaticDomain) { $LoadedDomain = $StaticDomain }
if (!$LoadedDomain) { $LoadedDomain = "repackage-remarry-reviving.ngrok-free.dev" }
if (!$ModelName) { $ModelName = "votoseguro-lfm3" }

$LocalPort = 11434
$RenderPingUrl = "https://votoseguro-api-plyu.onrender.com/api/v1/ai/node/ping"

Write-Host "[1/5] Verificando Servidor Local de IA (Ollama en puerto $LocalPort con CORS)..." -ForegroundColor White

function Test-PortOpen([string]$HostName, [int]$Port) {
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $iar = $tcpClient.BeginConnect($HostName, $Port, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne(1000, $false)
        if ($wait -and $tcpClient.Connected) {
            $tcpClient.EndConnect($iar)
            $tcpClient.Close()
            return $true
        }
        $tcpClient.Close()
        return $false
    } catch {
        return $false
    }
}

$IsOllamaRunning = Test-PortOpen -HostName "127.0.0.1" -Port $LocalPort

if (!$IsOllamaRunning) {
    Write-Host "   > Ollama no detectado en puerto $LocalPort. Iniciando 'ollama serve' en segundo plano..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    
    $Retries = 0
    while ($Retries -lt 15) {
        Start-Sleep -Seconds 1
        $Retries++
        if (Test-PortOpen -HostName "127.0.0.1" -Port $LocalPort) {
            $IsOllamaRunning = $true
            break
        }
    }
    if ($IsOllamaRunning) {
        Write-Host "   > Ollama iniciado y escuchando exitosamente en puerto $LocalPort." -ForegroundColor Green
    } else {
        Write-Host "   [ERROR] No se pudo iniciar Ollama automáticamente. Ejecute 'ollama serve' manualmente." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   > Servidor Ollama activo en 127.0.0.1:$LocalPort." -ForegroundColor Green
}

# 4. Verificar que el modelo votoseguro-lfm3 exista
Write-Host "`n[2/5] Verificando presencia del modelo '$ModelName'..." -ForegroundColor White
$ModelExists = $false
try {
    $TagsResponse = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/api/tags" -Method Get -TimeoutSec 5
    foreach ($m in $TagsResponse.models) {
        if ($m.name.StartsWith($ModelName)) {
            $ModelExists = $true
            break
        }
    }
} catch {
    Write-Host "   > Advertencia consultando tags: $_" -ForegroundColor DarkGray
}

if (!$ModelExists) {
    $Modelfile = "$ProjectRoot\services\llm\Modelfile.votoseguro"
    Write-Host "   > Modelo '$ModelName' no encontrado en Ollama. Compilando desde $Modelfile..." -ForegroundColor Yellow
    if (Test-Path $Modelfile) {
        & ollama create $ModelName -f $Modelfile
        Write-Host "   > Compilación completada." -ForegroundColor Green
    } else {
        Write-Host "   [ERROR] Modelfile no encontrado en $Modelfile" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   > Modelo '$ModelName' disponible y verificado." -ForegroundColor Green
}

# 5. Pre-carga en memoria RAM/VRAM (keep_alive: -1) para CERO Cold-Start
Write-Host "`n[3/5] Pre-cargando modelo '$ModelName' en memoria RAM (keep_alive: -1)..." -ForegroundColor White
$WarmupBody = @{
    model = $ModelName
    prompt = "ping"
    keep_alive = -1
} | ConvertTo-Json

try {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $WarmupResp = Invoke-RestMethod -Uri "http://127.0.0.1:$LocalPort/api/generate" -Method Post -Body $WarmupBody -ContentType "application/json" -TimeoutSec 30
    $sw.Stop()
    Write-Host "   > Modelo pre-cargado residente en memoria RAM. Latencia inicial: $($sw.ElapsedMilliseconds) ms." -ForegroundColor Green
} catch {
    Write-Host "   > Advertencia durante pre-carga: $_" -ForegroundColor Yellow
}

# 6. Iniciar túnel de ngrok resolviendo la ruta ejecutable real
Write-Host "`n[4/5] Levantando Túnel Estático HTTPS..." -ForegroundColor White

$TunnelUrl = "https://$LoadedDomain"

if ($UseCloudflare) {
    Write-Host "   > Utilizando Cloudflare Tunnel (-UseCloudflare activado)..." -ForegroundColor Yellow
} else {
    Write-Host "   > Dominio Estático de ngrok: $LoadedDomain" -ForegroundColor Cyan
    
    # Resolver ejecutable de ngrok (.exe)
    $NgrokBinary = ""
    $CandidatePaths = @(
        "C:\Users\Ale\AppData\Roaming\npm\node_modules\ngrok\bin\ngrok.exe",
        "$env:LOCALAPPDATA\ngrok\ngrok.exe",
        "$env:ProgramFiles\ngrok\ngrok.exe"
    )
    foreach ($cp in $CandidatePaths) {
        if (Test-Path $cp) { $NgrokBinary = $cp; break }
    }
    if (!$NgrokBinary) {
        $cmd = Get-Command "ngrok.exe" -ErrorAction SilentlyContinue
        if ($cmd) { $NgrokBinary = $cmd.Source }
    }
    if (!$NgrokBinary) {
        $cmdAny = Get-Command "ngrok" -ErrorAction SilentlyContinue
        if ($cmdAny) { $NgrokBinary = $cmdAny.Source }
    }

    # Verificar si ngrok ya está corriendo
    $NgrokRunning = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
    if (!$NgrokRunning) {
        Write-Host "   > Iniciando proceso ngrok con url=https://$LoadedDomain..." -ForegroundColor White
        $NgrokArgs = "http --url=https://$LoadedDomain $LocalPort --host-header=localhost:$LocalPort"
        
        if ($NgrokBinary -and $NgrokBinary.ToLower().EndsWith(".exe")) {
            Start-Process -FilePath $NgrokBinary -ArgumentList $NgrokArgs -WindowStyle Minimized
        } else {
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c ngrok $NgrokArgs" -WindowStyle Minimized
        }
        Start-Sleep -Seconds 3
    } else {
        Write-Host "   > Proceso ngrok ya se encuentra en ejecución." -ForegroundColor Green
    }
}

# 7. Test de Salud y Ping de Verificación al Túnel Estático (hasta 12 intentos)
Write-Host "`n[5/5] Verificando acceso público al túnel y sincronizando con Render / Supabase..." -ForegroundColor White

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$PublicHealthUrl = "$TunnelUrl/v1/models"
$Headers = @{
    "ngrok-skip-browser-warning" = "true"
    "User-Agent" = "VotoSeguro-Local-Tunnel-Verifier/2.5"
}

$TunnelVerified = $false
$TunnelLatencyMs = $null
$MaxTries = 12
$TryCount = 0
$LastErrorMsg = ""

while ($TryCount -lt $MaxTries -and !$TunnelVerified) {
    $TryCount++
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $CheckResp = Invoke-RestMethod -Uri $PublicHealthUrl -Method Get -Headers $Headers -TimeoutSec 5
        $sw.Stop()
        $TunnelLatencyMs = $sw.ElapsedMilliseconds
        $TunnelVerified = $true
        Write-Host "   > Conexión al túnel verificada: HTTP 200 OK (${TunnelLatencyMs} ms)." -ForegroundColor Green
    } catch {
        $LastErrorMsg = $_.Exception.Message
        Write-Host "   > Esperando que ngrok active el dominio (intento $TryCount/$MaxTries)..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 2
    }
}

# Si falló tras 12 intentos, diagnosticar con API local de ngrok
if (!$TunnelVerified) {
    Write-Host "   [ERROR] No se pudo verificar la activación pública de https://$LoadedDomain." -ForegroundColor Red
    if ($LastErrorMsg) {
        Write-Host "   Detalle del error: $LastErrorMsg" -ForegroundColor Yellow
    }
    try {
        $LocalNgrok = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($LocalNgrok) {
            Write-Host "   Info ngrok local (127.0.0.1:4040):" -ForegroundColor DarkGray
            $LocalNgrok.tunnels | ForEach-Object { Write-Host "     - $($_.name): $($_.public_url) -> $($_.config.addr)" -ForegroundColor DarkGray }
        }
    } catch {}
}

# 8. Sincronizar y Notificar al Backend en Render
$RenderNotified = $false
if ($TunnelVerified) {
    try {
        $PingBody = @{
            node_status = "ONLINE"
            llm_base_url = "$TunnelUrl/v1"
            model_name = $ModelName
            provider = "OLLAMA"
            tunnel_domain = $LoadedDomain
            local_latency_ms = $TunnelLatencyMs
            timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        } | ConvertTo-Json

        $PingResp = Invoke-RestMethod -Uri $RenderPingUrl -Method Post -Body $PingBody -ContentType "application/json" -TimeoutSec 10
        $RenderNotified = $true
        Write-Host "   > Backend en Render notificado exitosamente (Nodo Neuronal ONLINE sincronizado)." -ForegroundColor Green
    } catch {
        Write-Host "   > Sincronización con Render pendiente (el servicio en la nube se actualizará en la próxima consulta o arranque): $_" -ForegroundColor Yellow
    }
}

# 9. Resumen de Estado en Pantalla
Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "   ESTADO OPERATIVO DEL NODO NEURONAL LOCAL (VOTOSEGURO v2.0)" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
if ($TunnelVerified) {
    Write-Host "   Estado del Túnel:          🟢 ONLINE (Activo, Protegido y Verificado)" -ForegroundColor Green
} else {
    Write-Host "   Estado del Túnel:          🟠 OFFLINE (Falla de verificación en túnel)" -ForegroundColor Red
}
Write-Host "   URL Pública Permanente:    $TunnelUrl/v1" -ForegroundColor Yellow
Write-Host "   Modelo Residente en RAM:   $ModelName (keep_alive: -1)" -ForegroundColor White
Write-Host "   Puerto Local Mapeado:      127.0.0.1:$LocalPort (CORS: *)" -ForegroundColor White
Write-Host "   Backend de Destino:        https://votoseguro-api-plyu.onrender.com" -ForegroundColor Cyan
Write-Host "   Cabecera de Nube Obligada: ngrok-skip-browser-warning: true" -ForegroundColor DarkGray
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "   💡 Este túnel estático permite que la API en Render consulte este modelo" -ForegroundColor White
Write-Host "      local para IA-L1, IA-L2b, IA-L3 e IA-L5 con inferencia neuronal real." -ForegroundColor White
Write-Host "   🛑 Para detener el túnel y descargar el modelo de la RAM, ejecute:" -ForegroundColor White
Write-Host "      DETENER_IA_LOCAL.bat" -ForegroundColor Yellow
Write-Host "================================================================================`n" -ForegroundColor Cyan
