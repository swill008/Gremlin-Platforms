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

Item {
    id: _root

    property RootModel action

    implicitHeight: _content.height

    // Show all child nodes
    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        ListView {
            model: _root.action.getActions("children")

            delegate: ActionNode {
                Layout.fillWidth: true

                action: modelData
                parentAction: _root.action
                containerName: "children"
            }
        }
    }
}
