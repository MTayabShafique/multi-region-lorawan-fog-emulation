param(
    [int] $CertificateDays = 397,
    [int] $CaDays = 3650,
    [switch] $RotateLeaves
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputRoot = Join-Path $projectRoot "tls\generated"
$caDirectory = Join-Path $outputRoot "ca"
$caKey = Join-Path $caDirectory "ca.key"
$caCertificate = Join-Path $caDirectory "ca.crt"

if (-not (Get-Command openssl -ErrorAction SilentlyContinue)) {
    throw "OpenSSL is required. Install it and ensure 'openssl' is available on PATH."
}

function Invoke-OpenSsl {
    param([string[]] $OpenSslArguments)
    & openssl @OpenSslArguments
    if ($LASTEXITCODE -ne 0) {
        throw "OpenSSL failed: openssl $($OpenSslArguments -join ' ')"
    }
}

function Write-AsciiFile {
    param([string] $Path, [string[]] $Lines)
    [System.IO.File]::WriteAllLines($Path, $Lines, [System.Text.Encoding]::ASCII)
}

function New-LeafCertificate {
    param(
        [string] $Name,
        [ValidateSet("server", "client")]
        [string] $Purpose,
        [string[]] $DnsNames = @()
    )

    $directory = Join-Path $outputRoot $Name
    $key = Join-Path $directory "$Name.key"
    $csr = Join-Path $directory "$Name.csr"
    $certificate = Join-Path $directory "$Name.crt"
    $extensionFile = Join-Path $directory "$Name.ext"

    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    if ((Test-Path -LiteralPath $certificate) -and -not $RotateLeaves) {
        Write-Host "Keeping existing certificate: $certificate"
        return
    }

    $extendedUsage = if ($Purpose -eq "server") { "serverAuth" } else { "clientAuth" }
    $extensions = @(
        "basicConstraints=critical,CA:FALSE",
        "keyUsage=critical,digitalSignature,keyEncipherment",
        "extendedKeyUsage=$extendedUsage",
        "subjectKeyIdentifier=hash",
        "authorityKeyIdentifier=keyid,issuer"
    )
    if ($DnsNames.Count -gt 0) {
        $sanValues = 0..($DnsNames.Count - 1) | ForEach-Object { "DNS.$($_ + 1)=$($DnsNames[$_])" }
        $extensions += "subjectAltName=@alt_names"
        $extensions += "[alt_names]"
        $extensions += $sanValues
    }
    Write-AsciiFile $extensionFile $extensions

    Invoke-OpenSsl -OpenSslArguments @("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", $key)
    Invoke-OpenSsl -OpenSslArguments @(
        "req", "-new", "-sha256", "-key", $key,
        "-subj", "/O=SensIoT/OU=MQTT/CN=$Name", "-out", $csr
    )
    Invoke-OpenSsl -OpenSslArguments @(
        "x509", "-req", "-sha256", "-in", $csr,
        "-CA", $caCertificate, "-CAkey", $caKey,
        "-CAserial", (Join-Path $caDirectory "ca.srl"), "-CAcreateserial",
        "-days", "$CertificateDays", "-extfile", $extensionFile, "-out", $certificate
    )

    Remove-Item -LiteralPath $csr, $extensionFile -Force
    Invoke-OpenSsl -OpenSslArguments @("verify", "-CAfile", $caCertificate, $certificate)
}

New-Item -ItemType Directory -Force -Path $caDirectory | Out-Null
if ((Test-Path -LiteralPath $caKey) -or (Test-Path -LiteralPath $caCertificate)) {
    if (-not ((Test-Path -LiteralPath $caKey) -and (Test-Path -LiteralPath $caCertificate))) {
        throw "The CA is incomplete. Restore both tls/generated/ca/ca.key and ca.crt before continuing."
    }
    Write-Host "Keeping existing MQTT CA. CA replacement is intentionally not automatic."
}
else {
    Invoke-OpenSsl -OpenSslArguments @("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", $caKey)
    Invoke-OpenSsl -OpenSslArguments @(
        "req", "-x509", "-new", "-sha256", "-key", $caKey,
        "-days", "$CaDays", "-subj", "/O=SensIoT/OU=MQTT/CN=SensIoT MQTT Root CA",
        "-out", $caCertificate
    )
    Write-Host "Created MQTT CA: $caCertificate"
}

New-LeafCertificate -Name "chirpstack-server" -Purpose server -DnsNames @(
    "chirpstack-haproxy", "emqx1", "emqx2", "emqx3", "localhost"
)
New-LeafCertificate -Name "fog-server" -Purpose server -DnsNames @(
    "fog-haproxy", "node1.emqx.io", "node2.emqx.io", "node3.emqx.io",
    "fog-emqx1", "fog-emqx2", "fog-emqx3", "localhost"
)

@(
    "chirpstack-core",
    "gateway-bridge",
    "automated-metrics",
    "chirpstack-bridge",
    "fog-workers",
    "sensiot"
) | ForEach-Object {
    New-LeafCertificate -Name $_ -Purpose client
}

Write-Host "MQTT certificates are ready under $outputRoot."
Write-Host "Keep ca.key offline and never copy it into a container or Docker secret."
