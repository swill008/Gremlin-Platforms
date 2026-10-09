// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style
import "menu_model.js" as MenuModel

// The program's right-click menu, in the Button Map's style. It lists only
// what applies to what was clicked (build() returns the list, made with
// menu_model.js): a title, a few quick rows, then collapsed sections that
// open one at a time. It reopens the section last used for that kind of
// thing. It opens at the pointer and never jumps: what would go below the
// window (from the first section that does not fit) goes into a second
// column beside it, on the right when there is room, else on the left. That
// column sits as high as it needs to fit above the window's bottom, and
// scrolls only when taller than the window.
// Keys: Up/Down move, Enter acts, Right/Left open/close a section or step a
// row of values, Esc closes.
//
//   ContextMenu { id: _menu; build: function() { return MenuModel.menu(...) } }
//   _menu.openAt(item, x, y)    at a point in item's coordinates
//   _menu.openBelow(button)     under a button
Popup {
    id: _menu

    // function() -> a menu from MenuModel.menu(); called on each open and
    // after every toggle or choice.
    property var build: null
    property var model: MenuModel.menu("", "", [], [], [])
    // Rows that cannot be used now are left out, as are empty sections.
    property bool hideUnavailable: true
    property real menuWidth: Style.menuWidth
    property string current: ""
    property int focusRow: -1
    // Where the pointer last was on screen: Qt also reports hover when rows
    // move under a still pointer, which must not take the keyboard's row.
    property point _lastHover: Qt.point(-1, -1)
    property real anchorX: 0
    property real anchorY: 0
    // Stays open after a row is chosen (refreshed to the new state) and can be
    // dragged by its title; a click outside it or Esc closes it (Button Map).
    property bool stayOpen: false
    // Pinned with the pin by the title: a click outside does not close it, it
    // stays open after a row is chosen and stays where it is; Esc closes it
    // (and unpins it).
    property bool pinned: false
    // Moved by dragging the title: placed where dropped, no flipping.
    property bool _dragged: false
    readonly property real edge: Style.menuPad
    readonly property real rowH: Style.menuRowH
    readonly property int textPx: Style.menuTextPx
    readonly property var rows: _rows(model, current)

    function hoverRow(area, m, index) {
        var g = area.mapToGlobal(m.x, m.y)
        if (Math.abs(g.x - _lastHover.x) < 0.5 && Math.abs(g.y - _lastHover.y) < 0.5)
            return
        _lastHover = Qt.point(g.x, g.y)
        focusRow = index
    }

    // The second column: the row it starts at (-1: one column), and its side.
    property int splitAt: -1
    // Between the two columns' panels (each has its own padding).
    readonly property real gap: 2 * Style.menuPad + Style.dp(6)
    readonly property real colW: menuWidth - leftPadding - rightPadding
    // Heights laid out by _layout(): the first column (title, quick rows and
    // the sections that fit), the second, and the part always in the first
    // (title and quick rows).
    property real _col1H: 0
    property real _col2H: 0
    property real _fixedH: 0

    // Where the first column is: at the pointer, or to its left when the
    // menu would go past the window's right edge (as before).
    readonly property real _mainX: {
        var pw = parent ? parent.width : 0
        if (_dragged)
            return Math.max(edge, Math.min(anchorX, pw - edge - menuWidth))
        if (anchorX + menuWidth > pw - edge)
            return Math.max(edge, anchorX - menuWidth)
        return anchorX
    }
    readonly property bool secondLeft: {
        var pw = parent ? parent.width : 0
        return splitAt >= 0 && _mainX + menuWidth + gap + colW > pw - edge
            && _mainX - gap - colW >= edge
    }

    // The first column's top: at the pointer; moved up only as far as the
    // title and quick rows need (right at the window's bottom).
    readonly property real _mainY: {
        var ph = parent ? parent.height : 0
        var need = _fixedH + topPadding + bottomPadding
        return Math.max(edge, Math.min(anchorY, ph - edge - need))
    }
    readonly property real _pads: topPadding + bottomPadding
    // The first column's height: what it holds, inside the window.
    readonly property real _col1Box: Math.min(_col1H + _pads, (parent ? parent.height : 400) - edge - _mainY)
    // The second column: as tall as it needs (the window at most), level with
    // the first column, or higher when it would go below the window.
    readonly property real _col2Box: splitAt >= 0
        ? Math.min(_col2H + _pads, (parent ? parent.height : 400) - 2 * edge) : 0
    readonly property real _col2Y: {
        var ph = parent ? parent.height : 0
        return Math.max(edge, Math.min(_mainY, ph - edge - _col2Box))
    }

    parent: Overlay.overlay
    padding: Style.menuPad
    width: menuWidth + (splitAt >= 0 ? gap + colW : 0)
    x: secondLeft ? _mainX - gap - colW : _mainX
    y: splitAt >= 0 ? Math.min(_mainY, _col2Y) : _mainY
    height: Math.max(_mainY + _col1Box, splitAt >= 0 ? _col2Y + _col2Box : 0) - y
    onRowsChanged: _relayout()
    onOpened: _relayout()
    onAnchorYChanged: _relayout()
    Connections {
        target: _menu.parent
        function onHeightChanged() { _menu._relayout() }
    }

    function _relayout() {
        Qt.callLater(_layout)
    }

    // Puts each row in the first column, or (from the first section that
    // would go below the window) in the second, top to bottom.
    function _layout() {
        if (!_rowsHost || !_col2Host)
            return
        var n = rows.length
        var heights = []
        for (var i = 0; i < n; i++) {
            var it = _repeater.itemAt(i)
            heights.push(it ? it.height : rowH)
        }
        var titleH = _titleBlock.visible ? _titleBlock.height + _titleLine.height : 0
        var first = n
        for (i = 0; i < n; i++) {
            if (rows[i].type === "header") {
                first = i
                break
            }
        }
        var fixed = titleH
        for (i = 0; i < first; i++)
            fixed += heights[i]
        _fixedH = fixed
        var ph = parent ? parent.height : 0
        var avail = ph - edge - _mainY - topPadding - bottomPadding
        var split = -1
        var used = fixed
        i = first
        while (i < n) {
            var j = i + 1
            while (j < n && rows[j].type !== "header")
                j++
            var sectionH = 0
            for (var k = i; k < j; k++)
                sectionH += heights[k]
            if (used + sectionH > avail + 0.5) {
                split = i
                break
            }
            used += sectionH
            i = j
        }
        splitAt = split
        var y1 = 0
        var y2 = 0
        for (i = 0; i < n; i++) {
            var row = _repeater.itemAt(i)
            if (!row)
                continue
            if (split >= 0 && i >= split) {
                row.parent = _col2Host
                row.y = y2
                y2 += heights[i]
            } else {
                row.parent = _rowsHost
                row.y = y1
                y1 += heights[i]
            }
            row.x = 0
        }
        _col1H = titleH + y1
        _col2H = y2
    }
    modal: false
    focus: true
    closePolicy: pinned ? Popup.CloseOnEscape : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)
    onClosed: pinned = false

    // Clicks, the wheel and the pointer on the menu stay on the menu: nothing
    // under it (the Button Map) reacts to them.
    // One panel per column: the menu at the pointer, and the second column
    // beside it as high as it needs.
    background: Item {
        MenuSurface {
            x: _menu.secondLeft ? _menu.colW + _menu.gap : 0
            y: _menu._mainY - _menu.y
            width: _menu.menuWidth
            height: _menu._col1Box
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.AllButtons
                hoverEnabled: true
                onWheel: (w) => { w.accepted = true }
            }
        }
        MenuSurface {
            visible: _menu.splitAt >= 0
            x: _menu.secondLeft ? 0 : _menu.colW + _menu.gap
            y: _menu._col2Y - _menu.y
            width: _menu.menuWidth
            height: _menu._col2Box
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.AllButtons
                hoverEnabled: true
                onWheel: (w) => { w.accepted = true }
            }
        }
    }

    // Opens at a point in item's coordinates (the window's without an item).
    function openAt(item, ix, iy) {
        refresh()
        // A pinned menu stays where it is and shows what was clicked now.
        if (pinned && opened) {
            current = MenuModel.lastSection(model.kind)
            focusRow = -1
            _keys.forceActiveFocus()
            return
        }
        var p = item ? item.mapToItem(parent, ix, iy) : Qt.point(ix, iy)
        anchorX = p.x
        anchorY = p.y
        _dragged = false
        current = MenuModel.lastSection(model.kind)
        focusRow = -1
        open()
        _keys.forceActiveFocus()
    }

    // Opens under a button, lined up with its left edge.
    function openBelow(item) {
        openAt(item, 0, item ? item.height : 0)
    }

    function refresh() {
        if (typeof build === "function")
            model = build() || MenuModel.menu("", "", [], [], [])
    }

    function toggleSection(key) {
        current = (current === key) ? "" : key
        MenuModel.rememberSection(model.kind, current)
    }

    function run(item, value) {
        if (!item || !item.enabled)
            return
        var kindBefore = model.kind
        if (item.kind === "action") {
            if (!item.keepOpen && !stayOpen && !pinned)
                close()
            item.run()
        } else if (item.kind === "toggle") {
            item.run()
        } else if (item.kind === "entry") {
            if (!item.keepOpen && !stayOpen && !pinned)
                close()
            item.run(value)
        } else if (item.kind === "number" && item.go && item.closeOnGo && !pinned) {
            close()
            item.run(value)
        } else {
            item.run(value)
        }
        if (opened) {
            refresh()
            // stayOpen: an action that took away what the menu was for (Break
            // Group, Delete) closes it rather than showing another thing's menu.
            if (stayOpen && !pinned && model.kind !== kindBefore)
                close()
        }
    }

    function _shown(item) {
        return !hideUnavailable || item.enabled || !!item.shownOff
    }

    // Visible rows, top to bottom: quick rows, then each section header and,
    // for the open one, its rows.
    function _rows(m, open) {
        var out = []
        var q = m.quick || []
        for (var i = 0; i < q.length; i++) {
            if (_shown(q[i]))
                out.push({ type: "item", item: q[i], indent: false })
        }
        var s = m.sections || []
        for (var k = 0; k < s.length; k++) {
            var items = s[k].items.filter(_shown)
            if (!items.length)
                continue
            var isOpen = s[k].key === open
            out.push({ type: "header", key: s[k].key, title: s[k].title, open: isOpen })
            if (!isOpen)
                continue
            for (var j = 0; j < items.length; j++)
                out.push({ type: "item", item: items[j], indent: true })
        }
        return out
    }

    // Plain text of what is shown, for tests.
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
                t += ": " + it.value + (it.suffix || "")
            if (it.hint)
                t += " (" + it.hint + ")"
            if (it.tip)
                t += " [tip: " + it.tip + "]"
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
        // Rows just rebuilt (a section opened) are placed on the next turn.
        _layout()
        var it = _repeater.itemAt(i)
        if (!it)
            return null
        var p = it.mapToItem(null, 0, 0)
        return { x: p.x, y: p.y, w: it.width, h: it.height }
    }

    // Runs the row showing this text, as a click would (tests and the
    // palette).
    function activate(text, value) {
        var i = rowIndexOf(text)
        if (i < 0)
            return false
        var r = rows[i]
        if (r.type === "header")
            toggleSection(r.key)
        else
            run(r.item, value)
        return true
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

    contentItem: FocusScope {
        id: _keys
        implicitHeight: Math.max(_menu._col1H, _menu._col2H)

        Keys.onPressed: (e) => {
            var r = _menu.rows[_menu.focusRow]
            if (e.key === Qt.Key_Down) {
                _menu._move(1)
            } else if (e.key === Qt.Key_Up) {
                _menu._move(-1)
            } else if (e.key === Qt.Key_Return || e.key === Qt.Key_Enter || e.key === Qt.Key_Space) {
                if (r && r.type === "header")
                    _menu.toggleSection(r.key)
                else if (r && (r.item.kind === "number" || r.item.kind === "entry")) {
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
            x: _menu.secondLeft ? _menu.colW + _menu.gap : 0
            y: _menu._mainY - _menu.y
            width: _menu.colW
            height: _menu._col1Box - _menu._pads
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
                var second = _menu.splitAt >= 0 && i >= _menu.splitAt
                var flick = second ? _flick2 : _flick
                var top = item.y + (second ? 0 : _rowsHost.y)
                if (top < flick.contentY)
                    flick.contentY = top
                else if (top + item.height > flick.contentY + flick.height)
                    flick.contentY = top + item.height - flick.height
            }

            Column {
                id: _column
                // Rows make room for the scroll bar when there is one.
                width: _flick.width - (_flick.scrolls ? _bar.width : 0)
                spacing: 0

                // Title: what was clicked, with its header buttons and the
                // pin. With stayOpen or pinned, drag it to move the menu.
                RowLayout {
                    id: _titleBlock
                    visible: _menu.model.title.length > 0 || _menu.model.header.length > 0
                    width: parent.width
                    height: visible ? _menu.rowH + Style.dp(4) : 0
                    spacing: Style.dp(4)
                    Label {
                        MouseArea {
                            anchors.fill: parent
                            enabled: _menu.stayOpen || _menu.pinned
                            cursorShape: enabled ? Qt.SizeAllCursor : Qt.ArrowCursor
                            property point _start
                            property point _origin
                            onPressed: (m) => {
                                _start = mapToItem(_menu.parent, m.x, m.y)
                                _origin = Qt.point(_menu._mainX, _menu._mainY)
                            }
                            onPositionChanged: (m) => {
                                if (!pressed)
                                    return
                                var p = mapToItem(_menu.parent, m.x, m.y)
                                _menu._dragged = true
                                _menu.anchorX = _origin.x + p.x - _start.x
                                _menu.anchorY = _origin.y + p.y - _start.y
                            }
                        }
                        Layout.fillWidth: true
                        Layout.leftMargin: Style.dp(6)
                        text: _menu.model.title
                        font.pixelSize: _menu.textPx
                        font.bold: true
                        color: Style.menuTextStrong
                        elide: Text.ElideRight
                    }
                    Label {
                        id: _pin
                        Layout.rightMargin: Style.dp(2)
                        font.family: Style.iconFont
                        font.pixelSize: _menu.textPx
                        // pin-fill when pinned, pin-angle when not.
                        text: _menu.pinned ? "\uF4EC" : "\uF4EB"
                        color: _menu.pinned ? Style.menuAccent : (_pinArea.containsMouse ? Style.menuText : Style.menuTextOff)
                        MouseArea {
                            id: _pinArea
                            anchors.fill: parent
                            anchors.margins: -Style.dp(4)
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: _menu.pinned = !_menu.pinned
                        }
                        ToolTip.visible: _pinArea.containsMouse
                        ToolTip.text: _menu.pinned ? "Unpin: a click outside closes the menu" : "Pin: keep the menu open"
                    }
                    Repeater {
                        model: _menu.model.header
                        delegate: Rectangle {
                            id: _headBtn
                            required property var modelData
                            readonly property bool on: modelData.enabled === undefined || !!modelData.enabled
                            implicitWidth: _headText.implicitWidth + Style.dp(12)
                            implicitHeight: _menu.rowH - Style.dp(4)
                            radius: Style.dp(4)
                            color: _headArea.containsMouse && on ? Style.menuHover : Style.clear
                            border.color: _headArea.containsMouse && on ? Style.menuAccent : Style.menuDivider
                            Label {
                                id: _headText
                                anchors.centerIn: parent
                                text: _headBtn.modelData.label
                                font.pixelSize: _menu.textPx - Style.dp(1)
                                color: _headBtn.on ? Style.menuText : Style.menuTextOff
                            }
                            MouseArea {
                                id: _headArea
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: _headBtn.on
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    // Undo/Redo change the map, the open menu rebuilds and
                                    // this button is replaced while it runs: hold on to the
                                    // menu first, not through this button afterwards.
                                    var menu = _menu
                                    _headBtn.modelData.run()
                                    if (menu)
                                        menu.refresh()
                                }
                            }
                        }
                    }
                }
                Rectangle {
                    id: _titleLine
                    visible: _menu.model.title.length > 0 || _menu.model.header.length > 0
                    width: parent.width
                    height: visible ? 1 : 0
                    color: Style.menuDivider
                }

                // The first column's rows (placed by _layout()).
                Item {
                    id: _rowsHost
                    width: parent.width
                    height: _menu._col1H - (_titleBlock.visible ? _titleBlock.height + _titleLine.height : 0)
                }
            }
        }

        // The second column: the sections that would go below the window.
        Flickable {
            id: _flick2
            visible: _menu.splitAt >= 0
            x: _menu.secondLeft ? 0 : _menu.colW + _menu.gap
            y: _menu._col2Y - _menu.y
            width: _menu.colW
            height: _menu._col2Box - _menu._pads
            clip: true
            contentWidth: width
            contentHeight: _menu._col2H
            boundsBehavior: Flickable.StopAtBounds
            readonly property bool scrolls: contentHeight > height + 1
            ScrollBar.vertical: ScrollBar {
                id: _bar2
                policy: _flick2.scrolls ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            }
            Item {
                id: _col2Host
                width: _flick2.width - (_flick2.scrolls ? _bar2.width : 0)
                height: _menu._col2H
            }
        }

        // Every row, made once; _layout() puts each in its column.
        Repeater {
            id: _repeater
            model: _menu.rows
            delegate: Loader {
                required property var modelData
                required property int index
                width: parent ? parent.width : 0
                sourceComponent: modelData.type === "header" ? _header
                    : ({ choice: _choice, number: _number, entry: _entry })[modelData.item.kind] || _plain
                onLoaded: {
                    item.row = Qt.binding(function() { return modelData })
                    item.rowIndex = Qt.binding(function() { return index })
                    _menu._relayout()
                }
                onHeightChanged: _menu._relayout()
            }
        }
    }

    // A section header: click to open or close it.
    Component {
        id: _header
        MenuRowBackground {
            property var row: null
            property int rowIndex: -1
            implicitHeight: _menu.rowH
            // One row lights at a time: the pointer moves the keyboard's row.
            hot: _menu.focusRow === rowIndex
            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 1
                color: Style.menuDivider
            }
            Label {
                anchors.verticalCenter: parent.verticalCenter
                x: Style.dp(6)
                width: parent.width - Style.dp(12)
                text: (row && row.open ? "▾  " : "▸  ") + (row ? row.title : "")
                font.pixelSize: _menu.textPx
                font.bold: !!(row && row.open)
                color: Style.menuText
                elide: Text.ElideRight
            }
            MouseArea {
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
        MenuRowBackground {
            property var row: null
            property int rowIndex: -1
            readonly property var it: row ? row.item : null
            implicitHeight: _menu.rowH
            hot: !!(it && it.enabled && _menu.focusRow === rowIndex)
            Label {
                anchors.verticalCenter: parent.verticalCenter
                x: row && row.indent ? Style.menuIndent : Style.dp(6)
                width: parent.width - x - Math.max(Style.dp(26), _hint.width + Style.dp(16))
                text: it ? it.text : ""
                font.pixelSize: _menu.textPx
                font.bold: !!(it && it.danger)
                color: !(it && it.enabled) ? Style.menuTextOff : (it.danger ? Style.menuDanger : Style.menuText)
                elide: Text.ElideRight
            }
            // A shortcut, or a toggle's check mark.
            Label {
                id: _hint
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: Style.dp(8)
                text: !it ? "" : (it.kind === "toggle" ? (it.checked ? "✓" : "") : (it.hint || ""))
                font.pixelSize: it && it.kind === "toggle" ? _menu.textPx : _menu.textPx - Style.dp(1)
                color: it && it.kind === "toggle" ? Style.menuAccent : Style.menuHint
            }
            // What it does, as the program's usual tooltip (like the pin's);
            // a greyed-out row shows it too.
            ToolTip.visible: !!(it && it.tip) && _rowArea.containsMouse
            ToolTip.text: it && it.tip ? it.tip : ""
            MouseArea {
                id: _rowArea
                anchors.fill: parent
                hoverEnabled: true
                readonly property bool on: !!(it && it.enabled)
                cursorShape: on ? Qt.PointingHandCursor : Qt.ArrowCursor
                // Only a moving pointer: rows that slide under a still one keep the keyboard's row.
                onPositionChanged: (m) => { if (on) _menu.hoverRow(this, m, rowIndex) }
                // Off: hovered only, for its tooltip; a click does nothing.
                onClicked: {
                    if (!on)
                        return
                    _menu.focusRow = rowIndex
                    _menu.run(it)
                }
            }
        }
    }

    // A value to type: a label, a small box (with ‹ › steps) and its unit
    // or button. Enter applies it.
    Component {
        id: _number
        MenuRowBackground {
            id: _numRow
            property var row: null
            property int rowIndex: -1
            readonly property var it: row ? row.item : null
            implicitHeight: _menu.rowH + Style.dp(4)
            hot: _menu.focusRow === rowIndex
            bar: false

            function editValue() {
                _numField.forceActiveFocus()
                _numField.selectAll()
            }
            function typed() {
                var v = Number(_numField.text)
                if (v !== v)
                    v = it.value
                v = Math.max(it.min, Math.min(it.max, v))
                return it.integer ? Math.round(v) : v
            }
            function apply() {
                if (it)
                    _menu.run(it, typed())
            }
            function stepBy(n) {
                if (!it)
                    return
                var v = Math.max(it.min, Math.min(it.max, typed() + n * it.step))
                _numField.text = "" + v
                if (!it.go)
                    _menu.run(it, v)
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onPositionChanged: (m) => _menu.hoverRow(this, m, _numRow.rowIndex)
            }
            Label {
                id: _numLabel
                x: row && row.indent ? Style.menuIndent : Style.dp(6)
                anchors.verticalCenter: parent.verticalCenter
                width: it && it.go ? parent.width - x - _numBox.width - Style.dp(8) : Style.dp(78)
                text: it ? it.text : ""
                font.pixelSize: _menu.textPx
                color: it && it.enabled ? Style.menuTextSoft : Style.menuTextOff
                elide: Text.ElideRight
            }
            Row {
                id: _numBox
                x: _numLabel.x + _numLabel.width + Style.dp(4)
                anchors.verticalCenter: parent.verticalCenter
                spacing: Style.dp(4)
                Repeater {
                    model: it && it.step ? [-1] : []
                    delegate: _stepButton
                }
                TextField {
                    id: _numField
                    width: Style.dp(it && it.go ? 44 : 64)
                    height: _menu.rowH
                    topPadding: 0
                    bottomPadding: 0
                    horizontalAlignment: it && it.step ? Text.AlignHCenter : Text.AlignLeft
                    font.pixelSize: _menu.textPx
                    enabled: !!(it && it.enabled)
                    text: it ? "" + it.value : ""
                    selectByMouse: true
                    validator: DoubleValidator {
                        bottom: _numRow.it ? _numRow.it.min : -1e9
                        top: _numRow.it ? _numRow.it.max : 1e9
                        notation: DoubleValidator.StandardNotation
                    }
                    onAccepted: {
                        _numRow.apply()
                        if (_menu.opened)
                            _keys.forceActiveFocus()
                    }
                    Keys.onEscapePressed: _keys.forceActiveFocus()
                }
                Repeater {
                    model: it && it.step ? [1] : []
                    delegate: _stepButton
                }
                Label {
                    visible: !!(it && it.suffix)
                    anchors.verticalCenter: parent.verticalCenter
                    text: it ? (it.suffix || "") : ""
                    font.pixelSize: _menu.textPx
                    color: Style.menuTextSoft
                }
                // A button that runs with the value, e.g. Add.
                Rectangle {
                    visible: !!(it && it.go)
                    anchors.verticalCenter: parent.verticalCenter
                    implicitWidth: _goText.implicitWidth + Style.dp(12)
                    implicitHeight: _menu.rowH - Style.dp(4)
                    radius: Style.dp(4)
                    color: _goArea.containsMouse ? Style.menuAccent : Style.clear
                    border.color: Style.menuAccent
                    Label {
                        id: _goText
                        anchors.centerIn: parent
                        text: it ? (it.go || "") : ""
                        font.pixelSize: _menu.textPx - Style.dp(1)
                        color: _goArea.containsMouse ? Style.onColor : Style.menuText
                    }
                    MouseArea {
                        id: _goArea
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: !!(_numRow.it && _numRow.it.enabled)
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _numRow.apply()
                    }
                }
            }
            Component {
                id: _stepButton
                Rectangle {
                    required property var modelData
                    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                    width: Style.dp(18)
                    height: _menu.rowH - Style.dp(4)
                    radius: Style.dp(4)
                    color: _stepArea.containsMouse ? Style.menuHover : Style.clear
                    border.color: _stepArea.containsMouse ? Style.menuAccent : Style.menuDivider
                    Label {
                        anchors.centerIn: parent
                        text: modelData < 0 ? "‹" : "›"
                        font.pixelSize: _menu.textPx
                        color: Style.menuText
                    }
                    MouseArea {
                        id: _stepArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _numRow.stepBy(modelData)
                    }
                }
            }
        }
    }

    // Text to type: a label and a box; Enter applies it.
    Component {
        id: _entry
        MenuRowBackground {
            id: _entryRow
            property var row: null
            property int rowIndex: -1
            readonly property var it: row ? row.item : null
            implicitHeight: _menu.rowH + Style.dp(4)
            hot: _menu.focusRow === rowIndex
            bar: false

            function editValue() {
                _entryField.forceActiveFocus()
            }

            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onPositionChanged: (m) => _menu.hoverRow(this, m, _entryRow.rowIndex)
            }
            Label {
                id: _entryLabel
                x: row && row.indent ? Style.menuIndent : Style.dp(6)
                anchors.verticalCenter: parent.verticalCenter
                width: Style.dp(78)
                text: it ? it.text : ""
                font.pixelSize: _menu.textPx
                color: it && it.enabled ? Style.menuTextSoft : Style.menuTextOff
                elide: Text.ElideRight
            }
            TextField {
                id: _entryField
                x: _entryLabel.x + _entryLabel.width + Style.dp(4)
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - x - Style.dp(6)
                height: _menu.rowH
                topPadding: 0
                bottomPadding: 0
                font.pixelSize: _menu.textPx
                enabled: !!(_entryRow.it && _entryRow.it.enabled)
                placeholderText: _entryRow.it ? (_entryRow.it.placeholder || "") : ""
                selectByMouse: true
                onAccepted: {
                    var value = text.trim()
                    if (!value.length)
                        return
                    text = ""
                    _menu.run(_entryRow.it, value)
                    if (_menu.opened)
                        _keys.forceActiveFocus()
                }
                Keys.onEscapePressed: _keys.forceActiveFocus()
            }
        }
    }

    // A row of values: a label, then the values as small buttons.
    Component {
        id: _choice
        MenuRowBackground {
            id: _choiceRow
            property var row: null
            property int rowIndex: -1
            readonly property var it: row ? row.item : null
            implicitHeight: _flow.implicitHeight + Style.dp(8)
            hot: _menu.focusRow === rowIndex
            bar: false
            Label {
                id: _choiceLabel
                x: row && row.indent ? Style.menuIndent : Style.dp(6)
                y: Style.dp(4) + (_menu.rowH - Style.dp(4) - height) / 2
                width: Style.dp(78)
                text: it ? it.text : ""
                font.pixelSize: _menu.textPx
                color: it && it.enabled ? Style.menuTextSoft : Style.menuTextOff
                elide: Text.ElideRight
            }
            Flow {
                id: _flow
                x: _choiceLabel.x + _choiceLabel.width + Style.dp(4)
                y: Style.dp(4)
                width: parent.width - x - Style.dp(6)
                spacing: Style.dp(3)
                Repeater {
                    model: _choiceRow.it ? _choiceRow.it.options : []
                    delegate: Rectangle {
                        id: _opt
                        required property var modelData
                        implicitWidth: _optText.implicitWidth + Style.dp(10)
                        implicitHeight: _menu.rowH - Style.dp(4)
                        radius: Style.dp(4)
                        color: modelData.checked ? Style.menuAccent : (_optArea.containsMouse ? Style.menuBg : Style.clear)
                        border.color: (modelData.checked || _optArea.containsMouse) ? Style.menuAccent : Style.menuDivider
                        border.width: _optArea.containsMouse ? 2 : 1
                        Label {
                            id: _optText
                            anchors.centerIn: parent
                            text: _opt.modelData.text
                            font.pixelSize: _menu.textPx - Style.dp(1)
                            color: _opt.modelData.checked ? Style.onColor
                                : (_choiceRow.it && _choiceRow.it.enabled ? Style.menuText : Style.menuTextOff)
                        }
                        MouseArea {
                            id: _optArea
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: !!(_choiceRow.it && _choiceRow.it.enabled)
                            cursorShape: Qt.PointingHandCursor
                            onPositionChanged: (m) => _menu.hoverRow(this, m, _choiceRow.rowIndex)
                            onClicked: {
                                _menu.focusRow = _choiceRow.rowIndex
                                _menu.run(_choiceRow.it, _opt.modelData.value)
                            }
                        }
                    }
                }
            }
        }
    }
}
