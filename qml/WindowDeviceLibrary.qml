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
        "settings": "Device Library Settings saved."
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
    readonly property bool canCopy: !busy && hasSel
        && (isSetup || details.hasCurrent === true || details.count > 0)
    // S12: what the device has now (a module file, or plugged in: its
    // bindings) can be saved; a Deleted or pack-only device has nothing.
    readonly property bool canSave: !busy && hasSel && details.hasCurrent === true
    // S30: any stick with an id, plugged in or not.
    readonly property bool canOutput: !busy && hasSel && (details.guid || "").length > 0
    readonly property bool canDelete: !busy && hasSel
        && (isSetup || details.count > 0 || details.canDeleteDevice === true)

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
        if (!hasSel || busy)
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
    function askDelete() {
        if (!canDelete)
            return
        if (isSetup)
            _deleteDlg.ask(details.key, "Delete the saved setup “" + details.name + "”?",
                           "It is removed from the Device Library. This can't be undone.")
        else if (details.canDeleteDevice)
            _deleteDlg.ask(details.key, "Delete " + details.name + " and its saved setups?",
                           details.countText + " are removed with it. This can't be undone.")
        else
            _deleteDlg.ask(details.key, "Delete the saved setups of " + details.name + "?",
                           details.countText + " are removed. The device itself stays: "
                           + "a stick that is set up here is deleted with Delete Device on Home.")
    }

    // The Device Library Guide: only the Device Library's topics (S42).
    function openGuide() {
        Helpers.createComponent("DialogDeviceLibraryGuide.qml")
    }

    Shortcut { sequence: "F1"; onActivated: _lib.openGuide() }
    Shortcut { sequence: "F2"; onActivated: _lib.startRename() }
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
                    enabled: _lib.isSetup && !_lib.busy
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
                ThemedMenuItem { text: "Rename…"; hint: "F2"; enabled: _lib.hasSel && !_lib.busy; onTriggered: _lib.startRename() }
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
                ThemedMenuItem { text: "Swap with Another Stick…"; enabled: !_lib.busy && _lib.deviceConnected; onTriggered: _lib.openSwap() }
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
                                readonly property bool isSel: _lib.lib && _lib.lib.selected === modelData.key
                                objectName: "libraryRow_" + modelData.key
                                width: ListView.view.width
                                height: isDev ? Style.dp(50) : Style.dp(42)
                                color: isSel ? Style.bgSelected : (isDev ? Style.bgCard : Style.bgWell)

                                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Style.line }
                                Rectangle { visible: _row.isSel; width: Style.dp(3); height: parent.height; color: Style.accent }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: _lib.lib.select(_row.modelData.key)
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
                                    Label { text: "History"; font.bold: true; color: Style.fgStrong }
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
                                visible: _lib.isDevice
                                objectName: "librarySaveButton"
                                Layout.fillWidth: true
                                text: "Save to Device Library…"
                                enabled: _lib.canSave
                                onClicked: _lib.openSave()
                            }
                            Button {
                                objectName: "libraryCopyButton"
                                Layout.fillWidth: true
                                text: "Copy to Another Stick…"
                                highlighted: true
                                enabled: _lib.canCopy
                                onClicked: _lib.openCopy()
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Button {
                                    objectName: "librarySwapButton"
                                    Layout.fillWidth: true
                                    text: "Swap with Another Stick…"
                                    enabled: !_lib.busy && _lib.deviceConnected
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
                                    Layout.fillWidth: true
                                    text: "Export…"
                                    enabled: !_lib.busy && _lib.isSetup
                                    onClicked: {
                                        _exportFile.selectedFile = _lib.details.name.replace(/[\\/:*?"<>|]/g, "_") + ".zip"
                                        _exportFile.open()
                                    }
                                }
                                Button {
                                    id: _deleteButton
                                    objectName: "libraryDeleteButton"
                                    Layout.fillWidth: true
                                    text: "Delete…"
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

    // S15: Delete… asks first.
    Dialog {
        id: _deleteDlg
        objectName: "libraryDeleteDialog"
        property string key: ""
        property string body: ""
        anchors.centerIn: Overlay.overlay
        width: Math.min(_lib.width - Style.dp(40), Style.dp(520))
        modal: true
        function ask(k, heading, text) {
            key = k
            title = heading
            body = text
            open()
        }
        Label { width: parent.width; wrapMode: Text.Wrap; text: _deleteDlg.body }
        footer: DialogButtonBox {
            Button { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            Button { text: "Delete"; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
        }
        onAccepted: _lib.lib.deleteItem(key)
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
