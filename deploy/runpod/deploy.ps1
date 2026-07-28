<#
.SYNOPSIS
    Deploy one-liner para CASEI RunPod.
.DESCRIPTION
    Build, tag, push y (opcionalmente) actualiza el pod en RunPod via API.
.EXAMPLE
    .\deploy\runpod\deploy.ps1
    .\deploy\runpod\deploy.ps1 -SkipPush
    .\deploy\runpod\deploy.ps1 -Tag "hotfix-01"
#>
[CmdletBinding()]
param(
    [string]$Tag,
    [string]$Registry = "develazquez01/casei-runpod",
    [switch]$SkipPush,
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# --- Helpers ---
function Write-Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "   OK: $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "   FAIL: $msg" -ForegroundColor Red; exit 1 }

# --- 1. Verificar Docker ---
Write-Step "Verificando Docker Desktop"
try {
    docker info *>$null
    Write-Ok "Docker esta corriendo"
} catch {
    Write-Fail "Docker Desktop no esta corriendo. Abrelo y vuelve a intentar."
}

# --- 2. Generar tag ---
if (-not $Tag) {
    $date = Get-Date -Format "yyyyMMdd"
    $existing = docker images --format "{{.Tag}}" $Registry 2>$null |
        Where-Object { $_ -match "^worker-$date-(\d+)$" } |
        ForEach-Object { [int]($_ -replace "worker-$date-", "") } |
        Sort-Object -Descending |
        Select-Object -First 1
    $seq = if ($existing) { $existing + 1 } else { 1 }
    $Tag = "worker-$date-{0:D2}" -f $seq
}
$LocalImage = "casei-runpod-worker:$Tag"
$RemoteImage = "${Registry}:$Tag"

Write-Step "Tag: $Tag"
Write-Host "   Local:  $LocalImage"
Write-Host "   Remote: $RemoteImage"

# --- 3. Build ---
Write-Step "Construyendo imagen"
$buildStart = Get-Date
docker build -f deploy/runpod/Dockerfile -t $LocalImage .
if ($LASTEXITCODE -ne 0) { Write-Fail "docker build fallo" }
$buildTime = [math]::Round(((Get-Date) - $buildStart).TotalSeconds, 1)
Write-Ok "Build completado en ${buildTime}s"

# --- 4. Validar bundle ---
if (-not $SkipValidation) {
    Write-Step "Validando bundle ML dentro de la imagen"
    $version = docker run --rm `
        --entrypoint python3 `
        -e CASEI_STRICT_BUNDLE_CHECKSUMS=true `
        $LocalImage `
        -c "from app.services.model_persistence_service import load_persisted_model_bundle; print(load_persisted_model_bundle()['manifest']['model_version'])"
    if ($LASTEXITCODE -ne 0) { Write-Fail "Validacion del bundle fallo" }
    Write-Ok "Bundle valido: $version"
}

# --- 5. Tag + Push ---
if (-not $SkipPush) {
    Write-Step "Subiendo imagen a Docker Hub"
    docker tag $LocalImage $RemoteImage
    docker push $RemoteImage
    if ($LASTEXITCODE -ne 0) { Write-Fail "docker push fallo" }
    Write-Ok "Imagen publicada: $RemoteImage"

    # --- 6. Actualizar RunPod via API (si hay API key) ---
    $RunpodApiKey = $env:RUNPOD_API_KEY
    $RunpodPodId = $env:RUNPOD_POD_ID
    if ($RunpodApiKey -and $RunpodPodId) {
        Write-Step "Actualizando pod en RunPod"
        $body = @{
            query = "mutation { podEditJob(input: {podId: `"$RunpodPodId`", imageName: `"$RemoteImage`"}) { id imageName } }"
        } | ConvertTo-Json

        $response = Invoke-RestMethod `
            -Uri "https://api.runpod.io/graphql?api_key=$RunpodApiKey" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body

        if ($response.data.podEditJob.id) {
            Write-Ok "Pod $RunpodPodId actualizado con imagen $RemoteImage"
            Write-Host "   RunPod reiniciara el pod automaticamente." -ForegroundColor Yellow
        } else {
            Write-Host "   WARN: No se pudo actualizar el pod. Hazlo manual en runpod.io" -ForegroundColor Yellow
            Write-Host "   Imagen: $RemoteImage"
        }
    } else {
        Write-Host ""
        Write-Host "   Para auto-actualizar el pod, configura:" -ForegroundColor Yellow
        Write-Host '   $env:RUNPOD_API_KEY = "tu-api-key"'
        Write-Host '   $env:RUNPOD_POD_ID  = "tu-pod-id"'
        Write-Host ""
        Write-Host "   Mientras tanto, actualiza manualmente en runpod.io:" -ForegroundColor Yellow
        Write-Host "   Imagen: $RemoteImage" -ForegroundColor White
    }
} else {
    Write-Ok "Push omitido (-SkipPush)"
}

# --- Resumen ---
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Deploy completado: $RemoteImage" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
