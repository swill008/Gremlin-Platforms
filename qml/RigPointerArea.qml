// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// All mouse, wheel and key input of the Device Mapping Editor: picking, dragging,
// drawing, resizing, band selection and the right-click menus.
MouseArea {
    property var ed: null
    property var menuTarget: null
    property var menu: null
    property var spineHoldTimer: null
    anchors.fill: parent
    z: 8
    enabled: ed.interactive
    hoverEnabled: true
    preventStealing: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    // A drawing tool draws; a move shows SizeAll once past its dead zone;
    // otherwise the cursor over a handle (07 S152).
    cursorShape: ed.drawTool.length ? Qt.CrossCursor
                 : (isMoveDrag(ed.dragKind) && !moveArmed) ? Qt.SizeAllCursor
                 : hoverCursor
    property int hoverCursor: Qt.ArrowCursor
    focus: true
    Keys.onDeletePressed: ed.deleteSelected()
    Keys.onPressed: (e) => {
        // Esc during a drag puts everything back as it was at the press, with
        // no undo step; the selection stays (07 S150).
        if (e.key === Qt.Key_Escape && ed.dragKind !== "") {
            cancelDrag()
            e.accepted = true
            return
        }
        // Set Print Area waiting for its drag: Esc cancels it.
        if (e.key === Qt.Key_Escape && ed.printAreaArm) {
            ed.printAreaArm = false
            e.accepted = true
            return
        }
        // Crop mode: Enter keeps the crop, Esc puts it back as it was when
        // crop mode started (07 S148).
        if (ed.cropId && (e.key === Qt.Key_Return || e.key === Qt.Key_Enter)) {
            ed.finishCrop()
            e.accepted = true
            return
        }
        if (ed.cropId && e.key === Qt.Key_Escape) {
            ed.cancelCrop()
            e.accepted = true
            return
        }
        if (e.key === Qt.Key_Backspace) {
            ed.deleteSelected()
            e.accepted = true
        } else if ((e.key === Qt.Key_Return || e.key === Qt.Key_Enter) && ed.drawTool === "path" && ed.pathDraft.length) {
            ed.finishPath(false)
            e.accepted = true
        } else if (e.key === Qt.Key_Escape) {
            if (ed.renameId) {
                ed.cancelRename()
            } else {
                ed.cancelAllActions()
                // Esc also closes (and unpins) a pinned menu.
                ed.closeMenu()
            }
            e.accepted = true
        } else if ((e.modifiers & Qt.ControlModifier) && e.key === Qt.Key_L) {
            // Ctrl+L locks or unlocks the selection; Ctrl+Shift+L unlocks everything.
            if (e.modifiers & Qt.ShiftModifier)
                ed.unlockAll()
            else
                ed.toggleLockSelection()
            e.accepted = true
        } else if ((e.modifiers & Qt.ControlModifier) && e.key === Qt.Key_Z) {
            if (e.modifiers & Qt.ShiftModifier)
                ed.redo()
            else
                ed.undo()
            e.accepted = true
        } else if ((e.modifiers & Qt.ControlModifier) && e.key === Qt.Key_D) {
            ed.duplicateSelection()
            e.accepted = true
        } else if ((e.modifiers & Qt.ControlModifier) && e.key === Qt.Key_C) {
            ed.copySelection()
            e.accepted = true
        } else if ((e.modifiers & Qt.ControlModifier) && e.key === Qt.Key_V) {
            ed.pasteClipboard()
            e.accepted = true
        } else if (e.key === Qt.Key_Left || e.key === Qt.Key_Right || e.key === Qt.Key_Up || e.key === Qt.Key_Down) {
            // Shift+arrow moves 10 px, ten plain arrow steps (07 S145).
            var step = (e.modifiers & Qt.ShiftModifier) ? 10 : 1
            var dx = 0
            var dy = 0
            if (e.key === Qt.Key_Left) dx = -step
            if (e.key === Qt.Key_Right) dx = step
            if (e.key === Qt.Key_Up) dy = -step
            if (e.key === Qt.Key_Down) dy = step
            ed.nudge(dx / Math.max(1, ed.spaceRect().w), dy / Math.max(1, ed.spaceRect().h))
            e.accepted = true
        }
    }

    // Move dead zone (D-FIXLIST-B1): a chip, group member, drawing or free
    // table cell moves only once the pointer is more than 4 screen pixels
    // from the press, so a click that wobbles only selects.
    readonly property real moveDeadZone: 4
    property bool moveArmed: false
    property real pressSceneX: 0
    property real pressSceneY: 0
    // The press in map coordinates, for Shift's move line lock (07 S144).
    property real pressX: 0
    property real pressY: 0
    // Alt-press on a selected item's body: the selection is copied when the
    // drag leaves the dead zone, and the copies move (07 S143).
    property bool altCopyArmed: false
    function isMoveDrag(kind) {
        return kind === "chip" || kind === "member" || kind === "draw" || kind === "tablecell"
    }
    // True while a move drag is still inside its dead zone.
    function inDeadZone(m) {
        if (!moveArmed || !isMoveDrag(ed.dragKind))
            return false
        var sp = mapToItem(null, m.x, m.y)
        if (Math.hypot(sp.x - pressSceneX, sp.y - pressSceneY) <= moveDeadZone)
            return true
        moveArmed = false
        return false
    }

    onPressed: (m) => {
        var ps = mapToItem(null, m.x, m.y)
        pressSceneX = ps.x
        pressSceneY = ps.y
        moveArmed = true
        pressX = m.x
        pressY = m.y
        altCopyArmed = false
        ed.mapPressed()
        if (ed.renameId) {
            var nr = ed.nodeAt(ed.renameId)
            var mr = (ed.renameMember >= 0 && nr && nr.members) ? nr.members[ed.renameMember] : null
            var rr = ed.chipScreenRect(nr, mr)
            if (!(m.x >= rr.x && m.x <= rr.x + rr.width && m.y >= rr.y && m.y <= rr.y + rr.height))
                ed.commitRename()
        }
        forceActiveFocus()
        ed.altHeld = !!(m.modifiers & Qt.AltModifier)
        ed.shiftHeld = !!(m.modifiers & Qt.ShiftModifier)
        // Ctrl held skips snapping (07 S142).
        ed.snapOffHeld = !!(m.modifiers & Qt.ControlModifier)
        // The selection box's resize handles (07 S153), before the print
        // area: with Alt (from the centre) they may sit on an empty part.
        if (ed.interactive && m.button === Qt.LeftButton && !ed.printAreaArm && !ed.drawTool.length) {
            var grh = ed.onGroupResizeHandle(m.x, m.y)
            if (grh) {
                ed.beginGesture()
                ed.beginGroupResize(grh, m.x, m.y)
                ed.dragKind = "groupresize"
                return
            }
        }
        // The print area: Alt+drag from an empty part of the map (on an
        // item Alt copies it, 07 S143; with a drawing tool Alt draws from
        // the centre, 07 S146), or any drag after Set Print Area.
        if (ed.interactive && m.button === Qt.LeftButton
                && (ed.printAreaArm || (ed.altHeld && !ed.drawTool.length && !ed.hitTest(m.x, m.y).id))) {
            ed.beginGesture()
            ed.beginPrintArea(m.x, m.y)
            ed.dragKind = "printarea"
            return
        }
        if (ed.interactive && ed.drawTool === "path") {
            if (m.button === Qt.RightButton)
                ed.finishPath(false)
            else
                ed.pathClick(m.x, m.y)
            return
        }
        if (ed.interactive && ed.drawTool === "pen" && m.button === Qt.LeftButton) {
            ed.beginGesture()
            ed.penStart(m.x, m.y)
            ed.dragKind = "pen"
            return
        }
        if (ed.interactive && m.button === Qt.LeftButton && !ed.drawTool.length) {
            var onGuide = ed.rulerGuideAt(m.x, m.y)
            var under = onGuide ? ed.hitTest(m.x, m.y) : null
            if (onGuide && !(under && under.kind)) {
                ed.beginGesture()
                ed.guideDrag = onGuide
                ed.dragKind = "rulerguide"
                return
            }
        }
        if (ed.interactive && m.button === Qt.LeftButton && ed.onTurnHandle(m.x, m.y)) {
            ed.beginGesture()
            ed.beginTurn(m.x, m.y)
            ed.dragKind = "turn"
            return
        }
        var hit = ed.hitTest(m.x, m.y)
        var shift = (m.modifiers & Qt.ShiftModifier) || (m.modifiers & Qt.ControlModifier)
        if (m.button === Qt.RightButton) {
            // Where the menu was asked for, for Paste Here (07 S136).
            menuTarget.mapX = m.x
            menuTarget.mapY = m.y
            if (hit.kind === "spine") {
                // Picked as a left click picks it, drawn at once (a part of a
                // selection keeps the selection: the menu acts on all of it).
                if (!ed.isSelected(hit.id)) {
                    ed.setSelection(shift ? menuSelectionPlus(hit.id) : [hit.id])
                    ed.bump()
                }
                ed.selectedId = hit.id
                ed.selectedLeader = (hit.leader !== undefined) ? hit.leader : 0
                ed.selectedSpine = hit.spine
                menuTarget.nodeId = hit.id
                menuTarget.kind = "spine"
                menuTarget.leader = (hit.leader !== undefined) ? hit.leader : 0
                menuTarget.seg = hit.spine
                ed.spineHoldArm = true
                ed.spineHoldId = hit.id
                ed.spineHoldLeader = menuTarget.leader
                ed.spineHoldIndex = hit.spine
                ed.spineHoldX = m.x
                ed.spineHoldY = m.y
                spineHoldTimer.restart()
                return
            }
            if (hit.id) {
                // Shift/Ctrl+right-click on an unselected item adds it, so the
                // menu (titled for it, or "N selected") acts on what it names.
                if (!ed.isSelected(hit.id)) {
                    ed.setSelection(shift ? menuSelectionPlus(hit.id) : [hit.id])
                    ed.bump()
                }
                menuTarget.nodeId = hit.id
                menuTarget.kind = hit.kind || ""
                menuTarget.seg = (hit.seg !== undefined) ? hit.seg : -1
                menuTarget.leader = (hit.leader !== undefined) ? hit.leader : 0
                ed.selectedLeader = menuTarget.leader
                ed.selectedSeg = menuTarget.seg
                if (hit.kind === "spine")
                    ed.selectedSpine = hit.spine
                if (hit.kind === "member")
                    ed.selectedMember = hit.member
                else if (ed.groupEditId && ed.groupEditId === hit.id) {
                    var gn0 = ed.nodeAt(hit.id)
                    var mi0 = gn0 ? ed.memberHit(gn0, m.x, m.y) : -1
                    ed.selectedMember = mi0
                }
                var tn = ed.nodeAt(hit.id)
                if (ed.isText(tn)) {
                    ed.chipMenuRequested(m.x, m.y)
                    menu.openAt(ed, m.x, m.y)
                    return
                }
                if (ed.isTable(tn)) {
                    var cell = ed.tableCellAt(tn, m.x, m.y)
                    ed.tableRow = cell.row
                    ed.tableCol = cell.col
                    ed.tableExtra = (cell.extra !== undefined) ? cell.extra : -1
                    ed.chipMenuRequested(m.x, m.y)
                    menu.openAt(ed, m.x, m.y)
                    return
                }
            } else {
                menuTarget.nodeId = ""
                menuTarget.kind = ""
                menuTarget.seg = -1
                menuTarget.leader = 0
            }
            ed.chipMenuRequested(m.x, m.y)
            menu.openAt(ed, m.x, m.y)
            return
        }
        if (hit.kind === "overlayPin") {
            ed.setSelection([hit.id])
            ed.selectedId = hit.id
            ed.toggleLock(hit.id)
            ed.dragKind = ""
            return
        }
        if (hit.kind === "draw") {
            var dnPre = ed.nodeAt(hit.id)
            var shiftCell = shift && ed.isTable(dnPre) && hit.handle === "body"
            // Shift on a handle changes what the drag does (proportions, 45
            // degree steps, side skew with Ctrl), not the selection.
            var onHandle = !!(hit.handle && hit.handle !== "body")
            if (shift && !shiftCell && !onHandle)
                ed.toggleSelected(hit.id)
            else if (!ed.isSelected(hit.id))
                ed.setSelection([hit.id])
            var dn = dnPre
            if (ed.textPaintOn && ed.isText(dn)) {
                ed.applyTextFormat(dn.id)
                ed.dragKind = ""
                return
            }
            if (ed.plantSnap && ed.isOverlay(dn)) {
                ed.addSocketAt(dn, m.x, m.y)
                return
            }
            var g = dn ? ed.drawGeom(dn) : { x: 0, y: 0, w: 8, h: 8 }
            if (ed.isLocked(dn)) {
                ed.dragKind = ""
                ed.bump()
                return
            }
            ed.beginGesture()
            if (hit.handle && hit.handle.indexOf("cell-") === 0) {
                var crc = ed.tableCurrentRect(dn)
                ed.dragKind = hit.handle
                ed.rzX0 = crc.x
                ed.rzY0 = crc.y
                ed.rzX1 = crc.x + crc.w
                ed.rzY1 = crc.y + crc.h
            } else if (isSideHandle(hit.handle) && (m.modifiers & Qt.ControlModifier) && (m.modifiers & Qt.ShiftModifier)
                       && ed.cropId !== dn.id && ed.beginSideSkew(dn, hit.handle, m.x, m.y)) {
                // Ctrl+Shift on a side handle skews along that side (07 S147);
                // beginSideSkew says no when the item can't skew.
                ed.dragKind = "sideskew"
            } else if (hit.handle && hit.handle !== "body") {
                ed.dragKind = "draw-" + hit.handle
                ed.cropStart = dn && dn.crop ? JSON.parse(JSON.stringify(dn.crop)) : null
                ed.rzX0 = g.x
                ed.rzY0 = g.y
                ed.rzX1 = g.x + g.w
                ed.rzY1 = g.y + g.h
            } else if (ed.isTable(dn)) {
                var tcell = ed.tableCellAt(dn, m.x, m.y)
                ed.tableRow = tcell.row
                ed.tableCol = tcell.col
                ed.tableExtra = (tcell.extra !== undefined) ? tcell.extra : -1
                var extraHit = ed.tableExtra >= 0
                var gridFree = tcell.row >= 0 && (ed.tableCellIsFree(dn, tcell.row, tcell.col) || !!(m.modifiers & Qt.ShiftModifier))
                var wantFree = extraHit || gridFree
                if (wantFree) {
                    if (!extraHit && !ed.tableCellIsFree(dn, tcell.row, tcell.col))
                        ed.setTableCellFree(true)
                    var rc = extraHit ? ed.tableExtraRect(dn, ed.tableExtra) : ed.tableCellRect(dn, tcell.row, tcell.col)
                    ed.dragKind = "tablecell"
                    ed.dragOffX = m.x - rc.x
                    ed.dragOffY = m.y - rc.y
                } else {
                    ed.dragKind = "draw"
                    ed.dragOffX = m.x - g.x
                    ed.dragOffY = m.y - g.y
                    altCopyArmed = ed.altHeld && ed.isSelected(hit.id)
                }
            } else {
                ed.dragKind = "draw"
                ed.dragOffX = m.x - g.x
                ed.dragOffY = m.y - g.y
                altCopyArmed = ed.altHeld && ed.isSelected(hit.id)
            }
            ed.bump()
            return
        }
        if (ed.drawTool.length && (!hit.kind || hit.kind === "")) {
            var p0 = ed.snapEnt(m.x, m.y, ed.snapOffHeld)
            ed.beginGesture()
            ed.dragKind = "drawnew"
            ed.drawX0 = p0.x
            ed.drawY0 = p0.y
            ed.drawX1 = p0.x
            ed.drawY1 = p0.y
            return
        }
        if (hit.kind === "line" && !shift) {
            ed.setSelection([hit.id])
            ed.selectedId = hit.id
            ed.selectedLeader = (hit.leader !== undefined) ? hit.leader : 0
            ed.selectedSeg = (hit.seg !== undefined) ? hit.seg : 0
            ed.selectedSpine = -1
            ed.lineArm = true
            ed.lineArmX = m.x
            ed.lineArmY = m.y
            ed.beginGesture()
            ed.dragKind = "linearm"
            ed.bump()
            return
        }
        if (hit.kind === "from" || hit.kind === "to") {
            if (!shift)
                ed.setSelection([hit.id])
            ed.selectedId = hit.id
            ed.selectedSpine = -1
            ed.selectedLeader = (hit.leader !== undefined) ? hit.leader : 0
            // The end comes off its hook now; that and the drop are one step.
            ed.beginGesture()
            ed.dragKind = hit.kind
            var ne = ed.nodeAt(hit.id)
            if (ne) {
                var L0 = ed.currentLeader(ne)
                if (!L0) {
                    ed.dragKind = ""
                    ed.endGesture()
                    return
                }
                var ep = ed.endPt(hit.kind === "to" ? L0.to : L0.from)
                var fr = { type: "free", fx: ed.xToFx(ep.x), fy: ed.yToFy(ep.y) }
                if (hit.kind === "to") L0.to = fr
                else L0.from = fr
            }
            ed.bump()
            return
        }
        if (hit.kind === "member") {
            ed.setSelection([hit.id])
            ed.selectedId = hit.id
            ed.selectedMember = hit.member
            ed.selectedSpine = -1
            ed.beginGesture()
            ed.dragKind = "member"
            ed.dragMember = hit.member
            var nm = ed.nodeAt(hit.id)
            if (nm && nm.members && nm.members[hit.member]) {
                var mm = nm.members[hit.member]
                ed.dragOffX = m.x - (ed.fxToX(nm.chipFx) + ed.groupMinX(nm) + ed.memberLocalX(nm, mm))
                ed.dragOffY = m.y - (ed.fyToY(nm.chipFy) + ed.groupMinY(nm) + ed.memberLocalY(nm, mm))
            }
            ed.bump()
            return
        }
        if (hit.kind === "chip") {
            if (shift)
                ed.toggleSelected(hit.id)
            else if (!ed.isSelected(hit.id))
                ed.setSelection([hit.id])
            ed.selectedId = hit.id
            ed.selectedSpine = -1
            ed.selectedSeg = -1
            ed.beginGesture()
            ed.dragKind = "chip"
            ed.dragSpine = -1
            altCopyArmed = ed.altHeld && ed.isSelected(hit.id)
            var n2 = ed.nodeAt(hit.id)
            if (n2) {
                ed.dragOffX = m.x - ed.fxToX(n2.chipFx)
                ed.dragOffY = m.y - ed.fyToY(n2.chipFy)
            }
            ed.bump()
            return
        }
        if (hit.kind === "hot" || hit.kind === "spine") {
            if (!shift)
                ed.setSelection([hit.id])
            ed.selectedId = hit.id
            ed.selectedSpine = hit.spine
            ed.selectedLeader = (hit.leader !== undefined) ? hit.leader : 0
            if (hit.kind === "spine") {
                ed.selectedSeg = hit.spine + 1
                ed.dragLeader = (hit.leader !== undefined) ? hit.leader : 0
            }
            ed.beginGesture()
            ed.dragKind = hit.kind
            ed.dragSpine = hit.spine
            ed.bump()
            return
        }
        ed.dragKind = "band"
        ed.banding = false
        ed.bandAdd = shift
        ed.bandX0 = m.x
        ed.bandY0 = m.y
        ed.bandX1 = m.x
        ed.bandY1 = m.y
        if (!shift)
            ed.setSelection([])
        ed.bump()
    }
    onExited: {
        ed.hoverHwLabel = ""
        if (ed.overlayHoverId) {
            ed.overlayHoverId = ""
            ed.repaint()
        }
    }
    // The mouse grab was taken away mid-drag: the drag stops, as one step.
    onCanceled: {
        spineHoldTimer.stop()
        ed.spineHoldArm = false
        if (ed.dragKind === "printarea")
            ed.endPrintArea()
        else if (ed.dragKind === "pen")
            ed.penEnd()
        else if (ed.dragKind === "rulerguide" && ed.guideDrag)
            ed.rulerGuidesEdited()
        else if (ed.dragKind === "groupresize")
            ed.endGroupResize()
        altCopyArmed = false
        ed.stopGesture()
        ed.dragKind = ""
    }
    onPositionChanged: (m) => {
        ed.altHeld = !!(m.modifiers & Qt.AltModifier)
        ed.shiftHeld = !!(m.modifiers & Qt.ShiftModifier)
        ed.snapOffHeld = !!(m.modifiers & Qt.ControlModifier)
        ed.setOverlayHover(m.x, m.y)
        ed.setChipTip(m.x, m.y)
        if (!ed.dragKind)
            hoverCursor = cursorAt(m.x, m.y)
        if (ed.drawTool === "path" && ed.pathDraft.length)
            ed.pathHoverAt(m.x, m.y)
        if (ed.dragKind === "pen") {
            ed.penMove(m.x, m.y)
            return
        }
        if (ed.dragKind === "printarea") {
            ed.movePrintArea(m.x, m.y)
            return
        }
        if (ed.dragKind === "groupresize") {
            ed.dragGroupResize(m.x, m.y)
            return
        }
        if (ed.dragKind === "sideskew") {
            ed.applySideSkew(m.x, m.y)
            return
        }
        if (inDeadZone(m))
            return
        if (altCopyArmed) {
            altCopyArmed = false
            copyForAltDrag()
        }
        if (ed.dragKind === "chip" || ed.dragKind === "member")
            ed.poolHover = ed.overPool(m.x, m.y)
        if (ed.dragKind === "rulerguide" && ed.guideDrag) {
            ed.dragRulerGuide(ed.guideDrag.axis, ed.guideDrag.index, m.x, m.y)
            return
        }
        if (!ed.dragKind) {
            return
        }
        if (ed.dragKind === "drawnew") {
            var p1 = ed.snapEnt(m.x, m.y, ed.snapOffHeld)
            p1 = ed.drawToolPoint(ed.drawX0, ed.drawY0, p1.x, p1.y)
            ed.drawX1 = p1.x
            ed.drawY1 = p1.y
            return
        }
        if (ed.dragKind === "band") {
            ed.bandX1 = m.x
            ed.bandY1 = m.y
            if (!ed.banding && Math.hypot(m.x - ed.bandX0, m.y - ed.bandY0) > 4)
                ed.banding = true
            return
        }
        if (ed.dragKind === "linearm") {
            if (Math.hypot(m.x - ed.lineArmX, m.y - ed.lineArmY) <= 6)
                return
            var sid = ed.addSpineAt(ed.selectedId, ed.lineArmX, ed.lineArmY, true)
            ed.lineArm = false
            if (sid < 0) {
                ed.dragKind = ""
                return
            }
            ed.dragKind = "spine"
            ed.dragSpine = sid
            ed.selectedSpine = sid
            ed.applyPointer(m.x, m.y, ed.snapOffHeld)
            return
        }
        // Shift during a move keeps it on a horizontal, vertical or 45
        // degree line from the press (07 S144).
        if (ed.shiftHeld && isMoveDrag(ed.dragKind)) {
            var lp = shiftLock(m.x, m.y)
            ed.applyPointer(lp.x, lp.y, ed.snapOffHeld)
            return
        }
        ed.applyPointer(m.x, m.y, ed.snapOffHeld)
    }
    onReleased: (m) => {
        if (ed.spineHoldArm) {
            spineHoldTimer.stop()
            ed.spineHoldArm = false
            if (m.button === Qt.RightButton) {
                menuTarget.mapX = ed.spineHoldX
                menuTarget.mapY = ed.spineHoldY
                ed.chipMenuRequested(ed.spineHoldX, ed.spineHoldY)
                menu.openAt(ed, ed.spineHoldX, ed.spineHoldY)
            }
            return
        }
        releaseDrag(m)
        // Every drag is one undo step, made here (07 S55a).
        ed.endGesture()
    }
    // The current selection plus id (selectedId counts even when selectedIds
    // doesn't hold it), id last so it becomes selectedId.
    function menuSelectionPlus(id) {
        var s = (ed.selectedIds || []).slice()
        if (ed.selectedId && s.indexOf(ed.selectedId) < 0)
            s.push(ed.selectedId)
        s.push(id)
        return s
    }

    // (x, y) moved onto the nearest horizontal, vertical or 45 degree line
    // through the press (07 S144).
    function shiftLock(x, y) {
        var dx = x - pressX
        var dy = y - pressY
        var step = Math.PI / 4
        var a = Math.round(Math.atan2(dy, dx) / step) * step
        var len = dx * Math.cos(a) + dy * Math.sin(a)
        return Qt.point(pressX + Math.cos(a) * len, pressY + Math.sin(a) * len)
    }

    // Alt-drag: the selection is copied in place (just above the originals,
    // the copies selected) and the drag goes on with the copies. The gesture
    // began at the press, so copy and move are one undo step (07 S143).
    function copyForAltDrag() {
        var before = (ed.selectedIds && ed.selectedIds.length) ? ed.selectedIds.slice()
                                                                 : (ed.selectedId ? [ed.selectedId] : [])
        // duplicateInPlace returns the copies in stacking order.
        var stacked = (ed.nodes || []).filter(function(q) { return q && before.indexOf(q.id) >= 0 })
        var at = -1
        for (var i = 0; i < stacked.length; i++) {
            if (stacked[i].id === ed.selectedId)
                at = i
        }
        ed.beginGesture()
        var copies = ed.duplicateInPlace() || []
        // The copy of the dragged item is the one dragged on.
        if (at >= 0 && copies.length === stacked.length)
            ed.selectedId = copies[at]
    }

    // Esc during a drag (07 S150): the editor restores the map from the
    // press without an undo step; the pointer state is cleared here.
    function cancelDrag() {
        var kind = ed.dragKind
        ed.cancelGesture()
        if (kind === "pen")
            ed.pathDraft = []
        ed.dragKind = ""
        ed.banding = false
        ed.lineArm = false
        ed.poolHover = false
        ed.guideDrag = null
        ed.clearMoveGuides()
        moveArmed = false
        altCopyArmed = false
        ed.bump()
    }

    function isSideHandle(h) {
        return h === "n" || h === "s" || h === "e" || h === "w"
    }

    // A handle's outward direction in the item's own box, in degrees (y down),
    // or -1 for anything that is not a resize handle. Item handles are
    // nw..e (cell handles cell-nw..), the selection box's tl..l.
    function handleAngle(h) {
        var name = (h || "").indexOf("cell-") === 0 ? h.slice(5) : (h || "")
        var a = { e: 0, se: 45, s: 90, sw: 135, w: 180, nw: 225, n: 270, ne: 315,
                  r: 0, br: 45, b: 90, bl: 135, l: 180, tl: 225, t: 270, tr: 315 }[name]
        return a === undefined ? -1 : a
    }

    // The two-headed arrow for a direction on screen.
    function sizeCursorFor(deg) {
        var a = ((deg % 180) + 180) % 180
        var k = Math.round(a / 45) % 4
        return [Qt.SizeHorCursor, Qt.SizeFDiagCursor, Qt.SizeVerCursor, Qt.SizeBDiagCursor][k]
    }

    // The cursor over (x, y) with no drag running (07 S152): a resize handle
    // shows the arrow along its on-screen direction (after flips and the
    // item's rotation); a rotate grip the open hand (Qt has no rotate cursor).
    function cursorAt(x, y) {
        if (!ed.interactive || ed.drawTool.length)
            return Qt.ArrowCursor
        var gh = ed.onGroupResizeHandle(x, y)
        if (gh)
            return sizeCursorFor(handleAngle(gh))
        if (ed.onTurnHandle(x, y))
            return Qt.OpenHandCursor
        var hit = ed.hitTest(x, y)
        if (hit.kind !== "draw" || !hit.handle)
            return Qt.ArrowCursor
        if (hit.handle === "rotate")
            return Qt.OpenHandCursor
        var n = ed.nodeAt(hit.id)
        var base = handleAngle(hit.handle)
        if (!n || base < 0)
            return Qt.ArrowCursor
        if (n.flipH)
            base = 180 - base
        if (n.flipV)
            base = -base
        return sizeCursorFor(base + (n.rot || 0))
    }

    function releaseDrag(m) {
        if (ed.dragKind === "groupresize") {
            ed.dragKind = ""
            ed.endGroupResize()
            return
        }
        if (ed.dragKind === "sideskew") {
            ed.dragKind = ""
            ed.bump()
            return
        }
        if (ed.dragKind === "turn") {
            ed.dragKind = ""
            ed.endTurn()
            return
        }
        if (ed.dragKind === "pen") {
            ed.dragKind = ""
            ed.penEnd()
            return
        }
        if (ed.dragKind === "printarea") {
            ed.movePrintArea(m.x, m.y)
            ed.dragKind = ""
            ed.endPrintArea()
            return
        }
        if (ed.dragKind === "rulerguide") {
            var gd = ed.guideDrag
            ed.dragKind = ""
            ed.guideDrag = null
            if (gd)
                ed.dropRulerGuide(gd.axis, gd.index, m.x, m.y)
            return
        }
        if (ed.dragKind === "draw-tail") {
            ed.dropCalloutTip(ed.nodeAt(ed.selectedId), m.x, m.y)
            ed.dragKind = ""
            ed.bump()
            return
        }
        if (ed.dragKind === "linearm") {
            ed.lineArm = false
            ed.dragKind = ""
            ed.bump()
            return
        }
        if (ed.dragKind === "drawnew") {
            ed.addDrawFree(ed.drawTool, ed.drawX0, ed.drawY0, ed.drawX1, ed.drawY1)
            ed.dragKind = ""
            return
        }
        if (ed.dragKind === "band") {
            if (ed.banding)
                ed.selectBand(ed.bandAdd)
            ed.banding = false
            ed.dragKind = ""
            ed.bump()
            return
        }
        if (ed.dragKind === "from" || ed.dragKind === "to") {
            var n3 = ed.nodeAt(ed.selectedId)
            if (n3) {
                var hooked = ed.attachNear(m.x, m.y, { altOff: ed.snapOffHeld, owner: n3 })
                var Lr = ed.currentLeader(n3)
                if (Lr) {
                    if (ed.dragKind === "to") Lr.to = hooked
                    else {
                        Lr.from = hooked
                        if (hooked.type === "chip" && hooked.id === n3.id)
                            n3.pin = hooked.pin || n3.pin
                    }
                    if (ed.selectedLeader === 0) {
                        n3.to = Lr.to
                        n3.from = Lr.from
                    }
                }
            }
            ed.dragKind = ""
            ed.bump()
            return
        }
        // Never left the dead zone: the press only selected.
        if (inDeadZone(m)) {
            moveArmed = false
            ed.poolHover = false
            ed.dragKind = ""
            ed.clearMoveGuides()
            ed.bump()
            return
        }
        moveArmed = false
        // Dropped on the pool: back off the map.
        if ((ed.dragKind === "chip" || ed.dragKind === "member") && ed.poolHover) {
            ed.poolHover = false
            ed.dragKind = ""
            ed.clearMoveGuides()
            ed.returnToPool()
            return
        }
        ed.poolHover = false
        if (ed.dragKind) {
            if (ed.dragKind === "chip" || ed.dragKind === "member")
                ed.snapChipToSocket(ed.selectedId, m.x, m.y)
            if (ed.dragKind === "chip" || ed.dragKind === "draw" || ed.dragKind === "tablecell" || ed.dragKind === "member")
                ed.commitGuideSnap()
            ed.dragKind = ""
            ed.clearMoveGuides()
            ed.bump()
        }
    }
    onDoubleClicked: (m) => {
        if (ed.drawTool === "path") {
            ed.finishPath(false)
            return
        }
        var hit = ed.hitTest(m.x, m.y)
        if (!hit.kind || !hit.id) {
            ed.cancelAllActions()
            return
        }
        if (hit.kind === "line") {
            ed.selectedId = hit.id
            ed.selectedLeader = (hit.leader !== undefined) ? hit.leader : 0
            ed.selectedSeg = (hit.seg !== undefined) ? hit.seg : 0
            ed.toggleSegCurve()
            return
        }
        if (ed.renameId)
            ed.commitRename()
        var gn = hit.id ? ed.nodeAt(hit.id) : null
        if (gn && ed.isText(gn)) {
            ed.setSelection([gn.id])
            ed.beginTextRename(gn.id)
            return
        }
        if (gn && ed.isTable(gn)) {
            var cell2 = ed.tableCellAt(gn, m.x, m.y)
            ed.setSelection([gn.id])
            ed.tableRow = cell2.row
            ed.tableCol = cell2.col
            ed.tableExtra = (cell2.extra !== undefined) ? cell2.extra : -1
            if (cell2.row >= 0 || ed.tableExtra >= 0)
                ed.beginTableRename(gn.id, cell2.row, cell2.col, ed.tableExtra)
            return
        }
        // A click selects, a double-click edits. A group opens on its first
        // double-click; inside it, a double-click edits the member.
        if (gn && ed.isGroup(gn)) {
            var wasOpen = ed.groupEditId === gn.id
            if (!wasOpen)
                ed.beginGroupEdit(gn.id)
            var mi = (hit.member !== undefined && hit.member >= 0) ? hit.member : ed.memberHit(gn, m.x, m.y)
            if (mi >= 0)
                ed.selectedMember = mi
            ed.armRenameId = ""
            ed.armRenameMember = -1
            if (mi >= 0 && wasOpen)
                ed.beginRename(gn.id, mi)
            else
                ed.bump()
            return
        }
        if (gn && !ed.isDraw(gn) && (hit.kind === "chip" || hit.kind === "member")) {
            ed.setSelection([gn.id])
            ed.armRenameId = ""
            ed.armRenameMember = -1
            ed.beginRename(gn.id, -1)
        }
    }
    onWheel: (w) => {
        if (!ed.interactive || !ed.face || !ed.face.zoomAtItem) {
            w.accepted = false
            return
        }
        var dy = w.pixelDelta.y !== 0 ? w.pixelDelta.y : w.angleDelta.y
        if (dy === 0) {
            w.accepted = false
            return
        }
        ed.face.zoomAtItem(this, w.x, w.y, Math.pow(ed.face.wheelBase || 1.0012, dy))
        w.accepted = true
    }
}
