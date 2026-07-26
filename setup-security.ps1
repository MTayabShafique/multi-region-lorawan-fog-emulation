param(
    [string] $PostgresPassword,
    [string] $LorawanInfluxUsername = "root",
    [string] $LorawanInfluxPassword,
    [string] $LorawanInfluxToken,
    [string] $SensiotInfluxUsername = "root",
    [string] $SensiotInfluxPassword,
    [string] $SensiotInfluxToken
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function New-SecuritySecret {
    param([int] $ByteLength = 36)
    $bytes = New-Object byte[] $ByteLength
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function New-ClusterCookie {
    param([int] $ByteLength = 32)
    $bytes = New-Object byte[] $ByteLength
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

function Write-Utf8File {
    param([string] $Path, [string[]] $Lines)
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    [System.IO.File]::WriteAllLines($Path, $Lines, [System.Text.UTF8Encoding]::new($false))
}

function Get-ExistingDotEnvValue {
    param(
        [string] $Path,
        [string] $Key
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -like "$Key=*" } | Select-Object -First 1
    if ($line) {
        return ($line -split "=", 2)[1]
    }
    return $null
}

$chirpstackEnvPath = Join-Path $projectRoot "chirpstack-docker\.env"
$fogEnvPath = Join-Path $projectRoot "fog-nodes\.env"
$sensiotEnvPath = Join-Path $projectRoot "The-SENSIOT-Framework\.env"
$visualizationEnvPath = Join-Path $projectRoot "Visualization\.env"
if (-not $PostgresPassword) { $PostgresPassword = Get-ExistingDotEnvValue $chirpstackEnvPath "POSTGRES_PASSWORD" }
if (-not $LorawanInfluxPassword) { $LorawanInfluxPassword = Get-ExistingDotEnvValue $chirpstackEnvPath "LORAWAN_INFLUX_PASSWORD" }
if (-not $LorawanInfluxToken) { $LorawanInfluxToken = Get-ExistingDotEnvValue $chirpstackEnvPath "LORAWAN_INFLUX_TOKEN" }
if (-not $SensiotInfluxPassword) { $SensiotInfluxPassword = Get-ExistingDotEnvValue $sensiotEnvPath "SENSIOT_INFLUX_PASSWORD" }
if (-not $SensiotInfluxToken) { $SensiotInfluxToken = Get-ExistingDotEnvValue $sensiotEnvPath "SENSIOT_INFLUX_TOKEN" }

if (-not $PostgresPassword) { $PostgresPassword = New-SecuritySecret }
if (-not $LorawanInfluxPassword) { $LorawanInfluxPassword = New-SecuritySecret }
if (-not $LorawanInfluxToken) { $LorawanInfluxToken = New-SecuritySecret }
if (-not $SensiotInfluxPassword) { $SensiotInfluxPassword = New-SecuritySecret }
if (-not $SensiotInfluxToken) { $SensiotInfluxToken = New-SecuritySecret }

$chirpstackApiSecret = Get-ExistingDotEnvValue $chirpstackEnvPath "CHIRPSTACK_API_SECRET"
$chirpstackCookie = Get-ExistingDotEnvValue $chirpstackEnvPath "CHIRPSTACK_EMQX_COOKIE"
$fogCookie = Get-ExistingDotEnvValue $fogEnvPath "FOG_EMQX_COOKIE"
$chirpstackMqttPassword = Get-ExistingDotEnvValue $chirpstackEnvPath "CHIRPSTACK_MQTT_PASSWORD"
$gatewayMqttPassword = Get-ExistingDotEnvValue $chirpstackEnvPath "GATEWAY_MQTT_PASSWORD"
$metricsMqttPassword = Get-ExistingDotEnvValue $chirpstackEnvPath "METRICS_MQTT_PASSWORD"
$bridgeMqttPassword = Get-ExistingDotEnvValue $fogEnvPath "CHIRPSTACK_BRIDGE_MQTT_PASSWORD"
$fogEu868Password = Get-ExistingDotEnvValue $fogEnvPath "FOG_EU868_MQTT_PASSWORD"
$fogUs915Password = Get-ExistingDotEnvValue $fogEnvPath "FOG_US915_MQTT_PASSWORD"
$fogIn865Password = Get-ExistingDotEnvValue $fogEnvPath "FOG_IN865_MQTT_PASSWORD"
$fogRu864Password = Get-ExistingDotEnvValue $fogEnvPath "FOG_RU864_MQTT_PASSWORD"
$fogRedisPassword = Get-ExistingDotEnvValue $fogEnvPath "FOG_REDIS_PASSWORD"
$sensiotMqttPassword = Get-ExistingDotEnvValue $sensiotEnvPath "SENSIOT_MQTT_PASSWORD"
$sensiotWebApiKey = Get-ExistingDotEnvValue $sensiotEnvPath "SENSIOT_WEB_API_KEY"
$grafanaPassword = Get-ExistingDotEnvValue $visualizationEnvPath "GRAFANA_ADMIN_PASSWORD"
$chirpstackDashboardPassword = Get-ExistingDotEnvValue $chirpstackEnvPath "CHIRPSTACK_EMQX_DASHBOARD_PASSWORD"
$fogDashboardPassword = Get-ExistingDotEnvValue $fogEnvPath "FOG_EMQX_DASHBOARD_PASSWORD"
if (-not $grafanaPassword) { $grafanaPassword = New-SecuritySecret }
if (-not $chirpstackDashboardPassword) { $chirpstackDashboardPassword = New-SecuritySecret }
if (-not $fogDashboardPassword) { $fogDashboardPassword = New-SecuritySecret }
if (-not $chirpstackApiSecret) { $chirpstackApiSecret = New-SecuritySecret }
if (-not $chirpstackCookie) { $chirpstackCookie = New-ClusterCookie }
if (-not $fogCookie) { $fogCookie = New-ClusterCookie }
if (-not $chirpstackMqttPassword) { $chirpstackMqttPassword = New-SecuritySecret }
if (-not $gatewayMqttPassword) { $gatewayMqttPassword = New-SecuritySecret }
if (-not $metricsMqttPassword) { $metricsMqttPassword = New-SecuritySecret }
if (-not $bridgeMqttPassword) { $bridgeMqttPassword = New-SecuritySecret }
if (-not $fogEu868Password) { $fogEu868Password = New-SecuritySecret }
if (-not $fogUs915Password) { $fogUs915Password = New-SecuritySecret }
if (-not $fogIn865Password) { $fogIn865Password = New-SecuritySecret }
if (-not $fogRu864Password) { $fogRu864Password = New-SecuritySecret }
if (-not $fogRedisPassword) { $fogRedisPassword = New-SecuritySecret }
if (-not $sensiotMqttPassword) { $sensiotMqttPassword = New-SecuritySecret }
if (-not $sensiotWebApiKey) { $sensiotWebApiKey = New-SecuritySecret }

Write-Utf8File (Join-Path $projectRoot "chirpstack-docker\.env") @(
    "POSTGRES_PASSWORD=$PostgresPassword",
    "CHIRPSTACK_API_SECRET=$chirpstackApiSecret",
    "CHIRPSTACK_EMQX_COOKIE=$chirpstackCookie",
    "CHIRPSTACK_EMQX_DASHBOARD_PASSWORD=$chirpstackDashboardPassword",
    "CHIRPSTACK_MQTT_PASSWORD=$chirpstackMqttPassword",
    "GATEWAY_MQTT_PASSWORD=$gatewayMqttPassword",
    "METRICS_MQTT_PASSWORD=$metricsMqttPassword",
    "LORAWAN_INFLUX_USERNAME=$LorawanInfluxUsername",
    "LORAWAN_INFLUX_PASSWORD=$LorawanInfluxPassword",
    "LORAWAN_INFLUX_TOKEN=$LorawanInfluxToken"
)

Write-Utf8File (Join-Path $projectRoot "fog-nodes\.env") @(
    "FOG_EMQX_COOKIE=$fogCookie",
    "FOG_EMQX_DASHBOARD_PASSWORD=$fogDashboardPassword",
    "FOG_EU868_MQTT_PASSWORD=$fogEu868Password",
    "FOG_US915_MQTT_PASSWORD=$fogUs915Password",
    "FOG_IN865_MQTT_PASSWORD=$fogIn865Password",
    "FOG_RU864_MQTT_PASSWORD=$fogRu864Password",
    "CHIRPSTACK_BRIDGE_MQTT_PASSWORD=$bridgeMqttPassword",
    "FOG_REDIS_PASSWORD=$fogRedisPassword"
)

Write-Utf8File (Join-Path $projectRoot "The-SENSIOT-Framework\.env") @(
    "SENSIOT_MQTT_PASSWORD=$sensiotMqttPassword",
    "SENSIOT_WEB_API_KEY=$sensiotWebApiKey",
    "SENSIOT_INFLUX_USERNAME=$SensiotInfluxUsername",
    "SENSIOT_INFLUX_PASSWORD=$SensiotInfluxPassword",
    "SENSIOT_INFLUX_TOKEN=$SensiotInfluxToken"
)

Write-Utf8File (Join-Path $projectRoot "Visualization\.env") @(
    "GRAFANA_ADMIN_PASSWORD=$grafanaPassword",
    "LORAWAN_INFLUX_TOKEN=$LorawanInfluxToken",
    "SENSIOT_INFLUX_TOKEN=$SensiotInfluxToken"
)

Write-Host "Security files generated. Values were not printed."
Write-Host "Start the broker containers, then run apply-security.ps1."
