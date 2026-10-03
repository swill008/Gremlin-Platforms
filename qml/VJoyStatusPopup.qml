// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

Popup {
    id: _root

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Style.dp(16)
    width: Style.dp(420)

    property var status: _status

    VJoyStatus {
        id: _status

        Component.onCompleted: refresh()
    }

    background: Rectangle {
        color: Style.background
        border.color: Style.accent
        border.width: Style.dp(1)
        radius: Style.dp(4)
    }

    onOpened: {
        if (_root.status) {
            _root.status.refresh()
        }
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(12)
        width: parent ? parent.width : Style.dp(420)

        Label {
            text: "Device tabs"
            font.bold: true
            font.pixelSize: Style.dp(16)
        }

        Label {
            text: "Check a device to show its tab."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            opacity: 0.75
            font.pixelSize: Style.dp(12)
        }

        Repeater {
            model: [
                {"key": "keyboard", "label": "Keyboard"},
                {"key": "logical", "label": "Logical Device"},
                {"key": "osc", "label": "OSC"},
                {"key": "xbox", "label": "Xbox 360 Controller"}
            ]

            CheckBox {
                required property var modelData
                text: modelData.label
                checked: _root.status && _root.status.pinStamp >= 0 && _root.status.isExtraPinned(modelData.key)
                onToggled: {
                    if (_root.status) {
                        _root.status.setExtraPinned(modelData.key, checked)
                    }
                }
            }
        }

        Label {
            text: "vJoy  ·  " + (_root.status ? _root.status.activeCount : 0) + " of 16 installed and activated"
            font.bold: true
        }

        GridLayout {
            columns: 4
            columnSpacing: Style.dp(12)
            rowSpacing: Style.dp(10)
            Layout.fillWidth: true

            Repeater {
                model: 16

                RowLayout {
                    required property int index
                    readonly property int deviceId: index + 1
                    readonly property bool active: _root.status && _root.status.activeCount >= 0 && _root.status.isActive(deviceId)
                    readonly property bool pinned: _root.status && _root.status.pinStamp >= 0 && _root.status.isPinned(deviceId)
                    Layout.fillWidth: true
                    spacing: Style.dp(4)

                    CheckBox {
                        checked: parent.pinned
                        enabled: parent.active
                        onToggled: {
                            if (_root.status) {
                                _root.status.setPinned(parent.deviceId, checked)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: Style.dp(32)
                        radius: Style.dp(4)
                        color: parent.active ? Style.accent : Style.background
                        border.color: parent.active ? Style.accent : Style.lowColor
                        border.width: Style.dp(1)

                        Label {
                            anchors.centerIn: parent
                            text: deviceId
                            font.bold: true
                            font.pixelSize: Style.dp(14)
                            color: parent.parent.active ? Style.background : Style.foreground
                            opacity: parent.parent.active ? 1.0 : 0.45
                        }
                    }
                }
            }
        }
    }
}
