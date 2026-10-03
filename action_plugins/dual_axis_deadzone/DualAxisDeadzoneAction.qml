// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Profile
import Gremlin.UI
import "../../qml"
import Gremlin.Style

Item {
    id: _root

    property DualAxisDeadzoneModel action
    property LabelValueSelectionModel deadzoneListModel: action.deadzoneActionList

    implicitHeight: _content.height

    Connections {
        target: action

        function onModelChanged() {
            deadzoneListModel.currentValue = _root.action.deadzone
        }
    }


    // Dialog to change the label of the current action
    Dialog {
        id: _dialog

        anchors.centerIn: Overlay.overlay

        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        focus: true

        title: "Rename Action"

        Row {
            anchors.fill: parent

            JGTextField {
                id: _actionLabel

                width: Style.dp(400)
                focus: true

                text: action.label
                placeholderText: "Action label"

                onAccepted: () => { _dialog.accept() }
            }
        }

        onAccepted: () => { action.label = _actionLabel.text }
    }

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        // +-------------------------------------------------------------------
        // | Deadzone instance selection and management
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                Layout.preferredWidth: Style.dp(150)

                text: "Deadzone instance"
            }

            LabelValueComboBox {
                model: _root.deadzoneListModel

                Component.onCompleted: () => {
                    _root.deadzoneListModel.currentValue = _root.action.deadzone
                }

                onSelectionChanged: () => {
                    _root.action.deadzone = _root.deadzoneListModel.currentValue
                }
            }

            IconButton {
                text: bsi.icons.add_new
                font.pixelSize: Style.dp(24)

                onClicked: () => { _root.action.newDeadzone() }
            }

            IconButton {
                text: bsi.icons.rename
                font.pixelSize: Style.dp(24)

                onClicked: () => { _dialog.open() }
            }
        }

        // Deadzone configuration
        RowLayout {
            Label {
                Layout.preferredWidth: Style.dp(150)

                text: "Deadzone limits"
            }

            Label {
                text: "Inner"
            }

            FloatSpinBox {
                id: _innerValue

                minValue: 0.0
                maxValue: 1.0
                decimals: Style.decimalsPrecise
                value: _root.action.innerDeadzone

                onValueModified: (newValue) => {
                    _root.action.innerDeadzone = newValue
                }
            }

            Label {
                Layout.leftMargin: Style.dp(20)

                text: "Outer"
            }

            FloatSpinBox {
                id: _outerValue

                minValue: 0.0
                maxValue: 1.0
                decimals: Style.decimalsPrecise
                value: _root.action.outerDeadzone

                onValueModified: (newValue) => {
                    _root.action.outerDeadzone = newValue

                }
            }
        }

        // +-------------------------------------------------------------------
        // | Axis assignments
        // +-------------------------------------------------------------------
        RowLayout {
            // First axis selection
            Label {
                text: "First axis: "
                font.family: "Segoe UI"
                font.weight: 600
            }
            Label {
                text: _root.action.axis1.label
            }
            IconButton {
                text: bsi.icons.replace

                onClicked: () => { _root.action.axis1 = uiState.currentInput }
            }

            LayoutHorizontalSpacer {
                Layout.fillWidth: false
                Layout.preferredWidth: Style.dp(50)
            }

            // Second axis selection
            Label {
                text: "Second axis: "
                font.family: "Segoe UI"
                font.weight: 600
            }
            Label {
                text: _root.action.axis2.label
            }
            IconButton {
                text: bsi.icons.replace

                onClicked: () => { _root.action.axis2 = uiState.currentInput }
            }
        }

        // +-------------------------------------------------------------------
        // | First axis actions
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                text: "First axis"
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback: (x) => { _root.action.appendAction(x, "first") }
            }
        }

        Rectangle {
            id: _firstDivider
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        Repeater {
            model: _root.action.getActions("first")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "first"

                Layout.fillWidth: true
            }
        }

        // +-------------------------------------------------------------------
        // | Second axis actions
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                text: "Second axis"
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback: (x) => { _root.action.appendAction(x, "second") }
            }
        }

        Rectangle {
            id: _secondDivider
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        Repeater {
            model: _root.action.getActions("second")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "second"

                Layout.fillWidth: true
            }
        }
    }

    // Drop action for insertion into empty/first slot of the short actions
    ActionDragDropArea {
        target: _firstDivider
        dropCallback: (drop) => {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "first");
        }
    }

    // Drop action for insertion into empty/first slot of the long actions
    ActionDragDropArea {
        target: _secondDivider
        dropCallback: (drop) => {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "second");
        }
    }
}
