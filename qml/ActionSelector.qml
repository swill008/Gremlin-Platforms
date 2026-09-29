// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts

import Gremlin.Profile


Item {
    id: _root

    property ActionModel actionNode
    property var callback: null

    implicitHeight: _content.implicitHeight
    implicitWidth: 200

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

        Button {
            id: _button

            text: "Add Action"

            onClicked: {
                _root.callback(_combobox.currentText)
            }
        }

        ComboBox {
            id: _combobox

            Layout.fillWidth: true
            Layout.minimumWidth: 72
            popup.width: Math.max(width, 240)
        }
    }
}