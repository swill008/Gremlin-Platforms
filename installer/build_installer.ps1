# Builds the installer from dist\gremlin_platforms (run pyinstaller first).
# The version comes from version.json so the file name matches the release.
param([string]$Iscc = "")

$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content (Join-Path $root "version.json") -Raw | ConvertFrom-Json).version
if (-not $Iscc) {
    $Iscc = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Iscc) { throw "ISCC.exe not found: install Inno Setup 6 or pass -Iscc." }
if (-not (Test-Path (Join-Path $root "dist\gremlin_platforms\gremlin_platforms.exe"))) {
    throw "dist\gremlin_platforms is missing: run pyinstaller joystick_gremlin.spec first."
}
& $Iscc "/DMyAppVersion=$version" (Join-Path $PSScriptRoot "gremlin_platforms.iss")
if ($LASTEXITCODE -ne 0) { throw "ISCC failed ($LASTEXITCODE)." }
