// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Profile
import Gremlin.Style


Item {
    id: _root

    property ActionModel actionNode
    property var callback: null

    implicitHeight: _content.implicitHeight
    // Sized from the text: the widest action name is the preferred width,
    // the chosen name plus Add Action the least it squeezes to.
    implicitWidth: _content.implicitWidth
    Layout.minimumWidth: _combobox.Layout.minimumWidth + _content.spacing + _button.implicitWidth

    Connections {
        target: actionNode

        function onActionChanged() {
            _combobox.model = actionNode.compatibleActions
        }
    }

    onActionNodeChanged: {
        _combobox.model = actionNode.compatibleActions
    }

    RowLayout {
        id: _content

        anchors.fill: parent

        // Pick the action, then add it (reads left to right).
        ComboBox {
            id: _combobox

            Layout.fillWidth: true
            Layout.minimumWidth: Math.ceil(_current.advanceWidth) + leftPadding + rightPadding
                + (contentItem ? contentItem.leftPadding + contentItem.rightPadding : 0) + Style.dp(2)
            implicitContentWidthPolicy: ComboBox.WidestText
            popup.width: Math.max(width, Style.dp(240))

            TextMetrics {
                id: _current
                font: _combobox.font
                text: _combobox.currentText
            }
        }

        Button {
            id: _button

            text: "Add Action"
            // Nothing to add when no action fits here.
            enabled: _combobox.count > 0 && _combobox.currentText.length > 0

            onClicked: {
                if (_combobox.currentText.length)
                    _root.callback(_combobox.currentText)
            }
        }
    }
}