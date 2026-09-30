// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U

import Gremlin.Profile
import Gremlin.ActionPlugins
import "../../qml"


Item {
    id: _root

    property PauseResumeModel action

    implicitHeight: _content.height

    RowLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RadioButton {
            autoExclusive: false
            checkable: false
            text: "Pause"

            checked: _root.action.operation === "Pause"
            onClicked: function() {
                _root.action.operation = "Pause"
            }
        }
        RadioButton {
            autoExclusive: false
            checkable: false
            text: "Resume"

            checked: _root.action.operation === "Resume"
            onClicked: function() {
                _root.action.operation = "Resume"
            }
        }
        RadioButton {
            autoExclusive: false
            checkable: false
            text: "Toggle"

            checked: _root.action.operation === "Toggle"
            onClicked: function() {
                _root.action.operation = "Toggle"
            }
        }
    }
}
