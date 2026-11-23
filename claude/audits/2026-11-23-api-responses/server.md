# Control API answers and errors: the program side (agent AUD-SRV, 2026-11-23)

Read-only audit of every call's answers and errors on the program side, against
`claude/program-map/13-control-api.md` (S1-S24, section 12). Started 15:59, ended 16:03.

Files read: `gremlin/control_api.py`, `gremlin/ui/control_windows.py`,
`gremlin/ui/backend.py` (`register_api_calls`, `command_list`, `run_command_id`,
`_on_run_started` / `_on_run_stopped`, `loadProfile` / `_load_profile`, `saveProfile`),
`joystick_gremlin.py` (control_api hooks), `gremlin/threads.py` (`main_call_wait`),
`gremlin/ui/option.py` (`change_setting`, `main_layout`), `gremlin/code_runner.py`
(`last_error`), `gremlin_ctl/client.py` (timeouts only, for the cross-check). One read-only
probe, run with a temporary USERPROFILE: 31 Options settings are reachable; none has only
one of min or max; no setting type falls through to "changed in Options only"; the trace
categories are hidhide, screen-saver-mode, window, timing, osc, osc/receive, osc/inputs,
osc/output, osc/feedback and osc/setup.

**Note:** another agent (QML) was editing `gremlin/ui/control_windows.py` during this
audit, to make spin boxes typable: it adds `_spin_box`, `_name`, and an Enter key at the
end of `_type_into`. The control_windows line numbers below are from the file as committed
(HEAD). The findings still hold with that edit in place.

## Shared paths (every call)

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Switch off | "Control from other programs is off in Options › General." (control_api.py:54, 163) | OK | - | S2 |
| Request isn't JSON | "The request isn't JSON." (:216) | OK | - | S9 |
| JSON without a string `call` | `A request is {"call": name, "args": {}}.` (:219) | OK | - | S9 |
| `args` is a falsy non-object (`[]`, `0`, `""`) | treated as `{}`, so the call runs (:221 `or {}`) | Minor | Only `None` or a missing key should mean `{}` | S9 |
| `args` is a non-empty non-object | "args must be an object." (:166) | OK | - | S9 |
| Unknown call (including `""`) | "Unknown call: X. The call 'help' lists them." (:173) | OK (an empty name reads "Unknown call: .") | - | S10 |
| Misspelled or unknown argument key | ignored without a word; the call runs as if the argument were missing (see trace.on, window.type, log) | **No** | Each call declares its argument keys in `register(..., args=(...))`, and dispatch refuses others: "trace.on has no argument 'categroy' (it takes: category)." `help` then lists the keys too | S9, S10 |
| Another call is running | "Busy with another call; try again." after waiting up to the call's own limit (:186) | OK | - | S9 |
| Main-thread call over its limit | "<call> took over N s; the program carried on without it." (:199); `threads.main_call_wait` also logs a second warning line (threads.py:331-333) | **Partly** | The job still runs later when the main thread frees up (threads.py:310-312). An option.set, profile.load or window.type that times out is reported as failed but may still happen. Skip a job that starts after its caller gave up (in `threads.main_call_wait`, the shared owner), or say "it may still happen" | S9 |
| Worst-case wait vs the client's limit | waiting for `_busy` (up to the call's limit) and the call itself (up to its limit) are separate, so a 30 s call can take 60 s; `gremlin_ctl` gives up after 40 s (client.py:34) and reports "not running" (exit 2) | **No** | Use one deadline for the busy wait and the call (or a short cap on the busy wait), so every answer comes before the client's 40 s | S9, S11 |
| Request over 1 MB | `recv_bytes(MAX_REQUEST_BYTES)` raises OSError; `_serve` drops the connection with no answer and no log line (:413, 418); the client reports "not running" | **No** | Answer "The request is over 1 MB." (or log it) before closing | S9 |
| Unexpected fault in a handler | "<ExceptionName>: <text>" plus a traceback in the log (:204-206) | OK | - | S8 |
| Switch turned off mid-call | the call finishes; its answer is lost because the connection is closed (`_Server.close`); the client says "not running" | Acceptable | - | S2, S12 |
| Log line | "API: <call>[ <args JSON>] -> ok \| error: <text>", Warning level, hello skipped (:177-181) | OK | - | S8, S18 |
| Key handshake fails | logged "API: a connection was refused (<Exception>)" (:318) | OK | - | S12 |

## hello / help

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| hello | {"version": 1, "program_version"} (:603) | OK | - | S9 |
| help | [{"name", "summary"}] sorted by name (:609) | OK | - | S10 |
| help summaries | present for all 24 calls. command.run's summary has no `{id}` (backend.py:790), so a reader can't learn the argument key; trace.on and trace.off don't say where the categories are listed. The wording mixes command form ("Run the open profile.", "Open a profile", "Stop the Run.") with "Runs/Opens/Closes/Presses" | **Partly** | "Runs a main window menu command {id} (commands lists them)."; "Tracing on, or one category {category} (trace.status lists them)."; pick one verb form | S10 |

## state

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Normal | {version, api_version, profile, profile_name, unsaved, run (starting/running/stopped), mode, tracing, health, screen_saver_mode} (:637-652) | OK | - | S3, S10 |
| Window not ready | "The program's window isn't ready yet." (:599) | OK | - | - |
| One value can't be read | that value is null, with a traceback in the log (`_guarded`, :619) | OK (a null is not explained in the answer) | - | S3 |
| Screen Saver Mode module not loaded | `screen_saver_mode`: null (:630-632) | OK | - | S3 |
| Main thread blocked | the timeout line above | OK | - | S9 |

## devices

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Normal | plugged-in devices, then known hardware that isn't plugged in, each once, ids in lower case (:668-721) | OK | - | S3, S21 |
| `store.known_devices()` fails | the plugged-in devices only, logged (:697) | OK | - | S21 |
| `device_class.can` raises | the whole call fails with "<Exception>: ..." (:705, unguarded) | Minor | Skip that row and log it, as for known_devices | S21 |

## run.start / run.stop

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Started | {"run": "running"} after runStartHandled (:784-789) | OK | - | S24 |
| Stopped | {"run": "stopped"} after runStopHandled | OK | - | S24 |
| Already in the wanted state | the answer comes at once (:749-750) | OK | - | S24 |
| Run fails to start | the error is `runner.last_error`, which is the raw exception text, e.g. "No module named 'x'" (code_runner.py:471, 479; backend.py:900). The program's own message heading ("Could not run the profile." / "...a user plugin is missing.") is not in it | **Partly** | Keep the heading in `last_error`: "Could not run the profile: <reason>." | S24 ("with the program's own message") |
| Run's answer not in 10 s | "The Run didn't start within 10 s." / "...stop within 10 s." (:786) | OK | - | S24 |
| Main thread doesn't take the request in 10 s | `main_call_wait` raises TimeoutError, which passes through `_run_set` to `_run`'s "run.start took over 10 s; the program carried on without it." (:779, 196-201) | **No** | In `_run_set`, catch TimeoutError and raise the S24 text | S24 |
| Run fails inline | "The Run didn't start." or last_error (:782) | OK | - | S24 |
| run.stop while a Run is starting | Stop is sent; `_on_run_stopped` answers the waiter even while `_starting` (backend.py:683-686), so the answer can be "stopped" while a Run is still on its way | Edge case | Note only; the state was true when it was read | S24 |
| Window not ready | "The program's window isn't ready yet." | OK | - | - |

## profile.load

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Missing or empty path | "profile.load needs a path." (:810) | OK | - | S10 |
| Relative path | resolved against the **program's** working folder (:811). gremlin-ctl resolves it first (cli.py:170); MCP and raw clients don't | **Partly** | Refuse relative paths: "profile.load needs a full path." | S10 |
| No file / a folder | "No profile file at <path>." (:813) | OK | - | S10 |
| Unsaved changes | "The open profile has unsaved changes; save or discard them in the program first." (:816) | OK | - | S20 |
| File isn't a profile / fails to read | "The profile didn't open (the program says why)." (:822). The reason sits in `backend._load_problem` (backend.py:1169) but only reaches an error box on the PC, which a remote user can't see. The open profile has been replaced (the previous one read again, or a new empty one), and the answer doesn't say so | **No** | "The profile didn't open: <_load_problem>. <previous> is open again." (or "A new, empty profile is open.") | S8 (one plain line), S20 |
| A Run was going | the load stops the Run (`_load_profile` calls `activate_gremlin(False)`, backend.py:1147); the answer {"profile"} doesn't say | Minor | Add "run": the state after the load | S24 spirit |
| Over 30 s | the timeout line; the load may still finish later | see shared | - | S9 |

## profile.save

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Untitled | "The open profile has no file yet: save it in the program first (File › Save As)." (:830) | OK | - | S20 |
| Saved | {"profile", "saved": true}, History marked by API (:839-843) | OK | - | S7 |
| Saved, but a side file failed | `saveProblem()` text (:842) | OK | - | S20 |
| Write raised (disk full, access denied) | "The profile was not saved." with no reason: `saveProfile`'s `except Exception` returns False without setting `_save_problem` (backend.py:973-976) | **No** | Set `_save_problem = str(e)` there, so the answer says why | S8 |
| File missing after the write | "The profile was not saved." (backend.py:957-959) | Partly | "The profile file wasn't there after saving: <path>." | S8 |

## option.get / option.set / options.list

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Key missing or malformed | `A setting key is "section/group/name" (options.list).` (:850) | OK | - | S10, S19 |
| Unknown key | "No Options setting a/b/c (options.list lists them)." (:852) | OK | - | S19 |
| A setting Options shows with its own row (MetaConfigOption only) | "No Options setting ..." (excluded by `cfg.exists`, :867) | Partly | S19 says these are refused. "<title> is changed in Options only." would say why | S19 |
| get the switch | works (read-only) | OK | - | S2 |
| set the switch | "Only the user can change this setting, in Options › General." (:962) | OK | - | S2 |
| set without a value | "option.set needs a value." (:964) | OK | - | S10 |
| Bool not true/false/on/off/yes/no/1/0 | "This setting is on or off: true or false." (:929) | OK (doesn't name the setting) | Name it: "<title> is on or off: true or false." | - |
| Number not a number | "This setting is a number (int)." (:937) | Partly: "int"/"float" is Python wording | "<title> is a whole number." / "...a number." | - |
| Int given 1.7 (JSON number) | stored as 1 without a word (`int(1.7)`, :935) | **No** | Refuse a value with a fraction | - |
| Float given "nan" / "inf" | NaN passes the range check (every comparison with NaN is False) and is stored; inf is refused only if there is a max (:938-940) | **No** | Refuse values that aren't finite | - |
| Out of range | "This setting is from L to H." (:940); with only one limit it would read "from None to H" (no such setting today: probe) | OK today | Word each limit on its own | - |
| Selection not a choice | "Choose one of: a, b, c." (:946), case-sensitive | OK | - | - |
| String/Path given a list or number | stored as its str() (`"[1]"`) without a word (:948-949) | Minor | Refuse a value that isn't text | - |
| Start with Windows refused by Windows | "The setting was not changed (Windows kept its own)." (:969) | OK (it is the only live setting) | - | S19 |
| Changed | the setting's description, History "Changed <title> (by API)" (:966-970) | OK | - | S7, S22 |
| options.list | [{key, title, section, group, type, value, description, choices?, min?, max?}] (:899) | OK | - | S10 |

## trace.on / trace.off / trace.status

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| No category | the whole of tracing on/off, then the status (:985-986) | OK | - | S10 |
| Unknown category | "No trace category X; one of: hidhide, ..., osc/setup." (:990) | OK | - | S10 |
| Misspelled argument key (`categroy`) | the **whole** of tracing goes on/off without a word | **No** | Unknown argument keys refused (shared row) | S9 |
| Category on while tracing is off | the row is ticked; the answer shows tracing false | OK (the status shows it) | - | - |
| trace.status | {tracing, categories{name: bool}, file} (:1005) | OK | - | S10 |

## log

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Default | the last 50 system lines {file, lines} (:1032-1047) | OK | - | S3 |
| `which` not system/trace (and any other case, e.g. "System") | `which is "system" or "trace".` (:1046) | OK | - | S10 |
| lines not a number | "lines is a number." (:1039) | OK | - | - |
| lines 0 | 50 lines (`or 50`, :1037) | **No** | 0 or below: "lines is 1 to 2000." | - |
| lines over 2000 / below 0 | clamped to 2000 / 1 without a word (:1040) | Minor | Say it, or refuse it | - |
| Log file missing | {"file", "lines": []} | OK | - | - |

## commands / command.run (backend.py)

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| commands | [{id, text, group}] main window only (backend.py:728-747) | OK | - | S5, S17 |
| Bridge not ready (before Main.qml) | commands: `[]`; command.run: "No command called 'x'" | Minor | "The menu commands aren't ready yet." when the bridge is None | S17 |
| command.run without id | "No command called ''" (backend.py:781-783) | **No** | "command.run needs an id (commands lists them)." | S17 |
| Unknown or another window's id | "No command called 'x'" | OK | - | S17 |
| Known command that can't be used now | {"ran": false} | OK | - | S17 |
| Command throws in QML | logged "Command x failed: ...", answers {"ran": false} (backend.py:758-762) | Partly | A command that throws is a fault, not "can't be used now": answer the error text | S17 |

## window.* (control_windows.py, HEAD lines)

| Case | Answer today | OK? | Suggested fix | Spec ref |
|---|---|---|---|---|
| Missing window/button/field/command/path argument | "Missing 'window'" etc. (:272-276) | Partly | Same form as the rest: "window.read needs a window name." | S8 |
| No such window | "No window called 'x'" (:69) | OK | - | S8 |
| Several match | "2 windows match 'x': A, B" (:71) | OK | - | S6 |
| `find_window("")` / `_pick` empty name | "No window named" / "No button named" (:59, 186): can't be reached because `_arg` checks first | Dead code | Remove, or reword | - |
| window.list | [{title, visible}] (:279) | OK | - | S6 |
| window.open known command | {"ran": true}, log "Ran menu command x by API" (:283-295). Any command runs, not only ones that open a window, and the answer doesn't name the window | Partly | Answer the new window's title when one opened | S6 |
| window.open unknown or unusable id | one message for both: "Command 'x' isn't a menu command or can't be used now" (:291). command.run separates the two cases (S17) | **No** | Same split as command.run: "No command called 'x'" / "'x' can't be used now" | S6, S17 (consistency) |
| window.close main | "The main window isn't closed by the API" (:301) | OK | - | S13 |
| window.close refused by the window | {"closed": title} even when the window's `onClosing` sets `close.accepted = false` and asks to save (DialogCalibration.qml:190, DialogConfigureModule.qml:411, DialogDeviceMappingEditor.qml:39, DialogOptions.qml:38). Reports success while the window stays open and a question waits | **No** | After `close()`, if `window.isVisible()`: error "<title> didn't close: it asks about unsaved changes." | S6 |
| window.read | {title, items[{kind, name, text, enabled, checked?, placeholder?}]} (:308) | OK; CTL-READ-LABELS stays open | - | S6, S14, S15 |
| window.screenshot path not .png | "The picture path must end in .png" (:317) | OK | - | S6 |
| No folder | "No folder X" (:320) | OK | - | - |
| Relative path | saved relative to the program's working folder (:315-325) | Partly | Refuse relative paths: "window.screenshot needs a full path." | S6 |
| Window hidden or grab fails | "Couldn't take a picture of X" (:323) | Partly | Say "X isn't shown" when `not window.isVisible()` | S6 |
| Can't write | "Couldn't write X" (:325) | OK | - | - |
| window.press not found / ambiguous / turned off | "No button 'x' in T" / "2 buttons called 'x' in T; name one by its objectName" / "'x' is turned off in T" (:201-204, 334) | OK | - | S8, S14 |
| window.press success | {"pressed": text}, queued, so a later click failure is only logged (:336, 231-232) | OK by design | - | S6 |
| window.type read-only field | "No field 'x' in T" (a read-only field counts as text, :135-136) | Partly | "'x' in T can't be typed into" | S6 |
| window.type without `text` (or a misspelled key) | the field is **cleared** without a word (:344 `.get("text", "")`) | **No** | A missing `text` is an error; an explicit "" clears | S6 |
| window.type text a validator turns away | written with `setProperty("text")`, which skips the validator; the answer shows the text as set (:248-250). For a spin box (the QML agent's new Enter key), the box may put back its old number; the answer then shows what is there, which is right | **Partly** | When the field's text after typing isn't what was asked, answer an error ("T's field 'x' doesn't take 'abc'") instead of forcing it | S6 |
| window.type turned off | "That field is turned off in T" (:346) | OK (doesn't name the field) | "'x' is turned off in T" like press | - |
| "by API" log lines | `_log` writes at **Info** (:31), so the "Pressed ... by API" and "Typed into ... by API" lines are hidden at the default level; only the Warning "API: window.press ..." line shows | **Partly** | Write at Warning as S18 does | S8, S18 |
| Error punctuation | window and command errors have no full stop and use Python repr quotes ('x'; a name with an apostrophe gets "..."); control_api errors end with "." and use no quotes | Minor | One style for all (the spec quotes the no-full-stop form) | S8 |

## joystick_gremlin.py hooks

| Case | Today | OK? | Spec ref |
|---|---|---|---|
| Switch registered before the purge | `register_options()` (joystick_gremlin.py:995-997) | OK | S2 |
| Calls join before the pipe opens | `attach_ui()` then `start()` (:1413-1416), errors logged | OK | S12 |
| Quit | `stop()` in `shutdown_cleanup` only when loaded (:409-411) | OK | S12 |

## Ranked findings

1. **window.close reports success when the window refused to close** (control_windows.py:298-305). Four dialogs ask about unsaved changes in `onClosing`; the API answers {"closed": title} while the window stays open and a question waits on the PC. *Gap vs spec* (S6: close one).
2. **Misspelled or missing argument keys are ignored and the call does something else.** `trace.on {"categroy": "osc"}` turns all tracing on (control_api.py:984); `window.type` without `text` clears the field (control_windows.py:344); `log {"line": 5}` returns 50 lines. Fix at the shared owner: `register(..., args=...)` and dispatch refuses unknown keys (this also lets `help` list the arguments). *Spec change* (S9/S10 don't say what happens to unknown arguments). A narrower fix, making `text` required in window.type, is a *gap vs spec* under S6.
3. **A main-thread call that times out may still happen later.** The answer says it failed ("the program carried on without it"), but `threads.main_call_wait` still runs the queued job when the main thread frees up (threads.py:310-312, 321-334). option.set, profile.load and window.type can change things after reporting failure. Fix in `threads.main_call_wait`: skip a job that starts after its caller gave up. *Gap vs spec* (S9: past the limit the answer is an error, which implies nothing happened).
4. **The server can answer after the client has given up.** The busy wait and the call each get the call's full limit (control_api.py:186-194), so a 30 s call can take 60 s, past gremlin-ctl's 40 s (client.py:34). The user then sees "not running" (exit 2) although the program runs. *Gap vs spec* (S9 limits, S11 exit 2 meaning).
5. **profile.load failure gives no reason** (control_api.py:821-822): "The profile didn't open (the program says why)". The reason is in `backend._load_problem`, but only a dialog on the PC shows it. The answer also doesn't say the open profile was replaced. *Gap vs spec* (S8: an expected failure answers one plain line of text).
6. **run.start / run.stop answer the wrong text when the main thread is blocked.** A TimeoutError from `main_call_wait` (control_api.py:779) gives "run.start took over 10 s; the program carried on without it." instead of S24's "The Run didn't start within 10 s." *Gap vs spec* (S24).
7. **A failed Run's error is the raw exception text** ("No module named 'x'", code_runner.py:471, 479), without the program's heading "Could not run the profile". *Gap vs spec* (S24: "the program's own message").
8. **profile.save gives no reason when the write raised** (backend.py:973-976 leaves `_save_problem` empty, so the answer is "The profile was not saved."). *Gap vs spec* (S8).
9. **window.open lumps "unknown id" with "can't be used now"** (control_windows.py:289-293), unlike command.run's split under S17; it also runs commands that open no window. *Spec change* (S17 covers command.run only; making window.open the same is a small extension).
10. **window.type forces text past a validator** (control_windows.py:248-250) and answers it as typed. *Gap vs spec* (S6: type "as the user"); note the QML agent's spin box edit in progress.
11. **command.run without an id answers "No command called ''"** (backend.py:781-783), and its help summary lacks `{id}` (backend.py:790). *Gap vs spec* (S10 help, S17).
12. **Option value checks are loose.** Int 1.7 is stored as 1; Float "nan" is stored; String/Path accept a list as its str(); the messages say "(int)"/"(float)" and don't name the setting (control_api.py:921-953). *Gap vs spec*: no spec statement covers this; low risk.
13. **The "by API" lines for window open/close/press/type are at Info** (control_windows.py:31), so they don't show at the default level. *Gap vs spec* (S8, S18).
14. **A request over 1 MB is dropped with no answer and no log line** (control_api.py:413, 418); the client says "not running". *Gap vs spec* (S9: every request gets an answer).
15. **Relative paths in profile.load and window.screenshot resolve against the program's working folder** (control_api.py:811, control_windows.py:315). gremlin-ctl resolves them first; MCP and raw clients don't. *Spec change* (whether to refuse relative paths).
16. **log `lines: 0` gives 50 lines, and over 2000 is clamped without a word** (control_api.py:1037-1040). *Gap vs spec*: minor.
17. **Wording and shape consistency.** Window and command errors have no full stop and use repr quotes; the others end with "." and use no quotes. Missing-argument errors read "Missing 'window'" in one place and "profile.load needs a path." in another. Help summaries mix verb forms. The menu command id is `{id}` in command.run but `{command}` in window.open. *Spec change* (S8 quotes the current window-message form; renaming an argument changes the protocol for the client and MCP).
18. Small items: `devices` fails whole when `device_class.can` raises (control_api.py:705); `commands` answers `[]` and command.run "No command called" before the bridge is up (backend.py:732-734); a command that throws in QML answers {"ran": false} (backend.py:758-762); `find_window("")` / `_pick("")` messages can't be reached. *Gap vs spec*: low.

No raw tracebacks reach the client for any expected case read here. Every window, command and option error is a CallError, and only real faults answer "<Exception>: text".
