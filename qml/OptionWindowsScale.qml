// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

Item {
    implicitHeight: _row.implicitHeight
    implicitWidth: Style.dp(420)

    WindowsScaleModel { id: _model }

    RowLayout {
        id: _row
        anchors.fill: parent
        spacing: Style.dp(8)

        CheckBox {
            id: _box
            text: "Disable Windows scaling"
            checked: _model ? _model.disabled : false
            onClicked: if (_model) _model.setDisabled(checked)
        }
    }
}
