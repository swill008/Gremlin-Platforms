// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.ActionPlugins
import Gremlin.Profile
import Gremlin.Style
import "../../qml"

Item {
    property HatButtonsModel action

    implicitHeight: _content.height

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            Label {
                text: "Button mode"
            }
            RadioButton {
                autoExclusive: false
                checkable: false
                text: "4 way"
                checked: _root.action.buttonCount == 4

                onClicked: {
                    _root.action.buttonCount = 4
                }
            }
            RadioButton {
                autoExclusive: false
                checkable: false
                text: "8 way"
                checked: _root.action.buttonCount == 8

                onClicked: {
                    _root.action.buttonCount = 8
                }
            }
        }

        Repeater {
            model: _root.action.buttonCount

            delegate: ButtonContainer {}
        }
    }

    component ButtonContainer : ColumnLayout {
        Layout.fillWidth: true

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: _root.action.buttonName(index)
            }

            LayoutHorizontalSpacer {}

            ActionSelector {
                actionNode: _root.action
                callback: function(x) {
                    _root.action.appendAction(x, _root.action.buttonName(index));
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: Style.dp(2)
            color: Style.lowColor
        }

        ListView {
            id: _buttonSequence

            model: _root.action.getActions(_root.action.buttonName(index))

            Layout.fillWidth: true
            implicitHeight: contentHeight

            delegate: ActionNode {
                action: modelData
                parentAction: _root.action
                containerName: _root.action.buttonName(index)

                width: _buttonSequence.width
            }
        }
    }
}
