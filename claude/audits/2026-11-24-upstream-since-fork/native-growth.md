# Private bytes outside the Python heap (S2-NATIVE, 2026-11-23)

Agent S2-NATIVE, 19:19-19:34. The question (user approved a, 2026-11-23):
after memory-fix stage 1, private bytes grow much faster than the Python
heap. In memory.md ("After stage 1"), page switching shows the heap growing
about +0.7 MB per block while private bytes grow +6 to +20 MB. Where does
the rest go? No program code was changed and nothing was committed.

## How it was measured

- A probe script in the session scratchpad (`native\native_probe.py`) runs
  the scenarios from `tools/memory_probe.py` (its `_setup`) in the same
  set-up: its own process, off-screen, a temporary `USERPROFILE`, stand-in
  hardware and fake vJoy.
- At each reading it settles first (pump plus `gc.collect()`, twice). Then
  it records:
  - private bytes;
  - every Windows heap, walked with `HeapWalk`: bytes in use ("busy"), the
    number of blocks in use, free bytes inside committed heap memory, and
    blocks of 512 KB or more;
  - committed private memory outside the heaps (`VirtualQuery`). This is
    where the JavaScript engine's own memory and Python's arenas live;
  - Python's pymalloc arenas and used bytes (`sys._debugmallocstats`);
  - the count of gc objects.
- `tracemalloc` was off, so its own cost is not in the figures.
- The heap walk keeps the Python lock (`ctypes.PyDLL`), so no thread can
  deadlock on the heap lock.
- Each run is 2 warm-up repetitions, then blocks of 20 page-switch rounds
  (B) or 25 pane opens (C). Raw JSON and logs are in the session scratchpad
  under `native\out\` (not in the repo).
- Releases tested after each block, each followed by a reading:
  `engine.collectGarbage()` (JavaScript GC), `engine.trimComponentCache()`,
  `QPixmapCache.clear()` plus `QQuickWindow.releaseResources()`, and
  `HeapCompact` on every heap plus `_heapmin`. Each was also run alone, in
  its own process.
- Committed stage-1 build: run from a temporary `git worktree` of e479e6eb,
  removed afterwards.
- Isolation tests (`native\iso.py`): a bare QML engine with a Loader
  switching between two tiny files, 800 cycles, one QML pattern per
  process.

## Where B's growth goes (current working tree, no releases)

Over 8 blocks (160 rounds), `Bplain`:

| | Block 0 | Block 8 | Growth |
|---|---|---|---|
| Private bytes | 201.8 MB | 264.5 MB | +62.7 MB |
| Heap, busy | 100.1 MB | 120.0 MB | +19.9 MB (of which +9.1 MB is blocks of 512 KB or more) |
| Heap, blocks in use | 311,861 | 342,096 | +30,235 (about 3,300 per block) |
| Heap, free but committed | 18.5 MB | 44.8 MB | +26.3 MB |
| Outside the heaps | 65.1 MB | 69.8 MB | +4.7 MB |
| pymalloc arenas | 41 | 41 | 0 |
| Python used bytes | 39.91 MB | 40.19 MB | +0.28 MB |

All of the growth is in the Windows heap (`malloc` from Qt and C++) or the
JavaScript engine. Python's own memory is flat.

## Candidates, one by one

| # | Candidate | How measured | Numbers | Verdict |
|---|---|---|---|---|
| 1 | Qt's component and type cache (compiled QML units not in use) | `trimComponentCache()` after each block, alone (`trimOnly`) and in the chain (`Bint`); blocks in use before and after | Each trim frees about 5,100 blocks (0.85-0.9 MB). With a trim each block, blocks in use stay flat (314.3-314.5k at each block end, 309.2k after each trim). Without it they climb 3,300 per block with no end in sight. Single pages switched back and forth: Keyboard without trim +1,300 blocks per block (about 30 per page load); with trim, flat. | **Cause (verified)**: about 25-40 heap blocks per page load stay in the engine's cache of unused component data until trimmed. Nothing trims it today except the tray release. |
| 2 | JavaScript heap (QV4) | `collectGarbage()` alone (`jsgcOnly`); memory outside the heaps | Without JS GC, memory outside the heaps climbs late in a run (`curLong`: 66.4 MB to 75.4 MB over blocks 6-11). With JS GC each block it stays at 66.0-66.5 MB. The heap's free-but-committed memory levels off at about 40-42 MB instead of creeping. | **Cause (verified)**: garbage collection runs late. Dead JavaScript-owned objects pile up between collections, which raises the heap's high-water mark. Each collection frees only a few dozen heap blocks, but the steady growth drops (see the table below). |
| 3 | Windows heap fragmentation and high-water mark | Free-but-committed heap bytes; `HeapCompact` and `_heapmin` | Free bytes grow from 18 MB to 36-45 MB. `HeapCompact` and `_heapmin` give back about 0-1 MB. With releases each block, free bytes level off at about 34-42 MB. Without them they keep creeping (`curLong`: 38 MB to 45 MB, blocks 4-11). | **Part of it (verified)**. The NT heap keeps freed memory committed after a peak. This is the largest single share of private growth (about 40%), but most of it is the high-water mark from items 1 and 2 plus page-load peaks. It levels off once those are released. |
| 4 | Image and texture caches, scene graph | `QPixmapCache.clear()` plus `releaseResources()` on every `QQuickWindow` | Busy bytes -0.01 MB; private bytes 0 | **Not it.** |
| 5 | QObjects without Python wrappers not freed | Heap blocks in use (every C++ object is at least one) | With trim and JS GC, blocks in use are flat over 6 blocks (120 rounds). On the committed stage-1 build (e479e6eb) they grow 21,000-62,000 per block (`wtH`: 309,956 to 484,354 over 6 blocks; private 202.8 to 274.9 MB). | **Not in the current tree.** It was large on e479e6eb, so the stage-2 conversions in progress have already removed about 85% of the native block growth. |
| 6 | Python heap and arenas | `_debugmallocstats` | Arenas 41 throughout; +0.02-0.04 MB per block | **Not it.** |
| 7 | Fonts and glyphs, and other large buffers | Heap block-size histogram (`curH`, start against block 6) | Once per run, at a random block (block 3, 4, 5 or 7, seen in 6 of 9 long runs), the same set of about 10 big blocks appears again: one of 7,420,756 B, nine of 110-262 KB, and a separate 2 MiB block. That is about +9-14 MB in one step; after it, flat (`curLong` stays at 37.51 MB of big blocks from block 3 to 11). Two copies of the set already exist at start. | **A one-time step, not a leak.** Which object it is was **not verified**. The shape (one big buffer plus table-sized pieces, copied whole) fits a font engine or a glyph cache. It explains the uneven blocks in memory.md (+20.4 then +6.2). |
| 8 | Stage-2 shells still present | e479e6eb against the current tree, same probe | e479e6eb: +72 MB over 6 blocks, about 21k+ blocks per block. Current tree: +51.6 MB over 6 blocks, of which about 13 MB is the one-time step, and 3.3k blocks per block. | The stage-2 work so far already removes most of the native object growth. What is left is items 1-3. |

### Growth per block of 20 rounds with each release (B, steady state, one-time step left out)

| Run | Releases after each block | Private growth per block |
|---|---|---|
| `Bplain`, `curLong` | none | +3.4 to +4.3 MB |
| `trimOnly` | `trimComponentCache` | about +1.5 MB (blocks 2-4: +2.5, +1.4, +1.3; after the step, -1.0) |
| `jsgcOnly` | `collectGarbage` | about +1.0 MB (+0.6, +1.8, +0.8, +1.0) |
| `Bint` | JS GC, trim, pixmap and scene graph, heap compact | about +0.6 MB (229.2 to 231.1 MB over blocks 3-6) |

Action pane open and close (C, 25 opens per block): +0.6 MB per block
without releases, +0.2 MB with a trim each block.

Block times were unchanged with trims (25.0-26.1 s per 20 rounds in every
run). The probe's waits dominate those times, so a slower first page load
after a trim would not show here.

### Isolation tests (bare engine, 800 Loader cycles)

| Pattern in the loaded file | Heap blocks kept per cycle | Freed by JS GC | Freed by trim |
|---|---|---|---|
| Plain items | 3.0 | all | 0 |
| `Qt.createQmlObject(...)` (FloatSpinBox's validator) | 2.0 | all | 0 |
| JavaScript import, with and without `.pragma library` | 2.9 | all | 0 |
| Inline `Component` plus `createObject` | 8.1 | all | 0 |
| Python object from a factory slot (parented) | 7.0 | all | 0 |
| ModelFactory pattern (C++ ownership plus `setParent`) | 4.3 | all | 0 |
| `Connections` on a Python object | 2.0 | all | 0 |
| **Python type made by QML (`IsoModel {}`)** | **19.1** | 5,064 of 15,242 | 0 |

- None of these patterns makes trimmable entries. The source of item 1 in
  the real pages is still **not verified**: something in the pages that the
  tiny files lack.
- The last row confirms the PySide leak behind stage 1 on its own: a
  Python type made by QML keeps about 12.7 heap blocks per object even
  after JS GC. The factory pattern keeps none. This is the same finding as
  upstream 02a280e8.

## Causes found

1. **The QML engine's component cache is never trimmed while the window is
   shown.** Every page load leaves about 25-40 heap blocks of unused
   compiled component data. `trimComponentCache()` frees all of it and
   stops the block count growing. Today only `gremlin/ui/tray_memory.py`
   (`release`) calls it, when the main window hides to the tray. Which page
   content creates the new entries is not verified (see the isolation
   table).
2. **JavaScript garbage collection runs late.** Between collections, dead
   JavaScript-owned objects and the engine's own memory raise the
   high-water mark, and the Windows heap keeps that memory committed.
   `collectGarbage()` after the page change halves to quarters the growth.
3. **The Windows heap keeps freed memory committed** (fragmentation and
   high-water mark). Most of this follows from 1 and 2 and levels off once
   they are released. `HeapCompact` does not give it back.
4. **A one-time step** of about 9-14 MB: one copy of a set of large buffers,
   once per run. It is not a leak. Its owner is not verified.

The stage-2 shells were a large native cost on e479e6eb (21k+ heap blocks
per 20 rounds). The work in progress has already removed most of it.

## Fix that would address it

At one shared owner, call `engine.collectGarbage()`, then `gc.collect()`,
then `engine.trimComponentCache()` a short while after a page unloads or a
window closes. Debounce it, for example 1-2 s after the last change, so a
quick string of switches costs one clean-up.

- The pieces are already in `tray_memory.release()`; split them out as
  `release_unused(engine)` and call that from the page Loaders'
  unload/`activeChanged` and from window close. In this probe that takes B
  from about +4 MB to about +0.6 MB per 20 rounds.
- Leave out the scene-graph release and `HeapCompact`: they gave nothing
  back.
- Cost: after a trim, the next load of an unloaded page compiles its types
  again from the on-disk `.qmlc` cache. The probe could not see this cost;
  measure first-page-load time live before choosing the delay.
- Optional follow-up to find the owner of cause 1: bisect the Keyboard
  page's content in the isolation harness (about 30 trimmable blocks per
  load to find).
- This changes no behaviour the user sees, but it adds a timed clean-up.
  The lead decides whether it needs a spec line (01 App shell, tray release
  section) before it is built.

How upstream handles it (git, `upstream/develop`):

- 9fb7147b ("Reduce memory usage spikes and gc"): `gc.collect()` at the
  end of a profile load (`backend.py`), and a new `ObjectLoader.qml`.
  `ObjectLoader` is an Item that calls `component.createObject` and
  `item.destroy()` itself, used instead of `Loader` "without some of the
  memory issues arising from it".
- 02a280e8 and 9602a510: the ModelFactory move, which our stage 1 follows.
- Upstream never calls `collectGarbage` or `trimComponentCache` (git grep
  on `upstream/develop`: no hits). So upstream does not address cause 1,
  and treats cause 2 only on the Python side.

**Effort:** no timing data yet for this kind of work. Rough guesses:

- the clean-up helper and its calls: 15-30 min for one agent, plus a probe
  re-run (about 3 min of runs) and quick tests;
- the optional owner hunt for cause 1: 20-40 min.
