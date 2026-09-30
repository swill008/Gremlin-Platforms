// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win
    width: 420
    height: 360
    title: "Hidden devices"

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }
    color: Style.background
    U.Universal.theme: Style.theme

    property var moduleModel: null
    property var hiddenRows: []

    function refreshHidden() {
        hiddenRows = moduleModel ? moduleModel.hiddenList() : []
    }

    Component.onCompleted: {
        width = Style.dp(420)
        height = Style.dp(360)
        refreshHidden()
    }

    Connections {
        target: moduleModel
        function onHiddenChanged() { _win.refreshHidden() }
    }

    ListView {
        id: _list
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        anchors.bottomMargin: Style.dp(108)
        model: hiddenRows
        delegate: RowLayout {
            width: ListView.view.width
            Label { text: modelData; Layout.fillWidth: true; color: Style.foreground }
            Button {
                text: "Unhide"
                onClicked: {
                    if (moduleModel)
                        moduleModel.unignoreSlug(modelData)
                    _win.refreshHidden()
                }
            }
        }
    }

    Label {
        anchors.centerIn: parent
        visible: _list.count === 0
        text: "No hidden devices."
        color: "#A1A1AA"
    }

    Button {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin: Style.dp(12)
        anchors.bottomMargin: Style.dp(66)
        text: "Unhide all"
        enabled: _list.count > 0
        onClicked: {
            if (moduleModel)
                moduleModel.unignoreAll()
            refreshHidden()
        }
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
