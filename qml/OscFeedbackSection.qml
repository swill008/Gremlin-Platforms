// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

import "confirm.js" as Confirm

// OSC's Module Setup "Feedback" section (D-09-OSC-FEEDBACK): what Gremlin
// sends back to OSC devices. Each change is checked and written to OSC's
// file at once.
Frame {
    id: _root
    objectName: "oscFeedbackSection"

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
        text: saved
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

    ColumnLayout {
        anchors.fill: parent
        spacing: Style.dp(6)

        Label {
            text: "Feedback"
            font.bold: true
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

                    delegate: Frame {
                        id: _row
                        objectName: "oscFeedbackRow"
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true

                        ColumnLayout {
                            anchors.fill: parent
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
                                Button {
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
                        }
                    }
                }
            }
        }

        Button {
            objectName: "oscFeedbackAddRow"
            text: "Add Row"
            onClicked: _model.addRow()
        }

        MessageLine {
            id: _message
            objectName: "oscFeedbackMessage"
            Layout.fillWidth: true
        }
    }
}
