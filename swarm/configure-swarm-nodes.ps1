param(
    [Parameter(Mandatory = $true)]
    [string] $Node1,
    [Parameter(Mandatory = $true)]
    [string] $Node2,
    [Parameter(Mandatory = $true)]
    [string] $Node3
)

$ErrorActionPreference = "Stop"

$uniqueNodeCount = @(@($Node1, $Node2, $Node3) | Select-Object -Unique).Count
if ($uniqueNodeCount -ne 3) {
    throw "Node1, Node2, and Node3 must identify three different swarm nodes."
}

$swarmState = docker info --format '{{.Swarm.LocalNodeState}}'
if ($LASTEXITCODE -ne 0 -or $swarmState.Trim() -ne "active") {
    throw "The selected Docker context is not attached to an active swarm."
}

docker node update --label-add sensiot_emqx_slot=1 --label-add sensiot_redis_slot=1 --label-add sensiot_ingress=true $Node1
if ($LASTEXITCODE -ne 0) { throw "Could not label $Node1." }

docker node update --label-add sensiot_emqx_slot=2 --label-add sensiot_redis_slot=2 --label-add sensiot_ingress=true $Node2
if ($LASTEXITCODE -ne 0) { throw "Could not label $Node2." }

docker node update --label-add sensiot_emqx_slot=3 --label-add sensiot_redis_slot=3 $Node3
if ($LASTEXITCODE -ne 0) { throw "Could not label $Node3." }

Write-Host "Swarm node roles configured:"
Write-Host "  $Node1 -> EMQX 1, Redis 1, Sentinel 1, ingress"
Write-Host "  $Node2 -> EMQX 2, Redis 2, Sentinel 2, ingress"
Write-Host "  $Node3 -> EMQX 3, Redis 3, Sentinel 3"
