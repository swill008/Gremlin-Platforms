# Control API sweep against the installed program (2026-11-23)

Agent SWEEP, 08:33-08:40. Every `gremlin-ctl` command and every MCP tool, run
against the installed Gremlin-Platforms 1.1.1
(`C:\Users\Stacie\AppData\Local\Programs\Gremlin-Platforms\`), profile
"test profile Gremlin Platforms.xml" running, Options › General › Control ›
"Allow control from other programs" on. Spec: `claude/program-map/13-control-api.md`
(S1-S23). Closes the "not yet tried from the installed program" part of
CTL-NOT-TRIED (section 10 there) except the items under "Not tested".

How: `gremlin-ctl.exe` driven by a Python script (each command in text, with
`--json` first and with `--json` after the command; exit codes checked; JSON
output parsed); the MCP server started exactly as `.mcp.json` says (Poetry venv
Python, `tools/gremlin_mcp/server.py`, stdio, repo as working folder) and
driven by the `mcp` package's `stdio_client` + `ClientSession`. Scripts and raw
results (results-*.json, screenshots) were in the session scratchpad only.

## Summary

| Part | Cases | Pass | Fail |
|---|---|---|---|
| CLI (`gremlin-ctl.exe`) | 138 | 137 | 1 (finding 1) |
| MCP server (22 tools, all called, plus 5 error cases) | 44 | 44 | 0 |
| System log: one "API:" line per call, no `hello` line (S8, S18) | 143 lines checked | yes | - |
| History: `option set` → "Changed Input highlighting (by API)" (S7, S22) | 8 entries (6 CLI, 2 MCP) | yes | - |
| History: `profile save` marked "(by API)" (S7) | - | not observable | see finding 5 |
| Refusal of `option set` on the switch (S2, S19) | CLI ×3, MCP ×1 | yes, exit 1 / is_error | - |
| Exit codes 0 / 1 / 2 (endpoint file missing) / 3 (copy of endpoint.json with version 99) | all | yes | - |

## Findings for the lead (no program code changed)

1. **`run-command` with an unknown id succeeds.** `gremlin-ctl run-command no.such.command`
   prints `ran: no` and exits 0; the log line says `API: command.run {"id": "no.such.command"} -> ok`.
   A script can't tell an unknown id from a command that can't be used now
   (`view.home` while Home is shown also gives `ran: no`, which is correct:
   its `enabled` is false on Home). `Backend.run_command_id` returns False for
   both by design (its docstring), and the MCP tool documents `{"ran": false}`;
   S17 says `command.run` "refuses" other windows' commands. Question for the
   user: should an unknown id (or another window's id) be a call error, exit 1?
2. **Window errors carry the Python exception name and log a traceback.**
   `window read|close|press|type` on a missing window, button or field, and
   `window close` on the main window (S13), answer e.g.
   `gremlin-ctl: window.read: ValueError: No window called 'No Such Window'`
   (MCP: `Error executing tool gremlin_window_read: ValueError: No window called 'No Such Window'`),
   and each writes a full `Traceback ... File "gremlin\ui\control_windows.py", line 359, in run`
   block to system.log (7 tracebacks for the 7 such calls). The other calls'
   expected errors (option, profile, trace) are clean one-line `CallError`s with
   no traceback.
3. **`help` summary for `devices` is stale:** "Devices plugged in." but S21
   lists the known devices that aren't plugged in too.
4. **`devices` ids are inconsistent in case:** plugged-in devices give
   `guid=87FDB100-...` (upper case), known not-plugged devices `guid=c6ec6fc0-...`
   (lower case). The field is named `guid` (S21 says "id"). Minor.
5. **`profile save` "(by API)" could not be seen.** Three CLI saves and one MCP
   save of the unchanged profile rewrote the file (modified time changed,
   content identical, same MD5) and added no History entry, so there was
   nothing to mark. S7 for `profile save` stays verified by unit tests only; seeing
   it on the installed program needs a real profile change, which this sweep
   didn't make.
6. Cosmetic: calls without arguments log with a double space,
   `API: state  -> ok`.

## Not tested

- Exit 2 with the switch off (the switch was not to be changed); only the
  "endpoint file missing" form of exit 2 was tried.
- `option set` of int, float, selection and path settings (only a bool).
- Where API-opened windows appear on screen (S6); they were closed within
  about a second of opening.
- The 10 s / 30 s main-thread limits (S9).

## Restored

`ui/general/input-highlighting` back to on; tracing off with every category
ticked (as at the start); every opened window (Health ×5, Search ×2) closed,
`windows` lists only the main window; profile reloaded (same MD5
9869ee5a025e02574e3a21400a54daeb, `unsaved: no`), Run `running`, mode Default;
the switch never changed. View back on Home.

## CLI results

| # | Command | Mode | Exit (expected) | Result | Notes |
|---|---|---|---|---|---|
| 1 | `gremlin-ctl state` | text | 0 (0) | PASS | version: 1.1.1 |
| 2 | `gremlin-ctl --json state` | json | 0 (0) | PASS | { |
| 3 | `gremlin-ctl state --json` | json-after | 0 (0) | PASS | { |
| 4 | `gremlin-ctl devices` | text | 0 (0) | PASS | name= VKBSim NXT  SEM THQ FSM.GA   label= VKBSim NXT  SEM TH |
| 5 | `gremlin-ctl --json devices` | json | 0 (0) | PASS | ts": 0, |
| 6 | `gremlin-ctl devices --json` | json-after | 0 (0) | PASS | ts": 0, |
| 7 | `gremlin-ctl commands` | text | 0 (0) | PASS | cripts  (View) |
| 8 | `gremlin-ctl --json commands` | json | 0 (0) | PASS | iceMappingEditor", |
| 9 | `gremlin-ctl commands --json` | json-after | 0 (0) | PASS | iceMappingEditor", |
| 10 | `gremlin-ctl options` | text | 0 (0) | PASS | tion=Root folder for user files. Takes effect on the next st |
| 11 | `gremlin-ctl --json options` | json | 0 (0) | PASS | "description": "Device files, pictures, and imported copies. |
| 12 | `gremlin-ctl options --json` | json-after | 0 (0) | PASS | "description": "Device files, pictures, and imported copies. |
| 13 | `gremlin-ctl options list` | text | 0 (0) | PASS | tion=Root folder for user files. Takes effect on the next st |
| 14 | `gremlin-ctl option get ui/general/input-highlighting` | text | 0 (0) | PASS | key: ui/general/input-highlighting |
| 15 | `gremlin-ctl --json option get ui/general/input-highlighting` | json | 0 (0) | PASS | { |
| 16 | `gremlin-ctl option get ui/general/input-highlighting --json` | json-after | 0 (0) | PASS | { |
| 17 | `gremlin-ctl trace status` | text | 0 (0) | PASS | tracing: no |
| 18 | `gremlin-ctl --json trace status` | json | 0 (0) | PASS | { |
| 19 | `gremlin-ctl trace status --json` | json-after | 0 (0) | PASS | { |
| 20 | `gremlin-ctl log system -n 5` | text | 0 (0) | PASS | file: C:\Users\Stacie\Gremlin Platforms\logs\system.log |
| 21 | `gremlin-ctl --json log system -n 5` | json | 0 (0) | PASS | { |
| 22 | `gremlin-ctl log system -n 5 --json` | json-after | 0 (0) | PASS | { |
| 23 | `gremlin-ctl log trace -n 3` | text | 0 (0) | PASS | file: C:\Users\Stacie\Gremlin Platforms\logs\trace.log |
| 24 | `gremlin-ctl --json log trace -n 3` | json | 0 (0) | PASS | { |
| 25 | `gremlin-ctl log trace -n 3 --json` | json-after | 0 (0) | PASS | { |
| 26 | `gremlin-ctl log` | text | 0 (0) | PASS | -> ok |
| 27 | `gremlin-ctl windows` | text | 0 (0) | PASS | title=test profile Gremlin Platforms.xml  visible=yes |
| 28 | `gremlin-ctl --json windows` | json | 0 (0) | PASS | [ |
| 29 | `gremlin-ctl windows --json` | json-after | 0 (0) | PASS | [ |
| 30 | `gremlin-ctl help` | text | 0 (0) | PASS | sage and exit |
| 31 | `gremlin-ctl --json help` | json | 0 (0) | PASS | , value}." |
| 32 | `gremlin-ctl help --json` | json-after | 0 (0) | PASS | , value}." |
| 33 | `gremlin-ctl ` | text | 0 (0) | PASS | usage: gremlin-ctl [-h] [--json] [--timeout TIMEOUT] COMMAND |
| 34 | `gremlin-ctl --help` | text | 0 (0) | PASS | usage: gremlin-ctl [-h] [--json] [--timeout TIMEOUT] COMMAND |
| 35 | `gremlin-ctl call state` | text | 0 (0) | PASS | version: 1.1.1 |
| 36 | `gremlin-ctl --json call state` | json | 0 (0) | PASS | { |
| 37 | `gremlin-ctl call state --json` | json-after | 0 (0) | PASS | { |
| 38 | `gremlin-ctl call option.get {"key": "ui/general/input-highlighting"}` | text | 0 (0) | PASS | key: ui/general/input-highlighting |
| 39 | `gremlin-ctl --json call option.get {"key": "ui/general/input-highlighting"}` | json | 0 (0) | PASS | { |
| 40 | `gremlin-ctl call option.get {"key": "ui/general/input-highlighting"} --json` | json-after | 0 (0) | PASS | { |
| 41 | `gremlin-ctl call log {"which": "system", "lines": 2}` | text | 0 (0) | PASS | file: C:\Users\Stacie\Gremlin Platforms\logs\system.log |
| 42 | `gremlin-ctl --json call log {"which": "system", "lines": 2}` | json | 0 (0) | PASS | { |
| 43 | `gremlin-ctl call log {"which": "system", "lines": 2} --json` | json-after | 0 (0) | PASS | { |
| 44 | `gremlin-ctl option get no/such/key` | text | 1 (1) | PASS | gremlin-ctl: option.get: No Options setting no/such/key (options.list lists them). |
| 45 | `gremlin-ctl --json option get no/such/key` | json | 1 (1) | PASS | gremlin-ctl: option.get: No Options setting no/such/key (options.list lists them). |
| 46 | `gremlin-ctl option get no/such/key --json` | json-after | 1 (1) | PASS | gremlin-ctl: option.get: No Options setting no/such/key (options.list lists them). |
| 47 | `gremlin-ctl window read No Such Window` | text | 1 (1) | PASS | gremlin-ctl: window.read: ValueError: No window called 'No Such Window' |
| 48 | `gremlin-ctl --json window read No Such Window` | json | 1 (1) | PASS | gremlin-ctl: window.read: ValueError: No window called 'No Such Window' |
| 49 | `gremlin-ctl window read No Such Window --json` | json-after | 1 (1) | PASS | gremlin-ctl: window.read: ValueError: No window called 'No Such Window' |
| 50 | `gremlin-ctl option set global/control/allow-other-programs false` | text | 1 (1) | PASS | gremlin-ctl: option.set: Only the user can change this setting, in Options › General. |
| 51 | `gremlin-ctl --json option set global/control/allow-other-programs false` | json | 1 (1) | PASS | gremlin-ctl: option.set: Only the user can change this setting, in Options › General. |
| 52 | `gremlin-ctl option set global/control/allow-other-programs false --json` | json-after | 1 (1) | PASS | gremlin-ctl: option.set: Only the user can change this setting, in Options › General. |
| 53 | `gremlin-ctl run-command no.such.command` | text | 0 (1) | FAIL | prints "ran: no", exit 0 (finding 1) |
| 54 | `gremlin-ctl call no.such.call` | text | 1 (1) | PASS | gremlin-ctl: no.such.call: Unknown call: no.such.call. The call 'help' lists them. |
| 55 | `gremlin-ctl profile load C:\no\such\profile.xml` | text | 1 (1) | PASS | gremlin-ctl: profile.load: No profile file at C:\no\such\profile.xml. |
| 56 | `gremlin-ctl profile load` | text | 1 (1) | PASS | gremlin-ctl: profile load needs a file |
| 57 | `gremlin-ctl option set ui/general/input-highlighting` | text | 1 (1) | PASS | gremlin-ctl: option set needs a value |
| 58 | `gremlin-ctl window screenshot x` | text | 1 (1) | PASS | gremlin-ctl: window screenshot takes 2 argument(s) |
| 59 | `gremlin-ctl window close test profile Gremlin Platforms.xml` | text | 1 (1) | PASS | gremlin-ctl: window.close: ValueError: The main window isn't closed by the API |
| 60 | `gremlin-ctl trace on no-such-cat` | text | 1 (1) | PASS | gremlin-ctl: trace.on: No trace category no-such-cat; one of: hidhide, screen-saver-mode, window, timing, osc, |
| 61 | `gremlin-ctl option set ui/general/input-highlighting notabool` | text | 1 (1) | PASS | gremlin-ctl: option.set: This setting is on or off: true or false. |
| 62 | `gremlin-ctl run sideways` | text | 2 (2) | PASS | gremlin-ctl run: error: argument action: invalid choice: 'sideways' (choose from 'start', 'stop') |
| 63 | `gremlin-ctl state` | text | 2 (2) | PASS | gremlin-ctl: Gremlin-Platforms isn't running, or control from other programs is off in Options › General |
| 64 | `gremlin-ctl --json state` | json | 2 (2) | PASS | gremlin-ctl: Gremlin-Platforms isn't running, or control from other programs is off in Options › General |
| 65 | `gremlin-ctl state --json` | json-after | 2 (2) | PASS | gremlin-ctl: Gremlin-Platforms isn't running, or control from other programs is off in Options › General |
| 66 | `gremlin-ctl help` | text | 0 (0) | PASS | usage: gremlin-ctl [-h] [--json] [--timeout TIMEOUT] COMMAND |
| 67 | `gremlin-ctl --json help` | json | 2 (2) | PASS | gremlin-ctl: Gremlin-Platforms isn't running, or control from other programs is off in Options › General |
| 68 | `gremlin-ctl state` | text | 3 (3) | PASS | gremlin-ctl: Gremlin-Platforms speaks control protocol 99; this gremlin-ctl speaks 1. Use the gremlin-ctl that |
| 69 | `gremlin-ctl --json state` | json | 3 (3) | PASS | gremlin-ctl: Gremlin-Platforms speaks control protocol 99; this gremlin-ctl speaks 1. Use the gremlin-ctl that |
| 70 | `gremlin-ctl state --json` | json-after | 3 (3) | PASS | gremlin-ctl: Gremlin-Platforms speaks control protocol 99; this gremlin-ctl speaks 1. Use the gremlin-ctl that |
| 71 | `gremlin-ctl option set ui/general/input-highlighting false` | text | 0 (0) | PASS | key: ui/general/input-highlighting |
| 72 | `gremlin-ctl option set ui/general/input-highlighting true` | text | 0 (0) | PASS | key: ui/general/input-highlighting |
| 73 | `gremlin-ctl --json option set ui/general/input-highlighting false` | json | 0 (0) | PASS | { |
| 74 | `gremlin-ctl --json option set ui/general/input-highlighting true` | json | 0 (0) | PASS | { |
| 75 | `gremlin-ctl option set ui/general/input-highlighting false --json` | json-after | 0 (0) | PASS | { |
| 76 | `gremlin-ctl option set ui/general/input-highlighting true --json` | json-after | 0 (0) | PASS | { |
| 77 | `gremlin-ctl trace off timing` | text | 0 (0) | PASS | tracing: no |
| 78 | `gremlin-ctl trace on timing` | text | 0 (0) | PASS | tracing: no |
| 79 | `gremlin-ctl --json trace off osc/receive` | json | 0 (0) | PASS | { |
| 80 | `gremlin-ctl --json trace on osc/receive` | json | 0 (0) | PASS | { |
| 81 | `gremlin-ctl trace off timing --json` | json-after | 0 (0) | PASS | { |
| 82 | `gremlin-ctl trace on timing --json` | json-after | 0 (0) | PASS | { |
| 83 | `gremlin-ctl trace on` | text | 0 (0) | PASS | tracing: yes |
| 84 | `gremlin-ctl trace off` | text | 0 (0) | PASS | tracing: no |
| 85 | `gremlin-ctl --json trace on` | json | 0 (0) | PASS | { |
| 86 | `gremlin-ctl --json trace off` | json | 0 (0) | PASS | { |
| 87 | `gremlin-ctl trace on --json` | json-after | 0 (0) | PASS | { |
| 88 | `gremlin-ctl trace off --json` | json-after | 0 (0) | PASS | { |
| 89 | `gremlin-ctl run stop` | text | 0 (0) | PASS | run: stopped |
| 90 | `gremlin-ctl run start` | text | 0 (0) | PASS | run: starting |
| 91 | `gremlin-ctl --json run stop` | json | 0 (0) | PASS | { |
| 92 | `gremlin-ctl --json run start` | json | 0 (0) | PASS | { |
| 93 | `gremlin-ctl run stop --json` | json-after | 0 (0) | PASS | { |
| 94 | `gremlin-ctl run start --json` | json-after | 0 (0) | PASS | { |
| 95 | `gremlin-ctl run-command view.home` | text | 0 (0) | PASS | ran: no |
| 96 | `gremlin-ctl --json run-command view.home` | json | 0 (0) | PASS | { |
| 97 | `gremlin-ctl run-command view.home --json` | json-after | 0 (0) | PASS | { |
| 98 | `gremlin-ctl profile save` | text | 0 (0) | PASS | profile: C:\Users\Stacie\Gremlin Platforms\profiles\test pro |
| 99 | `gremlin-ctl --json profile save` | json | 0 (0) | PASS | { |
| 100 | `gremlin-ctl profile save --json` | json-after | 0 (0) | PASS | { |
| 101 | `gremlin-ctl profile load C:\Users\Stacie\Gremlin Platforms\profiles\test profile Gremlin Platforms.xml` | text | 0 (0) | PASS | profile: C:\Users\Stacie\Gremlin Platforms\profiles\test pro |
| 102 | `gremlin-ctl --json profile load C:\Users\Stacie\Gremlin Platforms\profiles\test profile Gremlin Platforms.xml` | json | 0 (0) | PASS | { |
| 103 | `gremlin-ctl profile load C:\Users\Stacie\Gremlin Platforms\profiles\test profile Gremlin Platforms.xml --json` | json-after | 0 (0) | PASS | { |
| 104 | `gremlin-ctl run start` | text | 0 (0) | PASS | run: starting |
| 105 | `gremlin-ctl run-command view.deviceBindings` | text | 0 (0) | PASS | ran: yes |
| 106 | `gremlin-ctl --json run-command view.home` | json | 0 (0) | PASS | { |
| 107 | `gremlin-ctl run-command tools.health` | text | 0 (0) | PASS | ran: yes |
| 108 | `gremlin-ctl --json windows` | json | 0 (0) | PASS | [ |
| 109 | `gremlin-ctl window close Health` | text | 0 (0) | PASS | closed: Health |
| 110 | `gremlin-ctl window open tools.health` | text | 0 (0) | PASS | ran: yes |
| 111 | `gremlin-ctl --json windows` | json | 0 (0) | PASS | [ |
| 112 | `gremlin-ctl window read Health` | text | 0 (0) | PASS | =yes |
| 113 | `gremlin-ctl --json window read Health` | json | 0 (0) | PASS | "text", |
| 114 | `gremlin-ctl window read Health --json` | json-after | 0 (0) | PASS | "text", |
| 115 | `gremlin-ctl window screenshot Health <scratch>\shot-1.png` | text | 0 (0) | PASS | path: C:\Users\Stacie\AppData\Local\Temp\claude\906eff5ad66b |
| 116 | `gremlin-ctl --json window screenshot Health <scratch>\shot-2.png` | json | 0 (0) | PASS | { |
| 117 | `gremlin-ctl window screenshot Health <scratch>\shot-3.png --json` | json-after | 0 (0) | PASS | { |
| 118 | `gremlin-ctl window press Health All profiles` | text | 0 (0) | PASS | pressed: All profiles |
| 119 | `gremlin-ctl --json window press Health This profile only` | json | 0 (0) | PASS | { |
| 120 | `gremlin-ctl window press Health All profiles --json` | json-after | 0 (0) | PASS | { |
| 121 | `gremlin-ctl window press Health This profile only` | text | 0 (0) | PASS | pressed: This profile only |
| 122 | `gremlin-ctl window press Health No Such Button` | text | 1 (1) | PASS | gremlin-ctl: window.press: ValueError: No button 'No Such Button' in Health |
| 123 | `gremlin-ctl window close Health` | text | 0 (0) | PASS | closed: Health |
| 124 | `gremlin-ctl --json window open tools.health` | json | 0 (0) | PASS | { |
| 125 | `gremlin-ctl --json window close Health` | json | 0 (0) | PASS | { |
| 126 | `gremlin-ctl window open tools.health --json` | json-after | 0 (0) | PASS | { |
| 127 | `gremlin-ctl window close Health --json` | json-after | 0 (0) | PASS | { |
| 128 | `gremlin-ctl window open tools.search` | text | 0 (0) | PASS | ran: yes |
| 129 | `gremlin-ctl --json windows` | json | 0 (0) | PASS | [ |
| 130 | `gremlin-ctl window type Search searchBox button` | text | 0 (0) | PASS | text: button |
| 131 | `gremlin-ctl --json window type Search searchBox axis` | json | 0 (0) | PASS | { |
| 132 | `gremlin-ctl window type Search searchBox  --json` | json-after | 0 (0) | PASS | { |
| 133 | `gremlin-ctl window type Search noSuchField x` | text | 1 (1) | PASS | gremlin-ctl: window.type: ValueError: No field 'noSuchField' in Search |
| 134 | `gremlin-ctl window close Search` | text | 0 (0) | PASS | closed: Search |
| 135 | `gremlin-ctl window close Search` | text | 1 (1) | PASS | gremlin-ctl: window.close: ValueError: No window called 'Search' |
| 136 | `gremlin-ctl windows` | text | 0 (0) | PASS | title=test profile Gremlin Platforms.xml  visible=yes |
| 137 | `gremlin-ctl --json windows` | json | 0 (0) | PASS | [ |
| 138 | `gremlin-ctl windows --json` | json-after | 0 (0) | PASS | [ |

## MCP results

| # | Tool | Args | Result | Pass | Notes |
|---|---|---|---|---|---|
| 1 | `list_tools` | `{}` | ok | PASS | 22 tools |
| 2 | `gremlin_state` | `{}` | ok | PASS |  |
| 3 | `gremlin_devices` | `{}` | ok | PASS |  |
| 4 | `gremlin_commands` | `{}` | ok | PASS |  |
| 5 | `gremlin_options_list` | `{}` | ok | PASS |  |
| 6 | `gremlin_option_get` | `{"key": "ui/general/input-highlighting"}` | ok | PASS |  |
| 7 | `gremlin_option_set` | `{"key": "ui/general/input-highlighting", "value": false}` | ok | PASS |  |
| 8 | `gremlin_option_set` | `{"key": "ui/general/input-highlighting", "value": true}` | ok | PASS |  |
| 9 | `gremlin_trace_status` | `{}` | ok | PASS |  |
| 10 | `gremlin_trace_off` | `{"category": "timing"}` | ok | PASS |  |
| 11 | `gremlin_trace_on` | `{"category": "timing"}` | ok | PASS |  |
| 12 | `gremlin_trace_off` | `{"category": "osc/receive"}` | ok | PASS |  |
| 13 | `gremlin_trace_on` | `{"category": "osc/receive"}` | ok | PASS |  |
| 14 | `gremlin_trace_on` | `{}` | ok | PASS |  |
| 15 | `gremlin_trace_off` | `{}` | ok | PASS |  |
| 16 | `gremlin_log` | `{"which": "system", "lines": 3}` | ok | PASS |  |
| 17 | `gremlin_log` | `{"which": "trace", "lines": 2}` | ok | PASS |  |
| 18 | `gremlin_log` | `{}` | ok | PASS |  |
| 19 | `gremlin_run_stop` | `{}` | ok | PASS |  |
| 20 | `gremlin_run_start` | `{}` | ok | PASS |  |
| 21 | `gremlin_run_command` | `{"id": "view.deviceBindings"}` | ok | PASS |  |
| 22 | `gremlin_run_command` | `{"id": "view.home"}` | ok | PASS |  |
| 23 | `gremlin_profile_save` | `{}` | ok | PASS |  |
| 24 | `gremlin_profile_load` | `{"path": "C:\\Users\\Stacie\\Gremlin Platforms\\profiles\\test profile Gremlin Platforms.xml"}` | ok | PASS |  |
| 25 | `gremlin_run_start` | `{}` | ok | PASS |  |
| 26 | `gremlin_windows` | `{}` | ok | PASS |  |
| 27 | `gremlin_window_open` | `{"command": "tools.health"}` | ok | PASS |  |
| 28 | `gremlin_window_read` | `{"window": "Health"}` | ok | PASS |  |
| 29 | `gremlin_window_screenshot` | `{"window": "Health", "path": "<scratch>\\mcp-shot.png"}` | ok | PASS |  |
| 30 | `gremlin_window_press` | `{"window": "Health", "button": "All profiles"}` | ok | PASS |  |
| 31 | `gremlin_window_press` | `{"window": "Health", "button": "This profile only"}` | ok | PASS |  |
| 32 | `gremlin_window_close` | `{"window": "Health"}` | ok | PASS |  |
| 33 | `gremlin_window_open` | `{"command": "tools.search"}` | ok | PASS |  |
| 34 | `gremlin_window_type` | `{"window": "Search", "field": "searchBox", "text": "button"}` | ok | PASS |  |
| 35 | `gremlin_window_type` | `{"window": "Search", "field": "searchBox", "text": ""}` | ok | PASS |  |
| 36 | `gremlin_window_close` | `{"window": "Search"}` | ok | PASS |  |
| 37 | `gremlin_option_get` | `{"key": "no/such/key"}` | error (is_error) | PASS | Error executing tool gremlin_option_get: No Options setting no/such/key (options.list lists them). |
| 38 | `gremlin_option_set` | `{"key": "global/control/allow-other-programs", "value": false}` | error (is_error) | PASS | Error executing tool gremlin_option_set: Only the user can change this setting, in Options › General. |
| 39 | `gremlin_window_read` | `{"window": "No Such Window"}` | error (is_error) | PASS | Error executing tool gremlin_window_read: ValueError: No window called 'No Such Window' |
| 40 | `gremlin_profile_load` | `{"path": "C:\\no\\such\\profile.xml"}` | error (is_error) | PASS | Error executing tool gremlin_profile_load: No profile file at C:\no\such\profile.xml. |
| 41 | `gremlin_trace_on` | `{"category": "no-such-cat"}` | error (is_error) | PASS | Error executing tool gremlin_trace_on: No trace category no-such-cat; one of: hidhide, screen-saver-mode, wind |
| 42 | `gremlin_windows` | `{}` | ok | PASS |  |
| 43 | `gremlin_state` | `{}` | ok | PASS |  |
| 44 | `all tools called` | `{}` | ok | PASS | not called: [] |
