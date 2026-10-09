// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

// OSC's Module Setup "Server" section (D-09-OSC-FILE point 4). Each change
// is checked and written to OSC's file at once, and takes effect at once.
Frame {
    id: _root
    objectName: "oscServerSection"

    property alias model: _model

    // A box still being typed in when the window closes is saved too.
    function commit() {
        _host.save()
        _port.save()
        _outHost.save()
        _outPort.save()
        _delay.save()
    }
    Component.onDestruction: commit()

    OscServerModel {
        id: _model
        onMessageChanged: {
            if (message.length)
                _message.show(message, true)
            else
                _message.clear()
        }
    }

    component SettingField: TextField {
        id: _field
        property string key: ""
        property string saved: ""
        text: saved
        selectByMouse: true
        function save() {
            if (text !== saved)
                _model.setValue(key, text)
        }
        onEditingFinished: save()
        onSavedChanged: text = saved
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Style.dp(6)

        Label {
            text: "Server"
            font.bold: true
        }

        CheckBox {
            objectName: "oscServerEnabled"
            text: "Listen for OSC messages"
            checked: _model.enabled
            onClicked: _model.setValue("enabled", checked)
        }

        GridLayout {
            columns: 4
            columnSpacing: Style.dp(8)
            rowSpacing: Style.dp(4)
            Layout.fillWidth: true

            Label { text: "Host" }
            SettingField {
                id: _host
                objectName: "oscServerHost"
                key: "host"
                saved: _model.host
                Layout.fillWidth: true
                placeholderText: "All addresses on this PC"
                PointerTip {
                    text: "Leave blank to listen on all addresses on this PC, "
                          + "or type an IP address or computer name."
                    show: _host.hovered
                }
            }
            Label { text: "Port" }
            SettingField {
                id: _port
                objectName: "oscServerPort"
                key: "port"
                saved: _model.port
                Layout.preferredWidth: Style.dp(80)
                inputMethodHints: Qt.ImhDigitsOnly
            }

            Label { text: "Output host" }
            SettingField {
                id: _outHost
                objectName: "oscServerOutputHost"
                key: "output_host"
                saved: _model.outputHost
                Layout.fillWidth: true
            }
            Label { text: "Port" }
            SettingField {
                id: _outPort
                objectName: "oscServerOutputPort"
                key: "output_port"
                saved: _model.outputPort
                Layout.preferredWidth: Style.dp(80)
                inputMethodHints: Qt.ImhDigitsOnly
            }
        }

        Label {
            text: "The output host and port are used once OSC output is built."
            color: Style.fgMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            spacing: Style.dp(8)
            CheckBox {
                objectName: "oscServerAutorelease"
                text: "Auto-release address-only messages after"
                checked: _model.autoreleaseNoArg
                onClicked: _model.setValue("autorelease_no_arg", checked)
            }
            SettingField {
                id: _delay
                objectName: "oscServerDelay"
                key: "autorelease_delay_ms"
                saved: _model.autoreleaseDelay
                Layout.preferredWidth: Style.dp(80)
                inputMethodHints: Qt.ImhDigitsOnly
            }
            Label { text: "ms (default delay)" }
        }

        CheckBox {
            objectName: "oscServerPadArgs"
            text: "Pad address-only messages (treat them as value 1.0)"
            checked: _model.padArgs
            onClicked: _model.setValue("pad_args", checked)
        }

        MessageLine {
            id: _message
            objectName: "oscServerMessage"
            Layout.fillWidth: true
        }
    }
}
