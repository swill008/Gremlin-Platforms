// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The OSC Add window (D-09-OSC-INPUT): one OSC input with its settings.
// Typed, Listen and Bulk capture all use the settings chosen here. Encoder
// mode (D-09-OSC-ENCODER) adds format, output and step size / pulse delay. Opened
// with openForEdit() it changes an existing input's settings instead.

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
    // "" adds a new input; a uid edits that input's settings.
    property string editUid: ""
    readonly property bool editing: editUid.length > 0
    // The values of the last captured message (P1..Pn).
    readonly property var capturedValues: _splitValues(lastParameters)
    // Source choices: the captured values, or as many as the edited input needs.
    property int _extraSources: 0
    readonly property int sourceCount: Math.max(capturedValues.length, _extraSources)
    property int sourceIndex: 0
    // trigger as loaded for an edit (false is kept when the box stays off).
    property var _loadedTrigger: null
    // An input with actions keeps its type (axis or button): "" / "axis" / "button".
    property string lockedKind: ""
    // Every change to the window's settings (pushed to the model while listening).
    readonly property var currentSettings: settings()

    readonly property string buttonHelpText: "The input presses when the value at the source is not zero (0) and releases when it is zero (0).\nA message with no value presses, then releases after the delay.\nUse this mode to trigger button presses from OSC messages."
    readonly property string axisHelpText: "The value at the source is used as an axis value.\nValues from Min to Max are scaled to the range -1.0 to 1.0."
    readonly property string changeHelpText: "The input presses when the value at the source changes, then releases after the delay."
    readonly property string encoderHelpText: "Each message is one turn of the encoder.\nAxis: each turn moves the axis by the step size (clockwise up, counter-clockwise down).\nPulses: each turn in the chosen direction presses the button, then releases it after the delay.\nAuto works out the format from the values received."

    signal accepted(var settings)

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Style.dp(20)
    width: Style.dp(860)

    OscSettingsInfo { id: _oscInfo }
    OscBulkCapture { id: _bulk }

    // A Button Map card (osc_style.md): card fill, strong line, round corners.
    background: Rectangle {
        color: Style.bgCard
        border.color: Style.lineStrong
        border.width: 1
        radius: Style.dp(8)
    }

    function _splitValues(text) {
        var t = String(text || "").trim()
        if (!t.length)
            return []
        return t.split(",").map(function(v) { return v.trim() })
    }

    function resetFields() {
        editUid = ""
        _cmd.text = ""
        lastParameters = ""
        lastSource = ""
        closeOnCapture = true
        _extraSources = 0
        sourceIndex = 0
        _loadedTrigger = null
        lockedKind = ""
        _modeButton.checked = true
        _messageOnly.checked = true
        _data.text = ""
        _rangeMin.text = "0"
        _rangeMax.text = "1"
        _triggerOn.checked = false
        _delay.text = "250"
        _encFormatAuto.checked = true
        _encStep.text = "0.05"
        _encOutAxis.checked = true
        _encDelay.text = "100"
        _message.clear()
    }

    // Fill the window from an input's settings (inputSettings(uid)).
    function openForEdit(uid, s) {
        resetFields()
        editUid = uid
        var st = s || {}
        _cmd.text = st.address || ""
        var encAxis = st.mode === "encoder" && (st.enc_output || "axis") === "axis"
        if (st.locked)
            lockedKind = (st.mode === "axis" || encAxis) ? "axis" : "button"
        if (st.enc_format === "direction")
            _encFormatDirection.checked = true
        else if (st.enc_format === "signed")
            _encFormatSigned.checked = true
        if (st.enc_step !== undefined && st.enc_step !== null)
            _encStep.text = String(st.enc_step)
        if (st.enc_output === "pulse_cw")
            _encOutCw.checked = true
        else if (st.enc_output === "pulse_ccw")
            _encOutCcw.checked = true
        if (st.mode === "encoder") {
            _modeEncoder.checked = true
            if (st.delay_ms !== undefined && st.delay_ms !== null)
                _encDelay.text = String(st.delay_ms)
        } else if (st.mode === "axis")
            _modeAxis.checked = true
        else if (st.mode === "change")
            _modeChange.checked = true
        else
            _modeButton.checked = true
        var data = st.data || []
        if (st.cmd_mode === "data")
            _messageData.checked = true
        _data.text = data.join(", ")
        sourceIndex = st.source || 0
        _extraSources = Math.max(data.length, sourceIndex > 0 ? sourceIndex + 1 : 0)
        _rangeMin.text = st.range_min !== undefined && st.range_min !== null ? String(st.range_min) : "0"
        _rangeMax.text = st.range_max !== undefined && st.range_max !== null ? String(st.range_max) : "1"
        _loadedTrigger = st.trigger === undefined ? null : st.trigger
        _triggerOn.checked = st.trigger === true
        if (st.delay_ms !== undefined && st.delay_ms !== null)
            _delay.text = String(st.delay_ms)
        open()
    }

    function selectedMode() {
        if (_modeAxis.checked)
            return "axis"
        if (_modeChange.checked)
            return "change"
        if (_modeEncoder.checked)
            return "encoder"
        return "button"
    }

    function encoderFormat() {
        if (_encFormatDirection.checked)
            return "direction"
        if (_encFormatSigned.checked)
            return "signed"
        return "auto"
    }

    function encoderOutput() {
        if (_encOutCw.checked)
            return "pulse_cw"
        if (_encOutCcw.checked)
            return "pulse_ccw"
        return "axis"
    }

    readonly property bool encoderPulses: _modeEncoder.checked && !_encOutAxis.checked

    // An encoder on a locked input keeps its kind: axis output, or pulses.
    function fitEncoderOutput() {
        if (lockedKind === "axis")
            _encOutAxis.checked = true
        else if (lockedKind === "button" && _encOutAxis.checked)
            _encOutCw.checked = true
    }

    function stepError() {
        if (!_modeEncoder.checked)
            return ""
        var v = Number(_encStep.text)
        if (!_encStep.text.trim().length || isNaN(v) || v <= 0 || v > 2)
            return "The step size must be a number above 0 and at most 2."
        return ""
    }

    function rangeError() {
        if (!_modeAxis.checked)
            return ""
        var lo = Number(_rangeMin.text)
        var hi = Number(_rangeMax.text)
        if (!_rangeMin.text.trim().length || !_rangeMax.text.trim().length
                || isNaN(lo) || isNaN(hi))
            return "Min and Max must be numbers."
        if (lo >= hi)
            return "Min must be less than Max."
        return ""
    }

    function delayError() {
        if (encoderPulses) {
            if (!/^\d+$/.test(_encDelay.text.trim()))
                return "The delay must be a whole number of milliseconds."
            return ""
        }
        if (!_triggerOn.checked || !_modeButton.checked)
            return ""
        var t = _delay.text.trim()
        if (!/^\d+$/.test(t))
            return "The delay must be a whole number of milliseconds."
        return ""
    }

    function settings() {
        var trigger = _triggerOn.checked ? true
            : (_loadedTrigger === false ? false : null)
        var dataMode = _messageData.checked
        var delay = null
        if (encoderPulses)
            delay = delayError() === "" ? parseInt(_encDelay.text.trim()) : null
        else if (_triggerOn.checked && delayError() === "")
            delay = parseInt(_delay.text.trim())
        return {
            "address": _cmd.text.trim(),
            "mode": selectedMode(),
            "cmd_mode": dataMode ? "data" : "message",
            "data": dataMode ? _splitValues(_data.text) : [],
            "source": sourceIndex,
            "range_min": Number(_rangeMin.text) || 0.0,
            "range_max": _rangeMax.text.trim().length ? Number(_rangeMax.text) : 1.0,
            "trigger": trigger,
            "delay_ms": delay,
            "enc_format": encoderFormat(),
            "enc_step": stepError() === "" ? Number(_encStep.text) : 0.05,
            "enc_output": encoderOutput()
        }
    }

    function helpText() {
        if (_modeAxis.checked)
            return axisHelpText
        if (_modeChange.checked)
            return changeHelpText
        if (_modeEncoder.checked)
            return encoderHelpText
        return buttonHelpText
    }

    function footerText() {
        if (_messageData.checked)
            return "The OSC message and its data are used as the input."
        return "The OSC message is the primary input (data ignored)."
    }

    function pauseHighlight() {
        if (backend)
            backend.pauseInputHighlighting("osc-add")
    }

    function resumeHighlight() {
        if (backend)
            backend.resumeInputHighlighting("osc-add")
    }

    function pushCaptureSettings() {
        if (deviceModel && typeof deviceModel.setCaptureSettings === "function")
            deviceModel.setCaptureSettings(settings())
    }

    onCurrentSettingsChanged: {
        if (deviceModel && deviceModel.listening)
            pushCaptureSettings()
    }

    function bindCapturedCommand(address) {
        var cmd = (address || "").trim()
        if (!cmd.length)
            return
        _listenSettings.close()
        _root.accepted(_root.settings())
        _root.close()
    }

    // OK: adds the input, or saves the edited input's settings.
    function accept() {
        var err = rangeError() || stepError() || delayError()
        if (err.length) {
            _message.show(err, true)
            return false
        }
        var s = settings()
        if (!s.address.length)
            return false
        if (editing) {
            var res = deviceModel ? deviceModel.updateInputSettings(editUid, s) : ""
            if (res && String(res).length) {
                _message.show(String(res), true)
                return false
            }
            close()
            return true
        }
        _root.accepted(s)
        close()
        return true
    }

    function startListen() {
        if (!deviceModel)
            return
        if (deviceModel.listening) {
            deviceModel.cancelListen()
            resumeHighlight()
            return
        }
        closeOnCapture = !_bulkCapture.checked
        pauseHighlight()
        _listenSettings.messageText = _oscInfo.summary()
        _listenSettings.open()
        pushCaptureSettings()
        if (_bulkCapture.checked)
            _bulk.start(deviceModel, settings())
        else
            deviceModel.listenForCommand(settings())
    }

    function stopListen() {
        if (deviceModel && deviceModel.listening)
            deviceModel.cancelListen()
        resumeHighlight()
    }

    Connections {
        target: _root.deviceModel

        function onCommandCaptured(address, parameters) {
            _cmd.text = address
            lastParameters = parameters
            lastSource = address
            if (sourceIndex >= Math.max(capturedValues.length, 1))
                sourceIndex = 0
            _data.text = capturedValues.join(", ")
            if (!_root.closeOnCapture)
                return
            _root.bindCapturedCommand(address)
        }
    }

    DismissibleDialog {
        id: _listenSettings
        objectName: "oscListenBox"

        titleText: "Listening for OSC"
        confirmText: "Stop"
        messageText: ""

        onOpened: _root.closePolicy = Popup.NoAutoClose
        onClosed: {
            _root.closePolicy = Popup.CloseOnEscape | Popup.CloseOnPressOutside
            // Stop (or Escape) ends listening; after a capture it has ended already.
            _root.stopListen()
        }
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(10)

        Label {
            text: _root.editing ? "OSC Input Settings" : "OSC Input Mapper"
            font.bold: true
            font.pixelSize: Style.dp(16)
            color: Style.fgStrong
        }

        Label { text: "OSC message:" }

        RowLayout {
            Label { text: "Address:"; Layout.preferredWidth: Style.dp(70) }
            TextField {
                id: _cmd
                objectName: "oscCmd"
                Layout.fillWidth: true
                placeholderText: "/button/1"
                readOnly: _root.editing
            }
        }

        Label { text: "Parameters:  " + (_root.lastParameters || "") }
        Label { text: "Source:  " + (_root.lastSource || "") }

        RowLayout {
            spacing: Style.dp(16)
            Layout.fillWidth: true
            Label { text: "Action mode:" }
            RadioButton {
                id: _modeChange
                objectName: "oscModeChange"
                text: "Change"
                enabled: _root.lockedKind !== "axis"
            }
            RadioButton {
                id: _modeButton
                objectName: "oscModeButton"
                text: "Button"
                checked: true
                enabled: _root.lockedKind !== "axis"
            }
            RadioButton {
                id: _modeAxis
                objectName: "oscModeAxis"
                text: "Axis"
                enabled: _root.lockedKind !== "button"
            }
            RadioButton {
                id: _modeEncoder
                objectName: "oscModeEncoder"
                text: "Encoder"
                onCheckedChanged: if (checked) _root.fitEncoderOutput()
            }
            Item { Layout.fillWidth: true }
            RadioButton { id: _messageOnly; objectName: "oscMessageOnly"; text: "Message only"; checked: true }
            RadioButton { id: _messageData; objectName: "oscMessageData"; text: "Message + data" }
        }

        ButtonGroup { buttons: [_modeChange, _modeButton, _modeAxis, _modeEncoder] }
        ButtonGroup { buttons: [_messageOnly, _messageData] }

        RowLayout {
            visible: _messageData.checked
            Label { text: "Data:"; Layout.preferredWidth: Style.dp(70) }
            TextField {
                id: _data
                objectName: "oscData"
                Layout.fillWidth: true
                placeholderText: "1, 0.5"
            }
        }

        // Which value of the message the input reads (P1 = the first).
        RowLayout {
            objectName: "oscSourceRow"
            visible: _root.sourceCount > 0
            spacing: Style.dp(8)
            Label { text: "Source value:" }
            Repeater {
                model: _root.sourceCount
                RadioButton {
                    objectName: "oscSource" + index
                    text: "P" + (index + 1)
                    checked: _root.sourceIndex === index
                    onClicked: _root.sourceIndex = index
                }
            }
        }

        RowLayout {
            objectName: "oscRangeRow"
            visible: _modeAxis.checked
            spacing: Style.dp(8)
            Label { text: "Min:" }
            TextField {
                id: _rangeMin
                objectName: "oscRangeMin"
                text: "0"
                implicitWidth: Style.dp(80)
            }
            Label { text: "Max:" }
            TextField {
                id: _rangeMax
                objectName: "oscRangeMax"
                text: "1"
                implicitWidth: Style.dp(80)
            }
            Label {
                objectName: "oscRangeError"
                text: _root.rangeError()
                color: Style.dangerText
            }
        }

        RowLayout {
            spacing: Style.dp(6)
            visible: _modeButton.checked
            CheckBox { id: _triggerOn; objectName: "oscTrigger"; text: "Trigger on message" }
            TextField {
                id: _delay
                objectName: "oscDelay"
                text: "250"
                implicitWidth: Style.dp(60)
                enabled: _triggerOn.checked
            }
            Label { text: "ms" }
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
            Label {
                text: _root.delayError()
                color: Style.dangerText
            }
        }

        // Encoder (D-09-OSC-ENCODER): format, output, step size or pulse delay.
        RowLayout {
            objectName: "oscEncoderFormatRow"
            visible: _modeEncoder.checked
            spacing: Style.dp(8)
            Label { text: "Format:" }
            RadioButton { id: _encFormatAuto; objectName: "oscEncFormatAuto"; text: "Auto"; checked: true }
            RadioButton { id: _encFormatDirection; objectName: "oscEncFormatDirection"; text: "1 = clockwise, 0 = counter-clockwise" }
            RadioButton { id: _encFormatSigned; objectName: "oscEncFormatSigned"; text: "+n and −n" }
        }
        ButtonGroup { buttons: [_encFormatAuto, _encFormatDirection, _encFormatSigned] }

        RowLayout {
            objectName: "oscEncoderOutputRow"
            visible: _modeEncoder.checked
            spacing: Style.dp(8)
            Label { text: "Output:" }
            RadioButton {
                id: _encOutAxis
                objectName: "oscEncOutAxis"
                text: "Axis"
                checked: true
                enabled: _root.lockedKind !== "button"
            }
            RadioButton {
                id: _encOutCw
                objectName: "oscEncOutCw"
                text: "Pulses clockwise"
                enabled: _root.lockedKind !== "axis"
            }
            RadioButton {
                id: _encOutCcw
                objectName: "oscEncOutCcw"
                text: "Pulses counter-clockwise"
                enabled: _root.lockedKind !== "axis"
            }
        }
        ButtonGroup { buttons: [_encOutAxis, _encOutCw, _encOutCcw] }

        RowLayout {
            objectName: "oscEncoderStepRow"
            visible: _modeEncoder.checked && _encOutAxis.checked
            spacing: Style.dp(8)
            Label { text: "Step size:" }
            TextField {
                id: _encStep
                objectName: "oscEncStep"
                text: "0.05"
                implicitWidth: Style.dp(80)
            }
            Label {
                text: _root.stepError()
                color: Style.dangerText
            }
        }

        RowLayout {
            objectName: "oscEncoderDelayRow"
            visible: _root.encoderPulses
            spacing: Style.dp(6)
            Label { text: "Release after:" }
            TextField {
                id: _encDelay
                objectName: "oscEncDelay"
                text: "100"
                implicitWidth: Style.dp(60)
            }
            Label { text: "ms" }
            Repeater {
                model: [
                    {"label": "1/10s", "ms": "100"},
                    {"label": "1/4s", "ms": "250"},
                    {"label": "1/2s", "ms": "500"}
                ]
                Button {
                    text: modelData.label
                    onClicked: _encDelay.text = modelData.ms
                }
            }
            Label {
                text: _root.delayError()
                color: Style.dangerText
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
                color: Style.noteFill
                border.color: Style.noteLine
                radius: Style.dp(4)

                Label {
                    id: _help
                    anchors.fill: parent
                    anchors.margins: Style.dp(8)
                    wrapMode: Text.WordWrap
                    verticalAlignment: Text.AlignTop
                    text: _root.helpText()
                    color: Style.noteText
                }
            }
        }

        Label { text: _root.footerText() }

        MessageLine {
            id: _message
            Layout.fillWidth: true
        }

        Item { Layout.preferredHeight: Style.dp(8) }

        RowLayout {
            Button {
                objectName: "oscListen"
                visible: !_root.editing
                text: deviceModel && deviceModel.listening ? "Listening…" : "Listen"
                onClicked: _root.startListen()
            }
            CheckBox {
                id: _bulkCapture
                objectName: "oscBulk"
                visible: !_root.editing
                text: "Bulk capture"
                PointerTip {
                    text: "Bulk capture mode is intended for simple devices such as the Stream Deck to capture manual button presses. Each new message is added with this window's settings."
                    show: true
                }
                onCheckedChanged: {
                    if (!checked && deviceModel && deviceModel.listening)
                        deviceModel.cancelListen()
                }
            }
            Item { Layout.fillWidth: true }
            Button {
                objectName: "oscOk"
                text: "OK"
                highlighted: true
                enabled: _cmd.text.trim().length > 0
                         && _root.rangeError() === "" && _root.stepError() === ""
                         && _root.delayError() === ""
                onClicked: _root.accept()
            }
            Button {
                text: "Cancel"
                onClicked: _root.close()
            }
        }
    }

    onClosed: {
        if (deviceModel && deviceModel.listening)
            deviceModel.cancelListen()
        resumeHighlight()
    }
}
