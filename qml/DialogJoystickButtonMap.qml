// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import "helpers.js" as Helpers

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _buttonMap

    // ToolWindowMemory sets the saved or default size when the window opens.
    width: 1180
    height: 980
    minimumWidth: Style.dp(880)
    minimumHeight: Style.dp(720)

    color: Style.background
    U.Universal.theme: Style.theme

    title: targetName.length ? ("Button Map — " + targetName) : "Button Map"

    ToolWindowMemory {
        host: _buttonMap
        name: "button-map"
        defaultWidth: Style.dp(1180)
        defaultHeight: Style.dp(980)
    }

    onClosing: (e) => {
        if (_allowClose || !editing)
            return
        if (!isDirty())
            return
        e.accepted = false
        askLeave("close")
    }

    property string leaveKind: ""
    property string targetName: ""

    function askLeave(kind) {
        leaveKind = kind
        _saveGate.detail = "Editor changes are not saved. Leave without saving and this work will be lost."
        _saveGate.ask()
    }
    property string targetGuid: ""
    property string initialPhoto: ""
    property string loadedDevice: ""
    property string pendingDevice: ""
    property string pendingPhoto: ""
    property string pendingGuid: ""
    property bool startBlank: false
    property bool faceLive: false
    // Measured by growFileMenu() at startup and each time the menu opens.
    property int fileMenuW: 280

    TextMetrics {
        id: _menuMetric
        font.pixelSize: Style.dp(14)
    }

    function growFileMenu() {
        var labels = [
            "Edit Mapping",
            "Fit to photo frame",
            "Choose background…",
            "Export PDF…",
            "Export PNG…",
            "Export JPG…",
            "Export size",
            "Reset layout",
            "Clear image"
        ]
        var rows = []
        try {
            rows = _devices.listRows() || []
        } catch (err) {
            rows = []
        }
        var i
        for (i = 0; i < rows.length; i++)
            labels.push(String(rows[i].name || ""))
        var max = Style.dp(160)
        for (i = 0; i < labels.length; i++) {
            _menuMetric.text = labels[i]
            if (_menuMetric.advanceWidth > max)
                max = _menuMetric.advanceWidth
        }
        fileMenuW = Math.ceil(max + Style.dp(88))
    }
    property string stockImage: {
        if (/evo l|ot l/i.test(targetName))
            return "qml/images/vkb_gladiator_evo_l.jpg"
        if (/gladiator/i.test(targetName))
            return "qml/images/vkb_gladiator_rig.jpg"
        if (initialPhoto.length)
            return initialPhoto
        return "qml/images/vkb_gladiator_rig.jpg"
    }
    property int _nameTick: 0
    property bool editing: false
    // The Layers panel shows while editing; View > Layers turns it off and on.
    property bool layersOn: true
    // The Properties panel shows the selection's exact values; View > Properties.
    property bool propsOn: true
    onEditingChanged: {
        poolDrag = false
        if (editing)
            Qt.callLater(refreshReservoir)
    }
    property var liveNodes
    property var workNodes
    property string photoOverride: ""
    property string storedImage: ""
    property string liveImage: ""
    property bool fittedOldPage: false
    property bool fittedThisEdit: false
    property real viewPctSave: 1
    property real viewPanX: 0
    property real viewPanY: 0
    property real photoScale: 1
    property real photoOffX: 0
    property real photoOffY: 0
    property real photoRot: 0
    // The photo's Layers panel flags as loaded; the editor keeps the live ones.
    property bool photoHidden: false
    property bool photoLocked: false
    property bool movePhoto: false
    property var livePhoto
    property var workPhoto
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
    property real panelW: 0
    property real panelH: 0
    property bool panelFillW: true
    property bool panelDockB: true
    property real _prsX: 0
    property real _prsY: 0
    property real _prsW: 0
    property real _prsH: 0
    property real _prmX: 0
    property real _prmY: 0
    property string _prEdge: ""
    property bool saveOk: true

    function clampPool() {
        var box = _poolFloat
        if (!box || !box.parent)
            return
        var pw = box.parent.width
        var ph = box.parent.height
        if (panelFillW || box.width < Style.dp(40)) {
            box.x = Style.dp(12)
            box.width = Math.max(Style.dp(280), pw - Style.dp(24))
        }
        box.width = Math.max(Style.dp(280), Math.min(box.width, pw - Style.dp(16)))
        box.height = Math.max(Style.dp(90), Math.min(panelH, ph - Style.dp(16)))
        panelH = box.height
        if (panelDockB)
            box.y = ph - box.height - Style.dp(12)
        box.x = Math.max(Style.dp(8), Math.min(box.x, pw - box.width - Style.dp(8)))
        box.y = Math.max(Style.dp(8), Math.min(box.y, ph - box.height - Style.dp(8)))
    }

    function startPanelResize(edge, mx, my, item) {
        _prEdge = edge
        _prsX = _poolFloat.x
        _prsY = _poolFloat.y
        _prsW = _poolFloat.width
        _prsH = _poolFloat.height
        var p = item.mapToItem(_poolFloat.parent, mx, my)
        _prmX = p.x
        _prmY = p.y
    }

    function movePanelResize(mx, my, item) {
        var p = item.mapToItem(_poolFloat.parent, mx, my)
        var dx = p.x - _prmX
        var dy = p.y - _prmY
        var nx = _prsX
        var ny = _prsY
        var nw = _prsW
        var nh = _prsH
        var e = _prEdge
        var host = _poolFloat.parent
        if (e.indexOf("e") >= 0) {
            nw = _prsW + dx
            panelFillW = false
        }
        if (e.indexOf("w") >= 0) {
            nw = _prsW - dx
            panelFillW = false
        }
        if (e.indexOf("s") >= 0) {
            nh = _prsH + dy
            panelDockB = false
        }
        if (e.indexOf("n") >= 0)
            nh = _prsH - dy
        var maxW = Math.max(Style.dp(280), host.width - Style.dp(16))
        var maxH = Math.max(Style.dp(90), host.height - Style.dp(16))
        nw = Math.max(Style.dp(280), Math.min(nw, maxW))
        nh = Math.max(Style.dp(90), Math.min(nh, maxH))
        if (e.indexOf("w") >= 0)
            nx = _prsX + _prsW - nw
        if (e.indexOf("n") >= 0)
            ny = _prsY + _prsH - nh
        nx = Math.max(Style.dp(8), Math.min(nx, host.width - nw - Style.dp(8)))
        ny = Math.max(Style.dp(8), Math.min(ny, host.height - nh - Style.dp(8)))
        _poolFloat.x = nx
        _poolFloat.y = ny
        _poolFloat.width = nw
        _poolFloat.height = nh
        panelH = nh
        panelW = nw
    }

    ViewerDeviceModel { id: _devices }
    HardwareProfile { id: _hw }
    ButtonMapOptions {
        id: _opts
        onChanged: _buttonMap.applyOptionsToEditor()
    }

    Instantiator {
        id: _inputDeviceItems
        model: _devices
        delegate: MenuItem {
            required property string name
            required property string guid
            text: name
            enabled: !_buttonMap.editing
            checkable: true
            checked: name === _buttonMap.targetName
            onTriggered: _buttonMap.openForDevice(name, "", guid)
        }
        onObjectAdded: function(index, object) {
            _fileMenu.insertItem(4 + index, object)
            growFileMenu()
        }
        onObjectRemoved: function(index, object) {
            _fileMenu.removeItem(object)
        }
    }

    DeviceNames {
        id: _names
        onChanged: _buttonMap._nameTick++
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

    function targetListed() {
        var rows = []
        try {
            rows = _devices.listRows() || []
        } catch (err) {
            return false
        }
        var i
        for (i = 0; i < rows.length; i++) {
            if (isTarget(rows[i].guid, rows[i].name))
                return true
        }
        return false
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
        var i
        for (i = 0; i < list.length; i++) {
            var n = list[i]
            if (n && n.shape === "image" && n.src)
                n.srcUrl = _hw.imageUrl(n.src)
        }
    }

    function applyImage(rel) {
        storedImage = rel && rel.length ? rel : stockImage
        photoOverride = _hw.imageUrl(storedImage)
    }

    function sceneShiftList(list) {
        if (!list)
            return
        function pos(v) { return Math.max(0, Math.min(1, 0.25 + (v || 0) * 0.5)) }
        function sz(v) { return (v || 0) * 0.5 }
        function mapEnd(e) {
            if (e && e.type === "free") {
                e.fx = pos(e.fx)
                e.fy = pos(e.fy)
            }
        }
        function mapSpines(arr) {
            if (!arr)
                return
            var s
            for (s = 0; s < arr.length; s++) {
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


    function remapPhotoWellList(list) {
        if (!list)
            return
        function pos(v) { return Math.max(0, Math.min(1, 0.125 + ((v || 0) - 0.25) * 1.5)) }
        function sz(v) { return (v || 0) * 1.5 }
        function mapEnd(e) {
            if (e && e.type === "free") {
                e.fx = pos(e.fx)
                e.fy = pos(e.fy)
            }
        }
        function mapSpines(arr) {
            if (!arr)
                return
            var s
            for (s = 0; s < arr.length; s++) {
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

    function loadLive() {
        if (_hw.setDeviceGuid)
            _hw.setDeviceGuid(targetGuid)
        var text = _hw.load(targetName)
        var doc = parseDoc(text)
        if (!doc || !doc.nodes) {
            return false
        }
        liveNodes = JSON.parse(JSON.stringify(doc.nodes))
        hydrateOverlays(liveNodes)
        liveImage = doc.image && doc.image.length ? doc.image : stockImage
        if (doc.ui)
            applyUi(doc.ui)
        applyImage(liveImage)
        livePhoto = photoFromDoc(doc.photo)
        applyPhoto(livePhoto)
        var well = Number(doc.photoWell || 0)
        if (well < 0.74) {
            remapPhotoWellList(liveNodes)
            doc.nodes = liveNodes
            doc.photoWell = 0.75
            try { _hw.save(targetName, JSON.stringify(doc)) } catch (err) {}
        }
        applyGridToEditor()
        applyViewToFace()
        applyPhotoToEditor()
        return true
    }

    function enterEdit() {
        if (editing)
            return
        try {
            loadLive()
        } catch (e) {
            console.warn("Button Map loadLive failed", e)
        }
        var src = []
        try {
            src = JSON.parse(JSON.stringify(liveNodes || []))
        } catch (e2) {
            console.warn("Button Map clone nodes failed", e2)
            src = []
        }
        workNodes = src
        hydrateOverlays(workNodes)
        workPhoto = photoFromDoc(livePhoto)
        applyPhoto(workPhoto)
        applyImage(liveImage.length ? liveImage : stockImage)
        editing = true
        fittedThisEdit = false
        selectedId = ""
        selectedNode = null
        Qt.callLater(function() {
            refreshReservoir()
            clampPool()
            applyGridToEditor()
            hydrateOverlays((_ed() && _ed().nodes) ? _ed().nodes : workNodes)
        })
    }

    function saveEdit(report) {
        if (report === undefined)
            report = true
        var ed = _cardLoader.item ? _cardLoader.item.editorItem : null
        var nodes = []
        if (ed && ed.nodes)
            nodes = ed.nodes
        else if (workNodes)
            nodes = workNodes
        var image = storedImage.length ? storedImage : stockImage
        var doc = {
            kind: "control.hardware",
            device: targetName,
            space: "world",
            page: 32000,
            pageW: 32000,
            pageH: 18000,
            photoWell: 0.75,
            image: image,
            imageWidth: 1348,
            imageHeight: 1380,
            photo: photoBag(),
            ui: uiBag(),
            nodes: nodes
        }
        var payload = JSON.stringify(doc)
        if (!_hw.save(targetName, payload)) {
            saveOk = false
            if (report) {
                _saveGate.announce(false, "Not written. It is still only on this screen.")
                if (backend)
                    backend.noteSave("The module file was not written.")
            }
            return false
        }
        var check = parseDoc(_hw.load(targetName))
        if (!check || !check.nodes) {
            saveOk = false
            if (report) {
                _saveGate.announce(false, "Saved to the module file, but it could not be read back.")
                if (backend)
                    backend.noteSave("Saved the module file to " + _hw.path + ", but it could not be read back.")
            }
            return false
        }
        liveNodes = JSON.parse(JSON.stringify(nodes))
        liveImage = image
        livePhoto = photoBag()
        clearRecovery()
        applyImage(liveImage)
        hydrateOverlays(liveNodes)
        saveOk = true
        if (report) {
            _saveGate.announce(true, "Saved to the module file.")
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

    function isDirty() {
        if (!editing)
            return false
        var image = storedImage.length ? storedImage : stockImage
        var live = liveImage.length ? liveImage : stockImage
        try {
            return JSON.stringify({ image: image, photo: photoBag(), nodes: editorNodesNow() }) !== JSON.stringify({ image: live, photo: livePhoto || photoFromDoc(null), nodes: liveNodes })
        } catch (e) {
            return true
        }
    }

    // --- recovery copies (Options → Button Map → Autosave) -------------------

    property string _lastRecovery: ""
    property var _pendingRecovery: null

    function recoveryPayload() {
        return JSON.stringify({
            image: storedImage.length ? storedImage : stockImage,
            photo: photoBag(),
            nodes: editorNodesNow()
        })
    }

    // Writes a recovery copy when there are unsaved changes; with none left
    // (everything undone), removes it.
    function autosaveNow() {
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

    // After a device opens: offer unsaved edits a crash left behind.
    function offerRecovery() {
        if (editing || !targetName.length)
            return
        var text = _hw.loadRecovery(targetName)
        if (!text.length)
            return
        var doc = null
        try { doc = JSON.parse(text) } catch (e) { doc = null }
        if (!doc || !doc.nodes)
            return
        var live = { image: liveImage.length ? liveImage : stockImage, photo: livePhoto || photoFromDoc(null), nodes: liveNodes }
        var same = false
        try {
            same = JSON.stringify({ image: doc.image, photo: doc.photo, nodes: doc.nodes }) === JSON.stringify(live)
        } catch (e2) {}
        if (same) {
            _hw.clearRecovery(targetName)
            return
        }
        _pendingRecovery = doc
        var when = String(doc.savedAt || "").replace("T", " at ")
        _recoverGate.choose("Unsaved edits found",
                            "Button Map has edits to " + targetName + (when.length ? " from " + when : "")
                            + " that were never saved, probably because the program closed unexpectedly.

"
                            + "Restore opens them for editing; save to keep them. Discard deletes them.",
                            "Restore", "Discard")
        _recoverGate.cancelText = "Not now"
    }

    function restoreRecovery() {
        var doc = _pendingRecovery
        _pendingRecovery = null
        if (!doc)
            return
        enterEdit()
        var nodes = JSON.parse(JSON.stringify(doc.nodes || []))
        hydrateOverlays(nodes)
        workNodes = nodes
        if (doc.image && String(doc.image).length)
            applyImage(String(doc.image))
        workPhoto = photoFromDoc(doc.photo)
        applyPhoto(workPhoto)
        Qt.callLater(function() {
            applyPhotoToEditor()
            var e = _ed()
            if (e && e.seedHist)
                e.seedHist()
            refreshReservoir()
        })
    }

    Timer {
        id: _autosaveTimer
        interval: Math.max(10, Number(_opts.values["autosave-seconds"]) || 60) * 1000
        repeat: true
        running: _buttonMap.editing && _opts.values["autosave"] !== false
        onTriggered: _buttonMap.autosaveNow()
    }

    function discardEdit() {
        clearRecovery()
        editing = false
        workNodes = []
        selectedId = ""
        selectedNode = null
        applyImage(liveImage)
        applyPhoto(livePhoto)
        movePhoto = false
        applyPhotoToEditor()
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
            _allowClose = true
            close()
            Qt.quit()
            return
        }
        askLeave("appquit")
    }

    function confirmLeaveSave() {
        saveEdit()
        if (!saveOk)
            return
        if (leaveKind === "close") {
            editing = false
            _allowClose = true
            close()
        } else if (leaveKind === "switch") {
            finishSwitch(pendingDevice)
        } else if (leaveKind === "blank") {
            clearToBlank()
        } else if (leaveKind === "appquit") {
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

    function showBlank(photo) {
        liveNodes = []
        workNodes = []
        var img = String(photo || "")
        liveImage = img
        storedImage = img
        photoOverride = img.length ? _hw.imageUrl(img) : ""
    }

    function clearToBlank() {
        discardEdit()
        faceLive = false
        targetName = ""
        loadedDevice = ""
        initialPhoto = ""
        pendingPhoto = ""
        pendingDevice = ""
        showBlank("")
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
        discardEdit()
        initialPhoto = pendingPhoto.length ? pendingPhoto : initialPhoto
        targetName = name
        targetGuid = pendingGuid
        loadedDevice = name
        if (!loadLive())
            showBlank(initialPhoto)
        pendingDevice = ""
        Qt.callLater(offerRecovery)
    }

    function openForDevice(name, photo, guid) {
        var next = String(name || "")
        pendingPhoto = String(photo || "")
        pendingGuid = String(guid || "")
        if (!next.length)
            return
        if (next === loadedDevice && sameGuid(pendingGuid, targetGuid) && _hasTarget.hit) {
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
        panelH = Style.dp(160)
        liveNodes = []
        workNodes = []
        resItems = []
        if (_devices)
            _devices.reload()
        growFileMenu()
        if (startBlank || !targetName.length) {
            targetName = ""
            loadedDevice = ""
            initialPhoto = ""
            showBlank("")
            return
        }
        loadedDevice = targetName
        if (!loadLive())
            showBlank(initialPhoto)
        Qt.callLater(offerRecovery)
    }

    DismissibleDialog {
        id: _recoverGate
        onConfirmed: _buttonMap.restoreRecovery()
        onDiscarded: {
            _buttonMap._pendingRecovery = null
            _buttonMap.clearRecovery()
        }
        onCancelled: _buttonMap._pendingRecovery = null
    }

    DismissibleDialog {
        id: _saveGate
        onSaveChosen: _buttonMap.confirmLeaveSave()
        onDiscardChosen: _buttonMap.confirmLeaveDiscard()
        onCancelled: _buttonMap.pendingDevice = ""
    }

    Dialog {
        id: _resetDlg
        title: "Reset layout"
        modal: true
        anchors.centerIn: parent
        width: Style.dp(460)
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(12)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.warn
                text: "Clear every chip, leader, and hotspot from the map?"
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: "Joystick mappings are not changed. Pressed buttons still light in the reservoir. Save after reset if you want the empty layout to become the live map."
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    text: "Keep map"
                    onClicked: _resetDlg.close()
                }
                Button {
                    text: "Reset layout"
                    highlighted: true
                    onClicked: {
                        _buttonMap.resetLayout()
                        _resetDlg.close()
                    }
                }
            }
        }
        onRejected: close()
    }

    // The program's User Guide window, at a section ("" for where it was).
    function openGuide(section) {
        var w = Helpers.createComponent("DialogHelp.qml")
        if (w && section)
            w.showSection(section)
    }

    function _ed() {
        return _cardLoader.item ? _cardLoader.item.editorItem : null
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
        ed.addChiplet(kind, hw, local.x, local.y)
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

    function deleteOrBreak() {
        var e = _ed()
        if (!e)
            return
        var n = e.nodeAt(e.selectedId)
        if (nodeIsGroup(n) || e.isGroup(n))
            e.ungroupSelection()
        else
            e.deleteChip()
        applySelected()
        refreshReservoir()
    }

    function nodeIsGroup(n) {
        return !!(n && (n.kind === "plus" || n.kind === "pair" || n.kind === "axis_stack" || n.kind === "stack" || (n.members && n.members.length)))
    }

    function captureView() {
        var f = _cardLoader.item
        if (!f)
            return
        viewPctSave = f.viewPct || 1
        viewPanX = f.panX || 0
        viewPanY = f.panY || 0
    }

    function photoFromDoc(p) {
        p = p || {}
        var s = Number(p.scale)
        if (!(s === s) || s <= 0)
            s = 1
        var ox = Number(p.offX)
        var oy = Number(p.offY)
        var r = Number(p.rot)
        if (!(ox === ox)) ox = 0
        if (!(oy === oy)) oy = 0
        if (!(r === r)) r = 0
        var pose = {
            scale: Math.max(0.25, Math.min(4, s)),
            offX: Math.max(-1, Math.min(1, ox)),
            offY: Math.max(-1, Math.min(1, oy)),
            rot: r
        }
        // Layers panel flags, kept only when on (as the editor saves them).
        if (p.hidden === true)
            pose.hidden = true
        if (p.locked === true)
            pose.locked = true
        return pose
    }

    function photoBag() {
        var e = _ed()
        if (e && e.photoBag)
            return e.photoBag()
        return photoFromDoc({
            scale: photoScale,
            offX: photoOffX,
            offY: photoOffY,
            rot: photoRot,
            hidden: photoHidden,
            locked: photoLocked
        })
    }

    function applyPhoto(p) {
        p = photoFromDoc(p)
        photoScale = p.scale
        photoOffX = p.offX
        photoOffY = p.offY
        photoRot = p.rot
        photoHidden = !!p.hidden
        photoLocked = !!p.locked
        applyPhotoToEditor()
        var e = _ed()
        if (faceLive && e && e.applyPhotoPose)
            e.applyPhotoPose({ scale: photoScale, offX: photoOffX, offY: photoOffY, rot: photoRot,
                               hidden: photoHidden, locked: photoLocked })
    }

    function applyPhotoToEditor() {
        if (!faceLive)
            return
        var e = _ed()
        if (!e)
            return
        if (e.applyPhotoPose)
            e.applyPhotoPose({
                scale: photoScale,
                offX: photoOffX,
                offY: photoOffY,
                rot: photoRot
            })
        else {
            e.photoScale = photoScale
            e.photoOffX = photoOffX
            e.photoOffY = photoOffY
            e.photoRot = photoRot
        }
        e.movePhoto = movePhoto && editing
        if (e.repaint)
            e.repaint()
    }

    function setPhotoScale(v) {
        photoScale = photoFromDoc({ scale: v }).scale
        applyPhotoToEditor()
        notePhotoChange()
    }

    function setPhotoOff(x, y) {
        var p = photoFromDoc({ offX: x, offY: y })
        photoOffX = p.offX
        photoOffY = p.offY
        applyPhotoToEditor()
        notePhotoChange()
    }

    function setPhotoRot(v) {
        var r = Number(v)
        if (!(r === r))
            r = 0
        photoRot = r
        applyPhotoToEditor()
        notePhotoChange()
    }

    // The pose returns to the frame; hidden and locked stay as they are.
    function resetPhoto() {
        var e = _ed()
        applyPhoto({ scale: 1, offX: 0, offY: 0, rot: 0,
                     hidden: e ? e.photoHidden : photoHidden, locked: e ? e.photoLocked : photoLocked })
        movePhoto = false
        applyPhotoToEditor()
        notePhotoChange()
    }

    // An undo step for a photo change, while editing.
    function notePhotoChange() {
        var e = _ed()
        if (editing && e && e.notePhotoChange)
            e.notePhotoChange()
    }

    // Undo or redo moved the photo in the editor: the sliders follow.
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
        var hex = _hw.colorAt(_buttonMap, wx, wy)
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
        var rel = _hw.pasteClipboardImage(targetName)
        if (rel.length)
            e.addOverlay(rel, _hw.imageUrl(rel))
    }

    function syncPhotoFromEditor() {
        var e = _ed()
        if (!e)
            return
        photoScale = e.photoScale
        photoOffX = e.photoOffX
        photoOffY = e.photoOffY
        photoRot = e.photoRot
    }

    function fitPhotoWell() {
        photoScale = 1
        applyPhotoToEditor()
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
            panY: viewPanY
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
        if (ui.gridSize >= 4)
            gridSize = ui.gridSize
        if (ui.viewPct > 0)
            viewPctSave = ui.viewPct
        if (ui.panX === ui.panX)
            viewPanX = ui.panX
        if (ui.panY === ui.panY)
            viewPanY = ui.panY
    }

    // Editor settings from Options (Edit → Editor options).
    function applyOptionsToEditor() {
        var e = _cardLoader.item ? _cardLoader.item.editorItem : null
        if (!e)
            return
        var o = _opts.values
        if (o["undo-steps"] > 0)
            e.histCap = o["undo-steps"]
        if (o["rotate-snap"] > 0)
            e.rotateSnap = o["rotate-snap"]
        e.findOn = o["press-to-find"] !== false
        e.findAxes = o["find-axes"] === true
    }

    function openEditorOptions() {
        var w = Helpers.createComponent("DialogOptions.qml", { initialSection: "Button Map" })
        if (w)
            w.showSection("Button Map")
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
        applyOptionsToEditor()
        if (e.repaint)
            e.repaint()
        applyViewToFace()
        applyPhotoToEditor()
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
        })
    }


    function fitToPhotoFrame() {
        if (fittedThisEdit)
            return
        var e = _ed()
        sceneShiftList(editing ? workNodes : liveNodes)
        fittedThisEdit = true
        if (e && e.repaint)
            e.repaint()
    }

    function persistUi() {
        var text = _hw.load(targetName)
        var doc = parseDoc(text)
        if (!doc) {
            doc = {
                kind: "control.hardware",
                device: targetName,
                image: liveImage.length ? liveImage : stockImage,
                nodes: liveNodes || []
            }
        }
        doc.ui = uiBag()
        if (_hw.saveUi)
            _hw.saveUi(targetName, JSON.stringify(doc))
        else
            _hw.save(targetName, JSON.stringify(doc))
    }

    function setGridPref(key, val) {
        if (key === "gridOn") gridOn = val
        else if (key === "snapOn") snapOn = val
        else if (key === "snapEntOn") snapEntOn = val
        else if (key === "gridSize") gridSize = val
        applyGridToEditor()
        persistUi()
    }

    function openChipMenu(x, y) {
        applySelected()
    }

    Menu {
        id: _groupMenu
        MenuItem { text: "Group selected"; onTriggered: { var e = _ed(); if (e) e.groupSelection() } }
        MenuItem {
            text: "Break group"
            enabled: { var e = _ed(); return !!(e && e.canUngroup()) }
            onTriggered: { var e = _ed(); if (e) e.ungroupSelection() }
        }
        MenuSeparator {}
        MenuItem { text: "Edit group"; onTriggered: { var e = _ed(); if (e) e.beginGroupEdit(e.selectedId) } }
        MenuItem { text: "Done editing group"; onTriggered: { var e = _ed(); if (e) e.endGroupEdit() } }
        MenuSeparator {}
        Menu {
            title: "Apply Format"
            enabled: {
                var e = _ed()
                return !!(e && e.isFiveWay(e.nodeAt(e.selectedId)))
            }
            Menu {
                title: "5-Way"
                MenuItem {
                    text: "Plus cluster"
                    checkable: true
                    checked: { var e = _ed(); return !!(e && e.fiveWayFormat(e.nodeAt(e.selectedId)) === "plus") }
                    onTriggered: { var e = _ed(); if (e) e.applyFiveWayFormat("plus") }
                }
                MenuItem {
                    text: "Mini hat"
                    checkable: true
                    checked: { var e = _ed(); return !!(e && e.fiveWayFormat(e.nodeAt(e.selectedId)) === "mini") }
                    onTriggered: { var e = _ed(); if (e) e.applyFiveWayFormat("mini") }
                }
                MenuItem {
                    text: "Named card"
                    checkable: true
                    checked: { var e = _ed(); return !!(e && e.fiveWayFormat(e.nodeAt(e.selectedId)) === "card") }
                    onTriggered: { var e = _ed(); if (e) e.applyFiveWayFormat("card") }
                }
                MenuItem {
                    text: "Radial leaders"
                    checkable: true
                    checked: { var e = _ed(); return !!(e && e.fiveWayFormat(e.nodeAt(e.selectedId)) === "radial") }
                    onTriggered: { var e = _ed(); if (e) e.applyFiveWayFormat("radial") }
                }
            }
        }
        MenuSeparator {}
        MenuItem { text: "Align left"; onTriggered: { var e = _ed(); if (e) e.setAlignH("left") } }
        MenuItem { text: "Align center"; onTriggered: { var e = _ed(); if (e) e.setAlignH("center") } }
        MenuItem { text: "Align right"; onTriggered: { var e = _ed(); if (e) e.setAlignH("right") } }
        MenuItem { text: "Free layout"; onTriggered: { var e = _ed(); if (e) e.setAlignH("free") } }
    }

    Menu {
        id: _leadMenu
        MenuItem { text: "Add straight spine"; onTriggered: { var e = _ed(); if (e && selectedNode) { e.ensureMidSpine(selectedNode); e.bump() } } }
        MenuItem { text: "Add curved spine"; onTriggered: { var e = _ed(); if (e && selectedNode) e.addCurveSpine(selectedNode) } }
        MenuItem { text: "This segment curved"; onTriggered: { var e = _ed(); if (e) e.setSegCurve(e.currentLeader(e.nodeAt(e.selectedId)), Math.max(0, e.selectedSeg), true) } }
        MenuItem { text: "This segment straight"; onTriggered: { var e = _ed(); if (e) e.setSegCurve(e.currentLeader(e.nodeAt(e.selectedId)), Math.max(0, e.selectedSeg), false) } }
        MenuItem { text: "All segments curved"; onTriggered: { var e = _ed(); if (e) e.setAllSegCurve(true) } }
        MenuItem { text: "All segments straight"; onTriggered: { var e = _ed(); if (e) e.setAllSegCurve(false) } }
        MenuSeparator {}
        MenuItem { text: "Add leader (same chip / hotspot)"; onTriggered: { var e = _ed(); if (e) e.addLeader() } }
        MenuItem { text: "Branch from this end"; onTriggered: { var e = _ed(); if (e) e.addBranch() } }
        MenuItem { text: "Delete leader"; onTriggered: { var e = _ed(); if (e) e.deleteLeader() } }
        MenuSeparator {}
        MenuItem { text: "Detach chip end"; onTriggered: { var e = _ed(); if (e) e.detachEnd("from") } }
        MenuItem { text: "Detach hotspot end"; onTriggered: { var e = _ed(); if (e) e.detachEnd("to") } }
        MenuItem { text: "Reconnect to this chip"; onTriggered: { var e = _ed(); if (e) e.attachEndToSelf("from") } }
        MenuItem { text: "Reconnect to this hotspot"; onTriggered: { var e = _ed(); if (e) e.attachEndToSelf("to") } }
        MenuItem { text: "Delete selected spine"; onTriggered: { var e = _ed(); if (e) e.deleteSelection() } }
    }


    FileDialog {
        id: _imageDialog
        title: "Choose background image"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Images (*.jpg *.jpeg *.png *.webp *.bmp)"]
        currentFolder: _hw.imagesFolderUrl()
        onAccepted: {
            var rel = _hw.copyImage(selectedFile, targetName)
            if (rel.length) {
                applyImage(rel)
                resetPhoto()
            }
        }
    }

    FileDialog {
        id: _overlayDialog
        title: "Import overlay image"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.bmp)"]
        currentFolder: _hw.imagesFolderUrl()
        onAccepted: {
            var rel = _hw.copyOverlay(selectedFile, targetName)
            var e = _ed()
            if (rel.length && e)
                e.addOverlay(rel, _hw.imageUrl(rel))
        }
    }

    // Export size: the page is drawn this many times larger than on screen.
    readonly property int exportScale: {
        var t = String(_opts.values["export-size"] || "2x")
        return t.charAt(0) === "1" ? 1 : (t.charAt(0) === "3" ? 3 : 2)
    }
    property var _exportJob: null

    // Saves the whole page, whatever the zoom, without selection rings,
    // handles, guides or the grid; hidden items are left out as always.
    function exportViewTo(url, format) {
        var e = _ed()
        if (!e)
            return
        _exportJob = { url: url, format: format }
        e.exporting = true
        // Let the editor redraw without its editing marks first.
        _exportTimer.restart()
    }

    function _grabExport() {
        var e = _ed()
        var job = _exportJob
        _exportJob = null
        if (!e || !job) {
            if (e)
                e.exporting = false
            return
        }
        var f = Math.max(1, exportScale)
        var r = e.spaceRect()
        var bg = String(Style.background)
        var ok = e.grabToImage(function(result) {
            e.exporting = false
            if (!result)
                return
            if (!_hw.savePageImage(result.image, r.x * f, r.y * f, r.w * f, r.h * f,
                                   String(job.url), job.format, bg, f))
                console.warn("Button Map export failed: " + job.url)
        }, Qt.size(Math.round(e.width * f), Math.round(e.height * f)))
        if (!ok)
            e.exporting = false
    }

    Timer {
        id: _exportTimer
        interval: 50
        onTriggered: _buttonMap._grabExport()
    }

    FileDialog {
        id: _exportPngDialog
        title: "Export PNG"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "png"
        nameFilters: ["PNG image (*.png)"]
        onAccepted: exportViewTo(selectedFile, "png")
    }
    FileDialog {
        id: _exportJpgDialog
        title: "Export JPG"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "jpg"
        nameFilters: ["JPEG image (*.jpg *.jpeg)"]
        onAccepted: exportViewTo(selectedFile, "jpg")
    }
    FileDialog {
        id: _exportPdfDialog
        title: "Export PDF"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "pdf"
        nameFilters: ["PDF (*.pdf)"]
        onAccepted: exportViewTo(selectedFile, "pdf")
    }

    Popup {
        id: _photoAdj
        modal: false
        focus: true
        x: Math.round((_buttonMap.width - width) / 2)
        y: Style.dp(52)
        width: Style.dp(360)
        implicitHeight: Style.dp(430)
        padding: Style.dp(12)
        background: Rectangle {
            color: Style.bgCard
            border.color: Style.line
            radius: Style.dp(4)
        }
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(8)
            Label { text: "Photo"; color: Style.fg; font.pixelSize: Style.dp(13) }
            Label { text: "Size  " + Math.round(photoScale * 100) + "%"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
            Slider {
                Layout.fillWidth: true
                from: 0.25
                to: 4
                stepSize: 0.01
                value: photoScale
                onMoved: _buttonMap.setPhotoScale(value)
            }
            Label { text: "Offset X  " + photoOffX.toFixed(3); color: Style.fgMuted; font.pixelSize: Style.dp(11) }
            Slider {
                Layout.fillWidth: true
                from: -0.5
                to: 0.5
                stepSize: 0.001
                value: photoOffX
                onMoved: _buttonMap.setPhotoOff(value, photoOffY)
            }
            Label { text: "Offset Y  " + photoOffY.toFixed(3); color: Style.fgMuted; font.pixelSize: Style.dp(11) }
            Slider {
                Layout.fillWidth: true
                from: -0.5
                to: 0.5
                stepSize: 0.001
                value: photoOffY
                onMoved: _buttonMap.setPhotoOff(photoOffX, value)
            }
            Label { text: "Rotate  " + Math.round(photoRot) + "°"; color: Style.fgMuted; font.pixelSize: Style.dp(11) }
            Slider {
                Layout.fillWidth: true
                from: -180
                to: 180
                stepSize: 1
                value: photoRot
                onMoved: _buttonMap.setPhotoRot(value)
            }
            RowLayout {
                Layout.fillWidth: true
                Button { text: "Size 100%"; onClicked: _buttonMap.fitPhotoWell() }
                Button { text: "Reset photo"; onClicked: _buttonMap.resetPhoto() }
                Item { Layout.fillWidth: true }
                Button { text: "Close"; onClicked: _photoAdj.close() }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.bottomMargin: Style.dp(78)
        spacing: 0

        MenuBar {
            Layout.fillWidth: true
            Menu {
                id: _fileMenu
                title: "File"
                width: _buttonMap.fileMenuW
                implicitWidth: _buttonMap.fileMenuW
                onAboutToShow: _buttonMap.growFileMenu()
                MenuItem {
                    text: "Edit Mapping"
                    enabled: !_buttonMap.editing
                    onTriggered: _buttonMap.enterEdit()
                }
                MenuItem { text: "Save"; enabled: _buttonMap.editing; onTriggered: _buttonMap.saveEdit() }
                MenuItem { text: "Cancel"; enabled: _buttonMap.editing; onTriggered: _buttonMap.cancelEdit() }
                MenuSeparator {}
                MenuItem { text: "Reset layout"; enabled: editing; onTriggered: _resetDlg.open() }
                MenuItem {
                    text: "Fit to photo frame"
                    enabled: editing && !fittedThisEdit
                    onTriggered: fitToPhotoFrame()
                }
                MenuSeparator {}
                MenuItem { text: "Choose background…"; enabled: editing; onTriggered: _imageDialog.open() }
                MenuItem {
                    text: "Clear image"
                    enabled: editing
                    onTriggered: {
                        _hw.clearImage(targetName)
                        applyImage(stockImage)
                        resetPhoto()
                    }
                }
                MenuSeparator {}
                MenuItem {
                    text: "Export PDF…"
                    onTriggered: _exportPdfDialog.open()
                }
                MenuItem {
                    text: "Export PNG…"
                    onTriggered: _exportPngDialog.open()
                }
                MenuItem {
                    text: "Export JPG…"
                    onTriggered: _exportJpgDialog.open()
                }
                Menu {
                    title: "Export size"
                    Repeater {
                        model: [1, 2, 3]
                        MenuItem {
                            required property int modelData
                            text: modelData + "×"
                            checkable: true
                            checked: _buttonMap.exportScale === modelData
                            onTriggered: _opts.set("export-size", modelData + "x")
                        }
                    }
                }
                MenuSeparator {}
                MenuItem {
                    text: "Close"
                    onTriggered: _buttonMap.close()
                }
            }
            Menu {
                title: "Edit"
                MenuItem {
                    text: "Undo"
                    enabled: { var e = _ed(); return e ? e.canUndo : false }
                    onTriggered: { var e = _ed(); if (e) e.undo() }
                }
                MenuItem {
                    text: "Redo"
                    enabled: { var e = _ed(); return e ? e.canRedo : false }
                    onTriggered: { var e = _ed(); if (e) e.redo() }
                }
                MenuSeparator {}
                MenuItem {
                    text: "Duplicate"
                    enabled: { var e = _ed(); return e && e.selectedId !== "" }
                    onTriggered: { var e = _ed(); if (e) e.duplicateSelection() }
                }
                MenuItem {
                    text: "Copy"
                    enabled: { var e = _ed(); return e && e.selectedId !== "" }
                    onTriggered: { var e = _ed(); if (e) e.copySelection() }
                }
                MenuItem {
                    text: "Paste"
                    enabled: { var e = _ed(); return e && e.clip && e.clip.length }
                    onTriggered: { var e = _ed(); if (e) e.pasteClipboard() }
                }
                MenuItem {
                    text: "Paste picture"
                    enabled: editing && _hw.clipboardHasImage
                    onTriggered: pastePicture()
                }
                MenuSeparator {}
                MenuItem {
                    text: "Editor options…"
                    onTriggered: _buttonMap.openEditorOptions()
                }
            }
            Menu {
                title: "View"
                MenuItem {
                    text: "Layers"
                    checkable: true
                    checked: layersOn
                    onTriggered: layersOn = !layersOn
                }
                MenuItem {
                    text: "Properties"
                    checkable: true
                    checked: propsOn
                    onTriggered: propsOn = !propsOn
                }
                MenuItem {
                    text: "Reset view (View 100%)"
                    onTriggered: {
                        var f = _cardLoader.item
                        if (f && f.resetView)
                            f.resetView()
                        captureView()
                        persistUi()
                    }
                }
                MenuSeparator {}
                Menu {
                    title: "Grid"
                    MenuItem {
                        text: "Show grid"
                        checkable: true
                        checked: _buttonMap.gridOn
                        onTriggered: _buttonMap.setGridPref("gridOn", checked)
                    }
                    MenuItem {
                        text: "Snap to grid"
                        checkable: true
                        checked: _buttonMap.snapOn
                        onTriggered: _buttonMap.setGridPref("snapOn", checked)
                    }
                    MenuItem {
                        text: "Snap to entities"
                        checkable: true
                        checked: _buttonMap.snapEntOn
                        onTriggered: _buttonMap.setGridPref("snapEntOn", checked)
                    }
                    MenuSeparator {}
                    Menu {
                        title: "Size"
                        MenuItem {
                            text: "4"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 4 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 4)
                        }
                        MenuItem {
                            text: "8"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 8 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 8)
                        }
                        MenuItem {
                            text: "12"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 12 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 12)
                        }
                        MenuItem {
                            text: "16"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 16 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 16)
                        }
                        MenuItem {
                            text: "24"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 24 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 24)
                        }
                        MenuItem {
                            text: "32"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 32 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 32)
                        }
                        MenuItem {
                            text: "48"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 48 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 48)
                        }
                        MenuItem {
                            text: "64"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 64 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 64)
                        }
                        MenuItem {
                            text: "200"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 200 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 200)
                        }
                        MenuItem {
                            text: "400"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 400 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 400)
                        }
                    }
                }
            }
            Menu {
                title: "Photo"
                MenuItem {
                    text: "Move photo"
                    checkable: true
                    enabled: editing
                    checked: {
                        var e = _ed()
                        return e ? e.movePhoto : _buttonMap.movePhoto
                    }
                    onTriggered: {
                        _buttonMap.movePhoto = checked
                        _buttonMap.applyPhotoToEditor()
                    }
                }
                MenuItem {
                    text: "Adjust photo…"
                    enabled: editing
                    onTriggered: _photoAdj.open()
                }
                MenuSeparator {}
                MenuItem {
                    text: "Reset photo"
                    enabled: editing
                    onTriggered: _buttonMap.resetPhoto()
                }
            }
            Menu {
                title: "Help"
                MenuItem {
                    text: "Button Map guide"
                    onTriggered: _buttonMap.openGuide("Button Map")
                }
                MenuItem {
                    text: "User Guide"
                    onTriggered: _buttonMap.openGuide("")
                }
            }
        }

        ToolBar {
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                spacing: Style.dp(8)
                Label {
                    visible: true
                    text: {
                        var f = _cardLoader.item
                        var raw = f ? Number(f.viewPct) : 1
                        var pct = (raw === raw) ? Math.round(raw * 100) : 100
                        return "View " + pct + "%"
                    }
                    color: Style.fg
                    font.pixelSize: Style.dp(12)
                }
                Label {
                    visible: editing
                    text: "Photo size " + Math.round(photoScale * 100) + "%"
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(12)
                }
                Label {
                    visible: {
                        resTick
                        var e = _ed()
                        return editing && e && e.drawTool && e.drawTool.length
                    }
                    text: "Drawing — drag empty. Shift locks aspect. Esc cancels."
                    color: Style.warn
                    font.pixelSize: Style.dp(12)
                }
                Label {
                    visible: editing && movePhoto
                    text: "Move photo — drag to park. Esc leaves the tool."
                    color: Style.warn
                    font.pixelSize: Style.dp(12)
                }
                Label {
                    visible: editing
                    text: "Module file  " + _hw.path
                    color: Style.fgMuted
                    font.pixelSize: Style.dp(11)
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                }
                Shortcut {
                    enabled: editing
                    sequence: "Delete"
                    onActivated: deleteOrBreak()
                }
                Shortcut {
                    enabled: editing
                    sequence: "Backspace"
                    onActivated: deleteOrBreak()
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+Z"
                    onActivated: { var e = _ed(); if (e) e.undo() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+Shift+Z"
                    onActivated: { var e = _ed(); if (e) e.redo() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+Y"
                    onActivated: { var e = _ed(); if (e) e.redo() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+Shift+V"
                    onActivated: pastePicture()
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+L"
                    onActivated: { var e = _ed(); if (e) e.toggleLockSelection() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+Shift+L"
                    onActivated: { var e = _ed(); if (e) e.unlockAll() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+G"
                    onActivated: { var e = _ed(); if (e) e.groupSelection() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+Shift+G"
                    onActivated: { var e = _ed(); if (e) e.ungroupSelection() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+D"
                    onActivated: { var e = _ed(); if (e) e.duplicateSelection() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+C"
                    onActivated: { var e = _ed(); if (e) e.copySelection() }
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+V"
                    onActivated: { var e = _ed(); if (e) e.pasteClipboard() }
                }
                Shortcut {
                    sequence: "F1"
                    onActivated: _buttonMap.openGuide("Button Map")
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+S"
                    onActivated: saveEdit()
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+0"
                    onActivated: {
                        if (_cardLoader.item)
                            _cardLoader.item.resetView()
                    }
                }
                Item { Layout.fillWidth: true; visible: !editing }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Item {
                id: _mapHost
                Layout.fillWidth: true
                Layout.fillHeight: true

                JGText {
                    anchors.centerIn: parent
                    visible: !targetName.length
                    text: "Choose a device from the File menu."
                    opacity: 0.65
                }

                JGText {
                    anchors.centerIn: parent
                    visible: targetName.length > 0 && !_hasTarget.hit
                    text: "Connect " + targetName
                    opacity: 0.65
                }

                QtObject {
                    id: _hasTarget
                    property bool hit: false
                }

                Component {
                    id: _cardComp
                    JoystickButtonMapCard {
                        id: _card
                        anchors.fill: parent
                        deviceGuid: parent.dGuid
                        title: _buttonMap.displayName(parent.dGuid, parent.dName)
                        pairLabel: parent.dPair
                        editing: _buttonMap.editing
                        editorNodes: _buttonMap.editing ? _buttonMap.workNodes : _buttonMap.liveNodes
                        photoOverride: _buttonMap.photoOverride
                        onChipRowsChanged: _buttonMap.deferReservoir()
                        Connections {
                            target: _card.editorItem
                            function onSelectedChanged() { _buttonMap.deferSelected() }
                            function onTickChanged() { _buttonMap.resTick++ }
                            function onChipMenuRequested(x, y) { _buttonMap.openChipMenu(x, y) }
                            function onFindNotPlaced(label) { _buttonMap.poolFilter = label }
                            function onOverlayImportRequested() { _overlayDialog.open() }
                            function onPastePictureRequested() { _buttonMap.pastePicture() }
                            function onColorPickRequested(field, hex) { _buttonMap.openColorField(field, hex, null) }
                            function onDrawToolChanged() { _buttonMap.resTick++ }
                            function onPhotoRestored() { _buttonMap.syncPhotoFromEditor() }
                            function onHistoryChanged() { _buttonMap.deferHistory() }
                            function onNodesChanged() { _buttonMap.deferHistory() }
                        }
                        Component.onCompleted: _cardLoader.item = _card
                    }
                }

                Repeater {
                    model: _devices
                    Loader {
                        id: _slot
                        required property string guid
                        required property string name
                        required property string pairLabel
                        required property bool mapped
                        anchors.fill: parent
                        active: _buttonMap.isTarget(guid, name)
                        visible: active
                        property string dGuid: guid
                        property string dName: name
                        property string dPair: pairLabel
                        sourceComponent: _cardComp
                        onActiveChanged: {
                            if (active) {
                                _hasTarget.hit = true
                                return
                            }
                            // Only the panel in use turns the face off: the other
                            // devices' panels report inactive as the list fills in.
                            if (_cardLoader.item === item) {
                                _cardLoader.item = null
                                _buttonMap.faceLive = false
                            }
                        }
                        onLoaded: {
                            _hasTarget.hit = true
                            _cardLoader.item = item
                            _buttonMap.faceLive = true
                            _buttonMap.deferFace()
                        }
                    }
                }

                Loader {
                    id: _directCard
                    anchors.fill: parent
                    active: {
                        var named = _buttonMap.targetName.length > 0
                        var guid = _buttonMap.targetGuid
                        return named && !_buttonMap.targetListed()
                    }
                    visible: active
                    property string dGuid: _buttonMap.targetGuid
                    property string dName: _buttonMap.targetName
                    property string dPair: ""
                    sourceComponent: _cardComp
                    onActiveChanged: {
                        if (active)
                            return
                        if (_cardLoader.item === item) {
                            _cardLoader.item = null
                            _buttonMap.faceLive = false
                        }
                    }
                    onLoaded: {
                        _hasTarget.hit = true
                        _cardLoader.item = item
                        _buttonMap.faceLive = true
                        _buttonMap.deferFace()
                    }
                }

                QtObject {
                    id: _cardLoader
                    property var item: null
                }

                Item {
                    id: _poolFloat
                    visible: editing
                    z: 30
                    // clampPool() sets the position and size each time the panel shows.
                    x: 12
                    width: 280
                    height: 160
                    onVisibleChanged: if (visible) Qt.callLater(clampPool)

                    component PoolGrip: MouseArea {
                        required property string edge
                        preventStealing: true
                        hoverEnabled: true
                        onPressed: (m) => startPanelResize(edge, m.x, m.y, this)
                        onPositionChanged: (m) => {
                            if (pressed)
                                movePanelResize(m.x, m.y, this)
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        z: 0
                        acceptedButtons: Qt.AllButtons
                        hoverEnabled: true
                        enabled: {
                            var e = _buttonMap._ed()
                            return !(e && e.dragKind && e.dragKind.length)
                        }
                        onPressed: (m) => { m.accepted = true }
                        onClicked: (m) => { m.accepted = true }
                        onDoubleClicked: (m) => { m.accepted = true }
                        onWheel: (w) => { w.accepted = true }
                    }

                    Rectangle {
                        anchors.fill: parent
                        z: 1
                        radius: Style.dp(12)
                        color: "#CC0C0C0E"
                        border.color: "#3F3F46"
                    }
                    ColumnLayout {
                        z: 2
                        anchors.fill: parent
                        anchors.margins: Style.dp(8)
                        anchors.bottomMargin: Style.dp(12)
                        anchors.rightMargin: Style.dp(10)
                        spacing: Style.dp(6)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Style.dp(6)
                            Item {
                                Layout.fillWidth: true
                                implicitHeight: Style.dp(28)
                                TextField {
                                    id: _poolSearch
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
                                    color: "#A1A1AA"
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
                            Button {
                                text: "Reset"
                                implicitHeight: Style.dp(28)
                                onClicked: clearPoolFilter()
                            }
                        }
                        Flickable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            interactive: !_buttonMap.poolDrag
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
                                            var t = _buttonMap.resTick
                                            if (!_buttonMap.faceLive || !modelData)
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
                                        opacity: (_buttonMap.poolDrag && _buttonMap.poolHw === (modelData ? modelData.hwId : -1) && _buttonMap.poolKind === (modelData ? modelData.kind : "")) ? 0.35 : 1
                                        Text {
                                            id: _chipLab
                                            anchors.centerIn: parent
                                            text: modelData ? modelData.friendly : ""
                                            color: lit ? "#BBF7D0" : "#E4E4E7"
                                            font.pixelSize: Style.dp(11)
                                        }
                                        PointerTip {
                                            delay: 400
                                            show: !_buttonMap.poolDrag && _poolChipHover.containsMouse
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
                                                _buttonMap.poolKind = modelData.kind
                                                _buttonMap.poolHw = modelData.hwId
                                                _buttonMap.poolName = modelData.friendly
                                                _buttonMap.poolX = p.x
                                                _buttonMap.poolY = p.y
                                                _buttonMap.poolDrag = true
                                            }
                                            onPositionChanged: (m) => {
                                                if (!_buttonMap.poolDrag)
                                                    return
                                                var p = mapToItem(_mapHost, m.x, m.y)
                                                _buttonMap.poolX = p.x
                                                _buttonMap.poolY = p.y
                                            }
                                            onReleased: (m) => {
                                                if (!_buttonMap.poolDrag)
                                                    return
                                                var p = mapToItem(_mapHost, m.x, m.y)
                                                dropPool(p.x, p.y)
                                            }
                                            onCanceled: _buttonMap.poolDrag = false
                                        }
                                    }
                                }
                            }
                        }
                    }

                    PoolGrip { edge: "n"; z: 3; height: Style.dp(6); anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; cursorShape: Qt.SizeVerCursor }
                    PoolGrip { edge: "s"; z: 3; height: Style.dp(6); anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; cursorShape: Qt.SizeVerCursor }
                    PoolGrip { edge: "w"; z: 3; width: Style.dp(6); anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.left: parent.left; cursorShape: Qt.SizeHorCursor }
                    PoolGrip { edge: "e"; z: 3; width: Style.dp(6); anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.right: parent.right; cursorShape: Qt.SizeHorCursor }
                    PoolGrip { edge: "nw"; z: 3; width: Style.dp(12); height: Style.dp(12); anchors.left: parent.left; anchors.top: parent.top; cursorShape: Qt.SizeFDiagCursor }
                    PoolGrip { edge: "ne"; z: 3; width: Style.dp(12); height: Style.dp(12); anchors.right: parent.right; anchors.top: parent.top; cursorShape: Qt.SizeBDiagCursor }
                    PoolGrip { edge: "sw"; z: 3; width: Style.dp(12); height: Style.dp(12); anchors.left: parent.left; anchors.bottom: parent.bottom; cursorShape: Qt.SizeBDiagCursor }
                    PoolGrip { edge: "se"; z: 4; width: Style.dp(14); height: Style.dp(14); anchors.right: parent.right; anchors.bottom: parent.bottom; cursorShape: Qt.SizeFDiagCursor }

                    Item {
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: Style.dp(3)
                        width: Style.dp(10)
                        height: Style.dp(10)
                        opacity: 0.55
                        Rectangle { width: Style.dp(8); height: Style.dp(1); color: "#A1A1AA"; rotation: -45; x: Style.dp(2); y: Style.dp(7) }
                        Rectangle { width: Style.dp(5); height: Style.dp(1); color: "#A1A1AA"; rotation: -45; x: Style.dp(5); y: Style.dp(8) }
                    }
                }

                // Layers: every item with an eye and a lock, top of the stack first.
                // On the right, above the pool when it is docked at the bottom.
                Binding {
                    target: _buttonMap._ed()
                    property: "canPastePicture"
                    value: _hw.clipboardHasImage
                    when: !!_buttonMap._ed()
                    restoreMode: Binding.RestoreNone
                }

                RigLayersPanel {
                    id: _layersPanel
                    ed: _buttonMap._ed()
                    visible: editing && layersOn && !!ed
                    z: 31
                    width: Style.dp(260)
                    x: parent.width - width - Style.dp(12)
                    y: Style.dp(12)
                    height: {
                        var bottom = parent.height - Style.dp(12)
                        if (_poolFloat.visible && _poolFloat.y > height * 0.5)
                            bottom = Math.min(bottom, _poolFloat.y - Style.dp(8))
                        return Math.max(Style.dp(120), bottom - y)
                    }
                    onCloseRequested: layersOn = false
                }

                // Properties: the selected item's place, size, angle and style.
                RigPropsPanel {
                    id: _propsPanel
                    ed: _buttonMap._ed()
                    visible: editing && propsOn && !!ed && ((ed.selectedIds || []).length > 0 || ed.selectedId !== "")
                    z: 31
                    width: Style.dp(300)
                    x: Style.dp(12)
                    y: Style.dp(12)
                    height: Math.min(implicitHeight, parent.height - Style.dp(24))
                    onCloseRequested: propsOn = false
                }

                Connections {
                    target: _mapHost
                    function onWidthChanged() { if (editing) clampPool() }
                    function onHeightChanged() { if (editing) clampPool() }
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

    component ColorSwatch: Rectangle {
        id: _sw
        property string hex: "#18181B"
        signal picked()
        Layout.preferredWidth: Style.dp(72)
        Layout.preferredHeight: Style.dp(24)
        width: Style.dp(72)
        height: Style.dp(24)
        radius: Style.dp(4)
        color: hex
        border.color: "#52525B"
        border.width: Style.dp(1)
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: _sw.picked()
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
        parent: _buttonMap.contentItem
        anchors.fill: parent
        z: 1000
        visible: _buttonMap.eyedropField !== ""
        cursorShape: Qt.CrossCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: (m) => {
            if (m.button === Qt.RightButton) {
                _buttonMap.eyedropField = ""
                return
            }
            var p = mapToItem(null, m.x, m.y)
            _buttonMap.takeEyedrop(p.x, p.y)
        }
        Keys.onEscapePressed: _buttonMap.eyedropField = ""
    }

    Popup {
        id: _colorPop
        parent: _buttonMap.contentItem
        width: Style.dp(248)
        height: Style.dp(400)
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: Style.dp(10)
        property string field: "color"
        // A colour was applied while open: it goes into the recent colours.
        property bool changed: false
        property real hh: 0
        property real ss: 0
        property real vv: 0.12
        readonly property color live: Qt.hsva(hh, ss, vv, 1)
        background: Rectangle {
            color: "#18181B"
            border.color: "#3F3F46"
            radius: Style.dp(8)
        }

        function openField(field, hex, anchorItem) {
            _colorPop.field = field
            changed = false
            var c = Qt.color(hex && hex.length ? hex : "#18181B")
            hh = c.hsvHue < 0 ? 0 : c.hsvHue
            ss = c.hsvSaturation
            vv = c.hsvValue
            if (anchorItem && parent) {
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
            if (!visible)
                return
            var e = _cardLoader.item ? _cardLoader.item.editorItem : null
            if (e) {
                e.applyField(field, _buttonMap._toHex(live))
                changed = true
            }
        }

        function takeHex(hex) {
            var c = Qt.color(hex)
            hh = c.hsvHue < 0 ? 0 : c.hsvHue
            ss = c.hsvSaturation
            vv = c.hsvValue
        }

        onClosed: {
            if (changed)
                _hw.noteColour(_buttonMap._toHex(live))
            changed = false
        }

        onHhChanged: pushLive()
        onSsChanged: pushLive()
        onVvChanged: pushLive()

        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(8)
            Label {
                text: "Pick color"
                color: "#E4E4E7"
                font.bold: true
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
                        _colorPop.ss = Math.max(0, Math.min(1, mx / Math.max(1, _sv.width)))
                        _colorPop.vv = Math.max(0, Math.min(1, 1 - my / Math.max(1, _sv.height)))
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
                    border.color: "#52525B"
                }
                Label {
                    Layout.fillWidth: true
                    text: _buttonMap._toHex(_colorPop.live)
                    color: "#E4E4E7"
                    font.family: "Consolas"
                    font.pixelSize: Style.dp(13)
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
                        border.color: "#52525B"
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
                text: "Pick from map"
                Layout.fillWidth: true
                onClicked: _buttonMap.startEyedropper(_colorPop.field)
            }
        }
    }
}
