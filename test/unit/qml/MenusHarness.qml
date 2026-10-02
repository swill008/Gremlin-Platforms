// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

import Gremlin.Menus
import Gremlin.Style

import "../../../qml"

// Every shared menu piece in one window, for menus_smoke.py.
ApplicationWindow {
    id: _win
    width: 900
    height: 700
    visible: true

    property bool saved: false
    property bool canPaste: false
    property bool snapOn: false
    property string ran: ""

    Component.onCompleted: {
        Commands.clear()
        Commands.defineAll([
            { id: "file.save", text: "Save Profile", group: "File", shortcut: "Ctrl+S",
              run: function() { _win.ran = "save" } },
            { id: "edit.paste", text: "Paste", group: "Edit", shortcut: "Ctrl+V",
              enabled: function() { return _win.canPaste }, run: function() { _win.ran = "paste" } },
            { id: "view.snap", text: "Snap", group: "View",
              checked: function() { return _win.snapOn }, run: function() { _win.snapOn = !_win.snapOn } },
            { id: "debug.hidden", text: "Hidden thing", group: "Debug",
              visible: function() { return false }, run: function() {} }
        ], "harness")
    }

    menuBar: ThemedMenuBar {
        ThemedMenu {
            id: _fileMenu
            title: "File"
            ThemedMenuItem { command: "file.save" }
            ThemedMenuSeparator {}
            ThemedMenuItem { command: "edit.paste" }
            ThemedMenuSeparator {}
            ThemedMenuItem { command: "view.snap" }
            ThemedMenuItem { command: "debug.hidden" }
            ThemedMenu {
                id: _emptySub
                title: "Nothing here"
                ThemedMenuItem { text: "Off"; enabled: false }
            }
            ThemedMenu {
                title: "Recent"
                ThemedMenuItem { text: "one.xml" }
            }
            ThemedMenuSeparator {}
            ThemedMenuItem { text: "Exit" }
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12

        OptionMenuPreview {
            id: _preview
            width: 600
        }

        ComboBox {
            id: _long
            width: 200
            model: ["Axis 1", "Axis 2", "Axis 3", "Axis 4", "Axis 5", "Axis 6", "Axis 7",
                    "Axis 8", "Slider 1", "Slider 2", "Dial 1", "Dial 2"]
        }
        TextField {
            id: _field
            width: 200
            text: "Throttle"
        }
        ComboBox {
            id: _short
            width: 200
            model: ["Small", "Medium", "Large"]
        }
    }

    CommandPalette {
        id: _palette
    }

    // A device card, for its right-click menu.
    StatusCard {
        id: _card
        x: 640
        y: 40
        width: 240
        height: 160
        cardName: "Stick"
        direction: "source"
    }

    // Shows a page's menu model.
    ContextMenu {
        id: _probe
    }

    // Rows of the long list showing now.
    function longShown() {
        var out = []
        var list = _long.popup.contentItem.children[1]
        for (var i = 0; i < _long.count; i++) {
            var row = list.itemAtIndex(i)
            if (row && row.visible)
                out.push(row.text)
        }
        return out.join("|")
    }
}
