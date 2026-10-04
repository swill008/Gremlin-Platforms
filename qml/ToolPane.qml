// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import Gremlin.Style

// A tool's panel, joined to its tab on a tool row (ToolDock, ToolRow): it
// opens from the tab's place, under a tab on the top row or over one on
// the bottom row, reaching the row so the two read as one piece (its border
// is open under the tab). Moving the tab moves the panel; it can't be
// dragged away from it. Unlocked, its free edges resize it (the one facing
// the map, the right one, and their corner); the size is kept with the tool
// (Reset Tool Rows forgets it). The one opened or clicked last is in front.
// The panel's own content fills it and draws its frame: `color` and
// `radius` must match that frame.
//
//   ToolPane { dock: _tools; toolId: "layers"; defaultW: ...; RigLayersPanel { anchors.fill: parent } }
Item {
    id: _pane

    property var dock: null
    property string toolId: ""
    // Shown when its tool is open and this is true (e.g. something selected).
    property bool shown: true
    // As wide as the map (the chip pool), its tab joining it where it sits.
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

    readonly property bool atTop: { dock ? dock.rev : 0; return dock ? dock.sideOf(toolId) === "top" : false }
    readonly property bool locked: { dock ? dock.rev : 0; return dock ? dock.isLocked(toolId) : true }
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
    // Where it meets the row: the tab's inner edge (else the parent's edge).
    readonly property real reach: !tab ? (atTop ? 0 : (parent ? parent.height : 0))
                                       : (atTop ? Math.min(0, tab.y + tab.h) : Math.max(parent.height, tab.y))
    readonly property real room: parent ? (atTop ? parent.height - reach : reach) - Style.dp(8) : 0

    visible: !!dock && dock.isOpen(toolId) && shown
    z: {
        if (!dock)
            return 30
        dock._front
        return 30 + dock.frontOf(toolId)
    }
    width: {
        if (!parent)
            return 0
        if (fullWidth)
            return parent.width - Style.dp(16)
        var w = liveW >= 0 ? liveW : (kept ? kept.w : defaultW)
        return Math.max(minW, Math.min(w, parent.width - Style.dp(16)))
    }
    height: {
        var h = liveH >= 0 ? liveH : (kept && kept.h > 0 ? kept.h : defaultH)
        return Math.max(Math.min(minH, room), Math.min(h, room))
    }
    x: {
        if (!parent)
            return 0
        if (fullWidth)
            return Style.dp(8)
        var want = tab ? tab.x : Style.dp(8)
        return Math.max(Style.dp(8), Math.min(want, parent.width - width - Style.dp(8)))
    }
    y: atTop ? reach : reach - height

    onVisibleChanged: {
        if (!dock)
            return
        dock.setPaneShown(toolId, visible)
        if (visible)
            dock.raise(toolId)
    }
    Component.onCompleted: if (dock) dock.setPaneColor(toolId, color)

    Item {
        id: _body
        anchors.fill: parent
    }

    // The join: the frame's border opened under the tab (and a corner the
    // tab sits on squared off).
    Item {
        id: _join
        visible: !!_pane.tab
        z: 50
        readonly property real tx: _pane.tab ? _pane.tab.x - _pane.x : 0
        readonly property real tw: _pane.tab ? _pane.tab.w : 0
        x: Math.max(0, tx)
        width: Math.max(0, Math.min(_pane.width, tx + tw) - x)
        height: _pane.radius + 1
        y: _pane.atTop ? 0 : _pane.height - height

        Rectangle {
            anchors.fill: parent
            anchors.leftMargin: _join.tx <= 0.5 ? 0 : 1
            anchors.rightMargin: _join.tx + _join.tw >= _pane.width - 0.5 ? 0 : 1
            color: _pane.color
        }
        // The tab's sides carried on to the frame's edge.
        Rectangle {
            visible: _join.tx <= 0.5
            width: 1
            height: parent.height
            color: _pane.lineColor
        }
        Rectangle {
            visible: _join.tx + _join.tw >= _pane.width - 0.5
            x: parent.width - 1
            width: 1
            height: parent.height
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

    // Resizing, unlocked: the edge facing the map, the right edge, and
    // their corner.
    component Grip: MouseArea {
        id: _grip
        property bool across: false
        property bool down: false
        property real startW: 0
        property real startH: 0
        property point start: Qt.point(0, 0)
        z: 70
        enabled: !_pane.locked
        hoverEnabled: true
        preventStealing: true
        cursorShape: !enabled ? Qt.ArrowCursor
                     : (across && down ? (_pane.atTop ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor)
                        : (across ? Qt.SizeHorCursor : Qt.SizeVerCursor))
        onPressed: (m) => {
            start = mapToItem(_pane.parent, m.x, m.y)
            startW = _pane.width
            startH = _pane.height
            if (_pane.dock)
                _pane.dock.raise(_pane.toolId)
        }
        onPositionChanged: (m) => {
            if (!pressed)
                return
            var p = mapToItem(_pane.parent, m.x, m.y)
            if (across)
                _pane.liveW = Math.max(_pane.minW, startW + (p.x - start.x))
            if (down)
                _pane.liveH = Math.max(_pane.minH, startH + (_pane.atTop ? p.y - start.y : start.y - p.y))
        }
        onReleased: {
            if (_pane.dock)
                _pane.dock.setSize(_pane.toolId, _pane.fullWidth ? 0 : _pane.width, _pane.height)
            _pane.liveW = -1
            _pane.liveH = -1
        }
        onCanceled: {
            _pane.liveW = -1
            _pane.liveH = -1
        }
    }

    Grip {
        objectName: "paneGripEdge"
        down: true
        x: 0
        width: parent.width - (_pane.fullWidth ? 0 : Style.dp(12))
        height: Style.dp(6)
        y: _pane.atTop ? parent.height - height : 0
    }
    Grip {
        objectName: "paneGripRight"
        visible: !_pane.fullWidth
        across: true
        x: parent.width - width
        width: Style.dp(6)
        y: _pane.atTop ? 0 : Style.dp(12)
        height: parent.height - Style.dp(12)
    }
    Grip {
        objectName: "paneGripCorner"
        visible: !_pane.fullWidth
        across: true
        down: true
        width: Style.dp(12)
        height: Style.dp(12)
        x: parent.width - width
        y: _pane.atTop ? parent.height - height : 0
    }
}
