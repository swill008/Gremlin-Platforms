// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Profile
import Gremlin.Style

Item {
    id: _root

    property InputItemModel inputItemModel
    // The one edit lock (06 S13): nothing is edited while the profile runs.
    EditLock { id: _lock }
    readonly property bool editorLocked: _lock.locked
    enabled: true
    opacity: editorLocked ? 0.55 : 1.0
    implicitHeight: Style.dp(200)

    // The model always comes from the page (the action panes, the catalog).
    // The Keyboard page uses the shared ActionPane (05 S128).

    ColumnLayout {
        anchors.fill: parent
        spacing: Style.dp(8)

        JGListView {
            Layout.fillHeight: true
            Layout.fillWidth: true
            scrollbarAlwaysVisible: true
            enabled: !editorLocked
            model: _root.inputItemModel
            delegate: _entryDelegate
        }

        Component {
            id: _entryDelegate

            Item {
                height: _binding.height
                width: _binding.width

                required property int index
                required property var modelData
                property ListView view: ListView.view

                InputItemBinding {
                    id: _binding

                    implicitWidth: view.width
                    enabled: !editorLocked

                    inputBinding: modelData
                    inputItemModel: _root.inputItemModel
                }
            }
        }
    }
}
