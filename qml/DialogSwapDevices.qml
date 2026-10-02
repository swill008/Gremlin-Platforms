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
    id: _swap
    font.pixelSize: Style.fontSize
    width: Style.dp(800)
    height: _content.implicitHeight + Style.dp(30)

    color: Style.background
    U.Universal.theme: Style.theme

    title: "Swap Devices"

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }

    // The card it was opened from: its device starts as the connected device.
    property string initialGuid: ""
    // Device ids compare without braces or case ({ABC} == abc).
    function _sameGuid(a, b) {
        function clean(v) { return String(v || "").replace(/[{}]/g, "").toLowerCase() }
        return clean(a).length > 0 && clean(a) === clean(b)
    }
    function pickInitial() {
        var box = _physicalDeviceSelection
        for (var i = 0; i < box.count; i++) {
            if (_sameGuid(box.valueAt(i), initialGuid)) {
                box.currentIndex = i
                return
            }
        }
    }
    onInitialGuidChanged: pickInitial()
    Component.onCompleted: Qt.callLater(pickInitial)

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
                    var from = _profileDeviceSelection.currentValue
                    var to = _physicalDeviceSelection.currentValue
                    // Every binding moves at once: ask first.
                    _swapGate.confirmThen("Swap bindings",
                        "Move every binding of " + _profileDeviceSelection.currentText
                        + " onto " + _physicalDeviceSelection.currentText + "?\n\n"
                        + "This changes the open profile. Nothing is saved yet: to undo, "
                        + "load the profile again without saving.",
                        "Swap bindings", function() {
                            _statusMessage.text = _tools.swapDevices(from, to)
                        })
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

    // Asks before Swap Bindings moves every binding.
    DismissibleDialog {
        id: _swapGate
    }
}
