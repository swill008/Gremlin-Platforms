# Installer early start (incident 2026-11-20 06:37) - INSTCHECK study

Read-only study, 06:39-06:44. Nothing was run or changed.

## Verdict
The starter of PID 22112 (06:37:24) is NOT verified. The disk holds no record of that process
(no process-creation audit, no Sysmon, no Application/System/Security events 06:36-06:39, no
crash.log or system.log line for it; its ImportError is in none of the logs). What is verified
is which candidates are ruled out, and the only ones left are outside the second installer.

Verified from evidence:
- (d) second installer: ruled out. Its log (Gremlin-Platforms-R1-1.0.40-Setup.log): 06:37:18.533
  opened, 18.709 "asking it to quit", 18.748 "took the quit request", 20.388 "quit", 20.405
  "Starting the installation process", files written to 27.978, "Installation process succeeded"
  28.040, the one exe [Run] entry (RestartAfterClose, because ClosedByInstaller and no /LAUNCH)
  at 28.045. DeinitializeSetup (28.601) did not relaunch (Finished = True). Nothing in the .iss
  starts the exe at 06:37:24; the only start calls are the [Run] entries and the
  DeinitializeSetup ExecAsOriginalUser. That 28.045 start is the one in system.log (HidHide start
  06:37:28, "Gremlin UI launching" 06:37:31, terminated 06:37:41): it came up fine, so it is not
  the crashed PID 22112.
- (b) Restart Manager: ruled out. [Setup] has CloseApplications=no, RestartApplications=no, and
  gremlin/, joystick_gremlin.py have no RegisterApplicationRestart.
- (c) self-restart: ruled out. No code in gremlin/ or joystick_gremlin.py respawns
  sys.executable on quit; HKCU Run has no Gremlin entry; no Gremlin scheduled task. The device
  helper log shows only "Ended: closed" at 06:37:19,958 (helper exits with its parent 17268).
- (a) first installer: NOT supported by its code either. After 17268 exited (06:37:19) its
  DeinitializeSetup would only relaunch when "not Finished"; Finished is set at ssPostInstall, so
  it does not. Its [Run] entries are all nowait except vc_redist (skipped, file missing), so by
  the .iss it should not have been waiting on 17268 at all. Its log was overwritten (same /LOG
  path, 06:37:28.608 close of the second run), so its real behaviour cannot be read.

Best-supported but UNVERIFIED: a start that came from outside setup's own code, 4-5 s after
17268 exited (06:37:19-20), i.e. something watching or waiting on 17268 (the first setup run, or
the shell/agent command that launched it and was holding the inherited pipe until 17268 exited,
which would explain "the first installer was still running" without any [Run] wait). If the
first installer really was a live Setup process, its parent/command line is the thing to
capture next time (see "Evidence to capture").

## Can a normal install or in-app update start Gremlin before files are copied?
- Setup's own code: no. [Run] entries run after "Installation process succeeded"; the
  DeinitializeSetup relaunch runs only after a failed/cancelled install, after the old files
  were put back.
- In-app update (gremlin/updater.py setup_arguments: /SILENT /SUPPRESSMSGBOXES /NORESTART /LAUNCH=1):
  the program has already quit, so ClosedByInstaller stays False and only the /LAUNCH=1 [Run]
  entry starts it, after the copy. No early start from setup.
- Not guarded today: anything else (shortcut, a second setup, a person) can start the exe while
  files are copied. There is no [Setup] SetupMutex, and the program checks only its own instance
  lock (joystick_gremlin.py acquire_instance_lock / _check_second_copy), not "setup is running".
  Two setups at once is also unguarded: the second one's PrepareToInstall closed the first
  one's program (this incident), and while setup 1 was mid-flight setup 2 moved files aside.
- The marker file {app}\.update-in-progress exists while files are moved aside (written in
  PrepareToInstall, deleted at ssPostInstall); a program started in that window crashes on
  missing _internal files, exactly the PySide6/libshiboken error seen.

## Fix options (recommended first)
1. Program refuses to start while an install is in progress (smallest, covers every starter).
   At startup (joystick_gremlin.py, before the Qt/PySide import is not possible because the
   import is what fails; do it in the exe's first Python lines or a tiny check before PySide6
   import) look for {install dir}\.update-in-progress; if present wait (bounded, e.g. 60 s, via
   gremlin.clock/threads rules) then start, or show "An update is installing; try again in a
   moment". Files: joystick_gremlin.py, tests. Spec: new statement on page 01 (S173 family)
   and S122 context; needs the user's approval first (change control).
2. Installer refuses to run while another setup of the same app runs: [Setup]
   SetupMutex=GremlinPlatformsSetup (Inno built-in; a second setup waits/stops). Files:
   installer/gremlin_platforms.iss, test_installer_closes_program.py (reads .iss text). Spec:
   S173 gets one sentence ("only one setup runs at a time"); the S121/S122 update statements
   are unchanged. Stops the double-install seen here (setup 2 closing setup 1's program).
3. Keep the relaunch after the install only (already true: [Run] after ssDone) - no change;
   verified above. A tidier variant, `Flags: nowait postinstall` entries are already after
   copy, so nothing to move.
4. Installer waits for the marker/another setup before PrepareToInstall (custom [Code]):
   more code than option 2 for the same effect; not recommended.

Recommended: option 2 first (one line, built-in, no program code), then option 1 only if an
early start by something other than setup is confirmed.

## Evidence to capture next time (cheap)
- Run the setup with /LOG to a unique name per run (e.g. timestamped), so a second run does not
  overwrite the first.
- Before the next try, enable "Audit Process Creation" or log in the program's first lines
  (parent PID and command line) so a start can be attributed; the exe currently logs nothing
  before the PySide import.

## Spec statements touched
- 01 S173 (installer closes the program, starts it again after installing) - option 2 adds a
  sentence; option 1 adds a new statement.
- 01 S121 / S122 (update, failed-update message) - read only; unchanged by either option.
- 01 S120, S123, S124 are unrelated (download disk errors, SSL close, data folder).
