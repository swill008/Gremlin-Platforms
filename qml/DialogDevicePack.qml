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
    id: _win
    width: 860
    height: 780
    minimumWidth: Style.dp(720)
    minimumHeight: Style.dp(640)
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
    property int tickRev: 0
    property int openRev: 0
    property var folded: ({})

    ListModel { id: _deviceModel }
    HardwareProfile { id: _hw }

    function _parse(raw) {
        try {
            return JSON.parse(raw)
        } catch (e) {
            return { ok: false, error: "Bad response" }
        }
    }

    function reloadDevices() {
        var info = _parse(_hw.packDevices())
        var rows = (info && info.devices) ? info.devices : []
        _deviceModel.clear()
        for (var i = 0; i < rows.length; ++i)
            _deviceModel.append(rows[i])
        if (_exportDevice.count > 0 && _exportDevice.currentIndex < 0)
            _exportDevice.currentIndex = 0
        refreshExport()
    }

    function refreshExport() {
        if (mode !== "export")
            return
        var name = _exportDevice.currentText || ""
        exportName = name
        exportPhoto = ""
        exportSize = ""
        if (!name.length) {
            status = "Choose a device."
            return
        }
        var info = _parse(_hw.peekPackDevice(name))
        if (!info.ok) {
            status = info.error || "This device has no module file yet."
            return
        }
        exportName = info.device || name
        exportPhoto = info.photoUrl || ""
        exportSize = info.sizeText || ""
        status = ""
    }

    function loadPack(info) {
        packInfo = info
        importName = info.exportedName || ""
        importPhoto = info.photoUrl || ""
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
        status = ""
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
        return JSON.stringify({ items: items, outputs: outputs })
    }

    function runImport() {
        var info = _parse(_hw.importPack(zipUrl, _saveAs.text, selectionJson()))
        status = info.ok ? (info.report || "Imported.") : (info.error || "Import failed.")
        if (info.ok)
            reloadDevices()
    }

    function askImport() {
        var missing = missingPictures()
        if (!missing.length) {
            runImport()
            return
        }
        _warnText.text = "The map uses a picture that is not ticked: "
                + missing.join(", ")
                + ". Those chips will have no picture."
        _warn.open()
    }

    Component.onCompleted: {
        width = Style.dp(860)
        height = Style.dp(780)
        reloadDevices()
    }

    FileDialog {
        id: _save
        title: "Export device pack"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "zip"
        nameFilters: ["Device packs (*.zip)"]
        currentFolder: _hw.exportFolderUrl()
        onAccepted: {
            var dest = Helpers.fileDialogUrl(_save)
            var name = _exportDevice.currentText || ""
            var info = _parse(_hw.exportPack(name, dest))
            status = info.ok
                    ? ("Wrote " + info.path + (info.sizeText ? " (" + info.sizeText + ")." : "."))
                    : (info.error || "Export failed.")
        }
    }

    FileDialog {
        id: _pick
        title: "Open device pack"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Device packs (*.zip)"]
        currentFolder: _hw.exportFolderUrl()
        onAccepted: {
            zipUrl = Helpers.fileDialogUrl(_pick)
            var info = _parse(_hw.peekPackZip(zipUrl))
            if (!info.ok) {
                status = info.error || "Could not read that pack."
                return
            }
            mode = "import"
            _pages.currentIndex = 1
            loadPack(info)
            var suggested = info.suggestedName || ""
            _saveAs.text = suggested
            if (suggested.length) {
                for (var i = 0; i < _importDevice.count; i++) {
                    if (_importDevice.textAt(i) === suggested) {
                        _importDevice.currentIndex = i
                        break
                    }
                }
            }
        }
    }

    Dialog {
        id: _warn
        title: "Picture not included"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Style.dp(460)
        standardButtons: Dialog.NoButton
        background: Rectangle { color: Style.bgCard; border.color: Style.line; radius: 4 }
        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                id: _warnText
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                color: Style.fg
            }
            RowLayout {
                Item { Layout.fillWidth: true }
                Button {
                    text: "Go back"
                    onClicked: _warn.close()
                }
                Button {
                    text: "Import"
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
                spacing: Style.dp(10)
                ComboBox {
                    id: _exportDevice
                    Layout.fillWidth: true
                    model: _deviceModel
                    textRole: "name"
                    onActivated: refreshExport()
                    onCurrentIndexChanged: refreshExport()
                }
                RowLayout {
                    id: _exportRow
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: Style.dp(28)
                    Rectangle {
                        Layout.fillHeight: true
                        Layout.preferredWidth: Math.min(_exportRow.height, Style.dp(560))
                        Layout.maximumWidth: Style.dp(560)
                        color: Style.bgCard
                        border.color: Style.line
                        radius: Style.dp(6)
                        Image {
                            anchors.fill: parent
                            anchors.margins: Style.dp(16)
                            source: exportPhoto
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
                        Button {
                            text: "Export…"
                            focusPolicy: Qt.NoFocus
                            font.pixelSize: Style.dp(18)
                            implicitHeight: Style.dp(44)
                            implicitWidth: Style.dp(160)
                            enabled: (_exportDevice.currentText || "").length > 0 && exportSize.length > 0
                            onClicked: {
                                var name = _exportDevice.currentText
                                var folder = _hw.exportFolderUrl()
                                var hint = _hw.defaultExportUrl(name)
                                _save.currentFolder = folder
                                if (hint && hint.length) {
                                    try { _save.selectedFile = hint } catch (e) {}
                                    try { _save.currentFile = hint } catch (e) {}
                                }
                                _save.open()
                            }
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
                        text: "Choose zip…"
                        focusPolicy: Qt.NoFocus
                        onClicked: {
                            _pick.currentFolder = _hw.exportFolderUrl()
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
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Put this pack on"; color: Style.foreground }
                    ComboBox {
                        id: _importDevice
                        Layout.fillWidth: true
                        model: _deviceModel
                        textRole: "name"
                        onActivated: _saveAs.text = currentText
                    }
                }
                TextField {
                    id: _saveAs
                    Layout.fillWidth: true
                    placeholderText: "Device name on this machine"
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 0
                    spacing: Style.dp(8)
                    Button {
                        text: "Open all"
                        focusPolicy: Qt.NoFocus
                        enabled: sections.length > 0
                        onClicked: setAll(true)
                    }
                    Button {
                        text: "Close all"
                        focusPolicy: Qt.NoFocus
                        enabled: sections.length > 0
                        onClicked: setAll(false)
                    }
                    Item { Layout.fillWidth: true }
                }
                ScrollView {
                    id: _scroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
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
                Button {
                    text: "Import"
                    focusPolicy: Qt.NoFocus
                    enabled: {
                        var rev = tickRev
                        return zipUrl.length > 0 && packInfo.ok === true && _saveAs.text.length > 0 && anyChecked()
                    }
                    onClicked: askImport()
                }
            }
        }

        Label {
            text: status
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
            color: Style.fg
            visible: status.length > 0
        }
    }
}
