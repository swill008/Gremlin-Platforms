// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Style

Popup {
    id: _root

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Style.dp(10)
    width: Style.dp(320)
    height: (heading.length > 0 ? Style.dp(86) : Style.dp(56)) + (showOption ? Style.dp(28) : 0)

    signal accepted(string value)
    property string text : "New text"
    property string heading: ""
    property string lastAccepted: ""
    property var validator: function(value) { return true }
    // A blank value is accepted where it means something (a device alias:
    // back to the device's own name); names that must exist turn it off.
    property bool allowBlank: true
    // Off: the name opens selected, so typing replaces it and a click
    // only places the cursor (it used to wipe the name).
    property bool clearOnClick: false
    property bool _clearedOnClick: false
    property bool _committed: false
    property bool showOption: false
    property string optionText: ""
    property bool optionChecked: false

    // OK is only offered for a usable value: passing the validator, and
    // not blank unless allowBlank. Checked whenever the text or the rule changes, not only
    // while typing, so a seeded or cleared name is checked too.
    function _check() {
        var value = _input.text
        var ok = (_root.allowBlank || value.trim().length > 0) && !!_root.validator(value)
        _input.outlineOverride = ok ? null : Style.error
        _button.enabled = ok
        return ok
    }

    function _accept() {
        if (!_check())
            return
        _root.lastAccepted = _input.text
        _root._committed = true
        _root.accepted(_input.text)
        _root.close()
    }

    onValidatorChanged: if (opened) _check()

    function seedText() {
        if (_root.text && _root.text.length > 0) {
            return _root.text
        }
        return lastAccepted
    }

    background: Rectangle {
        color: Style.background
        border.color: Style.accent
        border.width: Style.dp(1)
        radius: Style.dp(4)
    }

    onOpened: {
        _committed = false
        _clearedOnClick = false
        _input.text = seedText()
        _option.checked = optionChecked
        _input.forceActiveFocus()
        if (!clearOnClick) {
            _input.selectAll()
        }
        _check()
    }

    onTextChanged: {
        if (opened) {
            _clearedOnClick = false
            _input.text = seedText()
        }
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(6)

        Label {
            visible: _root.heading.length > 0
            text: _root.heading
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)

            JGTextField {
                id: _input

                Layout.fillWidth: true
                focus: true

                TapHandler {
                    onTapped: {
                        if (_root.clearOnClick && !_root._clearedOnClick) {
                            _input.text = ""
                            _root._clearedOnClick = true
                            _input.forceActiveFocus()
                        }
                    }
                }

                Keys.onReturnPressed: _root._accept()
                Keys.onEnterPressed: _root._accept()

                onTextChanged: if (_root.opened) _root._check()
            }

            Button {
                id: _button

                text: "Ok"

                onClicked: _root._accept()
            }
        }

        CheckBox {
            id: _option
            visible: _root.showOption
            text: _root.optionText
            Layout.fillWidth: true
            onClicked: _root.optionChecked = checked
        }
    }
}
