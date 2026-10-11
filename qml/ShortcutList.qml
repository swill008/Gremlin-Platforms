// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The Shortcuts panel (07 S100, S133): a read-only list of every key and
// what it does, under its top menu's title, then the mouse moves. Nothing in
// it runs a command. The rows are read from the menu bar each time refresh()
// runs (as the panel opens), so they show the menus as they are now. The
// shared search box (01 S141) keeps the rows whose name or key holds its
// text. It draws its own frame: fill its window with it.
//
//   ShortcutList { anchors.fill: parent; menuBar: _menuBar; mouseRows: [...] }
Item {
    id: _list

    // The window's ThemedMenuBar, or a list of its menus.
    property var menuBar: null
    // Shown last: [{ group: "Mouse", text: "Pan", keys: "Space+drag" }].
    property var mouseRows: []
    // Every row read by refresh(): { group, text, keys }.
    property var rows: []
    // What the search keeps, with a heading row ({ heading: true, group })
    // before each group's first row.
    property var shown: []
    // Rows matching the search (headings not counted).
    readonly property int matchCount: {
        var n = 0
        for (var i = 0; i < shown.length; i++) {
            if (!shown[i].heading)
                n++
        }
        return n
    }
    // How tall it wants to be, for its pane's first size.
    readonly property real wanted: _search.implicitHeight + Style.dp(16)
        + Math.min(_view.contentHeight, Style.menuRowH * 18)

    function _menus() {
        var out = []
        var bar = menuBar
        if (!bar)
            return out
        if (Array.isArray(bar))
            return bar.filter(function(m) { return !!m })
        for (var i = 0; i < bar.count; i++) {
            var m = bar.menuAt(i)
            if (m)
                out.push(m)
        }
        return out
    }

    function _readMenu(menu, group, out) {
        if (!menu)
            return
        if (typeof menu.beforeShow === "function")
            menu.beforeShow()
        for (var i = 0; i < menu.count; i++) {
            var item = menu.itemAt(i)
            // Separators have no text.
            if (!item || item.text === undefined || !String(item.text).length)
                continue
            if (item.subMenu) {
                _readMenu(item.subMenu, group, out)
                continue
            }
            // Command rows take their key from the command list.
            if (typeof item.refresh === "function")
                item.refresh()
            if (!item.hint || !String(item.hint).length)
                continue
            out.push({ group: group, text: String(item.text), keys: String(item.hint) })
        }
    }

    // Reads the menus again (call it as the panel opens) and shows them.
    function refresh() {
        var out = []
        var menus = _menus()
        for (var i = 0; i < menus.length; i++) {
            // Every menu, also one greyed out now (Insert, Arrange, Leader
            // and Format outside Edit): it lists keys, it runs nothing.
            _readMenu(menus[i], String(menus[i].title || ""), out)
        }
        var mice = mouseRows || []
        for (var j = 0; j < mice.length; j++) {
            out.push({ group: mice[j].group || "Mouse", text: String(mice[j].text || ""),
                       keys: String(mice[j].keys || "") })
        }
        rows = out
        search()
    }

    // Keeps the rows whose name or key holds the search text.
    function search() {
        var q = _search.text.trim().toLowerCase()
        var out = []
        var lastGroup = null
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i]
            if (q.length && r.text.toLowerCase().indexOf(q) < 0 && r.keys.toLowerCase().indexOf(q) < 0)
                continue
            if (r.group !== lastGroup) {
                out.push({ heading: true, group: r.group })
                lastGroup = r.group
            }
            out.push(r)
        }
        shown = out
        _view.positionViewAtBeginning()
    }

    // To the search box, its text selected.
    function focusSearch() {
        _search.focusField()
    }

    // Shown rows as "Group: Text (Keys)", headings as "# Group", for tests.
    function describe() {
        return shown.map(function(r) {
            return r.heading ? "# " + r.group : r.group + ": " + r.text + " (" + r.keys + ")"
        })
    }

    onVisibleChanged: {
        if (visible)
            refresh()
    }
    Component.onCompleted: refresh()

    Rectangle {
        anchors.fill: parent
        radius: Style.dp(8)
        color: Style.bgCard
        border.color: Style.lineStrong
        border.width: 1
    }
    // Its clicks and wheel are its own, not the map's.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onPressed: (m) => { m.accepted = true }
        onWheel: (w) => { w.accepted = true }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(8)
        spacing: Style.dp(6)

        SearchBox {
            id: _search
            objectName: "shortcutsSearch"
            Layout.fillWidth: true
            placeholder: "Search commands or keys"
            // The window's Ctrl+F belongs to Layers (07 S102).
            findShortcut: false
            count: _list.matchCount
            onTextChanged: _list.search()
        }

        ListView {
            id: _view
            objectName: "shortcutsList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: _list.shown
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            delegate: Item {
                id: _row
                required property var modelData
                required property int index
                readonly property bool heading: !!modelData.heading
                width: _view.width
                height: heading ? Style.menuRowH + Style.dp(8) : Style.menuRowH + Style.dp(2)

                SectionHeading {
                    visible: _row.heading
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: Style.dp(2)
                    text: _row.modelData.group || ""
                }

                Item {
                    visible: !_row.heading
                    anchors.fill: parent
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        x: Style.dp(10)
                        width: parent.width - x - _keys.implicitWidth - Style.dp(24)
                        text: _row.modelData.text || ""
                        font.pixelSize: Style.menuTextPx
                        color: Style.menuText
                        elide: Text.ElideRight
                    }
                    Text {
                        id: _keys
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: Style.dp(10)
                        text: _row.modelData.keys || ""
                        font.pixelSize: Style.menuTextPx - Style.dp(1)
                        color: Style.menuHint
                    }
                }
            }
        }
    }
}
