# Spec draft: device folders (feature 1) — for review

Drafted 2026-10-11 by SPEC-PKG. Nothing in the repo is changed yet.
One decision id for the whole feature: **D-03-DEVICE-FOLDERS**. Every new or
changed statement below carries `[changed 2026-10-11, user: D-03-DEVICE-FOLDERS]`
(written once here to keep the list short; the real edit adds it to each line).
Every new statement is "(not built yet)" until the code lands.

## How things are laid out today (from `gremlin/modules/store.py`)

- Module file: `modules/<slug>.json` (slug from the device name, or name + id start for a clash).
- Device photo and map pictures: `modules/<slug>/` (`pictures_dir_of`); the module file names them as `<slug>/<file>` (`picture_ref`).
- Old photo files: `modules/<slug>_photo.<ext>` beside the module files.
- Picture library: `modules/library/` (`library_dir`, `into_library`): a copy of every photo and picture chosen, never cleaned. Still written today by `hardware_profile.py` (lines 1290, 2130, 2180, 2222).
- Button Map recovery copy: `modules/recovery/<slug>.json` (`recovery_path`).
- Photo safety copy for Cancel: `modules/cache/photo-stash/<slug>/` (`photo_stash_dir`).
- Templates: `modules/templates/<name>.json` (pictures not inside, 07 S81).
- Delete Device removes the picture folder, old photo files, recovery copy and safety copies one by one (`_remove_device_leftovers`).
- Every module-file write calls `_saved()` (claims refresh + module files changed notice, 03 S126).

New layout: `modules/<shown name>/` holds everything for that device (decisions 1a, 2a, 3a).

---

## Page 03 — Modules (next free: S128)

**NEW**
- **S128** Each device should have one folder of its own in the modules folder, holding everything about it: its settings (claims, control names, page layout, Appearance, calibration), its Button Map (both planes, every layer), its pictures and its Button Map recovery copy. (1a, 2a)
- **S129** Saving should write in place: only the file that changed is rewritten, never the whole folder. (1a)
- **S130** A device's folder should be named after its shown name (e.g. "EVO R"), and its Windows id should be kept inside the folder; the program finds a device's folder by that id, not by the folder's name. (3a)
- **S131** Renaming a device should rename its folder at once; if the folder can't be renamed (a file is open elsewhere), the rename is refused and says why, and nothing changes. (3a)
- **S132** The second of two identical sticks should get its own folder named "<name> (2)" (the same name as its card, S5). (3a)
- **S133** Copying settings or a map from one device to another (Copy Button Map, applying a template, the Device Library's Copy and Restore, Device Pack import) should copy the picture files it uses into the receiving device's folder; two devices never share a picture file. (user, with 1a-9a)
- **S134** One-time move on the first start of this version: each device's current files (module file, pictures, old photo files, recovery copy) are gathered into its new folder; the originals are copied first to a dated backup folder; nothing is deleted. This is one-time code, tracked as **OT-1** in the tracker, and removed once it has run on the user's PC. (8a)

**CHANGED**
- **S1** old: "It should use one rule everywhere: the file saved for this device id, then a file bound to this exact device, then the file saved for this device name, then the file named after the device."
  new: "It should use one rule everywhere: the folder holding this device's id (S130), then the folder named after the device." (see Question 3 on file bindings)
- **S3** old: "A renamed stick should keep using its old file everywhere: Module Setup, Button Map, Run, Calibration, Auto Mapper, photo, Delete File, Delete Device, the "not saved yet" label."
  new: "A renamed stick should take its folder with it (S131), so every place (Module Setup, Button Map, Run, Calibration, Auto Mapper, photo, Delete File, Delete Device, the "not saved yet" label) uses the folder under its new name."
- **S4** old: "When no device matches, it should fall back to the file named after the device."
  new: "When no folder holds the device's id, it should fall back to the folder named after the device."
- **S6** old: "Each twin should have its own file, card, Button Map and calibration; an old shared choice should not hand one twin the other's file."
  new: "Each twin should have its own folder (S132), card, Button Map and calibration."
- **S52** old: "Import Image… should set the device picture."
  new: "Import Image… should copy the picture into the device's folder and set it as the device picture."
- **S54** old: "It should show the current file name, "(not saved yet)" when it is missing, and a note when the stick still opens a file of another name."
  new: "It should show the device's folder name, and "(not saved yet)" when it has none." (the "file of another name" note goes, see Question 3)
- **S92** old: "It should remove the device's actions in every mode, its module file and pictures, its file bindings, and the card's size and stack."
  new: "It should remove the device's actions in every mode, its whole folder (settings, map, pictures, recovery copy), and the card's size and stack."

**REMOVED**
- None outright; S94 ("A file another device uses should stay …") becomes moot if file bindings go (Question 3). Keep until that is answered.

---

## Page 07 — Button Map (next free: S106)

**NEW**
- **S106** On Save, picture files in the device's folder that its map no longer uses (both planes, every layer, and the photo) should be removed; pictures the map still uses stay. (6a)
- **S107** Undo during an edit should keep the pictures and photo it may need to put back in a temporary folder, which is deleted when the edit ends (Save, Cancel, Discard, closing the window). (6a)
- **S108** A picture the map names but whose file is missing should show, in Edit, as a grey placeholder reading "Picture missing: <file name>", with **Choose Picture…** on its right-click menu to point it at a new file; outside Edit, and in print and export, its area stays empty. (7a)
- **S109** Copy Button Map from Device and applying a template should copy the pictures they use into this device's folder (03 S133); Cancel removes them again. (with 1a)
- **S110** A template should be its own small folder holding the layout and its own copies of its pictures, so it still shows them after the device it came from is deleted. (5a)

**CHANGED**
- **S10** old: "It should keep a renamed stick's photo with the module file its Button Map opens."
  new: "It should keep a renamed stick's photo in its folder, which moves with the rename (03 S131)."
- **S26** old: "It should, on Cancel or Discard, put the session's starting photo back (files and the module file's `image`), and leave no undo steps behind."
  new: "It should, on Cancel or Discard, put the session's starting photo and pictures back from the edit's temporary folder (S107), and leave no undo steps behind."
- **S32** old: "… keep a recovery copy of unsaved edits (photo, pose, map) every "Seconds between recovery copies" while editing …"
  new: same text, plus "The recovery copy is kept in the device's folder (03 S128)."
- **S36** old: "It should, after a crash in the middle of a photo change, bring back the saved photo unless a recovery copy is waiting."
  new: "It should, after a crash in the middle of an edit, bring back the saved photo and pictures from the edit's temporary folder unless a recovery copy is waiting, then delete that folder."
- **S40** old: "It should, on Choose Photo…, copy the picture into the device's folder as its photo and keep the old one so Cancel can put it back."
  new: "It should, on Choose Photo…, copy the picture into the device's folder as its photo and keep the old one in the edit's temporary folder (S107) so Cancel can put it back."
- **S62** old: "… and save them beside the module file."
  new: "… and copy them into the device's folder."
- **S80** old: "It should rename, export to a file, import (a taken name gets a number) and delete templates …"
  new: same text, with "export to a file" reading "export to one file holding the template and its pictures, and import that file the same way". (see Question 6)

**REMOVED**
- **S81** old: "It should keep in a template where its pictures are, not the picture files." Why: replaced by S110 (a template carries its own pictures).

**Other map fixes on page 07**
- Section 3 row "Picture library `modules/library/` … (`_into_library` removed 2026-10-10, F4-DEAD; nothing writes it now)" is wrong: `store.into_library` is still called from `hardware_profile.py` (1290, 2130, 2180, 2222). Correct the row, then mark the library as removed by this feature.
- Section 3 row "Photo safety copy `modules/cache/photo-stash/<slug>/`" becomes the edit's temporary folder (S107).
- Q11 answered by this decision (see Gaps closed).

---

## Page 08 — History, Device Pack, Auto Mapper (next free: S111)

**NEW**
- **S111** Export should zip one device folder into one file (e.g. "EVO R.gmap", see Question 4); Import should unpack it into a new device folder (twins and taken names get "(2)"). (4a)
- **S112** Export/Import of device folders takes over from the Device Pack over time (to-do 40); until then the Device Pack keeps working as S49-S110 say. (4a)

**CHANGED**
- **S8** old: "Every save of a device's module file should be kept with the file before and after and every picture it names …"
  new: "Every save in a device's folder should be kept with the files before and after and every picture its map names …" (rest unchanged)
- **S14** old: "Files outside the modules folder itself (imported backups, recovery copies, templates, profile copies) should not be module-file entries."
  new: "Recovery copies, the edit's temporary folder, imported backups, templates and profile copies should not be module-file entries, also when they sit inside a device's folder."
- **S43** old: "A module file should be put back at once, with its pictures, into today's modules folder …"
  new: "A device's files should be put back at once, with their pictures, into that device's folder today (found by its id, 03 S130) …"
- **S49** old: "… should save a device's module file, its pictures, its wires … into one zip."
  new: "… should save a device's folder (settings, map, pictures), its wires … into one zip." (S112 says the Device Pack is phased out)

**REMOVED**
- None.

---

## Page 10 — Device Library (next free: S60)

**NEW**
- **S60** A saved setup's device part should be the same zip as Export makes (08 S111): the device's folder as it was. (4a)
- **S61** Copy to Another Stick and Restore should copy the pictures the map uses into the receiving stick's folder (03 S133). (with 1a)

**CHANGED**
- **S11** old: "A saved setup holds any of: Setup (claims, friendly names), Button Map and photo, Appearance, Calibration, and Bindings …"
  new: same, with "Button Map and photo" reading "Button Map (both planes, every layer) with its photo and pictures".
- **S18** old: "An autosave should hold everything the stick has: its module file and pictures, and its bindings …"
  new: "An autosave should hold everything the stick has: its whole folder, and its bindings …"
- **S52** old: "Remove from Library… removes the device entirely: its module file and folder (pictures, Button Map photo, recovery copies), …"
  new: "Remove from Library… removes the device entirely: its folder (settings, map, pictures, recovery copy), …" (rest unchanged)
- **S57** keeps "folder and file names the Library builds are cut to 80 characters"; extend to device folders (03 S130) if the user agrees (Question 2).

**REMOVED**
- None.

---

## Gaps closed

- **To-do 28 / GL-274** (picture library "Remove unused" button): closes as no longer needed; the shared library goes and each save removes its own unused pictures (07 S106). Replaces D-07-GL274-LATER.
- **07 Q11 / G19** (unused pictures after Cancel, `modules/library` growing for ever, leftovers of deleted devices): fixed by 07 S106, S107, 03 S92 (whole folder goes).
- **07 section 3 stale library note**: corrected (see page 07).
- Possibly **03 S94** and file-binding gaps, if file bindings go (Question 3).

## Decision row for claude/decisions.md (draft)

| D-03-DEVICE-FOLDERS | 2026-10-11 | **One folder per device** (feature 1, all "a"): (1a) one folder per device holds everything, saved in place, only the changed file rewritten; (2a) inside: the device's settings (claims, control names, page layout), its Button Map (both planes, every layer), its pictures and its recovery copy; (3a) the folder is named by the device's shown name, the device id is kept inside, renaming the device renames the folder, twins get "(2)"; (4a) Export zips one device folder into one file, Import unpacks it into a new device folder, this takes over from the Device Pack over time (to-do 40), the Device Library saves the same zip; (5a) a template is its own small folder with its own pictures; (6a) a device save removes picture files its map no longer uses, the shared picture library (`modules/library`) goes, Undo during an edit uses a temporary folder deleted when the edit ends, to-do 28 closes (replaces D-07-GL274-LATER); (7a) a missing picture shows in Edit as a grey "Picture missing: <file name>" placeholder with Choose Picture…, empty outside Edit and in print; (8a) a one-time move on first start gathers each device's files into its folder, originals kept in a dated backup folder, nothing deleted (one-time code, tracker OT-1); (9a) device folders are built first, background/foreground planes on top. Also: copying a map to another device copies its picture files into the receiving device's folder (no sharing). | User: all "a" (2026-10-11, Button Map plan, feature 1). | 03 S1, S3, S4, S6, S52, S54, S92, S128-S134; 07 S10, S26, S32, S36, S40, S62, S80, S81 (removed), S106-S110; 08 S8, S14, S43, S49, S111, S112; 10 S11, S18, S52, S57, S60, S61 |

And mark D-07-GL274-LATER: "Superseded 2026-10-11 by D-03-DEVICE-FOLDERS (no shared library; to-do 28 closed)."

---

## Questions the draft raised

**F1 — Device folders**

- **F1-1 Same name, not twins.** Two different devices with the same shown name (e.g. two "Throttle" from different makers, or a user renaming one stick to another's name): recommend a) "(2)" as for twins, decided by id; b) refuse the rename while another device has that name.
- **F1-2 Unsafe names.** Shown names may hold characters Windows can't use in a folder name (`\ / : * ? " < > |`, a trailing dot). Recommend a) replace each with "_" and cut to 80 characters (as 10 S57), the shown name stays as typed inside.
- **F1-3 File bindings.** Today a stick can be pointed at another device's module file (Module Setup's file choice; 03 S1 steps 2-3, S54, S94). With the id inside the folder this has no job. Recommend a) remove file bindings (unreleased program, no legacy compatibility); b) keep them as a pointer to another device's folder.
- **F1-4 File extension.** Decision 4a says "e.g. .gmap". Needs confirming: a) ".gmap"; b) another name; c) ".zip".
- **F1-5 Where Export's file goes.** a) a Save dialog anywhere except inside the modules folder (same rule as 08 S57); b) a fixed exports folder.
- **F1-6 Template export.** Does a template's "export to a file" become a zip of its folder too (same extension as F1-4 or its own)? Recommend a) same zip format, its own extension.
- **F1-7 Does the export zip carry bindings?** The device folder holds no profile wires; the Device Pack and Library saved setups do. Recommend a) the folder zip plus an optional bindings part, as the Library's saved setups have today.
- **F1-8 Which devices get folders.** Sticks only, or also Keyboard, OSC, the Logical Device and vJoy / Xbox output modules (all have module files today)? Recommend a) every device with a module file.
- **F1-9 Pictures added during an edit, then Cancel.** Are new pictures written into the device folder at once (and removed on Cancel), or into the temporary folder until Save? Recommend a) into the temporary folder until Save, so Cancel leaves nothing.
- **F1-10 Where the dated backup (8a) goes.** a) `<data folder>\backup\<date> device folders move\`; b) inside the modules folder.
- **F1-11 Imported backups.** Module Setup's import and Device Pack keep the previous file in `modules/imported` (03 S58, 08 S73). a) keep it there; b) move into the device's folder.
- **F1-12 Folder rename when a file is open.** Draft S131 says refuse the rename and say why; confirm.
