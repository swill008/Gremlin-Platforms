// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Qt.labs.qmlmodels

import Gremlin.Base
import Gremlin.Profile
import Gremlin.Script
import Gremlin.Style
import Gremlin.UI


// A script's variables (04 S85), one row each in the Options look: the
// name, its description under it and its control on the right; a red bar
// marks a value that isn't valid. Sits in a card (ScriptManager.qml); the
// page around it scrolls.
ColumnLayout {
    id: _root

    property alias model: _repeater.model

    spacing: 0

    Repeater {
        id: _repeater

        model: []
        delegate: _variableRenderer
    }

    DelegateChooser {
        id: _variableRenderer
        role: "type"

        DelegateChoice {
            roleValue: "bool"

            VariableRow {
                Switch {
                    Layout.alignment: Qt.AlignRight

                    checked: modelData.value
                    text: checked ? "On" : "Off"

                    onToggled: () => modelData.value = checked
                }
            }
        }

        DelegateChoice {
            roleValue: "float"

            VariableRow {
                FloatSpinBox {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    minValue: modelData.minValue
                    maxValue: modelData.maxValue
                    value: modelData.value

                    onValueModified: (newValue) => {
                        modelData.value = newValue
                    }
                }
            }
        }

        DelegateChoice {
            roleValue: "int"

            VariableRow {
                JGSpinBox {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    from: modelData.minValue
                    to: modelData.maxValue
                    value: modelData.value

                    onValueModified: function () {
                        modelData.value = value
                    }
                }
            }
        }

        DelegateChoice {
            roleValue: "keyboard"

            VariableRow {
                InputListener {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    text: modelData.label
                    callback: (inputs) => { modelData.updateKeyboard(inputs) }
                    multipleInputs: false
                    eventTypes: ["key"]
                }
            }
        }

        DelegateChoice {
            roleValue: "logical-device"

            VariableRow {
                LogicalDeviceSelector {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    validTypes: modelData.validTypes
                    logicalInputIdentifier: modelData.logicalInputIdentifier

                    onLogicalInputIdentifierChanged: () => {
                        modelData.logicalInputIdentifier = logicalInputIdentifier
                    }
                }
            }
        }

        DelegateChoice {
            roleValue: "osc-input"

            VariableRow {
                TooltipComboBox {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    model: modelData.options
                    currentIndex: modelData.currentIndex
                    displayText: currentIndex < 0 ? qsTr("Choose an OSC input")
                                                  : currentText

                    onActivated: (index) => { modelData.select(index) }
                }
            }
        }

        DelegateChoice {
            roleValue: "mode"

            VariableRow {
                id: _modeRow

                // Belongs to the delegate root, never the view.
                readonly property ModeListModel _modes:
                    ModelFactory.create("ModeListModel", _modeRow, {})

                TooltipComboBox {
                    id: _mode

                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    model: _modeRow._modes
                    textRole: "name"
                    valueRole: "name"

                    onActivated: () => { modelData.value = currentText }

                    Component.onCompleted: () => {
                        currentIndex = find(modelData.value)
                    }
                }
            }
        }

        DelegateChoice {
            roleValue: "selection"

            VariableRow {
                TooltipComboBox {
                    id: _selection

                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    model: modelData.options

                    onActivated: () => { modelData.value = currentText }

                    Component.onCompleted: () => {
                        currentIndex = find(modelData.value)
                    }

                    ToolTip {
                        text: parent.currentText
                        visible: _hoverHandler.hovered
                        x: _hoverHandler.point.position.x - width / 2
                        y: _hoverHandler.point.position.y - height - Style.dp(8)
                    }

                    HoverHandler {
                        id: _hoverHandler
                        acceptedDevices: PointerDevice.Mouse |
                            PointerDevice.TouchPad
                    }
                }
            }
        }

        DelegateChoice {
            roleValue: "string"

            VariableRow {
                JGTextField {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    text: modelData.value

                    onTextEdited: () => { modelData.value = text }
                }
            }
        }

        DelegateChoice {
            roleValue: "physical-input"

            VariableRow {
                InputListener {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignRight

                    text: modelData.label
                    callback: (inputs) => { modelData.updateJoystick(inputs) }
                    multipleInputs: false
                    eventTypes: modelData.validTypes
                }
            }
        }

        DelegateChoice {
            roleValue: "vjoy"

            VariableRow {
                VJoySelector {
                    Layout.fillWidth: true
                    // Never squeezed (to-do 98): the name gives way instead.
                    Layout.minimumWidth: implicitWidth
                    Layout.alignment: Qt.AlignRight

                    validTypes: modelData.validTypes

                    onSelectionChanged: (vjoyId, inputType, inputId) => {
                        modelData.vjoyId = vjoyId
                        modelData.inputType = inputType
                        modelData.inputId = inputId
                    }

                    Component.onCompleted: () => {
                        initialize(
                            modelData.vjoyId,
                            modelData.inputType,
                            modelData.inputId
                        )
                    }
                }
            }
        }

    }

    // One variable: modelData's name ("(req)" when it must be set) and
    // description, the control (the row's children) on the right. The name
    // gives way so the control keeps its width (to-do 98).
    component VariableRow : Item {
        id: _row

        default property alias control: _control.data

        Layout.fillWidth: true
        implicitHeight: _layout.implicitHeight + Style.dp(20)

        Rectangle {
            visible: index > 0
            width: parent.width
            height: Style.dp(1)
            color: Style.line
        }

        // Not valid yet: a red bar on the left edge.
        Rectangle {
            objectName: "scriptVariableInvalid"
            visible: !modelData.isValid
            x: Style.dp(1)
            y: Style.dp(8)
            width: Style.dp(4)
            height: parent.height - Style.dp(16)
            radius: Style.dp(2)
            color: Style.error
        }

        GridLayout {
            id: _layout

            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: Style.dp(14)
            anchors.rightMargin: Style.dp(14)
            columns: 2
            columnSpacing: Style.dp(16)

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(80)
                spacing: Style.dp(2)

                Label {
                    objectName: "scriptVariableName"
                    Layout.fillWidth: true
                    text: modelData.name + (modelData.isOptional ? "" : " (req)")
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(14)
                    wrapMode: Text.WordWrap
                }
                Label {
                    Layout.fillWidth: true
                    visible: text.length > 0
                    text: modelData.description || ""
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    wrapMode: Text.WordWrap
                }
            }

            ColumnLayout {
                id: _control

                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                Layout.preferredWidth: Style.dp(300)
                // A control that needs more (the vJoy picker's minimum) gets it.
                Layout.maximumWidth: Style.dp(360)
            }
        }
    }
}
