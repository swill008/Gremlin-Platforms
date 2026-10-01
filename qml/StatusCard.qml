// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Style

Rectangle {
    id: _card

    property string slug: ""
    property string cardName: ""
    property string rawName: ""
    property string guid: ""
    property string direction: "source"
    property string status: "Stub"
    property string bus: ""
    property int buttons: 0
    property int axes: 0
    property int hats: 0
    property string photo: ""
    property bool isStub: true
    property bool isModule: false
    property string tab: "physical"
    property string target: ""
    property string lastLine: ""
    property string lastHardware: ""
    property bool focused: false
    property int stackIndex: 0
    property bool stacked: false
    property bool lifting: false
    property bool resizing: false
    // Live size while a resize handle is dragged. The page shows it only during the
    // drag; otherwise the card follows its pile's saved size (width/height stay bound).
    property real liveW: 0
    property real liveH: 0
    property bool dropStacking: false
    property bool selected: false
    property bool canStackSelected: false
    property bool stretchPhoto: false
    property bool compactView: false
    z: stackIndex + (lifting || resizing ? 100 : 0)

    signal cardFocused()
    signal openConfiguration()
    signal openButtonMap()
    signal openOutputView()
    signal configureModule()
    signal autoMap()
    signal openDeviceViewer()
    signal openPairing()
    signal openCalibration()
    signal openDeviceInformation()
    signal assignHardware()
    signal ignoreDevice()
    signal dropAt(real sx, real sy)
    signal dragStarted()
    signal dragMovedAt(real sx, real sy)
    signal sizeChanged(int w, int h)
    signal resetSize()
    signal resetAllSizes()
    signal clearSettings()
    signal deleteDevice()
    signal unstackCard()
    signal unstackAllCards()
    signal shiftToggled()
    signal stackSelectedCards()

    implicitHeight: _body.implicitHeight + Style.dp(20)
    radius: Style.dp(4)
    clip: true
    color: selected ? "#1F2A37" : "#18181B"
    border.width: focused || selected || dropStacking ? Style.dp(2) : Style.dp(1)
    border.color: dropStacking ? "#22C55E" : (focused || selected ? "#E4E4E7" : "#3F3F46")

    ColumnLayout {
        id: _body
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        spacing: Style.dp(6)

        Item {
            id: _photoWell
            visible: !_card.compactView
            Layout.fillWidth: true
            Layout.fillHeight: stretchPhoto && !_card.compactView
            Layout.minimumHeight: _card.compactView ? 0 : Style.dp(72)
            Layout.preferredHeight: {
                if (_card.compactView)
                    return 0
                if (_photo.status === Image.Ready && _photo.implicitWidth > 0) {
                    var ratio = _photo.implicitHeight / _photo.implicitWidth
                    return Math.round(Math.min(Style.dp(280), Math.max(Style.dp(96), width * ratio)))
                }
                return Style.dp(120)
            }
            Layout.maximumHeight: _card.compactView ? 0 : Style.dp(100000)

            Rectangle {
                anchors.fill: parent
                color: "#09090B"
                border.color: "#3F3F46"
                border.width: Style.dp(1)
                radius: Style.dp(2)

                Image {
                    id: _photo
                    anchors.fill: parent
                    anchors.margins: Style.dp(2)
                    source: photo
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    cache: true
                    visible: photo && photo.length
                    onStatusChanged: _photoWell.Layout.preferredHeightChanged()
                    onImplicitWidthChanged: _photoWell.Layout.preferredHeightChanged()
                }

                Label {
                    anchors.centerIn: parent
                    visible: !(photo && photo.length)
                    text: isStub ? "No module photo" : "No photo"
                    color: "#A1A1AA"
                    font.pixelSize: Style.dp(11)
                }
            }
        }

        Label {
            text: cardName
            color: "#E4E4E7"
            font.pixelSize: Style.dp(14)
            font.bold: true
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        Label {
            text: status + " · " + bus
            color: "#A1A1AA"
            font.pixelSize: Style.dp(11)
        }

        Label {
            visible: isModule
            text: buttons + " buttons  " + axes + " axes  " + hats + " hats"
            color: "#E4E4E7"
            font.pixelSize: Style.dp(11)
        }

        Label {
            text: "Bound to: [" + (target.length ? target : "Not bound") + "]"
            color: "#A1A1AA"
            font.pixelSize: Style.dp(11)
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            HoverHandler { id: _boundHover }
            PointerTip {
                text: target
                show: target.length > 0
            }
        }

        Label {
            text: lastLine.length ? ("last: " + lastLine) : "last: —"
            color: "#E4E4E7"
            font.pixelSize: Style.dp(11)
            elide: Text.ElideRight
            Layout.fillWidth: true

            HoverHandler { id: _lastHover }
            PointerTip {
                text: lastHardware
                show: lastHardware.length > 0
            }
        }
    }

    MouseArea {
        id: _grab
        z: 5
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        // Do not drag this item. It lives in a Flow; moving it there
        // reflows the parent and the drop target chases itself.
        preventStealing: true
        property bool didDrag: false
        property bool shiftHeld: false
        property int pressButton: Qt.LeftButton
        property real pressX: 0
        property real pressY: 0
        property real lastSx: 0
        property real lastSy: 0
        // The card counts double-clicks itself: Qt did not report them on output
        // cards with pictures. Every card opens the same way.
        property real lastClickAt: 0
        property real lastClickX: 0
        property real lastClickY: 0
        enabled: !_card.resizing

        function isSecondClick(x, y) {
            var now = Date.now()
            var second = now - lastClickAt <= Qt.styleHints.mouseDoubleClickInterval
                && Math.abs(x - lastClickX) <= Style.dp(6)
                && Math.abs(y - lastClickY) <= Style.dp(6)
            lastClickAt = second ? 0 : now
            lastClickX = x
            lastClickY = y
            return second
        }

        onPressed: function(mouse) {
            didDrag = false
            shiftHeld = (mouse.modifiers & Qt.ShiftModifier) !== 0
            pressButton = mouse.button
            pressX = mouse.x
            pressY = mouse.y
        }
        onPositionChanged: function(mouse) {
            if (!pressed || pressButton !== Qt.LeftButton || shiftHeld)
                return
            if (!didDrag) {
                if (Math.abs(mouse.x - pressX) < 10 && Math.abs(mouse.y - pressY) < 10)
                    return
                didDrag = true
                // Lift only after the pointer moves. Lifting on the press
                // freezes the pane and cancels the click.
                _card.lifting = true
                _card.dragStarted()
            }
            var s = _grab.mapToItem(null, mouse.x, mouse.y)
            lastSx = s.x
            lastSy = s.y
            _card.dragMovedAt(s.x, s.y)
        }
        onReleased: function(mouse) {
            var dragged = didDrag
            var button = mouse.button
            var sx = lastSx
            var sy = lastSy
            var px = mouse.x
            var py = mouse.y
            var shift = shiftHeld || ((mouse.modifiers & Qt.ShiftModifier) !== 0)
            didDrag = false
            _card.lifting = false
            if (dragged) {
                lastClickAt = 0
                Qt.callLater(function() {
                    _card.dropAt(sx, sy)
                })
                return
            }
            if (button === Qt.RightButton) {
                lastClickAt = 0
                // Open after this release. Opening during the release makes
                // Qt treat it as a click outside and close the menu at once.
                Qt.callLater(function() {
                    _menu.popup(_grab, px, py)
                })
                return
            }
            if (shift) {
                lastClickAt = 0
                _card.shiftToggled()
                return
            }
            _card.cardFocused()
            if (button === Qt.LeftButton && isSecondClick(px, py))
                _card.openConfiguration()
        }
        onCanceled: function() {
            didDrag = false
            _card.lifting = false
        }
    }

    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: Style.dp(6)
        width: Style.dp(20)
        height: Style.dp(20)
        radius: Style.dp(2)
        z: 6
        color: _hideHover.hovered ? "#3F3F46" : "#00000000"
        border.color: "#3F3F46"
        border.width: Style.dp(1)

        Label {
            anchors.centerIn: parent
            text: "×"
            color: "#A1A1AA"
            font.pixelSize: Style.dp(12)
        }
        HoverHandler { id: _hideHover }
        MouseArea {
            anchors.fill: parent
            z: 7
            cursorShape: Qt.PointingHandCursor
            onClicked: _card.ignoreDevice()
        }
        PointerTip { text: "Hide device" }
    }

    Button {
        visible: _card.direction === "dest" && !_card.compactView
        z: 32
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Style.dp(16)
        anchors.rightMargin: Style.dp(16)
        y: _body.y + _photoWell.y + _photoWell.height - Style.dp(34)
        height: Style.dp(28)
        text: "Output View"
        onClicked: _card.openOutputView()
    }

    function _clampW(w) { return Math.max(220, Math.min(720, w)) }

    function _beginResize() {
        liveW = width
        liveH = height
        lifting = false
        resizing = true
    }

    function _endResize() {
        // Report first so the saved size is in place when the card stops resizing.
        sizeChanged(Math.round(liveW), Math.round(liveH))
        resizing = false
    }
    function _clampH(h) { return Math.max(140, Math.min(520, h)) }

    MouseArea {
        id: _east
        z: 20
        width: Style.dp(10)
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.bottomMargin: Style.dp(16)
        cursorShape: Qt.SizeHorCursor
        onPressed: function() { _card._beginResize() }
        onCanceled: function() { _card.resizing = false }
        onPositionChanged: function(mouse) {
            if (pressed)
                _card.liveW = _card._clampW(_card.liveW + mouse.x - width / 2)
        }
        onReleased: function() { _card._endResize() }
    }
    MouseArea {
        id: _south
        z: 20
        height: Style.dp(10)
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: Style.dp(16)
        cursorShape: Qt.SizeVerCursor
        onPressed: function() { _card._beginResize() }
        onCanceled: function() { _card.resizing = false }
        onPositionChanged: function(mouse) {
            if (pressed)
                _card.liveH = _card._clampH(_card.liveH + mouse.y - height / 2)
        }
        onReleased: function() { _card._endResize() }
    }
    MouseArea {
        id: _corner
        z: 21
        width: Style.dp(18)
        height: Style.dp(18)
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        cursorShape: Qt.SizeFDiagCursor
        onPressed: function() { _card._beginResize() }
        onCanceled: function() { _card.resizing = false }
        onPositionChanged: function(mouse) {
            if (pressed) {
                _card.liveW = _card._clampW(_card.liveW + mouse.x - width / 2)
                _card.liveH = _card._clampH(_card.liveH + mouse.y - height / 2)
            }
        }
        onReleased: function() { _card._endResize() }
        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: Style.dp(3)
            width: Style.dp(10)
            height: Style.dp(10)
            color: "#00000000"
            Canvas {
                anchors.fill: parent
                onPaint: {
                    var c = getContext("2d")
                    c.clearRect(0, 0, width, height)
                    c.strokeStyle = "#A1A1AA"
                    c.lineWidth = 1.5
                    c.beginPath(); c.moveTo(2, 10); c.lineTo(10, 2); c.stroke()
                    c.beginPath(); c.moveTo(6, 10); c.lineTo(10, 6); c.stroke()
                }
            }
        }
    }

    Menu {
        id: _menu
        // Keeps the menu inside the window near the bottom edge.
        margins: Style.dp(4)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        MenuItem {
            text: direction === "dest" ? "Output View" : "Open Configuration"
            onTriggered: direction === "dest" ? _card.openOutputView() : _card.openConfiguration()
        }
        MenuItem {
            text: "Button Map"
            onTriggered: _card.openButtonMap()
        }
        MenuItem {
            text: direction === "dest" ? "Configure output module" : "Configure input module"
            onTriggered: _card.configureModule()
        }
        MenuItem { text: "Auto Mapper"; onTriggered: _card.autoMap() }
        MenuItem {
            visible: direction !== "dest"
            height: visible ? implicitHeight : 0
            text: "Device Viewer"
            onTriggered: _card.openDeviceViewer()
        }
        MenuItem {
            text: (bus === "XInput" || tab === "xbox" || slug === "xbox") ? "Xbox Viewer" : "vJoy Viewer"
            onTriggered: _card.openPairing()
        }
        MenuItem {
            visible: direction !== "dest"
            height: visible ? implicitHeight : 0
            text: "Calibration"
            onTriggered: _card.openCalibration()
        }
        MenuItem { text: "Device Information"; onTriggered: _card.openDeviceInformation() }
        MenuItem {
            visible: direction !== "dest"
            height: visible ? implicitHeight : 0
            text: "Assign hardware…"
            onTriggered: _card.assignHardware()
        }
        MenuItem {
            visible: _card.canStackSelected
            height: visible ? implicitHeight : 0
            text: "Stack selected cards"
            onTriggered: _card.stackSelectedCards()
        }
        MenuItem {
            visible: stacked
            height: visible ? implicitHeight : 0
            text: "Unstack"
            onTriggered: _card.unstackCard()
        }
        MenuItem {
            visible: stacked
            height: visible ? implicitHeight : 0
            text: "Unstack all"
            onTriggered: _card.unstackAllCards()
        }
        MenuSeparator {}
        MenuItem { text: "Reset size"; onTriggered: _card.resetSize() }
        MenuItem { text: "Reset all card sizes"; onTriggered: _card.resetAllSizes() }
        MenuSeparator {}
        MenuItem { text: "Hide device"; onTriggered: _card.ignoreDevice() }
        MenuSeparator {}
        MenuItem { text: "Clear module settings"; onTriggered: _card.clearSettings() }
        MenuSeparator {}
        MenuItem {
            id: _deleteDeviceItem
            text: "Delete Device"
            onTriggered: _card.deleteDevice()
            contentItem: Label {
                text: _deleteDeviceItem.text
                color: "#F87171"
                font.bold: true
                leftPadding: Style.dp(12)
                rightPadding: Style.dp(12)
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
