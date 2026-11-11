$ErrorActionPreference = 'Stop'
$rpiAddress = if ($env:RPI_HOST) { $env:RPI_HOST } else { '192.168.43.206' }
& (Join-Path $PSScriptRoot 'start-all.ps1') -Mode Demo -RpiHost $rpiAddress
