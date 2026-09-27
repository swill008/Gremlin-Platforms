// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Profile

Item {
    id: _root

    property InputItemBindingModel inputBinding

    implicitWidth: _content.width
    implicitHeight: _content.height

    RowLayout {
        id: _content

        visible: !["button", "key"].includes(_root.inputBinding.inputType)

        Label {
            leftPadding: 20
            text: "Treat as"
        }

        RadioButton {
            autoExclusive: false
            text: "Button"
            property bool shown: _root.inputBinding && _root.inputBinding.behavior == "button"
            onShownChanged: if (!pressed) checked = shown
            Component.onCompleted: checked = shown
            onClicked: if (_root.inputBinding) _root.inputBinding.behavior = "button"
        }

        RadioButton {
            autoExclusive: false
            text: "Axis"

            visible: _root.inputBinding && _root.inputBinding.inputType == "axis"
            property bool shown: _root.inputBinding && _root.inputBinding.behavior == "axis"
            onShownChanged: if (!pressed) checked = shown
            Component.onCompleted: checked = shown
            onClicked: if (_root.inputBinding) _root.inputBinding.behavior = "axis"
        }

        RadioButton {
            autoExclusive: false
            text: "Hat"

            visible: _root.inputBinding && _root.inputBinding.inputType == "hat"
            property bool shown: _root.inputBinding && _root.inputBinding.behavior == "hat"
            onShownChanged: if (!pressed) checked = shown
            Component.onCompleted: checked = shown
            onClicked: if (_root.inputBinding) _root.inputBinding.behavior = "hat"
        }
    }
}
