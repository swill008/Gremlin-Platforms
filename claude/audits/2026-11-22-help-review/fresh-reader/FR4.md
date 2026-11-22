# FR4: fresh-reader report (2026-11-22)

Help read: qml/help/device_mapping_editor.js (whole chapter), plus searches of
the other chapters for "device map", "device image", "print", "throttle".

## Task 1: printed sheet for my throttle, with a label per button saying what it does

Could do it: with guesses

Steps:
1. Home: right-click the throttle's card, choose **Device Mapping Editor** (device-mapping-editor-open).
2. Choose **File › Edit Mapping** (Ctrl+E) (device-mapping-editor-edit).
3. If the throttle has no picture: guess that I press Ctrl+B, then **Edit › Background › Add Picture to Background…** (Ctrl+I) with a photo of it (device-mapping-editor-background), then Done.
4. Drag each chip from the **Chips** pool onto its button; or press each button (Press to find) so the pool filters to it (device-mapping-editor-select, -chips).
5. **Format › Chip Text › Action** (or Name and action); **Format › Labels Mode** › my mode (device-mapping-editor-action-labels).
6. **File › Save** (Ctrl+S).
7. **File › Print & Export…** (Ctrl+P), Letter/A4, **Page: Light** to save ink, **Print…** (device-mapping-editor-print).

Problems:
- Stuck on where the throttle's picture comes from. device-mapping-editor-about: "a picture of one device with a chip on each control." No topic says whether a new throttle has a picture or how to get one; the answer (Add Picture to Background, Ctrl+I) is buried in Background's "Good to know". Fix: a "Start a map for a new device" step in device-mapping-editor-edit: "No picture yet? Press Ctrl+I to add a photo of the device."
- Guess: is the action text on the printout? device-mapping-editor-action-labels says "The Labels Mode choice is forgotten when the Device Mapping Editor closes." It doesn't say whether Chip Text is kept, needs editing mode, or is what prints. Fix: add "Prints and exports show the chips as they show on screen" and say whether Chip Text is kept with the map.
- Guess: placing 30+ chips one by one. No topic says whether there is a quicker way than dragging each chip (and the throttle's buttons go to the pool unnamed). Fix: one line in device-mapping-editor-chips saying there is (or isn't) a way to place all chips at once; point to templates and Copy Device Map from Device for a similar throttle.
- Confusing wording: device-mapping-editor-chips: "To show its hotspot, choose Hotspot › Hide Hotspot again to turn it off." Reads as hide-to-show. Fix: "To show the hotspot, turn Hotspot › Hide Hotspot off."
- Slow: the print topic's What you see starts with **Custom / Scale / Freeform** before the plain paper case; a first-time printer only needs paper, Page and Print. Fix: move Custom/Freeform under its own "Custom sizes" heading after the preview.

## Task 2: move a label and its leader line, then undo a mistake

Could do it: with guesses

Steps:
1. In editing mode, drag the chip to its new place (device-mapping-editor-chips step 1).
2. To move the line's bend, select the leader and drag a segment (device-mapping-editor-hotspots).
3. To move where the line ends on the throttle, drag the hotspot (device-mapping-editor-hotspots).
4. Undo with **Ctrl+Z** (Edit menu or top of the right-click menu); Redo **Ctrl+Y** (device-mapping-editor-edit).

Problems:
- Guess: does the leader follow the chip? device-mapping-editor-hotspots: "Drag the chip and the hotspot separately." Never says the line stays joined and stretches. Fix: "The leader stays joined to both and stretches as you move either."
- Guess: "spine" is introduced as "a bend point (a spine)" and then the right-click menu lists "add straight or curved spines, convert them, clear them, or branch from an end" with no explanation of curved/branch. Fix: one line each, or drop "spine" and say "bend point" throughout.
- Undo is only described in device-mapping-editor-edit's Good to know; device-mapping-editor-hotspots (the topic I was in) has no mention or link. Fix: add "Ctrl+Z undoes a move" to the hotspots topic's Good to know.

## Task 3: export it as a picture file to share

Could do it: with guesses

Steps:
1. **File › Print & Export…** (Ctrl+P).
2. Optionally set a print area first: Alt+drag (device-mapping-editor-print-area).
3. Choose **Export PNG…** (or JPG); pick Page Dark/Light and Include background.

Problems:
- Guess: do unsaved edits export? device-mapping-editor-options: "Waiting for Save (Cancel takes it back): ... the print area, the print settings". device-mapping-editor-unplugged says an unplugged map "still exports". Neither says whether Export shows the saved map or what is on screen while editing. Fix: one line in device-mapping-editor-print.
- Disagreement: tools-history (tools.js): "the Device Mapping Editor's zoom, guides and print area, aren't kept." device-mapping-editor-print-area: "Print area changes wait for Save." "Aren't kept" reads as "not saved". Fix: in tools.js say "aren't listed in History".
- Missing: where the file goes. No topic says a save dialog asks for the file name and folder. Fix: "Export PNG… asks where to save the file."
- "Scale ... At 100%, the background picture prints at its own resolution" leaves a sharer guessing what size to pick for a forum or Discord post. Fix: give one example ("100% suits a screen; 200% for a sharp print").

## Top 3 problems

1. No path for a device with no picture yet (device-mapping-editor-about / -edit): the first thing a new throttle owner needs is buried in Background's Good to know.
2. Unclear what prints/exports: chip text vs Labels Mode (forgotten on close) and saved vs unsaved edits (device-mapping-editor-action-labels, -print).
3. Leader behaviour when a chip moves is never stated, and "spine" commands go unexplained (device-mapping-editor-hotspots).
