# Control API live tests, part 2 (2026-11-23)

Agent LIVE2, 09:36-09:42. Run against the installed Gremlin-Platforms 1.1.1
(`C:\Users\Stacie\AppData\Local\Programs\Gremlin-Platforms\gremlin-ctl.exe`),
profile "test profile Gremlin Platforms.xml" running, Options › General ›
Control switch on (never changed). Spec: `claude/program-map/13-control-api.md`.
Follows the first sweep (README.md here): covers its "Not tested" item
"`option set` of int, float, selection" (partly) and its finding 5 (History
"(by API)" for `profile save` not observable). No program code changed; no
windows opened (the Profile Settings view is a page of the main window).

## Summary

| # | Test | Result |
|---|---|---|
| 1 | `option set` on a number and a choice setting, plus invalid values; History settings.jsonl | PASS |
| 2 | History "(by API)" for `profile save` after a real profile change; file back byte for byte | PASS |
| 3 | vJoy keep-alive trace line | PASS (one finding about `run stop`'s reply) |
| 4 | Tracing left on overnight, Screen Saver Mode category on, keep-on untouched | done |

## 1. `option set` on a number and a choice setting

Number: `action/double-tap/duration` (float, 0.0-10.0). Choice:
`action/play-sound/playback-mode` (Sequential / Interrupt / Overlap).

| Step | Result |
|---|---|
| get duration | 0.5, exit 0 |
| set 0.6, get | 0.6, exit 0 |
| set 0.5, get | 0.5, exit 0 |
| set 99 | exit 1, `gremlin-ctl: option.set: This setting is from 0.0 to 10.0.` |
| set abc | exit 1, `gremlin-ctl: option.set: This setting is a number (float).` |
| get after invalid | 0.5 (unchanged) |
| get playback mode | Sequential |
| set Interrupt, get | Interrupt |
| set Sequential, get | Sequential |
| set Bogus | exit 1, `gremlin-ctl: option.set: Choose one of: Sequential, Interrupt, Overlap.` |
| get after invalid | Sequential (unchanged) |

History `settings.jsonl` went from 140 to 144 lines: exactly the 4 valid sets,
none for the 3 invalid ones. Each is titled "Changed Double Tap duration (by
API)" / "Changed Playback mode (by API)", `by: "api"`, with correct
before/after values (0.5→0.6, 0.6→0.5, Sequential→Interrupt,
Interrupt→Sequential). System log has one `API: option.set ... -> ok` or
`-> error: <message>` line per call, no tracebacks.

## 2. History "(by API)" for a profile save

Backup first: profile copied to the session scratchpad (`live2\backup.xml`),
SHA-256 `2cad5294...0d386d`, same as the original.

The change: `run-command view.settings` (Profile Settings page in the main
window), then `window press "<main window>" "Use the Options default (Options
→ Actions → Macro)"` to untick it (`unsaved: yes`), `profile save`
(`unsaved: no`). The vJoy Initial Values fields were not reachable: they have
no objectName and no placeholder, so `window type` can't name them (the
picker matches objectName, then placeholder text).

History `profile.jsonl` went 152 → 154 lines:

- `Changed Profile Settings (by API)`, kind `section`, `by: api`; before has
  `<macro-delay-source>options</macro-delay-source>`, after doesn't.
- `Saved test profile Gremlin Platforms.xml (Profile Settings) (by API)`, kind
  `profile`, `by: api`.

Undo: the same press (ticked again), `profile save`: two more entries with the
same titles and `by: api`. The profile file's SHA-256 is again
`2cad5294...0d386d`; `cmp` with the backup: identical. View returned to Home
(`run-command view.home`). This closes the sweep's finding 5: S7 for
`profile save` is seen on the installed program.

## 3. Keep-alive trace line

The keep-alive line (`trace.vjoy_keep_alive`, gremlin/trace.py) is an OUTPUT
line gated only by the master tracing switch; no category covers it, so
`trace on` was enough (every category was already ticked).

- 09:37:27 `trace on`; `option set global/vjoy/keep-alive true`; `run stop`;
  `run start`. Run start wrote vJoy 3 X/Y/Z at 09:37:28.1 (the trace shows
  them); nothing wrote vJoy after that.
- Lines seen in `log trace`:

```
09:38:28.100  vjoy 2  OUTPUT  vJoy 2 keep-alive reset (idle 60 s)
09:38:29.076  vjoy 1  OUTPUT  vJoy 1 keep-alive reset (idle 61 s)
09:38:29.107  vjoy 3  OUTPUT  vJoy 3 keep-alive reset (idle 61 s)
09:39:28.110  vjoy 2  OUTPUT  vJoy 2 keep-alive reset (idle 60 s)
09:39:29.084  vjoy 1  OUTPUT  vJoy 1 keep-alive reset (idle 60 s)
09:39:29.116  vjoy 3  OUTPUT  vJoy 3 keep-alive reset (idle 60 s)
```

  One reset per held vJoy per minute, all three devices, as 06 S54 says.
- 09:39:34 `option set global/vjoy/keep-alive false`; `run stop`; `run start`
  (09:39:35). Watched to 09:40:54 (80 s): no keep-alive line after the
  restart, so off is honoured at the next Run.

**Finding: `run stop`'s reply says `run: running`.** Both times `run stop`
answered `run: running` (exit 0), though the system log shows "Profile
stopped" at the same second and `state` straight after says `run: stopped`.
`_run_stop` (gremlin/control_api.py) reads `_run_state(backend)` right after
`backend.activate_gremlin(False)`, which evidently finishes the stop later.
The first sweep's row 89 got `run: stopped`, so the reply depends on timing.
`run start` answers `starting` (it has that state); `run stop` has no
"stopping" and reports the old state. Question for the user: should
`run stop` wait for the stop (or answer "stopping")?

## 4. Tracing left on for the overnight check

Start of run: `tracing: no`, every category ticked (hidhide,
screen-saver-mode, window, timing, osc and all 5 osc areas). End: `tracing:
yes`, the same categories all ticked (none changed), so Screen Saver Mode's
wake-cause and date lines are captured. `global/trace/keep-on` read from
configuration.json before and after: `False` both times (not changed), so
tracing goes off again if the program restarts. The timing category writes one
line every 10 s while events arrive, so trace.log grows overnight within its
size limit.

## End state (09:41)

- `state`: run `running`, mode Default, `unsaved: no`, health 0, tracing yes.
- `windows`: only the main window.
- Options: keep-alive `no`, control switch `yes` (never touched), Double Tap
  duration 0.5, Playback mode Sequential (all as at the start).
- Profile file identical to the backup; view on Home.
