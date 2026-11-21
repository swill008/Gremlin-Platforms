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
$dist = Join-Path $root "dist\gremlin_platforms"
if (-not (Test-Path (Join-Path $dist "gremlin_platforms.exe"))) {
    throw "dist\gremlin_platforms is missing: run pyinstaller joystick_gremlin.spec first."
}
# The driver installers the setup carries (01 S188) must be in installer\drivers.
$drivers = Join-Path $PSScriptRoot "drivers"
foreach ($name in @(
    "vJoySetup_v2.2.2.0_Win10_Win11.exe",
    "ViGEmBus_1.22.0_x64_x86_arm64.exe",
    "HidHide_1.5.230_x64.exe",
    "VC_redist.x64.exe"  # the Visual C++ runtime (01 S193), copied to {tmp} only
)) {
    if (-not (Test-Path (Join-Path $drivers $name))) {
        throw "installer\drivers\$name is missing: run 'python tools/fetch_drivers.py' (or add --from <folder> with the files)."
    }
}
# A resolved path, not installer\..\dist: Qt's deepest files are close to the
# 260 character path limit.
& $Iscc "/DMyAppVersion=$version" "/DDistDir=$dist" (Join-Path $PSScriptRoot "gremlin_platforms.iss")
if ($LASTEXITCODE -ne 0) { throw "ISCC failed ($LASTEXITCODE)." }
