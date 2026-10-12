# D-03-DEVICE-IMAGE: contract (DEVIMG-PLAN, 2026-10-11, planning only)

User decisions 1a, 2a, 3a, 4a (2026-10-11, "i approve your recommendations").
Line numbers are from the tree at 22:40 today, which includes the uncommitted
D-07-BG-COMPOSITE batch (store.py, hardware_profile.py, device_pack.py,
device_library.py, history_model.py are all modified and uncommitted). The
build starts after that batch is committed, or works on top of it.

## 0. What is there today (verified in code)

- An uploaded picture is a background layer. Every upload path ends in
  `store.set_device_photo(doc, ref, folder)` (store.py:1544-1594), which makes
  `ref` the bottom background picture (inserts a node at index 0 or replaces
  the `src` of the bottom one).
  - Module Setup Import Image: `DialogConfigureModule.qml:165-173 importPhoto`
    -> `HardwareProfile.keepPhoto` -> `copyImage` (hardware_profile.py:2220-2257,
    stages `photo<ext>` in the "setup" edit) -> Save
    `module_model.saveClaim` (module_model.py:2844-2966; `set_device_photo` at
    2918-2920) inside `store.commit_edit`. `HardwareProfile.commitEditFor`
    (hardware_profile.py:2351-2373) has a second `set_device_photo` branch that
    is reached only if the edit is still open after saveClaim (saveClaim
    commits it first, module_model.py:2937-2943), so in practice saveClaim is
    the one writer.
  - Logical Device card Add / Change Image: `ModuleListModel.setCardImage`
    (module_model.py:1698-1729; `slug != "logical"` refused at 1704) ->
    `import_photo` (module_model.py:400-441, writes `pictures/photo<ext>`,
    deletes other `photo.*`) -> `set_device_photo` in `store.update_path`.
  - Logical Device Remove Image: `removeCardImage` (module_model.py:1731-1760):
    deletes `store.photo_files` (store.py:569-579, `photo.*` and `photo_*`)
    and removes the bottom background node.
  - Home Undo for the picture: `_logical_picture` / `_put_logical_picture`
    (module_model.py:450-503) keep the `photo.*` file bytes and the bottom
    background node; `_home_state(picture=True)` (1250-1259), `_apply_state`
    (1303-1307).
- HidHide Add / Change Image does NOT touch the device: `HidHideModel.setDevicePhoto`
  (hidhide.py:1025-1045) stores the picked file's own path per HidHide instance in
  config `display/hidhide/photos` (`_load_photos` / `_save_photos`, hidhide.py:243-262);
  `_card_photo` (232-240) prefers it over `_module_photo` (498-512, which calls
  `hw.profilePhotoUrl(name)` without a guid); rows get `photo` and
  `photoSource` "override" / "missing" / "module" (hidhide.py:600-606). Spec
  02 S82 says exactly this (picked file used where it is).
- Readers of "the device's photo":
  - `store.shown_photo_ref` (store.py:1709-1717): device-photo.png when the map
    has a visible background and the file exists, else `device_photo_ref`
    (bottom background picture, store.py:1470-1481).
  - `HardwareProfile.profilePhotoUrl` (hardware_profile.py:2424-2454): uses
    shown_photo_ref, then ALSO falls back to any `pictures/photo.*` by glob
    (2445-2446); asks the maker via `_want_device_photo` (2456-2474).
    Called by Home cards (`module_model._photo` 2186-2190), Module Setup
    (DialogConfigureModule.qml:88, 155, 186), HidHide (`_module_photo`), Xbox page.
  - Device Library `photo()` (device_library.py:1806-1834) -> shown_photo_ref.
  - Export preview `device_pack` 832-835 -> shown_photo_ref; a second export
    preview `HardwareProfile.peekPackDeviceById` (hardware_profile.py:1393-1440)
    uses `device_photo_ref` (bottom background picture) at 1423, NOT the
    shown photo (a gap against 08 S107 today).
  - Import preview `device_pack` 1140-1142 -> shown_photo_ref.
  - History text `device_pack.module_text` 464-466 ("Photo" = bottom bg picture).
  - Device Library `_contents` holds "device_map" when `device_photo_ref`
    (device_library.py:1393).
- Carriers (all through `store.named_refs`, store.py:1720-1730): History
  (history_modules.py:213, history_model.py:678), edit start copies
  (store.py:1950), unused-picture clean-up (store.py:1786), `.gmap` export /
  import (device_zip.py:99, 658, 795; device_pack.py:962), Swap
  (library_swap.py:329 on map keys only), one-time folder move
  (folders_move.py:592). Pack import writes only pictures the nodes name
  (`_write_pictures`, device_pack.py:1636-1680, `used` from nodes at 1650-1655).
- The Device Mapping Editor's Save writes its whole payload over the file's
  keys (`packed.setdefault(key, value)` for disk keys only, then
  `doc.clear(); doc.update(packed)`, hardware_profile.py:2127-2137): any key in
  the editor's loaded document wins over the disk.

## 1. The file and where it is named

- File: `<device folder>/pictures/device-image.<ext>` (ext of the picked file
  if in `.png .jpg .jpeg .webp .bmp`, else `.jpg`, as `module_model._PHOTO_EXT`
  today). A clash with another file of that name gets `_<n>` through the
  existing `store._free_picture_name` (no reserved name needed: the image is
  found by its key, never by its file name).
- Named in the module file by one top-level key:
  `"deviceImage": "pictures/device-image.png"`. Not a node; no plane; the
  Device Mapping Editor never sees, shows, saves or removes it.
- Why a key and not "find device-image.* by glob": every carrier already works
  from `named_refs(doc)` (History, `.gmap`, Library saved setups, edit start,
  clean-up), so one line in `named_refs` carries it everywhere; a glob would
  need folder access in each carrier.

## 2. Store (gremlin/modules/store.py), owner A-STORE

```python
DEVICE_IMAGE_KEY = "deviceImage"
DEVICE_IMAGE_STEM = "device-image"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")   # moved from module_model._PHOTO_EXT

def device_image_ref(doc: object) -> str
    """The device's uploaded image as the module file names it
    ("pictures/<file>"), "" when none (03 S52 as changed)."""

def device_image_name(src: Path) -> str
    """"device-image" + the picked file's extension (IMAGE_EXT, else .jpg)."""

def shown_photo_ref(doc: object, exists: Callable[[str], bool]) -> str
    """Precedence (07 S127 as changed):
       1. device_image_ref(doc) when it is set and exists(it);
       2. picture_ref(DEVICE_PHOTO) when visible_background(doc) and exists(it);
       3. device_photo_ref(doc) (the bottom background picture: while the
          generated picture is being made, or when it is missing);
       4. "" (the caller's exists() / find_picture then gives nothing)."""

def named_refs(doc) -> set[str]       # + device_image_ref(doc) when set

def set_device_image(device_name: str, guid: str, src: Path | bytes,
                     who: str) -> str
    """Outside any edit (Home card menu, HidHide): copies src into the
    device's pictures/ under a free device-image name, names it in the
    module file (update_path(..., who): one write, one History entry, the
    module-files notice), then remove_unused_pictures(name, guid) drops the
    previous image file. Refuses a damaged module file (03 S64) before any
    picture is written: returns "". On a failed module write the new file
    is removed. Returns the new ref."""

def remove_device_image(device_name: str, guid: str, who: str) -> bool
    """Drops the key (update_path) and then the file (remove_unused_pictures;
    History keeps it with the entry). False when there was none, or the file
    is damaged."""
```

- `set_device_photo` (store.py:1544-1594) loses every caller (section 5) and
  goes, with its tests. `device_photo_ref` stays (fallback 3, module_text,
  device_library `_contents`, peekPack until switched).
- `photo_files` (store.py:569-579) goes (callers module_model 457, 502, 1713,
  1744 all replaced). `remove_pictures(pattern="photo.*")` (1428-1449) has no
  caller in gremlin/ (grep, 22:45): it goes too.
- `background_key` / `_layer_refs` are unchanged: the image is not part of the
  background, so setting it never re-makes device-photo.png (3a: the generated
  picture keeps being made from the background regardless).

## 3. Writers

| Writer | Code today | New (owner) |
|---|---|---|
| Home card **Add Image… / Change Image…** (every input card + Logical Device) | `setCardImage` slug "logical" only | `ModuleListModel.setCardImage(slug, fileUrl) -> bool`: row by slug -> (raw_name or name, guid); refuses cards without a device folder kind (output / Xbox per Q4); `store.set_device_image(name, guid, src, "Home")` inside `_home_step(label, image=(name, guid))`; label "Change Image" if `device_image_ref` was set else "Add Image"; then `_set_card_photo(slug)` (A-HOME) |
| Home card **Remove Image** | `removeCardImage` slug "logical" only | `removeCardImage(slug)`: `store.remove_device_image(...)` in `_home_step("Remove Image", image=...)` (A-HOME) |
| Module Setup **Add Image… / Change Image…** | `importPhoto` -> `keepPhoto`/`copyImage` stages `photo<ext>` | `HardwareProfile.keepImage(device_name, url) -> ref` stages `device-image<ext>` via `_stage` (same edit, same damage refusal); QML `stagedImage = ref`, `imageRemoved = false`; preview `_hw.imageUrl(ref)` (A-SETUP) |
| Module Setup **Remove Image** (new) | none | QML only: `stagedImage = ""`, `imageRemoved = true`, `claimDirty = true`; preview `_hw.generatedPhotoUrl(deviceName)` (precedence without step 1) (A-SETUP) |
| Module Setup **Save** | `saveClaim(name, direction, photo)` -> `set_device_photo` | `saveClaim(name, direction, image="", removeImage=False)` (new Slot overload str,str,str,bool): in `change(doc)`, `doc[DEVICE_IMAGE_KEY] = image` when image, `doc.pop(DEVICE_IMAGE_KEY)` when removeImage. commit_edit copies the staged file and `remove_unused_pictures` drops the old one (store.py:2038-2063) (A-HOME owns module_model.py) |
| `HardwareProfile.commitEditFor` photo branch (2356-2369) | second `set_device_photo` | goes; `_staged_photo` and `keepPhoto` / `copyImage` names go (A-SETUP) |
| HidHide **Add Image / Change Image** | `setDevicePhoto(instance, path)` -> config `photos` | `HidHideModel.setDeviceImage(instance_id, url) -> bool`: the row's linked module label -> (name, guid) from `_dill_matches()` (label "vJoy N": the vJoy device per Q4) -> `store.set_device_image(name, guid, src, "Hardware Hide")`; then `reload()`. `_CFG_PHOTOS`, `_load_photos`, `_save_photos`, `_card_photo`, `photoSource`, the photo half of `_forget_*` go; rows show `_module_photo` only, called WITH the guid (`hw.profilePhotoUrl(name, guid)`) (A-HIDHIDE) |
| Device Mapping Editor Save | writes its whole payload | `payload.pop(store.DEVICE_IMAGE_KEY, None)` before `packed` (hardware_profile.py ~2111) so the disk's key always stays (the editor doesn't own it; an image set on Home while the editor is open is not undone by its Save) (A-SETUP) |
| Pack import | `_write_pictures` writes only node pictures | ticked "Device image" row (`in.image`) takes the pack's key and file; unticked keeps this device's key (A-PACK) |

## 4. Readers (precedence everywhere through `shown_photo_ref`)

| Reader | Change (owner) |
|---|---|
| `HardwareProfile.profilePhotoUrl` 2424-2454 | precedence via shown_photo_ref; the `photo.*` glob fallback (2445-2446) GOES (it would put any old file ahead of the generated picture); `_want_device_photo` still runs on the background part even when the image wins (3a) (A-SETUP) |
| new `HardwareProfile.generatedPhotoUrl(name)` | shown_photo_ref with step 1 skipped: Module Setup's preview after a staged Remove (A-SETUP) |
| `peekPackDeviceById` 1423 | `store.shown_photo_ref(doc, lambda r: resolve(r) is not None)` (fixes the existing 08 S107 gap too) (A-SETUP) |
| Home cards, Xbox page, HidHide rows | through profilePhotoUrl, no change of their own; card model gains role `hasImage` (bool: `device_image_ref` set and file there) for the menu (A-HOME) |
| Device Library `photo()` 1821 | no code change (shown_photo_ref and the zip's names) |
| Export preview 832, Import preview 1140 | no code change (shown_photo_ref); `_stage_images` (device_pack.py:1059-1078) stages every file of the pack's pictures by its name, so the image's arc is in `urls` |
| `module_text` 464-466 | new section "Device image" for key `deviceImage` (else it lands in "Other settings") (A-PACK) |
| Device Library `_contents` 1393 | `deviceImage` counts toward "setup" (holds) (A-PACK) |
| StatusCard menu 538-544 | items on every input card + Logical Device; "Remove Image" visible on `hasImage`, not on `photo` (a generated picture is not removable here) (A-HOME) |

## 5. Undo

- Home: every card's Add / Change / Remove Image is one Home Undo step
  (01 S143, 03 S136). `_home_state(picture=True)` becomes
  `_home_state(image: tuple[str, str] | None)`: `state["image"] =
  {"name", "guid", "ref", "files": {file name: bytes}}` (the key and the
  image file's bytes, so Undo of Remove brings the file back).
  `_apply_state` puts the file back (`store.put_picture_at`), sets or pops
  the key (`store.update_path(..., "Home")`), drops an image file the state
  doesn't name (`_remove_pictures_soon`), `_set_card_photo(slug)`.
  Replaces `_logical_picture` / `_put_logical_picture` (module_model.py:450-503).
- Module Setup: the image change waits in the "setup" edit until Save (as
  Import Image today, 03 S52, 07 S107); Discard / Cancel drop it; it is not
  on Module Setup's own Undo pair (that covers checks and names only,
  DialogConfigureModule.qml:107-110). Unchanged rule.
- HidHide: no Undo of its own; History has the entry (02 S83: HidHide choices
  appear in History).
- History: each write is a module-file write through the store, so History
  keeps one entry with the image file (named_refs).

## 6. Carry rules

| Path | Rule | Code |
|---|---|---|
| History keep / restore (08 S8, S43) | carried: a named picture | none (named_refs) |
| `.gmap` export (08 S49, S113) | carried at `pictures/<file>` | none (named_refs, device_zip 99) |
| Import as a new device | taken | `_write_pictures`: add `device_image_ref(doc)` name to `used` |
| Import onto an existing device | own row "Device image" (`in.image`, Input module section); ticked: pack's key + file; unticked: this device's key stays (`_merge_module` must not copy `deviceImage` unless ticked) (Q3) | device_pack `_module_items`, `_merge_module`, `_write_pictures` |
| Restore Import (08 S80) | puts back the previous key and file | none (record list covers written files; verify) |
| Device Library Save / saved setups (10 S11, S18) | carried (a `.gmap`) | none |
| Device Library Restore (put back, `everything=True`) | taken | library_copy `_module_items`: add `in.image` when everything |
| Copy Setup to Another Stick (10 S22, S61) | NOT copied (it is a picture of the other stick) (Q2) | none: `in.image` not in `_PART_ITEMS` |
| Swap with Another Stick | NOT swapped: stays with its stick (Q2) | none: library_swap `_MAP_KEYS` = nodes, ui |
| Remove from Library / Delete Device | goes with the folder; the autosave `.gmap` holds it | none |
| Rename (03 S131) | whole folder moves | none |

## 7. What existing uploaded images become (no migration, unreleased program)

Every picture uploaded before this change is a bottom background layer
(`pictures/photo.<ext>` named by a background node). After the change, with
no migration code:
- It stays a background layer: the Device Mapping Editor shows it in
  Background as today; the generated picture (device-photo.png) includes it,
  so Home cards, Module Setup, HidHide and the Library look the same as now.
- The card menu says **Add Image…** (no uploaded image yet) and offers no
  Remove Image for it (it is removed in the editor's Background now).
- HidHide pictures picked before (config `display/hidhide/photos`) are no
  longer read: those rows show the device's shown photo instead; the old
  settings key is dropped at the next HidHide settings write (or left unused).
- OT-2 (`planes_once.old_photo_to_layer`, one-time code for maps saved before
  the planes) keeps turning an old top-level "image" into a bottom layer
  (Q8); it is no longer called from `set_device_photo` (which goes) but
  still from load, swap and pack import.
