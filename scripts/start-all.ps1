param(
  [ValidateSet('Demo', 'Full')][string]$Mode = 'Demo',
  [string]$RpiHost = '192.168.43.206',
  [int]$FrontendPort = 5173,
  [switch]$CheckOnly,
  [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontendDir = Join-Path $projectRoot 'FrontEnd\Intelligent_meeting_cloud'
$logDir = Join-Path $projectRoot '.codex-run-logs'
New-Item -ItemType Directory -Force $logDir | Out-Null

function Test-Port([string]$Target, [int]$Port) {
  $targets = if ($Target -eq '127.0.0.1') { @('127.0.0.1','::1') } else { @($Target) }
  foreach ($address in $targets) {
    $client = [Net.Sockets.TcpClient]::new()
    try { $task = $client.ConnectAsync($address, $Port); if ($task.Wait(700) -and $client.Connected) { return $true } }
    catch { } finally { $client.Dispose() }
  }
  return $false
}
function Read-Json([string]$Url) {
  try { return Invoke-RestMethod $Url -TimeoutSec 2 } catch { return $null }
}
function Wait-Http([string]$Url) {
  for ($attempt=0; $attempt -lt 40; $attempt++) {
    try { if ((Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 1).StatusCode -eq 200) { return } } catch {}
    Start-Sleep -Milliseconds 500
  }
  throw "Service readiness timeout: $Url. See $logDir"
}
$checks = [ordered]@{
  timestamp = (Get-Date).ToString('o'); mode = $Mode
  node = [bool](Get-Command node -ErrorAction SilentlyContinue)
  npm = [bool](Get-Command npm.cmd -ErrorAction SilentlyContinue)
  java = [bool](Get-Command java -ErrorAction SilentlyContinue)
  maven = [bool](Get-Command mvn -ErrorAction SilentlyContinue)
  mysql_tcp = (Test-Port '127.0.0.1' 3306)
  redis_tcp = (Test-Port '127.0.0.1' 6379)
  spring_port_8080_free = (-not (Test-Port '127.0.0.1' 8080))
  raspberry_sensor = (Read-Json "http://${RpiHost}:5000/api/health")
  frontend_requested_port_free = (-not (Test-Port '127.0.0.1' $FrontendPort))
}
$checks | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $logDir 'preflight.json') -Encoding UTF8
if ($CheckOnly) { $checks | ConvertTo-Json -Depth 5; exit 0 }
if (-not $checks.node -or -not $checks.npm) { throw 'Node.js and npm are required.' }
if ($Mode -eq 'Full') {
  if (-not $checks.java -or -not $checks.maven) { throw 'Full mode needs JDK 17+ and Maven. Use Demo for the offline walkthrough.' }
  if (-not $checks.mysql_tcp -or -not $checks.redis_tcp) { throw 'Start MySQL (3306), import the database, and start Redis (6379) before Full mode.' }
  if (-not $checks.spring_port_8080_free) { throw '8080 is occupied. Verify the owner before starting Spring; no existing process was stopped.' }
  if ($checks.raspberry_sensor.service -ne 'meeting-room-sensors' -or $checks.raspberry_sensor.source -ne 'sensor') { throw 'Full mode needs the updated Raspberry Pi hardware Flask service on port 5000.' }
  $springScript = Join-Path $PSScriptRoot 'start-backend.ps1'
  Start-Process powershell -WindowStyle Hidden -WorkingDirectory $projectRoot -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"{0}"' -f $springScript)) -RedirectStandardOutput (Join-Path $logDir 'spring.out.log') -RedirectStandardError (Join-Path $logDir 'spring.err.log') | Out-Null
  # HTTP 200 actuator is not configured: confirm the process before the final preflight.
  $springReady = $false
  for ($i=0; $i -lt 120; $i++) { if (Test-Port '127.0.0.1' 8080) { $springReady=$true; break }; Start-Sleep -Milliseconds 500 }
  if (-not $springReady) { throw 'Spring startup failed. Check spring.err.log and database credentials.' }
  $sensorTarget = "http://${RpiHost}:5000"
  $env:VITE_USE_MOCK = 'false'
} else {
  $env:VITE_USE_MOCK = 'true'
  if ($checks.raspberry_sensor.service -eq 'meeting-room-sensors' -and $checks.raspberry_sensor.source -eq 'sensor') {
    $sensorTarget = "http://${RpiHost}:5000"
  } else {
    $localSensor = Read-Json 'http://127.0.0.1:5058/api/health'
    if ($localSensor.service -ne 'meeting-room-sensors') {
      if (Test-Port '127.0.0.1' 5058) { throw '5058 is occupied by another service.' }
      $pythonExe = (Get-Command python -ErrorAction Stop).Source
      $env:MEETING_DATA_MODE = 'simulation'; $env:MEETING_PORT = '5058'
      $env:PYTHONIOENCODING = 'utf-8'
      $sensorFile = Join-Path $projectRoot 'Flask\unified_meeting_room_system.py'
      Start-Process -FilePath $pythonExe -WindowStyle Hidden -WorkingDirectory $projectRoot -ArgumentList @('-u',('"{0}"' -f $sensorFile)) -RedirectStandardOutput (Join-Path $logDir 'flask.out.log') -RedirectStandardError (Join-Path $logDir 'flask.err.log') | Out-Null
      Wait-Http 'http://127.0.0.1:5058/api/health'
    }
    $sensorTarget = 'http://127.0.0.1:5058'
  }
}
while (Test-Port '127.0.0.1' $FrontendPort) { $FrontendPort++; if ($FrontendPort -gt 5299) { throw 'No free frontend port.' } }
$env:VITE_SENSOR_API_URL='/sensor-api'; $env:VITE_SENSOR_PROXY_TARGET=$sensorTarget
$env:VITE_FACE_PROXY_TARGET="http://${RpiHost}:5001"
$env:VITE_PORT=[string]$FrontendPort
$npmExe=(Get-Command npm.cmd).Source
Start-Process cmd.exe -WindowStyle Hidden -WorkingDirectory $frontendDir -ArgumentList @('/d','/c', ('""{0}" run dev -- --host 0.0.0.0 --port {1} --strictPort"' -f $npmExe,$FrontendPort)) -RedirectStandardOutput (Join-Path $logDir 'vite.out.log') -RedirectStandardError (Join-Path $logDir 'vite.err.log') | Out-Null
$url="http://127.0.0.1:$FrontendPort/room-3d"
Wait-Http $url
$session = @{ url=$url; mode=$Mode; sensor_target=$sensorTarget; business_source=$env:VITE_USE_MOCK; source=(Read-Json "$sensorTarget/api/health").source }
$session | ConvertTo-Json | Set-Content (Join-Path $logDir 'session.json') -Encoding UTF8
$session | ConvertTo-Json
if (-not $NoBrowser) { Start-Process $url }
