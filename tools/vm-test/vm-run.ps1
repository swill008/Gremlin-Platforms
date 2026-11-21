# Runs a script block inside the test machine (PowerShell Direct) as the test
# account, which is an administrator there. Run on the host as administrator.
#   vm-run.ps1 -Script { Get-ChildItem C:\ }   or   -File inner.ps1
param(
    [scriptblock]$Script,
    [string]$File,
    [string]$Name = "GremlinTest",
    [string]$Folder = "E:\VM\GremlinTest",
    [object[]]$ArgumentList = @()
)
$ErrorActionPreference = "Stop"
$cred = Import-Clixml (Join-Path $Folder "vm-test-cred.xml")
if ($File) { $Script = [scriptblock]::Create((Get-Content $File -Raw)) }
Invoke-Command -VMName $Name -Credential $cred -ScriptBlock $Script -ArgumentList $ArgumentList
