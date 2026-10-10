// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Profile
import Gremlin.Style
import "../../qml"


Item {
    id: _root

    property MapToLogicalDeviceModel action

    implicitHeight: _content.height

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        // The controls of the action's type, never the one it sits on
        // (06 S93).
        TooltipComboBox {
            Layout.minimumWidth: Style.dp(200)
            Layout.fillWidth: true

            model: _root.action.controlPicker.choices
            currentIndex: _root.action.controlPicker.index

            onActivated: (index) => {
                _root.action.controlPicker.pick(index)
            }
        }

        // UI for a physical axis behaving as an axis
        Loader {
            active: _root.action.logicalInputType === "axis"
            Layout.fillWidth: true

            sourceComponent: Row {
                RadioButton {
                    autoExclusive: false
                    checkable: false
                    text: "Absolute"
                    checked: _root.action.axisMode === "absolute"

                    onClicked: {
                        _root.action.axisMode = "absolute"
                    }
                }
                RadioButton {
                    id: _relativeMode
                    autoExclusive: false
                    checkable: false
                    text: "Relative"
                    checked: _root.action.axisMode === "relative"

                    onClicked: {
                        _root.action.axisMode = "relative"
                    }
                }

                Label {
                    text: "Speed"
                    anchors.verticalCenter: parent.verticalCenter
                    visible: _relativeMode.checked
                }

                FloatSpinBox {
                    visible: _relativeMode.checked
                    minValue: 0
                    maxValue: 100
                    value: _root.action.axisScaling
                    stepSize: 0.05

                    onValueModified: (newValue) => {
                        _root.action.axisScaling = newValue
                    }
                }
            }
        }
        // UI for a button input
        Loader {
            active: _root.action.logicalInputType === "button"
            Layout.fillWidth: true

            sourceComponent: Row {
                Switch {
                    text: "Invert activation"
                    checked: _root.action.buttonInverted

                    onToggled: function()
                    {
                        _root.action.buttonInverted = checked
                    }
                }
            }
        }
    }
}
