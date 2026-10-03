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
import Gremlin.Menus
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

    property string stockImage: {
        if (/evo l|ot l/i.test(targetName))
            return "qml/images/vkb_gladiator_evo_l.jpg"
        if (/gladiator/i.test(targetName))
            return "qml/images/vkb_gladiator_rig.jpg"
        // Any other device: its own card photo, or no photo at all.
        return initialPhoto
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
        delegate: ThemedMenuItem {
            required property string name
            required property string guid
            text: name
            enabled: !_buttonMap.editing
            checkable: true
            checked: name === _buttonMap.targetName
            onTriggered: _buttonMap.openForDevice(name, "", guid)
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

    // Set when a photo file is replaced or put back under the same name, so
    // the photo reloads instead of showing Qt's cached copy.
    property double _photoStamp: 0

    function applyImage(rel) {
        storedImage = rel && rel.length ? rel : stockImage
        var url = _hw.imageUrl(storedImage)
        if (_photoStamp > 0 && url.indexOf("file:") === 0)
            url += (url.indexOf("?") < 0 ? "?" : "&") + "t=" + _photoStamp
        photoOverride = url
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
        applyGridToEditor()
        applyViewToFace()
        applyPhotoToEditor()
        return true
    }

    function enterEdit() {
        if (editing)
            return
        // A photo kept by an editing session that never finished (a crash)
        // is stale; this session keeps its own on its first photo change.
        _hw.dropPhotoStash(targetName)
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
        // Saved: the photo this session started with is no longer needed.
        _hw.dropPhotoStash(targetName)
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
                            + " that were never saved, probably because the program closed unexpectedly.\n\n"
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
        // Photo files changed in this session go back to how they were.
        if (_hw.restorePhoto(targetName))
            _photoStamp = Date.now()
        editing = false
        workNodes = []
        selectedId = ""
        selectedNode = null
        applyImage(liveImage)
        applyPhoto(livePhoto)
        movePhoto = false
        applyPhotoToEditor()
        // The discarded edits leave no undo steps behind: start the history
        // again from the live map once it is back on screen.
        Qt.callLater(function() {
            var e = _ed()
            if (e)
                e.seedHist()
        })
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
        // This device's photo only; never the previous device's.
        initialPhoto = pendingPhoto
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

    // Asks before a template is deleted.
    DismissibleDialog {
        id: _deleteGate
    }

    // Something the user asked for did not happen: say so.
    DismissibleDialog {
        id: _failNotice
    }

    function tellFailure(title, message) {
        _failNotice.announce(false, message)
        _failNotice.titleText = title
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
                text: "Clear everything from the map: chips, leaders, hotspots, drawings, text boxes, pictures and tables?"
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: "Actions are not changed. Ctrl+Z brings the layout back, and File → Cancel leaves editing without keeping the reset. Save to make the empty map the live one."
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

    // The Button Map Guide: only the Button Map's topics.
    function openGuide() {
        Helpers.createComponent("DialogButtonMapGuide.qml")
    }

    function _ed() {
        return _cardLoader.item ? _cardLoader.item.editorItem : null
    }

    // The editor leaves Move photo on its own (Esc, picking a node, layers);
    // follow it, or the hint stays up and the next photo change turns it back on.
    Connections {
        target: _cardLoader.item ? _cardLoader.item.editorItem : null
        ignoreUnknownSignals: true
        function onMovePhotoChanged() {
            var e = _buttonMap._ed()
            if (e && !e.movePhoto)
                _buttonMap.movePhoto = false
        }
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
        // A spine, a table cell, or every selected item; a group breaks up.
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
        // The look, kept only when changed.
        var look = { bright: [-1, 1], contrast: [-1, 1], grey: [0, 1], fade: [0, 0.9] }
        for (var key in look) {
            var v = Number(p[key])
            if (v === v && v !== 0)
                pose[key] = Math.max(look[key][0], Math.min(look[key][1], v))
        }
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
                               hidden: photoHidden, locked: photoLocked,
                               look: { bright: p.bright, contrast: p.contrast, grey: p.grey, fade: p.fade } })
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

    // The photo's look: an adjusted copy, made once the sliders rest.
    Timer {
        id: _lookTimer
        interval: 150
        onTriggered: {
            var e = _buttonMap._ed()
            if (!e)
                return
            e.photoLookUrl = _hw.adjustedPhotoUrl(String(e.photoBaseUrl), e.photoBright,
                                                  e.photoContrast, e.photoGrey)
        }
    }

    // The pose returns to the frame; hidden, locked and the look stay as they
    // are (Reset look puts the look back).
    function resetPhoto() {
        var e = _ed()
        applyPhoto({ scale: 1, offX: 0, offY: 0, rot: 0,
                     hidden: e ? e.photoHidden : photoHidden, locked: e ? e.photoLocked : photoLocked,
                     bright: e ? e.photoBright : 0, contrast: e ? e.photoContrast : 0,
                     grey: e ? e.photoGrey : 0, fade: e ? e.photoFade : 0 })
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
        addPictures(_hw.pasteClipboardPictures(targetName), undefined)
    }

    // New picture layers, each sized to its picture; a drop point centres
    // them there (several step down and right). One undo step for all.
    function addPictures(rels, at) {
        var e = _ed()
        if (!e || !rels || !rels.length) {
            if (e)
                e.showFindMessage("Nothing to add: no picture found.")
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
        notePhotoChange()
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
            guidesOn: guidesOn
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
        guidesX = Array.isArray(ui.guidesX) ? ui.guidesX : []
        guidesY = Array.isArray(ui.guidesY) ? ui.guidesY : []
        if (ui.guidesOn === true || ui.guidesOn === false)
            guidesOn = ui.guidesOn
    }

    // The device's ruler guides (saved with the view) and whether they show.
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
        refreshActionLabels()
    }

    // --- action labels (Options → Button Map → Labels) ------------------------

    // The mode whose actions the chips show; "" follows the program: the
    // running mode while the profile runs, else the mode shown in the main
    // window.
    property string labelMode: ""
    property var profileModes: _hw.profileModes()
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
            _buttonMap.profileModes = _hw.profileModes()
            if (_buttonMap.labelMode.length && _buttonMap.profileModes.indexOf(_buttonMap.labelMode) < 0)
                _buttonMap.labelMode = ""
            _buttonMap.refreshActionLabels()
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
        e.rulerGuidesX = guidesX.slice()
        e.rulerGuidesY = guidesY.slice()
        e.guidesOn = guidesOn
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
        // An undo step for the moved nodes (bump repaints too).
        if (editing && e && e.bump)
            e.bump()
        else if (e && e.repaint)
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

    // The command palette (Ctrl+K): this window's menu commands. They are
    // read from the menu bar as it opens and taken away as it closes, so the
    // shared command list never keeps hold of this window.
    CommandPalette {
        id: _palette
        owners: ["buttonmap"]
        beforeOpen: function() {
            Commands.removeOwner("buttonmap")
            Commands.defineFromMenuBar(_menuBar, "buttonmap")
        }
        onClosed: Commands.removeOwner("buttonmap")
    }
    Component.onDestruction: Commands.removeOwner("buttonmap")

    FileDialog {
        id: _imageDialog
        title: "Choose photo"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Images (*.jpg *.jpeg *.png *.webp *.bmp)"]
        currentFolder: _hw.imagesFolderUrl()
        onAccepted: {
            // Cancel can put the current photo back.
            _hw.stashPhoto(targetName)
            var rel = _hw.copyImage(selectedFile, targetName)
            if (rel.length) {
                _photoStamp = Date.now()
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
    // File → Print: the page as Export draws it, then the printer dialog.
    function printView() {
        exportViewTo("", "print")
    }

    function exportViewTo(url, format) {
        var e = _ed()
        if (!e)
            return
        _exportJob = { url: url, format: format }
        e.printLight = format === "print" ? _opts.values["print-light"] !== false
                                          : _opts.values["light-page"] === true
        e.exporting = true
        e.repaint()
        // Let the editor redraw without its editing marks first.
        _exportTimer.restart()
    }

    function _grabExport() {
        var e = _ed()
        var job = _exportJob
        _exportJob = null
        if (!e || !job) {
            if (e) {
                e.exporting = false
                e.printLight = false
                e.repaint()
            }
            return
        }
        var f = Math.max(1, exportScale)
        var r = e.spaceRect()
        var bg = e.printLight ? "white" : String(Style.background)
        var ok = e.grabToImage(function(result) {
            e.exporting = false
            e.printLight = false
            e.repaint()
            if (!result)
                return
            if (job.format === "print") {
                _hw.printPage(result.image, r.x * f, r.y * f, r.w * f, r.h * f, bg,
                              targetName.length ? targetName : "Button Map")
                return
            }
            if (!_hw.savePageImage(result.image, r.x * f, r.y * f, r.w * f, r.h * f,
                                   String(job.url), job.format, bg, f))
                console.warn("Button Map export failed: " + job.url)
        }, Qt.size(Math.round(e.width * f), Math.round(e.height * f)))
        if (!ok) {
            e.exporting = false
            e.printLight = false
            e.repaint()
        }
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
    // --- mirror, and copy another device's layout ------------------------------

    property var savedLayouts: []
    property var _copyFrom: null

    function mirrorNow() {
        var e = _ed()
        if (!e || !editing)
            return
        e.mirrorLayout(_opts.values["mirror-pictures"] === true)
        e.showFindMessage("Mirrored left to right. Undo puts it back.")
    }

    function openCopyLayout(row) {
        _copyFrom = row
        _copyDlg.open()
    }

    function copyLayoutFrom(row, mirror) {
        if (!row)
            return
        var text = row.template ? _hw.templateNodes(row.name) : _hw.layoutNodes(row.slug)
        if (!text.length)
            return
        var nodes = []
        try { nodes = JSON.parse(text) } catch (e) { return }
        if (!editing)
            enterEdit()
        hydrateOverlays(nodes)
        workNodes = nodes
        Qt.callLater(function() {
            var e = _ed()
            if (!e)
                return
            if (mirror)
                e.mirrorLayout(_opts.values["mirror-pictures"] === true)
            else
                e.bump()
            refreshReservoir()
            e.showFindMessage("Layout copied. Save to keep it; Undo puts the old one back.")
        })
    }

    Dialog {
        id: _copyDlg
        title: _buttonMap._copyFrom && _buttonMap._copyFrom.template ? "Apply template" : "Copy layout"
        modal: true
        // Another device's layout is usually the other hand's; a template is not.
        onOpened: _copyMirror.checked = !(_buttonMap._copyFrom && _buttonMap._copyFrom.template)
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
                      + (_buttonMap._copyFrom && _buttonMap._copyFrom.template ? "the template " : "the layout of ")
                      + (_buttonMap._copyFrom ? _buttonMap._copyFrom.name : "") + "?"
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: "This device's photo stays. Nothing is saved until you save; Undo puts the old layout back."
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
                    text: _buttonMap._copyFrom && _buttonMap._copyFrom.template ? "Apply template" : "Copy layout"
                    highlighted: true
                    onClicked: {
                        var row = _buttonMap._copyFrom
                        _copyDlg.close()
                        _buttonMap.copyLayoutFrom(row, _copyMirror.checked)
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
        var e = _ed()
        if (e)
            e.showFindMessage(ok ? "Saved style " + clean + "." : "The style was not saved.")
    }

    Dialog {
        id: _styleNameDlg
        title: "Save style"
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
                text: "Keeps this look under a name, to put on other items of the same kind from their right-click menu (Saved styles). A style of the same name is replaced. Options → Button Map → Library renames and deletes them."
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
                        _buttonMap.saveStyleAs(name)
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
            _templateReplace.confirm("Replace template", "A template called " + clean + " exists. Replace it with this layout?", "Replace")
            return
        }
        var ok = _hw.saveTemplate(clean, JSON.stringify(layoutNow() || []), targetName)
        refreshTemplates()
        var e = _ed()
        if (e)
            e.showFindMessage(ok ? "Saved as template " + clean + "." : "The template was not saved.")
    }

    DismissibleDialog {
        id: _templateReplace
        property string pendingName: ""
        onConfirmed: _buttonMap.saveTemplateAs(pendingName, true)
    }

    Dialog {
        id: _templateNameDlg
        title: "Save layout as template"
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
                text: "Keeps this layout's chips, leaders and drawings under a name, to apply to any device later (File → Templates → Apply template)."
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
                        _buttonMap.saveTemplateAs(name, false)
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
        height: Math.min(Style.dp(520), _buttonMap.height - Style.dp(80))
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        onOpened: _buttonMap.refreshTemplates()
        property string renaming: ""
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(8)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: _buttonMap.templateList.length
                      ? "Templates are kept with the module files. Export writes one to a file to share; Import adds one. Pictures in a template stay where they are, so share a Device Pack to send pictures too."
                      : "No templates yet. File → Templates → Save layout as template keeps the current layout."
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: Style.dp(4)
                model: _buttonMap.templateList
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: RowLayout {
                    required property var modelData
                    width: ListView.view.width
                    spacing: Style.dp(6)
                    TextField {
                        Layout.fillWidth: true
                        visible: _templatesDlg.renaming === modelData.name
                        text: modelData.name
                        onAccepted: {
                            var from = modelData.name
                            var to = text.trim()
                            _templatesDlg.renaming = ""
                            if (to.length && to !== from && !_hw.renameTemplate(from, to))
                                _buttonMap.tellFailure("Rename failed", "Could not rename "
                                    + from + " to " + to + ". A template may have that name already,"
                                    + " or its file could not be written.")
                            _buttonMap.refreshTemplates()
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
                    Button {
                        text: "Delete"
                        onClicked: {
                            var name = modelData.name
                            _deleteGate.confirmThen("Delete template",
                                "Delete the template “" + name + "”? Layouts made from it are not changed.",
                                "Delete", function() {
                                    _hw.deleteTemplate(name)
                                    _buttonMap.refreshTemplates()
                                }, null, true)
                        }
                    }
                }
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

    FileDialog {
        id: _templateExportFile
        property string templateName: ""
        title: "Export template"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["Button Map template (*.json)"]
        onAccepted: {
            if (!_hw.exportTemplate(templateName, selectedFile))
                _buttonMap.tellFailure("Export failed",
                    "Could not write " + templateName + " to that file.")
        }
    }

    FileDialog {
        id: _templateImportFile
        title: "Import template"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Button Map template (*.json)"]
        onAccepted: {
            var name = _hw.importTemplate(selectedFile)
            _buttonMap.refreshTemplates()
            var e = _buttonMap._ed()
            if (e)
                e.showFindMessage(name.length ? "Imported template " + name + "." : "That file is not a Button Map template.")
        }
    }

    // --- File → Export modes: one page per mode -----------------------------

    property var _modesJob: null
    property var _modesPicked: []
    property string _modesFormat: "pdf"

    function openExportModes() {
        _modesPicked = profileModes.slice()
        _modesDlg.open()
    }

    function toggleExportMode(mode, on) {
        var next = []
        for (var i = 0; i < profileModes.length; i++) {
            var m = profileModes[i]
            if (m === mode ? on : _modesPicked.indexOf(m) >= 0)
                next.push(m)
        }
        _modesPicked = next
    }

    function exportModesTo(url, format, modes) {
        var e = _ed()
        if (!e || !modes.length || _modesJob)
            return
        _modesJob = {
            url: String(url), format: format, modes: modes.slice(), i: 0,
            keepText: e.chipTextMode, f: Math.max(1, exportScale)
        }
        _hw.beginExportPages()
        // Pages that all read the same would be no use: show the actions.
        if (e.chipTextMode === "Name")
            e.chipTextMode = "Action"
        e.printLight = _opts.values["light-page"] === true
        e.exporting = true
        e.repaint()
        _nextModePage()
    }

    function _nextModePage() {
        var e = _ed()
        var job = _modesJob
        if (!e || !job)
            return
        if (job.i >= job.modes.length) {
            var written = _hw.finishExportPages(job.url, job.format, job.f)
            _modesJob = null
            e.exporting = false
            e.printLight = false
            e.repaint()
            e.exportTitle = ""
            e.chipTextMode = job.keepText
            refreshActionLabels()
            if (e.showFindMessage)
                e.showFindMessage(written ? "Exported " + job.modes.length + " modes." : "Export failed.")
            return
        }
        var mode = job.modes[job.i]
        e.actionLabels = labelsFor(mode)
        e.exportTitle = _opts.values["mode-title"] !== false ? mode : ""
        e.bump()
        _modesTimer.restart()
    }

    Timer {
        id: _modesTimer
        interval: 80
        onTriggered: {
            var e = _buttonMap._ed()
            var job = _buttonMap._modesJob
            if (!e || !job)
                return
            var r = e.spaceRect()
            var f = job.f
            var bg = e.printLight ? "white" : String(Style.background)
            var mode = job.modes[job.i]
            var ok = e.grabToImage(function(result) {
                if (result)
                    _hw.addExportPage(result.image, r.x * f, r.y * f, r.w * f, r.h * f, mode, bg)
                job.i++
                _buttonMap._nextModePage()
            }, Qt.size(Math.round(e.width * f), Math.round(e.height * f)))
            if (!ok) {
                job.i++
                _buttonMap._nextModePage()
            }
        }
    }

    Dialog {
        id: _modesDlg
        title: "Export modes"
        modal: true
        anchors.centerIn: parent
        width: Style.dp(420)
        standardButtons: Dialog.NoButton
        closePolicy: Popup.CloseOnEscape
        ColumnLayout {
            anchors.fill: parent
            spacing: Style.dp(8)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Style.fgMuted
                text: "One page per mode, each chip showing what its control does in that mode. "
                      + "A PDF gets a page per mode; PNG and JPG get a file per mode."
            }
            Repeater {
                model: _buttonMap.profileModes
                CheckBox {
                    required property string modelData
                    text: modelData
                    checked: _buttonMap._modesPicked.indexOf(modelData) >= 0
                    onToggled: _buttonMap.toggleExportMode(modelData, checked)
                }
            }
            CheckBox {
                text: "Mode name at the top of each page"
                checked: _opts.values["mode-title"] !== false
                onToggled: _opts.set("mode-title", checked)
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    text: "Cancel"
                    onClicked: _modesDlg.close()
                }
                Repeater {
                    model: ["PDF", "PNG", "JPG"]
                    Button {
                        required property string modelData
                        text: modelData + "…"
                        enabled: _buttonMap._modesPicked.length > 0
                        highlighted: modelData === "PDF"
                        onClicked: {
                            _buttonMap._modesFormat = modelData.toLowerCase()
                            _modesDlg.close()
                            _exportModesFile.open()
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: _exportModesFile
        title: "Export modes"
        fileMode: FileDialog.SaveFile
        defaultSuffix: _buttonMap._modesFormat
        nameFilters: _buttonMap._modesFormat === "pdf" ? ["PDF (*.pdf)"]
                     : (_buttonMap._modesFormat === "jpg" ? ["JPEG image (*.jpg *.jpeg)"] : ["PNG image (*.png)"])
        onAccepted: _buttonMap.exportModesTo(selectedFile, _buttonMap._modesFormat, _buttonMap._modesPicked)
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
        implicitHeight: Style.dp(690)
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
            Label { text: "Look"; color: Style.fg; font.pixelSize: Style.dp(13); Layout.topMargin: Style.dp(6) }
            Repeater {
                model: [
                    { key: "bright", label: "Brightness", from: -1, to: 1 },
                    { key: "contrast", label: "Contrast", from: -1, to: 1 },
                    { key: "grey", label: "Greyscale", from: 0, to: 1 },
                    { key: "fade", label: "Fade", from: 0, to: 0.9 }
                ]
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 0
                    readonly property real current: {
                        var e = _cardLoader.item ? _cardLoader.item.editorItem : null
                        if (!e)
                            return 0
                        var k = modelData.key
                        return k === "bright" ? e.photoBright : (k === "contrast" ? e.photoContrast
                               : (k === "grey" ? e.photoGrey : e.photoFade))
                    }
                    Label {
                        text: modelData.label + "  " + Math.round(parent.current * 100) + "%"
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(11)
                    }
                    Slider {
                        Layout.fillWidth: true
                        from: modelData.from
                        to: modelData.to
                        stepSize: 0.01
                        value: parent.current
                        onMoved: { var e = _buttonMap._ed(); if (e) e.setPhotoLook(modelData.key, value) }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Button { text: "Reset look"; onClicked: { var e = _buttonMap._ed(); if (e) e.resetPhotoLook() } }
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

        ThemedMenuBar {
            id: _menuBar
            Layout.fillWidth: true
            ThemedMenu {
                id: _fileMenu
                title: "File"
                // The lists in it are filled before ThemedMenu hides what
                // cannot be used and sizes itself.
                beforeShow: function() {
                    _buttonMap.savedLayouts = _hw.savedLayouts(_buttonMap.targetName)
                    _buttonMap.refreshTemplates()
                }
                ThemedMenuItem {
                    text: "Edit Mapping"
                    enabled: !_buttonMap.editing && _buttonMap.targetName.length > 0
                    onTriggered: _buttonMap.enterEdit()
                }
                ThemedMenuItem { text: "Save"; hint: "Ctrl+S"; enabled: _buttonMap.editing; onTriggered: _buttonMap.saveEdit() }
                ThemedMenuItem { text: "Cancel"; enabled: _buttonMap.editing; onTriggered: _buttonMap.cancelEdit() }
                ThemedMenuSeparator {}
                ThemedMenu {
                    id: _deviceMenu
                    title: "Device"
                }
                ThemedMenuItem { text: "Reset layout"; enabled: editing; onTriggered: _resetDlg.open() }
                ThemedMenuItem {
                    text: "Fit to photo frame"
                    enabled: editing && !fittedThisEdit
                    onTriggered: fitToPhotoFrame()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Export PDF…"
                    enabled: _buttonMap.targetName.length > 0
                    onTriggered: _exportPdfDialog.open()
                }
                ThemedMenuItem {
                    text: "Export PNG…"
                    enabled: _buttonMap.targetName.length > 0
                    onTriggered: _exportPngDialog.open()
                }
                ThemedMenuItem {
                    text: "Export JPG…"
                    enabled: _buttonMap.targetName.length > 0
                    onTriggered: _exportJpgDialog.open()
                }
                ThemedMenu {
                    id: _copyMenu
                    title: "Copy layout from"
                    enabled: _buttonMap.targetName.length > 0 && _buttonMap.savedLayouts.length > 0
                    Instantiator {
                        model: _buttonMap.savedLayouts
                        delegate: ThemedMenuItem {
                            required property var modelData
                            text: modelData.name + "…"
                            onTriggered: _buttonMap.openCopyLayout(modelData)
                        }
                        onObjectAdded: (index, object) => _copyMenu.insertItem(index, object)
                        onObjectRemoved: (index, object) => _copyMenu.removeItem(object)
                    }
                }
                ThemedMenu {
                    id: _templateMenu
                    title: "Templates"
                    enabled: _buttonMap.targetName.length > 0
                    beforeShow: _buttonMap.refreshTemplates
                    ThemedMenuItem {
                        text: "Save layout as template…"
                        enabled: (_buttonMap.layoutNow() || []).length > 0
                        onTriggered: _templateNameDlg.open()
                    }
                    ThemedMenu {
                        id: _applyTemplateMenu
                        title: "Apply template"
                        enabled: _buttonMap.templateList.length > 0
                        Instantiator {
                            model: _buttonMap.templateList
                            delegate: ThemedMenuItem {
                                required property var modelData
                                text: modelData.name + "…"
                                onTriggered: _buttonMap.openCopyLayout({ name: modelData.name, template: true })
                            }
                            onObjectAdded: (index, object) => _applyTemplateMenu.insertItem(index, object)
                            onObjectRemoved: (index, object) => _applyTemplateMenu.removeItem(object)
                        }
                    }
                    ThemedMenuItem {
                        text: "Manage templates…"
                        onTriggered: _templatesDlg.open()
                    }
                }
                ThemedMenuItem {
                    text: "Print…"
                    hint: "Ctrl+P"
                    enabled: _buttonMap.targetName.length > 0
                    onTriggered: _buttonMap.printView()
                }
                ThemedMenuItem {
                    text: "Export modes…"
                    enabled: _buttonMap.profileModes.length > 0 && _buttonMap.targetGuid.length > 0
                    onTriggered: _buttonMap.openExportModes()
                }
                ThemedMenuItem {
                    text: "Light page for exports"
                    enabled: _buttonMap.targetName.length > 0
                    checkable: true
                    checked: _opts.values["light-page"] === true
                    onTriggered: _opts.set("light-page", checked)
                }
                ThemedMenu {
                    title: "Export size"
                    enabled: _buttonMap.targetName.length > 0
                    Repeater {
                        model: [1, 2, 3]
                        ThemedMenuItem {
                            required property int modelData
                            text: modelData + "×"
                            checkable: true
                            checked: _buttonMap.exportScale === modelData
                            onTriggered: _opts.set("export-size", modelData + "x")
                        }
                    }
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Close"
                    onTriggered: _buttonMap.close()
                }
            }
            ThemedMenu {
                id: _editMenu
                title: "Edit"
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
                    text: "Duplicate"
                    hint: "Ctrl+D"
                    enabled: { var e = _ed(); return e && e.selectedId !== "" }
                    onTriggered: { var e = _ed(); if (e) e.duplicateSelection() }
                }
                ThemedMenuItem {
                    text: "Copy"
                    hint: "Ctrl+C"
                    enabled: { var e = _ed(); return e && e.selectedId !== "" }
                    onTriggered: { var e = _ed(); if (e) e.copySelection() }
                }
                ThemedMenuItem {
                    text: "Paste"
                    hint: "Ctrl+V"
                    enabled: { var e = _ed(); return e && e.clip && e.clip.length }
                    onTriggered: { var e = _ed(); if (e) e.pasteClipboard() }
                }
                ThemedMenuItem {
                    text: "Paste picture"
                    hint: "Ctrl+Shift+V"
                    enabled: editing && _hw.clipboardHasImage
                    onTriggered: pastePicture()
                }
                ThemedMenuItem {
                    text: "Mirror layout"
                    enabled: editing
                    onTriggered: _buttonMap.mirrorNow()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Editor options…"
                    onTriggered: _buttonMap.openEditorOptions()
                }
            }
            ThemedMenu {
                id: _viewMenu
                title: "View"
                ThemedMenu {
                    title: "Chip text"
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
                    title: "Labels mode"
                    ThemedMenuItem {
                        text: "Follow the program"
                        checkable: true
                        checked: _buttonMap.labelMode === ""
                        onTriggered: _buttonMap.labelMode = ""
                    }
                    ThemedMenuSeparator {}
                    Instantiator {
                        model: _buttonMap.profileModes
                        delegate: ThemedMenuItem {
                            required property string modelData
                            text: modelData
                            checkable: true
                            checked: _buttonMap.labelMode === modelData
                            onTriggered: _buttonMap.labelMode = modelData
                        }
                        onObjectAdded: (index, object) => _labelModeMenu.insertItem(index + 2, object)
                        onObjectRemoved: (index, object) => _labelModeMenu.removeItem(object)
                    }
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Layers"
                    checkable: true
                    checked: layersOn
                    onTriggered: layersOn = !layersOn
                }
                ThemedMenuItem {
                    text: "Properties"
                    checkable: true
                    checked: propsOn
                    onTriggered: propsOn = !propsOn
                }
                ThemedMenuItem {
                    text: "Command palette…"
                    hint: "Ctrl+K"
                    inPalette: false
                    onTriggered: _palette.open()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Zoom to fit page"
                    hint: "Ctrl+1"
                    onTriggered: _buttonMap.zoomToPage()
                }
                ThemedMenuItem {
                    text: "Zoom to selection"
                    hint: "Ctrl+2"
                    enabled: { var e = _ed(); return !!(e && e.selectedIds && e.selectedIds.length) }
                    onTriggered: _buttonMap.zoomToSelection()
                }
                ThemedMenuItem {
                    text: "Reset view (View 100%)"
                    onTriggered: {
                        var f = _cardLoader.item
                        if (f && f.resetView)
                            f.resetView()
                        captureView()
                        persistUi()
                    }
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Rulers"
                    checkable: true
                    checked: _opts.values["rulers"] === true
                    onTriggered: _opts.set("rulers", checked)
                }
                ThemedMenuItem {
                    text: "Show guides"
                    checkable: true
                    checked: _buttonMap.guidesOn
                    onTriggered: {
                        _buttonMap.guidesOn = checked
                        var e = _ed()
                        if (e)
                            e.guidesOn = checked
                        persistUi()
                    }
                }
                ThemedMenuItem {
                    text: "Clear guides"
                    enabled: _buttonMap.guidesX.length + _buttonMap.guidesY.length > 0
                    onTriggered: { var e = _ed(); if (e) e.clearRulerGuides() }
                }
                ThemedMenu {
                    title: "Grid"
                    ThemedMenuItem {
                        text: "Show grid"
                        checkable: true
                        checked: _buttonMap.gridOn
                        onTriggered: _buttonMap.setGridPref("gridOn", checked)
                    }
                    ThemedMenuItem {
                        text: "Snap to grid"
                        checkable: true
                        checked: _buttonMap.snapOn
                        onTriggered: _buttonMap.setGridPref("snapOn", checked)
                    }
                    ThemedMenuItem {
                        text: "Snap to entities"
                        checkable: true
                        checked: _buttonMap.snapEntOn
                        onTriggered: _buttonMap.setGridPref("snapEntOn", checked)
                    }
                    ThemedMenuSeparator {}
                    ThemedMenu {
                        title: "Size"
                        ThemedMenuItem {
                            text: "4"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 4 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 4)
                        }
                        ThemedMenuItem {
                            text: "8"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 8 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 8)
                        }
                        ThemedMenuItem {
                            text: "12"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 12 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 12)
                        }
                        ThemedMenuItem {
                            text: "16"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 16 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 16)
                        }
                        ThemedMenuItem {
                            text: "24"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 24 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 24)
                        }
                        ThemedMenuItem {
                            text: "32"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 32 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 32)
                        }
                        ThemedMenuItem {
                            text: "48"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 48 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 48)
                        }
                        ThemedMenuItem {
                            text: "64"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 64 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 64)
                        }
                        ThemedMenuItem {
                            text: "200"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 200 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 200)
                        }
                        ThemedMenuItem {
                            text: "400"
                            checkable: true
                            checked: { var e = _ed(); return e && e.gridSize === 400 }
                            onTriggered: _buttonMap.setGridPref("gridSize", 400)
                        }
                    }
                }
            }
            ThemedMenu {
                id: _photoMenu
                title: "Photo"
                // Everything in it needs editing.
                enabled: editing
                ThemedMenuItem { text: "Choose photo…"; enabled: editing; onTriggered: _imageDialog.open() }
                ThemedMenuItem {
                    text: "Clear photo"
                    enabled: editing
                    onTriggered: {
                        // Cancel can put the current photo back.
                        _hw.stashPhoto(targetName)
                        if (!_hw.clearImage(targetName)) {
                            // It may have stopped part way: put the photo back.
                            _hw.restorePhoto(targetName)
                            tellFailure("Clear photo failed",
                                "The photo file could not be removed (it may be open in another program).")
                            return
                        }
                        applyImage(stockImage)
                        resetPhoto()
                    }
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
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
                ThemedMenuItem {
                    text: "Adjust photo…"
                    enabled: editing
                    onTriggered: _photoAdj.open()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem {
                    text: "Reset photo"
                    enabled: editing
                    onTriggered: _buttonMap.resetPhoto()
                }
            }
            ThemedMenu {
                title: "Help"
                ThemedMenuItem {
                    text: "Button Map guide"
                    hint: "F1"
                    onTriggered: _buttonMap.openGuide()
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
                    sequence: "Ctrl+K"
                    onActivated: _palette.open()
                }
                Shortcut {
                    sequence: "F1"
                    onActivated: _buttonMap.openGuide()
                }
                Shortcut {
                    enabled: editing
                    sequence: "Ctrl+S"
                    onActivated: saveEdit()
                }
                Shortcut {
                    sequence: "Ctrl+P"
                    onActivated: _buttonMap.printView()
                }
                Shortcut {
                    sequence: "Ctrl+1"
                    onActivated: _buttonMap.zoomToPage()
                }
                Shortcut {
                    sequence: "Ctrl+2"
                    onActivated: _buttonMap.zoomToSelection()
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
                            function onPhotoBrightChanged() { _lookTimer.restart() }
                            function onPhotoContrastChanged() { _lookTimer.restart() }
                            function onPhotoGreyChanged() { _lookTimer.restart() }
                            function onPhotoBaseUrlChanged() { _lookTimer.restart() }
                            function onSaveStyleRequested(kind, fieldsJson) { _buttonMap.askStyleName(kind, fieldsJson) }
                            function onRulerGuidesEdited() { _buttonMap.guidesFromEditor() }
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

                // Drop picture files anywhere on the map to add them as layers.
                DropArea {
                    id: _pictureDrop
                    anchors.fill: parent
                    z: 40
                    enabled: !!_buttonMap._ed()
                    keys: ["text/uri-list"]
                    onEntered: (drag) => {
                        drag.accepted = drag.hasUrls && _hw.hasPictureFiles(drag.urls)
                    }
                    onDropped: (drop) => {
                        if (!drop.hasUrls)
                            return
                        if (_buttonMap.dropPictures(drop.urls, drop.x, drop.y, _pictureDrop))
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

                    // A chip dragged over the pool lights it: let go to take the
                    // chip off the map.
                    readonly property bool dropHot: {
                        var e = _buttonMap._ed()
                        return !!(e && e.poolHover)
                    }
                    Rectangle {
                        anchors.fill: parent
                        z: 1
                        radius: Style.dp(12)
                        color: "#CC0C0C0E"
                        border.color: _poolFloat.dropHot ? Style.accent : "#3F3F46"
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
                Binding {
                    target: _buttonMap._ed()
                    property: "clipboardSerial"
                    value: _hw.clipboardSerial
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
                        // The pool sits in the lower half: stop above it. (Of
                        // the parent's height: the panel's own would loop.)
                        if (_poolFloat.visible && _poolFloat.y > parent.height * 0.5)
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
