# Isolated A.1 Windows restart after Independent Review

🔵 **Information**

Use this guide only after Independent Review returns PASS for the exact published correction commit. A.1 acceptance remains pending. This code-only fix requires no dependency rebuild or data deletion. Keep the existing pilot and Cloudflare settings running unchanged.

🟠 **Purpose**

Restart only the separate test checkout `G:\Projects\vehicle-photo-qc-a1-test`, using only `G:\Projects\vehicle-photo-qc-a1-test-data`, on `127.0.0.1:8001`.

🛑 **Stop condition**

If any checkout, environment, data directory, server identity or review precondition differs, stop and report the mismatch. Do not reset/clean a dirty checkout, delete data, clear machine/user environment variables, change Cloudflare, or stop a pilot process to make these steps work.

## Stop the isolated test server

🟢 **Action — PowerShell 1: Isolated A.1 test server**

These window names identify separate PowerShell sessions. Locate the existing window that started the test app from `G:\Projects\vehicle-photo-qc-a1-test` on port 8001 with the test data directory above. Only after identifying it, press Ctrl+C there. If you cannot identify it, stop and report; do not kill processes by name or stop any service.

## Check and update the isolated checkout

🟢 **Action — PowerShell 2: Isolated A.1 verification and restart**

Open a fresh PowerShell window. Run this block. It changes only this checkout and process environment. It stops on dirty files or failed safety checks.

```powershell
$ErrorActionPreference = 'Stop'
$testRoot = 'G:\Projects\vehicle-photo-qc-a1-test'
$testData = 'G:\Projects\vehicle-photo-qc-a1-test-data'
Set-Location -LiteralPath $testRoot
if ((Get-Location).Path -ne $testRoot) { throw 'Unexpected working directory.' }
$repoRoot = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0 -or $repoRoot.Replace('/', '\') -ne $testRoot) {
    throw 'This is not the isolated test repository.'
}
$dirty = git status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Checkout is dirty or unreadable. Stop; preserve it.' }
$repoRemote = git remote get-url origin
if ($LASTEXITCODE -ne 0 -or $repoRemote -notin @(
    'https://github.com/GittyHubUser410/vehicle-photo-qc.git',
    'https://github.com/GittyHubUser410/vehicle-photo-qc',
    'git@github.com:GittyHubUser410/vehicle-photo-qc.git'
)) { throw 'Unexpected origin repository. Stop and report without sharing credentials.' }
foreach ($name in @('QC_PUBLIC_URL', 'QC_ACCESS_TEAM_DOMAIN', 'QC_ACCESS_AUD')) {
    foreach ($scope in @('Process', 'User', 'Machine')) {
        if ([Environment]::GetEnvironmentVariable($name, $scope)) {
            throw "Remote-mode setting $name exists in $scope. Stop; do not clear it."
        }
    }
}
if ($env:QC_DATA_DIR -and $env:QC_DATA_DIR -ne $testData) {
    throw 'QC_DATA_DIR points elsewhere. Stop.'
}
if (!(Test-Path -LiteralPath (Join-Path $testData 'qc.db') -PathType Leaf)) {
    throw 'Expected existing isolated test database is missing. Stop.'
}
if (!(Test-Path -LiteralPath '.\.venv\Scripts\python.exe' -PathType Leaf)) {
    throw 'Existing test Python environment is missing. Stop.'
}
if (Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -eq 8001 }) {
    throw 'Port 8001 is still occupied. Stop; do not kill an unidentified process.'
}
$reviewedCommit = '9bee7291360a18012379dd4a9aa51088f1494e93'
git fetch origin $reviewedCommit
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed. Stop.' }
$fetchedCommit = git rev-parse FETCH_HEAD
if ($LASTEXITCODE -ne 0 -or $fetchedCommit -ne $reviewedCommit) { throw 'Fetched commit mismatch.' }
$dirty = git status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Checkout changed. Stop; preserve it.' }
git checkout --detach $reviewedCommit
if ($LASTEXITCODE -ne 0) { throw 'Checkout failed. Stop.' }
$actualCommit = git rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actualCommit -ne $reviewedCommit) { throw 'Commit mismatch. Stop.' }
$env:QC_DATA_DIR = $testData
$env:PYTHONPATH = Join-Path $testRoot 'app\backend'
Write-Host "Reviewed commit: $actualCommit"
Write-Host "Test checkout: $testRoot"
Write-Host "Test data: $env:QC_DATA_DIR"
.\.venv\Scripts\python.exe -m uvicorn qc.main:create_app --factory --host 127.0.0.1 --port 8001 --workers 1 --no-proxy-headers
```

🔵 **Information**

Detached checkout means this server uses the exact reviewed commit rather than a moving branch. `--no-proxy-headers` prevents forwarded connection headers from changing the local request context. Keep this PowerShell window open while testing. No remote startup script is used.

🟣 **Expected result**

The printed paths match the isolated checkout and test data. The printed commit matches the PASS report. Uvicorn starts on `http://127.0.0.1:8001` without an authentication/configuration error.

## Retry the owner acceptance flow

🟢 **Action**

Open `http://127.0.0.1:8001`, refresh, and retry the same small disposable training import. Confirm it completes, labels remain Suggested, and examples are not exportable without verification. If convenient repeat at `http://localhost:8001`. Continue the existing A.1 Human Test Packet; this correction alone does not accept A.1.

🟡 **Report**

Did the isolated server start and the training import complete without the 403? **Yes / No**. On No, report the exact failing step, HTTP status and non-secret error text. Do not send tokens, environment dumps or tunnel credentials.

🛑 **Recovery**

If startup or import fails, Ctrl+C only in **PowerShell 2** and leave the checkout and all data intact. Report the failure for investigation; do not rebuild dependencies, delete data, roll back the database or change pilot settings.
