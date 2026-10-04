// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml

// A chip's label in the Button Map editor: one or two rows (Shift+Enter
// while naming), and the action on a row of its own in Name and action.
// The rows line up by Text Align, or each by its own (Align Rows
// Separately). One centred row draws as a plain centred text, as before.
Item {
    id: _label
    property var ed: null
    property var node: ({})
    property var mem: null
    property int rev: 0
    property string text: ""
    // Set by the chip (its text color, or the pressed one).
    property color color
    property real pixelSize: 10

    readonly property var rows: String(text).split("\n")
    readonly property bool apart: {
        _label.rev
        return rows.length > 1 && !!ed && ed.chipRowsApart(node, mem)
    }

    implicitWidth: apart ? _rows.implicitWidth : _one.implicitWidth
    implicitHeight: apart ? _rows.implicitHeight : _one.implicitHeight

    function _h(where) {
        if (where === "left")
            return Text.AlignLeft
        if (where === "right")
            return Text.AlignRight
        return Text.AlignHCenter
    }

    Text {
        id: _one
        renderType: Text.NativeRendering
        anchors.centerIn: parent
        visible: !_label.apart
        color: _label.color
        font.pixelSize: _label.pixelSize
        text: _label.text
        // One row has nothing to line up with: drawn as a plain text, as
        // before (an alignment set on it moves native text by a pixel).
        horizontalAlignment: {
            _label.rev
            if (_label.rows.length < 2 || !_label.ed)
                return Text.AlignLeft
            return _label._h(_label.ed.chipRowAlign(_label.node, _label.mem, 0))
        }
    }

    Column {
        id: _rows
        anchors.centerIn: parent
        visible: _label.apart
        // Every row as wide as the widest, so each can line up on its own.
        readonly property real rowW: {
            var most = 0
            for (var i = 0; i < _rowRep.count; i++) {
                var it = _rowRep.itemAt(i)
                if (it)
                    most = Math.max(most, it.implicitWidth)
            }
            return most
        }
        Repeater {
            id: _rowRep
            model: _label.apart ? _label.rows : []
            Text {
                required property string modelData
                required property int index
                renderType: Text.NativeRendering
                width: _rows.rowW
                color: _label.color
                font.pixelSize: _label.pixelSize
                text: modelData
                horizontalAlignment: {
                    _label.rev
                    return _label._h(_label.ed.chipRowAlign(_label.node, _label.mem, index))
                }
            }
        }
    }
}
