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
    implicitWidth: 480

    UiScaleModel { id: _model }

    RowLayout {
        id: _row
        anchors.fill: parent
        spacing: 10

        Slider {
            id: _slider
            Layout.fillWidth: true
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
                var next = Math.round(value)
                if (_model)
                    _model.setScale(next)
                Style.setUiScale(next)
            }
        }

        Label {
            text: Math.round(_slider.value) + "%"
            Layout.preferredWidth: 48
            horizontalAlignment: Text.AlignRight
        }
    }

    Component.onCompleted: Style.setUiScale(_model ? _model.scale : 100)
}
