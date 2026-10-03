// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style

// A section in the Options sidebar. The chosen one is highlighted with an
// accent bar. Clicking it shows that section (and clears a search).
AbstractButton {
    id: _button

    required property int index
    required property string name
    required property ConfigGroupModel groupModel

    readonly property bool current: _options.currentSection === index

    Layout.fillWidth: true
    implicitHeight: Style.dp(36)
    hoverEnabled: true

    background: Rectangle {
        radius: Style.dp(6)
        color: _button.current ? Style.bgSelected
            : (_button.hovered ? Style.bgHover : "transparent")

        Rectangle {
            visible: _button.current
            x: Style.dp(4)
            width: Style.dp(3)
            height: Style.dp(18)
            radius: Style.dp(2)
            anchors.verticalCenter: parent.verticalCenter
            color: Style.accent
        }
    }

    contentItem: Label {
        leftPadding: Style.dp(16)
        text: _button.name
        color: _button.current ? Style.fgStrong : Style.fgSoft
        font.pixelSize: Style.dp(14)
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    onClicked: {
        _options.currentSection = index
        _search.text = ""
    }
}
