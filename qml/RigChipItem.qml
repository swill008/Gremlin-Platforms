// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// One chip (button, axis or hat label) in the Button Map editor.
Rectangle {
    id: _chipRoot
    property var ed: null
    // Redrawn on the editor's tick, and while this item is being dragged on
    // the drag tick only (big maps: other items stay as they are).
    property int rev: ed ? ed.tick : 0
    property var node: ({ kind: "btn", hwId: 0 })
    property bool on: ed.litOf(node.kind, node.hwId)
    width: implicitWidth
    height: implicitHeight
    // A circle is as wide as it is tall (ed.chipH gives its diameter).
    implicitWidth: {
        _chipRoot.rev
        if (ed.isCircle(node, null))
            return ed.chipH(node)
        return _lab.implicitWidth + ed.uiPx(Math.max(10, (node.chipSize || 18) * 0.55))
    }
    implicitHeight: { _chipRoot.rev; return ed.chipH(node) }
    radius: { _chipRoot.rev; return ed.chipR(node, height || ed.chipH(node)) }
    color: {
        _chipRoot.rev
        if (ed.chipIsHollow(node)) return "transparent"
        return ed.ink(on && node.highlight ? (node.hlColor || "#14532D") : (node.color || "#18181B"))
    }
    border.color: {
        _chipRoot.rev
        return ed.ink(on && node.highlight ? (node.hlBorder || "#22C55E") : (node.border || "#3F3F46"))
    }
    border.width: { _chipRoot.rev; return ed.chipIsHollow(node) ? 2 : 1 }
    antialiasing: true
    RigSelRing {
        on: { _chipRoot.rev; return ed.isSelected(node.id) && !ed.exporting }
    }
    Text {
        renderType: Text.NativeRendering
        id: _lab
        anchors.centerIn: parent
        color: {
            _chipRoot.rev
            return ed.ink(on && node.highlight ? (node.hlText || "#BBF7D0") : (node.textColor || "#E4E4E7"))
        }
        font.pixelSize: { _chipRoot.rev; return ed.uiPx(ed.isCircle(node, null) ? ed.circleFont(node, null) : (node.fontSize || 10)) }
        text: {
            _chipRoot.rev
            return ed.chipText(node, null)
        }
    }
}
