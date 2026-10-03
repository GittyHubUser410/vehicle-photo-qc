$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed. Read the error above and retry." }
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Install Python 3.12 with the Windows Python launcher, then reopen PowerShell." }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "Install Node.js 22 LTS (22.12 or later), then reopen PowerShell." }
$nodeMajor = [int]((node --version).TrimStart('v').Split('.')[0])
if ($nodeMajor -lt 22) { throw "Node.js 22.12 or later is required." }
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    Check-Exit "Creating the Python environment"
}
& ".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
Check-Exit "Installing Python dependencies"
& ".venv\Scripts\python.exe" -m pip install --no-deps -e .
Check-Exit "Installing the application"
Push-Location "app\frontend"
try {
    npm.cmd ci
    Check-Exit "Installing interface dependencies"
    npm.cmd run build
    Check-Exit "Building the interface"
} finally { Pop-Location }
Write-Host ""
Write-Host "Setup complete. Run .\scripts\start-windows.ps1 and open http://127.0.0.1:8000" -ForegroundColor Green
