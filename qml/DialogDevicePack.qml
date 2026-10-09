// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Style
import "helpers.js" as Helpers

ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _win

    // Opens at the size it was left at (capped to the screen).
    ToolWindowMemory {
        host: _win
        name: "devicePack"
        defaultWidth: Style.fitWidth(Style.dp(860), Screen)
        defaultHeight: Style.fitHeight(Style.dp(780), Screen)
    }
    width: 860
    height: 780
    minimumWidth: Style.fitWidth(Style.dp(720), Screen)
    minimumHeight: Style.fitHeight(Style.dp(640), Screen)
    title: "Device Pack"

    Shortcut { sequence: "Esc"; onActivated: {} }
    Shortcut { sequence: "Return"; onActivated: {} }
    Shortcut { sequence: "Enter"; onActivated: {} }
    color: Style.background
    U.Universal.theme: Style.theme

    property string mode: "export"
    property string zipUrl: ""
    property string status: ""
    property string exportPhoto: ""
    property string exportName: ""
    property string exportSize: ""
    property string importPhoto: ""
    property string importName: ""
    property var packInfo: ({})
    property var sections: []
    property var checks: ({})
    property var targets: ({})
    // The "Put this pack on" row's id when a row was chosen; "" when the
    // target was typed or suggested by name (08 S106a).
    property string importGuid: ""
    property int tickRev: 0
    property int openRev: 0
    property var folded: ({})
    // Export: the device's modes with wires ({name, count}) and which are
    // ticked; the folder of the last export (Show Folder).
    property var exportModes: []
    property var exportTicks: ({})
    property int exportRev: 0
    property string exportFolder: ""
    // Import: the pack's notes, and whether Undo Import is offered.
    property var packNotes: ({})
    // Drivers the pack needs that aren't found (vJoy, a vJoy device, Xbox).
    property var packDrivers: []
    property bool canUndo: false
    // What the warning before Import showed (preview from the program).
    property var preview: ({})

    ListModel { id: _deviceModel }
    HardwareProfile { id: _hw }
    Connections {
        target: _hw
        function onPackExported(raw) {
            var info = _win._parse(raw)
            _win.say(info.ok
                    ? ("Wrote " + info.path + (info.sizeText ? " (" + info.sizeText + ")." : "."))
                    : (info.error || "Export failed."), !info.ok)
            _win.exportFolder = info.ok ? (info.folderUrl || "") : ""
        }
    }

    // 01 S142: what just happened, on the shared message line; after an
    // import its Undo link is Undo Import (08 S80).
    function say(text, failed, undoable) {
        status = text
        if (undoable)
            _message.show(text, !!failed, "Undo Import", _win.undoImport)
        else
            _message.show(text, !!failed)
    }

    function _parse(raw) {
        try {
            return JSON.parse(raw)
        } catch (e) {
            return { ok: false, error: "Bad response" }
        }
    }

    // A row's key: its Windows id, else its name (twins share a name, 08 S106a).
    function rowKey(row) {
        if (!row)
            return ""
        return String(row.guid || "").length ? "id:" + row.guid : "name:" + (row.name || "")
    }

    function reloadDevices() {
        // The chosen device stays chosen, found by its key.
        var i0 = _exportDevice.currentIndex
        var kept = (i0 >= 0 && i0 < _deviceModel.count) ? rowKey(_deviceModel.get(i0)) : ""
        var info = _parse(_hw.packDevices())
        var rows = (info && info.devices) ? info.devices : []
        _deviceModel.clear()
        for (var i = 0; i < rows.length; ++i)
            _deviceModel.append(rows[i])
        var pick = -1
        for (var k = 0; kept.length && k < rows.length; ++k) {
            if (rowKey(rows[k]) === kept) {
                pick = k
                break
            }
        }
        if (pick < 0 && rows.length > 0) {
            // The first device that can be exported: one without a module
            // file, or with a damaged one, has nothing to pack (08 S106).
            pick = 0
            for (var j = 0; j < rows.length; ++j) {
                if (rows[j].canExport) {
                    pick = j
                    break
                }
            }
        }
        if (_exportDevice.currentIndex !== pick)
            _exportDevice.currentIndex = pick
        refreshExport()
    }

    // The chosen device's name, from the list's row: currentText is the
    // label ("(2)", "(file damaged)") and, when the choice is set from code,
    // still the one before while currentIndexChanged runs.
    function exportDeviceName() {
        var i = _exportDevice.currentIndex
        if (i < 0 || i >= _deviceModel.count)
            return ""
        return _deviceModel.get(i).name || ""
    }

    // The chosen device's Windows id ("" when it has none): Export exports
    // that device, not the first of its name (08 S106a).
    function exportDeviceGuid() {
        var i = _exportDevice.currentIndex
        if (i < 0 || i >= _deviceModel.count)
            return ""
        return String(_deviceModel.get(i).guid || "")
    }

    // Export in the background (08 S107): the window stays usable, Export is
    // disabled and "Exporting…" shows until packExported says how it went.
    function startExport(dest) {
        if (_hw.packExporting)
            return
        var info = _parse(_hw.exportPackAsync(exportDeviceName(), dest, exportOptions()))
        if (!info.ok) {
            say(info.error || "Export failed.", true)
            return
        }
        say("", false)
        exportFolder = ""
    }

    function refreshExport() {
        if (mode !== "export")
            return
        var name = exportDeviceName()
        exportName = name
        exportPhoto = ""
        exportSize = ""
        exportModes = []
        exportTicks = {}
        exportFolder = ""
        if (!name.length) {
            say("Choose a device.", false)
            return
        }
        // By the row's id: a twin's own file, not the first one's (08 S106a).
        var info = _parse(_hw.peekPackDeviceById(name, exportDeviceGuid()))
        if (!info.ok) {
            say(info.error || "This device has no module file yet.", false)
            return
        }
        exportName = info.device || name
        exportPhoto = info.photoUrl || ""
        exportSize = info.sizeText || ""
        exportModes = info.modes || []
        var ticks = {}
        for (var m = 0; m < exportModes.length; ++m)
            ticks[exportModes[m].name] = true
        exportTicks = ticks
        exportRev = exportRev + 1
        say("", false)
    }

    function exportOptions() {
        var modes = []
        for (var m = 0; m < exportModes.length; ++m) {
            if (exportTicks[exportModes[m].name] === true)
                modes.push(exportModes[m].name)
        }
        return JSON.stringify({
            modes: modes,
            author: _author.text,
            note: _note.text,
            guid: exportDeviceGuid()
        })
    }

    // The first row with this device name (the list shows labels).
    function importRowOf(name) {
        for (var i = 0; i < _deviceModel.count; ++i) {
            if ((_deviceModel.get(i).name || "") === name)
                return i
        }
        return -1
    }

    function loadPack(info) {
        packInfo = info
        importName = info.exportedName || ""
        importPhoto = info.photoUrl || ""
        packNotes = info.notes || {}
        packDrivers = info.drivers || []
        var rows = info.sections || []
        var next = {}
        var names = {}
        for (var s = 0; s < rows.length; ++s) {
            rows[s].open = false
            if (String(rows[s].id || "").indexOf("out:") === 0)
                names[rows[s].id] = rows[s].target || rows[s].title || ""
            var items = rows[s].items || []
            for (var i = 0; i < items.length; ++i) {
                items[i].open = false
                next[items[i].id] = items[i].checked !== false
            }
        }
        sections = rows
        checks = next
        targets = names
        folded = {}
        tickRev = tickRev + 1
        openRev = openRev + 1
        say("", false)
    }

    function groupState(section) {
        var items = section.items || []
        var on = 0
        for (var i = 0; i < items.length; ++i) {
            if (checks[items[i].id] === true)
                on = on + 1
        }
        if (!items.length || on === 0)
            return Qt.Unchecked
        if (on === items.length)
            return Qt.Checked
        return Qt.PartiallyChecked
    }

    function setGroup(section, on) {
        var items = section.items || []
        for (var i = 0; i < items.length; ++i)
            checks[items[i].id] = on
        tickRev = tickRev + 1
    }

    function setAll(open) {
        var next = {}
        for (var s = 0; s < sections.length; ++s) {
            var section = sections[s]
            if (!section)
                continue
            next["s:" + (section.id || s)] = open
            var items = section.items || []
            for (var i = 0; i < items.length; ++i) {
                var item = items[i]
                next["r:" + (section.id || s) + "/" + ((item && item.id) || i)] = open
            }
        }
        folded = next
        openRev = openRev + 1
    }

    function toggleFold(key) {
        var next = {}
        for (var name in folded)
            next[name] = folded[name]
        next[key] = folded[key] !== true
        folded = next
        openRev = openRev + 1
    }

    function isFoldedOpen(key) {
        return folded[key] === true
    }

    function anyChecked() {
        for (var key in checks) {
            if (checks[key] === true)
                return true
        }
        return false
    }

    function missingPictures() {
        var titles = []
        var seen = {}
        var byId = {}
        for (var s = 0; s < sections.length; ++s) {
            var items = sections[s].items || []
            for (var i = 0; i < items.length; ++i)
                byId[items[i].id] = items[i]
        }
        for (var id in byId) {
            if (checks[id] !== true)
                continue
            var needs = byId[id].needs || []
            for (var n = 0; n < needs.length; ++n) {
                var pic = byId[needs[n]]
                if (!pic || checks[pic.id] === true || seen[pic.id])
                    continue
                seen[pic.id] = true
                titles.push(pic.title || "Picture")
            }
        }
        return titles
    }

    function selectionJson() {
        var items = []
        var outputs = {}
        for (var s = 0; s < sections.length; ++s) {
            var section = sections[s]
            if (String(section.id || "").indexOf("out:") === 0)
                outputs[String(section.id).substring(4)] = targets[section.id] || section.target || ""
            var rows = section.items || []
            for (var i = 0; i < rows.length; ++i) {
                if (checks[rows[i].id] === true)
                    items.push(rows[i].id)
            }
        }
        return JSON.stringify({ items: items, outputs: outputs, targetGuid: importGuid })
    }

    function runImport() {
        var chosen = JSON.parse(selectionJson())
        // Read from the preview: the warning has closed by now.
        chosen.createLogical = (preview.missingLogical || []).length > 0 && _createLogical.checked
        var target = _saveAs.text
        var url = zipUrl
        // The action panes close first (asking when one has changes), or a
        // later OK would write a pane's old copy back (05 Q8, GL-098).
        Helpers.closeActionPanes(function() {
            var info = _parse(_hw.importPack(url, target, JSON.stringify(chosen)))
            // An import that wrote nothing keeps the one before it undoable.
            canUndo = _hw.canUndoPackImport()
            say(info.ok ? (info.report || "Imported.") : (info.error || "Import failed."),
                !info.ok, info.ok && canUndo)
            if (info.ok)
                reloadDevices()
        })
    }

    function undoImport() {
        Helpers.closeActionPanes(function() {
            var info = _parse(_hw.undoPackImport(false))
            if (info.ask) {
                // A file saved again since the import (08 Q5): ask first.
                _undoGate.confirmThen("Undo Import?", info.error || "", "Undo Import",
                                      function() { _showUndo(_parse(_hw.undoPackImport(true))) },
                                      null, true)
                return
            }
            _showUndo(info)
        })
    }

    function _showUndo(info) {
        say(info.ok ? (info.report || "Undid the import.") : (info.error || "Undo failed."), !info.ok)
        canUndo = _hw.canUndoPackImport()
        reloadDevices()
    }

    // The warning before Import: what will be replaced, and what is kept.
    function warningText(p) {
        var lines = []
        var device = p.device || _saveAs.text
        var pieces = p.pieces || []
        var modes = p.modes || []
        // Checked controls are added, not replaced (08 Q3).
        if (p.addsChecks)
            lines.push("Import adds the pack's checked controls to the ones checked on "
                       + device + "; none are unchecked.")
        if (pieces.length || modes.length || !p.addsChecks)
            lines.push("Import replaces these on " + device + ":")
        for (var i = 0; i < pieces.length; ++i)
            lines.push("\u2022 " + pieces[i])
        for (var m = 0; m < modes.length; ++m) {
            var mode = modes[m]
            lines.push("\u2022 The wires and actions of " + device + " in " + mode.name
                       + ": " + mode.here + " here, " + mode.pack + " from the pack.")
        }
        var moves = p.moves || []
        for (var v = 0; v < moves.length; ++v)
            lines.push("Wires to " + moves[v].from + " will send to " + moves[v].to + ".")
        if ((p.leftOut || []).length)
            lines.push(device + " doesn't have " + p.leftOut.join(", ") + ": those are left out.")
        if (p.missingLogical && p.missingLogical.length)
            lines.push("Some wires send to Logical Device inputs that don't exist here: "
                       + p.missingLogical.join(", ") + ".")
        var drivers = p.drivers || []
        for (var d = 0; d < drivers.length; ++d)
            lines.push(drivers[d])
        var missing = missingPictures()
        if (missing.length)
            lines.push("The map uses a picture that is not ticked (" + missing.join(", ")
                       + "): those chips will have no picture.")
        lines.push("")
        if (p.hasModuleFile)
            lines.push("The previous module file is kept in the imported folder.")
        if (modes.length)
            lines.push("The profile changes on disk only when you save it.")
        lines.push("Undo Import puts this import back until you import again, open another pack, or close this window.")
        return lines.join("\n")
    }

    function askImport() {
        var p = _parse(_hw.previewPackImport(zipUrl, _saveAs.text, selectionJson()))
        if (!p.ok) {
            say(p.error || "Could not read that pack.", true)
            return
        }
        preview = p
        _warnText.text = warningText(p)
        _createLogical.checked = true
        _warn.open()
    }

    Component.onCompleted: reloadDevices()
    // Closing keeps the last import: Undo Import is no longer offered.
    onClosing: {
        _hw.keepPackImport()
        // The preview pictures in %TEMP% go with the window.
        _hw.dropPackPreview()
    }

    // 01 S143: both open in the last folder used for Device Packs.
    FilePicker {
        id: _save
        kind: "device-pack"
        mode: "save"
        title: "Export Device Pack"
        defaultSuffix: "zip"
        nameFilters: ["Device packs (*.zip)"]
        folder: _hw.exportFolderUrl()
        onPicked: (selected) => startExport(String(selected))
    }

    FilePicker {
        id: _pick
        kind: "device-pack"
        mode: "open"
        title: "Open Device Pack"
        nameFilters: ["Device packs (*.zip)"]
        folder: _hw.exportFolderUrl()
        onPicked: (selected) => {
            zipUrl = String(selected)
            // Another pack: the last import stays.
            _hw.keepPackImport()
            canUndo = _hw.canUndoPackImport()
            var info = _parse(_hw.peekPackZip(zipUrl))
            if (!info.ok) {
                say(info.error || "Could not read that pack.", true)
                return
            }
            mode = "import"
            _pages.currentIndex = 1
            loadPack(info)
            var suggested = info.suggestedName || ""
            _saveAs.text = suggested
            importGuid = ""
            _importDevice.currentIndex = suggested.length ? importRowOf(suggested) : -1
        }
    }

    // Undo Import over a file changed since the import asks first.
    DismissibleDialog { id: _undoGate }

    // Import is destructive: it replaces the ticked pieces on this machine
    // (checked controls are added, 08 Q3).
    Dialog {
        id: _warn
        objectName: "packWarning"
        title: "Replace with This Pack?"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(Style.dp(560), _win.width - Style.dp(32))
        standardButtons: Dialog.NoButton
        background: Rectangle { color: Style.bgCard; border.color: Style.danger; radius: 4 }
        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                id: _warnText
                objectName: "packWarningText"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.maximumHeight: _win.height * 0.6
                elide: Text.ElideRight
                color: Style.fg
            }
            CheckBox {
                id: _createLogical
                objectName: "packCreateLogical"
                visible: (_win.preview.missingLogical || []).length > 0
                text: "Create the missing Logical Device inputs"
            }
            RowLayout {
                Item { Layout.fillWidth: true }
                Button {
                    text: "Cancel"
                    onClicked: _warn.close()
                }
                Button {
                    objectName: "packReplace"
                    text: "Replace"
                    highlighted: true
                    U.Universal.accent: Style.danger
                    onClicked: {
                        _warn.close()
                        runImport()
                    }
                }
            }
        }
    }

    component PackMark: CheckBox {
        property var section
        tristate: true
        checkState: {
            var rev = _win.tickRev
            return _win.groupState(section)
        }
        nextCheckState: function() {
            var turnOn = _win.groupState(section) !== Qt.Checked
            _win.setGroup(section, turnOn)
            return turnOn ? Qt.Checked : Qt.Unchecked
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(16)
        anchors.bottomMargin: Style.dp(62)
        spacing: Style.dp(10)

        Label {
            text: "Device Pack"
            font.pixelSize: Style.dp(22)
            font.bold: true
            color: Style.foreground
        }
        // 08 Q4: the import changes the profile and files while it runs.
        RunningNote {}
        Label {
            text: mode === "export"
                  ? "Export sends the whole device. Nothing on the device is changed."
                  : "Tick a section to include every row in it. A partial tick means only some rows are included. Nothing is written until you import."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: Style.fgMuted
        }

        TabBar {
            id: _pages
            Layout.fillWidth: true
            onCurrentIndexChanged: {
                mode = currentIndex === 0 ? "export" : "import"
                if (mode === "export")
                    refreshExport()
            }
            TabButton { text: "Export"; width: implicitWidth }
            TabButton { text: "Import"; width: implicitWidth }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: _pages.currentIndex

            ColumnLayout {
                id: _exportPage
                spacing: Style.dp(10)
                ComboBox {
                    id: _exportDevice
                    Layout.fillWidth: true
                    model: _deviceModel
                    // The name, marked "(file damaged)" when its module file
                    // can't be read (08 S106).
                    textRole: "label"
                    onCurrentIndexChanged: refreshExport()
                }
                RowLayout {
                    id: _exportRow
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Style.dp(28)
                    Rectangle {
                        Layout.fillHeight: true
                        // From the page, not the row: the row's height follows
                        // its contents, this width included (a layout loop).
                        Layout.preferredWidth: Math.max(0, Math.min(
                            _exportPage.height - _exportDevice.height - _exportPage.spacing,
                            Style.dp(560)))
                        Layout.maximumWidth: Style.dp(560)
                        color: Style.bgCard
                        border.color: Style.line
                        radius: Style.dp(6)
                        // Decoded in the background at preview size: a large
                        // photo froze the window at each device change (08 S107).
                        Image {
                            objectName: "packExportPhoto"
                            anchors.fill: parent
                            anchors.margins: Style.dp(16)
                            source: exportPhoto
                            asynchronous: true
                            sourceSize.width: Style.dp(560)
                            sourceSize.height: Style.dp(560)
                            fillMode: Image.PreserveAspectFit
                            visible: exportPhoto.length > 0
                        }
                        Label {
                            anchors.centerIn: parent
                            visible: exportPhoto.length === 0
                            text: "No picture"
                            color: Style.fgMuted
                            font.pixelSize: Style.dp(22)
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: Style.dp(16)
                        Item { Layout.fillHeight: true; Layout.maximumHeight: Style.dp(40) }
                        Label {
                            text: exportName.length ? exportName : "No device"
                            color: Style.foreground
                            font.pixelSize: Style.dp(36)
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            text: exportSize.length ? ("Pack size: " + exportSize) : ""
                            color: Style.fg
                            font.pixelSize: Style.dp(24)
                        }
                        // The modes whose wires go in the pack.
                        Label {
                            visible: exportModes.length > 0
                            text: "Wires in these modes"
                            color: Style.fg
                        }
                        Flow {
                            visible: exportModes.length > 0
                            Layout.fillWidth: true
                            spacing: Style.dp(8)
                            Repeater {
                                model: exportModes
                                delegate: CheckBox {
                                    required property var modelData
                                    objectName: "exportMode:" + modelData.name
                                    text: modelData.name + " (" + modelData.count + ")"
                                    checked: {
                                        var rev = _win.exportRev
                                        return _win.exportTicks[modelData.name] === true
                                    }
                                    onToggled: {
                                        _win.exportTicks[modelData.name] = checked
                                        _win.exportRev = _win.exportRev + 1
                                    }
                                }
                            }
                        }
                        // Shown at the top of the import screen.
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: Style.dp(8)
                            Label { text: "Made by"; color: Style.fg }
                            TextField {
                                id: _author
                                objectName: "packAuthor"
                                Layout.fillWidth: true
                                placeholderText: "Your name (optional)"
                            }
                            Label { text: "Note"; color: Style.fg }
                            TextField {
                                id: _note
                                objectName: "packNote"
                                Layout.fillWidth: true
                                placeholderText: "For whoever imports it (optional)"
                            }
                        }
                        Button {
                            objectName: "packExportButton"
                            text: "Export…"
                            focusPolicy: Qt.NoFocus
                            font.pixelSize: Style.dp(18)
                            implicitHeight: Style.dp(44)
                            implicitWidth: Style.dp(160)
                            // One at a time (08 S107).
                            enabled: exportName.length > 0 && exportSize.length > 0
                                     && !_hw.packExporting
                            onClicked: {
                                var hint = _hw.defaultExportUrl(_win.exportDeviceName())
                                _save.currentFile = hint || ""
                                _save.open()
                            }
                        }
                        Label {
                            objectName: "packExportBusy"
                            visible: _hw.packExporting
                            text: "Exporting…"
                            color: Style.fgMuted
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Button {
                            objectName: "packShowFolder"
                            text: "Show Folder"
                            focusPolicy: Qt.NoFocus
                            visible: exportFolder.length > 0
                            onClicked: _hw.showFolder(exportFolder)
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            ColumnLayout {
                spacing: Style.dp(8)
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: "Choose Zip…"
                        focusPolicy: Qt.NoFocus
                        onClicked: {
                            _pick.open()
                        }
                    }
                    Item { Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(16)
                    Rectangle {
                        Layout.preferredWidth: Style.dp(200)
                        Layout.preferredHeight: Style.dp(200)
                        Layout.alignment: Qt.AlignTop
                        color: Style.bgCard
                        border.color: Style.line
                        radius: Style.dp(4)
                        visible: importPhoto.length > 0 && mode === "import"
                        Image {
                            anchors.fill: parent
                            anchors.margins: Style.dp(8)
                            source: importPhoto
                            asynchronous: true
                            sourceSize.width: Style.dp(200)
                            sourceSize.height: Style.dp(200)
                            fillMode: Image.PreserveAspectFit
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Label {
                            text: importName.length ? importName : "No pack open"
                            color: Style.foreground
                            font.pixelSize: Style.dp(18)
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            text: "Windows name in the pack. The device you choose below is the one that is written."
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            color: Style.fgMuted
                            visible: importName.length > 0
                        }
                        // Who made the pack, when, and their note.
                        Label {
                            objectName: "packNotes"
                            visible: text.length > 0
                            text: {
                                var n = _win.packNotes || {}
                                var by = []
                                if (n.author)
                                    by.push("By " + n.author)
                                if (n.exportedOn)
                                    by.push(n.exportedOn)
                                if (n.program)
                                    by.push("Gremlin-Platforms " + n.program)
                                var lines = []
                                if (by.length)
                                    lines.push(by.join(" \u00b7 "))
                                if (n.note)
                                    lines.push(n.note)
                                return lines.join("\n")
                            }
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            color: Style.fg
                        }
                        // A driver the pack needs isn't found: say so at once.
                        Label {
                            objectName: "packDrivers"
                            visible: _win.packDrivers.length > 0
                            text: _win.packDrivers.join("\n")
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            color: Style.warn
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Put this pack on"; color: Style.foreground }
                    // One target: picking a device fills the name below, and
                    // typing a name picks that device (or none, if it is new).
                    ComboBox {
                        id: _importDevice
                        objectName: "packImportDevice"
                        Layout.fillWidth: true
                        model: _deviceModel
                        // Named as on Home (twins "(2)", 08 S106a); the name
                        // below is the device's own name.
                        textRole: "label"
                        displayText: currentIndex < 0 ? "(the name typed below)" : currentText
                        onActivated: (index) => {
                            var row = _deviceModel.get(index)
                            _saveAs.text = row.name || ""
                            _win.importGuid = String(row.guid || "")
                        }
                    }
                }
                TextField {
                    id: _saveAs
                    Layout.fillWidth: true
                    placeholderText: "Device name on this machine (or pick one above)"
                    onTextEdited: {
                        _win.importGuid = ""
                        _importDevice.currentIndex = _win.importRowOf(text.trim())
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 0
                    spacing: Style.dp(8)
                    Button {
                        text: "Open All"
                        focusPolicy: Qt.NoFocus
                        enabled: sections.length > 0
                        onClicked: setAll(true)
                    }
                    Button {
                        text: "Close All"
                        focusPolicy: Qt.NoFocus
                        enabled: sections.length > 0
                        onClicked: setAll(false)
                    }
                    Item { Layout.fillWidth: true }
                }
                ScrollView {
                    id: _scroll
                    objectName: "packList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    // The list takes the room left and scrolls: its content's
                    // height must not push it up over the buttons above.
                    Layout.preferredHeight: Style.dp(120)
                    Layout.minimumHeight: Style.dp(60)
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ColumnLayout {
                        width: _scroll.availableWidth
                        spacing: Style.dp(8)
                        Repeater {
                            model: _win.sections
                            delegate: ColumnLayout {
                                required property var modelData
                                required property int index
                                property string sectionKey: "s:" + (modelData.id || index)
                                Layout.fillWidth: true
                                spacing: Style.dp(4)
                                Rectangle {
                                    Layout.fillWidth: true
                                    height: Style.dp(32)
                                    color: Style.bgRaised
                                    radius: Style.dp(3)
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: Style.dp(6)
                                        anchors.rightMargin: Style.dp(8)
                                        spacing: Style.dp(6)
                                        PackMark { section: modelData }
                                        Item {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            RowLayout {
                                                anchors.fill: parent
                                                spacing: Style.dp(6)
                                                Label {
                                                    text: {
                                                        var rev = _win.openRev
                                                        return _win.isFoldedOpen(sectionKey) ? "\u25BC" : "\u25B6"
                                                    }
                                                    color: Style.fg
                                                    font.pixelSize: Style.dp(10)
                                                }
                                                Label {
                                                    text: modelData.title || ""
                                                    color: Style.fg
                                                    font.pixelSize: Style.dp(13)
                                                    font.bold: true
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: _win.toggleFold(sectionKey)
                                            }
                                        }
                                    }
                                }
                                ColumnLayout {
                                    visible: {
                                        var rev = _win.openRev
                                        return _win.isFoldedOpen(sectionKey)
                                    }
                                    Layout.fillWidth: true
                                    Layout.leftMargin: Style.dp(28)
                                    spacing: Style.dp(4)
                                    TextField {
                                        visible: modelData.kind === "output"
                                        Layout.fillWidth: true
                                        placeholderText: "Output name on this machine"
                                        Component.onCompleted: text = _win.targets[modelData.id] || modelData.target || ""
                                        onTextEdited: _win.targets[modelData.id] = text
                                    }
                                    Repeater {
                                        id: itemRows
                                        property string sectionId: modelData.id || ""
                                        model: modelData.items || []
                                        delegate: ColumnLayout {
                                            required property var modelData
                                            required property int index
                                            property string rowKey: "r:" + itemRows.sectionId + "/" + (modelData.id || index)
                                            Layout.fillWidth: true
                                            spacing: Style.dp(2)
                                            Rectangle {
                                                Layout.fillWidth: true
                                                height: Style.dp(28)
                                                color: Style.bgCard
                                                border.color: Style.line
                                                radius: Style.dp(3)
                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: Style.dp(6)
                                                    anchors.rightMargin: Style.dp(8)
                                                    spacing: Style.dp(6)
                                                    CheckBox {
                                                        checked: {
                                                            var rev = _win.tickRev
                                                            return _win.checks[modelData.id] === true
                                                        }
                                                        onToggled: {
                                                            _win.checks[modelData.id] = checked
                                                            _win.tickRev = _win.tickRev + 1
                                                        }
                                                    }
                                                    Item {
                                                        Layout.fillWidth: true
                                                        Layout.fillHeight: true
                                                        RowLayout {
                                                            anchors.fill: parent
                                                            spacing: Style.dp(6)
                                                            Label {
                                                                text: {
                                                                    var rev = _win.openRev
                                                                    return _win.isFoldedOpen(rowKey) ? "\u25BC" : "\u25B6"
                                                                }
                                                                color: Style.fgMuted
                                                                font.pixelSize: Style.dp(10)
                                                            }
                                                            Label {
                                                                text: modelData.title || ""
                                                                color: Style.fg
                                                                Layout.fillWidth: true
                                                                elide: Text.ElideRight
                                                            }
                                                        }
                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: _win.toggleFold(rowKey)
                                                        }
                                                    }
                                                }
                                            }
                                            ColumnLayout {
                                                visible: {
                                                    var rev = _win.openRev
                                                    return _win.isFoldedOpen(rowKey)
                                                }
                                                Layout.fillWidth: true
                                                Layout.leftMargin: Style.dp(28)
                                                spacing: Style.dp(4)
                                                Image {
                                                    visible: modelData.kind === "image" && (modelData.url || "").length > 0
                                                    Layout.preferredWidth: Style.dp(480)
                                                    Layout.preferredHeight: Style.dp(320)
                                                    Layout.maximumWidth: _scroll.availableWidth - Style.dp(56)
                                                    fillMode: Image.PreserveAspectFit
                                                    asynchronous: true
                                                    sourceSize.width: Style.dp(480)
                                                    sourceSize.height: Style.dp(320)
                                                    source: modelData.url || ""
                                                }
                                                Label {
                                                    visible: modelData.kind !== "image"
                                                    text: modelData.body || ""
                                                    color: Style.fg
                                                    wrapMode: Text.WordWrap
                                                    Layout.fillWidth: true
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                RowLayout {
                    Button {
                        objectName: "packImport"
                        text: "Import"
                        focusPolicy: Qt.NoFocus
                        enabled: {
                            var rev = tickRev
                            return zipUrl.length > 0 && packInfo.ok === true && _saveAs.text.length > 0 && anyChecked()
                        }
                        onClicked: askImport()
                    }
                    Button {
                        objectName: "packUndo"
                        text: "Undo Import"
                        focusPolicy: Qt.NoFocus
                        visible: canUndo
                        onClicked: undoImport()
                    }
                }
            }
        }

        MessageLine {
            id: _message
            objectName: "packMessage"
            Layout.fillWidth: true
            busy: _hw.packExporting === true
        }
    }
}
