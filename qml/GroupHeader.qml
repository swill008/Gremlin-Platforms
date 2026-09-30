// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style

Item {
    id: _root

    property string title

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Label {
                text: title
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter

                height: Style.dp(2)
                color: Style.lowColor
            }
        }

    }
}
