// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// A group of chips (plus, pair, stack, 5-way) in the Button Map editor.
Item {
    id: _grp
    property var ed: null
    // Redrawn on the editor's tick, and while this item is being dragged on
    // the drag tick only (big maps: other items stay as they are).
    property int rev: ed ? ed.tick : 0
    property var node: ({ members: [] })

    Component { id: _mini; RigMiniChip { ed: _grp.ed; rev: _grp.rev } }
    Rectangle {
        visible: { _grp.rev; return ed.fiveWayFormat(_grp.node) === "mini" }
        anchors.fill: parent
        radius: ed.fixPx(Style.dp(4))
        color: {
            _grp.rev
            var n = _grp.node || {}
            return ed.ink(n.color || "#18181B")
        }
        border.color: {
            _grp.rev
            var n = _grp.node || {}
            return ed.ink(n.border || "#3F3F46")
        }
        border.width: ed.fixPx(Style.dp(1))
    }
    Text {
        renderType: Text.NativeRendering
        visible: { _grp.rev; return ed.captionH(_grp.node) > 0 }
        text: { _grp.rev; return ed.fiveWayCaption(_grp.node) }
        color: { _grp.rev; return ed.ink("#E4E4E7") }
        font.pixelSize: { _grp.rev; return ed.uiPx((_grp.node && _grp.node.fontSize) ? _grp.node.fontSize : 10) }
        x: ed.fixPx(Style.dp(2))
        y: 0
    }
    Repeater {
        model: { _grp.rev; return (_grp.node && _grp.node.members) ? _grp.node.members.length : 0 }
        delegate: Loader {
            required property int index
            x: {
                _grp.rev
                var m = _grp.node && _grp.node.members ? _grp.node.members[index] : null
                if (!m)
                    return 0
                return ed.memberLocalX(_grp.node, m)
            }
            y: {
                _grp.rev
                var m = _grp.node && _grp.node.members ? _grp.node.members[index] : null
                if (!m)
                    return 0
                return ed.memberLocalY(_grp.node, m)
            }
            sourceComponent: _mini
            onLoaded: {
                item.node = Qt.binding(function() { return _grp.node })
                item.memberIndex = index
                item.hwId = Qt.binding(function() {
                    var m = _grp.node && _grp.node.members ? _grp.node.members[index] : null
                    return m && m.hwId ? m.hwId : 0
                })
                item.leafKind = Qt.binding(function() {
                    var m = _grp.node && _grp.node.members ? _grp.node.members[index] : null
                    return ed.memberKind(_grp.node, m)
                })
            }
        }
    }
}
