// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

ToolButton {
    id: _button

    property alias color: _icon.color
    property alias tooltip: _tooltip.text
    property string caption: ""
    // Icon only (the caption is hidden): the main window sets it when the
    // toolbar would not fit with captions. The tooltip still names it.
    property bool compact: false
    // The width with its caption, whether or not the caption is shown.
    readonly property real fullWidth: Math.max(_icon.implicitWidth, _caption.implicitWidth)
                                      + leftPadding + rightPadding
    // The width with the icon only.
    readonly property real compactWidth: _icon.implicitWidth + leftPadding + rightPadding
    readonly property real sideSlack: Math.max(0, (_face.implicitWidth - _icon.implicitWidth) / 2)

    leftPadding: Style.dp(10)
    rightPadding: Style.dp(10)
    topPadding: Style.dp(4)
    bottomPadding: Style.dp(4)

    implicitWidth: _face.implicitWidth + leftPadding + rightPadding
    implicitHeight: _face.implicitHeight + topPadding + bottomPadding
    Layout.minimumWidth: implicitWidth
    Layout.preferredWidth: implicitWidth

    contentItem: Item {
        id: _face

        implicitWidth: Math.max(_icon.implicitWidth, _caption.visible ? _caption.implicitWidth : 0)
        implicitHeight: _icon.implicitHeight + (_caption.visible ? _caption.implicitHeight + Style.dp(2) : 0)

        Label {
            id: _icon
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            text: _button.text
            font.family: "bootstrap-icons"
            font.pixelSize: Style.dp(48)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        Label {
            id: _caption
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: _icon.bottom
            anchors.topMargin: Style.dp(2)
            visible: _button.caption.length > 0 && !_button.compact
            text: _button.caption
            font.pixelSize: Style.dp(18)
            horizontalAlignment: Text.AlignHCenter
        }
    }

    HoverHandler {
        id: _tipHover
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    }

    ToolTip {
        id: _tooltip
        visible: _tipHover.hovered && text.length > 0
        delay: 500
        x: _tipHover.point.position.x - width / 2
        y: _tipHover.point.position.y - height - Style.dp(8)
    }
}
