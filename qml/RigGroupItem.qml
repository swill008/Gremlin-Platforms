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
    property var node: ({ members: [] })

    Component { id: _mini; RigMiniChip { ed: _grp.ed } }
    Rectangle {
        visible: { ed.tick; return ed.fiveWayFormat(_grp.node) === "mini" }
        anchors.fill: parent
        radius: Style.dp(4)
        color: {
            ed.tick
            var n = _grp.node || {}
            return n.color || "#18181B"
        }
        border.color: {
            ed.tick
            var n = _grp.node || {}
            return n.border || "#3F3F46"
        }
        border.width: Style.dp(1)
    }
    Text {
        renderType: Text.NativeRendering
        visible: { ed.tick; return ed.captionH(_grp.node) > 0 }
        text: { ed.tick; return ed.fiveWayCaption(_grp.node) }
        color: "#E4E4E7"
        font.pixelSize: { ed.tick; return ed.uiPx((_grp.node && _grp.node.fontSize) ? _grp.node.fontSize : 10) }
        x: Style.dp(2)
        y: 0
    }
    Repeater {
        model: { ed.tick; return (_grp.node && _grp.node.members) ? _grp.node.members.length : 0 }
        delegate: Loader {
            required property int index
            x: {
                ed.tick
                var m = _grp.node && _grp.node.members ? _grp.node.members[index] : null
                if (!m)
                    return 0
                return ed.memberLocalX(_grp.node, m)
            }
            y: {
                ed.tick
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
