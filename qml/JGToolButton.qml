// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ToolButton {
    id: _button

    property alias color: _icon.color
    property alias tooltip: _tooltip.text
    property string caption: ""
    readonly property real sideSlack: Math.max(0, (_face.implicitWidth - _icon.implicitWidth) / 2)

    leftPadding: 10
    rightPadding: 10
    topPadding: 4
    bottomPadding: 4

    implicitWidth: _face.implicitWidth + leftPadding + rightPadding
    implicitHeight: _face.implicitHeight + topPadding + bottomPadding
    Layout.minimumWidth: implicitWidth
    Layout.preferredWidth: implicitWidth

    contentItem: Item {
        id: _face

        implicitWidth: Math.max(_icon.implicitWidth, _caption.visible ? _caption.implicitWidth : 0)
        implicitHeight: _icon.implicitHeight + (_caption.visible ? _caption.implicitHeight + 2 : 0)

        Label {
            id: _icon
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            text: _button.text
            font.family: "bootstrap-icons"
            font.pixelSize: 48
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Label {
            id: _caption
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: _icon.bottom
            anchors.topMargin: 2
            visible: _button.caption.length > 0
            text: _button.caption
            font.pixelSize: 18
            horizontalAlignment: Text.AlignHCenter
        }
    }

    ToolTip {
        id: _tooltip
        visible: _button.hovered
        delay: 500
    }
}
