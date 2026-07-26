param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern(".+/.+:.+")]
    [string] $Image
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$fogRoot = Join-Path $projectRoot "fog-nodes"

docker build --pull --tag $Image $fogRoot
if ($LASTEXITCODE -ne 0) {
    throw "Fog image build failed."
}

docker push $Image
if ($LASTEXITCODE -ne 0) {
    throw "Fog image push failed. Authenticate to the registry and retry."
}

Write-Host "Published fog worker image: $Image"
