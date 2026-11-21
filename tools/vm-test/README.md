# Driver test machine (Hyper-V)

For the driver setup tests that need a separate Windows (claude/plans/driver-setup-installer.md,
answers 11a and 21a). Outputs go to `E:\VM\GremlinTest\`, never into the repo.

1. Windows 11 ISO in `E:\VM\GremlinTest\` (downloaded 2026-11-21 from Microsoft's page;
   English x64, build 26300.9457; SHA-256 must be
   `BD4307DF32BC8AF33B39CCECB1174AEB345386630F89A2B86C7A4E36B55EA650`).
2. The user runs `set-test-password.ps1` once (asks for the test account's password; writes
   `autounattend.xml` and the encrypted `vm-test-cred.xml`). Claude never sees the password.
3. After the restart that finishes turning on Hyper-V: `create-vm.ps1` (as administrator) creates
   the machine (Gen 2, Secure Boot, virtual TPM, 8 CPUs, 16 GB, 80 GB), installs Windows unattended,
   then takes the checkpoint "clean".
4. Every driver test starts with `Restore-VMCheckpoint -VMName GremlinTest -Name clean`.
