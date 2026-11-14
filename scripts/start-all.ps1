param(
  [ValidateSet('Demo', 'Local', 'Full')][string]$Mode = 'Demo',
  [string]$RpiHost = '192.168.43.206',
  [int]$FrontendPort = 5173,
  [ValidateRange(1,65535)][int]$BackendPort = $(if ($env:SERVER_PORT) { [int]$env:SERVER_PORT } else { 8080 }),
  [switch]$CheckOnly,
  [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'backend-tools.ps1')
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
  try { return Invoke-RestMethod $Url -TimeoutSec 5 } catch { return $null }
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
  maven = [bool]((Get-Command mvn.cmd -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $projectRoot 'BackEnd/MeetingRoom-Parent/mvnw.cmd')))
  mysql_tcp = (Test-Port $(if ($env:MYSQL_HOST) { $env:MYSQL_HOST } else { '127.0.0.1' }) $(if ($env:MYSQL_PORT) { [int]$env:MYSQL_PORT } else { 3306 }))
  redis_tcp = (Test-Port $(if ($env:REDIS_HOST) { $env:REDIS_HOST } else { '127.0.0.1' }) $(if ($env:REDIS_PORT) { [int]$env:REDIS_PORT } else { 6379 }))
  spring_port_8080_free = (-not (Test-Port '127.0.0.1' 8080))
  backend_port = $BackendPort
  backend_port_free = (-not (Test-Port '127.0.0.1' $BackendPort))
  raspberry_sensor = (Read-Json "http://${RpiHost}:5000/api/health")
  frontend_requested_port_free = (-not (Test-Port '127.0.0.1' $FrontendPort))
}
$checks | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $logDir 'preflight.json') -Encoding UTF8
if ($CheckOnly) { $checks | ConvertTo-Json -Depth 5; exit 0 }
if (-not $checks.node -or -not $checks.npm) { throw 'Node.js and npm are required.' }
if ($Mode -ne 'Demo') {
  $null = Set-BackendJava
  if (-not $checks.mysql_tcp) { throw 'Start MySQL and import Database/schema-current.sql into a NEW database; set MYSQL_* for this installation.' }
  if ($Mode -eq 'Full' -and -not $checks.redis_tcp) { throw 'Full mode requires Redis. Local mode allows unavailable Redis and reports degraded health.' }
  if ($Mode -eq 'Full' -and ($checks.raspberry_sensor.service -ne 'meeting-room-sensors' -or $checks.raspberry_sensor.source -ne 'sensor')) { throw 'Full mode needs the updated Raspberry Pi hardware Flask service on port 5000.' }
  $businessUrl = "http://127.0.0.1:$BackendPort"
  $businessHealth = Read-Json "$businessUrl/health"
  if (-not $checks.backend_port_free -and $businessHealth.service -ne 'meeting-room-business') { throw "Backend port $BackendPort is occupied or unhealthy. Choose -BackendPort 18080 or verify the owner. No process was stopped." }
  $springScript = Join-Path $PSScriptRoot 'start-backend.ps1'
  if ($checks.backend_port_free) {
    $springProcess = Start-Process powershell -WindowStyle Hidden -WorkingDirectory $projectRoot -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"{0}"' -f $springScript),'-Port',[string]$BackendPort) -RedirectStandardOutput (Join-Path $logDir 'spring.out.log') -RedirectStandardError (Join-Path $logDir 'spring.err.log') -PassThru
    for ($i=0; $i -lt 360; $i++) {
      $businessHealth = Read-Json "$businessUrl/health"
      if ($businessHealth.service -eq 'meeting-room-business' -and $businessHealth.schema) { break }
      if ($springProcess.HasExited) { throw 'Spring startup failed. Check spring.out.log and spring.err.log.' }
      Start-Sleep -Milliseconds 500
    }
  }
  if (-not $businessHealth.schema) { throw 'Spring is not ready: database credentials or current schema are unavailable. Check logs.' }
  if ($Mode -eq 'Full' -and -not $businessHealth.redis) { throw 'Spring Redis PING failed. Check REDIS_* credentials and host.' }
  if (-not $businessHealth.redis) { Write-Warning 'Local business service is ready with Redis unavailable; health is degraded.' }
  $sensorTarget = "http://${RpiHost}:5000"
  $env:VITE_USE_MOCK = 'false'
}
if ($Mode -ne 'Full') {
  if ($Mode -eq 'Demo') {
  $env:VITE_USE_MOCK = 'true'
  }
  $env:VITE_AGENT_MODE = 'local'
  if ($Mode -eq 'Demo' -and $checks.raspberry_sensor.service -eq 'meeting-room-sensors' -and $checks.raspberry_sensor.source -eq 'sensor') {
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
$faceTarget = "http://${RpiHost}:5001"
if ($Mode -ne 'Full') {
  $faceHealth = Read-Json 'http://127.0.0.1:5001/health'
  if (-not (Test-Port '127.0.0.1' 5001)) {
    $pythonExe = (Get-Command python -ErrorAction Stop).Source
    & $pythonExe -c 'import flask, flask_cors, numpy, cv2'
    if ($LASTEXITCODE -ne 0) { throw 'Face demo dependencies missing: pip install -r MachineLearning/human_face/requirements.txt' }
    $env:FACE_DEVICE_URL = 'http://127.0.0.1:5058'
    $faceFile = Join-Path $projectRoot 'MachineLearning\human_face\face_api.py'
    Start-Process -FilePath $pythonExe -WindowStyle Hidden -WorkingDirectory $projectRoot -ArgumentList @('-u',('"{0}"' -f $faceFile)) -RedirectStandardOutput (Join-Path $logDir 'face.out.log') -RedirectStandardError (Join-Path $logDir 'face.err.log') | Out-Null
    Wait-Http 'http://127.0.0.1:5001/health'
    $faceHealth = Read-Json 'http://127.0.0.1:5001/health'
  }
  if ($faceHealth.model_name -ne 'custom-uniform-LBP') { throw '5001 is occupied by another face service. Check its owner before restarting.' }
  $faceTarget = 'http://127.0.0.1:5001'
}
$env:VITE_FACE_PROXY_TARGET=$faceTarget
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:$BackendPort"
$env:VITE_PORT=[string]$FrontendPort
$npmExe=(Get-Command npm.cmd).Source
Start-Process cmd.exe -WindowStyle Hidden -WorkingDirectory $frontendDir -ArgumentList @('/d','/c', ('""{0}" run dev -- --host 0.0.0.0 --port {1} --strictPort"' -f $npmExe,$FrontendPort)) -RedirectStandardOutput (Join-Path $logDir 'vite.out.log') -RedirectStandardError (Join-Path $logDir 'vite.err.log') | Out-Null
$url="http://127.0.0.1:$FrontendPort/room-3d"
Wait-Http $url
$session = @{ url=$url; mode=$Mode; business_target=$env:VITE_API_PROXY_TARGET; business_health=$businessHealth; sensor_target=$sensorTarget; face_target=$faceTarget; face_access='simulation-only; authorized samples/policy/threshold required'; business_source=$(if ($env:VITE_USE_MOCK -eq 'true') { 'mock' } else { 'spring-mysql' }); source=(Read-Json "$sensorTarget/api/health").source }
$session | ConvertTo-Json | Set-Content (Join-Path $logDir 'session.json') -Encoding UTF8
$session | ConvertTo-Json
if (-not $NoBrowser) { Start-Process $url }
