# D-07-BG-COMPOSITE: contract (BGPIC-PLAN, 2026-10-11)

The device's photo becomes one derived file: a picture of the whole visible
background plane. Everything below is the shared contract the build agents
work to. Line numbers are from the tree at 21:45 today.

## 1. The file

- Name and place: `<device folder>/pictures/device-photo.png`.
  New constant `store.DEVICE_PHOTO = "device-photo.png"`; its reference is
  `store.picture_ref(DEVICE_PHOTO)` = `"pictures/device-photo.png"`.
  The name is reserved: `put_picture` / `import_photo` / Add Picture never
  write a user picture under it (rename on clash, as for any other clash).
- Format: PNG with transparency (no page colour behind it), longest side at
  most 1024 px (`store.DEVICE_PHOTO_SIDE = 1024`), the other side in the
  composite's own proportion. A smaller composite is not enlarged: longest
  side = min(1024, the pixels the most detailed visible background picture
  would give the area at 100 %) and at least 64 px.
- What it shows: every visible background node (pictures, shapes, lines,
  text), each with its crop, Look, opacity, rotation (`rot`), skew, flip,
  in plane order; hidden layers (`n.hidden`, and a hidden layer group) left
  out, as in an export. No foreground, no chips, no print-area or screen-only
  view settings (the Background row's eye/opacity are screen-only, 07 S120).
- Area: the bounding box, in page fractions, of the visible background
  nodes as drawn (after rotation and skew), clamped to the page
  (0..1 x 0..1). Computed in the renderer from the hidden editor's own
  geometry (`nodeBox`/`drawGeom` turned by `rot` and the skew matrix), not in
  Python, so lines, paths and text boxes use the same maths as the screen.
- Staleness key: stored inside the PNG as a text chunk
  (`QImage.setText("GremlinBackgroundKey", key)`, read back with
  `QImageReader(path).text("GremlinBackgroundKey")`, header only).
  `key = sha1(RENDER_VERSION | json.dumps(visible background nodes, sort_keys,
  screen-only keys removed: srcUrl, lookUrl, selected, _*) | for each picture
  ref those nodes name: its file size in bytes)[:20]`.
  `RENDER_VERSION = 1` (bump it when the renderer's look changes, so every
  file is made again). File size, not modification time: a picture copied by
  Export / Import keeps its size, so an imported photo stays current and is
  not made again.
- Written without a History step: the file is derived, so the writer is
  `module_file_io.write_bytes(dest, data)` directly (atomic), never
  `put_picture_at` (whose `_before_picture_change` would add a History entry
  each time). History still keeps it as a picture the map names (below).

## 2. Store (gremlin/modules/store.py), owner A-STORE

```python
DEVICE_PHOTO = "device-photo.png"
DEVICE_PHOTO_SIDE = 1024
DEVICE_PHOTO_KEY = "GremlinBackgroundKey"
RENDER_VERSION = 1

def visible_background(doc: object) -> list[dict]
    """The background nodes a composite draws: plane "background", not
    hidden (node or its layer group), in order."""

def background_key(doc: object, folder: Path | None) -> str
    """"" when visible_background(doc) is empty; else the key of section 1."""

def device_photo_path(folder: Path) -> Path      # folder / PICTURES / DEVICE_PHOTO

def device_photo_key(folder: Path) -> str
    """The key in the folder's device-photo.png, "" when missing/unreadable."""

def device_photo_current(folder: Path, doc: object | None = None) -> bool
    """The file is there and its key equals background_key(doc or the
    folder's module.json, folder). False with no visible background."""

def write_device_photo(folder: Path, png: bytes) -> None
    """Atomic write, no History step; registry.trace("SAVE", "Module files",
    "write_device_photo", path, "written"). Raises OSError."""

def remove_device_photo(folder: Path) -> None   # no background left: file goes

def shown_photo_ref(doc: object, exists: Callable[[str], bool]) -> str
    """What every place that shows "the device's photo" uses (07 S127 as
    changed): picture_ref(DEVICE_PHOTO) when visible_background(doc) is not
    empty and exists(that ref); else device_photo_ref(doc) (the bottom
    background picture: the fallback while the file is being made or when
    it is missing)."""
```

- `device_photo_ref(doc)` keeps its meaning and name: the bottom background
  picture. It stays for everything that edits that layer (Module Setup's
  Import Image `set_device_photo`, hardware_profile 1419 / 2363,
  module_model 463 / 1751, planes_once, device_pack `_zip_pictures`' "Device
  photo" row and the "Photo" pack part). No caller outside "shown" changes.
- `named_refs(doc)` adds `picture_ref(DEVICE_PHOTO)` when the doc has a
  visible background. Effect: the unused-picture clean-up (07 S106) keeps
  the file; History keeps it with each save (08 S8); every `.gmap`
  (`device_zip._zip_pictures`, which already skips a named file that is
  missing, device_zip.py:119-121) and so every Device Library saved setup
  carries it. Nothing else in the pack code changes for carrying.

## 3. Who renders: the hidden renderer in the main window (QML route)

Chosen: the existing `RigRenderer` (the hidden copy of the map that already
draws every print, export and preview) hosted once in `qml/Main.qml`,
driven by a Python object's signal. Why this and not a Python
QPainter/QQuickRenderControl route:

- The background holds shapes, lines and text drawn by the editor's own
  JavaScript Canvas code (`RigDrawItem` + `rig_draw.js paintDraw`), plus the
  skew matrix, crop clip, stretch fill and flip; only the real editor
  component draws them identically. A Python painter would be a second
  renderer to keep in step (fails "fix at the shared owner").
- `RigRenderer` already works without the editor's window: it loads its own
  `VkbRigFace` off-screen; only `snapshot(e)` needs a live editor, and a
  snapshot is a plain object we can build from the module file.
- `QQuickRenderControl` would need its own engine, context and GL/RHI
  set-up, much more code, and still the same QML.
- Works off-screen (`QT_QPA_PLATFORM=offscreen`): the print tests already
  grab through `RigRenderer` this way (test_planes_print.py).

### Python side: gremlin/ui/device_photo.py (new), owner A-MAKER

```python
class DevicePhotoMaker(QtCore.QObject):
    # QML host draws one job: token, the module file's nodes (JSON text),
    # the picture folder's URL (to resolve "pictures/..." refs to srcUrl),
    # the longest side wanted, the PNG path to save to (a temp file under
    # store.folder()/"cache"/"device-photo").
    renderWanted = QtCore.Signal(str, str, str, int, str)
    #                         token, nodesJson, picturesUrl, side, outPath

    def request(self, device_name: str, guid: str) -> None
        """Queue one device (de-duplicated by folder); does nothing when
        its file is current; removes the file when it has no visible
        background."""

    def check_all(self) -> None
        """Every device folder (store.device_dirs()): request() the stale
        ones. Connected to signal.moduleFilesChanged (one burst after any
        module-file write: editor Save, Import as new / onto existing,
        Restore Import, History restore, Device Library restore, Module
        Setup Save with Import Image, the Logical Device card's Add /
        Change / Remove Image), and run once 2 s after start."""

    @QtCore.Slot(str, bool)
    def rendered(self, token: str, ok: bool) -> None
        """The host saved the PNG at outPath (ok) or gave up. Reads it,
        checks the module file did not change meanwhile (key computed at
        request time == key now; else request again), sets the text key,
        write_device_photo(), removes the temp file, then
        store.notify_module_files() so cards / Module Setup / HidHide /
        Library rows re-read their photo (the next check_all finds it
        current: no loop). One job at a time; the next is sent after."""

    hostReady: bool property (QML host sets maker.hostReady = true on
    Component.onCompleted). Without a host (unit tests, no window) requests
    wait and nothing is written; the fallback below shows the bottom
    picture.

def want(device_name: str, guid: str) -> None
    """Module-level: the running maker's request(), no-op without one.
    profilePhotoUrl calls it when the file is missing or stale (safety net
    for any write path that does not send the module-files notice)."""
```

- Created by `joystick_gremlin.py` next to the other context objects and
  exposed as context property `devicePhotoMaker` (lead-owned file; one line
  each; given to the lead).
- Job timeout: 10 s per job (the renderer gives up on a picture that never
  loads at 200 ticks of 40 ms = 8 s); a timed-out job is dropped and logged,
  retried once at the next check_all.
- Threads: main thread only (Qt objects); the key needs only `stat()` and a
  JSON read, no picture decode. No new thread (program-thread-rules).

### QML side, owner A-RENDER

`qml/RigRenderer.qml` (not in the lead's uncommitted batch) gains:

```js
// A snapshot without an editor, for the device's photo: the page at
// 1600 x 900 (the page's 16:9), no chips, the area set after load.
function snapshotOf(nodesJson) -> { nodes, props: {printArea: null},
                                     dest: null, chipRows: [], w: 1600,
                                     h: 900, area: {x:0,y:0,w:1600,h:900} }
// job fields added:
//   onlyBg: true      -> jobNodes keeps only visible background nodes
//   transparent: true -> the page Rectangle behind is not drawn
//   fitBackground: true -> in _applyEditor, props.printArea becomes the
//       union of the background nodes' turned boxes (page fractions,
//       clamped 0..1) before printAreaRect() is read; pixels are then
//       {w,h} = longest side job.side in that area's proportion.
function backgroundArea(e) -> {fx, fy, fw, fh}   // used by fitBackground
```

`qml/DevicePhotoHost.qml` (new, A-RENDER): an Item holding one
`RigRenderer`; `Connections { target: devicePhotoMaker; function
onRenderWanted(token, nodesJson, picturesUrl, side, outPath) }` resolves each
node's `src` to `srcUrl` (picturesUrl + name) and `lookUrl` through its own
`HardwareProfile { id: _hw }.adjustedPhotoUrl(srcUrl, look)` (the same Look
copy the editor uses), enqueues `{ snap: snapshotOf(...), onlyBg: true,
transparent: true, fitBackground: true, side: side, light: false,
includeBg: true, preview: "", onPicture: function(r) {
devicePhotoMaker.rendered(token, !!r && r.saveToFile(outPath)) } }`.
`ItemGrabResult.saveToFile(fileName)` is Qt Quick API (returns bool);
the PNG text key is added afterwards in Python.

`qml/Main.qml` (lead): `DevicePhotoHost {}` once, beside the other hidden
items. `qml/qmldir` / resources: add `DevicePhotoHost.qml` if the project
lists files there (lead checks).

NOT VERIFIED (build agent proves with the end-to-end test): that
`VkbRigFace` with `host: null` draws background Canvas shapes/text without
the editor window open (it does for Print & Export, which also runs with
host null in RigRenderer, so expected to work); that the face draws no page
fill of its own (if it does, `transparent` must also switch that off).

## 4. Fallback when the file is missing

`shown_photo_ref` returns the bottom background picture's ref (today's
behaviour) whenever the composite file is absent; `profilePhotoUrl` then
calls `device_photo.want(...)`. When the file exists but is stale (the
render not done yet) it is still shown until replaced (a second or so); the
maker replaces it and the notice refreshes the pages. No visible background
at all: the maker removes the file and every page shows "no photo" (07 S11,
no stock photo, unchanged).

## 5. Each place that shows the device's photo (switch to shown_photo_ref)

| Place | Code | Change (owner) |
|---|---|---|
| Home cards, Logical Device card, Module Setup, HidHide window, Xbox page | `HardwareProfile.profilePhotoUrl` hardware_profile.py:2420-2440 (cards via module_model `_photo` 2186; HidHide `_module_photo` hidhide.py:498-509) | `found = store.find_picture(base, store.shown_photo_ref(doc, lambda r: store.find_picture(base, r) is not None))`; when it fell back or the key is stale: `device_photo.want(name, guid)` (A-PYCALLERS). module_model.py and hidhide.py need no change (they go through profilePhotoUrl). |
| Device Library "Device map photo" | device_library.py:1819 `photo()` | `ref = store.shown_photo_ref(doc, lambda r: r in zf.namelist())` (A-PYCALLERS). device_library.py:1393 (has a map?) unchanged. device_library_model.py / WindowDeviceLibrary.qml unchanged. |
| Export Device preview | device_pack.py:831 `photo_ref` | `store.shown_photo_ref(doc, lambda r: resolve(r) is not None)` (A-PYCALLERS) |
| Import Device preview | device_pack.py:1136 `photo_arc` | `Path(store.shown_photo_ref(doc, lambda r: Path(r).name in urls)).name` (A-PYCALLERS) |
| Pack part lists (`"Photo"` line 465, `_zip_pictures` "Device photo" row 1207+) | unchanged: they name the bottom background picture as a part to take or keep (08 S75 ticks), not the shown photo. `_zip_pictures` must not list device-photo.png as a map picture: skip `DEVICE_PHOTO` there (A-PYCALLERS). |

## 6. When it is (re)made

Every module-file write sends `signal.moduleFilesChanged` (store
`_saved` -> `notify_module_files`, one burst, main thread), so one hook,
`DevicePhotoMaker.check_all`, covers: the editor's Save (07), Import Device
as new / onto existing and Restore Import (08 S111-S113), a History restore
(08), a Device Library restore (10), Module Setup's Save with Import Image
(03 S52), the Logical Device card's Add / Change / Remove Image (03 S88).
It re-makes only folders whose key changed, so a foreground-only Save (chips
moved) makes nothing. Plus the start-up check and the profilePhotoUrl safety
net. NOT VERIFIED: that History restore and Device Library restore write
through `store` (and so send the notice); the carry-through test agent
proves each path, and the safety net covers any that don't.

## 7. Packs, Library, History

- Export / Device Library save: the file rides along as a picture the map
  names (section 2), at `pictures/device-photo.png` in the zip.
- Import as new / onto existing / Restore Import: the file lands with the
  pictures; its key matches (same nodes, same picture sizes), so it is not
  made again. Import onto an existing device that keeps this device's
  background (08 S75 "map tick" off) keeps this device's file; Python import
  code must not take the pack's device-photo.png in that case: it is a
  background picture of the pack (A-PYCALLERS checks the import picture
  selection treats DEVICE_PHOTO with the background part). Any mismatch is
  caught by the key and made again.
- History: kept with each save as a named picture; after a restore the key
  decides (usually current; else made again).
- Old packs without the file: fallback shows the bottom picture, the maker
  makes the file after import (no compatibility code needed).

## 8. The new 100 % rule (07 S83 as changed), owner A-RENDER + lead's dialog

Code: `RigRenderer.exportFactor(e, scalePct)` (RigRenderer.qml:78-100) is
the one owner; Print & Export's pixels binding and `DialogDeviceMappingEditor
.exportFactor()` (1990-1994) call it.

Maths, per visible background picture `n` (`isBackground(n)`,
`shape === "image"`, not hidden), with `nat = {w, h}` its own pixels, `g =
e.drawGeom(n)` its box in editor pixels, crop `c` (keepW = 1 - c.l - c.r,
keepH = 1 - c.t - c.b, each at least 0.02). The picture is stretched to its
box (07 S140), so its detail is

    dx = nat.w * keepW / g.w      (image pixels per editor pixel, across)
    dy = nat.h * keepH / g.h      (down)
    d(n) = max(dx, dy)

Rotation and skew don't change d (they turn the box, not its size).

    factor = scale * max over n of d(n)          (some picture has nat > 0)
    factor = scale * 1920 / spaceRect().w        (no visible background picture)

where scale = clamp(scalePct, 10, 800) / 100. Then the existing 16384 px
cap (07) applies unchanged.

Picture sizes: the renderer can't wait for each picture to load in a
binding, so it asks `HardwareProfile.pictureSize(url) -> {w, h}` (new slot,
A-PYCALLERS, a header read with `QImageReader(path).size()`, {0,0} when
unreadable; cached by path + mtime). `RigRenderer` gets `property var
sizeOf: null` (a function url -> {w,h}); DialogDeviceMappingEditor sets
`RigRenderer { id: _renderer; sizeOf: function(u) { return
_hw.pictureSize(u) } }` (lead's batch file: wave 2). With `sizeOf` null the
factor falls back to `e.photoNatural()` for the bottom picture (today), so
wave 1 does not break the dialog. `e.tick` is read in exportFactor so the
binding follows layer changes.

PrintExportWindow.qml:470 label becomes "Scale (100% = the most detailed
background picture's own size)" (A-RENDER; file not in the lead's batch).
