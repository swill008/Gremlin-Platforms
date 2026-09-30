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
    implicitWidth: Style.dp(220)

    HighlightScopeModel {
        id: _model
    }

    RowLayout {
        id: _row

        anchors.fill: parent
        spacing: Style.dp(6)

        Repeater {
            model: ["This tab", "Any device"]

            Button {
                Layout.fillWidth: true
                Layout.preferredWidth: Style.dp(104)
                Layout.minimumWidth: Style.dp(84)

                text: modelData
                checked: _model && _model.scope === modelData
                checkable: true
                onClicked: () => {
                    if (_model) {
                        _model.setScope(modelData)
                    }
                }
            }
        }
    }
}
