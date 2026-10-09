# Device Library

**Approved by the user 2026-10-08. S1-S50 built (2026-10-08).** Written from
the design discussion of 2026-10-08 (decisions D-10-* in
`claude/decisions.md`) and the off-screen Qt prototype in
`.agent-logs/handson/DL/` (renders `dl_main.png`, `dl_menu.png`,
`dl_settings.png`, `dl_copy.png`, `dl_swap.png`, `dl_output.png`; not in
git). It replaces Swap Devices (04 S77-S83) and takes over the deleted
devices folder, which goes (03 S62, S90-S91, S98; 08 S86-S88; D-10-NO-DELETED-FOLDER).

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
| `<library folder>\` (default `<data folder>\device library`) | The Device Library. Its own setting, `device-library-folder`; the deleted devices folder and its setting are removed. |
| `<library folder>\library.json` | The list: devices (name, description, device id when known, kind: set up here / deleted / from a pack) and their saved setups (name, description, date, origin, whether it is the user's, what it holds, which profiles and modes its bindings came from, vJoy outputs). |
| `<library folder>\<device>\<saved setup>.zip` | Each saved setup is a Device Pack (08 S49-S55 format), so it can be exported and shared as it is. |

Code: the library owner `gremlin/device_library.py` (the one writer of
`library.json` and the packs, built on `device_pack.assemble` and the pack
import), a QML model in `gremlin/ui/`, `qml/WindowDeviceLibrary.qml` and its
dialogs. Copy, Swap and Change vJoy Output change profiles only through the
profile owner, and module files only through `modules/store.py`.

## 3. What it owns

- The library list and its saved setups (files above).
- The autosave rules and limit (Device Library Settings).
- Device names and descriptions for devices with no module file here (deleted,
  and those that came from a pack). For devices set up here the name is the module file's friendly
  name (S6).

## 4. Entry points (planned)

| Where | What |
|---|---|
| Home: **Device Library…** button; Tools › Device Setup › **Device Library…** | Opens the window. |
| Card menu: **Copy Setup to Another Stick…**, **Swap with Another Stick…**, **Change vJoy Output…** | Open the window on that card's device and the matching dialog. |
| Delete Device | Keeps the "stick deleted" autosave (S21). |
| Device Pack import onto a stick | Keeps the "before a Device Pack" autosave (S21); a pack imported in the Library is added as a saved setup (S35). |

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

- **S1** The Device Library should be a separate window, like the Button Map, with its own menu bar: **File** (Import Device Pack…, Export Saved Setup…, Open Library Folder, Close), **Edit** (Undo, Rename… (F2), Delete…, Tidy Library…; the description is edited in place), **Device** (Save to Device Library…, Copy to Another Stick…, Swap with Another Stick…, Change vJoy Output…), **View** (Connected, Not Connected, Deleted, Autosaves, Expand All, Collapse All, Search…), **Settings** (Device Library Settings…), **Help** (Device Library Guide, F1; S42). Menus follow 01 S66 (only what can be used now). [user decision: D-10-WINDOW]
- **S2** It should open from a Device Library… button on Home and from Tools › Device Setup › Device Library…; the card menu items (03 S88) open it on that card's device. [D-10-WINDOW]
- **S3** The left side should hold filter chips (Connected, Not connected, Deleted, Autosaves; several at once, each an outline with a tick when on), a search box and the device list; the right side the details of what is selected; a divider between them can be dragged. [D-10-WINDOW, D-10-PROTO]
- **S4** The status bar should show the number of devices and saved setups, the autosave limit, the library's size on disk (e.g. "Library: 48 MB") and the library folder. [D-10-TIDY]
- **S5** Search should match device names and descriptions, saved setup names and descriptions, what a saved setup holds (Setup, Button Map, Appearance, Calibration, Bindings), profile names, mode names, vJoy numbers and autosave reasons; Ctrl+F goes to the box, Esc clears it. [D-10-SEARCH]

### B. Devices

- **S6** There should be one row per device: plugged in now (**Connected**), set up here but unplugged (**Not connected**), or deleted (**Deleted**). A device that came only from someone else's pack is **Not connected**: it can be copied from, never to. Each row shows its name, description, state and number of saved setups. [D-10-LIBRARY] [changed 2026-10-08 to follow D-10-STREAMLINE] The program's built-in inputs (Keyboard, OSC) are listed after the devices under their own heading **Built-in inputs**; for them only Save to Device Library…, Restore to This Stick… (here: Restore), Export…, Rename… and Edit Description are offered, never Remove from Library, Clear Setup, Copy, Swap or Change vJoy Output, and they have no Connected / Not connected badge. The heading sits under a thin divider after the last device, in small muted capitals, not clickable or foldable; the state filters (Connected, Not connected, Deleted) don't hide them, only a search does, and the heading hides when a search leaves none of them. [2026-10-09: D-10-BUILTIN-SECTION, replaces D-10-NO-BUILTINS]
- **S7** Every device and every saved setup can be renamed and given a description. A device set up here has one name: renaming it in the Library renames it on its Home card and the other way round. [D-10-NAMES]
- **S8** Selecting a device should show its name, description, state, what inputs it has, and when it was last seen.
- **S9** Deleted devices are the ones deleted since the Library exists (Delete Device, Delete File); files in an old deleted devices folder are not read, moved or removed. [D-10-DELETED] [changed 2026-10-08 to follow D-10-NO-DELETED-FOLDER]

### C. Saved setups

- **S10** A device row should open with a caret to show its saved setups as rows under it, newest first. Saved setups the user made (or renamed or described, S13) show a save mark; autosaves show an autosave mark. [D-10-ROWS]
- **S11** A saved setup holds any of: Setup (claims, friendly names), Button Map and photo, Appearance, Calibration, and Bindings (from one profile, the modes saved, the vJoy outputs they send to). Selecting one should show its name (renamable), its description (editable in place), when and why it was kept, exactly what it holds, a Button Map photo preview, a short **Activity** list (saved, description edited, copied to which stick and when; named Activity so it isn't confused with Tools › History) [changed 2026-10-08 to follow D-10-ACTIVITY], and the actions Copy, Swap, Change vJoy Output, Export and Delete (Delete in red). [D-10-PROTO]
- **S12** Device › Save to Device Library… should keep a saved setup of the selected device (the user's own): its module file now, and its bindings from the profiles the user ticks (one saved setup per profile, named after the profile by default). [D-10-SAVE]
- **S13** An autosave the user renames or describes becomes the user's own and is never removed by the autosave limit. [D-10-AUTOSAVE]
- **S14** Export Saved Setup… should write the saved setup as a Device Pack anywhere the user picks (08 S57 rules). [D-10-SHARE]
- **S15** Deleting always asks first and names exactly what goes. On a saved setup, **Delete…** removes it. On a device the items depend on its state (S47): a **not connected** device (unplugged, deleted or from a pack) has **Remove from Library…**, which removes the device and all its saved setups, and, when it still has a module file here, removes that too as Home's Delete Device does (03 K, autosave first, refused while the profile runs); a **connected** device has **Clear Setup…** (the same as Delete Device: an autosave first, then its module file and bindings go; the stick stays plugged in with no setup) and **Delete Saved Setups…** (forgets its saved setups; the stick keeps its settings). [D-10-TIDY] [changed 2026-10-08 to follow D-10-REMOVE]

### D. Autosaves

- **S16** The program should keep an autosave of a stick, without asking, when: the stick is deleted (Delete Device); its module file is deleted (Module Setup's Delete File: setup only, "Autosave: module file deleted"); before Copy replaces its settings; before Swap; before Change vJoy Output; before a Device Pack is put on it. They are always on (they are the way back, S41). [D-10-AUTOSAVE] [changed 2026-10-08 to follow D-10-STREAMLINE]
- **S17** An autosave's name should say why it was kept: "Autosave: stick deleted", "Autosave: before Copy from <stick>", "Autosave: before Swap with <stick>", "Autosave: before Change vJoy Output (vJoy 1 → 2)", "Autosave: before Device Pack <pack>", "Autosave: before Restore of <saved setup>" (S48) (<pack> is the pack's file name without .zip; user, 2026-10-08). [D-10-AUTOSAVE]
- **S18** An autosave should hold everything the stick has: its module file and pictures, and its bindings in every mode from every profile the action changes (the open profile and any ticked saved profiles).
- **S19** Only the newest N autosaves per stick are kept (N = 10 by default, set in Device Library Settings); older autosaves are removed when a new one is kept. The user's own saved setups (S12, S13) are never removed this way. [D-10-AUTOSAVE]
- **S20** If an autosave can't be written or read back, the action that needed it should not run, and say so (as Delete Device's copy does today, 03 S91). [carries 03 S91, 08 S86]
- **S20a** A stick whose module file is damaged can still be autosaved: the autosave keeps the damaged file exactly as it is, with the stick's bindings, and shows it as holding "Setup (damaged file, kept as is)". So Delete Device and Delete File always work for it. Copy and Swap never put a damaged file on another stick (only its bindings can be copied from such a setup). [D-10-DAMAGED-KEPT]
- **S21** Delete Device should always keep a "stick deleted" autosave (when that trigger is on) and no longer ask "Save a copy". [D-10-DELETE, changes 03 S90-S91, 08 S86]

### E. Copy to Another Stick

- **S22** Copy should take a saved setup (or a device's current settings) and put it on a stick plugged in now. The To list holds only connected sticks; a stick never plugged in here can be copied from, never to. [D-10-COPY]
- **S23** The dialog should show From (device › saved setup), To, What to copy (Setup, Button Map, Appearance, Bindings ticked; Calibration unticked; defaults from Settings), the profiles to put the bindings in (every profile that has bindings for the target or source, only the open profile ticked to start, Tick all), the modes, and a warning box listing what won't copy because the target lacks it (buttons, hats, axes and the bindings on them). [D-10-COPY, D-10-PROFILES]
- **S24** Copy should work like a Device Pack import onto the target (08 S64-S79): ticked modes replace the target's wires and actions in that mode, controls the target doesn't have are left out and listed, outputs keep their vJoy. The source saved setup and device are never changed. [D-10-COPY]
- **S25** Before Copy changes anything it should keep the target's autosave (S16), and Undo puts the target back from it (S41). [D-10-AUTOSAVE] [changed 2026-10-08 to follow D-10-STREAMLINE]

### F. Swap with Another Stick

- **S26** Swap should exchange the ticked parts between two sticks plugged in now: each gets the other's settings. Bindings swap with every device reference inside actions and every script variable, as Swap Devices does today (04 S77-S78). [D-10-SWAP]
- **S27** The dialog should show both sticks, What trades places (as S23), the profiles (as S23), and warnings for both directions (what each stick lacks that the other has; those bindings stay where they were). The warnings also list actions elsewhere that refer to a control of one stick the other lacks (e.g. a Condition checking Left stick Axis 3 when Right stick has no Axis 3): the reference still moves with the swap, and is listed, not changed. [D-10-SWAP, D-10-PROFILES] [changed 2026-10-08 to follow D-10-SWAP-REFS]
- **S28** It should keep an autosave of each stick first; Undo puts both back from them (S41). [D-10-AUTOSAVE] [changed 2026-10-08 to follow D-10-STREAMLINE]
- **S29** It should refuse the Keyboard, Logical Device, OSC and Xbox, and refuse a stick swapped with itself. [carries 04 S79, 04 Q20]

### G. Change vJoy Output

- **S30** Change vJoy Output should keep a stick's bindings and change only which vJoy its Map to vJoy actions send to: one row per vJoy the stick sends to ("vJoy 1 (38 inputs) → [vJoy 2]", marked "changes" or "stays"), in the profiles ticked (as S23). A tick box "Also move <other stick> from vJoy 2 to vJoy 1 (swap them)" changes the stick that used the target vJoy the other way. [D-10-OUTPUT, D-10-PROFILES]
- **S31** Its warnings should list bindings that would send to an output the target vJoy's output module doesn't claim (they would send nothing), and macros and user scripts that name a vJoy number (not changed: "check it yourself"). [D-10-OUTPUT]
- **S32** It should keep an autosave of each stick that changes first; Undo puts them back from them (S41). [D-10-AUTOSAVE] [changed 2026-10-08 to follow D-10-STREAMLINE]

### H. Profiles that aren't open

- **S33** Copy, Swap and Change vJoy Output should change the open profile in memory (saved with File › Save Profile, as Device Pack import does, 08 S74). A ticked saved profile that isn't open is changed and saved on disk; each such save is a History entry (the whole file can be restored from History). There is no separate backup copy: the autosave holds the stick's bindings from every profile changed, and Undo (S41) puts them back. A failure partway through one profile leaves that file as it was. [D-10-PROFILES] [changed 2026-10-08 to follow D-10-STREAMLINE]
- **S34** A saved profile that can't be read or written should be named and left unchanged; the others still change. [D-10-PROFILES]

### I. Packs from other people

- **S35** File › Import Device Pack… should add the pack as a saved setup: under the device it was made from when that device is in the Library, otherwise under a new Not connected device named after the pack. The saved setup says where it came from ("From <Made by>'s pack") and takes the pack's Note as its description. [D-10-SHARE] [changed 2026-10-08 to follow D-10-STREAMLINE]

### J. Settings and tidying

- **S36** Settings › Device Library Settings… should hold: the number of autosaves kept per stick (S19), what Copy and Swap tick by default (Setup, Button Map, Appearance, Bindings on; Calibration off), and the library folder with Move…. [D-10-SETTINGS]
- **S37** The library folder has its own setting (default `<data folder>\device library`, chosen in Device Library Settings). The deleted devices folder and its setting are removed: Options › Folders no longer lists it, and nothing is carried over from it. [D-10-DELETED, changes 01 S124, 03 S98, 08 S87] [changed 2026-10-08 to follow D-10-NO-DELETED-FOLDER]
- **S38** Edit › Tidy Library… should list what it would remove (autosaves older than a chosen number of months; deleted devices with no saved setups), and remove it only after the user confirms. Nothing in the Library is removed without asking except by the autosave limit (S19). [D-10-TIDY]

### K. Undo and shortcuts

- **S39** Dropping a Device Pack (.zip) on the window should import it as File › Import Device Pack… does (S35). [D-10-STREAMLINE]
- **S40** Double-clicking a saved setup should open Copy to Another Stick with it as From. [D-10-STREAMLINE]
- **S41** Edit › Undo should put the last Copy, Swap or Change vJoy Output back by copying the autosaves it kept onto their sticks (every part they hold, into the profiles they came from). Because it uses the autosaves, it still works after the window closes or the program restarts, until another change replaces it. Undo is itself a change and keeps its own autosave first. The Edit menu item names the change: "Undo <change>" (e.g. "Undo Copy DCS F-16 to Right stick"), and right after an Undo it reads "Redo <change>". [D-10-STREAMLINE] [D-10-REDO-LABEL]

### L. Guide

- **S42** Help › Device Library Guide (and F1 in the window) should open the User Guide window showing only the Device Library's own topics, as the Button Map Guide does for the Button Map (07): what the Library is, devices and saved setups, autosaves, Copy, Swap, Change vJoy Output, Undo and Redo, profiles that aren't open, search and filters, packs (import, export, sharing), settings and Tidy, Delete Device and Delete File, renamed and twin sticks, and common questions. The program's User Guide keeps its Device Library topic and points to the guide. [D-10-GUIDE]

### M. Right-click menu and selection

- **S43** Right-clicking a row should first select it (highlighted, details shown, as a left-click does), then open its menu; the keyboard Menu key and Shift+F10 open the same menu on the selected row. Rows show a hover highlight and a pressed flash; a row that is being changed shows a small busy mark. [D-10-CONTEXT]
- **S44** A device's menu should hold, as they apply: Copy to Another Stick… (from its current settings), Swap with Another Stick… (connected), Change vJoy Output…, Save to Device Library…, Export Current Setup… (a Device Pack of its current settings), Rename… (F2), Edit Description, Open Module Setup…, Open Button Map, Show on Home, Expand / Collapse, and the delete items of S15. [D-10-CONTEXT]
- **S45** A saved setup's menu should hold: Copy to Another Stick…, Restore to This Stick… (S48), Export…, Rename… (F2), Edit Description, Keep This Autosave (S49, autosaves only), Delete…. [D-10-CONTEXT]
- **S46** The menu on empty space in the list should hold: Import Device Pack…, Expand All, Collapse All, Device Library Settings…. [D-10-CONTEXT]
- **S47** Menus show only what can be used now (01 S66); delete items are red and always ask first, naming what goes (e.g. "Remove T.16000M and its 4 saved setups from the Library?"). [D-10-CONTEXT, D-10-REMOVE] A device's menu title names its state ("Left throttle · Connected", "· Not connected", "· Deleted"), and each delete item has a tooltip (the program's usual hover tooltip, not text in the menu) saying what it does: Clear Setup… "Its settings go; the stick stays plugged in", Delete Saved Setups… "Only the saved setups go; its settings stay", Remove from Library… "Gone from the Library, with its saved setups". Remove from Library's question says Tools › History can put it back (D-10-IN-HISTORY). [D-10-DELETE-CLARITY] [D-10-MENU-TIPS] If Delete Device (run first for a device with a module file) fails, Remove stops and shows its reason; it never stops silently. [2026-10-09: D-10-REMOVE-ERROR]
- **S48** Restore to This Stick… should put a saved setup back on its own stick (which must be plugged in) as Copy does (S22-S25, autosave first, Undo), without choosing a target. [D-10-RESTORE]
- **S49** Keep This Autosave should make an autosave the user's own in one step (as renaming or describing it does, S13), so the autosave limit never removes it. [D-10-KEEP]
- **S50** Ctrl-click and Shift-click should select several saved setups (or several devices); Delete… / Remove from Library… then act on all of them after one question that lists them. Copy, Swap, Change, Restore, Rename and Export act on one row only. When a plugged-in stick is among several selected devices, the menu shows Remove from Library… greyed out (it can't be clicked) with the tooltip "Remove from Library works only on devices that aren't plugged in", instead of an empty menu. [D-10-MULTI] [D-10-MULTI-NOTE] [D-10-MENU-TIPS]
- **S51** Every change to the Library's own files is a Tools › History entry, like a module-file save: its list (names, descriptions, records) and its saved setups (a new one, a delete, Delete Saved Setups…, Remove from Library…, an autosave pruned past the limit). One action is one entry, named for what happened ("Removed HID Remapper ACHB from the Device Library", "Deleted saved setup X"); Restore puts back the files and the list as they were before it. Delete and Remove questions say "Tools › History can put it back." [user decision 2026-10-09: D-10-IN-HISTORY]
- **S52** Remove from Library… removes the device entirely: its module file and folder (pictures, Button Map photo, recovery copies), its saved setups and autosaves, its Library record and last-seen date, every file choice that points at its file (stale old ids too, 03 S94), its friendly name, its Home card settings (size, place, hidden, compact) and its calibration; its bindings leave the open profile (kept only if that profile is saved). Other saved profiles and HidHide are not touched. It is ONE Tools › History entry ("Removed X from the Device Library"; several at once: "Removed N devices from the Device Library") whose Restore puts every piece back. Clear Setup… is likewise one entry, "Cleared the setup of X" (its autosave and the module-file delete together). [2026-10-09: D-10-ONE-ENTRY-TITLES] A device still plugged in is not removed (it gets Clear Setup…, and Windows keeps listing it as a plain card on Home). [user decision 2026-10-09: D-10-REMOVE-ALL]
- **S53** Undo and Redo are separate items, each naming the change ("Undo Remove HID Remapper ACHB", "Redo Copy to Another Stick"): in Edit (Ctrl+Z, Ctrl+Y) and as small Undo / Redo buttons beside the right-click menu's title, as other right-click menus show them. They work on every Library action (each is one History entry, S51): Undo restores the newest one's "before", Redo its "after". Several steps: Undo walks back through this session's Library actions newest first, Redo forward; a new action clears Redo. Older changes stay in Tools › History. Replaces S41's single last-change Undo and D-10-REDO-LABEL. [user decision 2026-10-09: D-10-UNDO-REDO]
- **S54** After Remove, Delete or Clear Setup the message line ends with an **Undo** link that does the same as Edit › Undo. [D-10-UNDO-REDO]
- **S55** The Delete key on a selected row runs Delete… (a saved setup) or Remove from Library… (a device not plugged in), asking first as always; nothing for a built-in input. [D-10-UNDO-REDO]
- **S56** A row's right-click menu has **Show in History**: Tools › History filtered to that device (08 S32-S33). [D-10-UNDO-REDO]

## 9. Questions for the user

- **Q1** The design had a sixth autosave trigger, "a profile with bindings for the stick is deleted". The program can't delete profiles (that happens in Explorer), so it never sees it. **Decided (user, 2026-10-08): dropped** (D-10-Q1-DROP); the other autosaves and the user's own saved setups keep bindings copies.

## 10. Known gaps

All of it: the Device Library is not built. Today: Swap Devices (04 S77-S83)
swaps bindings only; Delete Device asks "Save a copy"; Delete Device and
Delete File write to the deleted devices folder, which has no viewer (03 gap
note, 08 coverage note).

## 11. Size and test coverage

None yet. Tests will drive the real path: the library owner (list, autosave
limit, renamed autosave kept, damaged pack), Copy/Swap/Change on profiles open
and not open (with backups and Undo), Delete Device's and Delete File's
autosaves, and the window off-screen.

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
| D-10-REMOVE | Remove from Library (not connected), Clear Setup and Delete Saved Setups (connected) |
| D-10-CONTEXT | Right-click menus for devices, saved setups and empty space; selection and feedback |
| D-10-RESTORE | Restore to This Stick |
| D-10-KEEP | Keep This Autosave |
| D-10-MULTI | Select several rows to delete together |
| D-10-MULTI-NOTE | Grey line when Remove can't apply to several selected devices |
| D-10-ACTIVITY | The saved setup's short list is called Activity |
| D-10-DELETE-CLARITY | State in the menu title, a grey line under each delete item, Remove's question says nothing is kept |
| D-10-MENU-TIPS | What a menu item does is a hover tooltip, never text in the menu; several devices with one plugged in: Remove greyed out with a tooltip |
| D-10-GUIDE | Device Library Guide in the window's Help menu (F1) |
| D-10-REDO-LABEL | After an Undo the Edit item reads "Redo <change>" |
| D-10-DAMAGED-KEPT | A damaged module file is autosaved as it is, so delete always works |
| D-10-SWAP-REFS | Swap warns about references to controls the other stick lacks |
| D-10-STREAMLINE | Undo puts the autosave back; autosaves always on; no profile backups (History covers whole files); Shared folded into Not connected; no Edit Description; drag-drop import and double-click to Copy |
| D-10-NO-DELETED-FOLDER | The deleted devices folder and its setting go; Delete File autosaves into the Library; nothing carried over (beta) |
