// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

RoundButton {
    property alias description: _description.text

    contentItem: RowLayout {
        spacing: Style.dp(4)
        anchors.centerIn: parent

        Label {
            Layout.leftMargin: Style.dp(8)
            Layout.alignment: Qt.AlignVCenter
            text: "\uF518"
            font.family: Style.iconFont
        }
        Label {
            id: _description
            Layout.alignment: Qt.AlignBaseline
            Layout.rightMargin: Style.dp(8)
            text: "Rec"
        }
    }
}
