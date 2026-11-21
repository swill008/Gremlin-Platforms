# Run this yourself (the user), once, in your own PowerShell window:
#   powershell -ExecutionPolicy Bypass -File tools\vm-test\set-test-password.ps1
#
# It asks for a password for the test machine's account "gremlintest" (use a
# test-only password, not one you use anywhere else) and writes:
#   E:\VM\GremlinTest\autounattend.xml   the answer file with the password filled in
#   E:\VM\GremlinTest\vm-test-cred.xml   the same sign-in, encrypted for your
#                                        Windows account only (Export-Clixml), so
#                                        scripts can run commands in the test
#                                        machine without anyone seeing the password
# Claude never sees or types the password.

$ErrorActionPreference = "Stop"
$out = "E:\VM\GremlinTest"
New-Item -ItemType Directory -Force $out | Out-Null
$template = Join-Path $PSScriptRoot "autounattend.template.xml"

$secure = Read-Host "Password for the test machine's account 'gremlintest'" -AsSecureString
$again = Read-Host "Type it again" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringUni(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
$plain2 = [Runtime.InteropServices.Marshal]::PtrToStringUni(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($again))
if ($plain -ne $plain2) { throw "The two passwords differ; nothing was written." }
if ($plain.Length -lt 1) { throw "Empty password; nothing was written." }

$escaped = [Security.SecurityElement]::Escape($plain)
(Get-Content $template -Raw).Replace("__TEST_PASSWORD__", $escaped) |
    Set-Content (Join-Path $out "autounattend.xml") -Encoding UTF8
New-Object Management.Automation.PSCredential("gremlintest", $secure) |
    Export-Clixml (Join-Path $out "vm-test-cred.xml")
$plain = $null; $plain2 = $null
Write-Host "Done: autounattend.xml and vm-test-cred.xml are in $out"
