// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The Find line, its filter ticks and the page's Undo bar, shared by the
// control pages (Logical Device, OSC). The page turns changed() into a
// filter call on its model.
ColumnLayout {
    id: _bar

    property var layout: null
    property string namePrefix: "control"
    property string placeholder: ""
    property var typeChoices: [
        { label: "All types", value: "all" },
        { label: "Buttons", value: "button" },
        { label: "Axes", value: "axis" },
        { label: "Hats", value: "hat" }
    ]
    // [{label, name}]: one tick each, on a line of their own.
    property var filters: []
    property bool locked: false
    property bool paneOpen: false
    // Page-only header buttons, after Clear: buttons: [ Button { ... } ].
    property alias buttons: _extras.data

    // An alias, not a binding: changed() is sent from the box's own textChanged.
    readonly property alias text: _findText.text
    readonly property string typeValue: {
        var choice = typeChoices[_findType.currentIndex]
        return choice ? choice.value : ""
    }
    property int _tickRev: 0
    readonly property bool filtering: {
        _tickRev
        if (_findText.text.length > 0 || _findType.currentIndex > 0)
            return true
        for (var i = 0; i < _ticks.count; i++) {
            var box = _ticks.itemAt(i)
            if (box && box.checked)
                return true
        }
        return false
    }

    signal changed()

    function isChecked(name) {
        for (var i = 0; i < _ticks.count; i++) {
            var box = _ticks.itemAt(i)
            if (box && box.name === name)
                return box.checked
        }
        return false
    }

    function clear() {
        _findText.clear()
        _findType.currentIndex = 0
        for (var i = 0; i < _ticks.count; i++) {
            var box = _ticks.itemAt(i)
            if (box)
                box.checked = false
        }
        _tickRev++
        changed()
    }

    Layout.fillWidth: true
    spacing: Style.dp(6)

    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: Style.dp(8)
        Layout.rightMargin: Style.dp(8)
        Layout.topMargin: Style.dp(8)
        spacing: Style.dp(8)
        Label {
            text: "Find"
            color: Style.fgMuted
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: Style.dp(5)
        }
        // The shared search box (01 S141): Ctrl+F, ×, Esc, "N found".
        SearchBox {
            id: _findText
            objectName: _bar.namePrefix + "Find"
            Layout.fillWidth: true
            Layout.minimumWidth: Style.dp(160)
            Layout.alignment: Qt.AlignTop
            placeholder: _bar.placeholder
            count: _bar.layout ? _bar.layout.parentCount : 0
            onTextChanged: _bar.changed()
        }
        ComboBox {
            id: _findType
            Layout.alignment: Qt.AlignTop
            model: _bar.typeChoices.map((c) => c.label)
            onActivated: _bar.changed()
        }
        Button {
            text: "Clear"
            Layout.alignment: Qt.AlignTop
            onClicked: _bar.clear()
        }
        RowLayout {
            id: _extras
            Layout.alignment: Qt.AlignTop
            Layout.fillWidth: false
            visible: children.length > 0
            spacing: Style.dp(8)
        }
        Label {
            // Why nothing here can be changed, and how to change it.
            text: _bar.locked ? "Profile running: stop it to edit" : ""
            color: Style.fgMuted
        }
    }
    // The filters, on a line of their own: they wrap when the page is
    // narrow instead of running under a side panel.
    Flow {
        Layout.fillWidth: true
        Layout.leftMargin: Style.dp(8)
        Layout.rightMargin: Style.dp(8)
        spacing: Style.dp(8)
        Repeater {
            id: _ticks
            model: _bar.filters
            delegate: CheckBox {
                required property var modelData
                readonly property string name: modelData.name
                text: modelData.label
                onClicked: {
                    _bar._tickRev++
                    _bar.changed()
                }
            }
        }
    }

    // The page's own Undo / Redo with the last change (01 S143);
    // the same rules as the menu items and Ctrl+Z / Ctrl+Y.
    UndoBar {
        objectName: _bar.namePrefix + "UndoBar"
        Layout.fillWidth: true
        Layout.leftMargin: Style.dp(8)
        Layout.rightMargin: Style.dp(8)
        canUndo: !!_bar.layout && _bar.layout.canUndo && !_bar.locked && !_bar.paneOpen
        canRedo: !!_bar.layout && _bar.layout.canRedo && !_bar.locked && !_bar.paneOpen
        undoTip: _bar.layout ? _bar.layout.undoTip : ""
        redoTip: _bar.layout ? _bar.layout.redoTip : ""
        lastChange: _bar.layout ? _bar.layout.lastChange : ""
        undone: _bar.layout ? _bar.layout.undone : ""
        onUndo: _bar.layout.undo()
        onRedo: _bar.layout.redo()
    }
}
