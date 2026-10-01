// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Config
import Gremlin.Device
import Gremlin.Style

Item {
    id: _root

    property Device device
    property var moduleModel: null
    property string claimDeviceName: ""
    property bool isOutput: false
    readonly property bool outputLive: isOutput || /^vJoy\s/i.test(claimDeviceName)
    readonly property bool editorLocked: backend && backend.gremlinActive && !outputLive
    readonly property bool runtimeActive: !!(backend && backend.gremlinActive)
    readonly property int claimedCount: _claimed.count

    enabled: true
    opacity: editorLocked ? 0.55 : 1.0

    ModuleClaimedInputModel {
        id: _claimed
        guid: device ? device.guid : ""
        deviceName: _root.claimDeviceName
    }

    Connections {
        target: moduleModel
        function onClaimsChanged() { _claimed.reload() }
    }

    Connections {
        target: uiState
        function onModeChanged() {
            if (uiState)
                _claimed.setMode(uiState.currentMode)
        }
    }

    Component.onCompleted: {
        if (uiState)
            _claimed.setMode(uiState.currentMode)
    }

    DeviceLiveState {
        id: _liveState
        guid: device ? device.guid : ""
        deviceName: _root.claimDeviceName
        locked: editorLocked
        liveWhileActive: outputLive
    }

    HighlightSpeedModel {
        id: _highlightSpeed
    }

    ActionNames { id: _actionNames }

    TextInputDialog {
        id: _renameDialog

        visible: false
        width: Style.dp(320)

        property int rowIndex: -1

        onAccepted: (value) => {
            if (editorLocked) {
                return
            }
            _actionNames.setOnModel(device, rowIndex, value)
            visible = false
        }
    }

    function showHid(hid) {
        if (editorLocked || hid < 0) {
            return
        }
        let row = _claimed.rowForDeviceIndex(hid)
        if (row < 0) {
            return
        }
        if (_inputList.currentIndex !== row) {
            _inputList.currentIndex = row
        }
        var win = Window.window
        if (win && win.deferListScroll)
            win.deferListScroll(_root, row)
        else
            scrollRowNow(row)
    }

    function scrollRowNow(row) {
        if (row < 0)
            return
        _inputList.positionViewAtIndex(row, ListView.Contain)
    }

    Connections {
        target: uiState

        function onDeviceChanged() {
            if (!uiState || editorLocked) {
                return
            }
            showHid(uiState.currentInputIndex)
        }
    }

    Connections {
        target: signal

        function onSetInputIndex(index) {
            showHid(index)
        }
    }

    JGListView {
        id: _inputList

        anchors.fill: parent
        anchors.leftMargin: Style.dp(10)

        scrollbarAlwaysVisible: true
        spacing: Style.dp(5)
        highlightFollowsCurrentItem: true
        highlightMoveVelocity: -1
        highlightMoveDuration: {
            if (!_highlightSpeed) {
                return 150
            }
            if (_highlightSpeed.speed === "Fast") {
                return 0
            }
            if (_highlightSpeed.speed === "Medium") {
                return 70
            }
            return 150
        }
        highlightResizeDuration: highlightMoveDuration

        model: _claimed

        delegate: InputButton {
            width: _inputList.width - Style.dp(20)
            height: Style.dp(50)
            enabled: !editorLocked

            liveIndex: model.deviceIndex
            liveState: (editorLocked && !outputLive) ? null : _liveState
            runtimeActive: _root.runtimeActive
            selected: model.index === _inputList.currentIndex
            onClicked: () => {
                if (!editorLocked) {
                    _inputList.currentIndex = model.index
                }
            }
            onRenameRequested: {
                if (editorLocked) {
                    return
                }
                _renameDialog.rowIndex = model.deviceIndex
                let current = _actionNames.getOnModel(device, model.deviceIndex)
                _renameDialog.text = current.length ? current : ""
                _renameDialog.visible = true
            }
        }

        footer: Item {
            width: ListView.view.width
            height: Style.dp(10)
        }

        function syncSelection() {
            if (!uiState || !device || currentIndex < 0 || editorLocked) {
                return
            }
            var hid = _claimed.deviceIndexAt(currentIndex)
            if (hid < 0) {
                return
            }
            var ident = device.inputIdentifier(hid)
            if (!ident) {
                return
            }
            uiState.setCurrentInput(ident, hid)
        }

        Component.onCompleted: syncSelection()
        onCurrentIndexChanged: syncSelection()
    }

    Label {
        anchors.centerIn: parent
        width: parent.width - Style.dp(32)
        visible: claimedCount === 0
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        color: Style.fgMuted
        text: outputLive
              ? "This list is the output module's claimed controls.\nWhen Gremlin is Active, axes and buttons follow the vJoy feeder, not HID."
              : "This window only shows what the input module passes.\nRight-click the card → Configure input module, press the controls to claim, then Save module."
    }
}
