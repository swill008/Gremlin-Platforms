// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import Gremlin.Menus
import "helpers.js" as Helpers
import "confirm.js" as Confirm
import "rig_commands.js" as RigCommands

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _editorWin

    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1180
    height: 980
    minimumWidth: Style.fitWidth(Style.dp(880), Screen)
    minimumHeight: Style.fitHeight(Style.dp(720), Screen)

    color: Style.background
    U.Universal.theme: Style.theme

    title: targetName.length ? ("Device Mapping Editor — " + targetName) : "Device Mapping Editor"

    ToolWindowMemory {
        host: _editorWin
        name: "device-mapping-editor"
        defaultWidth: Style.dp(1180)
        defaultHeight: Style.dp(980)
    }

    onClosing: (e) => {
        if (_allowClose || !editing)
            return
        if (!isDirty()) {
            endEditUnsaved()
            return
        }
        e.accepted = false
        askLeave("close")
    }

    property string leaveKind: ""
    property string targetName: ""
    // The map's parts of the module file as this window last read or wrote
    // them: another window may change the file meanwhile (History Restore,
    // Device Pack, Module Setup's Import Image; 07 Q6).
    property string _fileParts: ""
    // A Save that asked Keep mine / Take theirs: its report flag, and
    // whether a leave (close, switch...) waits for it.
    property bool _conflictReport: true
    property bool _leaveAfterSave: false
    property bool _conflictAsking: false

    function filePartsNow() {
        return targetName.length ? _fileWatch.mapParts(targetName, targetGuid) : ""
    }

    // This window's own change of the file is not a change made elsewhere;
    // one made elsewhere before it still is.
    function ownFileChange(change) {
        var unchanged = filePartsNow() === _fileParts
        var result = change()
        if (unchanged)
            _fileParts = filePartsNow()
        return result
    }

    function askLeave(kind) {
        leaveKind = kind
        // (A Save's Keep mine / Take theirs question, if open, is replaced.)
        _conflictAsking = false
        _leaveAfterSave = false
        _saveGate.detail = "Editor changes are not saved. Leave without saving and this work will be lost."
        _saveGate.ask()
    }
    property string targetGuid: ""
    // Given by Main.qml when it opens the window; not used: the map's own
    // background is all that shows (07 S11).
    property string loadedDevice: ""
    property string pendingDevice: ""
    property string pendingGuid: ""
    property bool startBlank: false
    property bool faceLive: false

    // Device list changes (plugged in, unplugged): bindings that ask the list
    // follow this.
    property int devTick: 0
    // The device can show: outputs, Keyboard, Logical Device and OSC always,
    // a stick only while connected.
    readonly property bool targetConnected: {
        devTick
        return targetName.length > 0 && _devices.available(targetGuid, targetName)
    }
    // The map shows while the device is there, and an edit stays on screen
    // (so it can be saved or cancelled) when its stick is unplugged. Hidden,
    // it is still there under a cover: Export still works without the stick.
    readonly property bool mapShown: targetName.length > 0 && (targetConnected || editing)
    // One card per device: devices coming and going leave it (and its undo
    // history) alone.
    readonly property string cardKey: targetName.length ? (targetGuid + "|" + targetName) : ""
    // The device's row in the list, for its id and what it is wired to.
    readonly property var targetRow: {
        devTick
        var rows = _devices.listRows() || []
        for (var i = 0; i < rows.length; i++) {
            if (isTarget(rows[i].guid, rows[i].name))
                return rows[i]
        }
        return null
    }

    Connections {
        target: _devices
        function onModelReset() {
            var was = _editorWin.targetConnected
            _editorWin.devTick++
            // The stick came back: its map loads again (an edit keeps its work).
            if (!was && _editorWin.targetConnected && !_editorWin.editing) {
                try {
                    _editorWin.loadLive()
                } catch (e) {
                    console.warn("Device Mapping Editor reload failed", e)
                }
            }
        }
    }

    property int _nameTick: 0
    property bool editing: false
    // No tool rows (07 S99): the menu bar, Chips on the left and the right
    // side panel (Layers, Properties under it). Device Map Options and
    // Keyboard Shortcuts are small windows of their own (S98, S100).
    onEditingChanged: {
        poolDrag = false
        Qt.callLater(fitSides)
        if (editing)
            Qt.callLater(refreshReservoir)
        else
            setEditPlane("foreground")
    }
    property var liveNodes
    property var workNodes
    // The bottom background picture ("the device's photo", 07 S127) of the
    // map shown, for the view: its load and size recover the view.
    property string photoOverride: ""
    property bool fittedOldPage: false
    property bool fittedThisEdit: false
    property real viewPctSave: 1
    property real viewPanX: 0
    property real viewPanY: 0
    property string selectedId: ""
    property var selectedNode: null
    property bool _allowClose: false
    property var resItems
    property int resTick: 0
    property string poolFilter: ""
    onPoolFilterChanged: refreshReservoir()
    property bool poolDrag: false
    property string poolKind: "btn"
    property int poolHw: 0
    property string poolName: ""
    property real poolX: 0
    property real poolY: 0
    property bool gridOn: true
    property bool snapOn: true
    property bool snapEntOn: true
    property int gridSize: 8
    property bool saveOk: true

    ViewerDeviceModel { id: _devices }
    HardwareProfile { id: _hw }
    ModuleFileWatch { id: _fileWatch }
    DeviceMapOptions {
        id: _opts
        onChanged: _editorWin.applyOptionsToEditor()
    }
    // Space held: the map pans with a left-drag in Edit (07 S14).
    DeviceMapSpaceKey { id: _spaceKey }
    Binding {
        target: _cardLoader.item && _cardLoader.item.editorItem ? _cardLoader.item.editorItem.face : null
        property: "spaceHeld"
        value: _spaceKey.held && !(_cardLoader.item.editorItem.renameId)
        when: !!(_cardLoader.item && _cardLoader.item.editorItem && _cardLoader.item.editorItem.face)
        restoreMode: Binding.RestoreNone
    }

    Instantiator {
        id: _inputDeviceItems
        model: _devices
        delegate: ThemedMenuItem {
            required property string name
            required property string guid
            text: name
            // Listed during an edit too: switching asks to save first.
            checkable: true
            checked: name === _editorWin.targetName
            onTriggered: {
                // A click flips 'checked': the tick follows the device shown.
                checked = Qt.binding(() => name === _editorWin.targetName)
                _editorWin.openForDevice(name, guid)
            }
        }
        // File → Device: the devices to switch to, under their own heading.
        onObjectAdded: function(index, object) {
            _deviceMenu.insertItem(index, object)
        }
        onObjectRemoved: function(index, object) {
            _deviceMenu.removeItem(object)
        }
    }

    DeviceNames {
        id: _names
        onChanged: _editorWin._nameTick++
    }

    function displayName(guid, name) {
        if (!_names) {
            return name
        }
        return _nameTick, _names.display(guid, name)
    }

    function sameGuid(a, b) {
        var left = String(a || "").toLowerCase().replace(/[{}-]/g, "")
        var right = String(b || "").toLowerCase().replace(/[{}-]/g, "")
        return left.length > 0 && left === right
    }

    function isTarget(guid, name) {
        if (sameGuid(guid, targetGuid))
            return true
        if (!targetName.length)
            return false
        var raw = String(name || "")
        var shown = String(displayName(guid, raw) || "")
        var t = targetName.toLowerCase()
        return raw.toLowerCase() === t || shown.toLowerCase() === t
    }

    function parseDoc(text) {
        try {
            var d = JSON.parse(text)
            return (d && d.nodes) ? d : null
        } catch (e) {
            return null
        }
    }

    function hydrateOverlays(list) {
        if (!list)
            return
        var e = _ed()
        if (e)
            giveLookMaker(e)
        var i
        for (i = 0; i < list.length; i++) {
            var n = list[i]
            if (n && n.shape === "image" && n.src) {
                n.srcUrl = _hw.imageUrl(n.src)
                // A picture's look (07 S43) shows from an adjusted copy.
                if (n.look && e && e.refreshLookUrl)
                    e.refreshLookUrl(n)
            }
        }
    }

    // The editor makes a picture's look copy through this window's
    // HardwareProfile (adjustedPhotoUrl, 07 S43).
    function giveLookMaker(e) {
        if (e && typeof e.lookUrlFor !== "function")
            e.lookUrlFor = function(url, look) { return _hw.adjustedPhotoUrl(url, look) }
    }

    // The bottom background picture of a node list (07 S127): its address,
    // or "" when the background has no picture.
    function bottomPictureUrl(list) {
        for (var i = 0; i < (list || []).length; i++) {
            var n = list[i]
            if (n && n.plane === "background" && n.shape === "image" && n.src)
                return n.srcUrl || _hw.imageUrl(n.src)
        }
        return ""
    }

    function notePhoto(list) {
        photoOverride = bottomPictureUrl(list)
    }

    function sceneShiftList(list) {
        if (!list)
            return
        function pos(v) { return Math.max(0, Math.min(1, 0.25 + (v || 0) * 0.5)) }
        function sz(v) { return (v || 0) * 0.5 }
        // While editing, a node's older spine list (n.spines) and its leader's
        // are often the same array, and ends can be shared too: shift each
        // point once, or spines land far off toward the middle (as rig_mirror
        // does with its done list).
        var done = []
        function once(obj) {
            if (!obj || done.indexOf(obj) >= 0)
                return false
            done.push(obj)
            return true
        }
        function mapEnd(e) {
            if (e && e.type === "free" && once(e)) {
                e.fx = pos(e.fx)
                e.fy = pos(e.fy)
            }
        }
        function mapSpines(arr) {
            if (!arr)
                return
            var s
            for (s = 0; s < arr.length; s++) {
                if (!once(arr[s]))
                    continue
                arr[s].fx = pos(arr[s].fx)
                arr[s].fy = pos(arr[s].fy)
            }
        }
        var i
        var k
        for (i = 0; i < list.length; i++) {
            var n = list[i]
            if (!n)
                continue
            if (n.chipFx !== undefined) n.chipFx = pos(n.chipFx)
            if (n.chipFy !== undefined) n.chipFy = pos(n.chipFy)
            if (n.fx !== undefined) n.fx = pos(n.fx)
            if (n.fy !== undefined) n.fy = pos(n.fy)
            if (n.fw !== undefined) n.fw = sz(n.fw)
            if (n.fh !== undefined) n.fh = sz(n.fh)
            // The hotspot and a callout's free pointer move with the rest.
            if (n.hotFx !== undefined) n.hotFx = pos(n.hotFx)
            if (n.hotFy !== undefined) n.hotFy = pos(n.hotFy)
            if (n.tail && n.tail.fx !== undefined && once(n.tail)) {
                n.tail.fx = pos(n.tail.fx)
                n.tail.fy = pos(n.tail.fy)
            }
            // Table cells moved off on their own (independent) too.
            var rows = n.rows || []
            for (k = 0; k < rows.length; k++) {
                var cells = (rows[k] && rows[k].cells) || []
                for (var c = 0; c < cells.length; c++) {
                    var cell = cells[c]
                    if (!cell || !once(cell))
                        continue
                    if (cell.efx !== undefined) cell.efx = pos(cell.efx)
                    if (cell.efy !== undefined) cell.efy = pos(cell.efy)
                    if (cell.efw !== undefined) cell.efw = sz(cell.efw)
                    if (cell.efh !== undefined) cell.efh = sz(cell.efh)
                }
            }
            var extras = n.extras || []
            for (k = 0; k < extras.length; k++) {
                if (!extras[k])
                    continue
                if (extras[k].efx !== undefined) extras[k].efx = pos(extras[k].efx)
                if (extras[k].efy !== undefined) extras[k].efy = pos(extras[k].efy)
                if (extras[k].efw !== undefined) extras[k].efw = sz(extras[k].efw)
                if (extras[k].efh !== undefined) extras[k].efh = sz(extras[k].efh)
            }
            var mem = n.members || []
            for (k = 0; k < mem.length; k++) {
                if (mem[k].ox !== undefined) mem[k].ox = sz(mem[k].ox)
                if (mem[k].oy !== undefined) mem[k].oy = sz(mem[k].oy)
                if (mem[k].offX !== undefined) mem[k].offX = sz(mem[k].offX)
                if (mem[k].offY !== undefined) mem[k].offY = sz(mem[k].offY)
            }
            mapSpines(n.spines)
            mapEnd(n.from)
            mapEnd(n.to)
            var leads = n.leaders || []
            for (k = 0; k < leads.length; k++) {
                mapSpines(leads[k].spines)
                mapEnd(leads[k].from)
                mapEnd(leads[k].to)
            }
        }
    }


    // followChange: the file changed elsewhere and the map follows it (not
    // an opening: a kept edit folder is left alone, it may be another
    // window's).
    function loadLive(followChange) {
        if (_hw.setDeviceGuid)
            _hw.setDeviceGuid(targetGuid)
        // An edit that never finished (the program closed mid-edit, 07 S36):
        // its temporary folder is dropped, or a Save cut short is put back.
        // Kept while unsaved edits wait to be offered: Restore and Not now
        // keep its pictures, Discard drops them (putSavedMapBack).
        if (!followChange && !editing && targetName.length)
            _hw.recoverEdit(targetName)
        _fileParts = filePartsNow()
        var text = _hw.load(targetName)
        var doc = parseDoc(text)
        if (!doc || !doc.nodes) {
            return false
        }
        // Both planes are nodes (07 S111); an old map's photo is already
        // its bottom background picture (load, 07 S125).
        liveNodes = JSON.parse(JSON.stringify(doc.nodes))
        hydrateOverlays(liveNodes)
        notePhoto(liveNodes)
        if (doc.ui)
            applyUi(doc.ui)
        applyGridToEditor()
        applyViewToFace()
        return true
    }

    // File › Edit Mapping, Ctrl+E and the view-only banner's link all
    // start editing here, with the same refusals (D-FIXLIST-B1).
    readonly property bool canEnterEdit: !editing && targetName.length > 0

    function enterEdit() {
        if (!canEnterEdit)
            return
        // Unsaved edits a crash left (put off with Not now) are offered
        // again: a new session would write over their copy, and Cancel
        // would delete it with their pictures. Restore starts Edit with them.
        if (offerRecovery())
            return
        _startEdit()
    }

    function _startEdit() {
        if (editing)
            return
        if (!sidesRestored)
            restoreSides()
        // (Pictures left by a session that never finished were put back by
        // loadLive.)
        try {
            loadLive()
        } catch (e) {
            console.warn("Device Mapping Editor loadLive failed", e)
        }
        var src = []
        try {
            src = JSON.parse(JSON.stringify(liveNodes || []))
        } catch (e2) {
            console.warn("Device Mapping Editor clone nodes failed", e2)
            src = []
        }
        workNodes = src
        hydrateOverlays(workNodes)
        // The print area, print setup and guides as this edit starts:
        // Cancel puts them back (07 Q1).
        noteEditUiBase()
        editing = true
        // The map as the editor tidies it on loading is where this edit
        // starts (taken when the editor is done: noteSeeded).
        editBase = null
        _baseWanted = true
        fittedThisEdit = false
        fitHistAt = -1
        selectedId = ""
        selectedNode = null
        Qt.callLater(function() {
            refreshReservoir()
            applyGridToEditor()
            hydrateOverlays((_ed() && _ed().nodes) ? _ed().nodes : workNodes)
        })
    }

    // keepMine: write over a change made elsewhere since this edit started
    // (the user chose Keep mine).
    function saveEdit(report, keepMine) {
        if (report === undefined)
            report = true
        // Changed elsewhere since this edit started: ask before writing over
        // it (07 Q6); nothing is written until the user chooses.
        if (!keepMine && targetName.length && filePartsNow() !== _fileParts) {
            saveOk = false
            _conflictReport = report
            _conflictAsking = true
            _saveGate.choose("Module File Changed",
                "The module file changed since you started editing (another window saved it).\n\n"
                + "Keep Mine writes your edits over that change. Take Theirs drops your edits "
                + "and shows the file as it is now.",
                "Keep Mine", "Take Theirs")
            return false
        }
        var ed = _cardLoader.item ? _cardLoader.item.editorItem : null
        // A drag left open ends as its one Undo step before the map is
        // written, so it can't hold Undo in the next edit (07 S55a).
        if (ed && ed.stopGesture)
            ed.stopGesture()
        // A name or text still being typed (Ctrl+S) is saved with the rest.
        if (ed && ed.renameId)
            ed.commitRename()
        var nodes = []
        if (ed && ed.nodes)
            nodes = ed.nodes
        else if (workNodes)
            nodes = workNodes
        // Both planes are in the nodes (07 S111): no photo of its own.
        var doc = {
            kind: "control.hardware",
            device: targetName,
            space: "world",
            // The page size is stamped by Save (hardware_profile.PAGE_SIZE).
            imageWidth: 1348,
            imageHeight: 1380,
            ui: uiBag(),
            nodes: nodes
        }
        var payload = JSON.stringify(doc)
        if (!_hw.save(targetName, payload)) {
            saveOk = false
            if (report) {
                say("Not written. It is still only on this screen.", true)
                if (backend)
                    backend.noteSave("The module file was not written.")
            }
            return false
        }
        var check = parseDoc(_hw.load(targetName))
        if (!check || !check.nodes) {
            saveOk = false
            if (report) {
                say("Saved to the module file, but it could not be read back.", true)
                if (backend)
                    backend.noteSave("Saved the module file to " + _hw.path + ", but it could not be read back.")
            }
            return false
        }
        liveNodes = JSON.parse(JSON.stringify(nodes))
        _fileParts = filePartsNow()
        // Saved: later changes are compared with what was just saved.
        editBase = JSON.stringify(nodes)
        _baseWanted = false
        noteEditUiBase()
        clearRecovery()
        hydrateOverlays(liveNodes)
        notePhoto(liveNodes)
        saveOk = true
        if (report) {
            say("Saved to the module file.")
            if (backend)
                backend.noteSave("Saved the module file to " + _hw.path)
        }
        return true
    }

    function editorNodesNow() {
        var ed = _cardLoader.item ? _cardLoader.item.editorItem : null
        if (ed && ed.nodes && ed.nodes.length)
            return ed.nodes
        return workNodes
    }

    // The map at the start of this edit as the editor tidied it (default
    // leaders, names, stacking filled in): tidying is not a change. null:
    // compared with the saved map (a restored or copied map, or before the
    // editor is done).
    property var editBase: null
    property bool _baseWanted: false

    function noteSeeded() {
        var e = _ed()
        if (!editing || !_baseWanted || !e || !e.seeded)
            return
        _baseWanted = false
        editBase = JSON.stringify(e.nodes || [])
    }

    function isDirty() {
        if (!editing)
            return false
        // The print area, print setup or guides changed in this edit.
        if (editUiChanged())
            return true
        // Both planes are nodes: a background change (a picture added,
        // replaced, moved or cleared) shows here too (07 S30). A new
        // picture always has a name of its own (07 S107).
        try {
            var now = JSON.stringify(editorNodesNow())
            var base = editBase !== null ? editBase : JSON.stringify(liveNodes)
            return now !== base
        } catch (e) {
            return true
        }
    }

    // --- recovery copies (Device Map Options → Recovery copies) -----------

    property string _lastRecovery: ""
    property var _pendingRecovery: null

    function recoveryPayload() {
        return JSON.stringify({
            nodes: editorNodesNow()
        })
    }

    // Writes a recovery copy when there are unsaved changes; with none left
    // (everything undone), removes it.
    function recoveryNow() {
        if (!editing || !targetName.length)
            return
        if (!isDirty()) {
            if (_lastRecovery.length) {
                _hw.clearRecovery(targetName)
                _lastRecovery = ""
            }
            return
        }
        var payload = recoveryPayload()
        if (payload === _lastRecovery)
            return
        if (_hw.saveRecovery(targetName, payload))
            _lastRecovery = payload
    }

    function clearRecovery() {
        _lastRecovery = ""
        if (targetName.length)
            _hw.clearRecovery(targetName)
    }

    // After a device opens, or on Edit: offer unsaved edits a crash left
    // behind. True when the offer is shown.
    function offerRecovery() {
        if (editing || !targetName.length)
            return false
        var text = _hw.loadRecovery(targetName)
        if (!text.length)
            return false
        var doc = null
        try { doc = JSON.parse(text) } catch (e) { doc = null }
        if (!doc || !doc.nodes)
            return false
        var same = false
        try {
            same = JSON.stringify(doc.nodes) === JSON.stringify(liveNodes)
        } catch (e2) {}
        if (same) {
            _hw.clearRecovery(targetName)
            return false
        }
        _pendingRecovery = doc
        var when = String(doc.savedAt || "").replace("T", " at ")
        _recoverGate.choose("Unsaved Edits Found",
                            "The Device Mapping Editor has edits to " + targetName + (when.length ? " from " + when : "")
                            + " that were never saved, probably because the program closed unexpectedly.\n\n"
                            + "Restore opens them for editing; save to keep them. Discard deletes them.",
                            "Restore", "Discard")
        _recoverGate.cancelText = "Not now"
        return true
    }

    // The recovery copy was discarded: the pictures its edit kept go and the
    // saved map (both planes) reads again (07 S34).
    function putSavedMapBack() {
        if (editing || !targetName.length || !_hw.cancelEdit(targetName))
            return
        loadLive()
    }

    // Not now: the copy and its pictures stay as they are, offered again the
    // next time this device's map opens.
    function putOffRecovery() {
        _pendingRecovery = null
    }

    // Another device (or a blank page) is about to show: an offer still open
    // is put off, never applied to the next device or deleted.
    function dropRecoveryOffer() {
        if (!_pendingRecovery && !_recoverGate.opened)
            return
        putOffRecovery()
        if (_recoverGate.opened)
            _recoverGate.close()
    }

    function restoreRecovery() {
        var doc = _pendingRecovery
        _pendingRecovery = null
        // (Only ever this device's copy: another device showing puts the
        // offer off, dropRecoveryOffer. The copy is found by module file, so
        // a stick renamed since keeps its copy under the old name.)
        if (!doc || editing)
            return
        _startEdit()
        // This session carries on with the copy: Save or Cancel removes it.
        _lastRecovery = JSON.stringify(doc)
        // The restored work is unsaved: compared with the saved map.
        _baseWanted = false
        // Both planes come back (their pictures kept in the edit's
        // temporary folder, 07 S36).
        var nodes = JSON.parse(JSON.stringify(doc.nodes || []))
        hydrateOverlays(nodes)
        workNodes = nodes
        Qt.callLater(function() {
            var e = _ed()
            if (e && e.seedHist)
                e.seedHist()
            refreshReservoir()
        })
    }

    Timer {
        id: _recoveryTimer
        interval: Math.max(10, Number(_opts.values["recovery-seconds"]) || 60) * 1000
        repeat: true
        running: _editorWin.editing && _opts.values["recovery-copies"] !== false
        onTriggered: _editorWin.recoveryNow()
    }

    // Every way out of an edit without saving (Cancel, Discard, closing the
    // window or quitting with nothing unsaved): a drag left open stops
    // (07 S55a), the edit's own recovery copy goes, also when every change
    // was undone before the timer removed it (S32, S34), and so do the
    // pictures it added. Outside Edit, a copy left by a crash (put off with
    // Not now) keeps both; Edit offers that copy before it starts, so a
    // session's copy is one it wrote or restored.
    function endEditUnsaved() {
        if (!editing)
            return
        var e = _ed()
        if (e && e.stopGesture)
            e.stopGesture()
        if (_lastRecovery.length)
            clearRecovery()
        // Pictures this edit added go with its temporary folder; the
        // device's folder was never touched (07 S26, S107).
        dropUnusedPictures()
    }

    function discardEdit() {
        if (editing) {
            endEditUnsaved()
            // So do the print area, print setup and guides (07 Q1).
            restoreEditUi()
        }
        _editUi = null
        editBase = null
        _baseWanted = false
        editing = false
        workNodes = []
        selectedId = ""
        selectedNode = null
        notePhoto(liveNodes)
        // The discarded edits leave no undo steps behind: start the history
        // again from the live map once it is back on screen.
        Qt.callLater(function() {
            var e = _ed()
            if (e)
                e.seedHist()
        })
    }

    // Take theirs: this edit goes (its added pictures with it) and the file
    // shows as it is now, with whatever background the other window saved.
    function takeTheirs() {
        discardEdit()
        loadLive(true)
    }

    function cancelEdit() {
        if (isDirty()) {
            askLeave("cancel")
            return
        }
        discardEdit()
    }

    function requestLeaveForAppQuit() {
        show()
        raise()
        requestActivate()
        if (_allowClose || !editing || !isDirty()) {
            if (!_allowClose)
                endEditUnsaved()
            _allowClose = true
            close()
            Qt.quit()
            return
        }
        askLeave("appquit")
    }

    function confirmLeaveSave() {
        _leaveAfterSave = true
        saveEdit()
        // The file changed elsewhere: Keep mine saves and then leaves.
        if (_conflictAsking)
            return
        _leaveAfterSave = false
        if (!saveOk)
            return
        finishLeave()
    }

    // An edit ended (saved, cancelled or the window closed): its temporary
    // folder goes, with every picture it added and Save did not keep
    // (07 S107). Save already put the kept ones in the device's folder.
    function dropUnusedPictures() {
        if (!targetName.length)
            return
        releaseEditPictures()
        _hw.cancelEdit(targetName)
    }

    // Before an edit's temporary folder goes, the editor lets go of the
    // pictures only that edit shows: one still loading (just pasted or
    // dropped) would otherwise go on reading a file that is gone and warn
    // "Cannot open" (D-TESTLIST-1 item 3). Clearing a picture's address
    // stops its load at once; the saved map's own pictures are kept, so
    // they don't load again.
    function releaseEditPictures() {
        var e = _ed()
        var list = (e && e.nodes) || []
        var keep = {}
        var i
        var live = liveNodes || []
        for (i = 0; i < live.length; i++) {
            var l = live[i]
            if (l && l.srcUrl)
                keep[l.srcUrl] = true
            if (l && l.lookUrl)
                keep[l.lookUrl] = true
        }
        var changed = false
        for (i = 0; i < list.length; i++) {
            var n = list[i]
            if (!n || n.shape !== "image")
                continue
            if (n.srcUrl && !keep[n.srcUrl]) {
                n.srcUrl = ""
                changed = true
            }
            if (n.lookUrl && !keep[n.lookUrl]) {
                n.lookUrl = ""
                changed = true
            }
        }
        if (changed && e.repaint)
            e.repaint()
    }

    function finishLeave() {
        if (leaveKind === "close") {
            dropUnusedPictures()
            editing = false
            _allowClose = true
            close()
        } else if (leaveKind === "switch") {
            finishSwitch(pendingDevice)
        } else if (leaveKind === "blank") {
            clearToBlank()
        } else if (leaveKind === "cancel") {
            // Saved: leave Edit (the saved map is what shows).
            discardEdit()
        } else if (leaveKind === "appquit") {
            dropUnusedPictures()
            _allowClose = true
            close()
            Qt.quit()
        }
    }

    function confirmLeaveDiscard() {
        discardEdit()
        if (leaveKind === "switch")
            finishSwitch(pendingDevice)
        if (leaveKind === "blank")
            clearToBlank()
        if (leaveKind === "close" || leaveKind === "appquit") {
            _allowClose = true
            close()
        }
        if (leaveKind === "appquit")
            Qt.quit()
    }

    function currentNode() {
        var ed = _cardLoader.item ? _cardLoader.item.editorItem : null
        if (ed && ed.selectedId) {
            return ed.nodeAt(ed.selectedId)
        }
        return null
    }

    function openColorField(field, hex, anchorItem) {
        if (!_colorPop)
            return
        _colorPop.openField(field, hex, anchorItem)
    }

    function applySelected() {
        var n = currentNode()
        selectedNode = n
        selectedId = n ? n.id : ""
    }

    // No map: an empty background, never another device's pictures (07 S11).
    function showBlank() {
        liveNodes = []
        workNodes = []
        photoOverride = ""
    }

    function clearToBlank() {
        dropRecoveryOffer()
        discardEdit()
        faceLive = false
        targetName = ""
        loadedDevice = ""
        pendingDevice = ""
        showBlank()
    }

    function openBlank() {
        if (editing && isDirty()) {
            pendingDevice = ""
            show()
            raise()
            requestActivate()
            askLeave("blank")
            return
        }
        clearToBlank()
        show()
        raise()
        requestActivate()
    }

    function finishSwitch(next) {
        var name = String(next || "")
        if (!name.length) {
            pendingDevice = ""
            return
        }
        dropRecoveryOffer()
        discardEdit()
        targetName = name
        targetGuid = pendingGuid
        loadedDevice = name
        // This device's own map only; never the previous device's (07 S11).
        if (!loadLive())
            showBlank()
        pendingDevice = ""
        Qt.callLater(offerRecovery)
    }

    function openForDevice(name, guid) {
        var next = String(name || "")
        pendingGuid = String(guid || "")
        if (!next.length)
            return
        if (next === loadedDevice && sameGuid(pendingGuid, targetGuid) && faceLive) {
            show()
            raise()
            requestActivate()
            return
        }
        if (editing && isDirty()) {
            pendingDevice = next
            show()
            raise()
            requestActivate()
            askLeave("switch")
            return
        }
        finishSwitch(next)
        show()
        raise()
        requestActivate()
    }

    Component.onCompleted: {
        // Insert, Arrange and Format from the command list (07 S134).
        buildCommandMenus()
        // The kept side panels, divider and print area frame (07 S99).
        readPanelStore()
        Qt.callLater(restoreSides)
        profileModes = _hw.profileModes()
        liveNodes = []
        workNodes = []
        resItems = []
        if (_devices)
            _devices.reload()
        if (startBlank || !targetName.length) {
            targetName = ""
            loadedDevice = ""
            showBlank()
            return
        }
        loadedDevice = targetName
        if (!loadLive())
            showBlank()
        Qt.callLater(offerRecovery)
    }

    DismissibleDialog {
        id: _recoverGate
        onConfirmed: _editorWin.restoreRecovery()
        onDiscarded: {
            _editorWin._pendingRecovery = null
            _editorWin.clearRecovery()
            _editorWin.putSavedMapBack()
        }
        onCancelled: _editorWin.putOffRecovery()
    }

    // What just happened, on the shared message line (01 S142): plain for
    // done, red for failed; it stays until the next message.
    function say(text, failed) {
        _messageLine.show(text, failed === true)
    }

    // Something the user asked for did not happen: say so, in red. Asked
    // from the Templates window, it says so there.
    function tellFailure(title, message) {
        var text = message || (title + ".")
        if (_templatesDlg.opened)
            _templatesMessage.show(text, true)
        else
            say(text, true)
    }

    // Leave questions (Save / Discard / Cancel), and Save's question when
    // the module file changed elsewhere during the edit (07 Q6): Keep mine
    // / Take theirs / Cancel.
    DismissibleDialog {
        id: _saveGate
        onSaveChosen: _editorWin.confirmLeaveSave()
        onConfirmed: {
            if (!_editorWin._conflictAsking)
                return
            var leave = _editorWin._leaveAfterSave
            _editorWin._conflictAsking = false
            _editorWin._leaveAfterSave = false
            _editorWin.saveEdit(_editorWin._conflictReport, true)
            if (leave && _editorWin.saveOk)
                _editorWin.finishLeave()
        }
        onDiscardChosen: {
            if (!_editorWin._conflictAsking) {
                _editorWin.confirmLeaveDiscard()
                return
            }
            var leave = _editorWin._leaveAfterSave
            _editorWin._conflictAsking = false
            _editorWin._leaveAfterSave = false
            _editorWin.takeTheirs()
            if (leave)
                _editorWin.finishLeave()
        }
        onCancelled: {
            _editorWin._conflictAsking = false
            _editorWin._leaveAfterSave = false
            _editorWin.pendingDevice = ""
        }
    }

    // Outside Edit the map follows its module file when another window
    // changes it (History Restore, Device Pack, Module Setup; 07 Q6), told
    // by the store's "module files changed" notice (D-01-OWNER-NOTICES).
    Connections {
        target: _fileWatch
        function onChanged() {
            if (!_editorWin.visible || _editorWin.editing)
                return
            if (_editorWin.loadedDevice !== _editorWin.targetName)
                return
            if (_editorWin.filePartsNow() === _editorWin._fileParts)
                return
            _editorWin.loadLive(true)
        }
    }

    // Reset Layout (07 S61): the shared question (01 S140).
    function askResetLayout() {
        return Confirm.ask(_editorWin.contentItem, {
            title: "Reset the layout?",
            text: "Clears everything from the map: chips, leaders, hotspots, drawings, text boxes, pictures and tables. Actions are not changed. File → Cancel leaves editing without keeping the reset; Save makes the empty map the live one.",
            note: "Ctrl+Z brings the layout back.",
            action: "Reset Layout",
            onAccept: function() { _editorWin.resetLayout() }
        })
    }

    // Help (F1): the one Help window on the Device Mapping Editor chapter (01 S128).
    function openGuide() {
        Helpers.createComponent("DialogHelp.qml", { chapter: "device-mapping-editor" })
    }

    function _ed() {
        return _cardLoader.item ? _cardLoader.item.editorItem : null
    }

    // What Ctrl+C copied, kept when another device's map opens (each map
    // has its own editor: copy on one stick, paste on the other).
    property var keptCopy: []
    property int keptCopySerial: -1

    function carryCopy(card) {
        Qt.callLater(function() {
            var e = card ? card.editorItem : null
            if (!e)
                return
            if (keptCopy.length) {
                e.copiedNodes = keptCopy
                e.clipSerial = keptCopySerial
            }
            // Both, whichever changes last: the copy and the clipboard
            // count it was made at (a stale count pasted the clipboard's
            // picture instead of the copy on the next device).
            function keep() {
                _editorWin.keptCopy = e.copiedNodes || []
                _editorWin.keptCopySerial = e.clipSerial
            }
            e.copiedNodesChanged.connect(keep)
            e.clipSerialChanged.connect(keep)
        })
    }

    function poolHaystack(row) {
        if (!row)
            return ""
        var hw = row.hwId
        var kind = row.kind || "btn"
        var alias = ""
        if (kind === "axis")
            alias = "axis " + hw + " a" + hw
        else if (kind === "hat")
            alias = "hat " + hw + " h" + hw
        else
            alias = "button " + hw + " btn " + hw + " b" + hw
        return [
            row.friendly || "",
            row.hwName || "",
            row.fullName || "",
            row.dest && row.dest !== "—" ? row.dest : "",
            kind,
            String(hw),
            alias
        ].join(" ").toLowerCase()
    }

    function poolMatches(row, q) {
        if (!q.length)
            return true
        var hay = poolHaystack(row)
        if (hay.indexOf(q) >= 0)
            return true
        var toks = q.split(/\s+/)
        for (var i = 0; i < toks.length; i++) {
            if (!toks[i].length)
                continue
            if (hay.indexOf(toks[i]) < 0)
                return false
        }
        return true
    }

    function refreshReservoir() {
        if (!faceLive)
            return
        var e = _ed()
        var all = (e && e.catalog) ? e.catalog() : []
        var q = (poolFilter || "").trim().toLowerCase()
        var u = []
        for (var i = 0; i < all.length; i++) {
            var row = all[i]
            if (row.placed)
                continue
            if (!poolMatches(row, q))
                continue
            u.push(row)
        }
        resItems = u
    }

    function clearPoolFilter() {
        poolFilter = ""
    }

    function dropPool(vx, vy) {
        var kind = poolKind
        var hw = poolHw
        poolDrag = false
        var ed = _ed()
        if (!ed || !kind || !(hw > 0))
            return
        if (_poolFloat && _poolFloat.visible) {
            var lp = _poolFloat.mapFromItem(_mapHost, vx, vy)
            if (lp.x >= 0 && lp.y >= 0 && lp.x <= _poolFloat.width && lp.y <= _poolFloat.height)
                return
        }
        var local = ed.mapFromItem(_mapHost, vx, vy)
        if (local.x < 0 || local.y < 0 || local.x > ed.width || local.y > ed.height)
            return
        ed.addChiplet(kind, hw, local.x, local.y, _opts.values["chip-only"] === true)
        refreshReservoir()
    }

    function resetLayout() {
        var e = _ed()
        if (e)
            e.pushHist()
        workNodes = []
        if (e)
            e.clearLayout()
        selectedId = ""
        selectedNode = null
        Qt.callLater(refreshReservoir)
    }

    // View > Reset View and Ctrl+0.
    function resetViewNow() {
        var f = _cardLoader.item
        if (f && f.resetView)
            f.resetView()
        captureView()
        persistUi()
    }

    function deleteOrBreak() {
        var e = _ed()
        if (!e)
            return
        // A spine, a table cell, or every selected item; a group breaks up.
        // Through rig_commands.js when it applies (07 S137: Repeat sees it).
        if (editing && RigCommands.enabled(e, "edit.delete"))
            RigCommands.run(e, "edit.delete")
        else
            e.deleteSelected()
        applySelected()
        refreshReservoir()
    }

    function captureView() {
        var f = _cardLoader.item
        if (!f)
            return
        viewPctSave = f.viewPct || 1
        viewPanX = f.panX || 0
        viewPanY = f.panY || 0
    }

    // --- side panels: Chips and Layers (07 S99, S128-S131) -----------------

    // The map area's least width: below it the pinned side panels unpin and
    // fold, Chips first, then Layers (S131).
    readonly property real mapMinWidth: Style.dp(420)
    // A side panel this window unpinned and folded for room (S131), or
    // folded for Background mode (S130): it comes back as it was when that
    // ends, unless the user changed it in between. Those folds aren't kept.
    property bool chipsSqueezed: false
    property bool layersSqueezed: false
    property bool chipsBgFolded: false

    // Puts the side panels as they were kept (at start and after Reset
    // Panels).
    // Set once the kept side-panel state is on the panels (restoreSides runs
    // a moment after the window opens; an Edit started before that runs it
    // first, so a panel's built-in width is never saved over the kept one).
    property bool sidesRestored: false
    function restoreSides() {
        sidesRestored = true
        chipsSqueezed = false
        layersSqueezed = false
        chipsBgFolded = false
        var sides = [[_chipsSide, "chips"], [_layersSide, "layers"]]
        for (var i = 0; i < sides.length; i++) {
            var st = _opts.sidePanelState(sides[i][1]) || {}
            // Kept in logical px at 100 % UI scale.
            sides[i][0].panelWidth = Number(st.width) * Style.dp(1)
            sides[i][0].pinned = !!st.pinned
            sides[i][0].open = !!st.open
        }
        readPanelStore()
        if (bgMode)
            bgFoldChips(true)
        Qt.callLater(fitSides)
    }

    // A strip, pin, fold arrow, resize, the View menu or a map click
    // changed a side panel: kept, and the user's choice from now on.
    // While a narrow window has unpinned it (S131), the pin it shows is the
    // window's, not the user's: opening or folding the drawer keeps only
    // open and width, and the kept pin stays for the next window. A click
    // on the pin itself keeps the pin.
    function sideChangedByUser(panel, id) {
        var squeezed = id === "chips" ? chipsSqueezed : layersSqueezed
        var state = { width: panel.panelWidth / Style.dp(1), open: panel.open }
        if (!squeezed || panel.pinned)
            state.pinned = panel.pinned
        if (id === "chips") {
            chipsSqueezed = false
            chipsBgFolded = false
        } else {
            layersSqueezed = false
        }
        _opts.setSidePanelState(id, state)
    }

    // The Layers/Properties divider's share (Layers' part) and the print
    // area's frame, kept in the Device Map settings (07 S99). The store's
    // getters are slots: read again whenever it says something changed.
    property real propsSplit: 0.6
    property bool printAreaOn: false
    function readPanelStore() {
        propsSplit = Number(_opts.propsSplit()) || 0.6
        printAreaOn = !!_opts.printAreaShown()
        propsOn = !!_opts.propsShown()
    }
    Connections {
        target: _opts
        function onPanelsChanged() { _editorWin.readPanelStore() }
    }

    // View > Show Print Area: the print area's frame on the map.
    function setPrintAreaShown(on) {
        printAreaOn = !!on
        _opts.setPrintAreaShown(!!on)
    }

    // View > Reset Panels (07 S99): the side panels and the divider as
    // they first were.
    function resetPanels() {
        _opts.resetPanels()
        propsOn = true
        restoreSides()
    }

    // Properties under Layers (07 S135): shown while something is selected,
    // unless View > Properties (F4) hid it.
    // Kept between sessions (07 S99, user 2026-10-11); read from and saved
    // to the panel store.
    property bool propsOn: true
    onPropsOnChanged: _opts.setPropsShown(propsOn)
    readonly property bool propsHasSelection: {
        var ed = _ed()
        return editing && !!ed && ((ed.selectedIds || []).length > 0 || ed.selectedId !== "")
    }
    readonly property bool propsShown: propsOn && propsHasSelection
    function toggleProps() {
        if (!_layersSide.open) {
            // Properties lives in the right panel: bring it out with it.
            propsOn = true
            _layersSide.unfold()
            return
        }
        propsOn = !propsOn
    }

    // Edit > Cut (07 S135): Copy then Delete; Copy is no undo step, so the
    // Delete is the one step.
    // Through rig_commands.js (07 S137: Repeat sees it; one Undo step).
    function cutNow() {
        runEdit("edit.cut")
    }

    // Edit > Cut / Copy / Paste / Duplicate / Delete / Select All and their
    // keys (07 S136 S137): through rig_commands.js, as the right-click rows,
    // so Repeat sees menus and keys. The Chips pool and the selection follow
    // from the editor's nodesChanged / historyChanged (deferHistory), for
    // every way in (menus, keys, right-click).
    function runEdit(id) {
        var e = _ed()
        if (!editing || !e)
            return
        if (id === "edit.delete") {
            deleteOrBreak()
            return
        }
        if (RigCommands.enabled(e, id))
            RigCommands.run(e, id)
    }

    // --- favourites (07 S136) -------------------------------------------------
    // Command ids kept by Device Map Options (a program setting); the star on
    // a menu-bar row adds or removes one, the right-click menu shows them.
    readonly property bool favouritesReady: typeof _opts.toggleFavourite === "function"
    readonly property var favouriteIds: (favouritesReady && _opts.favourites) ? _opts.favourites : []
    function isFavourite(id) {
        var list = favouriteIds || []
        for (var i = 0; i < list.length; i++) {
            if (list[i] === id)
                return true
        }
        return false
    }
    function toggleFavourite(id) {
        if (favouritesReady && id)
            _opts.toggleFavourite(id)
    }
    function removeFavourite(id) {
        if (typeof _opts.removeFavourite === "function" && id)
            _opts.removeFavourite(id)
    }
    // The store's list and count to the editor (its right-click menu).
    function applyFavouritesToEditor() {
        var e = _ed()
        if (!e || !favouritesReady)
            return
        var ids = []
        var list = _opts.favourites || []
        for (var i = 0; i < list.length; i++)
            ids.push(String(list[i]))
        if (e.favourites !== undefined)
            e.favourites = ids
        if (e.favouritesShown !== undefined && _opts.favouritesShown !== undefined)
            e.favouritesShown = Number(_opts.favouritesShown)
    }
    Connections {
        target: _opts
        ignoreUnknownSignals: true
        function onFavouritesChanged() { _editorWin.applyFavouritesToEditor() }
        function onFavouritesShownChanged() { _editorWin.applyFavouritesToEditor() }
    }
    // A star at the end of a menu-bar row (07 S136), shown on hover.
    function addStar(row, id) {
        if (!row || !id)
            return
        // Room for the star after the key (kept as a binding, as the scale can change).
        row.rightPadding = Qt.binding(function() { return Style.dp(30) })
        _starComp.createObject(row, { cmdId: id, row: row })
    }
    Component {
        id: _starComp
        Text {
            id: _star
            property string cmdId: ""
            property var row: null
            readonly property bool on: _editorWin.isFavourite(cmdId)
            objectName: "dmeStar_" + cmdId
            visible: _editorWin.favouritesReady && !!row
                && (_rowHover.hovered || row.highlighted || _starArea.containsMouse)
            anchors.right: parent ? parent.right : undefined
            anchors.rightMargin: Style.dp(8)
            anchors.verticalCenter: parent ? parent.verticalCenter : undefined
            text: on ? "★" : "☆"
            color: on ? Style.menuAccent : Style.menuHint
            font.pixelSize: Style.menuTextPx
            // Toggles the favourite; the row itself does not run.
            function toggle() { _editorWin.toggleFavourite(cmdId) }
            // The row's hover (its own follows the platform's hover setting).
            HoverHandler {
                id: _rowHover
                parent: _star.row
            }
            MouseArea {
                id: _starArea
                anchors.fill: parent
                anchors.margins: -Style.dp(4)
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: _star.toggle()
            }
        }
    }

    // Right-click > Show in Layers (07 S136): Layers unfolds (unpinned, it
    // slides over) and its row is scrolled to and lit.
    function showInLayers(id) {
        if (!id)
            return
        _layersSide.unfold()
        _layersPanel.revealNode(id)
        // Again once a just-opened panel is laid out.
        Qt.callLater(function() { _layersPanel.revealNode(id) })
    }
    // Right-click > Properties... (07 S136): as View > Properties (F4) when
    // it is off: Layers unfolds with Properties shown.
    function showProperties() {
        propsOn = true
        _layersSide.unfold()
    }

    // Background mode folds Chips and brings it back after (S130).
    function bgFoldChips(on) {
        if (on) {
            if (_chipsSide.open) {
                chipsBgFolded = true
                _chipsSide.open = false
            }
        } else if (chipsBgFolded) {
            chipsBgFolded = false
            _chipsSide.open = true
        }
    }
    onBgModeChanged: bgFoldChips(bgMode)

    // The window's width, a panel's pin or width changed: with too little
    // room for the map, Chips then Layers unpin and fold; with room again
    // they come back, Layers first (S131).
    function fitSides() {
        if (!editing)
            return
        var room = _mapRow.width - 2 * Style.dp(10)
        var strip = _chipsSide.stripWidth
        function tooNarrow() {
            return room - _chipsSide.takenWidth - _layersSide.takenWidth < mapMinWidth
        }
        if (tooNarrow() && !chipsSqueezed && !chipsBgFolded && _chipsSide.pinned && _chipsSide.open) {
            chipsSqueezed = true
            _chipsSide.pinned = false
            _chipsSide.open = false
        }
        if (tooNarrow() && !layersSqueezed && _layersSide.pinned && _layersSide.open) {
            layersSqueezed = true
            _layersSide.pinned = false
            _layersSide.open = false
        }
        if (layersSqueezed && !_layersSide.open
                && room - _chipsSide.takenWidth - _layersSide.shownWidth >= mapMinWidth) {
            layersSqueezed = false
            _layersSide.pinned = true
            _layersSide.open = true
        }
        if (chipsSqueezed && !layersSqueezed && !_chipsSide.open && !bgMode
                && room - _chipsSide.shownWidth - _layersSide.takenWidth >= mapMinWidth) {
            chipsSqueezed = false
            _chipsSide.pinned = true
            _chipsSide.open = true
        }
    }

    // --- background and foreground planes (07 S111-S127) ------------------

    // Background mode: the editor is editing the background (07 S113).
    readonly property bool bgMode: {
        var e = _ed()
        return editing && !!e && e.editPlane === "background"
    }
    // The first-time line in the banner, shown this time only (07 S114).
    property bool bgHintNow: false
    // The Background row's eye (07 S120): a program setting.
    readonly property bool bgHidden: _opts.values["bm-bg-hidden"] === true

    // Enters or leaves Background mode (the menus, Ctrl+B, Done, Esc). Layers' Background row sets the editor's editPlane itself; the
    // window follows that too (planeChanged).
    function setEditPlane(plane) {
        var e = _ed()
        if (!e)
            return
        var next = (plane === "background" && editing) ? "background" : "foreground"
        if (e.editPlane !== next)
            e.editPlane = next
    }

    // The menus Help's Show me › points at, by objectName: their title in
    // the menu bar is pulsed. Insert, Arrange and Leader work only while
    // editing.
    readonly property var _helpMenus: ({
        dmeMenuFile: _fileMenu, dmeMenuEdit: _editMenu, dmeMenuView: _viewMenu,
        dmeMenuInsert: _insertMenu, dmeMenuArrange: _arrangeMenu,
        dmeMenuLeader: _leaderMenu, dmeMenuFormat: _formatMenu, dmeMenuHelp: _helpMenu
    })
    readonly property var _helpEditOnlyMenus: ["dmeMenuInsert", "dmeMenuArrange", "dmeMenuLeader"]

    // A menu's title in the menu bar.
    function menuBarItem(name) {
        var menu = _helpMenus[name]
        for (var i = 0; menu && i < _menuBar.count; ++i)
            if (_menuBar.menuAt(i) === menu)
                return _menuBar.itemAt(i)
        return null
    }

    // The view-only banner's "File › Device" link (D-TESTLIST-1 item 4):
    // the File menu opens from the menu bar with its Device list out.
    function openDeviceMenu() {
        var bar = menuBarItem("dmeMenuFile")
        if (!bar)
            return false
        if (!_fileMenu.opened)
            bar.triggered()
        for (var i = 0; i < _fileMenu.count; i++) {
            var it = _fileMenu.itemAt(i)
            if (it && it.subMenu === _deviceMenu) {
                if (!_deviceMenu.opened)
                    it.triggered()
                return true
            }
        }
        return false
    }

    // Help's Show me › into this window (07 S126, D-07-PLANES-FOLLOWUP
    // Q1a): brings the window forward (on the first device when none is
    // shown), shows the place named and hands it to pulse: a menu's title
    // in the bar (dmeMenu…), the Chips or Layers side panel brought out
    // (chipsSide, layersSide), Properties under Layers (propsPanel), the
    // banner in Background mode (dmeBgBanner) or the Background row in
    // Layers in Foreground mode (dmeBgRow).
    // Returns "" or why not, which the message line says too.
    function revealForHelp(name, pulse) {
        var menu = _helpMenus.hasOwnProperty(name)
        if (!menu && ["chipsSide", "layersSide", "propsPanel", "dmeBgBanner", "dmeBgRow"].indexOf(name) < 0)
            return "No such place in the Device Mapping Editor: " + name
        show()
        raise()
        requestActivate()
        if (!targetName.length && _inputDeviceItems.count > 0) {
            var first = _inputDeviceItems.objectAt(0)
            openForDevice(first.name, first.guid)
        }
        var why = ""
        var needsEdit = !menu || _helpEditOnlyMenus.indexOf(name) >= 0
        if (needsEdit && !targetName.length)
            why = "Choose a device from the File menu first"
        else if (needsEdit && (!editing || !_ed()))
            why = "Edit the map to see this"
        else if (name === "propsPanel" && !propsHasSelection)
            why = "Select an item to see Properties"
        if (why !== "") {
            say(why)
            return why
        }
        var item = null
        if (menu) {
            item = menuBarItem(name)
        } else if (name === "chipsSide") {
            // Chips folds by itself in Background mode (07 S130).
            setEditPlane("foreground")
            _chipsSide.unfold()
            item = _chipsSide
        } else if (name === "layersSide") {
            _layersSide.unfold()
            item = _layersSide
        } else if (name === "propsPanel") {
            propsOn = true
            _layersSide.unfold()
            item = _propsPanel
        } else if (name === "dmeBgBanner") {
            setEditPlane("background")
            item = _bgBanner
        } else if (name === "dmeBgRow") {
            setEditPlane("foreground")
            _layersSide.unfold()
            item = _layersPanel.bgRowPart("dmeBgRow")
        }
        if (!item || !item.visible)
            return "Can't show this now"
        if (typeof pulse === "function")
            pulse(item)
        return ""
    }

    function escLeavesBackground() {
        resTick
        var e = _ed()
        if (!e)
            return false
        return !(e.drawTool && e.drawTool.length) && !e.printAreaArm && !e.renameId
               && !e.selectedId && !(e.selectedIds && e.selectedIds.length)
    }

    // Ctrl+Shift+B (07 S121): the selection to the other plane; the
    // editor says "Moved to …" with Undo (planeMoved).
    function moveSelectionToOtherPlane() {
        var e = _ed()
        if (!editing || !e)
            return
        var ids = (e.selectedIds && e.selectedIds.length) ? e.selectedIds.slice()
                  : (e.selectedId ? [e.selectedId] : [])
        if (!ids.length)
            return
        var first = e.nodeAt(ids[0])
        var inBg = first ? first.plane === "background" : bgMode
        // Through rig_commands.js when it applies (07 S137: Repeat sees it).
        var cmd = inBg ? "moveToForeground" : "moveToBackground"
        if (RigCommands.enabled(e, cmd))
            RigCommands.run(e, cmd)
        else
            e.moveToPlane(ids, inBg ? "foreground" : "background")
    }

    // A text field or a name being typed has the keys.
    function typingNow() {
        var e = _ed()
        if (e && e.renameId)
            return true
        var f = _editorWin.activeFocusItem
        return !!f && f.cursorPosition !== undefined && f.readOnly !== true
    }

    function toggleEditPlane() {
        setEditPlane(bgMode ? "foreground" : "background")
    }

    // The editor's plane changed, from here or from Layers.
    function planeChanged() {
        var e = _ed()
        if (!e)
            return
        if (e.editPlane !== "background") {
            bgHintNow = false
            return
        }
        if (!editing) {
            e.editPlane = "foreground"
            return
        }
        // Once for the whole program, never per device (07 S114).
        if (_opts.values["bm-bg-hint-seen"] !== true) {
            bgHintNow = true
            _opts.set("bm-bg-hint-seen", true)
        }
    }

    // The plane view settings (07 S115, S120): program settings, the same
    // for every map, never in the map file.
    function applyPlaneViewToEditor() {
        var e = _ed()
        if (!e)
            return
        var o = _opts.values
        e.showFgFaint = o["bm-fg-faint"] !== false
        e.bgViewHidden = o["bm-bg-hidden"] === true
        // A slider value not kept yet wins over the stored one.
        if (_planeViewTimer.running)
            return
        var op = Number(o["bm-bg-opacity"])
        e.bgViewOpacity = (op === op && op >= 0 && op <= 1) ? op : 1
    }

    // The editor's view settings changed (the Background row's eye and
    // Opacity slider, the banner's tick): kept as program settings. The
    // slider is kept once it rests.
    function keepPlaneView(key) {
        var e = _ed()
        if (!e)
            return
        if (key === "bm-bg-opacity") {
            _planeViewTimer.restart()
            return
        }
        var v = key === "bm-fg-faint" ? e.showFgFaint : e.bgViewHidden
        if (_opts.values[key] !== v)
            _opts.set(key, v)
    }

    Timer {
        id: _planeViewTimer
        interval: 300
        onTriggered: {
            var e = _editorWin._ed()
            if (e && Number(_opts.values["bm-bg-opacity"]) !== Number(e.bgViewOpacity))
                _opts.set("bm-bg-opacity", Number(e.bgViewOpacity))
        }
    }

    // Move to Background / Foreground (07 S121): the message line says so,
    // with Undo.
    function notePlaneMoved(plane, count) {
        if (!(count > 0))
            return
        _messageLine.show("Moved to " + (plane === "background" ? "Background" : "Foreground"),
                          false, "Undo", function() { var e = _ed(); if (e) e.undo() })
    }

    Connections {
        target: _cardLoader.item ? _cardLoader.item.editorItem : null
        ignoreUnknownSignals: true
        function onPlaneMoved(plane, count) { _editorWin.notePlaneMoved(plane, count) }
    }

    // Background > Add Picture to Background… (07 S40): the top background
    // layer, fitted to the photo frame; the file waits in the edit's
    // temporary folder until Save. One Undo step.
    function addBackgroundPicture(fileUrl) {
        var e = _ed()
        if (!editing || !e || !targetName.length)
            return ""
        _hw.notePictureFolder(fileUrl)
        var rel = _hw.copyOverlay(fileUrl, targetName)
        if (!rel.length) {
            say("The picture could not be added to the background.", true)
            return ""
        }
        var id = e.addOverlay(rel, _hw.imageUrl(rel),
                              { plane: "background", fitFrame: true, aspect: _hw.imageAspect(rel) })
        say("Added to the background. Undo takes it away.")
        return id
    }

    // Background > Clear Background (07 S41): every background layer goes
    // as one Undo step, without asking; Save removes unused picture files.
    function clearBackground() {
        var e = _ed()
        if (!editing || !e)
            return
        e.clearPlane("background")
        say("Background cleared. Undo puts it back.")
    }

    // Eyedropper: the next click anywhere in the window takes the colour
    // under it for the picker's field; Esc gives up.
    property string eyedropField: ""

    function startEyedropper(field) {
        eyedropField = field
        _colorPop.close()
        _eyedrop.forceActiveFocus()
    }

    function takeEyedrop(wx, wy) {
        var field = eyedropField
        eyedropField = ""
        var hex = _hw.colorAt(_editorWin, wx, wy)
        if (!hex.length)
            return
        var e = _ed()
        if (e)
            e.applyField(field, hex)
        _hw.noteColour(hex)
        _colorPop.openField(field, hex, null)
    }

    // The clipboard's picture as a new picture layer (Edit > Paste picture,
    // Ctrl+Shift+V, or the canvas menu).
    function pastePicture() {
        var e = _ed()
        if (!editing || !e)
            return
        addPictures(_hw.pasteClipboardPictures(targetName), undefined)
    }

    // New picture layers, each sized to its picture; a drop point centres
    // them there (several step down and right). One undo step for all.
    function addPictures(rels, at) {
        var e = _ed()
        if (!e || !rels || !rels.length) {
            say("Nothing to add: no picture found.", true)
            return
        }
        var ids = []
        for (var i = 0; i < rels.length; i++) {
            var opts = { aspect: _hw.imageAspect(rels[i]), noBump: true }
            if (at) {
                opts.fx = at.fx + i * 0.03
                opts.fy = at.fy + i * 0.03
            }
            ids.push(e.addOverlay(rels[i], _hw.imageUrl(rels[i]), opts))
        }
        e.setSelection(ids)
        e.bump()
    }

    // Picture files dropped on the map (from Explorer or another program).
    function dropPictures(urls, x, y, from) {
        var e = _ed()
        if (!e)
            return false
        if (!editing) {
            e.showFindMessage("Click Edit Mapping first, then drop the picture again.")
            return false
        }
        var p = e.mapFromItem(from, x, y)
        var rels = _hw.importPictureFiles(urls, targetName)
        addPictures(rels, { fx: e.xToFx(p.x), fy: e.yToFy(p.y) })
        return rels.length > 0
    }

    function applyViewToFace() {
        if (!faceLive)
            return
        var f = _cardLoader.item
        if (!f || !f.zoomFit)
            return
        var z = (viewPctSave || 1) * f.zoomFit
        f.zoom = Math.max(f.zoomMin, Math.min(f.zoomMax, z))
        f.panX = viewPanX
        f.panY = viewPanY
        if (f.clampPan)
            f.clampPan()
    }

    function uiBag() {
        captureView()
        return {
            gridOn: gridOn,
            snapOn: snapOn,
            snapEntOn: snapEntOn,
            gridSize: gridSize,
            viewPct: viewPctSave,
            panX: viewPanX,
            panY: viewPanY,
            guidesX: guidesX,
            guidesY: guidesY,
            guidesOn: guidesOn,
            printArea: printArea,
            print: printSetup
        }
    }

    function applyUi(ui) {
        if (!ui)
            return
        if (ui.gridOn === true || ui.gridOn === false)
            gridOn = ui.gridOn
        if (ui.snapOn === true || ui.snapOn === false)
            snapOn = ui.snapOn
        if (ui.snapEntOn === true || ui.snapEntOn === false)
            snapEntOn = ui.snapEntOn
        if (ui.gridSize >= 1)
            gridSize = ui.gridSize
        if (ui.viewPct > 0)
            viewPctSave = ui.viewPct
        if (ui.panX === ui.panX)
            viewPanX = ui.panX
        if (ui.panY === ui.panY)
            viewPanY = ui.panY
        guidesX = Array.isArray(ui.guidesX) ? ui.guidesX : []
        guidesY = Array.isArray(ui.guidesY) ? ui.guidesY : []
        if (ui.guidesOn === true || ui.guidesOn === false)
            guidesOn = ui.guidesOn
        var a = ui.printArea
        printArea = (a && a.fw > 0 && a.fh > 0) ? { fx: +a.fx, fy: +a.fy, fw: +a.fw, fh: +a.fh } : null
        var p = ui.print || {}
        printSetup = {
            paper: (p.paper === "fit" || paperInches[p.paper]) ? p.paper : "fit",
            landscape: p.landscape === true,
            margin: marginInches[p.margin] !== undefined ? p.margin : "quarter",
            scale: (p.scale >= 10 && p.scale <= 800) ? Math.round(p.scale) : 100,
            light: p.light === true,
            // Include background (07 S123): on unless turned off.
            includeBg: p.includeBg !== false
        }
    }

    // The device's ruler guides (saved with the view) and whether they show.
    // The print area ({fx, fy, fw, fh} of the page, or null: the whole
    // page): every export and print takes it. Saved with the map.
    property var printArea: null
    // Print & Export, saved with the map: the paper ("fit": the print
    // area's own shape), its orientation, the margins, the scale (100% =
    // the bottom background picture's own pixels; with none, the page 1920
    // px wide), the Page (light: white, every color's lightness turned
    // over) and Include background, the same for every print and export.
    property var printSetup: ({ paper: "fit", landscape: false, margin: "quarter", scale: 100, light: false, includeBg: true })
    readonly property var paperInches: ({
        letter: [8.5, 11], legal: [8.5, 14], tabloid: [11, 17],
        a3: [11.69, 16.54], a4: [8.27, 11.69], a5: [5.83, 8.27]
    })
    readonly property var marginInches: ({ none: 0, quarter: 0.25, half: 0.5 })

    // The print area's shape on the chosen paper (width / height inside the
    // margins), or 0 for "fit" (any shape).
    function printAspect() {
        var p = paperInches[printSetup.paper]
        if (!p)
            return 0
        var m = 2 * (marginInches[printSetup.margin] || 0)
        var w = (printSetup.landscape ? p[1] : p[0]) - m
        var h = (printSetup.landscape ? p[0] : p[1]) - m
        return h > 0 ? w / h : 0
    }

    // A Print & Export setting changed: kept with the map; a new paper or
    // orientation reshapes the print area round its middle.
    function setPrint(key, value) {
        var next = {}
        for (var k in printSetup)
            next[k] = printSetup[k]
        next[key] = value
        printSetup = next
        var e = _ed()
        if (e) {
            e.printAspect = printAspect()
            if (key === "paper" || key === "landscape" || key === "margin")
                e.reshapePrintArea()
        }
        persistUi()
    }

    // Export pixels for each editor pixel on screen: the scale over the
    // bottom background picture's own pixels (none: the page 1920 px wide,
    // 07 S83); the renderer works it out. The same export at any window size.
    function exportFactor() {
        var e = _ed()
        if (!e)
            return 1
        return _renderer.exportFactor(e, printSetup.scale)
    }

    // The export's size in pixels: the print area at the scale, no side
    // over 16384.
    function exportPixels() {
        var e = _ed()
        if (!e)
            return { w: 0, h: 0 }
        var r = e.printAreaRect()
        var f = exportFactor()
        f = Math.min(f, 16384 / Math.max(1, r.w, r.h))
        return { w: Math.max(1, Math.round(r.w * f)), h: Math.max(1, Math.round(r.h * f)) }
    }
    property var guidesX: []
    property var guidesY: []
    property bool guidesOn: true

    function guidesFromEditor() {
        var e = _ed()
        if (!e)
            return
        guidesX = e.rulerGuidesX.slice()
        guidesY = e.rulerGuidesY.slice()
        persistUi()
        noteEditStep()
    }

    // A print area or guide change in Edit is an undo step (07 Q3); Undo
    // itself adds none (the editor is restoring then).
    function noteEditStep() {
        var e = _ed()
        if (editing && e && e.pushHist)
            e.pushHist()
    }

    // Editor settings from Options (Edit → Device Map Options…).
    function applyOptionsToEditor() {
        var e = _cardLoader.item ? _cardLoader.item.editorItem : null
        if (!e)
            return
        var o = _opts.values
        if (o["undo-steps"] > 0)
            e.histCap = o["undo-steps"]
        var ink = String(o["print-area-color"] || "")
        e.printAreaColor = /^#[0-9A-Fa-f]{6}$/.test(ink) ? ink : String(Style.dangerBright)
        if (o["rotate-snap"] > 0)
            e.rotateSnap = o["rotate-snap"]
        e.savedStyles = _opts.styles
        e.poolHit = function(wx, wy) {
            if (!_poolFloat.visible)
                return false
            var p = _poolFloat.mapFromItem(null, wx, wy)
            return p.x >= 0 && p.y >= 0 && p.x <= _poolFloat.width && p.y <= _poolFloat.height
        }
        var f = e.face
        if (f && o["zoom-speed"] > 0)
            f.zoomSpeed = o["zoom-speed"]
        if (f)
            f.rulersOn = o["rulers"] === true
        e.findOn = o["press-to-find"] !== false
        e.findAxes = o["find-axes"] === true
        applyPlaneViewToEditor()
        applyFavouritesToEditor()
        giveLookMaker(e)
        refreshActionLabels()
    }

    // --- action labels (Device Map Options → Labels) ------------------------

    // The mode whose actions the chips show; "" follows the program: the
    // running mode while the profile runs, else the mode shown in the main
    // window.
    property string labelMode: ""
    // Set at start and by onProfileLabelsChanged (no binding to overwrite).
    property var profileModes: []
    readonly property string labelModeNow: {
        if (labelMode.length)
            return labelMode
        if (typeof backend !== "undefined" && backend && backend.gremlinActive)
            return backend.currentMode
        return (typeof uiState !== "undefined" && uiState) ? uiState.currentMode : ""
    }
    onLabelModeNowChanged: refreshActionLabels()

    Connections {
        target: _hw
        function onProfileLabelsChanged() {
            _editorWin.profileModes = _hw.profileModes()
            if (_editorWin.labelMode.length && _editorWin.profileModes.indexOf(_editorWin.labelMode) < 0)
                _editorWin.labelMode = ""
            _editorWin.refreshActionLabels()
        }
    }

    // The chosen mode follows a rename (it went back to following the
    // program); a deleted one goes back to following the program.
    Connections {
        target: typeof signal !== "undefined" ? signal : null
        function onModeRenamed(oldName, newName) {
            if (_editorWin.labelMode === oldName)
                _editorWin.labelMode = newName
        }
        function onModeDeleted(name) {
            if (_editorWin.labelMode === name)
                _editorWin.labelMode = ""
        }
    }

    function labelsFor(mode) {
        var o = _opts.values
        return _hw.actionLabels(targetGuid, mode, o["description-first"] !== false, o["several-actions"] === "All")
    }

    function refreshActionLabels() {
        var e = _ed()
        if (!e)
            return
        var o = _opts.values
        e.chipTextMode = String(o["chip-text"] || "Name")
        e.unboundText = String(o["unbound"] || "Name")
        e.actionLabels = (e.chipTextMode === "Name" || !targetGuid.length) ? ({}) : labelsFor(labelModeNow)
        e.bump()
    }

    function zoomToPage() {
        var e = _ed()
        var f = e ? e.face : null
        if (!f || !f.zoomToPage)
            return
        f.zoomToPage()
        captureView()
        persistUi()
    }

    function zoomToSelection() {
        var e = _ed()
        if (e && e.zoomToSelection()) {
            captureView()
            persistUi()
        }
    }

    function applyGridToEditor() {
        if (!faceLive)
            return
        var e = _cardLoader.item ? _cardLoader.item.editorItem : null
        if (!e)
            return
        e.gridOn = gridOn
        e.snapOn = snapOn
        e.snapEntOn = snapEntOn
        e.gridSize = gridSize
        e.rulerGuidesX = guidesX.slice()
        e.rulerGuidesY = guidesY.slice()
        e.guidesOn = guidesOn
        e.printArea = printArea
        e.printAspect = printAspect()
        applyOptionsToEditor()
        if (e.repaint)
            e.repaint()
        applyViewToFace()
        applyPlaneViewToEditor()
    }

    function deferSelected() {
        Qt.callLater(applySelected)
    }

    function deferReservoir() {
        Qt.callLater(refreshReservoir)
    }

    function deferFace() {
        Qt.callLater(function() {
            applyGridToEditor()
            refreshReservoir()
        })
    }

    function deferHistory() {
        Qt.callLater(function() {
            applySelected()
            refreshReservoir()
            if (editing)
                notePhoto(editorNodesNow())
        })
    }


    // The undo position right after Fit to Photo Frame: undoing back past it
    // makes Fit available again.
    property int fitHistAt: -1

    function fitToPhotoFrame() {
        if (fittedThisEdit)
            return
        var e = _ed()
        sceneShiftList(editing ? workNodes : liveNodes)
        fittedThisEdit = true
        // An undo step for the moved nodes (bump repaints too).
        if (editing && e && e.bump) {
            e.bump()
            fitHistAt = e.histAt
            say("Fitted to the photo frame. Undo puts it back.")
        } else if (e && e.repaint) {
            e.repaint()
        }
    }

    function noteHistoryForFit() {
        var e = _ed()
        if (fittedThisEdit && fitHistAt >= 0 && e && e.histAt < fitHistAt) {
            fittedThisEdit = false
            fitHistAt = -1
        }
    }

    // The parts of the ui block that belong to an edit (07 Q1): written by
    // Save, taken back by Cancel. The rest (view, zoom, grid, guides shown)
    // is kept at once.
    readonly property var editUiKeys: ["printArea", "print", "guidesX", "guidesY"]
    // The edit parts as the edit started (or was last saved).
    property var _editUi: null

    function editUiNow() {
        return {
            printArea: printArea,
            print: printSetup,
            guidesX: guidesX.slice(),
            guidesY: guidesY.slice()
        }
    }

    function noteEditUiBase() {
        _editUi = JSON.parse(JSON.stringify(editUiNow()))
    }

    // Cancel: the print area, print setup and guides go back to how the
    // edit found them.
    function restoreEditUi() {
        if (!_editUi)
            return
        var b = _editUi
        _editUi = null
        printArea = b.printArea ? { fx: +b.printArea.fx, fy: +b.printArea.fy,
                                    fw: +b.printArea.fw, fh: +b.printArea.fh } : null
        printSetup = b.print
        guidesX = (b.guidesX || []).slice()
        guidesY = (b.guidesY || []).slice()
        applyGridToEditor()
    }

    function editUiChanged() {
        return editing && _editUi !== null
            && JSON.stringify(editUiNow()) !== JSON.stringify(_editUi)
    }

    function persistUi() {
        // No device: nothing to keep them in (they used to go to a built-in
        // default device's file).
        if (!targetName.length)
            return
        var text = _hw.load(targetName)
        var doc = parseDoc(text)
        // No module file: zoom, grid, guides and the print area don't make
        // one (it showed up as an empty input module, or, in Edit, a file
        // with the old map). They wait here; Save writes them (07 S29, S96).
        if (!doc)
            return
        var ui = uiBag()
        if (editing) {
            // In Edit the print area, print setup and guides wait for Save.
            var kept = doc.ui || {}
            for (var i = 0; i < editUiKeys.length; i++) {
                var key = editUiKeys[i]
                if (kept[key] === undefined)
                    delete ui[key]
                else
                    ui[key] = kept[key]
            }
        }
        _hw.saveUi(targetName, JSON.stringify({ ui: ui }))
    }

    function setGridPref(key, val) {
        if (key === "gridOn") gridOn = val
        else if (key === "snapOn") snapOn = val
        else if (key === "snapEntOn") snapEntOn = val
        else if (key === "gridSize") gridSize = val
        applyGridToEditor()
        persistUi()
    }

    // Ctrl+F and View > Search layers… (07 S102): to the Layers search box,
    // opening Layers first. Later, so a just-opened pane is shown.
    function searchLayers() {
        if (!editing)
            return
        _layersSide.unfold()
        Qt.callLater(function() { _layersPanel.focusSearch() })
    }

    function openChipMenu(x, y) {
        applySelected()
    }

    // A key works only while nothing is being typed (07 S133).

    // Only while this window has the focus (not while Keyboard Shortcuts
    // or Options does) and nothing is being typed.
    function keyOk(on) {
        return !!on && keysHere && !typingNow()
    }
    // False while Keyboard Shortcuts or Options holds the keyboard. Qt
    // reports one `active` for this window and its transient children, so
    // the child's own focus decides (checked off-screen, 2026-10-11).
    readonly property bool keysHere: !(_shortcutsWin.visible && _shortcutsWin.contentItem.activeFocus)
                                     && !(_optionsWin.visible && _optionsWin.contentItem.activeFocus)
    // Back in the Device Mapping Editor (it holds the keyboard again): an unpinned
    // Keyboard Shortcuts window closes (07 S100; its own focus-out isn't
    // reported while it is a transient child of this window).
    onKeysHereChanged: {
        if (keysHere && _shortcutsWin.visible && !_shortcutsWin.pinned)
            _shortcutsWin.close()
    }

    // Help > Keyboard Shortcuts… and Ctrl+K (07 S100): its own window.
    function openShortcuts() {
        _shortcutsWin.openFor(_editorWin)
    }

    // Edit > Device Map Options… and Ctrl+, (07 S98): its own window.
    function openOptions() {
        _optionsWin.openFor(_editorWin)
    }

    // Insert, Arrange and Format (07 S134): the commands from
    // rig_commands.js, the same code the right-click menus run. cmdRev
    // goes up as a menu opens, so ticks read the selection again.
    property int cmdRev: 0
    function cmdOk(id) {
        var e = _ed()
        return editing && !!e && !!RigCommands.enabled(e, id)
    }
    function runCmd(id) {
        var e = _ed()
        if (editing && e && RigCommands.enabled(e, id))
            RigCommands.run(e, id)
    }

    // The keys as Shortcut sequences: Return is both Enter keys; a key that
    // needs Shift for its sign also comes as the shifted sign.
    function keySequences(key) {
        var k = String(key)
        if (k === "Return" || k === "Enter")
            return ["Return", "Enter"]
        if (k === "Ctrl+Shift+]")
            return [k, "Ctrl+}"]
        if (k === "Ctrl+Shift+[")
            return [k, "Ctrl+{"]
        return [k]
    }

    // A command key from the list may run now: its command can be used,
    // nothing is being typed, and Return is not finishing a path.
    function cmdKeyOk(id, key) {
        if (!keyOk(cmdOk(id)))
            return false
        if (key === "Return" || key === "Enter") {
            var e = _ed()
            if (e && e.drawTool && e.drawTool.length)
                return false
        }
        return true
    }

    // Menu rows made from rig_commands.js: { id, item }.
    property var _cmdRows: []

    // Fills Insert, Arrange and Format from RigCommands.list() once (07
    // S134): a submenu per `sub` at its first item, in list order, ahead
    // of the menu's own rows; and a Shortcut for each key, except hintOnly
    // ones (the window has their Shortcut already).
    function buildCommandMenus() {
        if (_cmdRows.length)
            return
        var menus = { "Insert": _insertMenu, "Arrange": _arrangeMenu, "Leader": _leaderMenu, "Format": _formatMenu }
        var at = { "Insert": 0, "Arrange": 0, "Leader": 0, "Format": 0 }
        var subs = {}
        var rows = []
        // Each menu that holds command rows gets one hover watcher, which
        // shows a greyed row's reason (07 S121).
        var watched = []
        function watch(m) {
            if (watched.indexOf(m) < 0) {
                watched.push(m)
                _cmdWhyComp.createObject(m.contentItem, { list: m.contentItem })
            }
        }
        var entries = RigCommands.list(_ed()) || []
        for (var i = 0; i < entries.length; i++) {
            var c = entries[i]
            var menu = menus[c.menu]
            if (!menu)
                continue
            // A "-" row is a separator between a menu's groups.
            if (c.id === "-") {
                if (c.sub && c.sub.length) {
                    var inSub = subs[c.menu + "/" + c.sub]
                    if (inSub)
                        inSub.addItem(_cmdSepComp.createObject(inSub.contentItem))
                } else {
                    menu.insertItem(at[c.menu]++, _cmdSepComp.createObject(menu.contentItem))
                }
                continue
            }
            var host = menu
            if (c.sub && c.sub.length) {
                var subKey = c.menu + "/" + c.sub
                if (!subs[subKey]) {
                    subs[subKey] = _cmdMenuComp.createObject(menu, { title: c.sub })
                    menu.insertMenu(at[c.menu]++, subs[subKey])
                }
                host = subs[subKey]
            }
            // Made inside the menu's list (a visual item), so Qt doesn't warn
            // "not placed in the graphics scene" before insertItem places it.
            var item = _cmdItemComp.createObject(host.contentItem, { cmdId: c.id, text: c.text, hint: c.key || "" })
            watch(host)
            if (host === menu)
                menu.insertItem(at[c.menu]++, item)
            else
                host.addItem(item)
            rows.push({ id: c.id, item: item })
            if (c.key && c.key.length && !c.hintOnly)
                _cmdKeyComp.createObject(_editorWin, { cmdId: c.id, cmdKey: c.key, sequences: keySequences(c.key) })
        }
        _cmdRows = rows
    }

    // The rows' texts again (the rotate step follows Device Map Options).
    function refreshCommandTexts() {
        cmdRev++
        var entries = RigCommands.list(_ed()) || []
        var byId = {}
        for (var i = 0; i < entries.length; i++)
            byId[entries[i].id] = entries[i]
        for (var j = 0; j < _cmdRows.length; j++) {
            var c = byId[_cmdRows[j].id]
            if (c)
                _cmdRows[j].item.text = c.text
        }
    }

    Component {
        id: _cmdItemComp
        ThemedMenuItem {
            property string cmdId: ""
            enabled: _editorWin.cmdOk(cmdId)
            // Greyed out: why, as its tooltip (07 S121); "" when there is no
            // reason to give.
            readonly property string whyText: {
                _editorWin.cmdRev
                if (enabled || !_editorWin.editing || typeof RigCommands.whyDisabled !== "function")
                    return ""
                var e = _editorWin._ed()
                return e ? String(RigCommands.whyDisabled(e, cmdId) || "") : ""
            }
            // On/off commands (Crop, ID Column) show a tick (07 S134).
            checkable: !!RigCommands.CHECKABLE[cmdId]
            checked: { _editorWin.cmdRev; var e = _editorWin._ed(); return checkable && RigCommands.checked(e, cmdId) }
            onTriggered: _editorWin.runCmd(cmdId)
            Component.onCompleted: _editorWin.addStar(this, cmdId)
        }
    }
    // A disabled row gets no hover of its own, so the menu's list watches
    // the pointer and shows the reason of the greyed row under it.
    Component {
        id: _cmdWhyComp
        Item {
            objectName: "dmeCmdWhy"
            property var list: null
            anchors.fill: parent
            z: 100
            HoverHandler { id: _whyHover }
            // The reason of the greyed row at (x, y) in this item, or "".
            function tipAt(x, y) {
                if (!list)
                    return ""
                var q = mapToItem(list.contentItem, x, y)
                var row = list.itemAt(q.x, q.y)
                return row && !row.enabled && row.whyText ? row.whyText : ""
            }
            readonly property string tipText: _whyHover.hovered
                ? tipAt(_whyHover.point.position.x, _whyHover.point.position.y) : ""
            ToolTip.visible: tipText.length > 0
            ToolTip.text: tipText
        }
    }
    Component {
        id: _cmdMenuComp
        ThemedMenu {
            compact: false
        }
    }
    Component {
        id: _cmdSepComp
        ThemedMenuSeparator {}
    }
    Component {
        id: _cmdKeyComp
        Shortcut {
            property string cmdId: ""
            property string cmdKey: ""
            enabled: _editorWin.cmdKeyOk(cmdId, cmdKey)
            onActivated: _editorWin.runCmd(cmdId)
            onActivatedAmbiguously: _editorWin.runCmd(cmdId)
        }
    }

    // Device Map Options (07 S98) and Keyboard Shortcuts (S100): small
    // windows of their own.
    DeviceMapOptionsWindow {
        id: _optionsWin
        opts: _opts
        onColorRequested: (key, hex) => _editorWin.openColorField("printAreaColor", hex, null)
    }
    ShortcutsWindow {
        id: _shortcutsWin
        menuBar: _menuBar
        // Its pin is kept with the panels (07 S100).
        Component.onCompleted: pinned = !!_opts.sidePanelState("shortcuts").pinned
        onPinnedChanged: _opts.setSidePanelState("shortcuts", { pinned: pinned })
        // The keys no menu shows (S134).
        keyRows: [
            { group: "Keys", text: "Nudge", keys: "Arrows" },
            { group: "Keys", text: "Nudge 10 px", keys: "Shift+Arrows" },
            { group: "Keys", text: "Finish a path", keys: "Enter" },
            { group: "Keys", text: "Undo a path point", keys: "Backspace" },
            { group: "Keys", text: "Finish a crop", keys: "Enter" },
            { group: "Keys", text: "Cancel / leave (during a drag: put it back)", keys: "Esc" }
        ]
        mouseRows: [
            { group: "Mouse", text: "Set print area", keys: "Alt+drag on empty space" },
            { group: "Mouse", text: "Copy", keys: "Alt+drag an item" },
            { group: "Mouse", text: "Keep a move on a line", keys: "Shift while dragging" },
            { group: "Mouse", text: "Skip snapping", keys: "Ctrl while dragging" },
            { group: "Mouse", text: "Free proportions", keys: "Shift+drag a corner" },
            { group: "Mouse", text: "Resize from the center", keys: "Alt+drag a handle" },
            { group: "Mouse", text: "Skew", keys: "Ctrl+Shift+drag a side handle" },
            { group: "Mouse", text: "Turn in steps", keys: "Shift+drag the round handle" },
            { group: "Mouse", text: "Lines at 45° steps", keys: "Shift while drawing" },
            { group: "Mouse", text: "Draw from the center", keys: "Alt while drawing" },
            { group: "Mouse", text: "Pan", keys: "Space+drag" },
            { group: "Mouse", text: "Pan", keys: "Middle-drag" },
            { group: "Mouse", text: "Zoom", keys: "Wheel" },
            { group: "Mouse", text: "Edit Background", keys: "Double-click the Background row" }
        ]
    }

    // View > Zoom In / Zoom Out (07 S133): a step about the view's middle.
    function zoomStep(factor) {
        var e = _ed()
        var f = e ? e.face : null
        if (!f || !f.zoomAt)
            return
        f.zoomAt(NaN, NaN, factor)
        captureView()
        persistUi()
    }

    // Edit > Select All (07 S133): every item on the edited plane that a
    // band drag could take (not hidden, not locked).
    function selectAllNow() {
        var e = _ed()
        if (!editing || !e)
            return
        if (typeof e.selectAll === "function") {
            e.selectAll()
            return
        }
        var ids = []
        var list = e.nodes || []
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (!n || e.isHidden(n) || e.isLocked(n) || !e.inEditPlane(n))
                continue
            if (ids.indexOf(n.id) < 0)
                ids.push(n.id)
            if (n.packId && ids.indexOf(n.packId) < 0)
                ids.push(n.packId)
        }
        e.setSelection(ids)
    }

    // File > History: this map's saved versions (Tools > History).
    function openHistory() {
        if (!targetName.length)
            return
        // By this device's id, every area (twin sticks apart; a save that
        // also changed claims shows too), as Module Setup does (08 Q15);
        // entries from before device folders by its name (08 S43).
        Helpers.createComponent("DialogHistory.qml", {
            filter: JSON.stringify({
                deviceId: _fileWatch.deviceIdFor(targetName, targetGuid),
                deviceName: targetName
            }),
            filterLabel: targetName
        })
    }

    function setGuidesShown(on) {
        guidesOn = on
        var e = _ed()
        if (e)
            e.guidesOn = on
        persistUi()
    }

    // Choosers open in the last folder used for their kind (01 S143).
    FilePicker {
        id: _bgPictureDialog
        kind: "picture"
        title: "Choose Background Picture"
        nameFilters: ["Images (*.jpg *.jpeg *.png *.webp *.bmp)"]
        folder: _hw.imagesFolderUrl()
        onPicked: (selectedFile) => _editorWin.addBackgroundPicture(selectedFile)
    }

    FilePicker {
        id: _overlayDialog
        kind: "picture"
        title: "Import Picture"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.bmp)"]
        folder: _hw.imagesFolderUrl()
        onPicked: (selectedFile) => {
            _hw.notePictureFolder(selectedFile)
            var rel = _hw.copyOverlay(selectedFile, targetName)
            var e = _ed()
            // The picture's own proportions, so its box is the picture (07 S140).
            if (rel.length && e)
                e.addOverlay(rel, _hw.imageUrl(rel), { aspect: _hw.imageAspect(rel) })
        }
    }

    // Choose Picture… on a picture whose file is missing (07 S108): the new
    // file waits in the edit like any added picture; the item keeps its
    // place (one Undo step).
    FilePicker {
        id: _choosePictureDialog
        property string nodeId: ""
        function pick(id) {
            nodeId = String(id || "")
            open()
        }
        kind: "picture"
        title: "Choose Picture"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.bmp)"]
        folder: _hw.imagesFolderUrl()
        onPicked: (selectedFile) => {
            _hw.notePictureFolder(selectedFile)
            var e = _ed()
            var n = e ? e.nodeAt(nodeId) : null
            if (!n)
                return
            var rel = _hw.choosePictureFor(String(n.src || ""), selectedFile)
            if (rel.length)
                e.repointPicture(nodeId, rel, _hw.imageUrl(rel), _hw.imageAspect(rel))
        }
    }

    // --- Print & Export: every picture comes from RigRenderer ---------------

    // A hidden copy of the map draws each print, export and preview at its
    // own size; the map on screen is never touched.
    // 100 % comes from the background picture with the most detail; the
    // pictures' own sizes are read from their files (07 S83).
    RigRenderer {
        id: _renderer
        sizeOf: function(u) { return _hw.pictureSize(u) }
    }

    // A job for the renderer: the map as it is now (the whole page with
    // whole), at pixels (the export's size unless given), on Print &
    // Export's background; onPicture(grab result, or null) once drawn.
    function _renderJob(onPicture, pixels, whole) {
        var e = _ed()
        if (!e)
            return null
        return {
            snap: _renderer.snapshot(e, whole === true),
            pixels: pixels || exportPixels(),
            light: printSetup.light === true,
            includeBg: printSetup.includeBg !== false,
            onPicture: onPicture
        }
    }

    function _say(text) {
        say(text, true)
    }

    // An export is being drawn or written (07 S101): one at a time, so
    // Print & Export's Export buttons wait for it.
    property bool _exportDrawing: false
    property string _exportTarget: ""
    readonly property bool exportBusy: _exportDrawing || _hw.exporting === true

    // A PNG, JPG or PDF of the print area, written in the background
    // (07 S101); its result comes with _hw.areaSaved.
    function exportTo(url, format) {
        if (exportBusy)
            return
        var px = exportPixels()
        var setup = JSON.stringify(printSetup)
        var target = String(url)
        var job = _renderJob(function(result) {
            _editorWin._exportDrawing = false
            if (!result) {
                console.warn("Device Mapping Editor export failed: " + target)
                _editorWin._say("Export failed. The map could not be drawn.")
                return
            }
            _editorWin._exportTarget = target
            if (!_hw.saveAreaAsync(result.image, px.w, px.h, target, format, setup))
                console.warn("Device Mapping Editor export not started (one is running): " + target)
        }, px)
        if (!job)
            return
        _exportDrawing = true
        _renderer.enqueue(job)
    }

    Connections {
        target: _hw
        function onAreaSaved(ok, error) {
            if (ok)
                return
            console.warn("Device Mapping Editor export failed: " + _editorWin._exportTarget)
            // Which file and why (07 Q19), as Template export says.
            _editorWin.tellFailure("Export Failed", error || _hw.exportError() || "Export failed.")
        }
    }

    // Print: the print area, then Windows' printer dialog.
    function printNow() {
        var px = exportPixels()
        var setup = JSON.stringify(printSetup)
        var title = targetName.length ? targetName : "Device map"
        var job = _renderJob(function(result) {
            if (result)
                _hw.printImage(result.image, px.w, px.h, title, setup)
        }, px)
        if (job)
            _renderer.enqueue(job)
    }

    // Print & Export's preview, at most maxW x maxH pixels; done(grab
    // result) once drawn. kind "page": the whole page (cut to the print
    // area as it moves); "area": the print area as the export draws it.
    function renderPreview(kind, maxW, maxH, done) {
        var e = _ed()
        if (!e)
            return
        var whole = kind === "page"
        var r = whole ? e.spaceRect() : exportPixels()
        var k = Math.min(maxW / Math.max(1, r.w), maxH / Math.max(1, r.h))
        if (!whole)
            k = Math.min(1, k)
        var size = { w: Math.max(1, Math.round(r.w * k)), h: Math.max(1, Math.round(r.h * k)) }
        var job = _renderJob(done, size, whole)
        if (!job)
            return
        job.preview = kind
        _renderer.enqueue(job)
    }

    // A preview of this kind waiting to be drawn is no longer wanted.
    function dropPreview(kind) {
        _renderer.drop(kind)
    }

    FilePicker {
        id: _exportPngDialog
        kind: "export"
        mode: "save"
        title: "Export PNG"
        defaultSuffix: "png"
        nameFilters: ["PNG image (*.png)"]
        onPicked: (selectedFile) => exportTo(selectedFile, "png")
    }
    FilePicker {
        id: _exportJpgDialog
        kind: "export"
        mode: "save"
        title: "Export JPG"
        defaultSuffix: "jpg"
        nameFilters: ["JPEG image (*.jpg *.jpeg)"]
        onPicked: (selectedFile) => exportTo(selectedFile, "jpg")
    }
    // --- mirror, and copy another device's layout ------------------------------

    property var savedLayouts: []
    property var _copyFrom: null

    function mirrorNow() {
        var e = _ed()
        if (!e || !editing)
            return
        e.mirrorLayout(_opts.values["mirror-pictures"] === true)
        say("Mirrored left to right. Undo puts it back.")
    }

    function openCopyLayout(row) {
        _copyFrom = row
        _copyDlg.open()
    }

    // withBg: Copy the background too (07 S76); without it this device's
    // background stays.
    function copyLayoutFrom(row, mirror, withBg) {
        if (!row)
            return
        // The pictures it uses wait in this device's edit and are copied
        // into its folder on Save (07 S109).
        var text = row.template ? _hw.templateNodes(row.name, targetName)
                                : _hw.layoutNodes(row.slug, targetName)
        if (!text.length)
            return
        var nodes = []
        try { nodes = JSON.parse(text) } catch (e) { return }
        if (!editing) {
            // Edit starts from the current map first, so its undo history
            // holds it before the copy replaces it.
            enterEdit()
            // Unsaved edits from a crash were offered first.
            if (!editing)
                return
            // The copy is a change: compared with the saved map.
            _baseWanted = false
            Qt.callLater(function() { _replaceLayout(nodes, mirror, row, withBg === true) })
            return
        }
        _replaceLayout(nodes, mirror, row, withBg === true)
    }

    // How many chips (group members too) are for controls this device
    // does not have (07 Q8); 0 when its controls aren't known.
    function lackingChips(list) {
        var e = _ed()
        if (!e || !targetGuid.length)
            return 0
        var have = _hw.deviceControls(targetGuid)
        if (!have || !have.known)
            return 0
        var count = 0
        function check(kind, hw) {
            var number = Number(hw)
            if (!(number > 0))
                return
            var ids = have[e.leafKind(kind)] || []
            for (var k = 0; k < ids.length; k++) {
                if (Number(ids[k]) === number)
                    return
            }
            count++
        }
        for (var i = 0; i < (list || []).length; i++) {
            var n = list[i]
            if (!n || e.isDraw(n))
                continue
            var mem = n.members || []
            if (mem.length) {
                for (var m = 0; m < mem.length; m++)
                    check(e.memberKind(n, mem[m]), mem[m].hwId)
            } else if (n.hwId !== undefined) {
                check(n.kind, n.hwId)
            }
        }
        return count
    }

    // What Copy Device Map and Apply Template say after the copy: chips for
    // controls this device lacks (07 Q8).
    function copyNotes(list, row) {
        var text = ""
        var lacking = lackingChips(list)
        if (lacking === 1)
            text += " 1 chip is for a control this device does not have."
        else if (lacking > 1)
            text += " " + lacking + " chips are for controls this device does not have."
        return text
    }

    function _isBg(n) {
        return !!n && n.plane === "background"
    }

    function _replaceLayout(nodes, mirror, row, withBg) {
        var before = _ed()
        if (before && before.flushPendingStep)
            before.flushPendingStep()
        // The undo position before the copy: the copy (and its mirroring)
        // is one step after it (S78).
        var startAt = before ? before.histAt : -1
        // This device's background stays unless it is copied too (07 S76).
        var own = []
        if (!withBg) {
            var cur = (before && before.nodes) ? before.nodes : (workNodes || [])
            own = JSON.parse(JSON.stringify(cur.filter(_isBg)))
            hydrateOverlays(own)
            nodes = nodes.filter(function(n) { return !_isBg(n) })
        }
        hydrateOverlays(nodes)
        // Mirroring turns the copy only: the kept background joins after it.
        var later = mirror && own.length > 0
        workNodes = later ? nodes : own.concat(nodes)
        Qt.callLater(function() {
            var e = _ed()
            if (!e)
                return
            if (mirror)
                e.mirrorLayout(_opts.values["mirror-pictures"] === true)
            else
                e.bump()
            if (later) {
                workNodes = own.concat((e.nodes || []).filter(function(n) { return !_isBg(n) }))
                e.bump()
            }
            if (e === before && e.squashHistSince)
                e.squashHistSince(startAt)
            refreshReservoir()
            say("Layout copied. Save to keep it; Undo puts the old one back."
                              + copyNotes(e.nodes, row))
        })
    }

    Dialog {
        id: _copyDlg
        title: _editorWin._copyFrom && _editorWin._copyFrom.template ? "Apply Template" : "Copy Device Map"
        modal: true
        // Another device's layout is usually the other hand's; a template is not.
        onOpened: {
            _copyMirror.checked = !(_editorWin._copyFrom && _editorWin._copyFrom.template)
            // Off by default (07 S76).
            _copyBg.checked = false
        }
        anchors.centerIn: parent
        width: Style.dp(460)
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(10)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fg
                text: "Replace this map's chips, leaders and drawings with "
                      + (_editorWin._copyFrom && _editorWin._copyFrom.template ? "the template " : "the layout of ")
                      + (_editorWin._copyFrom ? _editorWin._copyFrom.name : "") + "?"
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: _copyBg.checked
                      ? "This device's background is replaced too. Nothing is saved until you save; Undo puts the old layout back."
                      : "This device's background stays. Nothing is saved until you save; Undo puts the old layout back."
            }
            CheckBox {
                id: _copyBg
                objectName: "dmeCopyBgTick"
                checked: false
                text: "Copy the background too"
            }
            CheckBox {
                id: _copyMirror
                checked: true
                text: "Mirror left to right (for the other hand's stick)"
            }
            CheckBox {
                text: "Mirror pictures too"
                enabled: _copyMirror.checked
                checked: _opts.values["mirror-pictures"] === true
                onToggled: _opts.set("mirror-pictures", checked)
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    text: "Cancel"
                    onClicked: _copyDlg.close()
                }
                Button {
                    text: _editorWin._copyFrom && _editorWin._copyFrom.template ? "Apply Template" : "Copy Device Map"
                    highlighted: true
                    onClicked: {
                        var row = _editorWin._copyFrom
                        _copyDlg.close()
                        _editorWin.copyLayoutFrom(row, _copyMirror.checked, _copyBg.checked)
                    }
                }
            }
        }
    }

    // --- saved styles: the name for Save this style ----------------------------

    property string _styleKind: ""
    property string _styleFields: ""

    function askStyleName(kind, fieldsJson) {
        _styleKind = kind
        _styleFields = fieldsJson
        _styleNameDlg.open()
    }

    function saveStyleAs(name) {
        var clean = String(name || "").trim()
        if (!clean.length)
            return
        var ok = _opts.saveStyle(clean, _styleKind, _styleFields)
        say(ok ? "Saved style " + clean + "." : "The style was not saved.", !ok)
    }

    Dialog {
        id: _styleNameDlg
        title: "Save Style"
        modal: true
        anchors.centerIn: parent
        width: Style.dp(400)
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        onOpened: {
            _styleName.text = ""
            _styleName.forceActiveFocus()
        }
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(10)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: "Keeps this look under a name, to put on other items of the same kind from their right-click menu (Saved styles). A style of the same name is replaced. Edit → Device Map Options… → Library renames and deletes them."
            }
            TextField {
                id: _styleName
                Layout.fillWidth: true
                placeholderText: "Style name, e.g. Weapons, red"
                onAccepted: _styleSave.clicked()
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    text: "Cancel"
                    onClicked: _styleNameDlg.close()
                }
                Button {
                    id: _styleSave
                    text: "Save"
                    highlighted: true
                    enabled: _styleName.text.trim().length > 0
                    onClicked: {
                        var name = _styleName.text
                        _styleNameDlg.close()
                        _editorWin.saveStyleAs(name)
                    }
                }
            }
        }
    }

    // --- layout templates (File → Templates) ---------------------------------

    property var templateList: []
    property string _templateMsg: ""

    function refreshTemplates() {
        templateList = _hw.templates()
    }

    function layoutNow() {
        return editing ? editorNodesNow() : liveNodes
    }

    function saveTemplateAs(name, replace) {
        var clean = String(name || "").trim()
        if (!clean.length)
            return
        if (!replace && _hw.templateExists(clean)) {
            _templateReplace.pendingName = clean
            _templateReplace.confirm("Replace Template", "A template called " + clean + " exists. Replace it with this layout?", "Replace")
            return
        }
        var ok = _hw.saveTemplate(clean, JSON.stringify(layoutNow() || []), targetName)
        refreshTemplates()
        say(ok ? "Saved as template " + clean + "." : "The template was not saved.", !ok)
    }

    DismissibleDialog {
        id: _templateReplace
        property string pendingName: ""
        onConfirmed: _editorWin.saveTemplateAs(pendingName, true)
    }

    Dialog {
        id: _templateNameDlg
        title: "Save Layout as Template"
        modal: true
        anchors.centerIn: parent
        width: Style.dp(420)
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        onOpened: {
            _templateName.text = targetName
            _templateName.selectAll()
            _templateName.forceActiveFocus()
        }
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(10)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: "Keeps this layout's chips, leaders and drawings under a name, to apply to any device later (File → Templates → Apply Template)."
            }
            TextField {
                id: _templateName
                Layout.fillWidth: true
                placeholderText: "Template name"
                onAccepted: _templateSave.clicked()
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    text: "Cancel"
                    onClicked: _templateNameDlg.close()
                }
                Button {
                    id: _templateSave
                    text: "Save"
                    highlighted: true
                    enabled: _templateName.text.trim().length > 0
                    onClicked: {
                        var name = _templateName.text
                        _templateNameDlg.close()
                        _editorWin.saveTemplateAs(name, false)
                    }
                }
            }
        }
    }

    // Rename, export, delete and import templates.
    Dialog {
        id: _templatesDlg
        title: "Templates"
        modal: true
        anchors.centerIn: parent
        width: Style.dp(560)
        height: Math.min(Style.dp(520), _editorWin.height - Style.dp(80))
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        onOpened: {
            _templatesMessage.clear()
            _editorWin.refreshTemplates()
        }
        property string renaming: ""
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(8)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: _editorWin.templateList.length
                      ? "Each template is kept in its own folder with its own copies of its pictures. Export writes one, pictures and all, to a .gtemplate file to share; Import adds one."
                      : "No templates yet. File → Templates → Save Layout as Template… keeps the current layout."
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: Style.dp(4)
                model: _editorWin.templateList
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: RowLayout {
                    required property var modelData
                    width: ListView.view.width
                    spacing: Style.dp(6)
                    // The shared Rename box (01 S135): Enter or a click
                    // away saves once, Esc cancels.
                    RenameField {
                        Layout.fillWidth: true
                        name: modelData.name
                        open: _templatesDlg.renaming === modelData.name
                        onRenamed: (newName) => {
                            if (!_hw.renameTemplate(modelData.name, newName))
                                _editorWin.tellFailure("Rename Failed", _hw.templateError())
                        }
                        onEnded: {
                            _templatesDlg.renaming = ""
                            open = Qt.binding(() => _templatesDlg.renaming === modelData.name)
                            _editorWin.refreshTemplates()
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        visible: _templatesDlg.renaming !== modelData.name
                        color: Style.fg
                        elide: Text.ElideRight
                        text: modelData.name + "  ·  " + modelData.count + (modelData.count === 1 ? " item" : " items")
                    }
                    Button {
                        text: "Rename"
                        onClicked: _templatesDlg.renaming = modelData.name
                    }
                    Button {
                        text: "Export…"
                        onClicked: {
                            _templateExportFile.templateName = modelData.name
                            _templateExportFile.open()
                        }
                    }
                    DangerButton {
                        objectName: "templateDelete"
                        text: "Delete"
                        onClicked: {
                            var name = modelData.name
                            Confirm.ask(_editorWin.contentItem, {
                                title: "Delete template “" + name + "”?",
                                text: "Layouts made from it are not changed.",
                                undoable: false,
                                action: "Delete Template",
                                onAccept: function() {
                                    _hw.deleteTemplate(name)
                                    _editorWin.refreshTemplates()
                                }
                            })
                        }
                    }
                }
            }
            MessageLine {
                id: _templatesMessage
                objectName: "templatesMessage"
                Layout.fillWidth: true
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Style.dp(8)
                Button {
                    text: "Import…"
                    onClicked: _templateImportFile.open()
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Close"
                    onClicked: _templatesDlg.close()
                }
            }
        }
    }

    FilePicker {
        id: _templateExportFile
        property string templateName: ""
        kind: "template"
        mode: "save"
        title: "Export Template"
        defaultSuffix: "gtemplate"
        nameFilters: ["Device map template (*.gtemplate)"]
        onPicked: (selectedFile) => {
            if (!_hw.exportTemplate(templateName, selectedFile))
                _editorWin.tellFailure("Export Failed", _hw.templateError())
        }
    }

    FilePicker {
        id: _templateImportFile
        kind: "template"
        title: "Import Template"
        nameFilters: ["Device map template (*.gtemplate)"]
        onPicked: (selectedFile) => {
            var name = _hw.importTemplate(selectedFile)
            _editorWin.refreshTemplates()
            _templatesMessage.show(name.length ? "Imported template " + name + "." : "That file is not a Device map template.",
                                   !name.length)
        }
    }

    // File > Print & Export: its window, and the print area shown on the
    // map to move and resize while it is open.
    function openPrintExport() {
        setPrintAreaShown(true)
        _printWin.show()
        _printWin.raise()
        _printWin.requestActivate()
    }

    // The file dialogs, for Print & Export's buttons.
    function openExportFile(kind) {
        if (kind === "pdf")
            _exportPdfDialog.open()
        else if (kind === "jpg")
            _exportJpgDialog.open()
        else
            _exportPngDialog.open()
    }

    PrintExportWindow {
        id: _printWin
        host: _editorWin
        transientParent: _editorWin
    }

    FilePicker {
        id: _exportPdfDialog
        kind: "export"
        mode: "save"
        title: "Export PDF"
        defaultSuffix: "pdf"
        nameFilters: ["PDF (*.pdf)"]
        onPicked: (selectedFile) => exportTo(selectedFile, "pdf")
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // The menu bar (07 S135), in its order; a separator between groups.
        ThemedMenuBar {
            id: _menuBar
            Layout.fillWidth: true
            ThemedMenu {
                id: _fileMenu
                objectName: "dmeMenuFile"
                title: "File"
                // The lists in it are filled before ThemedMenu hides what
                // cannot be used and sizes itself.
                beforeShow: function() {
                    _editorWin.savedLayouts = _hw.savedLayouts(_editorWin.targetName)
                    _editorWin.refreshTemplates()
                }
                ThemedMenuItem {
                    text: "Edit Mapping"
                    hint: "Ctrl+E"
                    enabled: _editorWin.canEnterEdit
                    onTriggered: _editorWin.enterEdit()
                }
                ThemedMenuItem { text: "Save"; hint: "Ctrl+S"; enabled: _editorWin.editing; onTriggered: _editorWin.saveEdit() }
                ThemedMenuItem { text: "Cancel"; hint: "Ctrl+Shift+W"; enabled: _editorWin.editing; onTriggered: _editorWin.cancelEdit() }
                // This map's saved versions.
                ThemedMenuItem {
                    text: "History"
                    hint: "Ctrl+H"
                    enabled: _editorWin.targetName.length > 0
                    onTriggered: _editorWin.openHistory()
                }
                ThemedMenuSeparator {}
                ThemedMenu {
                    id: _deviceMenu
                    title: "Device"
                }
                ThemedMenuSeparator {}
                ThemedMenu {
                    id: _templateMenu
                    title: "Templates"
                    enabled: _editorWin.targetName.length > 0
                    beforeShow: _editorWin.refreshTemplates
                    ThemedMenuItem {
                        text: "Save Layout as Template…"
                        hint: "Ctrl+Shift+S"
                        enabled: (_editorWin.layoutNow() || []).length > 0
                        onTriggered: _templateNameDlg.open()
                    }
                    ThemedMenu {
                        id: _applyTemplateMenu
                        title: "Apply Template"
                        enabled: _editorWin.templateList.length > 0
                        Instantiator {
                            model: _editorWin.templateList
                            delegate: ThemedMenuItem {
                                required property var modelData
                                text: modelData.name + "…"
                                onTriggered: _editorWin.openCopyLayout({ name: modelData.name, template: true })
                            }
                            onObjectAdded: (index, object) => _applyTemplateMenu.insertItem(index, object)
                            onObjectRemoved: (index, object) => _applyTemplateMenu.removeItem(object)
                        }
                    }
                    ThemedMenuItem {
                        text: "Manage Templates…"
                        hint: "Ctrl+Shift+T"
                        onTriggered: _templatesDlg.open()
                    }
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Print & Export…"
                    hint: "Ctrl+P"
                    enabled: _editorWin.targetName.length > 0
                    onTriggered: _editorWin.openPrintExport()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Close"
                    hint: "Ctrl+W"
                    onTriggered: _editorWin.close()
                }
            }
            ThemedMenu {
                id: _editMenu
                objectName: "dmeMenuEdit"
                title: "Edit"
                // The devices with a device map, for Copy Device Map from Device.
                beforeShow: function() {
                    _editorWin.savedLayouts = _hw.savedLayouts(_editorWin.targetName)
                }
                ThemedMenuItem {
                    text: "Undo"
                    hint: "Ctrl+Z"
                    // Only while editing: the history is of edits.
                    enabled: { var e = _ed(); return editing && e ? e.canUndo : false }
                    onTriggered: { var e = _ed(); if (e) e.undo() }
                }
                ThemedMenuItem {
                    text: "Redo"
                    hint: "Ctrl+Y"
                    enabled: { var e = _ed(); return editing && e ? e.canRedo : false }
                    onTriggered: { var e = _ed(); if (e) e.redo() }
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    objectName: "dmeCut"
                    text: "Cut"
                    hint: "Ctrl+X"
                    enabled: { var e = _ed(); return editing && !!e && e.selectedId !== "" }
                    onTriggered: _editorWin.cutNow()
                    Component.onCompleted: _editorWin.addStar(this, "edit.cut")
                }
                ThemedMenuItem {
                    text: "Copy"
                    hint: "Ctrl+C"
                    enabled: { var e = _ed(); return e && e.selectedId !== "" }
                    onTriggered: _editorWin.runEdit("edit.copy")
                    Component.onCompleted: _editorWin.addStar(this, "edit.copy")
                }
                ThemedMenuItem {
                    text: "Paste"
                    hint: "Ctrl+V"
                    enabled: { var e = _ed(); return e && e.copiedNodes && e.copiedNodes.length }
                    onTriggered: _editorWin.runEdit("edit.paste")
                    Component.onCompleted: _editorWin.addStar(this, "edit.paste")
                }
                ThemedMenuItem {
                    text: "Paste Picture"
                    hint: "Ctrl+Shift+V"
                    enabled: editing && _hw.clipboardHasImage
                    onTriggered: pastePicture()
                }
                ThemedMenuItem {
                    text: "Duplicate"
                    hint: "Ctrl+D"
                    enabled: { var e = _ed(); return e && e.selectedId !== "" }
                    onTriggered: _editorWin.runEdit("edit.duplicate")
                    Component.onCompleted: _editorWin.addStar(this, "edit.duplicate")
                }
                ThemedMenuItem {
                    text: "Delete"
                    hint: "Delete"
                    enabled: { var e = _ed(); return editing && e && e.selectedId !== "" }
                    onTriggered: _editorWin.deleteOrBreak()
                    Component.onCompleted: _editorWin.addStar(this, "edit.delete")
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Select All"
                    hint: "Ctrl+A"
                    enabled: editing
                    onTriggered: _editorWin.runEdit("edit.selectAll")
                    Component.onCompleted: _editorWin.addStar(this, "edit.selectAll")
                }
                ThemedMenuSeparator {}
                ThemedMenu {
                    id: _bgMenu
                    objectName: "dmeMenuBackground"
                    title: "Background"
                    // Edit › Background › (user 2026-10-11: moved into Edit); everything
                    // in it needs editing (07 S39).
                    enabled: editing
                    ThemedMenuItem {
                        objectName: "dmeEditBackground"
                        text: "Edit Background"
                        hint: "Ctrl+B"
                        enabled: editing && !_editorWin.bgMode
                        onTriggered: _editorWin.setEditPlane("background")
                    }
                    ThemedMenuSeparator {}
                    ThemedMenuItem {
                        objectName: "dmeAddBgPicture"
                        text: "Add Picture to Background…"
                        hint: "Ctrl+I"
                        enabled: editing
                        onTriggered: _bgPictureDialog.open()
                    }
                    ThemedMenuItem {
                        objectName: "dmeClearBackground"
                        text: "Clear Background"
                        enabled: editing
                        onTriggered: _editorWin.clearBackground()
                    }
                }
                ThemedMenuSeparator {}
                // Another device's device map onto this one (its background
                // stays unless copied too, 07 S76).
                ThemedMenu {
                    id: _copyMenu
                    title: "Copy Device Map from Device"
                    enabled: _editorWin.targetName.length > 0 && _editorWin.savedLayouts.length > 0
                    Instantiator {
                        model: _editorWin.savedLayouts
                        delegate: ThemedMenuItem {
                            required property var modelData
                            text: modelData.name + "…"
                            onTriggered: _editorWin.openCopyLayout(modelData)
                        }
                        onObjectAdded: (index, object) => _copyMenu.insertItem(index, object)
                        onObjectRemoved: (index, object) => _copyMenu.removeItem(object)
                    }
                }
                ThemedMenuItem {
                    text: "Mirror Layout"
                    hint: "Ctrl+M"
                    enabled: editing
                    onTriggered: _editorWin.mirrorNow()
                }
                ThemedMenuItem { text: "Reset Layout"; enabled: editing; onTriggered: _editorWin.askResetLayout() }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    objectName: "dmeOptionsItem"
                    text: "Device Map Options…"
                    hint: "Ctrl+,"
                    onTriggered: _editorWin.openOptions()
                }
            }
            ThemedMenu {
                id: _viewMenu
                objectName: "dmeMenuView"
                title: "View"
                ThemedMenuItem {
                    text: "Zoom In"
                    hint: "Ctrl+="
                    onTriggered: _editorWin.zoomStep(1.25)
                }
                ThemedMenuItem {
                    text: "Zoom Out"
                    hint: "Ctrl+-"
                    onTriggered: _editorWin.zoomStep(0.8)
                }
                ThemedMenuItem {
                    text: "Zoom to Fit Page"
                    hint: "Ctrl+1"
                    onTriggered: _editorWin.zoomToPage()
                }
                ThemedMenuItem {
                    text: "Zoom to Selection"
                    hint: "Ctrl+2"
                    enabled: { var e = _ed(); return !!(e && e.selectedIds && e.selectedIds.length) }
                    onTriggered: _editorWin.zoomToSelection()
                }
                ThemedMenuItem {
                    text: "Fit to Photo Frame"
                    hint: "Ctrl+3"
                    enabled: editing && !fittedThisEdit
                    onTriggered: fitToPhotoFrame()
                }
                ThemedMenuItem {
                    text: "Reset View"
                    hint: "Ctrl+0"
                    onTriggered: _editorWin.resetViewNow()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Chips"
                    hint: "F6"
                    enabled: editing
                    checkable: true
                    checked: _chipsSide.open
                    onTriggered: _chipsSide.toggle()
                }
                ThemedMenuItem {
                    text: "Layers"
                    hint: "F7"
                    enabled: editing
                    checkable: true
                    checked: _layersSide.open
                    onTriggered: _layersSide.toggle()
                }
                ThemedMenuItem {
                    objectName: "dmePropertiesItem"
                    text: "Properties"
                    hint: "F4"
                    enabled: editing
                    checkable: true
                    checked: _editorWin.propsOn && _layersSide.open
                    onTriggered: {
                        _editorWin.toggleProps()
                        checked = Qt.binding(() => _editorWin.propsOn && _layersSide.open)
                    }
                }
                ThemedMenuItem {
                    text: "Search layers…"
                    hint: "Ctrl+F"
                    enabled: editing
                    onTriggered: _editorWin.searchLayers()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Rulers"
                    hint: "Ctrl+R"
                    checkable: true
                    checked: _opts.values["rulers"] === true
                    onTriggered: _opts.set("rulers", checked)
                }
                ThemedMenuItem {
                    text: "Show Guides"
                    hint: "Ctrl+;"
                    checkable: true
                    checked: _editorWin.guidesOn
                    onTriggered: _editorWin.setGuidesShown(checked)
                }
                ThemedMenuItem {
                    text: "Clear Guides"
                    enabled: _editorWin.guidesX.length + _editorWin.guidesY.length > 0
                    onTriggered: { var e = _ed(); if (e) e.clearRulerGuides() }
                }
                ThemedMenu {
                    title: "Grid"
                    ThemedMenuItem {
                        text: "Show Grid"
                        hint: "Ctrl+'"
                        checkable: true
                        checked: _editorWin.gridOn
                        onTriggered: _editorWin.setGridPref("gridOn", checked)
                    }
                    ThemedMenuSeparator {}
                    ThemedMenu {
                        title: "Size"
                        Repeater {
                            model: [1, 2, 4, 8, 12, 16, 24, 32, 48, 64, 200, 400]
                            ThemedMenuItem {
                                required property int modelData
                                text: String(modelData)
                                checkable: true
                                checked: { var e = _ed(); return !!e && e.gridSize === modelData }
                                onTriggered: _editorWin.setGridPref("gridSize", modelData)
                            }
                        }
                    }
                }
                ThemedMenuItem {
                    text: "Snap to Grid"
                    hint: "Ctrl+Shift+'"
                    checkable: true
                    checked: _editorWin.snapOn
                    onTriggered: _editorWin.setGridPref("snapOn", checked)
                }
                ThemedMenuItem {
                    text: "Snap to Entities"
                    hint: "Ctrl+Shift+;"
                    checkable: true
                    checked: _editorWin.snapEntOn
                    onTriggered: _editorWin.setGridPref("snapEntOn", checked)
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    objectName: "dmeShowPrintArea"
                    text: "Show Print Area"
                    enabled: editing
                    checkable: true
                    checked: _editorWin.printAreaOn
                    onTriggered: {
                        _editorWin.setPrintAreaShown(checked)
                        // Follows the store again (Print & Export shows it too).
                        checked = Qt.binding(() => _editorWin.printAreaOn)
                    }
                }
                ThemedMenuItem {
                    text: "Set Print Area"
                    hint: "Alt+drag"
                    enabled: editing
                    onTriggered: {
                        var e = _ed()
                        if (!e)
                            return
                        _editorWin.setPrintAreaShown(true)
                        e.printAreaArm = true
                        if (e.showFindMessage)
                            e.showFindMessage("Drag on the map to set the print area. Esc cancels.")
                    }
                }
                ThemedMenuItem {
                    text: "Clear Print Area"
                    enabled: editing && !!_editorWin.printArea
                    onTriggered: { var e = _ed(); if (e) e.clearPrintArea() }
                }
                ThemedMenuItem {
                    text: "Print Area Color…"
                    onTriggered: {
                        var e = _ed()
                        _editorWin.openColorField("printAreaColor", (e && e.printAreaColor.length) ? e.printAreaColor : String(Style.dangerBright), null)
                    }
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    objectName: "dmeResetPanels"
                    text: "Reset Panels"
                    onTriggered: _editorWin.resetPanels()
                }
            }
            // Insert, Arrange and Format (07 S134): filled from
            // rig_commands.js (buildCommandMenus); rows that don't apply to
            // the selection are greyed out, not hidden.
            ThemedMenu {
                id: _insertMenu
                objectName: "dmeMenuInsert"
                title: "Insert"
                compact: false
                enabled: editing
                beforeShow: _editorWin.refreshCommandTexts
            }
            ThemedMenu {
                id: _arrangeMenu
                objectName: "dmeMenuArrange"
                title: "Arrange"
                compact: false
                enabled: editing
                // Its texts follow the editor (the rotate step).
                beforeShow: _editorWin.refreshCommandTexts
            }
            // Leaders and callouts in a menu of their own (user 2026-10-11).
            ThemedMenu {
                id: _leaderMenu
                objectName: "dmeMenuLeader"
                title: "Leader"
                compact: false
                enabled: editing
                beforeShow: _editorWin.refreshCommandTexts
            }
            ThemedMenu {
                id: _formatMenu
                objectName: "dmeMenuFormat"
                title: "Format"
                compact: false
                beforeShow: _editorWin.refreshCommandTexts
                // Chip Text and Labels Mode moved here from View (S135).
                ThemedMenuSeparator {}
                ThemedMenu {
                    title: "Chip Text"
                    Repeater {
                        model: ["Name", "Action", "Name and action"]
                        ThemedMenuItem {
                            required property string modelData
                            text: modelData
                            checkable: true
                            checked: String(_opts.values["chip-text"] || "Name") === modelData
                            onTriggered: _opts.set("chip-text", modelData)
                        }
                    }
                }
                ThemedMenu {
                    id: _labelModeMenu
                    title: "Labels Mode"
                    ThemedMenuItem {
                        text: "Follow the Program"
                        checkable: true
                        checked: _editorWin.labelMode === ""
                        onTriggered: _editorWin.labelMode = ""
                    }
                    ThemedMenuSeparator {}
                    Instantiator {
                        model: _editorWin.profileModes
                        delegate: ThemedMenuItem {
                            required property string modelData
                            text: modelData
                            checkable: true
                            checked: _editorWin.labelMode === modelData
                            onTriggered: _editorWin.labelMode = modelData
                        }
                        onObjectAdded: (index, object) => _labelModeMenu.insertItem(index + 2, object)
                        onObjectRemoved: (index, object) => _labelModeMenu.removeItem(object)
                    }
                }
            }
            ThemedMenu {
                id: _helpMenu
                objectName: "dmeMenuHelp"
                title: "Help"
                ThemedMenuItem {
                    text: "Help"
                    hint: "F1"
                    onTriggered: _editorWin.openGuide()
                }
                ThemedMenuItem {
                    objectName: "dmeKeyboardShortcuts"
                    text: "Keyboard Shortcuts…"
                    hint: "Ctrl+K"
                    onTriggered: _editorWin.openShortcuts()
                }
            }
        }

        // The view-only banner (D-FIXLIST-B1 item 1): one slim line under
        // the menu bar while the map is live (not editing), in the
        // Background-mode banner's look. No close button; hidden while
        // editing. Two texts (D-TESTLIST-1 item 4): with no device, how to
        // choose one (its "File › Device" link opens that menu); with a
        // device, its link starts editing as File › Edit Mapping does.
        Rectangle {
            id: _viewOnlyBanner
            objectName: "dmeViewOnlyBanner"
            visible: !_editorWin.editing
            Layout.fillWidth: true
            Layout.leftMargin: Style.dp(10)
            Layout.rightMargin: Style.dp(10)
            Layout.topMargin: Style.dp(4)
            Layout.preferredHeight: _viewOnlyRow.implicitHeight + Style.dp(4)
            radius: Style.dp(4)
            color: Style.infoFillDeep
            border.color: Style.info
            readonly property bool hasDevice: _editorWin.targetName.length > 0
            RowLayout {
                id: _viewOnlyRow
                anchors.centerIn: parent
                spacing: 0
                Label {
                    objectName: "dmeViewOnlyText"
                    text: _viewOnlyBanner.hasDevice
                          ? "View only. To edit this device map, choose File › "
                          : "No device chosen. Choose one from "
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(11)
                }
                Label {
                    id: _viewOnlyDevice
                    objectName: "dmeViewOnlyDevice"
                    text: "File › Device"
                    visible: !_viewOnlyBanner.hasDevice
                    color: Style.info
                    font.pixelSize: Style.dp(11)
                    font.underline: true
                    Accessible.role: Accessible.Link
                    Accessible.name: text
                    Accessible.onPressAction: activate()
                    function activate() {
                        _editorWin.openDeviceMenu()
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _viewOnlyDevice.activate()
                    }
                }
                Label {
                    id: _viewOnlyEdit
                    objectName: "dmeViewOnlyEdit"
                    visible: _viewOnlyBanner.hasDevice
                    text: "Edit Mapping"
                    enabled: _editorWin.canEnterEdit
                    color: enabled ? Style.info : Style.fg
                    opacity: enabled ? 1 : 0.6
                    font.pixelSize: Style.dp(11)
                    font.underline: enabled
                    Accessible.role: Accessible.Link
                    Accessible.name: text
                    Accessible.onPressAction: activate()
                    function activate() {
                        _editorWin.enterEdit()
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: parent.enabled
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _viewOnlyEdit.activate()
                    }
                }
                Label {
                    text: _viewOnlyBanner.hasDevice
                          ? "."
                          : ", then File › Edit Mapping to edit its device map."
                    color: Style.fgStrong
                    font.pixelSize: Style.dp(11)
                }
            }
        }

        // What just happened: saved, exported, copied, failed (01 S142).
        MessageLine {
            id: _messageLine
            Layout.fillWidth: true
        }

        RowLayout {
            id: _mapRow
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0
            onWidthChanged: Qt.callLater(_editorWin.fitSides)

            // Chips (07 S128-S131): a side panel on the left edge, folded to a
            // strip or out at its width. Pinned it takes its width from the
            // map area; unpinned it is drawn over the map (this slot's z).
            Item {
                id: _leftSlot
                Layout.fillHeight: true
                Layout.preferredWidth: _chipsSide.takenWidth
                z: 60
                SidePanel {
                    id: _chipsSide
                    objectName: "chipsSide"
                    side: "left"
                    title: "Chips"
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    available: _editorWin.editing
                    minWidth: Style.dp(210)
                    maxWidth: Style.dp(520)
                    onChanged: _editorWin.sideChangedByUser(_chipsSide, "chips")
                    onStripClicked: _layersSide.foldIfUnpinned()
                    onTakenWidthChanged: Qt.callLater(_editorWin.fitSides)

                        Item {
                            id: _poolFloat
                            objectName: "chipPool"
                            anchors.fill: parent

                            // Its background: takes the clicks (not the map's).
                            MouseArea {
                                anchors.fill: parent
                                z: 0
                                acceptedButtons: Qt.AllButtons
                                hoverEnabled: true
                                enabled: {
                                    var e = _editorWin._ed()
                                    return !(e && e.dragKind && e.dragKind.length)
                                }
                                onPressed: (m) => { m.accepted = true }
                                onClicked: (m) => { m.accepted = true }
                                onDoubleClicked: (m) => { m.accepted = true }
                                onWheel: (w) => { w.accepted = true }
                            }

                            // A chip dragged over the pool lights it: let go to take the
                            // chip off the map.
                            readonly property bool dropHot: {
                                var e = _editorWin._ed()
                                return !!(e && e.poolHover)
                            }
                            Rectangle {
                                anchors.fill: parent
                                z: 1
                                radius: Style.dp(8)
                                color: Style.bgCard
                                border.color: _poolFloat.dropHot ? Style.accent : Style.lineStrong
                                border.width: _poolFloat.dropHot ? Style.dp(3) : 1
                            }
                            Label {
                                z: 3
                                visible: _poolFloat.dropHot
                                anchors.centerIn: parent
                                text: "Let go to take it off the map"
                                color: Style.fg
                                font.bold: true
                                background: Rectangle { color: Style.bgCard; radius: Style.dp(4) }
                                padding: Style.dp(6)
                            }
                            ColumnLayout {
                                z: 2
                                anchors.fill: parent
                                anchors.margins: Style.dp(8)
                                anchors.bottomMargin: Style.dp(12)
                                anchors.rightMargin: Style.dp(10)
                                spacing: Style.dp(6)
                                // The filter box has the whole top row; Reset and
                                // Chip only sit under it (07 S132).
                                Item {
                                    Layout.fillWidth: true
                                    implicitHeight: Style.dp(28)
                                    TextField {
                                        id: _poolSearch
                                        objectName: "poolFilter"
                                        anchors.fill: parent
                                        placeholderText: "Filter friendly or hardware"
                                        text: poolFilter
                                        rightPadding: Style.dp(26)
                                        onTextChanged: {
                                            if (poolFilter !== text)
                                                poolFilter = text
                                        }
                                    }
                                    Text {
                                        visible: poolFilter.length > 0
                                        anchors.right: parent.right
                                        anchors.rightMargin: Style.dp(8)
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "×"
                                        color: Style.fgMuted
                                        font.pixelSize: Style.dp(16)
                                        z: 2
                                        MouseArea {
                                            anchors.fill: parent
                                            anchors.margins: -Style.dp(6)
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: clearPoolFilter()
                                        }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Style.dp(6)
                                    Button {
                                        objectName: "poolReset"
                                        text: "Reset"
                                        implicitHeight: Style.dp(28)
                                        onClicked: clearPoolFilter()
                                    }
                                    // Device Map Options → Chip only, here where chips are added.
                                    CheckBox {
                                        objectName: "poolChipOnly"
                                        // Its whole label whenever the panel has room
                                        // (the spacer after it takes what is left);
                                        // it shrinks only when the panel does.
                                        Layout.preferredWidth: implicitWidth
                                        Layout.maximumWidth: implicitWidth
                                        Layout.minimumWidth: implicitIndicatorWidth + leftPadding + rightPadding
                                        text: "Chip only"
                                        checked: _opts.values["chip-only"] === true
                                        onToggled: _opts.set("chip-only", checked)
                                        ToolTip.visible: hovered
                                        ToolTip.text: "Add chips with no leader and no hotspot"
                                    }
                                    Item { Layout.fillWidth: true }
                                }
                                Flickable {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    interactive: !_editorWin.poolDrag
                                    pressDelay: 0
                                    contentWidth: width
                                    contentHeight: _resFlow.implicitHeight
                                    boundsBehavior: Flickable.StopAtBounds
                                    Flow {
                                        id: _resFlow
                                        width: parent.width
                                        spacing: Style.dp(6)
                                        Repeater {
                                            model: resItems
                                            delegate: Rectangle {
                                                required property var modelData
                                                property bool lit: {
                                                    var t = _editorWin.resTick
                                                    if (!_editorWin.faceLive || !modelData)
                                                        return false
                                                    var e = _ed()
                                                    if (!e || !e.litOf)
                                                        return false
                                                    return e.litOf(modelData.kind, modelData.hwId)
                                                }
                                                implicitWidth: Math.min(Style.dp(260), _chipLab.implicitWidth + Style.dp(18))
                                                implicitHeight: Style.dp(26)
                                                radius: Style.dp(13)
                                                color: lit ? "#14532D" : "#18181B"
                                                border.color: lit ? "#22C55E" : "#3F3F46"
                                                border.width: lit ? Style.dp(2) : Style.dp(1)
                                                opacity: (_editorWin.poolDrag && _editorWin.poolHw === (modelData ? modelData.hwId : -1) && _editorWin.poolKind === (modelData ? modelData.kind : "")) ? 0.35 : 1
                                                Text {
                                                    id: _chipLab
                                                    anchors.centerIn: parent
                                                    text: modelData ? modelData.friendly : ""
                                                    color: lit ? "#BBF7D0" : "#E4E4E7"
                                                    font.pixelSize: Style.dp(11)
                                                }
                                                PointerTip {
                                                    show: !_editorWin.poolDrag && _poolChipHover.containsMouse
                                                    timeout: 4000
                                                    text: {
                                                        var e = _ed()
                                                        if (!e || !modelData)
                                                            return ""
                                                        return e.hardwareLabel(modelData.kind, modelData.hwId)
                                                    }
                                                }
                                                MouseArea {
                                                    id: _poolChipHover
                                                    anchors.fill: parent
                                                    z: 2
                                                    hoverEnabled: true
                                                    preventStealing: true
                                                    cursorShape: Qt.OpenHandCursor
                                                    onPressed: (m) => {
                                                        if (!modelData)
                                                            return
                                                        var p = mapToItem(_mapHost, m.x, m.y)
                                                        _editorWin.poolKind = modelData.kind
                                                        _editorWin.poolHw = modelData.hwId
                                                        _editorWin.poolName = modelData.friendly
                                                        _editorWin.poolX = p.x
                                                        _editorWin.poolY = p.y
                                                        _editorWin.poolDrag = true
                                                    }
                                                    onPositionChanged: (m) => {
                                                        if (!_editorWin.poolDrag)
                                                            return
                                                        var p = mapToItem(_mapHost, m.x, m.y)
                                                        _editorWin.poolX = p.x
                                                        _editorWin.poolY = p.y
                                                    }
                                                    onReleased: (m) => {
                                                        if (!_editorWin.poolDrag)
                                                            return
                                                        var p = mapToItem(_mapHost, m.x, m.y)
                                                        dropPool(p.x, p.y)
                                                    }
                                                    onCanceled: _editorWin.poolDrag = false
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                }
            }

            Item {
                id: _mapHost
                Layout.fillWidth: true
                Layout.fillHeight: true
                // Room between the map (its rulers) and the side panels.
                Layout.margins: Style.dp(10)

                JGText {
                    anchors.centerIn: parent
                    visible: !targetName.length
                    text: "Choose a device from the File menu."
                    opacity: 0.65
                }

                // Background mode's banner (07 S114, S115): over the map,
                // never printed (the renderer draws from the editor).
                Rectangle {
                    id: _bgBanner
                    objectName: "dmeBgBanner"
                    visible: _editorWin.bgMode
                    z: 50
                    anchors.top: parent.top
                    anchors.topMargin: Style.dp(6)
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(parent.width - Style.dp(20), _bgBannerCol.implicitWidth + Style.dp(24))
                    height: _bgBannerCol.implicitHeight + Style.dp(12)
                    radius: Style.dp(6)
                    color: Style.infoFillDeep
                    border.color: Style.info
                    ColumnLayout {
                        id: _bgBannerCol
                        anchors.centerIn: parent
                        width: parent.width - Style.dp(24)
                        spacing: Style.dp(2)
                        RowLayout {
                            spacing: Style.dp(8)
                            Label {
                                objectName: "dmeBgBannerText"
                                text: "Editing the background —"
                                color: Style.fgStrong
                                font.pixelSize: Style.dp(12)
                            }
                            Button {
                                objectName: "dmeBgDone"
                                text: "Done"
                                font.pixelSize: Style.dp(11)
                                onClicked: _editorWin.setEditPlane("foreground")
                            }
                            CheckBox {
                                objectName: "dmeFgFaintTick"
                                text: "Show foreground faintly"
                                font.pixelSize: Style.dp(11)
                                checked: _opts.values["bm-fg-faint"] !== false
                                onToggled: {
                                    _opts.set("bm-fg-faint", checked)
                                    checked = Qt.binding(() => _opts.values["bm-fg-faint"] !== false)
                                }
                            }
                        }
                        Label {
                            objectName: "dmeBgHint"
                            visible: _editorWin.bgHintNow
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "Your chips are shown faintly. Use Move to Foreground to bring an item forward."
                            color: Style.fg
                            font.pixelSize: Style.dp(11)
                        }
                    }
                }


                Component {
                    id: _cardComp
                    DeviceMapCard {
                        id: _card
                        anchors.fill: parent
                        deviceGuid: parent.dGuid
                        title: _editorWin.displayName(parent.dGuid, parent.dName)
                        pairLabel: parent.dPair
                        editing: _editorWin.editing
                        editorNodes: _editorWin.editing ? _editorWin.workNodes : _editorWin.liveNodes
                        photoOverride: _editorWin.photoOverride
                        onChipRowsChanged: _editorWin.deferReservoir()
                        // Reset Shape gives a picture back its own proportions (07 S154).
                        function giveAspectFn() {
                            if (editorItem)
                                editorItem.imageAspectFn = function(rel) { return _hw.imageAspect(rel) }
                        }
                        onEditorItemChanged: giveAspectFn()
                        Connections {
                            target: _card.editorItem
                            function onSelectedChanged() { _editorWin.deferSelected() }
                            function onTickChanged() { _editorWin.resTick++ }
                            function onChipMenuRequested(x, y) { _editorWin.openChipMenu(x, y) }
                            function onFindNotPlaced(label) { _editorWin.poolFilter = label }
                            function onEditPlaneChanged() { _editorWin.planeChanged() }
                            function onShowFgFaintChanged() { _editorWin.keepPlaneView("bm-fg-faint") }
                            function onBgViewHiddenChanged() { _editorWin.keepPlaneView("bm-bg-hidden") }
                            function onBgViewOpacityChanged() { _editorWin.keepPlaneView("bm-bg-opacity") }
                            function onSaveStyleRequested(kind, fieldsJson) { _editorWin.askStyleName(kind, fieldsJson) }
                            function onRulerGuidesEdited() { _editorWin.guidesFromEditor() }
                            function onOverlayImportRequested() { _overlayDialog.open() }
                            function onChoosePictureRequested(nodeId) { _choosePictureDialog.pick(nodeId) }
                            function onPastePictureRequested() { _editorWin.pastePicture() }
                            function onColorPickRequested(field, hex) { _editorWin.openColorField(field, hex, null) }
                            function onDrawToolChanged() { _editorWin.resTick++ }
                            function onHistoryChanged() {
                                _editorWin.noteHistoryForFit()
                                _editorWin.deferHistory()
                            }
                            function onNodesChanged() { _editorWin.deferHistory() }
                            function onMapPressed() {
                                _chipsSide.foldIfUnpinned()
                                _layersSide.foldIfUnpinned()
                            }
                            function onPrintAreaEdited(drawn) {
                                _editorWin.printArea = _card.editorItem.printArea
                                if (drawn)
                                    _editorWin.setPrintAreaShown(true)
                                _editorWin.persistUi()
                                _editorWin.noteEditStep()
                            }
                            function onSeededChanged() { _editorWin.noteSeeded() }
                        }
                        // The right-click menu's additions (07 S136).
                        Connections {
                            target: _card.editorItem
                            ignoreUnknownSignals: true
                            function onShowInLayersRequested(id) { _editorWin.showInLayers(id) }
                            function onPropertiesRequested() { _editorWin.showProperties() }
                            function onFavouriteToggled(id) { _editorWin.toggleFavourite(id) }
                            function onFavouriteRemoved(id) { _editorWin.removeFavourite(id) }
                        }
                        Component.onCompleted: {
                            _cardLoader.item = _card
                            giveAspectFn()
                        }
                        // A newer card may already be in use: only this one's own.
                        Component.onDestruction: {
                            if (_cardLoader.item === _card) {
                                _cardLoader.item = null
                                _editorWin.faceLive = false
                            }
                        }
                    }
                }

                // The device's map: made again only when another device is
                // chosen (cardKey), not when devices come and go.
                Repeater {
                    model: _editorWin.cardKey.length ? [_editorWin.cardKey] : []
                    Loader {
                        id: _slot
                        anchors.fill: parent
                        property string dGuid: _editorWin.targetRow ? _editorWin.targetRow.guid : _editorWin.targetGuid
                        property string dName: _editorWin.targetRow ? _editorWin.targetRow.name : _editorWin.targetName
                        property string dPair: _editorWin.targetRow ? _editorWin.targetRow.pairLabel : ""
                        sourceComponent: _cardComp
                        onLoaded: {
                            _cardLoader.item = item
                            _editorWin.faceLive = true
                            _editorWin.deferFace()
                            _editorWin.carryCopy(item)
                        }
                    }
                }

                // The stick is unplugged: its map is covered (Export still
                // draws it), and comes back by itself when the stick does.
                Rectangle {
                    anchors.fill: parent
                    visible: _editorWin.targetName.length > 0 && !_editorWin.mapShown
                    z: 44
                    color: Style.background
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.AllButtons
                        hoverEnabled: true
                        onWheel: (w) => { w.accepted = true }
                    }
                    JGText {
                        anchors.centerIn: parent
                        text: "Connect " + _editorWin.targetName + " to see its device map."
                        opacity: 0.65
                    }
                }

                // The stick was unplugged during an edit: the work stays.
                Rectangle {
                    visible: _editorWin.editing && !_editorWin.targetConnected
                    z: 45
                    anchors.top: parent.top
                    anchors.topMargin: Style.dp(8)
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(parent.width - Style.dp(32), _offNote.implicitWidth + Style.dp(24))
                    height: _offNote.implicitHeight + Style.dp(12)
                    radius: Style.dp(4)
                    color: Style.bgRaised
                    border.color: Style.warn
                    JGText {
                        id: _offNote
                        anchors.centerIn: parent
                        width: Math.min(implicitWidth, parent.parent.width - Style.dp(56))
                        wrapMode: Text.WordWrap
                        text: _editorWin.targetName + " is disconnected. You can still save or cancel this edit."
                    }
                }

                // Drop picture files anywhere on the map to add them as layers.
                DropArea {
                    id: _pictureDrop
                    anchors.fill: parent
                    z: 40
                    enabled: !!_editorWin._ed()
                    keys: ["text/uri-list"]
                    onEntered: (drag) => {
                        drag.accepted = drag.hasUrls && _hw.hasPictureFiles(drag.urls)
                    }
                    onDropped: (drop) => {
                        if (!drop.hasUrls)
                            return
                        if (_editorWin.dropPictures(drop.urls, drop.x, drop.y, _pictureDrop))
                            drop.accept(Qt.CopyAction)
                    }
                    Rectangle {
                        anchors.fill: parent
                        visible: _pictureDrop.containsDrag
                        color: "transparent"
                        border.width: 3
                        border.color: Style.info
                        radius: 6
                    }
                }

                QtObject {
                    id: _cardLoader
                    property var item: null
                }

                // The print area's frame: View > Show Print Area (07 S135).
                Binding {
                    target: _editorWin._ed()
                    property: "printAreaShown"
                    // Only while editing (07 S86).
                    value: _editorWin.printAreaOn && _editorWin.editing
                    when: !!_editorWin._ed()
                    restoreMode: Binding.RestoreNone
                }
                Binding {
                    target: _editorWin._ed()
                    property: "canPastePicture"
                    value: _hw.clipboardHasImage
                    when: !!_editorWin._ed()
                    restoreMode: Binding.RestoreNone
                }
                Binding {
                    target: _editorWin._ed()
                    property: "clipboardSerial"
                    value: _hw.clipboardSerial
                    when: !!_editorWin._ed()
                    restoreMode: Binding.RestoreNone
                }
                MouseArea {
                    id: _poolCatch
                    anchors.fill: parent
                    z: 40
                    visible: poolDrag
                    hoverEnabled: true
                    preventStealing: true
                    acceptedButtons: Qt.LeftButton
                    onPositionChanged: (m) => {
                        poolX = m.x
                        poolY = m.y
                    }
                    onReleased: (m) => dropPool(m.x, m.y)
                    onCanceled: poolDrag = false
                }
            }

            // Layers (07 S128-S131): a side panel on the right edge, as Chips.
            Item {
                id: _rightSlot
                Layout.fillHeight: true
                Layout.preferredWidth: _layersSide.takenWidth
                z: 60
                SidePanel {
                    id: _layersSide
                    objectName: "layersSide"
                    side: "right"
                    title: "Layers"
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    available: _editorWin.editing
                    minWidth: Style.dp(220)
                    maxWidth: Style.dp(560)
                    onChanged: _editorWin.sideChangedByUser(_layersSide, "layers")
                    onStripClicked: _chipsSide.foldIfUnpinned()
                    onTakenWidthChanged: Qt.callLater(_editorWin.fitSides)

                    // Layers on top; Properties under it while something is
                    // selected (07 S135), with a divider dragged to share the
                    // height. The share is kept when a drag ends (S99).
                    Item {
                        id: _rightBody
                        objectName: "rightPanelBody"
                        anchors.fill: parent
                        readonly property real grip: Style.dp(6)
                        // Mid-drag: the share so far (kept on release); -1 otherwise.
                        property real liveShare: -1
                        readonly property real share: Math.max(0.2, Math.min(0.8,
                            liveShare >= 0 ? liveShare : _editorWin.propsSplit))

                        RigLayersPanel {
                            id: _layersPanel
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: _editorWin.propsShown
                                    ? Math.round((parent.height - _rightBody.grip) * _rightBody.share)
                                    : parent.height
                            ed: _editorWin._ed()
                            showTitle: false
                            onCloseRequested: _layersSide.fold()
                        }

                        // The Layers / Properties divider.
                        Item {
                            id: _propsDivider
                            objectName: "propsDivider"
                            visible: _editorWin.propsShown
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: _layersPanel.bottom
                            height: _rightBody.grip
                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                height: 1
                                color: _dividerArea.containsMouse || _dividerArea.pressed ? Style.accent : Style.lineStrong
                            }
                            MouseArea {
                                id: _dividerArea
                                anchors.fill: parent
                                anchors.topMargin: -Style.dp(2)
                                anchors.bottomMargin: -Style.dp(2)
                                hoverEnabled: true
                                preventStealing: true
                                cursorShape: Qt.SizeVerCursor
                                property real startY: 0
                                property real startShare: 0
                                onPressed: (m) => {
                                    startY = mapToItem(_rightBody, m.x, m.y).y
                                    startShare = _rightBody.share
                                    _rightBody.liveShare = startShare
                                }
                                onPositionChanged: (m) => {
                                    if (!pressed)
                                        return
                                    var room = Math.max(1, _rightBody.height - _rightBody.grip)
                                    var y = mapToItem(_rightBody, m.x, m.y).y
                                    _rightBody.liveShare = Math.max(0.2, Math.min(0.8, startShare + (y - startY) / room))
                                }
                                onReleased: {
                                    var kept = _rightBody.liveShare
                                    _editorWin.propsSplit = kept
                                    _rightBody.liveShare = -1
                                    _opts.setPropsSplit(kept)
                                }
                                onCanceled: _rightBody.liveShare = -1
                            }
                        }

                        // Properties: the selected item's place, size, angle
                        // and style.
                        RigPropsPanel {
                            id: _propsPanel
                            objectName: "propsPanel"
                            visible: _editorWin.propsShown
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: _propsDivider.bottom
                            anchors.bottom: parent.bottom
                            ed: _editorWin._ed()
                            onCloseRequested: _editorWin.propsOn = false
                        }
                    }
                }
            }
        }

        // The status line: the view's size, the plane being edited, what the
        // tool does, and the module file (its full path on hover).
        ToolBar {
            id: _statusLine
            Layout.fillWidth: true
            implicitHeight: Style.dp(20)
            topPadding: 0
            bottomPadding: 0
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.dp(6)
                anchors.rightMargin: Style.dp(6)
                spacing: Style.dp(10)
                Label {
                    visible: true
                    text: {
                        var f = _cardLoader.item
                        var raw = f ? Number(f.viewPct) : 1
                        var pct = (raw === raw) ? Math.round(raw * 100) : 100
                        return "View " + pct + "%"
                    }
                    color: Style.fg
                    font.pixelSize: Style.dp(11)
                }
                Label {
                    // 07 S117: the plane while editing; "Background hidden"
                    // while the Background row's eye hides it.
                    objectName: "dmePlaneStatus"
                    visible: text.length > 0
                    text: {
                        var parts = []
                        if (editing)
                            parts.push(_editorWin.bgMode ? "Background" : "Foreground")
                        if (_editorWin.bgHidden && !_editorWin.bgMode)
                            parts.push("Background hidden")
                        return parts.join(" · ")
                    }
                    color: _editorWin.bgMode ? Style.info : Style.fgMuted
                    font.pixelSize: Style.dp(11)
                }
                Label {
                    visible: {
                        resTick
                        var e = _ed()
                        return editing && e && e.drawTool && e.drawTool.length
                    }
                    text: "Drawing — drag empty. Shift locks aspect. Esc cancels."
                    color: Style.warn
                    font.pixelSize: Style.dp(11)
                }
                Label {
                    id: _fileLabel
                    visible: editing
                    text: "Module file  " + _hw.path
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(11)
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                    HoverHandler { id: _fileHover }
                    ToolTip.visible: _fileHover.hovered && _fileLabel.truncated
                    ToolTip.text: _hw.path
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Delete"
                    onActivated: deleteOrBreak()
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Backspace"
                    onActivated: deleteOrBreak()
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+Z"
                    onActivated: { var e = _ed(); if (e) e.undo() }
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+Shift+Z"
                    onActivated: { var e = _ed(); if (e) e.redo() }
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+Y"
                    onActivated: { var e = _ed(); if (e) e.redo() }
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+Shift+V"
                    onActivated: pastePicture()
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+L"
                    onActivated: _editorWin.runCmd("lock")
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+Shift+L"
                    onActivated: _editorWin.runCmd("unlockAll")
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+G"
                    // As Group Selected: only when it would do something.
                    onActivated: _editorWin.runCmd("group")
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+Shift+G"
                    onActivated: _editorWin.runCmd("breakGroup")
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+D"
                    onActivated: _editorWin.runEdit("edit.duplicate")
                }
                Shortcut {
                    // Edit > Cut (07 S135).
                    sequence: "Ctrl+X"
                    enabled: keyOk(editing)
                    onActivated: cutNow()
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+C"
                    onActivated: _editorWin.runEdit("edit.copy")
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+V"
                    onActivated: _editorWin.runEdit("edit.paste")
                }
                Shortcut {
                    enabled: _editorWin.keysHere
                    sequence: "Ctrl+K"
                    onActivated: _editorWin.openShortcuts()
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+F"
                    onActivated: searchLayers()
                }
                Shortcut {
                    enabled: _editorWin.keysHere
                    sequence: "F1"
                    onActivated: _editorWin.openGuide()
                }
                Shortcut {
                    enabled: _editorWin.keysHere && (editing)
                    sequence: "Ctrl+S"
                    onActivated: saveEdit()
                }
                Shortcut {
                    sequence: "Ctrl+P"
                    enabled: _editorWin.keysHere && (_editorWin.targetName.length > 0)
                    onActivated: _editorWin.openPrintExport()
                }
                Shortcut {
                    // Move to Background / Move to Foreground (07 S121).
                    sequence: "Ctrl+Shift+B"
                    enabled: _editorWin.keysHere && (editing)
                    onActivated: {
                        if (!_editorWin.typingNow())
                            _editorWin.moveSelectionToOtherPlane()
                    }
                }
                Shortcut {
                    // Background mode in and out (07 S113).
                    sequence: "Ctrl+B"
                    enabled: _editorWin.keysHere && (editing)
                    onActivated: _editorWin.toggleEditPlane()
                }
                Shortcut {
                    // Esc leaves Background mode once nothing else is
                    // going on (a selection, a drawing tool, a rename or
                    // Set Print Area take Esc first, in the editor).
                    sequence: "Esc"
                    enabled: _editorWin.keysHere && (_editorWin.bgMode && _editorWin.escLeavesBackground())
                    onActivated: _editorWin.setEditPlane("foreground")
                }
                Shortcut {
                    enabled: _editorWin.keysHere
                    sequence: "Ctrl+1"
                    onActivated: _editorWin.zoomToPage()
                }
                Shortcut {
                    enabled: _editorWin.keysHere
                    sequence: "Ctrl+2"
                    onActivated: _editorWin.zoomToSelection()
                }
                Shortcut {
                    enabled: _editorWin.keysHere
                    // As View > Reset View: in and out of Edit, and kept.
                    sequence: "Ctrl+0"
                    onActivated: _editorWin.resetViewNow()
                }
                // The menus' other keys (07 S133): each only while its menu
                // command can be used and nothing is being typed (keyOk).
                // Keys that need Shift for their sign also come as the
                // shifted sign, and a press both match runs it once.
                Shortcut {
                    sequence: "Ctrl+E"
                    enabled: keyOk(canEnterEdit)
                    onActivated: enterEdit()
                }
                Shortcut {
                    sequence: "Ctrl+H"
                    enabled: keyOk(targetName.length > 0)
                    onActivated: openHistory()
                }
                Shortcut {
                    sequence: "Ctrl+W"
                    enabled: keyOk(true)
                    onActivated: _editorWin.close()
                }
                Shortcut {
                    sequence: "Ctrl+Shift+W"
                    enabled: keyOk(editing)
                    onActivated: cancelEdit()
                }
                Shortcut {
                    sequence: "Ctrl+Shift+S"
                    enabled: keyOk(targetName.length > 0)
                    onActivated: {
                        if ((layoutNow() || []).length > 0)
                            _templateNameDlg.open()
                    }
                }
                Shortcut {
                    sequence: "Ctrl+Shift+T"
                    enabled: keyOk(targetName.length > 0)
                    onActivated: _templatesDlg.open()
                }
                Shortcut {
                    sequence: "Ctrl+3"
                    enabled: keyOk(editing && !fittedThisEdit)
                    onActivated: fitToPhotoFrame()
                }
                Shortcut {
                    sequence: "Ctrl+A"
                    enabled: keyOk(editing)
                    onActivated: _editorWin.runEdit("edit.selectAll")
                }
                Shortcut {
                    sequence: "Ctrl+M"
                    enabled: keyOk(editing)
                    onActivated: mirrorNow()
                }
                Shortcut {
                    sequence: "Ctrl+,"
                    enabled: keyOk(true)
                    onActivated: openOptions()
                }
                Shortcut {
                    sequence: "F6"
                    enabled: keyOk(editing)
                    onActivated: _chipsSide.toggle()
                }
                Shortcut {
                    sequence: "F7"
                    enabled: keyOk(editing)
                    onActivated: _layersSide.toggle()
                }
                Shortcut {
                    sequence: "F4"
                    enabled: keyOk(editing)
                    onActivated: toggleProps()
                }
                Shortcut {
                    sequences: ["Ctrl+=", "Ctrl++"]
                    enabled: keyOk(true)
                    onActivated: zoomStep(1.25)
                    onActivatedAmbiguously: zoomStep(1.25)
                }
                Shortcut {
                    sequence: "Ctrl+-"
                    enabled: keyOk(true)
                    onActivated: zoomStep(0.8)
                }
                Shortcut {
                    sequence: "Ctrl+R"
                    enabled: keyOk(true)
                    onActivated: _opts.set("rulers", _opts.values["rulers"] !== true)
                }
                Shortcut {
                    sequence: "Ctrl+;"
                    enabled: keyOk(true)
                    onActivated: setGuidesShown(!guidesOn)
                }
                Shortcut {
                    sequence: "Ctrl+'"
                    enabled: keyOk(true)
                    onActivated: setGridPref("gridOn", !gridOn)
                }
                Shortcut {
                    sequences: ["Ctrl+Shift+'", "Ctrl+\""]
                    enabled: keyOk(true)
                    onActivated: setGridPref("snapOn", !snapOn)
                    onActivatedAmbiguously: setGridPref("snapOn", !snapOn)
                }
                Shortcut {
                    sequences: ["Ctrl+Shift+;", "Ctrl+:"]
                    enabled: keyOk(true)
                    onActivated: setGridPref("snapEntOn", !snapEntOn)
                    onActivatedAmbiguously: setGridPref("snapEntOn", !snapEntOn)
                }
                Shortcut {
                    sequence: "Ctrl+I"
                    enabled: keyOk(editing)
                    onActivated: _bgPictureDialog.open()
                }
                Item { Layout.fillWidth: true; visible: !editing }
            }
        }
    }

    Rectangle {
        id: _poolGhost
        parent: _mapHost
        visible: poolDrag && editing
        z: 2000
        width: Math.max(Style.dp(36), _ghostLab.implicitWidth + Style.dp(18))
        height: Style.dp(26)
        radius: Style.dp(13)
        x: poolX - width * 0.5
        y: poolY - height * 0.5
        color: "#14532D"
        border.color: "#4ADE80"
        border.width: Style.dp(1)
        Text {
            id: _ghostLab
            anchors.centerIn: parent
            text: poolName
            color: "#BBF7D0"
            font.pixelSize: Style.dp(11)
        }
    }

    function _toHex(c) {
        var r = Math.round(c.r * 255)
        var g = Math.round(c.g * 255)
        var b = Math.round(c.b * 255)
        if (r < 0) r = 0
        if (r > 255) r = 255
        if (g < 0) g = 0
        if (g > 255) g = 255
        if (b < 0) b = 0
        if (b > 255) b = 255
        var rs = r.toString(16)
        var gs = g.toString(16)
        var bs = b.toString(16)
        if (rs.length < 2) rs = "0" + rs
        if (gs.length < 2) gs = "0" + gs
        if (bs.length < 2) bs = "0" + bs
        return "#" + rs + gs + bs
    }

    MouseArea {
        id: _eyedrop
        parent: _editorWin.contentItem
        anchors.fill: parent
        z: 1000
        visible: _editorWin.eyedropField !== ""
        cursorShape: Qt.CrossCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: (m) => {
            if (m.button === Qt.RightButton) {
                _editorWin.eyedropField = ""
                return
            }
            var p = mapToItem(null, m.x, m.y)
            _editorWin.takeEyedrop(p.x, p.y)
        }
        Keys.onEscapePressed: _editorWin.eyedropField = ""
    }

    Popup {
        id: _colorPop
        parent: _editorWin.contentItem
        width: Style.dp(248)
        height: Style.dp(400)
        modal: false
        focus: true
        // Above an open menu (the Device Mapping Editor's menu stays open while you pick).
        z: 1
        // Pinned with the pin by the title: a click outside does not close it;
        // Esc closes it (and unpins it).
        property bool pinned: false
        // Dragged by its title: it opens where it was left.
        property bool moved: false
        closePolicy: pinned ? Popup.CloseOnEscape : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)
        padding: Style.dp(10)
        property string field: "color"
        // A colour was applied while open: it goes into the recent colours.
        property bool changed: false
        property real hh: 0
        property real ss: 0
        property real vv: 0.12
        readonly property color live: Qt.hsva(hh, ss, vv, 1)
        background: Rectangle {
            color: Style.bgRaised
            border.color: Style.lineStrong
            radius: Style.dp(8)
            // Clicks, the wheel and the pointer on the picker stay on it:
            // nothing under it (the menu, the map) reacts to them.
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.AllButtons
                hoverEnabled: true
                onWheel: (w) => { w.accepted = true }
            }
        }

        // Set while hue, saturation and value are set together (opening the
        // picker, a swatch): nothing is pushed half-way.
        property bool _setting: false

        function _setHsv(c) {
            _setting = true
            hh = c.hsvHue < 0 ? 0 : c.hsvHue
            ss = c.hsvSaturation
            vv = c.hsvValue
            _setting = false
        }

        function openField(field, hex, anchorItem) {
            _colorPop.field = field
            changed = false
            // Shows the field's color; applies nothing (it is already set).
            _setHsv(Qt.color(hex && hex.length ? hex : "#18181B"))
            if (moved || (opened && pinned)) {
                // Stays where it was put.
            } else if (anchorItem && parent) {
                var p = anchorItem.mapToItem(parent, 0, anchorItem.height + 4)
                x = Math.max(8, Math.min(parent.width - width - 8, p.x - width + anchorItem.width))
                y = Math.max(8, Math.min(parent.height - height - 8, p.y))
            } else if (parent) {
                x = Math.max(8, (parent.width - width) * 0.5)
                y = Math.max(8, (parent.height - height) * 0.5)
            }
            open()
        }

        function pushLive() {
            if (!visible || _setting)
                return
            var e = _cardLoader.item ? _cardLoader.item.editorItem : null
            if (e) {
                // From hh, ss, vv themselves: the 'live' binding may not have
                // caught up yet inside these change handlers.
                var hex = _editorWin._toHex(Qt.hsva(hh, ss, vv, 1))
                if (field === "printAreaColor")
                    e.printAreaColor = hex
                else
                    e.applyFieldLive(field, hex)
                changed = true
            }
        }

        function takeHex(hex) {
            _setHsv(Qt.color(hex))
            pushLive()
        }

        onClosed: {
            if (changed && field === "printAreaColor")
                _opts.set("print-area-color", _editorWin._toHex(live))
            if (changed)
                _hw.noteColour(_editorWin._toHex(live))
            changed = false
            // Pick from Map closes it for a moment: the pin stays.
            if (!_editorWin.eyedropField.length)
                pinned = false
        }

        onHhChanged: pushLive()
        onSsChanged: pushLive()
        onVvChanged: pushLive()

        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(8)
            // Title: drag it to move the picker; the pin keeps it open.
            RowLayout {
                Layout.fillWidth: true
                Label {
                    Layout.fillWidth: true
                    text: "Pick Color"
                    color: Style.fg
                    font.bold: true
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.SizeAllCursor
                        property point _start
                        property point _origin
                        onPressed: (m) => {
                            _start = mapToItem(_colorPop.parent, m.x, m.y)
                            _origin = Qt.point(_colorPop.x, _colorPop.y)
                        }
                        onPositionChanged: (m) => {
                            if (!pressed)
                                return
                            var p = mapToItem(_colorPop.parent, m.x, m.y)
                            var pw = _colorPop.parent ? _colorPop.parent.width : 0
                            var ph = _colorPop.parent ? _colorPop.parent.height : 0
                            _colorPop.moved = true
                            _colorPop.x = Math.max(0, Math.min(pw - _colorPop.width, _origin.x + p.x - _start.x))
                            _colorPop.y = Math.max(0, Math.min(ph - _colorPop.height, _origin.y + p.y - _start.y))
                        }
                    }
                }
                Label {
                    font.family: Style.iconFont
                    font.pixelSize: Style.dp(14)
                    // pin-fill when pinned, pin-angle when not.
                    text: _colorPop.pinned ? "\uF4EC" : "\uF4EB"
                    color: _colorPop.pinned ? Style.menuAccent : (_pickPinArea.containsMouse ? Style.menuText : Style.menuTextOff)
                    MouseArea {
                        id: _pickPinArea
                        anchors.fill: parent
                        anchors.margins: -Style.dp(4)
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: _colorPop.pinned = !_colorPop.pinned
                    }
                    ToolTip.visible: _pickPinArea.containsMouse
                    ToolTip.text: _colorPop.pinned ? "Unpin: a click outside closes the picker" : "Pin: keep the picker open"
                }
            }
            Item {
                id: _sv
                Layout.fillWidth: true
                Layout.preferredHeight: Style.dp(140)
                Rectangle {
                    anchors.fill: parent
                    radius: Style.dp(4)
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: "#FFFFFF" }
                        GradientStop { position: 1; color: Qt.hsva(_colorPop.hh, 1, 1, 1) }
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: Style.dp(4)
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#00000000" }
                        GradientStop { position: 1; color: "#FF000000" }
                    }
                }
                Rectangle {
                    width: Style.dp(12)
                    height: Style.dp(12)
                    radius: Style.dp(6)
                    color: "transparent"
                    border.color: "#FFFFFF"
                    border.width: Style.dp(2)
                    x: _colorPop.ss * _sv.width - Style.dp(6)
                    y: (1 - _colorPop.vv) * _sv.height - Style.dp(6)
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: Style.dp(2)
                        radius: Style.dp(4)
                        color: "transparent"
                        border.color: "#111111"
                        border.width: Style.dp(1)
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    preventStealing: true
                    function take(mx, my) {
                        // Both together, then one push (not one half-way).
                        _colorPop._setting = true
                        _colorPop.ss = Math.max(0, Math.min(1, mx / Math.max(1, _sv.width)))
                        _colorPop.vv = Math.max(0, Math.min(1, 1 - my / Math.max(1, _sv.height)))
                        _colorPop._setting = false
                        _colorPop.pushLive()
                    }
                    onPressed: (m) => take(m.x, m.y)
                    onPositionChanged: (m) => { if (pressed) take(m.x, m.y) }
                }
            }
            Item {
                id: _hue
                Layout.fillWidth: true
                Layout.preferredHeight: Style.dp(16)
                Rectangle {
                    anchors.fill: parent
                    radius: Style.dp(4)
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: "#FF0000" }
                        GradientStop { position: 0.17; color: "#FFFF00" }
                        GradientStop { position: 0.33; color: "#00FF00" }
                        GradientStop { position: 0.50; color: "#00FFFF" }
                        GradientStop { position: 0.67; color: "#0000FF" }
                        GradientStop { position: 0.83; color: "#FF00FF" }
                        GradientStop { position: 1.0; color: "#FF0000" }
                    }
                }
                Rectangle {
                    width: Style.dp(6)
                    height: parent.height + Style.dp(4)
                    y: -Style.dp(2)
                    x: _colorPop.hh * _hue.width - Style.dp(3)
                    radius: Style.dp(2)
                    color: "transparent"
                    border.color: "#FFFFFF"
                    border.width: Style.dp(2)
                }
                MouseArea {
                    anchors.fill: parent
                    preventStealing: true
                    function take(mx) {
                        _colorPop.hh = Math.max(0, Math.min(1, mx / Math.max(1, _hue.width)))
                    }
                    onPressed: (m) => take(m.x)
                    onPositionChanged: (m) => { if (pressed) take(m.x) }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Rectangle {
                    width: Style.dp(36)
                    height: Style.dp(24)
                    radius: Style.dp(4)
                    color: _colorPop.live
                    border.color: Style.lineStrong
                }
                // The color as #RRGGBB; type one (#RGB, with or without #)
                // and press Enter.
                TextField {
                    id: _hexField
                    Layout.fillWidth: true
                    text: _editorWin._toHex(_colorPop.live)
                    font.family: Style.monoFont
                    font.pixelSize: Style.dp(13)
                    selectByMouse: true
                    validator: RegularExpressionValidator {
                        regularExpression: /#?[0-9A-Fa-f]{0,6}/
                    }
                    onAccepted: _hexField.take()
                    onEditingFinished: _hexField.take()

                    function take() {
                        var t = text.trim()
                        if (t.length && t[0] !== "#")
                            t = "#" + t
                        if (/^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(t)) {
                            if (t.length === 4)
                                t = "#" + t[1] + t[1] + t[2] + t[2] + t[3] + t[3]
                            _colorPop.takeHex(t.toUpperCase())
                        }
                        // Shows the picked color again (and follows it).
                        text = Qt.binding(() => _editorWin._toHex(_colorPop.live))
                    }
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: Style.dp(4)
                Repeater {
                    model: ["#18181B", "#3F3F46", "#E4E4E7", "#14532D", "#22C55E", "#BBF7D0", "#1D4ED8", "#7C2D12", "#831843", "#0F766E", "#FBBF24", "#000000", "#FFFFFF", "#7F1D1D"]
                    Rectangle {
                        required property string modelData
                        width: Style.dp(16)
                        height: Style.dp(16)
                        radius: Style.dp(3)
                        color: modelData
                        border.color: Style.lineStrong
                        MouseArea {
                            anchors.fill: parent
                            onClicked: _colorPop.takeHex(modelData)
                        }
                    }
                }
            }
            // The colours last applied (any device), newest first.
            Label {
                visible: _hw.recentColours.length > 0
                text: "Recent"
                color: Style.fgMuted
                font.pixelSize: Style.dp(11)
            }
            Flow {
                visible: _hw.recentColours.length > 0
                Layout.fillWidth: true
                spacing: Style.dp(4)
                Repeater {
                    model: _hw.recentColours
                    Rectangle {
                        required property string modelData
                        width: Style.dp(16)
                        height: Style.dp(16)
                        radius: Style.dp(3)
                        color: modelData
                        border.color: Style.lineStrong
                        MouseArea {
                            anchors.fill: parent
                            onClicked: _colorPop.takeHex(modelData)
                        }
                    }
                }
            }
            Button {
                text: "Pick from Map"
                Layout.fillWidth: true
                onClicked: _editorWin.startEyedropper(_colorPop.field)
            }
        }
    }
}
