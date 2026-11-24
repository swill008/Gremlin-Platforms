// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Base as Base
import Gremlin.Compact as Compact
import Gremlin.Device
import Gremlin.Style
import Gremlin.UI


Item {
    id: _root

    property bool useCompact: false
    property string logicalInputType

    // Passed to the model by hand, valid types before the identifier (the
    // model finds the identifier among the inputs of those types). The
    // user's pick comes out as logicalInputSelected; the selector never
    // writes logicalInputIdentifier, so an outside binding to it stays.
    property var logicalInputIdentifier: null
    property var validTypes: []

    signal logicalInputSelected(InputIdentifier identifier)

    implicitHeight: _content.height
    implicitWidth: _content.implicitWidth

    Component { id: _baseVariant;    Base.TooltipComboBox    {} }
    Component { id: _compactVariant; Compact.TooltipComboBox {} }

    // Made by ModelFactory (PySide6 never frees QML-made Python objects,
    // PYSIDE-1407); freed with this item.
    readonly property LogicalDeviceSelectorModel _model:
        ModelFactory.create("LogicalDeviceSelectorModel", _root, {})

    property bool _ready: false
    function _passTypes() {
        if (_model)
            _model.validTypes = validTypes
    }
    function _passIdentifier() {
        if (_ready && _model && logicalInputIdentifier)
            _model.currentIdentifier = logicalInputIdentifier
    }
    Component.onCompleted: {
        _passTypes()
        _ready = true
        _passIdentifier()
    }
    onValidTypesChanged: _passTypes()
    onLogicalInputIdentifierChanged: _passIdentifier()

    Connections {
        target: _model
        function onSelectionChanged() {
            _root.logicalInputSelected(_root._model.currentIdentifier)
        }
    }

    Connections {
        target: _loader.item

        function onActivated(index) {
            if (_model.currentIndex !== index) {
                _model.currentIndex = index
            }
        }
    }

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        Loader {
            id: _loader

            Layout.minimumWidth: Style.dp(200)
            Layout.fillWidth: true

            sourceComponent: _root.useCompact ? _compactVariant : _baseVariant

            onLoaded: {
                item.width        = Qt.binding(() => _loader.width)
                item.model        = Qt.binding(() => _model)
                item.textRole     = "label"
                item.currentIndex = Qt.binding(() => _model.currentIndex)
            }
        }
    }

}
