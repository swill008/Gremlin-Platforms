// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Profile
import "../../qml"
import Gremlin.Style


Item {
    id: _root

    property MapToVjoyModel action

    implicitHeight: _content.height


    // The picker, then its options on their own lines (EW-2): the axis
    // choices wrap when the pane is narrow, "Invert activation" sits under
    // the picker as in Map to Xbox.
    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        VJoySelector {
            Layout.fillWidth: true
            Layout.minimumWidth: Style.dp(160)
            validTypes: [_root.action.actionBehavior]

            // Propagate internal changes to the external interface.
            onSelectionChanged: (vjoyId, inputType, inputId) => {
                _root.action.vjoyDeviceId = vjoyId
                _root.action.vjoyInputType = inputType
                _root.action.vjoyInputId = inputId

            }

            Component.onCompleted: {
                initialize(
                    _root.action.vjoyDeviceId,
                    _root.action.actionBehavior,
                    _root.action.vjoyInputId
                )
            }
        }

        // UI for a physical axis behaving as an axis
        Loader {
            active: _root.action.vjoyInputType == "axis"
            visible: active
            Layout.fillWidth: true

            sourceComponent: Flow {
                spacing: Style.dp(8)

                RadioButton {
                    autoExclusive: false
                    checkable: false
                    text: "Absolute"
                    checked: _root.action.axisMode == "absolute"

                    onClicked: {
                        _root.action.axisMode = "absolute"
                    }
                }
                RadioButton {
                    id: _relativeMode
                    autoExclusive: false
                    checkable: false
                    text: "Relative"
                    checked: _root.action.axisMode == "relative"

                    onClicked: {
                        _root.action.axisMode = "relative"
                    }
                }

                // "Speed" wraps with its box, never apart from it.
                Row {
                    visible: _relativeMode.checked
                    spacing: Style.dp(8)

                    Label {
                        text: "Speed"
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    FloatSpinBox {
                        minValue: 0
                        maxValue: 100
                        stepSize: 0.1
                        value: _root.action.axisScaling

                        onValueModified: (newValue) => {
                            _root.action.axisScaling = newValue
                        }
                    }
                }
            }
        }
        // UI for a button input
        Loader {
            active: _root.action.vjoyInputType == "button"
            visible: active

            sourceComponent: Switch {
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
