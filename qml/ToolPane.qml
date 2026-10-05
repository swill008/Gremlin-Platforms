// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.Style

// A tool's panel, joined to its tab on a tool row (ToolDock, ToolRow): it
// opens from the tab's place, on the map side of it (under a top-row tab,
// over a bottom-row one, beside a side-row one), reaching the row so the two
// read as one piece (its border is open where the tab meets it). Moving the
// tab moves the panel; it can't be dragged away from it. Unlocked, its free
// edges resize it (the one facing the map, the one along the row, and their
// corner); the size is kept with the tool (Reset Tool Rows forgets it). The
// one opened or clicked last is in front. The panel's own content fills it
// and draws its frame: `color` and `radius` must match that frame.
//
// Floating (ToolDock.floatAt / setFloating), it sits over the map where it
// was put, with a title bar: its name, pin, lock and close. Unlocked, the
// title bar moves it (dropped on a tool row, it docks there; double-click:
// back to its row) and every edge and corner resizes it. Kept in the map
// area; its place and size are kept with the tool.
//
//   ToolPane { dock: _tools; toolId: "layers"; defaultW: ...; RigLayersPanel { anchors.fill: parent } }
Item {
    id: _pane

    property var dock: null
    property string toolId: ""
    // Shown when its tool is open and this is true (e.g. something selected).
    property bool shown: true
    // As long as the map along its row (the chip pool: as wide as the map
    // from a top or bottom tab, as tall from a side one), its tab joining it
    // where it sits; its depth from the row is defaultH (or as resized).
    property bool fullWidth: false
    // Its size until resized (e.g. its content's), and the least it takes.
    property real defaultW: Style.dp(300)
    property real defaultH: Style.dp(200)
    property real minW: Style.dp(160)
    property real minH: Style.dp(80)
    // The content's frame, for the join under the tab.
    property color color: Style.bgCard
    property color lineColor: Style.lineStrong
    property real radius: Style.dp(8)
    default property alias content: _body.data

    readonly property string side: { dock ? dock.rev : 0; return dock ? dock.sideOf(toolId) : "bottom" }
    readonly property bool vertical: side === "left" || side === "right"
    // Kept for tests and older callers: at the top row.
    readonly property bool atTop: side === "top"
    readonly property bool locked: { dock ? dock.rev : 0; return dock ? dock.isLocked(toolId) : true }
    readonly property bool floating: { dock ? dock.rev : 0; return dock ? dock.isFloating(toolId) : false }
    readonly property bool pinned: { dock ? dock.rev : 0; return dock ? dock.isPinned(toolId) : false }
    readonly property string title: { var t = dock ? dock.tool(toolId) : null; return t ? t.label : toolId }
    readonly property real titleH: Style.dp(26)
    // Floating, while its title bar is dragged: how far it has moved (drawn
    // with this offset; moving the panel itself would end the drag).
    property real dragDx: 0
    property real dragDy: 0
    transform: Translate { x: _pane.dragDx; y: _pane.dragDy }
    // Floating: its place and size so far while moved or resized.
    property real liveFX: -1
    property real liveFY: -1
    property real liveFW: -1
    property real liveFH: -1
    readonly property var fPos: { dock ? dock.rev : 0; return dock ? dock.floatPos(toolId) : { x: -1, y: -1 } }
    readonly property var fSize: { dock ? dock.rev : 0; return dock ? dock.floatSize(toolId) : { w: 0, h: 0 } }
    readonly property real floatW: {
        var w = liveFW >= 0 ? liveFW
              : (fSize.w > 0 ? fSize.w : (fullWidth ? Math.min(pw - 2 * margin, Style.dp(720)) : defaultW))
        return Math.max(Math.min(minW, pw), Math.min(w, pw))
    }
    readonly property real floatH: {
        var h = liveFH >= 0 ? liveFH : (fSize.h > 0 ? fSize.h : defaultH + titleH)
        return Math.max(Math.min(minH + titleH, ph), Math.min(h, ph))
    }
    readonly property real floatX: {
        var x = liveFX >= 0 ? liveFX : (fPos.x >= 0 ? fPos.x : (pw - floatW) / 2)
        return Math.max(0, Math.min(x, pw - floatW))
    }
    readonly property real floatY: {
        var y = liveFY >= 0 ? liveFY : (fPos.y >= 0 ? fPos.y : (ph - floatH) / 3)
        return Math.max(0, Math.min(y, ph - floatH))
    }
    // The tab, in the parent's coordinates ({x, y, w, h}), or null.
    readonly property var tab: {
        if (!dock || !parent)
            return null
        dock.rev
        dock.layoutRev
        parent.width
        parent.height
        return dock.tabRect(toolId, parent)
    }
    readonly property var kept: { dock ? dock.rev : 0; return dock ? dock.sizeOf(toolId) : null }
    // Mid-resize: the size so far (kept on release).
    property real liveW: -1
    property real liveH: -1
    readonly property real pw: parent ? parent.width : 0
    readonly property real ph: parent ? parent.height : 0
    readonly property real margin: Style.dp(8)
    // Where it meets the row: the tab's inner edge (else the parent's edge).
    readonly property real reach: {
        switch (side) {
        case "top": return tab ? Math.min(0, tab.y + tab.h) : 0
        case "left": return tab ? Math.min(0, tab.x + tab.w) : 0
        case "right": return tab ? Math.max(pw, tab.x) : pw
        default: return tab ? Math.max(ph, tab.y) : ph
        }
    }
    // Room away from the row (its depth), and along it.
    readonly property real room: {
        switch (side) {
        case "top": return ph - reach - margin
        case "left": return pw - reach - margin
        case "right": return reach - margin
        default: return reach - margin
        }
    }
    readonly property real alongRoom: (vertical ? ph : pw) - 2 * margin

    // Its depth (away from the row) and length (along it).
    readonly property real depth: {
        var d = vertical ? (fullWidth ? (liveH >= 0 ? liveH : (kept && kept.h > 0 ? kept.h : defaultH))
                                      : (liveW >= 0 ? liveW : (kept && kept.w > 0 ? kept.w : defaultW)))
                         : (liveH >= 0 ? liveH : (kept && kept.h > 0 ? kept.h : defaultH))
        var least = vertical && !fullWidth ? minW : minH
        return Math.max(Math.min(least, room), Math.min(d, room))
    }
    readonly property real length: {
        if (fullWidth)
            return alongRoom
        var l = vertical ? (liveH >= 0 ? liveH : (kept && kept.h > 0 ? kept.h : defaultH))
                         : (liveW >= 0 ? liveW : (kept && kept.w > 0 ? kept.w : defaultW))
        var least = vertical ? minH : minW
        return Math.max(Math.min(least, alongRoom), Math.min(l, alongRoom))
    }
    // Its start along the row: under its tab, kept in the window.
    readonly property real start: {
        if (fullWidth)
            return margin
        var want = tab ? (vertical ? tab.y : tab.x) : margin
        return Math.max(margin, Math.min(want, (vertical ? ph : pw) - length - margin))
    }

    visible: !!dock && dock.isOpen(toolId) && shown
    z: {
        if (!dock)
            return 30
        dock._front
        // Floating panels over docked ones.
        return 30 + dock.frontOf(toolId) + (floating ? 20 : 0)
    }
    width: floating ? floatW : (vertical ? depth : length)
    height: floating ? floatH : (vertical ? length : depth)
    x: floating ? floatX : (side === "left" ? reach : (side === "right" ? reach - width : start))
    y: floating ? floatY : (side === "top" ? reach : (side === "bottom" ? reach - height : start))

    onVisibleChanged: {
        if (!dock)
            return
        dock.setPaneShown(toolId, visible)
        if (visible)
            dock.raise(toolId)
    }
    Component.onCompleted: if (dock) dock.setPaneColor(toolId, color)

    // Floating: a frame round the title bar and the content.
    Rectangle {
        visible: _pane.floating
        anchors.fill: parent
        radius: _pane.radius
        color: _pane.color
        border.color: _pane.lineColor
        border.width: 1
    }

    Item {
        id: _body
        anchors.fill: parent
        anchors.topMargin: _pane.floating ? _pane.titleH : 0
    }

    // Floating: the title bar (its name, pin, lock, close). Drag it to move
    // the panel; dropped on a tool row it docks there; double-click: back
    // to its row.
    Item {
        id: _titleBar
        objectName: "paneTitle"
        visible: _pane.floating
        z: 65
        width: parent.width
        height: _pane.titleH

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: _pane.radius
            color: Style.bgRaised
        }
        Label {
            anchors.verticalCenter: parent.verticalCenter
            x: Style.dp(10)
            text: _pane.title
            color: Style.fg
            font.pixelSize: Style.dp(12)
            font.bold: true
        }
        MouseArea {
            id: _move
            objectName: "paneMove"
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            // Nothing above takes the drag over.
            preventStealing: true
            enabled: !_pane.locked
            hoverEnabled: true
            cursorShape: !enabled ? Qt.ArrowCursor : (pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
            property point start: Qt.point(0, 0)
            property real startX: 0
            property real startY: 0
            onPressed: (m) => {
                start = mapToItem(_pane.parent, m.x, m.y)
                startX = _pane.x
                startY = _pane.y
            }
            onPositionChanged: (m) => {
                if (!pressed)
                    return
                var p = mapToItem(_pane.parent, m.x, m.y)
                // Kept inside the map area.
                _pane.dragDx = Math.max(-startX, Math.min(p.x - start.x, _pane.pw - _pane.width - startX))
                _pane.dragDy = Math.max(-startY, Math.min(p.y - start.y, _pane.ph - _pane.height - startY))
                var s = mapToItem(null, m.x, m.y)
                _pane.dock.dragging = _pane.toolId
                _pane.dock.dropSide = _pane.dock.sideAt(s.x, s.y)
            }
            onReleased: (m) => {
                var dock = _pane.dock
                var side = dock.dropSide
                dock.dragging = ""
                dock.dropSide = ""
                var nx = startX + _pane.dragDx
                var ny = startY + _pane.dragDy
                _pane.dragDx = 0
                _pane.dragDy = 0
                if (side.length) {
                    // Docked on that row where it was let go.
                    var s = mapToItem(null, m.x, m.y)
                    var row = dock.rows[side]
                    var p = row.mapFromItem(null, s.x, s.y)
                    var id = _pane.toolId
                    Qt.callLater(function() {
                        dock.dropAt(id, (row.vertical ? p.y : p.x) - Style.dp(20), side)
                    })
                    return
                }
                dock.setFloatPlace(_pane.toolId, nx, ny)
            }
            onCanceled: {
                _pane.dragDx = 0
                _pane.dragDy = 0
                _pane.dock.dragging = ""
                _pane.dock.dropSide = ""
            }
            onDoubleClicked: _pane.dock.setFloating(_pane.toolId, false)
        }
        Row {
            anchors.right: parent.right
            anchors.rightMargin: Style.dp(8)
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.dp(10)
            component TitleIcon: Label {
                id: _icon
                property alias area: _iconArea
                signal clicked()
                font.family: Style.iconFont
                font.pixelSize: Style.dp(12)
                MouseArea {
                    id: _iconArea
                    anchors.fill: parent
                    anchors.margins: -Style.dp(4)
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: _icon.clicked()
                }
            }
            TitleIcon {
                objectName: "panePin"
                text: _pane.pinned ? "\uF4EC" : "\uF4EB"
                color: _pane.pinned ? Style.accent : (area.containsMouse ? Style.fg : Style.fgMuted)
                onClicked: _pane.dock.setPinned(_pane.toolId, !_pane.pinned)
                ToolTip.visible: area.containsMouse
                ToolTip.delay: 600
                ToolTip.text: _pane.pinned ? "Unpin: hides when you click the map" : "Pin: stays open when you click the map"
            }
            TitleIcon {
                objectName: "paneLock"
                text: _pane.locked ? "\uF47A" : "\uF600"
                color: _pane.locked ? Style.accent : (area.containsMouse ? Style.fg : Style.fgMuted)
                onClicked: _pane.dock.setLocked(_pane.toolId, !_pane.locked)
                ToolTip.visible: area.containsMouse
                ToolTip.delay: 600
                ToolTip.text: _pane.locked ? "Unlock: can be moved and resized" : "Lock: can't be moved or resized"
            }
            Label {
                objectName: "paneClose"
                text: "×"
                font.pixelSize: Style.dp(16)
                color: _closeArea.containsMouse ? Style.fg : Style.fgMuted
                MouseArea {
                    id: _closeArea
                    anchors.fill: parent
                    anchors.margins: -Style.dp(4)
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: _pane.dock.setOpen(_pane.toolId, false)
                }
                ToolTip.visible: _closeArea.containsMouse
                ToolTip.delay: 600
                ToolTip.text: "Close (it floats here again next time)"
            }
        }
    }

    // Floating, unlocked: every edge and corner resizes it.
    component FloatGrip: MouseArea {
        property bool l: false
        property bool r: false
        property bool t: false
        property bool b: false
        property point start: Qt.point(0, 0)
        property rect from: Qt.rect(0, 0, 0, 0)
        visible: _pane.floating
        enabled: !_pane.locked
        z: 75
        hoverEnabled: true
        preventStealing: true
        cursorShape: !enabled ? Qt.ArrowCursor
                     : ((l && t) || (r && b)) ? Qt.SizeFDiagCursor
                     : ((r && t) || (l && b)) ? Qt.SizeBDiagCursor
                     : (l || r) ? Qt.SizeHorCursor : Qt.SizeVerCursor
        onPressed: (m) => {
            start = mapToItem(_pane.parent, m.x, m.y)
            from = Qt.rect(_pane.x, _pane.y, _pane.width, _pane.height)
            _pane.dock.raise(_pane.toolId)
        }
        onPositionChanged: (m) => {
            if (!pressed)
                return
            var p = mapToItem(_pane.parent, m.x, m.y)
            var dx = p.x - start.x
            var dy = p.y - start.y
            var minW = _pane.minW
            var minH = _pane.minH + _pane.titleH
            var x = from.x, y = from.y, w = from.width, h = from.height
            if (r)
                w = Math.max(minW, from.width + dx)
            if (b)
                h = Math.max(minH, from.height + dy)
            if (l) {
                w = Math.max(minW, from.width - dx)
                x = from.x + from.width - w
            }
            if (t) {
                h = Math.max(minH, from.height - dy)
                y = from.y + from.height - h
            }
            _pane.liveFX = x
            _pane.liveFY = y
            _pane.liveFW = w
            _pane.liveFH = h
        }
        onReleased: {
            _pane.dock.setFloatPlace(_pane.toolId, _pane.x, _pane.y, _pane.width, _pane.height)
            _pane.liveFX = -1
            _pane.liveFY = -1
            _pane.liveFW = -1
            _pane.liveFH = -1
        }
        onCanceled: {
            _pane.liveFX = -1
            _pane.liveFY = -1
            _pane.liveFW = -1
            _pane.liveFH = -1
        }
    }
    FloatGrip { objectName: "floatGripLeft"; l: true; width: _pane.grip; y: _pane.corner; height: parent.height - 2 * _pane.corner }
    FloatGrip { objectName: "floatGripRight"; r: true; width: _pane.grip; x: parent.width - width; y: _pane.corner; height: parent.height - 2 * _pane.corner }
    FloatGrip { objectName: "floatGripTop"; t: true; height: Style.dp(4); x: _pane.corner; width: parent.width - 2 * _pane.corner }
    FloatGrip { objectName: "floatGripBottom"; b: true; height: _pane.grip; y: parent.height - height; x: _pane.corner; width: parent.width - 2 * _pane.corner }
    FloatGrip { objectName: "floatGripTopLeft"; l: true; t: true; width: _pane.corner; height: _pane.corner }
    FloatGrip { objectName: "floatGripTopRight"; r: true; t: true; width: _pane.corner; height: _pane.corner; x: parent.width - width }
    FloatGrip { objectName: "floatGripBottomLeft"; l: true; b: true; width: _pane.corner; height: _pane.corner; y: parent.height - height }
    FloatGrip { objectName: "floatGripBottomRight"; r: true; b: true; width: _pane.corner; height: _pane.corner; x: parent.width - width; y: parent.height - height }

    // The join: the frame's border opened where the tab meets it (and a
    // corner the tab sits on squared off).
    Item {
        id: _join
        visible: !!_pane.tab && !_pane.floating
        z: 50
        // The tab along the panel's edge: its start and length there.
        readonly property real t0: _pane.tab ? (_pane.vertical ? _pane.tab.y - _pane.y : _pane.tab.x - _pane.x) : 0
        readonly property real tl: _pane.tab ? (_pane.vertical ? _pane.tab.h : _pane.tab.w) : 0
        readonly property real span: _pane.vertical ? _pane.height : _pane.width
        readonly property real a: Math.max(0, t0)
        readonly property real b: Math.min(span, t0 + tl)
        readonly property real band: _pane.radius + 1
        x: _pane.vertical ? (_pane.side === "left" ? 0 : _pane.width - band) : a
        y: _pane.vertical ? a : (_pane.side === "top" ? 0 : _pane.height - band)
        width: _pane.vertical ? band : Math.max(0, b - a)
        height: _pane.vertical ? Math.max(0, b - a) : band

        Rectangle {
            anchors.fill: parent
            anchors.leftMargin: !_pane.vertical && _join.t0 > 0.5 ? 1 : 0
            anchors.rightMargin: !_pane.vertical && _join.t0 + _join.tl < _join.span - 0.5 ? 1 : 0
            anchors.topMargin: _pane.vertical && _join.t0 > 0.5 ? 1 : 0
            anchors.bottomMargin: _pane.vertical && _join.t0 + _join.tl < _join.span - 0.5 ? 1 : 0
            color: _pane.color
        }
        // The tab's sides carried on to the frame's edge, where the tab sits
        // on a corner.
        Rectangle {
            visible: _join.t0 <= 0.5
            width: _pane.vertical ? parent.width : 1
            height: _pane.vertical ? 1 : parent.height
            color: _pane.lineColor
        }
        Rectangle {
            visible: _join.t0 + _join.tl >= _join.span - 0.5
            x: _pane.vertical ? 0 : parent.width - 1
            y: _pane.vertical ? parent.height - 1 : 0
            width: _pane.vertical ? parent.width : 1
            height: _pane.vertical ? 1 : parent.height
            color: _pane.lineColor
        }
    }

    // A press anywhere on it brings it to the front (and goes on through).
    MouseArea {
        anchors.fill: parent
        z: 60
        acceptedButtons: Qt.AllButtons
        onPressed: (m) => {
            if (_pane.dock)
                _pane.dock.raise(_pane.toolId)
            m.accepted = false
        }
    }

    // Resizing, unlocked: the edge facing the map (its depth), the far edge
    // along the row (its length; not for a full-length panel), and their
    // corner.
    component Grip: MouseArea {
        id: _grip
        property bool deep: false
        property bool long: false
        property real startDepth: 0
        property real startLength: 0
        property point start: Qt.point(0, 0)
        z: 70
        visible: !_pane.floating
        enabled: !_pane.locked
        hoverEnabled: true
        preventStealing: true
        cursorShape: {
            if (!enabled)
                return Qt.ArrowCursor
            if (deep && long)
                return (_pane.side === "top" || _pane.side === "left") ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor
            var acrossX = _pane.vertical ? deep : long
            return acrossX ? Qt.SizeHorCursor : Qt.SizeVerCursor
        }
        onPressed: (m) => {
            start = mapToItem(_pane.parent, m.x, m.y)
            startDepth = _pane.depth
            startLength = _pane.length
            if (_pane.dock)
                _pane.dock.raise(_pane.toolId)
        }
        onPositionChanged: (m) => {
            if (!pressed)
                return
            var p = mapToItem(_pane.parent, m.x, m.y)
            var dx = p.x - start.x
            var dy = p.y - start.y
            if (deep) {
                var grow = { top: dy, bottom: -dy, left: dx, right: -dx }[_pane.side]
                var d = Math.max(_pane.vertical && !_pane.fullWidth ? _pane.minW : _pane.minH, startDepth + grow)
                if (_pane.vertical && !_pane.fullWidth)
                    _pane.liveW = d
                else
                    _pane.liveH = d
            }
            if (long) {
                var l = startLength + (_pane.vertical ? dy : dx)
                if (_pane.vertical)
                    _pane.liveH = Math.max(_pane.minH, l)
                else
                    _pane.liveW = Math.max(_pane.minW, l)
            }
        }
        onReleased: {
            if (_pane.dock) {
                // Kept as {w, h}: a full-length panel keeps only its depth (h).
                if (_pane.fullWidth)
                    _pane.dock.setSize(_pane.toolId, 0, _pane.depth)
                else
                    _pane.dock.setSize(_pane.toolId, _pane.width, _pane.height)
            }
            _pane.liveW = -1
            _pane.liveH = -1
        }
        onCanceled: {
            _pane.liveW = -1
            _pane.liveH = -1
        }
    }

    readonly property real grip: Style.dp(6)
    readonly property real corner: Style.dp(12)

    // The edge facing the map.
    Grip {
        objectName: "paneGripEdge"
        deep: true
        x: _pane.side === "left" ? parent.width - _pane.grip : 0
        y: _pane.side === "top" ? parent.height - _pane.grip : 0
        width: _pane.vertical ? _pane.grip : parent.width - (_pane.fullWidth ? 0 : _pane.corner)
        height: _pane.vertical ? parent.height - (_pane.fullWidth ? 0 : _pane.corner) : _pane.grip
    }
    // The far edge along the row (right for top/bottom, bottom for sides).
    Grip {
        objectName: "paneGripRight"
        visible: !_pane.fullWidth && !_pane.floating
        long: true
        x: _pane.vertical ? (_pane.side === "left" ? 0 : _pane.corner) : parent.width - _pane.grip
        y: _pane.vertical ? parent.height - _pane.grip : (_pane.side === "top" ? 0 : _pane.corner)
        width: _pane.vertical ? parent.width - _pane.corner : _pane.grip
        height: _pane.vertical ? _pane.grip : parent.height - _pane.corner
    }
    Grip {
        objectName: "paneGripCorner"
        visible: !_pane.fullWidth && !_pane.floating
        deep: true
        long: true
        width: _pane.corner
        height: _pane.corner
        x: (_pane.side === "left" || !_pane.vertical) ? parent.width - width : 0
        y: (_pane.side === "top" || _pane.vertical) ? parent.height - height : 0
    }
}
