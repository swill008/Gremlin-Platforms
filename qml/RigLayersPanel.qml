// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// The Button Map editor's Layers panel: every item, top of the stack first,
// with an eye (show or hide) and a lock on each. Chips and groups open to
// their hotspot and leaders, which have their own eye and lock; the
// background photo is the last row. Click a row to select it (Ctrl or Shift
// adds), drag a row to restack it, double-click to rename a drawing.
Rectangle {
    id: _panel

    property var ed: null
    property string filter: "all"
    // Chip ids whose hotspot and leader rows are open.
    property var expanded: ({})
    property string renameId: ""
    // Row being dragged to a new place, and where the line shows.
    property int dragRow: -1
    property int dropRow: -1
    readonly property real rowH: Style.dp(26)
    readonly property int textPx: Style.dp(13)
    readonly property var rows: (ed && ed.layerRows) ? (ed.tick, ed.layerRows(filter, expanded)) : []

    signal closeRequested()

    color: Style.bgCard
    border.color: Style.lineStrong
    border.width: 1
    radius: Style.dp(8)

    // Keeps clicks and the wheel off the map underneath.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onWheel: (w) => { w.accepted = true }
    }

    function toggleOpen(id) {
        var e = expanded
        if (e[id])
            delete e[id]
        else
            e[id] = true
        expanded = Object.assign({}, e)
    }

    function select(row, mods) {
        if (!row || row.part === "photo" || !row.id)
            return
        if (mods & (Qt.ShiftModifier | Qt.ControlModifier))
            ed.toggleSelected(row.id)
        else
            ed.setSelection([row.id])
        ed.bump()
    }

    function flag(row, which) {
        if (row.part === "photo")
            ed.setPhotoFlag(which, !(which === "hidden" ? ed.photoHidden : ed.photoLocked))
        else
            ed.toggleLayerFlag(row.id, row.part, which)
    }

    // Moves the dragged item so it sits just above the item of the row the
    // line is over (or to the bottom when the line is under the last row).
    function drop(fromRow, beforeRow) {
        var moving = rows[fromRow]
        if (!moving || moving.depth !== 0 || moving.part === "photo")
            return
        var target = null
        for (var k = beforeRow; k < rows.length; k++) {
            if (rows[k].depth === 0 && rows[k].part !== "photo") {
                target = rows[k]
                break
            }
        }
        if (target && target.id === moving.id)
            return
        var from = moving.index
        if (!target) {
            ed.moveNodeTo(moving.id, 0)
            return
        }
        var t = target.index
        ed.moveNodeTo(moving.id, from < t ? t : t + 1)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(6)
        spacing: Style.dp(4)

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(4)
            Label {
                text: "Layers"
                font.pixelSize: _panel.textPx
                font.bold: true
                color: Style.fgStrong
                Layout.fillWidth: true
            }
            Repeater {
                model: [
                    { label: "Show all", run: function() { _panel.ed.showAll() } },
                    { label: "Unlock all", run: function() { _panel.ed.unlockAll() } }
                ]
                delegate: Rectangle {
                    required property var modelData
                    implicitWidth: _hdrText.implicitWidth + Style.dp(10)
                    implicitHeight: Style.dp(22)
                    radius: Style.dp(4)
                    color: _hdrArea.containsMouse ? Style.bgSelected : Style.clear
                    border.color: Style.line
                    Label {
                        id: _hdrText
                        anchors.centerIn: parent
                        text: modelData.label
                        font.pixelSize: _panel.textPx - Style.dp(1)
                        color: Style.fg
                    }
                    MouseArea {
                        id: _hdrArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: modelData.run()
                    }
                }
            }
            Label {
                text: "×"
                font.pixelSize: Style.dp(16)
                color: _closeArea.containsMouse ? Style.fgStrong : Style.fgMuted
                MouseArea {
                    id: _closeArea
                    anchors.fill: parent
                    anchors.margins: -Style.dp(4)
                    hoverEnabled: true
                    onClicked: _panel.closeRequested()
                }
            }
        }

        // Filter by kind of item.
        Flow {
            Layout.fillWidth: true
            spacing: Style.dp(3)
            Repeater {
                model: [
                    { key: "all", label: "All" }, { key: "chips", label: "Chips" },
                    { key: "drawings", label: "Drawings" }, { key: "pictures", label: "Pictures" },
                    { key: "text", label: "Text & tables" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool on: _panel.filter === modelData.key
                    implicitWidth: _fText.implicitWidth + Style.dp(10)
                    implicitHeight: Style.dp(20)
                    radius: Style.dp(4)
                    color: on ? Style.accent : (_fArea.containsMouse ? Style.bgSelected : Style.clear)
                    border.color: on ? Style.accent : Style.line
                    Label {
                        id: _fText
                        anchors.centerIn: parent
                        text: modelData.label
                        font.pixelSize: _panel.textPx - Style.dp(2)
                        color: parent.on ? Style.onColor : Style.fg
                    }
                    MouseArea {
                        id: _fArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: _panel.filter = modelData.key
                    }
                }
            }
        }

        Flickable {
            id: _flick
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: _rowsColumn.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            // Scrolls only when the rows do not fit, and never during a row drag.
            interactive: _panel.dragRow < 0 && contentHeight > height + 1
            ScrollBar.vertical: ScrollBar { policy: _flick.contentHeight > _flick.height + 1 ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff }

            Column {
                id: _rowsColumn
                width: _flick.width - Style.dp(8)

                Repeater {
                    id: _repeater
                    model: _panel.rows
                    delegate: Rectangle {
                        id: _row
                        required property var modelData
                        required property int index
                        readonly property var row: modelData
                        width: _rowsColumn.width
                        height: _panel.rowH
                        color: row.selected ? Style.bgSelected : (_rowArea.containsMouse ? Style.bgRaised : Style.clear)
                        opacity: (row.hidden || row.hiddenFrom) ? 0.55 : 1

                        // Drop line: the dragged row lands above this one.
                        Rectangle {
                            visible: _panel.dragRow >= 0 && _panel.dropRow === _row.index
                            anchors.top: parent.top
                            width: parent.width
                            height: Style.dp(2)
                            color: Style.accent
                            z: 3
                        }
                        Rectangle {
                            visible: _panel.dragRow >= 0 && _panel.dropRow === _panel.rows.length && _row.index === _panel.rows.length - 1
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: Style.dp(2)
                            color: Style.accent
                            z: 3
                        }

                        MouseArea {
                            id: _rowArea
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton
                            preventStealing: true
                            property real pressY: 0
                            onPressed: (m) => { pressY = m.y }
                            onPositionChanged: (m) => {
                                if (!pressed || _row.row.depth !== 0 || _row.row.part === "photo")
                                    return
                                if (_panel.dragRow < 0 && Math.abs(m.y - pressY) > Style.dp(6))
                                    _panel.dragRow = _row.index
                                if (_panel.dragRow >= 0) {
                                    var p = mapToItem(_rowsColumn, m.x, m.y)
                                    _panel.dropRow = Math.max(0, Math.min(_panel.rows.length, Math.round(p.y / _panel.rowH)))
                                }
                            }
                            // Dropping or selecting rebuilds the rows, this one
                            // included: reset the drag first, act last.
                            onReleased: (m) => {
                                var panel = _panel
                                var from = panel.dragRow
                                var to = panel.dropRow
                                panel.dragRow = -1
                                panel.dropRow = -1
                                if (from >= 0)
                                    panel.drop(from, to)
                                else
                                    panel.select(_row.row, m.modifiers)
                            }
                            onDoubleClicked: {
                                if (_row.row.renamable)
                                    _panel.renameId = _row.row.id
                                else if (_row.row.depth === 0 && (_row.row.type === "chip"))
                                    _panel.ed.beginRename(_row.row.id, -1)
                            }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Style.dp(4) + _row.row.depth * Style.dp(16)
                            anchors.rightMargin: Style.dp(2)
                            spacing: Style.dp(2)

                            // Open or close a chip's hotspot and leader rows.
                            Label {
                                Layout.preferredWidth: Style.dp(14)
                                text: _row.row.canOpen ? (_row.row.open ? "" : "") : ""
                                font.family: "bootstrap-icons"
                                font.pixelSize: Style.dp(10)
                                color: Style.fgMuted
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: _row.row.canOpen
                                    onClicked: _panel.toggleOpen(_row.row.id)
                                }
                            }
                            Label {
                                Layout.preferredWidth: Style.dp(18)
                                text: {
                                    var t = _row.row.type
                                    var icons = {
                                        chip: "", group: "", shape: "", line: "",
                                        picture: "", text: "", table: "", hotspot: "",
                                        leader: "", photo: ""
                                    }
                                    return icons[t] || ""
                                }
                                font.family: "bootstrap-icons"
                                font.pixelSize: Style.dp(12)
                                color: Style.fgSoft
                            }
                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Label {
                                    visible: _panel.renameId !== _row.row.id || _row.row.part !== ""
                                    anchors.fill: parent
                                    verticalAlignment: Text.AlignVCenter
                                    text: _row.row.name
                                    font.pixelSize: _panel.textPx
                                    color: Style.fg
                                    elide: Text.ElideRight
                                }
                                TextField {
                                    id: _nameField
                                    visible: _panel.renameId === _row.row.id && _row.row.part === ""
                                    anchors.fill: parent
                                    font.pixelSize: _panel.textPx
                                    text: _row.row.name
                                    selectByMouse: true
                                    onVisibleChanged: if (visible) { forceActiveFocus(); selectAll() }
                                    onAccepted: {
                                        // Renaming rebuilds the rows, this one included: finish first.
                                        var panel = _panel
                                        var id = _row.row.id
                                        var name = text
                                        panel.renameId = ""
                                        panel.ed.renameLayer(id, name)
                                    }
                                    Keys.onEscapePressed: _panel.renameId = ""
                                    onActiveFocusChanged: if (!activeFocus && visible) _panel.renameId = ""
                                }
                            }
                            // Eye and lock. Dimmed when the chip they belong to
                            // already hides or locks them.
                            Repeater {
                                model: ["hidden", "locked"]
                                delegate: Label {
                                    required property string modelData
                                    readonly property bool on: modelData === "hidden" ? _row.row.hidden : _row.row.locked
                                    readonly property bool from: modelData === "hidden" ? _row.row.hiddenFrom : _row.row.lockedFrom
                                    Layout.preferredWidth: Style.dp(22)
                                    horizontalAlignment: Text.AlignHCenter
                                    text: modelData === "hidden" ? ((on || from) ? "" : "")
                                                                 : ((on || from) ? "" : "")
                                    font.family: "bootstrap-icons"
                                    font.pixelSize: Style.dp(13)
                                    color: on ? Style.accent : (from ? Style.fgDisabled : (_flagArea.containsMouse ? Style.fg : Style.fgMuted))
                                    MouseArea {
                                        id: _flagArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: _panel.flag(_row.row, parent.modelData)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Text lines of the rows, for tests.
    function describe() {
        var out = []
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i]
            var t = "  ".repeat(r.depth) + (r.canOpen ? (r.open ? "v " : "> ") : "") + r.name
            if (r.hidden) t += " [hidden]"
            if (r.locked) t += " [locked]"
            if (r.hiddenFrom) t += " (hidden by chip)"
            if (r.lockedFrom) t += " (locked by chip)"
            if (r.selected) t += " *"
            out.push(t)
        }
        return out
    }

    // A row's rectangle in window coordinates (laid out first, as rows may
    // just have changed).
    function rowRect(i) {
        _rowsColumn.forceLayout()
        var it = _repeater.itemAt(i)
        if (!it)
            return null
        var p = it.mapToItem(null, 0, 0)
        return { x: p.x, y: p.y, w: it.width, h: it.height }
    }
}
