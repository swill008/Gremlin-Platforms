// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Menus
import Gremlin.Style

import "confirm.js" as Confirm

// OSC's Module Setup "Feedback" section (D-09-OSC-FEEDBACK): what Gremlin
// sends back to OSC devices. Each change is checked and written to OSC's
// file at once. It is the Feedback tab's body in OSC Setup (OscSetupTabs).
// It sits straight on its tab's card, as the other tabs do (osc_style.md):
// no card of its own inside it.
Item {
    id: _root
    objectName: "oscFeedbackSection"
    implicitWidth: _column.implicitWidth
    implicitHeight: _column.implicitHeight

    property alias model: _model

    // A box still being typed in when the window closes is saved too.
    function commit() {
        _syncAddress.save()
        _rate.save()
    }
    Component.onDestruction: commit()

    OscFeedbackModel {
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
        // Set in code, not bound: typing would break a binding anyway.
        Component.onCompleted: text = saved
        selectByMouse: true
        function save() {
            if (text !== saved)
                _model.setSetting(key, text)
        }
        onEditingFinished: save()
        onSavedChanged: text = saved
    }

    // A text box for one part of row rowIndex.
    component RowField: TextField {
        property int rowIndex: -1
        property string key: ""
        property string saved: ""
        text: saved
        selectByMouse: true
        onEditingFinished: {
            if (text !== saved && !_model.setRowValue(rowIndex, key, text))
                text = saved
        }
    }

    // A picker for one part of row rowIndex; choices are {value, text}.
    component RowPicker: ComboBox {
        property int rowIndex: -1
        property string key: ""
        property var saved
        textRole: "text"
        valueRole: "value"
        Component.onCompleted: currentIndex = indexOfValue(saved)
        onActivated: _model.setRowValue(rowIndex, key, currentValue)
    }

    // Asks a Companion template's few fields, then adds its row.
    Dialog {
        id: _template
        objectName: "oscFeedbackTemplateDialog"
        property string kind: ""
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        title: kind === "companion_variable" ? "Companion custom variable"
             : kind === "companion_text" ? "Companion key text"
             : "Companion key color"

        function ask(which) {
            kind = which
            _varName.text = "gremlin_mode"
            _page.text = "1"
            _keyRow.text = "0"
            _keyColumn.text = "0"
            _offColour.text = _model.defaultOffColor
            _onColour.text = _model.defaultOnColor
            open()
        }

        function add() {
            var params = kind === "companion_variable"
                ? { name: _varName.text }
                : { page: _page.text, row: _keyRow.text, column: _keyColumn.text,
                    off: _offColour.text, on: _onColour.text }
            var said = _model.addTemplateRow(kind, params)
            if (_model.message.length)
                return   // refused: the message line says why; the dialog stays
            close()
            if (said.length)
                _message.show(said, false)
        }

        ColumnLayout {
            spacing: Style.dp(10)

            RowLayout {
                visible: _template.kind === "companion_variable"
                spacing: Style.dp(6)
                Label { text: "Variable name"; color: Style.fgSoft }
                JGTextField {
                    id: _varName
                    objectName: "oscTemplateVariable"
                    selectByMouse: true
                    Layout.preferredWidth: Style.dp(180)
                }
            }
            Label {
                visible: _template.kind === "companion_variable"
                text: "Create the custom variable in Companion first."
                font.pixelSize: Style.dp(11)
                color: Style.fgMuted
            }
            RowLayout {
                visible: _template.kind !== "companion_variable"
                spacing: Style.dp(6)
                Label { text: "Page"; color: Style.fgSoft }
                JGTextField {
                    id: _page
                    objectName: "oscTemplatePage"
                    inputMethodHints: Qt.ImhDigitsOnly
                    Layout.preferredWidth: Style.dp(60)
                }
                Label { text: "Row"; color: Style.fgSoft }
                JGTextField {
                    id: _keyRow
                    objectName: "oscTemplateRow"
                    inputMethodHints: Qt.ImhDigitsOnly
                    Layout.preferredWidth: Style.dp(60)
                }
                Label { text: "Column"; color: Style.fgSoft }
                JGTextField {
                    id: _keyColumn
                    objectName: "oscTemplateColumn"
                    inputMethodHints: Qt.ImhDigitsOnly
                    Layout.preferredWidth: Style.dp(60)
                }
            }
            RowLayout {
                visible: _template.kind === "companion_colour"
                spacing: Style.dp(6)
                Label { text: "Off color"; color: Style.fgSoft }
                Rectangle {
                    implicitWidth: Style.dp(22)
                    implicitHeight: Style.dp(22)
                    radius: Style.dp(3)
                    border.color: Style.lineStrong
                    color: /^#[0-9a-fA-F]{6}$/.test(_offColour.text) ? _offColour.text : Style.clear
                }
                JGTextField {
                    id: _offColour
                    objectName: "oscTemplateOff"
                    Layout.preferredWidth: Style.dp(90)
                }
                Label { text: "On color"; color: Style.fgSoft }
                Rectangle {
                    implicitWidth: Style.dp(22)
                    implicitHeight: Style.dp(22)
                    radius: Style.dp(3)
                    border.color: Style.lineStrong
                    color: /^#[0-9a-fA-F]{6}$/.test(_onColour.text) ? _onColour.text : Style.clear
                }
                JGTextField {
                    id: _onColour
                    objectName: "oscTemplateOn"
                    Layout.preferredWidth: Style.dp(90)
                }
            }
            Label {
                visible: _template.kind !== "companion_variable"
                text: "Pages count from 1, rows and columns from 0. Turn on Companion\u2019s OSC Listener (Settings \u203a OSC)."
                font.pixelSize: Style.dp(11)
                color: Style.fgMuted
                wrapMode: Text.WordWrap
                Layout.maximumWidth: Style.dp(380)
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Style.dp(8)
                Item { Layout.fillWidth: true }
                Button {
                    objectName: "oscTemplateAdd"
                    text: "Add Row"
                    highlighted: true
                    onClicked: _template.add()
                }
                Button {
                    text: "Cancel"
                    onClicked: _template.close()
                }
            }
        }
    }

    ColumnLayout {
        id: _column
        anchors { left: parent.left; right: parent.right; top: parent.top }
        spacing: Style.dp(6)

        SectionHeading {
            text: "Feedback"
            Layout.fillWidth: true
        }

        CheckBox {
            objectName: "oscFeedbackEnabled"
            text: "Send feedback to OSC devices"
            checked: _model.feedbackEnabled
            onClicked: _model.setSetting("feedback_enabled", checked)
        }

        RowLayout {
            spacing: Style.dp(8)
            Label { text: "Send everything again at:" }
            CheckBox {
                objectName: "oscFeedbackResendRun"
                text: "Run start"
                checked: _model.resendRun
                onClicked: _model.setSetting("resend_run", checked)
            }
            CheckBox {
                objectName: "oscFeedbackResendMode"
                text: "Mode change"
                checked: _model.resendMode
                onClicked: _model.setSetting("resend_mode", checked)
            }
            CheckBox {
                objectName: "oscFeedbackResendProfile"
                text: "Profile switch"
                checked: _model.resendProfile
                onClicked: _model.setSetting("resend_profile", checked)
            }
        }

        RowLayout {
            spacing: Style.dp(8)
            Layout.fillWidth: true
            CheckBox {
                objectName: "oscFeedbackSyncEnabled"
                text: "Send everything again when a message comes to"
                checked: _model.syncEnabled
                onClicked: _model.setSetting("sync_enabled", checked)
            }
            SettingField {
                id: _syncAddress
                objectName: "oscFeedbackSyncAddress"
                key: "sync_address"
                saved: _model.syncAddress
                enabled: _model.syncEnabled
                Layout.fillWidth: true
            }
        }

        RowLayout {
            spacing: Style.dp(8)
            Label { text: "At most" }
            SettingField {
                id: _rate
                objectName: "oscFeedbackRate"
                key: "feedback_rate"
                saved: _model.feedbackRate
                Layout.preferredWidth: Style.dp(70)
                inputMethodHints: Qt.ImhDigitsOnly
            }
            Label { text: "messages per second per address" }
        }

        Label {
            visible: _rows.count === 0
            text: "No feedback rows. Add a row to send a value to an OSC device when it changes."
            color: Style.fgMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        // The rows (the Module Setup window scrolls OSC's sections).
        Item {
            objectName: "oscFeedbackRows"
            visible: _rows.count > 0
            Layout.fillWidth: true
            implicitHeight: _rowsColumn.implicitHeight

            ColumnLayout {
                id: _rowsColumn
                width: parent.width
                spacing: Style.dp(4)

                Repeater {
                    id: _rows
                    model: _model.rows

                    delegate: Rectangle {
                        id: _row
                        objectName: "oscFeedbackRow"
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        implicitHeight: _rowColumn.implicitHeight + Style.dp(12)
                        color: Style.bgRaised
                        border.color: Style.line
                        border.width: 1
                        radius: Style.dp(4)

                        ColumnLayout {
                            id: _rowColumn
                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: Style.dp(6) }
                            spacing: Style.dp(4)

                            RowLayout {
                                spacing: Style.dp(6)
                                Layout.fillWidth: true

                                CheckBox {
                                    objectName: "oscFeedbackRowEnabled"
                                    checked: _row.modelData.enabled
                                    onClicked: _model.setRowValue(_row.index, "enabled", checked)
                                    PointerTip {
                                        text: "Send this row"
                                        show: parent.hovered
                                    }
                                }
                                Label { text: "Source" }
                                RowPicker {
                                    objectName: "oscFeedbackRowKind"
                                    rowIndex: _row.index
                                    key: "kind"
                                    saved: _row.modelData.kind
                                    model: _model.kindChoices
                                    Layout.preferredWidth: Style.dp(190)
                                }
                                RowPicker {
                                    objectName: "oscFeedbackRowVjoy"
                                    visible: _row.modelData.kind === "vjoy_button"
                                             || _row.modelData.kind === "vjoy_axis"
                                    rowIndex: _row.index
                                    key: "device"
                                    saved: _row.modelData.device
                                    model: _model.vjoyChoices
                                    Layout.preferredWidth: Style.dp(100)
                                }
                                RowField {
                                    objectName: "oscFeedbackRowNumber"
                                    visible: _row.modelData.kind === "vjoy_button"
                                             || _row.modelData.kind === "vjoy_axis"
                                    rowIndex: _row.index
                                    key: "input"
                                    saved: String(_row.modelData.input)
                                    placeholderText: _row.modelData.kind === "vjoy_axis"
                                                     ? "Axis" : "Button"
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    Layout.preferredWidth: Style.dp(70)
                                }
                                RowPicker {
                                    objectName: "oscFeedbackRowLogical"
                                    visible: _row.modelData.kind === "logical"
                                    rowIndex: _row.index
                                    key: "input"
                                    saved: _row.modelData.input
                                    model: _model.logicalChoices
                                    displayText: currentIndex < 0 ? "Pick a control" : currentText
                                    Layout.preferredWidth: Style.dp(180)
                                }
                                RowPicker {
                                    objectName: "oscFeedbackRowOsc"
                                    visible: _row.modelData.kind === "osc_input"
                                    rowIndex: _row.index
                                    key: "input"
                                    saved: _row.modelData.input
                                    model: _model.oscChoices
                                    displayText: currentIndex < 0 ? "Pick an OSC input" : currentText
                                    Layout.preferredWidth: Style.dp(180)
                                }
                                Item { Layout.fillWidth: true }
                                DangerButton {
                                    objectName: "oscFeedbackRowRemove"
                                    text: "Remove"
                                    onClicked: {
                                        var index = _row.index
                                        var address = _row.modelData.address
                                        Confirm.ask(_root, {
                                            title: "Remove feedback row " + address + "?",
                                            text: "Nothing more is sent to " + address + ".",
                                            undoable: true,
                                            note: "You can restore it from Tools › History.",
                                            action: "Remove Row",
                                            onAccept: function() { _model.removeRow(index) }
                                        })
                                    }
                                }
                            }

                            RowLayout {
                                spacing: Style.dp(6)
                                Layout.fillWidth: true

                                Label { text: "Send to" }
                                RowPicker {
                                    objectName: "oscFeedbackRowTarget"
                                    rowIndex: _row.index
                                    key: "target"
                                    saved: _row.modelData.target
                                    model: _model.targetChoices
                                    Layout.preferredWidth: Style.dp(160)
                                }
                                Label { text: "Type" }
                                RowPicker {
                                    objectName: "oscFeedbackRowType"
                                    rowIndex: _row.index
                                    key: "type"
                                    saved: _row.modelData.type
                                    model: _model.typeChoices
                                    Layout.preferredWidth: Style.dp(120)
                                }
                                Item { Layout.fillWidth: true }
                            }

                            RowLayout {
                                spacing: Style.dp(6)
                                Layout.fillWidth: true

                                Label { text: "Address" }
                                RowField {
                                    objectName: "oscFeedbackRowAddress"
                                    rowIndex: _row.index
                                    key: "address"
                                    saved: _row.modelData.address
                                    Layout.fillWidth: true
                                }
                                Label { text: "Min:" }
                                RowField {
                                    objectName: "oscFeedbackRowMin"
                                    rowIndex: _row.index
                                    key: "min"
                                    saved: _row.modelData.min
                                    Layout.preferredWidth: Style.dp(60)
                                }
                                Label { text: "Max:" }
                                RowField {
                                    objectName: "oscFeedbackRowMax"
                                    rowIndex: _row.index
                                    key: "max"
                                    saved: _row.modelData.max
                                    Layout.preferredWidth: Style.dp(60)
                                }
                            }

                            // Off/On: when set, an on/off source sends these
                            // instead of Min/Max (e.g. the two template colors).
                            RowLayout {
                                spacing: Style.dp(6)
                                Layout.fillWidth: true

                                Label { text: "Off:" }
                                RowField {
                                    objectName: "oscFeedbackRowOff"
                                    rowIndex: _row.index
                                    key: "off_value"
                                    saved: _row.modelData.offValue
                                    placeholderText: "Min"
                                    Layout.preferredWidth: Style.dp(110)
                                }
                                Label { text: "On:" }
                                RowField {
                                    objectName: "oscFeedbackRowOn"
                                    rowIndex: _row.index
                                    key: "on_value"
                                    saved: _row.modelData.onValue
                                    placeholderText: "Max"
                                    Layout.preferredWidth: Style.dp(110)
                                }
                                Label {
                                    text: "Sent instead of Min/Max for an on/off source; a color (#rrggbb) to a key color goes as r g b."
                                    font.pixelSize: Style.dp(11)
                                    color: Style.fgMuted
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }
        }

        Button {
            objectName: "oscFeedbackAddRow"
            text: "Add Row \u25be"
            onClicked: _addMenu.popup(0, height)

            ThemedMenu {
                id: _addMenu
                objectName: "oscFeedbackAddMenu"
                ThemedMenuItem {
                    objectName: "oscAddBlankRow"
                    text: "Blank row"
                    onTriggered: _model.addTemplateRow("blank", {})
                }
                ThemedMenu {
                    objectName: "oscAddCompanionMenu"
                    title: "Companion"
                    ThemedMenuItem {
                        objectName: "oscAddCompanionVariable"
                        text: "Custom variable\u2026"
                        onTriggered: _template.ask("companion_variable")
                    }
                    ThemedMenuItem {
                        objectName: "oscAddCompanionText"
                        text: "Key text\u2026"
                        onTriggered: _template.ask("companion_text")
                    }
                    ThemedMenuItem {
                        objectName: "oscAddCompanionColour"
                        text: "Key color (off/on)\u2026"
                        onTriggered: _template.ask("companion_colour")
                    }
                }
            }
        }

        MessageLine {
            id: _message
            objectName: "oscFeedbackMessage"
            Layout.fillWidth: true
        }
    }
}
