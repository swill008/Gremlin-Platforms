// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style

Popup {
    id: _root

    property var deviceModel: null
    property string lastParameters: ""
    property string lastSource: ""
    property bool closeOnCapture: true
    readonly property string buttonHelpText: "The input will trigger a press action when the first parameter value is not zero (0).\nA value of zero (0) will trigger a release action.\nUse this mode to trigger button presses from OSC messages."

    signal accepted(string cmd, string mode)

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Style.dp(20)
    width: Style.dp(860)

    OscSettingsInfo { id: _oscInfo }
    OscBulkCapture { id: _bulk }

    background: Rectangle {
        color: Style.background
        border.color: Style.accent
        border.width: Style.dp(1)
        radius: Style.dp(4)
    }

    function resetFields() {
        _cmd.text = ""
        lastParameters = ""
        lastSource = ""
        closeOnCapture = true
        _modeButton.checked = true
        _messageOnly.checked = true
        _triggerOn.checked = false
        _delay.text = "250"
    }

    function helpText() {
        if (_modeAxis.checked || _modeChange.checked) {
            return "The first parameter is used as an axis value.\nValues are limited to the range -1.0 to 1.0."
        }
        return buttonHelpText
    }

    function footerText() {
        if (_messageData.checked) {
            return "The OSC message and its data are used as the input."
        }
        return "The OSC message is the primary input (data ignored)"
    }

    function selectedMode() {
        if (_modeAxis.checked || _modeChange.checked) {
            return "Axis"
        }
        return "Button"
    }

    function pauseHighlight() {
        if (backend) {
            backend.pauseInputHighlighting()
        }
    }

    function resumeHighlight() {
        if (backend) {
            backend.resumeInputHighlighting()
        }
    }

    function bindCapturedCommand(address) {
        var cmd = (address || "").trim()
        if (!cmd.length) {
            return
        }
        _listenSettings.close()
        _root.accepted(cmd, _root.selectedMode())
        _root.close()
    }

    Connections {
        target: _root.deviceModel

        function onCommandCaptured(address, parameters) {
            _cmd.text = address
            lastParameters = parameters
            lastSource = address
            if (!_root.closeOnCapture) {
                return
            }
            _root.bindCapturedCommand(address)
        }
    }

    DismissibleDialog {
        id: _listenSettings

        titleText: "Listening for OSC"
        confirmText: "OK"
        messageText: ""

        onOpened: _root.closePolicy = Popup.NoAutoClose
        onClosed: _root.closePolicy = Popup.CloseOnEscape | Popup.CloseOnPressOutside
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(10)

        Label {
            text: "OSC Input Mapper"
            font.bold: true
            font.pixelSize: Style.dp(16)
        }

        Label { text: "OSC message:" }

        RowLayout {
            Label { text: "Cmd:"; Layout.preferredWidth: Style.dp(70) }
            TextField {
                id: _cmd
                Layout.fillWidth: true
                placeholderText: "/button/1"
            }
        }

        Label { text: "Parameters:  " + (_root.lastParameters || "") }
        Label { text: "Source:  " + (_root.lastSource || "") }

        RowLayout {
            spacing: Style.dp(16)
            Layout.fillWidth: true
            Label { text: "Action mode:" }
            RadioButton { id: _modeChange; text: "Change" }
            RadioButton { id: _modeButton; text: "Button"; checked: true }
            RadioButton { id: _modeAxis; text: "Axis" }
            Item { Layout.fillWidth: true }
            RadioButton { id: _messageOnly; text: "Message only"; checked: true }
            RadioButton {
                id: _messageData
                text: "Message + data"
            }
        }

        ButtonGroup { buttons: [_modeChange, _modeButton, _modeAxis] }
        ButtonGroup { buttons: [_messageOnly, _messageData] }

        RowLayout {
            spacing: Style.dp(6)
            CheckBox { id: _triggerOn; text: "Trigger on message" }
            TextField {
                id: _delay
                text: "250"
                implicitWidth: Style.dp(60)
                enabled: _triggerOn.checked
            }
            Repeater {
                model: [
                    {"label": "1/10s", "ms": "100"},
                    {"label": "1/4s", "ms": "250"},
                    {"label": "1/2s", "ms": "500"},
                    {"label": "3/4s", "ms": "750"},
                    {"label": "1s", "ms": "1000"}
                ]
                Button {
                    text: modelData.label
                    enabled: _triggerOn.checked
                    onClicked: _delay.text = modelData.ms
                }
            }
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: _helpMeasure.implicitHeight + Style.dp(16)

            Label {
                id: _helpMeasure
                visible: false
                width: parent.width - Style.dp(16)
                wrapMode: Text.WordWrap
                text: _root.buttonHelpText
            }

            Rectangle {
                anchors.fill: parent
                color: "#8a7a2a"
                border.color: "#c4b44a"

                Label {
                    id: _help
                    anchors.fill: parent
                    anchors.margins: Style.dp(8)
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignTop
                    text: _root.helpText()
                    color: "#1b1b1b"
                }
            }
        }

        Label { text: _root.footerText() }

        Item { Layout.preferredHeight: Style.dp(8) }

        RowLayout {
            Button {
                text: deviceModel && deviceModel.listening ? "Listening…" : "Listen"
                onClicked: {
                    if (!deviceModel) {
                        return
                    }
                    if (deviceModel.listening) {
                        deviceModel.cancelListen()
                        _root.resumeHighlight()
                    } else {
                        _root.closeOnCapture = !_bulkCapture.checked
                        _root.pauseHighlight()
                        _listenSettings.messageText = _oscInfo.summary()
                        _listenSettings.open()
                        if (_bulkCapture.checked) {
                            _bulk.start(deviceModel, _root.selectedMode())
                        } else {
                            deviceModel.listenForCommand()
                        }
                    }
                }
            }
            CheckBox {
                id: _bulkCapture
                text: "Bulk capture"
                PointerTip {
                    text: "Bulk capture mode is intended for simple devices such as the Stream Deck to capture manual button presses."
                    delay: 400
                    show: true
                }
                onCheckedChanged: {
                    if (!checked && deviceModel && deviceModel.listening) {
                        deviceModel.cancelListen()
                    }
                }
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Ok"
                enabled: _cmd.text.trim().length > 0
                onClicked: {
                    _root.accepted(_cmd.text.trim(), _root.selectedMode())
                    _root.close()
                }
            }
            Button {
                text: "Cancel"
                onClicked: _root.close()
            }
        }
    }

    onClosed: {
        if (deviceModel && deviceModel.listening) {
            deviceModel.cancelListen()
        }
        _root.resumeHighlight()
    }
}
