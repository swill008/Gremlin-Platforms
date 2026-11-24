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
