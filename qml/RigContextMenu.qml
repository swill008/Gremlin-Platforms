// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// The Button Map editor's right-click menu. It lists only what applies to the
// clicked item (rig_menu.js builds the list): a title, a few quick actions,
// then collapsed sections that open one at a time. It reopens the section
// last used for that kind of item, flips to stay inside the window and
// scrolls when taller than it. Keys: Up/Down move, Enter acts, Right/Left
// open/close a section or step a row of values, Esc closes.
Popup {
    id: _menu

    property var ed: null
    property var model: ({ kind: "", title: "", quick: [], sections: [] })
    // Last opened section per kind of item, for this session.
    property var lastSection: ({})
    property string current: ""
    property int focusRow: -1
    // Where the pointer last was on screen: Qt also reports hover when rows
    // move under a still pointer, which must not take the keyboard's row.
    property point _lastHover: Qt.point(-1, -1)

    function hoverRow(area, m, index) {
        var g = area.mapToGlobal(m.x, m.y)
        if (Math.abs(g.x - _lastHover.x) < 0.5 && Math.abs(g.y - _lastHover.y) < 0.5)
            return
        _lastHover = Qt.point(g.x, g.y)
        focusRow = index
    }
    property real anchorX: 0
    property real anchorY: 0
    readonly property real edge: Style.dp(4)
    readonly property real rowH: Style.dp(24)
    readonly property int textPx: Style.dp(13)
    readonly property var rows: _rows(model, current)

    parent: Overlay.overlay
    padding: Style.dp(4)
    width: Style.dp(300)
    height: Math.min(_column.implicitHeight + topPadding + bottomPadding, parent ? parent.height - 2 * edge : 400)
    x: {
        var pw = parent ? parent.width : 0
        if (anchorX + width > pw - edge)
            return Math.max(edge, anchorX - width)
        return anchorX
    }
    y: {
        var ph = parent ? parent.height : 0
        if (anchorY + height > ph - edge)
            return Math.max(edge, Math.min(anchorY - height, ph - edge - height))
        return anchorY
    }
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: Style.bgRaised
        border.color: Style.lineStrong
        border.width: 1
        radius: Style.dp(6)
    }

    // Opens at a point in the editor's coordinates.
    function openAt(ex, ey) {
        refresh()
        var p = ed.mapToItem(parent, ex, ey)
        anchorX = p.x
        anchorY = p.y
        current = lastSection[model.kind] || ""
        focusRow = -1
        open()
        _keys.forceActiveFocus()
    }

    function refresh() {
        if (ed)
            model = ed.menuModel()
    }

    function toggleSection(key) {
        current = (current === key) ? "" : key
        var last = lastSection
        last[model.kind] = current
        lastSection = last
    }

    function run(item, value) {
        if (!item || !item.enabled)
            return
        if (item.kind === "action") {
            close()
            item.run()
        } else if (item.kind === "toggle") {
            item.run()
        } else {
            item.run(value)
        }
    }

    // Visible rows, top to bottom: quick actions, then each section header
    // and, for the open one, its items.
    function _rows(m, open) {
        var out = []
        var q = m.quick || []
        for (var i = 0; i < q.length; i++)
            out.push({ type: "item", item: q[i], indent: false })
        var s = m.sections || []
        for (var k = 0; k < s.length; k++) {
            var isOpen = s[k].key === open
            out.push({ type: "header", key: s[k].key, title: s[k].title, open: isOpen })
            if (!isOpen)
                continue
            for (var j = 0; j < s[k].items.length; j++)
                out.push({ type: "item", item: s[k].items[j], indent: true })
        }
        return out
    }

    // Plain text of what is shown, for tests and the live log.
    function describe() {
        var out = [model.title]
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i]
            if (r.type === "header") {
                out.push((r.open ? "v " : "> ") + r.title)
                continue
            }
            var it = r.item
            var t = (r.indent ? "  " : "") + it.text
            if (it.kind === "toggle")
                t += it.checked ? " [x]" : " [ ]"
            if (it.kind === "choice")
                t += ": " + it.options.map(function(o) { return o.checked ? "*" + o.text : o.text }).join(" | ")
            if (it.kind === "number")
                t += ": " + it.value + it.suffix
            if (!it.enabled)
                t += " (off)"
            out.push(t)
        }
        return out
    }

    // Index of the row showing this text (a header title or an item's text).
    function rowIndexOf(text) {
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i]
            if ((r.type === "header" ? r.title : r.item.text) === text)
                return i
        }
        return -1
    }

    // A row's rectangle in window coordinates.
    function rowRect(i) {
        var it = _repeater.itemAt(i)
        if (!it)
            return null
        var p = it.mapToItem(null, 0, 0)
        return { x: p.x, y: p.y, w: it.width, h: it.height }
    }

    function _selectable(i) {
        var r = rows[i]
        return !!r && (r.type === "header" || r.item.enabled)
    }

    function _move(step) {
        var i = focusRow
        for (var n = 0; n < rows.length; n++) {
            i = (i + step + rows.length) % rows.length
            if (_selectable(i)) {
                focusRow = i
                _flick.ensureVisible(i)
                return
            }
        }
    }

    function _stepChoice(item, step) {
        var opts = item.options
        var at = -1
        for (var i = 0; i < opts.length; i++) {
            if (opts[i].checked)
                at = i
        }
        var next = Math.max(0, Math.min(opts.length - 1, at < 0 ? 0 : at + step))
        run(item, opts[next].value)
    }

    Connections {
        target: _menu.ed
        // Checks and labels follow every change while the menu is open.
        function onTickChanged() {
            if (_menu.opened)
                _menu.refresh()
        }
    }

    contentItem: FocusScope {
        id: _keys
        implicitHeight: _column.implicitHeight

        Keys.onPressed: (e) => {
            var r = _menu.rows[_menu.focusRow]
            if (e.key === Qt.Key_Down) {
                _menu._move(1)
            } else if (e.key === Qt.Key_Up) {
                _menu._move(-1)
            } else if (e.key === Qt.Key_Return || e.key === Qt.Key_Enter || e.key === Qt.Key_Space) {
                if (r && r.type === "header")
                    _menu.toggleSection(r.key)
                else if (r && r.item.kind === "number") {
                    var row = _repeater.itemAt(_menu.focusRow)
                    if (row && row.item)
                        row.item.editValue()
                } else if (r && r.item.kind !== "choice")
                    _menu.run(r.item)
            } else if (e.key === Qt.Key_Right || e.key === Qt.Key_Left) {
                var step = e.key === Qt.Key_Right ? 1 : -1
                if (r && r.type === "header" && r.open === (step < 0))
                    _menu.toggleSection(r.key)
                else if (r && r.type === "item" && r.item.kind === "choice")
                    _menu._stepChoice(r.item, step)
            } else {
                return
            }
            e.accepted = true
        }

        Flickable {
            id: _flick
            anchors.fill: parent
            clip: true
            contentWidth: width
            contentHeight: _column.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            readonly property bool scrolls: contentHeight > height + 1
            ScrollBar.vertical: ScrollBar {
                id: _bar
                policy: _flick.scrolls ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            }

            function ensureVisible(i) {
                var item = _repeater.itemAt(i)
                if (!item)
                    return
                var top = item.y + _rowsColumn.y
                if (top < contentY)
                    contentY = top
                else if (top + item.height > contentY + height)
                    contentY = top + item.height - height
            }

            Column {
                id: _column
                // Rows make room for the scroll bar when there is one.
                width: _flick.width - (_flick.scrolls ? _bar.width : 0)
                spacing: 0

                // Title: what was clicked, with undo and redo.
                RowLayout {
                    width: parent.width
                    height: _menu.rowH + Style.dp(4)
                    spacing: Style.dp(4)
                    Label {
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(6)
                        text: _menu.model.title
                        font.pixelSize: _menu.textPx
                        font.bold: true
                        color: Style.fgStrong
                        elide: Text.ElideRight
                    }
                    Repeater {
                        model: [
                            { label: "Undo", on: _menu.ed && _menu.ed.canUndo, run: function() { _menu.ed.undo() } },
                            { label: "Redo", on: _menu.ed && _menu.ed.canRedo, run: function() { _menu.ed.redo() } }
                        ]
                        delegate: Rectangle {
                            required property var modelData
                            implicitWidth: _undoText.implicitWidth + Style.dp(12)
                            implicitHeight: _menu.rowH - Style.dp(4)
                            radius: Style.dp(4)
                            color: _undoArea.containsMouse && modelData.on ? Style.bgHover : Style.clear
                            border.color: _undoArea.containsMouse && modelData.on ? Style.accent : Style.line
                            Label {
                                id: _undoText
                                anchors.centerIn: parent
                                text: modelData.label
                                font.pixelSize: _menu.textPx - Style.dp(1)
                                color: modelData.on ? Style.fg : Style.fgDisabled
                            }
                            MouseArea {
                                id: _undoArea
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: modelData.on
                                cursorShape: Qt.PointingHandCursor
                                onClicked: modelData.run()
                            }
                        }
                    }
                }
                Rectangle {
                    width: parent.width
                    height: 1
                    color: Style.line
                }

                Column {
                    id: _rowsColumn
                    width: parent.width

                    Repeater {
                        id: _repeater
                        model: _menu.rows
                        delegate: Loader {
                            required property var modelData
                            required property int index
                            width: _rowsColumn.width
                            sourceComponent: modelData.type === "header" ? _header
                                : (modelData.item.kind === "choice" ? _choice
                                   : (modelData.item.kind === "number" ? _number : _plain))
                            onLoaded: {
                                item.row = Qt.binding(function() { return modelData })
                                item.rowIndex = Qt.binding(function() { return index })
                            }
                        }
                    }
                }
            }
        }
    }

    // A section header: click to open or close it.
    Component {
        id: _header
        Rectangle {
            property var row: null
            property int rowIndex: -1
            implicitHeight: _menu.rowH
            // One row lights at a time: the pointer moves the keyboard's row.
            readonly property bool hot: _menu.focusRow === rowIndex
            color: hot ? Style.bgHover : Style.clear
            // An accent bar on the row under the pointer.
            Rectangle {
                visible: parent.hot
                width: Style.dp(3)
                height: parent.height
                color: Style.accent
            }
            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 1
                color: Style.line
            }
            Label {
                anchors.verticalCenter: parent.verticalCenter
                x: Style.dp(6)
                width: parent.width - Style.dp(12)
                text: (row && row.open ? "▾  " : "▸  ") + (row ? row.title : "")
                font.pixelSize: _menu.textPx
                font.bold: !!(row && row.open)
                color: Style.fg
                elide: Text.ElideRight
            }
            MouseArea {
                id: _headArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                // Only a moving pointer: rows that slide under a still one keep the keyboard's row.
                onPositionChanged: (m) => _menu.hoverRow(this, m, rowIndex)
                onClicked: {
                    _menu.focusRow = rowIndex
                    _menu.toggleSection(row.key)
                }
            }
        }
    }

    // An action or a toggle.
    Component {
        id: _plain
        Rectangle {
            property var row: null
            property int rowIndex: -1
            readonly property var it: row ? row.item : null
            implicitHeight: _menu.rowH
            readonly property bool hot: !!(it && it.enabled && _menu.focusRow === rowIndex)
            color: hot ? Style.bgHover : Style.clear
            Rectangle {
                visible: parent.hot
                width: Style.dp(3)
                height: parent.height
                color: Style.accent
            }
            Label {
                anchors.verticalCenter: parent.verticalCenter
                x: row && row.indent ? Style.dp(22) : Style.dp(6)
                width: parent.width - x - Style.dp(26)
                text: it ? it.text : ""
                font.pixelSize: _menu.textPx
                color: it && it.enabled ? Style.fg : Style.fgDisabled
                elide: Text.ElideRight
            }
            Label {
                visible: !!(it && it.kind === "toggle")
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: Style.dp(8)
                text: it && it.checked ? "✓" : ""
                font.pixelSize: _menu.textPx
                color: Style.accent
            }
            MouseArea {
                id: _plainArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                // Only a moving pointer: rows that slide under a still one keep the keyboard's row.
                onPositionChanged: (m) => _menu.hoverRow(this, m, rowIndex)
                enabled: !!(it && it.enabled)
                onClicked: {
                    _menu.focusRow = rowIndex
                    _menu.run(it)
                }
            }
        }
    }

    // A value to type: a label, a small box and its unit; Enter applies it.
    Component {
        id: _number
        Rectangle {
            property var row: null
            property int rowIndex: -1
            readonly property var it: row ? row.item : null
            implicitHeight: _menu.rowH + Style.dp(4)
            color: _menu.focusRow === rowIndex ? Style.bgHover : Style.clear

            function editValue() {
                _numField.forceActiveFocus()
                _numField.selectAll()
            }

            Label {
                id: _numLabel
                x: row && row.indent ? Style.dp(22) : Style.dp(6)
                anchors.verticalCenter: parent.verticalCenter
                width: Style.dp(78)
                text: it ? it.text : ""
                font.pixelSize: _menu.textPx
                color: it && it.enabled ? Style.fgSoft : Style.fgDisabled
            }
            TextField {
                id: _numField
                x: _numLabel.x + _numLabel.width + Style.dp(4)
                anchors.verticalCenter: parent.verticalCenter
                width: Style.dp(64)
                height: _menu.rowH
                topPadding: 0
                bottomPadding: 0
                font.pixelSize: _menu.textPx
                enabled: !!(it && it.enabled)
                text: it ? "" + it.value : ""
                selectByMouse: true
                validator: DoubleValidator {
                    bottom: it ? it.min : -1e9
                    top: it ? it.max : 1e9
                    notation: DoubleValidator.StandardNotation
                }
                onAccepted: {
                    var v = Number(text)
                    if (it && v === v)
                        _menu.run(it, v)
                    _keys.forceActiveFocus()
                }
                Keys.onEscapePressed: _keys.forceActiveFocus()
            }
            Label {
                x: _numField.x + _numField.width + Style.dp(4)
                anchors.verticalCenter: parent.verticalCenter
                text: it ? it.suffix : ""
                font.pixelSize: _menu.textPx
                color: Style.fgSoft
            }
        }
    }

    // A row of values: a label, then the values as small buttons.
    Component {
        id: _choice
        Rectangle {
            id: _choiceRow
            property var row: null
            property int rowIndex: -1
            readonly property var it: row ? row.item : null
            implicitHeight: _flow.implicitHeight + Style.dp(8)
            color: _menu.focusRow === rowIndex ? Style.bgHover : Style.clear
            Label {
                id: _choiceLabel
                x: row && row.indent ? Style.dp(22) : Style.dp(6)
                y: Style.dp(4) + (_menu.rowH - Style.dp(4) - height) / 2
                width: Style.dp(78)
                text: it ? it.text : ""
                font.pixelSize: _menu.textPx
                color: it && it.enabled ? Style.fgSoft : Style.fgDisabled
                elide: Text.ElideRight
            }
            Flow {
                id: _flow
                x: _choiceLabel.x + _choiceLabel.width + Style.dp(4)
                y: Style.dp(4)
                width: parent.width - x - Style.dp(6)
                spacing: Style.dp(3)
                Repeater {
                    model: it ? it.options : []
                    delegate: Rectangle {
                        required property var modelData
                        implicitWidth: _optText.implicitWidth + Style.dp(10)
                        implicitHeight: _menu.rowH - Style.dp(4)
                        radius: Style.dp(4)
                        color: modelData.checked ? Style.accent : (_optArea.containsMouse ? Style.bgRaised : Style.clear)
                        border.color: (modelData.checked || _optArea.containsMouse) ? Style.accent : Style.line
                        border.width: _optArea.containsMouse ? 2 : 1
                        Label {
                            id: _optText
                            anchors.centerIn: parent
                            text: modelData.text
                            font.pixelSize: _menu.textPx - Style.dp(1)
                            color: modelData.checked ? Style.onColor : (it && it.enabled ? Style.fg : Style.fgDisabled)
                        }
                        MouseArea {
                            id: _optArea
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: !!(it && it.enabled)
                            cursorShape: Qt.PointingHandCursor
                            onPositionChanged: (m) => _menu.hoverRow(this, m, _choiceRow.rowIndex)
                            onClicked: {
                                _menu.focusRow = rowIndex
                                _menu.run(it, modelData.value)
                            }
                        }
                    }
                }
            }
        }
    }
}
