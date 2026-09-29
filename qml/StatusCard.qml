// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
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
    property bool pinActive: false
    property bool hoverPeek: true
    property int stackIndex: 0
    property bool stacked: false
    property bool lifting: false
    property bool resizing: false
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
    signal pinControlDisplay()
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
    signal clearSettings()
    signal deleteDevice()
    signal unstackCard()
    signal unstackAllCards()
    signal shiftToggled()
    signal stackSelectedCards()

    implicitHeight: _body.implicitHeight + 20
    radius: 4
    clip: true
    color: selected ? "#1F2A37" : "#18181B"
    border.width: focused || selected || dropStacking ? 2 : 1
    border.color: dropStacking ? "#22C55E" : (focused || selected ? "#E4E4E7" : "#3F3F46")

    ColumnLayout {
        id: _body
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        Item {
            id: _photoWell
            visible: !_card.compactView
            Layout.fillWidth: true
            Layout.fillHeight: stretchPhoto && !_card.compactView
            Layout.minimumHeight: _card.compactView ? 0 : 72
            Layout.preferredHeight: {
                if (_card.compactView)
                    return 0
                if (_photo.status === Image.Ready && _photo.implicitWidth > 0) {
                    var ratio = _photo.implicitHeight / _photo.implicitWidth
                    return Math.round(Math.min(280, Math.max(96, width * ratio)))
                }
                return 120
            }
            Layout.maximumHeight: _card.compactView ? 0 : 100000

            Rectangle {
                anchors.fill: parent
                color: "#09090B"
                border.color: "#3F3F46"
                border.width: 1
                radius: 2

                Image {
                    id: _photo
                    anchors.fill: parent
                    anchors.margins: 2
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
                    font.pixelSize: 11
                }

                Rectangle {
                    visible: pinActive || (hoverPeek && _hover.hovered)
                    anchors.fill: parent
                    color: "#AA14532D"
                    Label {
                        anchors.centerIn: parent
                        text: pinActive ? "Control Display pinned" : "Control Display"
                        color: "#BBF7D0"
                        font.pixelSize: 11
                    }
                }
            }

            HoverHandler { id: _hover }
        }

        Label {
            text: cardName
            color: "#E4E4E7"
            font.pixelSize: 14
            font.bold: true
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        Label {
            text: status + " · " + bus
            color: "#A1A1AA"
            font.pixelSize: 11
        }

        Label {
            visible: isModule
            text: buttons + " buttons  " + axes + " axes  " + hats + " hats"
            color: "#E4E4E7"
            font.pixelSize: 11
        }

        Label {
            text: "Bound to: [" + (target.length ? target : "Not bound") + "]"
            color: "#A1A1AA"
            font.pixelSize: 11
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
            font.pixelSize: 11
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
        enabled: !_card.resizing

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
                Qt.callLater(function() {
                    _card.dropAt(sx, sy)
                })
                return
            }
            if (button === Qt.RightButton) {
                // Open after this release. Opening during the release makes
                // Qt treat it as a click outside and close the menu at once.
                Qt.callLater(function() {
                    _menu.popup(_grab, px, py)
                })
                return
            }
            if (shift)
                _card.shiftToggled()
            else
                _card.cardFocused()
        }
        onCanceled: function() {
            didDrag = false
            _card.lifting = false
        }
        onDoubleClicked: function(mouse) {
            if (mouse.button === Qt.LeftButton && !didDrag)
                _card.openConfiguration()
        }
    }

    Rectangle {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 6
        width: 20
        height: 20
        radius: 2
        z: 6
        color: _hideHover.hovered ? "#3F3F46" : "#00000000"
        border.color: "#3F3F46"
        border.width: 1

        Label {
            anchors.centerIn: parent
            text: "×"
            color: "#A1A1AA"
            font.pixelSize: 12
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
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        y: _body.y + _photoWell.y + _photoWell.height - 34
        height: 28
        text: "Output View"
        onClicked: _card.openOutputView()
    }

    function _clampW(w) { return Math.max(220, Math.min(720, w)) }
    function _clampH(h) { return Math.max(140, Math.min(520, h)) }

    MouseArea {
        id: _east
        z: 20
        width: 10
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.bottomMargin: 16
        cursorShape: Qt.SizeHorCursor
        onPressed: function() { _card.resizing = true; _card.lifting = false }
        onCanceled: function() { _card.resizing = false }
        onPositionChanged: function(mouse) {
            if (pressed)
                _card.width = _card._clampW(_card.width + mouse.x - width / 2)
        }
        onReleased: function() {
            _card.resizing = false
            _card.sizeChanged(Math.round(_card.width), Math.round(_card.height))
        }
    }
    MouseArea {
        id: _south
        z: 20
        height: 10
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 16
        cursorShape: Qt.SizeVerCursor
        onPressed: function() { _card.resizing = true; _card.lifting = false }
        onCanceled: function() { _card.resizing = false }
        onPositionChanged: function(mouse) {
            if (pressed)
                _card.height = _card._clampH(_card.height + mouse.y - height / 2)
        }
        onReleased: function() {
            _card.resizing = false
            _card.sizeChanged(Math.round(_card.width), Math.round(_card.height))
        }
    }
    MouseArea {
        id: _corner
        z: 21
        width: 18
        height: 18
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        cursorShape: Qt.SizeFDiagCursor
        onPressed: function() { _card.resizing = true; _card.lifting = false }
        onCanceled: function() { _card.resizing = false }
        onPositionChanged: function(mouse) {
            if (pressed) {
                _card.width = _card._clampW(_card.width + mouse.x - width / 2)
                _card.height = _card._clampH(_card.height + mouse.y - height / 2)
            }
        }
        onReleased: function() {
            _card.resizing = false
            _card.sizeChanged(Math.round(_card.width), Math.round(_card.height))
        }
        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 3
            width: 10
            height: 10
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
        MenuItem {
            visible: direction !== "dest"
            height: visible ? implicitHeight : 0
            text: pinActive ? "Unpin Control Display" : "Pin Control Display"
            onTriggered: _card.pinControlDisplay()
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
                leftPadding: 12
                rightPadding: 12
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
