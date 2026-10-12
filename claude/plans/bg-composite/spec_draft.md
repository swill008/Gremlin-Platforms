# D-07-BG-COMPOSITE: spec draft (BGPIC-PLAN, 2026-10-11)

User decisions 2026-10-11 ("1a", "1.a", approved, go). Tag on every changed
or new line: [changed 2026-10-11, user: D-07-BG-COMPOSITE]. The page 07 text
below was read at 21:45 (lead's batch not yet committed: A-DOCS applies it
after the commit, against the committed text). Next free statement number on
07 checked as S157 (S140-S156 are D-07-PS-MATCH; gaps run to G63); A-DOCS re-checks.

## Page 07, section 8

**S83 (changed)**

- **S83** It should make 100% scale the own pixels of the visible background picture with the most detail (the most picture pixels per unit of the page, its crop and box size counted; hidden pictures left out); with no visible background picture, the page 1920 pixels wide; from 10% to 800%, whatever the window size or screen scale; the "photo frame" keeps its name. [help: File menu and export] [test: test_print_export_window.py::test_every_screen_scale_gives_the_same_picture] [test: test_device_mapping_editor_print_area.py::test_scale_and_saving] [changed 2026-10-11, user: D-07-BG-COMPOSITE] (was: It should make 100% scale the own pixels of the bottom background picture (none: the page 1920 pixels wide), from 10% to 800%, whatever the window size or screen scale; the "photo frame" keeps its name.) [changed 2026-10-11, user: D-07-BACKGROUND-PLANES] (was: It should make 100% scale the photo's own pixels (no photo: the page 1920 pixels wide), from 10% to 800%, whatever the window size or screen scale.)

(The test tag `test_planes_print.py::test_100_percent_is_the_bottom_background_pictures_own_pixels` is replaced by `test_planes_print.py::test_100_percent_is_the_most_detailed_background_picture` once T-SWEEP lands; not built until then.)

**S127 (changed)**

- **S127** On screen, "Background" should name the background plane everywhere (menu, items, Layers, status line, Help); "photo" stays only for the device's picture in general. "The device's photo" shown elsewhere (Home cards, the Logical Device card, Module Setup, the HidHide window, the Xbox page, the Device Library's Device map photo, the Export / Import Device previews) is the device's background picture (S157); while it is being made, or when the device has none yet, the bottom background picture is shown instead. Module Setup's Import Image sets the bottom background picture (one owner, RB1, Q5), and the background picture is then made from the whole background. [changed 2026-10-11, user: D-07-BG-COMPOSITE] (was: ... "The device's photo" shown elsewhere (Module Setup, Home cards, HidHide, the Xbox page) is the bottom background picture, and Module Setup's Import Image sets that same layer (one owner, RB1, Q5).) [changed 2026-10-11, user: D-07-BACKGROUND-PLANES] [existing test tags kept; `test_planes_store.py::test_profile_photo_is_the_bottom_background_picture` becomes the fallback case]

**S157 (new)**

- **S157** Whenever the background changes, the program should save a picture of the whole background plane in the device's folder (`pictures/device-photo.png`, "the device's background picture"): every visible background layer (pictures, shapes, lines and text) drawn together with its crop, Look, opacity, rotation, skew and flip, hidden layers left out as in an export, cut to the layers' own extent, at most 1024 pixels on its longer side, on a transparent ground. It is made at the Device Mapping Editor's Save, and when Import Device (as a new device or onto an existing one), Restore Import, a History restore, a Device Library restore, Module Setup's Import Image or the Logical Device card's Add / Change / Remove Image changes the background; a save that leaves the background as it was makes nothing new. It is kept and carried with the device's pictures (History, `.gmap`, Device Library saved setups) and made again whenever it no longer matches the background; a device with no visible background has none. [changed 2026-10-11, user: D-07-BG-COMPOSITE] [help: Background and foreground] (not built yet)

## Page 07, section 10 (known gaps)

- **G64** (open, 2026-10-11, D-07-BG-COMPOSITE) S83, S127, S157: the device's background picture is not made yet; everything shows the bottom background picture and 100% follows the bottom background picture. Fix: contract scratchpad/bgpic (`store.shown_photo_ref`, `gremlin/ui/device_photo.py`, `DevicePhotoHost.qml`, `RigRenderer.exportFactor`). (A-DOCS: use the next free G number.)

## Page 07, section 12 (decisions)

| S83, S127, S157 | 2026-10-11 (D-07-BG-COMPOSITE; user: "1a", "1.a", approved, "the user's ask is now a go"): the device's photo shown everywhere is a saved picture of the whole visible background plane (S157), made whenever the background changes, at most about 1024 px, in the device's folder; this replaces 17a's "the bottom background picture is the device's photo elsewhere" for what is shown (Module Setup's Import Image still sets the bottom background picture). 100% is set by the visible background picture with the most detail; no pictures: the page 1920 px wide (replaces 16a's "the bottom background picture sets 100 %"). Not built yet (G64). |

And in the D-07-BACKGROUND-PLANES row, after "(16a, 17a)": "(16a and 17a's shown photo replaced 2026-10-11 by D-07-BG-COMPOSITE)".

## Page 03 (modules), section 8

- **S52 (changed)** Import Image… should copy the picture into the device's folder and set it as the bottom background picture of its device map (07, D-07-BACKGROUND-PLANES 17a); the device's photo shown afterwards is the background picture made from the whole background (07 S157). [changed 2026-10-11, user: D-03-DEVICE-FOLDERS] [changed 2026-10-11, user: D-07-BACKGROUND-PLANES] [changed 2026-10-11, user: D-07-BG-COMPOSITE] (was: Import Image… should copy the picture into the device's folder and set it as the device picture, which is the bottom background picture of its device map (07, D-07-BACKGROUND-PLANES 17a).) [existing help/test tags kept]
- **S73 (changed)** A card should show its photo, the device's background picture (07 S157; the bottom background picture until that is made) (not in compact view), name, status · bus, claimed counts in words ("1 hat", "2 hats"), "Driven by: [...]" on output cards only, and "last: ...". [changed 2026-10-11, user: D-07-BG-COMPOSITE] (was: A card should show its photo (not in compact view), name, ...) [existing tags kept]
- **S88 (changed, one sentence added after the Logical Device's Add Image… / Change Image… text)** "The picture it adds becomes the Logical Device's bottom background picture, and the card shows the background picture made from it (07 S157)." [changed 2026-10-11, user: D-07-BG-COMPOSITE]

## Page 08 (History, packs), section 8

- **S8 (note, no change of meaning)**: append "The device's background picture (07 S157) is one of the pictures the map names." [changed 2026-10-11, user: D-07-BG-COMPOSITE]
- **S20**: no change (the background picture is a named picture like any other).
- **S75 (changed)**: append "Keeping this device's background keeps its background picture; taking the pack's background takes the pack's (07 S157)." [changed 2026-10-11, user: D-07-BG-COMPOSITE]
- **S113 (changed)**: "A `.gmap` should carry every background layer, its pictures and the device's background picture (07 S157); Import puts them back as they were." [changed 2026-10-11, user: D-07-BG-COMPOSITE] (was: A `.gmap` should carry every background layer and its pictures; Import puts them back as they were.) [existing tags kept]
- Export / Import Device previews (08 S111 area): A-DOCS adds to the statement that names the preview picture: "the preview shows the device's background picture (07 S157; the bottom background picture when the file has none)".

## Page 10 (Device Library), section 8

- **S11 (changed)**: "... a Device map photo preview (the saved setup's background picture, 07 S157; its bottom background picture when it has none), ..." [changed 2026-10-11, user: D-07-BG-COMPOSITE] (rest unchanged) [test tag added when T-CARRY lands: test_device_photo_carry.py::test_a_saved_setup_shows_its_background_picture]

## Help topics (A-DOCS; wording in the Help's style)

- qml/help/device_mapping_editor.js, Background topic (line ~164): replace "Its bottom picture is the device's photo." with "When you save, a picture of the whole background (every visible layer, as it looks) becomes the device's photo on Home, in Module Setup, in the HidHide window and in the Device Library."
- qml/help/device_mapping_editor.js, Print & Export topic (line ~590): "<b>Scale</b>: the size in pixels of every export and print. 100% shows the most detailed background picture at its own size, pixel for pixel (without a background picture, the page 1920 pixels wide). ..."
- qml/PrintExportWindow.qml label (A-RENDER, code): "Scale (100% = the most detailed background picture's own size)".
- qml/help/home_devices.js line ~36: "The device photo, a picture of the device's background (left out in <b>Compact view</b>) and the device name."
- qml/help/device_library.js line ~116: "Device map photo" sentence: "a picture of the saved setup's background".
- Module Setup Help topic (wherever Import Image is described): "Import Image… puts the picture at the bottom of the device map's background; the device's photo is then a picture of the whole background."
- Glossary: if claude/glossary.md defines "device's photo" / "photo", A-DOCS reports the new wording to the lead (glossary changes are a user decision; UI text follows the glossary). Suggested: "Device's photo: a picture of the whole visible background of the device's map, saved with the device."
