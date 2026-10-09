// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

// OSC Module Setup's "Discovery" tab (D-09-OSC-DISCOVERY, D-09-OSC-TABS):
// Announce this PC, Find OSC devices and the found list with "Add as Target".
Flickable {
    id: _root
    objectName: "oscDiscoveryTab"

    required property OscServerModel server

    clip: true
    contentWidth: width
    contentHeight: _column.implicitHeight + Style.dp(24)
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {
        policy: _root.contentHeight > _root.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
    }

    ColumnLayout {
        id: _column
        x: Style.dp(14)
        y: Style.dp(12)
        width: _root.width - Style.dp(28)
        spacing: Style.dp(10)

        SectionHeading {
            text: "Discovery"
            Layout.fillWidth: true
        }

        Label {
            objectName: "oscDiscoveryUnavailable"
            visible: !_root.server.discoveryAvailable
            text: "Discovery is not available on this PC."
            color: Style.fgMuted
        }

        CheckBox {
            objectName: "oscAnnounce"
            enabled: _root.server.discoveryAvailable
            text: "Announce this PC"
            checked: _root.server.announce
            onClicked: _root.server.setValue("announce", checked)
            PointerTip {
                text: "Lets OSC apps on your network find this PC and its port."
                show: parent.hovered
            }
        }

        CheckBox {
            objectName: "oscFindDevices"
            enabled: _root.server.discoveryAvailable
            text: "Find OSC devices"
            checked: _root.server.findDevices
            onClicked: _root.server.setValue("find_devices", checked)
            PointerTip {
                text: "Lists OSC apps on your network that announce themselves."
                show: parent.hovered
            }
        }

        // The found devices, in a well.
        Rectangle {
            visible: _root.server.findDevices
            Layout.fillWidth: true
            implicitHeight: _found.implicitHeight + Style.dp(12)
            color: Style.bgWell
            border.color: Style.line
            radius: Style.dp(4)

            ColumnLayout {
                id: _found
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    margins: Style.dp(6)
                }
                spacing: Style.dp(4)

                Label {
                    objectName: "oscFoundEmpty"
                    visible: _root.server.foundDevices.length === 0
                    text: "No OSC devices found yet."
                    color: Style.fgMuted
                    Layout.margins: Style.dp(4)
                }

                Repeater {
                    model: _root.server.findDevices ? _root.server.foundDevices : []
                    delegate: RowLayout {
                        id: _device
                        required property var modelData
                        required property int index
                        objectName: "oscFound" + index
                        spacing: Style.dp(6)
                        Layout.fillWidth: true
                        Label {
                            objectName: "oscFoundName" + _device.index
                            text: _device.modelData.name
                            color: Style.fg
                            Layout.preferredWidth: Style.dp(180)
                            elide: Text.ElideRight
                        }
                        Label {
                            text: _device.modelData.host + ":" + _device.modelData.port
                            font.family: Style.monoFont
                            color: Style.fgMuted
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                        }
                        Button {
                            objectName: "oscFoundAdd" + _device.index
                            text: "Add as Target"
                            implicitHeight: Style.dp(28)
                            onClicked: _root.server.addFoundTarget(_device.modelData.name,
                                                                   _device.modelData.host,
                                                                   _device.modelData.port)
                        }
                    }
                }
            }
        }
    }
}
