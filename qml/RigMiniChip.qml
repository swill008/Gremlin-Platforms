// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// One member chip inside a group in the Button Map editor.
Rectangle {
    property var ed: null
    property int hwId: 0
    property var node: ({})
    property int memberIndex: -1
    property string leafKind: "btn"
    property bool on: ed.litOf(leafKind, hwId)
    readonly property var mem: {
        ed.tick
        return (node && node.members && memberIndex >= 0) ? node.members[memberIndex] : null
    }
    width: implicitWidth
    height: implicitHeight
    implicitWidth: { ed.tick; return t.implicitWidth + ed.uiPx(Math.max(10, ed.styleVal(node, mem, "chipSize", 18) * 0.55)) }
    implicitHeight: { ed.tick; return ed.chipH(node, mem) }
    radius: { ed.tick; return ed.chipR(node, height || ed.chipH(node, mem), mem) }
    color: {
        ed.tick
        var hl = ed.styleVal(node, mem, "highlight", true)
        if (ed.fiveWayFormat(node) === "mini") {
            return on && hl ? ed.styleVal(node, mem, "hlColor", "#14532D") : "transparent"
        }
        if (ed.chipIsHollow(node, mem)) return "transparent"
        return on && hl ? ed.styleVal(node, mem, "hlColor", "#14532D") : ed.styleVal(node, mem, "color", "#18181B")
    }
    border.color: {
        ed.tick
        var hl = ed.styleVal(node, mem, "highlight", true)
        if (ed.fiveWayFormat(node) === "mini")
            return on && hl ? ed.styleVal(node, mem, "hlBorder", "#22C55E") : "transparent"
        return on && hl ? ed.styleVal(node, mem, "hlBorder", "#22C55E") : ed.styleVal(node, mem, "border", "#3F3F46")
    }
    border.width: { ed.tick; return ed.chipIsHollow(node, mem) ? 2 : 1 }
    antialiasing: true
    RigSelRing {
        on: {
            ed.tick
            return ed.isSelected(node.id)
        }
        ringColor: {
            ed.tick
            if (ed.groupEditId === node.id && ed.selectedMember === memberIndex)
                return "#38BDF8"
            return "#FBBF24"
        }
    }
    Text {
        renderType: Text.NativeRendering
        id: t
        anchors.centerIn: parent
        color: {
            ed.tick
            var hl = ed.styleVal(node, mem, "highlight", true)
            return parent.on && hl ? ed.styleVal(node, mem, "hlText", "#BBF7D0") : ed.styleVal(node, mem, "textColor", "#E4E4E7")
        }
        font.pixelSize: { ed.tick; return ed.uiPx(ed.styleVal(node, mem, "fontSize", 10)) }
        visible: {
            ed.tick
            return !(ed.renameId === node.id && ed.renameMember === memberIndex)
        }
        text: {
            ed.tick
            var m = node && node.members ? node.members[memberIndex] : null
            return ed.memberLabel(node, m)
        }
    }
}
