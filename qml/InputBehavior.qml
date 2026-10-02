// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Profile
import Gremlin.Style

Item {
    id: _root

    property InputItemBindingModel inputBinding
    readonly property bool hasChoice: inputBinding
        && inputBinding.inputType !== "button"
        && inputBinding.inputType !== "key"

    // Switching behavior removes the binding's actions, so ask first.
    function treatAs(kind) {
        var b = inputBinding
        if (!b || b.behavior == kind)
            return
        var n = b.actionCount()
        if (n === 0) {
            b.behavior = kind
            return
        }
        _behaviorGate.confirmThen("Treat as " + kind[0].toUpperCase() + kind.slice(1) + "?",
            "Changing how this input is treated removes its "
                + (n === 1 ? "action" : n + " actions") + ".",
            "Change and remove", function() {
                if (_root.inputBinding === b)
                    b.behavior = kind
            }, null, true)
    }

    implicitWidth: hasChoice ? _content.implicitWidth : 0
    implicitHeight: hasChoice ? _content.implicitHeight : 0

    RowLayout {
        id: _content

        visible: _root.hasChoice

        Label {
            leftPadding: Style.dp(20)
            text: "Treat as"
        }

        RadioButton {
            autoExclusive: false
            checkable: false
            text: "Button"
            property bool shown: _root.inputBinding && _root.inputBinding.behavior == "button"
            onShownChanged: if (!pressed) checked = shown
            Component.onCompleted: checked = shown
            onClicked: _root.treatAs("button")
        }

        RadioButton {
            autoExclusive: false
            checkable: false
            text: "Axis"

            visible: _root.inputBinding && _root.inputBinding.inputType == "axis"
            property bool shown: _root.inputBinding && _root.inputBinding.behavior == "axis"
            onShownChanged: if (!pressed) checked = shown
            Component.onCompleted: checked = shown
            onClicked: _root.treatAs("axis")
        }

        RadioButton {
            autoExclusive: false
            checkable: false
            text: "Hat"

            visible: _root.inputBinding && _root.inputBinding.inputType == "hat"
            property bool shown: _root.inputBinding && _root.inputBinding.behavior == "hat"
            onShownChanged: if (!pressed) checked = shown
            Component.onCompleted: checked = shown
            onClicked: _root.treatAs("hat")
        }
    }

    DismissibleDialog {
        id: _behaviorGate
    }
}
