$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Run scripts\setup-windows.ps1 first." }
if (-not (Test-Path "app\frontend\dist\index.html")) { throw "The interface is not built. Run scripts\setup-windows.ps1." }
if ($env:QC_PUBLIC_URL) {
    Write-Host "Protected remote mode: open $env:QC_PUBLIC_URL and sign in. Keep this window open; Ctrl+C stops the app."
} else {
    Write-Host "Local-only mode: open http://127.0.0.1:8000. Keep this window open; Ctrl+C stops the app."
}
& ".venv\Scripts\python.exe" -m uvicorn qc.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
