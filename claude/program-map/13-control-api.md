# Control from other programs (control API, gremlin-ctl)

**Approved 2026-11-23 (user: "build it now"); being built 2026-11-23 to
`claude/plans/control-api-contract.md`.** Written from the user's decisions of
2026-11-23 in `claude/plans/control-api.md` (section 12). Sections 2-6 and 11
are written from the contract; items marked "names to confirm" are to be
checked against the build agents' reports.

## 1. Purpose

During the 2026-11-22 display-wake investigation, reading Screen Saver Mode's
wake count, whether a profile ran, and turning tracing on all needed outside
scripts or the user. Control from other programs lets the user, other users,
scripts and Claude read the program's state and control it from the same PC:
the `gremlin-ctl` command line, and a development-only MCP server for Claude
Code. It is off until the user switches it on in Options.

## 2. Files

Being built 2026-11-23 (`claude/plans/control-api-contract.md`; names to confirm):
- `gremlin/control_api.py` (new, agent API): the switch's setting (`global/control/allow-other-programs`), the listener (a private Windows named pipe, `multiprocessing.connection` `Listener(family="AF_PIPE", authkey=key)`, the same method as `gremlin/device_disable.py`), the endpoint file, `PROTOCOL_VERSION` (1), the call registry `register(name, handler, *, main_thread=False, timeout_s=10.0, summary="")` and `calls()`, `attach_ui()`, and the calls hello, help, state, devices, run.start, run.stop, profile.load {path}, profile.save, option.get / option.set {key[, value]}, options.list, trace.on / trace.off {category?: hidhide, screen-saver-mode, window, timing, osc or osc/<area>}, trace.status, log {which, lines}. Dispatch checks the switch first; one call at a time; main-thread calls bounded. The listener checks the key on each connection with 5 s bounded reads, closes a connection idle for 120 s, and takes at most 4 connections at once.
- `gremlin/ui/control_windows.py` (new, agent WINDOWS): the window calls window.list, window.open, window.close, window.read, window.screenshot, window.press, window.type; `register_api_calls(control_api)`.
- `gremlin/ui/backend.py` (agent COMMANDS; page 01): `Backend.setCommandBridge` (called from `Main.qml` `Component.onCompleted`), `Backend.command_list()`, `Backend.run_command_id(id)`, `Backend.register_api_calls(control_api)` with the calls commands (main-window commands only, owner "main", 45 today) and command.run (refuses other windows' commands).
- `qml/Main.qml` (agent COMMANDS; page 01): the command bridge only (runs a command id from `qml/main_commands.js` `commandList()`).
- `gremlin/ui/option.py` (agent API; page 01): `shown_setting` / `change_setting`, shared by the Options rows and the API; the **Control** group in Options › General (after vJoy) and the title **Allow control from other programs** (`_LAYOUT`, `_KEY_TITLES`).
- `joystick_gremlin.py` (agent API; page 01): starts and stops control from other programs with the program, and calls `control_api.attach_ui()` once the UI exists.
- `gremlin_ctl/` (new package, agent CLI): `gremlin_ctl/client.py` (the client library: `connect(timeout_s=5.0) -> Client`, `Client.call(name, **args)`, errors `NotRunning`, `Off`, `VersionMismatch`, `CallError`; pure Python, no Qt, no `gremlin` imports), `gremlin_ctl/cli.py` (the commands, readable text or `--json`, exit codes), `gremlin_ctl/__main__.py`, `gremlin_ctl/__init__.py`. Built as `gremlin-ctl.exe` (console) by `joystick_gremlin.spec`, shipped by the installer (`installer/`) next to `gremlin_platforms.exe` (01 S152).
- `tools/gremlin_mcp/server.py`, `tools/gremlin_mcp/README.md` (new, agent MCP; development only, not in the installer): an MCP stdio server with 22 tools, one per API call (`gremlin_state` … `gremlin_window_type`), using `gremlin_ctl.client` only and connecting again for each call; `.mcp.json` (new) entry "gremlin" (stdio) runs it with the Poetry venv Python; the `mcp` package (2.3.x) is in a new Poetry dev group (`[tool.poetry.group.dev.dependencies]` in `pyproject.toml`), not in the installer.
- Help (agent DOCS): `qml/help/getting_started.js` topic `getting-started-control` (Control the program from other programs); `qml/help/options_profile.js` topic `options-profile-general` (the Control group).

Note: `gremlin_ctl/` is under the change control guards (01 S156, 2026-11-23); `tools/gremlin_mcp/` is development only and stays outside.

## 3. What it owns

| Data | Owner | Written by | Read by |
|---|---|---|---|
| The switch **Allow control from other programs** (S2) | the setting `global/control/allow-other-programs` (Bool, off at first, registered in `control_api.py`) | the user in Options › General › Control only; `option.set` refuses this key | `control_api` at start and on change |
| The pipe's address and key (S12) | `control_api` (address `\\.\pipe\gremlin-platforms-api-` + 16 random hex characters; key 32 random bytes, made each time the listener starts) | the listener start | `%USERPROFILE%\Gremlin Platforms\api\endpoint.json` (`util.userprofile_path`, not the movable data folder) {"address", "key" (hex), "version", "pid"}, read by `gremlin_ctl.client` |
| The calls and their summaries (S5, S10) | `control_api` registry (`register`, `calls()`) | each owning module at attach time (`control_api`, `backend.register_api_calls`, `control_windows.register_api_calls`) | the listener; `help` |
| The MCP tools (S1) | `tools/gremlin_mcp/server.py` (22 tools, one per call; development only) | - | Claude Code through `.mcp.json` |
| The protocol (S9) | `control_api` (program side), `gremlin_ctl/client.py` (the only client code that knows it) | - | the CLI and the MCP server through the client |

## 4. Entry points

| Entry | Where | What runs |
|---|---|---|
| Options › General › Control › **Allow control from other programs** turned on or off (S2) | the setting's change → `control_api` | on: the listener starts and the endpoint file is written; off: the listener stops and the file is deleted |
| Program start / quit | `joystick_gremlin.py` (start/stop hook; `control_api.attach_ui()` once the UI exists) | the listener starts when the switch is on; at quit it stops and the endpoint file is deleted |
| A call arriving on the pipe | the listener thread | the registered handler; `main_thread=True` handlers run on the Qt main thread with a bounded wait (S9) |
| `gremlin-ctl <command>` (S11) | `gremlin-ctl.exe` / `python -m gremlin_ctl` | `gremlin_ctl.cli` → `gremlin_ctl.client` |
| An MCP tool call from Claude Code (S1) | `tools/gremlin_mcp/server.py` (stdio, from `.mcp.json`) | `gremlin_ctl.client` (a new connection per call) |
| The command bridge | `Main.qml` `Component.onCompleted` → `Backend.setCommandBridge` | `Backend.command_list()`, `Backend.run_command_id(id)` |

## 5. Talks to

| Who | How | What |
|---|---|---|
| Settings (page 01) | the setting `global/control/allow-other-programs`; `option.get` / `option.set` / `options.list` read and change other settings | the switch; Options values |
| Run / Stop, profiles (pages 04, 06) | run.start, run.stop, profile.load {path}, profile.save, through the program's own Run and File paths | the running profile |
| The menu command list (page 01 S65) | `qml/main_commands.js` `commandList()` through `backend` and the `Main.qml` bridge | commands, command.run, window.open |
| Tracing (page 01 S146-S151) | `gremlin.trace` (on/off; the switchable rows from `trace.categories()`) | trace.on, trace.off, trace.status; log {which: "trace"} |
| The system log (page 01) | `logging` | one line per call except the version handshake (`hello`): "API: <call> <short args> -> ok\|error: <text>"; window press and type say "by API" (S8) |
| History (page 08) | History's existing recording path (`begin_group` with {"by": "api"} for `option.set`; `history.made_by("api")` around `profile.save`) | profile and Options changes made through the API, marked "by API" (S7) |
| Screen Saver Mode (page 12), Health (page 01 S197), devices (page 02; `device_initialization.joystick_devices()` and `modules/store.known_devices()`) | read-only status reads | state, devices |
| Qt windows (QQuickWindow) | `control_windows` on the main thread | list, open, close, read, grab (screenshot), press, type (S6) |

## 6. Threads and timers

| Thread or timer | Started by | Does | Ends |
|---|---|---|---|
| The listener thread | `control_api` through `gremlin.threads`, only while the switch is on and the program runs | accepts one connection at a time, reads requests, runs handlers; bounded waits; never blocks the main thread | switch off or quit (bounded stop) |
| Main-thread calls | `gremlin.threads` main call from the listener thread, bounded by the call's `timeout_s` (10 s; 30 s for profile.load and window.screenshot) | runs `main_thread=True` handlers (commands, windows, Run, profile, options) | on return, or on timeout the reply is an error and the program carries on (S9) |

Off (S2): no listener, no thread, no endpoint file.

## 7. Rule breaks

None planned. Layer rule: calls use the program's own paths (Run / Stop, File, Options, the menu command list, tracing); nothing touches vJoy, ViGEm or hardware directly. Program thread rules: the listener runs on a `gremlin.threads` thread with bounded waits; the program never waits on the API (S9).

## 8. Behaviour spec

- **S1** **Three layers, one owner each.** (1) The API in the program: a private Windows named pipe with a secret key (the same method as the device helper); the key is written to a file in the user's Gremlin Platforms folder; it is the only part that touches the program. (2) The client library: one Python module that connects to the pipe and makes the calls, the only code that knows the protocol. (3) Front ends on the library: the command line `gremlin-ctl.exe`, shipped in the installer next to `gremlin_platforms.exe`, with a Help page; and an MCP server in the repo (`tools/gremlin_mcp/`), started by Claude Code from the project's `.mcp.json`, development only, its package a dev dependency, not in the installer. [decided 2026-11-23, user: shape agreed, 6a, 2a]
- **S2** **The switch.** Options › General, group **Control** (after vJoy), **Allow control from other programs**, off by default; its description: "Lets the gremlin-ctl command line and other programs on this PC read and control Gremlin-Platforms." Only the user changes it: the API cannot turn itself on or off (`option.set` on this key is refused). Local PC only. With the switch off, a client's answer says control from other programs is off, and nothing happens. [decided 2026-11-23, user: 1a, 5a]
- **S3** **What can be read.** The running profile, devices and whether each is plugged in, Screen Saver Mode's state and wake counts, the Health count, tracing on or off, and the last N log lines (system or trace). [decided 2026-11-23, user: 1c] [built 2026-11-23: `devices` lists the plugged-in devices, then the other devices the program knows (`store.known_devices()`), each with `plugged_in`] [test: `test_control_api.py::test_devices_lists_known_devices_that_are_not_plugged_in`]
- **S4** **What can be done.** Start and stop the profile; load and save a profile; tracing categories on and off; run any menu command by its id from the menu command list (`qml/main_commands.js`); read and change Options settings (except the switch, S2); window actions (S6). [decided 2026-11-23, user: 1c]
- **S5** **Commands come from the menu command list,** so a new menu command needs no API work. [decided 2026-11-23, user: design for change]
- **S6** **Window actions.** Windows are named by their shown title. A client can list the windows, open one by its menu command id, close one, read its visible text, buttons, fields and checks as a list, take a screenshot of that window only to a PNG file, press a named button and type into a named field. Windows the API opens appear where the program normally opens them. Window actions are allowed while the user works. [decided 2026-11-23, user: 3b, 4c, 4a, 3a]
- **S7** **History.** Profile and Options changes made through the API go into Tools › History marked "by API"; start and stop and tracing go to the log only. [decided 2026-11-23, user: 3a] [built 2026-11-23: `option.set` as one group "(by API)" (S22); `profile.save` runs the save inside `history.made_by("api")`, so each entry the save writes (each input, the whole-profile copy) keeps its own kind and subject and gets {"by": "api"} and a title ending "(by API)"; a Restore's title drops the mark] [test: `test_control_api.py::test_option_set_changes_the_setting_and_history_marks_it_by_api`, `::test_history_entries_made_by_the_api_are_marked`, `::test_profile_save_marks_its_history_entries_by_api`]
- **S8** **Every API action is written to the system log** as coming from the API: one line per call, "API: <call> <short args> -> ok" or "-> error: <text>"; a window press or type says "by API". The version handshake (`hello`, which the client sends before every call) is not logged, so one command writes one line. The line is "API: <call> -> ..." for a call with no arguments (no double space) or "API: <call> <args JSON> -> ...". An expected failure answers one plain line of text, window calls too (e.g. "No window called 'No Such Window'", "No button 'Nope' in <title>"), and the log gets only its "-> error: ..." line, no traceback; an unexpected fault still answers "<ExceptionName>: <text>" and logs a traceback. [decided 2026-11-23, user: 3a; hello not logged: user 2026-11-23, 2a; one-line errors and spacing: user 2026-11-23, 2a, 3a, D-13-SWEEP] [test: `test_control_api.py::test_every_call_writes_an_api_line_to_the_system_log`, `test_the_hello_handshake_writes_no_api_line`]
- **S9** **Messages.** A JSON request {"call", "args"} and answer {"ok": true, "result"} or {"ok": false, "error"}. An API version the clients check (`hello`, version 1). One call at a time; a 10 s limit (30 s for screenshots and profile loads); the program never waits on the API: a call that runs on the main thread and goes over its limit answers with an error and the program carries on. [decided 2026-11-23, user: 1a, 2a, 3a, 4a]
- **S10** **The calls,** each a command-line command and an MCP tool: `state` (version, running profile, mode, tracing on or off, Health count, Screen Saver Mode state and wake counts); `devices`; `run start`, `run stop`; `profile load <file>`, `profile save`; `commands` (menu command ids and names); `run-command <id>`; `option get <section/group/name>`, `option set <key> <value>`, `options list`; `trace on|off [category]`, `trace status`; `log [system|trace] [last N]`; `windows`, `window open <command id>`, `window close <name>`, `window read <name>`, `window screenshot <name> <file.png>`, `window press <name> <button>`, `window type <name> <field> <text>`; `help`. [decided 2026-11-23, user: 1a, 2a, 3a, 4a]
- **S11** **The command line** prints readable text, and raw JSON with `--json` for scripts. Exit codes: 0 done, 1 the call failed, 2 the program isn't running or control from other programs is off, 3 version mismatch. [decided 2026-11-23, user: 2a; exit codes from the approved contract]
- **S12** **The key.** While the switch is on and the program runs, the program makes a new random key and pipe name and writes them to `%USERPROFILE%\Gremlin Platforms\api\endpoint.json` (the user's Gremlin Platforms folder, not the movable data folder); switching off or quitting stops the listener and deletes the file. [decided 2026-11-23, user: shape agreed; file layout from the approved contract]

Details added by the build agents (approved by the user 2026-11-23: answers 2a, 3a, 4a and, for S17, a):
- **S13** `window.close` refuses the main window. [user confirmed 2026-11-23: 3a]
- **S14** A mouse area counts as a button for `window.read` and `window.press` only when it has an object name. [user confirmed 2026-11-23: 3a]
- **S15** `window.read` rows also give "checked" for check boxes and "placeholder" for fields. [user confirmed 2026-11-23: 3a]
- **S16** `window.press` and `window.type` work on a hidden window when the item itself is set visible. [user confirmed 2026-11-23: 3a]
- **S17** `commands` lists only the main window's commands (owner "main", 45 today), and `command.run` refuses other windows' commands. An id that isn't one of these commands (unknown, or another window's) is an error: the call fails with "No command called '<id>'" (gremlin-ctl exit 1); a known command that can't be used now answers {"ran": false}. [user confirmed 2026-11-23: a; unknown ids an error: user 2026-11-23, 1a, D-13-SWEEP] [test: `test_control_api.py::test_command_run_with_an_unknown_id_is_an_error`]
- **S18** The system log line for each call (S8) is written at Warning level, so it shows at the default Diagnostic logs level. [user confirmed 2026-11-23: 2a]
- **S19** `option get` / `option set` work only on settings Options shows; settings with their own custom rows, and the switch (S2), are refused. [user confirmed 2026-11-23: 3a]
- **S20** `profile load` refuses while the open profile has unsaved changes; `profile save` refuses an Untitled profile. [user confirmed 2026-11-23: 3a]
- **S23** `gremlin-ctl call <name> [json]` makes any call by its name, with its arguments as JSON, so a new call can be used before it has its own command (advanced use). [user approved 2026-11-23: 4a] [test: test_gremlin_ctl_cli.py]
- **S21** `devices` lists real devices only: the plugged-in devices (name, label, id, virtual, vJoy id, axes, buttons, hats), then each known hardware device that isn't plugged in (the open profile's devices and saved module files, `store.known_devices()`), once each by its device id, with `plugged_in` false and its counts empty (S3). Device ids are always lower case with dashes and no braces (the form the Library and profiles use), plugged in or not. The `help` summary and `gremlin-ctl devices` help say "devices, plugged in or not". Not listed: known entries without a device id, the program's own inputs (Keyboard, OSC, Logical Device) and the output modules (vJoy N, the Xbox pad), as `device_class` classes them. [user 2026-11-23, 2a; id case and help wording: user 2026-11-23, 3a, D-13-SWEEP] [test: `test_control_api.py::test_devices_lists_real_devices_only_each_once`, `test_gremlin_ctl_cli.py::test_devices_help_says_plugged_in_or_not`]
- **S22** An `option set` change goes into History as "Changed <setting> (by API)" (S7). [user confirmed 2026-11-23: 3a]

## 9. Questions for the user

- ~~Q1~~ (2026-11-23) S13-S22: details the build agents chose. Answered 2026-11-23 (2a, 3a; S17: a).
- ~~Q2~~ (answered by decision 3a, D-13-HISTORY; built 2026-11-23, S7) `profile save` through the API marked "by API" in History.

## 10. Known gaps

- CTL-NOT-TRIED (open, 2026-11-23): S1-S12 built 2026-11-23 with tests (section 11); not yet tried from the installed program with `gremlin-ctl.exe` on the user's PC. Names in sections 2-6 and 11 to confirm from the agents' reports.
- CTL-GUARD (closed 2026-11-23, user 1a: `gremlin_ctl/` added to both guards and CLAUDE.md rule 5, 01 S156): `gremlin_ctl/` is new program code (built into `gremlin-ctl.exe` and shipped) but is outside the program folder lists of `test/unit/test_program_map_covers_files.py`, `test/unit/test_spec_line.py` and `.claude/CLAUDE.md` change control rule 5 (01 S156); adding it changes S156 and needs the user's OK. `tools/gremlin_mcp/` is development only and stays outside.
- CTL-READ-LABELS (open, 2026-11-23): `window.read` can't see a control's accessible name (`Accessible.name`) or a label that sits beside a field, so such a field or button may be listed without its name.
- CTL-MCP-SCREENSHOT (open, 2026-11-23): the MCP screenshot tool returns the file path, not the picture.
- ~~CTL-HISTORY-OPTIONS~~ (closed 2026-11-23, agent API's report): `option.set` changes go to History as "Changed <setting> (by API)" (S22).
- ~~CTL-SAVE-HISTORY~~ (closed 2026-11-23, agent FIX-API): `profile.save` runs inside `history.made_by("api")`; each entry it writes is marked {"by": "api"} and "(by API)" (S7).
- ~~CTL-TRACE-CATEGORIES~~ (closed 2026-11-23, agent FIX-API): `gremlin/trace.py` owns the list (`trace.categories()`, `Category`, `NOT_CATEGORIES`); `control_api.py` reads it; guard `test_trace_additions.py::test_every_trace_switch_setting_is_a_category` fails on a new debug/trace setting that is neither a category nor in `NOT_CATEGORIES`.
- ~~CTL-DEVICES-KNOWN~~ (closed 2026-11-23, agent FIX-API): `devices` listed plugged-in devices only, against S3; it now adds the known devices with `plugged_in` false (S21).
- ~~CTL-DEVICES-REAL~~ (closed 2026-11-23, agent FIX-DEV): `devices` also listed the built-in inputs, the vJoy output modules and id-less known entries, against S21; it now lists real devices only, each once.
- ~~CTL-RUN-UNKNOWN~~ (closed 2026-11-23, agent FIX-A, D-13-SWEEP 1a): `command.run` with an unknown id answered {"ran": false} like a command that can't be used now; it is now an error (S17).
- ~~CTL-DEVICES-HELP~~ (closed 2026-11-23, agents FIX-A and FIX-B, D-13-SWEEP 3a): the `devices` help said plugged-in devices only; it now says plugged in or not (S21).
- ~~CTL-HELLO-LOG~~ (closed 2026-11-23, agent FIX-DEV): every gremlin-ctl command wrote two log lines (its `hello` handshake too); `hello` is no longer logged (S8).

## 11. Size and test coverage

Being built 2026-11-23 (agent TESTS; names to confirm): `test/unit/test_control_api*.py` (the switch off by default and refused through `option.set`, the endpoint file written and deleted, the version check, the system log line per call, main-thread timeout answers an error, History "by API"; FIX-API 2026-11-23: `test_devices_lists_known_devices_that_are_not_plugged_in`, `test_history_entries_made_by_the_api_are_marked`, `test_profile_save_marks_its_history_entries_by_api`; FIX-DEV 2026-11-23: `test_devices_lists_real_devices_only_each_once`, `test_the_hello_handshake_writes_no_api_line`; FIX-A 2026-11-23: `test_command_run_with_an_unknown_id_is_an_error`), `test/unit/test_gremlin_ctl*.py` (the client errors, the CLI's readable text, `--json` and exit codes 0-3; FIX-A 2026-11-23: `test_devices_help_says_plugged_in_or_not`), `test/unit/test_trace_additions*.py` (the trace additions on pages 01, 06 and 12; FIX-API 2026-11-23: `test_categories_name_every_on_off_row_of_the_trace_tab`, `test_every_trace_switch_setting_is_a_category` (guard), `test_a_category_switch_sets_its_row`), `test/unit/test_gremlin_mcp.py` (the MCP tools). Counts: the lead after the batch.

## 12. Review

| Decision | Summary |
|---|---|
| D-13-AGENT-DETAILS (2026-11-23, user: 1a, 2a, 3a, 4a) | `gremlin_ctl/` under change control (01 S156); API log lines at Warning level (S18); the agents' limits approved (S13-S16, S19, S20, S22); `gremlin-ctl call` kept (S23) |
| D-13-SHAPE (2026-11-23, user: shape agreed; 6a, 2a) | Three layers: the API in the program (private named pipe + secret key, the device helper's method), one client library, front ends on it: `gremlin-ctl.exe` in the installer with a Help page (6a, 2a), and an MCP server in the repo for development only (2a) (S1, S12) |
| D-13-SCOPE (2026-11-23, user: 1c) | Read state; start/stop, profile load/save, tracing, any menu command by id, Options read and change; window actions (S3, S4) |
| D-13-COMMANDS (2026-11-23, user: design for change) | Commands come from the menu command list; new menu commands need no API work (S5) |
| D-13-WINDOWS (2026-11-23, user: 3b, 4c, 4a; allowed while the user works 3a) | Open/close by command id, screenshot the window only, read visible text and buttons, press and type; windows open where they normally do; named by their shown title (S6) |
| D-13-HISTORY (2026-11-23, user: 3a) | Profile and Options changes through the API go into History marked "by API"; start/stop and tracing to the log only; every action in the system log (S7, S8) |
| D-13-DEVICES-LOG (2026-11-23, user: 2a) | `devices` lists real devices only, each once (plugged in, then known hardware not plugged in; no built-in inputs, output modules or id-less entries) (S21); the version handshake `hello` writes no "API:" log line (S8) |
| D-13-SWITCH (2026-11-23, user: 1a, 5a) | Options › General **Allow control from other programs**, off by default; only the user changes it; local PC only (S2) |
| D-13-SWEEP (2026-11-23, user: 1a, 2a, 3a) | From the live sweep (claude/audits/2026-11-23-control-api-sweep/): 1a `command.run` with an id that isn't a main window command fails with "No command called '<id>'" (exit 1); a known command that can't be used now still answers {"ran": false} (S17). 2a window call errors (missing window, button or field; closing the main window) are plain one-line messages without the Python exception name, and log only the "-> error" line, no traceback; unexpected faults keep the exception name and traceback (S8). 3a `devices` ids always lower case with dashes, no braces (S21); the `devices` help says devices, plugged in or not (S21); no double space in the log line of a call without arguments (S8) |
| D-13-CALLS (2026-11-23, user: 1a, 2a, 3a, 4a) | The call list, JSON messages, a version the clients check, one call at a time, 10 s / 30 s limits, the program never waits on the API; readable text with `--json` (S9-S11) |
| Build (2026-11-23, user: "build it now") | Built to `claude/plans/control-api-contract.md` together with the tracing additions (01 S198, 06 S189-S190, 12 S42) |
