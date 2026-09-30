// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Style

ColumnLayout {
    id: _root

    property string deviceGuid: ""
    property string title: ""
    spacing: 0

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: _inner.implicitHeight + Style.dp(16)
        color: "#101215"
        border.color: Style.medColor
        border.width: Style.dp(1)
        radius: Style.dp(6)

        RowLayout {
            id: _inner
            width: parent.width - Style.dp(16)
            x: Style.dp(8)
            y: Style.dp(6)
            spacing: Style.dp(8)

            JGText {
                text: title
                opacity: 0.75
                font.pixelSize: Style.dp(16)
            }

            JGText {
                text: "No Map to vJoy"
                opacity: 0.45
                font.pixelSize: Style.dp(13)
            }

            Item { Layout.fillWidth: true }
        }
    }
}
