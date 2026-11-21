# YAJB 0.1.5 vs Gremlin-Platforms: was code taken? (2026-11-20)

Read-only comparison. YAJB copy kept at E:\Users\Stacie\Documents\Reference\YAJB-0.1.5
(installer checksum matches yajb.vercel.app/latest.json: 96a88dc0...c49c1d).

## Facts

- Our fork (swill008/Gremlin-Platforms) is public on GitHub; the photo editor
  with leader lines (qml/VkbRigEditor.qml, RigLeaderLayer.qml) was public from
  2026-09-13 / 2026-10-02. YAJB's repo (Morgan-Caldbeck/yajb) is not public; its
  site is yajb.vercel.app. An older name in its code: "SC VKB Binder".
- Languages: YAJB is TypeScript/React in Electron; ours is Python + QML. No code
  can be pasted between them; only ideas or translated logic.
- Names and strings: none of Gremlin, GremlinEx, WhiteMagic, swill008, Device
  Pack, Screen Saver, Input Tester, dill, ViGEm, Device Map, bootstrap-icons,
  device helper appears in YAJB's code (main process 1,275 lines, renderer app
  ~12,000 lines).
- HidHide: YAJB runs HidHideCLI.exe (--dev-gaming, --dev-hide, --cloak-on) and
  bundles the HidHide installer. Ours talks to the driver directly with IOCTLs
  (gremlin/hidhide_driver.py) and bundles nothing.
- vJoy: YAJB loads vJoyInterface.dll with koffi (8 calls), fixed devices 1/2,
  an "Alt" layer at button offset 64, and bundles vJoy 2.2.2.0 with a
  vJoyConfig script. Ours uses the vjoy/ package inherited from JoystickGremlin
  (ctypes) and bundles neither.
- Input: YAJB reads sticks with SDL (@kmamal/sdl); ours with dill (DirectInput,
  C++).
- Purpose: YAJB writes Star Citizen actionmaps.xml and types a reload command
  into the game console; ours maps inputs to vJoy/ViGEm/keyboard through
  profiles and action plugins. File formats differ (.yajbstick JSON vs our XML).
- Stick pictures: YAJB places fixed dots on a product photo with callout
  columns at the sides; ours is a free-form canvas (Button Map) with chips,
  leader lines and planes. Similar idea (photo + labels + lines), different
  build.
- Comment wording in both is plain British-style English ("isn't", "Lets go
  of", "centred"); style alone is not evidence of copying.

## Conclusion

No sign that YAJB's code was taken from ours: no shared identifiers, strings,
file formats, algorithms or libraries. Overlap is at the idea level (vJoy +
HidHide + a labelled stick photo), which many joystick tools share.

Limits: YAJB ships compiled and minified with most comments stripped, its
source history is private, and idea-level inspiration can't be proved or ruled
out from the program alone.

## Follow-up study (2026-11-21): speed, architecture, UI, packaging

### Is YAJB faster? (read from its code, not timed)

- YAJB main process (`out/main/index.js` ~lines 138-250): `setInterval(() =>
  this.snapshot(), 33)`, about 30 Hz. `snapshot()` builds a signature from every
  stick with axes rounded to 0.02 (`Math.round(v*50)/50`) and calls `syncAll()`
  only when the signature changes. So a press can wait up to 33 ms before vJoy
  sees it, and a slow fine axis movement is only sent when it crosses a 2% step.
  `sync()` then sends only what changed (buttons, axes scaled 1-32768, POVs with
  -1 -> 0xFFFFFFFF centred).
- Ours: dill calls our handler per input event
  (`gremlin/event_handler.py:366`, `set_input_event_callback`). dill's own
  DirectInput reading is compiled upstream code; not checked inside.
- Footprint: YAJB installer 145 MB (Electron bundles Chromium); ours 54 MB.
- Scope: YAJB = two VKB sticks -> vJoy 1/2, one Alt layer (button offset 64),
  writes Star Citizen actionmaps.xml. Ours = any device, profiles/modes,
  actions/macros, vJoy/Xbox (ViGEm)/keyboard/OSC outputs, Library, History,
  Device Map, Screen Saver Mode.
- Conclusion: not faster, narrower. Switching architecture would be a full
  rewrite in another language for less. Not recommended.

### Where YAJB is better (ideas only)

1. Look: five skins (manual, avionics, hud, retro, brand), cockpit fonts, drawn
   hats/buttons that light up on press.
2. Setup: installer bundles vJoy and HidHide and sets up the vJoy devices.
3. Updates: checks its site and installs new versions itself.
4. Game export: one click writes the game's keybind file.

### Can we use its UI components?

- Not directly. They are React components (HeroUI, HeroUI Pro, YAJB's own);
  they need a browser and can't run in QML.
- Licences: HeroUI is MIT; HeroUI Pro is a paid licence bought by YAJB's
  author (not reusable); YAJB's own code has no licence (all rights reserved).
- Qt WebEngine could host web pages, but adds ~100 MB (a second Chromium), two
  UI systems and a Python<->JavaScript bridge per screen. Not recommended.
- Usable, rebuilt in QML:
  - Phosphor icons (MIT; ~1,500 in the full set, 29 used by YAJB): take from
    Phosphor's own release, not from YAJB.
  - Fonts (SIL Open Font License): Rajdhani, JetBrains Mono, B612, Exo 2, IBM
    Plex, Manrope, Rubik: take from Google Fonts, not from YAJB.
  - Skin colours, spacing, corner sizes: reference for our own `theme/` files.
  - Drawn hats, buttons, stick axes: idea only; redraw with QML shapes (their
    geometry code is all rights reserved) until the user's licence check.
  - Control behaviour (selects, tabs): Qt Quick Controls already cover it.
- Options given to the user (open): a) QML skin system with their look as
  reference (recommended), b) icons and fonts only, c) look into Qt
  WebEngine, d) nothing for now.

### Mock-up shown in chat (2026-11-21)

Our mapping screen in a YAJB-style "manual" skin, drawn inline: paper
colours, Rajdhani + JetBrains Mono, top bar (profile, mode, Running), device and
output list on the left, the stick in the middle with a square hat, button dots
in four states (idle, mapped, shift button, pressed now), callout labels with
lines on both sides and small X/Y axis bars, and on the right the selected
control's action list (vJoy button, macro, Add action) and a skin picker
(Manual, HUD, Avionics, Retro). Menus, words and layout stay ours; only the look
follows theirs. In the real program the outline would be the Button Map photo.

### Packaging the drivers: what YAJB does and what we do today

- YAJB bundles `vJoySetup_v2.2.2.0_Win10_Win11.exe` (5.3 MB, signed by Brunner
  Elektronik AG, MIT licence by Shaul Eizikovich) and `HidHide_1.5.230_x64.exe`
  (8.1 MB, signed by Nefarius Software Solutions e.U., MIT licence). It does not
  bundle ViGEmBus.
- `setup-vjoy.cmd` (run elevated by its installer and from its Settings):
  installs vJoy silently (`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-`) only
  if `%ProgramFiles%\vJoy\x64\vJoyInterface.dll` is missing; checks devices 1
  and 2 with `vJoyConfig -t N` (8 axes, 128 buttons, 4 continuous POVs) and
  reconfigures only if they differ, because a change removes and re-creates the
  virtual sticks and a running game loses them. Logs to
  `%TEMP%\yajb-vjoy-setup.log`. Exit codes 10/11 on failure.
- Ours today: `installer/gremlin_platforms.iss` installs no drivers. We ship only
  the client DLLs (`vjoy/vJoyInterface.dll`, `vigem/ViGEmClient.dll`); the user
  installs vJoy and ViGEmBus themselves. The app checks: `vjoy.py` `vJoyEnabled`,
  `vigem/ids.py` driver version, the Xbox Setup window (`DialogXboxSetup.qml`,
  `XboxDriverCheck.qml`) with a Download link.
