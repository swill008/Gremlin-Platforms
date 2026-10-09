// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

// OSC Module Setup's "Server" tab (D-09-OSC-FILE point 4, D-09-OSC-TABS):
// listening, host and port, this PC's addresses with Copy, auto-release and
// padding. Each change is checked and written to OSC's file at once.
Flickable {
    id: _root
    objectName: "oscServerSection"

    required property OscServerModel server

    // A box still being typed in when the window closes is saved too.
    function commit() {
        _host.save()
        _port.save()
        _delay.save()
    }
    Component.onDestruction: commit()

    clip: true
    contentWidth: width
    contentHeight: _column.implicitHeight + Style.dp(24)
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {
        policy: _root.contentHeight > _root.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
    }

    component SettingField: JGTextField {
        property string key: ""
        property string saved: ""
        // Set in code, not bound: typing would break a binding anyway.
        Component.onCompleted: text = saved
        selectByMouse: true
        function save() {
            if (text !== saved)
                _root.server.setValue(key, text)
        }
        onEditingFinished: save()
        onSavedChanged: text = saved
    }

    // The Button Map's small outline button.
    component SmallButton: Rectangle {
        id: _small
        property alias text: _smallText.text
        readonly property alias hovered: _smallArea.containsMouse
        signal clicked()
        implicitWidth: _smallText.implicitWidth + Style.dp(14)
        implicitHeight: Style.dp(24)
        radius: Style.dp(4)
        color: _smallArea.containsMouse ? Style.bgSelected : Style.clear
        border.color: Style.line
        Label {
            id: _smallText
            anchors.centerIn: parent
            font.pixelSize: Style.dp(12)
            color: Style.fg
        }
        MouseArea {
            id: _smallArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: _small.clicked()
        }
    }

    ColumnLayout {
        id: _column
        x: Style.dp(14)
        y: Style.dp(12)
        width: _root.width - Style.dp(28)
        spacing: Style.dp(10)

        SectionHeading {
            text: "Server"
            Layout.fillWidth: true
        }

        CheckBox {
            objectName: "oscServerEnabled"
            text: "Listen for OSC messages"
            checked: _root.server.enabled
            onClicked: _root.server.setValue("enabled", checked)
        }

        GridLayout {
            columns: 4
            columnSpacing: Style.dp(6)
            rowSpacing: Style.dp(4)
            Layout.fillWidth: true

            Label {
                text: "Host"
                color: Style.fgSoft
            }
            SettingField {
                id: _host
                objectName: "oscServerHost"
                key: "host"
                saved: _root.server.host
                Layout.fillWidth: true
                placeholderText: "All addresses on this PC"
                PointerTip {
                    text: "Leave blank to listen on all addresses on this PC, "
                          + "or type an IP address or computer name."
                    show: _host.hovered
                }
            }
            Label {
                text: "Port"
                color: Style.fgSoft
            }
            SettingField {
                id: _port
                objectName: "oscServerPort"
                key: "port"
                saved: _root.server.port
                Layout.preferredWidth: Style.dp(90)
                inputMethodHints: Qt.ImhDigitsOnly
            }
        }

        // This PC's addresses and the port, for the app that sends here.
        Label {
            text: "Use one of these in your app:"
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
        }
        Repeater {
            model: _root.server.pcAddresses
            delegate: RowLayout {
                id: _addressRow
                required property string modelData
                required property int index
                readonly property string address: modelData + ":" + _root.server.port
                spacing: Style.dp(8)
                Label {
                    objectName: "oscPcAddress" + _addressRow.index
                    text: _addressRow.address
                    font.family: Style.monoFont
                    color: Style.fg
                }
                SmallButton {
                    objectName: "oscCopyAddress" + _addressRow.index
                    text: "Copy"
                    onClicked: _root.server.copyText(_addressRow.address)
                }
            }
        }

        RowLayout {
            spacing: Style.dp(6)
            Layout.topMargin: Style.dp(8)
            CheckBox {
                objectName: "oscServerAutorelease"
                text: "Auto-release address-only messages after"
                checked: _root.server.autoreleaseNoArg
                onClicked: _root.server.setValue("autorelease_no_arg", checked)
            }
            SettingField {
                id: _delay
                objectName: "oscServerDelay"
                key: "autorelease_delay_ms"
                saved: _root.server.autoreleaseDelay
                Layout.preferredWidth: Style.dp(90)
                inputMethodHints: Qt.ImhDigitsOnly
            }
            Label {
                text: "ms (default delay)"
                color: Style.fgSoft
            }
        }

        CheckBox {
            objectName: "oscServerPadArgs"
            text: "Pad address-only messages (treat them as value 1.0)"
            checked: _root.server.padArgs
            onClicked: _root.server.setValue("pad_args", checked)
        }
    }
}
