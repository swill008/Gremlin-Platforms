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

    // The control box, then its options on their own line under it
    // (EW-2), as in Map to Xbox.
    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        // The controls of the action's type, never the one it sits on
        // (06 S93).
        TooltipComboBox {
            id: _control
            objectName: "logicalControl"
            // Never narrower than the shown "⚠ <Control>".
            Layout.minimumWidth: Math.max(Style.dp(200), cantSend
                ? contentItem.contentWidth + contentItem.leftPadding
                  + contentItem.rightPadding + leftPadding + rightPadding : 0)
            Layout.fillWidth: true

            // A deleted control: "⚠ <Control>" in red with why as the
            // tooltip, in place of the box's own (D-05-CANT-SEND-ALL).
            readonly property bool cantSend: _root.action.controlPicker.cantSendText !== ""
            enableTooltips: !cantSend
            displayText: cantSend ? "⚠ " + _root.action.controlPicker.missingLabel : currentText

            model: _root.action.controlPicker.choices
            currentIndex: _root.action.controlPicker.index

            onActivated: (index) => {
                _root.action.controlPicker.pick(index)
            }

            Component.onCompleted: {
                if (contentItem && contentItem.color !== undefined) {
                    const box = _control
                    contentItem.color = Qt.binding(() =>
                        box.cantSend ? Style.danger
                        : !box.enabled ? box.U.Universal.chromeDisabledLowColor
                        : box.U.Universal.foreground)
                }
            }

            HoverHandler { id: _controlHover }
            WrappingTooltip {
                text: _root.action.controlPicker.cantSendText
                visible: _control.cantSend && _controlHover.hovered
            }
        }

        // UI for a physical axis behaving as an axis
        Loader {
            active: _root.action.logicalInputType === "axis"
            Layout.fillWidth: true

            // Wraps when narrow; Speed stays with its box.
            sourceComponent: Flow {
                spacing: Style.dp(8)

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

                Row {
                    spacing: Style.dp(8)
                    visible: _relativeMode.checked

                    Label {
                        text: "Speed"
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    FloatSpinBox {
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
