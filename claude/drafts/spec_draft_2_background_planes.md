# Spec draft for review: background and foreground planes (D-07-BACKGROUND-PLANES)

Drafted by SPEC-PLANES, 2026-10-11, from the user's decisions A–N and 11–21 (all recommended).
Assumes feature 1 (device folders, D-03-DEVICE-FOLDERS) is built first: every picture lives in its device's folder.
Every new or changed line below carries `[changed 2026-10-11, user: D-07-BACKGROUND-PLANES]` (shown once per line as **[D-07-BP]** to keep this short).

---

## Page 07 Button Map

### CHANGED statements

| S | Old text (quoted) | New text |
|---|---|---|
| S14 | "It should light a chip while its control is pressed when not editing; hovering a chip says which control it is, and dragging pans." | It should light a chip while its control is pressed when not editing; hovering a chip says which control it is. Outside Edit, a left-drag pans. In Edit, in both Foreground and Background mode, Space + left-drag pans; a middle-drag pans everywhere; the wheel zooms. (K) **[D-07-BP]** |
| S94 | "It should zoom from 50% to 600%, with Ctrl+0, Ctrl+1 and Ctrl+2." | It should zoom from 50% to 600% with the wheel and with Ctrl+0, Ctrl+1 and Ctrl+2, the same in both modes. (K) **[D-07-BP]** |
| S39 | "It should offer the Photo menu only while editing." | It should offer the **Background** menu (Edit Background, Add Picture to Background…, Clear Background) only while editing. (B, L) **[D-07-BP]** |
| S40 | "It should, on Choose Photo…, copy the picture into the device's folder as its photo and keep the old one so Cancel can put it back." | It should, on **Add Picture to Background…**, copy the picture into the device's folder and add it as the top background layer, fitted to the photo frame; it is one Undo step and Cancel takes it away. (E, L) **[D-07-BP]** |
| S41 | "It should, on Clear Photo, leave no photo (decision Q4: no stock or card photo); if the file can't be removed, put the photo back and say "Clear Photo Failed"." | It should, on **Clear Background**, remove every background layer as one Undo step (no stock or card picture, Q4); picture files nothing uses any more go on Save (feature 1, 6a). (L) **[D-07-BP]** |
| S42 | "It should move, size (25% to 400%), offset and turn the photo with Move Photo and Adjust Photo…; Reset Photo puts the pose back and leaves the look." | It should move, resize, rotate, turn by quarter turns, flip, crop and skew a background item with the same handles, right-click menu and Properties panel as a foreground item of its kind. (F, N) **[D-07-BP]** |
| S43 | "It should apply Brightness, Contrast, Greyscale and Fade, save them with the layout, show them on the live map and in exports, and step through them with Undo." | It should offer **Look** (Brightness, Contrast, Greyscale) and **Opacity** on every picture on both planes ("Fade" becomes Opacity), save them with the map, show them on the live map and in prints and exports, and step through them with Undo. (F) **[D-07-BP]** |
| S44 | "It should let the photo be hidden or locked from its Layers row; the flags are saved only when on." | It should let each background layer be hidden or locked from its Layers row, as foreground layers are; the flags are saved only when on. (G) **[D-07-BP]** |
| S11 | "It should show no photo for a device that has none, never another device's photo or the Gladiator photo." | It should show an empty background for a device that has none, never another device's pictures or the Gladiator photo. (L) **[D-07-BP]** |
| S26 | "…put the session's starting photo back (files and the module file's `image`), and leave no undo steps behind." | It should, on Cancel or Discard, put the session's starting map back, both planes and every picture they use, and leave no undo steps behind. (L) **[D-07-BP]** |
| S30 | "It should count a new photo of the same file type as an unsaved change." | It should count any background change (a picture added, replaced, moved or cleared) as an unsaved change. (L) **[D-07-BP]** |
| S34 | "…Discard deletes the copy and puts the saved photo back…" | …Discard deletes the copy and puts the saved map (both planes) back… (rest unchanged) (L) **[D-07-BP]** |
| S36 | "It should, after a crash in the middle of a photo change, bring back the saved photo unless a recovery copy is waiting." | It should, after a crash in the middle of an edit, bring back the saved background unless a recovery copy is waiting. (L) **[D-07-BP]** |
| S57 | "It should undo the map and the photo's pose, flags and look, and also Choose Photo, Clear Photo, print area changes and guide changes (each one undo step); grid and view are not undo steps." | It should undo both planes in one history: every item's pose, flags and look, Add Picture to Background, Clear Background, Move to Background / Foreground, print area and guide changes (each one step, named with its plane); grid, view, switching mode, "Show foreground faintly" and the Background opacity slider are not undo steps. (16) **[D-07-BP]** |
| S62 | "…and save them beside the module file." | …and add them to the plane being edited (the background in Background mode), saving the files in the device's folder. (E) **[D-07-BP]** |
| S76 | "It should replace this map's chips, leaders and drawings with the copy, keep this device's photo, …" | It should replace this map's chips, leaders and drawings and every background layer with the copy, copying its pictures into this device's folder; … (rest unchanged). (14; see question Q-P4) **[D-07-BP]** |
| S83 | "It should make 100% scale the photo's own pixels (no photo: the page 1920 pixels wide), …" | It should make 100% scale the own pixels of the bottom background picture (none: the page 1920 pixels wide), … (rest unchanged). (see Q-P6) **[D-07-BP]** |
| S87 | "…leave selection marks, handles, guides, grid, hidden items and the red debug frame out…" | …leave selection marks, handles, guides, grid, hidden items, the Background mode banner and the faint-foreground view out; both planes print at full strength… (rest unchanged). (C, J) **[D-07-BP]** |
| S89 | "…a white page with every colour's lightness turned over, the photo unchanged…" | …a white page with every colour's lightness turned over, every picture (both planes) unchanged… (L) **[D-07-BP]** |
| S102 | kind toggles "…Text · Tables · Photo" | Toggle "Photo" goes; the list shows only the plane being edited, and in Background mode only the kinds the background holds (Shapes, Lines, Pictures, Text) show as toggles. (G, N) **[D-07-BP]** |

### NEW statements (page 07, next free S106)

**Planes**
- **S106** A map should have two planes: the **background** (artwork, any number of layers) and the **foreground** (chips and everything else); the background is always drawn behind the foreground. (A) **[D-07-BP]**
- **S107** The background should hold only pictures, shapes (including lines) and text; chips, groups of chips, leaders, hotspots and tables stay foreground-only. (E) **[D-07-BP]**

**Background mode**
- **S108** It should enter **Background mode** from Background › Edit Background, a double-click on the Background row in Layers, the **Foreground | Background** switch on the toolbar, or Ctrl+B (shown in the menu and the switch's tooltip); it leaves by **Done**, Esc or the switch. (B, 12) **[D-07-BP]**
- **S109** In Background mode a coloured banner should read "Editing the background — Done"; the first time ever, it adds "Your chips are shown faintly. Use Move to Foreground to bring an item forward.", never again after. (B, 21) **[D-07-BP]**
- **S110** In Background mode the foreground should show faintly (about 25%, normal colours, labels readable), take no clicks and give no snaps; the banner's **Show foreground faintly** tick hides it, and the choice is remembered for the Button Map window. (C) **[D-07-BP]**
- **S111** In Foreground mode the background should be shown but can't be clicked, dragged or selected. (D) **[D-07-BP]**
- **S112** The status line should say "Foreground" or "Background" while editing. (17) **[D-07-BP]**
- **S113** Align and Distribute (right-click › Align and Distribute) should work in Background mode as in Foreground mode. (15) **[D-07-BP]**

**Layers**
- **S114** Layers should list only the plane being edited, with the same controls in both modes (select, rename, hide, lock, group, drag to reorder; Bring to Front, Bring Forward, Send Back, Send to Back within that plane). (G) **[D-07-BP]**
- **S115** In Foreground mode Layers should end with a folded **Background** row: double-click edits the background; its lock locks every background layer at once; its **Opacity** slider changes how strongly the background shows on screen only (a view setting: not saved with the map, not printed, not an Undo step). (G, 11, 13) **[D-07-BP]**

**Moving between planes**
- **S116** **Move to Background** / **Move to Foreground** (right-click menu, Layers menu, Arrange, Ctrl+Shift+B) should move the selected items, several at once in their order, to the other plane, landing next to it (bottom of the foreground, top of the background); one Undo step; the message line says "Moved to Background" (or Foreground) with Undo. Kinds the background can't hold are greyed out with a tooltip saying why. (H) **[D-07-BP]**

**Snapping**
- **S117** Items should snap within their own plane (items, grid, guides); foreground chips and leaders may also snap to snap points on background pictures; background items never snap to the foreground. (I) **[D-07-BP]**

**Printing**
- **S118** Print & Export should print both planes, background underneath, with an **Include background** tick (on by default) that leaves the background out when off. (J) **[D-07-BP]**

**Big pictures**
- **S119** A picture over about 4000 pixels on a side should be kept as it is, drawn on screen from a cached screen-sized copy, and printed and exported from the original. (18) **[D-07-BP]**

**Older maps**
- **S120** A map saved before the planes should open in the new format with no converter, except that its old background photo settings are read once on first open and become a background picture layer (one-time code, tracker OT item). (M) **[D-07-BP]**

**Help**
- **S121** Help should have a topic "Background and foreground" in place of "Change the photo", with Show me links to the switch, the banner and the Background row. (20) **[D-07-BP]**

**Words**
- **S122** On screen, "Background" should name the background plane everywhere (menu, items, Layers, status line, Help); "photo" stays only for the device's picture in general. (L) **[D-07-BP]**

### REMOVED statements / features (page 07)
- The **Move Photo** mode (was in S42; section 4 row "Photo → Move Photo / Adjust Photo… / Reset Photo"). (N)
- The **Adjust Photo…** dialog and its look sliders (`_photoAdj`, `_lookTimer`, `adjustedPhotoUrl`; section 4 row "Adjust Photo look sliders"; section 6 `_lookTimer`). (N)
- The non-selectable "Background photo" Layers row (was S44). (N)
- **Reset Photo** (was in S42): goes with Adjust Photo, see Q-P2.
- **Choose Photo…** and **Clear Photo** menu items: replaced by Add Picture to Background… and Clear Background (S40, S41).
- Section 3 rows to drop or reword at build time: `photo` pose and look keys, adjusted-photo cache `modules/cache/photo-<hash>.png`, photo safety copy (feature 1 takes its job).

---

## Page 08 History, Device Pack (decision 14)

- **NEW S111** A Device Pack (and its successor, the device-folder export, feature 1 4a) should carry every background layer and its pictures; Import puts them back as they were. Tested. (14) **[D-07-BP]**
- **NEW S112** History Restore of a Button Map save should put back both planes and every picture they use. Tested. (14) **[D-07-BP]**
- **CHANGED S75** old: "Configuration Appearance, Output View Appearance and where the photo sits should come with the pack." new: "Configuration Appearance, Output View Appearance and every background layer should come with the pack." **[D-07-BP]**
- **CHANGED S9** old: "A save that changes only the Button Map's view (zoom, pan, grid, guides, print area) should not be kept." new: add "the faint-foreground choice and the Background opacity slider" to the list. **[D-07-BP]**

## Page 10 Device Library (decision 14)

- **NEW S60** Save to Device Library, Copy to Another Stick and Restore should carry every background layer and its pictures (copied into the receiving device's folder). Tested. (14) **[D-07-BP]**

---

## Glossary (claude/glossary.md)

Core terms (add):
- **Background** — the plane of a Button Map behind everything: pictures, shapes and text, in any number of layers. Not the Print & Export page colour (see Q-P5).
- **Foreground** — the plane in front: chips, groups, leaders, hotspots, tables, and any picture, shape or text not moved to the background.
- **Background mode** — editing the background; the foreground shows faintly and can't be clicked. Entered by Edit Background, the switch, Ctrl+B or the Background row; left by Done or Esc.
- **Move to Background / Move to Foreground** — sends the selected items to the other plane.
- **Show foreground faintly** — the tick in the Background mode banner.
- **Include background** — the Print & Export tick that prints the background plane.

Changed rows:
- Line 84 (Layers kinds): drop "· Photo" from the toggles. **[D-07-BP]**
- Line 75 (file pickers): "Choose Photo" → "Add Picture to Background". **[D-07-BP]**
- Line 125 **Button Map**: "a **hotspot** on the photo for each" → "a **hotspot** on the device's picture for each"; add "drawn on a **background** behind a **foreground**".
- Use/Instead-of row (new): Use **Background**, **Opacity**; instead of "Photo" (for the plane), "Fade", "Move Photo", "Adjust Photo".
- **Photo** kept only in its general sense (the device's picture; Module Setup, Home card, HidHide).

---

## Decision row (claude/decisions.md, draft)

| D-07-BACKGROUND-PLANES | 2026-10-11 | **Background and foreground planes** (A–N, 11–21, all recommended): a Button Map has a background plane (pictures, shapes, text; any number of layers) always behind the foreground (chips and everything else). Background mode (Edit Background, Layers' Background row, the Foreground / Background switch, Ctrl+B; Done / Esc) with a banner and a faint, unclickable foreground; in Foreground mode the background can't be touched. Same tools and Layers controls on both planes; Move to Background / Foreground (Ctrl+Shift+B, one Undo step); snapping within a plane, plus chips to background snap points; one Undo history naming the plane; Print & Export prints both, "Include background"; panning Space + left-drag, middle-drag kept; Look and Opacity on every picture ("Fade" goes); big pictures drawn from a cached copy. "Photo" becomes "Background" where it means the plane. Move Photo, Adjust Photo and the fixed Background photo row go. Old maps: no converter, the old photo read once into a background picture (one-time code). Device Pack / folder export, Device Library, History and Copy Button Map from Device carry every background layer. Built on device folders (D-03-DEVICE-FOLDERS). | User: answers to Feature 2 questions, "all recommended" (2026-10-11). | 07 S11, S14, S26, S30, S34, S36, S39-S44, S57, S62, S76, S83, S87, S89, S94, S102, new S106-S122; 08 S9, S75, new S111-S112; 10 new S60; glossary |

---

## Questions the draft raised

- **Q-P1 Ctrl+B (checked).** Free: no `Ctrl+B` or `Ctrl+Shift+B` in `DialogJoystickButtonMap.qml` (window shortcuts at about lines 3930-4027: Delete, Backspace, Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y, Ctrl+Shift+V, Ctrl+L, Ctrl+Shift+L, Ctrl+G, Ctrl+Shift+G, Ctrl+D, C, V, K, F, F1, S, P, 1, 2, 0), nor in `VkbRigEditor`, `VkbRigFace`, `RigLayersPanel` or the `rig_*.js` files (no `Key_B`). One care point: while a text box is being typed in, Ctrl+B might be expected to mean bold; text boxes have no bold shortcut today.
- **Q-P2 Align and Distribute (checked).** They exist today for the foreground: right-click section "Align and Distribute" (`rig_menu.js:721`, Across / Down / Space Out; `rig_align.js`), so decision 15 applies and S113 is written. Also: Reset Photo is not named in decision N. Recommend it goes with Adjust Photo (each picture already has Reset Crop; no picture has a "reset pose"). Confirm?
- **Q-P3 Undo naming (checked).** Undo steps have no names today (`VkbRigEditor.pushHist()` takes none; `UndoBar` shows only buttons). Decision 16 needs a step name. Recommend: the Undo / Redo tooltips and Edit menu read "Undo: Move picture (Background)"; undoing a Background step while in Foreground mode undoes it without switching mode, and the message line says "Undid a Background change" so the user knows something changed behind.
- **Q-P4 Copy Button Map from Device vs S76.** Today the copy keeps this device's photo; decision 14 says the copy carries every background layer. Copying the EVO L map onto an EVO R would then bring the EVO L picture. Recommend: a tick "Copy the background too" in the copy dialog, unticked for another device, ticked for a template. Or carry it always, as decided?
- **Q-P5 "Background" already used in Print & Export.** The Print & Export **Background** setting (Dark / Light page, S82, S89) clashes with the new plane name and the "Include background" tick. Recommend renaming that setting **Page** (Dark page / Light page).
- **Q-P6 100% scale (S83) and "photo frame" (S60 Fit to Photo Frame, S68).** With many background pictures, which sets 100%? Recommend the bottom background picture. Should "photo frame" be renamed "picture frame" or left (it is a page area, not the plane)? Recommend leave, it's general "photo" sense.
- **Q-P7 The device's photo elsewhere.** Module Setup, Home cards, HidHide and the Xbox page show "the device's photo" (`profilePhotoUrl`). Which background picture is that? Recommend: the bottom background picture; Module Setup's Import Image sets that same layer (one owner, RB1, Q5).
- **Q-P8 Background row's eye.** Decision 11 gives the folded row an opacity slider and 13 a lock; should its eye hide the whole background (view-only, like the slider) or set every layer's hidden flag (saved)? Recommend view-only.
- **Q-P9 Clear Background** asks first? It can be undone, so recommend no question (as Clear Photo today).
- **Q-P10 "First time" hint (21)** is remembered program-wide (one setting), not per device. Confirm.
