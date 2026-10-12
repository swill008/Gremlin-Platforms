// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Profile
import "helpers.js" as Helpers
import "confirm.js" as Confirm
import Gremlin.Style

Item {
    id: _root

    property InputItemBindingModel inputBinding
    property InputItemModel inputItemModel
    property bool hideControlSetup: false
    property bool catalogSequence: false
    readonly property bool showTreat: !hideControlSetup && _behavior.hasChoice

    implicitHeight: _layout.implicitHeight

    ColumnLayout {
        id: _layout

        anchors.left: parent.left
        anchors.right: parent.right

        // Treat as has its own line so the name line can be narrower.
        // A button or a key has no Treat as, so that line is not shown.
        RowLayout {
            visible: _root.showTreat
            Layout.fillWidth: true
            spacing: Style.dp(6)

            IconButton {
                visible: !_root.catalogSequence

                font.pixelSize: Style.dp(24)
                horizontalPadding: -Style.dp(5)
                text: bsi.icons.verticalDrag

                MouseArea {
                    id: _gripTop

                    anchors.fill: parent
                    preventStealing: true
                    hoverEnabled: true
                    cursorShape: Qt.OpenHandCursor
                    drag.target: _payload
                    drag.axis: Drag.XAndYAxis
                    drag.threshold: Style.dp(4)

                    onPressed: (mouse) => {
                        var pos = mapToItem(_root, mouse.x, mouse.y)
                        _payload.x = pos.x
                        _payload.y = pos.y
                    }
                }
            }

            InputBehavior {
                id: _behavior

                visible: _root.showTreat
                Layout.preferredWidth: visible ? implicitWidth : 0
                Layout.maximumWidth: visible ? implicitWidth : 0
                inputBinding: _root.inputBinding
            }
        }

        // Note, the action picker, then the hint and remove buttons on one
        // line when they fit; in a narrow pane the picker goes onto a second
        // line under the note.
        GridLayout {
            id: _generalHeader

            // The column's width, not the grid's own (which grows to its least
            // width when that is wider).
            readonly property bool wide: _layout.width >=
                (_rowGrip.visible ? _rowGrip.implicitWidth + columnSpacing : 0)
                + _description.Layout.minimumWidth + columnSpacing
                + _rootSelector.Layout.minimumWidth
                + (_rootHint.visible ? _rootHint.implicitWidth + columnSpacing : 0)
                + (_rootRemove.visible ? _rootRemove.implicitWidth + columnSpacing : 0)

            Layout.fillWidth: true
            columns: 5

            IconButton {
                id: _rowGrip

                visible: !_root.catalogSequence && !_root.showTreat
                Layout.row: 0
                Layout.column: 0
                Layout.preferredWidth: visible ? implicitWidth : 0
                Layout.maximumWidth: visible ? implicitWidth : 0

                font.pixelSize: Style.dp(24)
                horizontalPadding: -Style.dp(5)
                text: bsi.icons.verticalDrag

                MouseArea {
                    id: _gripName

                    anchors.fill: parent
                    preventStealing: true
                    hoverEnabled: true
                    cursorShape: Qt.OpenHandCursor
                    drag.target: _payload
                    drag.axis: Drag.XAndYAxis
                    drag.threshold: Style.dp(4)

                    onPressed: (mouse) => {
                        var pos = mapToItem(_root, mouse.x, mouse.y)
                        _payload.x = pos.x
                        _payload.y = pos.y
                    }
                }
            }

            JGTextField {
                id: _description

                Layout.row: 0
                Layout.column: 1
                Layout.preferredWidth: Style.dp(160)
                Layout.minimumWidth: Style.dp(110)
                Layout.maximumWidth: Style.dp(200)

                // Glossary: "Note" (the Description action keeps its name).
                placeholderText: "Note"
                text: _root.inputBinding.rootAction ?
                    _root.inputBinding.rootAction.actionLabel : ""

                onTextEdited: () => {
                    _root.inputBinding.rootAction.actionLabel = text
                }
            }

            ActionSelector {
                id: _rootSelector

                Layout.row: _generalHeader.wide ? 0 : 1
                Layout.column: _generalHeader.wide ? 2 : 1
                Layout.columnSpan: _generalHeader.wide ? 1 : 4
                Layout.fillWidth: true

                actionNode: _root.inputBinding.rootAction
                callback: (x) => { actionNode.appendAction(x, "children") }
            }

            Label {
                id: _rootHint

                visible: _root.inputBinding.userFeedback.length > 0
                Layout.row: 0
                Layout.column: 3

                font.family: Style.iconFont
                font.pixelSize: Style.dp(24)

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
                id: _rootRemove

                visible: !_root.catalogSequence
                Layout.row: 0
                Layout.column: 4
                Layout.alignment: Qt.AlignRight
                text: bsi.icons.remove
                font.pixelSize: Style.dp(24)

                PointerTip { text: "Remove this binding and all its actions" }

                onClicked: () => {
                    var binding = _root.inputBinding
                    var model = _root.inputItemModel
                    var n = binding ? binding.actionCount() : 0
                    if (n === 0) {
                        model.deleteActionSequnce(binding)
                        return
                    }
                    Confirm.ask(_root, {
                        title: "Remove this binding?",
                        text: (n === 1 ? "Its action goes" : "Its " + n + " actions go") + " with it.",
                        undoable: false,
                        action: "Remove Binding",
                        onAccept: function() { model.deleteActionSequnce(binding) }
                    })
                }
            }
        }

        // UI for an axis behaving like a button.
        Loader {
            active: !_root.hideControlSetup &&
                _root.inputBinding.behavior == "button" &&
                _root.inputBinding.inputType == "axis"
            visible: active

            sourceComponent: RowLayout {
                Label {
                    Layout.leftMargin: Style.dp(20)

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
                    Layout.leftMargin: Style.dp(20)

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

        width: Style.dp(1)
        height: Style.dp(1)

        Drag.active: (_gripTop.drag.active || _gripName.drag.active) && _root.inputBinding && _root.inputBinding.rootAction
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
