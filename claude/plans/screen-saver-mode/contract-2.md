# Screen Saver Mode, batch 2: tracing, drivers, "never" fix (2026-11-15)

User (2026-11-15, after trying 1.0.38 installed): "we need to add tracing to this portion of the program for
debugging"; 28 a (Ignore works for drivers and services too); 29 a (fix the "never" bug and add tracing).
Base: contract.md (same rules for every agent apply).

## Facts checked on the user's PC (2026-11-15, elevated, then undone)
- `powercfg /requestsoverride DRIVER "USB Audio 2.0 (USB\VID_0DB0&PID_CD0E&MI_00\9&9c4d365&0&0000)" SYSTEM` is
  accepted; the name is exactly the text after "[DRIVER] " in `powercfg /requests`. Removing:
  `powercfg /requestsoverride DRIVER "<name>"` (no types). `/requestsoverride` lists it under [DRIVER] as
  "<name> SYSTEM" (name may contain spaces, brackets, backslashes and &; the types are the trailing upper-case words).
- Real `/requests` output: a request line is followed by an optional detail line ("An audio stream is currently in
  use.", "Electron"); overridden programs still appear in `/requests` (the override only stops their effect).
- The user's overrides: [PROCESS] "RustDesk.exe DISPLAY SYSTEM AWAYMODE", [DRIVER] "FxSound Audio Enhancer SYSTEM".
- Windows' display-off time is 300 s (AC); the window showed "never" because status is only filled by tick(),
  which doesn't run while Screen Saver Mode is off.
- SERVICE form is untested (no service request on this PC); build it the same way, say so as not verified.

## Changes
1. **Never bug (S5):** `ScreenSaverMode.status()` while off (or before the first tick) must carry Windows' current
   wait for the chosen action (`windows_wait_s`, read through WindowsApi, cheap) so the window shows "5 min".
2. **Drivers and services (S14):** `ProgramRequest` gains `kind: str` ("PROCESS" | "DRIVER" | "SERVICE"; name =
   exe file name for PROCESS, the full text for DRIVER/SERVICE, detail line kept as `detail: str`).
   `set_ignored(name, ignored, kind="PROCESS", runner=None)`. Name checks: PROCESS = bare .exe name as now;
   DRIVER/SERVICE = non-empty, no double quote, no line breaks, length <= 260. The command quotes the name.
   Every row gets the switch (no "not a program file name" refusal for drivers/services).
3. **Tracing (new S16, page 01 Tracing):** a **Screen Saver Mode** tick on the Trace tab, next to HidHide's tick, in
   gremlin/trace.py (stored like `_CFG_HIDHIDE`). API (SSM-TRACE owns it):
   `trace.screen_saver_on() -> bool`, `trace.set_screen_saver(on: bool) -> None`,
   `trace.screen_saver(text: str) -> None` (writes one trace line, control "Screen Saver Mode", only while tracing is
   on and the tick is on; cheap no-op otherwise). Lines (each owner writes its own):
   - core: listener started / stopped / failed (with Windows error), countdown started (wait, from Windows or typed),
     hold began / ended (reason), action fired (which, result), problem changed (text), settings applied.
   - scan: each Refresh Devices run (devices found, each rate), each list_requests / set_ignored run: the exact
     command line, exit code, refused / timeout, the raw output (trimmed to 4 KB), parsed rows, and the check result.
   - model: button presses and the message shown.
   Errors (exceptions, refusals, failed checks) ALSO go to the normal log (`logging.getLogger("system")`) even with
   tracing off, so a failure is never silent.

## Owners
| Agent | Files |
|---|---|
| SSM-CORE2 | gremlin/screen_saver_mode.py, test/unit/test_ssm_core.py |
| SSM-SCAN2 | gremlin/power_requests.py, gremlin/hid_report_scan.py, test/unit/test_ssm_scan.py |
| SSM-TRACE | gremlin/trace.py and the Trace tab's tick (the QML/model file that shows the HidHide tick), a new test test/unit/test_ssm_trace.py, existing trace tests that pin the tick list |
| SSM-UI2 | gremlin/ui/screen_saver_mode_model.py, qml/WindowScreenSaverMode.qml, test/unit/test_ssm_ui.py, ssm_ui_fakes.py, ssm_ui_smoke.py, test/unit/test_ssm_e2e.py (update for kind/driver rows) |
| SSM-DOCS2 | claude/program-map/12-screen-saver-mode.md (S14 widened, new S16, sections 2-6, 10, 11, section 12 rows), 01-app-shell.md (Tracing tick list), README counts, glossary, qml/help/tools.js (Screen Saver Mode entry + the Tracing help where ticks are listed) |
Agents code against this contract; other agents' files may not exist in their new form yet: use small fakes.
