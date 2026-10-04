// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

import QtQuick.Controls.Universal as U

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Profile
import "../../qml"


Item {
    id: _root

    property SmartToggleModel action

    implicitHeight: _content.height

    // Show all child nodes
    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Label {
                text: "Hold time (sec)"
            }
            FloatSpinBox {
                minValue: 0
                maxValue: 10
                value: _root.action.delay
                stepSize: 0.05

                onValueModified: (newValue) => {
                    _root.action.delay = newValue
                }
            }

            LayoutHorizontalSpacer {}

            ActionSelector {
                actionNode: _root.action
                callback: function(x) { _root.action.appendAction(x, "children"); }
            }
        }

        Repeater {
            model: _root.action.getActions("children")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "children"

                Layout.fillWidth: true
            }
        }
    }
}
