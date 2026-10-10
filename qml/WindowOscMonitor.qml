// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

// The OSC Monitor's Pop out window (D-09-OSC-MONITOR): the same panel the
// OSC page docks, in its own window. It holds OSC's port open while the
// window is open and releases it on close.
ApplicationWindow {
    id: _win
    font.pixelSize: Style.fontSize
    width: 1000
    height: 600
    minimumWidth: Style.fitWidth(Style.dp(700), Screen)
    minimumHeight: Style.fitHeight(Style.dp(400), Screen)
    title: qsTr("OSC Monitor")
    color: Style.background
    U.Universal.theme: Style.theme

    readonly property alias panel: _panel
    readonly property alias monitor: _panel.monitor
    readonly property alias addWindow: _addDialog

    property bool _open: true

    ToolWindowMemory {
        host: _win
        name: "oscMonitor"
        defaultWidth: Style.dp(1000)
        defaultHeight: Style.dp(600)
    }

    onClosing: _open = false
    onVisibleChanged: if (visible) _open = true

    OscMonitorPanel {
        id: _panel
        anchors.fill: parent
        docked: false
        folded: false
        pageOpen: _win._open && _win.visible

        onAddAsInputRequested: (settings) => {
            _addDialog.openForEdit("", settings)
            _addDialog.lastParameters = settings.values || ""
        }
    }

    OscAddDialog {
        id: _addDialog
        objectName: "oscMonitorAdd"

        deviceModel: OscDeviceManagementModel {}

        onAccepted: (settings) => {
            if (!_panel.editorLocked)
                deviceModel.createConfiguredInput(settings)
        }
    }
}
