// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// A drawing in the Button Map editor: shape, text box, table or image layer.
Item {
    id: _drawRoot
    property var ed: null
    property var node: ({ kind: "draw" })
    anchors.fill: parent
    Canvas {
        id: _dc
        visible: {
            var n = node
            return !!(n && n.shape !== "image" && n.shape !== "table" && n.shape !== "text")
        }
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            if (node && node.shape !== "image" && node.shape !== "table" && node.shape !== "text")
                ed.paintDraw(ctx, node, width, height)
        }
    }
    Item {
        id: _tableFace
        anchors.fill: parent
        clip: false
        visible: { ed.tick; return !!(node && node.shape === "table") }
        Repeater {
            model: {
                ed.tick
                var n = node
                if (!n || n.shape !== "table")
                    return 0
                var rows = (n.rows && n.rows.length) ? n.rows.length : 0
                var cols = (n.cols > 0) ? n.cols : 0
                return rows * cols
            }
            Rectangle {
                required property int index
                readonly property int row: {
                    var n = node
                    var cols = (n && n.cols > 0) ? n.cols : 2
                    return Math.floor(index / cols)
                }
                readonly property int col: {
                    var n = node
                    var cols = (n && n.cols > 0) ? n.cols : 2
                    return index % cols
                }
                x: {
                    ed.tick
                    var n = node
                    if (!n)
                        return 0
                    var g = ed.drawGeom(n)
                    return ed.tableCellRect(n, row, col).x - g.x
                }
                y: {
                    ed.tick
                    var n = node
                    if (!n)
                        return 0
                    var g = ed.drawGeom(n)
                    return ed.tableCellRect(n, row, col).y - g.y
                }
                width: {
                    ed.tick
                    return node ? ed.tableCellRect(node, row, col).w : 8
                }
                height: {
                    ed.tick
                    return node ? ed.tableCellRect(node, row, col).h : 8
                }
                color: {
                    ed.tick
                    return ed.tableCellStyle(node, col).fill
                }
                border.color: {
                    ed.tick
                    var sel = ed.isSelected(node.id) && ed.tableRow === row && ed.tableCol === col
                    return sel ? "#FBBF24" : ed.tableCellStyle(node, col).border
                }
                border.width: {
                    ed.tick
                    var sel = ed.isSelected(node.id) && ed.tableRow === row && ed.tableCol === col
                    return sel ? 2 : 1
                }
                Text {
                    renderType: Text.NativeRendering
                    anchors.fill: parent
                    anchors.margins: Style.dp(3)
                    visible: {
                        ed.tick
                        return !(ed.renameId === node.id && ed.tableRow === row && ed.tableCol === col)
                    }
                    text: {
                        ed.tick
                        return ed.tableCellText(node, row, col)
                    }
                    color: {
                        ed.tick
                        return ed.tableCellStyle(node, col).text
                    }
                    font.pixelSize: { ed.tick; return ed.uiPx((node && node.fontSize) ? node.fontSize : 10) }
                    elide: Text.ElideRight
                    wrapMode: Text.NoWrap
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                Repeater {
                    model: {
                        ed.tick
                        var n = node
                        var on = ed.interactive && n && ed.isSelected(n.id) && !ed.isLocked(n)
                        on = on && ed.tableExtra < 0 && ed.tableRow === row && ed.tableCol === col
                        on = on && ed.tableCellIsFree(n, row, col)
                        return on ? 8 : 0
                    }
                    Rectangle {
                        required property int index
                        width: Style.dp(8)
                        height: Style.dp(8)
                        radius: Style.dp(1)
                        z: 6
                        color: "#FBBF24"
                        border.color: "#18181B"
                        x: {
                            var xs = [0, parent.width, 0, parent.width, parent.width * 0.5, parent.width * 0.5, 0, parent.width]
                            return xs[index] - 4
                        }
                        y: {
                            var ys = [0, 0, parent.height, parent.height, 0, parent.height, parent.height * 0.5, parent.height * 0.5]
                            return ys[index] - 4
                        }
                    }
                }
            }
        }
        Repeater {
            model: {
                ed.tick
                var n = node
                if (!n || n.shape !== "table" || !n.extras)
                    return 0
                return n.extras.length
            }
            Rectangle {
                required property int index
                x: {
                    ed.tick
                    var n = node
                    if (!n)
                        return 0
                    var g = ed.drawGeom(n)
                    return ed.tableExtraRect(n, index).x - g.x
                }
                y: {
                    ed.tick
                    var n = node
                    if (!n)
                        return 0
                    var g = ed.drawGeom(n)
                    return ed.tableExtraRect(n, index).y - g.y
                }
                width: {
                    ed.tick
                    return node ? ed.tableExtraRect(node, index).w : 8
                }
                height: {
                    ed.tick
                    return node ? ed.tableExtraRect(node, index).h : 8
                }
                color: {
                    ed.tick
                    return ed.tableCellStyle(node, -1).fill
                }
                border.color: {
                    ed.tick
                    var sel = ed.isSelected(node.id) && ed.tableExtra === index
                    return sel ? "#FBBF24" : ed.tableCellStyle(node, -1).border
                }
                border.width: {
                    ed.tick
                    return (ed.isSelected(node.id) && ed.tableExtra === index) ? 2 : 1
                }
                Text {
                    renderType: Text.NativeRendering
                    anchors.fill: parent
                    anchors.margins: Style.dp(3)
                    visible: {
                        ed.tick
                        return !(ed.renameId === node.id && ed.tableExtra === index)
                    }
                    text: {
                        ed.tick
                        var e = node && node.extras ? node.extras[index] : null
                        return e && e.text ? e.text : ""
                    }
                    color: {
                        ed.tick
                        return ed.tableCellStyle(node, -1).text
                    }
                    font.pixelSize: { ed.tick; return ed.uiPx((node && node.fontSize) ? node.fontSize : 10) }
                    elide: Text.ElideRight
                    wrapMode: Text.NoWrap
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                Repeater {
                    model: {
                        ed.tick
                        return (ed.interactive && node && ed.isSelected(node.id) && !ed.isLocked(node) && ed.tableExtra === index) ? 8 : 0
                    }
                    Rectangle {
                        required property int index
                        width: Style.dp(8)
                        height: Style.dp(8)
                        radius: Style.dp(1)
                        z: 6
                        color: "#FBBF24"
                        border.color: "#18181B"
                        x: {
                            var xs = [0, parent.width, 0, parent.width, parent.width * 0.5, parent.width * 0.5, 0, parent.width]
                            return xs[index] - 4
                        }
                        y: {
                            var ys = [0, 0, parent.height, parent.height, 0, parent.height, parent.height * 0.5, parent.height * 0.5]
                            return ys[index] - 4
                        }
                    }
                }
            }
        }
    }
    Item {
        visible: {
            ed.tick
            return !!(node && node.shape === "text")
        }
        anchors.fill: parent
        Rectangle {
            anchors.fill: parent
            color: {
                ed.tick
                var n = node
                if (!n)
                    return "#18181B"
                if (n.theme)
                    return ed.textThemeStyle(n).fill
                return n.color || "#18181B"
            }
            opacity: {
                ed.tick
                var n = node
                if (n && n.fillOpacity !== undefined && n.fillOpacity !== null)
                    return n.fillOpacity
                return 1
            }
        }
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: {
                ed.tick
                var n = node
                if (!n)
                    return "#3F3F46"
                if (n.theme)
                    return ed.textThemeStyle(n).border
                return n.border || "#3F3F46"
            }
            border.width: { ed.tick; return (node && node.stroke) ? node.stroke : 1 }
            opacity: {
                ed.tick
                var n = node
                if (n && n.borderOpacity !== undefined && n.borderOpacity !== null)
                    return n.borderOpacity
                return 1
            }
        }
        Text {
            renderType: Text.NativeRendering
            anchors.fill: parent
            anchors.margins: Style.dp(4)
            visible: {
                ed.tick
                return !(ed.renameId === node.id)
            }
            text: {
                ed.tick
                return (node && node.text) ? node.text : "Text"
            }
            color: {
                ed.tick
                var n = node
                if (!n)
                    return "#E4E4E7"
                if (n.theme)
                    return ed.textThemeStyle(n).text
                return n.textColor || "#E4E4E7"
            }
            font.pixelSize: { ed.tick; return ed.uiPx((node && node.fontSize) ? node.fontSize : 12) }
            font.bold: { ed.tick; return !!(node && node.bold) }
            wrapMode: {
                ed.tick
                return (node && node.wrap === false) ? Text.NoWrap : Text.WordWrap
            }
            elide: Text.ElideRight
            horizontalAlignment: {
                ed.tick
                var a = node && node.align ? node.align : "center"
                if (a === "left") return Text.AlignLeft
                if (a === "right") return Text.AlignRight
                return Text.AlignHCenter
            }
            verticalAlignment: {
                ed.tick
                var a = node && node.valign ? node.valign : "middle"
                if (a === "top") return Text.AlignTop
                if (a === "bottom") return Text.AlignBottom
                return Text.AlignVCenter
            }
        }
    }
    Connections {
        target: ed
        function onTickChanged() { if (_dc.visible) _dc.requestPaint() }
    }
    Image {
        visible: { var n = node; return !!(n && n.shape === "image") }
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: {
            ed.tick
            var n = node || {}
            return n.srcUrl || ""
        }
    }
    Repeater {
        model: {
            ed.tick
            var n = node
            return (n && n.sockets) ? n.sockets.length : 0
        }
        Rectangle {
            required property int index
            width: Style.dp(8)
            height: Style.dp(8)
            radius: Style.dp(4)
            color: "#F4F4F5"
            border.color: "#18181B"
            border.width: Style.dp(1)
            z: 5
            x: {
                var n = node
                if (!n || !n.sockets || index >= n.sockets.length)
                    return 0
                return n.sockets[index].ux * _drawRoot.width - 4
            }
            y: {
                var n = node
                if (!n || !n.sockets || index >= n.sockets.length)
                    return 0
                return n.sockets[index].uy * _drawRoot.height - 4
            }
        }
    }
    // Resize handles: eight on a box, one on each end of a line.
    Repeater {
        model: (ed.interactive && node && ed.isSelected(node.id) && !ed.isLocked(node) && !ed.tableCellHandlesOn(node))
            ? (ed.isLine(node) ? 2 : 8) : 0
        Rectangle {
            required property int index
            readonly property var lineEnds: {
                ed.tick
                return ed.isLine(_drawRoot.node) ? (_drawRoot.node.ends || [0, 0.5, 1, 0.5]).slice() : null
            }
            width: Style.dp(8)
            height: Style.dp(8)
            radius: lineEnds ? width / 2 : Style.dp(1)
            color: "#FBBF24"
            border.color: "#18181B"
            x: {
                if (lineEnds)
                    return lineEnds[index * 2] * _drawRoot.width - 4
                var xs = [0, _drawRoot.width, 0, _drawRoot.width, _drawRoot.width * 0.5, _drawRoot.width * 0.5, 0, _drawRoot.width]
                return xs[index] - 4
            }
            y: {
                if (lineEnds)
                    return lineEnds[index * 2 + 1] * _drawRoot.height - 4
                var ys = [0, 0, _drawRoot.height, _drawRoot.height, 0, _drawRoot.height, _drawRoot.height * 0.5, _drawRoot.height * 0.5]
                return ys[index] - 4
            }
            z: 4
        }
    }
}
