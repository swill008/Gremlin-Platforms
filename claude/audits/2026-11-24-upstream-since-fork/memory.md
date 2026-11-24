# PYSIDE-WRAPPERS measured: kept wrappers of QML-made Python objects

Agent MEM, 2026-11-23, 18:10-18:25. This is the measurement designed in
`compare-measure.md` item 15. The probe is `tools/memory_probe.py`. No
program code was changed and nothing was committed.

## How it was run

- Each scenario ran in its own process: off-screen (`QT_QPA_PLATFORM=offscreen`,
  so no window was shown on any screen), with a temporary `USERPROFILE`,
  the stand-in hardware from `test/fake_hardware.py` (fake "pJoy Pro"
  stick), and the journey harness's fake vJoy (`test/journeys/_harness.py`).
  Real vJoy was never loaded.
- Each run was 2 warm-up repetitions, then 3 measured blocks of 25
  repetitions. A reading was taken after the warm-up (block 0) and after
  each block. Before every reading the probe ran `gc.collect()` twice and a
  pump that also runs `deleteLater()`.
- Each reading recorded: private bytes (`PrivateUsage`, as `memory_mb()` in
  `test/unit/device_mapping_editor_lifecycle_smoke.py`); the Python heap
  (`tracemalloc`, started after the warm-up); counts of the 81 QML-made
  Python types, split into valid and kept shells (`shiboken6.isValid`);
  everything reachable from the shells' `__dict__` (with `sys.getsizeof`,
  stopping at modules, classes, functions and live Qt objects); QObjects
  under the engine's root objects and all windows (by class); and the number
  of live `gremlin.profile.Profile` objects.
- The probe finds the 81 types by script: 117 classes are registered with
  `QmlElement`, and 81 of them are instantiated in QML files. This matches
  the plan's count.
- Two follow-up runs (10 repetitions per block) were made after the main
  run:
  - **C + E:** `TreeNode` (the mode tree) was added to the hold check, the
    QObject class names were recorded, and scenario E was added (profile
    load, then the pane on a Change Mode row).
  - **B + D with `--js-gc`:** the QML engine's JavaScript garbage collector
    (`engine.collectGarbage()`) ran before each reading. This checks whether
    the growth outside the Python heap is only JavaScript garbage that had
    not yet been collected.
- The raw JSON and logs are in the session scratchpad (`memrun`, `memrun2`,
  `memrun3`), not in the repo. Run `python tools/memory_probe.py` to
  reproduce them; the run takes about 5 min.

## Numbers per block (main run, 25 repetitions per block)

"Private" and "heap" are in MB. "Shells" is the number of kept wrappers
(invalid ones). "Reach" is the bytes reachable from all the shells'
`__dict__`. A jump from block 0 to block 1 is partly the cost of starting
`tracemalloc` itself; the verdicts use block 1 to block 3.

| Scenario (one repetition) | Block | Private | Heap | Shells | Reach | QObjects | Profiles |
|---|---|---|---|---|---|---|---|
| A. Profile load (p1, then p2; 1.4-1.6 s each) | 0 | 172.1 | 0.32 | 0 | 0 | 2102 | 1 |
| | 1 | 189.8 | 0.79 | 0 | 0 | 2102 | 1 |
| | 2 | 193.2 | 0.80 | 0 | 0 | 2102 | 1 |
| | 3 | 193.4 | 0.82 | 0 | 0 | 2102 | 1 |
| B. Page switch (Keyboard, Logical, OSC, Device Bindings, Home, Device Bindings; 1.3-1.4 s each) | 0 | 206.2 | 1.02 | 86 | 0.48 MB | 4927 | 1 |
| | 1 | 242.5 | 7.21 | 1161 | 6.41 MB | 4927 | 1 |
| | 2 | 271.0 | 13.39 | 2236 | 12.35 MB | 4927 | 1 |
| | 3 | 294.9 | 19.47 | 3311 | 18.28 MB | 4927 | 1 |
| C. Action pane on a Change Mode + Macro row, opened and closed (0.45 s each) | 0 | 193.4 | 1.10 | 8 | 11 KB | 4936 | 1 |
| | 1 | 198.0 | 1.24 | 108 | 142 KB | 4961 | 1 |
| | 2 | 200.9 | 1.41 | 208 | 274 KB | 4986 | 1 |
| | 3 | 202.9 | 1.61 | 308 | 405 KB | 5011 | 1 |
| D. Seven windows opened and closed (3.2 s each) | 0 | 188.8 | 0.42 | 174 | 0.40 MB | 2064 | 1 |
| | 1 | 207.7 | 2.58 | 1624 | 2.15 MB | 2064 | 1 |
| | 2 | 223.9 | 4.58 | 3074 | 3.91 MB | 2064 | 1 |
| | 3 | 240.8 | 6.57 | 4524 | 5.66 MB | 2064 | 1 |

The seven windows in scenario D are Options, Input Viewer, Manage Modes,
Device Information, Calibration, Live Log and Device Mapping Editor; all
seven opened and closed. In every scenario the valid object counts of the
81 types were flat from block 1 to block 3, and the window count was 1.

Follow-up runs (10 repetitions per block):

| Run | Block 1 to 2 private | Block 2 to 3 private | Shells per block | Other |
|---|---|---|---|---|
| C (repeat) | +3.5 MB | +0.8 MB | +40 | QObjects +10 per block: `InputIdentifier` +1 per pane open |
| E. Profile load + pane on a Change Mode row, twice per repetition (2.3 s each) | +3.0 MB | +3.2 MB | +90 | `TreeNode` held: +90 per block; QObjects +20 (`InputIdentifier`); Profiles stay 1 |
| B with JavaScript GC | +14.8 MB | +18.3 MB | +430 | same picture as without it |
| D with JavaScript GC | +6.2 MB | +6.4 MB | +580 | same picture as without it |

The JavaScript garbage collector did not change the growth. B is about
1.5-1.8 MB per round and D about 0.63 MB per repetition, the same as or
more than without it. The growth is therefore not JavaScript garbage that
was waiting to be collected.

## Verdicts by the plan's thresholds

### A. Profile load: harmless (levels off)

- Private bytes grew +3.4 MB from block 1 to 2, then +0.2 MB from block 2
  to 3. That is +3.6 MB in total, over the plan's 2 MB line, but it levels
  off instead of growing by the same amount each block. That is the
  pattern of a cache.
- The Python heap was flat (+0.03 MB).
- Profile loads made no kept shells (0 throughout).
- The live `Profile` count stayed at 1.
- QObject and valid counts were flat.
- Upstream's 9602a510 case ("objects aren't released on profile loading")
  does not happen with the pages left as they are. See E for the case where
  the pages are rebuilt.

### B. Page switch: real leak

- Private bytes grew linearly: +28.5 MB, then +23.9 MB per 25 rounds. That
  is about 1 MB per round of six page opens, far over the plan's 1 MB per
  25 repetitions.
- The Python heap grew +6.2 MB per block, and the shells account for almost
  all of it (reach +5.9 MB per block).
- 43 shells are kept per round:

  | Type | Per round | Each holds |
  |---|---|---|
  | `WindowPlacement` | 16 | about 230 B |
  | `EditLock` | 10 | about 260 B |
  | `HardwareLayoutModel` | 2 | **about 97 KB** (by far the biggest) |
  | `Device` | 2 | |
  | `DeviceLiveState` | 2 | about 6.7 KB |
  | `DeviceListModel` | 2 | |
  | `KeyboardLayoutModel`, `LogicalLayoutModel`, `OscLayoutModel`, `OscDeviceManagementModel`, `OscMonitorModel`, `InputListenerModel`, `FolderMemory`, `OscSettingsInfo`, `OscBulkCapture` | 1 each | about 1-3.5 KB for the layout models |

- What the shells keep alive (tracemalloc, block 1 to block 3):
  - `HardwareLayoutModel` keeps its row dicts: `gremlin/ui/hardware_layout.py:528`
    `_row()` is +5.9 MB, and `:193` `_inputs` is +1.0 MB. The shared row
    code in `gremlin/ui/control_layout.py:225, 412, 426-427, 814` and
    `gremlin/ui/binding_catalog.py:216, 222` adds about 0.4 MB each.
  - `HardwareLayoutModel`, `Device` and `DeviceLiveState` shells each hold
    a `dill.DeviceSummary`. These are new copies: each
    `gremlin.modules.hardware.device_info()` call builds a fresh one
    (`dill/__init__.py:262`), with its `AxisMap` list, so 150 copies pile up
    per block. Each is a copy of the stick's description, not the live
    device or a profile object. By the plan's rule ("any kept shell keeps a
    ... device object alive") this still counts as a hold.
- The live `Profile` count stayed at 1. QObject and valid counts were flat,
  so the C++ side of the page items is freed.
- About 18-22 MB per block of the private growth is outside the Python
  heap, and it is not JavaScript garbage (see the follow-up run). Its cause
  is **unverified**; it may be per-wrapper memory inside shiboken or Qt
  model internals that the shells keep. Clearing the shells' `__dict__`
  would recover the Python part (about 6 MB per block). Whether it also
  frees the rest can only be shown by trying it.
- At this rate, 10 MB is about 10 rounds, which is about 50-60 page changes.

### C. Action pane open and close: real leak, small

- Private bytes grew +2.9 MB, then +2.0 MB per 25 opens (about 80-120 KB
  per open). That is over the plan's 1 MB per 25. In the 10-repetition run
  the figures were +3.5 MB and +0.8 MB, so the growth is noisy.
- The QObject count was not flat: it grew by 1 per open.
- The shells themselves are small: 3 `ModeListModel` and 1
  `ModeHierarchyModel` per open, about 1.3 KB per shell (under the plan's
  2 KB line).
- The `ModeListModel` shells hold `TreeNode` mode objects through
  `_lookup` (`gremlin/ui/profile.py:819-838`). Here those were the current
  profile's mode tree, which is alive anyway.
- The growing QObject is **`InputIdentifier`**, a live object and not a
  shell: one more is left per pane open, under a long-lived parent. The
  likely source is `gremlin/ui/device.py:413`, where
  `InputIdentifier(parent=self)` is made on every call. That call path is
  **unverified**: the counts show the growth, but the caller was not
  traced.
- At this rate, 10 MB is about 100 pane opens.

### E. Profile load + action pane (C and A together): real leak (mode-tree hold)

- Each `ModeListModel` shell keeps the mode tree (`TreeNode`) of the
  profile that was open when the shell was made: +90 `TreeNode` per block
  of 10 repetitions (each repetition is 2 loads and 2 pane opens). So after
  a load, shells keep the old profile's modes alive.
- The `Profile` object itself is not held (the count stays at 1). The size
  is small: about 1.9 KB per `ModeListModel` shell.
- `OutputModuleDevices` shells also appear here, about 9 KB each.
- Private bytes grew about 3 MB per 10 repetitions, linearly.
- This is the plan's "indirect hold" case. It is proven for mode objects,
  but not for whole profiles.

### D. Windows opened and closed: real leak

- Private bytes grew linearly: +16.2 MB, then +16.9 MB per 25 repetitions.
  That is about 0.66 MB per round of seven windows, about 95 KB per window
  opened on average.
- The Python heap grew +2.0 MB per block, and the shells account for most
  of it (reach +1.75 MB per block).
- 58 shells are kept per round. The biggest holders:

  | Type | Each holds | Window | What it keeps |
  |---|---|---|---|
  | `ConfigSectionModel` | **about 27 KB** | Options | its `ConfigGroupModel` lists (`gremlin/ui/option.py:543-545, 641-644, 281-288`) |
  | `TraceView` | about 7.9 KB | Live Log | its trace lines |
  | `AxisCalibration` | about 6.5 KB | Calibration | `DeviceSummary` copies again |
  | `LiveLog`, `HardwareProfile`, `ViewerDeviceModel`, `ModulePairDeviceModel` | 1.5-3.2 KB | | |
  | `WindowPlacement`, `FolderMemory`, `DebugMode`, `HighlightSpeedModel` (8-10 per round) | about 230-260 B | | |

- The live `Profile` count stayed at 1. QObject and valid counts were flat.
- About 14 MB per block of the private growth is outside the Python heap,
  and it is not JavaScript garbage (cause **unverified**, as in B).
- At this rate, 10 MB is about 15 rounds, which is about 100 window opens.
- The probe did not measure each window on its own. The 2026-10-02 note
  ("Device Mapping Editor: 1-2 MB kept, flat over later opens") was not
  re-checked for that window by itself.

## What this means for the PYSIDE-WRAPPERS gap

- The program map's PYSIDE-WRAPPERS note ("harmless, upstream, nothing to
  fix here") does not hold.
- The `test/unit/test_leaks.py` comment says the kept shells hold nothing
  ("C++ gone, no holder in Python, signals disconnected"). That is wrong:
  the shells keep everything their `__dict__` holds.
- The memory grows with use: about 1 MB per page round, 95 KB per window
  opened, and 80-120 KB per action pane opened.
- Upstream's reading holds ("created but then not correctly deleted",
  PYSIDE-1407). It applies to the 81 types QML instantiates; profile loads
  alone are clean.
- This is now a spec matter for the user (program map page 01, gap
  PYSIDE-WRAPPERS). Nothing was changed.

## What to do next (for the user to choose; efforts not estimated here)

1. **Fix the biggest holders first, by size per repetition:**
   1. `HardwareLayoutModel`: 97 KB per Device Bindings open, plus
      `DeviceSummary` copies.
   2. `ConfigSectionModel`: 27 KB per Options open.
   3. `DeviceLiveState`, `Device` and `AxisCalibration`: 6-7 KB each, plus
      `DeviceSummary` copies.
   4. `TraceView`: 8 KB per Live Log open.
   5. `ModeListModel`: it holds the mode trees of old profiles, so it is
      the indirect-hold case. It is small, but it is the most used type.
   6. The `InputIdentifier` child left per pane open (`gremlin/ui/device.py:413`).
      This is a separate, ordinary parent-held growth, not a wrapper issue.
2. **Ways to fix the shells:**
   - a) **Upstream's way (02a280e8, follow-ups 9602a510, 66bb2477,
     9fb7147b):** QML stops writing `TypeName {}` for these types. It calls
     a singleton factory slot instead (`ModelFactory.modeListModel(parentItem)`
     in `gremlin/ui/model_factory.py`), which builds the object in Python
     with the QML item as its Qt parent. Qt's parent deletion then frees it,
     and no QML-owned Python shell is left. Upstream has 24 slots; we have
     81 types at 115 QML sites. The work could be staged: the holders
     above first, then the rest.
   - b) **A smaller fix:** a shared base class (or mix-in) that clears
     `__dict__` when the object's `destroyed` signal fires. That empties
     the shells and frees what they hold (the Python part, about 6 MB per
     block in B). Whether it also frees the growth outside the Python heap
     is unverified until it is tried.
   - Both would need a guard test that fails on a new QML-made type that
     isn't covered. See the "design for change" rule.
3. **Re-run this probe after any fix** (`python tools/memory_probe.py`).
   For the per-window question in D, run D with one window at a time; that
   needs a small option added to the probe.
4. **Update the stale records after the user's decision:**
   - the `test_leaks.py` comment and its `counts()` filter;
   - the program map page 01 PYSIDE-WRAPPERS gap.

## After stage 1

Agent S1-MEASURE, 2026-11-23, 18:55-19:02. Measured after the stage-1 QML
conversion (plan `claude/plans/memory-qml-factory.md`: 10 QML files, the 19
`FACTORY_ONLY` types, one `InputIdentifier` per input). No program code was
changed and nothing was committed.

### How it was run

- Same probe, same set-up as above: off-screen, temporary `USERPROFILE`,
  stand-in hardware, fake vJoy, 2 warm-up repetitions, then 3 blocks of 25.
- Three changes to `tools/memory_probe.py`:
  - **Factory types counted.** The probe found the QML-made types by
    searching for `TypeName {`; converted types no longer match, so it
    also reads `ModelFactory.create("TypeName", ...)`. The count is still 81.
    (A first run without this counted only 62 types and was thrown away.)
  - **`--no-qobjects`.** S1-PY found that Python's `findChildren` on a QML
    item keeps the children it returns alive. The probe's QObject count
    used it at every reading, so the main run skips that count (QObjects
    read -1). A second run of C and E (10 repetitions per block) kept the
    count on, to check `InputIdentifier`.
  - **D per window.** `D=<file>` runs D with that one window. `--per-window`
    splits D into one process per window, and `--jobs N` caps the processes.
    This run had D (all seven) and D for each of the seven windows, 4
    processes at a time.
- Readings from the baseline were taken with the `findChildren` walk on. If
  that walk kept objects alive, the baseline private bytes are a little
  high. The C and E runs with the walk on show the same picture as without
  it.
- Raw JSON and logs: session scratchpad `s1run` and `s1qobj` (not in the
  repo).

### Before and after, block 1 to block 3 (50 repetitions)

| Scenario | Private before | Private after | Heap before | Heap after | Shells per repetition before | after |
|---|---|---|---|---|---|---|
| A. Profile load | +3.6 MB (levels off) | +3.0 MB (+2.2, +0.8: levels off) | +0.03 MB | +0.01 MB | 0 | 0 |
| B. Page switch (one round) | +52.4 MB | +26.7 MB (+20.4, +6.2) | +12.3 MB | +1.35 MB | 43 | 33 |
| C. Action pane open and close | +4.9 MB | +3.6 MB (+1.4, +2.3) | +0.37 MB | +0.03 MB | 4 | **0** |
| D. Seven windows (one round) | +33.1 MB | +12.6 MB (+4.2, +8.3) | +4.0 MB | +1.25 MB | 58 | 49 |
| E. Load + pane, twice (10 per block) | +6.2 MB per 20 | +3.5 MB per 20 (+1.2, +2.4) | | +0.36 MB | 9 (`TreeNode` held) | 1 (`OutputModuleDevices`) |

Reach (bytes the shells' `__dict__` keep) per block: B 5.9 MB before, 0.50
MB after; D 1.75 MB before, 0.49 MB after; C 130 KB before, 0 after.
The live `Profile` count stayed 1 everywhere. The valid object counts were
flat. In the C and E runs with the QObject count on, QObjects were flat
(C 4934, E 4962 in every block); before, they grew by 1 per pane open.

### D, one window at a time (25 opens per block)

| Window | Private, block 1 to 3 | Shells per open | Reach per open | What is left |
|---|---|---|---|---|
| Options | +1.5 MB | 11 | 2.8 KB | `HighlightSpeedModel` 8, `LogLevelModel`, `DebugMode`, `WindowPlacement` (`ConfigSectionModel`, 27 KB, gone) |
| Input Viewer | +2.6 MB | 3 | 1.9 KB | `ModulePairDeviceModel`, `DebugMode`, `WindowPlacement` |
| Manage Modes | +1.0 MB | 2 | 0.5 KB | `DebugMode`, `WindowPlacement` (mode models gone) |
| Device Information | +1.4 MB | 3 | 2.2 KB | `DeviceListModel` (holds 2 `DeviceSummary`), `DebugMode`, `WindowPlacement` |
| Calibration | +0.8 MB | 2 | 0.5 KB | `DebugMode`, `WindowPlacement` (`AxisCalibration` gone) |
| Live Log | +2.2 MB | 4 | 1.0 KB | `LogLevelModel`, `FolderMemory`, `DebugMode`, `WindowPlacement` (`TraceView`, `LiveLog` gone) |
| Device Mapping Editor | +5.6 MB | 24 | 10.6 KB | `FolderMemory` 8, `DebugMode` 4, `WindowPlacement` 4, `DeviceMapOptions` 2, `HardwareProfile` 2, `ViewerDeviceModel`, `ModuleFileWatch`, `DeviceNames`, `DeviceMapSpaceKey` |

Each window alone grows 16-110 KB per open in private bytes, most of it
outside the Python heap. Single-window figures are small and noisy (0.8-2.6
MB per 50 opens); the Device Mapping Editor is the clear largest, about
110 KB per open. The 2026-10-02 note ("1-2 MB kept, flat over later
opens") does not hold for it: it grew +2.5 MB and +3.0 MB in the two
blocks.

### Verdicts

- **A. Profile load: harmless, as before.** It levels off and keeps no
  shells.
- **B. Page switch: much smaller, still a leak.** Heap growth is down by
  about 90% and the shells keep about 20 KB per round instead of about
  240 KB. `HardwareLayoutModel`, `Device`, `DeviceLiveState` and
  `DeviceListModel` (the Device Bindings holders, with their
  `DeviceSummary` copies) are gone. Private bytes still grow about 0.25-0.8
  MB per round (the two blocks differ: +20.4, +6.2), over the 1 MB per 25
  line. Left per round: `WindowPlacement` 16, `EditLock` 8 (was 10), and 1
  each of `KeyboardLayoutModel`, `LogicalLayoutModel`, `OscLayoutModel`
  (the biggest left, about 3.6 KB), `OscDeviceManagementModel`,
  `OscMonitorModel`, `InputListenerModel`, `FolderMemory`, `OscSettingsInfo`
  and `OscBulkCapture`. All are stage-2 types (groups B, D, F).
- **C. Action pane: shells and QObject growth fixed.** There are no shells.
  `InputIdentifier` no longer grows. The heap is flat. Private bytes still
  rise 1-2 MB per 25 opens (noisy: +1.4 and +2.3 in the main run, +1.2 and
  +0.7 per 10 in the QObject run), outside the Python heap. The cause is
  **unverified**.
- **E. Profile load + pane: the mode-tree hold is gone.** No `TreeNode` or
  `ModeListModel` is kept. The one shell left per repetition is
  `OutputModuleDevices` (about 9 KB, its `_choices` and `_modules`;
  `gremlin/ui/output_modules.py:120-121`), from `VJoySelector`, a stage-2
  type (group D). Private bytes grow about 1-2.5 MB per 10 repetitions.
- **D. Windows: much smaller, still a leak.** Heap growth is down by about
  70%, and the biggest holders (`ConfigSectionModel`, `TraceView`,
  `AxisCalibration`, `LiveLog`) are gone. Private bytes still grow about
  0.17-0.33 MB per round (+4.2, then +8.3 per 25), over the line. Left per round:
  `DebugMode` 10, `WindowPlacement` 10, `FolderMemory` 9,
  `HighlightSpeedModel` 8, `LogLevelModel` 2, `DeviceMapOptions` 2,
  `HardwareProfile` 2, and 1 each of `ViewerDeviceModel`,
  `ModulePairDeviceModel`, `ModuleFileWatch`, `DeviceListModel`,
  `DeviceNames` and `DeviceMapSpaceKey`. All are stage-2 types (groups A,
  C, E, F).

### What is left for stage 2

1. Most shells left per round are the small shared types: `WindowPlacement`
   (26 per B + D round), `DebugMode` (10), `FolderMemory` (10),
   `EditLock` (8), `HighlightSpeedModel` (8). They are 230-430 B each, but
   they are the most numerous (group F, plus group C for
   `HighlightSpeedModel` and `LogLevelModel`).
2. The biggest left per shell: `OscLayoutModel`, `LogicalLayoutModel` and
   `KeyboardLayoutModel` (3-3.6 KB, page switch); `OutputModuleDevices`
   (9 KB, Change Mode pane after a load); `ViewerDeviceModel`,
   `DeviceListModel`, `LogLevelModel` and `HardwareProfile` (1.5-2.1 KB).
   `DeviceListModel` in Device Information still holds `DeviceSummary`
   copies.
3. The Device Mapping Editor keeps 24 shells per open (about 10.6 KB), the
   most of any window.
4. In every scenario, private bytes grow faster than the Python heap. For
   example, in B the heap grows +0.7 MB per block but private bytes grow
   +6-20 MB. That part is outside Python, and its cause is still
   **unverified**. The stage-2 re-run (S2-MEASURE) shows whether it goes
   when no shells are left. If it does not, it is a separate question
   (Qt, shiboken or QML internals).

## After stage 2

Agent S2-MEASURE, 2026-11-23, 19:31-19:43. Measured after the stage-2 QML
conversion: all 81 QML-made Python types are now made only through
`ModelFactory.create(...)` (115 QML sites, no `TypeName {}` left), and the
Health and Search windows close properly. No program code and no probe code
was changed, and nothing was committed.

### How it was run

- Same probe and set-up as stage 1: off-screen, temporary `USERPROFILE`,
  stand-in hardware, fake vJoy, 2 warm-up repetitions, then 3 blocks of 25.
  The probe still finds 81 types, all by their `ModelFactory.create` call.
- Main run: A, B, C, E and D for each of the seven windows (one process per
  window), 4 processes at a time, with `--no-qobjects`.
- `--per-window` replaces D (all seven) instead of adding to it, so D for
  all seven windows ran on its own afterwards (25 per block, `--no-qobjects`).
- C and E with the QObject count on, 10 repetitions per block, as in stage 1.
- B with the JavaScript garbage collector (`--js-gc`) before each reading,
  to check whether B's remaining growth is uncollected JavaScript garbage.
- Note: E ran with 25 repetitions per block in the main run (stage 1: 10).
- Raw JSON and logs: session scratchpad `s2run`, `s2runD`, `s2qobj`,
  `s2jsgc` (not in the repo).

### Before and after, block 1 to block 3 (50 repetitions)

Private bytes are in MB, with the two block steps in brackets. "Shells" is
the number kept per repetition.

| Scenario | Private: baseline | stage 1 | stage 2 | Heap: baseline | stage 1 | stage 2 | Shells: baseline | stage 1 | stage 2 |
|---|---|---|---|---|---|---|---|---|---|
| A. Profile load | +3.6 | +3.0 | **+0.1** (+0.57, -0.47) | +0.03 | +0.01 | +0.02 | 0 | 0 | 0 |
| B. Page switch (one round) | +52.4 | +26.7 | +26.4 (+7.4, +19.0) | +12.3 | +1.35 | **+0.07** | 43 | 33 | **0** |
| B with JavaScript GC (stage 2: 25 per block) | +33.1 per 20 (10 per block) | | +15.3 per 50 (+6.2, +9.1) | | | +0.07 | | | 0 |
| C. Action pane open and close | +4.9 | +3.6 | +2.5 (+1.5, +1.0) | +0.37 | +0.03 | +0.03 | 4 | 0 | 0 |
| C, QObject run (10 per block) | | +1.9 per 20 | +2.7 per 20 (+1.1, +1.6) | | | +0.06 | | 0 | 0 |
| D. Seven windows (one round) | +33.1 | +12.6 | +9.9 (+1.3, +8.5) | +4.0 | +1.25 | **+0.04** | 58 | 49 | **0** |
| E. Load + pane, twice (25 per block) | | | **+1.5** (+1.41, +0.12) | | | +0.06 | | | 0 |
| E, QObject run (10 per block) | +6.2 per 20 | +3.5 per 20 | +7.5 per 20 (+6.3, +1.3) | | +0.36 | +0.09 | 9 | 1 | 0 |

- Reach (bytes the shells' `__dict__` keep): 0 in every scenario (baseline:
  B 5.9 MB and D 1.75 MB per block; stage 1: B 0.50 MB and D 0.49 MB).
- The live `Profile` count stayed at 1 everywhere, and no heavy object
  (`Profile`, `Device`, `DeviceSummary`, `TreeNode`, ...) was reached.
- The valid object counts of the 81 types were the same in every block
  (16 or 25, the long-lived ones). So the factory does not leave live
  objects behind in place of shells.
- With the QObject count on, QObjects were flat: C 4934 and E 4962 in
  every block, the same as stage 1.

### D, one window at a time (25 opens per block)

| Window | Private, stage 1 | Private, stage 2 (steps) | Shells per open, stage 1 | stage 2 |
|---|---|---|---|---|
| Options | +1.5 MB | +0.92 (+0.11, +0.81) | 11 | 0 |
| Input Viewer | +2.6 MB | +1.79 (+1.24, +0.55) | 3 | 0 |
| Manage Modes | +1.0 MB | +0.38 (+0.31, +0.07) | 2 | 0 |
| Device Information | +1.4 MB | +1.37 (+0.37, +1.00) | 3 | 0 |
| Calibration | +0.8 MB | +0.63 (+0.24, +0.39) | 2 | 0 |
| Live Log | +2.2 MB | +0.67 (+0.37, +0.30) | 4 | 0 |
| Device Mapping Editor | +5.6 MB | **+0.43 (+0.50, -0.07)** | 24 | 0 |

The Device Mapping Editor, the largest in stage 1 (about 110 KB per open),
now levels off. Every single window is at or under the 1 MB per 25 line in
each block except Input Viewer's first block (+1.24).

### Verdicts against the plan's thresholds

The plan's thresholds are no kept shells, and private bytes flat from block
1 to block 3 or levelling off (under about 1 MB per 25 repetitions).

- **No shells: met everywhere.** 0 shells of any of the 81 types in every
  scenario and every window, as expected. Nothing is held through a shell.
- **A. Profile load: flat.** +0.1 MB over 50 loads. Passes.
- **E. Profile load + pane: levels off.** +1.41 then +0.12 MB per 25 (main
  run); +6.3 then +1.3 per 10 in the QObject run. The mode-tree hold and the
  `OutputModuleDevices` shell are gone. Passes (levels off).
- **C. Action pane: borderline.** +1.5 then +1.0 MB per 25 opens (about
  40-60 KB per open), at the 1 MB line, outside the Python heap (+0.03 MB).
  The QObject count is flat. Noisy as before; not clearly levelling off.
- **D, single windows: pass.** Small, mostly under 1 MB per 25, and the
  Device Mapping Editor levels off.
- **D, seven windows: not shown flat.** +1.3 then +8.5 MB per 25 rounds.
  The heap grew only +0.04 MB, so the growth is outside Python. The second
  block's jump is not seen in any single-window run (their sum is about
  +3.8 per 25 in the larger block), so it may be noise or an interaction
  between windows; **unverified**.
- **B. Page switch: still grows (fails the private-bytes threshold).**
  +7.4 then +19.0 MB per 25 rounds (about 0.3-0.75 MB per round of six page
  opens), with no shells and a flat heap (+0.07 MB). With the JavaScript GC
  it was +6.2 then +9.1, so part of it may be uncollected JavaScript
  garbage, but it still grows by about 0.25-0.35 MB per round.

### What is left

1. **No type still leaves shells.** Stage 2's goal is met.
2. **Growth outside the Python heap remains in B (and probably D).** Now that
   no shells are left, this is not the PySide wrapper issue. The Python heap
   is flat, the QObject count is flat in C and E, and the valid counts are
   flat. The cause is **unverified**: likely candidates are QML or Qt
   internals per page load (component or type caches, the scene graph, glyph
   or image caches, the Qt heap not returning freed memory to Windows).
   Finding it would need native tools (for example a heap snapshot with
   Windows Performance Recorder or UMDH) or a QML-only repro of the page
   switch; that is a separate question for the user.
3. **Small Python-side growth found by `tracemalloc` (block 1 to 3, 50
   repetitions).** All are small, none are shells:
   - `gremlin/ui/hardware_layout.py:444-449, 491-492`: each
     `HardwareLayoutModel` adds a `_pending_relay` listener to the store;
     a relay removes itself only when the store next fires after its model
     is gone. In B about 37 KB per 50 rounds (+196 relay allocations at
     `:446`), and the `gc` object count grows about 10 per round. Bounded
     only by the next pending-store event.
   - `joystick_gremlin.py:1155`: the `engine.warnings` lambda appends every
     QML warning to `qml_errors` for the whole run (the list is only needed
     for start-up). In D about 18 KB per 50 rounds (about 3 warnings per
     round of seven windows). Which warnings these are was not checked.
   - `gremlin/action_analysis.py:26, 48`: `_feedback_cache` gets one new
     entry per action pane open (C: +49 per 50 opens, about 140 B each with
     the `uuid` at `gremlin/util.py:426`). Entries expire by time but are
     never removed. Why each open has a new key was not traced.
   - About 46 B per call kept at `gremlin/ui/model_factory.py:177`
     (`setObjectOwnership`), `gremlin/ui/debug_mode.py:122` (the same call)
     and `gremlin/ui/window_placement.py:317` (`setWindowStates`): 2-7 KB
     per 50 repetitions. The cause (shiboken's per-call caches) is
     **unverified**.
4. **Next steps (for the user to choose; efforts not estimated here):**
   - a) Record PYSIDE-WRAPPERS as fixed for shells (program map page 01) and
     update the `test_leaks.py` comment and `counts()` filter.
   - b) Fix the three small Python-side growths above (relay clean-up when
     the model is destroyed, drop the warnings lambda after start-up, prune
     the feedback cache).
   - c) A separate investigation of B's native growth (native heap tools or
     a QML-only repro).
