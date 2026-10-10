// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style
import "confirm.js" as Confirm

// OSC Module Setup's "Server" tab (D-09-OSC-FILE point 4, D-09-OSC-TABS):
// listening, host and port, this PC's addresses with Copy, auto-release and
// padding, and the allowed senders (09 S160). Each change is checked and
// written to OSC's file at once.
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

        // Allowed senders (09 S160): OSC only from these addresses and
        // ranges; empty = everyone. A card like the Output tab's targets.
        Rectangle {
            objectName: "oscAllowedSenders"
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(8)
            color: Style.bgCard
            border.color: Style.lineStrong
            border.width: 1
            radius: Style.dp(8)
            implicitHeight: _senders.implicitHeight + Style.dp(16)

            ColumnLayout {
                id: _senders
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    margins: Style.dp(8)
                }
                spacing: Style.dp(4)

                Label {
                    text: "Allowed senders"
                    font.pixelSize: Style.dp(13)
                    font.bold: true
                    color: Style.fgStrong
                }
                Label {
                    text: "OSC is accepted only from these IP addresses and ranges. "
                          + "Listen and Bulk capture obey the list too; the OSC Monitor "
                          + "still shows other senders as blocked."
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                EmptyState {
                    objectName: "oscSendersEmpty"
                    visible: _root.server.allowSenders.length === 0
                    text: "Empty: OSC from every sender is accepted."
                    Layout.fillWidth: true
                }

                Repeater {
                    model: _root.server.allowSenders
                    delegate: Rectangle {
                        id: _senderRow
                        required property string modelData
                        required property int index
                        objectName: "oscSender" + index
                        Layout.fillWidth: true
                        implicitHeight: Style.dp(34)
                        radius: Style.dp(4)
                        color: _senderHover.hovered ? Style.bgRaised : Style.clear
                        HoverHandler { id: _senderHover }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Style.dp(6)
                            anchors.rightMargin: Style.dp(4)
                            spacing: Style.dp(6)
                            Label {
                                objectName: "oscSenderText" + _senderRow.index
                                text: _senderRow.modelData
                                font.family: Style.monoFont
                                color: Style.fg
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                            }
                            DangerButton {
                                objectName: "oscSenderRemove" + _senderRow.index
                                text: "Remove"
                                implicitHeight: Style.dp(28)
                                onClicked: {
                                    var entry = _senderRow.modelData
                                    var server = _root.server
                                    var last = server.allowSenders.length === 1
                                    Confirm.ask(_root, {
                                        title: "Remove " + entry + "?",
                                        text: last
                                            ? "The list is then empty: OSC from every sender is accepted."
                                            : "OSC from " + entry + " is no longer accepted.",
                                        undoable: true,
                                        action: "Remove",
                                        onAccept: function() { server.removeSender(entry) }
                                    })
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    spacing: Style.dp(6)
                    Layout.fillWidth: true
                    Layout.topMargin: Style.dp(4)

                    function submit() {
                        if (_root.server.addSender(_senderField.text))
                            _senderField.text = ""
                    }

                    JGTextField {
                        id: _senderField
                        objectName: "oscSenderField"
                        placeholderText: "IP address (192.168.1.5) or range (192.168.1.0/24)"
                        selectByMouse: true
                        Layout.fillWidth: true
                        onAccepted: parent.submit()
                    }
                    Button {
                        objectName: "oscSenderAdd"
                        text: "Add"
                        implicitHeight: Style.dp(28)
                        enabled: _senderField.text.trim().length > 0
                        onClicked: parent.submit()
                    }
                }
            }
        }
    }
}
