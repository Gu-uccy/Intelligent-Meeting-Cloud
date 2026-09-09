$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendDir = Join-Path $root "FrontEnd\Intelligent_meeting_cloud"
$flaskDir = Join-Path $root "Flask"
$flaskPython = Join-Path $flaskDir ".venv\Scripts\python.exe"
$pythonCommand = $null
$rpiHost = if ($env:RPI_HOST) { $env:RPI_HOST } else { "192.168.43.206" }
$sensorPort = 5000

function Test-TcpPort([string]$hostName, [int]$port) {
  try {
    return (Test-NetConnection -ComputerName $hostName -Port $port -WarningAction SilentlyContinue -InformationLevel Quiet)
  } catch {
    return $false
  }
}

function Test-HttpEndpoint([string]$url) {
  try {
    $response = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
  } catch {
    return $false
  }
}

if (-not (Test-Path $frontendDir)) {
  throw "Frontend directory not found: $frontendDir"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm is not installed or not available in PATH."
}

if (Test-Path $flaskPython) {
  try {
    & $flaskPython -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) {
      $pythonCommand = $flaskPython
    }
  } catch {
    $pythonCommand = $null
  }
}

if (-not $pythonCommand) {
  $systemPython = Get-Command python -ErrorAction SilentlyContinue
  if ($systemPython) {
    $pythonCommand = $systemPython.Source
  }
}

$rpiSensorOnline = Test-TcpPort $rpiHost $sensorPort
if ($rpiSensorOnline) {
  $sensorTarget = "http://$rpiHost`:$sensorPort"
  Write-Host "Raspberry Pi sensor service detected: $sensorTarget" -ForegroundColor Green
} else {
  if (-not $pythonCommand) {
    throw "Raspberry Pi sensor service is offline and no usable Python interpreter was found."
  }

  if (-not (Test-TcpPort "127.0.0.1" $sensorPort)) {
    Start-Process powershell -WorkingDirectory $flaskDir -ArgumentList @(
      "-NoExit",
      "-ExecutionPolicy", "Bypass",
      "-Command", "& '$pythonCommand' '$flaskDir\unified_meeting_room_system.py'"
    )
    Start-Sleep -Seconds 2
  }

  $sensorTarget = "http://127.0.0.1:$sensorPort"
  Write-Host "Raspberry Pi sensor service is offline; local simulation started: $sensorTarget" -ForegroundColor Yellow
}

$env:VITE_USE_MOCK = "true"
$env:VITE_SENSOR_API_URL = "/sensor-api"
$env:VITE_SENSOR_CHART_URL = "/sensor-chart"
$env:VITE_SENSOR_PROXY_TARGET = $sensorTarget
$env:VITE_FACE_API_URL = "/face-api"
$env:VITE_FACE_PROXY_TARGET = "http://$rpiHost`:5001"
$env:VITE_PORT = "5173"

if (-not (Test-HttpEndpoint "http://127.0.0.1:5173/")) {
  Start-Process cmd.exe -WorkingDirectory $frontendDir -ArgumentList @(
    "/k",
    "npm.cmd run dev -- --host 0.0.0.0"
  )

  $frontendReady = $false
  for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    if (Test-HttpEndpoint "http://127.0.0.1:5173/") {
      $frontendReady = $true
      break
    }
  }

  if (-not $frontendReady) {
    throw "Frontend did not become available at http://127.0.0.1:5173/"
  }
}

Start-Process "http://127.0.0.1:5173"

Write-Host "Demo frontend: http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host "Sensor target:  $sensorTarget" -ForegroundColor Cyan
Write-Host "Login and meeting-room data use the project's demo mode." -ForegroundColor DarkGray
