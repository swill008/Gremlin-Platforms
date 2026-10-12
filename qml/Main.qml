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
import "window_registry.js" as Registry
import "main_commands.js" as MainCommands
import "device_library_open.js" as DeviceLibraryOpen
import "help_links.js" as HelpLinks

ApplicationWindow {
    font.pixelSize: Style.fontSize

    // "* name" (the * means unsaved changes); the title bar shows
    // "Gremlin-Platforms R1 1.0.30 - * name" (gremlin/ui/window_titles.py, 01 S57).
    title: (profileDirty ? "* " : "") + (backend ? backend.windowTitle : "Untitled")

    // Unsaved changes, checked while the window is in front (edits only
    // happen then) and right after a load or save. The cheap check: it
    // rebuilds the profile only after an edit (04 Q19); the questions use
    // the exact profileContainsUnsavedChanges.
    property bool profileDirty: false
    function refreshProfileDirty() {
        profileDirty = !!(backend && backend.profileLooksUnsaved)
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
        // A Logical Device edit (its file is saved with the profile, 04 S2).
        function onUnsavedChanged() { Qt.callLater(refreshProfileDirty) }
    }

    // Unsaved profile edits a crash left (04 S94): Restore / Discard /
    // Not now, as the Device Mapping Editor's Autosave. Not now keeps the copy for the
    // next open of the profile.
    function offerProfileRecovery() {
        if (!backend || typeof backend.takeRecoveryOffer !== "function")
            return
        var offer = backend.takeRecoveryOffer()
        if (!offer || offer.name === undefined)
            return
        _profileRecoveryGate.recoveryPath = String(offer.path || "")
        var when = String(offer.savedAt || "").replace("T", " at ")
        _profileRecoveryGate.choose("Unsaved Edits Found",
                                    "The profile " + offer.name + " has edits" + (when.length ? " from " + when : "")
                                    + " that were never saved, probably because the program closed unexpectedly.

"
                                    + "Restore opens them; save to keep them. Discard deletes them.",
                                    "Restore", "Discard")
        _profileRecoveryGate.cancelText = "Not now"
    }
    Connections {
        target: backend
        function onRecoveryOfferChanged() { Qt.callLater(offerProfileRecovery) }
    }
    DismissibleDialog {
        id: _profileRecoveryGate
        objectName: "profileRecoveryGate"
        property string recoveryPath: ""
        onConfirmed: backend.restoreRecovery(recoveryPath)
        onDiscarded: backend.discardRecovery(recoveryPath)
    }
    // The toolbar's width with or without the captions. When the window is
    // narrower than the toolbar with captions, the buttons show their icons
    // only (the tooltips still name them). Worked out from the parts, not the
    // row, so it can't loop.
    readonly property int _modeListWidth: Style.dp(200)
    readonly property int _modeListMinWidth: Style.dp(120)
    function _toolbarWidth(withCaptions) {
        var buttons = [_homeButton, _toggleButton, _vjoyViewerButton, _inputTesterButton,
                       _deviceMappingEditorButton, _deviceLibraryButton, _logicalButton, _optionsButton]
        var w = _homeButton.rightPadding + _toolbarRow.spacing * buttons.length
        for (var i = 0; i < buttons.length; i++)
            w += withCaptions ? buttons[i].fullWidth : buttons[i].compactWidth
        return w + Math.max(0, (_toggleButton.fullWidth - _toggleButton.compactWidth) / 2) * (withCaptions ? 1 : 0)
    }
    readonly property bool toolbarCompact: width < Math.ceil(_toolbarWidth(true))
    // The Mode group on the bar under the toolbar (01 S58a): Mode, the mode
    // list (narrowed to its minimum when short of room), Manage Modes and the
    // divider, each with its margin. The page's own controls after it scroll
    // when they don't fit, so they don't count.
    function _modeBarWidth(fullList) {
        return Style.dp(12) * 2 + _modeBarRow.spacing * 4
            + _modeLabel.implicitWidth + Style.dp(10)
            + (fullList ? _modeListWidth : _modeListMinWidth) + Style.dp(10)
            + _manageModesButton.implicitWidth + Style.dp(10)
            + Style.dp(1) + Style.dp(10)
    }
    // The open page's item and its own controls for the bar (a page may
    // declare `property Component pageBar`; none means an empty bar).
    readonly property Item currentPageItem: {
        var loaders = [_statusLoader, _outputLoader, _logicalLoader, _oscPageLoader,
                       _deviceBindingsPageLoader, _keyboardPageLoader, _xboxLoader,
                       _scriptLoader, _settingsLoader]
        for (var i = 0; i < loaders.length; i++)
            if (loaders[i].visible && loaders[i].item)
                return loaders[i].item
        return null
    }
    readonly property Component currentPageBar:
        currentPageItem && currentPageItem.pageBar ? currentPageItem.pageBar : null
    // Never narrower than the toolbar with icons only or the bar under it
    // with the list narrowed (so Manage Modes stays in the window), and
    // never wider or taller than the screen.
    minimumWidth: Style.fitWidth(Math.max(Style.dp(1300), Math.ceil(_toolbarWidth(false)),
                                          Math.ceil(_modeBarWidth(false))), Screen)
    minimumHeight: Style.fitHeight(Style.dp(700), Screen)
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
    // unloaded to give their memory back. The binding pages stay while they hold
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
        // Tool windows reach closeActionPanes() through Helpers.
        Helpers.setMainWindow(_root)
        Style.helpLinks = { check: _helpLinkCheck, reveal: _helpLinkReveal }
        Qt.callLater(offerProfileRecovery)
    }

    Component.onDestruction: () => {
        if (Style.helpLinks && Style.helpLinks.check === _helpLinkCheck)
            Style.helpLinks = null
    }

    // Help's "Open ›" and "Show me ›" links (01 S139, D-01-HELP-LINKS).
    // check(link) and reveal(link) return "" or why it can't be shown now.
    // Show me points without choosing: a menu drops down with the item
    // pulsing, a button pulses; nothing is triggered.

    // Visible text compared without "…", "&" or case.
    function _helpNorm(text) {
        return String(text || "").replace(/…/g, "").replace(/\.\.\./g, "")
                                 .replace(/&/g, "").trim().toLowerCase()
    }

    // Toolbar buttons by caption, tooltip and other names (Run and Stop
    // are one button).
    function _helpToolbarButton(name) {
        var want = _helpNorm(name)
        var buttons = [_homeButton, _toggleButton, _vjoyViewerButton, _inputTesterButton,
                       _deviceMappingEditorButton, _deviceLibraryButton, _logicalButton, _optionsButton]
        for (var i = 0; i < buttons.length; ++i) {
            var b = buttons[i]
            var names = [b.caption, b.tooltip]
            if (b === _toggleButton)
                names = names.concat(["Run", "Stop", "Run the profile", "Stop the profile"])
            for (var j = 0; j < names.length; ++j)
                if (_helpNorm(names[j]) === want)
                    return b
        }
        return null
    }

    function _helpModeBarControl(name) {
        var want = _helpNorm(name)
        if (want === "" || want === "mode")
            return _modeSelector
        if (want === "manage modes")
            return _manageModesButton
        return null
    }

    // A row of a menu: available now if shown and enabled; a submenu if it
    // has something in it.
    function _helpRowUsable(item) {
        if (item.subMenu) {
            if (typeof item.subMenu.compactNow === "function")
                item.subMenu.compactNow()
            return item.subMenu.enabled
                    && (typeof item.subMenu.hasShown !== "function" || item.subMenu.hasShown())
        }
        if (typeof item.refresh === "function")
            item.refresh()
        return item.shown !== false && item.enabled
    }

    // {chain: [menus], rows: [row in each menu], error} for a menu path:
    // chain[0] is the menu bar's menu, rows[k] the row picked in chain[k].
    function _helpMenuPath(parts) {
        var bar = _root.menuBar
        var path = parts.join("/")
        if (!bar || parts.length < 2)
            return { error: "No such menu item: " + path }
        var top = null
        var topIndex = -1
        for (var i = 0; i < bar.count; ++i) {
            var m = bar.menuAt(i)
            if (m && _helpNorm(m.title) === _helpNorm(parts[0])) {
                top = m
                topIndex = i
                break
            }
        }
        if (!top)
            return { error: "No such menu item: " + path }
        var chain = [top]
        var rows = []
        var menu = top
        for (var p = 1; p < parts.length; ++p) {
            var found = null
            for (var r = 0; r < menu.count; ++r) {
                var row = menu.itemAt(r)
                if (row && row.text !== undefined && _helpNorm(row.text) === _helpNorm(parts[p])) {
                    found = row
                    break
                }
            }
            if (!found)
                return { error: "No such menu item: " + path }
            rows.push(found)
            if (p < parts.length - 1) {
                if (!found.subMenu)
                    return { error: "No such menu item: " + path }
                menu = found.subMenu
                chain.push(menu)
            }
        }
        return { chain: chain, rows: rows, topIndex: topIndex, error: "" }
    }

    // Options' settings by label, without opening Options (findSetting
    // ignores case; a repeated label also matches with its group).
    ConfigSectionModel { id: _helpOptionLabels }

    function _helpLinkCheck(link) {
        var parsed = HelpLinks.parse(link)
        var parts = parsed.parts
        if (parsed.kind === "open") {
            var id = parts[0]
            if (!HelpLinks.isAllowedOpen(id) || !Commands.get(id))
                return "Help can't open this: " + id
            // Not enabled means that page is the one showing already:
            // reveal brings the main window to the front.
            return ""
        }
        if (parsed.kind !== "show" || !parts.length)
            return "Not a link to the program: " + link
        var rest = parts.slice(1)
        if (parts[0] === "menu") {
            var found = _helpMenuPath(rest)
            if (found.error)
                return found.error
            for (var k = 0; k < found.rows.length; ++k)
                if (!_helpRowUsable(found.rows[k]))
                    return rest.join(" › ") + " can't be used now."
            return ""
        }
        if (parts[0] === "toolbar")
            return _helpToolbarButton(rest.join("/")) ? "" : "No such toolbar button: " + rest.join("/")
        if (parts[0] === "modebar")
            return _helpModeBarControl(rest.join("/")) ? "" : "No such mode bar control: " + rest.join("/")
        if (parts[0] === "option") {
            var hit = _helpOptionLabels.findSetting(rest.join("/"))
            return hit && hit.length ? "" : "No such setting in Options: " + rest.join("/")
        }
        if (parts[0] === "devicemappingeditor")
            return _helpDeviceMappingEditorTargets.indexOf(rest.join("/")) >= 0
                ? "" : "No such place in the Device Mapping Editor: " + rest.join("/")
        return "Not a link to the program: " + link
    }

    // What show:devicemappingeditor/<objectName> may point at in the Device
    // Mapping Editor window (07 S126, D-07-PLANES-FOLLOWUP Q1a); its revealForHelp shows
    // them. Known here so links check without the window open.
    // One per area (user 2026-10-11): each menu's title in the bar, the two
    // side panels, Properties, the Background banner and row.
    readonly property var _helpDeviceMappingEditorTargets: [
        "dmeMenuFile", "dmeMenuEdit", "dmeMenuView", "dmeMenuInsert", "dmeMenuArrange",
        "dmeMenuLeader", "dmeMenuFormat", "dmeMenuHelp",
        "chipsSide", "layersSide", "propsPanel", "dmeBgBanner", "dmeBgRow"]

    function _helpFront() {
        if (_root.visibility === Window.Minimized || !_root.visible)
            _root.showNormal()
        _root.raise()
        _root.requestActivate()
    }

    function _helpPulse(item) {
        var component = Qt.createComponent("Pulse.qml")
        return component.status === Component.Ready ? component.createObject(item) : null
    }

    // Scrolls a toolbar or page-bar flick so the control shows.
    function _helpScrollTo(item, flick) {
        if (!flick || !flick.interactive)
            return
        var at = item.mapToItem(flick.contentItem, 0, 0)
        if (at.x < flick.contentX)
            flick.contentX = at.x
        else if (at.x + item.width > flick.contentX + flick.width)
            flick.contentX = Math.min(flick.contentWidth - flick.width, at.x + item.width - flick.width)
    }

    function _helpLinkReveal(link) {
        var why = _helpLinkCheck(link)
        if (why !== "")
            return why
        var parsed = HelpLinks.parse(link)
        var parts = parsed.parts
        if (parsed.kind === "open") {
            if (!Commands.trigger(parts[0]))
                _helpFront()
            return ""
        }
        var rest = parts.slice(1)
        if (parts[0] === "option") {
            Commands.trigger("tools.options")
            var win = Helpers.windowOf("DialogOptions.qml")
            if (!win || typeof win.revealSetting !== "function")
                return "Options didn't open."
            return win.revealSetting(rest.join("/")) ? "" : "No such setting in Options: " + rest.join("/")
        }
        if (parts[0] === "devicemappingeditor") {
            // The window as it is, or opened blank (it picks a device).
            var map = deviceMappingEditorWindow()
            if (!map)
                openBlankDeviceMappingEditor()
            map = deviceMappingEditorWindow()
            if (!map || typeof map.revealForHelp !== "function")
                return "The Device Mapping Editor didn't open."
            return map.revealForHelp(rest.join("/"), _helpPulse)
        }
        _helpFront()
        if (parts[0] === "toolbar") {
            var button = _helpToolbarButton(rest.join("/"))
            _helpScrollTo(button, _toolbarFlick)
            _helpPulse(button)
            return ""
        }
        if (parts[0] === "modebar") {
            _helpPulse(_helpModeBarControl(rest.join("/")))
            return ""
        }
        // A menu: drop each menu down in turn, mark the last row and pulse
        // it. Nothing is chosen.
        var found = _helpMenuPath(rest)
        var bar = _root.menuBar
        var barItem = bar.itemAt(found.topIndex)
        found.chain[0].popup(barItem, 0, barItem.height)
        for (var k = 0; k < found.rows.length; ++k) {
            var menu = found.chain[k]
            var row = found.rows[k]
            for (var r = 0; r < menu.count; ++r)
                if (menu.itemAt(r) === row)
                    menu.currentIndex = r
            if (row.subMenu)
                row.subMenu.popup(row, row.width, 0)
            else
                _helpPulse(row)
        }
        return ""
    }

    U.Universal.theme: Style.theme
    color: Style.background

    property string configTitleName: ""
    // Moves when a card's shown name may have changed (the user's name for
    // a device, 10 S7): the Device Bindings page title reads it afresh.
    property int namesRev: 0

    function configTitleShown() {
        return namesRev, _moduleModel.shownName(uiState ? String(uiState.currentDevice || "") : "",
                                                configTitleName)
    }
    onConfigTitleNameChanged: {
        syncOutputView()
        Qt.callLater(syncDeviceBindingsPage)
    }
    property string configDirection: ""
    property int sourceModuleCount: 0
    property int destModuleCount: 0
    // The Output View's Appearance panel, open or closed per device. The
    // Device Bindings, Keyboard, Logical and OSC pages keep their own.
    property bool outputViewPanel: true
    property bool _panelReady: false
    property string _panelDevice: ""

    function panelDeviceId() {
        var guid = uiState ? String(uiState.currentDevice || "") : ""
        if (guid.length)
            return guid
        return configTitleName
    }

    function applyDisplayPanel() {
        var id = panelDeviceId()
        _panelDevice = id
        _panelReady = false
        if (configDirection === "dest")
            outputViewPanel = id.length ? _windowPlacement.displayPanelOpen("output", id) : true
        _panelReady = true
    }

    function rememberDisplayPanel() {
        if (!_panelReady || configDirection !== "dest")
            return
        var id = _panelDevice.length ? _panelDevice : panelDeviceId()
        if (!id.length)
            return
        _windowPlacement.setDisplayPanelOpen("output", id, outputViewPanel)
    }

    function refreshDestBound() {
        if (_destBound)
            _destBound.text = _moduleModel.boundLine(configTitleName)
    }
    // Module Setup: one at a time, also kept in the shared window list.
    property var configureWin: null
    onConfigureWinChanged: Registry.track("DialogConfigureModule.qml", configureWin)

    ModuleListModel {
        id: _moduleModel
    }

    // The card's device name (its folder is found from it and its id).
    function cardDeviceName(card) {
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
        uiState.setCurrentDevice(uiState.logicalDeviceGuid)
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

    function openDeviceBindingsNow(card) {
        if (!uiState || !card)
            return
        _panelReady = false
        _moduleModel.setFocus(card.slug)
        configTitleName = cardDeviceName(card)
        refreshDestBound()
        configDirection = card.direction || "source"
        uiState.setCurrentDevice(card.guid)
        uiState.setCurrentTab(card.tab || "physical")
        uiState.setCurrentRoom("configuration")
        applyDisplayPanel()
        refreshSourceModuleCount()
        // The page shows the new device at once, not after the deferred
        // sync (SHAKE-STRESS-09); the later call then changes nothing.
        syncDeviceBindingsPage()
    }

    // The device under the open Device Bindings page can change without a card
    // click: an unplugged stick moves the page to the first stick left, or to
    // the Logical Device when none is (UIState, 02 S33). The page then
    // belongs to that device: title, focused card, direction and panels
    // (05 S105).
    Instantiator {
        id: _cardGuids
        model: _moduleModel
        delegate: QtObject {
            required property string slug
            required property string guid
        }
    }

    function _plainGuid(text) {
        return String(text || "").toUpperCase().replace(/[{}-]/g, "")
    }

    function _cardForGuid(guid) {
        var want = _plainGuid(guid)
        if (!want.length)
            return null
        for (var i = 0; i < _cardGuids.count; i++) {
            var row = _cardGuids.objectAt(i)
            if (row && _plainGuid(row.guid) === want)
                return _moduleModel.cardMap(row.slug)
        }
        return null
    }

    function followShownDevice() {
        if (!uiState || uiState.currentRoom !== "configuration")
            return
        if (uiState.currentTab === "logical") {
            if (configDirection !== "logical") {
                _panelReady = false
                configTitleName = "Logical Device"
                configDirection = "logical"
            }
            return
        }
        if (uiState.currentTab !== "physical")
            return
        var card = _cardForGuid(uiState.currentDevice)
        if (!card || !card.slug)
            return
        var focused = _moduleModel.focusedCardMap()
        if (focused && focused.slug === card.slug && configTitleName === cardDeviceName(card))
            return
        openDeviceBindingsNow(card)
    }

    Connections {
        target: uiState
        function onDeviceChanged() { Qt.callLater(_root.followShownDevice) }
        function onTabChanged() { Qt.callLater(_root.followShownDevice) }
    }

    property var _afterDisplayLeave: null

    function leaveDisplayThen(next) {
        _afterDisplayLeave = next
        continueDisplayLeave()
    }

    // The joystick Device Bindings page (05 S121-S131).
    function deviceBindingsPane() {
        return _deviceBindingsPageLoader.item
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

    // The Device Bindings page shows the open device under its module name.
    function syncDeviceBindingsPage() {
        var page = _deviceBindingsPageLoader.item
        if (!page || !uiState || uiState.currentTab !== "physical")
            return
        var guid = String(uiState.currentDevice || "")
        if (page.guid !== guid || page.deviceName !== configTitleName)
            page.setDevice(guid, configTitleName)
    }

    function logicalPane() {
        return _logicalLoader.item
    }

    // The OSC page (09 S129): the Logical Device page's pane rules.
    function oscPane() {
        return _oscPageLoader.item
    }

    // Tools > OSC Monitor (09 S138): the OSC page with its Monitor shown.
    property bool _oscMonitorWanted: false

    function openOscMonitor() {
        if (!uiState)
            return
        var card = _cardForGuid(uiState.oscDeviceGuid) || _moduleModel.cardMap("osc")
        var page = oscPane()
        if (page && uiState.currentRoom === "configuration" && uiState.currentTab === "osc") {
            page.showMonitor()
            return
        }
        _oscMonitorWanted = true
        if (card)
            openDeviceBindingsForCard(card)
    }

    // Each open page with unsaved edits asks in turn (Save / Discard /
    // Cancel); its leaveResolved() comes back here for the next one.
    function _leavePages() {
        var pages = [outputPane(), deviceBindingsPane(), keyboardPane(), logicalPane(), oscPane()]
        var out = []
        for (var i = 0; i < pages.length; ++i)
            out.push(_paneOf(pages[i]))
        return out
    }

    // What answers the leave / pane calls for a page: its shared ActionPane
    // (`property alias actionPane`), or the page itself (Output View).
    function _paneOf(page) {
        return page ? (page.actionPane || page) : null
    }

    function continueDisplayLeave() {
        var output = outputPane()
        if (output)
            output.leaveMessage = _quitPending ? "Appearance changes are not saved. Quit and they will be lost." : ""
        var pages = _leavePages()
        for (var i = 0; i < pages.length; ++i) {
            var page = pages[i]
            if (page && page.hasUnsaved && page.hasUnsaved()) {
                page.requestLeave()
                return
            }
        }
        var next = _afterDisplayLeave
        _afterDisplayLeave = null
        if (next)
            next()
    }

    // The open action panes (Device Bindings, Keyboard, Logical Device and
    // OSC pages). Tools that change bindings behind a pane (Auto Mapping Tool
    // Create, History Restore, Device Pack import) close them first, or a
    // later OK would write the pane's old copy back (05 Q8,
    // D-05-DRAFT-OUTDATED).
    function _actionPanes() {
        var panes = []
        var all = [deviceBindingsPane(), keyboardPane(), logicalPane(), oscPane()]
        for (var i = 0; i < all.length; ++i)
            if (all[i])
                panes.push(_paneOf(all[i]))
        return panes
    }

    function _paneChanged(pane) {
        return typeof pane.paneHasChanges === "function" && !!pane.paneHasChanges()
    }

    // Closes a pane without saving (its draft is dropped).
    function _closeActionPane(pane) {
        if (typeof pane.closeActionPane === "function")
            pane.closeActionPane()
        else if (typeof pane.closePaneNow === "function")
            pane.closePaneNow()
    }

    // Closes the action panes, then calls then(). A pane with changes that
    // are not saved asks first: Discard closes them and goes on, Cancel
    // keeps them open and then() is not called.
    function closeActionPanes(then) {
        var panes = _actionPanes()
        var changed = false
        for (var i = 0; i < panes.length; ++i)
            changed = changed || _paneChanged(panes[i])
        var go = function() {
            var open = _actionPanes()
            for (var j = 0; j < open.length; ++j)
                _closeActionPane(open[j])
            if (typeof then === "function")
                then()
        }
        if (!changed) {
            go()
            return
        }
        _actionPaneGate.confirmThen("Unsaved Changes",
                                    "The action editor has changes that are not saved.",
                                    "Discard", go, null, true)
    }

    // Run (toolbar and tray). An action pane with changes asks first
    // ("Save or discard the open action first?", 06 Q6): the profile runs
    // as saved, and the panes are locked while it runs. Stop never asks.
    function toggleRun() {
        if (!backend)
            return
        if (_editLock.locked) {
            // Running: Stop never asks.
            backend.toggleActiveState()
            return
        }
        var panes = _actionPanes()
        var changed = false
        for (var i = 0; i < panes.length; ++i)
            changed = changed || _paneChanged(panes[i])
        if (!changed) {
            _closeActionPanesThenRun()
            return
        }
        // From the tray the window may be hidden: the question must show.
        if (!_root.visible)
            _root.show()
        _root.raise()
        _root.requestActivate()
        _runGate.ask("Save or discard the open action first?")
    }

    function _closeActionPanesThenRun() {
        var open = _actionPanes()
        for (var j = 0; j < open.length; ++j)
            _closeActionPane(open[j])
        if (backend && !backend.gremlinActive)
            backend.toggleActiveState()
    }

    // Save in each pane with changes; false (the pane stays open and Run
    // waits) when one could not be saved, for example an unfinished action.
    function _saveChangedPanes() {
        var panes = _actionPanes()
        for (var i = 0; i < panes.length; ++i) {
            var pane = panes[i]
            if (!_paneChanged(pane))
                continue
            if (typeof pane.savePane !== "function" || !pane.savePane())
                return false
        }
        return true
    }

    function cancelDisplayLeave() {
        _afterDisplayLeave = null
        _oscMonitorWanted = false
        if (_quitPending) {
            _quitPending = false
            if (backend)
                backend.setRestartOnExit(false)
            if (updater)
                updater.setInstallOnExit(false)
        }
    }

    // The Keyboard page (CF-Q7).
    function keyboardPane() {
        return _keyboardPageLoader.item
    }

    // Unsaved Output View display options or an edited action pane on the
    // Device Bindings, Keyboard, Logical or OSC page.
    function displayUnsaved() {
        var pages = _leavePages()
        for (var i = 0; i < pages.length; ++i) {
            var page = pages[i]
            if (page && page.hasUnsaved && page.hasUnsaved())
                return true
        }
        return false
    }

    function openDeviceBindingsForCard(card) {
        if (!uiState || !card)
            return
        var name = cardDeviceName(card)
        var direction = card.direction || "source"
        if (uiState.currentRoom === "configuration" && configTitleName === name && configDirection === direction) {
            applyDisplayPanel()
            return
        }
        leaveDisplayThen(function() { openDeviceBindingsNow(card) })
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

    // The Logical Device page is a step of the input cycle (to-do 132).
    function cycleModules(direction, step) {
        var shown = configDirection === "logical" ? "source" : configDirection
        if (shown !== direction || !_moduleModel)
            return
        var slugs = _moduleModel.pileLeaders(direction) || []
        if (slugs.length < 2)
            return
        var focus = configDirection === "logical" ? "logical"
                                                  : String(_moduleModel.focusedSlug || "")
        var index = moduleIndex(slugs, focus)
        var card = _moduleModel.cardMap(slugs[(index + step + slugs.length) % slugs.length])
        if (card && card.slug)
            openDeviceBindingsForCard(card)
    }

    function cycleDeviceBindings(step) {
        cycleModules("source", step)
    }

    function cycleOutput(step) {
        cycleModules("dest", step)
    }

    function openOutputViewForCard(card) {
        openDeviceBindingsForCard(card)
    }

    // Menu commands act on the selected card (the Home page's focus).
    function openDeviceBindingsForFocus() {
        var card = _moduleModel.focusedCardMap()
        if (card && card.slug)
            openDeviceBindingsForCard(card)
        else if (uiState)
            uiState.setCurrentRoom("configuration")
    }

    // card: the card a card command came from; menu commands leave it out
    // and get the selected card.
    function openConfigureModule(direction, card) {
        if (!card || !card.slug)
            card = _moduleModel.focusedCardMap()
        // Tools > Output (Input) Module Setup on a card of the other kind
        // opens the first device of the asked kind: an input stick's
        // module must not be saved as an output module.
        if (direction && card && card.slug && (card.direction || "source") !== direction)
            card = _moduleModel.firstCardMap(direction)
        // The Xbox output has no Module Setup (it claims nothing), and nor
        // has the Logical Device (GL-146).
        if (card && (card.bus === "XInput" || card.tab === "xbox" || card.tab === "logical"))
            return
        if (direction && (!card || !card.slug))
            return
        var want = direction
        if (!want && card && card.direction === "dest")
            want = "dest"
        if (!want)
            want = "source"
        var name = card ? cardDeviceName(card) : ""
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
            // answering that question; leave it in front and open the asked
            // one once it closes (Discard, or Save then OK). Cancel drops
            // the request (03 S40).
            _setupRequest = { "from": old, "direction": direction, "card": card }
            old.close()
            if (old.visible) {
                _dropSetupRequestOnCancel(old)
                old.raise()
                old.requestActivate()
                return
            }
            _setupRequest = null
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
            var next = (_root._setupRequest && _root._setupRequest.from === win) ? _root._setupRequest : null
            if (next)
                _root._setupRequest = null
            Qt.callLater(function() {
                if (_root.configureWin === win)
                    _root.configureWin = null
                win.destroy()
                if (next)
                    _root.openConfigureModule(next.direction, next.card)
            })
        })
        win.show()
        win.raise()
        win.requestActivate()
    }

    // Module Setup for another device, asked for while the open one asks
    // about its unsaved changes: {from, direction, card}.
    property var _setupRequest: null

    // Cancel on the open window's unsaved-changes question keeps it and
    // drops the request for the other device.
    function _dropSetupRequestOnCancel(win) {
        var parts = win.contentData || win.data || []
        for (var i = 0; i < parts.length; i++) {
            var gate = parts[i]
            if (!gate || !gate.visible || typeof gate.ask !== "function" || !gate.cancelled)
                continue
            var drop = function() {
                gate.cancelled.disconnect(drop)
                if (_root._setupRequest && _root._setupRequest.from === win)
                    _root._setupRequest = null
            }
            gate.cancelled.connect(drop)
            return
        }
    }

    // Opens (or brings forward) the card's viewer; it never closes one that
    // is already open (the toolbar's Toggle buttons do that). The Xbox
    // output's live pads are on its Output View.
    function pairingForCard(card) {
        if (!card)
            return
        if (card.bus === "XInput" || card.tab === "xbox" || card.slug === "xbox")
            openOutputViewForCard(card)
        else
            Helpers.createComponent("DialogInputViewer.qml")
    }

    // Xbox Setup (D-XBOX-PADS): the ViGEmBus check and how many Xbox pads
    // are on. From the Xbox card's menu, the palette and the Xbox Output
    // View's "Open Xbox Setup".
    function openXboxSetup() {
        return Helpers.createComponent("DialogXboxSetup.qml")
    }

    // The Xbox output's Output View (its card is always there).
    function openXboxOutputView() {
        var card = _moduleModel ? _moduleModel.cardMap("xbox") : null
        if (card && card.slug)
            openOutputViewForCard(card)
    }

    function closeWorkRoomNow() {
        if (!uiState)
            return
        _panelReady = false
        configTitleName = ""
        configDirection = ""
        uiState.setCurrentRoom("status")
        uiState.setCurrentTab("physical")
    }

    function closeWorkRoom() {
        leaveDisplayThen(function() { closeWorkRoomNow() })
    }

    function closeDeletedDevice(card) {
        var name = card ? String(card.rawName || card.name || "").trim() : ""
        var guid = card ? String(card.guid || "") : ""
        if (name && (configTitleName === name || (uiState && String(uiState.currentDevice || "") === guid)))
            closeWorkRoomNow()
        // Its windows close without asking: Save would write the deleted
        // device's module file again (07 Q7).
        var dropped = false
        var map = deviceMappingEditorWindow()
        if (map && (String(map.targetName || "") === name || String(map.targetGuid || "") === guid)) {
            dropped = deviceMappingEditorNeedsLeave()
            map._allowClose = true
            map.close()
        }
        var setup = configureWin
        if (setup && (String(setup.deviceName || "") === name || String(setup.deviceGuid || "") === guid)) {
            dropped = dropped || (typeof setup.hasUnsavedWork === "function" && setup.hasUnsavedWork())
            setup.allowClose = true
            setup.close()
        }
        if (dropped) {
            _notificationDialog.title = "Device Deleted"
            _notificationDialog.text = (name.length ? name : "The device") + " was deleted, so its open windows were closed without saving."
            _notificationDialog.open()
        }
    }

    // Same as opening a profile: asks only when there is something to lose,
    // and offers Save.
    // The open panes and drafts ask first, then the profile (01 S71), as
    // Load and Recent do.
    function requestNewProfile() {
        leaveDisplayThen(function() {
            guardUnsavedChanges(function() { backend.newProfile() }, false)
        })
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

    function deviceMappingEditorWindow() {
        return Helpers.windowOf("DialogDeviceMappingEditor.qml")
    }

    function openDeviceMappingEditorForCard(card) {
        var name = ""
        var guid = ""
        if (card) {
            name = String(card.rawName || card.name || "")
            guid = String(card.guid || "")
        }
        name = name.trim()
        if (!name.length)
            return
        var existing = deviceMappingEditorWindow()
        if (existing && existing.openForDevice) {
            existing.openForDevice(name, guid)
            existing.show()
            existing.raise()
            existing.requestActivate()
            return
        }
        Helpers.createComponent("DialogDeviceMappingEditor.qml", {
            "targetName": name,
            "targetGuid": guid
        })
    }

    // For the command list (main_commands.js), which keeps no window list of
    // its own (helpers.js keeps one list for the whole program).
    function openTool(spec) {
        Helpers.createComponent(spec)
    }

    // The Device Library window (10 S2), on a device and one of its
    // dialogs ("copy", "swap", "output") or on nothing ("", "", "").
    function openDeviceLibrary(deviceName, guid, action) {
        DeviceLibraryOpen.openDeviceLibrary(String(deviceName || ""), String(guid || ""),
                                            String(action || ""))
    }

    // The Device Library's row menus (10 S15, S44), for target {name, guid,
    // slug} (device_library_open.js toMain): Home's Delete Device, Module
    // Setup, Device Mapping Editor, Show on Home. Returns a Result as JSON text.
    function libraryAction(action, target) {
        var name = String(target.name || "")
        var card = _moduleModel.cardMap(String(target.slug || ""))
        if (action === "deleteDevice") {
            var raw = _moduleModel.deleteDevice(name, String(target.guid || ""))
            try {
                if (JSON.parse(raw).ok)
                    _root.closeDeletedDevice(card && card.slug ? card : { "rawName": name, "guid": target.guid })
            } catch (err) {}
            return raw
        }
        if (action === "history") {
            // 10 S56: Tools > History on this device, card or not: its
            // module file's changes (as Module Setup's History, 08 Q15)
            // and the Device Library's changes that list it.
            var guid = String(target.guid || "")
            Helpers.createComponent("DialogHistory.qml", {
                "filter": JSON.stringify({ "ofDevice": {
                    "deviceId": String(_moduleModel.deviceIdFor(guid, name) || ""),
                    "guid": guid,
                    "name": name
                } }),
                "filterLabel": String(target.shown || name)
            })
            return JSON.stringify({ "ok": true })
        }
        if (!card || !card.slug)
            return JSON.stringify({ "ok": false, "error": (target.shown || name) + " has no card on Home." })
        if (action === "moduleSetup")
            _root.openConfigureModule(card.direction === "dest" ? "dest" : "source", card)
        else if (action === "deviceMappingEditor")
            _root.openDeviceMappingEditorForCard(card)
        else if (action === "home")
            _root.showCardOnHome(card)
        else
            return JSON.stringify({ "ok": false, "error": "Unknown action " + action })
        return JSON.stringify({ "ok": true })
    }

    // Show on Home: the main window in front, on Home, with that card
    // selected and scrolled into view.
    function showCardOnHome(card) {
        if (uiState && uiState.currentRoom !== "status")
            uiState.setCurrentRoom("status")
        _moduleModel.setFocus(card.slug)
        if (!_root.visible)
            _root.show()
        _root.raise()
        _root.requestActivate()
        Qt.callLater(function() {
            var page = _statusLoader.item
            var item = page && page.cardBySlug ? page.cardBySlug(card.slug) : null
            var flick = item ? item.parent : null
            while (flick && flick.contentY === undefined)
                flick = flick.parent
            if (!flick)
                return
            var at = item.mapToItem(flick.contentItem, 0, 0)
            if (at.y >= flick.contentY && at.y + item.height <= flick.contentY + flick.height)
                return
            var most = Math.max(0, flick.contentHeight - flick.height)
            flick.contentY = Math.min(most, Math.max(0, at.y - Style.dp(12)))
        })
    }

    // The same, with properties (Tools > History shows everything, even
    // when it is open on one device's changes).
    function openToolWith(spec, properties) {
        Helpers.createComponent(spec, properties)
    }

    // A Recent file that won't open (moved, deleted, damaged) offers
    // Forget It, as at start (04 Q15): backend.loadRecentProfile reports
    // it with recentProfileFailed instead of an error box.
    function loadRecent(file) {
        if (backend)
            leaveDisplayThen(function() {
                guardUnsavedChanges(function() {
                    if (typeof backend.loadRecentProfile === "function")
                        backend.loadRecentProfile(file)
                    else
                        backend.loadProfile(file)
                })
            })
    }

    function offerForgetRecent(path, why) {
        _lastProfileGate.confirmThen(
            "Recent Profile Didn't Open",
            "This profile didn't open:\n" + path + "\n\n" + why
            + "\n\nForget it, so it isn't listed under Recent or opened at start? "
            + "The file itself stays.",
            "Forget It",
            function() { backend.forgetProfile(path) })
        _lastProfileGate.cancelText = "Keep"
    }

    function fileNameOf(path) {
        var text = String(path || "")
        var cut = Math.max(text.lastIndexOf("/"), text.lastIndexOf("\\"))
        return cut >= 0 ? text.slice(cut + 1) : text
    }

    function openBlankDeviceMappingEditor() {
        var existing = deviceMappingEditorWindow()
        if (existing && existing.openBlank) {
            existing.openBlank()
            return
        }
        Helpers.createComponent("DialogDeviceMappingEditor.qml", {
            "startBlank": true,
            "targetName": "",
            "targetGuid": ""
        })
    }

    function deviceMappingEditorNeedsLeave() {
        var w = deviceMappingEditorWindow()
        if (!w)
            return false
        if (!w.editing)
            return false
        if (typeof w.isDirty !== "function")
            return false
        return w.isDirty()
    }

    function offerDeviceMappingEditorLeaveThenQuit() {
        var w = deviceMappingEditorWindow()
        if (!w)
            return false
        if (typeof w.requestLeaveForAppQuit === "function") {
            w.requestLeaveForAppQuit()
            return true
        }
        return false
    }

    function deactivateThenQuit() {
        if (deviceMappingEditorNeedsLeave()) {
            offerDeviceMappingEditorLeaveThenQuit()
            return
        }
        // Quitting stops a running profile once, in shutdown_cleanup.
        _quitting = true
        Qt.quit()
    }

    // Set once the quit has asked everything: the close the quit makes
    // then goes through onClosing without asking again or clearing a
    // restart or install.
    property bool _quitting: false

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
            // The profile was written but a file its Save also writes was
            // not (04 S13): that message names the file.
            var problem = backend ? backend.saveProblem() : ""
            _saveResultDialog.announce(false, problem !== ""
                ? problem : "Not written. It is still only on this screen.")
            if (backend)
                backend.noteSave(problem !== "" ? problem : "The profile was not written.")
        }
    }

    // Debug › Tracing (main_commands.js): tracing on or off (D-01-TRACE).
    TraceSwitch {
        id: _tracing
    }

    // Tools › Input Tester… (main_commands.js, D-02-INPUT-TESTER): starts
    // the separate tester program; a message when it can't.
    InputTesterLink {
        id: _inputTesterLink
    }

    // The device's background picture (07 S157): draws it, hidden, when
    // devicePhotoMaker asks (gremlin/ui/device_photo.py).
    DevicePhotoHost {}

    function openInputTester() {
        var message = _inputTesterLink.launch()
        if (message.length) {
            _notificationDialog.title = "Input Tester"
            _notificationDialog.text = message
            _notificationDialog.open()
        }
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
            // The Logical Device's and OSC's edits are discarded with the
            // profile's (D-04-LD-FILE, D-09-OSC-FILE).
            if (backend) {
                backend.discardLogicalDevice()
                backend.discardOscDevice()
                // The Device Bindings page's groups, order and names (CS1).
                backend.discardDeviceBindingsLayouts()
            }
            if (action)
                action()
        }
        onCancelled: {
            takeAction()
            if (quitting)
                cancelQuitRequest()
        }
    }

    // The one locked-while-running rule (B5a, 06 S13): Run asks about
    // open action panes only when it starts a Run.
    EditLock { id: _editLock }

    // toggleRun(): Save / Discard / Cancel for an action pane with changes.
    DismissibleDialog {
        id: _runGate
        onSaveChosen: {
            if (_root._saveChangedPanes())
                _root._closeActionPanesThenRun()
        }
        onDiscardChosen: _root._closeActionPanesThenRun()
    }

    // closeActionPanes(): Discard / Cancel for an action pane with changes.
    DismissibleDialog {
        id: _actionPaneGate
    }

    // Asks before a save leaves out unfinished actions (saveProfileChecked).
    DismissibleDialog {
        id: _unfinishedGate
    }

    // The profile used last didn't open at start: forget it, or keep it
    // (to fix the file, or plug in the drive it is on).
    DismissibleDialog {
        id: _lastProfileGate
    }

    DismissibleDialog {
        id: _saveResultDialog

        confirmText: "OK"
    }

    // 01 S143: opens in the last folder used for profiles.
    FilePicker {
        id: _saveProfileFileDialog
        kind: "profile"
        mode: "save"
        title: "Save Profile As"

        // Set by guardUnsavedChanges: runs after a successful save.
        property var afterSave: null
        // That follow-up is a quit: cancelling calls it off.
        property bool afterSaveQuitting: false

        acceptLabel: "Save"
        defaultSuffix: "xml"
        nameFilters: ["Profile files (*.xml)"]
        folder: backend ? backend.profilesFolderUrl() : ""

        onPicked: (file) => {
            if (!backend) {
                return
            }
            var next = afterSave
            var wasQuitting = afterSaveQuitting
            afterSave = null
            afterSaveQuitting = false
            saveProfileChecked(file, function(ok) {
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
        onCancelled: () => {
            var wasQuitting = afterSaveQuitting
            afterSave = null
            afterSaveQuitting = false
            if (wasQuitting)
                cancelQuitRequest()
        }
    }

    FilePicker {
        id: _loadProfileFileDialog
        kind: "profile"
        mode: "open"
        title: "Open Profile"

        acceptLabel: "Open"
        defaultSuffix: "xml"
        nameFilters: ["Profile files (*.xml)"]
        folder: backend ? backend.profilesFolderUrl() : ""

        onPicked: (file) => {
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
            ThemedMenuItem { command: "file.programFolder" }
            ThemedMenuItem { command: "file.dataFolder" }
            ThemedMenuSeparator {}
            ThemedMenuItem { command: "file.exit" }
        }

        ThemedMenu {
            title: qsTr("View")

            ThemedMenuItem { command: "view.home" }
            ThemedMenuItem { command: "view.deviceBindings" }
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
                ThemedMenuItem { command: "tools.inputTester" }
            }
            ThemedMenu {
                title: qsTr("Device Setup")
                ThemedMenuItem { command: "tools.calibration" }
                ThemedMenuItem { command: "tools.hidhide" }
                ThemedMenuItem { command: "tools.configureInput" }
                ThemedMenuItem { command: "tools.configureOutput" }
                ThemedMenuItem { command: "tools.deviceInfo" }
                ThemedMenuItem { command: "tools.deviceLibrary" }
                ThemedMenuItem { command: "tools.devicePack" }
            }
            ThemedMenu {
                title: qsTr("Mapping")
                ThemedMenuItem { command: "tools.logical" }
                ThemedMenuItem { command: "tools.deviceMappingEditor" }
                ThemedMenuItem { command: "tools.autoMappingTool" }
                ThemedMenuItem { command: "tools.manageModes" }
            }
            ThemedMenuSeparator {}
            ThemedMenuItem { command: "tools.oscMonitor" }
            ThemedMenuItem { command: "tools.history" }
            ThemedMenuItem { command: "tools.options" }
        }

        ThemedMenu {
            title: qsTr("Debug")

            ThemedMenuItem { command: "debug.liveLog" }
            ThemedMenuItem { command: "debug.tracing" }
        }

        ThemedMenu {
            title: qsTr("Help")

            ThemedMenuItem { command: "help.guide" }
            ThemedMenuItem { command: "help.updates" }
            ThemedMenuItem { command: "help.diagnostics" }
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

    header: ColumnLayout {
        spacing: 0

        ToolBar {
            id: _toolbar
            Layout.fillWidth: true

            // Scrolls sideways only when even the icons don't fit (a high UI
            // scale on a small screen), so every button stays reachable.
            Flickable {
                id: _toolbarFlick
                anchors.fill: parent
                implicitHeight: _toolbarRow.implicitHeight
                                + (_toolbarScroll.visible ? _toolbarScroll.height : 0)
                contentWidth: Math.max(width, Math.ceil(_root._toolbarWidth(false)))
                contentHeight: height
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentWidth > width
                clip: true

                ScrollBar.horizontal: ScrollBar {
                    id: _toolbarScroll
                    visible: _toolbarFlick.contentWidth > _toolbarFlick.width
                    policy: ScrollBar.AlwaysOn
                }

                RowLayout {
                    id: _toolbarRow
                    x: _homeButton.rightPadding + spacing + _toggleButton.sideSlack
                    // As wide as its buttons: they stay on the left with their
                    // usual gap (a full-width row would spread them out).
                    width: implicitWidth
                    height: implicitHeight
                    spacing: Style.dp(8)

                    JGToolButton {
                        id: _homeButton
                        compact: _root.toolbarCompact
                        text: "\uF425"
                        caption: "Home"
                        color: (!uiState || uiState.currentRoom === "status") ? Style.accent : Style.foreground
                        tooltip: qsTr("Home screen")

                        onClicked: () => { closeWorkRoom() }
                    }
                    JGToolButton {
                        id: _toggleButton
                        compact: _root.toolbarCompact
                        text: "\uF448"
                        // Glossary: Run / Stop.
                        caption: backend && backend.gremlinActive ? "Stop" : "Run"
                        color: backend && backend.gremlinActive ? Style.accent : Style.foreground
                        tooltip: backend && backend.gremlinActive ? qsTr("Stop the profile") : qsTr("Run the profile")

                        onClicked: () => { _root.toggleRun() }
                    }

                    JGToolButton {
                        id: _vjoyViewerButton
                        compact: _root.toolbarCompact
                        text: "\uF788"
                        tooltip: qsTr("Show or hide the vJoy Viewer")
                        caption: "vJoy Viewer"

                        onClicked: () => {
                            Helpers.toggleComponent("DialogInputViewer.qml")
                        }
                    }

                    // 01 S58 (D-01-INPUT-TESTER-BUTTON): starts the separate
                    // Input Tester, as Tools › Viewers › Input Tester… does.
                    JGToolButton {
                        id: _inputTesterButton
                        compact: _root.toolbarCompact
                        text: ""
                        tooltip: qsTr("Input Tester: see what other programs see through HidHide")
                        caption: "Input Tester"

                        onClicked: () => { openInputTester() }
                    }

                    JGToolButton {
                        id: _deviceMappingEditorButton
                        compact: _root.toolbarCompact
                        text: "\uF47F"
                        tooltip: qsTr("Device Mapping Editor: Open a blank device map")
                        caption: "Mapping Editor"

                        onClicked: () => { openBlankDeviceMappingEditor() }
                    }

                    // Every page (01 S58, 10 S2): the window on no device.
                    JGToolButton {
                        id: _deviceLibraryButton
                        compact: _root.toolbarCompact
                        text: "\uF447"
                        tooltip: qsTr("Every device and its saved setups")
                        caption: "Device Library"

                        onClicked: () => { _root.openDeviceLibrary("", "", "") }
                    }

                    JGToolButton {
                        id: _logicalButton
                        compact: _root.toolbarCompact
                        text: "\uF2D6"
                        caption: "Logical Device"
                        color: (uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "logical") ? Style.accent : Style.foreground
                        tooltip: qsTr("Open the Logical Device configuration")

                        onClicked: () => { openLogicalDevice() }
                    }

                    JGToolButton {
                        id: _optionsButton
                        compact: _root.toolbarCompact
                        text: "\uF3E5"
                        // Program-wide settings; the profile's own are its Profile Settings tab.
                        caption: "Options"
                        tooltip: qsTr("Options: settings for the whole program")

                        onClicked: () => {
                            Helpers.createComponent("DialogOptions.qml")
                        }
                    }
                }
            }
        }

        // Under the toolbar on every page (01 S58a): Mode, its list and
        // Manage Modes always on the left, a divider, then the open page's
        // own controls (its pageBar, if it has one).
        Item {
            id: _modeBar
            objectName: "modeBar"
            Layout.fillWidth: true
            implicitHeight: _modeBarRow.implicitHeight + Style.dp(12)

            RowLayout {
                id: _modeBarRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: Style.dp(12)
                anchors.rightMargin: Style.dp(12)
                anchors.verticalCenter: parent.verticalCenter
                spacing: Style.dp(8)

                    Label {
                        id: _modeLabel
                        Layout.rightMargin: Style.dp(10)

                        // One mode: the one you edit is the one that runs.
                        text: "Mode"
                    }

                    TooltipComboBox {
                        id: _modeSelector

                        // Narrows (down to its minimum) only when the toolbar is short of room.
                        Layout.fillWidth: true
                        Layout.preferredWidth: _root._modeListWidth
                        Layout.maximumWidth: _root._modeListWidth
                        Layout.minimumWidth: _root._modeListMinWidth
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
                        }
                    }

                    Button {
                        id: _manageModesButton
                        text: "Manage Modes"
                        Layout.rightMargin: Style.dp(10)
                        onClicked: () => {
                            Helpers.createComponent("DialogManageModes.qml")
                        }
                    }

                    Rectangle {
                        id: _modeBarDivider
                        objectName: "modeBarDivider"
                        Layout.preferredWidth: Style.dp(1)
                        Layout.fillHeight: true
                        Layout.rightMargin: Style.dp(10)
                        color: Style.line
                    }

                    // The page's own controls; they scroll sideways only
                    // when even the narrowed mode list leaves too little room,
                    // so the Mode group never moves.
                    Flickable {
                        id: _pageBarFlick
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        // Takes what the Mode group leaves; the mode list
                        // narrows first only when there is none.
                        Layout.preferredWidth: 0
                        implicitHeight: _pageBarLoader.implicitHeight
                                        + (_pageBarScroll.visible ? _pageBarScroll.height : 0)
                        contentWidth: Math.max(width, _pageBarLoader.implicitWidth)
                        contentHeight: height
                        flickableDirection: Flickable.HorizontalFlick
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentWidth > width
                        clip: true

                        ScrollBar.horizontal: ScrollBar {
                            id: _pageBarScroll
                            visible: _pageBarFlick.contentWidth > _pageBarFlick.width
                            policy: ScrollBar.AlwaysOn
                        }

                        Loader {
                            id: _pageBarLoader
                            objectName: "pageBarLoader"
                            width: _pageBarFlick.contentWidth
                            sourceComponent: _root.currentPageBar
                        }
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
                    show: _savedLine.text.length > 0
                }
            }
        }
    }

    BootstrapIcons {
        id: bsi
        resource: "qrc:///BootstrapIcons"
    }

    Connections {
        target: uiState

        function onDeviceChanged() {
            syncOutputView()
            Qt.callLater(_root.syncDeviceBindingsPage)
        }
        // The Device Bindings and Keyboard pages follow the mode themselves.
        function onModeChanged() {
            if (!uiState) {
                return
            }
            var logi = logicalPane()
            if (logi)
                logi.setMode(uiState.currentMode)
            var osc = oscPane()
            if (osc)
                osc.setMode(uiState.currentMode)
            _modeSelector.currentIndex = _modeSelector.find(uiState.currentMode)
        }
    }
    // backend.recentProfileFailed (B4's side of 04 Q15); ignored until the
    // backend has it.
    Connections {
        target: backend
        ignoreUnknownSignals: true
        function onRecentProfileFailed(path, why) { _root.offerForgetRecent(path, why) }
    }

    Connections {
        target: backend

        function onLastProfileFailed(path, why) {
            _lastProfileGate.confirmThen(
                "Last Profile Didn't Open",
                "The profile used last didn't open:\n" + path + "\n\n" + why
                + "\n\nA new, empty profile is open instead. Forget this profile, so it "
                + "isn't opened at start or listed under Recent? The file itself stays.",
                "Forget It",
                function() { backend.forgetProfile(path) })
            _lastProfileGate.cancelText = "Keep"
        }

        // Open action panes belong to the old profile; nothing unsaved is left by now.
        function onProfileChanged() {
            var pages = [_root.deviceBindingsPane(), _root.keyboardPane(),
                         _root.logicalPane(), _root.oscPane()]
            for (var i = 0; i < pages.length; ++i) {
                var pane = _root._paneOf(pages[i])
                if (pane && pane.closePaneNow)
                    pane.closePaneNow()
            }
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

        // Options' OSC line: OSC's Module Setup, as its card opens it
        // (D-09-OSC-FILE).
        function onOpenOscModuleSetup() {
            var card = _cardForGuid(uiState ? uiState.oscDeviceGuid : "")
            if (card && card.slug)
                _root.openConfigureModule("source", card)
        }

        // The OSC page's "Feedback settings…": OSC's Module Setup on that
        // tab (09 S154).
        function onOpenOscModuleSetupAt(tab) {
            onOpenOscModuleSetup()
            if (configureWin && configureWin.oscTab !== undefined) {
                configureWin.oscTab = ""
                configureWin.oscTab = String(tab || "")
            }
        }

        // OSC Setup's Feedback tab "Edit on the OSC page" (09 S154).
        function onOpenOscPage() {
            if (!uiState)
                return
            var card = _cardForGuid(uiState.oscDeviceGuid) || _moduleModel.cardMap("osc")
            if (card)
                _root.openDeviceBindingsForCard(card)
        }
    }

    onClosing: (close) => {
        _windowPlacement.save(_root)
        if (_quitting)
            return
        if (backend)
            backend.setRestartOnExit(false)
        if (updater)
            updater.setInstallOnExit(false)
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
        if (deviceMappingEditorNeedsLeave()) {
            offerDeviceMappingEditorLeaveThenQuit()
            close.accepted = false
            return
        }
        // Nothing to ask: the X quits the program, the same as File > Exit,
        // also while a tool window (they have no parent) is open (01 Q1).
        _quitting = true
        Qt.quit()
    }

    ColumnLayout {
        id: _columnLayout

        anchors.fill: parent

        property bool onStatus: !uiState || uiState.currentRoom === "status"

        Connections {
            target: _moduleModel
            function onClaimsChanged() { refreshDestBound() }
            function onTargetsChanged() { refreshDestBound() }
            function onNamesChanged() { _root.namesRev++ }
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
                onOpenDeviceBindings: function(card) {
                    openDeviceBindingsForCard(card)
                }
                onOpenDeviceMappingEditor: function(card) {
                    openDeviceMappingEditorForCard(card)
                }
                onOpenOutputView: function(card) {
                    openOutputViewForCard(card)
                }
                onConfigureModule: function(card) {
                    // The Xbox card's item is Xbox Setup… (D-XBOX-PADS).
                    if (card && (card.bus === "XInput" || card.tab === "xbox" || card.slug === "xbox"))
                        openXboxSetup()
                    else
                        openConfigureModule(card.direction === "dest" ? "dest" : "source", card)
                }
                onOpenAutoMappingTool: function(card) {
                    Helpers.createComponent("DialogAutoMappingTool.qml", {
                        // The card's device folder (found by its id), as the
                        // window's list names it; card.slug is its card key.
                        "initialSlug": String(_moduleModel.moduleFileFor(card.guid || "",
                                card.rawName || card.name || "") || card.slug || "")
                    })
                }
                onOpenPairing: function(card) {
                    pairingForCard(card)
                }
                onOpenCalibration: function(card) {
                    Helpers.createComponent("DialogCalibration.qml", {
                        // The card's device folder (found by its id), as the
                        // window's list names it; card.slug is its card key.
                        "initialSlug": String(_moduleModel.moduleFileFor(card.guid || "",
                                card.rawName || card.name || "") || card.slug || "")
                    })
                }
                onOpenDeviceInformation: function(card) {
                    Helpers.createComponent("DialogDeviceInformation.qml", {"initialGuid": card.guid || ""})
                }
                // The card menu's Copy / Swap / Change vJoy Output (10 S2,
                // 03 S88).
                onOpenDeviceLibrary: function(card, action) {
                    // _root's function: here a bare openDeviceLibrary is this
                    // page's own signal, which would fire itself.
                    _root.openDeviceLibrary(card ? String(card.rawName || card.name || "") : "",
                                      card ? String(card.guid || "") : "", action)
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
                            text: "Output View"
                            font.pixelSize: Style.dp(22)
                            font.bold: true
                        }
                        Label {
                            visible: configDirection !== "dest" && configDirection !== "logical"
                            text: "Device Bindings"
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
                            visible: configDirection !== ""
                            enabled: (configDirection === "dest" ? _root.destModuleCount : _root.sourceModuleCount) > 1
                            opacity: enabled ? 1 : 0.35
                            onClicked: configDirection === "dest" ? _root.cycleOutput(-1) : _root.cycleDeviceBindings(-1)
                            PointerTip {
                                text: configDirection === "dest" ? "Previous output module" : "Previous input module"
                                show: true
                            }
                        }
                        IconButton {
                            text: "\uF285"
                            font.pixelSize: Style.dp(18)
                            visible: configDirection !== ""
                            enabled: (configDirection === "dest" ? _root.destModuleCount : _root.sourceModuleCount) > 1
                            opacity: enabled ? 1 : 0.35
                            onClicked: configDirection === "dest" ? _root.cycleOutput(1) : _root.cycleDeviceBindings(1)
                            PointerTip {
                                text: configDirection === "dest" ? "Next output module" : "Next input module"
                                show: true
                            }
                        }
                        Label {
                            id: _configTitle
                            visible: configDirection !== "logical"
                            // The user's name for the device (10 S7).
                            text: configTitleName.length ? _root.configTitleShown() : "device"
                            font.pixelSize: Style.dp(22)
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                    Label {
                        id: _destBound
                        objectName: "destBound"
                        visible: configDirection === "dest"
                        text: "Driven by: [nothing]"
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    // OSC's full name under its title (D-09-OSC-CARD-LINE).
                    Label {
                        objectName: "oscFullName"
                        visible: configDirection === "source" && !!uiState
                                 && uiState.currentTab === "osc"
                        text: "Open Sound Control (OSC)"
                        color: Style.fgMuted
                        font.pixelSize: Style.dp(12)
                        Layout.fillWidth: true
                    }
                }
                // Not on the Xbox page: its list has its own Appearance
                // button on the page bar (XboxDevice.qml pageBar, 03 S139).
                Button {
                    objectName: "outputAppearanceButton"
                    visible: configDirection === "dest" && !(uiState && uiState.currentTab === "xbox")
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
                target: _root._paneOf(_logicalLoader.item)
                ignoreUnknownSignals: true
                function onLeaveResolved() { _root.continueDisplayLeave() }
                function onLeaveCancelled() { _root.cancelDisplayLeave() }
            }
        }

        // The OSC page (09 S129): built like the Logical Device page.
        Loader {
            id: _oscPageLoader

            Layout.fillHeight: true
            Layout.fillWidth: true
            active: uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "osc"
                    && _root.configDirection !== "dest"
                    && _root._configLive
            visible: active
            source: "OscPage.qml"
            onLoaded: {
                if (uiState)
                    item.setMode(uiState.currentMode)
                if (_root._oscMonitorWanted) {
                    _root._oscMonitorWanted = false
                    item.showMonitor()
                }
            }

            Connections {
                target: _root._paneOf(_oscPageLoader.item)
                ignoreUnknownSignals: true
                function onLeaveResolved() { _root.continueDisplayLeave() }
                function onLeaveCancelled() { _root.cancelDisplayLeave() }
            }
        }

        // The joystick Device Bindings page (05 S121-S131): built like the
        // Logical Device page.
        Loader {
            id: _deviceBindingsPageLoader

            Layout.fillHeight: true
            Layout.fillWidth: true
            active: uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "physical"
                    && _root.configDirection !== "dest"
                    && _root._configLive
            visible: active
            source: "DeviceBindingsPage.qml"
            onLoaded: _root.syncDeviceBindingsPage()

            Connections {
                target: _root._paneOf(_deviceBindingsPageLoader.item)
                ignoreUnknownSignals: true
                function onLeaveResolved() { _root.continueDisplayLeave() }
                function onLeaveCancelled() { _root.cancelDisplayLeave() }
            }
        }

        // The Keyboard page (CF-Q7): the same layout.
        Loader {
            id: _keyboardPageLoader

            Layout.fillHeight: true
            Layout.fillWidth: true
            active: uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "keyboard"
                    && _root.configDirection !== "dest"
                    && _root._configLive
            visible: active
            source: "KeyboardPage.qml"

            Connections {
                target: _root._paneOf(_keyboardPageLoader.item)
                ignoreUnknownSignals: true
                function onLeaveResolved() { _root.continueDisplayLeave() }
                function onLeaveCancelled() { _root.cancelDisplayLeave() }
            }
        }

        Loader {
            id: _xboxLoader

            Layout.fillHeight: true
            Layout.fillWidth: true
            active: uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "xbox"
                    && _root._configLive
            visible: active
            sourceComponent: XboxDevice {}
        }
        // The Xbox Output View's "Open Xbox Setup" (D-XBOX-PADS).
        Connections {
            target: _xboxLoader.item
            function onXboxSetupRequested() { _root.openXboxSetup() }
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
}
