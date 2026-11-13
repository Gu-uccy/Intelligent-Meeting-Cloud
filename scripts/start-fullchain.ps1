<#
.SYNOPSIS
    全链路一键启动 / 停止脚本（MySQL + Spring Boot + 自研人脸服务 + 传感器服务 + Vue 前端）

.DESCRIPTION
    启动后各服务端口：
        MySQL             3307   （独立实例，不碰你机器上原有的 3306 服务）
        Spring Boot 后端  8081   （用户/会议室/预约，真实读写 MySQL）
        自研人脸服务       5001   （自研 LBP + 自动阈值 + 刷脸预约/刷脸开门 + 审计）
        传感器/设备服务    5058   （模拟模式：门禁/灯光可回写；树莓派在线时自动走硬件）
        Vue 前端          5173   （/api -> 8081，/face-api -> 5001，/sensor-api -> 5058）

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/start-fullchain.ps1
    powershell -ExecutionPolicy Bypass -File scripts/start-fullchain.ps1 -Status
    powershell -ExecutionPolicy Bypass -File scripts/start-fullchain.ps1 -Stop
#>
[CmdletBinding()]
param(
    [switch]$Stop,
    [switch]$Status,
    [switch]$SkipDb,
    [switch]$RebuildBackend
)

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $repo '.run'
$logDir = Join-Path $repo '.run/logs'
$pidFile = Join-Path $runDir 'pids.json'
New-Item -ItemType Directory -Force -Path $runDir, $logDir | Out-Null

$MYSQL_HOME = 'D:\mysql-8.0.31-winx64'
$MYSQL_DATA = 'D:\zongshe\.localmysql\data'
$JAVA = 'D:\java\jdk21\bin\java.exe'
$MAVEN = 'D:\Maven\apache-maven-3.9.12\bin\mvn.cmd'
$BACKEND_DIR = Join-Path $repo 'BackEnd/MeetingRoom-Parent'
$BACKEND_JAR = Join-Path $BACKEND_DIR 'MeetingRoom-Management/target/MeetingRoom-Management-0.0.1-SNAPSHOT.jar'
$FRONTEND_DIR = Join-Path $repo 'FrontEnd/Intelligent_meeting_cloud'
$FACE_DIR = Join-Path $repo 'MachineLearning/human_face'
$FLASK_DIR = Join-Path $repo 'Flask'

function Test-Port([int]$port) {
    try { return (Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue).TcpTestSucceeded }
    catch { return $false }
}

function Wait-Port([int]$port, [string]$name, [int]$timeoutSec = 90) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $timeoutSec) {
        if (Test-Port $port) { Write-Host ("  [OK]   {0} 已就绪（:{1}）" -f $name, $port) -ForegroundColor Green; return $true }
        Start-Sleep -Milliseconds 800
    }
    Write-Host ("  [FAIL] {0} 在 {1}s 内未监听 :{2}，请查看 .run/logs" -f $name, $timeoutSec, $port) -ForegroundColor Red
    return $false
}

function Get-ProcIds {
    if (Test-Path $pidFile) { try { return (Get-Content $pidFile -Raw | ConvertFrom-Json) } catch { } }
    return $null
}

# ---------------------------------------------------------------- 停止 / 状态
if ($Stop) {
    $pids = Get-ProcIds
    if (-not $pids) { Write-Host '没有找到 .run/pids.json，可能未用本脚本启动过。' -ForegroundColor Yellow }
    else {
        $names = @('vite', 'sensor', 'face', 'backend', 'mysql')
        foreach ($n in $names) {
            $id = $pids.$n
            if ($id) {
                try { Stop-Process -Id $id -Force -ErrorAction Stop; Write-Host ("  已停止 {0} (PID {1})" -f $n, $id) }
                catch { Write-Host ("  {0} 已不在运行" -f $n) -ForegroundColor DarkGray }
            }
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    Write-Host '完成。' -ForegroundColor Green
    return
}

if ($Status) {
    $pairs = @(
        @('MySQL', 3307), @('Spring Boot 后端', 8081), @('自研人脸服务', 5001),
        @('传感器/设备服务', 5058), @('Vue 前端', 5173)
    )
    foreach ($p in $pairs) {
        $up = Test-Port $p[1]
        $flag = if ($up) { 'UP  ' } else { 'DOWN' }
        $color = if ($up) { 'Green' } else { 'Red' }
        Write-Host ("  {0} {1,-18} :{2}" -f $flag, $p[0], $p[1]) -ForegroundColor $color
    }
    if (Test-Port 8081) {
        try {
            $h = Invoke-RestMethod 'http://127.0.0.1:5001/health' -TimeoutSec 5
            Write-Host ("  人脸服务：底库 {0} 人 / {1} 张，阈值 {2}（{3}）" -f $h.gallery_identities, $h.gallery_faces, $h.threshold, $h.threshold_source) -ForegroundColor Cyan
        } catch { }
    }
    return
}

Write-Host ''
Write-Host '================ 智能会议室 全链路启动 ================' -ForegroundColor Cyan
$started = [ordered]@{}
$existing = Get-ProcIds
if ($existing) { foreach ($k in $existing.PSObject.Properties.Name) { $started[$k] = $existing.$k } }

# ---------------------------------------------------------------- 1. MySQL(3307)
if (-not $SkipDb) {
    if (Test-Port 3307) {
        Write-Host '  [SKIP] MySQL 3307 已在运行' -ForegroundColor DarkGray
    } else {
        if (-not (Test-Path $MYSQL_DATA)) {
            Write-Host '  [INIT] 初始化 MySQL 数据目录（仅首次）…'
            & "$MYSQL_HOME\bin\mysqld.exe" --initialize-insecure --datadir="$MYSQL_DATA" --basedir="$MYSQL_HOME" --console *> "$logDir\mysql-init.log"
        }
        Write-Host '  [RUN ] 启动 MySQL :3307'
        $p = Start-Process -FilePath "$MYSQL_HOME\bin\mysqld.exe" `
            -ArgumentList "--datadir=$MYSQL_DATA", "--basedir=$MYSQL_HOME", "--port=3307", "--console", "--skip-log-bin" `
            -RedirectStandardOutput "$logDir\mysql.out.log" -RedirectStandardError "$logDir\mysql.err.log" -PassThru -WindowStyle Hidden
        $started['mysql'] = $p.Id
        Wait-Port 3307 'MySQL' 60 | Out-Null

        # 首次导入：建库 + 建表 + 对齐脚本
        $cnt = & "$MYSQL_HOME\bin\mysql.exe" "--host=127.0.0.1" "--port=3307" "--user=root" -N -B -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='meeting_room_db';" 2>$null
        if (-not $cnt -or [int]$cnt -lt 10) {
            Write-Host '  [INIT] 导入数据库结构（Database/smart-meeting-room-db + align-schema-for-code.sql）'
            & "$MYSQL_HOME\bin\mysql.exe" "--host=127.0.0.1" "--port=3307" "--user=root" "--default-character-set=utf8mb4" `
                -e "CREATE DATABASE IF NOT EXISTS meeting_room_db DEFAULT CHARACTER SET utf8mb4;" *> "$logDir\db-create.log"
            & "$MYSQL_HOME\bin\mysql.exe" "--host=127.0.0.1" "--port=3307" "--user=root" "--default-character-set=utf8mb4" `
                "--database=meeting_room_db" -e "source $($repo -replace '\\','/')/Database/smart-meeting-room-db" *> "$logDir\db-import.log"
            & "$MYSQL_HOME\bin\mysql.exe" "--host=127.0.0.1" "--port=3307" "--user=root" "--default-character-set=utf8mb4" `
                "--database=meeting_room_db" -e "source $($repo -replace '\\','/')/Database/align-schema-for-code.sql" *> "$logDir\db-align.log"
            Write-Host '  [OK]   数据库初始化完成' -ForegroundColor Green
        } else {
            Write-Host ("  [SKIP] meeting_room_db 已有 {0} 张表" -f $cnt) -ForegroundColor DarkGray
        }
    }
}

# ---------------------------------------------------------------- 2. 后端(8081)
if (Test-Port 8081) {
    Write-Host '  [SKIP] 后端 8081 已在运行' -ForegroundColor DarkGray
} else {
    if ($RebuildBackend -or -not (Test-Path $BACKEND_JAR)) {
        Write-Host '  [BUILD] 打包 Spring Boot 后端…'
        & $MAVEN -o -q -DskipTests package -f "$BACKEND_DIR/pom.xml" *> "$logDir\backend-build.log"
    }
    if (-not (Test-Path $BACKEND_JAR)) {
        Write-Host '  [FAIL] 后端 jar 不存在，打包失败，见 .run/logs/backend-build.log' -ForegroundColor Red
    } else {
        Write-Host '  [RUN ] 启动 Spring Boot :8081'
        $env:SPRING_DATASOURCE_URL = 'jdbc:mysql://127.0.0.1:3307/meeting_room_db?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf-8&zeroDateTimeBehavior=convertToNull&useSSL=false&allowPublicKeyRetrieval=true'
        $env:SPRING_DATASOURCE_USERNAME = 'root'
        $env:SPRING_DATASOURCE_PASSWORD = ''
        $env:SPRING_DATASOURCE_DRIVER_CLASS_NAME = 'com.mysql.cj.jdbc.Driver'
        $env:SERVER_PORT = '8081'
        $env:SPRING_PROFILES_ACTIVE = 'dev'
        $p = Start-Process -FilePath $JAVA -ArgumentList '-jar', "`"$BACKEND_JAR`"" -WorkingDirectory (Split-Path $BACKEND_JAR) `
            -RedirectStandardOutput "$logDir\backend.out.log" -RedirectStandardError "$logDir\backend.err.log" -PassThru -WindowStyle Hidden
        $started['backend'] = $p.Id
        Wait-Port 8081 'Spring Boot 后端' 120 | Out-Null
    }
}

# ---------------------------------------------------------------- 3. 人脸服务(5001)
if (Test-Port 5001) {
    Write-Host '  [SKIP] 人脸服务 5001 已在运行' -ForegroundColor DarkGray
} else {
    Write-Host '  [RUN ] 启动自研人脸服务 :5001'
    $env:MYSQL_HOST = '127.0.0.1'; $env:MYSQL_PORT = '3307'; $env:MYSQL_USER = 'root'
    $env:MYSQL_PASSWORD = ''; $env:MYSQL_DB = 'meeting_room_db'
    $env:FACE_SENSOR_BASE = 'http://127.0.0.1:5058'; $env:FACE_API_PORT = '5001'
    $p = Start-Process -FilePath 'python' -ArgumentList 'face_service_lbp.py' -WorkingDirectory $FACE_DIR `
        -RedirectStandardOutput "$logDir\face.out.log" -RedirectStandardError "$logDir\face.err.log" -PassThru -WindowStyle Hidden
    $started['face'] = $p.Id
    Wait-Port 5001 '自研人脸服务' 60 | Out-Null
}

# ---------------------------------------------------------------- 4. 传感器/设备(5058)
if (Test-Port 5058) {
    Write-Host '  [SKIP] 传感器服务 5058 已在运行' -ForegroundColor DarkGray
} else {
    Write-Host '  [RUN ] 启动传感器/设备服务 :5058（模拟模式）'
    $env:MEETING_DATA_MODE = 'simulation'
    $env:MEETING_PORT = '5058'
    $p = Start-Process -FilePath 'python' -ArgumentList 'unified_meeting_room_system.py' -WorkingDirectory $FLASK_DIR `
        -RedirectStandardOutput "$logDir\sensor.out.log" -RedirectStandardError "$logDir\sensor.err.log" -PassThru -WindowStyle Hidden
    $started['sensor'] = $p.Id
    Wait-Port 5058 '传感器/设备服务' 60 | Out-Null
}

# ---------------------------------------------------------------- 5. 前端(5173)
if (Test-Port 5173) {
    Write-Host '  [SKIP] 前端 5173 已在运行' -ForegroundColor DarkGray
} else {
    if (-not (Test-Path (Join-Path $FRONTEND_DIR 'node_modules'))) {
        Write-Host '  [INIT] 安装前端依赖（仅首次，约 1 分钟）…'
        & npm.cmd --prefix $FRONTEND_DIR ci --no-audit --no-fund *> "$logDir\npm-install.log"
    }
    Write-Host '  [RUN ] 启动 Vue 前端 :5173'
    $p = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' -WorkingDirectory $FRONTEND_DIR `
        -RedirectStandardOutput "$logDir\vite.out.log" -RedirectStandardError "$logDir\vite.err.log" -PassThru -WindowStyle Hidden
    $started['vite'] = $p.Id
    Wait-Port 5173 'Vue 前端' 120 | Out-Null
}

$started | ConvertTo-Json | Set-Content -Encoding UTF8 $pidFile

# ---------------------------------------------------------------- 汇总
Write-Host ''
Write-Host '--------------------------------------------------------' -ForegroundColor Cyan
Write-Host ('  前端入口   http://127.0.0.1:5173/login') -ForegroundColor White
Write-Host ('  后端接口   http://127.0.0.1:8081/login') -ForegroundColor White
Write-Host ('  人脸服务   http://127.0.0.1:5001/health') -ForegroundColor White
Write-Host ('  设备服务   http://127.0.0.1:5058/api/current') -ForegroundColor White
Write-Host '--------------------------------------------------------' -ForegroundColor Cyan
if (Test-Port 5001) {
    try {
        $h = Invoke-RestMethod 'http://127.0.0.1:5001/health' -TimeoutSec 5
        if ($h.gallery_identities -eq 0) {
            Write-Host '  ⚠ 人脸底库为空：先登录 → 「人脸门禁」页录入本人人脸，才能刷脸预约/解锁' -ForegroundColor Yellow
        } else {
            Write-Host ('  人脸底库：{0} 人 / {1} 张，阈值 {2}（{3}）' -f $h.gallery_identities, $h.gallery_faces, $h.threshold, $h.threshold_source) -ForegroundColor Green
        }
    } catch { }
}
Write-Host '  停止所有服务： powershell -File scripts/start-fullchain.ps1 -Stop' -ForegroundColor DarkGray
Write-Host '  查看状态：     powershell -File scripts/start-fullchain.ps1 -Status' -ForegroundColor DarkGray
Write-Host '  日志目录：     .run/logs' -ForegroundColor DarkGray
Write-Host ''
