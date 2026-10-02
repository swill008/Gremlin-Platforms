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
import "helpers.js" as Helpers

Item {
    id: _page
    focus: true
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Escape) {
            deselectAll()
            event.accepted = true
        }
    }

    property var model: null
    // Cards on show, kept current as the model reloads.
    property int shownCount: 0
    function recountShown() { shownCount = model ? model.visibleCount() : 0 }
    onModelChanged: recountShown()
    Connections {
        target: _page.model
        ignoreUnknownSignals: true
        function onModelReset() { _page.recountShown() }
        function onRowsInserted() { _page.recountShown() }
        function onRowsRemoved() { _page.recountShown() }
    }
    readonly property bool splitOn: model && model.splitMode !== "none"
    property var _liveCards: []
    property var slotSnap: []

    property string dragSlug: ""
    property string dragDir: ""
    property string dragName: ""
    property string dragPhoto: ""
    property string insertBefore: ""
    property string homeBefore: ""
    property string dragStackSlug: ""
    property string stackCandidate: ""
    property int ghostW: 0
    property int ghostH: 0
    property int pendingStackW: 0
    property int pendingStackH: 0
    property real dragOriginX: 0
    property real dragOriginY: 0
    property real stackTravel: 0
    property real insertTravel: Style.dp(24)
    property real floatX: 0
    property real floatY: 0
    property real grabOffX: 0
    property real grabOffY: 0
    property bool gotGrab: false
    property var selectedSlugs: []
    property int selectRev: 0

    signal focusSlug(string slug)
    signal openConfiguration(var card)
    signal openButtonMap(var card)
    signal openOutputView(var card)
    signal configureModule(var card)
    signal autoMap(var card)
    signal openPairing(var card)
    signal openCalibration(var card)
    signal openDeviceInformation(var card)
    signal assignHardware(var card)
    signal ignoreDevice(var card)
    signal deviceDeleted(var card)

    property int pileRev: 0

    function pack(m) {
        return {
            slug: m.slug,
            name: m.cardName || m.name,
            rawName: m.rawName,
            guid: m.guid,
            photo: m.photo || "",
            direction: m.direction,
            status: m.status,
            bus: m.bus,
            tab: m.tab,
            isStub: m.isStub,
            isModule: m.isModule
        }
    }

    function registerCard(card) {
        _liveCards.push(card)
    }

    function unregisterCard(card) {
        _liveCards = _liveCards.filter(function(item) { return item !== card })
    }

    function paneDir(card) {
        if (_page.model && _page.model.splitMode !== "none")
            return card.direction
        return ""
    }

    function cardOnPage(card) {
        if (!card || !card.slug)
            return false
        if (card.width < Style.dp(32) || card.height < Style.dp(32))
            return false
        var p = card
        while (p) {
            if (p.visible === false)
                return false
            p = p.parent
        }
        return true
    }

    function cardBySlug(slug) {
        for (var i = 0; i < _liveCards.length; ++i) {
            var card = _liveCards[i]
            if (card && card.slug === slug && cardOnPage(card))
                return card
        }
        return null
    }

    function cardUnder(px, py) {
        for (var i = 0; i < _liveCards.length; ++i) {
            var card = _liveCards[i]
            if (!card || !cardOnPage(card))
                continue
            var o = card.mapToItem(_page, 0, 0)
            if (px >= o.x && py >= o.y && px <= o.x + card.width && py <= o.y + card.height)
                return card
        }
        return null
    }

    function deselectAll() {
        var hadSel = selectedSlugs.length > 0
        if (hadSel) {
            selectedSlugs = []
            selectRev++
        }
        if (model)
            model.setFocus("")
        _page.focusSlug("")
        refreshCards()
        forceActiveFocus()
    }

    function _selectHas(slug) {
        return selectedSlugs.indexOf(slug) >= 0
    }

    function clearSelection() {
        if (!selectedSlugs.length)
            return
        selectedSlugs = []
        selectRev++
        refreshCards()
        forceActiveFocus()
    }

    function toggleSelect(card) {
        if (!card || !card.slug)
            return
        var slug = card.slug
        var dir = card.direction || ""
        var list = selectedSlugs.slice()
        if (list.length && model) {
            var first = model.cardMap(list[0])
            if (first && first.direction && dir && first.direction !== dir)
                list = []
        }
        if (!list.length && model && model.focusedSlug && model.focusedSlug !== slug) {
            var foc = model.cardMap(model.focusedSlug)
            if (foc && (!dir || !foc.direction || foc.direction === dir))
                list = [model.focusedSlug]
        }
        var i = list.indexOf(slug)
        if (i >= 0)
            list.splice(i, 1)
        else
            list.push(slug)
        selectedSlugs = list
        selectRev++
        refreshCards()
        forceActiveFocus()
    }

    function stackSelected(leader) {
        if (!model || !leader)
            return
        var list = selectedSlugs.slice()
        if (list.indexOf(leader) < 0 || list.length < 2)
            return
        model.stackSelected(leader, list.join(","))
        selectedSlugs = []
        selectRev++
        refreshCards()
    }

    function snapshotSlots(dragged, dir, dragCard) {
        var list = []
        if (!model)
            return
        var leaders = model.pileLeaders(dir)
        var skip = dragged
        for (var k = 0; k < leaders.length; ++k) {
            var mem = model.pileMembers(leaders[k])
            for (var m = 0; m < mem.length; ++m) {
                if (mem[m] === dragged)
                    skip = leaders[k]
            }
        }
        for (var i = 0; i < leaders.length; ++i) {
            var s = leaders[i]
            if (s === skip)
                continue
            var card = cardBySlug(s)
            if (!card)
                continue
            var o = card.mapToItem(_page, 0, 0)
            // Keep original positions. Compacting put the next card's
            // center on the one you picked up, so a few pixels right
            // already counted as "past it" (~20%) while left needed a
            // full cover (~90%).
            list.push({
                slug: s,
                left: o.x,
                mid: o.x + card.width / 2,
                top: o.y,
                y: o.y + card.height / 2,
                w: card.width,
                h: card.height
            })
        }
        slotSnap = list
    }

    function pickInsertFromSnap(gx, gy) {
        var slots = slotSnap
        if (!slots || !slots.length)
            return insertBefore
        var hit = false
        var before = ""
        for (var j = 0; j < slots.length; ++j) {
            var s = slots[j]
            var sameRow = Math.abs(gy - s.y) < Math.max(Style.dp(120), s.h * 0.75)
            if (!sameRow)
                continue
            hit = true
            // Float center vs the card's left edge: ~50% overlap from
            // either side, same distance in both directions.
            if (gx <= s.left) {
                before = s.slug
                break
            }
        }
        if (!hit)
            return insertBefore
        return before
    }

    function nextLeader(slug, dir) {
        if (!model)
            return ""
        var list = model.pileLeaders(dir)
        for (var i = 0; i < list.length; ++i) {
            if (list[i] === slug)
                return (i + 1 < list.length) ? list[i + 1] : ""
            var mem = model.pileMembers(list[i])
            for (var j = 0; j < mem.length; ++j) {
                if (mem[j] === slug)
                    return (i + 1 < list.length) ? list[i + 1] : ""
            }
        }
        return ""
    }

    function beginDrag(card) {
        if (!card || !card.slug)
            return
        clearSelection()
        var origin = card.mapToItem(_page, 0, 0)
        var mid = card.mapToItem(_page, card.width / 2, card.height / 2)
        dragOriginX = mid.x
        dragOriginY = mid.y
        stackTravel = Math.max(Style.dp(110), Math.min(card.width, card.height) * 0.5)
        dragDir = paneDir(card)
        dragName = card.cardName || ""
        dragPhoto = card.photo || ""
        ghostW = Math.round(card.width)
        ghostH = Math.round(card.height)
        floatX = origin.x
        floatY = origin.y
        gotGrab = false
        grabOffX = 0
        grabOffY = 0
        dragStackSlug = ""
        stackCandidate = ""
        pendingStackW = 0
        pendingStackH = 0
        snapshotSlots(card.slug, dragDir, card)
        homeBefore = nextLeader(card.slug, dragDir)
        insertBefore = homeBefore
        dragSlug = card.slug
    }

    function updateDragAt(sx, sy) {
        if (!dragSlug)
            return
        var p = _page.mapFromItem(null, sx, sy)
        if (!gotGrab) {
            grabOffX = p.x - floatX
            grabOffY = p.y - floatY
            gotGrab = true
        }
        floatX = p.x - grabOffX
        floatY = p.y - grabOffY
        var gx = floatX + ghostW / 2
        var gy = floatY + ghostH / 2
        var dx = gx - dragOriginX
        var dy = gy - dragOriginY
        var traveled = Math.sqrt(dx * dx + dy * dy)
        if (traveled < insertTravel)
            return
        var before = pickInsertFromSnap(gx, gy)
        if (insertBefore !== before)
            insertBefore = before
    }

    function clearDrag() {
        dragSlug = ""
        dragDir = ""
        dragName = ""
        dragPhoto = ""
        insertBefore = ""
        homeBefore = ""
        dragStackSlug = ""
        stackCandidate = ""
        pendingStackW = 0
        pendingStackH = 0
        gotGrab = false
        slotSnap = []
    }

    function handleDrop(slug) {
        if (!model || !slug) {
            clearDrag()
            return
        }
        var before = insertBefore
        var home = homeBefore
        clearDrag()
        if (before === home)
            return
        model.unstackSlug(slug)
        model.moveSlugBefore(slug, before)
    }

    function askDelete(card) {
        if (!card || !model)
            return
        var raw = String(card.rawName || card.cardName || card.name || "")
        var preview = {}
        try {
            preview = JSON.parse(model.deletePreview(raw, card.guid || ""))
        } catch (err) {
            preview = {}
        }
        _deleteCard = card
        _deleteName = String(preview.name || raw)
        _deleteCanPack = !!preview.canPack
        _deleteShared = !!preview.shared
        _deleteForeign = !!preview.foreign
        _deleteListed = preview.listed !== false
        _deleteKeepModule = !!preview.keepModule
        _deleteSaveCopy = _deleteCanPack
        _saveCopyBox.checked = _deleteCanPack
        _explainAdvance = false
        _explainDialog.open()
    }

    function explainBody() {
        var lines = ["Delete " + _deleteName + "."]
        if (_deleteKeepModule)
            lines.push("This does not delete the vJoy or Xbox module file. Only wires stored on this device are removed. Wires from input devices stay.")
        else if (_deleteForeign)
            lines.push("This device is using another device's file. That file stays. Only this device's wires are removed.")
        else if (_deleteShared)
            lines.push("Another device uses this module file, so the file stays. Only this device's wires are removed. The card stays.")
        else
            lines.push("This removes this device's module file, its pictures, and its wires in every mode. The card's size and stack are cleared.")
        if (!_deleteKeepModule)
            lines.push("vJoy and Xbox module files stay. Other input devices that use them are not changed.")
        if (!_deleteKeepModule && !_deleteShared && _deleteListed)
            lines.push("The Windows device stays, and a stub card remains.")
        else if (!_deleteListed)
            lines.push("This device is not connected, so no card will remain.")
        if (!_deleteCanPack)
            lines.push("This device has no module file, so a pack cannot be saved.")
        return lines.join("\n\n")
    }

    function confirmBody() {
        var line = "Really delete " + _deleteName + "?"
        if (_deleteSaveCopy)
            line += " A pack will be written to deleted devices first."
        else
            line += " No copy will be saved."
        if (_deleteKeepModule)
            line += " The output module file stays. Only this device's wires are removed."
        else if (_deleteShared)
            line += " The module file stays."
        else if (_deleteListed)
            line += " A stub card will remain."
        else
            line += " No card will remain."
        return line
    }

    function runDelete() {
        if (!model || !_deleteCard)
            return
        var raw = String(_deleteCard.rawName || _deleteCard.cardName || _deleteCard.name || "")
        var guid = String(_deleteCard.guid || "")
        var card = _deleteCard
        var rawResult = model.deleteDevice(raw, guid, _deleteSaveCopy)
        var result = {}
        try {
            result = JSON.parse(rawResult)
        } catch (err) {
            result = { ok: false, error: "The delete could not be read." }
        }
        if (!result.ok) {
            _doneTitle = "Delete stopped"
            _doneMessage = String(result.error || "The device was not deleted.")
            _doneDialog.open()
            return
        }
        var done = "Deleted " + String(result.name || _deleteName) + "."
        if (result.packPath)
            done += " A copy was saved to " + result.packPath + "."
        else
            done += " No copy was saved."
        if (result.keepModule)
            done += " The output module file was kept. Only this device's wires were removed."
        else if (result.keptFile)
            done += " The module file was kept because another device uses it."
        else if (result.stub)
            done += " A stub card remains."
        else
            done += " No card remains."
        if (result.profileSaved === false)
            done += " Save the profile to keep the wire removal."
        _doneTitle = "Device deleted"
        _doneMessage = done
        _doneDialog.open()
        deviceDeleted(card)
    }

    property var _deleteCard: null
    property string _deleteName: ""
    property bool _deleteCanPack: false
    property bool _deleteShared: false
    property bool _deleteForeign: false
    property bool _deleteListed: true
    property bool _deleteKeepModule: false
    property bool _deleteSaveCopy: true
    property bool _explainAdvance: false
    property bool _confirmAdvance: false
    property string _doneTitle: ""
    property string _doneMessage: ""

    function bindCard(card) {
        _page.registerCard(card)
        card.onCardFocused.connect(function() {
            _page.clearSelection()
            if (model)
                model.raiseSlug(card.slug)
            _page.focusSlug(card.slug)
            _page.refreshCards()
        })
        card.shiftToggled.connect(function() { _page.toggleSelect(card) })
        card.stackSelectedCards.connect(function() { _page.stackSelected(card.slug) })
        card.onOpenConfiguration.connect(function() { _page.openConfiguration(_page.pack(card)) })
        card.openButtonMap.connect(function() { _page.openButtonMap(_page.pack(card)) })
        card.openOutputView.connect(function() { _page.openOutputView(_page.pack(card)) })
        card.onConfigureModule.connect(function() { _page.configureModule(_page.pack(card)) })
        card.onAutoMap.connect(function() { _page.autoMap(_page.pack(card)) })
        card.onOpenPairing.connect(function() { _page.openPairing(_page.pack(card)) })
        card.onOpenCalibration.connect(function() { _page.openCalibration(_page.pack(card)) })
        card.onOpenDeviceInformation.connect(function() { _page.openDeviceInformation(_page.pack(card)) })
        card.onAssignHardware.connect(function() { _page.assignHardware(_page.pack(card)) })
        card.onIgnoreDevice.connect(function() { _page.ignoreDevice(_page.pack(card)) })
        card.dragStarted.connect(function() { _page.beginDrag(card) })
        card.dragMovedAt.connect(function(sx, sy) { _page.updateDragAt(sx, sy) })
        card.dropAt.connect(function() { _page.handleDrop(card.slug) })
        card.onSizeChanged.connect(function(w, h) {
            if (model)
                model.setPileSize(card.slug, Math.round(w * 100 / Style.uiScale), Math.round(h * 100 / Style.uiScale))
        })
        card.onResetSize.connect(function() {
            if (model)
                model.resetCardSize(card.slug)
        })
        card.onResetAllSizes.connect(function() { _page.resetAllCardSizes() })
        card.onClearSettings.connect(function() {
            if (model)
                model.clearCardSettings(card.slug)
        })
        card.onDeleteDevice.connect(function() { _page.askDelete(card) })
        card.onUnstackCard.connect(function() {
            if (model)
                model.unstackSlug(card.slug)
        })
        card.onUnstackAllCards.connect(function() {
            if (model)
                model.unstackAll(card.slug)
        })
        card.Component.onDestruction.connect(function() { _page.unregisterCard(card) })
    }

    function refreshCards() {
        for (var i = 0; i < _liveCards.length; ++i) {
            var card = _liveCards[i]
            if (card && card.slug)
                fillCard(card, card.slug)
        }
    }

    function fillCard(card, slug) {
        if (!model)
            return
        var info = model.cardMap(slug)
        card.slug = info.slug || slug
        card.cardName = info.name || ""
        card.rawName = info.rawName || ""
        card.guid = info.guid || ""
        card.direction = info.direction || "source"
        card.status = info.status || ""
        card.bus = info.bus || ""
        card.buttons = info.buttons || 0
        card.axes = info.axes || 0
        card.hats = info.hats || 0
        if (card.photo !== (info.photo || ""))
            card.photo = info.photo || ""
        card.isStub = !!info.isStub
        card.isModule = !!info.isModule
        card.tab = info.tab || "physical"
        card.target = info.target || ""
        card.lastLine = info.lastLine || ""
        card.lastHardware = info.lastHardware || ""
        card.focused = !!info.focused
        if (card.lifting && _page.dragSlug !== card.slug)
            card.lifting = false
        card.selected = _page._selectHas(card.slug)
        card.canStackSelected = card.selected && selectedSlugs.length >= 2
    }

    onVisibleChanged: {
        if (!visible)
            return
        clearDrag()
        if (_inputPane)
            _inputPane.dragLocks = 0
        if (_outputPane)
            _outputPane.dragLocks = 0
        if (_allPane)
            _allPane.dragLocks = 0
        refreshCards()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(8)

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            CheckBox {
                text: "Compact view"
                checked: !!(_page.model && _page.model.compactView)
                onToggled: {
                    if (_page.model)
                        _page.model.setCompactView(checked)
                }
            }
            Label { text: "Split"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
            ComboBox {
                id: _split
                model: ["None", "Vertical", "Horizontal"]
                implicitWidth: Style.dp(140)
                currentIndex: {
                    var mode = _page.model ? _page.model.splitMode : "none"
                    if (mode === "vertical") return 1
                    if (mode === "horizontal") return 2
                    return 0
                }
                onActivated: {
                    if (!_page.model)
                        return
                    _page.model.setSplitMode(["none", "vertical", "horizontal"][currentIndex])
                }
            }
        }

        SplitView {
            id: _splitView
            Layout.fillWidth: true
            Layout.fillHeight: _page.splitOn
            visible: _page.splitOn
            orientation: (_page.model && _page.model.splitMode === "horizontal") ? Qt.Vertical : Qt.Horizontal
            handle: Rectangle { implicitWidth: Style.dp(8); implicitHeight: Style.dp(8); color: Style.lineStrong }

            property bool applying: false

            function applyRatio() {
                if (!_page.model || width < 8 || height < 8)
                    return
                applying = true
                var r = _page.model.splitRatio
                if (!(r > 0))
                    r = 0.5
                if (orientation === Qt.Horizontal)
                    _inputPane.SplitView.preferredWidth = Math.round(width * r)
                else
                    _inputPane.SplitView.preferredHeight = Math.round(height * r)
                applying = false
            }

            function saveRatio() {
                if (applying || !_page.model || width < 8 || height < 8)
                    return
                var r = orientation === Qt.Horizontal ? (_inputPane.width / width) : (_inputPane.height / height)
                if (!(r > 0))
                    return
                _page.model.setSplitRatio(r)
            }

            Timer {
                id: _ratioSave
                interval: 150
                onTriggered: _splitView.saveRatio()
            }

            onWidthChanged: if (visible) applyRatio()
            onHeightChanged: if (visible) applyRatio()
            onVisibleChanged: {
                if (visible)
                    Qt.callLater(applyRatio)
            }
            onResizingChanged: if (!resizing && visible) saveRatio()

            StatusPane {
                id: _inputPane
                SplitView.minimumWidth: Style.dp(180)
                SplitView.minimumHeight: Style.dp(120)
                title: "Input modules"
                direction: "source"
                onWidthChanged: if (_splitView.visible && !_splitView.applying) _ratioSave.restart()
                onHeightChanged: if (_splitView.visible && !_splitView.applying) _ratioSave.restart()
            }
            StatusPane {
                id: _outputPane
                SplitView.minimumWidth: Style.dp(180)
                SplitView.minimumHeight: Style.dp(120)
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                title: "Output modules"
                direction: "dest"
            }
        }

        StatusPane {
            id: _allPane
            Layout.fillWidth: true
            Layout.fillHeight: !_page.splitOn
            visible: !_page.splitOn
            title: ""
            direction: ""
        }
    }

    component SlotGhost: Rectangle {
        radius: Style.dp(4)
        color: Style.alpha(Style.bgCard, 0.2)
        border.width: Style.dp(2)
        border.color: Style.fgMuted

        Image {
            anchors.fill: parent
            anchors.margins: Style.dp(10)
            source: _page.dragPhoto
            // The card's photo size (StatusCard), not the full photo.
            sourceSize: Qt.size(720 * Screen.devicePixelRatio, 520 * Screen.devicePixelRatio)
            fillMode: Image.PreserveAspectFit
            opacity: 0.4
            visible: _page.dragPhoto && _page.dragPhoto.length
            asynchronous: true
            cache: true
        }

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Style.dp(12)
            text: _page.dragName
            color: Style.fg
            font.pixelSize: Style.dp(13)
            font.bold: true
            opacity: 0.8
        }
    }

    component StatusPane: Item {
        id: _pane
        property string title: ""
        property string direction: ""
        property int dragLocks: 0
        property bool paneActive: {
            var mode = _page.model ? _page.model.splitMode : "none"
            if (!_pane.direction.length)
                return mode === "none"
            return mode !== "none"
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(6)

            Label {
                visible: _pane.title.length
                text: _pane.title
                color: Style.fg
                font.pixelSize: Style.dp(20)
                font.bold: true
                font.capitalization: Font.AllUppercase
            }

            Flickable {
                id: _flick
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: width
                contentHeight: _flow.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                interactive: _pane.dragLocks === 0
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                MouseArea {
                    z: -1
                    width: _flick.width
                    height: Math.max(_flick.height, _flow.implicitHeight)
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    preventStealing: false
                    onPressed: function(mouse) {
                        if (_page.dragSlug.length) {
                            mouse.accepted = false
                            return
                        }
                        var p = mapToItem(_page, mouse.x, mouse.y)
                        if (_page.cardUnder(p.x, p.y)) {
                            mouse.accepted = false
                            return
                        }
                        if (mouse.button === Qt.RightButton) {
                            _page.popupEmptyMenu(p.x, p.y)
                            return
                        }
                        if (!(mouse.modifiers & Qt.ShiftModifier))
                            _page.deselectAll()
                        mouse.accepted = false
                    }
                }

                Flow {
                    id: _flow
                    width: _flick.width
                    spacing: (_page.model && _page.model.compactView) ? Style.dp(8) : Style.dp(16)

                    Repeater {
                        id: _piles
                        model: {
                            _page.pileRev
                            if (!_pane.paneActive)
                                return []
                            return _page.model ? _page.model.pileLeaders(_pane.direction) : []
                        }

                        delegate: Item {
                            id: _pile
                            property var members: _page.model ? _page.model.pileMembers(modelData) : [modelData]
                            property int extra: Math.max(0, members.length - 1) * Style.dp(14)
                            property bool dragging: false
                            property bool isDragHome: _page.dragSlug === modelData && members.length === 1
                            property bool showGhost: {
                                if (!_page.dragSlug.length || _page.dragStackSlug.length)
                                    return false
                                if (_pane.direction.length && _page.dragDir !== _pane.direction)
                                    return false
                                return _page.insertBefore === modelData
                            }
                            property int cardW: {
                                _page.pileRev
                                var compact = _page.model && _page.model.compactView
                                if (!compact) {
                                    var saved = _page.model ? _page.model.cardWidth(modelData) : 0
                                    if (saved >= 220)
                                        return Style.dp(saved)
                                }
                                var avail = _flow.width
                                var want = Style.dp(compact ? 240 : 280)
                                if (avail < Style.dp(40))
                                    return want
                                return Math.min(want, avail)
                            }
                            property int cardH: {
                                _page.pileRev
                                if (_page.model && _page.model.compactView)
                                    return 0
                                var saved = _page.model ? _page.model.cardHeight(modelData) : 0
                                return saved >= 140 ? Style.dp(saved) : 0
                            }
                            property int ghostPad: showGhost ? _page.ghostW + Style.dp(16) : 0

                            width: isDragHome ? 0 : (cardW + extra + ghostPad)
                            height: {
                                if (isDragHome)
                                    return Math.max(1, _page.ghostH)
                                var compact = _page.model && _page.model.compactView
                                var c = _memberCards.itemAt(0)
                                var need = (c && c.implicitHeight > 0) ? Math.round(c.implicitHeight) : Style.dp(compact ? 120 : 260)
                                var h = Math.max(cardH >= Style.dp(140) ? cardH : 0, need) + extra
                                if (showGhost)
                                    h = Math.max(h, _page.ghostH)
                                return h
                            }
                            z: dragging || isDragHome ? 10000 : 0
                            clip: false

                            function freezeSlot() {
                                dragging = true
                                _pane.dragLocks += 1
                            }

                            function thawSlot() {
                                if (!dragging)
                                    return
                                dragging = false
                                _pane.dragLocks = Math.max(0, _pane.dragLocks - 1)
                            }

                            SlotGhost {
                                visible: _pile.showGhost
                                x: 0
                                y: 0
                                width: visible ? _page.ghostW : 0
                                height: visible ? _page.ghostH : 0
                            }

                            Repeater {
                                id: _memberCards
                                model: _pile.members
                                delegate: StatusCard {
                                    id: _card
                                    x: index * 14 + _pile.ghostPad
                                    y: index * 14
                                    stackIndex: index
                                    stacked: _pile.members.length > 1
                                    compactView: !!(_page.model && _page.model.compactView)
                                    width: _card.resizing ? _card.liveW : _pile.cardW
                                    height: _card.resizing ? _card.liveH : Math.max(_pile.cardH > 0 ? _pile.cardH : 0, implicitHeight)
                                    stretchPhoto: _pile.cardH >= Style.dp(140)
                                    dropStacking: false
                                    opacity: (_page.dragSlug === modelData || _page.dragSlug === slug) ? 0 : 1
                                    onLiftingChanged: {
                                        if (lifting)
                                            _pile.freezeSlot()
                                        else
                                            _pile.thawSlot()
                                    }
                                    Component.onCompleted: {
                                        _page.fillCard(_card, modelData)
                                        _page.bindCard(_card)
                                    }
                                }
                            }
                        }
                    }

                    SlotGhost {
                        visible: _pane.paneActive && _page.dragSlug.length && !_page.dragStackSlug.length && _page.insertBefore === "" && (!_pane.direction.length || _page.dragDir === _pane.direction)
                        width: visible ? _page.ghostW : 0
                        height: visible ? _page.ghostH : 0
                    }
                }
            }
        }
    }

    Item {
        id: _float
        visible: _page.dragSlug.length > 0
        z: 100000
        x: _page.floatX
        y: _page.floatY
        width: _page.ghostW
        height: _page.ghostH

        Rectangle {
            anchors.fill: parent
            radius: Style.dp(4)
            color: Style.bgCard
            border.width: Style.dp(2)
            border.color: Style.fg

            Image {
                anchors.fill: parent
                anchors.margins: Style.dp(10)
                source: _page.dragPhoto
                // The card's photo size (StatusCard), not the full photo.
                sourceSize: Qt.size(720 * Screen.devicePixelRatio, 520 * Screen.devicePixelRatio)
                fillMode: Image.PreserveAspectFit
                visible: _page.dragPhoto && _page.dragPhoto.length
                asynchronous: true
                cache: true
            }

            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Style.dp(12)
                text: _page.dragName
                color: Style.fg
                font.pixelSize: Style.dp(13)
                font.bold: true
            }
        }
    }

    function popupEmptyMenu(pageX, pageY) {
        // After this release: opening during it reads as a click outside.
        Qt.callLater(function() { _emptyMenu.openAt(_page, pageX, pageY) })
    }

    // The page's right-click menu (Gremlin.Menus), off the cards.
    ContextMenu {
        id: _emptyMenu
        menuWidth: Style.dp(240)
        build: function() {
            return MenuModel.menu("home", "Home", [
                MenuModel.action("Unhide all devices", function() {
                    if (_page.model)
                        _page.model.unignoreAll()
                }, !!(_page.model && _page.model.hiddenList().length)),
                MenuModel.action("Reset all card sizes", function() { _page.resetAllCardSizes() }),
                MenuModel.command("view.hidden"),
                MenuModel.section("layout", "Layout", [
                    MenuModel.command("view.layout.single"),
                    MenuModel.command("view.layout.side"),
                    MenuModel.command("view.layout.stacked")
                ])
            ])
        }
    }

    function resetAllCardSizes() {
        if (model)
            model.resetAllCardSizes()
    }

    Connections {
        target: model
        function onPanesChanged() {
            _page.pileRev++
            if (_splitView.visible)
                Qt.callLater(_splitView.applyRatio)
        }
        function onClaimsChanged() {
            Qt.callLater(_page.refreshCards)
        }
        function onLastChanged() {
            Qt.callLater(_page.refreshCards)
        }
        function onFocusChanged() {
            Qt.callLater(_page.refreshCards)
        }
    }

    Popup {
        id: _explainDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        focus: true
        padding: Style.dp(16)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        onClosed: {
            if (!_explainAdvance)
                return
            _explainAdvance = false
            _confirmAdvance = false
            _confirmDialog.open()
        }

        background: Rectangle {
            color: Style.background
            border.color: Style.accent
            border.width: Style.dp(1)
            radius: Style.dp(4)
        }

        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                text: "Delete Device"
                font.bold: true
                font.pixelSize: Style.dp(16)
                Layout.preferredWidth: Style.dp(440)
            }
            Label {
                text: _page.explainBody()
                wrapMode: Text.WordWrap
                Layout.preferredWidth: Style.dp(440)
                Layout.fillWidth: true
            }
            CheckBox {
                id: _saveCopyBox
                text: "Save a copy in deleted devices"
                enabled: _page._deleteCanPack
                onToggled: _page._deleteSaveCopy = checked
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    text: "Cancel"
                    onClicked: _explainDialog.close()
                }
                Button {
                    text: "Continue"
                    highlighted: true
                    onClicked: {
                        _explainAdvance = true
                        _explainDialog.close()
                    }
                }
            }
        }
    }

    Popup {
        id: _confirmDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        focus: true
        padding: Style.dp(16)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        onClosed: {
            if (!_confirmAdvance)
                return
            _confirmAdvance = false
            _page.runDelete()
        }

        background: Rectangle {
            color: Style.background
            border.color: Style.danger
            border.width: Style.dp(1)
            radius: Style.dp(4)
        }

        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                text: "Really delete this device?"
                font.bold: true
                font.pixelSize: Style.dp(16)
                color: Style.dangerText
                Layout.preferredWidth: Style.dp(440)
            }
            Label {
                text: _page.confirmBody()
                wrapMode: Text.WordWrap
                Layout.preferredWidth: Style.dp(440)
                Layout.fillWidth: true
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    text: "Cancel"
                    onClicked: _confirmDialog.close()
                }
                Button {
                    text: "Delete"
                    onClicked: {
                        _confirmAdvance = true
                        _confirmDialog.close()
                    }
                    contentItem: Label {
                        text: "Delete"
                        color: Style.onColor
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.hovered ? Style.dangerHover : Style.danger
                        radius: Style.dp(4)
                    }
                }
            }
        }
    }

    Popup {
        id: _doneDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        focus: true
        padding: Style.dp(16)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: Style.background
            border.color: _doneTitle === "Delete stopped" ? Style.danger : Style.accent
            border.width: Style.dp(1)
            radius: Style.dp(4)
        }

        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                text: _page._doneTitle
                font.bold: true
                font.pixelSize: Style.dp(16)
                Layout.preferredWidth: Style.dp(440)
            }
            Label {
                text: _page._doneMessage
                wrapMode: Text.WordWrap
                Layout.preferredWidth: Style.dp(440)
                Layout.fillWidth: true
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                Button {
                    text: "OK"
                    highlighted: true
                    onClicked: _doneDialog.close()
                }
            }
        }
    }

    Label {
        anchors.centerIn: parent
        visible: model !== null && shownCount === 0
        text: "No devices to show. Plug in hardware or unhide a card from View → Hidden devices…"
        color: Style.fgMuted
    }
}
