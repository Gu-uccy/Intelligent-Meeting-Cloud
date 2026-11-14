param(
  [string]$MysqlBinDirectory = 'C:\Program Files\MySQL\MySQL Server 8.0\bin',
  [string]$EvidenceOutputDirectory,
  [switch]$SkipBuild,
  [switch]$KeepRunning,
  [switch]$LaunchLocal
)
$ErrorActionPreference = 'Stop'
trap { Write-Error $_ -ErrorAction Continue; exit 1 }
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($LaunchLocal) { $KeepRunning = $true }
. (Join-Path $PSScriptRoot 'backend-tools.ps1')
$javaExe = Set-BackendJava
$backendDir = Join-Path $projectRoot 'BackEnd/MeetingRoom-Parent'
$mysqlExe = Join-Path $MysqlBinDirectory 'mysql.exe'
$mysqldExe = Join-Path $MysqlBinDirectory 'mysqld.exe'
$mysqlAdminExe = Join-Path $MysqlBinDirectory 'mysqladmin.exe'
foreach ($exe in @($mysqlExe,$mysqldExe,$mysqlAdminExe)) {
  if (-not (Test-Path -LiteralPath $exe)) { throw "MySQL executable missing: $exe" }
}
function Get-AvailablePort {
  $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0)
  $listener.Start()
  try { return $listener.LocalEndpoint.Port } finally { $listener.Stop() }
}
$runName = 'business-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,6)
$taskDir = Join-Path $projectRoot ".codex-run-logs/$runName"
New-Item -ItemType Directory -Path $taskDir | Out-Null
if (-not $EvidenceOutputDirectory) { $EvidenceOutputDirectory = $taskDir }
New-Item -ItemType Directory -Force -Path $EvidenceOutputDirectory | Out-Null
$mysqlPort = Get-AvailablePort
$backendPort = Get-AvailablePort
$dataDir = Join-Path $taskDir 'mysql-data'
$clientConfig = Join-Path $taskDir 'mysql-client.ini'
$dbName = 'meeting_acceptance_' + (Get-Date -Format 'yyyyMMddHHmmss')
$taskPassword = [Guid]::NewGuid().ToString('N')
$springProcess = $null
$mysqlProcess = $null
$completed = $false
try {
  $initialize = Start-Process $mysqldExe -WindowStyle Hidden -ArgumentList @('--no-defaults','--initialize-insecure',('"--basedir={0}"' -f (Split-Path $MysqlBinDirectory)),('"--datadir={0}"' -f $dataDir),'--console') -RedirectStandardOutput (Join-Path $taskDir 'mysql-init.out.log') -RedirectStandardError (Join-Path $taskDir 'mysql-init.log') -Wait -PassThru
  if ($initialize.ExitCode -ne 0) { throw 'Isolated MySQL initialization failed. See mysql-init.log.' }
  $mysqlProcess = Start-Process $mysqldExe -WindowStyle Hidden -ArgumentList @('--no-defaults',('"--basedir={0}"' -f (Split-Path $MysqlBinDirectory)),('"--datadir={0}"' -f $dataDir),"--port=$mysqlPort",'--bind-address=127.0.0.1','--mysqlx=OFF','--console') -RedirectStandardOutput (Join-Path $taskDir 'mysql.out.log') -RedirectStandardError (Join-Path $taskDir 'mysql.err.log') -PassThru
  $ready = $false
  for ($i=0;$i -lt 30;$i++) {
    $ErrorActionPreference='Continue'
    & $mysqlAdminExe --no-defaults --host=127.0.0.1 "--port=$mysqlPort" --user=root --skip-password ping 2>$null | Out-Null
    $ErrorActionPreference='Stop'
    if ($LASTEXITCODE -eq 0) { $ready=$true; break }
    Start-Sleep -Milliseconds 500
  }
  if (-not $ready) { throw 'Isolated MySQL did not become ready.' }
  $setup = "ALTER USER 'root'@'localhost' IDENTIFIED BY '$taskPassword'; CREATE DATABASE $dbName CHARACTER SET utf8mb4;"
  $ErrorActionPreference='Continue'
  $setup | & $mysqlExe --no-defaults --host=127.0.0.1 "--port=$mysqlPort" --user=root --skip-password 2>$null
  $ErrorActionPreference='Stop'
  if ($LASTEXITCODE -ne 0) { throw 'Test database credential setup failed.' }
  @('[client]','host=127.0.0.1',"port=$mysqlPort",'user=root',"password=$taskPassword",'default-character-set=utf8mb4') | Set-Content $clientConfig -Encoding ASCII
  # Pipe UTF-8 SQL without PowerShell 5's ASCII pipeline conversion.
  $importProcess = [Diagnostics.Process]::new()
  $importProcess.StartInfo = [Diagnostics.ProcessStartInfo]::new()
  $importProcess.StartInfo.FileName = $mysqlExe
  $importProcess.StartInfo.Arguments = '"--defaults-file=' + $clientConfig + '" ' + $dbName
  $importProcess.StartInfo.UseShellExecute = $false
  $importProcess.StartInfo.CreateNoWindow = $true
  $importProcess.StartInfo.RedirectStandardInput = $true
  $null = $importProcess.Start()
  $sqlBytes = [IO.File]::ReadAllBytes((Join-Path $projectRoot 'Database/schema-current.sql'))
  $importProcess.StandardInput.BaseStream.Write($sqlBytes,0,$sqlBytes.Length)
  $importProcess.StandardInput.Close()
  $importProcess.WaitForExit()
  if ($importProcess.ExitCode -ne 0) { throw 'Current schema import failed.' }
  if (-not $SkipBuild) {
    & (Get-BackendMaven $backendDir) -B -f (Join-Path $backendDir 'pom.xml') -pl MeetingRoom-Management -am package *> (Join-Path $taskDir 'maven.log')
    if ($LASTEXITCODE -ne 0) { throw 'Maven build/tests failed. See maven.log.' }
  }
  $env:MYSQL_HOST='127.0.0.1'; $env:MYSQL_PORT=[string]$mysqlPort; $env:MYSQL_USER='root'; $env:MYSQL_PASSWORD=$taskPassword; $env:MYSQL_DB=$dbName
  $env:SERVER_PORT=[string]$backendPort; $env:MEETING_SCHEDULING_ENABLED='false'
  # Deliberately absent Redis verifies honest degraded health and the optional Local path.
  $env:REDIS_HOST='127.0.0.1'; $env:REDIS_PORT=[string](Get-AvailablePort)
  $jar = Join-Path $backendDir 'MeetingRoom-Management/target/MeetingRoom-Management-0.0.1-SNAPSHOT.jar'
  $springProcess = Start-Process $javaExe -WindowStyle Hidden -ArgumentList @('-jar',('"{0}"' -f $jar)) -WorkingDirectory $projectRoot -RedirectStandardOutput (Join-Path $taskDir 'spring.out.log') -RedirectStandardError (Join-Path $taskDir 'spring.err.log') -PassThru
  $businessUrl = "http://127.0.0.1:$backendPort"
  $ready=$false
  for ($i=0;$i -lt 60;$i++) {
    try { $health=Invoke-RestMethod "$businessUrl/health" -TimeoutSec 5; if ($health.schema) { $ready=$true; break } } catch { }
    if ($springProcess.HasExited) { throw 'Spring exited before readiness. See spring.out.log.' }
    Start-Sleep -Milliseconds 500
  }
  if (-not $ready) { throw 'Spring schema readiness timed out.' }
  $env:MEETING_TEST_URL=$businessUrl; $env:MEETING_TEST_DB=$dbName; $env:MEETING_TEST_MYSQL=$mysqlExe; $env:MEETING_TEST_MYSQL_CONFIG=$clientConfig; $env:EVIDENCE_OUTPUT_DIR=$EvidenceOutputDirectory
  & python (Join-Path $projectRoot 'delivery/tests/local_business_smoke.py')
  if ($LASTEXITCODE -ne 0) { throw 'Real business HTTP acceptance failed. See business-http.json.' }
  # Local-only credentials; never stage .codex-run-logs. This file supports a later Local UI session.
  $envFile = Join-Path $taskDir 'local-env.ps1'
  @("`$env:JAVA_HOME='$($env:JAVA_HOME)'", "`$env:MYSQL_HOST='127.0.0.1'", "`$env:MYSQL_PORT='$mysqlPort'", "`$env:MYSQL_DB='$dbName'", "`$env:MYSQL_USER='root'", "`$env:MYSQL_PASSWORD='$taskPassword'", "`$env:SERVER_PORT='$backendPort'", "`$env:REDIS_HOST='127.0.0.1'", "`$env:REDIS_PORT='$($env:REDIS_PORT)'", "`$env:MEETING_SCHEDULING_ENABLED='false'") | Set-Content $envFile -Encoding UTF8
  @{task_dir=$taskDir; business_url=$businessUrl; mysql_port=$mysqlPort; environment_file=$envFile; keep_running=[bool]$KeepRunning} | ConvertTo-Json | Set-Content (Join-Path $taskDir 'session.json') -Encoding UTF8
  $completed=$true
  Write-Host "PASS. Evidence: $EvidenceOutputDirectory"
  if ($KeepRunning) { Write-Host "Services kept for Local mode. Environment: $envFile" }
  if ($LaunchLocal) { & (Join-Path $PSScriptRoot 'start-all.ps1') -Mode Local -BackendPort $backendPort }
} finally {
  if (-not ($KeepRunning -and $completed)) {
    $ErrorActionPreference='Continue'
    if ($springProcess -and -not $springProcess.HasExited) { Stop-Process -Id $springProcess.Id -ErrorAction SilentlyContinue }
    if (Test-Path $clientConfig) { & $mysqlAdminExe "--defaults-file=$clientConfig" shutdown 2>$null | Out-Null }
    elseif ($mysqlProcess) { & $mysqlAdminExe --no-defaults --host=127.0.0.1 "--port=$mysqlPort" --user=root --skip-password shutdown 2>$null | Out-Null }
  }
}
