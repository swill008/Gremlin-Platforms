// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

import "confirm.js" as Confirm

Item {
    id: _root

    readonly property bool editorLocked: backend && backend.gremlinActive
    enabled: !editorLocked
    opacity: editorLocked ? 0.55 : 1.0

    property int inputIndex
    property InputIdentifier inputIdentifier
    property alias device: _inputList.model

    ActionNames { id: _actionNames }

    function selectOscInput(index) {
        if (editorLocked) {
            return
        }
        _inputList.currentIndex = index
        inputIndex = index
        inputIdentifier = _inputList.model.inputIdentifier(index)
        if (uiState) {
            uiState.setCurrentTab("osc")
            uiState.setCurrentDevice("a7c3e91b-4d2f-4e18-9b06-2f8c1d5a6e70")
            uiState.setCurrentInput(inputIdentifier, index)
        }
    }

    TextInputDialog {
        id: _textInput

        visible: false
        width: Style.dp(300)

        property var callback: null

        onAccepted: (value) => {
            if (editorLocked) {
                return
            }
            callback(value)
            visible = false
        }
    }

    // Clear: the shared question (01 S140).
    function askClear() {
        var n = _inputList.count
        return Confirm.ask(_root, {
            title: "Clear OSC inputs?",
            text: n === 1 ? "The one OSC input in this profile goes, with its actions."
                : "All " + n + " OSC inputs in this profile go, with their actions.",
            undoable: false,
            action: "Clear OSC Inputs",
            onAccept: function() {
                if (!editorLocked) {
                    _inputList.model.clearAllInputs()
                }
            }
        })
    }

    OscImportDialog {
        id: _importDialog

        onAccepted: (text) => {
            if (!editorLocked) {
                _inputList.model.importInputs(text)
            }
        }
    }

    OscAddDialog {
        id: _addDialog

        deviceModel: _inputList.model

        onAccepted: (cmd, mode) => {
            if (!editorLocked) {
                _inputList.model.createMappedInput(mode, cmd)
            }
        }
    }

    ColumnLayout {
        id: _content

        anchors.fill: parent

        JGListView {
            id: _inputList

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(10)

            scrollbarAlwaysVisible: true
            spacing: Style.dp(5)

            model: OscDeviceManagementModel {}

            delegate: InputButton {
                width: _inputList.width - Style.dp(20)
                height: Style.dp(50)
                enabled: !editorLocked

                selected: model.index === _inputList.currentIndex
                onClicked: () => {
                    if (!editorLocked) {
                        _inputList.currentIndex = model.index
                    }
                }
                onRenameRequested: {
                    if (editorLocked) {
                        return
                    }
                    let current = _actionNames.getOnModel(_inputList.model, index)
                    _textInput.text = current.length ? current : ""
                    _textInput.callback = (value) => {
                        _actionNames.setOnModel(_inputList.model, index, value)
                    }
                    _textInput.visible = true
                }

                editButton: IconButton {
                    text: bsi.icons.edit
                    font.pixelSize: Style.dp(12)
                    width: Style.dp(15)
                    enabled: !editorLocked

                    onClicked: () => {
                        if (editorLocked) {
                            return
                        }
                        _textInput.text = label
                        _textInput.callback = (value) => {
                            _inputList.model.changeName(label, value)
                        }
                        _textInput.visible = true
                    }
                }

                deleteButton: IconButton {
                    text: bsi.icons.remove
                    font.pixelSize: Style.dp(12)
                    width: Style.dp(15)
                    enabled: !editorLocked

                    onClicked: () => {
                        if (!editorLocked) {
                            _inputList.model.deleteInput(label)
                        }
                    }
                }
            }

            footer: Item {
                width: ListView.view.width
                height: Style.dp(10)
            }

            onCurrentIndexChanged: () => {
                if (editorLocked) {
                    return
                }
                inputIndex = currentIndex
                inputIdentifier = model.inputIdentifier(currentIndex)
            }
        }

        Connections {
            target: _inputList.model

            function onListenBound(index) {
                _root.selectOscInput(index)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(44)
            Layout.leftMargin: Style.dp(10)
            Layout.rightMargin: Style.dp(10)
            enabled: !editorLocked

            DangerButton {
                objectName: "oscClear"
                text: "Clear…"
                onClicked: _root.askClear()
            }

            Item { Layout.fillWidth: true }

            Button {
                text: "Sort"
                onClicked: _inputList.model.sortInputs()
            }
            Button {
                text: "Add"
                onClicked: {
                    _addDialog.resetFields()
                    _addDialog.open()
                }
            }
            Button {
                text: "Import"
                onClicked: {
                    _importDialog.resetFields()
                    _importDialog.open()
                }
            }
        }
    }
}
