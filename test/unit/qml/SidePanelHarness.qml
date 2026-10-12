// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls

import Gremlin.Style

import "../../../qml"

// Two side panels round a stand-in map, laid out as the Device Mapping Editor does:
// the map narrows by each panel's takenWidth; a map click folds unpinned
// panels; a strip click folds the other panel if unpinned. For
// side_panel_smoke.py.
ApplicationWindow {
    id: _win
    width: 1000
    height: 600
    visible: true

    property int leftChanged: 0
    property int rightChanged: 0
    property int mapClicks: 0

    Rectangle {
        id: _map
        objectName: "map"
        x: _leftPanel.takenWidth
        width: _win.width - _leftPanel.takenWidth - _rightPanel.takenWidth
        height: _win.height
        color: "#888888"
        MouseArea {
            anchors.fill: parent
            onPressed: {
                _win.mapClicks++
                _leftPanel.foldIfUnpinned()
                _rightPanel.foldIfUnpinned()
            }
        }
    }

    SidePanel {
        id: _leftPanel
        objectName: "leftPanel"
        z: 10
        side: "left"
        title: "Chips"
        pinned: true
        open: false
        panelWidth: 260
        minWidth: 180
        maxWidth: 400
        anchors.left: parent.left
        height: _win.height
        onChanged: _win.leftChanged++
        onStripClicked: _rightPanel.foldIfUnpinned()
        Rectangle { objectName: "leftContent"; anchors.fill: parent; color: "#336699" }
    }

    SidePanel {
        id: _rightPanel
        objectName: "rightPanel"
        z: 10
        side: "right"
        title: "Layers"
        pinned: false
        open: false
        panelWidth: 300
        minWidth: 200
        maxWidth: 450
        anchors.right: parent.right
        height: _win.height
        onChanged: _win.rightChanged++
        onStripClicked: _leftPanel.foldIfUnpinned()
        Rectangle { objectName: "rightContent"; anchors.fill: parent; color: "#996633" }
    }
}
