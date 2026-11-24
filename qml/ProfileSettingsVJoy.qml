// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Base
import Gremlin.Profile
import Gremlin.Style
import Gremlin.UI

// Options › vJoy (04 S62, S96-S98): each vJoy as output or input, and the
// initial axis values used when the profile runs. Options scrolls it.
ColumnLayout {
    id: _root

    // Options' search: only the rows it matches show.
    property string filterText: ""
    readonly property bool searching: filterText.trim() !== ""
    readonly property int searchFound: _modesFound + _valuesFound

    // The matching rows; counted again when rows come or go.
    readonly property int _modesFound: {
        _modeRepeater.revision
        var n = 0
        for (var i = 0; i < _modeRepeater.count; i++) {
            var row = _modeRepeater.itemAt(i)
            if (row && row.found)
                n++
        }
        return n
    }
    readonly property int _valuesFound: {
        _initialRepeater.revision
        var n = 0
        for (var i = 0; i < _initialRepeater.count; i++) {
            var card = _initialRepeater.itemAt(i)
            if (card)
                n += card.axesFound
        }
        return n
    }

    function matches(text) {
        var needle = filterText.trim().toLowerCase()
        return needle === "" || String(text).toLowerCase().indexOf(needle) >= 0
    }

    spacing: 0

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Style.dp(4)

        GroupLabel {
            text: "vJoy Behavior"
            visible: !_root.searching || _root._modesFound > 0
        }
        Card {
            visible: !_root.searching || _root._modesFound > 0
            Repeater {
                id: _modeRepeater
                readonly property VJoyInputOrOutputModel _vjoyModes:
                    ModelFactory.create("VJoyInputOrOutputModel", _modeRepeater)
                model: _vjoyModes

                // Goes up as rows come or go.
                property int revision: 0
                onItemAdded: revision++
                onItemRemoved: revision++

                // The first row that shows (no divider above it).
                readonly property int firstFound: {
                    revision
                    for (var i = 0; i < count; i++) {
                        var row = itemAt(i)
                        if (row && row.found)
                            return i
                    }
                    return -1
                }

                delegate: OptionEntryCard {
                    readonly property bool found: _root.matches(
                        "vJoy Behavior " + title + " Output Input " + _modesNote.text)
                    visible: found
                    Layout.fillWidth: true
                    divider: index > _modeRepeater.firstFound
                    title: `vJoy ${vid}`

                    RowLayout {
                        spacing: Style.dp(8)

                        Label {
                            text: "Output"
                            color: Style.fgSoft
                            font.pixelSize: Style.dp(14)
                        }
                        Switch {
                            objectName: `vjoyIsInput:${vid}`
                            text: "Input"

                            checked: isInput
                            onToggled: () => { isInput = checked }
                        }
                    }
                }
            }
        }
        Label {
            id: _modesNote
            visible: !_root.searching || _root._modesFound > 0
            Layout.fillWidth: true
            Layout.topMargin: Style.dp(2)
            text: "Output: used by 'Map to vJoy'. Input: read like any other "
                + "joystick, useful when several vJoy devices are used by "
                + "different programs."
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
            wrapMode: Text.WordWrap
        }

        GroupLabel {
            id: _valuesLabel
            text: "vJoy Initial Values (used when the profile runs)"
            visible: !_root.searching || _root._valuesFound > 0
        }
        Repeater {
            id: _initialRepeater
            readonly property OutputVJoyListModel _outputVJoys:
                ModelFactory.create("OutputVJoyListModel", _initialRepeater)
            model: _outputVJoys

            property int revision: 0
            onItemAdded: revision++
            onItemRemoved: revision++

            delegate: Card {
                id: _card
                readonly property int axesFound: {
                    _axes.revision
                    var n = 0
                    for (var i = 0; i < _axes.count; i++) {
                        var axis = _axes.itemAt(i)
                        if (axis && axis.found)
                            n++
                    }
                    return n
                }
                visible: !_root.searching || axesFound > 0
                required property int vjoyId
                required property var initialValuesModel
                Layout.bottomMargin: Style.dp(12)

                Label {
                    Layout.fillWidth: true
                    Layout.leftMargin: Style.dp(14)
                    Layout.topMargin: Style.dp(10)
                    Layout.bottomMargin: Style.dp(10)
                    text: `vJoy ${_card.vjoyId}`
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(14)
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Style.dp(1)
                    color: Style.line
                }

                // The axes, in two columns.
                GridLayout {
                    Layout.fillWidth: true
                    Layout.margins: Style.dp(14)
                    columns: 2
                    columnSpacing: Style.dp(24)
                    rowSpacing: Style.dp(8)

                    Repeater {
                        id: _axes
                        model: _card.initialValuesModel

                        property int revision: 0
                        onItemAdded: revision++
                        onItemRemoved: revision++

                        delegate: RowLayout {
                            readonly property bool found: _root.matches(
                                _valuesLabel.text + ` vJoy ${_card.vjoyId} ` + label)
                            visible: found
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: Style.dp(12)

                            Label {
                                text: label
                                color: Style.fgStrong
                                font.pixelSize: Style.dp(14)
                                Layout.preferredWidth: Style.dp(110)
                                elide: Text.ElideRight
                            }

                            // Named for the control API (13 D-13-INITIAL-VALUES).
                            FloatSpinBox {
                                objectName: `vjoyInitialValue:${_card.vjoyId}:${label}`
                                minValue: -1.0
                                maxValue: 1.0
                                stepSize: 0.05

                                value: model.value
                                onValueModified: (newValue) => { model.value = newValue }
                            }

                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }
        }
    }

    // A small heading over a card, as ConfigGroup's.
    component GroupLabel : Label {
        Layout.topMargin: Style.dp(14)
        color: Style.fgMuted
        font.pixelSize: Style.dp(12)
    }

    // The card rows sit in, as ConfigGroup's.
    component Card : Rectangle {
        default property alias rows: _rows.data
        Layout.fillWidth: true
        implicitHeight: _rows.implicitHeight
        radius: Style.dp(6)
        color: Style.bgCard
        border.color: Style.line
        border.width: Style.dp(1)

        ColumnLayout {
            id: _rows
            width: parent.width
            spacing: 0
        }
    }
}
