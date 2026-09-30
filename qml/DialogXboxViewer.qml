// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _xboxViewer

    width: 1200
    height: 800
    minimumWidth: 800
    minimumHeight: 500

    color: Style.background
    Universal.theme: Style.theme

    title: "Xbox Viewer"

    ToolWindowMemory {
        host: _xboxViewer
        name: "xbox-viewer"
        defaultWidth: 1200
        defaultHeight: 800
    }

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }

    readonly property string oscGuid: "a7c3e91b-4d2f-4e18-9b06-2f8c1d5a6e70"

    XboxViewerDeviceModel { id: _devices }

    function pairTitle(guid, name) {
        var key = String(guid || "").toLowerCase().replace(/[{}]/g, "")
        if (key === oscGuid) {
            return "OSC"
        }
        return name && name.length ? name : guid
    }

    Component.onCompleted: () => {
        if (_devices) {
            _devices.reload()
        }
    }

    ScrollView {
        id: _dynamicScroll
        anchors.fill: parent
        anchors.margins: 12
        anchors.bottomMargin: 58

        Component.onCompleted: () => {
            _dynamicScroll.contentItem.boundsMovement = Flickable.StopAtBounds
            _dynamicScroll.contentItem.boundsBehavior = Flickable.StopAtBounds
        }

        ColumnLayout {
            id: _stateDisplay
            width: Math.max(_dynamicScroll.availableWidth, 760)
            spacing: 8

            JGText {
                visible: !_devices || _devices.count === 0
                text: "No Map to Xbox actions on connected devices."
                opacity: 0.65
            }

            Repeater {
                model: _devices
                delegate: Loader {
                    required property string guid
                    required property string name
                    required property string pairLabel

                    Layout.fillWidth: true
                    Layout.preferredHeight: item ? item.implicitHeight : 0
                    sourceComponent: _pairComp

                    property string _guid: guid
                    property string _name: _xboxViewer.pairTitle(guid, name)
                    property string _pair: pairLabel
                }
            }
        }
    }

    Component {
        id: _pairComp
        XboxViewerCard {
            deviceGuid: parent._guid
            title: parent._name
            pairLabel: parent._pair
            width: parent.width
        }
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
