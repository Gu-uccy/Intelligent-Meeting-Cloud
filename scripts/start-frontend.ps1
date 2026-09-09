$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendDir = Join-Path $root "FrontEnd\Intelligent_meeting_cloud"

if (-not (Test-Path $frontendDir)) {
  throw "Frontend directory not found: $frontendDir"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm is not installed or not available in PATH."
}

Set-Location $frontendDir

Write-Host "Starting frontend: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "Working directory: $frontendDir" -ForegroundColor DarkGray

npm run dev -- --host 0.0.0.0
