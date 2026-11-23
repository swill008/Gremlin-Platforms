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
2 not running/off, 3 version mismatch (renumbered 2026-11-23, see the evening batch below). Built as gremlin-ctl.exe
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

## Batch 2026-11-23 evening: research answers (D-13-RESEARCH, S25-S31)

Shared names every agent works to:

- `control_api.CallError(text, code="failed")`; `.code` in
  {"bad_args", "unknown_call", "not_found", "not_ready", "refused", "busy",
  "timeout", "too_large", "failed"} (`control_api.CODES`). Error answer:
  {"ok": false, "error": text, "code": code}. `WindowError(CallError)` keeps
  its name and takes a code.
- `control_api.register(name, handler, *, main_thread, timeout_s, summary,
  args=None)`; `args` is `{name: control_api.Arg(...)}` with
  `Arg(type, required=False, help="", min=None, max=None, choices=None)`,
  type one of "str", "int", "float", "bool", "object", "list", "any".
  control_api checks args before the handler: unknown, missing, wrong type,
  out of range -> CallError(..., "bad_args"). `calls()` / `help` give
  [{"name", "summary", "args": {name: {"type", "required", "help", "min",
  "max", "choices"}}}].
- Message style (S27): one sentence ending in ".", names in 'quotes',
  missing argument "<call> needs <argument>.".
- `threads.main_call_wait`: a job not started when the caller gives up is
  dropped (never runs); a running one -> TimeoutError whose text ends
  "it may still finish." -> code "timeout".
- gremlin-ctl exits: 0 ok, 1 failed (incl. stopped answering / closed mid
  call), 2 typed wrong, 3 version, 4 not running / control off.
  `cli.EXIT_OK, EXIT_CALL_ERROR, EXIT_USAGE = 2, EXIT_VERSION = 3,
  EXIT_NOT_RUNNING = 4`. `client.ClientError` subclasses keep their names;
  `client.CallError` (its existing name) carries `.code`; a new `client.StoppedAnswering`
  (exit 1).
- `--json` error on stdout: {"ok": false, "code", "error", "exit"}.
- window.open argument renamed `command` -> `id`.
- Backend gives the API public reasons (no private reads):
  `Backend.last_load_problem() -> str` (the reason the last load failed, ""
  if none) and `Backend.last_save_problem() -> str` (why the last save
  failed). control_api.profile.load / profile.save put them in the error.
- `commands` / `command.run` before the menu bridge is ready -> `not_ready`;
  a command that throws in QML -> `failed` with its text.
