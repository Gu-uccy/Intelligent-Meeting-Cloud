$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$frontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"

if (-not (Test-Path $backendScript)) {
  throw "Backend start script not found: $backendScript"
}

if (-not (Test-Path $frontendScript)) {
  throw "Frontend start script not found: $frontendScript"
}

Start-Process powershell -WorkingDirectory $root -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy", "Bypass",
  "-File", "`"$backendScript`""
)

Start-Sleep -Seconds 2

Start-Process powershell -WorkingDirectory $root -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy", "Bypass",
  "-File", "`"$frontendScript`""
)

Write-Host "Backend and frontend start windows have been opened." -ForegroundColor Green
Write-Host "Backend URL:  http://127.0.0.1:8080" -ForegroundColor Cyan
Write-Host "Frontend URL: http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host "If the backend fails to start, check MySQL and Redis first." -ForegroundColor Yellow
