// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Profile
import Gremlin.Style

Item {
    id: _root

    property InputItemModel inputItemModel
    property int inputIndex
    property bool isOutput: false
    property bool holdModel: false
    property bool inlineMode: false
    property bool hideControlSetup: false
    property bool catalogSequence: false
    property int onlySequence: -1
    property color editorFill: Style.infoFillDeep
    property color editorEdge: Style.info
    property color editorAccent: Style.info
    property int editorRadius: Style.dp(3)
    property int editorBorderW: Style.dp(1)
    property int editorAccentW: Style.dp(3)
    property bool showAccent: true
    property int editorPad: Style.dp(10)
    property int editorPadTop: Style.dp(10)
    property int editorPadRight: Style.dp(10)
    property int editorPadBottom: Style.dp(10)
    property int editorPadLeft: Style.dp(10)
    readonly property bool editorLocked: backend && backend.gremlinActive && !isOutput
    enabled: true
    opacity: editorLocked ? 0.55 : 1.0
    implicitHeight: inlineMode ? Math.max(Style.dp(80), _content.implicitHeight) + editorPadTop + editorPadBottom : Style.dp(200)

    Rectangle {
        visible: inlineMode
        anchors.fill: parent
        color: editorFill
        border.color: editorEdge
        border.width: editorBorderW
        radius: editorRadius
    }

    Rectangle {
        visible: inlineMode && showAccent && editorAccentW > 0
        width: editorAccentW
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: Math.max(Style.dp(1), editorBorderW)
        color: editorAccent
    }

    Component.onCompleted: {
        if (holdModel || !backend || !uiState)
            return
        _root.inputItemModel = backend.getInputItem(
            uiState.currentInput,
            uiState.currentInputIndex
        )
    }

    Connections {
        target: uiState

        function onInputChanged() {
            if (_root.holdModel || !backend || !uiState)
                return
            _root.inputItemModel = backend.getInputItem(
                uiState.currentInput,
                uiState.currentInputIndex
            )
        }
    }

    Connections {
        target: signal

        function onReloadCurrentInputItem() {
            if (_root.holdModel || !backend || !uiState)
                return
            _root.inputItemModel = backend.getInputItem(
                uiState.currentInput,
                uiState.currentInputIndex
            )
        }
    }

    DismissibleDialog {
        id: _selectInputDialog

        titleText: "Select an input"
        messageText: "Select an input first before adding an action sequence."
        confirmText: "OK"
    }

    ColumnLayout {
        id: _content

        anchors.fill: inlineMode ? undefined : parent
        x: inlineMode ? editorPadLeft : 0
        y: inlineMode ? editorPadTop : 0
        width: parent.width - (inlineMode ? editorPadLeft + editorPadRight : 0)
        spacing: Style.dp(8)

        Repeater {
            id: _inlineRepeater
            model: _root.inlineMode && _root.onlySequence < 0 ? _root.inputItemModel : null

            delegate: InputItemBinding {
                Layout.fillWidth: true
                enabled: !editorLocked
                inputBinding: modelData
                inputItemModel: _root.inputItemModel
                hideControlSetup: _root.hideControlSetup
                catalogSequence: _root.catalogSequence
            }
        }

        Loader {
            Layout.fillWidth: true
            active: _root.inlineMode && _root.onlySequence >= 0 && _root.inputItemModel
                    && _root.onlySequence < _root.inputItemModel.rowCount()
            sourceComponent: InputItemBinding {
                width: _content.width
                enabled: !editorLocked
                inputItemModel: _root.inputItemModel
                inputBinding: _root.inputItemModel.data(_root.inputItemModel.index(_root.onlySequence, 0))
                hideControlSetup: _root.hideControlSetup
                catalogSequence: _root.catalogSequence
            }
        }

        JGListView {
            id: _listView
            visible: !_root.inlineMode
            Layout.fillHeight: true
            Layout.fillWidth: true
            scrollbarAlwaysVisible: true
            enabled: !editorLocked
            model: _root.inlineMode ? null : _root.inputItemModel
            delegate: _entryDelegate
        }

        Component {
            id: _entryDelegate

            Item {
                id: _delegate

                height: _binding.height
                width: _binding.width

                required property int index
                required property var modelData
                property ListView view: ListView.view

                InputItemBinding {
                    id: _binding

                    implicitWidth: view.width
                    enabled: !editorLocked

                    inputBinding: modelData
                    inputItemModel: _root.inputItemModel
                    hideControlSetup: _root.hideControlSetup
                }
            }
        }
    }
}
