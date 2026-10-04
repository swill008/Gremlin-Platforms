// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.ActionPlugins
import "../../qml"
import Gremlin.Style

Item {
    id: _root

    property MapToXboxModel action
    implicitHeight: _content.height

    ColumnLayout {
        id: _content
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Style.dp(4)

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)

            Label { text: "Xbox" }
            // Xbox output modules (one pad for now).
            ComboBox {
                id: _pad
                Layout.minimumWidth: Style.dp(120)
                textRole: "label"
                valueRole: "value"
                model: _root.action.padChoices
                onModelChanged: Qt.callLater(() => {
                    currentIndex = Math.max(0, indexOfValue(_root.action.xboxDeviceId))
                })
                Component.onCompleted: {
                    currentIndex = Math.max(0, indexOfValue(_root.action.xboxDeviceId))
                }
                onActivated: _root.action.xboxDeviceId = currentValue
            }

            Label { text: "Target" }
            ComboBox {
                id: _target
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(60)
                textRole: "label"
                valueRole: "value"
                model: _root.action.targetChoices
                // Re-select the saved control whenever the list is rebuilt.
                onModelChanged: Qt.callLater(() => {
                    currentIndex = Math.max(0, indexOfValue(_root.action.xboxTarget))
                })
                Component.onCompleted: {
                    currentIndex = Math.max(0, indexOfValue(_root.action.xboxTarget))
                }
                onActivated: {
                    _root.action.xboxTarget = currentValue
                }
            }

            ComboBox {
                visible: _root.action.xboxTargetKind === "trigger"
                textRole: "label"
                valueRole: "value"
                model: [
                    { value: "full", label: "Full axis" },
                    { value: "upper", label: "Upper half" }
                ]
                Component.onCompleted: currentIndex = Math.max(0, indexOfValue(_root.action.triggerRange))
                onActivated: _root.action.triggerRange = currentValue
                PointerTip {
                    text: "Full axis: -1 is 0%, +1 is 100%. Upper half: center is 0%, +1 is 100%."
                    delay: 300
                    show: true
                }
            }

            Switch {
                visible: _root.action.xboxTargetKind === "button"
                text: "Invert activation"
                checked: _root.action.buttonInverted
                onToggled: _root.action.buttonInverted = checked
            }
        }
    }
}
