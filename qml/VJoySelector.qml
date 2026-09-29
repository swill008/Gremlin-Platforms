// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Base as Base
import Gremlin.Compact as Compact
import Gremlin.Device
import Gremlin.Style


Item {
    id: _root

    property bool useCompact: false
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
        spacing: 10

        Loader {
            id: _deviceLoader

            Layout.minimumWidth: 72
            Layout.fillWidth: true

            sourceComponent: _root.useCompact ? _compactVariant : _baseVariant

            onLoaded: {
                item.width = Qt.binding(() => _deviceLoader.width)
                item.model = Qt.binding(() => _vjoy ? _vjoy.vjoyDevices : [])
                item.popup.contentItem.showScrollBar = false
            }
        }

        Loader {
            id: _inputLoader

            Layout.minimumWidth: 72
            Layout.fillWidth: true

            sourceComponent: _root.useCompact ? _compactVariant : _baseVariant

            onLoaded: {
                item.width = Qt.binding(() => _inputLoader.width)
                item.model = Qt.binding(() => _vjoy ? _vjoy.inputChoices : [])
            }
        }

        HorizontalDivider {}

        Label {
            visible: _vjoy && !_vjoy.hasValidVJoyDevices

            text: "No output modules available."
            color: Style.error
        }

        Label {
            visible: _vjoy && _vjoy.hasValidVJoyDevices && _vjoy.inputChoices.length === 0

            text: "Output module has no claimed controls."
            color: "#A1A1AA"
        }
    }
}
