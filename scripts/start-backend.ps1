param(
  [int]$Port = $(if ($env:SERVER_PORT) { [int]$env:SERVER_PORT } else { 8080 }),
  [switch]$BuildOnly
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot 'backend-tools.ps1')

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $root "BackEnd\MeetingRoom-Parent"

if (-not (Test-Path $backendDir)) {
  throw "Backend directory not found: $backendDir"
}

$javaExe = Set-BackendJava
$mavenExe = Get-BackendMaven $backendDir

Set-Location $backendDir

Write-Host "Backend: http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Working directory: $backendDir" -ForegroundColor DarkGray

# Build/install the dependencies first: spring-boot:run on the whole reactor
# otherwise tries to run the aggregator/common modules as applications.
& $mavenExe -B -pl MeetingRoom-Management -am package -DskipTests
if ($LASTEXITCODE -ne 0) { throw "Maven reactor build failed." }
if ($BuildOnly) { return }
$env:SERVER_PORT = [string]$Port
& $javaExe -jar 'MeetingRoom-Management/target/MeetingRoom-Management-0.0.1-SNAPSHOT.jar'
if ($LASTEXITCODE -ne 0) { throw "Spring Boot exited with an error." }
