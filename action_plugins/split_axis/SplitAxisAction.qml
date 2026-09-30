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

    property SplitAxisModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Label {
                text: "Split axis at"
            }

            FloatSpinBox {
                minValue: -1.0
                maxValue: 1.0
                stepSize: 0.05
                decimals: Style.decimalsPrecise
                value: _root.action.splitValue

                onValueModified: (newValue) => {
                    _root.action.splitValue = newValue
                }
            }
        }

        // +-------------------------------------------------------------------
        // | Lower split actions
        // +-------------------------------------------------------------------
        RowLayout {
            id: _lowerHeader

            Label {
                text: "Actions for the <b>lower / left</b> part of the split."
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback: (x) => { _root.action.appendAction(x, "lower"); }
            }
        }

        HorizontalDivider {
            id: _lowerDivider

            Layout.fillWidth: true

            dividerColor: Style.lowColor
            lineWidth: Style.dp(2)
            spacing: Style.dp(2)
        }

        Repeater {
            model: _root.action.getActions("lower")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "lower"

                Layout.fillWidth: true
            }
        }

        // +-------------------------------------------------------------------
        // | Upper split actions
        // +-------------------------------------------------------------------
        RowLayout {
            id: _upperHeader

            Label {
                text: "Actions for the <b>upper / right</b> part of the split."
            }

            Rectangle {
                Layout.fillWidth: true
            }

            ActionSelector {
                actionNode: _root.action
                callback: (x) => { _root.action.appendAction(x, "upper"); }
            }
        }

        HorizontalDivider {
            id: _upperDivider

            Layout.fillWidth: true

            dividerColor: Style.lowColor
            lineWidth: Style.dp(2)
            spacing: Style.dp(2)
        }

        Repeater {
            model: _root.action.getActions("upper")

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: "upper"

                Layout.fillWidth: true
            }
        }
    }

    // Drop action for insertion into empty/first slot of the upper actions
    ActionDragDropArea {
        target: _upperDivider
        dropCallback: (drop) => {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "upper");
        }
    }

    // Drop action for insertion into empty/first slot of the lower actions
    ActionDragDropArea {
        target: _lowerDivider
        dropCallback: (drop) => {
            modelData.dropAction(drop.text, modelData.sequenceIndex, "lower");
        }
    }

}
