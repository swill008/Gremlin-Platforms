// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Style

Item {
    id: _root

    property var layout
    property bool locked: false
    signal closeRequested()

    readonly property bool canEdit: layout && !locked
    U.Universal.theme: Style.theme

    Rectangle {
        anchors.fill: parent
        color: Style.background
    }

    function _groupTitles() {
        if (!layout)
            return ["Ungrouped"]
        var rows = layout.groups
        var titles = []
        for (var i = 0; i < rows.length; ++i)
            titles.push(rows[i].title)
        return titles
    }

    Flickable {
        id: _flick
        anchors.fill: parent
        contentWidth: width
        contentHeight: _col.implicitHeight
        clip: true
        ScrollBar.vertical: ScrollBar { }

    ColumnLayout {
        id: _col
        width: _flick.width
        spacing: Style.dp(8)

        RowLayout {
            Label {
                text: "Layout"
                color: "#E4E4E7"
                font.bold: true
                font.pixelSize: Style.dp(16)
                Layout.fillWidth: true
            }
            Button {
                text: "Undo"
                enabled: canEdit && layout.canUndo
                onClicked: layout.undo()
            }
            Button {
                text: "Redo"
                enabled: canEdit && layout.canRedo
                onClicked: layout.redo()
            }
            Button {
                text: "×"
                implicitWidth: Style.dp(28)
                onClicked: _root.closeRequested()
            }
        }

        Label { text: "Add rows"; color: "#A1A1AA"; font.bold: true }
        RowLayout {
            Label { text: "Type"; color: "#E4E4E7" }
            ComboBox {
                id: _addType
                Layout.fillWidth: true
                model: ["Button", "Axis", "Hat"]
            }
        }
        RowLayout {
            Label { text: "Count"; color: "#E4E4E7" }
            SpinBox {
                id: _addCount
                from: 1
                to: 128
                value: 1
                editable: true
            }
        }
        RowLayout {
            Label { text: "Group"; color: "#E4E4E7" }
            TextField {
                id: _addGroup
                Layout.fillWidth: true
                placeholderText: "Ungrouped, or a group name"
                color: "#E4E4E7"
            }
        }
        RowLayout {
            Label { text: "Name"; color: "#E4E4E7" }
            TextField {
                id: _addName
                Layout.fillWidth: true
                placeholderText: "Optional name for each new row"
                color: "#E4E4E7"
            }
        }
        Button {
            text: "Add"
            Layout.fillWidth: true
            highlighted: true
            enabled: canEdit
            onClicked: {
                if (!canEdit)
                    return
                var kinds = ["button", "axis", "hat"]
                layout.addMany(kinds[_addType.currentIndex], _addCount.value, _addGroup.text, _addName.text)
                _addCount.value = 1
            }
        }

        Label { text: "Groups"; color: "#A1A1AA"; font.bold: true }
        RowLayout {
            TextField {
                id: _newGroup
                Layout.fillWidth: true
                placeholderText: "New group name"
                color: "#E4E4E7"
            }
            Button {
                text: "New group"
                enabled: canEdit
                onClicked: {
                    if (canEdit && _newGroup.text.trim().length) {
                        layout.addGroup(_newGroup.text)
                        _newGroup.text = ""
                    }
                }
            }
        }
        ListView {
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(140)
            clip: true
            model: layout ? layout.groups : []
            spacing: Style.dp(4)
            delegate: Rectangle {
                width: ListView.view.width
                height: Style.dp(36)
                color: "#27272A"
                radius: Style.dp(3)
                required property var modelData
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: Style.dp(6)
                    Label {
                        text: modelData.title
                        color: "#E4E4E7"
                        font.bold: true
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Label { text: modelData.summary; color: "#A1A1AA"; font.pixelSize: Style.dp(11) }
                    Button {
                        visible: modelData.name.length > 0
                        text: "Up"
                        enabled: canEdit
                        onClicked: layout.moveGroupUp(modelData.name)
                    }
                    Button {
                        visible: modelData.name.length > 0
                        text: "Down"
                        enabled: canEdit
                        onClicked: layout.moveGroupDown(modelData.name)
                    }
                    Button {
                        visible: modelData.name.length > 0
                        text: "Rename"
                        enabled: canEdit
                        onClicked: {
                            _renameField.text = modelData.name
                            _renameGroup = modelData.name
                            _rename.open()
                        }
                    }
                    Button {
                        visible: modelData.name.length > 0
                        text: "Delete"
                        enabled: canEdit
                        onClicked: layout.removeGroup(modelData.name)
                    }
                }
            }
        }

        Label { text: "Selected rows"; color: "#A1A1AA"; font.bold: true }
        Label {
            text: layout ? layout.selectionLabel : ""
            color: "#E4E4E7"
            Layout.fillWidth: true
        }
        RowLayout {
            TextField {
                id: _selName
                Layout.fillWidth: true
                placeholderText: "Your name"
                color: "#E4E4E7"
            }
            Button {
                text: "Set name"
                enabled: canEdit && layout.selectionCount > 0
                onClicked: layout.setSelectedName(_selName.text)
            }
            Button {
                text: "Clear"
                enabled: canEdit && layout.selectionCount > 0
                onClicked: {
                    _selName.text = ""
                    layout.setSelectedName("")
                }
            }
        }
        RowLayout {
            ComboBox {
                id: _moveGroup
                Layout.fillWidth: true
                model: _root._groupTitles()
            }
            Button {
                text: "Move to group"
                enabled: canEdit && layout.selectionCount > 0
                onClicked: {
                    var title = _moveGroup.currentText
                    layout.moveSelected(title === "Ungrouped" ? "" : title)
                }
            }
        }
        Button {
            text: "Delete rows"
            enabled: canEdit && layout.selectionCount > 0
            onClicked: layout.deleteParents(layout.selectionKeys())
        }

        Label { text: "Order"; color: "#A1A1AA"; font.bold: true }
        Button { text: "Order by system name"; Layout.fillWidth: true; enabled: canEdit; onClicked: layout.sortBySystem() }
        Button { text: "Order by your name"; Layout.fillWidth: true; enabled: canEdit; onClicked: layout.sortByName() }
        Button { text: "Order group names A to Z"; Layout.fillWidth: true; enabled: canEdit; onClicked: layout.sortGroupNames() }

        Label { text: "Find"; color: "#A1A1AA"; font.bold: true }
        TextField {
            id: _search
            Layout.fillWidth: true
            placeholderText: "System name, your name, or group"
            color: "#E4E4E7"
            onTextChanged: _applyFilter()
        }
        ComboBox {
            id: _findType
            Layout.fillWidth: true
            model: ["All types", "Buttons", "Axes", "Hats"]
            onActivated: _applyFilter()
        }
        CheckBox { id: _findUngrouped; text: "Ungrouped"; onClicked: _applyFilter() }
        CheckBox { id: _findNoWriter; text: "No hardware writer"; onClicked: _applyFilter() }
        CheckBox { id: _findNoAction; text: "No actions in this mode"; onClicked: _applyFilter() }
        Button {
            text: "Clear filter"
            Layout.fillWidth: true
            onClicked: {
                _search.text = ""
                _findType.currentIndex = 0
                _findUngrouped.checked = false
                _findNoWriter.checked = false
                _findNoAction.checked = false
                _applyFilter()
            }
        }
        Item { Layout.preferredHeight: Style.dp(12) }
    }
    }

    function _applyFilter() {
        if (!layout)
            return
        var types = ["all", "button", "axis", "hat"]
        layout.setFilter(
            _search.text,
            types[_findType.currentIndex],
            _findUngrouped.checked,
            _findNoWriter.checked,
            _findNoAction.checked
        )
    }

    property string _renameGroup: ""
    Dialog {
        id: _rename
        title: "Rename group"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        TextField {
            id: _renameField
            width: Style.dp(240)
            color: "#E4E4E7"
        }
        onAccepted: {
            if (canEdit)
                layout.renameGroup(_root._renameGroup, _renameField.text)
        }
    }
}
