// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// One chip (button, axis or hat label) in the Button Map editor.
Rectangle {
    property var ed: null
    property var node: ({ kind: "btn", hwId: 0 })
    property bool on: ed.litOf(node.kind, node.hwId)
    width: implicitWidth
    height: implicitHeight
    implicitWidth: { ed.tick; return _lab.implicitWidth + ed.uiPx(Math.max(10, (node.chipSize || 18) * 0.55)) }
    implicitHeight: { ed.tick; return ed.chipH(node) }
    radius: { ed.tick; return ed.chipR(node, height || ed.chipH(node)) }
    color: {
        ed.tick
        if (ed.chipIsHollow(node)) return "transparent"
        return on && node.highlight ? (node.hlColor || "#14532D") : (node.color || "#18181B")
    }
    border.color: {
        ed.tick
        return on && node.highlight ? (node.hlBorder || "#22C55E") : (node.border || "#3F3F46")
    }
    border.width: { ed.tick; return ed.chipIsHollow(node) ? 2 : 1 }
    antialiasing: true
    RigSelRing {
        on: { ed.tick; return ed.isSelected(node.id) && !ed.exporting }
    }
    Text {
        renderType: Text.NativeRendering
        id: _lab
        anchors.centerIn: parent
        color: {
            ed.tick
            return on && node.highlight ? (node.hlText || "#BBF7D0") : (node.textColor || "#E4E4E7")
        }
        font.pixelSize: { ed.tick; return ed.uiPx(node.fontSize || 10) }
        text: {
            ed.tick
            return ed.chipText(node, null)
        }
    }
}
