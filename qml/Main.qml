// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Base
import Gremlin.Config
import Gremlin.Device
import Gremlin.Profile
import Gremlin.Style
import Gremlin.UI

import "helpers.js" as Helpers

ApplicationWindow {

    title: backend ? backend.windowTitle : "Gremlin-Platforms R1"
    minimumWidth: 1300
    minimumHeight: 700
    width: 1400
    height: 900
    visible: true
    id: _root

    WindowPlacement { id: _windowPlacement }

    Component.onCompleted: () => {
        if (backend) {
            Style.isDarkMode = backend.useDarkMode
        }
        _windowPlacement.restore(_root)
        refreshSourceModuleCount()
    }

    Universal.theme: Style.theme
    color: Style.background

    property string pinSlug: ""
    property string configTitleName: ""
    property string configDirection: ""
    property int sourceModuleCount: 0
    property bool outputViewPanel: true
    property bool catalogPanel: true
    property bool _panelReady: false
    property string _panelDevice: ""

    function panelKind() {
        return configDirection === "dest" ? "output" : "configuration"
    }

    function panelDeviceId() {
        var guid = uiState ? String(uiState.currentDevice || "") : ""
        if (guid.length)
            return guid
        return configTitleName
    }

    function applyDisplayPanel() {
        var id = panelDeviceId()
        _panelDevice = id
        var open = id.length ? _windowPlacement.displayPanelOpen(panelKind(), id) : true
        _panelReady = false
        if (configDirection === "dest")
            outputViewPanel = open
        else
            catalogPanel = open
        _panelReady = true
    }

    function rememberDisplayPanel() {
        if (!_panelReady)
            return
        var id = _panelDevice.length ? _panelDevice : panelDeviceId()
        if (!id.length)
            return
        var kind = panelKind()
        var open = kind === "output" ? outputViewPanel : catalogPanel
        _windowPlacement.setDisplayPanelOpen(kind, id, open)
    }

    function refreshDestBound() {
        if (_destBound)
            _destBound.text = _moduleModel.boundLine(configTitleName)
    }
    property var configureWin: null

    ModuleListModel {
        id: _moduleModel
    }

    function focusedCard() {
        var slug = _moduleModel.focusedSlug
        for (var i = 0; i < _moduleModel.rowCount(); ++i) {
            var ix = _moduleModel.index(i, 0)
            if (_moduleModel.data(ix, 0x0101) === slug)
                return ix
        }
        return null
    }

    function moduleField(rolePlus, slug) {
        // roles start at UserRole+1 = 0x0101
        for (var i = 0; i < _moduleModel.rowCount(); ++i) {
            var ix = _moduleModel.index(i, 0)
            if (String(_moduleModel.data(ix, 257)) === String(slug)) {
                return _moduleModel.data(ix, 256 + rolePlus)
            }
        }
        return ""
    }

    function moduleFileName(card) {
        if (!card)
            return ""
        return card.rawName || card.name || ""
    }

    function openConfigurationNow(card) {
        if (!uiState || !card)
            return
        _panelReady = false
        _moduleModel.setFocus(card.slug)
        configTitleName = moduleFileName(card)
        refreshDestBound()
        configDirection = card.direction || "source"
        uiState.setCurrentDevice(card.guid)
        uiState.setCurrentTab(card.tab || "physical")
        uiState.setCurrentRoom("configuration")
        applyDisplayPanel()
        refreshSourceModuleCount()
    }

    property var _afterDisplayLeave: null

    function leaveDisplayThen(next) {
        _afterDisplayLeave = next
        continueDisplayLeave()
    }

    function continueDisplayLeave() {
        if (_deviceInputList && _deviceInputList.hasUnsaved && _deviceInputList.hasUnsaved()) {
            _deviceInputList.requestLeave()
            return
        }
        if (_outputModuleView && _outputModuleView.hasUnsaved && _outputModuleView.hasUnsaved()) {
            _outputModuleView.requestLeave()
            return
        }
        var next = _afterDisplayLeave
        _afterDisplayLeave = null
        if (next)
            next()
    }

    function cancelDisplayLeave() {
        _afterDisplayLeave = null
    }

    function openConfigurationForCard(card) {
        if (!uiState || !card)
            return
        var name = moduleFileName(card)
        var direction = card.direction || "source"
        if (uiState.currentRoom === "configuration" && configTitleName === name && configDirection === direction) {
            applyDisplayPanel()
            return
        }
        leaveDisplayThen(function() { openConfigurationNow(card) })
    }

    function refreshSourceModuleCount() {
        var slugs = _moduleModel ? _moduleModel.pileLeaders("source") : []
        sourceModuleCount = slugs ? slugs.length : 0
    }

    function cycleConfiguration(step) {
        if (configDirection === "dest" || !_moduleModel || sourceModuleCount < 2)
            return
        var slugs = _moduleModel.pileLeaders("source") || []
        if (!slugs.length)
            return
        var focus = String(_moduleModel.focusedSlug || "")
        var index = 0
        for (var i = 0; i < slugs.length; ++i) {
            if (String(slugs[i]) === focus) {
                index = i
                break
            }
            var members = _moduleModel.pileMembers(slugs[i]) || []
            var found = false
            for (var m = 0; m < members.length; ++m) {
                if (String(members[m]) === focus) {
                    index = i
                    found = true
                    break
                }
            }
            if (found)
                break
        }
        var nextIndex = (index + step + slugs.length) % slugs.length
        var card = _moduleModel.cardMap(slugs[nextIndex])
        if (card && card.slug)
            openConfigurationForCard(card)
    }

    function openOutputViewForCard(card) {
        openConfigurationForCard(card)
    }

    function openConfigurationForFocus() {
        var card = _statusLastCard
        if (!card || !card.slug)
            card = _moduleModel.focusedCardMap()
        if (card && card.slug)
            openConfigurationForCard(card)
        else if (uiState)
            uiState.setCurrentRoom("configuration")
    }

    property var _statusLastCard: null

    function pinFocusedControlDisplay() {
        var card = _statusLastCard && _statusLastCard.slug ? _statusLastCard : _moduleModel.focusedCardMap()
        if (!card || !card.slug)
            return
        pinSlug = (pinSlug === card.slug) ? "" : card.slug
    }

    function openConfigureModule(direction) {
        var card = _statusLastCard && _statusLastCard.slug ? _statusLastCard : _moduleModel.focusedCardMap()
        var want = direction
        if (!want && card && card.direction === "dest")
            want = "dest"
        if (!want)
            want = "source"
        if (configureWin) {
            configureWin.direction = want
            configureWin.deviceName = card ? moduleFileName(card) : ""
            configureWin.deviceGuid = card ? (card.guid || "") : ""
            configureWin.moduleModel = _moduleModel
            configureWin.raise()
            configureWin.requestActivate()
            return
        }
        var comp = Qt.createComponent("DialogConfigureModule.qml")
        if (comp.status !== Component.Ready) {
            console.log(comp.errorString())
            return
        }
        configureWin = comp.createObject(_root, {
            "direction": want,
            "deviceName": card ? moduleFileName(card) : "",
            "deviceGuid": card ? (card.guid || "") : "",
            "moduleModel": _moduleModel
        })
        if (!configureWin)
            return
        configureWin.closing.connect(function() {
            Qt.callLater(function() { _root.configureWin = null })
        })
        configureWin.show()
        configureWin.raise()
        configureWin.requestActivate()
    }

    function openExportDevices() {
        Helpers.createComponent("DialogExportDevices.qml", {
            "deviceName": (_statusLastCard && moduleFileName(_statusLastCard))
                          ? moduleFileName(_statusLastCard)
                          : moduleFileName(_moduleModel.focusedCardMap())
        })
    }

    function openHiddenDevices() {
        Helpers.createComponent("DialogHiddenDevices.qml", {
            "moduleModel": _moduleModel
        })
    }

    function pairingForCard(card) {
        if (!card)
            return
        if (card.bus === "XInput" || card.tab === "xbox" || card.slug === "xbox")
            Helpers.toggleComponent("DialogXboxViewer.qml")
        else
            Helpers.toggleComponent("DialogInputViewer.qml")
    }

    function closeWorkRoomNow() {
        if (!uiState)
            return
        _panelReady = false
        configTitleName = ""
        configDirection = ""
        uiState.setCurrentRoom("status")
        uiState.setCurrentTab("physical")
        if (_scriptButton)
            _scriptButton.checked = false
        if (_profileSettingsButton)
            _profileSettingsButton.checked = false
    }

    function closeWorkRoom() {
        leaveDisplayThen(function() { closeWorkRoomNow() })
    }

    function requestNewProfile() {
        _newProfileDialog.open()
    }

    function saveCurrentProfile() {
        if (!backend) {
            return
        }
        var fpath = backend.profilePath()
        if (fpath === "") {
            _saveProfileFileDialog.open()
        } else {
            showSaveResult(backend.saveProfile(fpath), fpath)
        }
    }

    function buttonMapWindow() {
        return Helpers.windowOf("DialogJoystickButtonMap.qml")
    }

    function openButtonMapForCard(card) {
        var name = ""
        var photo = ""
        var guid = ""
        if (card) {
            name = String(card.rawName || card.name || "")
            photo = String(card.photo || "")
            guid = String(card.guid || "")
        }
        name = name.trim()
        if (!name.length)
            return
        var existing = buttonMapWindow()
        if (existing && existing.openForDevice) {
            existing.openForDevice(name, photo, guid)
            existing.show()
            existing.raise()
            existing.requestActivate()
            return
        }
        Helpers.createComponent("DialogJoystickButtonMap.qml", {
            "targetName": name,
            "targetGuid": guid,
            "initialPhoto": photo
        })
    }

    function fileNameOf(path) {
        var text = String(path || "")
        var cut = Math.max(text.lastIndexOf("/"), text.lastIndexOf("\\"))
        return cut >= 0 ? text.slice(cut + 1) : text
    }

    function openActionEditor(hid) {
        var name = _deviceInputList ? _deviceInputList.claimDeviceName : ""
        var single = hid >= 0
        var existing = Helpers.windowOf("DialogActionEditor.qml")
        if (existing && existing.openFor) {
            existing.openFor(name, _deviceModel, hid, single)
            return
        }
        Helpers.createComponent("DialogActionEditor.qml", {
            "deviceName": name,
            "device": _deviceModel,
            "startHid": hid,
            "singleControl": single
        })
    }

    function openBlankButtonMap() {
        var existing = buttonMapWindow()
        if (existing && existing.openBlank) {
            existing.openBlank()
            return
        }
        Helpers.createComponent("DialogJoystickButtonMap.qml", {
            "startBlank": true,
            "targetName": "",
            "targetGuid": ""
        })
    }

    function buttonMapNeedsLeave() {
        var w = buttonMapWindow()
        if (!w)
            return false
        if (!w.editing)
            return false
        if (typeof w.isDirty !== "function")
            return false
        return w.isDirty()
    }

    function offerButtonMapLeaveThenQuit() {
        var w = buttonMapWindow()
        if (!w)
            return false
        if (typeof w.requestLeaveForAppQuit === "function") {
            w.requestLeaveForAppQuit()
            return true
        }
        return false
    }

    function deactivateThenQuit() {
        if (buttonMapNeedsLeave()) {
            offerButtonMapLeaveThenQuit()
            return
        }
        if (backend && backend.gremlinActive) {
            backend.toggleActiveState()
        }
        Qt.quit()
    }

    function quitGremlin() {
        if (backend && backend.profileContainsUnsavedChanges) {
            _saveBeforeQuitDialog.ask()
        } else {
            deactivateThenQuit()
        }
    }

    function showSaveResult(ok, path) {
        if (ok)
            _saveResultDialog.announce(true, "Saved to the profile.")
        else
            _saveResultDialog.announce(false, "Not written. It is still only on this screen.")
    }

    ColorInformation {
        id: colorInformation
    }

    ErrorDialog {
        id: _errorDialog

        title: "A fatal error ocurred"
    }

    MessageDialog {
        id: _notificationDialog

        modality: Qt.ApplicationModal
        buttons: MessageDialog.Ok
    }

    DismissibleDialog {
        id: _saveBeforeQuitDialog

        detail: "There are unsaved changes in the current profile. Save them before quitting, or they will be lost."

        onSaveChosen: {
            if (!backend)
                return
            var fpath = backend.profilePath()
            if (fpath === "") {
                _saveProfileFileDialog.quitAfterSave = true
                _saveProfileFileDialog.open()
            } else if (backend.saveProfile(fpath)) {
                deactivateThenQuit()
            } else {
                showSaveResult(false, fpath)
            }
        }
        onDiscardChosen: deactivateThenQuit()
    }

    DismissibleDialog {
        id: _newProfileDialog

        titleText: "New Profile"
        messageText: "Creating a new profile will replace the current profile. Unsaved mappings will be lost.\n\nProgram Options and OSC Settings will Persist"
        confirmText: "Create new profile"
        cancelText: "Cancel"
        destructive: true

        onConfirmed: {
            if (backend) {
                backend.newProfile()
            }
        }
    }

    DismissibleDialog {
        id: _saveResultDialog

        confirmText: "OK"
    }

    VJoyStatusPopup {
        id: _vjoyStatusPopup
    }

    FileDialog {
        id: _saveProfileFileDialog
        title: "Please choose a file"

        property bool quitAfterSave: false

        acceptLabel: "Save"
        defaultSuffix: "xml"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Profile files (*.xml)"]

        onAccepted: () => {
            if (!backend) {
                return
            }
            var ok = backend.saveProfile(currentFile)
            if (quitAfterSave) {
                quitAfterSave = false
                if (ok) {
                    deactivateThenQuit()
                } else {
                    showSaveResult(false, "")
                }
            } else {
                showSaveResult(ok, backend.profilePath())
            }
        }
    }

    FileDialog {
        id: _loadProfileFileDialog
        title: "Please choose a file"

        acceptLabel: "Open"
        defaultSuffix: "xml"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Profile files (*.xml)"]

        onAccepted: () => {
            if (backend) {
                backend.loadProfile(currentFile)
            }
        }
    }

    HintsTooltip {
        id: _hintsTooltip

        hints: []
    }

    menuBar: MenuBar {
        Menu {
            title: qsTr("File")

            Action {
                text: qsTr("New Profile")
                shortcut: "Ctrl+N"
                onTriggered: () => { requestNewProfile() }
            }
            Action {
                text: qsTr("Load Profile")
                shortcut: "Ctrl+O"
                onTriggered: () => { _loadProfileFileDialog.open() }
            }
            AutoSizingMenu {
                title: qsTr("Recent")

                Repeater {
                    model: backend ? backend.recentProfiles : []
                    delegate: MenuItem {
                        text: fileNameOf(modelData)
                        ToolTip.visible: hovered
                        ToolTip.text: modelData
                        ToolTip.delay: 400
                        onTriggered: () => {
                            if (backend) {
                                backend.loadProfile(modelData)
                            }
                        }
                    }
                }
            }
            Action {
                text: qsTr("Save Profile")
                shortcut: "Ctrl+S"
                onTriggered: () => { saveCurrentProfile() }
            }
            MenuItem {
                text: qsTr("Save Profile As")
                onTriggered: () => { _saveProfileFileDialog.open() }
            }
            MenuItem {
                text: qsTr("Exit")
                onTriggered: () => { quitGremlin() }
            }
        }

        Menu {
            title: qsTr("View")

            MenuItem {
                text: qsTr("Home")
                onTriggered: () => { closeWorkRoom() }
            }
            MenuItem {
                text: qsTr("Configuration")
                onTriggered: () => { openConfigurationForFocus() }
            }
            MenuItem {
                text: qsTr("Control Display")
                onTriggered: () => { pinFocusedControlDisplay() }
            }
            MenuSeparator {}
            Menu {
                title: qsTr("Home layout")
                MenuItem { text: qsTr("Single list"); onTriggered: _moduleModel.setSplitMode("none") }
                MenuItem { text: qsTr("Side by side"); onTriggered: _moduleModel.setSplitMode("vertical") }
                MenuItem { text: qsTr("Stacked"); onTriggered: _moduleModel.setSplitMode("horizontal") }
            }
            MenuItem {
                text: qsTr("Hidden devices…")
                onTriggered: () => { openHiddenDevices() }
            }
            MenuItem {
                text: qsTr("Scripts")
                onTriggered: () => {
                    leaveDisplayThen(function() {
                        if (uiState) {
                            uiState.setCurrentRoom("scripts")
                            uiState.setCurrentTab("scripts")
                        }
                    })
                }
            }
            MenuItem {
                text: qsTr("Profile Settings")
                onTriggered: () => {
                    leaveDisplayThen(function() {
                        if (uiState) {
                            uiState.setCurrentRoom("settings")
                            uiState.setCurrentTab("settings")
                        }
                    })
                }
            }
        }

        Menu {
            title: qsTr("Tools")

            MenuItem {
                text: qsTr("Manage Modes")
                onTriggered: () => {
                    Helpers.createComponent("DialogManageModes.qml")
                }
            }
            MenuItem {
                text: qsTr("vJoy Viewer")
                onTriggered: () => {
                    Helpers.toggleComponent("DialogInputViewer.qml")
                }
            }
            MenuItem {
                text: qsTr("Xbox Viewer")
                onTriggered: () => {
                    Helpers.toggleComponent("DialogXboxViewer.qml")
                }
            }
            MenuItem {
                text: qsTr("Device Viewer")
                onTriggered: () => { Helpers.toggleComponent("DialogDeviceViewer.qml") }
            }
            MenuItem {
                text: qsTr("Action Editor")
                onTriggered: () => { openActionEditor(-1) }
            }
            MenuItem {
                text: qsTr("Button Map")
                onTriggered: () => { openBlankButtonMap() }
            }
            MenuItem {
                text: qsTr("Calibration")
                onTriggered: () => {
                    Helpers.createComponent("DialogCalibration.qml")
                }
            }
            MenuItem {
                text: qsTr("Device Information")
                onTriggered: () => {
                    Helpers.createComponent("DialogDeviceInformation.qml")
                }
            }
            MenuSeparator {}
            MenuItem {
                text: qsTr("Auto Mapper")
                onTriggered: () => {
                    Helpers.createComponent("DialogAutoMapper.qml")
                }
            }
            MenuItem {
                text: qsTr("Swap Devices")
                onTriggered: () => {
                    Helpers.createComponent("DialogSwapDevices.qml")
                }
            }
            MenuItem {
                text: qsTr("Configure input module")
                onTriggered: () => { openConfigureModule("source") }
            }
            MenuItem {
                text: qsTr("Configure output module")
                onTriggered: () => { openConfigureModule("dest") }
            }
            MenuItem {
                text: qsTr("Import devices…")
                onTriggered: () => { Helpers.createComponent("DialogImportDevices.qml") }
            }
            MenuItem {
                text: qsTr("Export devices…")
                onTriggered: () => { openExportDevices() }
            }
            MenuSeparator {}
            MenuItem {
                text: qsTr("HiDHide")
                onTriggered: () => {
                    Helpers.createComponent("DialogHardwareHide.qml")
                }
            }
            MenuItem {
                text: qsTr("Options")
                onTriggered: () => {
                    Helpers.createComponent("DialogOptions.qml")
                }
            }
        }

        Menu {
            title: qsTr("Help")

            MenuItem {
                text: qsTr("User Guide")
                onTriggered: () => {
                    Helpers.createComponent("DialogHelp.qml")
                }
            }
            MenuItem {
                text: qsTr("About")
                onTriggered: () => {
                    Helpers.createComponent("DialogAbout.qml")
                }
            }
        }
    }

    header: ToolBar {
        id: _toolbar

        RowLayout {
            anchors.fill: parent

            JGToolButton {
                text: "\uF425"
                caption: "Home"
                color: (!uiState || uiState.currentRoom === "status") ? Style.accent : Style.foreground
                tooltip: qsTr("Home screen")

                onClicked: () => { closeWorkRoom() }
            }
            JGToolButton {
                text: "\uF448"
                caption: "Toggle"
                color: backend && backend.gremlinActive ? Style.accent : Style.foreground
                tooltip: qsTr("Toggle Active")

                onClicked: () => {
                    if (backend) {
                        backend.toggleActiveState()
                    }
                }
            }

            JGToolButton {
                text: "\uF3F2"
                tooltip: qsTr("Toggle vJoy Viewer")
                caption: "vJoy Viewer"

                onClicked: () => {
                    Helpers.toggleComponent("DialogInputViewer.qml")
                }
            }

            JGToolButton {
                text: "\uF2D4"
                tooltip: qsTr("Toggle Xbox Viewer")
                caption: "Xbox Viewer"

                onClicked: () => {
                    Helpers.toggleComponent("DialogXboxViewer.qml")
                }
            }

            JGToolButton {
                text: "\uF5E7"
                tooltip: qsTr("Open a blank Button Map")
                caption: "Button Map"

                onClicked: () => { openBlankButtonMap() }
            }

            JGToolButton {
                text: "\uF4CA"
                tooltip: qsTr("Toggle Device Viewer")
                caption: "Device"

                onClicked: () => {
                    Helpers.toggleComponent("DialogDeviceViewer.qml")
                }
            }

            JGToolButton {
                text: "\uF3E5"
                tooltip: qsTr("Open options")

                onClicked: () => {
                    Helpers.createComponent("DialogOptions.qml")
                }
            }

            LayoutHorizontalSpacer {}

            Label {
                Layout.rightMargin: 10

                text: uiState && uiState.currentRoom === "configuration" && configDirection !== "dest" ? "Configuring mode" : "Mode"
            }

            TooltipComboBox {
                id: _modeSelector

                Layout.preferredWidth: 200
                Layout.rightMargin: 10

                model: ModeListModel { id: _modeList }
                textRole: "name"
                valueRole: "name"

                background: Rectangle {
                    implicitWidth: 120
                    implicitHeight: 32
                    border.width: 1
                    border.color: _modeSelector.down || _modeSelector.hovered
                            ? _modeSelector.Universal.baseMediumColor
                            : _modeSelector.Universal.baseMediumLowColor
                    color: _modeSelector.down
                            ? _modeSelector.Universal.listMediumColor
                            : _modeSelector.Universal.altMediumLowColor
                }

                delegate: ItemDelegate {
                    required property var model
                    required property int index

                    width: ListView.view ? ListView.view.width : implicitWidth
                    text: model[_modeSelector.textRole]
                    font.weight: _modeSelector.currentIndex === index ? Font.DemiBold : Font.Normal
                    highlighted: false
                    hoverEnabled: true

                    background: Rectangle {
                        color: (_modeSelector.highlightedIndex === index || parent.hovered)
                                ? _modeSelector.Universal.listMediumColor
                                : "transparent"
                    }
                }

                onActivated: () => {
                    if (uiState) {
                        uiState.setCurrentMode(currentText)
                    }
                }

                Connections {
                    target: _modeList
                    function onModelReset() {
                        if (!uiState)
                            return
                        var index = _modeSelector.find(uiState.currentMode)
                        if (index >= 0)
                            _modeSelector.currentIndex = index
                    }
                }

                Component.onCompleted: () => {
                    if (uiState) {
                        currentIndex = find(uiState.currentMode)
                    }
                }

                ToolTip {
                    visible: parent.hovered
                    text: qsTr("Select mode to edit")
                    delay: 500
                }
            }

            Button {
                text: "Manage Modes"
                Layout.rightMargin: 10
                onClicked: () => {
                    Helpers.createComponent("DialogManageModes.qml")
                }
            }
        }
    }

    footer: Rectangle {
        id: _footer

        height: 30
        color: Universal.chromeMediumColor

        RowLayout {
            anchors.fill: parent

            Label {
                Layout.preferredWidth: 200
                padding: 5

                color: backend && backend.gremlinActive ? Style.foreground : "#A1A1AA"
                text: "<B>Status: </B>" +
                    Helpers.selectText(
                        backend && backend.gremlinActive, "Active", "Not Running"
                    ) +
                    Helpers.selectText(
                        backend && backend.gremlinActive && backend.gremlinPaused, " (Paused)", ""
                    )
            }

            Label {
                Layout.fillWidth: true
                padding: 5

                text: "<B>Executing mode: </B>" + (backend ? backend.currentMode : "")
            }
        }
    }

    DeviceListModel {
        id: _deviceListModel

        deviceType: "physical"
    }

    Device {
        id: _deviceModel

        guid: uiState ? uiState.currentDevice : ""
    }

    BootstrapIcons {
        id: bsi
        resource: "qrc:///BootstrapIcons"
    }

    Connections {
        target: uiState

        function onModeChanged() {
            if (!uiState) {
                return
            }
            _deviceModel.setMode(uiState.currentMode)
            _logicalDeviceList.device.setMode(uiState.currentMode)
            _oscDeviceList.device.setMode(uiState.currentMode)
            _modeSelector.currentIndex = _modeSelector.find(uiState.currentMode)
        }
        function onTabChanged() {
            if (!uiState) {
                return
            }
            _scriptButton.checked = uiState.currentTab === "scripts"
            _profileSettingsButton.checked = uiState.currentTab === "settings"
        }
    }
    Connections {
        target: backend

        function onProfileChanged() {
        }

        function onQuitRequested() {
            _root.quitGremlin()
        }
    }
    Connections {
        target: signal

        function onConfigChanged() {
            if (backend) {
                Style.isDarkMode = backend.useDarkMode
            }
        }

        function onShowError(message, details) {
            _errorDialog.text = message
            _errorDialog.detailedText = details
            _errorDialog.open()
        }

        function onShowNotification(title, message) {
            _notificationDialog.title = title
            _notificationDialog.text = message
            _notificationDialog.open()
        }
    }

    onClosing: (close) => {
        _windowPlacement.save(_root)
        if (_outputModuleView && _outputModuleView.hasUnsaved && _outputModuleView.hasUnsaved()) {
            close.accepted = false
            _outputModuleView.requestClose()
            return
        }
        if (_deviceInputList && _deviceInputList.hasUnsaved && _deviceInputList.hasUnsaved()) {
            close.accepted = false
            _deviceInputList.requestClose()
            return
        }
        if (backend && backend.profileContainsUnsavedChanges) {
            _saveBeforeQuitDialog.ask()
            close.accepted = false
            return
        }
        if (buttonMapNeedsLeave()) {
            offerButtonMapLeaveThenQuit()
            close.accepted = false
        }
    }

    ColumnLayout {
        id: _columnLayout

        anchors.fill: parent
        anchors.bottomMargin: 58

        property InputConfiguration inputConfigurationWidget
        property bool onStatus: !uiState || uiState.currentRoom === "status"
        property bool onConfig: uiState && uiState.currentRoom === "configuration"

        Connections {
            target: _moduleModel
            function onClaimsChanged() { refreshDestBound() }
            function onPanesChanged() { _root.refreshSourceModuleCount() }
            function onModelReset() { _root.refreshSourceModuleCount() }
        }

        StatusPage {
            id: _statusPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !uiState || uiState.currentRoom === "status"
            model: _moduleModel
            pinSlug: _root.pinSlug
            onFocusSlug: function(slug) {
                _moduleModel.setFocus(slug)
            }
            onOpenConfiguration: function(card) {
                _statusLastCard = card
                openConfigurationForCard(card)
            }
            onOpenButtonMap: function(card) {
                _statusLastCard = card
                openButtonMapForCard(card)
            }
            onOpenOutputView: function(card) {
                _statusLastCard = card
                openOutputViewForCard(card)
            }
            onConfigureModule: function(card) {
                _statusLastCard = card
                openConfigureModule(card.direction === "dest" ? "dest" : "source")
            }
            onPinControlDisplay: function(card) {
                _statusLastCard = card
                pinSlug = (pinSlug === card.slug) ? "" : card.slug
            }
            onAutoMap: function(card) {
                _statusLastCard = card
                Helpers.createComponent("DialogAutoMapper.qml")
            }
            onOpenDeviceViewer: function(card) {
                _statusLastCard = card
                Helpers.toggleComponent("DialogDeviceViewer.qml")
            }
            onOpenPairing: function(card) {
                _statusLastCard = card
                pairingForCard(card)
            }
            onOpenCalibration: function(card) {
                _statusLastCard = card
                Helpers.createComponent("DialogCalibration.qml", {"initialSlug": card.slug || ""})
            }
            onOpenDeviceInformation: function(card) {
                _statusLastCard = card
                Helpers.createComponent("DialogDeviceInformation.qml")
            }
            onAssignHardware: function(card) {
                _statusLastCard = card
                Helpers.createComponent("DialogSwapDevices.qml")
            }
            onIgnoreDevice: function(card) {
                _moduleModel.ignoreSlug(card.slug)
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: uiState && uiState.currentRoom === "configuration"
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 12
                Layout.topMargin: 16
                Layout.bottomMargin: 14
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label {
                        text: configDirection === "dest" ? "Output Module View" : "Configuration"
                        color: "#A1A1AA"
                        font.pixelSize: 12
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        IconButton {
                            visible: configDirection !== "dest"
                            text: "\uF284"
                            font.pixelSize: 18
                            enabled: _root.sourceModuleCount > 1
                            opacity: enabled ? 1 : 0.35
                            onClicked: _root.cycleConfiguration(-1)
                            ToolTip.visible: hovered
                            ToolTip.text: "Previous input module"
                        }
                        IconButton {
                            visible: configDirection !== "dest"
                            text: "\uF285"
                            font.pixelSize: 18
                            enabled: _root.sourceModuleCount > 1
                            opacity: enabled ? 1 : 0.35
                            onClicked: _root.cycleConfiguration(1)
                            ToolTip.visible: hovered
                            ToolTip.text: "Next input module"
                        }
                        Label {
                            id: _configTitle
                            text: configTitleName.length ? configTitleName : "device"
                            font.pixelSize: 22
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                    Label {
                        id: _destBound
                        visible: configDirection === "dest"
                        text: "Bound to: [Not bound]"
                        color: "#A1A1AA"
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Label {
                        visible: configDirection === "dest"
                        text: "View only — driven by input module mappings."
                        color: "#A1A1AA"
                        font.pixelSize: 12
                    }
                }
                Button {
                    visible: configDirection === "dest"
                    text: outputViewPanel ? "Hide Display Options" : "Edit Display Options"
                    onClicked: {
                        outputViewPanel = !outputViewPanel
                        rememberDisplayPanel()
                    }
                }
                Button {
                    visible: configDirection !== "dest"
                    text: catalogPanel ? "Hide Display Options" : "Edit Display Options"
                    onClicked: {
                        catalogPanel = !catalogPanel
                        rememberDisplayPanel()
                    }
                }
                Button {
                    visible: configDirection !== "dest"
                    text: "Close"
                    onClicked: closeWorkRoom()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#3F3F46"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: uiState && (uiState.currentRoom === "scripts" || uiState.currentRoom === "settings")
            height: visible ? implicitHeight : 0

            Label {
                text: uiState && uiState.currentRoom === "scripts" ? "Scripts" : "Profile Settings"
                font.pixelSize: 16
                font.bold: true
                Layout.leftMargin: 12
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Home"
                Layout.rightMargin: 12
                onClicked: closeWorkRoom()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: uiState && uiState.currentRoom === "configuration" && !configTitleName.length
            height: visible ? implicitHeight : 0

            DeviceList {
                id: _deviceList

                Layout.minimumHeight: 50
                Layout.maximumHeight: 50
                Layout.fillWidth: true

                deviceListModel: _deviceListModel
            }

            ColumnLayout {
                IconButton {
                    text: "\uF285"
                    font.pixelSize: 14

                    onClicked: () => { _deviceList.nextTab() }
                }
                IconButton {
                    text: "\uF284"
                    font.pixelSize: 14

                    onClicked: () => { _deviceList.previousTab() }
                }
            }

            DeviceTabBar {
                scrollbarAlwaysVisible: false

                Component.onCompleted: () => { _scriptButton.checked = false }

                JGTabButton {
                    id: _scriptButton

                    text: "Scripts"
                    width: _metricScripts.width + 50
                    checked: false

                    onClicked: () => {
                        leaveDisplayThen(function() {
                            if (uiState) {
                                uiState.setCurrentRoom("scripts")
                                uiState.setCurrentTab("scripts")
                            }
                        })
                    }

                    TextMetrics {
                        id: _metricScripts

                        font: _scriptButton.font
                        text: _scriptButton.text
                    }
                }

                JGTabButton {
                    id: _profileSettingsButton

                    text: "Settings"
                    width: _metricProfileSettings.width + 50
                    checked: false

                    onClicked: () => {
                        leaveDisplayThen(function() {
                            if (uiState) {
                                uiState.setCurrentRoom("settings")
                                uiState.setCurrentTab("settings")
                            }
                        })
                    }

                    TextMetrics {
                        id: _metricProfileSettings

                        font: _profileSettingsButton.font
                        text: _profileSettingsButton.text
                    }
                }
            }
        }

        OutputModuleView {
            id: _outputModuleView

            Layout.fillHeight: true
            Layout.fillWidth: true
            visible: uiState && uiState.currentRoom === "configuration"
                     && _root.configDirection === "dest"
                     && uiState.currentTab !== "xbox"
            guid: uiState ? uiState.currentDevice : ""
            deviceName: configTitleName
            moduleModel: _moduleModel
            showPanel: _root.outputViewPanel
            onClosePanel: {
                _root.outputViewPanel = false
                _root.rememberDisplayPanel()
            }
            onLeaveResolved: _root.continueDisplayLeave()
            onLeaveCancelled: _root.cancelDisplayLeave()
        }

        SplitView {
            id: _splitView

            Layout.fillHeight: true
            Layout.fillWidth: true
            visible: uiState && uiState.currentRoom === "configuration"
                     && !(_root.configDirection === "dest" && uiState.currentTab !== "xbox")

            clip: true
            orientation: (uiState && uiState.currentTab === "physical") ? Qt.Vertical : Qt.Horizontal

            BindingCatalog {
                id: _deviceInputList

                visible: uiState && uiState.currentTab === "physical"
                SplitView.minimumWidth: 400
                SplitView.fillWidth: true
                SplitView.fillHeight: true

                device: _deviceModel
                moduleModel: _moduleModel
                claimDeviceName: configTitleName
                isOutput: _root.configDirection === "dest"
                showPanel: _root.configDirection === "dest" ? _root.outputViewPanel : _root.catalogPanel
                onClosePanel: {
                    if (_root.configDirection === "dest")
                        _root.outputViewPanel = false
                    else
                        _root.catalogPanel = false
                    _root.rememberDisplayPanel()
                }
                onLeaveResolved: _root.continueDisplayLeave()
                onLeaveCancelled: _root.cancelDisplayLeave()
            }

            LogicalDevice {
                id: _logicalDeviceList

                visible: uiState && uiState.currentTab === "logical"
                SplitView.minimumWidth: 400

                onInputIdentifierChanged: () => {
                    if (uiState) {
                        uiState.setCurrentInput(inputIdentifier, inputIndex)
                    }
                }
            }

            OscDevice {
                id: _oscDeviceList

                visible: uiState && uiState.currentTab === "osc"
                SplitView.minimumWidth: 400

                onInputIdentifierChanged: () => {
                    if (uiState) {
                        uiState.setCurrentInput(inputIdentifier, inputIndex)
                    }
                }
            }

            XboxDevice {
                id: _xboxDeviceList

                visible: uiState && uiState.currentTab === "xbox"
                SplitView.minimumWidth: 400
                SplitView.fillWidth: true
            }

            KeyboardInputList {
                id: _keyboardInputList

                visible: uiState && uiState.currentTab === "keyboard"
                SplitView.minimumWidth: 400
            }

            InputConfiguration {
                id: _inputConfigurationPanel
                isOutput: _root.configDirection === "dest"

                visible: uiState && !["scripts", "settings", "xbox", "physical"].includes(uiState.currentTab)

                Component.onCompleted: () => {
                    if (backend && uiState) {
                        inputItemModel = backend.getInputItem(
                            uiState.currentInput,
                            uiState.currentInputIndex
                        )
                    }
                }

                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: 900
            }
        }

        ScriptManager {
            id: _scriptManager

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.verticalStretchFactor: 10

            visible: uiState && uiState.currentRoom === "scripts"

            scriptListModel: backend ? backend.scriptListModel : null
        }

        ProfileSettings {
            id: _profileSettings

            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.verticalStretchFactor: 10

            visible: uiState && uiState.currentRoom === "settings"

            settingsModel: ProfileSettingsModel {}
        }
    }


    DebugFileLine {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }
}
