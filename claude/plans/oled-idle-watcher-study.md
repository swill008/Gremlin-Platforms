# Study: Idle-timer blockers & an "OLED idle watcher" for Gremlin Platforms

Written 2026-11-15 from a diagnostic session on the user's Windows PC. Purpose: give the Gremlin Platforms
session everything needed to build a built-in idle watcher that makes the screensaver / display-off fire
even though some HID devices keep Windows' idle timer pinned at zero.

## 1. The problem (user requirement)

- Main monitor is an **LG UltraGear OLED (3440x1440)**. Burn-in risk: the screen MUST blank or the
  screensaver MUST fire when the user walks away.
- Windows settings: **blank screensaver (`scrnsave.scr`) after 3 min**, **display off after 5 min**
  (power plan "High performance", AC VIDEOIDLE = 300 s), system sleep = Never.
- Neither ever happened. Root cause: Windows' last-input time (`GetLastInputInfo`) is refreshed every
  ~15–50 ms with nobody touching anything, so the idle countdown never starts.

## 2. Measured findings

### Method (reproducible)
1. Sample `GetLastInputInfo` vs `GetTickCount` every 100 ms; count how often `dwTime` changes.
2. Simultaneously install `WH_KEYBOARD_LL` (13) and `WH_MOUSE_LL` (14) hooks and count events.
   - **Gotcha:** a hidden WinForms form + `Application.Run` silently received nothing in this
     environment. What worked: hooks installed on a thread that pumps messages explicitly with
     `MsgWaitForMultipleObjects(…, QS_ALLINPUT 0x4FF)` + `PeekMessage(PM_REMOVE)`. Validate any monitor by
     injecting a mouse move and confirming it is counted before trusting a "0 events" result.
3. Enumerate every HID interface (SetupDi on `HidD_GetHidGuid`), open each with
   `CreateFile(GENERIC_READ, FILE_SHARE_READ|WRITE)`, read input reports for 4 s, count reports/sec.

### Results
| Test (15 s, hands off) | idle-timer resets | LL kb/mouse events |
|---|---|---|
| Normal (all devices on) | 137 | 0 |
| Mic consumer-control disabled, VKB on | 137 | 0 |
| VKB disabled, mic consumer-control on | 137 | 0 |
| **Both disabled** | **0** | 0 |

**Two independent culprits; either one alone is enough to pin the idle timer at 0:**

| Device | HID collection | Reports | Instance ID |
|---|---|---|---|
| **Maono PD200X Podcast Microphone** | Usage page 0x0C (Consumer), usage 0x01 — "HID-compliant consumer control device" (USB MI_03) | ~18/s, constant | `HID\VID_352F&PID_0104&MI_03\B&12148D1&0&0000` |
| **VKBSim NXT SEM THQ FSM.GA** (throttle module) | Usage page 0x01, usage 0x04 (Joystick) | ~12–13/s, constant | `HID\VID_231D&PID_2234\8&707C6B9&0&0000` |

- No keyboard/mouse input involved (0 hook events) — this is NOT mouse jitter or injected input.
- Ruled out: Xbox controller (XInput packet number static), vJoy devices / Gremlin Platforms
  (0 reports with Gremlin closed; closing Gremlin did not help), RustDesk session, keyboard, mouse.
- The VKB also has three latched buttons held (0-indexed 13, 17, 22) and axes at minimum — separate
  issue that caused a phantom "up" in a game; not the idle cause.
- Both devices were **re-enabled** afterwards at the user's request (default state now).
- Separately, RustDesk held a `DISPLAY` power request; a permanent
  `powercfg /requestsoverride PROCESS RustDesk.exe DISPLAY` was added and is still in place.

## 3. Web research — why it happens, known fixes

- Long-standing, widely reported Windows 10/11 behaviour: HID game controllers (and some other HID
  devices) that stream reports continuously are treated as user activity, so idle/screensaver/display-off
  never triggers. Reports go back to ~2015 (VKB Gladiator mk2/NXT, VKB T-Rudder, Thrustmaster
  Warthog/TWCS, Logitech X56, 8BitDo, Xbox-style pads; also USB mics/audio like Razer Seiren V3).
- A Microsoft Q&A thread measured a Warthog throttle resetting the idle timer every ~15 ms via
  `GetLastInputInfo` — same signature as ours. Thrustmaster/VKB say it's a Windows issue; no vendor fix.
- Commonly suggested fixes and their real track record:
  - Uncheck "Allow this device to wake the computer" / `powercfg /devicedisablewake` → **does not help**
    (that's wake-from-sleep, not the idle timer).
  - "Allow this device to save power" → unconfirmed.
  - Windows updates (KB5022360 etc.) → fixed briefly for one or two people in 2023, regressed later;
    user is on build 26200 and still affected.
  - Driver/firmware updates, VKB "eco" settings → no effect reported.
  - **Disable the device (Device Manager / script)** → works, but the controller is unusable.
  - **Switchable USB hub** → works, manual.
- No setting exists to tell Windows "ignore this device for idle purposes". Hence the watcher approach.

Sources: Microsoft Q&A 4356722 (Win11 USB joysticks prevent display standby), Microsoft Q&A 4304790
(HID game controller prevents monitor sleep), answers.microsoft.com "No Idle … with USB Joystick",
MSFS forum thread 258263 "Prevent Controllers From Interfering with Windows Power Management",
VKB-SIM forum t=4591 / t=4882 / t=2118, OpenLogi PR #2162 (periodic HID traffic resetting idle clock),
GetLastInputInfo docs, Maono PD200X FAQ, github.com/letopg/pd200x-linux.

## 4. Proposed feature: built-in "OLED idle watcher"

Idea: keep our OWN idle clock from keyboard + mouse only (ignoring HID/joystick noise), and when it
expires, start the screensaver and/or turn displays off ourselves. Devices stay enabled; no toggling.

### Core design
- **Input source:** `WH_KEYBOARD_LL` + `WH_MOUSE_LL` hooks on a dedicated thread with an explicit message
  pump (see gotcha above). Alternatively Raw Input (`RIDEV_INPUTSINK`) for usage page 0x01 usages 0x02
  (mouse) and 0x06 (keyboard) only. Each event → `last_real_input = now`.
  - Optionally ignore mouse moves with zero/tiny delta to avoid sensor jitter.
  - Decide whether injected input (LLKHF_INJECTED / LLMHF_INJECTED) counts — RustDesk/remote control
    and Gremlin's own vJoy→keyboard macros inject input. Probably: count injected input that did NOT
    come from Gremlin itself (Gremlin can tag its own SendInput via dwExtraInfo and skip those).
- **Optional: count *meaningful* joystick activity** so a long stick-only flight doesn't blank the
  screen: Gremlin already reads every physical device — treat an axis change beyond a deadband
  (e.g. >2–3% of range) or a button *transition* as activity. Static streams (same values repeated,
  latched toggles held) must NOT count. This is the key advantage of building it into Gremlin.
- **Actions when our idle ≥ threshold:**
  - Screensaver: read `HKCU\Control Panel\Desktop` → `SCRNSAVE.EXE`, `ScreenSaveTimeOut`,
    `ScreenSaveActive`; launch `"<scr>" /s`, or `SendMessage(HWND_BROADCAST/GetDesktopWindow,
    WM_SYSCOMMAND, SC_SCREENSAVE, 0)`.
  - Display off: `SendMessage(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)` (or PostMessage).
  - Default thresholds: mirror the Windows values (screensaver 180 s, display 300 s) read from the
    registry / `powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE`; allow override in settings.
  - Fire each action once per idle period; reset when real input arrives (Windows wakes the display
    itself on real input).
- **Suppression (don't blank while it matters):**
  - A full-screen / exclusive app in the foreground (`SHQueryUserNotificationState` →
    QUNS_BUSY / QUNS_RUNNING_D3D_FULL_SCREEN / QUNS_PRESENTATION_MODE), or the active Gremlin profile
    being in "game running" state.
  - Media playback / other apps' legit `ES_DISPLAY_REQUIRED` requests: optional — `powercfg /requests`
    needs admin; `CallNtPowerInformation`/`PowerGetActiveScheme` can't list requests. Simplest: a user
    toggle "respect video playback" using `SHQueryUserNotificationState` + foreground-window heuristics.
  - Workstation locked → nothing to do (Windows handles it).
- **UI/settings:** enable toggle, thresholds, "count joystick movement as activity" + deadband,
  "suppress during full-screen apps", status line showing *our* idle time vs Windows' idle time
  (`GetLastInputInfo`) — handy diagnostic: if Windows' idle is stuck at ~0 while ours counts, the
  watcher is doing its job.
- **Diagnostics tool worth bundling:** the HID report-rate scan (section 2, step 3) as a
  "Which devices keep my PC awake?" button — lists devices sending constant reports.

### Things to verify while building
- Does launching the screensaver while Windows' own idle is 0 keep it running, or does the next VKB/mic
  report dismiss it? (Screensavers usually exit on mouse/keyboard messages, not on HID game-controller
  reports — but test with both devices streaming.) Same for SC_MONITORPOWER: confirm the display stays
  off while the streams continue. If the streams wake the display, fallback is to briefly suspend
  reading/close handles or use the monitor's DDC/CI power-off — test before promising.
- Multi-monitor: user has 4 displays (LG UltraGear OLED primary 3440x1440, two CF15T 1920x1080, LG TV).
  SC_MONITORPOWER affects all.
- HidHide is installed and hides some devices from normal processes; Gremlin is presumably whitelisted.

## 5. Environment facts

- Windows 11 Pro build 26200, PC hostname DESKTOP-DNCONIH. Python app at
  `E:\Users\Stacie\Documents\GitHub\Gremlin-Platforms` (installed build in
  `%LOCALAPPDATA%\Programs\Gremlin-Platforms\gremlin_platforms.exe`).
- Connected input gear: VKB NXT SEM THQ FSM.GA (231D:2234), Xbox controller (045E:0B12 / XInput),
  4 vJoy devices (1234:BEAD) fed by Gremlin, Maono PD200X mic (352F:0104), Razer BlackWidow V3,
  Logitech G502 + receiver. HidHide + ViGEm bus + Virtual Desktop gamepad bus installed.

## 6. Follow-up tests in Gremlin Platforms session (2026-11-15)

Idle-clock resets counted with GetLastInputInfo every 100 ms, 15 s, hands off.

| Setup | Resets / 15 s |
|---|---|
| Normal (HidHide Block list, devices seen by Windows) | 150 |
| HidHide Allow list, VKBs + mic consumer control hidden, no replug | 150 |
| Same, after replugging throttle and mic | 0 |
| HidHide back to Block list, no replug since | 0 |
| Allow list with Gremlin allowed, Gremlin reading the throttle (Reset Devices), no profile running | 150 |

- HidHide only takes effect for a device hidden when Windows sets it up (plug-in or start-up).
- Whoever reads the throttle (Windows or Gremlin) keeps the idle clock reset, so "Gremlin in the middle"
  via HidHide does not work while Gremlin is open. Decision: Gremlin keeps its own idle clock
  from keyboard and mouse only (user, 2026-11-15).
- HidHide restored exactly after every test (settings diffed against a saved copy).

Screen test (scrnsave.scr /s, then SC_MONITORPOWER 2 via PostMessage HWND_BROADCAST), reports flowing
(about 10 resets/s):
- Run 1: the blank screensaver stayed on the full 30 s; all four displays stayed off the full 45 s
  until the user moved the mouse. The reports end neither.
- Run 2: the screensaver ended after 3.8 s because the user moved the mouse (confirmed);
  displays went off and the mouse woke them.
- Separate screensaver tests (user's request): test 1, hands off: ran the full 15 s and was closed by
  the test; test 2, user moved the mouse: ended after 3.6 s, as expected.

Display-request flag (CallNtPowerInformation SystemExecutionState, no admin), 2026-11-15:
nothing playing 0x0; a video playing in a browser window 0x3 (display + system required);
paused 0x0. Gremlin holds off on this flag (spec 12 S15).
