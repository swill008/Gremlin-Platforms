// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only
// Device-Configuration-Macro Change — grouped bindings catalog.

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts
import QtQuick.Dialogs

import Gremlin.Config
import Gremlin.Device
import Gremlin.Profile
import Gremlin.Style
import Gremlin.UI

Item {
    id: _root

    property Device device
    property var moduleModel: null
    property string claimDeviceName: ""
    property bool isOutput: false
    property int editingHid: -1
    property int editingSeq: -1
    property int quickHid: -1
    property int quickSeq: -1
    property bool advancedOpen: false
    property bool editorWindowOpen: false
    property int paneHid: -1
    property int paneSeq: -1
    property string paneName: ""
    property string paneSummary: ""
    property int paneWidth: 560
    property bool closeAfterOk: false
    property bool paneChoiceReady: false
    property var panePending: null
    property int revealOnceRow: -1
    property int revealTries: 0
    property bool showPanel: false
    property bool parkEmptyInUnmapped: false
    signal closePanel()
    signal advancedRequested(int hid)
    readonly property bool editorLocked: backend && backend.gremlinActive && !isOutput
    readonly property bool runtimeActive: !!(backend && backend.gremlinActive)

    property int listPadding: 8
    property int rowSpacing: 4
    property int groupBetween: 4
    property int groupInside: 4
    property int unmappedGap: 48
    property string groupAlign: "left"
    property int groupLeft: 0
    property int groupRight: 0
    property int groupWidthPct: 100
    property string groupPadShape: "box"
    property int groupPad: 48
    property int groupPadTop: 48
    property int groupPadRight: 48
    property int groupPadBottom: 48
    property int groupPadLeft: 48
    property int groupRadius: 0
    property string colorGroup: "#00000000"
    property int parentHeight: 50
    property int childHeight: 36
    property string parentAlign: "left"
    property int parentLeft: 0
    property int parentRight: 0
    property int parentWidthPct: 100
    property string childAlign: "left"
    property int childLeft: 24
    property int childRight: 24
    property int childWidthPct: 50
    property int parentFont: 13
    property int childFont: 12
    property int summaryFont: 12
    property bool parentBold: true
    property bool showChildren: true
    property bool showLiveBars: true
    property bool showLeds: true
    property bool showSummary: true
    property int rowRadius: 3
    property int nameColW: 180
    property int childNameColW: 160
    property int rowInnerPad: 10
    property string listPadShape: "sides"
    property int listPad: 8
    property int listPadTop: 0
    property int listPadRight: 8
    property int listPadBottom: 0
    property int listPadLeft: 8
    property string parentPadShape: "sides"
    property int parentPad: 10
    property int parentPadTop: 0
    property int parentPadRight: 8
    property int parentPadBottom: 0
    property int parentPadLeft: 10
    property string childPadShape: "sides"
    property int childPad: 10
    property int childPadTop: 0
    property int childPadRight: 8
    property int childPadBottom: 0
    property int childPadLeft: 10
    property int childRadius: 3
    property string editorPadShape: "box"
    property int editorPadTop: 10
    property int editorPadRight: 10
    property int editorPadBottom: 10
    property int editorPadLeft: 10
    property int editorIndent: 12
    property string editorAlign: "left"
    property int editorRight: 0
    property int editorWidthPct: 100
    property int editorPad: 10
    property int editorGap: 4
    property int editorRadius: 3
    property int editorBorderW: 1
    property int editorAccentW: 3
    property bool showEditorAccent: true
    property string colorParent: "#111113"
    property string colorChild: "#111113"
    property string colorSelected: "#27272A"
    property string colorText: "#E4E4E7"
    property string colorMuted: "#A1A1AA"
    property string colorLive: "#22C55E"
    property string colorBorder: "#3F3F46"
    property string colorSelectBorder: "#E4E4E7"
    property string colorEditor: "#0F2744"
    property string colorEditorBorder: "#3B82F6"
    property string colorEditorAccent: "#3B82F6"
    property string colorScreen: "#00000000"
    property string screenImage: ""
    property string _colorTarget: "parent"
    property string toastText: "Display Options Saved"

    BindingCatalogModel {
        id: _catalog
        guid: device ? device.guid : ""
        deviceName: _root.claimDeviceName
        parkEmptyInUnmapped: _root.parkEmptyInUnmapped
    }

    ListModel { id: _copySources }

    WindowPlacement {
        id: _panePlacement
    }

    DismissibleDialog {
        id: _paneLeave
        onSaveChosen: {
            var seq = _catalog.commitPane()
            if (seq >= 0)
                _root.paneSeq = seq
            _catalog.reload()
            var pending = _root.panePending
            _root.panePending = null
            if (!pending)
                return
            if (pending.close) {
                _root.closeAdvancedPane()
                _root.afterPaneClosedForLeave()
            } else {
                _root.startPane(pending.hid, pending.seq)
            }
        }
        onDiscardChosen: {
            _catalog.discardPane()
            var pending = _root.panePending
            _root.panePending = null
            if (!pending)
                return
            if (pending.close) {
                _root.closeAdvancedPane()
                _root.afterPaneClosedForLeave()
            } else {
                _root.startPane(pending.hid, pending.seq)
            }
        }
        onCancelled: {
            _root.panePending = null
            if (_root._leaveAfterPane) {
                _root._leaveAfterPane = false
                _root.leaveCancelled()
            }
        }
    }

    Component.onCompleted: {
        closeAfterOk = _panePlacement.closePaneAfterOk()
        var saved = _panePlacement.actionPaneWidth()
        if (saved >= 420)
            paneWidth = saved
        paneChoiceReady = true
        if (uiState)
            _catalog.setMode(uiState.currentMode)
        loadCatalog()
    }

    Connections {
        target: moduleModel
        function onClaimsChanged() { _catalog.reload() }
        function onViewChanged() { loadCatalog() }
    }

    Connections {
        target: uiState
        function onModeChanged() {
            if (uiState)
                _catalog.setMode(uiState.currentMode)
        }
        function onDeviceChanged() {
            if (!uiState)
                return
            showHid(uiState.currentInputIndex)
        }
    }

    onClaimDeviceNameChanged: Qt.callLater(loadCatalog)

    DeviceLiveState {
        id: _liveState
        guid: device ? device.guid : ""
        deviceName: _root.claimDeviceName
        locked: editorLocked
        liveWhileActive: false
    }

    HighlightSpeedModel {
        id: _highlightSpeed
    }

    ColorDialog {
        id: _colorDlg
        title: "Choose color"
        onAccepted: {
            var c = selectedColor.toString()
            if (_colorTarget === "child") colorChild = c
            else if (_colorTarget === "selected") colorSelected = c
            else if (_colorTarget === "text") colorText = c
            else if (_colorTarget === "muted") colorMuted = c
            else if (_colorTarget === "live") colorLive = c
            else if (_colorTarget === "border") colorBorder = c
            else if (_colorTarget === "selectBorder") colorSelectBorder = c
            else if (_colorTarget === "editor") colorEditor = c
            else if (_colorTarget === "editorBorder") colorEditorBorder = c
            else if (_colorTarget === "editorAccent") colorEditorAccent = c
            else if (_colorTarget === "group") colorGroup = c
            else if (_colorTarget === "screen") colorScreen = c
            else colorParent = c
        }
    }

    FileDialog {
        id: _screenImageDlg
        title: "Screen background"
        nameFilters: ["Images (*.png *.jpg *.jpeg *.bmp *.webp)"]
        fileMode: FileDialog.OpenFile
        onAccepted: screenImage = selectedFile.toString()
    }

    function catalogPayload() {
        return {
            listPadding: padEdge(listPadShape, listPad, listPadLeft),
            rowSpacing: groupBetween,
            groupBetween: groupBetween,
            groupInside: groupInside,
            unmappedGap: unmappedGap,
            groupAlign: groupAlign,
            groupLeft: groupLeft,
            groupRight: groupRight,
            groupWidthPct: groupWidthPct,
            groupPadShape: groupPadShape,
            groupPad: groupPad,
            groupPadTop: groupPadTop,
            groupPadRight: groupPadRight,
            groupPadBottom: groupPadBottom,
            groupPadLeft: groupPadLeft,
            groupRadius: groupRadius,
            colorGroup: colorGroup,
            parentHeight: parentHeight,
            childHeight: childHeight,
            parentAlign: parentAlign,
            parentLeft: parentLeft,
            parentRight: parentRight,
            parentWidthPct: parentWidthPct,
            childAlign: childAlign,
            childLeft: childLeft,
            childRight: childRight,
            childWidthPct: childWidthPct,
            parentFont: parentFont,
            childFont: childFont,
            summaryFont: summaryFont,
            parentBold: parentBold,
            showChildren: showChildren,
            showLiveBars: showLiveBars,
            showLeds: showLeds,
            showSummary: showSummary,
            rowRadius: rowRadius,
            nameColW: nameColW,
            childNameColW: childNameColW,
            rowInnerPad: padEdge(parentPadShape, parentPad, parentPadLeft),
            listPadShape: listPadShape,
            listPad: listPad,
            listPadTop: listPadTop,
            listPadRight: listPadRight,
            listPadBottom: listPadBottom,
            listPadLeft: listPadLeft,
            parentPadShape: parentPadShape,
            parentPad: parentPad,
            parentPadTop: parentPadTop,
            parentPadRight: parentPadRight,
            parentPadBottom: parentPadBottom,
            parentPadLeft: parentPadLeft,
            childPadShape: childPadShape,
            childPad: childPad,
            childPadTop: childPadTop,
            childPadRight: childPadRight,
            childPadBottom: childPadBottom,
            childPadLeft: childPadLeft,
            childRadius: childRadius,
            editorPadShape: editorPadShape,
            editorPadTop: editorPadTop,
            editorPadRight: editorPadRight,
            editorPadBottom: editorPadBottom,
            editorPadLeft: editorPadLeft,
            editorIndent: editorIndent,
            editorAlign: editorAlign,
            editorRight: editorRight,
            editorWidthPct: editorWidthPct,
            editorPad: editorPad,
            editorGap: editorGap,
            editorRadius: editorRadius,
            editorBorderW: editorBorderW,
            editorAccentW: editorAccentW,
            showEditorAccent: showEditorAccent,
            colorParent: colorParent,
            colorChild: colorChild,
            colorSelected: colorSelected,
            colorText: colorText,
            colorMuted: colorMuted,
            colorLive: colorLive,
            colorBorder: colorBorder,
            colorSelectBorder: colorSelectBorder,
            colorEditor: colorEditor,
            colorEditorBorder: colorEditorBorder,
            colorEditorAccent: colorEditorAccent,
            colorScreen: colorScreen,
            screenImage: screenImage,
            parkEmptyInUnmapped: parkEmptyInUnmapped,
            sections: sectionState()
        }
    }

    property bool openScreen: false
    property bool openShown: false
    property bool openList: false
    property bool openGroup: false
    property bool openParent: false
    property bool openChild: false
    property bool openText: false
    property bool openSelection: false
    property bool openEditor: false

    function sectionState() {
        return {
            "screen": openScreen,
            "shown": openShown,
            "list": openList,
            "group": openGroup,
            "parent": openParent,
            "child": openChild,
            "text": openText,
            "selection": openSelection,
            "editor": openEditor
        }
    }

    function applySections(raw) {
        var s = raw || {}
        openScreen = !!s.screen
        openShown = !!s.shown
        openList = !!s.list
        openGroup = !!s.group
        openParent = !!s.parent
        openChild = !!s.child
        openText = !!s.text
        openSelection = !!s.selection
        openEditor = !!s.editor
    }

    function setAllSections(open) {
        openScreen = open
        openShown = open
        openList = open
        openGroup = open
        openParent = open
        openChild = open
        openText = open
        openSelection = open
        openEditor = open
    }

    function applyDefaults() {
        listPadding = 8
        rowSpacing = 4
        groupBetween = 4
        groupInside = 4
        unmappedGap = 48
        groupAlign = "left"
        groupLeft = 0
        groupRight = 0
        groupWidthPct = 100
        groupPadShape = "box"
        groupPad = 48
        groupPadTop = 48
        groupPadRight = 48
        groupPadBottom = 48
        groupPadLeft = 48
        groupRadius = 0
        colorGroup = "#00000000"
        parentHeight = 50
        childHeight = 36
        parentAlign = "left"
        parentLeft = 0
        parentRight = 0
        parentWidthPct = 100
        childAlign = "left"
        childLeft = 24
        childRight = 24
        childWidthPct = 50
        parentFont = 13
        childFont = 12
        summaryFont = 12
        parentBold = true
        showChildren = true
        showLiveBars = true
        showLeds = true
        showSummary = true
        rowRadius = 3
        nameColW = 180
        childNameColW = 160
        rowInnerPad = 10
        listPadShape = "sides"
        listPad = 8
        listPadTop = 0
        listPadRight = 8
        listPadBottom = 0
        listPadLeft = 8
        parentPadShape = "sides"
        parentPad = 10
        parentPadTop = 0
        parentPadRight = 8
        parentPadBottom = 0
        parentPadLeft = 10
        childPadShape = "sides"
        childPad = 10
        childPadTop = 0
        childPadRight = 8
        childPadBottom = 0
        childPadLeft = 10
        childRadius = 3
        editorPadShape = "box"
        editorPadTop = 10
        editorPadRight = 10
        editorPadBottom = 10
        editorPadLeft = 10
        editorIndent = 12
        editorAlign = "left"
        editorRight = 0
        editorWidthPct = 100
        editorPad = 10
        editorGap = 4
        editorRadius = 3
        editorBorderW = 1
        editorAccentW = 3
        showEditorAccent = true
        colorParent = "#111113"
        colorChild = "#111113"
        colorSelected = "#27272A"
        colorText = "#E4E4E7"
        colorMuted = "#A1A1AA"
        colorLive = "#22C55E"
        colorBorder = "#3F3F46"
        colorSelectBorder = "#E4E4E7"
        colorEditor = "#0F2744"
        colorEditorBorder = "#3B82F6"
        colorEditorAccent = "#3B82F6"
        colorScreen = "#00000000"
        screenImage = ""
        parkEmptyInUnmapped = false
        setAllSections(false)
    }

    function numVal(v, d) {
        var n = Number(v)
        return (v === undefined || v === null || v === "" || isNaN(n)) ? d : n
    }

    function padEdge(shape, size, side) {
        return shape === "box" ? size : side
    }

    function edgeOr(v, fallback) {
        return v === undefined || v === null || v === "" ? fallback : numVal(v, fallback)
    }

    function loadCatalog() {
        if (!moduleModel || !claimDeviceName.length)
            return
        refreshCopySources()
        try {
            var v = JSON.parse(moduleModel.catalogConfigJson(claimDeviceName, device ? device.guid : ""))
        } catch (e) {
            return
        }
        applyCatalogValues(v)
        rememberCatalog()
    }

    function copyCatalogFrom(name, guid) {
        if (!moduleModel || !name)
            return
        try {
            var v = JSON.parse(moduleModel.catalogConfigJson(name, guid || ""))
        } catch (e) {
            return
        }
        applyCatalogValues(v)
    }

    function refreshCopySources() {
        _copySources.clear()
        if (!moduleModel || !moduleModel.otherSourceCatalogs)
            return
        var rows = []
        try {
            rows = JSON.parse(moduleModel.otherSourceCatalogs(claimDeviceName) || "[]")
        } catch (e) {
            return
        }
        for (var i = 0; i < rows.length; ++i)
            _copySources.append({
                "label": rows[i].name,
                "name": rows[i].name,
                "guid": rows[i].guid || ""
            })
    }

    function applyCatalogValues(v) {
        listPadding = numVal(v.listPadding, 8)
        rowSpacing = numVal(v.rowSpacing, 4)
        groupBetween = edgeOr(v.groupBetween, rowSpacing)
        groupInside = edgeOr(v.groupInside, rowSpacing)
        unmappedGap = edgeOr(v.unmappedGap, 48)
        groupAlign = v.groupAlign || "left"
        groupLeft = edgeOr(v.groupLeft, 0)
        groupRight = edgeOr(v.groupRight, 0)
        groupWidthPct = edgeOr(v.groupWidthPct, 100)
        groupPadShape = v.groupPadShape || "box"
        groupPad = edgeOr(v.groupPad, 48)
        groupPadTop = edgeOr(v.groupPadTop, 48)
        groupPadRight = edgeOr(v.groupPadRight, 48)
        groupPadBottom = edgeOr(v.groupPadBottom, 48)
        groupPadLeft = edgeOr(v.groupPadLeft, 48)
        groupRadius = edgeOr(v.groupRadius, 0)
        colorGroup = v.colorGroup || "#00000000"
        parentHeight = numVal(v.parentHeight, 50)
        childHeight = numVal(v.childHeight, 36)
        parentAlign = v.parentAlign || "left"
        parentLeft = numVal(v.parentLeft, 0)
        parentRight = numVal(v.parentRight, 0)
        parentWidthPct = numVal(v.parentWidthPct, 100)
        childAlign = v.childAlign || "left"
        childLeft = numVal(v.childLeft, 24)
        childRight = numVal(v.childRight, 24)
        childWidthPct = numVal(v.childWidthPct, 50)
        parentFont = numVal(v.parentFont, 13)
        childFont = numVal(v.childFont, 12)
        summaryFont = numVal(v.summaryFont, 12)
        parentBold = v.parentBold !== false
        showChildren = v.showChildren !== false
        showLiveBars = v.showLiveBars !== false
        showLeds = v.showLeds !== false
        showSummary = v.showSummary !== false
        rowRadius = numVal(v.rowRadius, 3)
        nameColW = numVal(v.nameColW, 180)
        childNameColW = numVal(v.childNameColW, 160)
        rowInnerPad = numVal(v.rowInnerPad, 10)
        var listLegacy = numVal(v.listPadding, 8)
        listPadShape = v.listPadShape || "sides"
        listPad = numVal(v.listPad, listLegacy)
        listPadLeft = edgeOr(v.listPadLeft, listLegacy)
        listPadRight = edgeOr(v.listPadRight, listLegacy)
        listPadTop = edgeOr(v.listPadTop, 0)
        listPadBottom = edgeOr(v.listPadBottom, 0)
        var inner = rowInnerPad
        parentPadShape = v.parentPadShape || "sides"
        parentPad = numVal(v.parentPad, inner)
        parentPadLeft = edgeOr(v.parentPadLeft, inner)
        parentPadRight = edgeOr(v.parentPadRight, 8)
        parentPadTop = edgeOr(v.parentPadTop, 0)
        parentPadBottom = edgeOr(v.parentPadBottom, 0)
        childPadShape = v.childPadShape || parentPadShape
        childPad = edgeOr(v.childPad, parentPad)
        childPadLeft = edgeOr(v.childPadLeft, parentPadLeft)
        childPadRight = edgeOr(v.childPadRight, parentPadRight)
        childPadTop = edgeOr(v.childPadTop, parentPadTop)
        childPadBottom = edgeOr(v.childPadBottom, parentPadBottom)
        childRadius = edgeOr(v.childRadius, rowRadius)
        var ed = numVal(v.editorPad, 10)
        editorPadShape = v.editorPadShape || "box"
        editorPad = ed
        editorPadTop = edgeOr(v.editorPadTop, ed)
        editorPadRight = edgeOr(v.editorPadRight, ed)
        editorPadBottom = edgeOr(v.editorPadBottom, ed)
        editorPadLeft = edgeOr(v.editorPadLeft, ed)
        editorIndent = numVal(v.editorIndent, 12)
        editorAlign = v.editorAlign || "left"
        editorRight = numVal(v.editorRight, 0)
        editorWidthPct = numVal(v.editorWidthPct, 100)
        editorPad = numVal(v.editorPad, 10)
        editorGap = numVal(v.editorGap, 4)
        editorRadius = numVal(v.editorRadius, 3)
        editorBorderW = numVal(v.editorBorderW, 1)
        editorAccentW = numVal(v.editorAccentW, 3)
        showEditorAccent = v.showEditorAccent !== false
        colorParent = v.colorParent || "#111113"
        colorChild = v.colorChild || "#111113"
        colorSelected = v.colorSelected || "#27272A"
        colorText = v.colorText || "#E4E4E7"
        colorMuted = v.colorMuted || "#A1A1AA"
        colorLive = v.colorLive || "#22C55E"
        colorBorder = v.colorBorder || "#3F3F46"
        colorSelectBorder = v.colorSelectBorder || "#E4E4E7"
        colorEditor = v.colorEditor || "#0F2744"
        colorEditorBorder = v.colorEditorBorder || "#3B82F6"
        colorEditorAccent = v.colorEditorAccent || v.colorEditorBorder || "#3B82F6"
        colorScreen = v.colorScreen || "#00000000"
        screenImage = v.screenImage || ""
        parkEmptyInUnmapped = v.parkEmptyInUnmapped === true
        applySections(v.sections)
    }

    property string savedCatalog: ""

    function rememberCatalog() {
        savedCatalog = JSON.stringify(catalogPayload())
    }

    function hasUnsaved() {
        return savedCatalog.length > 0 && JSON.stringify(catalogPayload()) !== savedCatalog
    }

    function saveParkEmpty(value) {
        parkEmptyInUnmapped = !!value
        saveCatalog()
    }

    function saveCatalog() {
        var ok = false
        if (moduleModel && claimDeviceName.length)
            ok = moduleModel.saveCatalogConfig(claimDeviceName, device ? device.guid : "", JSON.stringify(catalogPayload()))
        if (ok) {
            rememberCatalog()
            _saveGate.announce(true, "Saved to the module file.")
            if (backend)
                backend.noteSave("Saved the display look to " + moduleModel.lastSavedPath())
        } else {
            _saveGate.announce(false, "Not written. It is still only on this screen.")
            if (backend)
                backend.noteSave("The display look was not written.")
        }
    }

    property bool _leaveOnly: false
    property bool _leaveAfterPane: false
    signal leaveResolved()
    signal leaveCancelled()

    function afterPaneClosedForLeave() {
        if (!_leaveAfterPane)
            return
        _leaveAfterPane = false
        requestLeave()
    }

    function requestLeave() {
        if (paneHid >= 0 && _catalog.paneDirty()) {
            _leaveAfterPane = true
            panePending = { "close": true }
            _paneLeave.ask("This control has changes that are not saved.")
            return
        }
        if (paneHid >= 0)
            closeAdvancedPane()
        if (!hasUnsaved()) {
            leaveResolved()
            return
        }
        _leaveOnly = true
        _saveGate.detail = "Display options are not saved. Leave this device and they will be lost."
        _saveGate.ask()
    }

    function requestClose() {
        _leaveOnly = false
        if (hasUnsaved()) {
            _saveGate.detail = "Display options are not saved. Close this panel and they will be lost."
            _saveGate.ask()
            return
        }
        closePanel()
    }

    function resetCatalog() {
        applyDefaults()
        toastText = "Options have been reset"
        _savedToast.open()
    }

    function openSequence(hid, seq, row) {
        if (hid < 0 || seq < 0 || editorLocked)
            return
        if (_root.editingHid === hid && _root.editingSeq === seq) {
            closeEditor()
            return
        }
        if (_root.editingHid >= 0)
            _catalog.refreshOpenRow(_root.editingHid)
        _root.editingSeq = seq
        _root.editingHid = hid
        selectHid(hid)
        armReveal(row)
    }

    function selectHid(hid) {
        if (!uiState || !device || hid < 0)
            return
        var ident = device.inputIdentifier(hid)
        if (!ident)
            return
        uiState.setCurrentInput(ident, hid)
    }

    function bumpReveal() {
        if (revealOnceRow >= 0)
            _revealTimer.restart()
    }

    function armReveal(row) {
        if (row < 0)
            return
        revealOnceRow = row
        revealTries = 0
        _revealTimer.restart()
    }

    Timer {
        id: _revealTimer
        interval: 0
        onTriggered: {
            var row = revealOnceRow
            var item = row >= 0 ? _list.itemAtIndex(row) : null
            var editorOpen = item && _root.editingHid >= 0
            var editorLaidOut = !item || !item.hostsEditor || item.height >= parentHeight + 80
            if (editorOpen && !editorLaidOut && revealTries < 8) {
                revealTries += 1
                _revealTimer.restart()
                return
            }
            revealOnceRow = -1
            revealRow(row)
        }
    }

    function revealRow(row) {
        if (row < 0)
            return
        Qt.callLater(function() {
            if (row >= _list.count)
                return
            var item = _list.itemAtIndex(row)
            if (!item) {
                _list.positionViewAtIndex(row, ListView.Contain)
                return
            }
            var top = item.y - _list.contentY
            var viewH = _list.height
            if (viewH <= 0)
                return
            if (item.height >= viewH) {
                if (top < -1 || top > 1)
                    _list.positionViewAtIndex(row, ListView.Beginning)
                return
            }
            if (top < 0 || top + item.height > viewH)
                _list.positionViewAtIndex(row, ListView.Contain)
        })
    }

    function showHid(hid) {
        if (hid < 0)
            return
        let row = _catalog.rowForDeviceIndex(hid)
        if (row < 0)
            return
        if (_list.currentIndex !== row)
            _list.currentIndex = row
        if (_root.editingHid === hid)
            return
        revealRow(row)
    }

    function openEditor(hid) {
        if (hid < 0 || editorLocked)
            return
        if (_root.editingHid >= 0 && _root.editingHid !== hid)
            _catalog.refreshOpenRow(_root.editingHid)
        var opening = _root.editingHid !== hid
        _root.editingHid = hid
        selectHid(hid)
        if (opening)
            armReveal(_catalog.rowForDeviceIndex(hid))
    }

    function closeEditor() {
        var hid = _root.editingHid
        var reset = false
        if (hid >= 0)
            reset = _catalog.refreshOpenRow(hid)
        _root.editingHid = -1
        _root.editingSeq = -1
        if (reset)
            revealRow(_catalog.rowForDeviceIndex(hid))
    }

    function rowX(total, align, left, right, pct) {
        var w = rowW(total, align, left, right, pct)
        if (align === "center")
            return Math.max(0, Math.round((total - w) / 2))
        if (align === "right")
            return Math.max(0, total - w - right)
        return left
    }

    function rowW(total, align, left, right, pct) {
        if (align === "center")
            return Math.max(120, Math.round(total * pct / 100))
        return Math.max(120, total - left - right)
    }

    function leafX(total) {
        return rowX(total, childAlign, childLeft, childRight, childWidthPct)
    }

    function leafW(total) {
        return rowW(total, childAlign, childLeft, childRight, childWidthPct)
    }

    function parentX(total) {
        return rowX(total, parentAlign, parentLeft, parentRight, parentWidthPct)
    }

    function parentW(total) {
        return rowW(total, parentAlign, parentLeft, parentRight, parentWidthPct)
    }

    function editorX(total) {
        return rowX(total, editorAlign, editorIndent, editorRight, editorWidthPct)
    }

    function editorW(total) {
        return rowW(total, editorAlign, editorIndent, editorRight, editorWidthPct)
    }

    function groupX(total) {
        return rowX(total, groupAlign, groupLeft, groupRight, groupWidthPct)
    }

    function groupW(total) {
        return rowW(total, groupAlign, groupLeft, groupRight, groupWidthPct)
    }

    function clampPane(width) {
        var reserved = 400
        if (showPanel)
            reserved += 360
        var maxW = Math.max(420, _root.width - reserved)
        return Math.max(420, Math.min(maxW, Math.round(width)))
    }

    function openAdvancedPane(hid) {
        requestPane(hid, -1)
    }

    function requestPane(hid, seq) {
        if (paneHid === hid && paneSeq === seq && paneHid >= 0)
            return
        if (paneHid >= 0 && _catalog.paneDirty()) {
            panePending = { "hid": hid, "seq": seq, "close": false }
            _paneLeave.ask("This control has changes that are not saved.")
            return
        }
        startPane(hid, seq)
    }

    function startPane(hid, seq) {
        var count = _catalog.beginPane(hid, seq)
        paneHid = hid
        paneSeq = seq
        paneName = _catalog.controlLabel(hid)
        paneSummary = seq < 0 && count < 1 ? "New action" : "Editing this action"
        advancedOpen = true
        selectHid(hid)
    }

    function acceptPane() {
        if (_catalog.paneDirty()) {
            var seq = _catalog.commitPane()
            if (seq >= 0)
                paneSeq = seq
            paneSummary = "Editing this action"
            _catalog.reload()
        }
        if (closeAfterOk)
            closeAdvancedPane()
    }

    function closeAdvancedPane() {
        _catalog.endPane()
        paneHid = -1
        paneSeq = -1
        paneName = ""
        paneSummary = ""
        advancedOpen = editorWindowOpen
        if (!advancedOpen)
            _catalog.reload()
    }

    function requestClosePane() {
        if (paneHid >= 0 && _catalog.paneDirty()) {
            panePending = { "close": true }
            _paneLeave.ask("This control has changes that are not saved.")
            return
        }
        closeAdvancedPane()
    }

    Connections {
        target: signal
        function onSetInputIndex(index) { showHid(index) }
        function onInputItemChanged(itemIndex) {
            if (_root.advancedOpen)
                return
            if (_root.editingHid >= 0) {
                _catalog.noteOpenRow(itemIndex)
                return
            }
            _catalog.reload()
        }
        function onAdvancedEditorChanged(open) {
            _root.editorWindowOpen = open
            _root.advancedOpen = open || _root.paneHid >= 0
            if (!_root.advancedOpen)
                _catalog.reload()
        }
    }

    component FoldSection: ColumnLayout {
        id: fold
        property string title: ""
        property bool open: false
        signal toggled(bool value)
        default property alias body: _body.data
        Layout.fillWidth: true
        spacing: 4

        Rectangle {
            Layout.fillWidth: true
            height: 26
            color: "#27272A"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6
                Label {
                    text: fold.open ? "\u25BC" : "\u25B6"
                    color: "#E4E4E7"
                    font.pixelSize: 10
                }
                Label {
                    text: fold.title
                    color: "#E4E4E7"
                    font.pixelSize: 11
                    font.bold: true
                    Layout.fillWidth: true
                }
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: fold.toggled(!fold.open)
            }
        }
        ColumnLayout {
            id: _body
            visible: fold.open
            Layout.fillWidth: true
            spacing: 4
        }
    }

    component TrackSpin: SpinBox {
        property int source: 0
        signal userSet(int value)
        editable: true
        Component.onCompleted: value = source
        onSourceChanged: if (value !== source) value = source
        onValueModified: userSet(value)
    }

    component FlagBox: CheckBox {
        property bool source: false
        signal userSet(bool value)
        Component.onCompleted: checked = source
        onSourceChanged: if (!pressed) checked = source
        onClicked: userSet(checked)
    }

    component AlignFields: ColumnLayout {
        property string align: "left"
        property int fromLeft: 0
        property int fromRight: 0
        property int widthPct: 100
        signal edited(string align, int fromLeft, int fromRight, int widthPct)
        onAlignChanged: if (_alignPick) _alignPick.currentIndex = _alignPick.pick(align)
        Layout.fillWidth: true
        spacing: 4

        RowLayout {
            Label { text: "Alignment"; color: "#E4E4E7"; Layout.preferredWidth: 70 }
            ComboBox {
                id: _alignPick
                Layout.fillWidth: true
                textRole: "label"
                model: [
                    { "label": "Left", "value": "left" },
                    { "label": "Center", "value": "center" },
                    { "label": "Right", "value": "right" }
                ]
                function pick(value) {
                    if (value === "center")
                        return 1
                    if (value === "right")
                        return 2
                    return 0
                }
                function stored() {
                    if (currentIndex === 1)
                        return "center"
                    if (currentIndex === 2)
                        return "right"
                    return "left"
                }
                Component.onCompleted: currentIndex = pick(align)
                onActivated: edited(stored(), fromLeft, fromRight, widthPct)
            }
        }
        RowLayout {
            visible: align !== "center"
            Label { text: "Left"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 800; stepSize: 8; source: fromLeft; onUserSet: (v) => { edited(align, v, fromRight, widthPct); }}
        }
        RowLayout {
            visible: align !== "center"
            Label { text: "Right"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 800; stepSize: 8; source: fromRight; onUserSet: (v) => { edited(align, fromLeft, v, widthPct); }}
        }
        RowLayout {
            visible: align === "center"
            Label { text: "Width %"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 20; to: 100; source: widthPct; onUserSet: (v) => { edited(align, fromLeft, fromRight, v); }}
        }
    }

    component PadFields: ColumnLayout {
        property string shape: "box"
        property int size: 8
        property int padTop: 0
        property int padRight: 8
        property int padBottom: 0
        property int padLeft: 8
        signal edited(string shape, int size, int padTop, int padRight, int padBottom, int padLeft)
        onShapeChanged: if (_shapePick) _shapePick.currentIndex = _shapePick.pick(shape)
        Layout.fillWidth: true
        spacing: 4

        RowLayout {
            Label { text: "Shape"; color: "#E4E4E7"; Layout.preferredWidth: 70 }
            ComboBox {
                id: _shapePick
                Layout.fillWidth: true
                model: ["Same on all sides", "Each side"]
                function pick(value) { return value === "sides" ? 1 : 0 }
                Component.onCompleted: currentIndex = pick(shape)
                onActivated: {
                    if (currentIndex === 0)
                        edited("box", size, size, size, size, size)
                    else
                        edited("sides", size, size, size, size, size)
                }
            }
        }
        RowLayout {
            visible: shape !== "sides"
            Label { text: "Size"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 80; source: size; onUserSet: (v) => { edited("box", v, v, v, v, v); }}
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Top"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 80; source: padTop; onUserSet: (v) => { edited("sides", size, v, padRight, padBottom, padLeft); }}
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Right"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 80; source: padRight; onUserSet: (v) => { edited("sides", size, padTop, v, padBottom, padLeft); }}
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Bottom"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 80; source: padBottom; onUserSet: (v) => { edited("sides", size, padTop, padRight, v, padLeft); }}
        }
        RowLayout {
            visible: shape === "sides"
            Label { text: "Left"; color: "#E4E4E7"; Layout.fillWidth: true }
            TrackSpin { from: 0; to: 80; source: padLeft; onUserSet: (v) => { edited("sides", size, padTop, padRight, padBottom, v); }}
        }
    }

    component ColorPick: RowLayout {
        property string label: ""
        property color swatch: "#111111"
        property string target: ""
        Layout.fillWidth: true
        Label {
            text: label
            color: "#E4E4E7"
            wrapMode: Text.WordWrap
            Layout.preferredWidth: 150
            Layout.maximumWidth: 160
        }
        Button {
            Layout.fillWidth: true
            text: "Choose…"
            onClicked: { _colorTarget = target; _colorDlg.selectedColor = swatch; _colorDlg.open() }
            background: Rectangle { color: swatch; border.color: "#3F3F46"; border.width: 1; radius: 3 }
            contentItem: Label { text: parent.text; color: "#111111"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                anchors.fill: parent
                visible: _root.colorScreen !== "#00000000"
                color: _root.colorScreen
            }
            Image {
                anchors.fill: parent
                visible: _root.screenImage.length > 0
                source: _root.screenImage
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
            }

            ColumnLayout {
            anchors.fill: parent
            spacing: 6

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: padEdge(listPadShape, listPad, listPadLeft)
                Layout.rightMargin: padEdge(listPadShape, listPad, listPadRight)
                Layout.topMargin: 8
                Label { text: "Type"; color: colorMuted }
                ComboBox {
                    id: _typeBox
                    Layout.preferredWidth: 180
                    model: ["All types", "Map to vJoy", "Map to keyboard", "Map to mouse", "Map to Xbox", "Macro", "Change mode", "Other", "Unmapped"]
                    onActivated: {
                        var tags = ["all", "vjoy", "keyboard", "mouse", "xbox", "macro", "mode", "other", "unmapped"]
                        _catalog.typeFilter = tags[currentIndex]
                    }
                }
                Label { text: "Destination"; color: colorMuted }
                OutputModuleDevices { id: _destModules }
                ComboBox {
                    id: _destBox
                    visible: _destModules.hasValidVJoyDevices
                    Layout.fillWidth: visible
                    model: _catalog.destChoices
                    onActivated: {
                        _catalog.destFilter = currentText === "All devices" ? "all" : currentText
                    }
                }
                Label {
                    visible: !_destModules.hasValidVJoyDevices
                    Layout.fillWidth: true
                    text: "No output module claimed"
                    color: colorMuted
                }
            }

            JGListView {
                id: _list
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.leftMargin: padEdge(listPadShape, listPad, listPadLeft)
                Layout.rightMargin: padEdge(listPadShape, listPad, listPadRight)
                Layout.topMargin: padEdge(listPadShape, listPad, listPadTop)
                Layout.bottomMargin: padEdge(listPadShape, listPad, listPadBottom)
                scrollbarAlwaysVisible: true
                spacing: 0
                highlightFollowsCurrentItem: false
                highlightMoveDuration: {
                    if (!_highlightSpeed)
                        return 150
                    if (_highlightSpeed.speed === "Fast")
                        return 0
                    if (_highlightSpeed.speed === "Medium")
                        return 70
                    return 150
                }
                model: _catalog
                property int editingHid: _root.editingHid
                property bool catalogLocked: _root.editorLocked
                property bool catalogIsOutput: _root.isOutput
                property var live: _liveState
                property var catalogModel: _catalog
                property int parentH: _root.parentHeight
                property int childH: _root.childHeight
                property bool kidsOn: _root.showChildren
                property int quickHid: _root.quickHid
                property int quickSeq: _root.quickSeq
                function openAdvanced(hid) {
                    _root.openAdvancedPane(hid)
                }
                property bool barsOn: _root.showLiveBars
                property bool ledsOn: _root.showLeds
                property bool summaryOn: _root.showSummary
                property int pFont: _root.parentFont
                property int cFont: _root.childFont
                property int sFont: _root.summaryFont
                property bool pBold: _root.parentBold
                property int rowRad: _root.rowRadius
                property int nameW: _root.nameColW
                property int childNameW: _root.childNameColW
                property int innerPad: _root.rowInnerPad
                property int edIndent: _root.editorIndent
                property int edPad: _root.editorPad
                property int edGap: _root.editorGap
                property int edRad: _root.editorRadius
                property int edBorderW: _root.editorBorderW
                property int edAccentW: _root.editorAccentW
                property bool edAccentOn: _root.showEditorAccent
                property color cParent: _root.colorParent
                property color cChild: _root.colorChild
                property color cSel: _root.colorSelected
                property color cText: _root.colorText
                property color cMuted: _root.colorMuted
                property color cLive: _root.colorLive
                property color cBorder: _root.colorBorder
                property color cSelBorder: _root.colorSelectBorder
                property color cEditor: _root.colorEditor
                property color cEditorEdge: _root.colorEditorBorder
                property color cEditorAccent: _root.colorEditorAccent

                function openRow(hid, seq, row) { _root.openSequence(hid, seq, row) }

                delegate: Item {
                    id: _row
                    required property int index
                    required property string rowKind
                    required property string name
                    required property string summary
                    required property string typeLabel
                    required property string destLabel
                    required property string kind
                    required property int hwId
                    required property int deviceIndex
                    required property int bindingCount
                    required property int indent
                    required property int sequenceIndex
                    required property bool simple
                    property var lv: ListView.view
                    readonly property bool isLeaf: rowKind === "leaf"
                    readonly property bool groupStart: rowKind === "group" || rowKind === "unmapped"
                    readonly property int kidCount: groupStart ? lv.catalogModel.leafRun(index) : 0
                    readonly property int shownKids: lv.kidsOn ? kidCount : 0
                    readonly property int gPadT: groupStart ? _root.padEdge(_root.groupPadShape, _root.groupPad, _root.groupPadTop) : 0
                    readonly property int gPadB: groupStart ? _root.padEdge(_root.groupPadShape, _root.groupPad, _root.groupPadBottom) : 0
                    readonly property int gPadL: (groupStart || isLeaf) ? _root.padEdge(_root.groupPadShape, _root.groupPad, _root.groupPadLeft) : 0
                    readonly property int gPadR: (groupStart || isLeaf) ? _root.padEdge(_root.groupPadShape, _root.groupPad, _root.groupPadRight) : 0
                    readonly property int topGap: {
                        if (hideLeaf)
                            return 0
                        if (isLeaf)
                            return _root.groupInside
                        if (rowKind === "unmapped-header")
                            return index > 0 ? _root.unmappedGap : 0
                        if (index > 0)
                            return _root.groupBetween + gPadT
                        return gPadT
                    }
                    readonly property bool endOfCard: isLeaf && lv.catalogModel.lastLeaf(index)
                    readonly property int bottomGap: {
                        if (hideLeaf)
                            return 0
                        if (groupStart && shownKids === 0)
                            return gPadB
                        if (endOfCard)
                            return gPadB
                        return 0
                    }
                    readonly property int boxX: (groupStart || isLeaf) ? _root.groupX(width) + gPadL : 0
                    readonly property int boxW: {
                        if (!(groupStart || isLeaf))
                            return width
                        return Math.max(40, _root.groupW(width) - gPadL - gPadR)
                    }
                    width: lv.width - 12
                    readonly property bool isGroup: rowKind === "group" || rowKind === "unmapped"
                    readonly property bool expanded: isGroup && deviceIndex === lv.editingHid && deviceIndex >= 0
                    readonly property int bodyH: isLeaf ? lv.childH : lv.parentH
                    readonly property bool hideLeaf: isLeaf && !lv.kidsOn
                    height: hideLeaf ? 0 : (topGap + bodyH + bottomGap)
                    visible: !hideLeaf

                    readonly property bool selected: index === lv.currentIndex || expanded
                    property int liveStamp: lv.live.stamp
                    property string inputKind: (liveStamp >= 0 && deviceIndex >= 0) ? lv.live.kindAt(deviceIndex) : ""
                    property real liveValue: (liveStamp >= 0 && deviceIndex >= 0) ? lv.live.valueAt(deviceIndex) : 0
                    readonly property bool ledOn: (inputKind === "button" || inputKind === "hat") && liveValue > 0.5
                    readonly property bool axisRow: kind === "axis"

                    Rectangle {
                        visible: groupStart && _root.colorGroup !== "#00000000" && _root.colorGroup !== "transparent"
                        z: -1
                        x: _root.groupX(_row.width)
                        y: index > 0 ? _root.groupBetween : 0
                        width: Math.max(0, _root.groupW(_row.width))
                        height: gPadT + (groupStart ? bodyH : lv.parentH) + (shownKids * (_root.groupInside + lv.childH)) + gPadB
                        radius: _root.groupRadius
                        color: _root.colorGroup
                    }

                    Rectangle {
                        id: _header
                        y: topGap
                        x: boxX + (isLeaf ? _root.leafX(boxW) : _root.parentX(boxW))
                        width: isLeaf ? _root.leafW(boxW) : _root.parentW(boxW)
                        height: isLeaf ? lv.childH : bodyH
                        radius: isLeaf ? _root.childRadius : lv.rowRad
                        border.width: selected ? 2 : 1
                        border.color: selected ? lv.cSelBorder : lv.cBorder
                        color: {
                            if (ledOn)
                                return Qt.rgba(lv.cLive.r, lv.cLive.g, lv.cLive.b, selected ? 0.55 : 0.28)
                            if (selected)
                                return lv.cSel
                            if (rowKind === "unmapped-header")
                                return "#18181B"
                            return isLeaf ? lv.cChild : lv.cParent
                        }

                        Rectangle {
                            visible: lv.barsOn && axisRow && rowKind === "group"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            y: lv.parentH - height - 1
                            height: 5
                            color: lv.cBorder
                            Rectangle {
                                width: {
                                    liveStamp
                                    return Math.max(0, Math.min(parent.width, parent.width * ((liveValue + 1.0) * 0.5)))
                                }
                                height: parent.height
                                color: lv.cLive
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            anchors.rightMargin: 64
                            enabled: deviceIndex >= 0
                            onClicked: {
                                lv.currentIndex = index
                                lv.syncSelection()
                                if (deviceIndex < 0)
                                    return
                                if (rowKind === "leaf")
                                    _root.requestPane(deviceIndex, sequenceIndex)
                                else if (rowKind === "group" || rowKind === "unmapped")
                                    _root.requestPane(deviceIndex, -1)
                            }
                        }

                        RowLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            height: isLeaf ? parent.height : lv.parentH
                            anchors.leftMargin: isLeaf
                                ? _root.padEdge(_root.childPadShape, _root.childPad, _root.childPadLeft)
                                : _root.padEdge(_root.parentPadShape, _root.parentPad, _root.parentPadLeft)
                            anchors.rightMargin: isLeaf
                                ? _root.padEdge(_root.childPadShape, _root.childPad, _root.childPadRight)
                                : _root.padEdge(_root.parentPadShape, _root.parentPad, _root.parentPadRight)
                            anchors.topMargin: isLeaf
                                ? _root.padEdge(_root.childPadShape, _root.childPad, _root.childPadTop)
                                : _root.padEdge(_root.parentPadShape, _root.parentPad, _root.parentPadTop)
                            anchors.bottomMargin: isLeaf
                                ? _root.padEdge(_root.childPadShape, _root.childPad, _root.childPadBottom)
                                : _root.padEdge(_root.parentPadShape, _root.parentPad, _root.parentPadBottom)
                            spacing: 8

                            Rectangle {
                                visible: lv.ledsOn && (kind === "button" || kind === "hat")
                                width: 10
                                height: 10
                                radius: 5
                                color: ledOn ? lv.cLive : lv.cBorder
                            }

                            Label {
                                text: rowKind === "leaf" ? typeLabel : name
                                color: lv.cText
                                font.bold: rowKind !== "leaf" && lv.pBold
                                font.pixelSize: rowKind === "leaf" ? lv.cFont : lv.pFont
                                elide: Text.ElideRight
                                Layout.preferredWidth: rowKind === "leaf" ? lv.childNameW : lv.nameW
                            }
                            Label {
                                visible: lv.summaryOn || rowKind === "leaf"
                                text: rowKind === "leaf" ? destLabel : (rowKind === "unmapped-header" ? summary : (rowKind === "unmapped" ? "Not bound" : summary))
                                color: lv.cMuted
                                font.pixelSize: lv.sFont
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                                wrapMode: Text.NoWrap
                            }
                            Button {
                                visible: isLeaf && !lv.catalogLocked
                                text: "Delete"
                                implicitWidth: 70
                                implicitHeight: 28
                                z: 2
                                onClicked: lv.catalogModel.removeSequence(deviceIndex, sequenceIndex)
                            }
                            Button {
                                visible: (rowKind === "group" || rowKind === "unmapped") && !lv.catalogLocked
                                text: "Add Action"
                                implicitWidth: 100
                                implicitHeight: 28
                                z: 2
                                onClicked: lv.openAdvanced(deviceIndex)
                            }
                        }
                    }
                }

                function syncSelection() {
                    if (!uiState || !device || currentIndex < 0 || _root.editorLocked)
                        return
                    var hid = _catalog.deviceIndexAt(currentIndex)
                    if (hid < 0)
                        return
                    _root.selectHid(hid)
                }

                onCurrentIndexChanged: syncSelection()
            }

            Label {
                visible: _catalog.count === 0
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: colorMuted
                horizontalAlignment: Text.AlignHCenter
                text: "This window only shows what the input module passes.\nRight-click the card → Configure input module, press the controls to claim, then Save module."
            }
            }
        }

        Rectangle {
            visible: _root.paneHid >= 0
            Layout.preferredWidth: 6
            Layout.fillHeight: true
            color: _paneGrip.pressed || _paneGrip.containsMouse ? "#3B82F6" : "#3F3F46"

            MouseArea {
                id: _paneGrip
                anchors.fill: parent
                anchors.leftMargin: -3
                anchors.rightMargin: -3
                hoverEnabled: true
                cursorShape: Qt.SplitHCursor
                preventStealing: true
                property real originX: 0
                property int originW: 560
                onPressed: (mouse) => {
                    originX = mapToItem(_root, mouse.x, mouse.y).x
                    originW = _root.paneWidth
                }
                onPositionChanged: (mouse) => {
                    if (!pressed)
                        return
                    var x = mapToItem(_root, mouse.x, mouse.y).x
                    _root.paneWidth = _root.clampPane(originW - (x - originX))
                }
                onReleased: _panePlacement.setActionPaneWidth(_root.paneWidth)
            }
        }

        Rectangle {
            visible: _root.paneHid >= 0
            Layout.preferredWidth: _root.paneWidth
            Layout.minimumWidth: 420
            Layout.maximumWidth: _root.clampPane(_root.paneWidth)
            Layout.fillHeight: true
            color: "#18181B"
            border.color: "#3F3F46"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                RowLayout {
                    Label {
                        text: _root.paneName.length ? _root.paneName : "Action Editor"
                        color: "#E4E4E7"
                        font.bold: true
                        font.pixelSize: 16
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Button {
                        text: "×"
                        implicitWidth: 28
                        onClicked: _root.requestClosePane()
                    }
                }
                Label {
                    visible: _root.paneSummary.length > 0
                    text: _root.paneSummary
                    color: "#9AA4B2"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                InputConfiguration {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    holdModel: true
                    inputItemModel: _catalog.paneModel
                }
                RowLayout {
                    CheckBox {
                        text: "Close pane after OK"
                        property bool shown: _root.closeAfterOk
                        onShownChanged: if (!pressed) checked = shown
                        Component.onCompleted: checked = shown
                        onClicked: {
                            _root.closeAfterOk = checked
                            if (_root.paneChoiceReady)
                                _panePlacement.setClosePaneAfterOk(checked)
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Button {
                        text: "OK"
                        implicitWidth: 72
                        highlighted: true
                        onClicked: _root.acceptPane()
                    }
                }
            }
        }

        Rectangle {
            visible: _root.showPanel
            Layout.preferredWidth: 360
            Layout.maximumWidth: 360
            Layout.fillHeight: true
            color: "#18181B"
            border.color: "#3F3F46"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                RowLayout {
                    Label {
                        text: "Input Configuration — Display Editor"
                        color: "#E4E4E7"
                        font.bold: true
                        font.pixelSize: 13
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "×"
                        implicitWidth: 28
                        onClicked: _root.requestClose()
                    }
                }
                RowLayout {
                    spacing: 8
                    Button { text: "Open all"; onClicked: setAllSections(true) }
                    Button { text: "Close all"; onClicked: setAllSections(false) }
                    Item { Layout.fillWidth: true }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ColumnLayout {
                        width: 330
                        spacing: 12

                        FoldSection {
                            title: "Screen"
                            open: openScreen
                            onToggled: (v) => { openScreen = v }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Background"; color: "#E4E4E7"; Layout.preferredWidth: 110 }
                                Button {
                                    Layout.fillWidth: true
                                    text: colorScreen === "#00000000" ? "None" : "Choose…"
                                    onClicked: {
                                        _colorTarget = "screen"
                                        _colorDlg.selectedColor = colorScreen === "#00000000" ? "#111113" : colorScreen
                                        _colorDlg.open()
                                    }
                                    background: Rectangle {
                                        color: colorScreen === "#00000000" ? "#27272A" : colorScreen
                                        border.color: "#3F3F46"
                                        border.width: 1
                                        radius: 3
                                    }
                                    contentItem: Label {
                                        text: parent.text
                                        color: "#F4F4F5"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                                Button {
                                    text: "Clear"
                                    enabled: colorScreen !== "#00000000"
                                    onClicked: colorScreen = "#00000000"
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Image"; color: "#E4E4E7"; Layout.preferredWidth: 110 }
                                Button {
                                    Layout.fillWidth: true
                                    text: screenImage.length ? "Change…" : "Choose…"
                                    onClicked: _screenImageDlg.open()
                                }
                                Button {
                                    text: "Clear"
                                    enabled: screenImage.length > 0
                                    onClicked: screenImage = ""
                                }
                            }
                            Label {
                                visible: screenImage.length > 0
                                text: "The image covers the color."
                                color: "#A1A1AA"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                        FoldSection {
                            title: "Shown"
                            open: openShown
                            onToggled: (v) => { openShown = v }
                            FlagBox { text: "Show child rows"; source: showChildren; onUserSet: (v) => { showChildren = v } }
                            FlagBox { text: "Show live bars"; source: showLiveBars; onUserSet: (v) => { showLiveBars = v } }
                            ColorPick { label: "Live bar"; swatch: colorLive; target: "live" }
                            FlagBox { text: "Show LED dots"; source: showLeds; onUserSet: (v) => { showLeds = v } }
                            FlagBox { text: "Show summary"; source: showSummary; onUserSet: (v) => { showSummary = v } }
                            RowLayout {
                                Label { text: "Summary size"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 9; to: 20; source: summaryFont; onUserSet: (v) => { summaryFont = v; }}
                            }
                        }
                        FoldSection {
                            title: "List"
                            open: openList
                            onToggled: (v) => { openList = v }
                            RowLayout {
                                Label { text: "Space between groups"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 48; source: groupBetween; onUserSet: (v) => { groupBetween = v; }}
                            }
                            RowLayout {
                                Label { text: "Space before Unmapped"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 80; source: unmappedGap; onUserSet: (v) => { unmappedGap = v; }}
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: listPadShape
                                size: listPad
                                padTop: listPadTop
                                padRight: listPadRight
                                padBottom: listPadBottom
                                padLeft: listPadLeft
                                onEdited: function(shape, size, padTop, padRight, padBottom, padLeft) {
                                    listPadShape = shape
                                    listPad = size
                                    listPadTop = padTop
                                    listPadRight = padRight
                                    listPadBottom = padBottom
                                    listPadLeft = padLeft
                                }
                            }
                        }
                        FoldSection {
                            title: "Group"
                            open: openGroup
                            onToggled: (v) => { openGroup = v }
                            RowLayout {
                                Label { text: "Space inside the group"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 48; source: groupInside; onUserSet: (v) => { groupInside = v; }}
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: groupPadShape
                                size: groupPad
                                padTop: groupPadTop
                                padRight: groupPadRight
                                padBottom: groupPadBottom
                                padLeft: groupPadLeft
                                onEdited: function(shape, size, padTop, padRight, padBottom, padLeft) {
                                    groupPadShape = shape
                                    groupPad = size
                                    groupPadTop = padTop
                                    groupPadRight = padRight
                                    groupPadBottom = padBottom
                                    groupPadLeft = padLeft
                                }
                            }
                            AlignFields {
                                align: groupAlign
                                fromLeft: groupLeft
                                fromRight: groupRight
                                widthPct: groupWidthPct
                                onEdited: function(align, fromLeft, fromRight, widthPct) {
                                    groupAlign = align
                                    groupLeft = fromLeft
                                    groupRight = fromRight
                                    groupWidthPct = widthPct
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: groupRadius; onUserSet: (v) => { groupRadius = v; }}
                            }
                            ColorPick { label: "Color"; swatch: colorGroup; target: "group" }
                        }
                        FoldSection {
                            title: "Parent row"
                            open: openParent
                            onToggled: (v) => { openParent = v }
                            RowLayout {
                                Label { text: "Height"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 36; to: 80; source: parentHeight; onUserSet: (v) => { parentHeight = v; }}
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: parentPadShape
                                size: parentPad
                                padTop: parentPadTop
                                padRight: parentPadRight
                                padBottom: parentPadBottom
                                padLeft: parentPadLeft
                                onEdited: function(shape, size, padTop, padRight, padBottom, padLeft) {
                                    parentPadShape = shape
                                    parentPad = size
                                    parentPadTop = padTop
                                    parentPadRight = padRight
                                    parentPadBottom = padBottom
                                    parentPadLeft = padLeft
                                }
                            }
                            AlignFields {
                                align: parentAlign
                                fromLeft: parentLeft
                                fromRight: parentRight
                                widthPct: parentWidthPct
                                onEdited: function(align, left, right, widthPct) {
                                    parentAlign = align
                                    parentLeft = left
                                    parentRight = right
                                    parentWidthPct = widthPct
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: rowRadius; onUserSet: (v) => { rowRadius = v; }}
                            }
                            RowLayout {
                                Label { text: "Name width"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 80; to: 360; stepSize: 10; source: nameColW; onUserSet: (v) => { nameColW = v; }}
                            }
                            ColorPick { label: "Row color"; swatch: colorParent; target: "parent" }
                            ColorPick { label: "Line around the row"; swatch: colorBorder; target: "border" }
                            Label {
                                text: "The child row uses this line too."
                                color: "#A1A1AA"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                        FoldSection {
                            title: "Child row"
                            open: openChild
                            onToggled: (v) => { openChild = v }
                            RowLayout {
                                Label { text: "Height"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 24; to: 60; source: childHeight; onUserSet: (v) => { childHeight = v; }}
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: childPadShape
                                size: childPad
                                padTop: childPadTop
                                padRight: childPadRight
                                padBottom: childPadBottom
                                padLeft: childPadLeft
                                onEdited: function(shape, size, padTop, padRight, padBottom, padLeft) {
                                    childPadShape = shape
                                    childPad = size
                                    childPadTop = padTop
                                    childPadRight = padRight
                                    childPadBottom = padBottom
                                    childPadLeft = padLeft
                                }
                            }
                            AlignFields {
                                align: childAlign
                                fromLeft: childLeft
                                fromRight: childRight
                                widthPct: childWidthPct
                                onEdited: function(align, left, right, widthPct) {
                                    childAlign = align
                                    childLeft = left
                                    childRight = right
                                    childWidthPct = widthPct
                                }
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: childRadius; onUserSet: (v) => { childRadius = v; }}
                            }
                            RowLayout {
                                Label { text: "Name width"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 80; to: 360; stepSize: 10; source: childNameColW; onUserSet: (v) => { childNameColW = v; }}
                            }
                            ColorPick { label: "Row color"; swatch: colorChild; target: "child" }
                        }
                        FoldSection {
                            title: "Text"
                            open: openText
                            onToggled: (v) => { openText = v }
                            RowLayout {
                                Label { text: "Parent text size"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 10; to: 22; source: parentFont; onUserSet: (v) => { parentFont = v; }}
                            }
                            FlagBox { text: "Bold names"; source: parentBold; onUserSet: (v) => { parentBold = v } }
                            RowLayout {
                                Label { text: "Child text size"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 9; to: 20; source: childFont; onUserSet: (v) => { childFont = v; }}
                            }
                            ColorPick { label: "Text color"; swatch: colorText; target: "text" }
                            ColorPick { label: "Muted text"; swatch: colorMuted; target: "muted" }
                        }
                        FoldSection {
                            title: "Selection"
                            open: openSelection
                            onToggled: (v) => { openSelection = v }
                            ColorPick { label: "Fill of a selected row"; swatch: colorSelected; target: "selected" }
                            ColorPick { label: "Line around a selected row"; swatch: colorSelectBorder; target: "selectBorder" }
                        }
                        FoldSection {
                            title: "Editor"
                            open: openEditor
                            onToggled: (v) => { openEditor = v }
                            AlignFields {
                                align: editorAlign
                                fromLeft: editorIndent
                                fromRight: editorRight
                                widthPct: editorWidthPct
                                onEdited: function(align, left, right, widthPct) {
                                    editorAlign = align
                                    editorIndent = left
                                    editorRight = right
                                    editorWidthPct = widthPct
                                }
                            }
                            Label { text: "Padding"; color: "#A1A1AA"; font.pixelSize: 11 }
                            PadFields {
                                shape: editorPadShape
                                size: editorPad
                                padTop: editorPadTop
                                padRight: editorPadRight
                                padBottom: editorPadBottom
                                padLeft: editorPadLeft
                                onEdited: function(shape, size, padTop, padRight, padBottom, padLeft) {
                                    editorPadShape = shape
                                    editorPad = size
                                    editorPadTop = padTop
                                    editorPadRight = padRight
                                    editorPadBottom = padBottom
                                    editorPadLeft = padLeft
                                }
                            }
                            RowLayout {
                                Label { text: "Gap below row"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 24; source: editorGap; onUserSet: (v) => { editorGap = v; }}
                            }
                            RowLayout {
                                Label { text: "Corner radius"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 16; source: editorRadius; onUserSet: (v) => { editorRadius = v; }}
                            }
                            RowLayout {
                                Label { text: "Border width"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 8; source: editorBorderW; onUserSet: (v) => { editorBorderW = v; }}
                            }
                            RowLayout {
                                Label { text: "Accent width"; color: "#E4E4E7"; Layout.fillWidth: true }
                                TrackSpin { from: 0; to: 12; source: editorAccentW; onUserSet: (v) => { editorAccentW = v; }}
                            }
                            FlagBox { text: "Show accent bar"; source: showEditorAccent; onUserSet: (v) => { showEditorAccent = v } }
                            ColorPick { label: "Fill"; swatch: colorEditor; target: "editor" }
                            ColorPick { label: "Border"; swatch: colorEditorBorder; target: "editorBorder" }
                            ColorPick { label: "Accent bar"; swatch: colorEditorAccent; target: "editorAccent" }
                        }

                    }
                }

                RowLayout {
                    spacing: 6
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        text: "Reset View\nto Default"
                        onClicked: resetCatalog()
                        contentItem: Text {
                            text: parent.text
                            color: "#FFFFFF"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            implicitHeight: 44
                            color: parent.down ? "#991B1B" : (parent.hovered ? "#EF4444" : "#DC2626")
                            border.width: 1
                            border.color: parent.hovered ? "#FCA5A5" : "#B91C1C"
                        }
                    }
                    Button {
                        id: _copyButton
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        text: "Copy View\nfrom…"
                        onClicked: {
                            refreshCopySources()
                            _copyMenu.popup(_copyButton, 0, _copyButton.height)
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#F4F4F5"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Button {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        text: "Save View\nSettings"
                        highlighted: true
                        onClicked: saveCatalog()
                        contentItem: Text {
                            text: parent.text
                            color: "#FFFFFF"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }
    }

    Menu {
        id: _copyMenu
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        width: 360

        MenuItem {
            text: "Replace this panel with the display settings from"
            enabled: false
            width: 360
        }
        MenuItem {
            text: "No other input module"
            enabled: false
            visible: _copySources.count === 0
            height: visible ? implicitHeight : 0
            width: 360
        }
        Instantiator {
            model: _copySources
            delegate: MenuItem {
                required property string label
                required property string name
                required property string guid
                text: label
                width: 360
                onTriggered: _root.copyCatalogFrom(name, guid)
            }
            onObjectAdded: (index, object) => _copyMenu.insertItem(_copyMenu.count, object)
            onObjectRemoved: (index, object) => _copyMenu.removeItem(object)
        }
    }

    DismissibleDialog {
        id: _saveGate
        onSaveChosen: {
            saveCatalog()
            if (hasUnsaved())
                return
            if (_leaveOnly) {
                _leaveOnly = false
                leaveResolved()
                return
            }
            closePanel()
        }
        onDiscardChosen: {
            loadCatalog()
            if (_leaveOnly) {
                _leaveOnly = false
                leaveResolved()
                return
            }
            closePanel()
        }
        onCancelled: {
            if (_leaveOnly) {
                _leaveOnly = false
                leaveCancelled()
            }
        }
    }

    Popup {
        id: _savedToast
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        dim: true
        Overlay.modal: Rectangle { color: "#66000000" }
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        padding: 18
        background: Rectangle {
            color: "#27272A"
            border.color: "#52525B"
            radius: 6
        }
        contentItem: Label {
            text: toastText
            color: "#F4F4F5"
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
        }
        Timer {
            id: _savedTimer
            interval: 2000
            onTriggered: _savedToast.close()
        }
        onOpened: _savedTimer.restart()
        onClosed: _savedTimer.stop()
    }
}
