# Control API, CLI and MCP server (plan, 2026-11-23)

Planning only; not approved to build. Answers from the user in chat, 2026-11-23.

## Why

During the 2026-11-22 display-wake investigation, reading Screen Saver Mode's
wake count, whether a profile ran, and turning tracing on all needed outside
scripts or the user. An API lets the user, other users, scripts and Claude
read and control the program.

## Shape (agreed)

Three layers, one owner each:

1. **API in the program**: a private Windows named pipe with a secret key
   (same method as the device helper, gremlin/device_disable.py MpListener
   AF_PIPE + authkey). The key is written to a file in the user's Gremlin
   Platforms folder. The only part that touches the program.
2. **Client library**: one Python module that connects to the pipe and makes
   the calls; the only code that knows the pipe's protocol.
3. **Front ends on the library**:
   - CLI `gremlin-ctl.exe` (answer 6a), shipped in the installer next to
     gremlin_platforms.exe, with a Help page (2a).
   - MCP server in the repo (tools/gremlin_mcp/), started by Claude Code from
     the project's .mcp.json; development only, its package a dev dependency,
     not in the installer (2a).

## Decisions

- Scope (1c): read state (running profile, devices + plugged in, Screen
  Saver Mode state and wake counts, Health count, tracing on/off, last N log
  lines); actions (start/stop the profile, tracing categories on/off, run any
  menu command by its id from qml/main_commands.js, read/change Options
  settings); window actions.
- Window actions (3b): open/close a window by command id; screenshot a
  Gremlin window (the window only) to PNG; read a window's visible text and
  buttons as a list; press a named button and type into a named field.
- Windows the API opens appear where the program normally opens them (4c).
- History (3a): profile and Options changes made through the API go into
  Tools › History marked "by API"; start/stop and tracing go to the log only.
- Every API action is written to the system log as coming from the API.
- Switch (1a): Options › General › "Allow control from other programs", off
  by default. Only the user changes it; the API cannot turn itself on or off
  (5a). Local PC only.
- Commands come from the menu command list, so new menu commands need no API
  work (design for change).

## Still to do before building

- A new spec page in claude/program-map (statements + section 12 decisions),
  written with the user; glossary words.
- Protocol details (message shape, errors, versioning) and the tool list.

## Effort

No timing data for a feature this size. Rough guess: spec page ~20 min with
the user; a batch of ~5 agents (pipe listener, client + CLI + Help, MCP
server, window actions, tests) ~15 min; checks + quick tests + commit ~7 min;
CI ~23 min.

## Same batch: tracing additions (user, 2026-11-23: 1a, 2a, 3b)

Built together with the API (3b). From the 2026-11-22 display-wake gaps
(claude/audits/2026-11-22-display-wakes-vjoy-keepalive/):

1. Wake cause: the keep-off wake trace line names the last input Windows saw
   just before it (device, kind, counted or not) and the time since the last
   vJoy / Xbox write. To name game controllers, Screen Saver Mode listens to
   their reports only while the displays are kept off and only to name the
   source; nothing new counts as input (2a). Page 12.
2. vJoy keep-alive resets get an output trace line. Page 06.
3. Profile start and stop in the system log, with the profile name. Page 06.
4. A date line in the trace when tracing turns on and at midnight.
Not chosen: the once-a-minute uncounted-input summary.

## Calls and messages (user, 2026-11-23: 1a, 2a, 3a, 4a)

Calls (each a CLI command and an MCP tool):
- State: `state` (version, running profile, mode, tracing on/off, Health
  count, Screen Saver Mode state and wake counts); `devices`.
- Profile: `run start`, `run stop`, `profile load <file>`, `profile save`.
- Commands: `commands` (menu command ids and names); `run-command <id>`.
- Options: `option get <section/group/name>`, `option set <key> <value>`,
  `options list`.
- Tracing: `trace on/off [category]`, `trace status`.
- Logs: `log [system|trace] [last N]`.
- Windows (named by their shown title, 4a): `windows`, `window open <command
  id>`, `window close <name>`, `window read <name>`, `window screenshot <name>
  <file.png>`, `window press <name> <button>`, `window type <name> <field>
  <text>`. Allowed while the user works (3a); the system log notes "by API".

Messages: JSON request `{"call", "args"}`, answer `{"ok", "result"|"error"}`;
an API version the clients check; one call at a time, 10 s limit (30 s for
screenshots and profile loads); the program never waits on the API. With the
switch off, the answer says so and nothing happens. CLI prints readable text,
`--json` for scripts (2a).
