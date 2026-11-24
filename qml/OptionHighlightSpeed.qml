// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style
import Gremlin.UI

Item {
    id: _root

    implicitHeight: _row.implicitHeight
    implicitWidth: Style.dp(252)

    // Made by ModelFactory (PYSIDE-1407: PySide6 never frees a Python object
    // QML declares); it lives as long as this row.
    readonly property HighlightSpeedModel _model:
        ModelFactory.create("HighlightSpeedModel", _root)

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
