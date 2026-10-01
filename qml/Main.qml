// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
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
    font.pixelSize: Style.fontSize

    title: backend ? backend.windowTitle : "Gremlin-Platforms R1"
    // Never narrower than the toolbar row, so Manage Modes stays in the window.
    minimumWidth: Math.max(Style.dp(1300), Math.ceil(_toolbarRow.implicitWidth + _toolbarRow.anchors.leftMargin))
    minimumHeight: Style.dp(700)
    // WindowPlacement sets the saved or default size at startup.
    width: 1400
    height: 900
    visible: true
    id: _root

    property string lastSaveText: ""

    WindowPlacement { id: _windowPlacement }

    Component.onCompleted: () => {
        if (backend) {
            Style.isDarkMode = backend.useDarkMode
        }
        _windowPlacement.restore(_root)
        refreshSourceModuleCount()
    }

    U.Universal.theme: Style.theme
    color: Style.background

    property string configTitleName: ""
    onConfigTitleNameChanged: {
        syncOutputView()
        syncCatalogView()
    }
    property string configDirection: ""
    property int sourceModuleCount: 0
    property int destModuleCount: 0
    property bool outputViewPanel: true
    property bool catalogPanel: true
    property bool parkEmptyInUnmapped: false
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

    function openLogicalDeviceNow() {
        if (!uiState)
            return
        _panelReady = false
        configTitleName = "Logical Device"
        configDirection = "logical"
        uiState.setCurrentDevice("f0af472f-8e17-493b-a1eb-7333ee8543f2")
        uiState.setCurrentTab("logical")
        uiState.setCurrentRoom("configuration")
    }

    function openLogicalDevice() {
        if (uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "logical")
            return
        // Home has no unsaved device pane. Do not wait on hidden leave dialogs.
        if (!uiState || uiState.currentRoom !== "configuration") {
            openLogicalDeviceNow()
            return
        }
        leaveDisplayThen(function() { openLogicalDeviceNow() })
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

    function catalogPane() {
        return _configSplitLoader.item ? _configSplitLoader.item.catalog : null
    }

    function outputPane() {
        return _outputLoader.item
    }

    function syncOutputView() {
        var view = _outputLoader.item
        if (!view)
            return
        view.guid = uiState ? uiState.currentDevice : ""
        view.deviceName = configTitleName
    }

    function syncCatalogView() {
        var split = _configSplitLoader.item
        if (!split || !split.catalog)
            return
        if (configDirection === "logical" || (uiState && uiState.currentTab === "logical"))
            return
        split.catalog.claimDeviceName = configTitleName
    }

    function revealCatalogRow(row) {
        Qt.callLater(function() {
            var split = _configSplitLoader.item
            if (!split || !split.catalog)
                return
            split.catalog.revealRowNow(row)
        })
    }

    function deferListScroll(list, row) {
        Qt.callLater(function() {
            if (!_configSplitLoader.item || !list)
                return
            list.scrollRowNow(row)
        })
    }

    function logicalPane() {
        return _logicalLoader.item
    }

    function continueDisplayLeave() {
        var catalog = catalogPane()
        if (catalog && catalog.hasUnsaved && catalog.hasUnsaved()) {
            catalog.requestLeave()
            return
        }
        var output = outputPane()
        if (output && output.hasUnsaved && output.hasUnsaved()) {
            output.requestLeave()
            return
        }
        var logical = logicalPane()
        if (logical && logical.hasUnsaved && logical.hasUnsaved()) {
            logical.requestLeave()
            return
        }
        var next = _afterDisplayLeave
        _afterDisplayLeave = null
        if (next)
            next()
    }

    function cancelDisplayLeave() {
        _afterDisplayLeave = null
        if (_quitPending) {
            _quitPending = false
            if (backend)
                backend.setRestartOnExit(false)
        }
    }

    // Unsaved display options or an edited Logical action pane.
    function displayUnsaved() {
        var panes = [catalogPane(), outputPane(), logicalPane()]
        for (var i = 0; i < panes.length; ++i) {
            var pane = panes[i]
            if (pane && pane.hasUnsaved && pane.hasUnsaved())
                return true
        }
        return false
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
        slugs = _moduleModel ? _moduleModel.pileLeaders("dest") : []
        destModuleCount = slugs ? slugs.length : 0
    }

    function moduleIndex(slugs, focus) {
        var index = 0
        for (var i = 0; i < slugs.length; ++i) {
            if (String(slugs[i]) === focus)
                return i
            var members = _moduleModel.pileMembers(slugs[i]) || []
            for (var m = 0; m < members.length; ++m) {
                if (String(members[m]) === focus)
                    return i
            }
        }
        return index
    }

    function cycleModules(direction, step) {
        if (configDirection !== direction || !_moduleModel)
            return
        var slugs = _moduleModel.pileLeaders(direction) || []
        if (slugs.length < 2)
            return
        var index = moduleIndex(slugs, String(_moduleModel.focusedSlug || ""))
        var card = _moduleModel.cardMap(slugs[(index + step + slugs.length) % slugs.length])
        if (card && card.slug)
            openConfigurationForCard(card)
    }

    function cycleConfiguration(step) {
        cycleModules("source", step)
    }

    function cycleOutput(step) {
        cycleModules("dest", step)
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

    function closeDeletedDevice(card) {
        var name = card ? String(card.rawName || card.name || "").trim() : ""
        var guid = card ? String(card.guid || "") : ""
        if (name && (configTitleName === name || (uiState && String(uiState.currentDevice || "") === guid)))
            closeWorkRoomNow()
        var map = buttonMapWindow()
        if (map && (String(map.targetName || "") === name || String(map.targetGuid || "") === guid))
            map.close()
        if (configureWin && (String(configureWin.deviceName || "") === name || String(configureWin.deviceGuid || "") === guid))
            configureWin.close()
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

    // restart: start Gremlin again once it has shut down. Any other quit clears it.
    function quitGremlin(restart) {
        if (backend)
            backend.setRestartOnExit(!!restart)
        // Panels and the Logical pane first, then the profile, then quit.
        _quitPending = true
        leaveDisplayThen(function() {
            _quitPending = false
            guardUnsavedChanges(deactivateThenQuit, true)
        })
    }

    property bool _quitPending: false

    // Runs action once unsaved profile changes are saved or discarded (same as R16's
    // guardUnsavedChanges). Cancel drops the action. quitting: a cancel also clears
    // the restart request.
    function guardUnsavedChanges(action, quitting) {
        if (backend && backend.profileContainsUnsavedChanges) {
            _saveBeforeContinueDialog.pendingAction = action
            _saveBeforeContinueDialog.quitting = !!quitting
            _saveBeforeContinueDialog.detail = quitting
                ? "There are unsaved changes in the current profile. Save them before quitting, or they will be lost."
                : "There are unsaved changes in the current profile. Save them before continuing, or they will be lost."
            _saveBeforeContinueDialog.ask()
        } else {
            action()
        }
    }

    function showSaveResult(ok, path) {
        var where = path ? String(path) : ""
        if (ok) {
            _saveResultDialog.announce(true, "Saved to the profile.")
            if (backend)
                backend.noteSave(where.length ? ("Saved the profile to " + where) : "Saved the profile.")
        } else {
            _saveResultDialog.announce(false, "Not written. It is still only on this screen.")
            if (backend)
                backend.noteSave("The profile was not written.")
        }
    }

    ColorInformation {
        id: colorInformation
    }

    ErrorDialog {
        id: _errorDialog

        title: "A fatal error occurred"
    }

    MessageDialog {
        id: _notificationDialog

        modality: Qt.ApplicationModal
        buttons: MessageDialog.Ok
    }

    DismissibleDialog {
        id: _saveBeforeContinueDialog

        property var pendingAction: null
        property bool quitting: false

        function takeAction() {
            var action = pendingAction
            pendingAction = null
            return action
        }

        onSaveChosen: {
            var action = takeAction()
            if (!backend || !action)
                return
            var fpath = backend.profilePath()
            if (fpath === "") {
                _saveProfileFileDialog.afterSave = action
                _saveProfileFileDialog.open()
            } else if (backend.saveProfile(fpath)) {
                action()
            } else {
                showSaveResult(false, fpath)
            }
        }
        onDiscardChosen: {
            var action = takeAction()
            if (action)
                action()
        }
        onCancelled: {
            takeAction()
            if (quitting && backend)
                backend.setRestartOnExit(false)
        }
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

        // Set by guardUnsavedChanges: runs after a successful save.
        property var afterSave: null

        acceptLabel: "Save"
        defaultSuffix: "xml"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Profile files (*.xml)"]
        currentFolder: backend.profilesFolderUrl()

        onAccepted: () => {
            if (!backend) {
                return
            }
            var ok = backend.saveProfile(currentFile)
            var next = afterSave
            afterSave = null
            if (next) {
                if (ok) {
                    next()
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
        currentFolder: backend.profilesFolderUrl()

        onAccepted: () => {
            var file = currentFile
            if (backend)
                guardUnsavedChanges(function() { backend.loadProfile(file) })
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
                        PointerTip {
                            text: modelData
                            delay: 400
                            show: true
                        }
                        onTriggered: () => {
                            var file = modelData
                            if (backend)
                                guardUnsavedChanges(function() { backend.loadProfile(file) })
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

            Menu {
                title: qsTr("Viewers")

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
            }
            Menu {
                title: qsTr("Device setup")

                MenuItem {
                    text: qsTr("Calibration")
                    onTriggered: () => {
                        Helpers.createComponent("DialogCalibration.qml")
                    }
                }
                MenuItem {
                    text: qsTr("HiDHide")
                    onTriggered: () => {
                        Helpers.createComponent("DialogHardwareHide.qml")
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
                    text: qsTr("Device Information")
                    onTriggered: () => {
                        Helpers.createComponent("DialogDeviceInformation.qml")
                    }
                }
                MenuItem {
                    text: qsTr("Swap Devices")
                    onTriggered: () => {
                        Helpers.createComponent("DialogSwapDevices.qml")
                    }
                }
                MenuItem {
                    text: qsTr("Device Pack")
                    onTriggered: () => { Helpers.createComponent("DialogDevicePack.qml") }
                }
            }
            Menu {
                title: qsTr("Mapping")

                MenuItem {
                    text: qsTr("Logical Device")
                    onTriggered: () => { openLogicalDevice() }
                }
                MenuItem {
                    text: qsTr("Button Map")
                    onTriggered: () => { openBlankButtonMap() }
                }
                MenuItem {
                    text: qsTr("Auto Mapper")
                    onTriggered: () => {
                        Helpers.createComponent("DialogAutoMapper.qml")
                    }
                }
                MenuItem {
                    text: qsTr("Manage Modes")
                    onTriggered: () => {
                        Helpers.createComponent("DialogManageModes.qml")
                    }
                }
            }
            MenuSeparator {}
            MenuItem {
                text: qsTr("Options")
                onTriggered: () => {
                    Helpers.createComponent("DialogOptions.qml")
                }
            }
        }

        Menu {
            title: qsTr("Debug")

            MenuItem {
                text: qsTr("Live Log Reader")
                onTriggered: () => {
                    Helpers.createComponent("DialogLiveLog.qml")
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
            id: _toolbarRow
            anchors.fill: parent
            anchors.leftMargin: _homeButton.rightPadding + spacing + _toggleButton.sideSlack
            spacing: Style.dp(8)

            JGToolButton {
                id: _homeButton
                text: "\uF425"
                caption: "Home"
                color: (!uiState || uiState.currentRoom === "status") ? Style.accent : Style.foreground
                tooltip: qsTr("Home screen")

                onClicked: () => { closeWorkRoom() }
            }
            JGToolButton {
                id: _toggleButton
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
                text: "\uF2D6"
                caption: "Logical Device"
                color: (uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "logical") ? Style.accent : Style.foreground
                tooltip: qsTr("Open the Logical Device configuration")

                onClicked: () => { openLogicalDevice() }
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
                Layout.rightMargin: Style.dp(10)

                text: "Configuring mode"
            }

            TooltipComboBox {
                id: _modeSelector

                Layout.preferredWidth: Style.dp(200)
                Layout.rightMargin: Style.dp(10)

                model: ModeListModel { id: _modeList }
                textRole: "name"
                valueRole: "name"

                background: Rectangle {
                    implicitWidth: Style.dp(120)
                    implicitHeight: Style.dp(32)
                    border.width: Style.dp(1)
                    border.color: _modeSelector.down || _modeSelector.hovered
                            ? _modeSelector.U.Universal.baseMediumColor
                            : _modeSelector.U.Universal.baseMediumLowColor
                    color: _modeSelector.down
                            ? _modeSelector.U.Universal.listMediumColor
                            : _modeSelector.U.Universal.altMediumLowColor
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
                                ? _modeSelector.U.Universal.listMediumColor
                                : "transparent"
                    }
                }

                onActivated: () => {
                    if (backend)
                        backend.selectMode(currentText)
                    else if (uiState)
                        uiState.setCurrentMode(currentText)
                }

                Connections {
                    target: _modeList
                    function onModelReset() {
                        // After the ComboBox's own reset, or it clears this again and the
                        // box shows blank (New Profile, Load, Save As).
                        Qt.callLater(function() {
                            if (!uiState)
                                return
                            var index = _modeSelector.find(uiState.currentMode)
                            _modeSelector.currentIndex = index >= 0 ? index : (_modeSelector.count > 0 ? 0 : -1)
                        })
                    }
                }

                Component.onCompleted: () => {
                    if (uiState) {
                        currentIndex = find(uiState.currentMode)
                    }
                }

                PointerTip {
                    text: qsTr("Mode. This is the map you are editing and the map that runs.")
                    delay: 500
                }
            }

            Button {
                text: "Manage Modes"
                Layout.rightMargin: Style.dp(10)
                onClicked: () => {
                    Helpers.createComponent("DialogManageModes.qml")
                }
            }
        }
    }

    footer: Rectangle {
        id: _footer

        height: Style.dp(30)
        color: U.Universal.chromeMediumColor

        RowLayout {
            anchors.fill: parent

            Label {
                Layout.preferredWidth: Style.dp(200)
                padding: Style.dp(5)

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
                Layout.preferredWidth: Style.dp(220)
                padding: Style.dp(5)

                text: "<B>Executing mode: </B>" + (backend ? backend.currentMode : "")
            }

            Label {
                id: _savedLine
                Layout.fillWidth: true
                padding: Style.dp(5)
                color: "#E4E4E7"
                elide: Text.ElideMiddle
                text: _root.lastSaveText
                HoverHandler {
                    id: _savedHover
                }
                PointerTip {
                    text: text
                    delay: 400
                    show: text.length > 0
                }
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

        function onDeviceChanged() {
            syncOutputView()
        }
        function onModeChanged() {
            if (!uiState) {
                return
            }
            _deviceModel.setMode(uiState.currentMode)
            var logi = logicalPane()
            if (logi)
                logi.setMode(uiState.currentMode)
            var split = _configSplitLoader.item
            if (split && split.oscList && split.oscList.device)
                split.oscList.device.setMode(uiState.currentMode)
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

        function onRestartRequested() {
            _root.quitGremlin(true)
        }

        function onSaveNoted(text) {
            _root.lastSaveText = text
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
        if (backend)
            backend.setRestartOnExit(false)
        _windowPlacement.save(_root)
        // Same order as File > Exit: panels, then the profile, then quit.
        if (displayUnsaved() || (backend && backend.profileContainsUnsavedChanges)) {
            close.accepted = false
            quitGremlin(false)
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
            onDeviceDeleted: function(card) {
                closeDeletedDevice(card)
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: uiState && uiState.currentRoom === "configuration"
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(16)
                Layout.rightMargin: Style.dp(12)
                Layout.topMargin: Style.dp(16)
                Layout.bottomMargin: Style.dp(14)
                spacing: Style.dp(12)

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Style.dp(2)
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.dp(8)
                        Label {
                            visible: configDirection === "dest"
                            text: "Output Module View"
                            font.pixelSize: Style.dp(22)
                            font.bold: true
                        }
                        Label {
                            visible: configDirection !== "dest" && configDirection !== "logical"
                            text: "Input Configuration"
                            font.pixelSize: Style.dp(22)
                            font.bold: true
                        }
                        Label {
                            visible: configDirection === "logical"
                            text: "Logical Device"
                            font.pixelSize: Style.dp(22)
                            font.bold: true
                        }
                        IconButton {
                            text: "\uF284"
                            font.pixelSize: Style.dp(18)
                            visible: configDirection === "source" || configDirection === "dest"
                            enabled: (configDirection === "dest" ? _root.destModuleCount : _root.sourceModuleCount) > 1
                            opacity: enabled ? 1 : 0.35
                            onClicked: configDirection === "dest" ? _root.cycleOutput(-1) : _root.cycleConfiguration(-1)
                            PointerTip {
                                text: configDirection === "dest" ? "Previous output module" : "Previous input module"
                                delay: 400
                                show: true
                            }
                        }
                        IconButton {
                            text: "\uF285"
                            font.pixelSize: Style.dp(18)
                            visible: configDirection === "source" || configDirection === "dest"
                            enabled: (configDirection === "dest" ? _root.destModuleCount : _root.sourceModuleCount) > 1
                            opacity: enabled ? 1 : 0.35
                            onClicked: configDirection === "dest" ? _root.cycleOutput(1) : _root.cycleConfiguration(1)
                            PointerTip {
                                text: configDirection === "dest" ? "Next output module" : "Next input module"
                                delay: 400
                                show: true
                            }
                        }
                        Label {
                            id: _configTitle
                            visible: configDirection !== "logical"
                            text: configTitleName.length ? configTitleName : "device"
                            font.pixelSize: Style.dp(22)
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
                        font.pixelSize: Style.dp(12)
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Label {
                        visible: configDirection === "dest"
                        text: "View only — driven by input module mappings."
                        color: "#A1A1AA"
                        font.pixelSize: Style.dp(12)
                    }
                }
                Button {
                    visible: configDirection === "dest"
                    text: outputViewPanel ? "Hide Editor" : "Show Editor"
                    onClicked: {
                        outputViewPanel = !outputViewPanel
                        rememberDisplayPanel()
                    }
                }
                CheckBox {
                    visible: configDirection !== "dest" && configDirection !== "logical"
                    text: "Move empty to Unmapped"
                    checked: _root.parkEmptyInUnmapped
                    onToggled: {
                        _root.parkEmptyInUnmapped = checked
                        var catalog = catalogPane()
                        if (catalog)
                            catalog.parkEmptyInUnmapped = checked
                    }
                    PointerTip {
                        text: "When checked, a control with no actions is listed under Unmapped."
                        delay: 400
                        show: true
                    }
                }
                Button {
                    visible: configDirection !== "dest" && configDirection !== "logical"
                    text: catalogPanel ? "Hide Editor" : "Show Editor"
                    onClicked: {
                        catalogPanel = !catalogPanel
                        rememberDisplayPanel()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Style.dp(1)
                color: "#3F3F46"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: uiState && (uiState.currentRoom === "scripts" || uiState.currentRoom === "settings")
            height: visible ? implicitHeight : 0

            Label {
                text: uiState && uiState.currentRoom === "scripts" ? "Scripts" : "Profile Settings"
                font.pixelSize: Style.dp(16)
                font.bold: true
                Layout.leftMargin: Style.dp(12)
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Home"
                Layout.rightMargin: Style.dp(12)
                onClicked: closeWorkRoom()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: uiState && uiState.currentRoom === "configuration" && !configTitleName.length
            height: visible ? implicitHeight : 0

            DeviceList {
                id: _deviceList

                Layout.minimumHeight: Style.dp(50)
                Layout.maximumHeight: Style.dp(50)
                Layout.fillWidth: true

                deviceListModel: _deviceListModel
            }

            ColumnLayout {
                IconButton {
                    text: "\uF285"
                    font.pixelSize: Style.dp(14)

                    onClicked: () => { _deviceList.nextTab() }
                }
                IconButton {
                    text: "\uF284"
                    font.pixelSize: Style.dp(14)

                    onClicked: () => { _deviceList.previousTab() }
                }
            }

            DeviceTabBar {
                scrollbarAlwaysVisible: false

                Component.onCompleted: () => { _scriptButton.checked = false }

                JGTabButton {
                    id: _scriptButton

                    text: "Scripts"
                    width: _metricScripts.width + Style.dp(50)
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
                    width: _metricProfileSettings.width + Style.dp(50)
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

        Loader {
            id: _outputLoader

            Layout.fillHeight: true
            Layout.fillWidth: true
            active: uiState && uiState.currentRoom === "configuration"
                    && _root.configDirection === "dest"
                    && uiState.currentTab !== "xbox"
            visible: active
            onLoaded: _root.syncOutputView()
            sourceComponent: OutputModuleView {
                moduleModel: _moduleModel
                showPanel: _root.outputViewPanel
                onClosePanel: {
                    _root.outputViewPanel = false
                    _root.rememberDisplayPanel()
                }
                onLeaveResolved: _root.continueDisplayLeave()
                onLeaveCancelled: _root.cancelDisplayLeave()
            }
        }

        Loader {
            id: _logicalLoader

            Layout.fillHeight: true
            Layout.fillWidth: true
            active: uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "logical"
            visible: active
            source: "LogicalPage.qml"
            onLoaded: {
                if (uiState)
                    item.setMode(uiState.currentMode)
            }

            Connections {
                target: _logicalLoader.item
                ignoreUnknownSignals: true
                function onLeaveResolved() { _root.continueDisplayLeave() }
                function onLeaveCancelled() { _root.cancelDisplayLeave() }
            }
        }

        Loader {
            id: _configSplitLoader

            Layout.fillHeight: true
            Layout.fillWidth: true
            active: uiState && uiState.currentRoom === "configuration"
                    && uiState.currentTab !== "logical"
                    && !(_root.configDirection === "dest" && uiState.currentTab !== "xbox")
            visible: active
            sourceComponent: _configSplitComp
            onLoaded: _root.syncCatalogView()
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


    Component {
        id: _configSplitComp

        SplitView {
            id: _splitView

            property alias catalog: _deviceInputList
            property alias oscList: _oscDeviceList

            clip: true
            orientation: (uiState && uiState.currentTab === "physical") ? Qt.Vertical : Qt.Horizontal

            BindingCatalog {
                id: _deviceInputList

                visible: uiState && uiState.currentTab === "physical"
                SplitView.minimumWidth: Style.dp(400)
                SplitView.fillWidth: true
                SplitView.fillHeight: true

                device: _deviceModel
                moduleModel: _moduleModel
                isOutput: _root.configDirection === "dest"
                showPanel: _root.configDirection === "dest" ? _root.outputViewPanel : _root.catalogPanel
                onParkEmptyInUnmappedChanged: _root.parkEmptyInUnmapped = parkEmptyInUnmapped
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
                SplitView.minimumWidth: Style.dp(360)
                SplitView.preferredWidth: Style.dp(420)
                SplitView.fillHeight: true

                onInputIdentifierChanged: () => {
                    if (uiState) {
                        uiState.setCurrentInput(inputIdentifier, inputIndex)
                    }
                }
            }

            OscDevice {
                id: _oscDeviceList

                visible: uiState && uiState.currentTab === "osc"
                SplitView.minimumWidth: Style.dp(400)

                onInputIdentifierChanged: () => {
                    if (uiState) {
                        uiState.setCurrentInput(inputIdentifier, inputIndex)
                    }
                }
            }

            XboxDevice {
                id: _xboxDeviceList

                visible: uiState && uiState.currentTab === "xbox"
                SplitView.minimumWidth: Style.dp(400)
                SplitView.fillWidth: true
            }

            KeyboardInputList {
                id: _keyboardInputList

                visible: uiState && uiState.currentTab === "keyboard"
                SplitView.minimumWidth: Style.dp(400)
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
                SplitView.minimumWidth: Style.dp(900)
            }
        }
    }
}
