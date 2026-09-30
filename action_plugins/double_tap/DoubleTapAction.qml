// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.ActionPlugins
import Gremlin.Base
import Gremlin.Profile
import Gremlin.Style
import "../../qml"


Item {
    id: _root

    property DoubleTapModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        // +-------------------------------------------------------------------
        // | Behavior configuration
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                id: _label

                text: "Double-tap threshold (sec)"
            }
            FloatSpinBox {
                minValue: 0
                maxValue: 100
                value: _root.action.threshold
                stepSize: 0.05

                onValueModified: (newValue) => {
                    _root.action.threshold = newValue
                }
            }

            LayoutHorizontalSpacer {}

            Label {
                text: "Single/Double tap:"
            }
            RadioButton {
                autoExclusive: false
                text: "exclusive"
                checked: _root.action.activateOn == "exclusive"

                onClicked: {
                    _root.action.activateOn = "exclusive"
                }
            }
            RadioButton {
                autoExclusive: false
                text: "combined"
                checked: _root.action.activateOn == "combined"

                onClicked: {
                    _root.action.activateOn = "combined"
                }
            }
        }

        // +-------------------------------------------------------------------
        // | Short press actions
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                text: "Single Tap"
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback: function(x) { _root.action.appendAction(x, "single"); }
            }
        }

        Rectangle {
            id: _singleDivider
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        Repeater {
            model: _root.action.getActions("single")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "single"

                Layout.fillWidth: true
            }
        }

        // +-------------------------------------------------------------------
        // | Long press actions
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                text: "Double Tap"
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback: function(x) { _root.action.appendAction(x, "double"); }
            }
        }

        Rectangle {
            id: _doubleDivider
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        Repeater {
            model: _root.action.getActions("double")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "double"

                Layout.fillWidth: true
            }
        }
    }

    // Drop action for insertion into empty/first slot of the short actions
    ActionDragDropArea {
        target: _singleDivider
        dropCallback: function(drop) {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "single");
        }
    }

    // Drop action for insertion into empty/first slot of the long actions
    ActionDragDropArea {
        target: _doubleDivider
        dropCallback: function(drop) {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "double");
        }
    }
}
