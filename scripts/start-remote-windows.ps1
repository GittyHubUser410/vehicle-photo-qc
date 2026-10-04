param([string]$ConfigFile = "remote-config.json")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path $ConfigFile)) { throw "Copy remote-config.example.json to remote-config.json and fill in your settings. See docs/REMOTE-ACCESS.md." }
$config = Get-Content -Raw $ConfigFile | ConvertFrom-Json
foreach ($name in @("public_url", "team_domain", "audience", "data_dir")) {
    if (-not $config.$name -or $config.$name -match "REPLACE") { throw "Fill in '$name' in $ConfigFile first." }
}
if (-not (Test-Path (Join-Path $config.data_dir "qc.db"))) { throw "data_dir must point to your existing data folder containing qc.db. No new library was created." }
$env:QC_PUBLIC_URL = $config.public_url
$env:QC_ACCESS_TEAM_DOMAIN = $config.team_domain
$env:QC_ACCESS_AUD = $config.audience
$env:QC_DATA_DIR = $config.data_dir
& "$PSScriptRoot\start-windows.ps1"
