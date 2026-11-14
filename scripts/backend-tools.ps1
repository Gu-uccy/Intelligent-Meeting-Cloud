$ErrorActionPreference = 'Stop'

function Get-BackendMaven([string]$BackendDirectory) {
  $wrapper = Join-Path $BackendDirectory 'mvnw.cmd'
  if (Test-Path -LiteralPath $wrapper) { return $wrapper }
  $installed = Get-Command mvn.cmd -ErrorAction SilentlyContinue
  if ($installed) { return $installed.Source }
  throw 'Maven Wrapper is missing. Restore BackEnd/MeetingRoom-Parent/mvnw.cmd and .mvn/wrapper.'
}

function Set-BackendJava {
  $javaExe = if ($env:JAVA_HOME -and (Test-Path (Join-Path $env:JAVA_HOME 'bin/java.exe'))) {
    Join-Path $env:JAVA_HOME 'bin/java.exe'
  } else {
    (Get-Command java -ErrorAction Stop).Source
  }
  # java writes its version to stderr even on success; avoid PowerShell 5 treating it as a terminating error.
  $javaProcess = [Diagnostics.Process]::new()
  $javaProcess.StartInfo = [Diagnostics.ProcessStartInfo]::new()
  $javaProcess.StartInfo.FileName = $javaExe
  $javaProcess.StartInfo.Arguments = '-XshowSettings:properties -version'
  $javaProcess.StartInfo.UseShellExecute = $false
  $javaProcess.StartInfo.CreateNoWindow = $true
  $javaProcess.StartInfo.RedirectStandardOutput = $true
  $javaProcess.StartInfo.RedirectStandardError = $true
  $null = $javaProcess.Start()
  $versionText = $javaProcess.StandardError.ReadToEnd() + $javaProcess.StandardOutput.ReadToEnd()
  $javaProcess.WaitForExit()
  if ($versionText -notmatch 'version "(?<major>\d+)') { throw 'Cannot read Java version. Set JAVA_HOME to JDK 17 or later.' }
  if ([int]$Matches.major -lt 17) { throw 'JDK 17 or later is required. Set JAVA_HOME to an installed JDK.' }
  if (-not $env:JAVA_HOME) {
    if ($versionText -match 'java.home\s*=\s*([^\r\n]+)') { $env:JAVA_HOME = $Matches[1].Trim() }
  }
  if (-not (Test-Path (Join-Path $env:JAVA_HOME 'bin/javac.exe'))) { throw 'JAVA_HOME must point to a full JDK, including javac.exe.' }
  return (Join-Path $env:JAVA_HOME 'bin/java.exe')
}
