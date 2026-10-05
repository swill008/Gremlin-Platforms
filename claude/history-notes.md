# Program-wide history (notes, planned 2026-10-05)

Status: to be fleshed out with the user before any code. Tracker ref: G-HISTORY.

## Why

The user wants a history across the whole program: earlier versions of
actions, modules and maps can be seen and restored, also after a restart.
It needs its own place, not leftovers in the profile. (The profile holds
about 764 unused actions in its file today; those are leaks, see below,
not a history. The library is meant to drop unused actions:
`Library.remove_unused` in `gremlin/profile.py` is called by most edit
paths.) An input action editor was developed once but not kept up; the
current pane editor is the one to build on (to confirm).

## What exists today

Every Undo is separate, in memory only, and lost on closing:

- Logical Device: Undo/Redo, 50 steps (`gremlin/ui/logical_layout.py` `_apply`).
- Button Map editor: its own Undo/Redo (`qml/VkbRigEditor.qml` `undo()`).
- Module file import: one Undo Last Import (`gremlin/ui/hardware_profile.py`).
- Configuration action editor, Module Setup, Output modules: none.

## Shape the user asked for

- A shared history that the program reads and writes, in its own files.
- Separate files per area are fine: input modules, output modules, action
  editor, Button Map.
- Applied across the entire program.

## Open questions (recommendation first)

1. What is recorded: every saved change (OK, Delete, Save Module, Button
   Map save), not every keystroke. Each entry keeps the before and after.
2. Files: `%USERPROFILE%\Gremlin Platforms\history\` with one file per
   area (`actions.jsonl`, `input-modules.jsonl`, `output-modules.jsonl`,
   `button-map.jsonl`) plus a small shared index for a timeline.
3. An entry names: time, area, profile, device, input and mode, what
   changed, before and after.
4. Keeping: a size cap per file (e.g. 5 MB) or an age limit (e.g. 90 days),
   whichever comes first; set in Options.
5. Where it shows: Tools > History (all areas, filters, search), and a
   History button in each editor for just that input or device. Restore
   puts the old version back as a normal change (itself in the history).
6. Undo/Redo stays as the quick in-session step and is added where it is
   missing; the history is the lasting record behind it.
7. The old input action editor: revive it, or build on the current pane
   editor (recommended)?
8. One shared reader/writer for every area, writing on a background thread
   with bounded waits (`gremlin.threads`, program thread rules).

## Related

- Profile leaks (unused actions written to the file): tracker G-LIBLEAK.
  Fixing them does not depend on the history, and the history must not
  rely on the profile keeping old actions.
