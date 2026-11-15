# Screen Saver Mode, batch 4: two timers and keeping the displays off (2026-11-15)

User (2026-11-15): "lets do a timer that is editable between the screensaver and the off"; then, after the
tests below, approved 1 a (keep the displays off), 2 a (show the wake count), 3 a (drop "blank screen saver
first"), 4 b (two timers in this build). Base rules: contract.md (every agent follows them).

## Facts measured on the user's PC (2026-11-15, claude/plans/oled-idle-watcher-study.md section 6)
- One power-off: Windows turns the displays back on within 7-270 ms, with no keyboard/mouse input, nothing
  holding the display, Gremlin's listener off too. With all four always-streaming devices disabled it stayed off
  30 s; with only the mic, or only the three VKB sticks, disabled it still woke: ANY always-streaming device wakes it.
- DDC/CI: the LG OLED lists power mode (D6 1/4) but ignores it (stayed "1", stayed on). Not usable.
- tools/monitor_keep_off_test.py: power off, then re-send whenever Windows reports the display ON (power-setting
  notification GUID_CONSOLE_DISPLAY_STATE 6FE69556-704A-47A0-8F24-C28D936FDA47) without keyboard/mouse input,
  at most once a second; stop on the first real input. 136 re-sends in 3.5 min; the screens stayed dark and the
  LG OLED went into its panel maintenance (user: "it went into maint mode. seems to work.").

## Behaviour
- **Two timers** replace the one Action choice (S4 changed, reverses decision 15):
  - **Screen saver** switch (on at first) + wait: Windows' screen saver wait shown and followed while no time is
    typed; a typed time overrides until cleared. Starts the screen saver chosen in Windows. No screen saver
    chosen in Windows → that row says "No screen saver is chosen in Windows." and does nothing (S8).
  - **Power off displays** switch (on at first) + wait: Windows' display-off time shown/followed; typed overrides.
  - Both count from the last keyboard/mouse input; each fires once per idle period; holds (full screen, display
    request, locked) hold both. If both are on and the power-off wait is not longer than the screen-saver wait,
    the window says "Power off comes at or before the screen saver: the screen saver won't show." (both still work).
- **Keeping the displays off** (S6 changed): after power off fires, Gremlin listens for Windows' display state
  (RegisterPowerSettingNotification on the input listener's hidden window, same thread). While "keep off" is
  active (set when power off fires, cleared by the next counted keyboard/mouse input or when the mode is switched
  off), each display-ON report is answered with one power-off to the listener window, at most once a second
  (POWER_OFF_GAP_S = 1.0). Count the re-sends per idle period and in total since start.
- **Wake count shown** (new S20): status line, while keeping off or after: "Windows turned the displays back on
  N times: devices that never go quiet (see Refresh Devices)." N = re-sends in the current/last idle period.
  Trace each re-send (S16) and log one INFO line per idle period with the count when the keep-off ends.
- Remove "blank screen saver first" (never committed; dropped by user 3 a).

## Settings (unreleased: no compatibility; replace the old keys)
section "global", group "screen-saver-mode": "enabled" (Bool False, unchanged), "screen-saver-on" (Bool True),
"screen-saver-wait-s" (Int 0 = Windows' time), "power-off-on" (Bool True), "power-off-wait-s" (Int 0),
"hold-fullscreen" (Bool True, unchanged). Remove "action" and "wait-override-s". History/Options names
(gremlin/ui/option.py _KEY_TITLES, _HIDDEN): "Screen Saver Mode", "Screen saver", "Screen saver wait",
"Power off displays", "Power off wait", "Hold off during full-screen programs".

## API (core)
`Settings(enabled, screen_saver_on=True, screen_saver_wait_s=0, power_off_on=True, power_off_wait_s=0,
hold_fullscreen=True)`. `Status` replaces action/wait fields with per-timer fields: `saver_wait_s`,
`saver_windows_wait_s`, `saver_from_windows`, `saver_fired`, `saver_remaining_s`, `off_wait_s`, `off_windows_wait_s`,
`off_from_windows`, `off_fired`, `off_remaining_s`, `keeping_off: bool`, `wakes: int`; keep enabled, listening,
idle_s, windows_idle_s, hold, hold_program, problem (screen-saver row: "no_screen_saver"; both rows: windows-never
per row → `saver_problem`, `off_problem`), last_reset_*, program_input_per_min. Remove ACTION_* constants.

## Owners
| Agent | Files |
|---|---|
| SSM-CORE4 | gremlin/screen_saver_mode.py, test/unit/test_ssm_core.py |
| SSM-UI4 | gremlin/ui/screen_saver_mode_model.py, qml/WindowScreenSaverMode.qml, gremlin/ui/option.py (the _KEY_TITLES / _HIDDEN rows only), test/unit/test_ssm_ui.py, ssm_ui_fakes.py, ssm_ui_smoke.py, test/unit/test_ssm_e2e.py |
| SSM-DOCS4 | claude/program-map/12-screen-saver-mode.md (S4, S5, S6, S8, S10 changed with "(was: …)"; new S20; section 10 gaps SSM-POWER-OFF-WAKES (cause, measurements) and SSM-DDC-IGNORED; sections 2-6, 11, 12 rows D-12-SSM-TWO-TIMERS (4 b), D-12-SSM-KEEP-OFF (1 a), D-12-SSM-WAKE-COUNT (2 a)), README counts, claude/glossary.md, qml/help/tools.js, release-notes/1.0.38.md (two timers, keeping the displays off) |
