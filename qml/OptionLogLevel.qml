// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

Item {
    id: _root

    implicitHeight: _row.implicitHeight
    implicitWidth: Style.dp(420)

    LogLevelModel {
        id: _model
    }

    RowLayout {
        id: _row

        anchors.fill: parent
        spacing: Style.dp(6)

        Repeater {
            model: ["Off", "ALL", "Info", "Warning", "Error"]

            Button {
                Layout.fillWidth: true
                Layout.preferredWidth: Style.dp(78)
                Layout.minimumWidth: Style.dp(64)

                text: modelData
                ToolTip.visible: hovered && modelData === "Off"
                ToolTip.text: "Nothing is written, except errors in system.log."
                checked: _model && _model.level === modelData
                checkable: true
                onClicked: () => {
                    if (_model) {
                        _model.setLevel(modelData)
                    }
                }
            }
        }
    }
}
