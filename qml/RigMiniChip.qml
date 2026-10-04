// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// One member chip inside a group in the Button Map editor.
Rectangle {
    id: _miniRoot
    property var ed: null
    // Redrawn on the editor's tick, and while this item is being dragged on
    // the drag tick only (big maps: other items stay as they are).
    property int rev: ed ? ed.tick : 0
    property int hwId: 0
    property var node: ({})
    property int memberIndex: -1
    property string leafKind: "btn"
    property bool on: ed.litOf(leafKind, hwId)
    readonly property var mem: {
        _miniRoot.rev
        return (node && node.members && memberIndex >= 0) ? node.members[memberIndex] : null
    }
    width: implicitWidth
    height: implicitHeight
    // A circle is as wide as it is tall (ed.chipH gives its diameter).
    implicitWidth: {
        _miniRoot.rev
        if (ed.isCircle(node, mem))
            return ed.chipH(node, mem)
        return t.implicitWidth + ed.uiPx(Math.max(10, ed.styleVal(node, mem, "chipSize", 18) * 0.55))
    }
    implicitHeight: { _miniRoot.rev; return ed.chipH(node, mem) }
    radius: { _miniRoot.rev; return ed.chipR(node, height || ed.chipH(node, mem), mem) }
    color: {
        _miniRoot.rev
        var hl = ed.styleVal(node, mem, "highlight", true)
        if (ed.fiveWayFormat(node) === "mini") {
            return on && hl ? ed.ink(ed.styleVal(node, mem, "hlColor", "#14532D")) : "transparent"
        }
        if (ed.chipIsHollow(node, mem)) return "transparent"
        return ed.ink(on && hl ? ed.styleVal(node, mem, "hlColor", "#14532D") : ed.styleVal(node, mem, "color", "#18181B"))
    }
    border.color: {
        _miniRoot.rev
        var hl = ed.styleVal(node, mem, "highlight", true)
        if (ed.fiveWayFormat(node) === "mini")
            return on && hl ? ed.ink(ed.styleVal(node, mem, "hlBorder", "#22C55E")) : "transparent"
        return ed.ink(on && hl ? ed.styleVal(node, mem, "hlBorder", "#22C55E") : ed.styleVal(node, mem, "border", "#3F3F46"))
    }
    border.width: { _miniRoot.rev; return ed.chipIsHollow(node, mem) ? 2 : 1 }
    antialiasing: true
    RigSelRing {
        on: {
            _miniRoot.rev
            return ed.isSelected(node.id) && !ed.exporting
        }
        ringColor: {
            _miniRoot.rev
            if (ed.groupEditId === node.id && ed.selectedMember === memberIndex)
                return "#38BDF8"
            return "#FBBF24"
        }
    }
    RigChipLabel {
        id: t
        // Fills the chip: its text is centred in the chip itself, as before.
        anchors.fill: parent
        ed: _miniRoot.ed
        node: _miniRoot.node
        mem: _miniRoot.mem
        rev: _miniRoot.rev
        color: {
            _miniRoot.rev
            var hl = ed.styleVal(node, mem, "highlight", true)
            return ed.ink(parent.on && hl ? ed.styleVal(node, mem, "hlText", "#BBF7D0") : ed.styleVal(node, mem, "textColor", "#E4E4E7"))
        }
        pixelSize: { _miniRoot.rev; return ed.uiPx(ed.isCircle(node, mem) ? ed.circleFont(node, mem) : ed.styleVal(node, mem, "fontSize", 10)) }
        visible: {
            _miniRoot.rev
            return !(ed.renameId === node.id && ed.renameMember === memberIndex)
        }
        text: {
            _miniRoot.rev
            var m = node && node.members ? node.members[memberIndex] : null
            return ed.chipText(node, m)
        }
    }
}
