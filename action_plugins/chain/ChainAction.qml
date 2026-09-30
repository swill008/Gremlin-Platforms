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
    property ChainModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Label {
                id: _label

                text: "Timeout (sec)"
            }

            FloatSpinBox {
                minValue: 0
                maxValue: 3600
                value: _root.action.timeout
                stepSize: 5

                onValueModified: (newValue) => {
                    _root.action.timeout = newValue
                }
            }

            LayoutHorizontalSpacer {}

            Button {
                text: "Add Chain Sequence"

                onPressed: function() {
                    _root.action.addSequence()
                }
            }
        }

        Repeater {
            model: _root.action.chainCount

            delegate: ChainSet {}
        }
    }

    component ChainSet : ColumnLayout {
        Layout.fillWidth: true

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: "Sequence " + index
            }

            LayoutHorizontalSpacer {}

            ActionSelector {
                actionNode: _root.action
                callback: function(x) {
                    _root.action.appendAction(x, index.toString());
                }
            }

            IconButton {
                text: bsi.icons.remove

                onClicked: function() {
                    _root.action.removeSequence(index)
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        ListView {
            id: _chainSequence

            model: _root.action.getActions(index.toString())

            Layout.fillWidth: true
            implicitHeight: contentHeight

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: index.toString()

                width: _chainSequence.width
            }
        }
    }
}
