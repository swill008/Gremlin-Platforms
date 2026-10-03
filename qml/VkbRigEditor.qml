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
import "rig_photo.js" as RigPhoto
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
import "rig_transform.js" as RigTransform
import "rig_hotspot.js" as RigHotspot

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
    property bool seeded: false
    property bool interactive: false
    // A picture of the page is being taken: no selection, handles, grid or
    // guides. showChrome is what visual parts check instead of interactive.
    property bool exporting: false
    readonly property bool showChrome: interactive && !exporting
    // Export on a light page for printing: colours drawn through ink().
    property bool printLight: false
    // Export modes: the mode's name, drawn at the top of the page while exporting.
    property string exportTitle: ""
    // Turning several items together (rig_grouprot.js): where they started,
    // and the angle so far.
    property var turnStart: null
    property real turnAngle: 0
    // The Path and Freehand tools' points so far (editor pixels), and the
    // pointer for the Path tool's next segment.
    property var pathDraft: []
    property var pathHover: null
    // Saved styles (Options → Button Map → Library), from the window.
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
    property string groupEditId: ""
    property int selectedMember: -1
    property int dragMember: -1
    property string renameId: ""
    property int renameMember: -1
    property int tableRow: -1
    property int tableCol: -1
    property int tableExtra: -1
    property string packWarn: ""
    readonly property real worldPageW: 32000
    readonly property real worldPageH: 18000
    readonly property real innerPageW: 24000
    readonly property real innerPageH: 13500
    readonly property real innerPadX: 0.125
    readonly property real innerPadY: 0.125
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
    property var clip: []
    property bool lineArm: false
    property real lineArmX: 0
    property real lineArmY: 0
    property bool spineHoldArm: false
    property string spineHoldId: ""
    property int spineHoldLeader: 0
    property int spineHoldIndex: -1
    property real spineHoldX: 0
    property real spineHoldY: 0
    property real photoScale: 1
    property real photoOffX: 0
    property real photoOffY: 0
    property real photoRot: 0
    property bool movePhoto: false
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
    // Layers panel flags for the background photo (saved with its pose).
    property bool photoHidden: false
    property bool photoLocked: false
    // The photo's look (Photo → Adjust photo), saved with its pose.
    property real photoBright: 0
    property real photoContrast: 0
    property real photoGrey: 0
    property real photoFade: 0
    // An adjusted copy of the photo for brightness, contrast and greyscale,
    // made by the window (HardwareProfile.adjustedPhotoUrl); "" for none.
    property string photoLookUrl: ""
    readonly property url photoBaseUrl: _photoWell ? _photoWell.baseUrl : ""
    property real photoDragX0: 0
    property real photoDragY0: 0
    signal selectedChanged()
    signal chipMenuRequested(real x, real y)
    signal overlayImportRequested()
    signal historyChanged()
    signal colorPickRequested(string field, string hex)
    // Undo or redo put the photo back; the window's sliders follow.
    signal photoRestored()
    // Press to find: a pressed control that has no chip on the map.
    signal findNotPlaced(string label)
    // Save this style: the window asks for a name.
    signal saveStyleRequested(string kind, string fieldsJson)
    // A ruler guide was added, dropped or removed: the window saves them.
    signal rulerGuidesEdited()

    property var hist
    property int histAt: -1
    property int histCap: 80
    // Degrees per Shift step when turning an item or drawing a line (Options).
    property int rotateSnap: 15
    // Press to find (Options → Button Map → Editing).
    property bool findOn: true
    property bool findAxes: false
    property var findPrev: ({})
    property string findMsg: ""
    // Chip text (Options → Button Map → Labels) and the window's labels for
    // the chosen mode: {"btn:5": "Gear up"}.
    property string chipTextMode: "Name"
    property string unboundText: "Name"
    property var actionLabels: ({})
    property bool _restoring: false
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
    function physicalName(kind, hwId) { return RigChips.physicalName(kind, hwId) }
    function hardwareLabel(kind, hwId) { return RigChips.hardwareLabel(kind, hwId) }
    function defaultFriendly(kind, hwId) { return RigChips.defaultFriendly(kind, hwId) }
    function isClearedFriendly(v) { return RigChips.isClearedFriendly(v) }
    function isUserFriendly(kind, hwId, v) { return RigChips.isUserFriendly(kind, hwId, v) }
    function carryFriendly(v, fallback) { return RigChips.carryFriendly(v, fallback) }
    function friendlyOf(n, mem) { return RigChips.friendlyOf(n, mem) }
    function fullNameOf(kind, hwId) { return RigChips.fullNameOf(kind, hwId) }
    function placedId(kind, hwId) { return RigChips.placedId(kind, hwId) }
    function chipText(n, mem) { return RigChips.chipText(n, mem) }
    function catalog() { return RigChips.catalog() }
    function hotFxOf(n) { return RigChips.hotFxOf(n) }
    function hotFyOf(n) { return RigChips.hotFyOf(n) }
    function addChiplet(kind, hwId, wx, wy, chipOnly) { return RigChips.addChiplet(kind, hwId, wx, wy, chipOnly) }
    function ensureFriendly(n) { return RigChips.ensureFriendly(n) }
    function litOf(kind, hwId) { return RigChips.litOf(kind, hwId) }
    function chipXY(n) { return RigChips.chipXY(n) }
    function pinPt(n, item, side) { return RigChips.pinPt(n, item, side) }
    function chipH(n, mem) { return RigChips.chipH(n, mem) }
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

    // The background photo's pose (scale, offset, rotation) and its frame (rig_photo.js)
    function viewCenterPage() { return RigPhoto.viewCenterPage() }
    function clampPhotoScale(v) { return RigPhoto.clampPhotoScale(v) }
    function clampPhotoOff(v) { return RigPhoto.clampPhotoOff(v) }
    function applyPhotoPose(pose) { return RigPhoto.applyPhotoPose(pose) }
    function resetPhotoPose() { return RigPhoto.resetPhotoPose() }
    function fitPhotoWell() { return RigPhoto.fitPhotoWell() }
    function photoBag() { return RigPhoto.photoBag() }
    function setPhotoLook(key, value) { return RigPhoto.setPhotoLook(key, value) }
    function resetPhotoLook() { return RigPhoto.resetPhotoLook() }
    function pagePhotoRect() { return RigPhoto.pagePhotoRect() }
    function toPhoto(mx, my) { return RigPhoto.toPhoto(mx, my) }

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
    function attachNear(x, y) { return RigLeaders.attachNear(x, y) }
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
    function pinTarget(id) { return RigOverlays.pinTarget(id) }
    function toggleLock(id) { return RigOverlays.toggleLock(id) }
    function beginPlantSnap() { return RigOverlays.beginPlantSnap() }
    function addSocketAt(n, mx, my) { return RigOverlays.addSocketAt(n, mx, my) }
    function socketWorld(n, sock) { return RigOverlays.socketWorld(n, sock) }
    function syncOverlayChips(n) { return RigOverlays.syncOverlayChips(n) }
    function unsnapChip(chipId) { return RigOverlays.unsnapChip(chipId) }
    function snapChipToSocket(chipId, mx, my) { return RigOverlays.snapChipToSocket(chipId, mx, my) }
    function clearSockets() { return RigOverlays.clearSockets() }

    // Drawings (rig_draw.js)
    function isDraw(n) { return RigDraw.isDraw(n) }
    function isTable(n) { return RigDraw.isTable(n) }
    function isText(n) { return RigDraw.isText(n) }
    function drawGeom(n) { return RigDraw.drawGeom(n) }
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
    function toggleLayerFlag(id, part, flag) { return RigLayers.toggleLayerFlag(id, part, flag) }
    function canDeleteLayer(id, part) { return RigLayers.canDeleteLayer(id, part) }
    function deleteLayer(id, part) { return RigLayers.deleteLayer(id, part) }
    function toggleLockSelection() { return RigLayers.toggleLockSelection() }
    function showAll() { return RigLayers.showAll() }
    function unlockAll() { return RigLayers.unlockAll() }
    function layerName(n) { return RigLayers.layerName(n) }
    function renameLayer(id, name) { return RigLayers.renameLayer(id, name) }
    function layerType(n) { return RigLayers.layerType(n) }
    function layerRows(filter, expanded) { return RigLayers.layerRows(filter, expanded) }
    function setPhotoFlag(flag, on) { return RigLayers.setPhotoFlag(flag, on) }

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

    // Transform handles (rig_transform.js)
    function transformModesFor(n) { return RigTransform.transformModesFor(n) }
    function setTransformMode(mode) { return RigTransform.setTransformMode(mode) }
    function canEditPoints(n) { return RigTransform.canEditPoints(n) }
    function hasShaping(n) { return RigTransform.hasShaping(n) }
    function skewMatrix(n, w, h) { return RigTransform.skewMatrix(n, w, h) }
    function transformHandles(n, w, h) { return RigTransform.transformHandles(n, w, h) }
    function transformHandleAt(n, px, py, w, h) { return RigTransform.transformHandleAt(n, px, py, w, h) }
    function dragTransform(n, name, mx, my) { return RigTransform.dragTransform(n, name, mx, my) }
    function convertToPath() { return RigTransform.convertToPath() }
    function resetShape() { return RigTransform.resetShape() }

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
    function isSelected(id) { return RigSelection.isSelected(id) }
    function setSelection(ids) { return RigSelection.setSelection(ids) }
    function toggleSelected(id) { return RigSelection.toggleSelected(id) }
    function cancelAllActions() { return RigSelection.cancelAllActions() }
    function overPool(mx, my) { return RigSelection.overPool(mx, my) }
    function returnToPool() { return RigSelection.returnToPool() }

    // What a pointer drag does to the item being dragged (rig_pointer.js)
    function applyPointer(mx, my, altOff) { return RigPointer.applyPointer(mx, my, altOff) }

    function repaint() {
        tick++
        if (_lines)
            _lines.requestPaint()
    }

    function bump() {
        repaint()
        selectedChanged()
        if (!_restoring)
            pushHist()
    }

    // An undo step: the nodes and the photo's pose and flags.
    function snapJson() {
        try {
            return JSON.stringify({ nodes: nodes || [], photo: photoBag() })
        } catch (e) {
            return "[]"
        }
    }

    function seedHist() {
        hist = [snapJson()]
        histAt = 0
        historyChanged()
    }

    function pushHist() {
        if (_restoring || !interactive)
            return
        var s = snapJson()
        var cur = hist || []
        if (histAt >= 0 && histAt < cur.length && cur[histAt] === s)
            return
        var next = cur.slice(0, histAt + 1)
        next.push(s)
        if (next.length > histCap)
            next = next.slice(next.length - histCap)
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
        if (!Array.isArray(doc) && doc.photo) {
            // The look is saved as plain keys; one left out was not set.
            var ph = doc.photo
            applyPhotoPose(Object.assign({ hidden: false, locked: false }, ph,
                                         { look: { bright: ph.bright, contrast: ph.contrast, grey: ph.grey, fade: ph.fade } }))
            photoRestored()
        }
    }

    // Photo changes from the Adjust photo sliders come many per drag: one undo
    // step once they stop.
    function notePhotoChange() {
        _photoHist.restart()
    }

    function undo() {
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
        } else {
            Qt.callLater(seedHist)
        }
        if (_lines)
            _lines.requestPaint()
    }

    // Physical names from the EVO R lock inventory. Shown as default friendly names.
    readonly property var physNames: ({
        "btn:1": "Red trigger half",
        "btn:2": "Red trigger full",
        "btn:3": "Red head button",
        "btn:4": "White cap",
        "btn:5": "Lower grip white",
        "btn:6": "Head 5-way (right of red) up",
        "btn:7": "Head 5-way (right of red) right",
        "btn:8": "Head 5-way (right of red) down",
        "btn:9": "Head 5-way (right of red) left",
        "btn:10": "Head 5-way (right of red) center",
        "btn:11": "Top-right head 5-way up",
        "btn:12": "Top-right head 5-way right",
        "btn:13": "Top-right head 5-way down",
        "btn:14": "Top-right head 5-way left",
        "btn:15": "Top-right head 5-way center",
        "btn:16": "Silver wheel 5-way up",
        "btn:17": "Silver wheel 5-way right",
        "btn:18": "Silver wheel 5-way down",
        "btn:19": "Silver wheel 5-way left",
        "btn:20": "Silver wheel 5-way center",
        "btn:21": "Grey paddle push",
        "btn:22": "Grey paddle pull",
        "btn:23": "En2 right knob up",
        "btn:24": "En2 right knob down",
        "btn:25": "En1 left knob up",
        "btn:26": "En1 left knob down",
        "btn:27": "Middle base pad",
        "btn:28": "Left base pad",
        "btn:29": "Right base pad",
        "hat:1": "Analog ministick",
        "axis:1": "Stick X roll",
        "axis:2": "Stick Y pitch",
        "axis:3": "Stick Z twist",
        "axis:4": "Z slider (En1–En2)"
    })

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
        function onWidthChanged() { _lines.requestPaint(); if (_grid) _grid.requestPaint() }
        function onHeightChanged() { _lines.requestPaint(); if (_grid) _grid.requestPaint() }
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
            // tick: hiding changes the node in place, not the node object.
            visible: { _ed.tick; return node !== null && !node.hidden }
            x: {
                _ed.tick
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
                _ed.tick
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
            rotation: { _ed.tick; return (_ed.isDraw(node) && node.rot) ? node.rot : 0 }
            opacity: { _ed.tick; return (_ed.isDraw(node) && node.opacity !== undefined && node.opacity !== null) ? node.opacity : 1 }
            transformOrigin: Item.Center
            clip: false
            width: {
                _ed.tick
                if (!node)
                    return 40
                if (_ed.isDraw(node))
                    return _ed.drawGeom(node).w
                if (_ed.isGroup(node))
                    return _ed.groupSpanW(node)
                return (_body.item && _body.item.implicitWidth > 1) ? _body.item.implicitWidth : _ed.chipWGuess(node, null)
            }
            height: {
                _ed.tick
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
                    _ed.tick
                    if (_wrap.node && (_ed.isGroup(_wrap.node) || _ed.isDraw(_wrap.node)))
                        return _wrap.width
                    return item ? item.implicitWidth : 0
                }
                height: {
                    _ed.tick
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
                    if (_wrap.node && _ed.isGroup(_wrap.node))
                        _ed.ensureMemberOffsets(_wrap.node)
                    if (_wrap.node && _ed.isTable(_wrap.node))
                        _ed.ensureTable(_wrap.node)
                }
            }
        }
    }

    RigLeaderLayer { id: _lines; ed: _ed; z: _ed.leaderLayerZ() }
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

    onWidthChanged: { _lines.requestPaint(); if (_grid) _grid.requestPaint() }
    onHeightChanged: { _lines.requestPaint(); if (_grid) _grid.requestPaint() }
    onTickChanged: _lines.requestPaint()
    onGridOnChanged: if (_grid) _grid.requestPaint()
    onGridSizeChanged: if (_grid) _grid.requestPaint()
    onNodesChanged: {
        seeded = false
        _lines.requestPaint()
        _seedTimer.restart()
    }

    Timer {
        id: _seedTimer
        interval: 80
        repeat: false
        onTriggered: {
            var list = _ed.nodes || []
            _ed.normalizeStacking()
            _ed.demoteSpecialKinds()
            for (var i = 0; i < list.length; i++) {
                _ed.ensureFriendly(list[i])
                _ed.ensureMidSpine(list[i])
            }
            _ed.seeded = true
            _ed.bump()
        }
    }

    RigPhotoLayer { id: _photoWell; ed: _ed; linesCanvas: _lines }

    RigGuides { id: _guides; ed: _ed; z: 3 }

    RigGrid { id: _grid; ed: _ed }

    RigPointerArea {
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
        delay: 400
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
        renderType: Text.NativeRendering
        id: _textFit
        visible: false
        width: 100
        wrapMode: Text.WordWrap
        font.pixelSize: 12
    }

    TextInput {
        id: _nameEdit
        z: 12
        visible: _ed.showChrome && _ed.renameId.length > 0
        x: {
            _ed.tick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return _ed.chipScreenRect(n, mem).x
        }
        y: {
            _ed.tick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return _ed.chipScreenRect(n, mem).y
        }
        width: {
            _ed.tick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return Math.max(Style.dp(48), _ed.chipScreenRect(n, mem).width)
        }
        height: {
            _ed.tick
            var n = _ed.nodeAt(_ed.renameId)
            var mem = (_ed.renameMember >= 0 && n && n.members) ? n.members[_ed.renameMember] : null
            return Math.max(18, _ed.chipScreenRect(n, mem).height)
        }
        transformOrigin: Item.Center
        rotation: {
            _ed.tick
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
        horizontalAlignment: TextInput.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter
        selectByMouse: true
        clip: true
        leftPadding: Style.dp(4)
        rightPadding: Style.dp(4)
        onTextChanged: _ed.renameDraft = text
        onAccepted: _ed.commitRename()
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

    // Several items selected: a dashed box round them and one rotate handle
    // above it, to turn them together.
    Item {
        id: _turnFrame
        z: 8
        visible: { _ed.tick; return _ed.showChrome && _ed.canTurnTogether() && _ed.dragKind !== "band" }
        readonly property var box: { _ed.tick; return _ed.selectionBounds() }
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
        Text {
            visible: _ed.dragKind === "turn"
            x: parent.width / 2 + 10
            y: -_ed.rotateHandleOffset - 10
            color: _ed.handleFill
            font.pixelSize: Style.dp(11)
            text: Math.round(_ed.turnAngle) + "°"
        }
    }

    // The mode's name on each page of File → Export modes.
    Text {
        z: 9
        visible: _ed.exporting && _ed.exportTitle.length > 0
        x: { _ed.tick; return _ed.spaceRect().x + _ed.spaceRect().w * 0.02 }
        y: { _ed.tick; return _ed.spaceRect().y + _ed.spaceRect().h * 0.02 }
        color: _ed.printLight ? "black" : Style.fg
        font.pixelSize: { _ed.tick; return _ed.uiPx(28) }
        font.bold: true
        text: _ed.exportTitle
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
        x: Math.min(_ed.drawX0, _ed.drawX1)
        y: Math.min(_ed.drawY0, _ed.drawY1)
        width: Math.max(1, Math.abs(_ed.drawX1 - _ed.drawX0))
        height: Math.max(1, Math.abs(_ed.drawY1 - _ed.drawY0))
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
            if (_lines)
                _lines.requestPaint()
            if (!_ed.hotPulsing())
                stop()
        }
    }

    Timer {
        id: _photoHist
        interval: 400
        repeat: false
        onTriggered: _ed.pushHist()
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
        function close() { _menu.close() }
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
