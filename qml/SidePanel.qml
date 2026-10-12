// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import Gremlin.Style

// A fixed side panel of the Device Mapping Editor (07 S128-S131): Chips on the left,
// Layers on the right. It is a drawer on its edge of the window (S129,
// D-07-SIDE-DRAWER). Folded it is left ajar: the panel's own edge (its
// colour, border and rounded corners) peeks `stripWidth` out from the
// window's edge. On hover it slides out a little further and shows its bold
// name and its pin at the top of that slice; the pin pins without opening.
// A click slides it all the way out at its last width (about 0.12 s), and
// folding slides it back to the ajar edge. A soft shadow runs along its map
// side. Its header has the name, a pin and a fold arrow; its inner edge
// resizes it (minWidth..maxWidth). It can't be dragged, floated or locked.
//
// Unpinned and open it is drawn over the map (`overlay`) and folds when the
// window calls foldIfUnpinned() (a map click, the other drawer's click).
// Pinned and open it takes `takenWidth` (its open width) beside the map,
// which the window narrows by it; folded it takes the ajar edge. The window
// anchors it to its edge, full height. Its width and takenWidth take their
// final value at once; only the drawn drawer slides (the hover peek is drawn
// over the map), so the map doesn't jitter.
//
// changed() is emitted after a change made from here (drawer click, pin,
// fold arrow, resize, toggle/fold/unfold/foldIfUnpinned), for the window to
// save; setting the properties directly (restoring, the window's own folds)
// does not emit it.
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
    // False hides it, ajar edge and all (outside Edit, S130).
    property bool available: true
    readonly property bool overlay: open && !pinned
    default property alias content: _body.data
    Component.onCompleted: {
        if (!(panelWidth > 0))
            panelWidth = Style.dp(260)
    }

    // How far the folded drawer's edge peeks out of the window.
    readonly property real stripWidth: Style.dp(7)
    // How far it peeks on hover: enough for its name and pin.
    readonly property real hoverWidth: Math.max(Style.dp(24), _sliceRow.implicitWidth + 2 * Style.dp(8))
    readonly property real headerHeight: Style.dp(28)
    readonly property real cornerRadius: Style.dp(6)
    readonly property real shadowWidth: Style.dp(6)
    // Mid-resize: the width so far (kept on release).
    property real liveWidth: -1
    // The open panel's width, kept between minWidth and maxWidth.
    readonly property real shownWidth: {
        var w = liveWidth >= 0 ? liveWidth : panelWidth
        return Math.max(minWidth, Math.min(w, Math.max(minWidth, maxWidth)))
    }
    // What it takes from the map area's width.
    readonly property real takenWidth: !available ? 0
                                       : (pinned && open ? shownWidth : stripWidth)
    readonly property bool _left: side !== "right"
    // Folded and hovered: it peeks further and shows its name and pin.
    readonly property bool _peeking: !open && (_stripArea.containsMouse || _pinArea.containsMouse)
    // How far the folded drawer is out: the ajar edge, or further on hover.
    property real _peek: _peeking ? hoverWidth : stripWidth
    Behavior on _peek {
        NumberAnimation { duration: 120; easing.type: Easing.OutCubic }
    }
    // How far the drawer is open: 0 folded, 1 open; slides between them.
    property real _reveal: open ? 1 : 0
    Behavior on _reveal {
        NumberAnimation { duration: 120; easing.type: Easing.OutCubic }
    }
    // How much of the drawer shows from the window's edge: exactly
    // shownWidth when open, so a resize follows the pointer.
    readonly property real _out: _peek + _reveal * (shownWidth - _peek)

    signal changed()
    // The folded drawer was clicked (after it unfolded or folded the panel).
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
    // A map click or the other drawer's click: an unpinned panel folds.
    function foldIfUnpinned() {
        if (open && !pinned)
            fold()
    }

    visible: available
    implicitWidth: available ? (open ? shownWidth : stripWidth) : 0
    width: implicitWidth

    // Where the drawer is drawn: from the window's edge out to its open
    // width plus its shadow (over the map where that is wider than this
    // item). It hides the part of the drawer still behind the window's edge.
    Item {
        id: _slot
        width: _side.shownWidth + _side.shadowWidth
        x: _side._left ? 0 : _side.width - width
        height: _side.height
        clip: true

        // The drawer: one frame, open or ajar, slid out by _out.
        Item {
            id: _panel
            objectName: "sidePanelBody"
            x: _side._left ? _side._out - width : _slot.width - _side._out
            width: _side.shownWidth
            height: _side.height

            // Its soft shadow on the map side.
            Rectangle {
                id: _shadow
                objectName: "sideShadow"
                readonly property color dark: Style.alpha(Style.dim, Style.isDarkMode ? 0.45 : 0.16)
                x: _side._left ? parent.width : -width
                width: _side.shadowWidth
                height: parent.height
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: _side._left ? _shadow.dark : Style.clear }
                    GradientStop { position: 1; color: _side._left ? Style.clear : _shadow.dark }
                }
            }
            // Its frame, rounded on the map side.
            Rectangle {
                objectName: "sideFrame"
                anchors.fill: parent
                topLeftRadius: _side._left ? 0 : _side.cornerRadius
                bottomLeftRadius: topLeftRadius
                topRightRadius: _side._left ? _side.cornerRadius : 0
                bottomRightRadius: topRightRadius
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

            // The header: its name, the pin and the fold arrow. Hidden while
            // folded (the ajar edge is the frame alone).
            Rectangle {
                id: _header
                x: 1
                y: 1
                width: parent.width - 2
                height: _side.headerHeight - 1
                color: Style.bgRaised
                // Follows the frame's rounded corner on the map side.
                topLeftRadius: _side._left ? 0 : _side.cornerRadius - 1
                topRightRadius: _side._left ? _side.cornerRadius - 1 : 0
                visible: _side.open || _side._reveal > 0

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
                visible: _header.visible
            }

            // The inner edge resizes it (open only: folded, that edge is the
            // ajar drawer, which opens it).
            MouseArea {
                id: _grip
                objectName: "sideGrip"
                readonly property real grip: Style.dp(6)
                x: _side._left ? parent.width - grip : 0
                width: grip
                height: parent.height
                enabled: _side.open
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
            // The slice of the folded drawer that shows: the ajar edge, or
            // more on hover. A click opens (or folds) the drawer.
            Item {
                id: _strip
                objectName: "sideStrip"
                x: _side._left ? parent.width - width : 0
                width: _side._out
                height: parent.height
                visible: !_side.open

                MouseArea {
                    id: _stripArea
                    objectName: "sideStripArea"
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        _side.toggle()
                        _side.stripClicked()
                    }
                    ToolTip.visible: containsMouse && !_pinArea.containsMouse && !_side.open
                    ToolTip.text: "Show the " + _side.title.toLowerCase()
                }

                // On hover: its bold name and its pin across the top of the
                // slice (the pin pins without opening).
                Row {
                    id: _sliceRow
                    objectName: "sideSlice"
                    x: _side._left ? parent.width - width - Style.dp(8) : Style.dp(8)
                    y: Style.dp(8)
                    spacing: Style.dp(6)
                    // Shown by opacity (not visible) so its width, which
                    // sets hoverWidth, is known before the first hover.
                    readonly property bool shown: _side._peeking && _side._reveal === 0
                    opacity: shown ? 1 : 0
                    Label {
                        objectName: "sideStripTitle"
                        anchors.verticalCenter: parent.verticalCenter
                        text: _side.title
                        font.pixelSize: Style.dp(12)
                        font.bold: true
                        color: Style.fg
                    }
                    // Pin: stays out beside the map.
                    Label {
                        objectName: "sideStripPin"
                        anchors.verticalCenter: parent.verticalCenter
                        font.family: Style.iconFont
                        font.pixelSize: Style.dp(11)
                        text: _side.pinned ? "" : ""
                        color: _side.pinned ? Style.accent : (_pinArea.containsMouse ? Style.fg : Style.fgMuted)
                        MouseArea {
                            id: _pinArea
                            anchors.fill: parent
                            enabled: _sliceRow.shown
                            anchors.margins: -Style.dp(3)
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                _side.pinned = !_side.pinned
                                _side.changed()
                            }
                        }
                        ToolTip.visible: _pinArea.containsMouse
                        ToolTip.text: _side.pinned ? "Unpin: slides out over the map and folds when you click the map"
                                                   : "Pin: stays out beside the map"
                    }
                }
            }
        }
    }
}
