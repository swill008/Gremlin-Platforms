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
import "confirm.js" as Confirm

Item {
    id: _page
    objectName: "homePage"
    focus: true
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Escape) {
            deselectAll()
            event.accepted = true
        }
    }

    // Home's Undo / Redo (01 S143, D-FIXLIST-B1 10): the steps are the
    // model's; Ctrl+Z, Ctrl+Y and Ctrl+Shift+Z while Home shows and no text
    // box is being typed in. On Windows StandardKey.Redo is Ctrl+Y and
    // Ctrl+Shift+Z.
    function _typing() {
        var f = Window.activeFocusItem
        return !!f && ("cursorPosition" in f)
    }
    function undo() {
        if (model && model.canUndo) {
            model.undo()
            refreshCards()
        }
    }
    function redo() {
        if (model && model.canRedo) {
            model.redo()
            refreshCards()
        }
    }
    Shortcut {
        enabled: _page.visible && !!_page.model && _page.model.canUndo
        sequences: [StandardKey.Undo]
        onActivated: if (!_page._typing()) _page.undo()
    }
    Shortcut {
        enabled: _page.visible && !!_page.model && _page.model.canRedo
        sequences: [StandardKey.Redo]
        onActivated: if (!_page._typing()) _page.redo()
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

    // A card being dragged to a new place (03 S81, as the Device Bindings
    // rows): a picture of the card follows the pointer and a line shows
    // where it will go; the other cards stay still.
    property string dragSlug: ""
    property string dragDir: ""
    property string insertBefore: ""
    property string homeBefore: ""
    property int ghostW: 0
    property int ghostH: 0
    // The card's picture (grabToImage) and the result that keeps it alive.
    property string dragGhost: ""
    property var _ghostResult: null
    // The drop line, in page coordinates; hidden where the card would stay.
    property bool dropLineShown: false
    property real dropLineX: 0
    property real dropLineY: 0
    property real dropLineH: 0
    property real floatX: 0
    property real floatY: 0
    property real grabOffX: 0
    property real grabOffY: 0
    property bool gotGrab: false
    property var selectedSlugs: []
    property int selectRev: 0

    signal focusSlug(string slug)
    signal openDeviceBindings(var card)
    signal openDeviceMappingEditor(var card)
    signal openOutputView(var card)
    signal configureModule(var card)
    signal openAutoMappingTool(var card)
    signal openPairing(var card)
    signal openCalibration(var card)
    signal openDeviceInformation(var card)
    // The Device Library (10 S2) on the card's device, with "copy", "swap"
    // or "output".
    signal openDeviceLibrary(var card, string action)
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

    // Where each other pile sits when the drag starts (page coordinates, in
    // the pane's order). Nothing moves during the drag, so it stays true.
    function snapshotSlots(dragged, dir) {
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
            // The pile's slot (a stack is wider and taller than its front card).
            var slot = card.parent || card
            var o = slot.mapToItem(_page, 0, 0)
            list.push({
                slug: s,
                left: o.x,
                top: o.y,
                w: slot.width,
                h: slot.height,
                mid: o.x + slot.width / 2
            })
        }
        slotSnap = list
    }

    // The drop spot under the pointer (page coordinates): the row the pointer
    // is in, then before the first pile whose middle is right of it, else
    // after the row's last pile. Sets insertBefore and the line.
    function pickDrop(px, py) {
        var slots = slotSnap
        if (!slots || !slots.length) {
            dropLineShown = false
            return
        }
        var rowTop = null
        var firstTop = slots[0].top
        for (var i = 0; i < slots.length; ++i) {
            firstTop = Math.min(firstTop, slots[i].top)
            if (slots[i].top <= py && (rowTop === null || slots[i].top > rowTop))
                rowTop = slots[i].top
        }
        if (rowTop === null)
            rowTop = firstTop
        var gap = (model && model.compactView) ? Style.dp(8) : Style.dp(16)
        var before = ""
        var lineX = 0
        var lineH = 0
        var last = -1
        var found = false
        for (var j = 0; j < slots.length; ++j) {
            var s = slots[j]
            if (Math.abs(s.top - rowTop) >= 1)
                continue
            lineH = Math.max(lineH, s.h)
            if (found)
                continue
            last = j
            if (px < s.mid) {
                before = s.slug
                lineX = s.left - gap / 2
                found = true
            }
        }
        if (!found) {
            var end = slots[last]
            before = last + 1 < slots.length ? slots[last + 1].slug : ""
            lineX = end.left + end.w + gap / 2
        }
        insertBefore = before
        dropLineX = lineX
        dropLineY = rowTop
        dropLineH = lineH
        dropLineShown = before !== homeBefore
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
        dragDir = paneDir(card)
        ghostW = Math.round(card.width)
        ghostH = Math.round(card.height)
        floatX = origin.x
        floatY = origin.y
        gotGrab = false
        grabOffX = 0
        grabOffY = 0
        dragGhost = ""
        _ghostResult = null
        dropLineShown = false
        snapshotSlots(card.slug, dragDir)
        homeBefore = nextLeader(card.slug, dragDir)
        insertBefore = homeBefore
        dragSlug = card.slug
        // The card's own picture (in a stack, the card picked up: the front
        // card). The card stays shown until the picture is ready.
        var slug = card.slug
        card.grabToImage(function(result) {
            if (_page.dragSlug !== slug)
                return
            _page._ghostResult = result
            _page.dragGhost = String(result.url)
        })
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
        pickDrop(p.x, p.y)
    }

    function clearDrag() {
        dragSlug = ""
        dragDir = ""
        insertBefore = ""
        homeBefore = ""
        dragGhost = ""
        _ghostResult = null
        dropLineShown = false
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
        // Out of its stack and moved: one Undo step.
        model.dropSlugBefore(slug, before)
    }

    function askDelete(card) {
        if (!card || !model)
            return
        // Output cards have no Delete Device (03 Q18).
        if (card.direction === "dest")
            return
        // It changes the running profile: refused while running (03 Q6).
        if (typeof backend !== "undefined" && backend && backend.gremlinActive) {
            _doneTitle = "Delete stopped"
            _doneMessage = "Stop the profile first. A device can't be deleted while the profile is running."
            _doneDialog.open()
            return
        }
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
        _deleteListed = preview.listed !== false
        _deleteKeepModule = !!preview.keepModule
        _explainAdvance = false
        _explainDialog.open()
    }

    function explainBody() {
        var lines = ["Delete " + _deleteName + "."]
        if (_deleteKeepModule)
            lines.push("This does not delete the vJoy or Xbox module file. Only actions stored on this device are removed. Actions from input devices stay.")
        else
            lines.push("This removes this device's folder (its settings, device map, pictures and recovery copy) and its actions in every mode. The card's size and stack are cleared.")
        if (!_deleteKeepModule)
            lines.push("vJoy and Xbox module files stay. Other input devices that use them are not changed.")
        if (!_deleteKeepModule && _deleteListed)
            lines.push("The Windows device stays, and its card stays without a module.")
        else if (!_deleteListed)
            lines.push("This device is not connected, so no card will remain.")
        // 03 S90, 10 S21: always kept; the user is not asked.
        lines.push("An autosave of this device is kept in the Device Library first, so it can be copied back. If the autosave can't be kept, nothing is deleted.")
        return lines.join("\n\n")
    }

    // The red confirm's text (step 2 of 3, 03 S90).
    function confirmBody() {
        var line = "An autosave is kept in the Device Library first."
        if (_deleteKeepModule)
            line += " The output module file stays. Only this device's actions are removed."
        else if (_deleteListed)
            line += " Its card will stay, without a module."
        else
            line += " No card will remain."
        return line
    }

    // Step 2 of 3: the shared red question (01 S140). History's "Deleted X"
    // entry can put it back (03 S94a).
    function askConfirm() {
        return Confirm.ask(_page, {
            title: "Delete " + _deleteName + "?",
            text: confirmBody(),
            undoable: true,
            action: "Delete Device",
            onAccept: function() { _page.runDelete() }
        })
    }

    // A damaged module file: move it aside (kept) and set the device up anew.
    function askStartFresh(card) {
        var name = String(card.rawName || card.cardName || card.name || "")
        var guid = String(card.guid || "")
        _startFreshGate.confirmThen("Start Fresh?",
            name + "'s module file can't be read (" + card.damaged + "). Start Fresh moves it"
                + " aside, keeping it as a copy, and starts an empty setup for this device:"
                + " its device map, claims and calibration start over. Nothing is deleted.",
            "Start Fresh", function() {
                var copy = model ? model.startFresh(name, guid) : ""
                _doneTitle = copy ? "Started fresh" : "Start Fresh stopped"
                _doneMessage = copy
                    ? "The damaged file was kept as:\n" + copy
                    : "The file could not be moved. It may be open in another program."
                _doneDialog.open()
            }, null, true)
    }

    function runDelete() {
        if (!model || !_deleteCard)
            return
        var raw = String(_deleteCard.rawName || _deleteCard.cardName || _deleteCard.name || "")
        var guid = String(_deleteCard.guid || "")
        var card = _deleteCard
        var rawResult = model.deleteDevice(raw, guid)
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
        if (result.autosaved)
            done += " An autosave was kept in the Device Library."
        if (result.keepModule)
            done += " The output module file was kept. Only this device's actions were removed."
        else if (result.stub)
            done += " Its card stays, without a module."
        else
            done += " No card remains."
        if (result.profileSaved === false)
            done += " Save the profile to keep the removal of those actions."
        _doneTitle = "Device deleted"
        _doneMessage = done
        _doneDialog.open()
        deviceDeleted(card)
    }

    property var _deleteCard: null
    property string _deleteName: ""
    property bool _deleteCanPack: false
    property bool _deleteListed: true
    property bool _deleteKeepModule: false
    property bool _explainAdvance: false
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
        card.onOpenDeviceBindings.connect(function() { _page.openDeviceBindings(_page.pack(card)) })
        card.openDeviceMappingEditor.connect(function() { _page.openDeviceMappingEditor(_page.pack(card)) })
        card.openOutputView.connect(function() { _page.openOutputView(_page.pack(card)) })
        card.onConfigureModule.connect(function() { _page.configureModule(_page.pack(card)) })
        card.onOpenAutoMappingTool.connect(function() { _page.openAutoMappingTool(_page.pack(card)) })
        card.onOpenPairing.connect(function() { _page.openPairing(_page.pack(card)) })
        card.onOpenCalibration.connect(function() { _page.openCalibration(_page.pack(card)) })
        card.onOpenDeviceInformation.connect(function() { _page.openDeviceInformation(_page.pack(card)) })
        card.onOpenDeviceLibrary.connect(function(action) { _page.openDeviceLibrary(_page.pack(card), action) })
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
        card.onStartFresh.connect(function() { _page.askStartFresh(card) })
        card.onExportDevice.connect(function() { _page.exportDevice(card) })
        card.onImportDevice.connect(function() { _page.importDevice(card) })
        card.onAddImage.connect(function() { _page.pickCardImage(card.slug) })
        card.onRemoveImage.connect(function() { _page.removeCardImage(card.slug) })
        card.onUnstackCard.connect(function() {
            if (model)
                model.unstackSlug(card.slug)
        })
        card.onUnstackAllCards.connect(function() {
            if (model)
                model.unstackAll(card.slug)
        })
        // The card menu's Undo / Redo pair; after the click, as the cards are
        // made again.
        card.undoStep.connect(function() { Qt.callLater(_page.undo) })
        card.redoStep.connect(function() { Qt.callLater(_page.redo) })
        card.Component.onDestruction.connect(function() { _page.unregisterCard(card) })
    }

    // Export Device… / Import Device… (08 S111, D-FIXLIST-B2): the one
    // Export / Import Device window (DialogDevicePack.qml), on that tab with
    // this card's device: chosen for Export, the suggested target for Import.
    function exportDevice(card) {
        _openExportImport("export", card)
    }

    function importDevice(card) {
        _openExportImport("import", card)
    }

    function _openExportImport(tab, card) {
        var w = Helpers.createComponent("DialogDevicePack.qml", { "mode": tab })
        if (w && typeof w.openFor === "function")
            w.openFor(tab, String(card.rawName || card.cardName || card.name || ""),
                      String(card.guid || ""))
        return w
    }

    // The Logical Device card's picture (03 S88, D-03-LD-IMAGE): the model
    // copies it next to the module file; Remove doesn't ask (History can
    // bring it back), as the Device Mapping Editor's Clear Photo.
    property string _imageSlug: ""

    function pickCardImage(slug) {
        _imageSlug = slug
        _cardImagePicker.open()
    }

    function removeCardImage(slug) {
        if (model && model.removeCardImage(slug))
            refreshCards()
    }

    FilePicker {
        id: _cardImagePicker
        kind: "picture"
        title: "Choose Image"
        nameFilters: ["Images (*.jpg *.jpeg *.png *.webp *.bmp)"]
        onPicked: (selectedFile) => {
            if (_page.model && _page._imageSlug
                    && _page.model.setCardImage(_page._imageSlug, String(selectedFile)))
                _page.refreshCards()
        }
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
        card.damaged = info.damaged || ""
        // Bindings this device sends that can't be sent (D-05-CANT-SEND).
        card.cantSendCount = info.cantSendCount || 0
        card.cantSendTip = info.cantSendTip || ""
        card.tab = info.tab || "physical"
        card.target = info.target || ""
        card.lastLine = info.lastLine || ""
        card.lastHardware = info.lastHardware || ""
        card.hasImage = !!info.hasImage
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

    // Home's controls, shown by Main in the bar under the toolbar (D-01-MODE-BAR).
    // Built in this file, so its bindings still reach _page. On the left
    // after the divider (01 S58a), then the Undo / Redo pair (01 S143).
    property Component pageBar: Component {
        RowLayout {
            Layout.fillWidth: true
            CheckBox {
                objectName: "homeCompactView"
                text: "Compact view"
                checked: !!(_page.model && _page.model.compactView)
                onToggled: {
                    if (_page.model)
                        _page.model.setCompactView(checked)
                }
            }
            Label { text: "Layout"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
            ComboBox {
                id: _split
                objectName: "homeLayoutCombo"
                // The same names as View → Home layout.
                model: ["Single list", "Side by side", "Stacked"]
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
            UndoBar {
                objectName: "homeUndoBar"
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(10)
                canUndo: !!_page.model && _page.model.canUndo
                canRedo: !!_page.model && _page.model.canRedo
                undoTip: _page.model ? _page.model.undoTip : ""
                redoTip: _page.model ? _page.model.redoTip : ""
                lastChange: _page.model ? _page.model.lastChange : ""
                undone: _page.model ? _page.model.undone : ""
                onUndo: _page.undo()
                onRedo: _page.redo()
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(12)
        spacing: Style.dp(8)

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
            // One Undo step per drag of the divider (D-FIXLIST-B1 10).
            onResizingChanged: {
                if (!visible || !_page.model)
                    return
                if (resizing) {
                    _page.model.beginDivider()
                    return
                }
                var r = orientation === Qt.Horizontal ? (_inputPane.width / width) : (_inputPane.height / height)
                if (r > 0 && width >= 8 && height >= 8)
                    _page.model.endDivider(r)
            }

            StatusPane {
                id: _inputPane
                SplitView.minimumWidth: Style.dp(180)
                SplitView.minimumHeight: Style.dp(120)
                title: "Input Modules"
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
                title: "Output Modules"
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
                            // The free width for this pile's front card: a card is
                            // never wider than the window shows (03 S83).
                            property real fitW: _flow.width - extra
                            property int cardW: {
                                _page.pileRev
                                var compact = _page.model && _page.model.compactView
                                var want = Style.dp(compact ? 240 : 280)
                                if (!compact) {
                                    var saved = _page.model ? _page.model.cardWidth(modelData) : 0
                                    if (saved >= 220)
                                        want = Style.dp(saved)
                                }
                                if (fitW < Style.dp(40))
                                    return want
                                return Math.min(want, Math.max(Style.dp(220), fitW))
                            }
                            property int cardH: {
                                _page.pileRev
                                if (_page.model && _page.model.compactView)
                                    return 0
                                var saved = _page.model ? _page.model.cardHeight(modelData) : 0
                                return saved >= 140 ? Style.dp(saved) : 0
                            }
                            // The front card's own height, kept up to date by the card
                            // (its photo loads after the slot is made). Reading the card
                            // through itemAt() would not update the slot when it grows,
                            // and the next row would overlap it.
                            property real leadH: 0

                            width: cardW + extra
                            height: {
                                var compact = _page.model && _page.model.compactView
                                var need = leadH > 0 ? Math.round(leadH) : Style.dp(compact ? 120 : 260)
                                return Math.max(cardH >= Style.dp(140) ? cardH : 0, need) + extra
                            }
                            z: dragging ? 10000 : 0
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

                            Repeater {
                                id: _memberCards
                                model: _pile.members
                                delegate: StatusCard {
                                    id: _card
                                    x: index * 14
                                    y: index * 14
                                    stackIndex: index
                                    stacked: _pile.members.length > 1
                                    compactView: !!(_page.model && _page.model.compactView)
                                    canUndo: !!(_page.model && _page.model.canUndo)
                                    canRedo: !!(_page.model && _page.model.canRedo)
                                    width: _card.resizing ? _card.liveW : _pile.cardW
                                    height: _card.resizing ? _card.liveH : Math.max(_pile.cardH > 0 ? _pile.cardH : 0, implicitHeight)
                                    stretchPhoto: _pile.cardH >= Style.dp(140)
                                    fitWidth: _pile.fitW
                                    dropStacking: false
                                    // Dimmed in its place while its picture is dragged.
                                    opacity: (_page.dragSlug === slug && _page.dragGhost.length) ? 0.4 : 1
                                    onLiftingChanged: {
                                        if (lifting)
                                            _pile.freezeSlot()
                                        else
                                            _pile.thawSlot()
                                    }
                                    // Resizing holds the page still, like a move does.
                                    onResizingChanged: {
                                        if (resizing)
                                            _pile.freezeSlot()
                                        else
                                            _pile.thawSlot()
                                    }
                                    onImplicitHeightChanged: {
                                        if (index === 0)
                                            _pile.leadH = implicitHeight
                                    }
                                    Component.onCompleted: {
                                        _page.fillCard(_card, modelData)
                                        _page.bindCard(_card)
                                        if (index === 0)
                                            _pile.leadH = implicitHeight
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // The dragged card's picture under the pointer, as the Device Bindings
    // rows show theirs (ControlTree): 0.85 opaque.
    Image {
        id: _float
        objectName: "homeDragPicture"
        visible: _page.dragSlug.length > 0 && _page.dragGhost.length > 0
        z: 100000
        x: _page.floatX
        y: _page.floatY
        width: _page.ghostW
        height: _page.ghostH
        source: _page.dragGhost
        cache: false
        opacity: 0.85
    }

    // Where the card will go: a 2 dp line between the cards (ControlTree's
    // insert line, upright here).
    Rectangle {
        id: _dropLine
        objectName: "homeDropLine"
        visible: _page.dragSlug.length > 0 && _page.dropLineShown
        z: 99999
        x: Math.round(_page.dropLineX - width / 2)
        y: _page.dropLineY
        width: Style.dp(2)
        height: _page.dropLineH
        color: Style.info
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
                MenuModel.action("Unhide All Cards", function() {
                    if (_page.model)
                        _page.model.unignoreAll()
                }, !!(_page.model && _page.model.hiddenList().length)),
                MenuModel.action("Reset All Card Sizes", function() { _page.resetAllCardSizes() })
            ], [
                // Opens to list each hidden card; clicking one unhides it.
                MenuModel.section("hidden", "Hidden Cards", _page.hiddenCardRows()),
                MenuModel.section("layout", "Layout", [
                    MenuModel.command("view.layout.single"),
                    MenuModel.command("view.layout.side"),
                    MenuModel.command("view.layout.stacked")
                ])
            ])
        }
    }

    // Home menu → Hidden Cards: a row per hidden card (by name). With none
    // hidden the section is left out of the menu.
    function hiddenCardRows() {
        var cards = _page.model ? _page.model.hiddenCards() : []
        return cards.map(function(card) {
            return MenuModel.action(card.name, function() {
                if (_page.model)
                    _page.model.unignoreSlug(card.slug)
            })
        })
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
        function onCantSendChanged() {
            Qt.callLater(_page.refreshCards)
        }
        // Driven by and the shown name are filled by hand (fillCard): they
        // follow while Home is shown (D-01-OWNER-NOTICES 1a, 2a).
        function onTargetsChanged() {
            Qt.callLater(_page.refreshCards)
        }
        function onNamesChanged() {
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
            _page.askConfirm()
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

    DismissibleDialog {
        id: _startFreshGate
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
        text: "No devices to show. Plug in hardware, or right-click here → Hidden Cards to show one again."
        color: Style.fgMuted
    }
}
