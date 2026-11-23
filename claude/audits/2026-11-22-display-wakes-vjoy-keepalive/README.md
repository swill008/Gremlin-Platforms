# Displays waking while Screen Saver Mode keeps them off (2026-11-22)

User report: with Gremlin running and the user away, the two side monitors kept
waking. Investigated 18:50-22:25 (lead, agents WATCH and VJTEST).

## Findings

- Any vJoy write makes Windows count user input and turn the displays on
  (vJoy 2.2.2, installed 2026-11-22 05:29). Seen at every write of the probe
  (vjoy-idle-probe.log: display ON 0.2-1.5 s after each write) and never
  between writes.
- While a Run holds vJoy, the keep-alive (gremlin/modules/output.py
  `_keep_alive_check` -> `VJoy.reset()`, spec 06 S54) writes every idle held
  device every 60 s, so Windows turned the displays on about once a minute;
  Screen Saver Mode turned them off again. system.log: 385 wakes 12:22-15:00,
  11 at 15:13-15:18, 50 at 18:38-19:03 (all during a Run); 0-1 per period with
  no Run. The trace does not log keep-alive resets, so the link per wake is
  inferred from timing, not seen line by line.
- The Steam Controller's mouse part (HID VID_28DE PID_1302 Col01) also woke the
  displays once (19:20:41): Screen Saver Mode turns off only its COL03 part.
- Screen Saver Mode's idle counter works: it counts only keyboard/mouse from the
  Wake PC devices; the PD200X microphone and VKB stick HID reports don't count.

## vJoy idle test (does vJoy 2.2.2 need the keep-alive?)

vjoy_idle_probe.py.txt (plain ctypes, not program code; kept as .txt so the linters skip it) held vJoy 1 with no writes
and checked at 5, 15, 30, 60, 120 and 180 min: device still owned, a new axis
value and a button press/release seen by Windows (joyGetPosEx) within 5 ms /
~270 ms. All 6 checkpoints PASS, 0 drift between checkpoints
(vjoy-idle-probe.log, 19:24:39-22:24:42). The dry run's FAILs were the
probe's own too-short button-off wait (100 ms), fixed before the real run.

Conclusion: on vJoy 2.2.2 an idle held device stays usable for at least
180 min without a keep-alive.

Decision (user, 2026-11-23, "1a, 2a, build it"): the keep-alive goes on an
Options switch, General › vJoy › "Keep vJoy devices awake", off by default,
manual only (for older vJoy versions). The Steam Controller's mouse part stays
as it is (it woke the displays once in about 9 hours).
