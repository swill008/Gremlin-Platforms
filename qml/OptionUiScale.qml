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
    implicitWidth: Style.dp(480)

    UiScaleModel { id: _model }

    RowLayout {
        id: _row
        anchors.fill: parent
        spacing: Style.dp(10)

        Slider {
            id: _slider
            Layout.fillWidth: true
            enabled: _model ? _model.enabled : false
            from: _model ? _model.minimum : 70
            to: _model ? _model.maximum : 200
            stepSize: 5
            snapMode: Slider.SnapAlways
            value: _model ? _model.scale : 100
            onPressedChanged: {
                if (!pressed)
                    _commit()
            }

            function _commit() {
                if (_model)
                    _model.setScale(Math.round(value))
            }
        }

        Label {
            text: Math.round(_slider.value) + "%"
            enabled: _slider.enabled
            Layout.preferredWidth: Style.dp(48)
            horizontalAlignment: Text.AlignRight
        }
    }
}
