param(
    [string] $DashboardUsername = "admin",
    [string] $InitialDashboardPassword = "public",
    [string] $FogBaseUrl = "http://localhost:18084/api/v5",
    [string] $ChirpStackBaseUrl = "http://localhost:18083/api/v5",
    [switch] $AllowInsecureRemoteHttp
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Assert-SecureManagementUrl {
    param([string] $BaseUrl)
    $uri = [Uri]$BaseUrl
    $loopbackHosts = @("localhost", "127.0.0.1", "::1")
    if (
        $uri.Scheme -ne "https" -and
        $uri.Host -notin $loopbackHosts -and
        -not $AllowInsecureRemoteHttp
    ) {
        throw "Refusing to send credentials over remote HTTP: $BaseUrl. Use HTTPS or an SSH tunnel to localhost."
    }
}

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

function Wait-EmqxApi {
    param([string] $BaseUrl)
    $deadline = (Get-Date).AddSeconds(90)
    do {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/status" -TimeoutSec 3 | Out-Null
            return
        }
        catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)
    throw "EMQX API did not become ready at $BaseUrl."
}

function Connect-EmqxApi {
    param(
        [string] $BaseUrl,
        [string] $Username,
        [string[]] $Passwords
    )
    foreach ($password in $Passwords) {
        if (-not $password) {
            continue
        }
        try {
            $body = @{ username = $Username; password = $password } | ConvertTo-Json
            $login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/login" -ContentType "application/json" -Body $body
            return @{ Authorization = "Bearer $($login.token)" }
        }
        catch {
            continue
        }
    }
    throw "Could not authenticate to $BaseUrl with the configured dashboard account."
}

function Set-MqttUser {
    param(
        [string] $BaseUrl,
        [hashtable] $Headers,
        [string] $Username,
        [string] $Password
    )
    $authenticator = [Uri]::EscapeDataString("password_based:built_in_database")
    $user = [Uri]::EscapeDataString($Username)
    try {
        Invoke-RestMethod -Method Delete -Uri "$BaseUrl/authentication/$authenticator/users/$user" -Headers $Headers | Out-Null
    }
    catch {
        # The user does not exist yet.
    }
    $createBody = @{ user_id = $Username; password = $Password; is_superuser = $false } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "$BaseUrl/authentication/$authenticator/users" -Headers $Headers -ContentType "application/json" -Body $createBody | Out-Null
}

function Set-DashboardPassword {
    param(
        [string] $BaseUrl,
        [hashtable] $Headers,
        [string] $Username,
        [string] $OldPassword,
        [string] $NewPassword
    )
    $user = [Uri]::EscapeDataString($Username)
    $body = @{ old_pwd = $OldPassword; new_pwd = $NewPassword } | ConvertTo-Json
    try {
        Invoke-RestMethod -Method Post -Uri "$BaseUrl/users/$user/change_pwd" -Headers $Headers -ContentType "application/json" -Body $body | Out-Null
        return
    }
    catch {
        # A repeated run already uses the generated password. Verify that state
        # instead of suppressing an unrelated API or credential failure.
        Connect-EmqxApi $BaseUrl $Username @($NewPassword) | Out-Null
    }
}

$chirpstack = Read-DotEnv (Join-Path $projectRoot "chirpstack-docker\.env")
$fog = Read-DotEnv (Join-Path $projectRoot "fog-nodes\.env")
$sensiot = Read-DotEnv (Join-Path $projectRoot "The-SENSIOT-Framework\.env")

$fogUrl = $FogBaseUrl.TrimEnd("/")
$chirpstackUrl = $ChirpStackBaseUrl.TrimEnd("/")
Assert-SecureManagementUrl $fogUrl
Assert-SecureManagementUrl $chirpstackUrl
Wait-EmqxApi $fogUrl
Wait-EmqxApi $chirpstackUrl

$fogHeaders = Connect-EmqxApi $fogUrl $DashboardUsername @(
    $fog["FOG_EMQX_DASHBOARD_PASSWORD"],
    $InitialDashboardPassword
)
$chirpstackHeaders = Connect-EmqxApi $chirpstackUrl $DashboardUsername @(
    $chirpstack["CHIRPSTACK_EMQX_DASHBOARD_PASSWORD"],
    $InitialDashboardPassword
)

Set-MqttUser $fogUrl $fogHeaders "chirpstack-bridge" $fog["CHIRPSTACK_BRIDGE_MQTT_PASSWORD"]
Set-MqttUser $fogUrl $fogHeaders "fog-eu868" $fog["FOG_EU868_MQTT_PASSWORD"]
Set-MqttUser $fogUrl $fogHeaders "fog-us915" $fog["FOG_US915_MQTT_PASSWORD"]
Set-MqttUser $fogUrl $fogHeaders "fog-in865" $fog["FOG_IN865_MQTT_PASSWORD"]
Set-MqttUser $fogUrl $fogHeaders "fog-ru864" $fog["FOG_RU864_MQTT_PASSWORD"]
Set-MqttUser $fogUrl $fogHeaders "sensiot" $sensiot["SENSIOT_MQTT_PASSWORD"]

Set-MqttUser $chirpstackUrl $chirpstackHeaders "chirpstack-core" $chirpstack["CHIRPSTACK_MQTT_PASSWORD"]
Set-MqttUser $chirpstackUrl $chirpstackHeaders "gateway-bridge" $chirpstack["GATEWAY_MQTT_PASSWORD"]
Set-MqttUser $chirpstackUrl $chirpstackHeaders "automated-metrics" $chirpstack["METRICS_MQTT_PASSWORD"]

$bridgeBody = @{
    type = "mqtt"
    name = "gateway-bridge"
    enable = $true
    server = "fog-haproxy:8883"
    username = "chirpstack-bridge"
    password = $fog["CHIRPSTACK_BRIDGE_MQTT_PASSWORD"]
    proto_ver = "v4"
    clean_start = $true
    keepalive = "300s"
    retry_interval = "15s"
    mode = "cluster_shareload"
    egress = @{
        local = @{ topic = "application/+/device/+/event/up" }
        remote = @{
            topic = 'region/${payload.regionConfigId}/${topic}'
            qos = 1
            retain = $false
            payload = '${payload}'
        }
    }
    ssl = @{
        enable = $true
        verify = "verify_peer"
        server_name_indication = "fog-haproxy"
        cacertfile = "/opt/emqx/etc/certs/ca.crt"
        certfile = "/opt/emqx/etc/certs/bridge-client.crt"
        keyfile = "/opt/emqx/etc/certs/bridge-client.key"
        versions = @("tlsv1.3", "tlsv1.2")
    }
} | ConvertTo-Json -Depth 8

try {
    Invoke-RestMethod -Method Put -Uri "$chirpstackUrl/bridges/mqtt:gateway-bridge" -Headers $chirpstackHeaders -ContentType "application/json" -Body $bridgeBody | Out-Null
}
catch {
    Invoke-RestMethod -Method Post -Uri "$chirpstackUrl/bridges" -Headers $chirpstackHeaders -ContentType "application/json" -Body $bridgeBody | Out-Null
}

Set-DashboardPassword $fogUrl $fogHeaders $DashboardUsername $InitialDashboardPassword $fog["FOG_EMQX_DASHBOARD_PASSWORD"]
Set-DashboardPassword $chirpstackUrl $chirpstackHeaders $DashboardUsername $InitialDashboardPassword $chirpstack["CHIRPSTACK_EMQX_DASHBOARD_PASSWORD"]

Write-Host "EMQX users, ACL-backed bridge, and dashboard passwords are configured."
