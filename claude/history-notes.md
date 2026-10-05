# Program-wide history (notes and design, 2026-10-05)

Status: built 2026-10-05 with the recommended decisions (the user's go-ahead):
store 4597e486, recording 20155486, window and Restore 780f16b8. Undo added where an editor had none (Module Setup, Calibration,
Configuration page). Tracker refs: G-HISTORY (the system), G-LIBLEAK (leaks), and the
bugs in "Found while gathering".

## Why

The user wants a history across the whole program: earlier versions of
actions, modules, Button Maps and settings can be seen and restored, also
after a restart. It lives in its own files, not as leftovers in the
profile (the profile's unused actions are leaks; see G-LIBLEAK). An input
action editor was developed once but not kept up; the current editors are
the ones to build on (to confirm).

## Where data lives today (the three stores)

| Store | File | When it is written | One place every write goes through |
|---|---|---|---|
| Profile: inputs, actions, modes, Logical Device, OSC rows, Profile Settings, vJoy initial values, scripts | `profiles\<name>.xml` | Only on Save Profile (and Delete Device, which saves at once). Edits stay in memory until then. | `Profile.to_xml` (`gremlin/profile.py:671`). Before = `_saved_snapshot` (the last load/save text), after = the new text. |
| Module files: claims, friendly names, calibration, Button Map (nodes, photo, ui), Appearance (`view`, `catalog`) | `modules\<slug>.json` plus pictures in `modules\<slug>\` and `modules\library\` | At once, by each editor's Save (Module Setup, Calibration, Button Map, Appearance, Auto Mapper claims, Device Pack, import) | `module_file.write_text` (`gremlin/modules/module_file.py:64`) for 8 writers; 3 paths bypass it (`_replace_file` for import, import undo and Device Pack; `restorePhoto`; deletes). |
| Program settings: Options, HidHide choices, OSC connection, folders, plus window/UI memory | `configuration.json` | About 1 s after a change (debounced) | `Configuration.save_now` (`gremlin/config.py:173`) |

Not data: Button Map recovery copies (`modules\recovery`), photo stash
(`modules\cache`), templates (`modules\templates`, own files), logs.

Undo today is separate per editor and in memory only: Logical Device (50
steps), Button Map editor (snapshots, `undo-steps` option 20-500), one
Undo Last Import. The Configuration action editor, Module Setup,
Calibration and the output modules have none.

## Found while gathering (fix before the history)

1. **Device Pack import empties the profile's action list (confirmed).**
   `Library.from_xml` (profile.py:469-475) keeps only the actions in the
   node it just read. Device Pack import calls it on the open profile
   (device_pack.py:961), so every other action leaves the list; the next
   Save Profile writes inputs that point at actions no longer in the
   file, and those actions are gone on the next load. Probe: 37 actions,
   import one, 1 left.
2. **Button Map Save drops calibration (confirmed in code).**
   `HardwareProfile.save` keeps only claim, direction, boundGuidLocal,
   boundName, view and catalog from the existing file
   (hardware_profile.py:2263). The user's module files have no
   calibration today, so nothing was lost yet.
3. **Profile save is not atomic** (`codecs.open(..., "w")`,
   profile.py:683): a crash mid-save can leave a broken profile.
   Module files and settings already use temp + replace.
4. **Photo restore on Cancel writes the module file raw**
   (`restorePhoto`, hardware_profile.py:2501): not atomic, no damage check.
5. **Probable: Button Map "unsaved" after Ctrl+S while still editing**
   (`saveEdit` never resets `editBase`, DialogJoystickButtonMap.qml:415),
   so autosave keeps writing recovery copies. To verify.
6. **Probable: Rename Mode leaves Change Mode actions pointing at the old
   name** (`rename_mode`, profile.py:1223). To verify.

## Leaks (G-LIBLEAK, full list)

Unused actions stay in the library and are saved: Configuration page
Delete (`binding_catalog.removeSequence`), the live editor's Remove
(`deleteActionSequnce`), Keyboard Delete, OSC Delete / Clear All, Delete
Mode (drops every input in it), Auto Mapper Overwrite, Chain Remove
Sequence, Hat Buttons 8 to 4, Logical Device Delete (kept for its Undo),
Device Pack import skips, and drafts while an editor pane is open (a Save
Profile then writes them). Also: `remove_unused` checks other actions but
not other inputs, and an action can be shared by inputs (Merge Axis
reuses one by default; Reference "use existing"; Dual Axis Deadzone), so
it can remove an action another input still uses. Every OK in the pane
editors copies the action under new ids, so comparing versions must use
content, not ids.

Fix: close each leak where it happens; at save write only actions some
input uses (walking every container: children, positive/negative,
true/false, single/double, short/long, lower/upper, first/second, chain
steps, hat directions), keeping the rest in memory for Undo; and make
the clean-up check inputs too.

## Design (proposed)

**Code layout**
- `gremlin/history.py`: the store (entry format, append, read, caps,
  restore payloads); no Qt beyond `gremlin.threads`; unit-testable.
- `gremlin/ui/history_model.py`: QML models (`Gremlin.UI`).
- `qml/DialogHistory.qml`: the window (Tools > History).
- `util.history_dir()` next to `modules_dir()` (follows a moved data
  folder), created by `ensure_data_folders()`.

**Writer**: producers call `history.record(...)` on the main thread; it
only queues. One thread via `threads.start("History", ..., stop=...)`
waits with bounded `get(timeout=...)`, appends one JSON line per entry
(append-only, safe with two running copies), drains its queue on stop,
and is flushed at quit next to `deferred_write.flush_all()`. Times from
`clock.now()`. Its own writes are traced (`trace("SAVE", "History", ...)`).

**Recording (three hooks, one per store)**
- Profile: in `Profile.to_xml`, compare `_saved_snapshot` with the new
  text; write one entry per changed input (device, input, mode; before
  and after action trees by content) and per changed section (modes,
  Logical Device, OSC, Profile Settings, scripts).
- Module files: in `module_file.write_text` (with the 3 bypasses routed
  through it and a matching `remove` for deletes); entry = file, device,
  what changed (claims, names, calibration, Button Map, Appearance),
  before and after. Pictures are kept once by content hash in
  `history\files\` so Restore can bring them back.
- Settings: in `Configuration.save_now`, changed keys only, user-facing
  ones only (Options, HidHide, OSC, folders); window and UI memory left out.

**Files**: `history\profile.jsonl`, `history\modules.jsonl`,
`history\button-map.jsonl`, `history\settings.jsonl`, `history\files\`.

**Restore**: goes through the normal save paths, so it is itself a
history entry. Profile items go back into the open profile as an unsaved
change (the user saves, as everywhere else). Module files and settings
are saved at once, as their editors do.

**Window**: one list for all areas (newest first) with filters (area,
device, profile, date) and search; select an entry to see before and
after; Restore. Each editor gets a History button that opens it filtered
to that input or device.

## Decisions for the user (recommendation first)

1. When an entry is made: at each save (Save Profile, a module Save, a
   settings change), not per edit. Profile edits therefore show at Save
   Profile.
2. Profile entries: per changed input and section, plus the last 20
   whole-profile snapshots (compressed) so a whole profile can be put back.
3. Settings: only user-facing ones (Options, HidHide, OSC, folders).
4. Button Map view state (zoom, pan, guides, grid): left out; print area
   and print settings: left out too (they change constantly).
5. Pictures: kept by content hash so Restore brings them back.
6. Limits: 90 days or 20 MB per file, whichever comes first, in Options.
7. Folder: in the data folder (`history\`), moving with it.
8. Order of work: bugs 1-4, then the leaks, then the history core and
   hooks, then the window, then Undo where it is missing.
9. Old input action editor: not revived; the history covers the current
   editors.
10. Glossary: add "History" and "Restore" before they appear on screen.
