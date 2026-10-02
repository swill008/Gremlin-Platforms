// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// All mouse, wheel and key input of the Button Map editor: picking, dragging,
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
    cursorShape: ed.drawTool.length ? Qt.CrossCursor : Qt.ArrowCursor
    focus: true
    Keys.onDeletePressed: {
        var n = ed.nodeAt(ed.selectedId)
        if (ed.isTable(n) && ed.tableExtra >= 0)
            ed.deleteThisTableCell()
        else if (ed.canUngroup())
            ed.ungroupSelection()
        else
            ed.deleteChip()
    }
    Keys.onPressed: (e) => {
        if (e.key === Qt.Key_Backspace) {
            var n = ed.nodeAt(ed.selectedId)
            if (ed.isTable(n) && ed.tableExtra >= 0)
                ed.deleteThisTableCell()
            else if (ed.canUngroup())
                ed.ungroupSelection()
            else
                ed.deleteChip()
            e.accepted = true
        } else if ((e.key === Qt.Key_Return || e.key === Qt.Key_Enter) && ed.drawTool === "path" && ed.pathDraft.length) {
            ed.finishPath(false)
            e.accepted = true
        } else if (e.key === Qt.Key_Escape) {
            if (ed.renameId)
                ed.cancelRename()
            else
                ed.cancelAllActions()
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
            var step = (e.modifiers & Qt.ShiftModifier) ? Math.max(2, ed.gridSize) : 1
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

    onPressed: (m) => {
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
        if (ed.interactive && ed.drawTool === "path") {
            if (m.button === Qt.RightButton)
                ed.finishPath(false)
            else
                ed.pathClick(m.x, m.y)
            return
        }
        if (ed.interactive && ed.drawTool === "pen" && m.button === Qt.LeftButton) {
            ed.penStart(m.x, m.y)
            ed.dragKind = "pen"
            return
        }
        if (ed.interactive && m.button === Qt.LeftButton && ed.onTurnHandle(m.x, m.y)) {
            ed.beginTurn(m.x, m.y)
            ed.dragKind = "turn"
            return
        }
        if (ed.interactive && ed.movePhoto && !ed.photoLocked && m.button === Qt.LeftButton) {
            ed.dragKind = "photo"
            ed.dragOffX = ed.photoOffX
            ed.dragOffY = ed.photoOffY
            ed.photoDragX0 = m.x
            ed.photoDragY0 = m.y
            return
        }
        var hit = ed.hitTest(m.x, m.y)
        var shift = (m.modifiers & Qt.ShiftModifier) || (m.modifiers & Qt.ControlModifier)
        if (m.button === Qt.RightButton) {
            if (hit.kind === "spine") {
                if (!shift && !ed.isSelected(hit.id))
                    ed.setSelection([hit.id])
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
                if (!shift && !ed.isSelected(hit.id))
                    ed.setSelection([hit.id])
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
                    menu.openAt(m.x, m.y)
                    return
                }
                if (ed.isTable(tn)) {
                    var cell = ed.tableCellAt(tn, m.x, m.y)
                    ed.tableRow = cell.row
                    ed.tableCol = cell.col
                    ed.tableExtra = (cell.extra !== undefined) ? cell.extra : -1
                    ed.chipMenuRequested(m.x, m.y)
                    menu.openAt(m.x, m.y)
                    return
                }
            } else {
                menuTarget.nodeId = ""
                menuTarget.kind = ""
                menuTarget.seg = -1
                menuTarget.leader = 0
            }
            ed.chipMenuRequested(m.x, m.y)
            menu.openAt(m.x, m.y)
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
            // Shift on a handle changes what the drag does (proportions, 15
            // degree steps), not the selection.
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
            if (hit.handle && hit.handle.indexOf("cell-") === 0) {
                var crc = ed.tableCurrentRect(dn)
                ed.dragKind = hit.handle
                ed.rzX0 = crc.x
                ed.rzY0 = crc.y
                ed.rzX1 = crc.x + crc.w
                ed.rzY1 = crc.y + crc.h
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
                }
            } else {
                ed.dragKind = "draw"
                ed.dragOffX = m.x - g.x
                ed.dragOffY = m.y - g.y
            }
            ed.bump()
            return
        }
        if (ed.drawTool.length && (!hit.kind || hit.kind === "")) {
            var p0 = ed.snapEnt(m.x, m.y, ed.altHeld)
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
            ed.dragKind = hit.kind
            var ne = ed.nodeAt(hit.id)
            if (ne) {
                var L0 = ed.currentLeader(ne)
                if (!L0)
                    return
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
            ed.dragKind = "chip"
            ed.dragSpine = -1
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
            ed.bump()
        }
    }
    onPositionChanged: (m) => {
        ed.altHeld = !!(m.modifiers & Qt.AltModifier)
        ed.shiftHeld = !!(m.modifiers & Qt.ShiftModifier)
        ed.setOverlayHover(m.x, m.y)
        ed.setChipTip(m.x, m.y)
        if (ed.drawTool === "path" && ed.pathDraft.length)
            ed.pathHoverAt(m.x, m.y)
        if (ed.dragKind === "pen") {
            ed.penMove(m.x, m.y)
            return
        }
        if (!ed.dragKind) {
            return
        }
        if (ed.dragKind === "drawnew") {
            var p1 = ed.snapEnt(m.x, m.y, ed.altHeld)
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
            ed.applyPointer(m.x, m.y, ed.altHeld)
            return
        }
        ed.applyPointer(m.x, m.y, ed.altHeld)
    }
    onReleased: (m) => {
        if (ed.spineHoldArm) {
            spineHoldTimer.stop()
            ed.spineHoldArm = false
            if (m.button === Qt.RightButton) {
                ed.chipMenuRequested(ed.spineHoldX, ed.spineHoldY)
                menu.openAt(ed.spineHoldX, ed.spineHoldY)
            }
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
                var hooked = ed.attachNear(m.x, m.y)
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
        if (gn && ed.isGroup(gn)) {
            if (ed.groupEditId !== gn.id)
                ed.beginGroupEdit(gn.id)
            var mi = (hit.member !== undefined && hit.member >= 0) ? hit.member : ed.memberHit(gn, m.x, m.y)
            if (mi >= 0)
                ed.selectedMember = mi
            if (mi >= 0 && ed.armRenameId === gn.id && ed.armRenameMember === mi) {
                ed.beginRename(gn.id, mi)
                ed.armRenameId = ""
                ed.armRenameMember = -1
            } else {
                ed.armRenameId = gn.id
                ed.armRenameMember = mi
                ed.bump()
            }
            return
        }
        if (gn && !ed.isDraw(gn) && (hit.kind === "chip" || hit.kind === "member")) {
            ed.setSelection([gn.id])
            if (ed.armRenameId === gn.id && ed.armRenameMember < 0) {
                ed.beginRename(gn.id, -1)
                ed.armRenameId = ""
                ed.armRenameMember = -1
            } else {
                ed.armRenameId = gn.id
                ed.armRenameMember = -1
            }
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
        ed.face.zoomAtItem(this, w.x, w.y, Math.pow(1.0012, dy))
        w.accepted = true
    }
}
