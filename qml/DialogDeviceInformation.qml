// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

ApplicationWindow {
    id: _info

    // Opens at the size it was left at (capped to the screen).
    ToolWindowMemory {
        host: _info
        name: "deviceInformation"
        defaultWidth: _info.minimumWidth
        defaultHeight: _info.minimumHeight
    }
    font.pixelSize: Style.fontSize
    minimumWidth: Style.fitWidth(Style.dp(1000), Screen)

    // The card it was opened from: its row is marked.
    property string initialGuid: ""
    // Device ids compare without braces or case ({ABC} == abc).
    function _sameGuid(a, b) {
        function clean(v) { return String(v || "").replace(/[{}]/g, "").toLowerCase() }
        return clean(a).length > 0 && clean(a) === clean(b)
    }

    minimumHeight: Style.fitHeight(Style.dp(300), Screen)

    color: Style.background
    U.Universal.theme: Style.theme

    title: "Device Information"

    ColumnLayout {
        anchors.fill: parent

        RowLayout {
            Layout.preferredHeight: Style.dp(50)

            HeaderText {
                text: "Name"
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(220)
            }
            HeaderText {
                text: "Axes"
                Layout.preferredWidth: Style.dp(50)
            }
            HeaderText {
                text: "Buttons"
                Layout.preferredWidth: Style.dp(75)
            }
            HeaderText {
                text: "Hats"
                Layout.preferredWidth: Style.dp(50)
            }
            HeaderText {
                text: "VID"
                Layout.preferredWidth: Style.dp(100)
            }
            HeaderText {
                text: "PID"
                Layout.preferredWidth: Style.dp(100)
            }
            HeaderText {
                text: "Joystick ID"
                Layout.preferredWidth: Style.dp(100)
            }
            HeaderText {
                text: "Device GUID"
                Layout.preferredWidth: Style.dp(320)
            }
        }

        ScrollView {
            id: _view

            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                spacing: 0

                Repeater {
                    model: DeviceListModel {}

                    delegate: Rectangle {
                        id: _outer

                        height: Style.dp(40)
                        width: _view.width

                        color: _info._sameGuid(guid, _info.initialGuid) ? Style.bgSelected
                             : (index % 2 === 0 ? Style.backgroundShade : Style.background)

                        RowLayout {
                            width: parent.width

                            TextEntry {
                                text: name
                                Layout.fillWidth: true
                                Layout.minimumWidth: Style.dp(220)
                                Layout.leftMargin: Style.dp(10)
                                horizontalAlignment: Text.AlignLeft

                                ToolTip {
                                    text: parent.text
                                    width: contentWidth > Style.dp(500) ? Style.dp(500) : contentWidth + Style.dp(20)
                                    visible: _hoverHandler.hovered
                                    delay: 500
                                    x: _hoverHandler.point.position.x - width / 2
                                    y: _hoverHandler.point.position.y - height - Style.dp(8)
                                }

                                HoverHandler {
                                    id: _hoverHandler
                                    acceptedDevices: PointerDevice.Mouse |
                                        PointerDevice.TouchPad
                                }

                            }
                            TextEntry {
                                text: axes
                                Layout.preferredWidth: Style.dp(50)
                            }
                            TextEntry {
                                text: buttons
                                Layout.preferredWidth: Style.dp(75)
                            }
                            TextEntry {
                                text: hats
                                Layout.preferredWidth: Style.dp(50)
                            }
                            TextEntry {
                                text: vid
                                Layout.preferredWidth: Style.dp(100)
                            }
                            TextEntry {
                                text: pid
                                Layout.preferredWidth: Style.dp(100)
                            }
                            TextEntry {
                                text: joy_id
                                Layout.preferredWidth: Style.dp(100)
                            }
                            JGTextField {
                                Layout.preferredWidth: Style.dp(320)
                                Layout.rightMargin: Style.dp(10)

                                text: guid

                                horizontalAlignment: Text.AlignHCenter
                                readOnly: true
                            }
                        }
                    }
                }
            }
        }
    }

    component TextEntry : JGText {
        Layout.preferredHeight: Style.dp(40)

        color: Style.foreground
        elide: Text.ElideRight

        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
        rightPadding: Style.dp(10)
    }

    component HeaderText : JGText {
        Layout.preferredHeight: Style.dp(40)

        color: Style.foreground
        font.weight: 600

        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
