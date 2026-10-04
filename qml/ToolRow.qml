// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.UI
import Gremlin.Style

// A window's tool row: one button per tool, centred. Every tool behaves the
// same way:
//   - its button opens it, and hides it again;
//   - pinned (the pin on its button), it stays open when the map is clicked;
//     unpinned, it hides when the map is clicked or another tool opens;
//   - locked (the lock on its button), it can't be dragged or resized, nor
//     its button moved; unlocked, the button can be dragged along the row.
// What is open, pinned and locked, and the order, are kept with the window
// layout under `name`. Adding a tool is one more entry in `tools`.
//
//   ToolRow { name: "button-map"; tools: [{ id: "chips", label: "Chips" }] }
//   row.isOpen("chips"), row.setOpen("chips", true), row.mapClicked()
Item {
    id: _row

    property string name: ""
    // [{ id, label, tip }] in their first order.
    property var tools: []
    // Starting state for a tool never used: { id: { open, pinned, locked } }.
    property var defaults: ({})
    // Tools that can't be used now (e.g. only while editing): id -> false.
    property var usable: ({})

    // id -> { open, pinned, locked }, and the ids in the row's order.
    property var _state: ({})
    property var _order: []
    // Bumped on every change: bindings on the getters follow it.
    property int rev: 0

    signal toolChanged(string id)

    implicitHeight: Style.dp(30)

    WindowPlacement { id: _store }

    Component.onCompleted: _load()
    onToolsChanged: _load()

    function _entry(id) {
        var s = _state[id]
        if (!s) {
            var d = defaults[id] || {}
            s = { open: !!d.open, pinned: !!d.pinned, locked: !!d.locked }
            _state[id] = s
        }
        return s
    }

    function _load() {
        var saved = {}
        try {
            saved = JSON.parse(name.length ? _store.toolRowState(name) : "{}") || {}
        } catch (e) {
            saved = {}
        }
        var items = saved.items || {}
        _state = {}
        for (var i = 0; i < tools.length; i++) {
            var id = tools[i].id
            var s = _entry(id)
            var keep = items[id]
            if (keep) {
                s.pinned = !!keep.pinned
                s.locked = !!keep.locked
                // Only a pinned tool reopens in a new session.
                s.open = !!keep.open && s.pinned
            }
        }
        // The saved order, then any tool it doesn't have yet.
        var order = (saved.order || []).filter(function(t) { return _has(t) })
        for (i = 0; i < tools.length; i++) {
            if (order.indexOf(tools[i].id) < 0)
                order.push(tools[i].id)
        }
        _order = order
        rev++
    }

    function _has(id) {
        for (var i = 0; i < tools.length; i++) {
            if (tools[i].id === id)
                return true
        }
        return false
    }

    function _save() {
        rev++
        if (!name.length)
            return
        var items = {}
        for (var i = 0; i < tools.length; i++) {
            var s = _entry(tools[i].id)
            items[tools[i].id] = { open: s.open, pinned: s.pinned, locked: s.locked }
        }
        _store.saveToolRowState(name, JSON.stringify({ order: _order, items: items }))
    }

    function tool(id) {
        for (var i = 0; i < tools.length; i++) {
            if (tools[i].id === id)
                return tools[i]
        }
        return null
    }

    function isUsable(id) { return usable[id] !== false }
    function isOpen(id) { rev; return _entry(id).open && isUsable(id) }
    function isPinned(id) { rev; return _entry(id).pinned }
    function isLocked(id) { rev; return _entry(id).locked }

    // Opening a tool hides the other unpinned ones.
    function setOpen(id, on) {
        var s = _entry(id)
        if (on) {
            for (var i = 0; i < tools.length; i++) {
                var other = tools[i].id
                var o = _entry(other)
                if (other !== id && o.open && !o.pinned) {
                    o.open = false
                    toolChanged(other)
                }
            }
        }
        if (s.open === !!on) {
            _save()
            return
        }
        s.open = !!on
        _save()
        toolChanged(id)
    }

    function toggle(id) { setOpen(id, !_entry(id).open) }

    function setPinned(id, on) {
        _entry(id).pinned = !!on
        _save()
        toolChanged(id)
    }

    function setLocked(id, on) {
        _entry(id).locked = !!on
        _save()
        toolChanged(id)
    }

    // A click on the map: unpinned tools hide.
    function mapClicked() {
        for (var i = 0; i < tools.length; i++) {
            var id = tools[i].id
            var s = _entry(id)
            if (s.open && !s.pinned) {
                s.open = false
                toolChanged(id)
            }
        }
        _save()
    }

    // The row's ids in order (for tests and the window).
    function order() { rev; return _order.slice() }

    // Puts a tool at another place in the row.
    function moveTo(id, index) {
        if (isLocked(id))
            return
        var order = _order.slice()
        var at = order.indexOf(id)
        if (at < 0)
            return
        order.splice(at, 1)
        order.splice(Math.max(0, Math.min(index, order.length)), 0, id)
        _order = order
        _save()
    }

    Rectangle {
        anchors.fill: parent
        color: Style.bgRaised
        Rectangle {
            width: parent.width
            height: 1
            color: Style.line
        }
    }

    Row {
        id: _buttons
        anchors.centerIn: parent
        spacing: Style.dp(6)

        Repeater {
            id: _rep
            model: { _row.rev; return _row._order }
            delegate: Rectangle {
                id: _btn
                required property string modelData
                required property int index
                readonly property var tool: _row.tool(modelData)
                readonly property bool open: { _row.rev; return _row.isOpen(modelData) }
                readonly property bool pinned: { _row.rev; return _row.isPinned(modelData) }
                readonly property bool locked: { _row.rev; return _row.isLocked(modelData) }
                readonly property bool usableNow: { _row.rev; return _row.isUsable(modelData) }
                objectName: "tool:" + modelData
                width: _inner.implicitWidth + Style.dp(12)
                height: _row.height - Style.dp(6)
                radius: Style.dp(4)
                opacity: usableNow ? 1 : 0.45
                color: open ? Style.bgSelected : (_main.containsMouse && usableNow ? Style.bgCard : Style.clear)
                border.color: open ? Style.accent : Style.line
                border.width: 1
                // Where a drag would drop it (while dragging an unlocked button).
                property real dragDx: 0
                transform: Translate { x: _btn.dragDx }
                z: _main.pressed ? 2 : 1

                Row {
                    id: _inner
                    anchors.centerIn: parent
                    spacing: Style.dp(6)
                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: _btn.tool ? _btn.tool.label : _btn.modelData
                        font.pixelSize: Style.dp(12)
                        color: _btn.open ? Style.fg : Style.fgMuted
                    }
                    // Pin: stays open when the map is clicked.
                    Label {
                        id: _pin
                        anchors.verticalCenter: parent.verticalCenter
                        font.family: Style.iconFont
                        font.pixelSize: Style.dp(11)
                        text: _btn.pinned ? "" : ""
                        color: _btn.pinned ? Style.accent : (_pinArea.containsMouse ? Style.fg : Style.fgMuted)
                        MouseArea {
                            id: _pinArea
                            anchors.fill: parent
                            anchors.margins: -Style.dp(3)
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: _row.setPinned(_btn.modelData, !_btn.pinned)
                        }
                        ToolTip.visible: _pinArea.containsMouse
                        ToolTip.delay: 600
                        ToolTip.text: _btn.pinned ? "Unpin: hides when you click the map" : "Pin: stays open when you click the map"
                    }
                    // Lock: can't be dragged or resized.
                    Label {
                        id: _lock
                        anchors.verticalCenter: parent.verticalCenter
                        font.family: Style.iconFont
                        font.pixelSize: Style.dp(11)
                        text: _btn.locked ? "" : ""
                        color: _btn.locked ? Style.accent : (_lockArea.containsMouse ? Style.fg : Style.fgMuted)
                        MouseArea {
                            id: _lockArea
                            anchors.fill: parent
                            anchors.margins: -Style.dp(3)
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: _row.setLocked(_btn.modelData, !_btn.locked)
                        }
                        ToolTip.visible: _lockArea.containsMouse
                        ToolTip.delay: 600
                        ToolTip.text: _btn.locked ? "Unlock: can be moved and resized" : "Lock: can't be moved or resized"
                    }
                }

                // Click: open or hide. Drag (unlocked): move along the row.
                MouseArea {
                    id: _main
                    anchors.fill: parent
                    z: -1
                    hoverEnabled: true
                    enabled: _btn.usableNow
                    // A hand, as over the pool's chips; closed while dragging it.
                    cursorShape: pressed && _moved ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    property real _startX: 0
                    property bool _moved: false
                    onPressed: (m) => {
                        _startX = mapToItem(_buttons, m.x, m.y).x
                        _moved = false
                    }
                    onPositionChanged: (m) => {
                        if (!pressed || _btn.locked)
                            return
                        var dx = mapToItem(_buttons, m.x, m.y).x - _startX
                        if (Math.abs(dx) > Style.dp(4))
                            _moved = true
                        if (_moved)
                            _btn.dragDx = dx
                    }
                    onReleased: (m) => {
                        if (!_moved) {
                            _row.toggle(_btn.modelData)
                            return
                        }
                        // The place whose middle the dragged button's middle passed.
                        var mid = _btn.x + _btn.width / 2 + _btn.dragDx
                        _btn.dragDx = 0
                        var at = 0
                        for (var i = 0; i < _rep.count; i++) {
                            var other = _rep.itemAt(i)
                            if (other && other !== _btn && mid > other.x + other.width / 2)
                                at++
                        }
                        _row.moveTo(_btn.modelData, at)
                    }
                    onCanceled: _btn.dragDx = 0
                }
                ToolTip.visible: _main.containsMouse && !!(_btn.tool && _btn.tool.tip)
                ToolTip.delay: 700
                ToolTip.text: _btn.tool && _btn.tool.tip ? _btn.tool.tip : ""
            }
        }
    }
}
