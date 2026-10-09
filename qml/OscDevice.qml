// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Menus
import Gremlin.Style

import "confirm.js" as Confirm
import "helpers.js" as Helpers

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

    // Delete: the shared question (01 S140, D-09-OSC-FAULTS).
    function askDelete(uid, address) {
        return Confirm.ask(_root, {
            title: "Delete OSC input?",
            text: "The OSC input " + address + " goes, with its actions.",
            undoable: true,
            note: "You can restore it from Tools › History.",
            action: "Delete",
            onAccept: function() {
                if (!editorLocked) {
                    _inputList.model.deleteInput(uid)
                }
            }
        })
    }

    // Change address: the model checks it; its error shows on the message line.
    function changeAddress(uid, value) {
        var err = _inputList.model.changeName(uid, value)
        if (err && String(err).length) {
            _message.show(String(err), true)
            return false
        }
        _message.clear()
        return true
    }

    function editSettings(uid) {
        if (editorLocked) {
            return
        }
        _addDialog.openForEdit(uid, _inputList.model.inputSettings(uid))
    }

    // The Add window filled in from a settings map (the OSC Monitor's
    // "Add as input…", OscMonitorModel.addSettings): adds, never edits.
    function openAddWith(settings) {
        if (editorLocked || !settings || !settings.address)
            return false
        _addDialog.openForEdit("", settings)
        _addDialog.lastParameters = settings.values || ""
        return true
    }

    // Tools › OSC Monitor (D-09-OSC-MONITOR); one window, shared with the menu.
    function openMonitor() {
        return Helpers.createComponent("WindowOscMonitor.qml")
    }

    OscImportDialog {
        id: _importDialog

        onAccepted: (text) => {
            if (!editorLocked) {
                var result = _inputList.model.importInputs(text)
                _message.show(result ? String(result) : "", false)
            }
        }
    }

    OscAddDialog {
        id: _addDialog

        deviceModel: _inputList.model

        onAccepted: (settings) => {
            if (!editorLocked) {
                _inputList.model.createConfiguredInput(settings)
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
                        if (!editorLocked) {
                            _rowMenu.popup()
                        }
                    }

                    ThemedMenu {
                        id: _rowMenu
                        objectName: "oscRowMenu"

                        ThemedMenuItem {
                            text: "Change Address…"
                            onTriggered: {
                                _textInput.text = label
                                _textInput.callback = (value) => {
                                    _root.changeAddress(model.uid, value)
                                }
                                _textInput.visible = true
                            }
                        }
                        ThemedMenuItem {
                            text: "Edit Settings…"
                            onTriggered: _root.editSettings(model.uid)
                        }
                    }
                }

                deleteButton: IconButton {
                    text: bsi.icons.remove
                    font.pixelSize: Style.dp(12)
                    width: Style.dp(15)
                    enabled: !editorLocked

                    onClicked: () => {
                        if (!editorLocked) {
                            _root.askDelete(model.uid, label)
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

        MessageLine {
            id: _message
            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(10)
            Layout.rightMargin: Style.dp(10)
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
                objectName: "oscMonitor"
                text: "Monitor"
                onClicked: _root.openMonitor()
            }
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
