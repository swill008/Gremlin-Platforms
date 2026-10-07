# Hands-on results: 02 Devices & input, 06 Runtime & outputs, gap list items 3-5, catch-up rows for 02/06  (agent H2, 2026-10-07)

Set-up for every probe: temp USERPROFILE under `.agent-logs/handson/H2/home/<probe>`,
`GREMLIN_OFFLINE=1`, off-screen (`offscreen:configfile=` 1920 x 1080), no keyboard or
mouse hook, the program's key/mouse output kept in-process (`test/fake_input.py`),
stand-in sticks through `test/fake_hardware.py`'s `FakeDill` (said per row). The real
vJoy driver was used only as test/integration does (acquire, write, reset, release) and
only after checking the user's Gremlin was not running; all three vJoy devices were
free and at rest at the end (`.agent-logs/handson/H2/read_vjoy_state.py`). HidHide and
ViGEm were stand-ins only. Probe scripts and their output (`<probe>.out.txt`) are in
`.agent-logs/handson/H2/`. Baseline: the 25 test files behind these rows, 375 passed
(`.agent-logs/handson/H2/baseline_pytest.txt`).

| Row | What was checked | How (off-screen / real screen / fake hardware) | Result | Evidence |
|---|---|---|---|---|
| 02 S3 | Home: one card per stick (twins "T.16000M" / "T.16000M (2)", "TWCS Throttle"), "vJoy 1", "vJoy 2", "Xbox 360 Controller"; with an own Xbox pad plugged in, no card for it | off-screen, fake hardware | PASS | `.agent-logs/handson/H2/s3_home.png`, `probe_home_run.out.txt` (cards); `.agent-logs/handson/H2/b2b_home_with_pad.png`, `probe_devinfo.out.txt` home-cards (no pad card) |
| 02 S53 | While running: mouse hook not running; mouse events from the hook's callback (left/right/middle/back/forward/wheel) reach no profile handler | off-screen, events fed to `EventListener._mouse_handler` | PASS | `probe_alias_mouse.out.txt` S53-running (mouse-hook-running false), S53-mouse-events-reaching-the-profile [] |
| 02 S66 | HidHide hides a stick from games, the program still sees it | needs the real driver with settings changed | BLOCKED | contract: no HidHide setting changes; model side covered by test_final_02 S76 tests (passed) |
| 02 S67 | Without the driver the window says "HidHide is not installed", plus the install note; switches greyed | off-screen, stand-in driver (absent) | PASS | `.agent-logs/handson/H2/hidhide_absent.png`, `probe_hidhide_absent.out.txt` |
| 02 S68 | Control off: note "Turn on 'Gremlin-Platforms controls HidHide' (above) … can't be changed."; no driver writes | off-screen, stand-in driver | PASS | `.agent-logs/handson/H2/hidhide_present.png`; driver-writes [] |
| 02 S74 | A device hidden in the driver (Enabled + on the list) is dimmed (opacity 0.55) and shows HIDDEN; the other is not | off-screen, stand-in driver | PASS | `.agent-logs/handson/H2/hidhide_present.png`; hidden-marks in `probe_hidhide_present.out.txt` |
| 02 Q7 / B2a (GL-122) / gap item 3 | Throttle resting at 80 % before start, Run without moving it | REAL loopback: vJoy 3 Z held at 80 % by a feeder process, real dill.dll, program Run path | FAIL | `probe_gl122_both.out.txt`: winmm reads Z 52428 (80 %); dill sends no event in 3 s; `dill.get_axis` = 0; Run sends 0.0 for Z; after a real move dill reports 0.7 |
| B2a (GL-126) / gap item 4 | Keys while the program is busy (main thread blocked 3 s): hook stays quick, events arrive afterwards, keys keep working, no restart | off-screen; the hook procedure called from a stand-in hook thread (no OS input) | PASS | `probe_gl126.out.txt`: hook proc max 0.28 ms while busy; 10/10 events delivered right after; 6/6 later keys arrive |
| B2a (G17) | Hold a bound key, Ctrl+Alt+Del, Esc, press again: fires | needs a person (secure desktop) | PERSON | closest: test_a_press_after_a_lost_release_is_a_new_press (passed) |
| B2a (Q4) | Map A to send B; B bound; press A: B binding doesn't fire | needs real SendInput through the hook | PERSON | closest: test_the_hook_marks_the_programs_own_keys, test_own_keys_are_ignored_while_a_run_is_on (passed) |
| B2b | HidHide window open: plugging a stick shows it in the list; closed: no reloads | off-screen, stand-in driver + fake hardware hot-plug | PASS | `.agent-logs/handson/H2/hidhide_after_plug.png`, rows-after-plug [New Stick, T.16000M, TWCS Throttle]; closed: test_hidhide_stops_reloading_when_its_window_is_closed (passed) |
| B2b (Q6) / 02 S9 | Device Information lists a left-out vJoy ("left out (see message)") and the program's own Xbox pad ("this program's Xbox pad") | off-screen, fake hardware (vJoy 2 discrete hats, own pad) | FAIL | `.agent-logs/handson/H2/b2b_device_information.png`: only 4 rows, neither row shown; `dbg_devicetype.out.txt` |
| B2b | Calibration on a stick whose module claims axes 1 and 3: the others say "(not claimed)" | off-screen, fake hardware | PASS | `.agent-logs/handson/H2/b2b_calibration_not_claimed.png`; "Y Axis (not claimed)", "X Rotation (not claimed)" |
| C3b | Listen for mouse buttons, macro Record with mouse | needs a real mouse | PERSON | closest: test_listen_ending_does_not_cut_off_a_mouse_recording, test_a_listen_closed_early_lets_go_of_the_mouse_hook (passed) |
| C3b | HidHide window with the real driver (control on, Enabled, tick, Allow/Block), joy.cpl | would change HidHide settings | BLOCKED | contract forbids HidHide changes |
| C3b | Run with an Xbox output: no device change, no reload, Steam doesn't flap | needs a real virtual pad | PERSON | closest: test_s26_plug_events_of_the_programs_own_xbox_pads_are_ignored (passed); stand-in ViGEm plug/unplug seen in `probe_vjoy_run.out.txt` |
| C3b | Stick alias shown in Live Log Reader Input Monitor | off-screen, fake hardware | PASS | `.agent-logs/handson/H2/c3b_input_monitor_alias.png`; "Left Stick · Button 2 pressed", raw name absent |
| C1 (02) | HidHide window at 100 % UI scale: no scrollbar | off-screen 1920 x 1080, default size 720 x 640 | PASS | body scrollbar size 1.0 (nothing to scroll); `.agent-logs/handson/H2/hidhide_present.png` |
| 06 S1 | Run: button reads Stop in the accent colour, status Running; Stop: Run, normal colour, Stopped | off-screen | PASS | `.agent-logs/handson/H2/s1_running.png`, `.agent-logs/handson/H2/s1_stopped.png`; colour #3e65ff = Style.accent, then #ffffff |
| 06 Q6 (Keyboard page) + batch 2 B1 | Edited Keyboard action pane, Run from toolbar and from the tray's Run: "Save or discard the open action first?"; Save runs with the change, Discard without, Cancel stays stopped | off-screen; tray via the same call system_tray._toggle_run makes | PASS | `.agent-logs/handson/H2/q6_run_gate.png`; `probe_rungate.out.txt` (6 cases) |
| 06 Q6 (Configuration, Logical Device panes) | Same question from those panes | not driven | PERSON | Main.qml toggleRun is shared; contract tests test_each_pane_answers_close_action_panes passed |
| 06 S17 / batch 1 GL-063 | Quit (File > Exit path) while running with a vJoy button held and the Xbox pad plugged in | REAL vJoy output, fake stick, stand-in ViGEm | FAIL | `probe_vjoy_run.out.txt` D-quit: vJoy free and pad unplugged, but winmm still reads vJoy 1 button 3 pressed (0b100) after the quit |
| 06 S54 / batch 3 C3a | Held vJoy idle over a minute is kept alive; after Stop no keep-alive, vJoy free | REAL vJoy output, fake stick | FAIL | `probe_keepalive.out.txt`: first re-send 119.3 s after the last write (spec: 60 s); after Stop: nothing armed, no calls, vJoy free (that part passes) |
| 06 S73 (WAV) | Real decoding at 100 % and 30 % through the program's AudioSample (not played) | off-screen, Windows WAVs | PASS | `probe_sound.out.txt`: peak ratio 0.30 for both files |
| 06 S73 (MP3, OGG, hearing) | MP3 and OGG decode; quieter at 30 % by ear | no MP3/OGG file on this PC; sound must be heard | PERSON | modes covered by test_stage1_runtime sound tests (passed) |
| 06 S76 | Text to Speech editor volume reads 0-100 ("Volume (%)", 100; 30 for a stored 0.3) | off-screen, action added through the editor's Add Action | PASS | `.agent-logs/handson/H2/s76_tts_volume.png`; `probe_tts_setup.out.txt` |
| batch 1 GL-047 | Tempo (long press -> vJoy button 2), hold, Stop before the 1 s long press: nothing fires, vJoy free | REAL vJoy output, fake stick | PASS | `probe_vjoy_run.out.txt` A-tempo: no SetBtn from the press, button 2 never set, status free, winmm buttons 0 |
| batch 2 B5a | Pane open, Run: page shows "Profile running: stop it to edit" | off-screen | PASS | `.agent-logs/handson/H2/b5a_keyboard_running.png`; running-texts |
| batch 2 B5b | TTS under Tempo / in a macro / on a keyboard key is heard, Options "(default)" voice | must be heard | PERSON | closest: test_speech_uses_the_options_voice_and_the_queue_modes, test_choosing_default_saves_no_voice_and_speaks_with_the_default (passed) |
| batch 3 C4 (vJoy) | Relative axis on Map to vJoy: moves while held (about 96 writes/s), stops at Stop, next Run clean | REAL vJoy output, fake stick | PASS | `probe_relative.out.txt` (288 writes in 3 s, one loop); `probe_vjoy_run.out.txt` B-relative: no writes after Stop |
| batch 3 C4 (Logical Device) | Relative axis on Map to Logical Device ends at Stop, next Run clean | automated tests only | PASS | test_the_logical_device_relative_loop_ends_with_stop, test_a_new_loop_does_not_wait_for_the_old_one[*] (passed) |
| batch 3 C1 (06) | Module Setup while running says "Saved changes work at once." | off-screen | PASS | `.agent-logs/handson/H2/c1_module_setup_running.png`: "The profile is running. Saved changes work at once." |
| gap item 5 (GL-003) | No vJoy (simulated in-process: driver off, no devices), open a profile with 5 Map to vJoy actions: opens, shows them, runs, saves all 5 back | off-screen, fake hardware, vJoy DLL answers patched in-process | PASS | `.agent-logs/handson/H2/gl003_opened.png`, `.agent-logs/handson/H2/gl003_configuration.png`, `.agent-logs/handson/H2/gl003_running.png`; map-to-vjoy-kept-on-save 5/5 |

Counts: PASS 20, FAIL 4, BLOCKED 2, PERSON 7 (33 rows).

## Failures

**02 Q7 / B2a / gap item 3 (GL-122), spec 02 Q7 (decision: read the real position from the driver for an axis not yet seen), 06 S8-S9.** With vJoy 3 as the "throttle" held at 80 % before the program started (Windows/winmm reads Z 52428 = 80 %), the real dill.dll sent no event for it in 3 s, and `dill.DILL.get_axis` returned 0 (centre). So the batch-2 fix in `gremlin/event_handler.py:608-622` (`EventListener.axis_value` reads `dill.DILL.get_axis` for an unseen axis) reads 0, and Run's refresh sent 0.0 for Z: the throttle is still sent as centre until it moves. After a real movement dill reported it at once (raw 22936, program 0.70). This also answers the question in Q7: dill.dll does not send starting values, and its `get_axis` gives only what its events have set. The unit test (test_an_axis_not_yet_seen_is_read_from_the_driver) passes because it fakes `get_axis`. Suggested fix: read the starting position some other way on the input side (dill polling the device state at start, or a DirectInput/winmm read through the input module), then cache it; needs a design decision.

**B2b (Q6) / 02 S9 (D-02-Q6, D-02-Q6-WORDING).** The Device Information window shows only the devices the program uses: no left-out vJoy row and no "this program's Xbox pad" row (the data has both: `information_devices()` returns them with their notes). Cause: `gremlin/ui/device.py:308` `deviceType = QtCore.Property(str, fset=_change_device_type)` has no getter, so QML's `DeviceListModel { deviceType: "information" }` (qml/DialogDeviceInformation.qml:112) is silently ignored and the model stays "all" (proved in `dbg_devicetype.out.txt`: set from QML -> "all", 4 rows; set from Python -> "information"; the property is not readable). The unit test sets it from Python, so it passes. Same silent drop for `deviceType: "physical"` in qml/Main.qml:1456 and qml/DialogSwapDevices.qml:55 (those lists likely include vJoy devices; not checked on screen). Suggested fix: give the property a getter (and notify).

**06 S17 / batch 1 GL-063 (also S29, S19; decision 06 Q2's "held-output release and the driver reset already let go").** Quitting while running left no vJoy device held (status free) and unplugged the stand-in Xbox pad, but vJoy 1 button 3, held at the quit, is still pressed in Windows after the quit (winmm 0b100); a relative axis stays where it was. The same happens at Stop: in a first run with a Tempo set to fire on press, vJoy 1 button 1 stayed pressed after Stop and was pressed again at the next Run (winmm 0b1 through later Runs). Cause: at release `VJoy.invalidate()` (vjoy/vjoy.py:811) calls `VJoy.reset()` (vjoy/vjoy.py:771-797), which does ResetVJD and then writes back every value from `VJoyStateCache` (including held buttons) before RelinquishVJD; reached from `output.reset_vjoy()` -> `VJoyProxy.reset()` (vjoy/vjoy.py:947). Suggested fix: at Stop/quit put the device at rest (clear its cache entry, or reset without restoring) before releasing it; the spec does not say in so many words what a released vJoy should show, so this may need the user's word (S17 hands-on expects "vJoy Monitor idle").

**06 S54 / batch 3 C3a.** The keep-alive re-sent an idle held vJoy only 119.3 s after its last write, not after 60 s. Cause: `_keep_alive_check` (gremlin/modules/output.py:288-305) runs every `_KEEP_ALIVE_S` from when the device was opened and only resets if the device has been idle for 60 s at that moment; a write just after the open (the usual case) makes the first check find 59.99 s and wait another full 60 s. Suggested fix: re-arm the check for the time left until 60 s after the last write. After Stop nothing was armed, no driver call was made and vJoy was free (that half passes).

## Blocked (why)

- 02 S66 and C3b "HidHide window with the real driver": both need HidHide settings changed on the real driver (control on, Enabled, ticks, lists); the contract forbids that. The window and model side was checked with a stand-in driver (S67, S68, S74, plug/unplug rows).

## Needs a person (what exactly to do and what to look for)

1. GL-122 / 02 Q7 with a real throttle: set the throttle at about 80 %, start the program, Run without touching it; vJoy Monitor/Viewer shows the output axis at centre (expected FAIL, see above) until the throttle moves.
2. GL-126 with real keys: open a large profile (or anything that keeps the program busy a few seconds) and type in another program and press bound keys meanwhile; keys reach the other program at once, bindings work afterwards without a restart. (Program side PASS above.)
3. G17: hold a bound key, press Ctrl+Alt+Del, Esc back, press the key again: the binding fires.
4. Q4: map key A to send B, bind B to something else, Run, press A: B's binding does not fire.
5. Plug and unplug a real stick with the HidHide window open (list follows), then closed (no delay or freeze).
6. Listen for mouse buttons (Keyboard page, Script settings) and macro Record with the mouse: each button and the wheel is caught; ending one doesn't cut off the other.
7. HidHide with the real driver (02 S66, C3b): control on, HidHide Enabled, tick a stick, try Allow and Block list; Test HidHide (joy.cpl) no longer lists it; the program still reacts to it.
8. Run a profile with an Xbox output so the program plugs in its pad: no device change, no reload, Steam does not flap.
9. 02 S3 on the real PC: two sticks, two vJoy devices, ViGEm: one card each, no card for the program's own Xbox pad. 02 S53: Run, click every mouse button and turn the wheel: nothing fires, Live Log shows no input.
10. 06 Q6 on the Configuration page and the Logical Device page: change an open action, press Run (toolbar, then tray): the question shows; Save / Discard / Cancel as on the Keyboard page.
11. 06 S73: one WAV, one MP3, one OGG Play Sound, each at 30 % and 100 %: each plays, quieter at 30 %.
12. Batch 2 B5b: Text to Speech under a Tempo, inside a macro and on a keyboard key, with Options voice "(default)": speech is heard each time with the chosen voice.
13. GL-003 on a PC or VM without vJoy: open a profile that uses Map to vJoy; it opens, keeps its actions, saves them back (simulated PASS above). Note: nothing on screen says vJoy is missing; the editor rows say "(no output module)" and the log says "Output blocked … not claimed by its output module".
14. GL-063 / GL-047 with the vJoy Monitor open: quit while holding a mapped button: the Monitor should be idle (expected FAIL, button stays lit); Tempo hold + Stop before the long press: nothing lights.

## Notes for the lead

- Probe artefact found and avoided: driving the app with `QTest.qWait` starves worker threads of the GIL (a 10 ms sleep took ~65 ms, the relative-axis loop wrote ~3 times a second). Under `app.exec()` the same loop wrote ~96 times a second. Timing rows were measured under `app.exec()`.
- The keep-alive probe ran without the hang tool: its stall watch ends an event loop idle for 30 s, which this row needs for two minutes; the probe's own watchdog (170 s) bounded it.
- The program `chdir`s to `dirname(sys.argv[0])` at import (joystick_gremlin.py:97-101): a script that imports it from another folder must set `sys.argv[0]` first, or a relative `configfile=` breaks with a silent exit 127.

# Catch-up test plan rows (claude/catchup-test-plan.md)

The hands-on rows that belong to pages 02 and 06 are the rows above: batch 1 047
(GL-047 row), 063 (06 S17 row); batch 2 B1 tray Run (06 Q6 row), B2a (Q7, GL-126, G17,
Q4 rows), B2b (HidHide plug/unplug, Device Information, Calibration rows), B5a Run
read-only (B5a row), B5b speech (B5b row); batch 3 C1 HidHide 100 % and Module Setup
while running, C3a idle vJoy keep-alive (S54 row), C3b (all four C3b rows), C4
relative axis (two C4 rows). The other catch-up hands-on rows are on the pages of the
other hands-on agents and were not checked here: batch 1 053 (page 04), 096 and 105
(page 05); batch 2 B1 tray/Exit/X (page 01/09), B3 (03), B4 (04), B5a Keyboard Add Key
and switching keys (05), B6 (07), B7 (08); batch 3 C1 Options picker titles (01), C2
(01/04), C3a Profile Settings with real vJoy, Rename rows, Home after Delete Device (03/04),
C4 Configuration Type box / Merge Axis / Deadzone (05), C5 (07/08).
