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
    id: _inputViewer

    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1200
    height: 800
    minimumWidth: Style.dp(800)
    minimumHeight: Style.dp(500)

    color: Style.background
    U.Universal.theme: Style.theme

    title: "vJoy Viewer"

    ToolWindowMemory {
        host: _inputViewer
        name: "vjoy-viewer"
        defaultWidth: Style.dp(1200)
        defaultHeight: Style.dp(800)
    }

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }

    ModulePairDeviceModel { id: _devices }

    Component.onCompleted: () => {
        if (_devices)
            _devices.reload()
    }

    ScrollView {
        id: _dynamicScroll
        anchors.fill: parent
        anchors.margins: Style.dp(12)

        Component.onCompleted: () => {
            _dynamicScroll.contentItem.boundsMovement = Flickable.StopAtBounds
            _dynamicScroll.contentItem.boundsBehavior = Flickable.StopAtBounds
        }

        ColumnLayout {
            id: _stateDisplay
            width: Math.max(_dynamicScroll.availableWidth, Style.dp(760))
            spacing: Style.dp(8)

            JGText {
                visible: _devices.count === 0
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                opacity: 0.65
                text: "No input module sends to a vJoy output yet. Save an input module and add Map to vJoy actions in Configuration."
            }

            Repeater {
                model: _devices
                delegate: Loader {
                    required property string guid
                    required property string name
                    required property string pairLabel
                    required property string deviceName
                    required property bool destEmpty

                    Layout.fillWidth: true
                    Layout.preferredHeight: item ? item.implicitHeight : 0
                    sourceComponent: _pairComp

                    property string _guid: guid
                    property string _name: name
                    property string _pair: pairLabel
                    property string _deviceName: deviceName
                    property bool _destEmpty: destEmpty
                }
            }
        }
    }

    Component {
        id: _pairComp
        InputViewerCard {
            deviceGuid: parent._guid
            deviceName: parent._deviceName
            title: parent._name
            pairLabel: parent._pair
            destEmpty: parent._destEmpty
            width: parent.width
        }
    }
}
