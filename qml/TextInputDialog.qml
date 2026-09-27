// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts

import Gremlin.Style

Popup {
    id: _root

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: 10
    width: 320
    height: heading.length > 0 ? 86 : 56

    signal accepted(string value)
    property string text : "New text"
    property string heading: ""
    property string lastAccepted: ""
    property var validator: function(value) { return true }
    property bool clearOnClick: true
    property bool _clearedOnClick: false
    property bool _committed: false

    function seedText() {
        if (_root.text && _root.text.length > 0) {
            return _root.text
        }
        return lastAccepted
    }

    background: Rectangle {
        color: Style.background
        border.color: Style.accent
        border.width: 1
        radius: 4
    }

    onOpened: {
        _committed = false
        _clearedOnClick = false
        _input.text = seedText()
        _input.forceActiveFocus()
        if (!clearOnClick) {
            _input.selectAll()
        }
    }

    onTextChanged: {
        if (opened) {
            _clearedOnClick = false
            _input.text = seedText()
        }
    }

    contentItem: ColumnLayout {
        spacing: 6

        Label {
            visible: _root.heading.length > 0
            text: _root.heading
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

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

                Keys.onReturnPressed: _button.click()
                Keys.onEnterPressed: _button.click()

                onTextEdited: () => {
                    let isValid = _root.validator(text)
                    _input.outlineOverride = isValid ? null : Style.error
                    _button.enabled = isValid
                }
            }

            Button {
                id: _button

                text: "Ok"

                onClicked: () => {
                    _root.lastAccepted = _input.text
                    _root._committed = true
                    _root.accepted(_input.text)
                    _root.close()
                }
            }
        }
    }
}
