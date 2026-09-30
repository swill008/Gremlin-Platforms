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

    property TempoModel action

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

                text: "Long-press threshold (sec)"
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
                text: "Activate on"
            }
            RadioButton {
                autoExclusive: false
                text: "press"
                checked: _root.action.activateOn == "press"

                onClicked: {
                    _root.action.activateOn = "press"
                }
            }
            RadioButton {
                autoExclusive: false
                text: "release"
                checked: _root.action.activateOn == "release"

                onClicked: {
                    _root.action.activateOn = "release"
                }
            }
        }

        // +-------------------------------------------------------------------
        // | Short press actions
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                text: "Short press"
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback: function(x) { _root.action.appendAction(x, "short"); }
            }
        }

        Rectangle {
            id: _shortDivider
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        Repeater {
            model: _root.action.getActions("short")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "short"

                Layout.fillWidth: true
            }
        }

        // +-------------------------------------------------------------------
        // | Long press actions
        // +-------------------------------------------------------------------
        RowLayout {
            Label {
                text: "Long press"
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback: function(x) { _root.action.appendAction(x, "long"); }
            }
        }

        Rectangle {
            id: _longDivider
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        Repeater {
            model: _root.action.getActions("long")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "long"

                Layout.fillWidth: true
            }
        }
    }

    // Drop action for insertion into empty/first slot of the short actions
    ActionDragDropArea {
        target: _shortDivider
        dropCallback: function(drop) {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "short");
        }
    }

    // Drop action for insertion into empty/first slot of the long actions
    ActionDragDropArea {
        target: _longDivider
        dropCallback: function(drop) {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "long");
        }
    }
}
