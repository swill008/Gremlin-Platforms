// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import Gremlin.Style

// The print area on the Button Map (rig_print_area.js): while shown
// (View > Print Area, or its tool), a dashed frame in the print area's
// color with a small "Print Area" label, and everything outside dimmed.
// While editing and not locked, its handles resize it and its border moves
// it. Also the rubber band while a new area is drawn (Alt+drag).
Item {
    id: _area
    property var ed: null
    anchors.fill: parent
    z: 9

    readonly property color ink: (ed && ed.printAreaColor.length) ? Qt.color(ed.printAreaColor) : Style.dangerBright
    readonly property var r: {
        if (!ed)
            return { x: 0, y: 0, w: 0, h: 0 }
        ed.printArea
        ed.width
        ed.height
        ed.anyTick
        return ed.printAreaRect()
    }
    readonly property bool shown: !!ed && ed.printAreaShown && !ed.exporting
    readonly property bool canEdit: shown && !!ed && ed.interactive && !ed.printAreaLocked

    // Outside the area: dimmed.
    Item {
        anchors.fill: parent
        visible: _area.shown
        Rectangle { color: Style.dim; x: 0; y: 0; width: parent.width; height: Math.max(0, _area.r.y) }
        Rectangle {
            color: Style.dim
            x: 0
            y: _area.r.y + _area.r.h
            width: parent.width
            height: Math.max(0, parent.height - y)
        }
        Rectangle { color: Style.dim; x: 0; y: _area.r.y; width: Math.max(0, _area.r.x); height: _area.r.h }
        Rectangle {
            color: Style.dim
            x: _area.r.x + _area.r.w
            y: _area.r.y
            width: Math.max(0, parent.width - x)
            height: _area.r.h
        }
    }

    // The frame: dashed, in the print area's color.
    Canvas {
        id: _frame
        visible: _area.shown
        x: _area.r.x - 2
        y: _area.r.y - 2
        width: _area.r.w + 4
        height: _area.r.h + 4
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        Connections {
            target: _area
            function onInkChanged() { _frame.requestPaint() }
        }
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = String(_area.ink)
            ctx.lineWidth = 2
            ctx.setLineDash([6, 4])
            ctx.strokeRect(2, 2, width - 4, height - 4)
        }
    }

    // Its name, above the frame's top-left corner (inside it at the top).
    Rectangle {
        visible: _area.shown
        x: _area.r.x
        y: _area.r.y - height - 3 >= 0 ? _area.r.y - height - 3 : _area.r.y + 3
        width: _label.implicitWidth + Style.dp(8)
        height: _label.implicitHeight + Style.dp(2)
        radius: Style.dp(3)
        color: Style.bgRaised
        border.color: _area.ink
        Text {
            id: _label
            anchors.centerIn: parent
            text: "Print Area"
            color: _area.ink
            font.pixelSize: Style.dp(10)
        }
    }

    // A new area being drawn (Alt+drag, or after Set Print Area).
    Rectangle {
        visible: !!_area.ed && _area.ed.dragKind === "printarea"
        // In the paper's shape when one is chosen.
        readonly property var drawn: {
            if (!_area.ed)
                return { x: 0, y: 0, w: 0, h: 0 }
            _area.ed.eaX1
            _area.ed.eaY1
            return _area.ed.drawnPrintRect()
        }
        x: drawn.x
        y: drawn.y
        width: drawn.w
        height: drawn.h
        color: Qt.rgba(_area.ink.r, _area.ink.g, _area.ink.b, 0.15)
        border.color: _area.ink
        border.width: Style.dp(1)
    }

    // Dragging a handle or the border: the area's rectangle when pressed,
    // and how each handle moves its edges.
    component Grip: MouseArea {
        id: _grip
        // Which edges move: "n", "se", ... or "move" for the whole area.
        property string edges: "move"
        property var start: null
        property point from: Qt.point(0, 0)
        enabled: _area.canEdit
        visible: _area.canEdit
        hoverEnabled: true
        preventStealing: true
        onPressed: (m) => {
            start = _area.ed.printAreaRect()
            from = mapToItem(_area, m.x, m.y)
        }
        onPositionChanged: (m) => {
            if (!pressed || !start)
                return
            var p = mapToItem(_area, m.x, m.y)
            var dx = p.x - from.x
            var dy = p.y - from.y
            var x = start.x
            var y = start.y
            var w = start.w
            var h = start.h
            if (edges === "move") {
                var s = _area.ed.spaceRect()
                x = Math.max(s.x, Math.min(s.x + s.w - w, x + dx))
                y = Math.max(s.y, Math.min(s.y + s.h - h, y + dy))
            } else {
                if (edges.indexOf("w") >= 0) { x += dx; w -= dx }
                if (edges.indexOf("e") >= 0) w += dx
                if (edges.indexOf("n") >= 0) { y += dy; h -= dy }
                if (edges.indexOf("s") >= 0) h += dy
            }
            _area.ed.setPrintAreaRect(x, y, w, h, edges)
        }
        onReleased: {
            start = null
            _area.ed.printAreaEdited(false)
        }
    }

    // The border moves the area (a band along each side).
    readonly property real band: Style.dp(6)
    Grip { edges: "move"; cursorShape: Qt.SizeAllCursor; x: _area.r.x - _area.band / 2; y: _area.r.y - _area.band / 2; width: _area.r.w + _area.band; height: _area.band }
    Grip { edges: "move"; cursorShape: Qt.SizeAllCursor; x: _area.r.x - _area.band / 2; y: _area.r.y + _area.r.h - _area.band / 2; width: _area.r.w + _area.band; height: _area.band }
    Grip { edges: "move"; cursorShape: Qt.SizeAllCursor; x: _area.r.x - _area.band / 2; y: _area.r.y; width: _area.band; height: _area.r.h }
    Grip { edges: "move"; cursorShape: Qt.SizeAllCursor; x: _area.r.x + _area.r.w - _area.band / 2; y: _area.r.y; width: _area.band; height: _area.r.h }

    // Handles on the corners and the middle of each side resize it.
    Repeater {
        model: [
            { e: "nw", fx: 0, fy: 0, c: Qt.SizeFDiagCursor }, { e: "n", fx: 0.5, fy: 0, c: Qt.SizeVerCursor },
            { e: "ne", fx: 1, fy: 0, c: Qt.SizeBDiagCursor }, { e: "e", fx: 1, fy: 0.5, c: Qt.SizeHorCursor },
            { e: "se", fx: 1, fy: 1, c: Qt.SizeFDiagCursor }, { e: "s", fx: 0.5, fy: 1, c: Qt.SizeVerCursor },
            { e: "sw", fx: 0, fy: 1, c: Qt.SizeBDiagCursor }, { e: "w", fx: 0, fy: 0.5, c: Qt.SizeHorCursor }
        ]
        Grip {
            required property var modelData
            edges: modelData.e
            cursorShape: modelData.c
            width: Style.dp(10)
            height: Style.dp(10)
            x: _area.r.x + modelData.fx * _area.r.w - width / 2
            y: _area.r.y + modelData.fy * _area.r.h - height / 2
            z: 2
            Rectangle {
                anchors.fill: parent
                color: Style.bgRaised
                border.color: _area.ink
                border.width: Style.dp(1)
            }
        }
    }
}
