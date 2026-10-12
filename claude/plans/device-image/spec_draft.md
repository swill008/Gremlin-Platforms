# D-03-DEVICE-IMAGE: spec draft (DEVIMG-PLAN, 2026-10-11; NOT applied)

Tag on every changed / added statement:
`[changed 2026-10-11, user: D-03-DEVICE-IMAGE] (not built yet)` /
`[added 2026-10-11, user: D-03-DEVICE-IMAGE] (not built yet)`, keeping the
old text in "(was: ...)" as the pages do. Wording marked {Qn} depends on the
answer in questions.md (recommended option written in).

## 03-modules.md

- S52. **Add Image…** (reads **Change Image…** when the device has an image)
  in Module Setup's **Device Image** box should keep the picked picture in
  the window's edit and, on Save, copy it into the device's folder as its
  device image (`pictures/device-image.<ext>`, named by the module file's
  `deviceImage`); **Remove Image** (only when it has one) drops the device
  image on Save. Neither touches the device map or its background layers.
  Cancel or Discard leaves the folder as it was. [changed 2026-10-11, user:
  D-03-DEVICE-IMAGE] (not built yet) (was: Import Image… should copy the
  picture into the device's folder and set it as the bottom background
  picture of its device map (07, D-07-BACKGROUND-PLANES 17a); the device's
  photo shown afterwards is the background picture made from the whole
  background (07 S157).)
- S73. A card should show its photo (07 S127: the device image when it has
  one, else the device's background picture, else the bottom background
  picture until that is made) (not in compact view), name, status · bus, ...
  [changed 2026-10-11, user: D-03-DEVICE-IMAGE] (not built yet) (was: its
  photo, the device's background picture (07 S157; the bottom background
  picture until that is made))
- S88 (Device section part only; the rest unchanged). Every input card (stick,
  Keyboard, OSC) and the Logical Device card {Q4: and vJoy output cards}
  should have **Add Image…** (reads **Change Image…** when the device has an
  image; opens the shared file chooser, "Choose Image") and **Remove Image**
  (only when it has one; doesn't ask, Home Undo and History can bring it
  back). The picture becomes the device image (S52), written through the
  store, so History, Save to Device Library, Export and Restore carry it;
  it never touches the device map. Each is one Home Undo step (S136).
  [changed 2026-10-11, user: D-03-DEVICE-IMAGE] (not built yet) (was: The
  Logical Device card's Device section has Add Image… ... the picture is its
  card photo, kept with its module file (`photo.<ext>` ... as the bottom
  background picture of its map (07 S127, `store.set_device_photo`) ...).
  Other cards have no image items (they set a picture in Module Setup).)
- S137 (new; S136 is the last today). A device should have at most
  one device image, set from the Home card menu, Module Setup or the HidHide
  window, all three changing the same file; setting it keeps the device's
  background picture being made (07 S157). [added 2026-10-11, user:
  D-03-DEVICE-IMAGE] (not built yet)
- Section 12 row: `| S52, S73, S88, S137 | 2026-10-11 (D-03-DEVICE-IMAGE; user:
  "i approve your recommendations", 1a 2a 3a 4a): an uploaded picture is the
  device image, its own file named by "deviceImage", not a background layer;
  shown ahead of the generated background picture; Add / Change / Remove on
  every input card and the Logical Device, in Module Setup and in HidHide. |`

## 07-device-mapping-editor.md

- S127. On screen, "Background" should name the background plane everywhere
  (menu, items, Layers, status line, Help); "photo" stays only for the
  device's picture in general. "The device's photo" shown elsewhere (Home
  cards, the Logical Device card, Module Setup, the HidHide window, the Xbox
  page, the Device Library's Device map photo, the Export / Import Device
  previews) is, in this order: the device image (03 S52) when it has one and
  the file is there; else the device's background picture (S157); else,
  while that is being made, the bottom background picture; else none (S11).
  The Device Mapping Editor never shows, saves or removes the device image.
  [changed 2026-10-11, user: D-03-DEVICE-IMAGE] (not built yet) (was: ...
  is the device's background picture (S157); while it is being made, or when
  the device has none yet, the bottom background picture is shown instead.
  Module Setup's Import Image sets the bottom background picture (one owner,
  RB1, Q5), and the background picture is then made from the whole
  background.)
- S157 (one sentence changed). "... It is made at the Device Mapping Editor's
  Save, and when Import Device (as a new device or onto an existing one),
  Restore Import, a History restore or a Device Library restore changes the
  background; a save that leaves the background as it was makes nothing new.
  It is still made when the device has a device image (03 S52), which is
  shown ahead of it." [changed 2026-10-11, user: D-03-DEVICE-IMAGE] (not
  built yet) (was: "... a Device Library restore, Module Setup's Import Image
  or the Logical Device card's Add / Change / Remove Image changes the
  background ...")

## 02-devices-input.md (HidHide)

- S82. A HidHide row's **Add Image** / **Change Image** should set the device
  image of the device the row is linked to (03 S52), copied into that
  device's folder, the same image its Home card and Module Setup show; a row
  linked to no device has the button disabled ("Not linked to a device")
  {Q5}. [changed 2026-10-11, user: D-03-DEVICE-IMAGE] (not built yet) (was:
  A device picture is used where it was picked (not copied); if moved or
  deleted the card shows no picture until another is picked.)
- Section 2 (`hidhide.py`) and section 6 settings row: `photos` goes from
  `display/hidhide/*`.

## 08-history-pack-automap.md

- S8. "... every picture its map names (the device image, the device photo
  and map pictures) ..." [changed 2026-10-11, user: D-03-DEVICE-IMAGE] (not
  built yet)
- S75 (added sentence). The device image comes with the pack as its own row,
  **Device image**; ticked, the pack's image replaces this device's; unticked,
  this device's stays. {Q1a: the bottom background picture's own "Device
  photo" row goes; it travels with the background (the Map tick) like any
  other background picture.} [changed 2026-10-11, user: D-03-DEVICE-IMAGE]
  (not built yet)
- S107. "... the preview shows the device's photo (07 S127: its device image,
  else its background picture, else the bottom background picture)."
  [changed ...] (also fixes `peekPackDeviceById`, which showed the bottom
  background picture)
- S113. "A `.gmap` should carry every background layer, its pictures, the
  device's background picture (07 S157) and the device image (03 S52);
  Import puts them back as they were." [changed ...]

## 10-device-library.md

- S11. "... a Device map photo preview (the saved setup's device photo, 07
  S127: its device image, else its background picture, else its bottom
  background picture) ..." [changed ...]
- S62 (added sentence). Save to Device Library and Restore carry the device
  image; Copy to Another Stick and Swap with Another Stick leave each
  stick's device image with that stick {Q2a}. [changed ...]

## claude/glossary.md (new row, beside "Device folder")

| A device's own uploaded picture (03 S52) [D-03-DEVICE-IMAGE, 2026-10-11; not built yet] | **Device Image** (the box in Module Setup); **Add Image…** / **Change Image…** / **Remove Image** (Home card menu, Device section; Module Setup; HidHide's row buttons **Add Image** / **Change Image**); in Help: "the device image" | "photo", "Import Image", "card picture" |

And the line under Term definitions:
| **Device image** | The picture you give a device (Add Image…): its own file in the device folder, shown on its card, in Module Setup and in HidHide ahead of the background picture. It is not part of the device map. |

## Help (A-DOCS)

- home_devices.js:90 (Logical Device only) -> every input card + Logical Device.
- home_devices.js:309, 312: Import Image… -> Add Image… / Change Image… /
  Remove Image; drop "puts the picture at the bottom of the device map's
  background".
- logical_device.js:36: same wording; "its card picture" -> "its device image".
