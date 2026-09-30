// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.ActionPlugins
import Gremlin.Profile

Item {
    id: _root

    // Data to render
    property RootModel action
    property bool compactMode: false
    property var inputItemModel
    property var inputBinding

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        Rectangle {
            id: _topRule

            Layout.fillWidth: true
            height: 0
            color: "transparent"
        }

        Repeater {
            model: _root.action ? _root.action.getActions("children") : []

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "children"
                compactMode: _root.compactMode
                inputItemModel: _root.inputItemModel
                inputBinding: _root.inputBinding

                Layout.fillWidth: true
            }
        }
    }

    ActionDragDropArea {
        target: _topRule
        dropCallback: function(drop) {
            action.dropAction(drop.text, action.sequenceIndex, "append");
        }
    }

}
