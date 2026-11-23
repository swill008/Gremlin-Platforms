# Control API batch: shared contract (2026-11-23)

Approved by the user ("build it now"). Plan and decisions: claude/plans/control-api.md
(read it first). Every agent works to this contract; one owner per file.
If you need something from a file you don't own, ask the lead (report it), don't edit it.

## Owners

| Agent | Owns |
|---|---|
| API | new gremlin/control_api.py; joystick_gremlin.py (start/stop hook only); gremlin/ui/option.py (switch placement + title) |
| WINDOWS | new gremlin/ui/control_windows.py |
| COMMANDS | gremlin/ui/backend.py; qml/Main.qml (command bridge only) |
| CLI | new gremlin_ctl/ package (client.py, cli.py, __main__.py); joystick_gremlin.spec; installer/ |
| MCP | new tools/gremlin_mcp/; .mcp.json; pyproject.toml (dev dependency only) |
| SSM-TRACE | gremlin/screen_saver_mode.py |
| TRACE | gremlin/modules/output.py; gremlin/code_runner.py; gremlin/trace.py |
| TESTS | new test files test/unit/test_control_api*.py, test_gremlin_ctl*.py, test_trace_additions*.py |
| DOCS | claude/program-map/* (new page 13-control-api.md, 01, 06, 12, the trace page, README); claude/glossary.md; qml/help/*.js |

## The switch

Config entry ("global", "control", "allow-other-programs"), PropertyType.Bool,
initial False, expose=True, description "Lets the gremlin-ctl command line and
other programs on this PC read and control Gremlin-Platforms." Registered in
gremlin/control_api.py. Options › General › group "Control" (after "vJoy"),
title "Allow control from other programs" (option.py _LAYOUT + _KEY_TITLES).
Only the user changes it: the API refuses option.set on this key.

## Pipe, key, endpoint (gremlin/control_api.py)

- PROTOCOL_VERSION = 1.
- multiprocessing.connection Listener(family="AF_PIPE", authkey=key), address
  r"\\.\pipe\gremlin-platforms-api-" + 16 random hex chars (same method as
  gremlin/device_disable.py MpListener). Listener on a gremlin.threads thread,
  bounded waits, hang-proof (program thread rules).
- While the switch is on and the program runs: key = 32 random bytes; the
  program writes `<user data folder>/api/endpoint.json`
  {"address": str, "key": hex str, "version": 1, "pid": int}. The user data
  folder is the one config.py / util use (C:\Users\<user>\Gremlin Platforms).
  Switch off or program exit: listener stops, endpoint.json deleted.
- Messages: Connection.send_bytes/recv_bytes of UTF-8 JSON.
  Request {"call": str, "args": {..}}; reply {"ok": true, "result": any} or
  {"ok": false, "error": str}. One call at a time per connection.
- Call "hello" -> {"version": 1, "program_version": str}.

## Call registry (gremlin/control_api.py)

    register(name: str, handler: Callable[[dict], Any], *, main_thread: bool = False,
             timeout_s: float = 10.0, summary: str = "") -> None
    calls() -> list[dict]   # [{"name", "summary"}], used by "help"

main_thread=True handlers run on the Qt main thread (gremlin.threads main
call) with a bounded wait (timeout_s); on timeout the reply is an error and
the program carries on. Every call writes one system log line:
"API: <call> <short args> -> ok|error: <text>".
Owning modules register their calls at import; control_api imports
gremlin.ui.control_windows and the backend bridge lazily (after the UI exists)
via a hook `control_api.attach_ui()` called from joystick_gremlin.py.

Calls owned by API: hello, help, state, devices, run.start, run.stop,
profile.load {path}, profile.save, option.get {key "section/group/name"},
option.set {key, value}, options.list, trace.on {category?}, trace.off
{category?}, trace.status, log {which: "system"|"trace", lines: int}.
Long ones (profile.load, screenshots) timeout_s=30.
History (3a): profile and Options changes made through the API go into
Tools › History marked "by API" using History's existing recording path; if
Options changes are not recorded in History today, record them for API calls
only and say so in the report.

## Calls owned by COMMANDS (gremlin/ui/backend.py + qml/Main.qml)

"commands" -> [{"id", "text", "group"}] from qml/main_commands.js
commandList(); "command.run" {id} -> {"ran": bool}. main_thread=True.
Python side exposes backend functions the handlers use; registers with
control_api.register in attach_ui time (control_api calls
backend.register_api_calls(control_api) — COMMANDS implements it).

## Calls owned by WINDOWS (gremlin/ui/control_windows.py)

All main_thread=True; windows named by their shown title (case-insensitive):
window.list -> [{"title", "visible"}]; window.open {command} (runs the menu
command id through COMMANDS' bridge); window.close {window};
window.read {window} -> {"title", "items": [{"kind": "text"|"button"|"field"|"check",
"name", "text", "enabled"}]}; window.screenshot {window, path} (QQuickWindow
grab of the window only, PNG, timeout 30); window.press {window, button}
(by visible text or objectName); window.type {window, field, text}.
Every press/type logs "by API". Register via
`control_windows.register_api_calls(control_api)` called from attach_ui.

## Client library and CLI (gremlin_ctl/)

client.py: `connect(timeout_s=5.0) -> Client` (reads endpoint.json, checks
version via hello); `Client.call(name, **args) -> Any`; errors `NotRunning`
(no endpoint / pipe gone: "Gremlin-Platforms isn't running"), `Off`
(message: "Control from other programs is off in Options › General"; used
when endpoint.json is missing but the program process exists — or simply
merge into NotRunning with both reasons), `VersionMismatch`, `CallError`.
Pure Python, no Qt, no gremlin imports (so the exe is small).
cli.py: commands mirror the calls (`gremlin-ctl state`, `run start|stop`,
`commands`, `run-command <id>`, `option get|set`, `options`, `trace on|off|status`,
`log`, `windows`, `window open|close|read|screenshot|press|type`, `help`);
readable text by default, `--json` raw. Exit codes 0 ok, 1 call error,
2 not running/off, 3 version mismatch. Built as gremlin-ctl.exe
(console) next to gremlin_platforms.exe, shipped by the installer.

## MCP server (tools/gremlin_mcp/server.py)

Uses gremlin_ctl.client only. One tool per call (gremlin_state,
gremlin_run_start, ..., gremlin_window_press). stdio server; .mcp.json entry
"gremlin" runs it with the Poetry venv Python. "mcp" package as a dev
dependency only; not in the installer.

## Tracing (no API interface)

SSM-TRACE: keep-off wake trace line names the last input Windows saw just
before it (device name, kind, counted or not) and time since the last vJoy /
Xbox write (read via a small public function TRACE adds in output.py:
`output.last_write_age_s() -> float | None` covering vJoy and Xbox). Game
controller (HID) reports are listened to only while the displays are kept
off, only to name the source; nothing new counts as input.
TRACE: output trace line at each keep-alive reset "vJoy N keep-alive reset
(idle 60 s)"; system log "Profile started (<name>)" / "Profile stopped
(<name>)" in code_runner; trace.py writes "--- YYYY-MM-DD ---" when tracing
turns on and at the first line after midnight; plus output.last_write_age_s().
