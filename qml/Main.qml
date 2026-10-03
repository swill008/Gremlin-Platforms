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

import Gremlin.Menus

import "helpers.js" as Helpers
import "main_commands.js" as MainCommands

ApplicationWindow {
    font.pixelSize: Style.fontSize

    // "* name - Gremlin-Platforms R1"; the * means unsaved changes.
    title: (profileDirty ? "* " : "") + (backend ? backend.windowTitle : "Untitled") + " - Gremlin-Platforms R1"

    // Unsaved changes, checked while the window is in front (edits only
    // happen then) and right after a load or save.
    property bool profileDirty: false
    function refreshProfileDirty() {
        profileDirty = !!(backend && backend.profileContainsUnsavedChanges)
    }
    Timer {
        interval: 1500
        repeat: true
        running: Qt.application.state === Qt.ApplicationActive
        onTriggered: refreshProfileDirty()
    }
    Connections {
        target: backend
        function onWindowTitleChanged() { Qt.callLater(refreshProfileDirty) }
        function onProfileChanged() { Qt.callLater(refreshProfileDirty) }
    }
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

    // The commands that have a shortcut (main_commands.js).
    property var shortcutCommands: []

    // Hidden to the tray (gremlin/ui/tray_memory.py): the pages are
    // unloaded to give their memory back. Configuration stays while it holds
    // unsaved display or Logical Device edits.
    property bool trayed: false
    property bool _keepConfigInTray: false
    readonly property bool _configLive: !trayed || _keepConfigInTray

    function enterTray() {
        _keepConfigInTray = displayUnsaved()
        trayed = true
    }

    function leaveTray() {
        trayed = false
        _keepConfigInTray = false
    }

    Component.onCompleted: () => {
        if (backend) {
            Style.isDarkMode = backend.useDarkMode
        }
        Commands.defineAll(MainCommands.commandList(), "main")
        shortcutCommands = Commands.withShortcuts()
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
        var quitText = _quitPending ? "Appearance changes are not saved. Quit and they will be lost." : ""
        var catalog = catalogPane()
        if (catalog)
            catalog.leaveMessage = quitText
        var output = outputPane()
        if (output)
            output.leaveMessage = quitText
        if (catalog && catalog.needsLeave && catalog.needsLeave()) {
            catalog.requestLeave()
            return
        }
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
            if (updater)
                updater.setInstallOnExit(false)
        }
    }

    // Unsaved display options or an edited Logical action pane.
    function displayUnsaved() {
        var catalog = catalogPane()
        if (catalog && catalog.needsLeave && catalog.needsLeave())
            return true
        var panes = [outputPane(), logicalPane()]
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

    // Menu commands act on the selected card (the Home page's focus).
    function openConfigurationForFocus() {
        var card = _moduleModel.focusedCardMap()
        if (card && card.slug)
            openConfigurationForCard(card)
        else if (uiState)
            uiState.setCurrentRoom("configuration")
    }

    // card: the card a card command came from; menu commands leave it out
    // and get the selected card.
    function openConfigureModule(direction, card) {
        if (!card || !card.slug)
            card = _moduleModel.focusedCardMap()
        var want = direction
        if (!want && card && card.direction === "dest")
            want = "dest"
        if (!want)
            want = "source"
        var name = card ? moduleFileName(card) : ""
        var guid = card ? (card.guid || "") : ""
        if (configureWin) {
            var old = configureWin
            if (old.deviceName === name && old.deviceGuid === guid && old.direction === want) {
                old.raise()
                old.requestActivate()
                return
            }
            // Another device: the open window's controls and photo belong to
            // its own device, so close it (it asks about unsaved changes
            // first) and open a fresh one. If it stays open, the user is
            // answering that question; leave it in front.
            old.close()
            if (old.visible) {
                old.raise()
                old.requestActivate()
                return
            }
            configureWin = null
        }
        var comp = Qt.createComponent("DialogConfigureModule.qml")
        if (comp.status !== Component.Ready) {
            console.log(comp.errorString())
            return
        }
        var win = comp.createObject(_root, {
            "direction": want,
            "deviceName": name,
            "deviceGuid": guid,
            "moduleModel": _moduleModel
        })
        if (!win)
            return
        configureWin = win
        // Runs after the window's own onClosing: a close it held open (to
        // ask about unsaved changes) keeps it.
        win.closing.connect(function(close) {
            if (close && !close.accepted)
                return
            Qt.callLater(function() {
                if (_root.configureWin === win)
                    _root.configureWin = null
                win.destroy()
            })
        })
        win.show()
        win.raise()
        win.requestActivate()
    }

    // Opens (or brings forward) the card's viewer; it never closes one that
    // is already open (the toolbar's Toggle buttons do that).
    function pairingForCard(card) {
        if (!card)
            return
        if (card.bus === "XInput" || card.tab === "xbox" || card.slug === "xbox")
            Helpers.createComponent("DialogXboxViewer.qml")
        else
            Helpers.createComponent("DialogInputViewer.qml")
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

    // Same as opening a profile: asks only when there is something to lose,
    // and offers Save.
    function requestNewProfile() {
        guardUnsavedChanges(function() {
            leaveDisplayThen(function() { backend.newProfile() })
        }, false)
    }

    function saveCurrentProfile() {
        if (!backend) {
            return
        }
        var fpath = backend.profilePath()
        if (fpath === "") {
            openSaveAs()
        } else {
            saveProfileChecked(fpath, function(ok) { showSaveResult(ok, fpath) })
        }
    }

    // File > Save As: never carries a follow-up left from an earlier quit.
    function openSaveAs() {
        _saveProfileFileDialog.afterSave = null
        _saveProfileFileDialog.afterSaveQuitting = false
        _saveProfileFileDialog.open()
    }

    // Saves the profile to path, asking first when the save would leave
    // out unfinished actions (an action with an error is not written).
    // then(ok) runs after the save; onCancel when the user goes back to
    // finish them instead.
    function saveProfileChecked(path, then, onCancel) {
        var doSave = function() { then(backend.saveProfile(path)) }
        var unfinished = backend.unfinishedActions()
        if (!unfinished.length) {
            doSave()
            return
        }
        _unfinishedGate.confirmThen("Unfinished Actions", unfinishedMessage(unfinished),
                                    "Save without them", doSave, onCancel || null, true)
    }

    function unfinishedMessage(list) {
        var shown = list.slice(0, 6).map(function(t) { return "• " + t }).join("\n")
        var more = list.length > 6 ? "\n…and " + (list.length - 6) + " more." : ""
        var head = list.length === 1 ? "1 action is not finished. It" : list.length + " actions are not finished. They"
        return head + " will be left out of the saved profile:\n\n" + shown + more
            + "\n\nCancel to go back and finish them."
    }

    // A quit (or restart, or update install) that waited on a save is
    // called off.
    function cancelQuitRequest() {
        if (backend)
            backend.setRestartOnExit(false)
        if (updater)
            updater.setInstallOnExit(false)
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

    // For the command list (main_commands.js), which keeps no window list of
    // its own (helpers.js keeps one list for the whole program).
    function openTool(spec) {
        Helpers.createComponent(spec)
    }

    function toggleTool(spec) {
        Helpers.toggleComponent(spec)
    }

    function loadRecent(file) {
        if (backend)
            leaveDisplayThen(function() {
                guardUnsavedChanges(function() { backend.loadProfile(file) })
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

    // A tool window with unsaved work (Configure module, Calibration), or
    // null. Quitting would close it without its own Save question.
    function toolWindowWithUnsavedWork() {
        var wins = [configureWin, Helpers.windowOf("DialogCalibration.qml")]
        for (var i = 0; i < wins.length; i++) {
            var w = wins[i]
            if (w && w.visible && typeof w.hasUnsavedWork === "function" && w.hasUnsavedWork())
                return w
        }
        return null
    }

    // Brings that window forward and lets it ask about its unsaved work;
    // the quit stops there. True when there was one.
    function stopQuitForToolWindow() {
        var w = toolWindowWithUnsavedWork()
        if (!w)
            return false
        cancelQuitRequest()
        w.show()
        w.raise()
        w.requestActivate()
        w.close()
        return true
    }

    // restart: start Gremlin again once it has shut down. update: run the
    // downloaded installer once it has shut down. Any other quit clears both.
    function quitGremlin(restart, update) {
        if (stopQuitForToolWindow())
            return
        if (backend)
            backend.setRestartOnExit(!!restart)
        if (updater)
            updater.setInstallOnExit(!!update)
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

        // Most errors are not fatal (an OSC port in use, a file that won't
        // load); the message says what happened.
        title: "Error"
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
            var wasQuitting = quitting
            if (fpath === "") {
                _saveProfileFileDialog.afterSave = action
                _saveProfileFileDialog.afterSaveQuitting = wasQuitting
                _saveProfileFileDialog.open()
            } else {
                saveProfileChecked(fpath, function(ok) {
                    if (ok) {
                        action()
                    } else {
                        showSaveResult(false, fpath)
                        if (wasQuitting)
                            cancelQuitRequest()
                    }
                }, function() {
                    if (wasQuitting)
                        cancelQuitRequest()
                })
            }
        }
        onDiscardChosen: {
            var action = takeAction()
            if (action)
                action()
        }
        onCancelled: {
            takeAction()
            if (quitting)
                cancelQuitRequest()
        }
    }

    // Asks before a save leaves out unfinished actions (saveProfileChecked).
    DismissibleDialog {
        id: _unfinishedGate
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
        title: "Save Profile As"

        // Set by guardUnsavedChanges: runs after a successful save.
        property var afterSave: null
        // That follow-up is a quit: cancelling calls it off.
        property bool afterSaveQuitting: false

        acceptLabel: "Save"
        defaultSuffix: "xml"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Profile files (*.xml)"]
        currentFolder: backend.profilesFolderUrl()

        onAccepted: () => {
            if (!backend) {
                return
            }
            var next = afterSave
            var wasQuitting = afterSaveQuitting
            afterSave = null
            afterSaveQuitting = false
            saveProfileChecked(currentFile, function(ok) {
                if (next) {
                    if (ok) {
                        next()
                    } else {
                        showSaveResult(false, "")
                        if (wasQuitting)
                            cancelQuitRequest()
                    }
                } else {
                    showSaveResult(ok, backend.profilePath())
                }
            }, function() {
                if (wasQuitting)
                    cancelQuitRequest()
            })
        }
        // Closing the file window without saving calls off what waited on
        // the save, quit included; the next Save As starts clean.
        onRejected: () => {
            var wasQuitting = afterSaveQuitting
            afterSave = null
            afterSaveQuitting = false
            if (wasQuitting)
                cancelQuitRequest()
        }
    }

    FileDialog {
        id: _loadProfileFileDialog
        title: "Open Profile"

        acceptLabel: "Open"
        defaultSuffix: "xml"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Profile files (*.xml)"]
        currentFolder: backend.profilesFolderUrl()

        onAccepted: () => {
            var file = currentFile
            if (backend)
                leaveDisplayThen(function() {
                    guardUnsavedChanges(function() { backend.loadProfile(file) })
                })
        }
    }

    HintsTooltip {
        id: _hintsTooltip

        hints: []
    }

    // The menu bar, shortcuts and command palette all come from one list of
    // commands (main_commands.js). Menus show only what can be used now.
    menuBar: ThemedMenuBar {
        ThemedMenu {
            title: qsTr("File")

            ThemedMenuItem { command: "file.new" }
            ThemedMenuItem { command: "file.load" }
            ThemedMenu {
                id: _recentMenu
                title: qsTr("Recent")

                Instantiator {
                    model: backend ? backend.recentProfiles : []
                    delegate: ThemedMenuItem {
                        required property var modelData
                        text: _root.fileNameOf(modelData)
                        PointerTip {
                            text: modelData
                            delay: 400
                            show: true
                        }
                        onTriggered: () => { _root.loadRecent(modelData) }
                    }
                    onObjectAdded: (index, object) => _recentMenu.insertItem(index, object)
                    onObjectRemoved: (index, object) => _recentMenu.removeItem(object)
                }
            }
            ThemedMenuItem { command: "file.save" }
            ThemedMenuItem { command: "file.saveAs" }
            ThemedMenuSeparator {}
            ThemedMenuItem { command: "file.exit" }
        }

        ThemedMenu {
            title: qsTr("View")

            ThemedMenuItem { command: "view.home" }
            ThemedMenuItem { command: "view.configuration" }
            ThemedMenuSeparator {}
            ThemedMenu {
                title: qsTr("Home Layout")
                ThemedMenuItem { command: "view.layout.single" }
                ThemedMenuItem { command: "view.layout.side" }
                ThemedMenuItem { command: "view.layout.stacked" }
            }
            ThemedMenuItem { command: "view.scripts" }
            ThemedMenuItem { command: "view.settings" }
            ThemedMenuSeparator {}
            ThemedMenuItem { command: "view.palette" }
        }

        ThemedMenu {
            title: qsTr("Tools")

            ThemedMenu {
                title: qsTr("Viewers")
                ThemedMenuItem { command: "tools.vjoyViewer" }
                ThemedMenuItem { command: "tools.xboxViewer" }
            }
            ThemedMenu {
                title: qsTr("Device Setup")
                ThemedMenuItem { command: "tools.calibration" }
                ThemedMenuItem { command: "tools.hidhide" }
                ThemedMenuItem { command: "tools.configureInput" }
                ThemedMenuItem { command: "tools.configureOutput" }
                ThemedMenuItem { command: "tools.deviceInfo" }
                ThemedMenuItem { command: "tools.swapDevices" }
                ThemedMenuItem { command: "tools.devicePack" }
            }
            ThemedMenu {
                title: qsTr("Mapping")
                ThemedMenuItem { command: "tools.logical" }
                ThemedMenuItem { command: "tools.buttonMap" }
                ThemedMenuItem { command: "tools.autoMapper" }
                ThemedMenuItem { command: "tools.manageModes" }
            }
            ThemedMenuSeparator {}
            ThemedMenuItem { command: "tools.options" }
        }

        ThemedMenu {
            title: qsTr("Debug")

            ThemedMenuItem { command: "debug.liveLog" }
        }

        ThemedMenu {
            title: qsTr("Help")

            ThemedMenuItem { command: "help.guide" }
            ThemedMenuItem { command: "help.updates" }
            ThemedMenuItem { command: "help.about" }
        }
    }

    // A shortcut for each command that has one.
    Instantiator {
        model: _root.shortcutCommands
        delegate: Shortcut {
            required property var modelData
            sequence: modelData.shortcut
            onActivated: Commands.trigger(modelData.id)
        }
    }

    CommandPalette {
        id: _commandPalette
        owners: ["main"]
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
                // Glossary: Run / Stop.
                caption: backend && backend.gremlinActive ? "Stop" : "Run"
                color: backend && backend.gremlinActive ? Style.accent : Style.foreground
                tooltip: backend && backend.gremlinActive ? qsTr("Stop the profile") : qsTr("Run the profile")

                onClicked: () => {
                    if (backend) {
                        backend.toggleActiveState()
                    }
                }
            }

            JGToolButton {
                text: "\uF3F2"
                tooltip: qsTr("Show or hide the vJoy Viewer")
                caption: "vJoy Viewer"

                onClicked: () => {
                    Helpers.toggleComponent("DialogInputViewer.qml")
                }
            }

            JGToolButton {
                text: "\uF2D4"
                tooltip: qsTr("Show or hide the Xbox Viewer")
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
                text: "\uF3E5"
                // Program-wide settings; the profile's own are its Profile Settings tab.
                caption: "Options"
                tooltip: qsTr("Options: settings for the whole program")

                onClicked: () => {
                    Helpers.createComponent("DialogOptions.qml")
                }
            }

            LayoutHorizontalSpacer {}

            Label {
                Layout.rightMargin: Style.dp(10)

                // One mode: the one you edit is the one that runs.
                text: "Mode"
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
                            : (Style.isDarkMode ? _modeSelector.U.Universal.altMediumLowColor : Style._light.item)
                }

                delegate: DropdownRow {
                    combo: _modeSelector
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
                    text: qsTr("Mode: the one you edit is the one that runs.")
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
        color: (Style.isDarkMode ? U.Universal.chromeMediumColor : Style._light.bar)

        RowLayout {
            anchors.fill: parent

            Label {
                Layout.preferredWidth: Math.max(Style.dp(200), implicitWidth)
                padding: Style.dp(5)

                color: backend && backend.gremlinActive ? Style.foreground : Style.fgMuted
                text: "<B>Status: </B>" +
                    Helpers.selectText(
                        backend && backend.gremlinActive, "Running", "Stopped"
                    ) +
                    Helpers.selectText(
                        backend && backend.gremlinActive && backend.gremlinPaused, " (Paused)", ""
                    ) +
                    // Started with edits that are not saved yet: they run too.
                    Helpers.selectText(
                        backend && backend.gremlinActive && _root.profileDirty, " (unsaved changes)", ""
                    )
            }

            Label {
                id: _savedLine
                Layout.fillWidth: true
                padding: Style.dp(5)
                color: Style.fg
                elide: Text.ElideMiddle
                text: _root.lastSaveText
                HoverHandler {
                    id: _savedHover
                }
                PointerTip {
                    text: _savedLine.text
                    delay: 400
                    show: _savedLine.text.length > 0
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

        // Open action panes belong to the old profile; nothing unsaved is left by now.
        function onProfileChanged() {
            var catalog = _root.catalogPane()
            if (catalog && catalog.paneHid >= 0)
                catalog.closeAdvancedPane()
            var logical = _root.logicalPane()
            if (logical && logical.closePaneNow)
                logical.closePaneNow()
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
        target: updater

        function onOfferUpdate() {
            Helpers.createComponent("DialogUpdate.qml")
        }

        function onInstallRequested() {
            _root.quitGremlin(false, true)
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
        if (updater)
            updater.setInstallOnExit(false)
        _windowPlacement.save(_root)
        // Same order as File > Exit: tool windows, panels, then the profile,
        // then quit.
        if (toolWindowWithUnsavedWork()) {
            close.accepted = false
            stopQuitForToolWindow()
            return
        }
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

        // Home stays loaded while the window shows; unloaded in the tray.
        Loader {
            id: _statusLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            active: !_root.trayed
            visible: active && (!uiState || uiState.currentRoom === "status")
            sourceComponent: StatusPage {
                model: _moduleModel
                onFocusSlug: function(slug) {
                    _moduleModel.setFocus(slug)
                }
                onOpenConfiguration: function(card) {
                    openConfigurationForCard(card)
                }
                onOpenButtonMap: function(card) {
                    openButtonMapForCard(card)
                }
                onOpenOutputView: function(card) {
                    openOutputViewForCard(card)
                }
                onConfigureModule: function(card) {
                    openConfigureModule(card.direction === "dest" ? "dest" : "source", card)
                }
                onAutoMap: function(card) {
                    Helpers.createComponent("DialogAutoMapper.qml", {"initialSlug": card.slug || ""})
                }
                onOpenPairing: function(card) {
                    pairingForCard(card)
                }
                onOpenCalibration: function(card) {
                    Helpers.createComponent("DialogCalibration.qml", {"initialSlug": card.slug || ""})
                }
                onOpenDeviceInformation: function(card) {
                    Helpers.createComponent("DialogDeviceInformation.qml", {"initialGuid": card.guid || ""})
                }
                onAssignHardware: function(card) {
                    Helpers.createComponent("DialogSwapDevices.qml", {"initialGuid": card.guid || ""})
                }
                onIgnoreDevice: function(card) {
                    _moduleModel.ignoreSlug(card.slug)
                }
                onDeviceDeleted: function(card) {
                    closeDeletedDevice(card)
                }
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
                        text: "Driven by: [nothing]"
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Label {
                        visible: configDirection === "dest"
                        text: "View only — shows what the input modules' actions send."
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                    }
                }
                Button {
                    visible: configDirection === "dest"
                    text: outputViewPanel ? "Hide Appearance" : "Appearance…"
                    // Hiding goes through the panel's close, which asks about unsaved
                    // display options and then hides it.
                    onClicked: {
                        var output = outputPane()
                        if (outputViewPanel && output && output.requestClose) {
                            output.requestClose()
                            return
                        }
                        outputViewPanel = !outputViewPanel
                        rememberDisplayPanel()
                    }
                }
                CheckBox {
                    visible: configDirection !== "dest" && configDirection !== "logical"
                    text: "Move inputs with no actions to the end"
                    checked: _root.parkEmptyInUnmapped
                    onToggled: {
                        _root.parkEmptyInUnmapped = checked
                        var catalog = catalogPane()
                        if (catalog)
                            catalog.parkEmptyInUnmapped = checked
                    }
                    PointerTip {
                        text: "When checked, controls with no actions are listed together under No actions."
                        delay: 400
                        show: true
                    }
                }
                Button {
                    visible: configDirection !== "dest" && configDirection !== "logical"
                    text: catalogPanel ? "Hide Appearance" : "Appearance…"
                    onClicked: {
                        var catalog = catalogPane()
                        if (catalogPanel && catalog && catalog.requestClose) {
                            catalog.requestClose()
                            return
                        }
                        catalogPanel = !catalogPanel
                        rememberDisplayPanel()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Style.dp(1)
                color: Style.line
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

                    text: "Profile Settings"
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
                    && _root._configLive
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
                    && _root._configLive
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
                    && _root._configLive
            visible: active
            sourceComponent: _configSplitComp
            onLoaded: _root.syncCatalogView()
        }

        // Loaded only while shown.
        Loader {
            id: _scriptLoader
            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.verticalStretchFactor: 10
            active: !!uiState && uiState.currentRoom === "scripts"
            visible: active
            sourceComponent: ScriptManager {
                scriptListModel: backend ? backend.scriptListModel : null
            }
        }

        // Loaded only while shown.
        Loader {
            id: _settingsLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.verticalStretchFactor: 10
            active: !!uiState && uiState.currentRoom === "settings"
            visible: active
            sourceComponent: ProfileSettings {
                settingsModel: ProfileSettingsModel {}
            }
        }
    }


    Component {
        id: _configSplitComp

        SplitView {
            id: _splitView

            // Each panel loads only for its own tab.
            readonly property var catalog: _catalogLoader.item
            readonly property var oscList: _oscLoader.item

            clip: true
            orientation: (uiState && uiState.currentTab === "physical") ? Qt.Vertical : Qt.Horizontal

            Loader {
                id: _catalogLoader
                active: uiState && uiState.currentTab === "physical"
                visible: active
                SplitView.minimumWidth: Style.dp(400)
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                onLoaded: _root.syncCatalogView()
                sourceComponent: BindingCatalog {
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
            }

            Loader {
                id: _logicalListLoader
                active: uiState && uiState.currentTab === "logical"
                visible: active
                SplitView.minimumWidth: Style.dp(360)
                SplitView.preferredWidth: Style.dp(420)
                SplitView.fillHeight: true
                sourceComponent: LogicalDevice {
                    onInputIdentifierChanged: () => {
                        if (uiState) {
                            uiState.setCurrentInput(inputIdentifier, inputIndex)
                        }
                    }
                }
            }

            Loader {
                id: _oscLoader
                active: uiState && uiState.currentTab === "osc"
                visible: active
                SplitView.minimumWidth: Style.dp(400)
                // It follows the mode from when it loads.
                onLoaded: if (uiState && item.device) item.device.setMode(uiState.currentMode)
                sourceComponent: OscDevice {
                    onInputIdentifierChanged: () => {
                        if (uiState) {
                            uiState.setCurrentInput(inputIdentifier, inputIndex)
                        }
                    }
                }
            }

            Loader {
                id: _xboxLoader
                active: uiState && uiState.currentTab === "xbox"
                visible: active
                SplitView.minimumWidth: Style.dp(400)
                SplitView.fillWidth: true
                sourceComponent: XboxDevice {}
            }

            Loader {
                id: _keyboardLoader
                active: uiState && uiState.currentTab === "keyboard"
                visible: active
                SplitView.minimumWidth: Style.dp(400)
                sourceComponent: KeyboardInputList {}
            }

            Loader {
                id: _inputConfigLoader
                active: uiState && !["scripts", "settings", "xbox", "physical"].includes(uiState.currentTab)
                visible: active
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: Style.dp(900)
                sourceComponent: InputConfiguration {
                    isOutput: _root.configDirection === "dest"

                    Component.onCompleted: () => {
                        if (backend && uiState) {
                            inputItemModel = backend.getInputItem(
                                uiState.currentInput,
                                uiState.currentInputIndex
                            )
                        }
                    }
                }
            }
        }
    }
}
