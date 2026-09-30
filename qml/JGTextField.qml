// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U

import Gremlin.Style

TextField {
    id: _control

    color: Style.foreground
    property var outlineOverride: null

    background: Rectangle {
        anchors.fill: parent
        border.color: _control.outlineOverride !== null ? _control.outlineOverride : (_control.activeFocus ? Style.accent : Style.lowColor)
        border.width: Style.dp(1)
        color: readOnly ? Style.lowColor : Style.background
    }
}
