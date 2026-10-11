// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Base as Base
import Gremlin.Compact as Compact
import Gremlin.Device
import Gremlin.Style


Item {
    id: _root

    property bool useCompact: false
    // The saved binding can't be sent (D-05-CANT-SEND); the tooltip says why.
    readonly property bool cantSend: _vjoy ? _vjoy.currentUnclaimed : false
    readonly property string cantSendText: _vjoy ? _vjoy.currentReason : ""
    property alias validTypes: _vjoy.validTypes

    signal selectionChanged(int deviceId, string inputType, int inputId)

    implicitHeight: _content.height
    implicitWidth: _content.implicitWidth

    function initialize(vjoy_id, input_type, input_id) {
        if (_vjoy) {
            _vjoy.setInitialState(vjoy_id, input_type, input_id)
        }
    }

    function updateState() {
        if (!_vjoy || !_deviceLoader.item || !_inputLoader.item) {
            return
        }
        _vjoy.setState(_deviceLoader.item.currentText, _inputLoader.item.currentText)
    }

    Component { id: _baseVariant;    Base.TooltipComboBox    {} }
    Component { id: _compactVariant; Compact.TooltipComboBox {} }

    OutputModuleDevices {
        id: _vjoy

        onCurrentSelectionChanged: (vjoyId, inputType, inputId) => {
            _root.selectionChanged(vjoyId, inputType, inputId)
        }

        onCurrentValuesChanged: (vjoy_name, input_name) => {
            if (_deviceLoader.item) {
                _deviceLoader.item.currentIndex = _deviceLoader.item.find(vjoy_name)
            }
            if (_inputLoader.item) {
                _inputLoader.item.currentIndex  = _inputLoader.item.find(input_name)
            }
        }
    }

    Connections {
        target: _deviceLoader.item
        function onActivated(index) { updateState() }
    }

    Connections {
        target: _inputLoader.item
        function onActivated(index) { updateState() }
    }

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Style.dp(10)

        Loader {
            id: _deviceLoader

            visible: _vjoy && _vjoy.hasValidVJoyDevices
            Layout.minimumWidth: visible ? Style.dp(72) : 0
            Layout.fillWidth: visible
            Layout.preferredWidth: visible ? -1 : 0

            sourceComponent: _root.useCompact ? _compactVariant : _baseVariant

            onLoaded: {
                item.width = Qt.binding(() => _deviceLoader.width)
                item.model = Qt.binding(() => _vjoy ? _vjoy.vjoyDevices : [])
            }
        }

        Loader {
            id: _inputLoader

            visible: _vjoy && _vjoy.hasValidVJoyDevices && _vjoy.inputChoices.length > 0
            // Never narrower than the shown "⚠ <Control>".
            Layout.minimumWidth: !visible ? 0 : Math.max(Style.dp(72),
                _root.cantSend && item
                ? item.contentItem.contentWidth + item.contentItem.leftPadding
                  + item.contentItem.rightPadding + item.leftPadding + item.rightPadding : 0)
            Layout.fillWidth: visible
            Layout.preferredWidth: visible ? -1 : 0

            sourceComponent: _root.useCompact ? _compactVariant : _baseVariant

            onLoaded: {
                item.width = Qt.binding(() => _inputLoader.width)
                item.model = Qt.binding(() => _vjoy ? _vjoy.inputChoices : [])
                // A binding that can't be sent: "⚠ <Control>" in red, its
                // own tooltip in place of the box's (D-05-CANT-SEND).
                item.enableTooltips = Qt.binding(() => !_root.cantSend)
                if (item.contentItem && item.contentItem.color !== undefined) {
                    const box = item
                    box.contentItem.color = Qt.binding(() =>
                        _root.cantSend ? Style.danger
                        : !box.enabled ? box.U.Universal.chromeDisabledLowColor
                        : box.U.Universal.foreground)
                }
            }

            HoverHandler { id: _cantSendHover }

            Base.WrappingTooltip {
                text: _root.cantSendText
                visible: _root.cantSend && _cantSendHover.hovered
            }
        }

        HorizontalDivider { visible: _vjoy && _vjoy.hasValidVJoyDevices }

        Label {
            visible: _vjoy && !_vjoy.hasValidVJoyDevices
            Layout.fillWidth: true

            text: "No output module claimed"
            color: Style.fgMuted
        }

        Label {
            visible: _vjoy && _vjoy.hasValidVJoyDevices && _vjoy.inputChoices.length === 0

            text: "Output module has no claimed controls."
            color: Style.fgMuted
        }
    }
}
