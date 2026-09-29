// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts

import Gremlin.Profile
import "helpers.js" as Helpers

Item {
    id: _root

    property InputItemBindingModel inputBinding
    property InputItemModel inputItemModel
    property bool hideControlSetup: false
    property bool catalogSequence: false
    property MouseArea dragHandleArea: _grip

    implicitHeight: _layout.implicitHeight

    ColumnLayout {
        id: _layout

        anchors.left: parent.left
        anchors.right: parent.right

        // Default header components visible with every input.
        RowLayout {
            id: _generalHeader

            Layout.fillWidth: true

            IconButton {
                id: _handle

                visible: !_root.catalogSequence

                font.pixelSize: 24
                horizontalPadding: -5
                text: bsi.icons.verticalDrag

                MouseArea {
                    id: _grip

                    anchors.fill: parent
                    preventStealing: true
                    hoverEnabled: true
                    cursorShape: Qt.OpenHandCursor
                    drag.target: _payload
                    drag.axis: Drag.XAndYAxis
                    drag.threshold: 4

                    onPressed: (mouse) => {
                        var pos = mapToItem(_root, mouse.x, mouse.y)
                        _payload.x = pos.x
                        _payload.y = pos.y
                    }
                }
            }

            InputBehavior {
                id: _behavior

                visible: !_root.hideControlSetup && hasChoice
                Layout.preferredWidth: visible ? implicitWidth : 0
                Layout.maximumWidth: visible ? implicitWidth : 0
                inputBinding: _root.inputBinding
            }

            JGTextField {
                id: _description

                Layout.preferredWidth: 160
                Layout.minimumWidth: 110
                Layout.maximumWidth: 200

                placeholderText: "Description"
                text: _root.inputBinding.rootAction ?
                    _root.inputBinding.rootAction.actionLabel : "Description"

                onTextEdited: () => {
                    _root.inputBinding.rootAction.actionLabel = text
                }
            }

            ActionSelector {
                Layout.fillWidth: true
                Layout.minimumWidth: 180

                actionNode: _root.inputBinding.rootAction
                callback: (x) => { actionNode.appendAction(x, "children") }
            }

            Label {
                visible: _root.inputBinding.userFeedback.length > 0

                font.family: "bootstrap-icons"
                font.pixelSize: 24

                text: Helpers.determineHintIcon(_root.inputBinding.userFeedback)
                color: Helpers.determineHintColor(_root.inputBinding.userFeedback)

                HoverHandler {
                    onHoveredChanged: () => {
                        _hintsTooltip.parent = parent
                        _hintsTooltip.x = -_hintsTooltip.width - 5
                        _hintsTooltip.y = parent.height + 5
                        _hintsTooltip.hints = _root.inputBinding.userFeedback
                        _hintsTooltip.visible = hovered
                    }
                }
            }

            IconButton {
                visible: !_root.catalogSequence
                text: bsi.icons.remove
                font.pixelSize: 24

                onClicked: () => {
                    _root.inputItemModel.deleteActionSequnce(_root.inputBinding)
                }
            }
        }

        // UI for an axis behaving like a button.
        Loader {
            id: _behaviorAxisButton

            active: !_root.hideControlSetup &&
                _root.inputBinding.behavior == "button" &&
                _root.inputBinding.inputType == "axis"
            visible: active

            sourceComponent: RowLayout {
                Label {
                    Layout.leftMargin: 20

                    text: "Activate between"
                }
                NumericalRangeSlider {
                    from: -1.0
                    to: 1.0
                    firstValue: _root.inputBinding.virtualButton.lowerLimit
                    secondValue: _root.inputBinding.virtualButton.upperLimit
                    stepSize: 0.1
                    decimals: 3

                    onFirstEdited: (value) => {
                        _root.inputBinding.virtualButton.lowerLimit = value
                    }
                    onSecondEdited: (value) => {
                        _root.inputBinding.virtualButton.upperLimit = value
                    }
                }
                Label {
                    text: "when entered from"
                }
                ComboBox {
                    model: ["Anywhere", "Above", "Below"]

                    // Select the correct entry.
                    Component.onCompleted: () => {
                        currentIndex = find(
                            _root.inputBinding.virtualButton.direction,
                            Qt.MatchFixedString
                        )
                    }

                    onActivated: () => {
                        _root.inputBinding.virtualButton.direction = currentText
                    }
                }
            }
        }

        // UI for a hat behaving like a button.
        Loader {
            active: !_root.hideControlSetup &&
                _root.inputBinding.behavior == "button" &&
                _root.inputBinding.inputType == "hat"
            visible: active

            sourceComponent: RowLayout {
                Label {
                    Layout.leftMargin: 20

                    text: "Activate on"
                }
                HatDirectionSelector {
                    virtualButton: _root.inputBinding.virtualButton
                }
            }
        }
    }

    Item {
        id: _payload

        width: 1
        height: 1

        Drag.active: _grip.drag.active && _root.inputBinding && _root.inputBinding.rootAction
        Drag.dragType: Drag.Automatic
        Drag.supportedActions: Qt.MoveAction
        Drag.proposedAction: Qt.MoveAction
        Drag.hotSpot.x: 0
        Drag.hotSpot.y: 0
        Drag.mimeData: {
            "application/x-gremlin-sequence": (_root.inputBinding && _root.inputBinding.rootAction)
                ? _root.inputBinding.rootAction.id : ""
        }
    }
}
