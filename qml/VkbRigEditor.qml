// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style
import Gremlin.Menus as Menus
import "rig_coords.js" as RigCoords
import "rig_style.js" as RigStyle
import "rig_snap.js" as RigSnap
import "rig_chips.js" as RigChips
import "rig_leaders.js" as RigLeaders
import "rig_hit.js" as RigHit
import "rig_groups.js" as RigGroups
import "rig_text.js" as RigText
import "rig_tables.js" as RigTables
import "rig_overlays.js" as RigOverlays
import "rig_draw.js" as RigDraw
import "rig_selection.js" as RigSelection
import "rig_pointer.js" as RigPointer
import "rig_menu.js" as RigMenu
import "rig_layers.js" as RigLayers
import "rig_props.js" as RigProps
import "rig_align.js" as RigAlign
import "rig_find.js" as RigFind
import "rig_mirror.js" as RigMirror
import "rig_grouprot.js" as RigGroupRot
import "rig_callout.js" as RigCallout
import "rig_path.js" as RigPath
import "rig_styles.js" as RigStyles
import "rig_rulers.js" as RigRulers
import "rig_print_area.js" as RigPrintJs
import "rig_transform.js" as RigTransform
import "rig_hotspot.js" as RigHotspot
import "rig_commands.js" as RigCommands

Item {
    id: _ed

    property var face: null
    property var nodes: []
    property string selectedId: ""
    property int selectedSpine: -1
    property string dragKind: ""
    property int dragSpine: -1
    property real dragOffX: 0
    property real dragOffY: 0
    property int tick: 0
    // While items are dragged only they follow: liveTick moves them, the
    // global tick stays (each pointer move used to redraw every item: about
    // 165 ms a move with 330 items). liveIds: the dragged items' ids.
    property var liveIds: ({})
    property int liveTick: 0
    // For what is drawn over the items (selection, handles, guides): both.
    readonly property int anyTick: tick + liveTick
    // The dragged items' leaders, and leaders ending on their hotspots: drawn
    // on their own canvas while dragging (redrawing every leader on each
    // pointer move cost about 120 ms on a big map).
    property var liveLeaderIds: ({})

    function paintLeaders() {
        if (_lines)
            _lines.requestPaint()
        if (_liveLines)
            _liveLines.requestPaint()
    }
    property bool seeded: false
    property bool interactive: false
    // A picture of the page is being taken: no selection, handles, grid or
    // guides. showChrome is what visual parts check instead of interactive.
    property bool exporting: false
    readonly property bool showChrome: interactive && !exporting
    // Export on a light page for printing: colours drawn through ink().
    property bool printLight: false
    // How much larger than on screen this editor draws (RigRenderer's copy
    // for a print or export; 1 on screen). Sizes kept in plain pixels (line
    // widths, borders) go through fixPx, so the picture keeps the screen's
    // proportions at any size.
    property real exportZoom: 1
    // Printing and exporting: pictures over about 4000 px are drawn from the
    // original instead of a screen-sized copy (07 S124; RigDrawItem).
    property bool fullResolution: false
    function fixPx(v) { return v * exportZoom }
    // Turning several items together (rig_grouprot.js): where they started,
    // and the angle so far.
    property var turnStart: null
    property real turnAngle: 0
    // Resizing several items by the selection box (rig_grouprot.js, 07
    // S153): the handle, the press, the box and each item at the press.
    property var groupRz: null
    readonly property real groupHandleSize: Style.dp(8)
    // The Path and Freehand tools' points so far (editor pixels), and the
    // pointer for the Path tool's next segment.
    property var pathDraft: []
    property var pathHover: null
    // Saved styles (Device Map Options → Library), from the window.
    property var savedStyles: []
    // Guides dragged out of the rulers, as page fractions (rig_rulers.js).
    property var rulerGuidesX: []
    property var rulerGuidesY: []
    property bool guidesOn: true
    property var guideDrag: null
    // The window's pool panel: poolHit(wx, wy) says whether a window point
    // is over it; poolHover is on while a dragged chip is over it.
    property var poolHit: null
    property bool poolHover: false
    // The selected drawing's handles (rig_transform.js): resize, shape, tips,
    // skew or bend. Back to resize whenever the selection changes.
    property string transformMode: "resize"
    // Hotspot pulses (rig_hotspot.js): when each pulse started, and which
    // controls were held at the last live update.
    property var hotPulseAt: ({})
    property var hotHeld: ({})
    property var selectedIds: []
    property bool banding: false
    property bool bandAdd: false
    property real bandX0: 0
    property real bandY0: 0
    property real bandX1: 0
    // The print area (rig_print_area.js): the page's part every export
    // takes ({fx, fy, fw, fh}, or null: the whole page), whether its frame
    // shows, whether it can be changed, its color, Set Print Area waiting
    // for a drag, and the area being drawn.
    property var printArea: null
    property bool printAreaShown: false
    // "" until the window sets it (Options' color, or the default red); a
    // plain value, not a binding, as the window replaces it.
    property string printAreaColor: ""
    property bool printAreaArm: false
    // The print area's shape (width / height) on the chosen paper, or 0:
    // any shape (Print & Export's "Freeform (As Drawn)").
    property real printAspect: 0
    property real eaX0: 0
    property real eaY0: 0
    property real eaX1: 0
    property real eaY1: 0
    property real bandY1: 0
    property bool gridOn: true
    property bool snapOn: true
    property bool snapEntOn: true
    property real guideX: -1
    property real guideY: -1
    property string guideXKind: ""
    property string guideYKind: ""
    property int gridSize: 200
    property bool altHeld: false
    property bool shiftHeld: false
    // Ctrl held during a drag: snapping off (07 S142; Alt is centre / copy).
    property bool snapOffHeld: false
    // Properties' Width/Height link (07 S155): on, one scales the other.
    property bool linkSize: true
    // The window's hook: fn(rel) -> a picture's width / height, or 0.
    property var imageAspectFn: null
    // The picture's crop when crop mode started (Esc puts it back, S148).
    property var cropEnterSnap: null
    property string groupEditId: ""
    property int selectedMember: -1
    property int dragMember: -1
    property string renameId: ""
    property int renameMember: -1
    property int tableRow: -1
    property int tableCol: -1
    property int tableExtra: -1
    property string packWarn: ""
    // The page and its photo frame as hardware_profile.PAGE_SIZE (07 S68):
    // the frame is the middle photoWellFraction of the page.
    readonly property real worldPageW: 32000
    readonly property real worldPageH: 18000
    readonly property real photoWellFraction: 0.75
    readonly property real innerPageW: worldPageW * photoWellFraction
    readonly property real innerPageH: worldPageH * photoWellFraction
    readonly property real innerPadX: (1 - photoWellFraction) / 2
    readonly property real innerPadY: (1 - photoWellFraction) / 2
    readonly property real uiRefW: 1600
    readonly property real uiScale: {
        var s = Math.min(width / Math.max(1, worldPageW), height / Math.max(1, worldPageH))
        var sw = worldPageW * s
        if (sw < 8)
            return 1
        return sw / uiRefW
    }
    readonly property string worldSpace: "world"
    property var textFormatClip: null
    property bool textPaintOn: false
    property string renameDraft: ""
    property string armRenameId: ""
    property int armRenameMember: -1
    property int selectedLeader: 0
    property int selectedSeg: -1
    property int dragLeader: 0
    property string drawTool: ""
    property bool plantSnap: false
    property string overlayHoverId: ""
    property string hoverHwLabel: ""
    property real hoverTipX: 0
    property real hoverTipY: 0
    property real drawX0: 0
    property real drawY0: 0
    property real drawX1: 0
    property real drawY1: 0
    property real rzX0: 0
    property real rzY0: 0
    property real rzX1: 0
    property real rzY1: 0
    // The items Ctrl+C copied (it was named clip, which hid Item.clip).
    property var copiedNodes: []
    property bool lineArm: false
    property real lineArmX: 0
    property real lineArmY: 0
    property bool spineHoldArm: false
    property string spineHoldId: ""
    property int spineHoldLeader: 0
    property int spineHoldIndex: -1
    property real spineHoldX: 0
    property real spineHoldY: 0
    // How far above a selected drawing's top edge its rotate handle sits.
    readonly property real rotateHandleOffset: 24
    // The picture in crop mode (its handles cut), and its crop when a handle
    // drag began.
    property string cropId: ""
    property var cropStart: null
    // Set by the window: the clipboard holds a picture to paste.
    property bool canPastePicture: false
    // The system clipboard's change count (set by the window) and its value
    // at the last chip copy: Ctrl+V pastes whichever was copied last.
    property int clipboardSerial: 0
    property int clipSerial: -1
    signal pastePictureRequested()
    // Selection and handle colours, the same on the photo in both themes.
    readonly property color handleFill: "#FBBF24"
    readonly property color handleInk: "#18181B"
    // The planes (07 S111-S122): which one is being edited ("foreground" or
    // "background"); in Background mode the foreground shows at fgFaint when
    // showFgFaint, else not at all (S115). In Foreground mode the Background
    // row's eye (bgViewHidden) and Opacity (bgViewOpacity) change how the
    // background shows on screen (S120). All are program settings set by the
    // window: never saved in the map, never undo steps (P4a).
    property string editPlane: "foreground"
    property bool showFgFaint: true
    property real fgFaint: 0.25
    property bool bgViewHidden: false
    property real bgViewOpacity: 1
    // Set by the window: function (srcUrl, look) giving an adjusted copy of a
    // picture for its look (HardwareProfile.adjustedPhotoUrl), kept in the
    // node's lookUrl (never saved). null: no adjusted copies.
    property var lookUrlFor: null
    // Move to Background / Foreground moved count items (S121): the window
    // says "Moved to Background" (or Foreground) with Undo.
    signal planeMoved(string plane, int count)
    signal selectedChanged()
    // Any press on the map (the window hides its unpinned tools).
    signal mapPressed()
    // The print area was drawn (drawn: a new one, show it) or changed.
    signal printAreaEdited(bool drawn)
    signal chipMenuRequested(real x, real y)
    signal overlayImportRequested()
    // Choose Picture… on a picture whose file is missing (07 S108).
    signal choosePictureRequested(string nodeId)
    signal historyChanged()
    signal colorPickRequested(string field, string hex)
    // Press to find: a pressed control that has no chip on the map.
    signal findNotPlaced(string label)
    // Save this style: the window asks for a name.
    signal saveStyleRequested(string kind, string fieldsJson)
    // A ruler guide was added, dropped or removed: the window saves them.
    signal rulerGuidesEdited()
    // Right-click additions (07 S136, S137): Show in Layers and Properties…
    // ask the window; the menu's ☆ and × change the program's Favourites
    // (the window keeps them in its settings).
    signal showInLayersRequested(string id)
    signal propertiesRequested()
    signal favouriteToggled(string id)
    signal favouriteRemoved(string id)
    // The last command with an id that ran (Repeat), the Favourites (command
    // ids, in the order added; set by the window) and how many the menu shows.
    property string lastCommandId: ""
    property var favourites: []
    property int favouritesShown: 5

    // The command list (rig_commands.js), for rig_menu.js and the window.
    function _cmds() { return (typeof RigCommands !== "undefined") ? RigCommands : null }
    function cmdApplies(id) {
        var c = _cmds()
        return !!(c && typeof c.applies === "function" && c.applies(_ed, id))
    }
    function cmdInfo(id) {
        var c = _cmds()
        return (c && typeof c.info === "function") ? c.info(_ed, id) : { id: id, text: id, key: "" }
    }
    function cmdRun(id) {
        var c = _cmds()
        if (c && typeof c.run === "function")
            return c.run(_ed, id)
    }
    function cmdRepeatLabel() {
        var c = _cmds()
        return (c && typeof c.repeatLabel === "function") ? c.repeatLabel(_ed) : ""
    }
    function cmdCanRepeat() {
        var c = _cmds()
        return !!(c && typeof c.canRepeat === "function" && c.canRepeat(_ed))
    }
    function cmdRepeat() {
        var c = _cmds()
        if (c && typeof c.repeat === "function")
            return c.repeat(_ed)
    }

    property var hist
    property int histAt: -1
    property int histCap: 80
    // Degrees per Shift step when turning an item or drawing a line (Options).
    property int rotateSnap: 15
    // Press to find (Device Map Options → Editing).
    property bool findOn: true
    property bool findAxes: false
    property var findPrev: ({})
    property string findMsg: ""
    // Chip text (Device Map Options → Labels) and the window's labels for
    // the chosen mode: {"btn:5": "Gear up"}.
    property string chipTextMode: "Name"
    property string unboundText: "Name"
    property var actionLabels: ({})
    property bool _restoring: false
    // The state after the latest edit of a run still waiting for its pause
    // (nudges, live edits): that run's undo step (S55).
    property string _runSnap: ""
    readonly property bool canUndo: histAt > 0
    readonly property bool canRedo: histAt >= 0 && hist && histAt < hist.length - 1

    // Do NOT declare signal nodesChanged — property var nodes already has it.

    // Page coordinates (rig_coords.js)
    function spaceRect() { return RigCoords.spaceRect() }
    function innerPageRect() { return RigCoords.innerPageRect() }
    function clamp01(v) { return RigCoords.clamp01(v) }
    function worldToX(wx) { return RigCoords.worldToX(wx) }
    function worldToY(wy) { return RigCoords.worldToY(wy) }
    function xToWorld(px) { return RigCoords.xToWorld(px) }
    function yToWorld(py) { return RigCoords.yToWorld(py) }
    function fxToX(fx) { return RigCoords.fxToX(fx) }
    function fyToY(fy) { return RigCoords.fyToY(fy) }
    function xToFx(px) { return RigCoords.xToFx(px) }
    function yToFy(py) { return RigCoords.yToFy(py) }
    function fwToW(fw) { return RigCoords.fwToW(fw) }
    function fhToH(fh) { return RigCoords.fhToH(fh) }

    // Chip, hotspot and leader styling (rig_style.js)
    function isStyleKey(key) { return RigStyle.isStyleKey(key) }
    function ink(c) { return RigStyle.ink(c) }
    function targetMember() { return RigStyle.targetMember() }
    function styleVal(n, mem, key, fallback) { return RigStyle.styleVal(n, mem, key, fallback) }
    function applyField(key, val) { return RigStyle.applyField(key, val) }
    function applyFieldLive(key, val) { return RigStyle.applyFieldLive(key, val) }
    function fieldEq(key, val, fallback) { return RigStyle.fieldEq(key, val, fallback) }
    function styleDefault(key) { return RigStyle.styleDefault(key) }
    function pickColor(field) { return RigStyle.pickColor(field) }
    function uiPx(px) { return RigStyle.uiPx(px) }
    function leaderWidthOf(n) { return RigStyle.leaderWidthOf(n) }
    function resetMemberStyle() { return RigStyle.resetMemberStyle() }

    // Grid snapping, snapping to other items, and the alignment guides (rig_snap.js)
    function snapWorld(w) { return RigSnap.snapWorld(w) }
    function snapPx(v) { return RigSnap.snapPx(v) }
    function nodeBox(n) { return RigSnap.nodeBox(n) }
    function clearMoveGuides() { return RigSnap.clearMoveGuides() }
    function guideSkipTarget(moving, other) { return RigSnap.guideSkipTarget(moving, other) }
    function updateMoveGuides(n) { return RigSnap.updateMoveGuides(n) }
    function commitGuideSnap() { return RigSnap.commitGuideSnap() }
    function snapPos(x, y, altOff) { return RigSnap.snapPos(x, y, altOff) }
    function snapEnt(x, y, altOff) { return RigSnap.snapEnt(x, y, altOff) }

    // Chips (rig_chips.js)
    function nodeAt(id) { return RigChips.nodeAt(id) }
    function nodeIndex(id) { return RigChips.nodeIndex(id) }
    function destOf(kind, hwId) { return RigChips.destOf(kind, hwId) }
    function memberKind(n, mem) { return RigChips.memberKind(n, mem) }
    function leafKind(kind) { return RigChips.leafKind(kind) }
    function hardwareLabel(kind, hwId) { return RigChips.hardwareLabel(kind, hwId) }
    function defaultFriendly(kind, hwId) { return RigChips.defaultFriendly(kind, hwId) }
    function isClearedFriendly(v) { return RigChips.isClearedFriendly(v) }
    function isUserFriendly(kind, hwId, v) { return RigChips.isUserFriendly(kind, hwId, v) }
    function carryFriendly(v, fallback) { return RigChips.carryFriendly(v, fallback) }
    function friendlyOf(n, mem) { return RigChips.friendlyOf(n, mem) }
    function fullNameOf(kind, hwId) { return RigChips.fullNameOf(kind, hwId) }
    function placedId(kind, hwId) { return RigChips.placedId(kind, hwId) }
    function chipText(n, mem) { return RigChips.chipText(n, mem) }
    function chipRows(n, mem) { return RigChips.chipRows(n, mem) }
    function chipRowsApart(n, mem) { return RigChips.chipRowsApart(n, mem) }
    function chipRowAlign(n, mem, row) { return RigChips.chipRowAlign(n, mem, row) }
    function oneLine(s) { return RigChips.oneLine(s) }
    function catalog() { return RigChips.catalog() }
    function hotFxOf(n) { return RigChips.hotFxOf(n) }
    function hotFyOf(n) { return RigChips.hotFyOf(n) }
    function addChiplet(kind, hwId, wx, wy, chipOnly) { return RigChips.addChiplet(kind, hwId, wx, wy, chipOnly) }
    function ensureFriendly(n) { return RigChips.ensureFriendly(n) }
    function litOf(kind, hwId) { return RigChips.litOf(kind, hwId) }
    function chipXY(n) { return RigChips.chipXY(n) }
    function pinPt(n, item, side) { return RigChips.pinPt(n, item, side) }
    function chipH(n, mem) { return RigChips.chipH(n, mem) }
    function isCircle(n, mem) { return RigChips.isCircle(n, mem) }
    function circleFont(n, mem) { return RigChips.circleFont(n, mem) }
    function chipR(n, h, mem) { return RigChips.chipR(n, h, mem) }
    function chipIsHollow(n, mem) { return RigChips.chipIsHollow(n, mem) }
    function hotSz(n) { return RigChips.hotSz(n) }
    function chipBounds(n) { return RigChips.chipBounds(n) }
    function hoverLabelAt(mx, my) { return RigChips.hoverLabelAt(mx, my) }
    function setChipTip(mx, my) { return RigChips.setChipTip(mx, my) }
    function chipScreenRect(n, mem) { return RigChips.chipScreenRect(n, mem) }
    function beginRename(id, memberIndex) { return RigChips.beginRename(id, memberIndex) }
    function commitRename() { return RigChips.commitRename() }
    function cancelRename() { return RigChips.cancelRename() }
    function chipWGuess(n, mem) { return RigChips.chipWGuess(n, mem) }

    // The middle of the view as a page point.
    function viewCenterPage() { return Qt.point(xToFx(width * 0.5), yToFy(height * 0.5)) }

    // Leader lines (rig_leaders.js)
    function hotPt(n) { return RigLeaders.hotPt(n) }
    function fromEnd(n) { return RigLeaders.fromEnd(n) }
    function toEnd(n) { return RigLeaders.toEnd(n) }
    function endPt(end) { return RigLeaders.endPt(end) }
    function _legacyLeader(n) { return RigLeaders._legacyLeader(n) }
    function leaderList(n) { return RigLeaders.leaderList(n) }
    function ensureLeaders(n) { return RigLeaders.ensureLeaders(n) }
    function currentLeader(n) { return RigLeaders.currentLeader(n) }
    function hollowMarkPad(end) { return RigLeaders.hollowMarkPad(end) }
    function pullToCircle(prev, center, r) { return RigLeaders.pullToCircle(prev, center, r) }
    function pullToBox(prev, center, hw, hh) { return RigLeaders.pullToBox(prev, center, hw, hh) }
    function clipHollowEnd(prev, tip, end) { return RigLeaders.clipHollowEnd(prev, tip, end) }
    function pathPtsL(L) { return RigLeaders.pathPtsL(L) }
    function pathPts(n) { return RigLeaders.pathPts(n) }
    function segIsCurve(L, j) { return RigLeaders.segIsCurve(L, j) }
    function setSegCurve(L, j, on) { return RigLeaders.setSegCurve(L, j, on) }
    function toggleSegCurve() { return RigLeaders.toggleSegCurve() }
    function setAllSegCurve(on) { return RigLeaders.setAllSegCurve(on) }
    function addLeader() { return RigLeaders.addLeader() }
    function addBranch() { return RigLeaders.addBranch() }
    function stripLeaders(n) { return RigLeaders.stripLeaders(n) }
    function deleteLeader() { return RigLeaders.deleteLeader() }
    function showLeaderHandles(n, li) { return RigLeaders.showLeaderHandles(n, li) }
    function drawMark(ctx, x, y, size, shape, fill, color) { return RigLeaders.drawMark(ctx, x, y, size, shape, fill, color) }
    function nearestPin(item, mx, my) { return RigLeaders.nearestPin(item, mx, my) }
    function attachNear(x, y, opts) { return RigLeaders.attachNear(x, y, opts) }
    function detachEnd(which) { return RigLeaders.detachEnd(which) }
    function attachEndToSelf(which) { return RigLeaders.attachEndToSelf(which) }
    function _clampPt(pts, i) { return RigLeaders._clampPt(pts, i) }
    function _bezierCtrl(pts, i) { return RigLeaders._bezierCtrl(pts, i) }
    function strokeLeader(ctx, n, pts, L) { return RigLeaders.strokeLeader(ctx, n, pts, L) }
    function ensureMidSpine(n) { return RigLeaders.ensureMidSpine(n) }
    function addCurveSpine(n) { return RigLeaders.addCurveSpine(n) }
    function _nearLeader(n, mx, my) { return RigLeaders._nearLeader(n, mx, my) }
    function _distBezier(mx, my, pts, j) { return RigLeaders._distBezier(mx, my, pts, j) }
    function _distSeg(px, py, x1, y1, x2, y2) { return RigLeaders._distSeg(px, py, x1, y1, x2, y2) }
    function clearAllSpines(id) { return RigLeaders.clearAllSpines(id) }
    function addSpineAt(id, mx, my, forceCurve) { return RigLeaders.addSpineAt(id, mx, my, forceCurve) }
    function deleteSpineAt(id, leader, index) { return RigLeaders.deleteSpineAt(id, leader, index) }
    function convertSelectedSpine() { return RigLeaders.convertSelectedSpine() }

    // Hit testing (rig_hit.js)
    function hitTest(mx, my) { return RigHit.hitTest(mx, my) }
    function hitDraw(n, mx, my) { return RigHit.hitDraw(n, mx, my) }
    function memberHit(n, mx, my) { return RigHit.memberHit(n, mx, my) }
    function rectHitsBand(r, x0, y0, x1, y1) { return RigHit.rectHitsBand(r, x0, y0, x1, y1) }
    function tableHitsBand(n, x0, y0, x1, y1) { return RigHit.tableHitsBand(n, x0, y0, x1, y1) }
    function tablesUnderChips(chips) { return RigHit.tablesUnderChips(chips) }
    function selectBand(add) { return RigHit.selectBand(add) }

    // Groups and 5-way formats (rig_groups.js)
    function groupAlignH(n) { return RigGroups.groupAlignH(n) }
    function setAlignH(mode) { return RigGroups.setAlignH(mode) }
    function bakeAlignToFree(n) { return RigGroups.bakeAlignToFree(n) }
    function memberPageFx(n, mem) { return RigGroups.memberPageFx(n, mem) }
    function memberPageFy(n, mem) { return RigGroups.memberPageFy(n, mem) }
    function memberIndexOf(n, mem) { return RigGroups.memberIndexOf(n, mem) }
    function stackPitch(n) { return RigGroups.stackPitch(n) }
    function memberLocalX(n, mem) { return RigGroups.memberLocalX(n, mem) }
    function memberLocalY(n, mem) { return RigGroups.memberLocalY(n, mem) }
    function memberHomeX(n, mem) { return RigGroups.memberHomeX(n, mem) }
    function memberHomeY(n, mem) { return RigGroups.memberHomeY(n, mem) }
    function groupMinX(n) { return RigGroups.groupMinX(n) }
    function groupMinY(n) { return RigGroups.groupMinY(n) }
    function groupSpanW(n) { return RigGroups.groupSpanW(n) }
    function groupSpanH(n) { return RigGroups.groupSpanH(n) }
    function isGroup(n) { return RigGroups.isGroup(n) }
    function isFiveWay(n) { return RigGroups.isFiveWay(n) }
    function fiveWayFormat(n) { return RigGroups.fiveWayFormat(n) }
    function memberHasOverride(mem) { return RigGroups.memberHasOverride(mem) }
    function clearGroupFormat() { return RigGroups.clearGroupFormat() }
    function fiveWayRole(mem) { return RigGroups.fiveWayRole(mem) }
    function fiveWayCaption(n) { return RigGroups.fiveWayCaption(n) }
    function captionH(n) { return RigGroups.captionH(n) }
    function themeLayout(n) { return RigGroups.themeLayout(n) }
    function ensureFiveWayRoles(n) { return RigGroups.ensureFiveWayRoles(n) }
    function roleWord(r) { return RigGroups.roleWord(r) }
    function systemName(n, mem) { return RigGroups.systemName(n, mem) }
    function memberHasCustomName(n, mem) { return RigGroups.memberHasCustomName(n, mem) }
    function memberLabel(n, mem) { return RigGroups.memberLabel(n, mem) }
    function memByRole(n, role) { return RigGroups.memByRole(n, role) }
    function themeGap(n) { return RigGroups.themeGap(n) }
    function themeGeom(n) { return RigGroups.themeGeom(n) }
    function themeCell(n) { return RigGroups.themeCell(n) }
    function clearThemeMemberLayout(n) { return RigGroups.clearThemeMemberLayout(n) }
    function applyFiveWayFormat(fmt) { return RigGroups.applyFiveWayFormat(fmt) }
    function resetFiveWayFormat() { return RigGroups.resetFiveWayFormat() }
    function buildRadialLeaders(n) { return RigGroups.buildRadialLeaders(n) }
    function beginGroupEdit(id) { return RigGroups.beginGroupEdit(id) }
    function endGroupEdit() { return RigGroups.endGroupEdit() }
    function ensureMemberOffsets(n) { return RigGroups.ensureMemberOffsets(n) }
    function demoteSpecialKinds() { return RigGroups.demoteSpecialKinds() }
    function canGroup() { return RigGroups.canGroup() }
    function canUngroup() { return RigGroups.canUngroup() }
    function _uid(prefix) { return RigGroups._uid(prefix) }
    function _styleOf(n) { return RigGroups._styleOf(n) }
    function _partsFrom(n) { return RigGroups._partsFrom(n) }
    function groupSelection() { return RigGroups.groupSelection() }
    function ungroupSelection() { return RigGroups.ungroupSelection() }
    function setGroupKind(kind) { return RigGroups.setGroupKind(kind) }

    // Text boxes (rig_text.js)
    function textThemeStyle(n) { return RigText.textThemeStyle(n) }
    function textFormatKeys() { return RigText.textFormatKeys() }
    function copyTextFormat() { return RigText.copyTextFormat() }
    function applyTextFormat(id) { return RigText.applyTextFormat(id) }
    function clearTextFormat() { return RigText.clearTextFormat() }
    function fitTextBox(n) { return RigText.fitTextBox(n) }
    function copyTextPlain() { return RigText.copyTextPlain() }
    function applyTextBoxSize(pw, ph) { return RigText.applyTextBoxSize(pw, ph) }
    function textBoxSizeEq(pw, ph) { return RigText.textBoxSizeEq(pw, ph) }
    function applyTextTheme(theme) { return RigText.applyTextTheme(theme) }
    function beginTextRename(id) { return RigText.beginTextRename(id) }

    // Tables (rig_tables.js)
    function emptyTableRow(cols) { return RigTables.emptyTableRow(cols) }
    function ensureTable(n) { return RigTables.ensureTable(n) }
    function tableMinW(n) { return RigTables.tableMinW(n) }
    function tableMinH(n) { return RigTables.tableMinH(n) }
    function tableHomeRect(n, row, col) { return RigTables.tableHomeRect(n, row, col) }
    function fitTableRow(n, row) { return RigTables.fitTableRow(n, row) }
    function tableGetCell(n, row, col) { return RigTables.tableGetCell(n, row, col) }
    function tableCellIsFree(n, row, col) { return RigTables.tableCellIsFree(n, row, col) }
    function tableExtraAt(n, i) { return RigTables.tableExtraAt(n, i) }
    function tablePartWorldRect(n, cell, fallback) { return RigTables.tablePartWorldRect(n, cell, fallback) }
    function writeTablePartRect(n, cell, x, y, w, h) { return RigTables.writeTablePartRect(n, cell, x, y, w, h) }
    function setTableCellIndependent(on) { return RigTables.setTableCellIndependent(on) }
    function tableCellHandlesOn(n) { return RigTables.tableCellHandlesOn(n) }
    function tableExtraRect(n, i) { return RigTables.tableExtraRect(n, i) }
    function tableCurrentCell(n) { return RigTables.tableCurrentCell(n) }
    function tableHasTarget() { return RigTables.tableHasTarget() }
    function tableTargetValid() { return RigTables.tableTargetValid() }
    function resetTableTarget() { return RigTables.resetTableTarget() }
    function tableCurrentRect(n) { return RigTables.tableCurrentRect(n) }
    function tableCellRect(n, row, col) { return RigTables.tableCellRect(n, row, col) }
    function tableCellAt(n, mx, my) { return RigTables.tableCellAt(n, mx, my) }
    function setTableCellFree(on) { return RigTables.setTableCellFree(on) }
    function toggleTableCellFree() { return RigTables.toggleTableCellFree() }
    function placeTableCell(where) { return RigTables.placeTableCell(where) }
    function spawnEmptyCell() { return RigTables.spawnEmptyCell() }
    function deleteThisTableCell() { return RigTables.deleteThisTableCell() }
    function tableCellStyle(n, col) { return RigTables.tableCellStyle(n, col) }
    function tableCellText(n, row, col) { return RigTables.tableCellText(n, row, col) }
    function addTableRow(below) { return RigTables.addTableRow(below) }
    function deleteTableRow() { return RigTables.deleteTableRow() }
    function addTableCol(right) { return RigTables.addTableCol(right) }
    function deleteTableCol() { return RigTables.deleteTableCol() }
    function toggleTableIdCol() { return RigTables.toggleTableIdCol() }
    function setTableTheme(name) { return RigTables.setTableTheme(name) }
    function setTableFont(sz) { return RigTables.setTableFont(sz) }
    function deleteTable() { return RigTables.deleteTable() }
    function beginTableRename(id, row, col, extra) { return RigTables.beginTableRename(id, row, col, extra) }
    function applyTableCellResize(n, mx, my, handle, altOff) { return RigTables.applyTableCellResize(n, mx, my, handle, altOff) }
    function attachChipToTable(table, chip) { return RigTables.attachChipToTable(table, chip) }
    function followTablePacked(table) { return RigTables.followTablePacked(table) }
    function attachDrawToTable(table, draw) { return RigTables.attachDrawToTable(table, draw) }
    function tablePackOf(n) { return RigTables.tablePackOf(n) }
    function shiftIndependentParts(table, dFx, dFy) { return RigTables.shiftIndependentParts(table, dFx, dFy) }
    function moveTablePack(table, dFx, dFy) { return RigTables.moveTablePack(table, dFx, dFy) }
    function refreshChipPack(chip) { return RigTables.refreshChipPack(chip) }
    function detachChipFromTable(chip) { return RigTables.detachChipFromTable(chip) }
    function detachTablePacked(table) { return RigTables.detachTablePacked(table) }
    function tableIsPacked(n) { return RigTables.tableIsPacked(n) }
    function packTableFromSelection() { return RigTables.packTableFromSelection() }

    // Image layers (overlays) (rig_overlays.js)
    function isOverlay(n) { return RigOverlays.isOverlay(n) }
    function isPinnable(n) { return RigOverlays.isPinnable(n) }
    function isLocked(n) { return RigOverlays.isLocked(n) }
    function pinLocal() { return RigOverlays.pinLocal() }
    function hitOverlayPin(n, mx, my) { return RigOverlays.hitOverlayPin(n, mx, my) }
    function overlayContains(n, mx, my) { return RigOverlays.overlayContains(n, mx, my) }
    function setOverlayHover(mx, my) { return RigOverlays.setOverlayHover(mx, my) }
    function addOverlay(rel, fileUrl, opts) { return RigOverlays.addOverlay(rel, fileUrl, opts) }
    function repointPicture(id, rel, fileUrl, aspect) { RigOverlays.repointPicture(id, rel, fileUrl, aspect) }
    function pinTarget(id) { return RigOverlays.pinTarget(id) }
    function toggleLock(id) { return RigOverlays.toggleLock(id) }
    function beginPlantSnap() { return RigOverlays.beginPlantSnap() }
    function addSocketAt(n, mx, my) { return RigOverlays.addSocketAt(n, mx, my) }
    function socketWorld(n, sock) { return RigOverlays.socketWorld(n, sock) }
    function syncOverlayChips(n) { return RigOverlays.syncOverlayChips(n) }
    function unsnapChip(chipId) { return RigOverlays.unsnapChip(chipId) }
    function snapChipToSocket(chipId, mx, my) { return RigOverlays.snapChipToSocket(chipId, mx, my) }
    function clearSockets() { return RigOverlays.clearSockets() }
    function frameFit(aspect) { return RigOverlays.frameFit(aspect) }
    function socketNear(mx, my) { return RigOverlays.socketNear(mx, my) }
    function socketChipIds(n) { return RigOverlays.socketChipIds(n) }

    // Drawings (rig_draw.js)
    function isDraw(n) { return RigDraw.isDraw(n) }
    function isTable(n) { return RigDraw.isTable(n) }
    function isText(n) { return RigDraw.isText(n) }
    function drawGeom(n) { return RigDraw.drawGeom(n) }
    function shapeOutlinePts(n, w, h) { return RigDraw.shapeOutlinePts(n, w, h) }
    function applyDrawResize(n, mx, my, handle, altOff) { return RigDraw.applyDrawResize(n, mx, my, handle, altOff) }
    function _drawStyle() { return RigDraw._drawStyle() }
    function addDrawAround(shape) { return RigDraw.addDrawAround(shape) }
    function addDrawFree(shape, x0, y0, x1, y1) { return RigDraw.addDrawFree(shape, x0, y0, x1, y1) }
    function setDrawTool(shape) { return RigDraw.setDrawTool(shape) }
    function lockAspect(x0, y0, x1, y1) { return RigDraw.lockAspect(x0, y0, x1, y1) }
    function requestDrawColor(field) { return RigDraw.requestDrawColor(field) }
    // Layers: stacking, hiding and locking, names (rig_layers.js)
    function normalizeStacking() { return RigLayers.normalizeStacking() }
    function insertBelowChips(n) { return RigLayers.insertBelowChips(n) }
    // The planes (rig_layers.js)
    function isBackground(n) { return RigLayers.isBackground(n) }
    function canHoldBackground(n) { return RigLayers.canHoldBackground(n) }
    function backgroundRefusal(n) { return RigLayers.backgroundRefusal(n) }
    function planeOf(n) { return RigLayers.planeOf(n) }
    function inEditPlane(n) { return RigLayers.inEditPlane(n) }
    function planeRange(plane) { return RigLayers.planeRange(plane) }
    function normalizePlanes() { return RigLayers.normalizePlanes() }
    function insertInPlane(n, plane) { return RigLayers.insertInPlane(n, plane) }
    function moveToPlane(ids, plane) { return RigLayers.moveToPlane(ids, plane) }
    function clearPlane(plane) { return RigLayers.clearPlane(plane) }
    function setPlaneLocked(plane, on) { return RigLayers.setPlaneLocked(plane, on) }
    function planeLocked(plane) { return RigLayers.planeLocked(plane) }
    function bottomPicture() { return RigLayers.bottomPicture() }
    function setPictureLook(id, key, value) { return RigLayers.setPictureLook(id, key, value) }
    function refreshLookUrl(n) { return RigLayers.refreshLookUrl(n) }
    function planeMoveItems(ids) { return RigMenu.planeMoveItems(ids) }
    // Callout "Detach from Chips" for the menu bar (rig_commands.js, 07 S134).
    function detachFromChips() { return RigMenu._detachFromChips() }
    // Pictures whose look changed: their adjusted copy is made once the
    // slider pauses briefly, not at every step of a drag.
    property var _lookWaiting: ({})
    function _queueLookUrl(id) {
        var w = _lookWaiting
        w[id] = true
        _lookWaiting = w
        _lookTimer.restart()
    }
    function planeOpacity(n) { return RigLayers.planeOpacity(n) }
    function foregroundOpacity() { return RigLayers.foregroundOpacity() }
    function leaderLayerZ() { return RigLayers.leaderLayerZ() }
    function moveNodeTo(id, index) { return RigLayers.moveNodeTo(id, index) }
    function bringForward() { return RigLayers.bringForward() }
    function sendBack() { return RigLayers.sendBack() }
    function bringToFront() { return RigLayers.bringToFront() }
    function sendToBack() { return RigLayers.sendToBack() }
    function isHidden(n) { return RigLayers.isHidden(n) }
    function hotBlocked(n) { return RigLayers.hotBlocked(n) }
    function hotHidden(n) { return RigLayers.hotHidden(n) }
    function leaderBlocked(n, li) { return RigLayers.leaderBlocked(n, li) }
    function leaderHidden(n, li) { return RigLayers.leaderHidden(n, li) }
    function layerFlag(id, part, flag) { return RigLayers.layerFlag(id, part, flag) }
    function layerFlagInherited(id, part, flag) { return RigLayers.layerFlagInherited(id, part, flag) }
    function setLayerFlag(id, part, flag, on) { return RigLayers.setLayerFlag(id, part, flag, on) }
    function setLayerFlags(targets, flag, on) { return RigLayers.setLayerFlags(targets, flag, on) }
    function toggleLayerFlag(id, part, flag) { return RigLayers.toggleLayerFlag(id, part, flag) }
    function canDeleteLayer(id, part) { return RigLayers.canDeleteLayer(id, part) }
    function deleteLayer(id, part) { return RigLayers.deleteLayer(id, part) }
    function toggleLockSelection() { return RigLayers.toggleLockSelection() }
    function showAll() { return RigLayers.showAll() }
    function unlockAll() { return RigLayers.unlockAll() }
    function layerName(n) { return RigLayers.layerName(n) }
    function renameLayer(id, name) { return RigLayers.renameLayer(id, name) }
    function layerType(n) { return RigLayers.layerType(n) }
    function layerRows(state, expanded) { return RigLayers.layerRows(state, expanded) }
    function layerCounts(state) { return RigLayers.layerCounts(state) }
    function selectLayerMatches(state) { return RigLayers.selectLayerMatches(state) }

    // Lining up and spacing out the selection (rig_align.js)
    function canAlign() { return RigAlign.canAlign() }
    function canDistribute() { return RigAlign.canDistribute() }
    function alignSelection(mode) { return RigAlign.alignSelection(mode) }

    // Press to find (rig_find.js)
    function findTick() { return RigFind.findTick() }
    function findControl(kind, hwId) { return RigFind.findControl(kind, hwId) }
    function showFindMessage(text) { return RigFind.showFindMessage(text) }

    // Mirroring the whole layout (rig_mirror.js)
    function mirrorLayout(pictures) { return RigMirror.mirrorLayout(pictures) }

    // Turning several items together (rig_grouprot.js)
    function canTurnTogether() { return RigGroupRot.canTurnTogether() }
    function selectionBounds() { return RigGroupRot.selectionBounds() }
    function onTurnHandle(mx, my) { return RigGroupRot.onTurnHandle(mx, my) }
    function turnPivot() { return RigGroupRot.turnPivot() }
    function beginTurn(mx, my) { return RigGroupRot.beginTurn(mx, my) }
    function dragTurn(mx, my) { return RigGroupRot.dragTurn(mx, my) }
    function endTurn() { return RigGroupRot.endTurn() }
    function turnSelectionBy(deg) { return RigGroupRot.turnSelectionBy(deg) }

    // View → Zoom to selection: the selected items fill the view.
    function zoomToSelection() {
        var ids = selectedIds || []
        if (!ids.length || !face || !face.fitEditorRect)
            return false
        var b = selectionBounds()
        if (ids.length === 1) {
            var n = nodeAt(ids[0])
            if (n)
                b = nodeBox(n)
        }
        if (!(b.w > 0 && b.h > 0))
            return false
        face.fitEditorRect(b.x, b.y, b.w, b.h)
        return true
    }

    // Callouts (rig_callout.js)
    function isCallout(n) { return RigCallout.isCallout(n) }
    function calloutTip(n) { return RigCallout.calloutTip(n) }
    function calloutTipLocal(n, w, h) { return RigCallout.calloutTipLocal(n, w, h) }
    function paintCallout(ctx, n, w, h, ox, oy) { return RigCallout.paintCallout(ctx, n, w, h, ox, oy) }
    function onCalloutTip(n, mx, my) { return RigCallout.onCalloutTip(n, mx, my) }
    function dragCalloutTip(n, mx, my) { return RigCallout.dragCalloutTip(n, mx, my) }
    function dropCalloutTip(n, mx, my) { return RigCallout.dropCalloutTip(n, mx, my) }
    function addCalloutTail() { return RigCallout.addCalloutTail() }
    function removeCalloutTail() { return RigCallout.removeCalloutTail() }
    function detachCalloutTail() { return RigCallout.detachCalloutTail() }
    function addCalloutFor(chipId) { return RigCallout.addCalloutFor(chipId) }

    // Paths and freehand lines (rig_path.js)
    function isPath(n) { return RigPath.isPath(n) }
    function isPathTool(tool) { return RigPath.isPathTool(tool) }
    function pathLocal(n, w, h) { return RigPath.pathLocal(n, w, h) }
    function pathPointsAt(n) { return RigPath.pathPointsAt(n) }
    function setPathPoints(n, pts) { return RigPath.setPathPoints(n, pts) }
    function pathClick(mx, my) { return RigPath.pathClick(mx, my) }
    function pathHoverAt(mx, my) { return RigPath.pathHoverAt(mx, my) }
    function finishPath(closed) { return RigPath.finishPath(closed) }
    function cancelPath() { return RigPath.cancelPath() }
    function undoPathPoint() { return RigPath.undoPathPoint() }
    function penStart(mx, my) { return RigPath.penStart(mx, my) }
    function penMove(mx, my) { return RigPath.penMove(mx, my) }
    function penEnd() { return RigPath.penEnd() }
    function paintPathDraft(ctx) { return RigPath.paintPathDraft(ctx) }
    function paintPath(ctx, n, w, h) { return RigPath.paintPath(ctx, n, w, h) }
    function hitPath(n, px, py, w, h) { return RigPath.hitPath(n, px, py, w, h) }
    function dragPathPoint(i, mx, my) { return RigPath.dragPathPoint(i, mx, my) }
    function togglePathClosed() { return RigPath.togglePathClosed() }
    function togglePathSmooth() { return RigPath.togglePathSmooth() }

    // Saved styles (rig_styles.js)
    function styleKindOf(n) { return RigStyles.styleKindOf(n) }
    function styleFieldsOf(n) { return RigStyles.styleFieldsOf(n) }
    function saveStyleOf(id) { return RigStyles.saveStyleOf(id) }
    function applySavedStyle(style) { return RigStyles.applySavedStyle(style) }
    function stylesFor(kind) { return RigStyles.stylesFor(kind) }

    // Ruler guides (rig_rulers.js)
    function addRulerGuide(axis, frac) { return RigRulers.addRulerGuide(axis, frac) }
    function moveRulerGuide(axis, index, frac) { return RigRulers.moveRulerGuide(axis, index, frac) }
    function removeRulerGuide(axis, index) { return RigRulers.removeRulerGuide(axis, index) }
    function clearRulerGuides() { return RigRulers.clearRulerGuides() }
    function rulerGuideAt(mx, my) { return RigRulers.rulerGuideAt(mx, my) }
    function dragRulerGuide(axis, index, mx, my) { return RigRulers.dragRulerGuide(axis, index, mx, my) }
    function dropRulerGuide(axis, index, mx, my) { return RigRulers.dropRulerGuide(axis, index, mx, my) }
    function rulerGuideLines() { return RigRulers.rulerGuideLines() }
    function printAreaRect() { return RigPrintJs.printAreaRect() }
    function beginPrintArea(x, y) { return RigPrintJs.beginPrintArea(x, y) }
    function movePrintArea(x, y) { return RigPrintJs.movePrintArea(x, y) }
    function endPrintArea() { return RigPrintJs.endPrintArea() }
    function setPrintAreaRect(x, y, w, h, edges) { return RigPrintJs.setPrintAreaRect(x, y, w, h, edges) }
    function clearPrintArea() { return RigPrintJs.clearPrintArea() }
    function shiftPrintArea(dfx, dfy, k, ax, ay) { return RigPrintJs.shiftPrintArea(dfx, dfy, k, ax, ay) }
    function reshapePrintArea() { return RigPrintJs.reshapePrintArea() }
    function drawnPrintRect() { return RigPrintJs.drawnPrintRect() }
    // The device's photo's own size in pixels: the bottom background
    // picture's ({0, 0} without one); what 100% print scale means (07 S83).
    function photoNatural() {
        return _bottomPic.status === Image.Ready ? { w: _bottomPic.implicitWidth, h: _bottomPic.implicitHeight } : { w: 0, h: 0 }
    }

    // Transform handles (rig_transform.js)
    function transformModesFor(n) { return RigTransform.transformModesFor(n) }
    function setTransformMode(mode) { return RigTransform.setTransformMode(mode) }
    function canEditPoints(n) { return RigTransform.canEditPoints(n) }
    function hasShaping(n) { return RigTransform.hasShaping(n) }
    function skewMatrix(n, w, h) { return RigTransform.skewMatrix(n, w, h) }
    function drawLocalPoint(n, x, y, w, h) { return RigTransform.drawLocalPoint(n, x, y, w, h) }
    function transformHandles(n, w, h) { return RigTransform.transformHandles(n, w, h) }
    function transformHandleAt(n, px, py, w, h) { return RigTransform.transformHandleAt(n, px, py, w, h) }
    function dragTransform(n, name, mx, my) { return RigTransform.dragTransform(n, name, mx, my) }
    function convertToPath() { return RigTransform.convertToPath() }
    // Reset Shape (07 S42) on an item (the selected one when id is ""): a
    // picture loses its crop, skew, flip and turn; a shape its shaping.
    function resetShape(id) {
        var n = nodeAt(id || selectedId)
        if (!n)
            return
        if (isOverlay(n))
            return RigLayers.resetPictureShape(n)
        if (n.id !== selectedId)
            setSelection([n.id])
        return RigTransform.resetShape()
    }

    // Hotspots (rig_hotspot.js)
    function hotPressed(n) { return RigHotspot.hotPressed(n) }
    function hotShown(n) { return RigHotspot.hotShown(n) }
    function paintHotspot(ctx, n, x, y, size, colour, selected) { return RigHotspot.paintHotspot(ctx, n, x, y, size, colour, selected) }
    function hotPulseTick() { return RigHotspot.hotPulseTick() }
    function hotPulsing() { return RigHotspot.hotPulsing() }
    function distributeSelection(axis) { return RigAlign.distributeSelection(axis) }

    // The Properties panel's fields (rig_props.js)
    function propsModel() { return RigProps.propsModel() }
    function setProp(key, value) { return RigProps.setProp(key, value) }

    // What the right-click menu offers (rig_menu.js)
    function menuKind() { return RigMenu.menuKind() }
    function menuTitle(kind) { return RigMenu.menuTitle(kind) }
    function menuModel() { return RigMenu.menuModel() }
    function menuLines() { return _menu.opened ? _menu.describe() : [] }
    function closeMenu() { _menu.close() }
    // The delegate drawing node i (for tests that need its frame).
    function _chipsItem(i) { return _chips.itemAt(i) }
    function menuRowRect(text) { return _menu.rowRect(_menu.rowIndexOf(text)) }
    function menuBox() { var p = _menu.contentItem.mapToItem(null, 0, 0); return { x: p.x, y: p.y, w: _menu.width, h: _menu.height, open: _menu.opened } }

    function paintDraw(ctx, n, w, h) { return RigDraw.paintDraw(ctx, n, w, h) }
    function isLine(n) { return RigDraw.isLine(n) }
    function isHead(style) { return RigDraw.isHead(style) }
    function paintHead(ctx, head, style) { return RigDraw.paintHead(ctx, head, style) }
    function isLineTool(tool) { return RigDraw.isLineTool(tool) }
    function lineEndsAt(n) { return RigDraw.lineEndsAt(n) }
    function setLineEnds(n, ax, ay, bx, by) { return RigDraw.setLineEnds(n, ax, ay, bx, by) }
    function applyDrawField(key, val) { return RigDraw.applyDrawField(key, val) }
    function swapLineHeads() { return RigDraw.swapLineHeads() }
    function drawToolPoint(x0, y0, x1, y1) { return RigDraw.drawToolPoint(x0, y0, x1, y1) }
    function isRotatable(n) { return RigDraw.isRotatable(n) }
    function isFlippable(n) { return RigDraw.isFlippable(n) }
    function setRotation(deg) { return RigDraw.setRotation(deg) }
    function flipSelection(axis) { return RigDraw.flipSelection(axis) }
    function toggleCrop() { return RigDraw.toggleCrop() }
    function setCropEdge(edge, pct) { return RigDraw.setCropEdge(edge, pct) }
    function resetCrop() { return RigDraw.resetCrop() }
    function drawNewBox() { return RigDraw.drawNewBox() }
    function finishCrop() { return RigDraw.finishCrop() }
    function cancelCrop() { return RigDraw.cancelCrop() }
    function beginSideSkew(n, h, x, y) { return RigTransform.beginSideSkew(n, h, x, y) }
    function applySideSkew(x, y) { return RigTransform.applySideSkew(x, y) }
    function onGroupResizeHandle(x, y) { return RigGroupRot.onGroupResizeHandle(x, y) }
    function beginGroupResize(h, x, y) { return RigGroupRot.beginGroupResize(h, x, y) }
    function dragGroupResize(x, y) { return RigGroupRot.dragGroupResize(x, y) }
    function endGroupResize() { return RigGroupRot.endGroupResize() }
    function canGroupResize() { return RigGroupRot.canGroupResize() }
    function duplicateInPlace() { return RigSelection.duplicateInPlace() }
    function groupResizeHandles(b) { return RigGroupRot.groupResizeHandles(b) }
    // A picture's own width / height (07 S154), or 0 when unknown.
    // Style.dp for the code-behind files, which can't see the Style
    // singleton themselves (handle hit radii, 07 S155).
    function uiDp(v) { return Style.dp(v) }

    function pictureAspect(n) {
        if (!n || !imageAspectFn)
            return 0
        var a = Number(imageAspectFn(n.src || ""))
        return isFinite(a) && a > 0 ? a : 0
    }

    // Selection, nudging, delete, copy/paste/duplicate and stacking order (rig_selection.js)
    function deleteSelection() { return RigSelection.deleteSelection() }
    function deleteChip(id) { return RigSelection.deleteChip(id) }
    function deleteSelected() { return RigSelection.deleteSelected() }
    function nudge(dx, dy) { return RigSelection.nudge(dx, dy) }
    function moveNodeBy(n, dx, dy, seenPack) { return RigSelection.moveNodeBy(n, dx, dy, seenPack) }
    function _newId(n) { return RigSelection._newId(n) }
    function shiftClone(n, dx, dy) { return RigSelection.shiftClone(n, dx, dy) }
    function pasteNodes(src, dx, dy) { return RigSelection.pasteNodes(src, dx, dy) }
    function duplicateSelection() { return RigSelection.duplicateSelection() }
    function copySelection() { return RigSelection.copySelection() }
    function pasteClipboard() { return RigSelection.pasteClipboard() }
    function cutSelection() { return RigSelection.cutSelection() }
    function pasteAt(x, y) { return RigSelection.pasteAt(x, y) }
    function selectAll() { return RigSelection.selectAll() }
    function _boxCentre(list) { return RigSelection._boxCentre(list) }
    function isSelected(id) { return RigSelection.isSelected(id) }
    function setSelection(ids) { return RigSelection.setSelection(ids) }
    function toggleSelected(id) { return RigSelection.toggleSelected(id) }
    function cancelAllActions() { return RigSelection.cancelAllActions() }
    function overPool(mx, my) { return RigSelection.overPool(mx, my) }
    function returnToPool() { return RigSelection.returnToPool() }
    function freeEndsAimedAt(id, memberIndex) { return RigSelection.freeEndsAimedAt(id, memberIndex) }

    // What a pointer drag does to the item being dragged (rig_pointer.js)
    function applyPointer(mx, my, altOff) { return RigPointer.applyPointer(mx, my, altOff) }

    function repaint() {
        tick++
        paintLeaders()
    }

    // A drag step: only the dragged items (the selection, and drawings drawn
    // around them) are drawn again. Tables and their packs move other items
    // too: those still redraw everything. Letting go makes an undo step,
    // which redraws everything anyway.
    function repaintForDrag() {
        if (dragKind === "tablecell")
            return repaint()
        var ids = (selectedIds || []).slice()
        if (selectedId && ids.indexOf(selectedId) < 0)
            ids.push(selectedId)
        var set = {}
        for (var i = 0; i < ids.length; i++) {
            var n = nodeAt(ids[i])
            if (!n || isTable(n) || tablePackOf(n))
                return repaint()
            set[n.id] = true
            // Chips on a picture's snap points follow it (P6a).
            var socks = socketChipIds(n)
            for (var si = 0; si < socks.length; si++)
                set[socks[si]] = true
        }
        var list = nodes || []
        for (var j = 0; j < list.length; j++) {
            var around = list[j].around || []
            for (var k = 0; k < around.length; k++) {
                if (set[around[k]]) {
                    set[list[j].id] = true
                    break
                }
            }
        }
        var same = Object.keys(set).length === Object.keys(liveIds || {}).length
        for (var key in set) {
            if (!(liveIds || {})[key])
                same = false
        }
        liveTick++
        if (!same) {
            liveIds = set
            liveLeaderIds = _leadersOn(set)
            paintLeaders()  // once: the still canvas leaves them out now
        } else if (_liveLines) {
            _liveLines.requestPaint()
        }
    }

    // The dragged items and those with a leader ending on one of them.
    function _leadersOn(set) {
        var out = {}
        for (var key in set)
            out[key] = true
        var list = nodes || []
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (out[n.id] || isDraw(n))
                continue
            var ls = leaderList(n)
            for (var j = 0; j < ls.length; j++) {
                var ends = [ls[j].from, ls[j].to]
                for (var e = 0; e < ends.length; e++) {
                    if (ends[e] && ends[e].id && set[ends[e].id])
                        out[n.id] = true
                }
            }
        }
        return out
    }

    function bump() {
        normalizePlanes()
        repaint()
        selectedChanged()
        if (!_restoring)
            pushHist()
    }

    // A pointer gesture (a drag from press to release) is one undo step
    // (07 S55a): steps asked for while it runs wait for endGesture().
    property bool gestureActive: false
    property string _gestureSnap: ""

    function beginGesture() {
        if (gestureActive)
            return
        // A waiting run of nudges keeps its own step, before the drag's.
        flushPendingStep()
        _gestureSnap = snapJson()
        gestureActive = true
    }

    // Ends the gesture: one step if the map changed since beginGesture().
    // Safe to call when no gesture runs.
    function endGesture() {
        if (!gestureActive)
            return
        gestureActive = false
        var changed = snapJson() !== _gestureSnap
        _gestureSnap = ""
        if (changed)
            pushHist()
    }

    // An undo step: the nodes of both planes (pictures, their look and the
    // background among them), the print area and the ruler guides (07 S57).
    // View settings (the plane being edited, the faint foreground, the
    // Background row's eye and Opacity) are not part of it (P1a, P4a).
    function snapJson() {
        try {
            return JSON.stringify({ nodes: nodes || [],
                                    printArea: printArea,
                                    guidesX: rulerGuidesX || [], guidesY: rulerGuidesY || [] })
        } catch (e) {
            return "[]"
        }
    }

    function seedHist() {
        hist = [snapJson()]
        histAt = 0
        historyChanged()
    }

    function replaceHistTop() {
        if (_restoring || !interactive)
            return
        flushPendingStep()
        var cur = hist || []
        if (histAt < 0 || histAt >= cur.length) {
            seedHist()
            return
        }
        var next = cur.slice()
        next[histAt] = snapJson()
        hist = next
        historyChanged()
    }

    // The steps made since position at become one (a command that changes
    // the map in two goes, such as a mirrored copy: S78).
    function squashHistSince(at) {
        var cur = hist || []
        if (at < 0 || histAt <= at + 1 || histAt >= cur.length)
            return
        var next = cur.slice(0, at + 1)
        next.push(cur[histAt])
        hist = next
        histAt = next.length - 1
        historyChanged()
    }

    function pushHist() {
        if (_restoring || !interactive || gestureActive)
            return
        // A run still waiting for its pause is its own step, before this
        // command's: Undo then takes back the command alone (S55).
        flushPendingStep()
        _pushSnap(snapJson())
    }

    function _pushSnap(s) {
        var cur = hist || []
        if (histAt >= 0 && histAt < cur.length && cur[histAt] === s)
            return
        var next = cur.slice(0, histAt + 1)
        next.push(s)
        // histCap is the steps back (S56): the start state is kept on top.
        if (next.length > histCap + 1)
            next = next.slice(next.length - histCap - 1)
        hist = next
        histAt = next.length - 1
        historyChanged()
    }

    function applySnap(s) {
        var doc = null
        try {
            doc = JSON.parse(s)
        } catch (e) {
            return
        }
        var next = Array.isArray(doc) ? doc : (doc.nodes || [])
        var list = nodes
        if (!list)
            return
        list.splice(0, list.length)
        for (var i = 0; i < next.length; i++)
            list.push(next[i])
        // Adjusted copies follow the look of that step.
        for (var k = 0; k < list.length; k++) {
            if (list[k] && list[k].look && isOverlay(list[k]))
                _queueLookUrl(list[k].id)
        }
        if (Array.isArray(doc))
            return
        // The print area and guides of that step; the window follows.
        if (doc.printArea !== undefined
                && JSON.stringify(doc.printArea) !== JSON.stringify(printArea)) {
            printArea = doc.printArea
            printAreaEdited(false)
        }
        if (doc.guidesX !== undefined
                && (JSON.stringify(doc.guidesX) !== JSON.stringify(rulerGuidesX || [])
                    || JSON.stringify(doc.guidesY || []) !== JSON.stringify(rulerGuidesY || []))) {
            rulerGuidesX = (doc.guidesX || []).slice()
            rulerGuidesY = (doc.guidesY || []).slice()
            rulerGuidesEdited()
        }
    }

    // Slider changes (a picture's look, the color picker) come many per drag:
    // one undo step once they stop.
    // The pause that ends such a run; tests set it to end runs when they
    // choose, whatever the machine's speed.
    property alias stepPauseMs: _runHist.interval
    readonly property bool stepWaiting: _runHist.running

    // A run of live edits (the color picker) makes one undo step when it
    // pauses, like a picture's look sliders. Its step is the state after its
    // latest edit, kept now: a command may change the map before the run's
    // step goes in.
    function noteLiveEdit() {
        if (_restoring || !interactive)
            return
        _runSnap = snapJson()
        _runHist.restart()
    }

    // A step still waiting for a pause (nudges, live edits) goes into the
    // history first, so Undo takes back exactly it.
    function flushPendingStep() {
        if (!_runHist.running)
            return
        _runHist.stop()
        _landRun()
    }

    function _landRun() {
        var s = _runSnap
        _runSnap = ""
        if (!_restoring && interactive && s)
            _pushSnap(s)
    }

    // The map takes the keys again (arrow nudges) after a click elsewhere,
    // such as a Layers row.
    function focusMap() {
        _pointer.forceActiveFocus()
    }

    function undo() {
        // Undo during a drag ends the drag first; its step is what goes back.
        stopGesture()
        flushPendingStep()
        if (!canUndo)
            return
        histAt = histAt - 1
        _restoring = true
        applySnap(hist[histAt])
        groupEditId = ""
        selectedMember = -1
        setSelection([])
        historyChanged()
        bump()
        _restoring = false
    }

    function redo() {
        // Undo during a drag ends the drag first; its step is what goes back.
        stopGesture()
        flushPendingStep()
        if (!canRedo)
            return
        histAt = histAt + 1
        _restoring = true
        applySnap(hist[histAt])
        groupEditId = ""
        selectedMember = -1
        setSelection([])
        historyChanged()
        bump()
        _restoring = false
    }

    // Stops a drag in progress (Undo/Redo or a lost mouse grab): the drag
    // keeps what it did so far as its one step.
    function stopGesture() {
        if (!gestureActive)
            return
        if (dragKind === "turn")
            endTurn()
        if (dragKind === "groupresize")
            endGroupResize()
        dragKind = ""
        banding = false
        lineArm = false
        poolHover = false
        guideDrag = null
        clearMoveGuides()
        endGesture()
    }

    // The readout's text for the drag running now (07 S151), or "".
    function _pctTxt(v) { return (Math.round(v * 1000) / 10).toFixed(1) + " %" }
    function _signedPct(v) {
        var t = _pctTxt(Math.abs(v))
        return (v < -0.0005 ? "−" : "+") + t
    }
    function _degTxt(d) { return (Math.round(d * 10) / 10).toFixed(1) + "°" }
    // Where an item was at the press, from the gesture's snapshot; parsed
    // once a gesture (kept on a plain object, so no binding follows it).
    property var _readoutCache: ({ key: "", nodes: null })
    function _gestureStartNode(id) {
        var c = _readoutCache
        if (c.key !== _gestureSnap) {
            c.key = _gestureSnap
            c.nodes = {}
            try {
                var doc = JSON.parse(_gestureSnap)
                var list = Array.isArray(doc) ? doc : (doc.nodes || [])
                for (var i = 0; i < list.length; i++)
                    c.nodes[list[i].id] = list[i]
            } catch (e) {
                c.nodes = {}
            }
        }
        return c.nodes[id] || null
    }
    function readoutText() {
        var dk = dragKind
        if (!dk)
            return ""
        var s = spaceRect()
        if (dk === "turn")
            return _degTxt(turnAngle)
        if (dk === "groupresize") {
            var gb = selectionBounds()
            return "W " + _pctTxt(gb.w / Math.max(1, s.w)) + "  H " + _pctTxt(gb.h / Math.max(1, s.h))
        }
        var n = nodeAt(selectedId)
        if (!n)
            return ""
        if (dk === "draw-rotate")
            return _degTxt(n.rot || 0)
        var sizeHandles = ["nw", "ne", "sw", "se", "n", "s", "w", "e"]
        if (dk.indexOf("draw-") === 0 && sizeHandles.indexOf(dk.slice(5)) >= 0 && isDraw(n) && !isLine(n)) {
            var g = drawGeom(n)
            return "W " + _pctTxt(g.w / Math.max(1, s.w)) + "  H " + _pctTxt(g.h / Math.max(1, s.h))
        }
        if (dk === "draw" || dk === "chip") {
            var was = _gestureStartNode(n.id)
            if (!was)
                return ""
            var dx = isDraw(n) ? (n.fx || 0) - (was.fx || 0) : (n.chipFx || 0) - (was.chipFx || 0)
            var dy = isDraw(n) ? (n.fy || 0) - (was.fy || 0) : (n.chipFy || 0) - (was.chipFy || 0)
            return "X " + _signedPct(dx) + "  Y " + _signedPct(dy)
        }
        return ""
    }

    // Esc during a drag (07 S150): everything goes back to how it was at the
    // press, with no undo step; the selection stays (less items the drag
    // made, such as Alt-drag copies). The map comes back the way Undo
    // brings a step back (applySnap). Returns whether a drag was cancelled.
    function cancelGesture() {
        if (!gestureActive)
            return false
        var snap = _gestureSnap
        var keep = (selectedIds || []).slice()
        gestureActive = false
        _gestureSnap = ""
        turnStart = null
        turnAngle = 0
        groupRz = null
        cropStart = null
        dragKind = ""
        banding = false
        lineArm = false
        poolHover = false
        guideDrag = null
        clearMoveGuides()
        if (snap && snapJson() !== snap) {
            _restoring = true
            applySnap(snap)
            var still = []
            for (var i = 0; i < keep.length; i++) {
                if (nodeAt(keep[i]))
                    still.push(keep[i])
            }
            setSelection(still)
            bump()
            _restoring = false
        } else {
            repaint()
        }
        return true
    }

    function clearLayout() {
        setSelection([])
        groupEditId = ""
        selectedMember = -1
        selectedLeader = 0
        selectedSeg = -1
        dragKind = ""
        bump()
    }

    onInteractiveChanged: {
        if (!interactive) {
            selectedId = ""
            selectedIds = []
            selectedSpine = -1
            dragKind = ""
            banding = false
            groupEditId = ""
            selectedMember = -1
            dragMember = -1
            hoverHwLabel = ""
            cancelRename()
            armRenameId = ""
            armRenameMember = -1
            editPlane = "foreground"
        } else {
            Qt.callLater(seedHist)
        }
        paintLeaders()
    }

    function ctxTarget() {
        tick
        return nodeAt((_ctx && _ctx.nodeId) || selectedId)
    }

    function ctxHasTheme() {
        tick
        var n = ctxTarget()
        return !!(n && isFiveWay(n) && fiveWayFormat(n) !== "")
    }

    function ctxHasGroupFormat() {
        tick
        var n = ctxTarget()
        if (!n || !isGroup(n))
            return false
        if (fiveWayFormat(n) !== "")
            return true
        var mem = n.members || []
        var i
        for (i = 0; i < mem.length; i++) {
            if (memberHasOverride(mem[i]))
                return true
        }
        return false
    }

    function ctxHasSpines() {
        tick
        var n = ctxTarget()
        if (!n || isDraw(n))
            return false
        var ls = leaderList(n)
        var i
        for (i = 0; i < ls.length; i++) {
            if (ls[i].spines && ls[i].spines.length)
                return true
        }
        return !!(n.spines && n.spines.length)
    }

    function ctxSpineIndex() {
        tick
        if (_ctx && _ctx.kind === "spine" && _ctx.seg >= 0)
            return _ctx.seg
        return selectedSpine
    }

    function ctxHasSelectedSpine() {
        return ctxSpineIndex() >= 0
    }

    function ctxSpineCurved() {
        tick
        var n = ctxTarget()
        var i = ctxSpineIndex()
        if (!n || i < 0)
            return false
        var L = currentLeader(n)
        return !!(L && L.spines && L.spines[i] && L.spines[i].curve)
    }

    function ctxMode() {
        tick
        var k = (_ctx && _ctx.kind) ? String(_ctx.kind) : ""
        if (k === "line" || k === "spine" || k === "from" || k === "to")
            return "leader"
        if (k === "draw")
            return "draw"
        var n = ctxTarget()
        if (!n)
            return "empty"
        if (isDraw(n))
            return "draw"
        return "chip"
    }

    function ctxIsLeader() {
        return ctxMode() === "leader"
    }

    function ctxHasMapItem() {
        var m = ctxMode()
        return m === "chip" || m === "leader"
    }


    Connections {
        target: face
        function onLiveStampChanged() { _ed.tick++ }
        function onDestTickChanged() { _ed.tick++ }
        function onWidthChanged() { paintLeaders(); if (_grid) _grid.requestPaint() }
        function onHeightChanged() { paintLeaders(); if (_grid) _grid.requestPaint() }
    }

    // Every node in list order (the last on top) and the leader canvas, which
    // sits just under the lowest chip.
    Item {
        id: _stack
        anchors.fill: parent
        z: 2

    Repeater {
        id: _chips
        model: { _ed.tick; return (_ed.nodes || []).length }
        delegate: Item {
            id: _wrap
            required property int index
            readonly property var node: {
                _ed.tick
                var list = _ed.nodes || []
                return (index >= 0 && index < list.length) ? list[index] : null
            }
            readonly property bool live: !!(node && _ed.liveIds && _ed.liveIds[node.id])
            readonly property int rev: _ed.tick + (live ? _ed.liveTick : 0)
            // tick: hiding changes the node in place, not the node object.
            // planeShow: the plane's on-screen strength (S115, S120).
            readonly property real planeShow: {
                _wrap.rev
                _ed.editPlane; _ed.interactive; _ed.exporting; _ed.showFgFaint
                _ed.fgFaint; _ed.bgViewHidden; _ed.bgViewOpacity
                return _ed.planeOpacity(node)
            }
            visible: { _wrap.rev; return node !== null && !node.hidden && planeShow > 0 }
            x: {
                _wrap.rev
                if (!node)
                    return 0
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).x
                var x = _ed.fxToX(node.chipFx)
                if (_ed.isGroup(node))
                    x += _ed.groupMinX(node)
                return x
            }
            y: {
                _wrap.rev
                if (!node)
                    return 0
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).y
                var y = _ed.fyToY(node.chipFy)
                if (_ed.isGroup(node))
                    y += _ed.groupMinY(node)
                return y
            }
            z: index
            rotation: { _wrap.rev; return (_ed.isDraw(node) && node.rot) ? node.rot : 0 }
            opacity: { _wrap.rev; return ((_ed.isDraw(node) && node.opacity !== undefined && node.opacity !== null) ? node.opacity : 1) * planeShow }
            transformOrigin: Item.Center
            clip: false
            width: {
                _wrap.rev
                if (!node)
                    return 40
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).w
                if (_ed.isGroup(node))
                    return _ed.groupSpanW(node)
                return (_body.item && _body.item.implicitWidth > 1) ? _body.item.implicitWidth : _ed.chipWGuess(node, null)
            }
            height: {
                _wrap.rev
                if (!node)
                    return 20
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).h
                if (_ed.isGroup(node))
                    return _ed.groupSpanH(node)
                return (_body.item && _body.item.implicitHeight > 1) ? _body.item.implicitHeight : _ed.chipH(node)
            }

            Loader {
                id: _body
                clip: false
                width: {
                    _wrap.rev
                    if (_wrap.node && (_ed.isGroup(_wrap.node) || _ed.isDraw(_wrap.node)))
                        return _wrap.width
                    return item ? item.implicitWidth : 0
                }
                height: {
                    _wrap.rev
                    if (_wrap.node && (_ed.isGroup(_wrap.node) || _ed.isDraw(_wrap.node)))
                        return _wrap.height
                    return item ? item.implicitHeight : 0
                }
                sourceComponent: {
                    var n = _wrap.node
                    if (!n) return _tagComp
                    if (_ed.isDraw(n)) return _drawComp
                    return _ed.isGroup(n) ? _groupComp : _tagComp
                }
                onLoaded: {
                    item.node = Qt.binding(function() { return _wrap.node })
                    item.rev = Qt.binding(function() { return _wrap.rev })
                    if (_wrap.node && _ed.isGroup(_wrap.node))
                        _ed.ensureMemberOffsets(_wrap.node)
                    if (_wrap.node && _ed.isTable(_wrap.node))
                        _ed.ensureTable(_wrap.node)
                }
            }
        }
    }

    // Leader lines and hotspots fade with the foreground (P7a).
    readonly property real fgShow: { _ed.editPlane; _ed.interactive; _ed.exporting; _ed.showFgFaint; _ed.fgFaint; return _ed.foregroundOpacity() }
    RigLeaderLayer { id: _lines; ed: _ed; part: "still"; z: _ed.leaderLayerZ(); opacity: _stack.fgShow; visible: _stack.fgShow > 0 }
    RigLeaderLayer { id: _liveLines; ed: _ed; part: "live"; z: _ed.leaderLayerZ(); opacity: _stack.fgShow; visible: _stack.fgShow > 0 }
    }

    Component {
        id: _groupComp
        RigGroupItem { ed: _ed }
    }

    Component {
        id: _drawComp
        RigDrawItem { ed: _ed }
    }

    Component {
        id: _tagComp
        RigChipItem { ed: _ed }
    }

    // Switching plane is not an edit (S57): what was selected on the other
    // plane is let go, tools and open groups end.
    onEditPlaneChanged: {
        groupEditId = ""
        selectedMember = -1
        drawTool = ""
        dragKind = ""
        banding = false
        cropId = ""
        cancelRename()
        RigLayers._dropOtherPlaneSelection()
        clearMoveGuides()
        repaint()
        selectedChanged()
    }

    onWidthChanged: { paintLeaders(); if (_grid) _grid.requestPaint() }
    onHeightChanged: { paintLeaders(); if (_grid) _grid.requestPaint() }
    onTickChanged: paintLeaders()
    onGridOnChanged: if (_grid) _grid.requestPaint()
    onGridSizeChanged: if (_grid) _grid.requestPaint()
    onNodesChanged: {
        seeded = false
        paintLeaders()
        _seedTimer.restart()
    }

    Timer {
        id: _seedTimer
        interval: 80
        repeat: false
        onTriggered: {
            var list = _ed.nodes || []
            _ed.normalizeStacking()
            _ed.normalizePlanes()
            _ed.demoteSpecialKinds()
            for (var i = 0; i < list.length; i++) {
                _ed.ensureFriendly(list[i])
                _ed.ensureMidSpine(list[i])
            }
            _ed.seeded = true
            _ed.repaint()
            _ed.selectedChanged()
            // Tidying a map as it loads is not an edit: the step it would
            // add replaces the latest one instead (entering Edit left an
            // undo step and "unsaved changes" with nothing changed).
            _ed.replaceHistTop()
        }
    }

    // The device's photo (the bottom background picture), read only for its
    // own size (photoNatural); never shown.
    Image {
        id: _bottomPic
        visible: false
        asynchronous: true
        cache: true
        source: {
            _ed.tick
            var n = _ed.bottomPicture()
            return (n && n.srcUrl) ? n.srcUrl : ""
        }
    }

    RigGuides { id: _guides; ed: _ed; z: 3 }

    RigGrid { id: _grid; ed: _ed }

    RigPointerArea {
        id: _pointer
        ed: _ed
        menuTarget: _ctx
        menu: _menu
        spineHoldTimer: _spineHold
    }

    MouseArea {
        anchors.fill: parent
        z: 8
        enabled: !_ed.interactive
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        onPositionChanged: (m) => _ed.setChipTip(m.x, m.y)
        onExited: _ed.hoverHwLabel = ""
    }

    ToolTip {
        visible: _ed.hoverHwLabel.length > 0 && !_ed.dragKind && !_ed.renameId
        text: _ed.hoverHwLabel
        delay: Style.tooltipDelayMs
        timeout: 4000
        x: _ed.hoverTipX - width / 2
        y: _ed.hoverTipY - height - Style.dp(8)
    }

    TextEdit {
        id: _textClip
        visible: false
        width: 1
        height: 1
    }

    Text {
        renderType: Text.QtRendering
        id: _textFit
        visible: false
        width: 100
        wrapMode: Text.WordWrap
        font.pixelSize: 12
    }

    // Names, text boxes and table cells: Enter keeps what was typed,
    // Shift+Enter starts a new line (a chip's name has two rows at most).
    TextEdit {
        id: _nameEdit
        z: 12
        visible: _ed.showChrome && _ed.renameId.length > 0
        x: {
            _ed.anyTick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return _ed.chipScreenRect(n, mem).x
        }
        y: {
            _ed.anyTick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return _ed.chipScreenRect(n, mem).y
        }
        width: {
            _ed.anyTick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return Math.max(Style.dp(48), _ed.chipScreenRect(n, mem).width)
        }
        height: {
            _ed.anyTick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return Math.max(18, _ed.chipScreenRect(n, mem).height, contentHeight + topPadding + bottomPadding)
        }
        transformOrigin: Item.Center
        rotation: {
            _ed.anyTick
            var n = _ed.nodeAt(_ed.renameId)
            return (n && _ed.isText(n) && n.rot) ? n.rot : 0
        }
        text: _ed.renameDraft
        color: "#E4E4E7"
        font.pixelSize: {
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return _ed.styleVal(n, mem, "fontSize", 10)
        }
        horizontalAlignment: TextEdit.AlignHCenter
        verticalAlignment: TextEdit.AlignVCenter
        selectByMouse: true
        clip: true
        wrapMode: TextEdit.NoWrap
        leftPadding: Style.dp(4)
        rightPadding: Style.dp(4)
        topPadding: Style.dp(2)
        bottomPadding: Style.dp(2)
        onTextChanged: _ed.renameDraft = text
        Keys.onReturnPressed: (event) => _nameEdit.newLineOrKeep(event)
        Keys.onEnterPressed: (event) => _nameEdit.newLineOrKeep(event)
        function newLineOrKeep(event) {
            event.accepted = true
            if (!(event.modifiers & Qt.ShiftModifier)) {
                _ed.commitRename()
                return
            }
            var n = _ed.nodeAt(_ed.renameId)
            var chip = n && !_ed.isText(n) && !_ed.isTable(n)
            if (chip && text.split("\n").length >= RigChips.CHIP_ROWS)
                return
            remove(selectionStart, selectionEnd)
            insert(cursorPosition, "\n")
        }
        Keys.onEscapePressed: (event) => {
            _ed.cancelRename()
            event.accepted = true
        }
        Rectangle {
            anchors.fill: parent
            z: -1
            radius: Style.dp(4)
            color: "#18181B"
            border.color: "#38BDF8"
            border.width: Style.dp(2)
        }
    }

    RigPrintArea { ed: _ed }

    Rectangle {
        visible: _ed.banding
        x: Math.min(_ed.bandX0, _ed.bandX1)
        y: Math.min(_ed.bandY0, _ed.bandY1)
        width: Math.abs(_ed.bandX1 - _ed.bandX0)
        height: Math.abs(_ed.bandY1 - _ed.bandY0)
        z: 9
        color: "#33FBBF24"
        border.color: "#FBBF24"
        border.width: Style.dp(1)
    }

    // Several items selected: a dashed box round them, one rotate handle
    // above it to turn them together, and eight handles to resize them
    // together (07 S153).
    Item {
        id: _turnFrame
        z: 8
        visible: { _ed.anyTick; return _ed.showChrome && _ed.canTurnTogether() && _ed.dragKind !== "band" }
        readonly property var box: { _ed.anyTick; return _ed.selectionBounds() }
        x: box.x
        y: box.y
        width: box.w
        height: box.h
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: _ed.handleFill
            border.width: 1
            opacity: 0.5
        }
        Rectangle {
            x: parent.width / 2 - 0.5
            y: -_ed.rotateHandleOffset + 4
            width: 1
            height: _ed.rotateHandleOffset - 4
            color: _ed.handleFill
        }
        Rectangle {
            x: parent.width / 2 - 6
            y: -_ed.rotateHandleOffset - 6
            width: 12
            height: 12
            radius: 6
            color: _ed.handleFill
            border.color: _ed.handleInk
            border.width: 2
        }
        Repeater {
            model: { _ed.anyTick; return _ed.canGroupResize() ? _ed.groupResizeHandles(_turnFrame.box) : [] }
            Rectangle {
                required property var modelData
                // Centred on the box's edge or corner (07 S155).
                x: modelData.x - _turnFrame.box.x - width / 2
                y: modelData.y - _turnFrame.box.y - height / 2
                width: _ed.groupHandleSize
                height: _ed.groupHandleSize
                radius: Style.dp(1)
                color: _ed.handleFill
                border.color: _ed.handleInk
            }
        }
    }

    // The readout beside the pointer during a resize, rotate, move or group
    // drag (07 S151): sizes and moves in Properties' units (% of the page),
    // angles in degrees. Chrome only: never in a print or export (S87).
    Rectangle {
        id: _readout
        readonly property string label: { _ed.anyTick; _ed.turnAngle; return _ed.gestureActive ? _ed.readoutText() : "" }
        visible: _ed.showChrome && label.length > 0
        z: 12
        x: Math.max(0, Math.min(_ed.width - width, _pointer.edMouseX + Style.dp(16)))
        y: Math.max(0, Math.min(_ed.height - height, _pointer.edMouseY + Style.dp(16)))
        width: _readoutText.implicitWidth + Style.dp(12)
        height: _readoutText.implicitHeight + Style.dp(6)
        radius: Style.dp(3)
        color: Style.bgRaised
        border.color: Style.lineStrong
        border.width: 1
        Text {
            id: _readoutText
            anchors.centerIn: parent
            color: Style.fgStrong
            font.pixelSize: Style.dp(11)
            text: _readout.label
        }
    }

    Text {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: Style.dp(6)
        z: 9
        visible: _ed.showChrome && text.length
        color: "#A1A1AA"
        font.pixelSize: Style.dp(10)
        text: {
            if (_ed.findMsg.length)
                return _ed.findMsg
            if (_ed.packWarn.length)
                return _ed.packWarn
            if (_ed.dragKind === "tablecell")
                return "Dragging free cell. Handles still resize the table."
            if (_ed.textPaintOn)
                return "Format painter — click a text box. Esc cancels."
            if (_ed.drawTool === "text")
                return "Draw text — drag a box. Double-click to edit. Esc cancels."
            if (_ed.drawTool === "table")
                return "Draw table — drag a box. Blank 1×2. Esc cancels."
            if (_ed.drawTool === "path")
                return "Path — click each point. Click the first point to close; double-click, Enter or right-click to finish. Shift: angle steps. Esc cancels."
            if (_ed.drawTool === "pen")
                return "Freehand — draw with the button held down. Esc stops."
            if (_ed.drawTool === "callout")
                return "Callout — drag a box, then drag the pointer's tip. Esc cancels."
            if (_ed.drawTool.length)
                return "Draw " + _ed.drawTool + " — drag on empty. Esc cancels."
            if (_ed.groupEditId.length) {
                var n = _ed.nodeAt(_ed.groupEditId)
                var mem = _ed.targetMember()
                var who = mem ? (_ed.roleWord(_ed.fiveWayRole(mem)) || "cell") : "group"
                return "Edit group " + _ed.groupEditId + " · " + who + ". Drag a cell to nudge. Esc done."
            }
            return ""
        }
    }

    Canvas {
        visible: _ed.interactive && _ed.dragKind === "drawnew" && !_ed.isLineTool(_ed.drawTool)
        // Alt draws from the centre (07 S146): the box comes from rig_draw.js.
        readonly property var box: {
            _ed.drawX0; _ed.drawY0; _ed.drawX1; _ed.drawY1; _ed.altHeld; _ed.drawTool
            return _ed.drawNewBox()
        }
        x: box.x
        y: box.y
        width: Math.max(1, box.w)
        height: Math.max(1, box.h)
        z: 7
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            _ed.paintDraw(ctx, { shape: _ed.drawTool || "rect", fill: "hollow", color: "#14532D", border: "#22C55E", stroke: 2 }, width, height)
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    // The Path and Freehand tools' line so far.
    Canvas {
        id: _pathPreview
        anchors.fill: parent
        visible: _ed.interactive && _ed.pathDraft.length > 0
        z: 7
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            _ed.paintPathDraft(ctx)
        }
        Connections {
            target: _ed
            function onTickChanged() { if (_pathPreview.visible) _pathPreview.requestPaint() }
            function onPathDraftChanged() { _pathPreview.requestPaint() }
        }
    }

    // Preview of a line or arrow being drawn, over the whole editor so a flat
    // line is not clipped to its own box.
    Canvas {
        id: _linePreview
        anchors.fill: parent
        visible: _ed.interactive && _ed.dragKind === "drawnew" && _ed.isLineTool(_ed.drawTool)
        z: 7
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (!visible)
                return
            var w = Math.max(1, width)
            var h = Math.max(1, height)
            _ed.paintDraw(ctx, {
                shape: "line",
                border: _ed._drawStyle().border,
                stroke: 2,
                headEnd: _ed.drawTool === "arrowline" ? "solid" : "none",
                ends: [_ed.drawX0 / w, _ed.drawY0 / h, _ed.drawX1 / w, _ed.drawY1 / h]
            }, w, h)
        }
        Connections {
            target: _ed
            function onDrawX1Changed() { _linePreview.requestPaint() }
            function onDrawY1Changed() { _linePreview.requestPaint() }
        }
    }

    Timer {
        id: _findMsgTimer
        interval: 3000
        onTriggered: _ed.findMsg = ""
    }

    Connections {
        target: _ed.face
        function onLiveStampChanged() {
            _ed.findTick()
            _ed.hotPulseTick()
        }
    }

    // Redraws the hotspots while a press pulse runs.
    Timer {
        id: _hotPulseTimer
        interval: 30
        repeat: true
        onTriggered: {
            paintLeaders()
            if (!_ed.hotPulsing())
                stop()
        }
    }

    Timer {
        id: _lookTimer
        interval: 120
        repeat: false
        onTriggered: {
            var ids = Object.keys(_ed._lookWaiting || {})
            _ed._lookWaiting = ({})
            for (var i = 0; i < ids.length; i++)
                _ed.refreshLookUrl(_ed.nodeAt(ids[i]))
            _ed.repaint()
        }
    }

    Timer {
        id: _runHist
        interval: 400
        repeat: false
        // The pause: the run's step goes in.
        onTriggered: _ed._landRun()
    }

    Timer {
        id: _spineHold
        interval: 450
        repeat: false
        onTriggered: {
            if (!_ed.spineHoldArm)
                return
            _ed.spineHoldArm = false
            _ed.deleteSpineAt(_ed.spineHoldId, _ed.spineHoldLeader, _ed.spineHoldIndex)
        }
    }

    // What the right-click menu was opened on. rig_*.js and the menu read
    // it; close() closes the menu.
    QtObject {
        id: _ctx
        property string nodeId: ""
        property string kind: ""
        property int seg: -1
        property int leader: 0
        // The point right-clicked, in editor-item pixels (RigPointerArea).
        property real mapX: 0
        property real mapY: 0
        // Cancelling (a double-click on empty map) leaves a pinned menu open.
        function close() { if (!_menu.pinned) _menu.close() }
    }

    // The right-click menu: the program's shared one (Gremlin.Menus), fed
    // by rig_menu.js. Rows that cannot be used now are greyed, not hidden.
    Menus.ContextMenu {
        id: _menu
        build: _ed.menuModel
        hideUnavailable: false
        // Stays open while you work and can be dragged by its title; a click
        // outside it closes it.
        stayOpen: true
        // Favourites (07 S137): the block at the top and the ☆ on rows.
        favouritesEnabled: true
        favouriteIds: _ed.favourites
        onFavouriteToggled: function(cmd) { _ed.favouriteToggled(cmd) }
        onFavouriteRemoved: function(cmd) { _ed.favouriteRemoved(cmd) }

        Connections {
            target: _ed
            // Checks and labels follow every change while the menu is open.
            function onTickChanged() {
                if (_menu.opened)
                    _menu.refresh()
            }
        }
    }
}
