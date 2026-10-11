// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.ActionPlugins
import Gremlin.Base as Base
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

        // Xbox and Target; Target goes onto the next line in a narrow pane.
        Flow {
            Layout.fillWidth: true
            spacing: Style.dp(8)

            RowLayout {
                spacing: Style.dp(8)

                Label { text: "Xbox" }
                // Xbox output modules (one pad for now).
                ComboBox {
                    id: _pad
                    // As wide as its widest pad name (or the shown "⚠ <pad>"),
                    // never squeezed below it.
                    implicitContentWidthPolicy: ComboBox.WidestText
                    Layout.minimumWidth: Math.max(implicitWidth, cantSend
                        ? contentItem.contentWidth + contentItem.leftPadding
                          + contentItem.rightPadding + leftPadding + rightPadding : 0)
                    textRole: "label"
                    valueRole: "value"
                    model: _root.action.padChoices
                    onModelChanged: Qt.callLater(() => {
                        currentIndex = Math.max(0, indexOfValue(_root.action.xboxDeviceId))
                    })
                    // A pad that can't be sent to: "⚠ <pad>" in red with
                    // why as the tooltip (D-05-CANT-SEND-ALL).
                    readonly property bool cantSend: _root.action.cantSendText !== ""
                    displayText: cantSend ? "⚠ " + _root.action.padLabel : currentText
                    Component.onCompleted: {
                        currentIndex = Math.max(0, indexOfValue(_root.action.xboxDeviceId))
                        if (contentItem && contentItem.color !== undefined) {
                            const box = _pad
                            contentItem.color = Qt.binding(() =>
                                box.cantSend ? Style.danger
                                : !box.enabled ? box.U.Universal.chromeDisabledLowColor
                                : box.U.Universal.foreground)
                        }
                    }
                    onActivated: _root.action.xboxDeviceId = currentValue

                    HoverHandler { id: _padHover }
                    Base.WrappingTooltip {
                        text: _root.action.cantSendText
                        visible: _pad.cantSend && _padHover.hovered
                    }
                }
            }

            RowLayout {
                spacing: Style.dp(8)

                Label { text: "Target" }
                ComboBox {
                    id: _target
                    // As wide as its widest control name.
                    implicitContentWidthPolicy: ComboBox.WidestText
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
            }
        }

        // The target's options on their own line, so the row fits a narrow pane.
        RowLayout {
            visible: _root.action.xboxTargetKind === "trigger" || _root.action.xboxTargetKind === "button"
            spacing: Style.dp(8)

            ComboBox {
                visible: _root.action.xboxTargetKind === "trigger"
                implicitContentWidthPolicy: ComboBox.WidestText
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
