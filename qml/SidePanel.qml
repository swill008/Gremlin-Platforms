// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.Style

// A fixed side panel of the Button Map (07 S128-S131): Chips on the left,
// Layers on the right. Folded, it is a slim strip on its edge with its name
// written vertically; a click on the strip brings the panel out beside it at
// its last width. Its header has the name, a pin and a fold arrow; its inner
// edge resizes it (minWidth..maxWidth). It can't be dragged, floated or
// locked.
//
// Unpinned and open it is drawn over the map (`overlay`) and folds when the
// window calls foldIfUnpinned() (a map click, the other strip's click).
// Pinned and open it takes `takenWidth` beside the map, which the window
// narrows by it. The window anchors it to its edge, full height; its width
// is the strip plus the open panel.
//
// changed() is emitted after a change made from here (strip, pin, fold
// arrow, resize, toggle/fold/unfold/foldIfUnpinned), for the window to save;
// setting the properties directly (restoring, the window's own folds) does
// not emit it.
//
//   SidePanel { side: "left"; title: "Chips"; panelWidth: Style.dp(260); ChipPool { anchors.fill: parent } }
Item {
    id: _side

    property string side: "left"
    property string title: ""
    property bool pinned: false
    property bool open: false
    // Its open width: a plain value (the window sets it from the kept state;
    // a binding here would be overwritten). 0 until set: Style.dp(260).
    property real panelWidth: 0
    property real minWidth: Style.dp(180)
    property real maxWidth: Style.dp(520)
    // False hides it, strip and all (outside Edit, S130).
    property bool available: true
    readonly property bool overlay: open && !pinned
    default property alias content: _body.data
    Component.onCompleted: {
        if (!(panelWidth > 0))
            panelWidth = Style.dp(260)
    }

    readonly property real stripWidth: Style.dp(22)
    readonly property real headerHeight: Style.dp(28)
    // Mid-resize: the width so far (kept on release).
    property real liveWidth: -1
    // The open panel's width, kept between minWidth and maxWidth.
    readonly property real shownWidth: {
        var w = liveWidth >= 0 ? liveWidth : panelWidth
        return Math.max(minWidth, Math.min(w, Math.max(minWidth, maxWidth)))
    }
    // What it takes from the map area's width.
    readonly property real takenWidth: !available ? 0
                                       : (pinned && open ? stripWidth + shownWidth : stripWidth)
    readonly property bool _left: side !== "right"

    signal changed()
    // The strip was clicked (after it unfolded or folded the panel).
    signal stripClicked()

    function unfold() {
        if (open)
            return
        open = true
        changed()
    }
    function fold() {
        if (!open)
            return
        open = false
        changed()
    }
    function toggle() {
        open = !open
        changed()
    }
    // A map click or the other strip's click: an unpinned panel folds.
    function foldIfUnpinned() {
        if (open && !pinned)
            fold()
    }

    visible: available
    implicitWidth: available ? stripWidth + (open ? shownWidth : 0) : 0
    width: implicitWidth

    // The strip on its edge.
    Rectangle {
        id: _strip
        objectName: "sideStrip"
        x: _side._left ? 0 : _side.width - width
        width: _side.stripWidth
        height: _side.height
        color: _stripArea.containsMouse ? Style.bgHover : Style.bgRaised

        // Its line on the map side, and the accent on its outer edge while open.
        Rectangle {
            x: _side._left ? parent.width - 1 : 0
            width: 1
            height: parent.height
            color: Style.line
        }
        Rectangle {
            visible: _side.open
            x: _side._left ? 0 : parent.width - width
            width: Style.dp(2)
            height: parent.height
            color: Style.accent
        }
        Label {
            objectName: "sideStripTitle"
            anchors.centerIn: parent
            rotation: _side._left ? -90 : 90
            text: _side.title
            font.pixelSize: Style.dp(12)
            color: _side.open || _stripArea.containsMouse ? Style.fg : Style.fgMuted
        }
        MouseArea {
            id: _stripArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                _side.toggle()
                _side.stripClicked()
            }
        }
        ToolTip.visible: _stripArea.containsMouse && !_side.open
        ToolTip.text: "Show the " + _side.title.toLowerCase()
    }

    // The open panel, beside the strip on the map side.
    Item {
        id: _panel
        objectName: "sidePanelBody"
        visible: _side.open
        x: _side._left ? _side.stripWidth : 0
        width: _side.shownWidth
        height: _side.height

        Rectangle {
            anchors.fill: parent
            color: Style.bgCard
            border.color: Style.lineStrong
            border.width: 1
        }
        // Presses the content doesn't take stop here (not on the map below).
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            onWheel: (w) => w.accepted = true
        }

        // The header: its name, the pin and the fold arrow.
        Rectangle {
            id: _header
            x: 1
            y: 1
            width: parent.width - 2
            height: _side.headerHeight - 1
            color: Style.bgRaised

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Style.line
            }
            Label {
                objectName: "sideTitle"
                anchors.verticalCenter: parent.verticalCenter
                x: Style.dp(10)
                width: parent.width - x - _icons.width - Style.dp(16)
                elide: Text.ElideRight
                text: _side.title
                color: Style.fg
                font.pixelSize: Style.dp(12)
                font.bold: true
            }
            Row {
                id: _icons
                anchors.right: parent.right
                anchors.rightMargin: Style.dp(8)
                anchors.verticalCenter: parent.verticalCenter
                spacing: Style.dp(10)
                component HeaderIcon: Label {
                    id: _icon
                    property alias area: _iconArea
                    signal clicked()
                    font.family: Style.iconFont
                    font.pixelSize: Style.dp(12)
                    MouseArea {
                        id: _iconArea
                        anchors.fill: parent
                        anchors.margins: -Style.dp(4)
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _icon.clicked()
                    }
                }
                HeaderIcon {
                    objectName: "sidePin"
                    text: _side.pinned ? "" : ""
                    color: _side.pinned ? Style.accent : (area.containsMouse ? Style.fg : Style.fgMuted)
                    onClicked: {
                        _side.pinned = !_side.pinned
                        _side.changed()
                    }
                    ToolTip.visible: area.containsMouse
                    ToolTip.text: _side.pinned ? "Unpin: slides out over the map and folds when you click the map"
                                               : "Pin: stays out beside the map"
                }
                HeaderIcon {
                    objectName: "sideFold"
                    // Points to its edge: chevron-left / chevron-right.
                    text: _side._left ? "" : ""
                    color: area.containsMouse ? Style.fg : Style.fgMuted
                    onClicked: _side.fold()
                    ToolTip.visible: area.containsMouse
                    ToolTip.text: "Fold"
                }
            }
        }

        Item {
            id: _body
            objectName: "sideContent"
            x: 1
            y: _side.headerHeight
            width: parent.width - 2
            height: parent.height - _side.headerHeight - 1
            clip: true
        }

        // The inner edge resizes it.
        MouseArea {
            id: _grip
            objectName: "sideGrip"
            readonly property real grip: Style.dp(6)
            x: _side._left ? parent.width - grip : 0
            width: grip
            height: parent.height
            hoverEnabled: true
            preventStealing: true
            cursorShape: Qt.SizeHorCursor
            property real startX: 0
            property real startWidth: 0
            onPressed: (m) => {
                startX = mapToItem(null, m.x, m.y).x
                startWidth = _side.shownWidth
            }
            onPositionChanged: (m) => {
                if (!pressed)
                    return
                var dx = mapToItem(null, m.x, m.y).x - startX
                _side.liveWidth = startWidth + (_side._left ? dx : -dx)
            }
            onReleased: {
                var w = _side.shownWidth
                _side.liveWidth = -1
                _side.panelWidth = w
                _side.changed()
            }
            onCanceled: _side.liveWidth = -1
        }
    }
}
