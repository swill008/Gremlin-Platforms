# D-07-BG-COMPOSITE: build split (BGPIC-PLAN, 2026-10-11)

Contract: scratchpad/bgpic/contract.md. Spec text: scratchpad/bgpic/spec_draft.md.

## Files the change touches, grouped by owner

| Group | Files | In the lead's uncommitted batch? |
|---|---|---|
| Store rules | gremlin/modules/store.py | no |
| Maker | gremlin/ui/device_photo.py (new) | no |
| Renderer and host | qml/RigRenderer.qml, qml/DevicePhotoHost.qml (new), qml/PrintExportWindow.qml | no |
| Python callers | gremlin/ui/hardware_profile.py, gremlin/device_library.py, gremlin/ui/device_pack.py | no |
| Lead wiring | joystick_gremlin.py (context property `devicePhotoMaker`), qml/Main.qml (`DevicePhotoHost {}`), qml/DialogDeviceMappingEditor.qml (`sizeOf` on `_renderer`, one line) | DialogDeviceMappingEditor.qml: YES |
| Old tests that pin the old rules | test/unit/test_planes_print.py, test/unit/planes_print_smoke.py, test/unit/test_planes_store.py, test/unit/test_planes_carry.py, test/unit/test_print_export_window.py (label / 100 % text, if pinned) | planes_print_smoke.py: YES |
| Spec, map, Help | claude/program-map/07-device-mapping-editor.md, 03-modules.md, 08-history-pack-automap.md, 10-device-library.md, README.md (counts); qml/help/device_mapping_editor.js, qml/help/home_devices.js, qml/help/device_library.js (and Module Setup's Help topic if it says "photo"); claude/glossary.md if "device's photo" is defined | 07 page, README.md, help/device_mapping_editor.js: YES |

Lead's uncommitted batch (from `git status`, 21:45): claude/program-map/07-*.md,
claude/program-map/README.md, claude/timings.md, qml/DialogDeviceMappingEditor.qml,
qml/RigDrawItem.qml, qml/RigPointerArea.qml, qml/RigPropsPanel.qml,
qml/VkbRigEditor.qml, qml/help/device_mapping_editor.js, qml/rig_*.js (callout,
chips, draw, grouprot, hit, layers, overlays, path, props, selection, shapes,
snap, transform), release-notes/1.0.33.md, test/unit/{b1_drag_smoke,
gesture_undo_core_smoke, gesture_undo_smoke, planes_print_smoke,
rig_editor_harness}.py, test_device_mapping_editor_menubar.py,
test_gesture_undo*.py, and the untracked ps_* / chip_drop_centre / rig_resize
tests. The plan touches none of the rig_*.js / VkbRigEditor / RigDrawItem
files (the renderer reads the editor's existing functions), so only the
three rows marked YES wait.

## Agents

| Agent | Files | Job | Why parallel / why one |
|---|---|---|---|
| A-STORE (wave 1) | gremlin/modules/store.py; new test/unit/test_device_photo_store.py | Constants, `visible_background`, `background_key`, `device_photo_path/key/current`, `write_device_photo` (no History step), `remove_device_photo`, `shown_photo_ref`, `named_refs` adds the file; reserved name in `put_picture`. Tests fail on old code (functions missing / named_refs without the file). | Own file; contract fixes every name the others call. |
| A-MAKER (wave 1) | new gremlin/ui/device_photo.py; new test/unit/test_device_photo_maker.py | `DevicePhotoMaker` (signal `renderWanted`, `request`, `check_all`, slot `rendered`, `hostReady`), `want()`; connect to `moduleFilesChanged`; one job at a time, 10 s timeout; tests with a fake host (a slot that writes a PNG to outPath) and a temp USERPROFILE. Report to lead the two wiring lines for joystick_gremlin.py. | New file; uses store functions by contract (stub-import until A-STORE lands, then run). |
| A-RENDER (wave 1) | qml/RigRenderer.qml, new qml/DevicePhotoHost.qml, qml/PrintExportWindow.qml; new test/unit/test_device_photo_render.py + device_photo_render_smoke.py | `snapshotOf`, job `onlyBg` / `transparent` / `fitBackground` / `side`, `backgroundArea(e)`; new `exportFactor` maths with `sizeOf` (fallback to `photoNatural`); the host; label text. Off-screen smoke: two background pictures + a shape, one hidden, flip and opacity: PNG longest side 1024, hidden one absent, transparent corners; 100 % picks the denser picture. Reports `Main.qml` line to lead. | Own files; the host only needs the maker's signal signature (contract). |
| A-PYCALLERS (wave 1) | gremlin/ui/hardware_profile.py, gremlin/device_library.py, gremlin/ui/device_pack.py; new test/unit/test_device_photo_shown.py | `profilePhotoUrl` through `shown_photo_ref` + `device_photo.want`; new slot `pictureSize(url)`; Library `photo()`; Export / Import previews; `_zip_pictures` skips DEVICE_PHOTO; import-onto-existing with the background kept does not take the pack's file. | Three files, all small edits of the same kind (switch to `shown_photo_ref`); one agent avoids three tiny agents racing on the same store contract. |
| T-E2E (wave 1, test-only) | new test/unit/test_device_photo_e2e.py + device_photo_e2e_smoke.py | Real path off-screen: engine with `devicePhotoMaker` + `DevicePhotoHost`, HardwareProfile Save of a map with a background -> file appears, key current, `profilePhotoUrl` returns it; a foreground-only Save makes nothing; removing the background removes the file. Written first against the contract (fails on old code), run when A-STORE/A-MAKER/A-RENDER report. | Test-only, own files. |
| T-CARRY (wave 1, test-only) | new test/unit/test_device_photo_carry.py | Each path that carries or changes it, with a recording fake maker: `.gmap` export holds pictures/device-photo.png; Library saved setup `photo()` shows it; Import as new / onto existing / Restore Import keep a current key (no re-make) and take or keep it with the background tick; History restore and Device Library restore send the notice -> `check_all` requests; Module Setup Save with Import Image and the Logical Device card's Add Image request a re-make. | Test-only, own file; proves 08/10 carry-through. |
| T-SWEEP (wave 2, after the lead's commit) | test/unit/test_planes_print.py, planes_print_smoke.py, test_planes_store.py, test_planes_carry.py, test_print_export_window.py (only if pinned) | Grep the tests for "bottom background picture", `photoNatural`, `device_photo_ref`, `profilePhotoUrl`, "100%"; rename/re-point `test_100_percent_is_the_bottom_background_pictures_own_pixels` -> `test_100_percent_is_the_most_detailed_background_picture` (smoke adds a second, denser picture above the bottom one); keep `test_profile_photo_is_the_bottom_background_picture` as the fallback case (rename `..._without_the_background_picture_file`). | planes_print_smoke.py is in the lead's batch; the others are kept with it so one agent owns the whole sweep. |
| A-DOCS (wave 2, after the lead's commit) | claude/program-map/07, 03, 08, 10, README.md; qml/help/device_mapping_editor.js, home_devices.js, device_library.js (+ Module Setup Help topic if it names the photo); claude/glossary.md if needed | Apply spec_draft.md; map sections 2 / 3 / 4 / 5 / 10 / 11 for the new files and functions (agents send their map lines); new gap G-row open until built; Help text for Scale 100 % and "the device's photo". | 07 page, README and device_mapping_editor.js are in the lead's batch; one docs owner. |

Lead (not an agent): joystick_gremlin.py and qml/Main.qml wiring (wave 1,
from A-MAKER / A-RENDER reports), qml/DialogDeviceMappingEditor.qml `sizeOf`
line (wave 2), tracker, timings, the one full run, commit.

Left out:
- No separate agent for module_model.py / hidhide.py / StatusCard.qml /
  StatusPage.qml / WindowDeviceLibrary.qml / device_library_model.py /
  DialogDevicePack.qml / DialogConfigureModule.qml: they all read the photo
  through `profilePhotoUrl`, `device_library.photo()` or the pack previews,
  so the change is made once at those owners (fix at the shared owner).
- No separate agent per caller file in A-PYCALLERS: same contract, small
  edits; splitting would cost more in briefs than it saves.
- No editor (VkbRigEditor / rig_*.js) agent: not needed; the renderer uses
  existing editor functions. That also keeps the lead's batch files free.
- 8 agents total (6 in wave 1, 2 in wave 2): inside the 8-10 limit.

## Effort (claude/timings.md rules of thumb)

| Item | Quote | Kind used |
|---|---|---|
| A-STORE, A-MAKER, A-PYCALLERS, T-CARRY, T-SWEEP, A-DOCS | 3-8 min each | Agent fix / feature / docs |
| A-RENDER, T-E2E | 3-8 min each (table); these two carry the only real risk (off-screen QML render, NOT VERIFIED points in contract section 3), so expect the top of the range | Agent fix / feature |
| Wave 1 as a parallel batch | ~10 min | "a batch of parallel agents ~10 min" |
| Wave 2 as a parallel batch (after the lead's commit) | ~10 min | same |
| Lead checks and map | ~5 min | end-to-end line |
| Full run + lint | 5-6 min | Full test run + lint |
| Commit / push | ~2 min | end-to-end line |
| CI | ~10 min (background) | CI on a push |
| End to end | about 30-35 min to commit (10 + 10 + 5 + 6 + 2), CI ~10 min after | sum of the table's steps |

Wave 2 can overlap wave 1 if the lead commits its batch first; then both
waves run together (~10 min) and the end to end is about 20-25 min to commit.
