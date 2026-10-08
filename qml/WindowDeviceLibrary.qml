// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Style
import Gremlin.Menus
import "helpers.js" as Helpers
import "device_library_open.js" as DeviceLibraryOpen

// The Device Library (10 Device Library): every device the program has
// known and its saved setups, with Copy, Swap and Change vJoy Output. Its
// model (context property deviceLibrary) is the only thing it talks to.
ApplicationWindow {
    id: _lib
    objectName: "deviceLibraryWindow"
    font.pixelSize: Style.fontSize
    font.family: Style.uiFont

    width: Style.fitWidth(Style.dp(1180), Screen)
    height: Style.fitHeight(Style.dp(720), Screen)
    minimumWidth: Style.fitWidth(Style.dp(860), Screen)
    minimumHeight: Style.fitHeight(Style.dp(520), Screen)
    color: Style.background
    U.Universal.theme: Style.theme
    title: "Device Library"

    readonly property var lib: typeof deviceLibrary !== "undefined" ? deviceLibrary : null
    readonly property var details: lib ? lib.details : ({})
    readonly property bool hasSel: details && details.key !== undefined
    readonly property bool isSetup: hasSel && details.kind === "setup"
    readonly property bool isDevice: hasSel && details.kind === "device"
    readonly property bool busy: lib ? lib.busy : false
    // The last change's outcome, shown above the status bar.
    property string message: ""
    property bool messageBad: false
    property bool renaming: false

    ToolWindowMemory {
        host: _lib
        name: "device-library"
        defaultWidth: Style.dp(1180)
        defaultHeight: Style.dp(720)
    }

    Component.onCompleted: if (lib) lib.refresh()
    onActiveChanged: if (active && lib && !busy) lib.refresh()

    // Opens on a device and, for the card menu items, its dialog (S2).
    function openOn(deviceName, guid, action) {
        if (!lib)
            return
        lib.refresh()
        var key = (deviceName.length || guid.length) ? lib.findDevice(deviceName, guid) : ""
        if (key.length)
            lib.select(key)
        else if (deviceName.length) {
            showMessage(deviceName + " isn't in the Device Library.", true)
            return
        }
        if (action === "copy")
            openCopy()
        else if (action === "swap")
            openSwap()
        else if (action === "output")
            openOutput()
    }

    function showMessage(text, bad) {
        message = text
        messageBad = bad
    }

    // What each change says when it is done.
    readonly property var doneText: ({
        "copy": "Copied. An autosave of the stick was kept first; Edit › Undo puts it back.",
        "swap": "Swapped. An autosave of each stick was kept first; Edit › Undo puts them back.",
        "output": "vJoy output changed. Edit › Undo puts it back.",
        "undo": "Put back from the autosave.",
        "import": "Device Pack added as a saved setup.",
        "export": "Saved setup exported.",
        "delete": "Deleted.",
        "tidy": "Library tidied.",
        "save": "Saved to the Device Library.",
        "settings": "Device Library Settings saved.",
        "remove": "Removed from the Library.",
        "deleteSetups": "Saved setups deleted. The stick keeps its settings.",
        "deleteMany": "Deleted.",
        "keep": "Kept as your own: the autosave limit never removes it.",
        "restore": "Restored. An autosave of the stick was kept first; Edit › Undo puts it back.",
        "exportCurrent": "Current setup exported."
    })

    Connections {
        target: _lib.lib
        function onResult(res) {
            var op = res.op
            if (op === "profiles" || op.indexOf("plan") === 0)
                return
            if (!res.ok) {
                _lib.showMessage(res.error || "That didn't work.", true)
                return
            }
            if (op === "rename" || op === "describe")
                return
            var text = _lib.doneText[op] || "Done."
            var more = (res.warnings || []).concat(res.notes || [])
            if (more.length)
                text += "  " + more.join("  ")
            _lib.showMessage(text, (res.warnings || []).length > 0)
        }
    }

    // | Actions (menus and the details' buttons)

    readonly property bool deviceConnected: hasSel && details.connected === true
    // Copy takes a saved setup, or a device's current settings (S22): on a
    // device with none here (deleted, from a pack), its newest saved setup.
    readonly property bool canCopy: !busy && hasSel && !several
        && (isSetup || details.hasCurrent === true || details.count > 0)
    // S12: what the device has now (a module file, or plugged in: its
    // bindings) can be saved; a Deleted or pack-only device has nothing.
    readonly property bool canSave: !busy && hasSel && !several && details.hasCurrent === true
    // S30: any stick with an id, plugged in or not.
    readonly property bool canOutput: !busy && hasSel && !several && (details.guid || "").length > 0
    // S15: a saved setup; a device not connected (Remove from Library); a
    // connected one's saved setups (Delete Saved Setups). S50: several.
    readonly property var picked: lib ? lib.selectedKeys : []
    readonly property bool several: picked.length > 1
    readonly property bool canDelete: !busy && hasSel
        && (several ? manyAction().length > 0
                    : (isSetup || !deviceConnected || details.count > 0))

    function openCopy() {
        if (!hasSel)
            return
        if (isDevice && details.hasCurrent !== true) {
            var newest = lib.newestSetup(details.key)
            if (!newest.length) {
                showMessage(details.name + " has nothing to copy: it isn't set up here and has no saved setup.", true)
                return
            }
            lib.select(newest)
        }
        _copyDlg.openFor(details)
    }
    function openSwap() { if (hasSel) _swapDlg.openFor(details) }
    function openOutput() { if (hasSel) _outputDlg.openFor(details) }
    function openSave() { if (hasSel) _saveDlg.openFor(details) }
    property string renameKey: ""
    property string renameFrom: ""
    function startRename() {
        if (!hasSel || busy || several)
            return
        renameKey = details.key
        renameFrom = details.name
        _nameField.text = details.name
        renaming = true
        _nameField.forceActiveFocus()
        _nameField.selectAll()
    }
    function finishRename(keep) {
        if (!renaming)
            return
        renaming = false
        var text = _nameField.text.trim()
        if (keep && text.length && renameKey.length && text !== renameFrom)
            lib.rename(renameKey, text)
    }
    // Edit › Delete… and the details' Delete…: what S15 gives the
    // selection (on a connected device, its saved setups).
    function askDelete() {
        if (!canDelete)
            return
        if (several)
            askMany()
        else if (isSetup) {
            var key = details.key
            _deleteDlg.ask("Delete the saved setup “" + details.name + "”?",
                           "It is removed from the Device Library. This can't be undone.",
                           "Delete", function() { _lib.lib.deleteItem(key) })
        }
        else if (!deviceConnected)
            askRemove()
        else
            askDeleteSetups()
    }

    // | Deleting by the device's state (S15, S47): each asks first and
    // names what goes.

    function _setupsText(n) {
        return n === 1 ? "its saved setup" : "its " + n + " saved setups"
    }

    // A not connected device: it and all its saved setups, and its module
    // file here first, as Home's Delete Device does (autosave first,
    // refused while the profile runs).
    function askRemove() {
        var key = details.key
        var plan = lib.removalPlan(key)
        var heading = "Remove " + details.name
            + (details.count > 0 ? " and " + _setupsText(details.count) : "")
            + " from the Library?"
        var body = (plan.module_file
                    ? "Its module file here goes too, as Delete Device on Home does: "
                      + "an autosave is kept first. " : "")
            + "This can't be undone."
        _deleteDlg.ask(heading, body, "Remove", function() { _lib.runRemove([key]) })
    }

    // A connected device: Clear Setup is Home's Delete Device for it.
    function askClearSetup() {
        var key = details.key
        _deleteDlg.ask("Clear the setup of " + details.name + "?",
                       "As Delete Device on Home: an autosave is kept in the Device Library first, "
                       + "then its module file and its bindings go. The stick stays plugged in "
                       + "with no setup.",
                       "Clear Setup", function() { _lib.runClearSetup(key) })
    }

    function askDeleteSetups() {
        var key = details.key
        _deleteDlg.ask("Delete " + details.name + "'s "
                       + (details.count === 1 ? "saved setup" : details.count + " saved setups") + "?",
                       "They are removed from the Device Library. The stick keeps its settings. "
                       + "This can't be undone.",
                       "Delete", function() { _lib.lib.deleteSavedSetups(key) })
    }

    // S50: what Delete… / Remove from Library… does to several rows ("" when
    // neither applies: devices that are connected).
    function manyAction() {
        if (!lib || picked.length < 2)
            return ""
        var rows = lib.rows
        var kind = ""
        for (var i = 0; i < picked.length; i++) {
            var row = _rowOf(picked[i])
            if (!row)
                continue
            kind = row.kind
            if (row.kind === "device" && row.state === "connected")
                return ""
        }
        return kind === "device" ? "remove" : (kind === "setup" ? "delete" : "")
    }
    function _rowOf(key) {
        var rows = lib ? lib.rows : []
        for (var i = 0; i < rows.length; i++)
            if (rows[i].key === key)
                return rows[i]
        return null
    }

    // One question that lists them.
    function askMany() {
        var what = manyAction()
        if (!what.length)
            return
        var keys = picked.slice()
        var lines = []
        var setups = 0
        var files = 0
        for (var i = 0; i < keys.length; i++) {
            var row = _rowOf(keys[i])
            if (!row)
                continue
            setups += row.count || 0
            if (what === "remove" && lib.removalPlan(keys[i]).module_file)
                files += 1
            lines.push("•  " + (row.label || row.name)
                       + (what === "remove" && row.count ? "  (" + row.countText.toLowerCase() + ")" : ""))
        }
        if (what === "delete")
            _deleteDlg.ask("Delete these " + keys.length + " saved setups?",
                           lines.join("\n") + "\n\nThey are removed from the Device Library. This can't be undone.",
                           "Delete", function() { _lib.lib.deleteMany(keys) })
        else
            _deleteDlg.ask("Remove these " + keys.length + " devices"
                           + (setups ? " and their " + (setups === 1 ? "saved setup" : setups + " saved setups") : "")
                           + " from the Library?",
                           lines.join("\n") + "\n\n"
                           + (files ? "A module file still here goes too, as Delete Device on Home "
                                      + "does: an autosave is kept first. " : "")
                           + "This can't be undone.",
                           "Remove", function() { _lib.runRemove(keys) })
    }

    // To the main window (Main.qml libraryAction): Home's Delete Device,
    // Module Setup, Button Map, Show on Home (S15, S44). Its Result.
    function toMain(action, key) {
        var raw = DeviceLibraryOpen.toMain(action, lib.deviceTarget(key))
        var res = {}
        try {
            res = JSON.parse(raw)
        } catch (err) {
            res = { ok: false, error: "That didn't work." }
        }
        if (!res.ok)
            showMessage(String(res.error || "That didn't work."), true)
        return res
    }

    // Remove from Library: Delete Device first where a module file is still
    // here (stops at the first refused), then the Library's part.
    function runRemove(keys) {
        for (var i = 0; i < keys.length; i++) {
            var plan = lib.removalPlan(keys[i])
            if (plan.module_file && !toMain("deleteDevice", keys[i]).ok)
                return
        }
        if (keys.length === 1)
            lib.removeDevice(keys[0])
        else
            lib.deleteMany(keys)
    }

    function runClearSetup(key) {
        if (!toMain("deleteDevice", key).ok)
            return
        lib.refresh()
        showMessage("Setup cleared. An autosave was kept in the Device Library first.", false)
    }

    // S48: back on its own stick, as Copy does.
    function askRestore() {
        var key = details.key
        _deleteDlg.ask("Restore “" + details.name + "” to " + details.deviceName + "?",
                       "It is put back on the stick as Copy does: an autosave of the stick is "
                       + "kept first, and Edit › Undo puts it back.",
                       "Restore", function() { _lib.lib.restoreToStick(key) }, true)
    }

    function editDescription() {
        _description.forceActiveFocus()
        _description.cursorPosition = _description.text.length
    }

    function exportSaved() {
        _exportFile.selectedFile = details.name.replace(/[\\/:*?"<>|]/g, "_") + ".zip"
        _exportFile.open()
    }
    function exportCurrent() {
        _exportCurrentFile.key = details.key
        _exportCurrentFile.selectedFile = details.name.replace(/[\\/:*?"<>|]/g, "_") + ".zip"
        _exportCurrentFile.open()
    }

    // | Right-click menus (S43-S50)

    // The row the menu is for ("" = empty space in the list).
    property string menuKey: ""

    function rowMenuModel() {
        if (!lib)
            return MenuModel.menu("", "", [], [])
        var free = !busy
        if (!menuKey.length)
            return MenuModel.menu("library-space", "Device Library", [
                MenuModel.action("Import Device Pack…", function() { _importFile.open() }, free),
                MenuModel.action("Expand All", function() { _lib.lib.setAllOpen(true) }),
                MenuModel.action("Collapse All", function() { _lib.lib.setAllOpen(false) }),
                MenuModel.action("Device Library Settings…", function() { _settingsDlg.openNow() }, free)
            ], [])
        var d = details
        var row = _rowOf(menuKey)
        if (several) {
            var what = manyAction()
            var title = picked.length + (row && row.kind === "device" ? " devices" : " saved setups")
            return MenuModel.menu("library-many", title, [
                what === "delete" ? MenuModel.action("Delete…", function() { _lib.askMany() }, free, { danger: true }) : null,
                what === "remove" ? MenuModel.action("Remove from Library…", function() { _lib.askMany() }, free, { danger: true }) : null,
                // A plugged-in stick among them: say why, not an empty menu.
                what === "" && row && row.kind === "device"
                    ? MenuModel.note("Remove from Library works only on devices that aren't plugged in") : null
            ], [])
        }
        if (d.kind === "setup") {
            var autosave = d.origin === "autosave" && !d.own
            return MenuModel.menu("library-setup", d.name, [
                MenuModel.action("Copy to Another Stick…", function() { _lib.openCopy() }, free),
                MenuModel.action("Restore to This Stick…", function() { _lib.askRestore() }, free && d.connected === true),
                MenuModel.action("Export…", function() { _lib.exportSaved() }, free),
                MenuModel.action("Rename…", function() { _lib.startRename() }, free, { hint: "F2" }),
                MenuModel.action("Edit Description", function() { _lib.editDescription() }, free),
                autosave ? MenuModel.action("Keep This Autosave", function() { _lib.lib.keep(d.key) }, free) : null,
                MenuModel.action("Delete…", function() { _lib.askDelete() }, free, { danger: true })
            ], [])
        }
        var connected = d.connected === true
        var current = d.hasCurrent === true
        // It has a card on Home: plugged in, or a module file here.
        var card = connected || (d.module || "").length > 0
        return MenuModel.menu("library-device", d.name, [
            MenuModel.action("Copy to Another Stick…", function() { _lib.openCopy() }, free && current),
            MenuModel.action("Swap with Another Stick…", function() { _lib.openSwap() }, free && connected),
            MenuModel.action("Change vJoy Output…", function() { _lib.openOutput() }, canOutput),
            MenuModel.action("Save to Device Library…", function() { _lib.openSave() }, canSave),
            MenuModel.action("Export Current Setup…", function() { _lib.exportCurrent() }, free && current),
            MenuModel.action("Rename…", function() { _lib.startRename() }, free, { hint: "F2" }),
            MenuModel.action("Edit Description", function() { _lib.editDescription() }, free),
            MenuModel.action("Open Module Setup…", function() { _lib.toMain("moduleSetup", d.key) }, card),
            MenuModel.action("Open Button Map", function() { _lib.toMain("buttonMap", d.key) }, card),
            MenuModel.action("Show on Home", function() { _lib.toMain("home", d.key) }, card),
            row && row.hasChildren
                ? MenuModel.action(row.open ? "Collapse" : "Expand", function() { _lib.lib.toggleOpen(d.key) })
                : null,
            connected ? null
                : MenuModel.action("Remove from Library…", function() { _lib.askRemove() }, free, { danger: true }),
            connected
                ? MenuModel.action("Clear Setup…", function() { _lib.askClearSetup() }, free, { danger: true })
                : null,
            connected && d.count > 0
                ? MenuModel.action("Delete Saved Setups…", function() { _lib.askDeleteSetups() }, free, { danger: true })
                : null
        ], [])
    }

    // A right-click on the list: on a row, it is selected first (unless it
    // is one of several selected), then its menu opens; elsewhere, the
    // empty space's menu.
    function rightClickAt(key, item, x, y) {
        if (key.length && picked.indexOf(key) < 0)
            lib.select(key)
        menuKey = key
        _rowMenu.openAt(item, x, y)
    }

    // The Menu key and Shift+F10: the menu on the selected row.
    function openMenuOnSelection() {
        if (!lib)
            return
        var key = lib.selected
        var rows = lib.rows
        var index = -1
        for (var i = 0; i < rows.length; i++)
            if (rows[i].key === key)
                index = i
        if (index < 0) {
            rightClickAt("", _list, Style.dp(24), Style.dp(12))
            return
        }
        _list.positionViewAtIndex(index, ListView.Contain)
        var item = _list.itemAtIndex(index)
        rightClickAt(key, item || _list, Style.dp(40), item ? item.height / 2 : Style.dp(12))
    }

    // The Device Library Guide: only the Device Library's topics (S42).
    function openGuide() {
        Helpers.createComponent("DialogDeviceLibraryGuide.qml")
    }

    Shortcut { sequence: "F1"; onActivated: _lib.openGuide() }
    Shortcut { sequence: "F2"; onActivated: _lib.startRename() }
    // S43: the selected row's menu from the keyboard.
    Shortcut { sequences: ["Menu", "Shift+F10"]; onActivated: _lib.openMenuOnSelection() }

    ContextMenu {
        id: _rowMenu
        objectName: "libraryRowMenu"
        build: _lib.rowMenuModel
    }
    Shortcut { sequence: "Ctrl+F"; onActivated: { _search.forceActiveFocus(); _search.selectAll() } }

    FileDialog {
        id: _importFile
        title: "Import Device Pack"
        nameFilters: ["Device Pack (*.zip)"]
        fileMode: FileDialog.OpenFile
        onAccepted: _lib.lib.importPack(Helpers.fileDialogUrl(_importFile))
    }
    FileDialog {
        id: _exportFile
        title: "Export Saved Setup"
        nameFilters: ["Device Pack (*.zip)"]
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        onAccepted: _lib.lib.exportSetup(_lib.details.key, Helpers.fileDialogUrl(_exportFile))
    }
    FileDialog {
        id: _exportCurrentFile
        property string key: ""
        title: "Export Current Setup"
        nameFilters: ["Device Pack (*.zip)"]
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        onAccepted: _lib.lib.exportCurrent(key, Helpers.fileDialogUrl(_exportCurrentFile))
    }

    // S39: a Device Pack dropped on the window is imported.
    DropArea {
        id: _drop
        objectName: "libraryDrop"
        anchors.fill: parent
        function zipOf(urls) {
            for (var i = 0; i < urls.length; i++) {
                if (String(urls[i]).toLowerCase().endsWith(".zip"))
                    return String(urls[i])
            }
            return ""
        }
        onEntered: (drag) => { drag.accepted = drag.hasUrls && zipOf(drag.urls).length > 0 }
        onDropped: (drop) => {
            var url = zipOf(drop.urls)
            if (url.length && _lib.lib) {
                _lib.lib.importPack(url)
                drop.accept()
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ThemedMenuBar {
            id: _menuBar
            Layout.fillWidth: true
            ThemedMenu {
                id: _fileMenu
                title: "File"
                ThemedMenuItem { text: "Import Device Pack…"; enabled: !_lib.busy; onTriggered: _importFile.open() }
                ThemedMenuItem {
                    text: "Export Saved Setup…"
                    enabled: _lib.isSetup && !_lib.busy && !_lib.several
                    onTriggered: {
                        _exportFile.selectedFile = _lib.details.name.replace(/[\\/:*?"<>|]/g, "_") + ".zip"
                        _exportFile.open()
                    }
                }
                ThemedMenuItem {
                    text: "Open Library Folder"
                    enabled: _lib.lib && _lib.lib.folderText.length > 0
                    onTriggered: Qt.openUrlExternally(_lib.lib.fileUrl(_lib.lib.folderText))
                }
                ThemedMenuSeparator {}
                ThemedMenuItem { text: "Close"; onTriggered: _lib.close() }
            }
            ThemedMenu {
                id: _editMenu
                title: "Edit"
                ThemedMenuItem {
                    objectName: "libraryUndoItem"
                    text: _lib.lib && _lib.lib.undoText.length ? _lib.lib.undoText : "Undo"
                    enabled: !_lib.busy && _lib.lib && _lib.lib.undoText.length > 0
                    onTriggered: _lib.lib.undo()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem { text: "Rename…"; hint: "F2"; enabled: _lib.hasSel && !_lib.busy && !_lib.several; onTriggered: _lib.startRename() }
                ThemedMenuItem { text: "Delete…"; danger: true; enabled: _lib.canDelete; onTriggered: _lib.askDelete() }
                ThemedMenuSeparator {}
                ThemedMenuItem { text: "Tidy Library…"; enabled: !_lib.busy; onTriggered: _tidyDlg.openNow() }
            }
            ThemedMenu {
                id: _deviceMenu
                title: "Device"
                ThemedMenuItem {
                    text: "Save to Device Library…"
                    enabled: _lib.canSave
                    onTriggered: _lib.openSave()
                }
                ThemedMenuSeparator {}
                ThemedMenuItem { text: "Copy to Another Stick…"; enabled: _lib.canCopy; onTriggered: _lib.openCopy() }
                ThemedMenuItem { text: "Swap with Another Stick…"; enabled: !_lib.busy && !_lib.several && _lib.deviceConnected; onTriggered: _lib.openSwap() }
                ThemedMenuItem { text: "Change vJoy Output…"; enabled: _lib.canOutput; onTriggered: _lib.openOutput() }
            }
            ThemedMenu {
                id: _viewMenu
                title: "View"
                Repeater {
                    model: [["connected", "Connected"], ["not_connected", "Not Connected"],
                            ["deleted", "Deleted"], ["autosaves", "Autosaves"]]
                    delegate: ThemedMenuItem {
                        required property var modelData
                        text: modelData[1]
                        checkable: true
                        checked: _lib.lib ? _lib.lib.filters[modelData[0]] === true : true
                        onTriggered: _lib.lib.setFilter(modelData[0], !(_lib.lib.filters[modelData[0]] === true))
                    }
                }
                ThemedMenuSeparator {}
                ThemedMenuItem { text: "Expand All"; onTriggered: _lib.lib.setAllOpen(true) }
                ThemedMenuItem { text: "Collapse All"; onTriggered: _lib.lib.setAllOpen(false) }
                ThemedMenuSeparator {}
                ThemedMenuItem { text: "Search…"; hint: "Ctrl+F"; onTriggered: { _search.forceActiveFocus(); _search.selectAll() } }
            }
            ThemedMenu {
                id: _settingsMenu
                title: "Settings"
                ThemedMenuItem { text: "Device Library Settings…"; enabled: !_lib.busy; onTriggered: _settingsDlg.openNow() }
            }
            ThemedMenu {
                id: _helpMenu
                title: "Help"
                ThemedMenuItem { text: "Device Library Guide"; hint: "F1"; onTriggered: _lib.openGuide() }
            }
        }

        SplitView {
            id: _split
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            // | Left: filters, search, the list (S3)
            Pane {
                SplitView.preferredWidth: Style.dp(640)
                SplitView.minimumWidth: Style.dp(380)
                padding: Style.dp(12)
                background: Rectangle { color: Style.bgPage }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: Style.dp(8)

                    Flow {
                        Layout.fillWidth: true
                        spacing: Style.dp(6)
                        Repeater {
                            model: [["connected", "Connected"], ["not_connected", "Not connected"],
                                    ["deleted", "Deleted"], ["autosaves", "Autosaves"]]
                            delegate: Rectangle {
                                id: _chip
                                required property var modelData
                                objectName: "libraryFilter_" + modelData[0]
                                readonly property bool on: _lib.lib ? _lib.lib.filters[modelData[0]] === true : true
                                implicitWidth: _chipText.implicitWidth + Style.dp(18)
                                implicitHeight: Style.dp(24)
                                width: implicitWidth
                                height: implicitHeight
                                radius: height / 2
                                color: on ? Style.alpha(Style.accent, 0.12) : Style.clear
                                border.color: on ? Style.accent : Style.line
                                function toggle() { _lib.lib.setFilter(modelData[0], !on) }
                                Label {
                                    id: _chipText
                                    anchors.centerIn: parent
                                    text: (_chip.on ? "✓ " : "") + _chip.modelData[1]
                                    font.pixelSize: Style.dp(12)
                                    color: _chip.on ? Style.fgStrong : Style.fgMuted
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: _chip.toggle()
                                }
                            }
                        }
                    }

                    TextField {
                        id: _search
                        objectName: "librarySearch"
                        Layout.fillWidth: true
                        placeholderText: "Search names, descriptions, profiles, modes, vJoy…  (Ctrl+F)"
                        onTextChanged: if (_lib.lib) _lib.lib.setSearch(text)
                        Keys.onEscapePressed: (event) => { text = ""; event.accepted = true }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: Style.bgCard
                        border.color: Style.line
                        radius: Style.dp(4)
                        clip: true

                        Label {
                            anchors.centerIn: parent
                            visible: _list.count === 0
                            color: Style.fgMuted
                            text: _search.text.length ? "Nothing matches the search." : "No devices to show."
                        }

                        ListView {
                            id: _list
                            objectName: "libraryList"
                            anchors.fill: parent
                            anchors.margins: 1
                            model: _lib.lib ? _lib.lib.rows : []
                            boundsBehavior: Flickable.StopAtBounds
                            ScrollBar.vertical: ScrollBar {}

                            delegate: Rectangle {
                                id: _row
                                required property var modelData
                                required property int index
                                readonly property bool isDev: modelData.kind === "device"
                                // Selected (one of several too, S50), hovered,
                                // pressed, being changed (S43).
                                readonly property bool isSel: _lib.picked.indexOf(modelData.key) >= 0
                                readonly property bool isBusy: _lib.lib !== null
                                    && _lib.lib.busyKeys.indexOf(modelData.key) >= 0
                                objectName: "libraryRow_" + modelData.key
                                width: ListView.view.width
                                height: isDev ? Style.dp(50) : Style.dp(42)
                                color: isSel ? Style.bgSelected
                                    : _rowMouse.pressed ? Style.alpha(Style.accent, 0.22)
                                    : _rowMouse.containsMouse ? Style.bgHover
                                    : (isDev ? Style.bgCard : Style.bgWell)

                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Style.line }
                                Rectangle { visible: _row.isSel; width: Style.dp(3); height: parent.height; color: Style.accent }

                                MouseArea {
                                    id: _rowMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    // S50: Ctrl-click adds or takes away, Shift-click a range.
                                    onClicked: (mouse) => _lib.lib.pick(_row.modelData.key,
                                        (mouse.modifiers & Qt.ControlModifier) ? "toggle"
                                        : (mouse.modifiers & Qt.ShiftModifier) ? "range" : "")
                                    // S40: a saved setup opens Copy; a device opens or closes.
                                    onDoubleClicked: {
                                        if (_row.isDev) {
                                            _lib.lib.toggleOpen(_row.modelData.key)
                                        } else {
                                            _lib.lib.select(_row.modelData.key)
                                            _lib.openCopy()
                                        }
                                    }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: _row.isDev ? Style.dp(8) : Style.dp(34)
                                    anchors.rightMargin: Style.dp(12)
                                    spacing: Style.dp(8)

                                    // The caret (S10).
                                    Text {
                                        visible: _row.isDev
                                        objectName: "libraryCaret_" + _row.modelData.key
                                        Layout.preferredWidth: Style.dp(18)
                                        text: _row.modelData.hasChildren ? (_row.modelData.open ? "" : "") : ""
                                        font.family: Style.iconFont
                                        font.pixelSize: Style.dp(13)
                                        color: Style.fgSoft
                                        MouseArea {
                                            anchors.fill: parent
                                            anchors.margins: -Style.dp(6)
                                            enabled: _row.modelData.hasChildren === true
                                            onClicked: _lib.lib.toggleOpen(_row.modelData.key)
                                        }
                                    }
                                    // Device, saved setup (save mark) or autosave (S10).
                                    Text {
                                        text: _row.isDev ? "" : (_row.modelData.mark === "autosave" ? "" : "")
                                        font.family: Style.iconFont
                                        font.pixelSize: Style.dp(_row.isDev ? 17 : 14)
                                        color: _row.isDev ? Style.fgSoft : (_row.modelData.mark === "autosave" ? Style.fgMuted : Style.info)
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        Label {
                                            objectName: "libraryRowName_" + _row.modelData.key
                                            Layout.fillWidth: true
                                            text: _row.modelData.label || _row.modelData.name
                                            elide: Text.ElideRight
                                            font.bold: _row.isDev
                                            color: Style.fgStrong
                                        }
                                        Label {
                                            Layout.fillWidth: true
                                            text: _row.isDev ? _row.modelData.description : _row.modelData.sub
                                            visible: text.length > 0
                                            elide: Text.ElideRight
                                            font.pixelSize: Style.dp(12)
                                            color: Style.fgMuted
                                        }
                                    }
                                    BusyIndicator {
                                        objectName: "libraryRowBusy_" + _row.modelData.key
                                        visible: _row.isBusy
                                        running: visible
                                        Layout.preferredWidth: Style.dp(16)
                                        Layout.preferredHeight: Style.dp(16)
                                    }
                                    Label {
                                        text: _row.isDev ? _row.modelData.countText : _row.modelData.date
                                        font.pixelSize: Style.dp(12)
                                        color: Style.fgMuted
                                    }
                                    Rectangle {
                                        visible: _row.isDev
                                        implicitWidth: _state.implicitWidth + Style.dp(14)
                                        implicitHeight: Style.dp(20)
                                        radius: height / 2
                                        color: Style.clear
                                        border.color: _state.color
                                        Label {
                                            id: _state
                                            anchors.centerIn: parent
                                            text: _row.modelData.stateLabel || ""
                                            font.pixelSize: Style.dp(11)
                                            color: _row.modelData.state === "connected" ? Style.okText
                                                : _row.modelData.state === "deleted" ? Style.fgMuted : Style.fgSoft
                                        }
                                    }
                                }
                            }
                        }

                        // Right-clicks on the list (S43, S46): a row's menu,
                        // or the empty space's. Left clicks pass through.
                        MouseArea {
                            id: _listMenuArea
                            objectName: "libraryListMenuArea"
                            anchors.fill: _list
                            acceptedButtons: Qt.RightButton
                            onClicked: (mouse) => {
                                var row = _list.itemAt(mouse.x + _list.contentX, mouse.y + _list.contentY)
                                _lib.rightClickAt(row ? String(row.modelData.key) : "", _listMenuArea, mouse.x, mouse.y)
                            }
                        }
                    }
                }
            }

            // | Right: what is selected (S8, S11)
            Pane {
                SplitView.fillWidth: true
                SplitView.minimumWidth: Style.dp(400)
                padding: Style.dp(16)
                background: Rectangle { color: Style.bgPage }

                Label {
                    anchors.centerIn: parent
                    visible: !_lib.hasSel
                    color: Style.fgMuted
                    text: "Select a device or a saved setup."
                }

                ScrollView {
                    id: _detailsScroll
                    objectName: "libraryDetails"
                    anchors.fill: parent
                    visible: _lib.hasSel
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: _detailsScroll.availableWidth
                        spacing: Style.dp(8)

                        Label {
                            text: _lib.details.crumb || ""
                            font.pixelSize: Style.dp(12)
                            color: Style.fgMuted
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                id: _nameLabel
                                objectName: "libraryName"
                                visible: !_lib.renaming
                                Layout.fillWidth: true
                                text: _lib.details.name || ""
                                font.pixelSize: Style.dp(20)
                                font.bold: true
                                color: Style.fgStrong
                                elide: Text.ElideRight
                            }
                            TextField {
                                id: _nameField
                                objectName: "libraryNameField"
                                visible: _lib.renaming
                                Layout.fillWidth: true
                                font.pixelSize: Style.dp(18)
                                onAccepted: _lib.finishRename(true)
                                onActiveFocusChanged: if (!activeFocus) _lib.finishRename(true)
                                Keys.onEscapePressed: (event) => { _lib.finishRename(false); event.accepted = true }
                            }
                            ToolButton {
                                objectName: "libraryRenameButton"
                                visible: !_lib.renaming
                                text: ""
                                font.family: Style.iconFont
                                enabled: !_lib.busy
                                ToolTip.visible: hovered
                                ToolTip.text: "Rename (F2)"
                                onClicked: _lib.startRename()
                            }
                        }
                        // Edited in place (S11; no Edit Description…).
                        TextArea {
                            id: _description
                            objectName: "libraryDescription"
                            Layout.fillWidth: true
                            Layout.minimumHeight: Style.dp(60)
                            wrapMode: TextEdit.Wrap
                            placeholderText: "Add a description"
                            // Which item the text is for, and the text as
                            // it was read: a change is kept for that item
                            // even when the selection moves first.
                            property string forKey: ""
                            property string loaded: ""
                            function load() {
                                forKey = _lib.details.key || ""
                                loaded = _lib.details.description || ""
                                text = loaded
                            }
                            function commit() {
                                if (forKey.length && text !== loaded) {
                                    loaded = text
                                    _lib.lib.describe(forKey, text)
                                }
                            }
                            onEditingFinished: commit()
                            Connections {
                                target: _lib.lib
                                function onChanged() {
                                    if ((_lib.details.key || "") !== _description.forKey) {
                                        _description.commit()
                                        _description.load()
                                    } else if (!_description.activeFocus) {
                                        _description.load()
                                    }
                                }
                            }
                            Component.onCompleted: load()
                        }

                        // A device (S8).
                        ColumnLayout {
                            visible: _lib.isDevice
                            spacing: Style.dp(4)
                            Label { text: (_lib.details.stateLabel || "") + " · " + (_lib.details.countText || ""); color: Style.fgSoft }
                            Label { objectName: "libraryDeviceInputs"; visible: (_lib.details.inputs || "").length > 0; text: "Inputs: " + (_lib.details.inputs || ""); color: Style.fgSoft }
                            Label { objectName: "libraryDeviceSeen"; visible: (_lib.details.lastSeen || "").length > 0; text: "Last seen " + (_lib.details.lastSeen || ""); color: Style.fgSoft }
                        }

                        // A saved setup (S11).
                        ColumnLayout {
                            visible: _lib.isSetup
                            Layout.fillWidth: true
                            spacing: Style.dp(6)
                            Label { text: _lib.details.kept || ""; font.pixelSize: Style.dp(12); color: Style.fgMuted }
                            Label { text: "Holds"; font.bold: true; color: Style.fgStrong; Layout.topMargin: Style.dp(6) }
                            GridLayout {
                                columns: 2
                                columnSpacing: Style.dp(24)
                                rowSpacing: Style.dp(2)
                                Repeater {
                                    model: _lib.details.holdsLabels || []
                                    delegate: Label { required property var modelData; text: "✓ " + modelData; color: Style.fg }
                                }
                            }
                            Repeater {
                                model: _lib.details.bindings || []
                                delegate: Label {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    wrapMode: Text.Wrap
                                    text: "✓ " + modelData
                                    color: Style.fg
                                }
                            }
                            Label {
                                visible: text.length > 0
                                text: _lib.details.sends || ""
                                font.pixelSize: Style.dp(12)
                                color: Style.fgSoft
                            }
                            Label {
                                visible: (_lib.details.holds || []).length === 0
                                text: "It holds nothing."
                                color: Style.fgMuted
                            }
                            RowLayout {
                                Layout.topMargin: Style.dp(6)
                                spacing: Style.dp(14)
                                Rectangle {
                                    Layout.preferredWidth: Style.dp(170)
                                    Layout.preferredHeight: Style.dp(150)
                                    Layout.alignment: Qt.AlignTop
                                    color: Style.bgWell
                                    border.color: Style.line
                                    radius: Style.dp(3)
                                    Image {
                                        objectName: "libraryPhoto"
                                        anchors.fill: parent
                                        anchors.margins: Style.dp(4)
                                        visible: (_lib.details.photo || "").length > 0
                                        source: visible ? _lib.lib.fileUrl(_lib.details.photo) : ""
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                    }
                                    Column {
                                        objectName: "libraryPhotoPlaceholder"
                                        anchors.centerIn: parent
                                        visible: (_lib.details.photo || "").length === 0
                                        spacing: Style.dp(6)
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: ""; font.family: Style.iconFont; font.pixelSize: Style.dp(34); color: Style.fgMuted }
                                        Label { text: "Button Map photo"; font.pixelSize: Style.dp(11); color: Style.fgMuted }
                                    }
                                }
                                ColumnLayout {
                                    Layout.alignment: Qt.AlignTop
                                    Layout.fillWidth: true
                                    spacing: Style.dp(3)
                                    // "Activity", not "History": Tools › History is the saved-changes window.
                                    Label { text: "Activity"; font.bold: true; color: Style.fgStrong }
                                    Repeater {
                                        model: _lib.details.history || []
                                        delegate: RowLayout {
                                            required property var modelData
                                            spacing: Style.dp(10)
                                            Label { text: modelData.at; font.pixelSize: Style.dp(12); color: Style.fgMuted }
                                            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: modelData.text; font.pixelSize: Style.dp(12); color: Style.fgSoft }
                                        }
                                    }
                                }
                            }
                        }

                        // The actions (S11).
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.topMargin: Style.dp(10)
                            spacing: Style.dp(8)
                            Button {
                                visible: _lib.isDevice && !_lib.several
                                objectName: "librarySaveButton"
                                Layout.fillWidth: true
                                text: "Save to Device Library…"
                                enabled: _lib.canSave
                                onClicked: _lib.openSave()
                            }
                            Button {
                                objectName: "libraryCopyButton"
                                // S50: one row only; hidden with several.
                                visible: !_lib.several
                                Layout.fillWidth: true
                                text: "Copy to Another Stick…"
                                highlighted: true
                                enabled: _lib.canCopy
                                onClicked: _lib.openCopy()
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                visible: !_lib.several
                                Button {
                                    objectName: "librarySwapButton"
                                    Layout.fillWidth: true
                                    text: "Swap with Another Stick…"
                                    enabled: !_lib.busy && !_lib.several && _lib.deviceConnected
                                    onClicked: _lib.openSwap()
                                }
                                Button {
                                    objectName: "libraryOutputButton"
                                    Layout.fillWidth: true
                                    text: "Change vJoy Output…"
                                    enabled: _lib.canOutput
                                    onClicked: _lib.openOutput()
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Button {
                                    objectName: "libraryExportButton"
                                    visible: !_lib.several
                                    Layout.fillWidth: true
                                    text: "Export…"
                                    enabled: !_lib.busy && !_lib.several && _lib.isSetup
                                    onClicked: {
                                        _exportFile.selectedFile = _lib.details.name.replace(/[\\/:*?"<>|]/g, "_") + ".zip"
                                        _exportFile.open()
                                    }
                                }
                                Button {
                                    id: _deleteButton
                                    objectName: "libraryDeleteButton"
                                    Layout.fillWidth: true
                                    // S15: a device's delete follows its state.
                                    text: _lib.isDevice && !_lib.several
                                          ? (_lib.deviceConnected ? "Delete Saved Setups…" : "Remove from Library…")
                                          : "Delete…"
                                    enabled: _lib.canDelete
                                    contentItem: Label {
                                        text: _deleteButton.text
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        color: _deleteButton.enabled ? Style.dangerText : Style.fgDisabled
                                    }
                                    onClicked: _lib.askDelete()
                                }
                            }
                        }
                    }
                }
            }
        }

        // The last change's outcome.
        Rectangle {
            objectName: "libraryMessage"
            Layout.fillWidth: true
            visible: _lib.message.length > 0
            implicitHeight: _msg.implicitHeight + Style.dp(12)
            color: _lib.messageBad ? Style.alpha(Style.danger, 0.18) : Style.bgRaised
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.dp(12)
                anchors.rightMargin: Style.dp(6)
                Label {
                    id: _msg
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: _lib.message
                    color: _lib.messageBad ? Style.dangerTextSoft : Style.fg
                }
                ToolButton {
                    text: ""
                    font.family: Style.iconFont
                    onClicked: _lib.message = ""
                }
            }
        }

        // The status bar (S4).
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Style.dp(28)
            color: Style.bgWell
            Rectangle { width: parent.width; height: 1; color: Style.line }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.dp(12)
                anchors.rightMargin: Style.dp(12)
                spacing: Style.dp(12)
                BusyIndicator {
                    visible: _lib.busy
                    running: visible
                    Layout.preferredWidth: Style.dp(18)
                    Layout.preferredHeight: Style.dp(18)
                }
                Label {
                    objectName: "libraryStatus"
                    text: (_lib.busy ? "Working…     " : "") + (_lib.lib ? _lib.lib.statusText : "")
                    font.pixelSize: Style.dp(12)
                    color: Style.fgSoft
                }
                Item { Layout.fillWidth: true }
                Label {
                    Layout.maximumWidth: _lib.width / 2
                    elide: Text.ElideLeft
                    text: _lib.lib && _lib.lib.folderText.length ? "Library folder: " + _lib.lib.folderText : ""
                    font.pixelSize: Style.dp(12)
                    color: Style.fgMuted
                }
            }
        }
    }

    // | Dialogs

    DialogLibraryCopy { id: _copyDlg; lib: _lib.lib }
    DialogLibrarySwap { id: _swapDlg; lib: _lib.lib }
    DialogLibraryOutput { id: _outputDlg; lib: _lib.lib }
    DialogLibrarySettings { id: _settingsDlg; lib: _lib.lib }
    DialogLibraryTidy { id: _tidyDlg; lib: _lib.lib }

    // S15, S47: every delete asks first, naming what goes (Restore asks
    // too, S48). go runs on the button (red for a delete).
    Dialog {
        id: _deleteDlg
        objectName: "libraryDeleteDialog"
        property string body: ""
        property string goText: "Delete"
        property bool danger: true
        property var go: null
        anchors.centerIn: Overlay.overlay
        width: Math.min(_lib.width - Style.dp(40), Style.dp(520))
        modal: true
        function ask(heading, text, button, run, safe) {
            title = heading
            body = text
            goText = button
            danger = safe !== true
            go = run
            open()
        }
        Label { width: parent.width; wrapMode: Text.Wrap; text: _deleteDlg.body }
        footer: DialogButtonBox {
            Button { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            Button {
                id: _deleteGo
                objectName: "libraryDeleteDialogGo"
                text: _deleteDlg.goText
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                contentItem: Label {
                    text: _deleteGo.text
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    color: _deleteDlg.danger ? Style.dangerText : Style.fg
                }
            }
        }
        onAccepted: {
            var run = go
            go = null
            if (typeof run === "function")
                run()
        }
    }

    // S12: Save to Device Library…: the module file now, and one saved
    // setup per ticked profile.
    Dialog {
        id: _saveDlg
        objectName: "librarySaveDialog"
        title: "Save to Device Library"
        anchors.centerIn: Overlay.overlay
        width: Math.min(_lib.width - Style.dp(40), Style.dp(560))
        modal: true
        property string key: ""
        property string deviceName: ""
        property bool hasModule: false
        property var profiles: []
        property int ticket: 0
        function openFor(d) {
            key = d.deviceKey
            deviceName = d.kind === "setup" ? d.deviceName : d.name
            hasModule = (d.module || "").length > 0
            profiles = []
            // The open profile always, ticked (S12, as Copy: D-10-PROFILES).
            ticket = _lib.lib.profilesUsing([d.guid || ""], true)
            open()
        }
        // Ticks change the list in place: counted on each toggle.
        property bool anyTicked: false
        function recount() { anyTicked = profiles.some(p => p.checked) }
        function ticked() {
            var out = []
            // The open profile that was never saved has path "" (S33).
            for (var i = 0; i < profiles.length; i++)
                if (profiles[i].checked && (profiles[i].path.length || profiles[i].open))
                    out.push(profiles[i].path)
            return out
        }
        Connections {
            target: _lib.lib
            function onResult(res) {
                if (res.op !== "profiles" || res.ticket !== _saveDlg.ticket)
                    return
                var list = []
                for (var i = 0; i < (res.profiles || []).length; i++) {
                    var p = res.profiles[i]
                    list.push({ name: p.name, path: p.path, open: p.open, checked: p.open === true })
                }
                _saveDlg.profiles = list
                _saveDlg.recount()
            }
        }
        ColumnLayout {
            width: parent.width
            spacing: Style.dp(6)
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: _saveDlg.hasModule
                      ? "Keeps " + _saveDlg.deviceName + "'s module file now, and its bindings from the profiles you tick: one saved setup per profile, named after the profile."
                      : "Keeps " + _saveDlg.deviceName + "'s bindings from the profiles you tick: one saved setup per profile, named after the profile. It has no module file here."
            }
            Repeater {
                model: _saveDlg.profiles
                delegate: CheckBox {
                    required property var modelData
                    required property int index
                    text: modelData.name + (modelData.open ? "  (open)" : "")
                    checked: modelData.checked
                    onToggled: { _saveDlg.profiles[index].checked = checked; _saveDlg.recount() }
                }
            }
            Label {
                visible: _saveDlg.profiles.length === 0
                text: _saveDlg.hasModule ? "No profile has bindings for it: only the module file is kept."
                                         : "No profile has bindings for it: there is nothing to save."
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
            }
        }
        footer: DialogButtonBox {
            Button { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            Button {
                objectName: "librarySaveDialogSave"
                text: "Save"
                // Something to keep: the module file, or a ticked profile.
                enabled: !_lib.busy && (_saveDlg.hasModule || _saveDlg.anyTicked)
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            }
        }
        onAccepted: _lib.lib.saveToLibrary(key, ticked())
    }
}
