// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style


// OSC's Module Setup "Feedback" section (D-09-OSC-FEEDBACK): what Gremlin
// sends back to OSC devices. Each change is checked and written to OSC's
// file at once. It is the Feedback tab's body in OSC Setup (OscSetupTabs).
// The rows are listed read-only here; they are added and edited on the OSC
// page (09 S154). Only the Custom variable template stays (S120).
// It sits straight on its tab's card, as the other tabs do (osc_style.md):
// no card of its own inside it.
Item {
    id: _root
    objectName: "oscFeedbackSection"
    implicitWidth: _column.implicitWidth
    implicitHeight: _column.implicitHeight

    property alias model: _model

    // The text of a {value, text} choice.
    function _choiceText(choices, value) {
        for (var i = 0; choices && i < choices.length; i++)
            if (choices[i].value === value)
                return choices[i].text
        return String(value || "")
    }

    // "Edit on the OSC page": the main window shows the OSC page.
    function openOscPage() {
        if (typeof signal !== "undefined" && signal && signal.openOscPage) {
            signal.openOscPage()
            return true
        }
        return false
    }

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

    // The Custom variable template (S120): asks the variable's name, then
    // adds a row that sends the current mode's name to it.
    Dialog {
        id: _template
        objectName: "oscFeedbackTemplateDialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        title: "Companion custom variable"

        function ask(which) {
            _varName.text = "gremlin_mode"
            open()
        }

        function add() {
            var said = _model.addTemplateRow("companion_variable", { name: _varName.text })
            if (_model.message.length)
                return   // refused: the message line says why; the dialog stays
            close()
            if (said.length)
                _message.show(said, false)
        }

        ColumnLayout {
            spacing: Style.dp(10)

            RowLayout {
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
                text: "Create the custom variable in Companion first."
                font.pixelSize: Style.dp(11)
                color: Style.fgMuted
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

        // The rows, read-only (09 S154): they are added and edited on the
        // OSC page, under their inputs.
        Label {
            objectName: "oscFeedbackNone"
            visible: _rows.count === 0
            text: "No feedback rows. Add them on the OSC page: right-click an input, Add Feedback."
            color: Style.fgMuted
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        ColumnLayout {
            objectName: "oscFeedbackRows"
            visible: _rows.count > 0
            spacing: Style.dp(2)
            Layout.fillWidth: true

            Repeater {
                id: _rows
                model: _model.rows

                delegate: RowLayout {
                    objectName: "oscFeedbackRow"
                    required property var modelData
                    spacing: Style.dp(8)
                    Layout.fillWidth: true
                    Label {
                        text: parent.modelData.enabled ? "On" : "Off"
                        color: parent.modelData.enabled ? Style.okText : Style.fgMuted
                        Layout.preferredWidth: Style.dp(28)
                    }
                    Label {
                        text: parent.modelData.address
                        color: Style.fg
                        font.bold: true
                    }
                    Label {
                        text: _root._choiceText(_model.kindChoices, parent.modelData.kind)
                              + " → " + _root._choiceText(_model.targetChoices, parent.modelData.target)
                        color: Style.fgMuted
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
            }
        }

        RowLayout {
            spacing: Style.dp(8)
            Button {
                objectName: "oscFeedbackEditOnPage"
                text: "Edit on the OSC page"
                onClicked: _root.openOscPage()
            }
            Button {
                objectName: "oscAddCompanionVariable"
                text: "Companion custom variable…"
                onClicked: _template.ask("companion_variable")
                PointerTip {
                    text: "Adds a row that sends the current mode's name to a Companion custom variable."
                    show: parent.hovered
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
