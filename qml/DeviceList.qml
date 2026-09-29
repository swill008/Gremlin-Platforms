// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal

import Gremlin.Device
import Gremlin.Profile

Item {
    id: _root

    property DeviceListModel deviceListModel
    property int _nameTick: 0
    property int _vjoyTick: 0

    DeviceNames {
        id: _names

        onChanged: _root._nameTick++
    }

    VJoyStatus {
        id: _vjoy

        onChanged: _root._vjoyTick++
    }

    TextInputDialog {
        id: _renameDialog

        visible: false
        width: 320
        clearOnClick: false

        property string nameKey: ""
        property string fallback: ""

        onAccepted: (value) => {
            _names.setAlias(nameKey, value)
            visible = false
        }
    }

    function rename(key, fallback) {
        if (!_names) {
            return
        }
        _renameDialog.nameKey = key
        _renameDialog.fallback = fallback
        _renameDialog.text = _names.display(key, fallback)
        _renameDialog.visible = true
    }

    function nextTab() {
        _deviceList.itemAt(_deviceList.currentIndex + 1)?.clicked()
    }

    function previousTab() {
        _deviceList.itemAt(_deviceList.currentIndex - 1)?.clicked()
    }

    function isVjoyTab(deviceName, vjoyId) {
        var label = String(deviceName || "").toLowerCase()
        return label.indexOf("vjoy") === 0 || Number(vjoyId) > 0
    }

    function showDeviceTab(deviceName, vjoyId) {
        if (!_root.isVjoyTab(deviceName, vjoyId)) {
            return true
        }
        return !!(_vjoy && _vjoy.isPinned(Number(vjoyId)))
    }

    function extraVisible(key) {
        return !!(_vjoy && _vjoy.isExtraPinned(key))
    }

    function displayName(key, fallback) {
        if (!_names) {
            return fallback
        }
        return _root._nameTick, _names.display(key, fallback)
    }

    function isRenamed(key, fallback) {
        return _root.displayName(key, fallback) !== fallback
    }

    DeviceTabBar {
        id: _deviceList

        anchors.fill: parent

        Repeater {
            id: _physicalInputs
            model: deviceListModel

            JGTabButton {
                id: _button

                visible: _root._vjoyTick >= 0 && _root.showDeviceTab(name, vjoy_id)
                text: _root.displayName(model.guid, name)
                width: visible ? _metric.width + 50 : 0
                checked: uiState && uiState.currentTab === "physical" &&
                    uiState.currentDevice === model.guid

                PointerTip {
                    text: name
                    delay: 400
                    show: visible && _root.isRenamed(model.guid, name)
                }

                onClicked: () => {
                    if (!uiState) {
                        return
                    }
                    uiState.setCurrentTab("physical")
                    uiState.setCurrentDevice(model.guid)
                }

                TapHandler {
                    onDoubleTapped: {
                        if (visible) {
                            _root.rename(model.guid, name)
                        }
                    }
                }

                TextMetrics {
                    id: _metric

                    font: _button.font
                    text: _button.text
                }
            }
        }

        JGTabButton {
            id: _keyboardButton

            visible: _root._vjoyTick >= 0 && _root.extraVisible("keyboard")
            text: _root.displayName("keyboard", "Keyboard")
            width: visible ? _metricKeyboard.width + 50 : 0
            checked: uiState && uiState.currentTab === "keyboard"

            PointerTip {
                text: "Keyboard"
                delay: 400
                show: visible && _root.isRenamed("keyboard", "Keyboard")
            }

            onClicked: () => {
                if (!uiState) {
                    return
                }
                uiState.setCurrentTab("keyboard")
                uiState.setCurrentDevice("6f1d2b61-d5a0-11cf-bfc7-444553540000")
            }

            TapHandler {
                onDoubleTapped: {
                    if (visible) {
                        _root.rename("keyboard", "Keyboard")
                    }
                }
            }

            TextMetrics {
                id: _metricKeyboard

                font: _keyboardButton.font
                text: _keyboardButton.text
            }
        }

        JGTabButton {
            id: _logicalButton

            visible: _root._vjoyTick >= 0 && _root.extraVisible("logical")
            text: _root.displayName("logical", "Logical Device")
            width: visible ? _metricIO.width + 50 : 0
            checked: uiState && uiState.currentTab === "logical"

            PointerTip {
                text: "Logical Device"
                delay: 400
                show: visible && _root.isRenamed("logical", "Logical Device")
            }

            onClicked: () => {
                if (!uiState) {
                    return
                }
                uiState.setCurrentTab("logical")
                uiState.setCurrentDevice("f0af472f-8e17-493b-a1eb-7333ee8543f2")
            }

            TapHandler {
                onDoubleTapped: {
                    if (visible) {
                        _root.rename("logical", "Logical Device")
                    }
                }
            }

            TextMetrics {
                id: _metricIO

                font: _logicalButton.font
                text: _logicalButton.text
            }
        }

        JGTabButton {
            id: _oscButton

            visible: _root._vjoyTick >= 0 && _root.extraVisible("osc")
            text: _root.displayName("osc", "OSC")
            width: visible ? _metricOsc.width + 50 : 0
            checked: uiState && uiState.currentTab === "osc"

            PointerTip {
                text: "OSC"
                delay: 400
                show: visible && _root.isRenamed("osc", "OSC")
            }

            onClicked: () => {
                if (!uiState) {
                    return
                }
                uiState.setCurrentTab("osc")
                uiState.setCurrentDevice("a7c3e91b-4d2f-4e18-9b06-2f8c1d5a6e70")
            }

            TapHandler {
                onDoubleTapped: {
                    if (visible) {
                        _root.rename("osc", "OSC")
                    }
                }
            }

            TextMetrics {
                id: _metricOsc

                font: _oscButton.font
                text: _oscButton.text
            }
        }

        JGTabButton {
            id: _xboxButton

            visible: _root._vjoyTick >= 0 && _root.extraVisible("xbox")
            text: _root.displayName("xbox", "Xbox 360 Controller")
            width: visible ? _metricXbox.width + 50 : 0
            checked: uiState && uiState.currentTab === "xbox"

            PointerTip {
                text: "Xbox 360 Controller"
                delay: 400
                show: visible && _root.isRenamed("xbox", "Xbox 360 Controller")
            }

            onClicked: () => {
                if (!uiState) {
                    return
                }
                uiState.setCurrentTab("xbox")
                uiState.setCurrentDevice("c8e4b6a1-3d92-4f17-9a50-7b2c4e8f1d60")
            }

            TapHandler {
                onDoubleTapped: {
                    if (visible) {
                        _root.rename("xbox", "Xbox 360 Controller")
                    }
                }
            }

            TextMetrics {
                id: _metricXbox

                font: _xboxButton.font
                text: _xboxButton.text
            }
        }
    }
}
