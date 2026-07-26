param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("eu868", "us915_0", "in865", "ru864")]
    [string] $Region,

    [string] $SourceDir = "LWN-Simulator",

    [switch] $Build
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourcePath = Join-Path $root $SourceDir
$configPath = Join-Path $root "configs\$Region.json"
$runtimePath = Join-Path $root "runtime\$Region"
$binaryName = if ($IsWindows -or $env:OS -eq "Windows_NT") { "lwnsimulator.exe" } else { "lwnsimulator" }
$sourceBinary = Join-Path $sourcePath "bin\$binaryName"

if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Simulator source directory not found: $sourcePath"
}

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Region config not found: $configPath"
}

if ($Build -or -not (Test-Path -LiteralPath $sourceBinary)) {
    if (-not (Get-Command make -ErrorAction SilentlyContinue)) {
        throw @"
The LWN Simulator build requires 'make', but it was not found on PATH.

Install GnuMake for Windows, restart PowerShell, then rerun:
  winget install GnuWin32.Make
  .\run-lwn-simulator.ps1 -Region $Region -Build

If the simulator binary already exists at:
  $sourceBinary
you can omit -Build.
"@
    }

    Push-Location $sourcePath
    try {
        make build
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path -LiteralPath $sourceBinary)) {
    throw "Simulator binary not found after build: $sourceBinary"
}

New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null
Copy-Item -LiteralPath $configPath -Destination (Join-Path $runtimePath "config.json") -Force

Write-Host "Starting LWN Simulator for $Region from $sourceBinary"
Push-Location $runtimePath
try {
    & $sourceBinary
}
finally {
    Pop-Location
}
