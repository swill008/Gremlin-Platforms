// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style
import Gremlin.Menus

// The Button Map editor's Layers panel: every item, top of the stack first,
// with an eye (show or hide) and a lock on each. Chips and groups open to
// their hotspot and leaders, which have their own eye and lock; the
// background photo is the last row. Click a row to select it (Ctrl or Shift
// adds), drag a row to restack it, double-click to rename a drawing. The
// trash icon, or Delete in a row's right-click menu, deletes it
// (ed.deleteLayer: chips back to the pool, leaders and pictures removed,
// hotspots hidden).
Rectangle {
    id: _panel

    property var ed: null
    // A row's menu is open (for tests).
    readonly property bool rowMenuOpen: _rowMenu.opened
    // Older tests' single kind ("all", "chips", "drawings", "pictures",
    // "text"); used only while no kind toggle is on and the search is empty.
    property string filter: "all"
    // The kind toggles that are on (none = every kind) and the search text.
    // Kept on the panel, which the window keeps while it is open: another
    // device's map (a new ed) keeps them (07 S102).
    property var kinds: []
    property string searchText: ""
    readonly property var filterState: ({ kinds: kinds.slice(), query: searchText.trim() })
    readonly property bool filtering: kinds.length > 0 || searchText.trim() !== ""
    readonly property var counts: (filtering && ed && ed.layerCounts) ? (ed.tick, ed.layerCounts(filterState)) : null
    // "12 of 148" or "No layers match" while a filter is on.
    readonly property string countText: !counts ? ""
        : (counts.matches > 0 ? counts.matches + " of " + counts.total : "No layers match")
    readonly property var kindToggles: [
        { key: "all", label: "All" }, { key: "chip", label: "Chips" },
        { key: "group", label: "Groups" }, { key: "hotspot", label: "Hotspots" },
        { key: "leader", label: "Leaders" }, { key: "shape", label: "Shapes" },
        { key: "line", label: "Lines" }, { key: "picture", label: "Pictures" },
        { key: "text", label: "Text" }, { key: "table", label: "Tables" },
        { key: "photo", label: "Photo" }
    ]
    // Chip ids whose hotspot and leader rows are open.
    property var expanded: ({})
    property string renameId: ""
    // Row being dragged to a new place, and where the line shows.
    property int dragRow: -1
    property int dropRow: -1
    readonly property real rowH: Style.dp(26)
    readonly property int textPx: Style.dp(13)
    readonly property var rows: (ed && ed.layerRows)
        ? (ed.tick, ed.layerRows(filtering ? filterState : filter, expanded)) : []

    signal closeRequested()

    // The row the right-click menu was opened on.
    property var menuRow: null

    function deleteRow(row) {
        if (row && ed && ed.canDeleteLayer(row.id, row.part))
            ed.deleteLayer(row.id, row.part)
    }

    ContextMenu {
        id: _rowMenu
        build: function() {
            var row = _panel.menuRow
            if (!row)
                return MenuModel.menu("layer", "", [], [], [])
            var dot = (row.part === "hot") ? "Hide Hotspot" : "Delete"
            return MenuModel.menu("layer", row.name, [
                MenuModel.action(dot, function() { _panel.deleteRow(row) },
                                 !!(_panel.ed && _panel.ed.canDeleteLayer(row.id, row.part)),
                                 { danger: row.part !== "hot" })
            ], [])
        }
    }

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

    // A kind toggle: All turns them all off; any other turns itself on or off.
    function toggleKind(key) {
        if (key === "all") {
            kinds = []
            return
        }
        var k = kinds.slice()
        var at = k.indexOf(key)
        if (at >= 0)
            k.splice(at, 1)
        else
            k.push(key)
        kinds = k
    }

    function kindOn(key) {
        return key === "all" ? kinds.length === 0 : kinds.indexOf(key) >= 0
    }

    // Ctrl+F: to the search box, its text selected.
    function focusSearch() {
        _search.forceActiveFocus()
        _search.selectAll()
    }

    // Enter in the box: every match selected on the map.
    function selectMatches() {
        if (filtering && ed && ed.selectLayerMatches)
            ed.selectLayerMatches(filterState)
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
        // Arrow keys nudge what was picked here (not while a row is being
        // renamed: a double-click's second release would end the rename).
        if (renameId === "")
            ed.focusMap()
    }

    // Group members have no eye or lock of their own (yet).
    function hasFlags(row) {
        return !!row && row.type !== "member"
    }

    function flag(row, which) {
        if (!hasFlags(row))
            return
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
            id: _header
            Layout.fillWidth: true
            spacing: Style.dp(4)
            Label {
                id: _title
                text: "Layers"
                font.pixelSize: _panel.textPx
                font.bold: true
                color: Style.fgStrong
                Layout.fillWidth: true
            }
            Repeater {
                id: _hdrRepeater
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
                id: _closeLabel
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

        // Search layers: filters the rows as you type; Esc or × clears it,
        // Enter selects every match on the map.
        TextField {
            id: _search
            objectName: "layersSearch"
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(26)
            font.pixelSize: _panel.textPx
            placeholderText: "Search layers…"
            selectByMouse: true
            leftPadding: Style.dp(6)
            rightPadding: Style.dp(22)
            topPadding: 0
            bottomPadding: 0
            verticalAlignment: TextInput.AlignVCenter
            Component.onCompleted: text = _panel.searchText
            onTextChanged: if (_panel.searchText !== text) _panel.searchText = text
            onAccepted: _panel.selectMatches()
            Keys.onEscapePressed: (e) => {
                if (text === "") {
                    e.accepted = false
                    return
                }
                _panel.searchText = ""
            }
            Connections {
                target: _panel
                function onSearchTextChanged() {
                    if (_search.text !== _panel.searchText)
                        _search.text = _panel.searchText
                }
            }
            Label {
                id: _clear
                anchors.right: parent.right
                anchors.rightMargin: Style.dp(6)
                anchors.verticalCenter: parent.verticalCenter
                visible: _search.text !== ""
                text: "×"
                font.pixelSize: Style.dp(16)
                color: _clearArea.containsMouse ? Style.fgStrong : Style.fgMuted
                MouseArea {
                    id: _clearArea
                    anchors.fill: parent
                    anchors.margins: -Style.dp(4)
                    hoverEnabled: true
                    cursorShape: Qt.ArrowCursor
                    onClicked: _panel.searchText = ""
                }
            }
        }

        // Show: one toggle per kind; any number on, none lights All.
        Flow {
            id: _kindFlow
            Layout.fillWidth: true
            spacing: Style.dp(3)
            Label {
                id: _showLabel
                height: Style.dp(20)
                verticalAlignment: Text.AlignVCenter
                text: "Show:"
                font.pixelSize: _panel.textPx - Style.dp(2)
                color: Style.fgMuted
            }
            Repeater {
                id: _kindRepeater
                model: _panel.kindToggles
                delegate: Rectangle {
                    required property var modelData
                    readonly property string key: modelData.key
                    readonly property bool on: _panel.kindOn(modelData.key)
                    implicitWidth: _fText.implicitWidth + Style.dp(10)
                    implicitHeight: Style.dp(20)
                    width: implicitWidth
                    height: implicitHeight
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
                        onClicked: _panel.toggleKind(modelData.key)
                    }
                }
            }
        }

        // How many rows match, while a filter is on.
        Label {
            id: _countLine
            Layout.fillWidth: true
            visible: _panel.countText !== ""
            text: _panel.countText
            font.pixelSize: _panel.textPx - Style.dp(2)
            color: Style.fgMuted
            elide: Text.ElideRight
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
                        // A heading (shown only for a matching row under
                        // it) is dimmed.
                        readonly property bool heading: !!row.heading
                        opacity: (heading ? 0.5 : 1) * ((row.hidden || row.hiddenFrom) ? 0.55 : 1)

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
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            preventStealing: true
                            property real pressY: 0
                            onPressed: (m) => {
                                pressY = m.y
                                if (m.button === Qt.RightButton) {
                                    // The row the menu is for shows as picked,
                                    // as a left click does (a row in a Shift
                                    // selection keeps the selection: the menu
                                    // acts on all of it). Selecting rebuilds
                                    // the rows, this one included: after this
                                    // handler, with the menu placed on the panel.
                                    var panel = _panel
                                    var menu = _rowMenu
                                    var row = _row.row
                                    var at = mapToItem(panel, m.x, m.y)
                                    panel.menuRow = row
                                    Qt.callLater(function() {
                                        if (!row.selected && row.id && row.part !== "photo") {
                                            panel.ed.setSelection([row.id])
                                            panel.ed.bump()
                                        }
                                        menu.openAt(panel, at.x, at.y)
                                    })
                                }
                            }
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
                                if (m.button === Qt.RightButton)
                                    return
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
                                font.family: Style.iconFont
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
                                        member: "", leader: "", photo: ""
                                    }
                                    return icons[t] || ""
                                }
                                font.family: Style.iconFont
                                font.pixelSize: Style.dp(12)
                                color: Style.fgSoft
                            }
                            Item {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Label {
                                    objectName: "rowName"
                                    visible: _panel.renameId !== _row.row.id || _row.row.part !== ""
                                    anchors.fill: parent
                                    verticalAlignment: Text.AlignVCenter
                                    text: _row.row.name
                                    font.pixelSize: _panel.textPx
                                    color: _row.heading ? Style.fgMuted : Style.fg
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
                            // Delete (trash), left of the eye so the eye and lock keep
                            // their places: not on the photo; greyed when locked or
                            // (a hotspot) already hidden.
                            Label {
                                readonly property bool can: !!(_panel.ed && _panel.ed.canDeleteLayer(_row.row.id, _row.row.part))
                                Layout.preferredWidth: Style.dp(22)
                                horizontalAlignment: Text.AlignHCenter
                                visible: _row.row.part !== "photo"
                                text: ""
                                font.family: Style.iconFont
                                font.pixelSize: Style.dp(13)
                                color: !can ? Style.fgDisabled : (_trashArea.containsMouse ? Style.dangerText : Style.fgMuted)
                                MouseArea {
                                    id: _trashArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: parent.can
                                    onClicked: _panel.deleteRow(_row.row)
                                }
                                ToolTip.visible: _trashArea.containsMouse
                                ToolTip.delay: 500
                                ToolTip.text: _row.row.part === "hot" ? "Hide hotspot"
                                    : (_row.row.type === "chip" || _row.row.type === "group") ? "Delete (back to the pool)"
                                    : "Delete"
                            }
                            // Eye and lock. Dimmed when the chip they belong to
                            // already hides or locks them.
                            Repeater {
                                model: ["hidden", "locked"]
                                delegate: Label {
                                    required property string modelData
                                    objectName: "flag_" + modelData
                                    readonly property bool on: modelData === "hidden" ? _row.row.hidden : _row.row.locked
                                    readonly property bool from: modelData === "hidden" ? _row.row.hiddenFrom : _row.row.lockedFrom
                                    Layout.preferredWidth: Style.dp(22)
                                    horizontalAlignment: Text.AlignHCenter
                                    text: modelData === "hidden" ? ((on || from) ? "" : "")
                                                                 : ((on || from) ? "" : "")
                                    font.family: Style.iconFont
                                    font.pixelSize: Style.dp(13)
                                    readonly property bool can: _panel.hasFlags(_row.row)
                                    color: !can ? Style.fgDisabled
                                         : (on ? Style.accent : (from ? Style.fgDisabled
                                         : (_flagArea.containsMouse ? Style.fg : Style.fgMuted)))
                                    MouseArea {
                                        id: _flagArea
                                        anchors.fill: parent
                                        enabled: parent.can
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

    // For tests: lays out the panel now.
    function forceLayout() {
        _rowsColumn.forceLayout()
    }

    function _find(item, name) {
        if (!item)
            return null
        if (item.objectName === name)
            return item
        var kids = item.children || []
        for (var i = 0; i < kids.length; i++) {
            var hit = _find(kids[i], name)
            if (hit)
                return hit
        }
        return null
    }

    // For tests: a kind toggle, the box's ×, a row's eye or lock.
    function kindButton(key) {
        for (var i = 0; i < _kindRepeater.count; i++)
            if (_kindRepeater.itemAt(i).key === key)
                return _kindRepeater.itemAt(i)
        return null
    }
    function clearButton() { return _clear }
    function flagButton(i, which) {
        _rowsColumn.forceLayout()
        return _find(_repeater.itemAt(i), "flag_" + which)
    }
    function litKinds() {
        var out = []
        for (var i = 0; i < kindToggles.length; i++)
            if (kindOn(kindToggles[i].key))
                out.push(kindToggles[i].key)
        return out
    }
    function searchFieldText() { return _search.text }
    function searchHasFocus() { return _search.activeFocus }
    function searchSelected() { return _search.selectedText }
    function rowLook(i) {
        _rowsColumn.forceLayout()
        var it = _repeater.itemAt(i)
        var name = _find(it, "rowName")
        return { heading: it.heading, opacity: it.opacity, color: String(name.color),
                 bold: name.font.bold }
    }
    // For tests: the header, box, toggles and count line parts that do not
    // fit inside the panel (or are squeezed below their text's width).
    function clippedParts() {
        var out = []
        var left = Style.dp(6) - 0.5
        var right = width - Style.dp(6) + 0.5
        function check(name, it, needW) {
            if (!it || !it.visible)
                return
            var p = it.mapToItem(_panel, 0, 0)
            if (p.x < left || p.x + it.width > right || it.width + 0.5 < needW)
                out.push(name + " x=" + Math.round(p.x) + " w=" + Math.round(it.width)
                         + " need=" + Math.round(needW) + " panel=" + Math.round(width))
        }
        check("title", _title, _title.implicitWidth)
        for (var h = 0; h < _hdrRepeater.count; h++)
            check("header " + h, _hdrRepeater.itemAt(h), _hdrRepeater.itemAt(h).implicitWidth)
        check("close", _closeLabel, _closeLabel.implicitWidth)
        check("search", _search, Style.dp(60))
        check("show", _showLabel, _showLabel.implicitWidth)
        for (var k = 0; k < _kindRepeater.count; k++)
            check("kind " + _kindRepeater.itemAt(k).key, _kindRepeater.itemAt(k),
                  _kindRepeater.itemAt(k).implicitWidth)
        check("count", _countLine, _countLine.implicitWidth)
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
