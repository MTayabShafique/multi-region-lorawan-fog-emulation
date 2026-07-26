param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern(".+/.+:.+")]
    [string] $FogImage,
    [Parameter(Mandatory = $true)]
    [ValidatePattern(".+/.+:.+")]
    [string] $AutoscalerImage,
    [string] $StackName = "sensiot-fog",
    [switch] $ValidateOnly,
    [switch] $EnableAutoscaling
)

$ErrorActionPreference = "Stop"
$swarmRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $swarmRoot
$stackFile = Join-Path $swarmRoot "fog-stack.yml"
$fogEnvFile = Join-Path $projectRoot "fog-nodes\.env"

function Read-DotEnv {
    param([string] $Path)
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if (-not $line -or $line.TrimStart().StartsWith("#")) {
            continue
        }
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            $values[$parts[0]] = $parts[1]
        }
    }
    return $values
}

function Test-DockerSecret {
    param([string] $Name)
    docker secret inspect $Name *> $null
    return $LASTEXITCODE -eq 0
}

function Add-DockerSecret {
    param(
        [string] $Name,
        [string] $Value
    )
    if (Test-DockerSecret $Name) {
        return
    }

    $tempPath = Join-Path ([System.IO.Path]::GetTempPath()) "$([Guid]::NewGuid().ToString('N')).secret"
    try {
        [System.IO.File]::WriteAllText(
            $tempPath,
            $Value,
            [System.Text.UTF8Encoding]::new($false)
        )
        docker secret create $Name $tempPath | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create Docker secret $Name."
        }
    }
    finally {
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force
        }
    }
}

function Add-DockerSecretFile {
    param(
        [string] $Name,
        [string] $Path
    )
    if (Test-DockerSecret $Name) {
        return
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing TLS file: $Path. Run generate-mqtt-certificates.ps1 first."
    }

    docker secret create $Name $Path | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create Docker secret $Name."
    }
}

function Get-MatchingNodes {
    param([string] $Label)
    $nodes = docker node ls --filter "node.label=$Label" --filter "status=ready" --format '{{.Hostname}}'
    if ($LASTEXITCODE -ne 0) {
        throw "Could not query swarm nodes."
    }
    return @($nodes | Where-Object { $_ })
}

$swarmState = docker info --format '{{.Swarm.LocalNodeState}}'
if ($LASTEXITCODE -ne 0 -or $swarmState.Trim() -ne "active") {
    throw "The selected Docker context is not attached to an active swarm."
}

$controlAvailable = docker info --format '{{.Swarm.ControlAvailable}}'
if ($controlAvailable.Trim().ToLowerInvariant() -ne "true") {
    throw "Deploy from a swarm manager Docker context."
}

$readyNodes = @(docker node ls --filter status=ready --format '{{.Hostname}}')
if ($readyNodes.Count -lt 3) {
    throw "At least three ready Linux nodes are required. Found $($readyNodes.Count)."
}

$requiredLabels = @(
    "sensiot_emqx_slot=1",
    "sensiot_emqx_slot=2",
    "sensiot_emqx_slot=3",
    "sensiot_redis_slot=1",
    "sensiot_redis_slot=2",
    "sensiot_redis_slot=3"
)
foreach ($label in $requiredLabels) {
    if ((Get-MatchingNodes $label).Count -ne 1) {
        throw "Exactly one ready node must have label '$label'."
    }
}

$ingressNodes = Get-MatchingNodes "sensiot_ingress=true"
if ($ingressNodes.Count -lt 2) {
    throw "At least two ready nodes must have label 'sensiot_ingress=true'."
}

if (-not (Test-Path -LiteralPath $fogEnvFile)) {
    throw "Missing fog-nodes/.env. Run setup-security.ps1 first."
}
$fogSecrets = Read-DotEnv $fogEnvFile
$secretMap = [ordered]@{
    sensiot_fog_emqx_cookie = "FOG_EMQX_COOKIE"
    sensiot_fog_eu868_mqtt_password = "FOG_EU868_MQTT_PASSWORD"
    sensiot_fog_us915_mqtt_password = "FOG_US915_MQTT_PASSWORD"
    sensiot_fog_in865_mqtt_password = "FOG_IN865_MQTT_PASSWORD"
    sensiot_fog_ru864_mqtt_password = "FOG_RU864_MQTT_PASSWORD"
    sensiot_fog_redis_password = "FOG_REDIS_PASSWORD"
}
foreach ($entry in $secretMap.GetEnumerator()) {
    $value = $fogSecrets[$entry.Value]
    if (-not $value) {
        throw "Missing $($entry.Value) in fog-nodes/.env. Run setup-security.ps1."
    }
}

$env:FOG_IMAGE = $FogImage
$env:AUTOSCALER_IMAGE = $AutoscalerImage
$env:STACK_NAME = $StackName
$env:AUTOSCALER_DRY_RUN = if ($EnableAutoscaling) { "false" } else { "true" }
$tlsFiles = [ordered]@{
    mqtt_ca = Join-Path $projectRoot "tls\generated\ca\ca.crt"
    server_cert = Join-Path $projectRoot "tls\generated\fog-server\fog-server.crt"
    server_key = Join-Path $projectRoot "tls\generated\fog-server\fog-server.key"
    workers_cert = Join-Path $projectRoot "tls\generated\fog-workers\fog-workers.crt"
    workers_key = Join-Path $projectRoot "tls\generated\fog-workers\fog-workers.key"
}
foreach ($path in $tlsFiles.Values) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing TLS file: $path. Run generate-mqtt-certificates.ps1 first."
    }
}
$tlsFingerprint = (
    $tlsFiles.Values |
        ForEach-Object { (Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash }
) -join ""
$env:FOG_TLS_VERSION = $tlsFingerprint.Substring(0, 16).ToLowerInvariant()
$configFiles = @(
    (Join-Path $projectRoot "fog-nodes\config\emqx\emqx.conf"),
    (Join-Path $projectRoot "fog-nodes\config\emqx\acl.conf"),
    (Join-Path $swarmRoot "config\fog-haproxy.cfg"),
    (Join-Path $projectRoot "fog-nodes\config\redis\redis-entrypoint.sh"),
    (Join-Path $projectRoot "fog-nodes\config\redis\sentinel-entrypoint.sh")
)
$configFingerprint = (
    $configFiles |
        ForEach-Object { (Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash } |
        ForEach-Object { $_.Substring(0, 12) }
) -join "-"
$env:FOG_CONFIG_VERSION = $configFingerprint
docker stack config --compose-file $stackFile | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Swarm stack validation failed."
}

if ($ValidateOnly) {
    Write-Host "Swarm preflight and stack rendering passed. No resources were changed."
    return
}

foreach ($entry in $secretMap.GetEnumerator()) {
    $value = $fogSecrets[$entry.Value]
    Add-DockerSecret $entry.Key $value
}

$tlsSecretMap = [ordered]@{
    "sensiot_fog_mqtt_ca_$($env:FOG_TLS_VERSION)" = $tlsFiles.mqtt_ca
    "sensiot_fog_server_mqtt_cert_$($env:FOG_TLS_VERSION)" = $tlsFiles.server_cert
    "sensiot_fog_server_mqtt_key_$($env:FOG_TLS_VERSION)" = $tlsFiles.server_key
    "sensiot_fog_workers_mqtt_cert_$($env:FOG_TLS_VERSION)" = $tlsFiles.workers_cert
    "sensiot_fog_workers_mqtt_key_$($env:FOG_TLS_VERSION)" = $tlsFiles.workers_key
}
foreach ($entry in $tlsSecretMap.GetEnumerator()) {
    Add-DockerSecretFile $entry.Key $entry.Value
}

docker network inspect sensiot-edge *> $null
if ($LASTEXITCODE -ne 0) {
    docker network create --driver overlay --attachable --opt encrypted sensiot-edge | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the sensiot-edge overlay network."
    }
}

docker stack deploy --with-registry-auth --prune --resolve-image always --compose-file $stackFile $StackName
if ($LASTEXITCODE -ne 0) {
    throw "Swarm stack deployment failed."
}

Write-Host "Stack '$StackName' submitted."
Write-Host "  Fog image: $FogImage"
Write-Host "  Autoscaler image: $AutoscalerImage"
Write-Host "  Autoscaling enabled: $($EnableAutoscaling.IsPresent)"
Write-Host "Track convergence with: docker stack services $StackName"
