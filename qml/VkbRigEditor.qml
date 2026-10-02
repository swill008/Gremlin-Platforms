// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style
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
    property real photoDragX0: 0
    property real photoDragY0: 0
    signal selectedChanged()
    signal chipMenuRequested(real x, real y)
    signal overlayImportRequested()
    signal historyChanged()
    signal colorPickRequested(string field, string hex)

    property var hist
    property int histAt: -1
    property int histCap: 80
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
    function catalog() { return RigChips.catalog() }
    function hotFxOf(n) { return RigChips.hotFxOf(n) }
    function hotFyOf(n) { return RigChips.hotFyOf(n) }
    function addChiplet(kind, hwId, wx, wy) { return RigChips.addChiplet(kind, hwId, wx, wy) }
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
    function addOverlay(rel, fileUrl) { return RigOverlays.addOverlay(rel, fileUrl) }
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
    function paintDraw(ctx, n, w, h) { return RigDraw.paintDraw(ctx, n, w, h) }

    // Selection, nudging, delete, copy/paste/duplicate and stacking order (rig_selection.js)
    function deleteSelection() { return RigSelection.deleteSelection() }
    function deleteChip(id) { return RigSelection.deleteChip(id) }
    function nudge(dx, dy) { return RigSelection.nudge(dx, dy) }
    function _newId(n) { return RigSelection._newId(n) }
    function shiftClone(n, dx, dy) { return RigSelection.shiftClone(n, dx, dy) }
    function pasteNodes(src, dx, dy) { return RigSelection.pasteNodes(src, dx, dy) }
    function duplicateSelection() { return RigSelection.duplicateSelection() }
    function copySelection() { return RigSelection.copySelection() }
    function pasteClipboard() { return RigSelection.pasteClipboard() }
    function bringForward() { return RigSelection.bringForward() }
    function sendBack() { return RigSelection.sendBack() }
    function isSelected(id) { return RigSelection.isSelected(id) }
    function setSelection(ids) { return RigSelection.setSelection(ids) }
    function toggleSelected(id) { return RigSelection.toggleSelected(id) }
    function cancelAllActions() { return RigSelection.cancelAllActions() }

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

    function snapJson() {
        try {
            return JSON.stringify(nodes || [])
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
        var next = []
        try {
            next = JSON.parse(s)
        } catch (e) {
            return
        }
        var list = nodes
        if (!list)
            return
        list.splice(0, list.length)
        for (var i = 0; i < next.length; i++)
            list.push(next[i])
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
            visible: node !== null
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
            z: {
                _ed.tick
                if (!node)
                    return 0
                if (node.zLayer !== undefined && node.zLayer !== null)
                    return node.zLayer
                return _ed.isDraw(node) ? 2 : 3
            }
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

    RigGuides { id: _guides; ed: _ed }

    RigGrid { id: _grid; ed: _ed }

    RigLeaderLayer { id: _lines; ed: _ed }

    RigPointerArea {
        ed: _ed
        chipMenu: _ctx
        tableMenu: _tableCtx
        textMenu: _textCtx
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
        visible: _ed.interactive && _ed.renameId.length > 0
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

    Text {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: Style.dp(6)
        z: 9
        visible: _ed.interactive && text.length
        color: "#A1A1AA"
        font.pixelSize: Style.dp(10)
        text: {
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
        visible: _ed.interactive && _ed.dragKind === "drawnew"
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

    Menu {
        id: _tableCtx
        MenuItem {
            text: "Add row below"
            onTriggered: _ed.addTableRow(true)
        }
        MenuItem {
            text: "Insert row above"
            onTriggered: _ed.addTableRow(false)
        }
        MenuItem {
            text: "Delete this row"
            enabled: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.rows && n.rows.length > 1)
            }
            onTriggered: _ed.deleteTableRow()
        }
        MenuSeparator {}
        MenuItem {
            text: "Add column right"
            onTriggered: _ed.addTableCol(true)
        }
        MenuItem {
            text: "Insert column left"
            onTriggered: _ed.addTableCol(false)
        }
        MenuItem {
            text: "Delete this column"
            enabled: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.cols > 1)
            }
            onTriggered: _ed.deleteTableCol()
        }
        MenuItem {
            text: "ID column"
            checkable: true
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.idCol)
            }
            onTriggered: _ed.toggleTableIdCol()
        }
        MenuItem {
            text: "Free position"
            checkable: true
            enabled: {
                _ed.tick
                return _ed.tableHasTarget()
            }
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                var c = _ed.tableCurrentCell(n)
                return !!(c && c.free)
            }
            onTriggered: _ed.toggleTableCellFree()
        }
        MenuItem {
            text: "Independent of table"
            checkable: true
            enabled: {
                _ed.tick
                return _ed.tableHasTarget()
            }
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                var c = _ed.tableCurrentCell(n)
                return !!(c && c.independent)
            }
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                var c = _ed.tableCurrentCell(n)
                _ed.setTableCellIndependent(!(c && c.independent))
            }
        }
        MenuItem {
            text: "Spawn empty cell"
            onTriggered: _ed.spawnEmptyCell()
        }
        MenuItem {
            text: "Delete this cell"
            enabled: {
                _ed.tick
                return _ed.tableExtra >= 0
            }
            onTriggered: _ed.deleteThisTableCell()
        }
        Menu {
            title: "Place"
            enabled: {
                _ed.tick
                return _ed.tableHasTarget()
            }
            MenuItem { text: "Far left"; onTriggered: _ed.placeTableCell("left") }
            MenuItem { text: "Center"; onTriggered: _ed.placeTableCell("center") }
            MenuItem { text: "Far right"; onTriggered: _ed.placeTableCell("right") }
            MenuSeparator {}
            MenuItem { text: "Top"; onTriggered: _ed.placeTableCell("top") }
            MenuItem { text: "Middle"; onTriggered: _ed.placeTableCell("middle") }
            MenuItem { text: "Bottom"; onTriggered: _ed.placeTableCell("bottom") }
        }
        MenuSeparator {}
        Menu {
            title: "Theme"
            MenuItem {
                text: "Gremlin dark"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || !n.theme || n.theme === "gremlin"
                }
                onTriggered: _ed.setTableTheme("gremlin")
            }
            MenuItem {
                text: "Gremlin hollow"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.theme === "hollow")
                }
                onTriggered: _ed.setTableTheme("hollow")
            }
            MenuItem {
                text: "Sheet"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.theme === "sheet")
                }
                onTriggered: _ed.setTableTheme("sheet")
            }
        }
        Menu {
            title: "Font size"
            MenuItem {
                text: "8"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 8)
                }
                onTriggered: _ed.setTableFont(8)
            }
            MenuItem {
                text: "10"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || !n.fontSize || n.fontSize === 10
                }
                onTriggered: _ed.setTableFont(10)
            }
            MenuItem {
                text: "12"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 12)
                }
                onTriggered: _ed.setTableFont(12)
            }
            MenuItem {
                text: "14"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 14)
                }
                onTriggered: _ed.setTableFont(14)
            }
            MenuItem {
                text: "16"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 16)
                }
                onTriggered: _ed.setTableFont(16)
            }
        }
        MenuSeparator {}
        MenuItem {
            text: "Break group"
            enabled: {
                _ed.tick
                return _ed.canUngroup()
            }
            onTriggered: _ed.ungroupSelection()
        }
        MenuItem {
            text: {
                _ed.tick
                var n = _ed.pinTarget()
                return _ed.isLocked(n) ? "Unpin" : "Pin"
            }
            checkable: true
            checked: {
                _ed.tick
                return _ed.isLocked(_ed.pinTarget())
            }
            onTriggered: {
                var n = _ed.pinTarget()
                if (n)
                    _ed.toggleLock(n.id)
            }
        }
        MenuItem {
            text: "Bring forward"
            onTriggered: _ed.bringForward()
        }
        MenuItem {
            text: "Send back"
            onTriggered: _ed.sendBack()
        }
        MenuSeparator {}
        MenuItem {
            text: "Delete table"
            onTriggered: _ed.deleteTable()
        }
    }

    Menu {
        id: _textCtx
        MenuItem {
            text: "Edit text…"
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                if (_ed.isText(n))
                    _ed.beginTextRename(n.id)
            }
        }
        MenuItem { text: "Delete text box"; onTriggered: _ed.deleteChip() }
        MenuItem { text: "Duplicate"; onTriggered: _ed.duplicateSelection() }
        MenuItem { text: "Copy format"; onTriggered: _ed.copyTextFormat() }
        MenuItem { text: "Copy text"; onTriggered: _ed.copyTextPlain() }
        MenuItem { text: "Clear formatting"; onTriggered: _ed.clearTextFormat() }
        MenuItem {
            text: "Paint format"
            enabled: {
                _ed.tick
                return !!_ed.textFormatClip
            }
            checkable: true
            checked: {
                _ed.tick
                return _ed.textPaintOn
            }
            onTriggered: {
                if (!_ed.textFormatClip)
                    return
                _ed.applyTextFormat()
                _ed.textPaintOn = true
                _ed.bump()
            }
        }
        MenuSeparator {}
        Menu {
            title: "Size"
            MenuItem {
                text: "Caption  72×20"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(72, 20)
                }
                onTriggered: _ed.applyTextBoxSize(72, 20)
            }
            MenuItem {
                text: "Small  96×24"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(96, 24)
                }
                onTriggered: _ed.applyTextBoxSize(96, 24)
            }
            MenuItem {
                text: "Medium  128×32"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(128, 32)
                }
                onTriggered: _ed.applyTextBoxSize(128, 32)
            }
            MenuItem {
                text: "Large  176×40"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(176, 40)
                }
                onTriggered: _ed.applyTextBoxSize(176, 40)
            }
            MenuItem {
                text: "Title  240×48"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(240, 48)
                }
                onTriggered: _ed.applyTextBoxSize(240, 48)
            }
            MenuItem {
                text: "Wide  280×28"
                checkable: true
                checked: {
                    _ed.tick
                    return _ed.textBoxSizeEq(280, 28)
                }
                onTriggered: _ed.applyTextBoxSize(280, 28)
            }
        }
        Menu {
            title: "Theme"
            MenuItem {
                text: "Gremlin dark"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || !n.theme || n.theme === "gremlin"
                }
                onTriggered: _ed.applyTextTheme("gremlin")
            }
            MenuItem {
                text: "Gremlin hollow"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.theme === "hollow")
                }
                onTriggered: _ed.applyTextTheme("hollow")
            }
            MenuItem {
                text: "Sheet"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.theme === "sheet")
                }
                onTriggered: _ed.applyTextTheme("sheet")
            }
        }
        Menu {
            title: "Font"
            MenuItem {
                text: "8"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 8)
                }
                onTriggered: _ed.applyField("fontSize", 8)
            }
            MenuItem {
                text: "10"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 10)
                }
                onTriggered: _ed.applyField("fontSize", 10)
            }
            MenuItem {
                text: "12"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || !n.fontSize || n.fontSize === 12
                }
                onTriggered: _ed.applyField("fontSize", 12)
            }
            MenuItem {
                text: "14"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 14)
                }
                onTriggered: _ed.applyField("fontSize", 14)
            }
            MenuItem {
                text: "16"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 16)
                }
                onTriggered: _ed.applyField("fontSize", 16)
            }
            MenuItem {
                text: "18"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 18)
                }
                onTriggered: _ed.applyField("fontSize", 18)
            }
            MenuItem {
                text: "24"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fontSize === 24)
                }
                onTriggered: _ed.applyField("fontSize", 24)
            }
        }
        Menu {
            title: "Color"
            MenuItem { text: "Text…"; onTriggered: _ed.requestDrawColor("textColor") }
            MenuItem { text: "Fill…"; onTriggered: _ed.requestDrawColor("color") }
            MenuItem { text: "Stroke…"; onTriggered: _ed.requestDrawColor("border") }
        }
        Menu {
            title: "Opacity"
            Menu {
            title: "Fill"
            MenuItem {
                text: "0%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fillOpacity === 0)
                }
                onTriggered: _ed.applyField("fillOpacity", 0)
            }
            MenuItem {
                text: "25%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fillOpacity === 0.25)
                }
                onTriggered: _ed.applyField("fillOpacity", 0.25)
            }
            MenuItem {
                text: "50%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fillOpacity === 0.5)
                }
                onTriggered: _ed.applyField("fillOpacity", 0.5)
            }
            MenuItem {
                text: "75%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.fillOpacity === 0.75)
                }
                onTriggered: _ed.applyField("fillOpacity", 0.75)
            }
            MenuItem {
                text: "100%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || n.fillOpacity === undefined || n.fillOpacity === 1
                }
                onTriggered: _ed.applyField("fillOpacity", 1)
            }
        }
        Menu {
            title: "Stroke"
            MenuItem {
                text: "0%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.borderOpacity === 0)
                }
                onTriggered: _ed.applyField("borderOpacity", 0)
            }
            MenuItem {
                text: "25%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.borderOpacity === 0.25)
                }
                onTriggered: _ed.applyField("borderOpacity", 0.25)
            }
            MenuItem {
                text: "50%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.borderOpacity === 0.5)
                }
                onTriggered: _ed.applyField("borderOpacity", 0.5)
            }
            MenuItem {
                text: "75%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && n.borderOpacity === 0.75)
                }
                onTriggered: _ed.applyField("borderOpacity", 0.75)
            }
            MenuItem {
                text: "100%"
                checkable: true
                checked: {
                    _ed.tick
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || n.borderOpacity === undefined || n.borderOpacity === 1
                }
                onTriggered: _ed.applyField("borderOpacity", 1)
            }
        }
        }
        Menu {
            title: "Align"
            MenuItem { text: "Left"; onTriggered: _ed.applyField("align", "left") }
            MenuItem { text: "Center"; onTriggered: _ed.applyField("align", "center") }
            MenuItem { text: "Right"; onTriggered: _ed.applyField("align", "right") }
            MenuSeparator {}
            MenuItem { text: "Top"; onTriggered: _ed.applyField("valign", "top") }
            MenuItem { text: "Middle"; onTriggered: _ed.applyField("valign", "middle") }
            MenuItem { text: "Bottom"; onTriggered: _ed.applyField("valign", "bottom") }
        }
        MenuItem {
            text: "Bold"
            checkable: true
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.bold)
            }
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                _ed.applyField("bold", !(n && n.bold))
            }
        }
        MenuItem {
            text: "Word wrap"
            checkable: true
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !n || n.wrap !== false
            }
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                _ed.applyField("wrap", !(n && n.wrap !== false))
            }
        }
        MenuItem {
            text: "Scale font with box"
            checkable: true
            checked: {
                _ed.tick
                var n = _ed.nodeAt(_ed.selectedId)
                return !!(n && n.scaleFont)
            }
            onTriggered: {
                var n = _ed.nodeAt(_ed.selectedId)
                _ed.applyField("scaleFont", !(n && n.scaleFont))
            }
        }
        MenuSeparator {}
        MenuItem {
            text: {
                _ed.tick
                var n = _ed.pinTarget()
                return _ed.isLocked(n) ? "Unpin" : "Pin"
            }
            checkable: true
            checked: {
                _ed.tick
                return _ed.isLocked(_ed.pinTarget())
            }
            onTriggered: {
                var n = _ed.pinTarget()
                if (n)
                    _ed.toggleLock(n.id)
            }
        }
        MenuItem { text: "Bring forward"; onTriggered: _ed.bringForward() }
        MenuItem { text: "Send back"; onTriggered: _ed.sendBack() }
    }

    Menu {
        id: _ctx
        property string nodeId: ""
        property string kind: ""
        property int seg: -1
        property int leader: 0
        MenuItem {
            text: "Undo"
            enabled: _ed.canUndo
            onTriggered: _ed.undo()
        }
        MenuItem {
            text: "Redo"
            enabled: _ed.canRedo
            onTriggered: _ed.redo()
        }
        MenuItem {
            text: "Clear Format"
            enabled: _ed.isGroup(_ed.ctxTarget()) && _ed.ctxHasGroupFormat()
            onTriggered: _ed.clearGroupFormat()
        }
        MenuSeparator {}
        Menu {
            title: "Chip"
            enabled: {
                var n = _ed.ctxTarget()
                return !!(n && !_ed.isDraw(n))
            }


            MenuItem {
                enabled: false
                text: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    var mem = _ed.targetMember()
                    if (n && mem)
                        return (n.id || "group") + " · " + (_ed.roleWord(_ed.fiveWayRole(mem)) || _ed.memberLabel(n, mem))
                    return n ? (_ed.friendlyOf(n, mem) || n.id || "Chip") : "Chip"
                }
            }
            MenuItem {
                text: "Rename"
                enabled: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!(n && !_ed.isDraw(n))
                }
                onTriggered: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    if (!n)
                        return
                    var mem = _ed.targetMember()
                    var mi = -1
                    if (mem && n.members) {
                        for (var i = 0; i < n.members.length; i++) {
                            if (n.members[i] === mem) {
                                mi = i
                                break
                            }
                        }
                    }
                    _ed.beginRename(n.id, mi)
                }
            }
            MenuSeparator {}
            Menu {
                id: _fontMenu
                title: "Font size"
                Instantiator {
                    model: [8, 9, 10, 11, 12, 14, 16, 18, 20, 22]
                    delegate: MenuItem {
                        required property int modelData
                        text: "" + modelData
                        checkable: true
                        checked: _ed.fieldEq("fontSize", modelData, 10)
                        onTriggered: _ed.applyField("fontSize", modelData)
                    }
                    onObjectAdded: (i, obj) => _fontMenu.insertItem(i, obj)
                    onObjectRemoved: (i, obj) => _fontMenu.removeItem(obj)
                }
            }
            Menu {
                title: "Chip"
                Menu {
                    id: _chipSzMenu
                    title: "Size"
                    Instantiator {
                        model: [12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 42, 48]
                        delegate: MenuItem {
                            required property int modelData
                            text: "" + modelData
                            checkable: true
                            checked: _ed.fieldEq("chipSize", modelData, 18)
                            onTriggered: _ed.applyField("chipSize", modelData)
                        }
                        onObjectAdded: (i, obj) => _chipSzMenu.insertItem(i, obj)
                        onObjectRemoved: (i, obj) => _chipSzMenu.removeItem(obj)
                    }
                }
                MenuItem {
                    text: "Round"
                    checkable: true
                    checked: _ed.fieldEq("chipShape", "round", "round")
                    onTriggered: _ed.applyField("chipShape", "round")
                }
                MenuItem {
                    text: "Square"
                    checkable: true
                    checked: _ed.fieldEq("chipShape", "square", "round")
                    onTriggered: _ed.applyField("chipShape", "square")
                }
                MenuSeparator {}
                MenuItem {
                    text: "Filled"
                    checkable: true
                    checked: _ed.fieldEq("chipFill", "filled", "filled")
                    onTriggered: _ed.applyField("chipFill", "filled")
                }
                MenuItem {
                    text: "Hollow"
                    checkable: true
                    checked: _ed.fieldEq("chipFill", "hollow", "filled")
                    onTriggered: _ed.applyField("chipFill", "hollow")
                }
                MenuSeparator {}
                MenuItem {
                    text: "Reset this cell"
                    enabled: _ed.targetMember() !== null
                    onTriggered: _ed.resetMemberStyle()
                }
            }
            Menu {
                title: "Colors"
                MenuItem { text: "Fill…"; onTriggered: _ed.pickColor("color") }
                MenuItem { text: "Outline…"; onTriggered: _ed.pickColor("border") }
                MenuItem { text: "Text…"; onTriggered: _ed.pickColor("textColor") }
                MenuSeparator {}
                MenuItem { text: "Pressed fill…"; onTriggered: _ed.pickColor("hlColor") }
                MenuItem { text: "Pressed outline…"; onTriggered: _ed.pickColor("hlBorder") }
                MenuItem { text: "Pressed text…"; onTriggered: _ed.pickColor("hlText") }
            }
            MenuItem {
                text: "Highlight on press"
                checkable: true
                checked: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !n || n.highlight !== false
                }
                onTriggered: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    _ed.applyField("highlight", !(n && n.highlight !== false))
                }
            }
            MenuSeparator {}
            MenuItem {
                text: "Delete chip"
                enabled: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return !!n && !_ed.isGroup(n) && !_ed.isDraw(n)
                }
                onTriggered: _ed.deleteChip()
            }
        
            
        }
        Menu {
            title: "Hotspot"
            enabled: {
                var n = _ed.ctxTarget()
                return !!(n && !_ed.isDraw(n))
            }


            Menu {
                id: _hotSzMenu
                title: "Size"
                Instantiator {
                    model: [4, 6, 8, 9, 10, 12, 14, 16, 20, 24, 28]
                    delegate: MenuItem {
                        required property int modelData
                        text: "" + modelData
                        checkable: true
                        checked: _ed.fieldEq("hotSize", modelData, 9)
                        onTriggered: _ed.applyField("hotSize", modelData)
                    }
                    onObjectAdded: (i, obj) => _hotSzMenu.insertItem(i, obj)
                    onObjectRemoved: (i, obj) => _hotSzMenu.removeItem(obj)
                }
            }
            MenuItem {
                text: "Round"
                checkable: true
                checked: _ed.fieldEq("hotShape", "round", "round")
                onTriggered: _ed.applyField("hotShape", "round")
            }
            MenuItem {
                text: "Square"
                checkable: true
                checked: _ed.fieldEq("hotShape", "square", "round")
                onTriggered: _ed.applyField("hotShape", "square")
            }
            MenuSeparator {}
            MenuItem {
                text: "Filled"
                checkable: true
                checked: _ed.fieldEq("hotFill", "filled", "filled")
                onTriggered: _ed.applyField("hotFill", "filled")
            }
            MenuItem {
                text: "Hollow"
                checkable: true
                checked: _ed.fieldEq("hotFill", "hollow", "filled")
                onTriggered: _ed.applyField("hotFill", "hollow")
            }
            MenuSeparator {}
            MenuItem { text: "Color…"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.pickColor("hotColor") } }
        
            
        }
        Menu {
            title: "Leader End"
            enabled: {
                var n = _ed.ctxTarget()
                return !!(n && !_ed.isDraw(n))
            }


            MenuItem { text: "Detach chip end"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.detachEnd("from") } }
            MenuItem { text: "Detach hotspot end"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.detachEnd("to") } }
            MenuSeparator {}
            MenuItem { text: "Reconnect to this chip"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.attachEndToSelf("from") } }
            MenuItem { text: "Reconnect to this hotspot"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.attachEndToSelf("to") } }
        
            
        }
        Menu {
            title: "Group"
            enabled: _ed.canGroup() || _ed.canUngroup() || _ed.isGroup(_ed.ctxTarget()) || _ed.groupEditId !== ""


            MenuItem {
                text: "Group selected"
                enabled: _ed.canGroup()
                onTriggered: _ed.groupSelection()
            }
            MenuItem {
                text: "Break group"
                enabled: {
                    _ed.tick
                    return _ed.canUngroup() || _ed.isGroup(_ed.ctxTarget())
                }
                onTriggered: _ed.ungroupSelection()
            }
            MenuItem {
                text: "Edit group"
                enabled: _ed.isGroup(_ed.ctxTarget())
                onTriggered: _ed.beginGroupEdit(_ctx.nodeId)
            }
            MenuItem {
                text: "Done editing group"
                enabled: _ed.groupEditId !== ""
                onTriggered: _ed.endGroupEdit()
            }
        
            
        }
        Menu {
            title: "Format"
            enabled: _ed.isFiveWay(_ed.ctxTarget()) || _ed.ctxHasTheme()


            Menu {
                title: "5-Way"
                enabled: _ed.isFiveWay(_ed.ctxTarget())
                MenuItem {
                    text: "Plus cluster"
                    checkable: true
                    checked: _ed.fiveWayFormat(_ed.ctxTarget()) === "plus"
                    onTriggered: {
                        _ed.selectedId = _ctx.nodeId || _ed.selectedId
                        _ed.applyFiveWayFormat("plus")
                    }
                }
                MenuItem {
                    text: "Mini hat"
                    checkable: true
                    checked: _ed.fiveWayFormat(_ed.ctxTarget()) === "mini"
                    onTriggered: {
                        _ed.selectedId = _ctx.nodeId || _ed.selectedId
                        _ed.applyFiveWayFormat("mini")
                    }
                }
                MenuItem {
                    text: "Named card"
                    checkable: true
                    checked: _ed.fiveWayFormat(_ed.ctxTarget()) === "card"
                    onTriggered: {
                        _ed.selectedId = _ctx.nodeId || _ed.selectedId
                        _ed.applyFiveWayFormat("card")
                    }
                }
                MenuItem {
                    text: "Radial leaders"
                    checkable: true
                    checked: _ed.fiveWayFormat(_ed.ctxTarget()) === "radial"
                    onTriggered: {
                        _ed.selectedId = _ctx.nodeId || _ed.selectedId
                        _ed.applyFiveWayFormat("radial")
                    }
                }
            }
            MenuItem {
                text: "Clear Format"
                enabled: _ed.ctxHasGroupFormat()
                onTriggered: _ed.clearGroupFormat()
            }
        
            
        }
        Menu {
            title: "Align"
            enabled: _ed.isGroup(_ed.ctxTarget())


            MenuItem { text: "Align left"; enabled: _ed.isGroup(_ed.ctxTarget()); onTriggered: _ed.setAlignH("left") }
            MenuItem { text: "Align center"; enabled: _ed.isGroup(_ed.ctxTarget()); onTriggered: _ed.setAlignH("center") }
            MenuItem { text: "Align right"; enabled: _ed.isGroup(_ed.ctxTarget()); onTriggered: _ed.setAlignH("right") }
            MenuItem { text: "Free layout"; enabled: _ed.isGroup(_ed.ctxTarget()); onTriggered: _ed.setAlignH("free") }
        
            
        }
        Menu {
            title: "Leader"
            enabled: {
                var n = _ed.ctxTarget()
                return !!(n && !_ed.isDraw(n))
            }


            MenuItem { text: "Color…"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.pickColor("leaderColor") } }
            Menu {
                id: _leadWMenu
                title: "Weight"
                Instantiator {
                    model: [8, 11, 15, 20, 25, 30, 40]
                    delegate: MenuItem {
                        required property int modelData
                        text: (modelData / 10).toFixed(1)
                        checkable: true
                        checked: {
                            var n = _ed.nodeAt(_ed.selectedId)
                            return Math.round(_ed.leaderWidthOf(n) * 10) === modelData
                        }
                        onTriggered: _ed.applyField("leaderWidth", modelData / 10)
                    }
                    onObjectAdded: (i, obj) => _leadWMenu.insertItem(i, obj)
                    onObjectRemoved: (i, obj) => _leadWMenu.removeItem(obj)
                }
            }
            MenuSeparator {}
            MenuItem { text: "Add straight spine"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.ensureMidSpine(_ed.nodeAt(_ed.selectedId)); _ed.bump() } }
            MenuItem { text: "Convert spine"; enabled: _ed.ctxHasSelectedSpine(); onTriggered: _ed.convertSelectedSpine() }
            MenuItem { text: "Add curved spine"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.addCurveSpine(_ed.nodeAt(_ed.selectedId)) } }
            Menu {
                title: "This segment"
                MenuItem { text: "Curved"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.selectedLeader = _ctx.leader; _ed.selectedSeg = _ctx.seg; _ed.setSegCurve(_ed.currentLeader(_ed.nodeAt(_ed.selectedId)), Math.max(0, _ctx.seg), true) } }
                MenuItem { text: "Straight"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.selectedLeader = _ctx.leader; _ed.selectedSeg = _ctx.seg; _ed.setSegCurve(_ed.currentLeader(_ed.nodeAt(_ed.selectedId)), Math.max(0, _ctx.seg), false) } }
            }
            Menu {
                title: "All segments"
                MenuItem { text: "Curved"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.setAllSegCurve(true) } }
                MenuItem { text: "Straight"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.setAllSegCurve(false) } }
            }
            MenuSeparator {}
            MenuItem { text: "Add leader"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.addLeader() } }
            MenuItem { text: "Branch from this end"; onTriggered: { _ed.selectedId = _ctx.nodeId || _ed.selectedId; _ed.selectedLeader = _ctx.leader; _ed.addBranch() } }
            MenuItem {
                text: "Clear all spines"
                enabled: {
                    var id = _ctx.nodeId || _ed.selectedId
                    var n = _ed.nodeAt(id)
                    return !!(n && !_ed.isDraw(n))
                }
                onTriggered: {
                    var id = _ctx.nodeId || _ed.selectedId
                    if (!_ed.nodeAt(id))
                        return
                    _ed.selectedId = id
                    _ed.clearAllSpines(id)
                }
            }
            MenuItem {
                text: "Delete spine"
                enabled: _ed.selectedSpine >= 0
                onTriggered: {
                    _ed.selectedId = _ctx.nodeId || _ed.selectedId
                    _ed.selectedLeader = _ctx.leader
                    _ed.deleteSelection()
                }
            }
            MenuItem {
                text: {
                    _ed.tick
                    var ids = _ed.selectedIds || []
                    return ids.length > 1 ? "Delete leaders" : "Delete leader"
                }
                enabled: {
                    var ids = (_ed.selectedIds && _ed.selectedIds.length) ? _ed.selectedIds : [_ed.selectedId]
                    var i
                    for (i = 0; i < ids.length; i++) {
                        var n = _ed.nodeAt(ids[i])
                        if (n && !_ed.isDraw(n) && _ed.leaderList(n).length)
                            return true
                    }
                    return false
                }
                onTriggered: {
                    _ed.deleteLeader()
                }
            }
        
            
        }
        Menu {
            title: "Draw"
            enabled: true

            MenuItem {
                text: { _ed.tick; var n = _ed.ctxTarget(); return _ed.isLocked(n) ? "Unpin overlay" : "Pin overlay" }
                enabled: { var n = _ed.ctxTarget(); return _ed.isOverlay(n) || _ed.isDraw(n) }
                onTriggered: {
                    _ed.selectedId = _ctx.nodeId || _ed.selectedId
                    _ed.toggleLock()
                }
            }
            MenuItem {
                text: _ed.plantSnap ? "Click overlay to plant snap…" : "Add snap point"
                enabled: { var n = _ed.ctxTarget(); return _ed.isOverlay(n) }
                onTriggered: {
                    _ed.selectedId = _ctx.nodeId || _ed.selectedId
                    _ed.beginPlantSnap()
                }
            }
            MenuItem {
                text: "Clear snap points"
                enabled: {
                    var n = _ed.ctxTarget()
                    return !!(n && n.sockets && n.sockets.length)
                }
                onTriggered: {
                    _ed.selectedId = _ctx.nodeId || _ed.selectedId
                    _ed.clearSockets()
                }
            }
            MenuSeparator {}

            Menu {
                title: "Around selection"
                enabled: {
                    var ids = _ed.selectedIds || []
                    var k
                    for (k = 0; k < ids.length; k++) {
                        if (!_ed.isDraw(_ed.nodeAt(ids[k])))
                            return true
                    }
                    return false
                }
                MenuItem { text: "Rectangle"; onTriggered: _ed.addDrawAround("rect") }
                MenuItem { text: "Rounded"; onTriggered: _ed.addDrawAround("roundrect") }
                MenuItem { text: "Ellipse"; onTriggered: _ed.addDrawAround("ellipse") }
                MenuItem { text: "Triangle"; onTriggered: _ed.addDrawAround("triangle") }
                MenuItem { text: "Diamond"; onTriggered: _ed.addDrawAround("diamond") }
            }
            Menu {
                title: "Free drag"
                MenuItem { text: "Rectangle"; checkable: true; checked: _ed.drawTool === "rect"; onTriggered: _ed.setDrawTool("rect") }
                MenuItem { text: "Rounded"; checkable: true; checked: _ed.drawTool === "roundrect"; onTriggered: _ed.setDrawTool("roundrect") }
                MenuItem { text: "Ellipse"; checkable: true; checked: _ed.drawTool === "ellipse"; onTriggered: _ed.setDrawTool("ellipse") }
                MenuItem { text: "Triangle"; checkable: true; checked: _ed.drawTool === "triangle"; onTriggered: _ed.setDrawTool("triangle") }
                MenuItem { text: "Diamond"; checkable: true; checked: _ed.drawTool === "diamond"; onTriggered: _ed.setDrawTool("diamond") }
                MenuItem { text: "Table"; checkable: true; checked: _ed.drawTool === "table"; onTriggered: _ed.setDrawTool("table") }
                MenuItem { text: "Text"; checkable: true; checked: _ed.drawTool === "text"; onTriggered: _ed.setDrawTool("text") }
                MenuSeparator {}
                MenuItem { text: "Import overlay…"; onTriggered: _ed.overlayImportRequested() }
                MenuSeparator {}
                MenuItem { text: "Cancel tool"; enabled: _ed.drawTool.length > 0; onTriggered: _ed.drawTool = "" }
            }
            MenuSeparator {}
            Menu {
                title: "Shape"
                enabled: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return _ed.isDraw(n) && !_ed.isTable(n) && !_ed.isText(n)
                }
                MenuItem { text: "Rectangle"; checkable: true; checked: _ed.fieldEq("shape", "rect", "rect"); onTriggered: _ed.applyField("shape", "rect") }
                MenuItem { text: "Rounded"; checkable: true; checked: _ed.fieldEq("shape", "roundrect", "rect"); onTriggered: _ed.applyField("shape", "roundrect") }
                MenuItem { text: "Ellipse"; checkable: true; checked: _ed.fieldEq("shape", "ellipse", "rect"); onTriggered: _ed.applyField("shape", "ellipse") }
                MenuItem { text: "Triangle"; checkable: true; checked: _ed.fieldEq("shape", "triangle", "rect"); onTriggered: _ed.applyField("shape", "triangle") }
                MenuItem { text: "Diamond"; checkable: true; checked: _ed.fieldEq("shape", "diamond", "rect"); onTriggered: _ed.applyField("shape", "diamond") }
            }
            Menu {
                id: _padMenu
                title: "Padding"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                Instantiator {
                    model: [4, 8, 12, 16, 24, 32]
                    delegate: MenuItem {
                        required property int modelData
                        text: "" + modelData
                        checkable: true
                        checked: _ed.fieldEq("pad", modelData, 8)
                        onTriggered: _ed.applyField("pad", modelData)
                    }
                    onObjectAdded: (i, obj) => _padMenu.insertItem(i, obj)
                    onObjectRemoved: (i, obj) => _padMenu.removeItem(obj)
                }
            }
            Menu {
                title: "Rotate"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                MenuItem { text: "0°"; onTriggered: _ed.applyField("rot", 0) }
                MenuItem { text: "90°"; onTriggered: _ed.applyField("rot", 90) }
                MenuItem { text: "180°"; onTriggered: _ed.applyField("rot", 180) }
                MenuItem { text: "270°"; onTriggered: _ed.applyField("rot", 270) }
                MenuItem { text: "-15°"; onTriggered: { var n = _ed.nodeAt(_ed.selectedId); _ed.applyField("rot", ((n && n.rot) ? n.rot : 0) - 15) } }
                MenuItem { text: "+15°"; onTriggered: { var n = _ed.nodeAt(_ed.selectedId); _ed.applyField("rot", ((n && n.rot) ? n.rot : 0) + 15) } }
            }
            MenuItem {
                text: "Filled"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                checkable: true
                checked: _ed.fieldEq("fill", "filled", "hollow")
                onTriggered: _ed.applyField("fill", "filled")
            }
            MenuItem {
                text: "Hollow"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                checkable: true
                checked: _ed.fieldEq("fill", "hollow", "hollow")
                onTriggered: _ed.applyField("fill", "hollow")
            }
            MenuItem {
                text: "Fill color…"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.requestDrawColor("color")
            }
            MenuItem {
                text: "Stroke color…"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.requestDrawColor("border")
            }
            Menu {
                title: "Stroke"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                MenuItem { text: "1"; checkable: true; checked: _ed.fieldEq("stroke", 1, 2); onTriggered: _ed.applyField("stroke", 1) }
                MenuItem { text: "2"; checkable: true; checked: _ed.fieldEq("stroke", 2, 2); onTriggered: _ed.applyField("stroke", 2) }
                MenuItem { text: "3"; checkable: true; checked: _ed.fieldEq("stroke", 3, 2); onTriggered: _ed.applyField("stroke", 3) }
                MenuItem { text: "4"; checkable: true; checked: _ed.fieldEq("stroke", 4, 2); onTriggered: _ed.applyField("stroke", 4) }
                MenuItem { text: "6"; checkable: true; checked: _ed.fieldEq("stroke", 6, 2); onTriggered: _ed.applyField("stroke", 6) }
            }
            Menu {
                title: "Opacity"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                MenuItem { text: "25%"; checkable: true; checked: _ed.fieldEq("opacity", 0.25, 1); onTriggered: _ed.applyField("opacity", 0.25) }
                MenuItem { text: "50%"; checkable: true; checked: _ed.fieldEq("opacity", 0.5, 1); onTriggered: _ed.applyField("opacity", 0.5) }
                MenuItem { text: "75%"; checkable: true; checked: _ed.fieldEq("opacity", 0.75, 1); onTriggered: _ed.applyField("opacity", 0.75) }
                MenuItem { text: "100%"; checkable: true; checked: _ed.fieldEq("opacity", 1, 1); onTriggered: _ed.applyField("opacity", 1) }
            }
            MenuSeparator {}
            MenuItem {
                text: "Bring forward"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.bringForward()
            }
            MenuItem {
                text: "Send back"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.sendBack()
            }
            MenuItem {
                text: "Detach from chips"
                enabled: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    return _ed.isDraw(n) && n.around && n.around.length
                }
                onTriggered: {
                    var n = _ed.nodeAt(_ed.selectedId)
                    if (!n) return
                    var g = _ed.drawGeom(n)
                    n.around = []
                    n.fx = _ed.xToFx(g.x)
                    n.fy = _ed.yToFy(g.y)
                    n.fw = g.w / Math.max(1, _ed.spaceRect().w)
                    n.fh = g.h / Math.max(1, _ed.spaceRect().h)
                    _ed.bump()
                }
            }
            MenuItem {
                text: "Delete drawing"
                enabled: _ed.isDraw(_ed.nodeAt(_ed.selectedId))
                onTriggered: _ed.deleteChip()
            }
        
            
        }


    }
}
