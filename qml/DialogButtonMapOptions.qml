// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Config
import Gremlin.Style

// The Button Map's own options (Button Map → Edit → Button Map Options…):
// the same rows and cards as the main Options window, for the Button Map's
// settings only. They are not in the main Options window.
ApplicationWindow {
    id: _bmOptions

    font.pixelSize: Style.fontSize
    width: Style.dp(560)
    height: Style.dp(700)
    minimumWidth: Style.dp(440)
    minimumHeight: Style.dp(400)

    U.Universal.theme: Style.theme
    color: Style.background

    title: "Button Map Options"

    ToolWindowMemory {
        host: _bmOptions
        name: "buttonmap-options"
        defaultWidth: Style.dp(560)
        defaultHeight: Math.min(Style.dp(700), Screen.desktopAvailableHeight - 60)
    }

    onClosing: () => {
        backend.emitConfigChanged()
    }

    ConfigSectionModel {
        id: _sectionModel
        scope: "button-map"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Label {
            Layout.leftMargin: Style.dp(20)
            Layout.topMargin: Style.dp(14)
            text: "Button Map Options"
            color: Style.fgStrong
            font.pixelSize: Style.dp(18)
        }

        ConfigSection {
            Layout.fillWidth: true
            Layout.fillHeight: true
            sectionModel: _sectionModel
            currentIndex: 0
        }
    }
}
