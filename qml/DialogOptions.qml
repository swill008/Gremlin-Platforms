// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Config
import Gremlin.Style
import "helpers.js" as Helpers

Window {
    id: _options
    width: 1200
    height: 700
    minimumWidth: 1200
    minimumHeight: 600

    Universal.theme: Style.theme
    color: Style.background

    title: "Options"

    ToolWindowMemory {
        host: _options
        name: "options"
        defaultWidth: 1200
        defaultHeight: 700
    }

    property real _appliedScale: 1

    function applyUiScale() {
        var s = Style.uiScale / 100
        if (s < 0.7)
            s = 0.7
        if (s > 2)
            s = 2
        var ratio = s / _appliedScale
        _appliedScale = s
        contentItem.scale = s
        contentItem.transformOrigin = Item.TopLeft
        width = Math.round(width * ratio)
        height = Math.round(height * ratio)
    }

    Connections {
        target: Style
        function onUiScaleChanged() {
            _options.applyUiScale()
        }
    }

    Component.onCompleted: applyUiScale()

    onClosing: () => {
        backend.emitConfigChanged()
    }

    ConfigSectionModel {
        id: _sectionModel
    }

    RowLayout {
        id: _root

        anchors.fill: parent
        anchors.bottomMargin: 58

        // Shows the list of all option sections.
        JGListView {
            id: _sectionSelector

            Layout.preferredWidth: 200
            Layout.fillHeight: true

            model: _sectionModel
            delegate: ConfigSectionButton {}

            Component.onCompleted: () => { currentItem.clicked() }
        }

        // Shows the contents of the currently selected section.
        ConfigSection {
            id: _configSection

            Layout.fillHeight: true
            Layout.fillWidth: true
        }
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
