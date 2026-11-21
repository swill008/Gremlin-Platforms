# Creates the Gremlin-Platforms driver test machine in Hyper-V and installs
# Windows 11 unattended (answer 21a, 2026-11-21). Run as administrator after
# the restart that finishes turning on Hyper-V, and after the user has run
# set-test-password.ps1.
#   powershell -ExecutionPolicy Bypass -File tools\vm-test\create-vm.ps1
#
# Generation 2, Secure Boot (Microsoft Windows template), a virtual TPM (Quick
# Create does not reliably add one), 4 processors, 8 GB, 80 GB dynamic disk,
# Default Switch, Guest Service Interface on (Copy-VMFile). Then it waits for
# the install to finish and takes the checkpoint "clean".

param(
    [string]$Name = "GremlinTest",
    [string]$Folder = "E:\VM\GremlinTest",
    [string]$WindowsIso = "E:\VM\GremlinTest\Windows11_Client_x64_en-us_26300_9457.iso",
    [int]$InstallTimeoutMin = 90
)
$ErrorActionPreference = "Stop"

function New-AnswerIso([string]$XmlPath, [string]$IsoPath) {
    # Builds a small ISO holding autounattend.xml with Windows' own IMAPI2FS;
    # Windows Setup finds the file on a second DVD drive.
    $stage = Join-Path $env:TEMP "gremlin-answer-iso"
    Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory $stage | Out-Null
    Copy-Item $XmlPath (Join-Path $stage "autounattend.xml")
    $fs = New-Object -ComObject IMAPI2FS.MsftFileSystemImage
    $fs.FileSystemsToCreate = 3   # ISO9660 + Joliet
    $fs.VolumeName = "ANSWER"
    $fs.Root.AddTree($stage, $false)
    $stream = $fs.CreateResultImage().ImageStream
    $out = [System.IO.File]::Create($IsoPath)
    try {
        $buffer = New-Object byte[] 65536
        $read = [ref]0
        $istream = [System.Runtime.InteropServices.ComTypes.IStream]$stream
        $ptr = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(4)
        try {
            do {
                $istream.Read($buffer, $buffer.Length, $ptr)
                $n = [System.Runtime.InteropServices.Marshal]::ReadInt32($ptr)
                if ($n -gt 0) { $out.Write($buffer, 0, $n) }
            } while ($n -gt 0)
        } finally { [System.Runtime.InteropServices.Marshal]::FreeHGlobal($ptr) }
    } finally { $out.Close() }
}

function Send-AnyKey([string]$VmName, [int]$Seconds = 20) {
    # Generation 2 machines show "Press any key to boot from CD or DVD";
    # tap Enter through the window so the Windows ISO boots.
    $vm = Get-CimInstance -Namespace root\virtualization\v2 -ClassName Msvm_ComputerSystem -Filter "ElementName='$VmName'"
    $kbd = Get-CimAssociatedInstance -InputObject $vm -ResultClassName Msvm_Keyboard
    $end = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $end) {
        Invoke-CimMethod -InputObject $kbd -MethodName TypeKey -Arguments @{ keyCode = 13 } | Out-Null
        Start-Sleep -Milliseconds 500
    }
}

if (-not (Get-Command New-VM -ErrorAction SilentlyContinue)) { throw "Hyper-V commands missing: restart Windows first." }
if (Get-VM -Name $Name -ErrorAction SilentlyContinue) { throw "A machine named $Name already exists." }
foreach ($f in $WindowsIso, (Join-Path $Folder "autounattend.xml"), (Join-Path $Folder "vm-test-cred.xml")) {
    if (-not (Test-Path $f)) { throw "Missing $f (download the ISO / run set-test-password.ps1 first)." }
}

$answerIso = Join-Path $Folder "answer.iso"
New-AnswerIso (Join-Path $Folder "autounattend.xml") $answerIso

$vhd = Join-Path $Folder "$Name.vhdx"
New-VM -Name $Name -Generation 2 -MemoryStartupBytes 8GB -NewVHDPath $vhd -NewVHDSizeBytes 80GB `
    -SwitchName "Default Switch" -Path $Folder | Out-Null
Set-VM -Name $Name -ProcessorCount 4 -StaticMemory -CheckpointType Standard -AutomaticCheckpointsEnabled $false
Set-VMFirmware -VMName $Name -EnableSecureBoot On -SecureBootTemplate MicrosoftWindows
Set-VMKeyProtector -VMName $Name -NewLocalKeyProtector
Enable-VMTPM -VMName $Name
Enable-VMIntegrationService -VMName $Name -Name "Guest Service Interface"
$dvd = Add-VMDvdDrive -VMName $Name -Path $WindowsIso -Passthru
Add-VMDvdDrive -VMName $Name -Path $answerIso
Set-VMFirmware -VMName $Name -FirstBootDevice $dvd

Start-VM -Name $Name
Send-AnyKey $Name

# The install is finished when PowerShell Direct can sign in.
$cred = Import-Clixml (Join-Path $Folder "vm-test-cred.xml")
$deadline = (Get-Date).AddMinutes($InstallTimeoutMin)
$ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 30
    try {
        $os = Invoke-Command -VMName $Name -Credential $cred -ScriptBlock { (Get-CimInstance Win32_OperatingSystem).Caption } -ErrorAction Stop
        Write-Host "Ready: $os"
        $ready = $true
        break
    } catch { Write-Host ("waiting for Windows setup ... " + (Get-Date -Format HH:mm)) }
}
if (-not $ready) { throw "Windows was not ready after $InstallTimeoutMin min." }

# Eject both ISOs so later restarts boot from the disk, then the clean point.
Get-VMDvdDrive -VMName $Name | Set-VMDvdDrive -Path $null
Stop-VM -Name $Name
Checkpoint-VM -Name $Name -SnapshotName "clean"
Write-Host "Checkpoint 'clean' taken."
