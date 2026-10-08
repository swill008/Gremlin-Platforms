# Device Library

**Approved by the user 2026-10-08. Not built yet.** Written from
the design discussion of 2026-10-08 (decisions D-10-* in
`claude/decisions.md`) and the off-screen Qt prototype in
`.agent-logs/handson/DL/` (renders `dl_main.png`, `dl_menu.png`,
`dl_settings.png`, `dl_copy.png`, `dl_swap.png`, `dl_output.png`; not in
git). It replaces Swap Devices (04 S77-S83) and takes over the deleted
devices folder (03 S90-S91, S98; 08 S86-S87).

## 1. Purpose

One place for every device the program has known: sticks plugged in now,
sticks set up here but unplugged, deleted sticks, and sticks shared by other
people that were never plugged in here. For each device it keeps **saved
setups**: stored copies of its settings and bindings, each with a name and a
description, made by the user or kept automatically (**autosaves**) before
anything replaces them. From a saved setup the user can **copy** it onto a
stick that is plugged in, **swap** two sticks' settings, or **change which
vJoy** a stick's bindings send to. Nothing is moved away from its source:
copying never changes the saved setup or the stick it came from.

Typical uses: a new stick gets an old (unplugged, broken) stick's bindings;
two sticks trade everything; two sticks trade vJoy outputs so a game sees
them the other way round; a friend's shared setup is put on your stick.

## 2. Files (planned)

| Path | What it holds |
|---|---|
| `<library folder>\` (default `<data folder>\device library`) | The Device Library. Takes over the deleted devices folder setting (Options › Folders today). |
| `<library folder>\library.json` | The list: devices (name, description, device id when known, kind: set up here / deleted / shared) and their saved setups (name, description, date, origin, whether it is the user's, what it holds, which profiles and modes its bindings came from, vJoy outputs). |
| `<library folder>\<device>\<saved setup>.zip` | Each saved setup is a Device Pack (08 S49-S55 format), so it can be exported and shared as it is. |
| Old deleted devices folder contents | Read as deleted devices: `<name>\<name>.<stamp>.zip` packs as saved setups; `<stem> <date time>.json` copies as setup-only saved setups. Left where they are. |

Code (planned): a library owner in `gremlin/modules/` (the one writer of
`library.json` and the packs, built on `device_pack.assemble` and the pack
import), a QML model in `gremlin/ui/`, `qml/WindowDeviceLibrary.qml` and its
dialogs. Copy, Swap and Change vJoy Output change profiles only through the
profile owner, and module files only through `modules/store.py`.

## 3. What it owns

- The library list and its saved setups (files above).
- The autosave rules and limit (Device Library Settings).
- Device names and descriptions for devices with no module file here (deleted
  and shared). For devices set up here the name is the module file's friendly
  name (S6).

## 4. Entry points (planned)

| Where | What |
|---|---|
| Home: **Device Library…** button; Tools › Device Setup › **Device Library…** | Opens the window. |
| Card menu: **Copy Setup to Another Stick…**, **Swap with Another Stick…**, **Change vJoy Output…** | Open the window on that card's device and the matching dialog. |
| Delete Device | Keeps the "stick deleted" autosave (S21). |
| Device Pack import onto a stick | Keeps the "before a Device Pack" autosave (S21); a pack opened in the Library is added as a shared device (S31). |

## 5. Talks to

Device Pack (export and import code), module store (`modules/store.py`), the
profile owner (bindings in the open profile and saved profiles), History
(every change it saves is a History entry like any other save), the device
list (which sticks are plugged in), output modules (which vJoy outputs are
claimed).

## 6. Threads and timers

Building and writing packs, reading saved profiles and measuring the folder
size run in the background (program thread rules: `gremlin.threads`, bounded
waits); the window stays responsive and shows when it is busy, as Device Pack
Export does (08 S107). One copy, swap or change at a time.

## 7. Rule breaks

None planned. Layer rule: the window never touches devices, vJoy or ViGEm; it
works on files and the profile through their owners.

## 8. Behaviour spec

### A. The window

- **S1** The Device Library should be a separate window, like the Button Map, with its own menu bar: **File** (Import Device Pack…, Export Saved Setup…, Open Library Folder, Close), **Edit** (Undo, Redo, Rename…, Edit Description…, Delete…, Tidy Library…), **Device** (Save to Device Library…, Copy to Another Stick…, Swap with Another Stick…, Change vJoy Output…), **View** (Connected, Not Connected, Deleted, Shared, Autosaves, Expand All, Collapse All, Search…), **Settings** (Device Library Settings…). Menus follow 01 S66 (only what can be used now). [user decision: D-10-WINDOW]
- **S2** It should open from a Device Library… button on Home and from Tools › Device Setup › Device Library…; the card menu items (03 S88) open it on that card's device. [D-10-WINDOW]
- **S3** The left side should hold filter chips (Connected, Not connected, Deleted, Shared, Autosaves; several at once, each an outline with a tick when on), a search box and the device list; the right side the details of what is selected; a divider between them can be dragged. [D-10-WINDOW, D-10-PROTO]
- **S4** The status bar should show the number of devices and saved setups, the autosave limit, the library's size on disk (e.g. "Library: 48 MB") and the library folder. [D-10-TIDY]
- **S5** Search should match device names and descriptions, saved setup names and descriptions, what a saved setup holds (Setup, Button Map, Appearance, Calibration, Bindings), profile names, mode names, vJoy numbers and autosave reasons; Ctrl+F goes to the box, Esc clears it. [D-10-SEARCH]

### B. Devices

- **S6** There should be one row per device: plugged in now (**Connected**), set up here but unplugged (**Not connected**), deleted (**Deleted**), or added from someone else's pack (**Shared**). Each row shows its name, description, state and number of saved setups. [D-10-LIBRARY]
- **S7** Every device and every saved setup can be renamed and given a description. A device set up here has one name: renaming it in the Library renames it on its Home card and the other way round. [D-10-NAMES]
- **S8** Selecting a device should show its name, description, state, what inputs it has, and when it was last seen.
- **S9** Deleted devices should include what the old deleted devices folder holds (packs and module file copies), without moving those files. [D-10-DELETED]

### C. Saved setups

- **S10** A device row should open with a caret to show its saved setups as rows under it, newest first. Saved setups the user made (or renamed or described, S13) show a save mark; autosaves show an autosave mark. [D-10-ROWS]
- **S11** A saved setup holds any of: Setup (claims, friendly names), Button Map and photo, Appearance, Calibration, and Bindings (from one profile, the modes saved, the vJoy outputs they send to). Selecting one should show its name (renamable), its description (editable in place), when and why it was kept, exactly what it holds, a Button Map photo preview, a short history (saved, description edited, copied to which stick and when), and the actions Copy, Swap, Change vJoy Output, Export and Delete (Delete in red). [D-10-PROTO]
- **S12** Device › Save to Device Library… should keep a saved setup of the selected device (the user's own): its module file now, and its bindings from the profiles the user ticks (one saved setup per profile, named after the profile by default). [D-10-SAVE]
- **S13** An autosave the user renames or describes becomes the user's own and is never removed by the autosave limit. [D-10-AUTOSAVE]
- **S14** Export Saved Setup… should write the saved setup as a Device Pack anywhere the user picks (08 S57 rules). [D-10-SHARE]
- **S15** Delete… should ask first, then remove the saved setup (or a device and all its saved setups). A connected or set-up device is never deleted here (that is Delete Device, 03 K); only its saved setups. [D-10-TIDY]

### D. Autosaves

- **S16** The program should keep an autosave of a stick, without asking, when: the stick is deleted (Delete Device); before Copy replaces its settings; before Swap; before Change vJoy Output; before a Device Pack is put on it. Each can be turned off in Device Library Settings; all are on by default. [D-10-AUTOSAVE]
- **S17** An autosave's name should say why it was kept: "Autosave: stick deleted", "Autosave: before Copy from <stick>", "Autosave: before Swap with <stick>", "Autosave: before Change vJoy Output (vJoy 1 → 2)", "Autosave: before Device Pack <pack>". [D-10-AUTOSAVE]
- **S18** An autosave should hold everything the stick has: its module file and pictures, and its bindings in every mode from every profile the action changes (the open profile and any ticked saved profiles).
- **S19** Only the newest N autosaves per stick are kept (N = 10 by default, set in Device Library Settings); older autosaves are removed when a new one is kept. The user's own saved setups (S12, S13) are never removed this way. [D-10-AUTOSAVE]
- **S20** If an autosave can't be written or read back, the action that needed it should not run, and say so (as Delete Device's copy does today, 03 S91). [carries 03 S91, 08 S86]
- **S21** Delete Device should always keep a "stick deleted" autosave (when that trigger is on) and no longer ask "Save a copy". [D-10-DELETE, changes 03 S90-S91, 08 S86]

### E. Copy to Another Stick

- **S22** Copy should take a saved setup (or a device's current settings) and put it on a stick plugged in now. The To list holds only connected sticks; a stick never plugged in here can be copied from, never to. [D-10-COPY]
- **S23** The dialog should show From (device › saved setup), To, What to copy (Setup, Button Map, Appearance, Bindings ticked; Calibration unticked; defaults from Settings), the profiles to put the bindings in (every profile that has bindings for the target or source, only the open profile ticked to start, Tick all), the modes, and a warning box listing what won't copy because the target lacks it (buttons, hats, axes and the bindings on them). [D-10-COPY, D-10-PROFILES]
- **S24** Copy should work like a Device Pack import onto the target (08 S64-S79): ticked modes replace the target's wires and actions in that mode, controls the target doesn't have are left out and listed, outputs keep their vJoy. The source saved setup and device are never changed. [D-10-COPY]
- **S25** Before Copy changes anything it should keep the target's autosave (S16), and Undo should put the target back. [D-10-AUTOSAVE]

### F. Swap with Another Stick

- **S26** Swap should exchange the ticked parts between two sticks plugged in now: each gets the other's settings. Bindings swap with every device reference inside actions and every script variable, as Swap Devices does today (04 S77-S78). [D-10-SWAP]
- **S27** The dialog should show both sticks, What trades places (as S23), the profiles (as S23), and warnings for both directions (what each stick lacks that the other has; those bindings stay where they were). [D-10-SWAP, D-10-PROFILES]
- **S28** It should keep an autosave of each stick first; Undo puts both back. [D-10-AUTOSAVE]
- **S29** It should refuse the Keyboard, Logical Device, OSC and Xbox, and refuse a stick swapped with itself. [carries 04 S79, 04 Q20]

### G. Change vJoy Output

- **S30** Change vJoy Output should keep a stick's bindings and change only which vJoy its Map to vJoy actions send to: one row per vJoy the stick sends to ("vJoy 1 (38 inputs) → [vJoy 2]", marked "changes" or "stays"), in the profiles ticked (as S23). A tick box "Also move <other stick> from vJoy 2 to vJoy 1 (swap them)" changes the stick that used the target vJoy the other way. [D-10-OUTPUT, D-10-PROFILES]
- **S31** Its warnings should list bindings that would send to an output the target vJoy's output module doesn't claim (they would send nothing), and macros and user scripts that name a vJoy number (not changed: "check it yourself"). [D-10-OUTPUT]
- **S32** It should keep an autosave of each stick that changes first; Undo puts them back. [D-10-AUTOSAVE]

### H. Profiles that aren't open

- **S33** Copy, Swap and Change vJoy Output should change the open profile in memory (saved with File › Save Profile, as Device Pack import does, 08 S74). A ticked saved profile that isn't open is changed on disk, after a backup copy of it is kept; each such change is a History entry. Undo puts the open profile back and puts back the backups of the others. [D-10-PROFILES]
- **S34** A saved profile that can't be read or written should be named and left unchanged; the others still change. [D-10-PROFILES]

### I. Shared devices

- **S35** File › Import Device Pack… should add the pack as a saved setup: under the device it was made from when that device is in the Library, otherwise under a new Shared device named after the pack, with the pack's Made by and Note as its description. [D-10-SHARE]

### J. Settings and tidying

- **S36** Settings › Device Library Settings… should hold: the autosave triggers (S16), the number of autosaves kept per stick (S19), what Copy and Swap tick by default (Setup, Button Map, Appearance, Bindings on; Calibration off), and the library folder with Move…. [D-10-SETTINGS]
- **S37** The library folder replaces the deleted devices folder setting: Options › Folders no longer lists deleted devices; an existing deleted devices folder setting becomes the library folder. [D-10-DELETED, changes 01 S124, 03 S98, 08 S87]
- **S38** Edit › Tidy Library… should list what it would remove (autosaves older than a chosen number of months; deleted devices with no saved setups), and remove it only after the user confirms. Nothing in the Library is removed without asking except by the autosave limit (S19). [D-10-TIDY]

## 9. Questions for the user

- **Q1** The design had a sixth autosave trigger, "a profile with bindings for the stick is deleted". The program can't delete profiles (that happens in Explorer), so it never sees it. **Decided (user, 2026-10-08): dropped** (D-10-Q1-DROP); the other autosaves and the user's own saved setups keep bindings copies.

## 10. Known gaps

All of it: the Device Library is not built. Today: Swap Devices (04 S77-S83)
swaps bindings only; Delete Device asks "Save a copy"; the deleted devices
folder has no viewer (03 gap note, 08 coverage note).

## 11. Size and test coverage

None yet. Tests will drive the real path: the library owner (list, autosave
limit, renamed autosave kept, damaged pack), Copy/Swap/Change on profiles open
and not open (with backups and Undo), Delete Device's autosave, the old
deleted devices folder read as deleted devices, and the window off-screen.

## 12. Review

Approved by the user, 2026-10-08 (wording as drafted; Q1 dropped).

| Decision | Summary |
|---|---|
| D-10-LIBRARY | Device Library: every device, current, unplugged, deleted and shared |
| D-10-NAMES | Rename and describe every device and saved setup |
| D-10-ROWS | Saved setups under a caret, newest first; autosaves marked |
| D-10-AUTOSAVE | Autosave triggers, reason in the name, newest 10 kept, renamed ones kept |
| D-10-WINDOW | Separate window with its own menus and settings |
| D-10-DELETED | Deleted devices included; the folder setting moves into the Library |
| D-10-DELETE | Delete Device always autosaves; no "Save a copy" question |
| D-10-COPY, D-10-SWAP, D-10-OUTPUT | The three actions, replacing Swap Devices |
| D-10-PROFILES | Profiles to change: a tick list, the open profile ticked |
| D-10-SEARCH | Search covers names, descriptions, contents, profiles, modes, vJoy |
| D-10-TIDY | Size in the status bar and Tidy Library… |
| D-10-SETTINGS, D-10-SAVE, D-10-SHARE, D-10-PROTO | Settings, saving, sharing, the prototype's layout |
| D-10-Q1-DROP | No autosave trigger for a deleted profile |
