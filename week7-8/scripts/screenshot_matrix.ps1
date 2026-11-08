# 跨分辨率截图矩阵：桌面四档 + 窄屏一档，结果写 CSV
#
# 用法（先启动 Flask 传感器服务与 Vite）：
#   powershell -ExecutionPolicy Bypass -File scripts/screenshot_matrix.ps1 `
#       -Base http://127.0.0.1:5173 -OutDir results/screenshots
#
# 依赖：本机 Chrome（默认路径，可用 -Chrome 指定）

param(
    [string]$Base = "http://127.0.0.1:5173",
    [string]$OutDir = "results/screenshots",
    [string]$Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe",
    [string]$Path = "/room-3d",
    [string]$Tag = "idle",
    [int]$WaitMs = 12000
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Chrome)) {
    throw "未找到 Chrome：$Chrome（可用 -Chrome 指定）"
}

$root = Split-Path -Parent $PSScriptRoot
$outPath = if ([System.IO.Path]::IsPathRooted($OutDir)) { $OutDir } else { Join-Path $root $OutDir }
if (-not (Test-Path -LiteralPath $outPath)) {
    New-Item -ItemType Directory -Path $outPath -Force | Out-Null
}

$sizes = @(
    @{ W = 1920; H = 1080; Name = "1920x1080"; Class = "桌面大屏" },
    @{ W = 1600; H = 900;  Name = "1600x900";  Class = "桌面常见" },
    @{ W = 1366; H = 768;  Name = "1366x768";  Class = "笔记本主流" },
    @{ W = 1024; H = 768;  Name = "1024x768";  Class = "窄桌面" },
    @{ W = 390;  H = 844;  Name = "390x844";   Class = "手机竖屏(窄屏)" }
)

$csv = Join-Path $outPath ("截图记录_" + $Tag + ".csv")
"分辨率,类别,文件,字节数,状态,时间" | Set-Content -LiteralPath $csv -Encoding utf8

foreach ($s in $sizes) {
    $file = Join-Path $outPath ("3d_" + $Tag + "_" + $s.Name + ".png")
    $profile = Join-Path $env:TEMP ("chrome_" + $s.Name + "_" + [guid]::NewGuid().ToString("N").Substring(0, 6))
    $url = $Base.TrimEnd("/") + $Path

    & $Chrome --headless=new --disable-gpu --enable-unsafe-swiftshader --no-first-run `
        --user-data-dir="$profile" --window-size="$($s.W),$($s.H)" `
        --virtual-time-budget=$WaitMs --screenshot="$file" $url 2>$null | Out-Null

    Start-Sleep -Milliseconds 400
    $ok = Test-Path -LiteralPath $file
    $bytes = if ($ok) { (Get-Item -LiteralPath $file).Length } else { 0 }
    $status = if ($ok) { "OK" } else { "FAILED" }
    $time = (Get-Date).ToString("HH:mm:ss")
    ("{0},{1},{2},{3},{4},{5}" -f $s.Name, $s.Class, (Split-Path -Leaf $file), $bytes, $status, $time) |
        Add-Content -LiteralPath $csv -Encoding utf8
    Write-Output ("{0} -> {1} ({2} bytes)" -f $s.Name, $status, $bytes)

    if (Test-Path -LiteralPath $profile) {
        Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Output ("记录文件：" + $csv)
