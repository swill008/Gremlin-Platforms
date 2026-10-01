// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQml.Models

import QtQuick.Controls.Universal as U

import Gremlin.ActionPlugins
import Gremlin.Profile
import Gremlin.Style


Item {
    id: _root

    property InputItemBindingModel inputBinding
    property InputItemModel inputItemModel
    property bool hideControlSetup: false
    property bool catalogSequence: false
    property InputItemBindingConfigurationHeader headerWidget: _header
    readonly property string sequenceId: (inputBinding && inputBinding.rootAction)
        ? inputBinding.rootAction.id : ""

    implicitHeight: _content.height

    Connections {
        target: signal

        function onReloadCurrentInputItem()
        {
            // Currently unused
        }
    }


    // Content
    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        // +--------------------------------------------------------------------
        // | Header
        // +--------------------------------------------------------------------
        InputItemBindingConfigurationHeader {
            id: _header

            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(5)
            Layout.rightMargin: Style.dp(20)

            inputBinding: _root.inputBinding
            inputItemModel: _root.inputItemModel
            hideControlSetup: _root.hideControlSetup
            catalogSequence: _root.catalogSequence
        }

        // +--------------------------------------------------------------------
        // | Render the root action node
        // +--------------------------------------------------------------------
        RootActionNode {
            id: _action_node

            Layout.fillWidth: true
            Layout.rightMargin: Style.dp(20)

            action: _root.inputBinding ? _root.inputBinding.rootAction : null
            inputBinding: _root.inputBinding
            inputItemModel: _root.inputItemModel
        }

        HorizontalDivider {
            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(5)
            Layout.rightMargin: Style.dp(20)

            spacing: Style.dp(15)
        }
    }

    DropArea {
        id: _sequenceDrop

        anchors.fill: parent
        keys: ["application/x-gremlin-sequence"]
        property bool placeBefore: true

        onPositionChanged: (drag) => {
            placeBefore = drag.y < height / 2
            _insertLine.y = placeBefore ? 0 : Math.max(0, height - 2)
            _insertLine.visible = drag.getDataAsString("application/x-gremlin-sequence") !== _root.sequenceId
        }
        onExited: _insertLine.visible = false
        onDropped: (drop) => {
            _insertLine.visible = false
            var source = drop.getDataAsString("application/x-gremlin-sequence")
            if (!source || source === _root.sequenceId || !_root.inputItemModel)
                return
            _root.inputItemModel.dropAction(
                source, _root.sequenceId, placeBefore ? "before" : "after"
            )
            drop.accept(Qt.MoveAction)
        }

        Rectangle {
            id: _insertLine

            visible: false
            z: 5
            anchors.left: parent.left
            anchors.right: parent.right
            height: Style.dp(2)
            color: Style.info
        }
    }
}