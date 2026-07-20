# Usage (interactive password prompt):
#   .\deploy\upload-and-deploy.ps1 -User root -HostIp 8.159.143.118
# Or with key:
#   .\deploy\upload-and-deploy.ps1 -User root -HostIp 8.159.143.118 -IdentityFile C:\path\to\id_rsa
param(
  [string]$HostIp = "8.159.143.118",
  [string]$User = "root",
  [string]$IdentityFile = "",
  [string]$RemoteDir = "/opt"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$PackScript = Join-Path $PSScriptRoot "pack-release.ps1"
& $PackScript
$Tar = Join-Path $Root "deploy\release\aigeovis-ai4safe.tgz"
if (-not (Test-Path $Tar)) { throw "tarball missing" }

$sshTarget = "$User@$HostIp"
$sshOpts = @("-o", "StrictHostKeyChecking=accept-new")
if ($IdentityFile) { $sshOpts += @("-i", $IdentityFile) }

Write-Output "Uploading $Tar -> ${sshTarget}:${RemoteDir}/"
scp @sshOpts $Tar "${sshTarget}:${RemoteDir}/aigeovis-ai4safe.tgz"

$remote = @"
set -e
cd $RemoteDir
rm -rf AiGeovis
tar -xzf aigeovis-ai4safe.tgz
chmod +x AiGeovis/deploy/setup-server.sh
bash AiGeovis/deploy/setup-server.sh
"@
Write-Output "Running remote setup..."
ssh @sshOpts $sshTarget $remote
Write-Output "Done. Check http://$HostIp/ and https://ai4safe.cn/ (after DNS A record)."
