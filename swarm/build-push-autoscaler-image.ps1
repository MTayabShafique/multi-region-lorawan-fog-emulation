param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern(".+/.+:.+")]
    [string] $Image
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$autoscalerRoot = Join-Path $projectRoot "autoscaler"

docker build --pull --tag $Image $autoscalerRoot
if ($LASTEXITCODE -ne 0) {
    throw "Autoscaler image build failed."
}

docker push $Image
if ($LASTEXITCODE -ne 0) {
    throw "Autoscaler image push failed. Authenticate to the registry and retry."
}

Write-Host "Published fog autoscaler image: $Image"
