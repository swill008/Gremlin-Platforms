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

                deleteButton: IconButton {
                    text: bsi.icons.remove
                    font.pixelSize: Style.dp(12)
                    width: Style.dp(15)
                    enabled: !editorLocked

                    onClicked: () => {
                        if (!editorLocked) {
                            _inputList.model.deleteInput(model.index)
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
            callback: (inputs) => { _inputList.model.addKey(inputs) }
            multipleInputs: false
            eventTypes: ["key"]
        }
    }
}
