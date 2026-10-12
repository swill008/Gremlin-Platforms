// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Menus
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
    // The device has its own Device Image (an input module's uploaded
    // picture; the model's hasImage). The generated picture doesn't count.
    property bool hasImage: false
    property bool isStub: true
    // Why the module file can't be read ("" when it is fine).
    property string damaged: ""
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
    // The widest the card may be where it sits (the page's free width; 0 =
    // no limit): a resize never makes it wider than the window shows.
    property real fitWidth: 0
    property bool dropStacking: false
    property bool selected: false
    property bool canStackSelected: false
    // This card is in a selection of one or more (Hide Selected Cards,
    // Reset Size of Selected Cards; D-03-HOME-BAND).
    property bool canActOnSelected: false
    property bool stretchPhoto: false
    property bool compactView: false
    // Map to vJoy bindings from this device that can't be sent
    // (D-05-CANT-SEND): the count and the tip listing them.
    property int cantSendCount: 0
    property string cantSendTip: ""
    readonly property bool cantSendShown: cantSendCount > 0
    readonly property string cantSendText: cantSendCount <= 0 ? ""
        : "⚠ " + cantSendCount + (cantSendCount === 1 ? " output" : " outputs") + " not found"
    // The OSC card's second line (D-09-OSC-CARD-LINE): where the server
    // listens, the last message, or why it isn't open. Made for the OSC card
    // only.
    readonly property bool _isOsc: slug === "osc"
    // No button / axis / hat count line on these cards (03 S73).
    readonly property bool _noCounts: ["keyboard", "osc", "logical"].indexOf(tab) >= 0
                                      || ["keyboard", "osc", "logical"].indexOf(slug) >= 0
    readonly property QtObject _oscStatus: _oscMaker.object
    Instantiator {
        id: _oscMaker
        model: _card._isOsc ? 1 : 0
        delegate: OscCardStatus {}
    }
    z: stackIndex + (lifting || resizing ? 100 : 0)

    signal cardFocused()
    signal openDeviceBindings()
    signal openDeviceMappingEditor()
    signal openOutputView()
    signal configureModule()
    signal openAutoMappingTool()
    signal openPairing()
    signal openCalibration()
    signal openDeviceInformation()
    // The Device Library on this card's device: "copy", "swap" or "output".
    signal openDeviceLibrary(string action)
    signal ignoreDevice()
    signal dropAt(real sx, real sy)
    signal dragStarted()
    signal dragMovedAt(real sx, real sy)
    signal sizeChanged(int w, int h)
    signal resetSize()
    signal resetAllSizes()
    signal clearSettings()
    signal deleteDevice()
    signal startFresh()
    signal exportDevice()
    signal importDevice()
    // The card's picture: the Logical Device's own (03 S88, D-03-LD-IMAGE)
    // or an input module's Device Image.
    signal addImage()
    signal removeImage()
    signal unstackCard()
    signal unstackAllCards()
    signal shiftToggled()
    signal stackSelectedCards()
    signal hideSelectedCards()
    signal resetSelectedSizes()
    // Home's Undo / Redo, beside the menu's title (D-FIXLIST-B1 10).
    property bool canUndo: false
    property bool canRedo: false
    signal undoStep()
    signal redoStep()

    implicitHeight: _body.implicitHeight + Style.dp(20)
    radius: Style.dp(4)
    clip: true
    color: selected ? Style.bgSelected : Style.bgCard
    // Red wins over the picked and focus colours; picked or focused shows
    // as a thicker red outline.
    border.width: cantSendShown && !dropStacking
        ? (activeFocus || focused || selected ? Style.dp(3) : Style.dp(2))
        : (activeFocus || focused || selected || dropStacking ? Style.dp(2) : Style.dp(1))
    border.color: dropStacking ? Style.ok
        : cantSendShown ? Style.danger
        : (activeFocus ? Style.accent : (focused || selected ? Style.fg : Style.line))

    // Keyboard: Tab and the arrow keys move between cards, Enter opens
    // Device Bindings as a double-click does, Space picks the card as a click
    // does. A click never gives a card the keys: a stick button that sends
    // Return must not open windows.
    objectName: "statusCard"
    activeFocusOnTab: true
    Keys.onReturnPressed: openDeviceBindings()
    Keys.onEnterPressed: openDeviceBindings()
    Keys.onSpacePressed: cardFocused()
    Keys.onRightPressed: _focusNextCard(true)
    Keys.onDownPressed: _focusNextCard(true)
    Keys.onLeftPressed: _focusNextCard(false)
    Keys.onUpPressed: _focusNextCard(false)

    function _focusNextCard(forward) {
        var item = _card
        for (var i = 0; i < 500; i++) {
            item = item.nextItemInFocusChain(forward)
            if (!item || item === _card)
                return
            if (item.objectName === "statusCard") {
                item.forceActiveFocus(forward ? Qt.TabFocusReason : Qt.BacktabFocusReason)
                return
            }
        }
    }

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
                color: Style.bgWell
                border.color: Style.line
                border.width: Style.dp(1)
                radius: Style.dp(2)

                Image {
                    id: _photo
                    objectName: "cardPhoto"
                    anchors.fill: parent
                    anchors.margins: Style.dp(2)
                    // Not decoded while compact: the small thumb shows it then.
                    source: _card.compactView ? "" : photo
                    fillMode: Image.PreserveAspectFit
                    // Decoded no larger than a card can show (maxW x maxH, see
                    // _clampW/_clampH), not at the photo's full size. A fixed
                    // size, so resizing a card does not decode the photo again.
                    sourceSize: Qt.size(_card.maxW * Screen.devicePixelRatio, _card.maxH * Screen.devicePixelRatio)
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
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(11)
                }
            }
        }

        // Compact view: the device's small picture beside the text lines
        // (D-03-COMPACT-THUMB), its icon when it has none, as the Device
        // Library rows show it.
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)

            DeviceThumb {
                objectName: "cardThumb"
                visible: _card.compactView
                Layout.alignment: Qt.AlignTop
                source: _card.compactView ? _card.photo : ""
                glyph: _card.slug === "keyboard" ? "" : ""
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Style.dp(6)

                Label {
                    objectName: "cardTitle"
                    text: cardName
                    color: Style.fg
                    font.pixelSize: Style.dp(14)
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    PointerTip {
                        objectName: "cardTitleTip"
                        show: _card._isOsc
                        text: _card._isOsc ? "Open Sound Control (OSC)" : ""
                    }
                }

                Label {
                    objectName: "cardStatusLine"
                    readonly property bool oscLine: _card._oscStatus !== null
                    text: oscLine ? _card._oscStatus.text
                        : (status === "Stub" ? "No module" : status) + " · " + bus
                    color: _card.damaged !== "" ? Style.danger
                        : oscLine && _card._oscStatus.warn ? Style.warn
                        : Style.fgMuted
                    font.pixelSize: Style.dp(11)
                    // A long message is cut with "…" (other cards as before).
                    elide: oscLine ? Text.ElideRight : Text.ElideNone
                    Layout.fillWidth: oscLine
                }

                Label {
                    visible: _card.cantSendShown
                    text: _card.cantSendText
                    color: Style.danger
                    font.pixelSize: Style.dp(11)
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                    PointerTip {
                        text: _card.cantSendTip
                    }
                }

                Label {
                    // Claimed counts; with no module file, the device's own counts
                    // (D-03-Q8-NOFILE). The Keyboard, OSC and Logical Device
                    // cards hold many kinds of input, so they show none.
                    objectName: "cardCounts"
                    visible: !_card._noCounts
                             && (isModule || (isStub && tab === "physical"))
                    text: buttons + (buttons === 1 ? " button  " : " buttons  ")
                          + axes + (axes === 1 ? " axis  " : " axes  ")
                          + hats + (hats === 1 ? " hat" : " hats")
                    color: Style.fg
                    font.pixelSize: Style.dp(11)
                }

                Label {
                    // Output cards only: what feeds them (the glossary's Driven by).
                    visible: direction === "dest"
                    text: "Driven by: [" + (target.length ? target : "nothing") + "]"
                    color: Style.fgMuted
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
                    color: Style.fg
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
                // As the Device Bindings rows (ControlTree): a 4 dp move starts it.
                if (Math.abs(mouse.x - pressX) + Math.abs(mouse.y - pressY) < Style.dp(4))
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
                // The card the menu is for shows as picked, as a left click
                // does; a card in a Shift selection keeps the selection (the
                // menu can act on all of it).
                if (!_card.selected)
                    _card.cardFocused()
                // Open after this release. Opening during the release makes
                // Qt treat it as a click outside and close the menu at once.
                Qt.callLater(function() {
                    _menu.openAt(_grab, px, py)
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
                _card.openDeviceBindings()
        }
        onCanceled: function() {
            didDrag = false
            _card.lifting = false
        }
    }

    Button {
        id: _outputButton
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
        contentItem: Label {
            text: _outputButton.text
            color: Style.onColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: Style.dp(3)
            color: _outputButton.hovered || _outputButton.down ? Style.photoButtonHover : Style.photoButton
            border.width: _outputButton.visualFocus ? Style.dp(2) : 0
            border.color: Style.onColor
        }
    }

    // The card size limits (03 S83): 220-1080 wide, 140-780 tall, and never
    // wider than the page has room for (fitWidth).
    readonly property int minW: 220
    readonly property int maxW: 1080
    readonly property int minH: 140
    readonly property int maxH: 780
    function _clampW(w) {
        var most = fitWidth > 0 ? Math.max(minW, Math.min(maxW, fitWidth)) : maxW
        return Math.max(minW, Math.min(most, w))
    }

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
    function _clampH(h) { return Math.max(minH, Math.min(maxH, h)) }

    MouseArea {
        id: _east
        z: 20
        width: Style.dp(10)
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.bottomMargin: Style.dp(16)
        cursorShape: Qt.SizeHorCursor
        // Keep the drag: Home's scroll area would take it and scroll.
        preventStealing: true
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
        // Keep the drag: Home's scroll area would take it and scroll.
        preventStealing: true
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
        // Keep the drag: Home's scroll area would take it and scroll.
        preventStealing: true
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
            color: "transparent"
            Canvas {
                anchors.fill: parent
                // Repaint when Dark mode changes the colour.
                property color ink: Style.fgMuted
                onInkChanged: requestPaint()
                onPaint: {
                    var c = getContext("2d")
                    c.clearRect(0, 0, width, height)
                    c.strokeStyle = ink
                    c.lineWidth = 1.5
                    c.beginPath(); c.moveTo(2, 10); c.lineTo(10, 2); c.stroke()
                    c.beginPath(); c.moveTo(6, 10); c.lineTo(10, 6); c.stroke()
                }
            }
        }
    }

    // The card's right-click menu (Gremlin.Menus): the two main ways in and
    // Hide Card (the card has no × of its own), then sections for the
    // module, viewers, card layout and the device.
    function menuModel() {
        var dest = direction === "dest"
        var xbox = bus === "XInput" || tab === "xbox" || slug === "xbox"
        // The Keyboard and OSC aren't game controllers: the Device Library's
        // Copy / Swap / Change vJoy Output, the Auto Mapping Tool and Device
        // Information don't list them.
        var notStick = slug === "keyboard" || slug === "osc"
        // The Logical Device has no hardware to set up, calibrate, describe
        // or swap (03 Q7).
        var logical = tab === "logical" || slug === "logical"
        return MenuModel.menu("card", cardName || rawName || "Device", [
            MenuModel.action(dest ? "Output View" : "Open Device Bindings",
                             function() { dest ? _card.openOutputView() : _card.openDeviceBindings() }),
            MenuModel.action("Device Mapping Editor", function() { _card.openDeviceMappingEditor() }),
            MenuModel.action("Hide Card", function() { _card.ignoreDevice() })
        ], [
            MenuModel.section("module", "Module", [
                // The Xbox output claims nothing; the Keyboard and OSC have
                // no axes to calibrate.
                (xbox || logical) ? null : MenuModel.action("Module Setup…",
                                 function() { _card.configureModule() }),
                // Xbox Setup (D-XBOX-PADS): the ViGEmBus check and how many
                // pads are on; Main opens it for the Xbox card's
                // configureModule.
                !xbox ? null : MenuModel.action("Xbox Setup…",
                                 function() { _card.configureModule() }),
                (notStick || xbox || logical) ? null
                    : MenuModel.action("Auto Mapping Tool", function() { _card.openAutoMappingTool() }),
                (dest || notStick || logical) ? null
                    : MenuModel.action("Calibration", function() { _card.openCalibration() })
            ]),
            MenuModel.section("view", "View", [
                // The Xbox pad view is part of the Xbox Output View now.
                xbox ? null : MenuModel.action("vJoy Viewer", function() { _card.openPairing() }),
                (notStick || xbox || logical) ? null
                    : MenuModel.action("Device Information", function() { _card.openDeviceInformation() })
            ]),
            MenuModel.section("cards", "Cards", [
                MenuModel.action("Stack Selected Cards", function() { _card.stackSelectedCards() }, _card.canStackSelected),
                MenuModel.action("Hide Selected Cards", function() { _card.hideSelectedCards() }, _card.canActOnSelected),
                MenuModel.action("Reset Size of Selected Cards", function() { _card.resetSelectedSizes() }, _card.canActOnSelected),
                MenuModel.action("Unstack", function() { _card.unstackCard() }, stacked),
                MenuModel.action("Unstack All", function() { _card.unstackAllCards() }, stacked),
                MenuModel.action("Reset Size", function() { _card.resetSize() }),
                MenuModel.action("Reset All Card Sizes", function() { _card.resetAllSizes() })
            ]),
            MenuModel.section("device", "Device", [
                _card.damaged === "" ? null
                    : MenuModel.action("Start Fresh…", function() { _card.startFresh() }),
                // Not on output (vJoy, Xbox), Keyboard, OSC or Logical Device
                // cards (03 S88, 09 S31): they open the Device Library.
                (dest || xbox || notStick || logical) ? null
                    : MenuModel.action("Copy Setup to Another Stick…", function() { _card.openDeviceLibrary("copy") }),
                (dest || xbox || notStick || logical) ? null
                    : MenuModel.action("Swap with Another Stick…", function() { _card.openDeviceLibrary("swap") }),
                (dest || xbox || notStick || logical) ? null
                    : MenuModel.action("Change vJoy Output…", function() { _card.openDeviceLibrary("output") }),
                // The Logical Device's card picture (03 S88, D-03-LD-IMAGE),
                // unchanged: its bottom background picture.
                !logical ? null
                    : MenuModel.action(_card.photo ? "Change Image…" : "Add Image…",
                                       function() { _card.addImage() }),
                (!logical || !_card.photo) ? null
                    : MenuModel.action("Remove Image", function() { _card.removeImage() }),
                // An input module's Device Image (D-03-DEVICE-IMAGE): only
                // the uploaded image is removable here, not the generated
                // picture. Output cards keep theirs as they are. A card needs
                // a readable module file to hold one.
                (dest || xbox || logical) ? null
                    : MenuModel.action(_card.hasImage ? "Change Image…" : "Add Image…",
                                       function() { _card.addImage() },
                                       _card.isModule && _card.damaged === ""),
                (dest || xbox || logical || !_card.hasImage) ? null
                    : MenuModel.action("Remove Image", function() { _card.removeImage() },
                                       _card.damaged === ""),
                // 08 S111 (D-FIXLIST-B2): open the Export / Import Device
                // window on that tab with this device (Export only once it
                // has a module file).
                MenuModel.action("Export Device…", function() { _card.exportDevice() }, _card.isModule),
                MenuModel.action("Import Device…", function() { _card.importDevice() }),
                MenuModel.action("Reset Card Layout", function() { _card.clearSettings() }),
                // Output module files are never deleted (03 Q18).
                dest ? null
                    : MenuModel.action("Delete Device", function() { _card.deleteDevice() }, true, { danger: true })
            ])
        ], [
            // Home's Undo / Redo (D-FIXLIST-B1 10), as the Device Mapping Editor's menus.
            { label: "Undo", enabled: _card.canUndo, run: function() { _card.undoStep() } },
            { label: "Redo", enabled: _card.canRedo, run: function() { _card.redoStep() } }
        ])
    }

    ContextMenu {
        id: _menu
        build: _card.menuModel
    }
}
