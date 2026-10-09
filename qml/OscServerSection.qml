// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

import "confirm.js" as Confirm

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
        }

        // This PC's addresses and the port, for the app that sends here.
        Label {
            text: "Use one of these in your app:"
            color: Style.fgMuted
        }
        Repeater {
            model: _model.pcAddresses
            delegate: RowLayout {
                required property string modelData
                required property int index
                readonly property string address: modelData + ":" + _model.port
                spacing: Style.dp(8)
                Label {
                    objectName: "oscPcAddress" + index
                    text: parent.address
                    font.family: Style.monoFont
                }
                Button {
                    objectName: "oscCopyAddress" + index
                    text: "Copy"
                    onClicked: _model.copyText(parent.address)
                }
            }
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

        SectionHeading {
            text: "Output"
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(8)
        }

        CheckBox {
            objectName: "oscOutputEnabled"
            text: "OSC output (Send OSC actions and feedback)"
            checked: _model.outputEnabled
            onClicked: _model.setValue("output_enabled", checked)
        }

        CheckBox {
            objectName: "oscReplyToSender"
            text: "Reply to sender"
            checked: _model.replyToSender
            onClicked: _model.setValue("reply_to_sender", checked)
            PointerTip {
                text: "The \"Reply\" target sends to the computer the last "
                      + "OSC message came from."
                show: parent.hovered
            }
        }

        Label {
            text: "Targets"
            font.bold: true
        }

        EmptyState {
            objectName: "oscTargetsEmpty"
            visible: _model.targets.length === 0
            text: "No targets yet. Add one below."
            Layout.fillWidth: true
        }

        Repeater {
            id: _targetRows
            model: _model.targets
            delegate: RowLayout {
                required property var modelData
                required property int index
                objectName: "oscTarget" + index
                spacing: Style.dp(8)
                Layout.fillWidth: true
                Label {
                    objectName: "oscTargetName" + index
                    text: modelData.name
                    font.bold: true
                    Layout.preferredWidth: Style.dp(120)
                    elide: Text.ElideRight
                }
                Label {
                    objectName: "oscTargetAddress" + index
                    text: modelData.host + ":" + modelData.port
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                Button {
                    objectName: "oscTargetEdit" + index
                    text: "Edit"
                    onClicked: _targetForm.edit(modelData)
                }
                DangerButton {
                    objectName: "oscTargetRemove" + index
                    text: "Remove"
                    onClicked: {
                        var target = modelData
                        Confirm.ask(_root, {
                            title: "Remove target " + target.name + "?",
                            text: "Send OSC actions and feedback rows that "
                                  + "use it will have no target.",
                            undoable: true,
                            action: "Remove",
                            onAccept: function() {
                                _model.removeTarget(target.id)
                                if (_targetForm.editId === target.id)
                                    _targetForm.reset()
                            }
                        })
                    }
                }
            }
        }

        // Add a target, or change the one being edited.
        RowLayout {
            id: _targetForm
            property string editId: ""
            spacing: Style.dp(8)
            Layout.fillWidth: true

            function edit(target) {
                editId = target.id
                _targetName.text = target.name
                _targetHost.text = target.host
                _targetPort.text = String(target.port)
                _targetName.forceActiveFocus()
            }
            function reset() {
                editId = ""
                _targetName.text = ""
                _targetHost.text = ""
                _targetPort.text = "8000"
            }
            function submit() {
                var done = editId.length
                    ? _model.editTarget(editId, _targetName.text, _targetHost.text,
                                        _targetPort.text)
                    : _model.addTarget(_targetName.text, _targetHost.text,
                                       _targetPort.text)
                if (done)
                    reset()
            }

            TextField {
                id: _targetName
                objectName: "oscTargetNameField"
                placeholderText: "Name"
                selectByMouse: true
                Layout.preferredWidth: Style.dp(120)
                onAccepted: _targetForm.submit()
            }
            TextField {
                id: _targetHost
                objectName: "oscTargetHostField"
                placeholderText: "IP address or computer name"
                selectByMouse: true
                Layout.fillWidth: true
                onAccepted: _targetForm.submit()
            }
            TextField {
                id: _targetPort
                objectName: "oscTargetPortField"
                text: "8000"
                selectByMouse: true
                inputMethodHints: Qt.ImhDigitsOnly
                Layout.preferredWidth: Style.dp(70)
                onAccepted: _targetForm.submit()
            }
            Button {
                objectName: "oscTargetSave"
                text: _targetForm.editId.length ? "Save Target" : "Add Target"
                onClicked: _targetForm.submit()
            }
            Button {
                objectName: "oscTargetCancel"
                visible: _targetForm.editId.length > 0
                text: "Cancel"
                onClicked: _targetForm.reset()
            }
        }

        SectionHeading {
            text: "Discovery"
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(8)
        }

        Label {
            objectName: "oscDiscoveryUnavailable"
            visible: !_model.discoveryAvailable
            text: "Discovery is not available on this PC."
            color: Style.fgMuted
        }

        CheckBox {
            objectName: "oscAnnounce"
            enabled: _model.discoveryAvailable
            text: "Announce this PC"
            checked: _model.announce
            onClicked: _model.setValue("announce", checked)
            PointerTip {
                text: "Lets OSC apps on your network find this PC and its port."
                show: parent.hovered
            }
        }

        CheckBox {
            objectName: "oscFindDevices"
            enabled: _model.discoveryAvailable
            text: "Find OSC devices"
            checked: _model.findDevices
            onClicked: _model.setValue("find_devices", checked)
            PointerTip {
                text: "Lists OSC apps on your network that announce themselves."
                show: parent.hovered
            }
        }

        Label {
            objectName: "oscFoundEmpty"
            visible: _model.findDevices && _model.foundDevices.length === 0
            text: "No OSC devices found yet."
            color: Style.fgMuted
        }

        Repeater {
            model: _model.findDevices ? _model.foundDevices : []
            delegate: RowLayout {
                required property var modelData
                required property int index
                objectName: "oscFound" + index
                spacing: Style.dp(8)
                Label {
                    objectName: "oscFoundName" + index
                    text: modelData.name
                    Layout.preferredWidth: Style.dp(160)
                    elide: Text.ElideRight
                }
                Label {
                    text: modelData.host + ":" + modelData.port
                    Layout.fillWidth: true
                }
                Button {
                    objectName: "oscFoundAdd" + index
                    text: "Add as Target"
                    onClicked: _model.addFoundTarget(modelData.name, modelData.host,
                                                     modelData.port)
                }
            }
        }

        MessageLine {
            id: _message
            objectName: "oscServerMessage"
            Layout.fillWidth: true
        }
    }
}
