// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// One Feedback row's editor, shown in the OSC page's action pane (09 S153,
// S155): source, target, address, Min/Max, type, off/on values and where the
// row is shown. It edits the model's draft (OscLayoutModel.feedbackEditor);
// the pane's OK writes it as one page Undo step. Stays editable while a
// profile runs.
Item {
    id: _root
    objectName: "oscFeedbackEditor"

    property var layout: null
    readonly property var draft: layout ? layout.feedbackEditor : ({})
    readonly property var choices: draft && draft.choices ? draft.choices : ({})
    readonly property string kind: draft && draft.kind ? String(draft.kind) : ""

    implicitHeight: _column.implicitHeight

    function _set(name, value) {
        if (layout)
            layout.setFeedbackField(name, value)
    }

    // A picker for one draft field; choices are {value, text}.
    component FieldPicker: ComboBox {
        property string field: ""
        property var saved
        textRole: "text"
        valueRole: "value"
        function _sync() { currentIndex = indexOfValue(saved) }
        Component.onCompleted: _sync()
        onSavedChanged: _sync()
        onModelChanged: _sync()
        onActivated: _root._set(field, currentValue)
    }

    // A text box for one draft field, sent when typing ends.
    component FieldText: JGTextField {
        property string field: ""
        property string saved: ""
        text: saved
        selectByMouse: true
        onEditingFinished: if (text !== saved) _root._set(field, text)
    }

    ColumnLayout {
        id: _column
        anchors { left: parent.left; right: parent.right; top: parent.top }
        spacing: Style.dp(8)

        Label {
            objectName: "oscFeedbackNote"
            visible: !!_root.draft.note
            text: _root.draft.note || ""
            color: Style.warn
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        CheckBox {
            objectName: "oscFeedbackOn"
            text: "Send this feedback"
            checked: !!_root.draft.enabled
            onClicked: _root._set("enabled", checked)
        }

        GridLayout {
            columns: 2
            columnSpacing: Style.dp(8)
            rowSpacing: Style.dp(6)
            Layout.fillWidth: true

            Label { text: "Source"; color: Style.fgSoft }
            RowLayout {
                spacing: Style.dp(6)
                Layout.fillWidth: true
                FieldPicker {
                    objectName: "oscFeedbackKind"
                    field: "kind"
                    saved: _root.kind
                    model: _root.choices.kinds || []
                    Layout.preferredWidth: Style.dp(190)
                }
                FieldPicker {
                    objectName: "oscFeedbackVjoy"
                    visible: _root.kind === "vjoy_button" || _root.kind === "vjoy_axis"
                    field: "device"
                    saved: _root.draft.device
                    model: _root.choices.vjoy || []
                    Layout.preferredWidth: Style.dp(100)
                }
                FieldText {
                    objectName: "oscFeedbackNumber"
                    visible: _root.kind === "vjoy_button" || _root.kind === "vjoy_axis"
                    field: "input"
                    saved: _root.draft.input !== undefined ? String(_root.draft.input) : ""
                    placeholderText: _root.kind === "vjoy_axis" ? "Axis" : "Button"
                    inputMethodHints: Qt.ImhDigitsOnly
                    Layout.preferredWidth: Style.dp(70)
                }
                FieldPicker {
                    objectName: "oscFeedbackLogical"
                    visible: _root.kind === "logical"
                    field: "input"
                    saved: _root.draft.input
                    model: _root.choices.logical || []
                    displayText: currentIndex < 0 ? "Pick a control" : currentText
                    Layout.fillWidth: true
                }
                FieldPicker {
                    objectName: "oscFeedbackOsc"
                    visible: _root.kind === "osc_input"
                    field: "input"
                    saved: _root.draft.input
                    model: _root.choices.osc || []
                    displayText: currentIndex < 0 ? "Pick an OSC input" : currentText
                    Layout.fillWidth: true
                }
                FieldPicker {
                    objectName: "oscFeedbackAction"
                    visible: _root.kind === "action_state"
                    field: "action"
                    saved: _root.draft.action
                    model: _root.choices.actions || []
                    displayText: currentIndex < 0
                        ? (count > 0 ? "Pick an action" : "No Smart Toggle or Tempo in this profile")
                        : currentText
                    Layout.fillWidth: true
                }
                Item {
                    visible: _root.kind === "mode" || _root.kind === "paused"
                    Layout.fillWidth: true
                }
            }

            Label { text: "Send to"; color: Style.fgSoft }
            RowLayout {
                spacing: Style.dp(6)
                Layout.fillWidth: true
                FieldPicker {
                    objectName: "oscFeedbackTarget"
                    field: "target"
                    saved: _root.draft.target
                    model: _root.choices.targets || []
                    Layout.preferredWidth: Style.dp(190)
                }
                Label { text: "Type"; color: Style.fgSoft }
                FieldPicker {
                    objectName: "oscFeedbackType"
                    field: "type"
                    saved: _root.draft.type
                    model: _root.choices.types || []
                    Layout.preferredWidth: Style.dp(120)
                }
                Item { Layout.fillWidth: true }
            }

            Label { text: "Address"; color: Style.fgSoft }
            FieldText {
                objectName: "oscFeedbackAddress"
                field: "address"
                saved: _root.draft.address || ""
                placeholderText: "/address"
                Layout.fillWidth: true
            }

            Label { text: "Min"; color: Style.fgSoft }
            RowLayout {
                spacing: Style.dp(6)
                FieldText {
                    objectName: "oscFeedbackMin"
                    field: "min"
                    saved: _root.draft.min || ""
                    Layout.preferredWidth: Style.dp(70)
                }
                Label { text: "Max"; color: Style.fgSoft }
                FieldText {
                    objectName: "oscFeedbackMax"
                    field: "max"
                    saved: _root.draft.max || ""
                    Layout.preferredWidth: Style.dp(70)
                }
            }

            Label { text: "Off"; color: Style.fgSoft }
            RowLayout {
                spacing: Style.dp(6)
                FieldText {
                    objectName: "oscFeedbackOff"
                    field: "offValue"
                    saved: _root.draft.offValue || ""
                    placeholderText: "Min"
                    Layout.preferredWidth: Style.dp(110)
                }
                Label { text: "On"; color: Style.fgSoft }
                FieldText {
                    objectName: "oscFeedbackOnValue"
                    field: "onValue"
                    saved: _root.draft.onValue || ""
                    placeholderText: "Max"
                    Layout.preferredWidth: Style.dp(110)
                }
            }

            Item { implicitWidth: 1 }
            Label {
                text: "Off and On are sent instead of Min and Max for an on/off source; a color (#rrggbb) to a key color goes as r g b."
                font.pixelSize: Style.dp(11)
                color: Style.fgMuted
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label { text: "Show under this input"; color: Style.fgSoft }
            FieldPicker {
                objectName: "oscFeedbackShowUnder"
                field: "showUnder"
                saved: _root.draft.showUnder || ""
                model: _root.choices.showUnder || []
                Layout.fillWidth: true
            }
        }

        Label {
            objectName: "oscFeedbackError"
            visible: !!_root.draft.error
            text: _root.draft.error || ""
            color: Style.dangerText
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}
