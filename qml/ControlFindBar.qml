// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// The Find line, its filter ticks and the page's Undo bar, shared by the
// control pages (Device Bindings, Keyboard, Logical Device, OSC). The page
// turns changed() into a filter call on its model; the "Can't be sent"
// tick (D-05-CANT-SEND) is the bar's own and tells the model directly
// (layout.setCantSendOnly).
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
    // [{label, name, checked}]: one tick each, on a line of their own;
    // checked (optional, default off) is how the tick starts.
    property var filters: []
    property bool locked: false
    property bool paneOpen: false
    // False: no Undo / Redo bar (a view-only list).
    property bool showUndo: true
    // False: no "Can't be sent" tick (a list without actions to send).
    property bool showCantSend: true
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
        if (_findText.text.length > 0 || _findType.currentIndex > 0 || _cantSend.checked)
            return true
        for (var i = 0; i < _ticks.count; i++) {
            var box = _ticks.itemAt(i)
            if (box && box.checked)
                return true
        }
        return false
    }

    signal changed()
    // Sent by clear() before changed(), so a page resets its own Find
    // boxes (the Device Bindings page's Type and Output, S124) too.
    signal cleared()

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
        if (_cantSend.checked) {
            _cantSend.checked = false
            if (layout)
                layout.setCantSendOnly(false)
        }
        _tickRev++
        cleared()
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
                checked: !!modelData.checked
                onClicked: {
                    _bar._tickRev++
                    _bar.changed()
                }
            }
        }
        // Only inputs with an action that can't be sent (D-05-CANT-SEND).
        CheckBox {
            id: _cantSend
            objectName: "cantSendTick"
            visible: _bar.showCantSend
            text: "Can't be sent"
            onClicked: {
                if (_bar.layout)
                    _bar.layout.setCantSendOnly(checked)
                _bar._tickRev++
                _bar.changed()
            }
        }
    }

    // The page's own Undo / Redo with the last change (01 S143);
    // the same rules as the menu items and Ctrl+Z / Ctrl+Y.
    UndoBar {
        objectName: _bar.namePrefix + "UndoBar"
        visible: _bar.showUndo
        Layout.fillWidth: true
        Layout.leftMargin: Style.dp(8)
        Layout.rightMargin: Style.dp(8)
        canUndo: _bar.showUndo && !!_bar.layout && _bar.layout.canUndo && !_bar.locked && !_bar.paneOpen
        canRedo: _bar.showUndo && !!_bar.layout && _bar.layout.canRedo && !_bar.locked && !_bar.paneOpen
        undoTip: _bar.layout ? _bar.layout.undoTip : ""
        redoTip: _bar.layout ? _bar.layout.redoTip : ""
        lastChange: _bar.layout ? _bar.layout.lastChange : ""
        undone: _bar.layout ? _bar.layout.undone : ""
        onUndo: _bar.layout.undo()
        onRedo: _bar.layout.redo()
    }
}
