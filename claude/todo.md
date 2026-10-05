# To do

Work that is known and parked. Each item names its tracker ref (UI issues
tracker) so the details stay in one place.

## Next up (added 2026-10-03)

- [x] **Hidden Cards in the Home menu, no window.** (done 2026-10-03) Remove the Hidden Cards
  window (`qml/DialogHiddenDevices.qml`) and View → Hidden Cards…
  (`qml/main_commands.js` `view.hidden`). In the Home right-click menu
  (`qml/StatusPage.qml`, next to Unhide All Cards), make **Hidden Cards** a
  submenu that slides out and lists each hidden card by name; clicking one
  unhides it. Nothing hidden: the submenu shows "No hidden cards" (disabled).
  Unhide All Cards stays. Update help (`qml/help_topics.js`: Home topics and
  the "Not on Home" troubleshooting line) and keep the glossary words (Hide
  Card / Hidden Cards).

## Button Map (planned 2026-10-04)

- [ ] **BM41 – A bigger page for the Button Map.** The page (32000 x 18000
  page units, `worldPageW/H` in `qml/VkbRigEditor.qml`; `pageW/pageH` saved
  by `gremlin/ui/hardware_profile.py`) grows so there is more room around
  the photo; the photo frame (inner page 24000 x 13500, `innerPad*`) keeps
  its size, centred. Every position is a fraction of the page (`fx`, `fy`,
  `rig_coords.js`), so all of them change meaning. Backward compatibility
  is not a concern (not released). To do:
  - New page size (16:9 kept) and paddings; `photoWell` follows.
  - Zoom-in limit from 8x to about 10x (the page and photo look ~23%
    smaller at the same zoom).
  - Rulers 0-100 over the new page; grid sizes keep their page units.
  - Convert the built-in maps and templates in the repo (`qml/maps`), redo
    the golden images and layout tests.
  - Exports: the print area and Scale unaffected; a whole-page export just
    has more margin.
  - Open questions: (1) 30% per side (about 70% more area, recommended) or
    30% more area (about 14% per side)? (2) The user's own maps: the
    program converts maps with the old page size as they load
    (recommended), the user re-places them, or a one-time conversion of
    their files (only with their go-ahead, on a backup).

## Program-wide history (planned 2026-10-05)

- [x] **G-HISTORY – History across the whole program.** (built 2026-10-05: 4597e486, 20155486, 780f16b8; Undo where it's missing is still to do) A shared history
  in its own files (per area: input modules, output modules, action
  editor, Button Map) that the program reads and writes, so earlier
  versions can be seen and restored, also after a restart. To be fleshed
  out with the user first: notes and open questions in
  `claude/history-notes.md`.
- [x] **G-LIBLEAK – Unused actions written to the profile.** (fixed 2026-10-05: b4539968) Some edit
  paths drop an action's link without removing the action, and saving
  writes every action, so the file grows (the user's profile: 1,172
  actions, 408 used). Under discussion: fix each leak, and skip unused
  actions when writing the file (kept in memory so Undo still works).

## OSC (parked 2026-10-02: leave OSC alone for now)

- [ ] **B15 – Default ports clash and disagree.** The program listens on 8000
  when nothing is set (`gremlin/osc.py` `DEFAULT_PORT`), Options shows 8001
  (`gremlin/ui/osc_option.py` `OscInputHostModel.port_default`), and output
  also defaults to 8000 (`DEFAULT_OUTPUT_PORT`). Suggested: input 8000,
  output 9000 (the usual OSC convention), one constant used everywhere.
- [ ] **B16 – OSC Add has controls that do nothing.** "Change" is saved as
  Axis; "message vs data" and "Trigger on message" with its delay are never
  passed on (`qml/OscAddDialog.qml`, `qml/OscDevice.qml` only sends the
  address and Button/Axis). The backend has no per-input settings for these;
  auto-release and its delay exist only as global options. Choose: build
  per-input support, or hide the controls until it exists.
- [ ] **B17 – OSC import promises change and encoder types.** Import turns
  C and E suffixes into plain axes (`gremlin/ui/osc_device_model.py`
  `_parse_import_line`), while `qml/OscImportDialog.qml` says otherwise.
  Goes with B16: real types, or fix the text.
