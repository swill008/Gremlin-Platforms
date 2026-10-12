# Photoshop-match batch (PS-MATCH), contract (lead, 2026-10-11 21:05)

User approved (2026-10-11): "I approve of your recommendations" for questions 1-21 (all a).
Rules for this batch from the user: write ALL code first; NO test runs, NO commits until the very end
(the lead runs the tests after every agent has finished). You may WRITE tests, but do not run them.
You may run pyright/lint on Python files you change; do not run pytest, probes or the app.

## The rule above everything (new spec S140)
A picture's handles always sit on the picture's own edges, before, during and after any drag.
Done by: the picture always fills its box exactly (RigDrawItem: Image fillMode Stretch, not
PreserveAspectFit; with a crop, the visible part fills the box). The box IS the picture.

## Behaviour (Photoshop match), the agent that owns it in [brackets]
1. Corner resize keeps the box's proportions AT PRESS (rzX0..rzX1 / rzY0..rzY1 ratio), not a square
   (lockAspect stays only for drawing new shapes with Shift). [RESIZE]
   Applies to pictures AND shapes (Photoshop 2020+: shapes keep proportions too); Shift frees it.
   Text boxes, callouts, tables and lines: unchanged (free; Shift keeps, as today). [RESIZE]
2. Side handles stretch one way only; the picture stretches with the box (falls out of the fill).
   Shift has no effect on side handles. [RESIZE]
3. Alt held on a handle drag: resize from the centre (the centre at press stays put; Shift+Alt free
   from centre). Works unrotated and rotated. Not for crop handles. [RESIZE]
4. Snapping off moves from Alt to Ctrl: a new editor property `snapOffHeld` (bool) = Ctrl held
   during the drag (set on every press/move by RigPointerArea from m.modifiers & ControlModifier).
   Every place that passes `altHeld` / `altOff` to snapEnt/snapPos for SNAPPING now passes
   `snapOffHeld` instead (rig_draw.js [RESIZE], rig_transform.js [XFORM], rig_path.js and
   RigPointerArea.qml [POINTER]). `altHeld` stays a property (Alt = centre / copy / print area).
   Alt+drag on an EMPTY part of the map still draws the print area (unchanged).
5. Alt-drag on an item's body: copies the selection in place (new ids, same plane, above the
   originals, selected) and drags the copies; the whole thing is ONE undo step. [POINTER]
   (Use the existing duplicate code path's helpers in rig_selection.js; ask the lead if you need a
   new helper there - XFORM owns rig_selection.js.)
6. Shift held DURING a move (after the 4 px dead zone, S139) locks the move to horizontal,
   vertical or 45 degrees from the press point. Shift/Ctrl-click at the press still adds/removes
   from the selection (unchanged). [POINTER]
7. Shift+arrow nudges 10 px (the same unit as a plain arrow's 1 px), not the grid step. [POINTER]
8. Line tool, Arrow line tool, line END handles and path segments with Shift: 45 degree steps
   (a constant 45, not rotateSnap). Rotation grips keep rotateSnap (15). Arrow "Tips" handles keep
   rotateSnap. [RESIZE for rig_draw.js lines; POINTER for rig_path.js segments]
9. Drawing a new shape: Alt draws from the centre (the press point is the centre); Shift+Alt a
   perfect shape from the centre. [RESIZE: addDrawShape / drawToolPoint; POINTER passes nothing new,
   altHeld is already set on press/move]
10. Skew: Ctrl+Shift-drag on a SIDE handle skews along that side (top/bottom = skewX,
    left/right = skewY), for items where transformModesFor(n) contains "skew", in any transform
    mode. New function in rig_transform.js: `beginSideSkew(n, handle, mx, my)` and
    `applySideSkew(mx, my)` (same limits as the skew diamonds: +-1.5, under 0.03 snaps to 0).
    [XFORM implements; POINTER dispatches: on press of a side handle with Ctrl+Shift held,
    dragKind = "sideskew" and calls ed.beginSideSkew(...), on move ed.applySideSkew(mx, my)]
11. Crop: Shift on a crop CORNER keeps the crop's proportions at press; Enter finishes crop mode
    (keeps the crop); Esc cancels crop mode and puts the crop back as it was when crop mode was
    entered (no undo step if nothing else changed). New functions in rig_draw.js:
    `finishCrop()` and `cancelCrop()`; toggleCrop() records `cropEnterSnap` (the picture's crop
    when crop mode starts). A flipped picture: dragging the crop side you SEE moves that side
    (swap l/r when flipH, t/b when flipV in cropFromDrag if the code shows they are swapped).
    [RESIZE implements in rig_draw.js / rig_shapes.js; POINTER wires Enter/Esc while ed.cropId]
12. Dragging a resize handle past the opposite edge mirrors the item (toggles flipH for a left/
    right crossing, flipV for top/bottom), like Photoshop; minimum size stays. [RESIZE]
13. Esc during a drag (any dragKind) cancels the drag: everything goes back to how it was at the
    press, no undo step, the selection stays. Esc with no drag running: unchanged.
    New editor function `cancelGesture()` [GROUP implements in VkbRigEditor.qml: restore from
    _gestureSnap without pushing a step, gestureActive=false]; POINTER calls it on Esc when
    ed.dragKind !== "" and then clears dragKind / pointer state.
14. Readout: during a resize, rotate, move or group drag a small box beside the pointer shows
    "W 24.5 %  H 12.0 %" (same units as Properties), "45.0°", or "X +1.2 %  Y −0.5 %". [GROUP,
    VkbRigEditor.qml: computed from the gesture's state; POINTER sets nothing new except calling
    existing functions]. Hidden in prints/exports (S87) like other marks.
15. Cursors: over a resize handle the matching two-headed arrow (SizeHor/SizeVer/SizeFDiag/
    SizeBDiag, picked from the handle's on-screen direction after the item's rotation), over the
    rotate grip a rotate-ish cursor (no Qt rotate cursor exists: use Qt.OpenHandCursor, and say
    so), over a body SizeAll only while dragging. Hover hit test via ed.hitTest on hover. [POINTER]
16. Several selected items: the selection box gets 8 resize handles (besides its rotate handle).
    Corner keeps the box's proportions (Shift frees), side stretches, Alt from centre; each item's
    position and size scale with the box; chips, hotspots and text keep their own size and only
    move; pictures and shapes scale (with a corner they keep their ratio). One undo step.
    New in rig_grouprot.js: `onGroupResizeHandle(mx, my)` -> handle name ("tl","t",...) or "",
    `beginGroupResize(handle, mx, my)`, `dragGroupResize(mx, my)`, `endGroupResize()`. [GROUP
    implements + draws the handles in VkbRigEditor.qml; POINTER dispatches dragKind "groupresize"
    before the group-turn check]
17. Reset Shape on a picture also restores the picture's own proportions, keeping its current
    width and centre: the ratio comes from `ed.pictureAspect(n)` (new editor function: returns the
    image's width/height via the hook `imageAspectFn` the window sets to _hw.imageAspect, or 0
    when unknown -> leave the size). [XFORM in rig_layers.js/rig_transform.js reset code; GROUP adds
    the property `property var imageAspectFn: null` and `function pictureAspect(n)` to
    VkbRigEditor.qml; the LEAD sets imageAspectFn in DialogDeviceMappingEditor.qml]
18. Import Picture passes the picture's aspect (lead, DialogDeviceMappingEditor.qml:2625).
    Choose Picture... (repointPicture) refits the box to the new picture's ratio, keeping width
    and centre: `repointPicture(id, rel, fileUrl, aspect)` gets an optional 4th arg. [DRAWITEM in
    rig_overlays.js; the lead passes _hw.imageAspect(rel) from the window]
19. Handles: centred exactly on edges/corners at every UI scale (offset = -size/2 using the same
    Style.dp value), rotate knob and transform diamonds likewise; hit radii scale with Style.dp
    (use the editor's existing scale value, e.g. a `handleHit` helper). [DRAWITEM: RigDrawItem.qml
    + rig_hit.js]
20. Skewed items: hit tests for the 8 handles and the rotate grip undo the skew on the pointer
    first (as drawLocalPoint already does with _unskew) [DRAWITEM, rig_hit.js]; the resize maths
    for a skewed item works in unskewed space so the drawn handle stays under the pointer
    [RESIZE, rig_draw.js].
21. Properties: a link button between Width and Height, ON by default (editor property
    `linkSize: true`, not saved per item, remembered with the window's UI prefs if that is easy,
    else session only). With it on, changing Width (or Height) scales the other by the item's
    current ratio. Tooltip "Keep proportions". [PROPS in rig_props.js + RigPropsPanel.qml; GROUP
    adds `property bool linkSize: true` to VkbRigEditor.qml]

## Editor forwarders (VkbRigEditor.qml, owned by GROUP)
GROUP adds, at once at the start, these properties/forwarders so others can call `ed.<name>`:
  property bool snapOffHeld: false
  property bool linkSize: true
  property var imageAspectFn: null
  property var cropEnterSnap: null
  function pictureAspect(n)
  function cancelGesture()
  function finishCrop() { return RigDraw.finishCrop() }
  function cancelCrop() { return RigDraw.cancelCrop() }
  function beginSideSkew(n, h, x, y) { return RigTransform.beginSideSkew(n, h, x, y) }
  function applySideSkew(x, y) { return RigTransform.applySideSkew(x, y) }
  function onGroupResizeHandle(x, y), beginGroupResize(h, x, y), dragGroupResize(x, y),
  endGroupResize()  -> RigGroupRot
  plus any other forwarder another agent's report asks for.
State the agents need on the editor (rzX0.. etc.) already exists.

## Spec (DOCS writes; page 07)
New statements S140-S151 (one per behaviour group above, wording from the lead's list) and changes to
statements that state the old keys (Alt skips snapping; Shift+arrow grid step; Shift 15 degree lines;
shape corner free). Help (qml/help/device_mapping_editor.js) and the Shortcuts window rows (lead).
