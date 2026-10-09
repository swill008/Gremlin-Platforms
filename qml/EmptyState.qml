// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// 01 S143 (D-01-SHARED-PIECES): the message an empty list shows, with one
// button for the next step (none when actionText is "").

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

Item {
    id: _root

    property alias text: _text.text
    property string actionText: ""

    signal action()

    implicitWidth: _column.implicitWidth
    implicitHeight: _column.implicitHeight

    ColumnLayout {
        id: _column
        anchors.centerIn: parent
        width: Math.min(implicitWidth, _root.width > 0 ? _root.width : implicitWidth)
        spacing: Style.dp(10)

        Label {
            id: _text
            objectName: "emptyStateText"
            Layout.fillWidth: true
            Layout.maximumWidth: _root.width > 0 ? _root.width : Number.POSITIVE_INFINITY
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            color: Style.fgMuted
        }

        Button {
            objectName: "emptyStateAction"
            Layout.alignment: Qt.AlignHCenter
            visible: _root.actionText.length > 0
            text: _root.actionText
            onClicked: _root.action()
        }
    }
}
