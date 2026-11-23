# API responses audit: the clients (gremlin-ctl, client library, MCP server, Help)

Agent AUD-CLI, 2026-11-23, 15:59-16:03. Read-only. Spec: `claude/program-map/13-control-api.md` (S1-S24; S11 exit codes 0/1/2/3/4).

Scope: `gremlin_ctl/client.py`, `gremlin_ctl/cli.py` (working copy, with agent CTL's exit-4 edit in it), `gremlin_ctl/__main__.py`, `tools/gremlin_mcp/server.py` (22 tools), `qml/help/getting_started.js` topic `getting-started-control`, `qml/help/options_profile.js:70`.

How it was checked:
- The installed `gremlin-ctl.exe` was run with read-only commands against the running program (state, devices, commands, options, windows, trace status, log, help, every `COMMAND --help`, mistyped commands, read errors).
- The not-running cases used `GREMLIN_CTL_ENDPOINT` pointing at fake endpoint files: missing, corrupt, empty, incomplete, a JSON list, a bad key, a dead process id, protocol version 2, a pipe that doesn't exist, and the real pipe with a wrong key.
- The repository's `cli.main()` was driven with a fake client for the cases the installed program must not be sent (the `call` arguments, a call error with `--json`, empty results).
- The MCP tools were called in Python with the fake endpoints, plus three read-only calls to the live program.

Note: the installed exe still exits 2 on a mistyped command (it predates CTL's change). The repository's `cli.py` exits 4, and the rows below describe the repository code unless they say "installed".

## Table

| # | Case | Code + message today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|---|
| 1 | Unknown command (`status`), extra word, bad `-n`, bad `--timeout` | 4 (installed: 2); usage + `gremlin-ctl: error: ...` on stderr | OK in repo | - | S11 |
| 2 | `profile load` without a file, `option set` without a value, `window press History` (wrong word count) | 4; `gremlin-ctl: profile load needs a file` on stderr, **no usage text** | Partly | Print the subcommand's usage first, as row 1 does; use the same `gremlin-ctl: error:` prefix | S11 ("the usage text goes to the error stream") |
| 3 | `call state {bad` (not valid JSON) | 4; `gremlin-ctl: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)` | Partly | Prefix it: "call: args must be a JSON object: <error>", plus usage | S11, S23 |
| 4 | `call state [1]`, `call state 5`, `call state null` (valid JSON, not an object) | **Uncaught TypeError, Python traceback**, exit 1 from Python | No | Check `isinstance(args, dict)` in the `call` builder (cli.py:152), raise `_UsageError` -> exit 4 | S11, S23 |
| 5 | `--timeout 0` (or negative) | Accepted; live: exit 2, `isn't running (no answer to state within 0 s)` while it was running | No | Refuse `--timeout` <= 0 as typed wrong (exit 4) | S11 |
| 6 | `log -n 0`, `log -n -5` | Accepted; live: `-n 0` printed the whole system log, `-n -5` printed one line | No | Refuse `-n` < 1 in the CLI (exit 4); the server side is for AUD-API | S10, S11 |
| 7 | `trace status hidhide` (category given to status) | 0; the category is silently ignored | Minor | Refuse a category with `status` (exit 4) | S10, S11 |
| 8 | No endpoint file (program closed or switch off) | 2; `Gremlin-Platforms isn't running, or control from other programs is off in Options › General` | OK, but says no next step | "...: start it, or switch on Options › General › Allow control from other programs" | S2, S11 |
| 9 | Endpoint file corrupt / empty / incomplete / a list / bad key hex | 2; the row 8 text + `(endpoint file unreadable: <json error>)`, `(endpoint file incomplete)`, `(endpoint key unreadable)` | OK | Optional: "switch the option off and on to write it again" | S11, S12 |
| 10 | Endpoint file left over (process id dead) | 2; `Gremlin-Platforms isn't running (its endpoint file is left over)` | OK | - | S11, S12 |
| 11 | Pipe gone (address doesn't exist) | 2; `Gremlin-Platforms isn't running` | OK | - | S11 |
| 12 | Wrong key (authentication refused) | 2; `isn't running (the pipe refused the key; the endpoint file is out of date)` | Partly: no next step, and "isn't running" is not quite the cause | "the endpoint file is out of date: switch the option off and on, or restart the program" | S11, S12 |
| 13 | Endpoint file version 2 | 3; `Gremlin-Platforms speaks control protocol 2; this gremlin-ctl speaks 1. Use the gremlin-ctl that came with the program.` | OK for the CLI; wrong advice through MCP (row 27) | - | S9, S11 |
| 14 | Leftover endpoint file of another version, program not running | 3 (the version is checked before the process id, client.py:204-209) | Minor | Check the process id first, so a dead program is 2 | S11 |
| 15 | Program running but silent past `--timeout` | 2; `isn't running (no answer to <call> within 40 s)` | Unclear | The text contradicts itself (it is running). Needs a decision on the code (row 29) | S9, S11 |
| 16 | Program closes during a call | 2; `Gremlin-Platforms isn't running` (client.py:164-166) | Unclear | The call may already have taken effect. Text: "the program closed before answering; the call may have run". Code: needs a decision (row 29) | S11 |
| 17 | Call refused by the program (`option get no/such/key`, `window read "No Such Window"`) | 1; `gremlin-ctl: option.get: No Options setting no/such/key (options.list lists them).` / `gremlin-ctl: window.read: No window called 'No Such Window'` | OK | Optional: the hint names the API call `options.list`; a CLI user types `gremlin-ctl options` (server text, AUD-API) | S8, S11 |
| 18 | Unreadable answer from the program | 1; `unreadable answer to <call>: ...` | OK | - | S11 |
| 19 | `--json` with any error | Plain text on stderr, nothing on stdout, same code | OK by S11's wording | Optional: `{"ok": false, "error", "code"}` on stdout with `--json`. Needs a decision (row 30) | S11 |
| 20 | `help` while not running | 0; prints the usage, then `(...isn't running...: the list of calls needs the program.)`. With `--json`: 2 | Inconsistent | Either is defensible; S11 says 2 = not running. Needs a decision (row 31) | S11 |
| 21 | `gremlin-ctl` with no command, `--help`, `COMMAND --help` | 0; usage on stdout | OK | - | S11 |
| 22 | `COMMAND --help` texts | Present for all 14 subcommands and match what they do. Missing help on positionals: `run-command id` (cli.py:104), `trace category` (cli.py:124, no hint where the names are), `log -n` (cli.py:132, no help and no default shown), `log which`, `call name/args` (cli.py:154-155) | Minor | Add: id "from `gremlin-ctl commands`"; category "names from `trace status`"; `-n` "lines from the end (default 50)"; args "a JSON object, e.g. \"{\\\"lines\\\": 5}\"" | S10, S23 |
| 23 | Readable text: `state` | Readable; floats are printed in full (`idle_s: 19.73366420000093`); an empty text prints as `saver_problem: ` (blank) | Minor | Round floats (for example to 0.1 s); print `-` for empty text | S11 |
| 24 | Readable text: `devices` | One `key=value` row per device; names with spaces and leading/trailing spaces read badly (`name= VKBSim NXT  SEM THQ FSM.GA   label=...`), clashing with the two-space separator | Minor | Quote values that contain spaces, or print one block per device | S11, S21 |
| 25 | Readable text: an empty object result | Prints `key: {}` (cli.py:224 only turns `[]` into `-`) | Minor | Treat `{}` like `[]` | S11 |
| 26 | Readable text: dead branch | `_print_result` has a `log` list case (cli.py:254); `log` now answers `{file, lines}`, so it is never used (the generic dict printing is used and reads fine) | Cleanup | Remove it or make it print `lines` without the indent | - |
| 27 | MCP: not running / off / version / stale / wrong key | `ToolError` carrying the client's text, no traceback (checked) | OK, except the version text tells an MCP user to "Use the gremlin-ctl that came with the program" | Word the mismatch neutrally ("this client speaks 1; use the client from the same version") | S1, S9 |
| 28 | MCP tool docs | Mostly accurate. **`gremlin_profile_load` says "Recorded in Tools > History as made by the API"** (server.py:118-119), but `profile.load` writes no History (control_api.py:804-823). `gremlin_profile_save` doesn't mention "by API" History or the Untitled refusal; `gremlin_profile_load` doesn't mention the unsaved-changes refusal (S20); `gremlin_run_start/stop` (server.py:106, 112) don't say they answer after the Run has started/stopped, or that a failed start is an error (S24); `gremlin_log.lines` has no bound (0 returns the whole log into the context) | Partly | Fix the load text; add S20/S24 notes; bound `lines` (1..some max) | S7, S20, S24 |
| 29 | MCP: `help` and `call` | No tools (22 tools; `hello`, `help` and `call` have none) | Gap or spec change | S10 says each call is "a command-line command and an MCP tool" and lists `help` | S10 |
| 30 | Help: exit codes | qml/help/getting_started.js:390-395 lists 0-3; **no 4** | Gap | Add "**4**: the command was typed wrong; the usage is shown" | S11 |
| 31 | Help: `call log {"lines": 5}` example | getting_started.js:379. **Fails in a command prompt**: cmd.exe splits it, giving `unrecognized arguments: 5}` (checked through cmd /c). `call log "{\"lines\": 5}"` and `call log {\"lines\":5}` work | Gap | Show the cmd.exe form `"{\"lines\": 5}"` (Help step 3 says to use a command prompt) | S23 |
| 32 | Help: `window press History Close`, `window type Search Find gear` | getting_started.js:377. From the code (not run, since press/type are not allowed in this audit): History has no button whose text or objectName is "Close" (DialogHistory.qml; it closes with Escape). The Search field is `searchBox`, placeholder "Search keys, actions, names and outputs…", so "Find" matches nothing (control_windows.py:179-204 matches objectName, then text or placeholder) | Gap (likely; check live) | Use names that exist, e.g. `window press History historyRefresh`, `window type Search searchBox gear` | S6, S14 |
| 33 | Help: other rows | `option get global/vjoy/keep-alive` exists (checked); command ids `tools.history` exist; 10 s / 30 s limits match S9; "Lists every command" for `help` is right (it also lists the calls) | OK | Optional: mention `COMMAND --help` and `--timeout`; say what to do on 2 (switch on the option) | S9-S11 |

## Ranked findings

1. **`gremlin-ctl call <name> <json>` with JSON that isn't an object crashes with a Python traceback.** cli.py:152 builds the args with `json.loads(a.args)` and cli.py:321 does `conn.call(call, **call_args)`, so `[1]`, `5` or `null` raise TypeError and Python's own exit code. Fix: check for a dict in the builder and raise `_UsageError` (exit 4). **Gap vs spec** (S11: no other code is used; S23).
2. **The Help page lists exit codes 0-3 only** (qml/help/getting_started.js:390-395). Code 4 is missing. **Gap vs spec** (S11, D-13-USAGE-EXIT). If agent CTL is not already doing this, it is the Help owner's job.
3. **The Help example `gremlin-ctl call log {"lines": 5}` fails in a command prompt** (getting_started.js:379; checked through cmd.exe: "unrecognized arguments: 5}"). Use `"{\"lines\": 5}"`. **Gap vs spec** (Help must match S23).
4. **The Help examples `window press History Close` and `window type Search Find gear` name a button and a field that don't exist** (getting_started.js:377; DialogHistory.qml has no "Close" button; the Search field is `searchBox`). This was found from the code; check it live before fixing. **Gap vs spec** (Help must match S6/S14).
5. **The MCP tool `gremlin_profile_load` says that loading is recorded in History** (server.py:118-119). `profile.load` writes no History entry (control_api.py:804-823). **Gap vs spec** (S7 is about changes only).
6. **Usage errors found after parsing print no usage text** (cli.py:312-314: `profile load` with no file, `option set` with no value, a wrong `window` word count, bad `call` JSON). They exit 4, but S11 says the usage goes to the error stream, and the prefix differs from argparse's (`gremlin-ctl:` vs `gremlin-ctl: error:`). **Gap vs spec** (S11).
7. **Out-of-range numbers are accepted:**
   - `--timeout 0` or a negative value (cli.py:71-76): live, `--timeout 0 state` answered exit 2 "isn't running" while the program was running.
   - `log -n 0` or a negative value (cli.py:132): live, `-n 0` printed the whole system log.
   - A category given to `trace status` is ignored (cli.py:117-124).

   All three should exit 4. **Gap vs spec** (S11: a bad argument is code 4). The server's handling of `lines` <= 0 is for AUD-API.
8. **A program that stops answering, or closes during a call, gives exit 2 "isn't running"** (client.py:157-162, 164-166). For a silent program the text contradicts itself. For a close mid-call, the call may already have taken effect (for example `run-command file.exit`; not tried). **Spec change (needs the user)**: S11 doesn't say which code these cases get. Options:
   - a) Keep 2, with clearer texts: "didn't answer within N s" and "closed before answering; the call may have run".
   - b) Give them 1 (the call failed).
9. **The texts for not running, switched off and wrong key don't say what to do** (client.py:36-40, 127-130). Suggested: "...isn't running, or Allow control from other programs is off: start it, or switch it on in Options › General › Control"; for the wrong key: "switch the option off and on, or restart the program". **Gap vs spec** (S2: "a client's answer says control from other programs is off". It does say so, but bundles it with "isn't running" and gives no next step; low).
10. **The MCP server has no `help` or `call` tool.** It has 22 tools against the S10 list, which includes `help` and says each call is "a command-line command and an MCP tool". **Spec change (needs the user)**: either add `gremlin_help` (and possibly `gremlin_call`) or note in S10 that `help` and `call` are command-line only.
11. **The MCP tool docs leave out answers and refusals the spec defines.**
    - `gremlin_run_start` / `gremlin_run_stop` (server.py:104-113) don't say they answer once the Run has started or stopped, or that a failed start is an error (S24).
    - The profile tools don't mention their refusals: unsaved changes for load, Untitled for save (S20).
    - `gremlin_log.lines` has no bound (server.py:220), so 0 can pour the whole log into Claude's context.

    **Gap vs spec** (docs must match S20/S24; low).
12. **The version mismatch text is CLI-only advice** ("Use the gremlin-ctl that came with the program", client.py:228-232), and the MCP server shows it as is. The version is also checked before the process id (client.py:204-209), so a leftover file from another version exits 3 instead of 2. **Gap vs spec** (low).
13. **The `--json` and `help` behaviour while not running needs a decision.**
    - With `--json`, an error is plain text on stderr and nothing goes to stdout.
    - `help` while not running exits 0 with a note (cli.py:326-328), but `--json help` exits 2.

    **Spec change (needs the user)**: S11 doesn't say whether `--json` errors are JSON, and `help` exiting 0 while not running is a deliberate exception to "2 = not running" that S11 doesn't record.
14. **Readable text, small fixes** (cli.py:206-247):
    - Floats are printed in full (`idle_s: 19.73366420000093`).
    - An empty text prints a blank; an empty object prints `{}`.
    - `devices` rows are hard to read when names contain spaces.
    - The `log` list branch at cli.py:254 is never used.
    - Subcommand `--help` is missing help on positional arguments (cli.py:104, 124, 132, 154-155).

    **Gap vs spec** (S11 readable text; low).

Checked and fine:
- Every not-running and endpoint-file case gives 2 with a clear reason.
- A version mismatch gives 3.
- Refused calls give 1 with the program's one-line text on stderr.
- The usage errors argparse catches give 4 in the repository.
- All 14 subcommands have `--help`, and their summaries match.
- The MCP tools return clear `ToolError`s with the client's text and no tracebacks, including the not-running/off message.
- The MCP server instructions and the README tool table match the 22 tools.
