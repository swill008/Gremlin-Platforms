// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Profile
import Gremlin.Style
import Gremlin.Menus as Menus
import Gremlin.Tools

ApplicationWindow {
    font.pixelSize: Style.fontSize
    width: Style.dp(800)
    height: _content.implicitHeight + Style.dp(30)

    color: Style.background
    U.Universal.theme: Style.theme

    title: "Swap Devices"

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }

    DeviceListModel {
        id: _physicalDevices

        deviceType: "physical"
    }

    ProfileDeviceListModel {
        id: _profileDevices
    }

    Tools {
        id: _tools
    }


    ColumnLayout {
        id: _content

        anchors.fill: parent
        anchors.margins: Style.dp(10)

        RowLayout {
            Label {
                Layout.preferredWidth: Style.dp(200)

                text: "From profile device"
                font.bold: true
            }

            ComboBox {
                id: _profileDeviceSelection

                Layout.fillWidth: true

                model: _profileDevices

                textRole: "nameAndActions"
                valueRole: "uuid"
            }
        }

        RowLayout {
            Label {
                Layout.preferredWidth: Style.dp(200)

                text: "To connected device"
                font.bold: true
            }

            ComboBox {
                id: _physicalDeviceSelection

                Layout.fillWidth: true

                model: _physicalDevices

                textRole: "name"
                valueRole: "guid"

                displayText: currentText + " : " + currentValue
                delegate: Menus.DropdownRow {
                    combo: _physicalDeviceSelection
                    labelFor: (i) => _physicalDeviceSelection.textAt(i) + " : " + _physicalDeviceSelection.valueAt(i)
                }
            }
        }

        RowLayout {
            Layout.topMargin: Style.dp(10)

            Button {
                text: "Swap Bindings"
                onClicked: () => {
                    _statusMessage.text = _tools.swapDevices(
                        _profileDeviceSelection.currentValue,
                        _physicalDeviceSelection.currentValue
                    )
                }
            }

            Label {
                id: _statusMessage

                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(10)

                text: "Select devices, then click the button."
            }
        }
    }
}
