// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.ActionPlugins
import Gremlin.Profile
import Gremlin.Style
import Gremlin.Util
import "../../qml"
import "../../qml/helpers.js" as Helpers

Item {
    id: _root

    property ConditionModel action
    readonly property int conditionLabelWidth: Style.dp(150)

    implicitHeight: _content.height

    // Turns the list of entries into an unordered HTML element.
    function toUnorderedList(entries) {
        return entries.join("<br>")
    }

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        // +-------------------------------------------------------------------
        // | Logical condition setup
        // +-------------------------------------------------------------------
        RowLayout {
            id: _logicalOperator

            Layout.fillWidth: true

            Label {
                text: "When "
            }
            ComboBox {
                id: _logicalOperatorSelector
                model: _root.action.logicalOperators

                textRole: "text"
                valueRole: "value"

                Component.onCompleted: () => {
                    currentIndex = indexOfValue(_root.action.logicalOperator)
                }

                onActivated: () => {
                    _root.action.logicalOperator = currentValue
                }
            }
            Label {
                text: "of the following conditions are met"
            }

            LayoutHorizontalSpacer {}

            Button {
                text: "Add Condition"

                onClicked: () => {
                    _root.action.addCondition(_condition.currentValue)
                }
            }

            ComboBox {
                id: _condition

                implicitContentWidthPolicy: ComboBox.WidestText
                textRole: "text"
                valueRole: "value"

                model: _root.action.conditionOperators
            }
        }

        Repeater {
            model: _root.action.conditions

            delegate: _conditionDelegate
        }

        // +-------------------------------------------------------------------
        // | True actions
        // +-------------------------------------------------------------------
        RowLayout {
            id: _trueHeader

            Label {
                text: "When the condition is <b>TRUE</b> then"
            }

            LayoutHorizontalSpacer {}

            ActionSelector {
                actionNode: _root.action
                callback: (x) => { _root.action.appendAction(x, "true"); }
            }
        }

        HorizontalDivider {
            id: _trueDivider

            Layout.fillWidth: true

            dividerColor: Style.lowColor
            lineWidth: Style.dp(2)
            spacing: Style.dp(2)
        }

        Repeater {
            model: _root.action.getActions("true")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "true"

                Layout.fillWidth: true
            }
        }

        // +-------------------------------------------------------------------
        // | False actions
        // +-------------------------------------------------------------------
        RowLayout {
            id: _falseHeader

            Label {
                text: "When the condition is <b>FALSE</b> then"
            }

            LayoutHorizontalSpacer {}

            ActionSelector {
                actionNode: _root.action
                callback: (x) => { _root.action.appendAction(x, "false"); }
            }
        }

        HorizontalDivider {
            id: _falseDivider

            Layout.fillWidth: true

            dividerColor: Style.lowColor
            lineWidth: Style.dp(2)
            spacing: Style.dp(2)
        }

        Repeater {
            model: _root.action.getActions("false")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "false"

                Layout.fillWidth: true
            }
        }
    }

    DelegateChooser {
        id: _conditionDelegate

        role: "conditionType"

        DelegateChoice {
            roleValue: "current_input"

            ConditionComponent {
                typeIcon: bsi.icons.icon_current_input
                conditionName: "Current Input"

                conditionItem: RowLayout {
                    Comparator {
                        comparator: modelData.comparator
                    }

                    LayoutHorizontalSpacer {}
                }
            }
        }

        DelegateChoice {
            roleValue: "joystick"

            ConditionComponent {
                typeIconSource: "qrc:/icons/physical_joystick"
                conditionName: "Joystick"

                conditionItem: RowLayout {
                    InputListener {
                        text: Helpers.safeText(toUnorderedList(modelData.states))

                        callback: (inputs) => {
                            modelData.updateFromUserInput(inputs)
                        }
                        multipleInputs: true
                        eventTypes: ["axis", "button", "hat"]
                    }

                    Comparator {
                        comparator: modelData.comparator
                    }

                    LayoutHorizontalSpacer {}

                }
            }
        }

        DelegateChoice {
            roleValue: "keyboard"

            ConditionComponent {
                typeIcon: bsi.icons.icon_keyboard
                conditionName: "Keyboard"

                conditionItem: RowLayout {
                    InputListener {
                        text: Helpers.safeText(
                            modelData.key, toUnorderedList(modelData.states)
                        )

                        callback: (inputs) => {
                            modelData.updateFromUserInput(inputs)
                        }
                        multipleInputs: true
                        eventTypes: ["key"]
                    }

                    Comparator {
                        comparator: modelData.comparator
                    }

                    LayoutHorizontalSpacer {}
                }
            }
        }

        DelegateChoice {
            roleValue: "logical_device"

            ConditionComponent {
                typeIcon: bsi.icons.icon_logical_device
                conditionName: "Logical Device"

                conditionItem: RowLayout {
                    LogicalDeviceSelector {
                        // The ordering is important, swapping it will result in the
                        // wrong item being displayed.
                        validTypes: ["axis", "button", "hat"]
                        logicalInputIdentifier: modelData.logicalInputIdentifier
                        useCompact: true

                        onLogicalInputIdentifierChanged: () => {
                            modelData.logicalInputIdentifier = logicalInputIdentifier
                        }
                    }

                    Label { text: "<b>True</b> when" }

                    Comparator {
                        comparator: modelData.comparator
                    }

                    LayoutHorizontalSpacer {}
                }
            }
        }

        DelegateChoice {
            roleValue: "vjoy"

            ConditionComponent {
                typeIcon: bsi.icons.icon_joystick
                conditionName: "vJoy"

                conditionItem: RowLayout {
                    VJoySelector {
                        validTypes: ["axis", "button", "hat"]
                        useCompact: true

                        onSelectionChanged: (vjoyId, inputType, inputId) => {
                            modelData.vjoyDeviceId = vjoyId
                            modelData.vjoyInputType = inputType
                            modelData.vjoyInputId = inputId
                        }

                        Component.onCompleted: () => {
                            initialize(
                                modelData.vjoyDeviceId,
                                modelData.vjoyInputType,
                                modelData.vjoyInputId
                            )
                        }
                    }

                    Label { text: "<b>True</b> when" }

                    Comparator {
                        comparator: modelData.comparator
                    }

                    LayoutHorizontalSpacer {}
                }
            }
        }
    }

    // Drop action for insertion into empty/first slot of the true actions
    ActionDragDropArea {
        target: _trueDivider
        dropCallback: (drop) => {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "true");
        }
    }

    // Drop action for insertion into empty/first slot of the false actions
    ActionDragDropArea {
        target: _falseDivider
        dropCallback: (drop) => {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "false");
        }
    }

    component DeleteConditionButton : IconButton {
        text: bsi.icons.remove
        font.pixelSize: Style.dp(16)

        onClicked: () => _root.action.removeCondition(index)
    }

    component ConditionComponent : RowLayout {
        property alias conditionItem: _actionLoader.sourceComponent
        property string typeIcon: ""
        property string typeIconSource: ""
        property string conditionName: ""

        Item {
            implicitWidth: _iconRow.implicitWidth
            implicitHeight: _iconRow.implicitHeight

            Row {
                id: _iconRow

                Label {
                    visible: typeIcon !== ""
                    text: typeIcon
                    font.family: "bootstrap-icons"
                    font.pixelSize: Style.dp(16)
                }
                Image {
                    width: Style.dp(16)
                    height: Style.dp(16)

                    visible: typeIconSource !== ""
                    source: typeIconSource
                    fillMode: Image.PreserveAspectFit
                }
            }

            HoverHandler {
                id: _iconHover
            }

            ToolTip {
                visible: _iconHover.hovered && conditionName !== ""
                text: conditionName
                delay: 500
            }
        }

        // Contains the specific condition component.
        Loader {
            id: _actionLoader

            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(10)
        }

        LayoutHorizontalSpacer {}

        Label {
            visible: modelData.isValid != true

            font.family: "bootstrap-icons"
            font.pixelSize: Style.dp(24)

            text: bsi.icons.error
            color: Style.error
        }

        DeleteConditionButton {}
    }
}
