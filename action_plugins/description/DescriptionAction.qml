// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.ActionPlugins
import Gremlin.Profile
import "../../qml"
import Gremlin.Style

Item {
    property DescriptionModel action

    implicitHeight: _content.height

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        Label {
            id: _label

            Layout.preferredWidth: Style.dp(150)

            text: "Description"
        }

        JGTextField {
            id: _description

            Layout.fillWidth: true

            placeholderText: null !== action ? null : "Enter description"
            text: action.description
            selectByMouse: true

            onTextChanged: () => { action.description = text }
        }
    }
}
