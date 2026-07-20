# Pack backend + frontend dist + deploy scripts for SCP to ECS
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$OutDir = Join-Path $Root "deploy\release"
$Staging = Join-Path $OutDir "AiGeovis"
Remove-Item -LiteralPath $OutDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $Staging | Out-Null

# Backend (exclude heavy/local caches)
$BackendSrc = Join-Path $Root "AiGeovis_backend"
$BackendDst = Join-Path $Staging "AiGeovis_backend"
robocopy $BackendSrc $BackendDst /E /XD __pycache__ .git .venv venv node_modules `
  /XF affiliation_cache.db *.pyc /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null

# Frontend dist
$DistSrc = Join-Path $Root "AiGeovis_frontend\dist"
if (-not (Test-Path $DistSrc)) { throw "dist missing; run npm run build first" }
$DistDst = Join-Path $Staging "AiGeovis_frontend\dist"
New-Item -ItemType Directory -Force -Path (Split-Path $DistDst) | Out-Null
robocopy $DistSrc $DistDst /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null

# Deploy scripts
$DeployDst = Join-Path $Staging "deploy"
New-Item -ItemType Directory -Force -Path $DeployDst | Out-Null
Copy-Item (Join-Path $PSScriptRoot "nginx-ai4safe.conf") $DeployDst
Copy-Item (Join-Path $PSScriptRoot "setup-server.sh") $DeployDst
Copy-Item (Join-Path $PSScriptRoot "README.md") $DeployDst

$Tar = Join-Path $OutDir "aigeovis-ai4safe.tgz"
if (Test-Path $Tar) { Remove-Item $Tar -Force }
Push-Location $OutDir
tar -czf aigeovis-ai4safe.tgz AiGeovis
Pop-Location
Get-Item $Tar | Format-List FullName, Length
Write-Output "OK: $Tar"
