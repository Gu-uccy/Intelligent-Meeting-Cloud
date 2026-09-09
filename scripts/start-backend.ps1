$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $root "BackEnd\MeetingRoom-Parent"

if (-not (Test-Path $backendDir)) {
  throw "Backend directory not found: $backendDir"
}

if (-not (Get-Command mvn -ErrorAction SilentlyContinue)) {
  throw "Maven (mvn) is not installed or not available in PATH."
}

Set-Location $backendDir

Write-Host "Starting backend: http://127.0.0.1:8080" -ForegroundColor Green
Write-Host "Working directory: $backendDir" -ForegroundColor DarkGray

mvn -pl MeetingRoom-Management -am spring-boot:run
