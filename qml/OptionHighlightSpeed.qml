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
    implicitWidth: Style.dp(252)

    HighlightSpeedModel {
        id: _model
    }

    RowLayout {
        id: _row

        anchors.fill: parent
        spacing: Style.dp(6)

        Repeater {
            model: ["Slow", "Medium", "Fast"]

            Button {
                Layout.fillWidth: true
                Layout.preferredWidth: Style.dp(80)
                Layout.minimumWidth: Style.dp(64)

                text: modelData
                checked: _model && _model.speed === modelData
                checkable: true
                onClicked: () => {
                    if (_model) {
                        _model.setSpeed(modelData)
                    }
                }
            }
        }
    }
}
