// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

Item {
    readonly property bool editorLocked: backend && backend.gremlinActive
    enabled: !editorLocked
    opacity: editorLocked ? 0.55 : 1.0

    ActionNames { id: _actionNames }

    DismissibleDialog { id: _deleteGate }

    // Each key is listed once, with the actions of the mode shown.
    Connections {
        target: uiState
        function onModeChanged() {
            if (uiState)
                _inputList.model.setMode(uiState.currentMode)
        }
    }
    Component.onCompleted: {
        if (uiState)
            _inputList.model.setMode(uiState.currentMode)
    }

    // The list was rebuilt (a key added or deleted, another mode or
    // profile): rows move, so the highlight goes to the editor's key, or it
    // stayed on the same row number, now another key. With no key in the
    // editor (another profile loaded), the row still selected is shown.
    Connections {
        target: _inputList.model
        function onModelReset() {
            // Once the list has taken the reset in.
            Qt.callLater(followEditor)
        }
    }

    function followEditor() {
        if (editorLocked || !uiState)
            return
        var current = uiState.currentInput
        if (current && current.isValid) {
            var at = _inputList.model.rowOf(current)
            if (at >= 0 && (at !== _inputList.currentIndex || uiState.currentInputIndex !== at))
                selectRow(at)
            return
        }
        var row = _inputList.currentIndex
        if (row >= 0 && row < _inputList.count)
            uiState.setCurrentInput(_inputList.model.inputIdentifier(row), row)
    }

    // Highlights a row and shows its key in the editor (the editor keeps
    // the row number: the right row is refreshed when its actions change).
    function selectRow(row) {
        if (row < 0 || row >= _inputList.count)
            return
        if (_inputList.currentIndex !== row)
            _inputList.currentIndex = row
        else
            uiState.setCurrentInput(_inputList.model.inputIdentifier(row), row)
    }

    // After a delete the editor moves to the row now in that place (it
    // stayed on the deleted key when the row number didn't change).
    function deleteKey(row, label) {
        _deleteGate.confirmThen("Delete Key?",
            "Delete " + label + " and its actions in this mode?",
            "Delete", function() {
                _inputList.model.deleteInput(row)
                var count = _inputList.count
                _inputList.currentIndex = -1
                if (count > 0)
                    _inputList.currentIndex = Math.min(row, count - 1)
            }, null, true)
    }

    TextInputDialog {
        id: _renameDialog

        visible: false
        width: Style.dp(320)

        property int rowIndex: -1

        onAccepted: (value) => {
            if (editorLocked) {
                return
            }
            _actionNames.setOnModel(_inputList.model, rowIndex, value)
            visible = false
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

            model: KeyboardManagerModel {}

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
                    _renameDialog.rowIndex = model.index
                    _renameDialog.text = description
                    _renameDialog.visible = true
                }

                // A key only in another mode has nothing here to delete.
                deleteButton: IconButton {
                    text: bsi.icons.remove
                    font.pixelSize: Style.dp(12)
                    width: Style.dp(15)
                    visible: model.inMode
                    enabled: !editorLocked

                    onClicked: () => {
                        if (!editorLocked) {
                            deleteKey(model.index, model.name)
                        }
                    }
                }
            }

            footer: Item {
                width: ListView.view.width
                height: Style.dp(10)
            }

            onCurrentIndexChanged: () => {
                if (editorLocked || !uiState) {
                    return
                }
                // No row: the last key was deleted, so the editor lets go of
                // it (it kept the deleted key, which came back when edited).
                if (currentIndex < 0) {
                    if (count === 0)
                        uiState.clearKeyboardInput()
                    return
                }
                uiState.setCurrentInput(
                    model.inputIdentifier(currentIndex),
                    currentIndex
                )
            }
         }

        InputListener {
            Layout.margins: Style.dp(10)
            Layout.alignment: Qt.AlignBottom | Qt.AlignHCenter
            enabled: !editorLocked

            text: "Add Key"
            // The key added is the one shown.
            callback: (inputs) => { selectRow(_inputList.model.addKey(inputs, uiState.currentMode)) }
            multipleInputs: false
            eventTypes: ["key"]
        }
    }
}
