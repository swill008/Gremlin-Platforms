// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Profile
import Gremlin.Style


Item {
    id: _root

    property ActionModel actionNode
    property var callback: null
    // Text shown before the picker (e.g. "Short press"). The picker sits at
    // the right; when the row is too narrow for both, the label wraps down
    // to labelMinimumWidth, then the picker moves onto the line below.
    property string label: ""
    property real labelMinimumWidth: _label.implicitWidth

    readonly property int _gap: Style.dp(10)
    readonly property bool _hasLabel: label !== ""
    // The least the picker squeezes to: the chosen name plus Add Action.
    readonly property real _pickMin: _combobox.Layout.minimumWidth + _content.spacing + _button.implicitWidth
    readonly property bool _stacked: _hasLabel && width < labelMinimumWidth + _gap + _pickMin

    // Sized from the text: the widest action name is the preferred width.
    implicitWidth: (_hasLabel ? _label.implicitWidth + _gap : 0) + _content.implicitWidth
    implicitHeight: _stacked
        ? _label.height + Style.dp(4) + _content.implicitHeight
        : Math.max(_hasLabel ? _label.height : 0, _content.implicitHeight)
    Layout.minimumWidth: _pickMin

    Label {
        id: _label

        visible: _root._hasLabel
        text: _root.label
        wrapMode: Text.WordWrap
        width: _root._stacked ? _root.width
            : Math.max(0, _root.width - _root._gap - _content.width)
        y: _root._stacked ? 0 : Math.max(0, (_content.height - height) / 2)
    }

    Connections {
        target: actionNode

        function onActionChanged() {
            _combobox.model = actionNode.compatibleActions
        }
    }

    onActionNodeChanged: {
        _combobox.model = actionNode.compatibleActions
    }

    RowLayout {
        id: _content

        x: _root._hasLabel && !_root._stacked ? _root.width - width : 0
        y: !_root._hasLabel ? 0
            : _root._stacked ? _label.height + Style.dp(4)
            : Math.max(0, (_label.height - height) / 2)
        width: !_root._hasLabel ? _root.width
            : _root._stacked ? Math.max(_root._pickMin, Math.min(implicitWidth, _root.width))
            : Math.max(_root._pickMin, Math.min(implicitWidth,
                _root.width - _root._gap - _label.implicitWidth))
        height: !_root._hasLabel ? _root.height : implicitHeight

        // Pick the action, then add it (reads left to right).
        ComboBox {
            id: _combobox

            Layout.fillWidth: true
            Layout.minimumWidth: Math.ceil(_current.advanceWidth) + leftPadding + rightPadding
                + (contentItem ? contentItem.leftPadding + contentItem.rightPadding : 0) + Style.dp(2)
            implicitContentWidthPolicy: ComboBox.WidestText
            popup.width: Math.max(width, Style.dp(240))

            TextMetrics {
                id: _current
                font: _combobox.font
                text: _combobox.currentText
            }
        }

        Button {
            id: _button

            text: "Add Action"
            // Nothing to add when no action fits here.
            enabled: _combobox.count > 0 && _combobox.currentText.length > 0

            onClicked: {
                if (_combobox.currentText.length)
                    _root.callback(_combobox.currentText)
            }
        }
    }
}