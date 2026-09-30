// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style

Window {
    id: _buttonMap

    width: 1180
    height: 980
    minimumWidth: 880
    minimumHeight: 720

    color: Style.background
    Universal.theme: Style.theme

    title: targetName.length ? ("Button Map — " + targetName) : "Button Map"

    ToolWindowMemory {
        host: _buttonMap
        name: "button-map"
        defaultWidth: 1180
        defaultHeight: 980
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
    property int fileMenuW: 280

    TextMetrics {
        id: _menuMetric
        font.pixelSize: 14
    }

    function growFileMenu() {
        var labels = [
            "Edit Mapping",
            "Fit to photo frame",
            "Choose background…",
            "Export map…",
            "Import map…",
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
        var max = 160
        for (i = 0; i < labels.length; i++) {
            _menuMetric.text = labels[i]
            if (_menuMetric.advanceWidth > max)
                max = _menuMetric.advanceWidth
        }
        fileMenuW = Math.ceil(max + 88)
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
    property string packKind: ""
    property string packDevice: ""
    property string packPhoto: ""
    property int packPlates: 0
    property bool packFallback: false
    property string packZip: ""
    property string packError: ""
    property real viewPctSave: 1
    property real viewPanX: 0
    property real viewPanY: 0
    property real photoScale: 1
    property real photoOffX: 0
    property real photoOffY: 0
    property real photoRot: 0
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
    property int chipPopW: 280
    property int chipPopH: 480
    property bool gridOn: true
    property bool snapOn: true
    property bool snapEntOn: true
    property int gridSize: 8
    property bool chipPopPlaced: false
    property real panelW: 0
    property real panelH: 160
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
        if (panelFillW || box.width < 40) {
            box.x = 12
            box.width = Math.max(280, pw - 24)
        }
        box.width = Math.max(280, Math.min(box.width, pw - 16))
        box.height = Math.max(90, Math.min(panelH, ph - 16))
        panelH = box.height
        if (panelDockB)
            box.y = ph - box.height - 12
        box.x = Math.max(8, Math.min(box.x, pw - box.width - 8))
        box.y = Math.max(8, Math.min(box.y, ph - box.height - 8))
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
        var maxW = Math.max(280, host.width - 16)
        var maxH = Math.max(90, host.height - 16)
        nw = Math.max(280, Math.min(nw, maxW))
        nh = Math.max(90, Math.min(nh, maxH))
        if (e.indexOf("w") >= 0)
            nx = _prsX + _prsW - nw
        if (e.indexOf("n") >= 0)
            ny = _prsY + _prsH - nh
        nx = Math.max(8, Math.min(nx, host.width - nw - 8))
        ny = Math.max(8, Math.min(ny, host.height - nh - 8))
        _poolFloat.x = nx
        _poolFloat.y = ny
        _poolFloat.width = nw
        _poolFloat.height = nh
        panelH = nh
        panelW = nw
    }

    ViewerDeviceModel { id: _devices }
    HardwareProfile { id: _hw }

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

    function discardEdit() {
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
    }

    DismissibleDialog {
        id: _saveGate
        onSaveChosen: _buttonMap.confirmLeaveSave()
        onDiscardChosen: _buttonMap.confirmLeaveDiscard()
        onCancelled: _buttonMap.pendingDevice = ""
    }

    Dialog {
        id: _helpDlg
        title: "Button Map — Help"
        modal: true
        anchors.centerIn: parent
        width: 640
        height: 680
        standardButtons: Dialog.Close
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        ListView {
            id: _helpList
            anchors.fill: parent
            anchors.margins: 4
            clip: true
            spacing: 14
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            model: [
                {
                    h: "Overview",
                    b: "Button Map is a picture of the selected device. Each chip marks one control. File → Edit Mapping starts an edit. The live view uses the same layout, and a press still lights the matching chip. Moving a chip does not change the action bound to that control.\n\nFile → Save writes the layout to this device’s module file. A successful save says “Saved to the module file.” File → Cancel drops the edit. Closing this window asks when the edit is not saved.\nF1 opens this page."
                },
                {
                    h: "World page",
                    b: "Layout lives on a 32000 × 18000 world page (16:9). The rig photo is a poster in the center 75% well. Nothing is measured on the JPEG.\nChips, hots, leaders, tables, and plates use page fractions only. A new hot starts on its chip; drag the ring onto the control.\nView is the camera (wheel / Reset view). Photo size / Move photo parks the poster under the overlay. File → Save writes nodes, page, photo pose, and ui. Grid / snap writes only ui."
                },
                {
                    h: "File",
                    b: "Edit Mapping — start the editor.\nSave — write this device’s module file. The editor stays open. A successful save says “Saved to the module file.” If the write fails, the message stays up until OK.\nCancel — leave without writing.\nReset layout — send every chip back to the pool. Inputs still light.\nFit to photo frame — used once when a saved layout is much larger than the photo. Then Save.\nChoose background… — pick a photo under the map.\nClear image — restore the picture from the module.\nExport map… — write a zip named after this device. Confirm the photo, then write.\nImport map… — pick a zip, confirm the device photo, then replace this device’s layout.\nClose — close the window. Unsaved work still asks."
                },
                {
                    h: "Edit menu",
                    b: "Undo / Redo — layout history for this session (also Ctrl+Z / Ctrl+Y).\nDuplicate (Ctrl+D) — copy the selection offset so it does not stack.\nCopy / Paste (Ctrl+C / Ctrl+V) — clipboard of chips, groups, and frames."
                },
                {
                    h: "View, zoom, pan",
                    b: "View is the camera. Scroll wheel zooms about the pointer, 50%–400%. View 100% frames the photo well. View 50% is the full 32000 page. Middle-button drag pans. Before Edit Mapping, left-drag also pans. View → Reset view returns View 100% and centered. Camera zoom and pan are stored in ui.\nPhoto size is the poster, not the camera. Photo → Adjust photo… has live sliders for size, offset, and rotate. Size 100% sets the poster size to 1. Photo → Move photo lets you drag the picture. Photo → Reset photo centers it and clears rotate. Pose is stored in the profile photo block and comes back on load.\nView → Grid → Show grid — the full world page. Step is world counts (200 suits 32000). Snap to grid / entities as before. Alt skips snap."
                },
                {
                    h: "Reservoir",
                    b: "The pool lists chips not on the map. Filter by friendly or hardware name. X or Reset clears the filter.\nDrag a chip from the pool onto the photo to place it. Resize the pool; the map does not zoom while the pointer is over it.\nEmpty photo right-click is Draw only — chips come from the pool."
                },
                {
                    h: "Chips",
                    b: "Left-drag moves the chip. The hotspot (dot on the photo) is the hardware contact — drag it separately.\nDefault label is the hardware id: Button 10, Axis 1, Hat 1. Hover a chip for a tooltip with that hardware id. Friendly names are optional — Rename to set one. Clear the friendly name to show the hardware id again. Plus / card / mini do not replace that with Up/Left/Push unless you type it.\nRight-click → Chip:\n  Rename — optional friendly label. Empty falls back to Button N / Axis N / Hat N.\n  Font size.\n  Chip size, Round / Square, Filled / Hollow.\n  Colors — Fill, Outline, Text, Pressed fill / outline / text. Color… opens the HSV picker.\n  Highlight on press — live fill when the stick is down.\n  Reset this cell — drop member style overrides (Edit group only).\n  Delete chip — back to the reservoir.\nHotspot (photo input) and Leader End (wire stop) are their own first-level menus, not under Chip.\nDelete / Backspace on a single chip also returns it to the pool.\nYellow ring is selection."
                },
                {
                    h: "Groups",
                    b: "Shift-click or rubber-band two or more chips, then Group → Group selected (Ctrl+G). Extra leaders drop; one remains. Table + chips: rubber-band the table and those chips, then Group — chips ride the plate, no 5-way. One table only. Break group on the table detaches chips and keeps the table.\nBreak group (Ctrl+Shift+G) or Delete on a group splits members back to singles.\nEdit group unlocks that group only. Other groups stay locked.\nDouble-click or right-click a member to target it. Drag that member to offset it. Chip style writes to that member only.\nDouble-click the member again to rename it.\nDone editing group or Esc ends the session. Double-click empty photo ends edit and clears the selection.\nSaved group style profiles are not in yet — each group keeps its own format and overrides."
                },
                {
                    h: "Format and Align",
                    b: "Format and Align are first-level drawers, not inside Group.\nFormat → 5-Way (five-member hat groups only):\n  Plus cluster — Up / Left / Push / Right / Down cross. Group name once. One leader.\n  Mini hat — compact U/D/L/R/C glyph.\n  Named card — header plus role-only rows.\n  Radial leaders — spokes from the group (can crowd three hats on this grip).\nPicking the theme that is already on re-applies it: stock layout, cell offsets and style overrides cleared, names kept.\nClear Format under Undo/Redo (group click) or Format → Clear Format strips the 5-Way theme and every cell override (size, shape, colors, offsets). Names, Align, and the group stay. Enabled when a theme or any cell override exists.\nAlign left / center / right / Free layout — only when the target is a group.\nFormat is presentation. Hardware ids stay grouped. Save writes the layout to this device’s module file."
                },
                {
                    h: "Context menu",
                    b: "The first screen follows the click target.\nUndo / Redo always.\nGroup click — Clear Format under Redo when the group has a theme or cell overrides.\nLeader or handle — Add spine, Convert spine, Delete selected spine, Clear spines, then the family drawers.\nChip / group — Chip, Hotspot, Leader End, Group, Format, Align, Leader, Draw.\nEmpty photo — Draw only.\nGray items are gated: no selection, not a group, no handle, or no spines."
                },
                {
                    h: "Hotspot",
                    b: "Hotspot is the input on the photo — the control you press — not the chip label.\nRight-click → Hotspot: Size, Round / Square, Filled / Hollow, Color… (HSV picker).\nThe yellow/white dot on the rig photo is this object."
                },
                {
                    h: "Leader End",
                    b: "Leader End is where the wire stops. It is not the hotspot fill.\nDetach chip end / Detach hotspot end — free that terminus.\nReconnect to this chip / Reconnect to this hotspot — snap it back.\nLeader (the next drawer) still owns line color, weight, extra leaders, and curve."
                },
                {
                    h: "Leaders",
                    b: "A leader is the line from chip (or group) to the hotspot.\nClick the line — select only. A click does not add a spine.\nDrag a segment — plant a curved spine at the grab point, then that handle follows the drag.\nClick a handle — select it (orange).\nShort right-click on a handle — menu. Use Delete selected spine.\nHold right-click about ½ second on a handle — delete that handle, no menu.\nFirst menu on a line or handle: Add spine, Convert spine (flip that handle curved ↔ straight, no check mark), Delete selected spine, Clear spines. Convert and Delete need a selected handle.\nLeader submenu: Color…, Weight 0.8–4.0, Add straight / curved spine, This segment or All segments Curved / Straight, Add leader, Branch from this end, Attach (detach / reconnect chip or hotspot ends), Clear all spines, Delete spine, Delete leader.\nDelete leader applies to every selected chip. Rubber-band several chips, then Leader → Delete leaders — each chip’s line is removed. One chip selected — only that chip’s current leader is removed.\nSpines show only while Edit Mapping is on. The chip-to-hotspot line stays in the live map unless you delete it."
                },
                {
                    h: "Draw",
                    b: "Right-click → Draw.\nAround selection — rectangle, rounded, ellipse, triangle, or diamond around selected chips; it moves with them.\nFree drag — pick a shape, drag on empty photo. Shift locks aspect. Esc or Cancel tool drops the tool. Yellow Drawing in the toolbar means a tool is armed.\nImport overlay… — add a PNG/JPEG plate on top of the photo. Transform, lock, plant snap points, drop chips onto them.\nTable — Draw → Free drag → Table. Rubber-band the first size. A blank 1×2 lands (one row, two columns). Handles resize the whole plate; cells share the new size. Right-click the table for the table-only menu (add/insert/delete row or column, ID column, Free position, Place left/center/right/top/middle/bottom, theme, font, pin, z, delete). Free position unlocks that cell so you can drag it; Shift+drag also unlocks and moves it. Spawn empty cell adds a blank free box the same size (no text, not a grid slot). Spawned cells get their own handles and start Independent of table so plate resize does not move them. Independent of table on a free cell stores page position/size. Delete this cell removes a spawned box only. The plate can shrink to 8 px, same floor as a spawned cell. Locked cells still move the whole table. Offsets are fractions of the plate so a resize keeps the cell’s place. Double-click a cell to type. Themes: Gremlin dark, Gremlin hollow, Sheet.\nText — Draw → Free drag → Text. Rubber-band the first size; Size submenu has Caption / Small / Medium / Large / Title / Wide. Double-click to type. Right-click the box for the text-only menu: Duplicate, Delete text box, theme, font, color, opacity, align, bold, word wrap (refits the box), scale font on resize, pin, z, Copy format / Paint format, Clear formatting, Copy text (plain). Packs with a table like chips.\nCorner handles resize. Detach from chips turns an around-frame into a free frame.\nShape, Padding, Rotate (0/90/180/270, ±15), Filled / Hollow, Fill color…, Stroke color…, Stroke width, Opacity.\nBring forward / Send back. Hollow frames click through to chips inside.\nOverlay images: File → Import overlay… then transform. A pin sits at the top-left of the plate. Click the pin (or Draw → Pin overlay) to freeze it: the plus clicks through to chips and leaders; only the pin stays live. Click the pin again to unpin and move/resize. Add snap point, Clear snap points. Drop a chip on a white socket to snap. Save writes pinned."
                },
                {
                    h: "Select and move",
                    b: "Click selects. Shift-click or Ctrl-click toggles. Drag empty glass to rubber-band.\nArrows nudge one view pixel. Shift+arrows nudge by the world-grid step.\nDrag near the page center or an edge — green guide; release snaps to that line.\nDuplicate / Copy / Paste under Edit. Pasted items offset on the page so they do not stack."
                },
                {
                    h: "Keyboard",
                    b: "Ctrl+S Save\nCtrl+Z Undo    Ctrl+Y or Ctrl+Shift+Z Redo\nCtrl+D Duplicate    Ctrl+C Copy    Ctrl+V Paste\nCtrl+G Group    Ctrl+Shift+G Break group\nDelete / Backspace  chip to pool, break group, or delete selected spine\nArrows nudge    Shift+Arrows grid nudge\nEsc  cancel draw tool / end group edit / cancel rename\nF1  this help\nAlt while dragging  skip snap\nShift while drawing  lock aspect"
                },
                {
                    h: "Save and live map",
                    b: "Save writes the layout to this device’s module file. That includes the chips, the photo, and the grid settings.\nThe live view still lights the control that is pressed. Chip names and colors are layout only. They do not change the actions in the profile."
                }
            ]
            delegate: Column {
                width: _helpList.width
                spacing: 4
                required property var modelData
                Label {
                    width: parent.width
                    text: modelData.h
                    color: "#FBBF24"
                    font.pixelSize: 15
                    font.bold: true
                }
                Label {
                    width: parent.width
                    text: modelData.b
                    color: "#E4E4E7"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 13
                    lineHeight: 1.25
                }
            }
        }
    }

    Dialog {
        id: _resetDlg
        title: "Reset layout"
        modal: true
        anchors.centerIn: parent
        width: 460
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        ColumnLayout {
            anchors.fill: parent
            spacing: 12
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#FBBF24"
                text: "Clear every chip, leader, and hotspot from the map?"
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#A1A1AA"
                text: "Joystick mappings are not changed. Pressed buttons still light in the reservoir. Save after reset if you want the empty layout to become the live map."
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8
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
        _chipPop.close()
    }

    function nodeIsGroup(n) {
        return !!(n && (n.kind === "plus" || n.kind === "pair" || n.kind === "axis_stack" || n.kind === "stack" || (n.members && n.members.length)))
    }

    function applyChipPopSize() {
        var maxW = Math.max(240, _buttonMap.width - 16)
        var maxH = Math.max(200, _buttonMap.height - 16)
        var w = Math.max(240, Math.min(chipPopW, maxW))
        var h = Math.max(200, Math.min(chipPopH, maxH))
        _chipPop.width = w
        _chipPop.height = h
        chipPopW = Math.round(w)
        chipPopH = Math.round(h)
    }

    function rememberChipPopSize() {
        chipPopW = Math.round(_chipPop.width)
        chipPopH = Math.round(_chipPop.height)
        persistChipPopUi()
    }

    function setChipPopSize(w, h) {
        if (w)
            chipPopW = w
        if (h)
            chipPopH = h
        applyChipPopSize()
        persistChipPopUi()
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
        return {
            scale: Math.max(0.25, Math.min(4, s)),
            offX: Math.max(-1, Math.min(1, ox)),
            offY: Math.max(-1, Math.min(1, oy)),
            rot: r
        }
    }

    function photoBag() {
        var e = _ed()
        if (e && e.photoBag)
            return e.photoBag()
        return photoFromDoc({
            scale: photoScale,
            offX: photoOffX,
            offY: photoOffY,
            rot: photoRot
        })
    }

    function applyPhoto(p) {
        p = photoFromDoc(p)
        photoScale = p.scale
        photoOffX = p.offX
        photoOffY = p.offY
        photoRot = p.rot
        applyPhotoToEditor()
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
    }

    function setPhotoOff(x, y) {
        var p = photoFromDoc({ offX: x, offY: y })
        photoOffX = p.offX
        photoOffY = p.offY
        applyPhotoToEditor()
    }

    function setPhotoRot(v) {
        var r = Number(v)
        if (!(r === r))
            r = 0
        photoRot = r
        applyPhotoToEditor()
    }

    function resetPhoto() {
        applyPhoto({ scale: 1, offX: 0, offY: 0, rot: 0 })
        movePhoto = false
        applyPhotoToEditor()
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
            chipPopW: chipPopW,
            chipPopH: chipPopH,
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
        if (ui.chipPopW >= 240)
            chipPopW = ui.chipPopW
        if (ui.chipPopH >= 200)
            chipPopH = ui.chipPopH
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

    function persistChipPopUi() {
        persistUi()
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


    function parsePack(text) {
        try {
            return JSON.parse(text)
        } catch (e) {
            return { ok: false, error: "Bad response" }
        }
    }

    function openExport() {
        packError = ""
        if (editing) {
            saveEdit(false)
            if (!saveOk) {
                _saveGate.announce(false, "Not written. It is still only on this screen.")
                return
            }
        }
        var hint = _hw.defaultExportUrl(targetName)
        _exportDialog.currentFolder = _hw.exportFolderUrl()
        _exportDialog.selectedFile = hint
        _exportDialog.open()
    }

    function openImport() {
        packError = ""
        _importDialog.currentFolder = _hw.exportFolderUrl()
        _importDialog.open()
    }

    function showPackPeek(kind, zipUrl) {
        packKind = kind
        packZip = zipUrl || ""
        var raw = kind === "import" ? _hw.peekZip(zipUrl) : _hw.peekLocal(targetName)
        var info = parsePack(raw)
        if (!info.ok) {
            packError = info.error || "Cannot read that map."
            _packFail.open()
            return
        }
        packDevice = info.device || targetName
        packPhoto = info.photoUrl || ""
        packPlates = info.plates || 0
        packFallback = !!info.fallback
        _packConfirm.open()
    }

    function confirmPack() {
        _packConfirm.close()
        var raw
        if (packKind === "import")
            raw = _hw.importMap(packZip)
        else
            raw = _hw.exportMap(targetName, packZip)
        var info = parsePack(raw)
        if (!info.ok) {
            packError = info.error || "Failed."
            _packFail.open()
            return
        }
        if (packKind === "import") {
            if (editing)
                cancelEdit()
            loadLive()
        }
        packError = packKind === "import" ? ("Imported " + (info.device || packDevice)) : "Exported map"
        saveOk = true
        _saveGate.announce(true, packError)
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

    FileDialog {
        id: _exportDialog
        title: "Export map"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: ["Map package (*.zip)"]
        onAccepted: showPackPeek("export", selectedFile)
    }

    FileDialog {
        id: _importDialog
        title: "Import map"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Map package (*.zip)"]
        onAccepted: showPackPeek("import", selectedFile)
    }

    function exportViewTo(url, format) {
        var path = String(url || "")
        if (path.indexOf("file:") === 0)
            path = path.replace("file:///", "").replace("file://", "")
        _buttonMap.grabToImage(function(result) {
            if (!result)
                return
            if (format === "pdf") {
                var png = path.replace(/\.pdf$/i, "") + ".png"
                result.saveToFile(png)
            } else {
                result.saveToFile(path)
            }
        })
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
        id: _packConfirm
        modal: true
        dim: true
        focus: true
        padding: 16
        closePolicy: Popup.CloseOnEscape
        parent: Overlay.overlay
        x: Overlay.overlay ? Math.round((Overlay.overlay.width - width) / 2) : Math.round((_buttonMap.width - width) / 2)
        y: Overlay.overlay ? Math.round((Overlay.overlay.height - height) / 2) : Math.round((_buttonMap.height - height) / 2)
        background: Rectangle {
            color: "#18181B"
            border.color: "#3F3F46"
            border.width: 1
            radius: 4
        }
        contentItem: Column {
            spacing: 12
            width: 280
            Text {
                width: parent.width
                text: packKind === "import" ? "Import map" : "Export map"
                color: "#E4E4E7"
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
            }
            Image {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 240
                height: 180
                fillMode: Image.PreserveAspectFit
                source: packPhoto
                cache: false
            }
            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                color: "#E4E4E7"
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                text: packDevice
            }
            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                color: "#A1A1AA"
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                text: {
                    var extra = packPlates === 1 ? "1 overlay plate" : (packPlates + " overlay plates")
                    var note = packFallback ? " Stock photo used for preview." : ""
                    if (packKind === "import")
                        return "Replace the hardware profile for this device.\n" + extra + "." + note
                    return extra + "." + note
                }
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8
                Button {
                    text: "Cancel"
                    onClicked: _packConfirm.close()
                }
                Button {
                    text: packKind === "import" ? "Replace" : "Save zip"
                    onClicked: confirmPack()
                }
            }
        }
    }

    Popup {
        id: _packFail
        modal: true
        dim: true
        focus: true
        padding: 16
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        parent: Overlay.overlay
        x: Overlay.overlay ? Math.round((Overlay.overlay.width - width) / 2) : Math.round((_buttonMap.width - width) / 2)
        y: Overlay.overlay ? Math.round((Overlay.overlay.height - height) / 2) : Math.round((_buttonMap.height - height) / 2)
        background: Rectangle {
            color: "#450A0A"
            border.color: "#DC2626"
            border.width: 1
            radius: 4
        }
        contentItem: Column {
            spacing: 12
            width: 280
            Text {
                width: parent.width
                wrapMode: Text.WordWrap
                color: "#FECACA"
                font.pixelSize: 13
                horizontalAlignment: Text.AlignHCenter
                text: packError.length ? packError : "Export failed"
            }
            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "OK"
                onClicked: _packFail.close()
            }
        }
    }

    Popup {
        id: _photoAdj
        modal: false
        focus: true
        x: Math.round((_buttonMap.width - width) / 2)
        y: 52
        width: 360
        implicitHeight: 430
        padding: 12
        background: Rectangle {
            color: "#18181B"
            border.color: "#3F3F46"
            radius: 4
        }
        ColumnLayout {
            anchors.fill: parent
            spacing: 8
            Label { text: "Photo"; color: "#E4E4E7"; font.pixelSize: 13 }
            Label { text: "Size  " + Math.round(photoScale * 100) + "%"; color: "#A1A1AA"; font.pixelSize: 11 }
            Slider {
                Layout.fillWidth: true
                from: 0.25
                to: 4
                stepSize: 0.01
                value: photoScale
                onMoved: _buttonMap.setPhotoScale(value)
            }
            Label { text: "Offset X  " + photoOffX.toFixed(3); color: "#A1A1AA"; font.pixelSize: 11 }
            Slider {
                Layout.fillWidth: true
                from: -0.5
                to: 0.5
                stepSize: 0.001
                value: photoOffX
                onMoved: _buttonMap.setPhotoOff(value, photoOffY)
            }
            Label { text: "Offset Y  " + photoOffY.toFixed(3); color: "#A1A1AA"; font.pixelSize: 11 }
            Slider {
                Layout.fillWidth: true
                from: -0.5
                to: 0.5
                stepSize: 0.001
                value: photoOffY
                onMoved: _buttonMap.setPhotoOff(photoOffX, value)
            }
            Label { text: "Rotate  " + Math.round(photoRot) + "°"; color: "#A1A1AA"; font.pixelSize: 11 }
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
        anchors.bottomMargin: 78
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
            }
            Menu {
                title: "View"
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
                    text: "Editor help"
                    onTriggered: _helpDlg.open()
                }
            }
        }

        ToolBar {
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                spacing: 8
                Label {
                    visible: true
                    text: {
                        var f = _cardLoader.item
                        var raw = f ? Number(f.viewPct) : 1
                        var pct = (raw === raw) ? Math.round(raw * 100) : 100
                        return "View " + pct + "%"
                    }
                    color: "#E4E4E7"
                    font.pixelSize: 12
                }
                Label {
                    visible: editing
                    text: "Photo size " + Math.round(photoScale * 100) + "%"
                    color: "#A1A1AA"
                    font.pixelSize: 12
                }
                Label {
                    visible: {
                        resTick
                        var e = _ed()
                        return editing && e && e.drawTool && e.drawTool.length
                    }
                    text: "Drawing — drag empty. Shift locks aspect. Esc cancels."
                    color: "#FBBF24"
                    font.pixelSize: 12
                }
                Label {
                    visible: editing && movePhoto
                    text: "Move photo — drag to park. Esc leaves the tool."
                    color: "#FBBF24"
                    font.pixelSize: 12
                }
                Label {
                    visible: editing
                    text: "Module file  " + _hw.path
                    color: "#A1A1AA"
                    font.pixelSize: 11
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
                    onActivated: _helpDlg.open()
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
                            function onOverlayImportRequested() { _overlayDialog.open() }
                            function onColorPickRequested(field, hex) { _buttonMap.openColorField(field, hex, null) }
                            function onDrawToolChanged() { _buttonMap.resTick++ }
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
                            _buttonMap.faceLive = false
                            if (_cardLoader.item === item)
                                _cardLoader.item = null
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
                        _buttonMap.faceLive = false
                        if (_cardLoader.item === item)
                            _cardLoader.item = null
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
                        radius: 12
                        color: "#CC0C0C0E"
                        border.color: "#3F3F46"
                    }
                    ColumnLayout {
                        z: 2
                        anchors.fill: parent
                        anchors.margins: 8
                        anchors.bottomMargin: 12
                        anchors.rightMargin: 10
                        spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Item {
                                Layout.fillWidth: true
                                implicitHeight: 28
                                TextField {
                                    id: _poolSearch
                                    anchors.fill: parent
                                    placeholderText: "Filter friendly or hardware"
                                    text: poolFilter
                                    rightPadding: 26
                                    onTextChanged: {
                                        if (poolFilter !== text)
                                            poolFilter = text
                                    }
                                }
                                Text {
                                    visible: poolFilter.length > 0
                                    anchors.right: parent.right
                                    anchors.rightMargin: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "×"
                                    color: "#A1A1AA"
                                    font.pixelSize: 16
                                    z: 2
                                    MouseArea {
                                        anchors.fill: parent
                                        anchors.margins: -6
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: clearPoolFilter()
                                    }
                                }
                            }
                            Button {
                                text: "Reset"
                                implicitHeight: 28
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
                                spacing: 6
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
                                        implicitWidth: Math.min(260, _chipLab.implicitWidth + 18)
                                        implicitHeight: 26
                                        radius: 13
                                        color: lit ? "#14532D" : "#18181B"
                                        border.color: lit ? "#22C55E" : "#3F3F46"
                                        border.width: lit ? 2 : 1
                                        opacity: (_buttonMap.poolDrag && _buttonMap.poolHw === (modelData ? modelData.hwId : -1) && _buttonMap.poolKind === (modelData ? modelData.kind : "")) ? 0.35 : 1
                                        Text {
                                            id: _chipLab
                                            anchors.centerIn: parent
                                            text: modelData ? modelData.friendly : ""
                                            color: lit ? "#BBF7D0" : "#E4E4E7"
                                            font.pixelSize: 11
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

                    PoolGrip { edge: "n"; z: 3; height: 6; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; cursorShape: Qt.SizeVerCursor }
                    PoolGrip { edge: "s"; z: 3; height: 6; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; cursorShape: Qt.SizeVerCursor }
                    PoolGrip { edge: "w"; z: 3; width: 6; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.left: parent.left; cursorShape: Qt.SizeHorCursor }
                    PoolGrip { edge: "e"; z: 3; width: 6; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.right: parent.right; cursorShape: Qt.SizeHorCursor }
                    PoolGrip { edge: "nw"; z: 3; width: 12; height: 12; anchors.left: parent.left; anchors.top: parent.top; cursorShape: Qt.SizeFDiagCursor }
                    PoolGrip { edge: "ne"; z: 3; width: 12; height: 12; anchors.right: parent.right; anchors.top: parent.top; cursorShape: Qt.SizeBDiagCursor }
                    PoolGrip { edge: "sw"; z: 3; width: 12; height: 12; anchors.left: parent.left; anchors.bottom: parent.bottom; cursorShape: Qt.SizeBDiagCursor }
                    PoolGrip { edge: "se"; z: 4; width: 14; height: 14; anchors.right: parent.right; anchors.bottom: parent.bottom; cursorShape: Qt.SizeFDiagCursor }

                    Item {
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 3
                        width: 10
                        height: 10
                        opacity: 0.55
                        Rectangle { width: 8; height: 1; color: "#A1A1AA"; rotation: -45; x: 2; y: 7 }
                        Rectangle { width: 5; height: 1; color: "#A1A1AA"; rotation: -45; x: 5; y: 8 }
                    }
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

    Popup {
        id: _chipPop
        parent: _buttonMap.contentItem
        width: 280
        height: 480
        modal: false
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape
        property real _rsx: 0
        property real _rsy: 0
        property real _rsw: 0
        property real _rsh: 0
        property real _rmx: 0
        property real _rmy: 0
        property string _redge: ""

        function startResize(edge, mx, my, item) {
            _redge = edge
            _rsx = x
            _rsy = y
            _rsw = width
            _rsh = height
            var p = item.mapToItem(parent, mx, my)
            _rmx = p.x
            _rmy = p.y
        }

        function moveResize(mx, my, item) {
            var p = item.mapToItem(parent, mx, my)
            var dx = p.x - _rmx
            var dy = p.y - _rmy
            var nx = _rsx
            var ny = _rsy
            var nw = _rsw
            var nh = _rsh
            var e = _redge
            if (e.indexOf("e") >= 0)
                nw = _rsw + dx
            if (e.indexOf("s") >= 0)
                nh = _rsh + dy
            if (e.indexOf("w") >= 0)
                nw = _rsw - dx
            if (e.indexOf("n") >= 0)
                nh = _rsh - dy
            var maxW = Math.max(240, parent.width - 16)
            var maxH = Math.max(200, parent.height - 16)
            nw = Math.max(240, Math.min(nw, maxW))
            nh = Math.max(200, Math.min(nh, maxH))
            if (e.indexOf("w") >= 0)
                nx = _rsx + _rsw - nw
            if (e.indexOf("n") >= 0)
                ny = _rsy + _rsh - nh
            nx = Math.max(8, Math.min(nx, parent.width - nw - 8))
            ny = Math.max(8, Math.min(ny, parent.height - nh - 8))
            x = nx
            y = ny
            width = nw
            height = nh
            chipPopW = Math.round(nw)
            chipPopH = Math.round(nh)
        }

        function startMove(mx, my, item) {
            _rsx = x
            _rsy = y
            var p = item.mapToItem(parent, mx, my)
            _rmx = p.x
            _rmy = p.y
        }

        function moveWin(mx, my, item) {
            var p = item.mapToItem(parent, mx, my)
            x = Math.max(8, Math.min(_rsx + p.x - _rmx, parent.width - width - 8))
            y = Math.max(8, Math.min(_rsy + p.y - _rmy, parent.height - height - 8))
        }

        background: Rectangle {
            color: "#111113"
            border.color: "#3F3F46"
            radius: 8
        }

        component Grip: MouseArea {
            required property string edge
            preventStealing: true
            hoverEnabled: true
            onPressed: (m) => _chipPop.startResize(edge, m.x, m.y, this)
            onPositionChanged: (m) => {
                if (pressed)
                    _chipPop.moveResize(m.x, m.y, this)
            }
            onReleased: rememberChipPopSize()
        }
        MouseArea {
            id: _chipDrag
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.SizeAllCursor
            acceptedButtons: Qt.LeftButton
            preventStealing: true
            enabled: {
                var e = _buttonMap._ed()
                return !(e && e.dragKind && e.dragKind.length)
            }
            onPressed: (m) => _chipPop.startMove(m.x, m.y, this)
            onPositionChanged: (m) => {
                if (pressed)
                    _chipPop.moveWin(m.x, m.y, this)
            }
            ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            anchors.bottomMargin: 14
            anchors.rightMargin: 12
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                Button {
                    text: "Undo"
                    implicitHeight: 24
                    enabled: { var e = _ed(); return e ? e.canUndo : false }
                    onClicked: { var e = _ed(); if (e) e.undo() }
                }
                Button {
                    text: "Redo"
                    implicitHeight: 24
                    enabled: { var e = _ed(); return e ? e.canRedo : false }
                    onClicked: { var e = _ed(); if (e) e.redo() }
                }
                Button {
                    text: "Group"
                    implicitHeight: 24
                    onClicked: _groupMenu.popup()
                }
                Button {
                    text: "Break group"
                    implicitHeight: 24
                    visible: {
                        var e = _ed()
                        return !!(e && e.canUngroup()) || nodeIsGroup(selectedNode)
                    }
                    onClicked: {
                        var e = _ed()
                        if (e)
                            e.ungroupSelection()
                        applySelected()
                        refreshReservoir()
                        _chipPop.close()
                    }
                }
                Button {
                    text: "Leader"
                    implicitHeight: 24
                    onClicked: _leadMenu.popup()
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "×"
                    implicitWidth: 28
                    implicitHeight: 24
                    onClicked: _chipPop.close()
                }
            }
            Label {
                text: selectedNode ? (selectedNode.friendly || selectedNode.id || "Chip") : "Chip"
                font.bold: true
                color: "#E4E4E7"
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#A1A1AA"
                font.pixelSize: 11
                text: {
                    var e = _ed()
                    var n = selectedNode
                    if (!n || !e)
                        return ""
                    if (n.members && n.members.length) {
                        var parts = []
                        var lk = n.kind === "axis_stack" ? "axis" : "btn"
                        for (var i = 0; i < n.members.length; i++)
                            parts.push(e.fullNameOf(lk, n.members[i].hwId))
                        return parts.join("\n")
                    }
                    return e.fullNameOf(n.kind, n.hwId)
                }
            }
            Flickable {
                id: _chipFlick
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                interactive: false
                contentWidth: width
                contentHeight: _chipForm.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                WheelHandler {
                    onWheel: (w) => {
                        var ny = _chipFlick.contentY - w.angleDelta.y * 0.5
                        var maxY = Math.max(0, _chipFlick.contentHeight - _chipFlick.height)
                        _chipFlick.contentY = Math.max(0, Math.min(maxY, ny))
                        w.accepted = true
                    }
                }
                ColumnLayout {
                    id: _chipForm
                    width: parent.width
                    spacing: 6

                    Label { text: "Friendly name"; color: "#A1A1AA" }
                    TextField {
                        Layout.fillWidth: true
                        text: selectedNode && selectedNode.friendly ? selectedNode.friendly : (selectedNode && selectedNode.label ? selectedNode.label : "")
                        placeholderText: "shown on the chip"
                        onEditingFinished: {
                            if (selectedNode) {
                                selectedNode.friendly = text
                                selectedNode.label = text
                                var e = _ed()
                                if (e) e.bump()
                            }
                        }
                    }

                    Label { text: "Group align"; color: "#A1A1AA"; visible: nodeIsGroup(selectedNode) }
                    RowLayout {
                        visible: nodeIsGroup(selectedNode)
                        Layout.fillWidth: true
                        spacing: 4
                        Button { text: "Left"; checkable: true; checked: selectedNode && selectedNode.alignH === "left"; onClicked: { var e = _ed(); if (e) e.setAlignH("left") } }
                        Button { text: "Center"; checkable: true; checked: !selectedNode || !selectedNode.alignH || selectedNode.alignH === "center"; onClicked: { var e = _ed(); if (e) e.setAlignH("center") } }
                        Button { text: "Right"; checkable: true; checked: selectedNode && selectedNode.alignH === "right"; onClicked: { var e = _ed(); if (e) e.setAlignH("right") } }
                        Button { text: "Free"; checkable: true; checked: selectedNode && selectedNode.alignH === "free"; onClicked: { var e = _ed(); if (e) e.setAlignH("free") } }
                    }

                    Label { text: "Hardware id"; color: "#A1A1AA"; visible: selectedNode && selectedNode.hwId !== undefined && !nodeIsGroup(selectedNode) }
                    SpinBox {
                        visible: selectedNode && selectedNode.hwId !== undefined && !nodeIsGroup(selectedNode)
                        from: 1
                        to: 64
                        value: selectedNode && selectedNode.hwId ? selectedNode.hwId : 1
                        onValueModified: {
                            if (selectedNode) {
                                selectedNode.hwId = value
                                var e = _ed()
                                if (e) e.bump()
                            }
                        }
                    }

                    Label { text: "Font size"; color: "#A1A1AA" }
                    SpinBox {
                        from: 8
                        to: 22
                        value: selectedNode && selectedNode.fontSize ? selectedNode.fontSize : 10
                        onValueModified: { var e = _ed(); if (e) e.applyField("fontSize", value) }
                    }
                    Label { text: "Chip size"; color: "#A1A1AA" }
                    SpinBox {
                        from: 12
                        to: 48
                        value: selectedNode && selectedNode.chipSize ? selectedNode.chipSize : 18
                        onValueModified: { var e = _ed(); if (e) e.applyField("chipSize", value) }
                    }
                    Label { text: "Chip shape"; color: "#A1A1AA" }
                    ComboBox {
                        Layout.fillWidth: true
                        model: ["Round", "Square"]
                        currentIndex: selectedNode && selectedNode.chipShape === "square" ? 1 : 0
                        onActivated: (idx) => { var e = _ed(); if (e) e.applyField("chipShape", idx === 1 ? "square" : "round") }
                    }
                    Label { text: "Chip fill"; color: "#A1A1AA" }
                    ComboBox {
                        Layout.fillWidth: true
                        model: ["Filled", "Hollow"]
                        currentIndex: selectedNode && selectedNode.chipFill === "hollow" ? 1 : 0
                        onActivated: (idx) => { var e = _ed(); if (e) e.applyField("chipFill", idx === 1 ? "hollow" : "filled") }
                    }
                    Label { text: "Hotspot size"; color: "#A1A1AA" }
                    SpinBox {
                        from: 4
                        to: 28
                        value: selectedNode && selectedNode.hotSize ? selectedNode.hotSize : 9
                        onValueModified: { var e = _ed(); if (e) e.applyField("hotSize", value) }
                    }
                    Label { text: "Hotspot shape"; color: "#A1A1AA" }
                    ComboBox {
                        Layout.fillWidth: true
                        model: ["Round", "Square"]
                        currentIndex: selectedNode && selectedNode.hotShape === "square" ? 1 : 0
                        onActivated: (idx) => { var e = _ed(); if (e) e.applyField("hotShape", idx === 1 ? "square" : "round") }
                    }
                    Label { text: "Hotspot fill"; color: "#A1A1AA" }
                    ComboBox {
                        Layout.fillWidth: true
                        model: ["Filled", "Hollow"]
                        currentIndex: selectedNode && selectedNode.hotFill === "hollow" ? 1 : 0
                        onActivated: (idx) => { var e = _ed(); if (e) e.applyField("hotFill", idx === 1 ? "hollow" : "filled") }
                    }
                    CheckBox {
                        text: "Highlight on press"
                        checked: selectedNode ? selectedNode.highlight !== false : true
                        onToggled: {
                            if (selectedNode) {
                                selectedNode.highlight = checked
                                var e = _ed()
                                if (e) e.bump()
                            }
                        }
                    }
                    Label { text: "Colors"; color: "#A1A1AA" }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 8
                        rowSpacing: 6
                        Label { text: "Fill"; color: "#A1A1AA" }
                        ColorSwatch { hex: selectedNode && selectedNode.color ? selectedNode.color : "#18181B"; onPicked: _colorPop.openField("color", hex, this) }
                        Label { text: "Outline"; color: "#A1A1AA" }
                        ColorSwatch { hex: selectedNode && selectedNode.border ? selectedNode.border : "#3F3F46"; onPicked: _colorPop.openField("border", hex, this) }
                        Label { text: "Text"; color: "#A1A1AA" }
                        ColorSwatch { hex: selectedNode && selectedNode.textColor ? selectedNode.textColor : "#E4E4E7"; onPicked: _colorPop.openField("textColor", hex, this) }
                        Label { text: "Highlight"; color: "#A1A1AA" }
                        ColorSwatch { hex: selectedNode && selectedNode.hlColor ? selectedNode.hlColor : "#14532D"; onPicked: _colorPop.openField("hlColor", hex, this) }
                        Label { text: "Pressed outline"; color: "#A1A1AA" }
                        ColorSwatch { hex: selectedNode && selectedNode.hlBorder ? selectedNode.hlBorder : "#22C55E"; onPicked: _colorPop.openField("hlBorder", hex, this) }
                        Label { text: "HL text"; color: "#A1A1AA" }
                        ColorSwatch { hex: selectedNode && selectedNode.hlText ? selectedNode.hlText : "#BBF7D0"; onPicked: _colorPop.openField("hlText", hex, this) }
                        Label { text: "Leader"; color: "#A1A1AA" }
                        ColorSwatch { hex: selectedNode && selectedNode.leaderColor ? selectedNode.leaderColor : "#A1A1AA"; onPicked: _colorPop.openField("leaderColor", hex, this) }
                        Label { text: "Hotspot"; color: "#A1A1AA" }
                        ColorSwatch { hex: selectedNode && selectedNode.hotColor ? selectedNode.hotColor : "#F4F4F5"; onPicked: _colorPop.openField("hotColor", hex, this) }
                    }
                    Label { text: "Leader weight"; color: "#A1A1AA" }
                    Slider {
                        Layout.fillWidth: true
                        from: 5
                        to: 40
                        stepSize: 1
                        value: selectedNode && selectedNode.leaderWidth > 0 ? selectedNode.leaderWidth * 10 : 11
                        onMoved: {
                            var e = _ed()
                            if (e)
                                e.applyField("leaderWidth", value / 10)
                        }
                    }
                    Button {
                        text: "Delete chip"
                        Layout.fillWidth: true
                        enabled: !nodeIsGroup(selectedNode)
                        onClicked: {
                            if (nodeIsGroup(selectedNode))
                                return
                            var e = _ed()
                            if (e)
                                e.deleteChip()
                            selectedId = ""
                            selectedNode = null
                            refreshReservoir()
                            _chipPop.close()
                        }
                    }
                }
            }
        }
        }

        Grip { edge: "n"; height: 6; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; cursorShape: Qt.SizeVerCursor }
        Grip { edge: "s"; height: 6; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; cursorShape: Qt.SizeVerCursor }
        Grip { edge: "w"; width: 6; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.left: parent.left; cursorShape: Qt.SizeHorCursor }
        Grip { edge: "e"; width: 6; anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.right: parent.right; cursorShape: Qt.SizeHorCursor }
        Grip { edge: "nw"; width: 12; height: 12; anchors.left: parent.left; anchors.top: parent.top; cursorShape: Qt.SizeFDiagCursor }
        Grip { edge: "ne"; width: 12; height: 12; anchors.right: parent.right; anchors.top: parent.top; cursorShape: Qt.SizeBDiagCursor }
        Grip { edge: "sw"; width: 12; height: 12; anchors.left: parent.left; anchors.bottom: parent.bottom; cursorShape: Qt.SizeBDiagCursor }
        Grip { edge: "se"; width: 14; height: 14; anchors.right: parent.right; anchors.bottom: parent.bottom; cursorShape: Qt.SizeFDiagCursor; z: 2 }

        Item {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 3
            width: 10
            height: 10
            opacity: 0.55
            Rectangle { width: 8; height: 1; color: "#A1A1AA"; rotation: -45; x: 2; y: 7 }
            Rectangle { width: 5; height: 1; color: "#A1A1AA"; rotation: -45; x: 5; y: 8 }
        }
    }

    Rectangle {
        id: _poolGhost
        parent: _mapHost
        visible: poolDrag && editing
        z: 2000
        width: Math.max(36, _ghostLab.implicitWidth + 18)
        height: 26
        radius: 13
        x: poolX - width * 0.5
        y: poolY - height * 0.5
        color: "#14532D"
        border.color: "#4ADE80"
        border.width: 1
        Text {
            id: _ghostLab
            anchors.centerIn: parent
            text: poolName
            color: "#BBF7D0"
            font.pixelSize: 11
        }
    }

    component ColorSwatch: Rectangle {
        id: _sw
        property string hex: "#18181B"
        signal picked()
        Layout.preferredWidth: 72
        Layout.preferredHeight: 24
        width: 72
        height: 24
        radius: 4
        color: hex
        border.color: "#52525B"
        border.width: 1
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

    Popup {
        id: _colorPop
        parent: _buttonMap.contentItem
        width: 248
        height: 330
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: 10
        property string field: "color"
        property real hh: 0
        property real ss: 0
        property real vv: 0.12
        readonly property color live: Qt.hsva(hh, ss, vv, 1)
        background: Rectangle {
            color: "#18181B"
            border.color: "#3F3F46"
            radius: 8
        }

        function openField(field, hex, anchorItem) {
            _colorPop.field = field
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
            if (e)
                e.applyField(field, _buttonMap._toHex(live))
        }

        onHhChanged: pushLive()
        onSsChanged: pushLive()
        onVvChanged: pushLive()

        ColumnLayout {
            anchors.fill: parent
            spacing: 8
            Label {
                text: "Pick color"
                color: "#E4E4E7"
                font.bold: true
            }
            Item {
                id: _sv
                Layout.fillWidth: true
                Layout.preferredHeight: 140
                Rectangle {
                    anchors.fill: parent
                    radius: 4
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: "#FFFFFF" }
                        GradientStop { position: 1; color: Qt.hsva(_colorPop.hh, 1, 1, 1) }
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 4
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#00000000" }
                        GradientStop { position: 1; color: "#FF000000" }
                    }
                }
                Rectangle {
                    width: 12
                    height: 12
                    radius: 6
                    color: "transparent"
                    border.color: "#FFFFFF"
                    border.width: 2
                    x: _colorPop.ss * _sv.width - 6
                    y: (1 - _colorPop.vv) * _sv.height - 6
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 2
                        radius: 4
                        color: "transparent"
                        border.color: "#111111"
                        border.width: 1
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
                Layout.preferredHeight: 16
                Rectangle {
                    anchors.fill: parent
                    radius: 4
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
                    width: 6
                    height: parent.height + 4
                    y: -2
                    x: _colorPop.hh * _hue.width - 3
                    radius: 2
                    color: "transparent"
                    border.color: "#FFFFFF"
                    border.width: 2
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
                    width: 36
                    height: 24
                    radius: 4
                    color: _colorPop.live
                    border.color: "#52525B"
                }
                Label {
                    Layout.fillWidth: true
                    text: _buttonMap._toHex(_colorPop.live)
                    color: "#E4E4E7"
                    font.family: "Consolas"
                    font.pixelSize: 13
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: 4
                Repeater {
                    model: ["#18181B", "#3F3F46", "#E4E4E7", "#14532D", "#22C55E", "#BBF7D0", "#1D4ED8", "#7C2D12", "#831843", "#0F766E", "#FBBF24", "#000000", "#FFFFFF", "#7F1D1D"]
                    Rectangle {
                        required property string modelData
                        width: 16
                        height: 16
                        radius: 3
                        color: modelData
                        border.color: "#52525B"
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                var c = Qt.color(modelData)
                                _colorPop.hh = c.hsvHue < 0 ? 0 : c.hsvHue
                                _colorPop.ss = c.hsvSaturation
                                _colorPop.vv = c.hsvValue
                            }
                        }
                    }
                }
            }
        }
    }

    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        moduleFile: _hw.path
    }
}
