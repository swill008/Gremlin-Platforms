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
    id: _hat
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
                    // The diagonals' actions would go: ask first.
                    var lost = _hat.action.actionsDroppedBy(4)
                    if (!lost) {
                        _hat.action.buttonCount = 4
                        return
                    }
                    _modeGate.confirmThen("Switch to 4 way",
                        (lost === 1 ? "1 action" : lost + " actions")
                        + " on the diagonal directions (North-East, South-East, South-West, North-West) will be removed. North, East, South and West keep theirs.",
                        "Switch to 4 way", function() { _hat.action.buttonCount = 4 }, null, true)
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

    // Asks before 4 way drops the diagonals' actions.
    DismissibleDialog {
        id: _modeGate
    }
}
