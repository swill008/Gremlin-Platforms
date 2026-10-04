// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Config
import Gremlin.Style
import "action_kinds.js" as ActionKinds

// Options → Actions → Add Action Menu: which actions the menu offers, under
// the same headings it uses (action_kinds.js), in two columns. Dragging an
// action by its handle reorders it among its own kind; the other actions
// keep their places (ActionSequenceOrdering.moveAmong).
Item {
    id: _root

    implicitHeight: _content.implicitHeight
    implicitWidth: _content.implicitWidth

    ActionSequenceOrdering {
        id: _data
    }

    // Bumped whenever the stored list changes, so the groups re-read it.
    property int _rev: 0
    Connections {
        target: _data
        function onLayoutChanged() { _root._rev++ }
        function onModelReset() { _root._rev++ }
        function onDataChanged() { _root._rev++ }
    }

    // UserRole + 1 name, + 2 shown (ActionSequenceOrdering).
    function nameAt(row) { return String(_data.data(_data.index(row, 0), Qt.UserRole + 1)) }
    function shownAt(row) { return !!_data.data(_data.index(row, 0), Qt.UserRole + 2) }

    // The stored rows of one kind, in their order.
    function rowsOf(kind) {
        _rev
        var out = []
        for (var i = 0; i < _data.rowCount(); i++) {
            var name = nameAt(i)
            if (!ActionKinds.internal[name] && ActionKinds.kindOf(name) === kind)
                out.push(i)
        }
        return out
    }

    readonly property var _counts: {
        _rev
        var shown = 0
        var all = 0
        for (var i = 0; i < _data.rowCount(); i++) {
            if (ActionKinds.internal[nameAt(i)])
                continue
            all++
            if (shownAt(i))
                shown++
        }
        return { shown: shown, all: all }
    }

    // The row being dragged and where it would go (a row of its kind, or -1
    // for after the last one).
    property int _dragRow: -1
    property int _dropBefore: -1
    property string _dragKind: ""

    ColumnLayout {
        id: _content
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Style.dp(6)

        Label {
            text: _root._counts.shown + " of " + _root._counts.all + " offered"
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: Style.dp(40)
            rowSpacing: 0

            Repeater {
                // Map to and Axis and Hat on the left, the rest on the right.
                model: [["map", "axis"], ["logic", "other"]]

                ColumnLayout {
                    required property var modelData
                    Layout.alignment: Qt.AlignTop
                    Layout.fillWidth: true
                    spacing: 0

                    Repeater {
                        model: parent.modelData
                        delegate: _kindGroup
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            Button {
                text: "Reset to Default"
                onClicked: _data.resetDefaults()
            }
        }
    }

    Component {
        id: _kindGroup

        ColumnLayout {
            id: _group

            required property string modelData
            readonly property string kind: modelData
            readonly property var rows: _root.rowsOf(kind)

            visible: rows.length > 0
            spacing: 0

            Label {
                Layout.topMargin: Style.dp(6)
                text: ActionKinds.titles[_group.kind]
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
            }

            ColumnLayout {
                id: _list
                spacing: 0

                Repeater {
                    model: _group.rows

                    RowLayout {
                        id: _row

                        required property int modelData
                        readonly property int row: modelData

                        spacing: Style.dp(6)

                        // Where a drop before this row would land.
                        Rectangle {
                            Layout.preferredWidth: Style.dp(3)
                            Layout.preferredHeight: Style.dp(18)
                            color: _root._dragKind === _group.kind && _root._dropBefore === _row.row
                                ? Style.accent : "transparent"
                        }

                        Label {
                            text: ""
                            font.family: Style.iconFont
                            color: Style.fgMuted

                            MouseArea {
                                anchors.fill: parent
                                anchors.margins: -Style.dp(4)
                                cursorShape: Qt.SizeVerCursor
                                preventStealing: true

                                onPressed: {
                                    _root._dragRow = _row.row
                                    _root._dragKind = _group.kind
                                    _root._dropBefore = _row.row
                                }
                                onPositionChanged: (mouse) => {
                                    var p = mapToItem(_list, mouse.x, mouse.y)
                                    var before = -1
                                    var kids = _list.children
                                    for (var i = 0; i < kids.length; i++) {
                                        var k = kids[i]
                                        if (k.row === undefined)
                                            continue
                                        if (p.y < k.y + k.height / 2) {
                                            before = k.row
                                            break
                                        }
                                    }
                                    _root._dropBefore = before
                                }
                                onReleased: {
                                    _data.moveAmong(_group.rows, _root._dragRow, _root._dropBefore)
                                    _root._dragRow = -1
                                    _root._dragKind = ""
                                }
                                onCanceled: {
                                    _root._dragRow = -1
                                    _root._dragKind = ""
                                }
                            }
                        }

                        CheckBox {
                            text: _root.nameAt(_row.row)
                            checked: { _root._rev; return _root.shownAt(_row.row) }
                            font.pixelSize: Style.dp(13)
                            padding: Style.dp(2)
                            onToggled: _data.setShown(_row.row, checked)
                        }
                    }
                }

                // A drop after the last action of this kind.
                Rectangle {
                    Layout.leftMargin: 0
                    Layout.preferredWidth: Style.dp(120)
                    Layout.preferredHeight: Style.dp(2)
                    color: _root._dragKind === _group.kind && _root._dropBefore === -1
                        ? Style.accent : "transparent"
                }
            }
        }
    }
}
