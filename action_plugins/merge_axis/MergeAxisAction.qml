// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Profile
import Gremlin.UI
import Gremlin.ActionPlugins
import "../../qml"
import Gremlin.Compact as Compact
import Gremlin.Style

Item {
    id: _root

    property MergeAxisModel action

    property LabelValueSelectionModel actionModel: action.mergeActionList
    property LabelValueSelectionModel operationModel: action.operationList

    implicitHeight: _content.height

    Connections {
        target: action

        function onModelChanged() {
            actionModel.currentValue = _root.action.mergeAction
            operationModel.currentValue = _root.action.operation
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
                id: _action_label

                width: Style.dp(400)
                focus: true

                text: action.label
                placeholderText: "Action label"

                onAccepted: () => { _dialog.accept() }
            }
        }

        onAccepted: () => { action.label = _action_label.text }
    }

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right


        // +-------------------------------------------------------------------
        // | Instance, operation and the two axes: labels in the first column.
        // | Too narrow for a label and a list side by side (the pane at its
        // | default width, a large UI scale), each list goes under its label.
        // +-------------------------------------------------------------------
        GridLayout {
            id: _grid

            // The lists keep at least 250 (LabelValueComboBox).
            readonly property bool wide: _content.width >= Math.max(
                _instanceLabel.implicitWidth, _operationLabel.implicitWidth,
                _firstLabel.implicitWidth, _secondLabel.implicitWidth)
                + Style.dp(250) + _instanceButtons.implicitWidth
                + 2 * columnSpacing

            Layout.fillWidth: true
            columns: 3
            columnSpacing: Style.dp(8)

            Label {
                id: _instanceLabel
                text: "Merge axis instance"
                Layout.row: 0
                Layout.column: 0
                Layout.columnSpan: _grid.wide ? 1 : 2
            }
            LabelValueComboBox {
                id: _action_selection

                Layout.row: _grid.wide ? 0 : 1
                Layout.column: _grid.wide ? 1 : 0
                Layout.columnSpan: _grid.wide ? 1 : 3
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(250)

                model: _root.actionModel

                Component.onCompleted: () => {
                    _root.actionModel.currentValue = _root.action.mergeAction
                }

                onSelectionChanged: () => {
                    _root.action.mergeAction = _root.actionModel.currentValue
                }
            }

            Row {
                id: _instanceButtons

                Layout.row: 0
                Layout.column: 2
                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter

                IconButton {
                    text: bsi.icons.add_new
                    font.pixelSize: Style.dp(24)

                    onClicked: () => { _root.action.newMergeAxis() }
                }

                IconButton {
                    text: bsi.icons.rename
                    font.pixelSize: Style.dp(24)

                    onClicked: () => { _dialog.open() }
                }
            }

            Label {
                id: _operationLabel
                text: "Merge operation"
                Layout.row: _grid.wide ? 1 : 2
                Layout.column: 0
                Layout.columnSpan: _grid.wide ? 1 : 3
            }
            LabelValueComboBox {
                id: _operation_selection

                Layout.row: _grid.wide ? 1 : 3
                Layout.column: _grid.wide ? 1 : 0
                Layout.columnSpan: _grid.wide ? 1 : 3
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(250)

                model: _root.operationModel

                Component.onCompleted: () => {
                    _root.operationModel.currentValue = _root.action.operation
                }

                onSelectionChanged: () => {
                    _root.action.operation = _root.operationModel.currentValue
                }
            }

            // +---------------------------------------------------------------
            // | Axis assignments: one line each, the name shortened to fit
            // +---------------------------------------------------------------
            Label {
                id: _firstLabel
                text: "First axis"
                font.family: Style.uiFont
                font.weight: 600
                Layout.row: _grid.wide ? 2 : 4
                Layout.column: 0
            }
            Label {
                text: _root.action.firstAxis.label
                elide: Text.ElideRight
                Layout.row: _grid.wide ? 2 : 4
                Layout.column: 1
                Layout.fillWidth: true
            }
            Compact.RecordButton {
                Layout.row: _grid.wide ? 2 : 4
                Layout.column: 2
                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                onClicked: () => { _root.action.firstAxis = uiState.currentInput }
            }

            Label {
                id: _secondLabel
                text: "Second axis"
                font.family: Style.uiFont
                font.weight: 600
                Layout.row: _grid.wide ? 3 : 5
                Layout.column: 0
            }
            Label {
                text: _root.action.secondAxis.label
                elide: Text.ElideRight
                Layout.row: _grid.wide ? 3 : 5
                Layout.column: 1
                Layout.fillWidth: true
            }
            Compact.RecordButton {
                Layout.row: _grid.wide ? 3 : 5
                Layout.column: 2
                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                onClicked: () => {
                    _root.action.secondAxis = uiState.currentInput
                }
            }
        }

        // +-------------------------------------------------------------------
        // | Child action selection
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                text: "Actions"
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback:  (x) => { _root.action.appendAction(x, "children") }
            }
        }

        Rectangle {
            id: _childActionDivider
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        // Display the actions operating on the merged axis output
        Repeater {
            model: _root.action.getActions("children")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "children"

                Layout.fillWidth: true
            }
        }
    }

    // Drop action for insertion into empty/first slot of the short actions
    ActionDragDropArea {
        target: _childActionDivider
        dropCallback: (drop) => {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "children");
        }
    }
}
