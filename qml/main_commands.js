// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The main window's commands (Gremlin.Menus commands.js): each one defined
// once, with its name, shortcut and when it can be used. The menu bar, the
// shortcuts and the command palette are built from this list. window: true
// marks a command that opens a window of its own (not a page of this one);
// the control API's window.open needs it (13 S29).
// Code-behind for Main.qml (imported without .pragma library): it uses the
// window's ids and functions directly.

function _room() {
    return uiState ? String(uiState.currentRoom || "") : ""
}

function _layout(mode) {
    return function() { return _moduleModel.splitMode === mode }
}

function commandList() {
    return [
        // File
        { id: "file.new", text: "New Profile", group: "File", shortcut: "Ctrl+N",
          run: function() { requestNewProfile() } },
        { id: "file.load", text: "Load Profile…", group: "File", shortcut: "Ctrl+O",
          keywords: "open", run: function() { _loadProfileFileDialog.open() } },
        { id: "file.save", text: "Save Profile", group: "File", shortcut: "Ctrl+S",
          run: function() { saveCurrentProfile() } },
        { id: "file.saveAs", text: "Save Profile As…", group: "File", shortcut: "Ctrl+Shift+S",
          run: function() { openSaveAs() } },
        { id: "file.programFolder", text: "Open Program Folder", group: "File",
          keywords: "install explorer", run: function() { backend.openProgramFolder() } },
        { id: "file.dataFolder", text: "Open Data Folder", group: "File",
          keywords: "profiles modules settings user explorer",
          run: function() { backend.openDataFolder() } },
        { id: "file.exit", text: "Exit", group: "File", keywords: "quit close",
          run: function() { quitGremlin() } },

        // View
        { id: "view.home", text: "Home", group: "View", keywords: "devices cards status",
          enabled: function() { return _room() !== "status" },
          run: function() { closeWorkRoom() } },
        { id: "view.deviceBindings", text: "Device Bindings", group: "View", keywords: "bindings configuration actions",
          run: function() { openDeviceBindingsForFocus() } },
        { id: "view.layout.single", text: "Single list", group: "View › Home Layout",
          checked: _layout("none"), run: function() { _moduleModel.setSplitMode("none") } },
        { id: "view.layout.side", text: "Side by side", group: "View › Home Layout",
          checked: _layout("vertical"), run: function() { _moduleModel.setSplitMode("vertical") } },
        { id: "view.layout.stacked", text: "Stacked", group: "View › Home Layout",
          checked: _layout("horizontal"), run: function() { _moduleModel.setSplitMode("horizontal") } },
        // The Xbox output's Output View (live pads and its controls); Help's
        // Open links use it. Not a menu item or a palette entry.
        { id: "view.xboxOutput", text: "Xbox Output View", group: "View",
          palette: false, menu: false, run: function() { openXboxOutputView() } },
        { id: "view.palette", text: "Command Palette…", group: "View", shortcut: "Ctrl+K",
          palette: false, run: function() { _commandPalette.open() } },

        // Tools
        { id: "tools.vjoyViewer", text: "vJoy Viewer", group: "Tools › Viewers", window: true,
          run: function() { openTool("DialogInputViewer.qml") } },
        // The Input Tester (D-02-INPUT-TESTER): what a game sees through HidHide.
        { id: "tools.inputTester", text: "Input Tester…", group: "Tools › Viewers",
          keywords: "hidhide game sees hidden visible check test devices",
          run: function() { openInputTester() } },
        { id: "tools.calibration", text: "Calibration", group: "Tools › Device Setup", window: true,
          run: function() { openTool("DialogCalibration.qml") } },
        { id: "tools.hidhide", text: "HidHide", group: "Tools › Device Setup", window: true, keywords: "hide devices",
          run: function() { openTool("DialogHardwareHide.qml") } },
        // Xbox Setup (D-XBOX-PADS): the ViGEmBus check and how many Xbox
        // pads are on. Its menu place is the Xbox card's menu.
        { id: "tools.xboxSetup", text: "Xbox Setup…", group: "Tools › Device Setup", window: true,
          keywords: "xbox pads vigem vigembus driver controllers count",
          menu: false, run: function() { openXboxSetup() } },
        // Drivers (06 S185, D-06-DRIVERS): install, update and set up vJoy,
        // ViGEmBus and HidHide through Gremlin Device Helper.
        { id: "tools.drivers", text: "Drivers…", group: "Tools", window: true,
          keywords: "vjoy vigembus hidhide driver install update",
          run: function() { openDrivers() } },
        { id: "tools.configureInput", text: "Input Module Setup", group: "Tools › Device Setup", window: true,
          run: function() { openConfigureModule("source") } },
        { id: "tools.configureOutput", text: "Output Module Setup", group: "Tools › Device Setup", window: true,
          run: function() { openConfigureModule("dest") } },
        { id: "tools.deviceInfo", text: "Device Information", group: "Tools › Device Setup", window: true,
          run: function() { openTool("DialogDeviceInformation.qml") } },
        // The Device Library (10 S2): every device and its saved setups.
        { id: "tools.deviceLibrary", text: "Device Library…", group: "Tools › Device Setup", window: true,
          keywords: "saved setup autosave copy swap change vjoy output replace stick",
          run: function() { openDeviceLibrary("", "", "") } },
        // Export / Import Device (08 S111, D-FIXLIST-B2): one window for
        // .gmap files; from here it opens on its Export tab.
        { id: "tools.devicePack", text: "Export / Import Device", group: "Tools › Device Setup", window: true,
          run: function() { openToolWith("DialogDevicePack.qml", { mode: "export" }) } },
        { id: "tools.logical", text: "Logical Device", group: "Tools › Mapping",
          enabled: function() {
              return !(uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "logical")
          },
          run: function() { openLogicalDevice() } },
        { id: "tools.deviceMappingEditor", text: "Device Mapping Editor", group: "Tools › Mapping", window: true,
          run: function() { openBlankDeviceMappingEditor() } },
        { id: "tools.autoMappingTool", text: "Auto Mapping Tool", group: "Tools › Mapping", window: true,
          run: function() { openTool("DialogAutoMappingTool.qml") } },
        { id: "tools.manageModes", text: "Manage Modes", group: "Tools › Mapping", window: true,
          run: function() { openTool("DialogManageModes.qml") } },
        // Search (D-01-SEARCH): every use of an input, output, mode or action type.
        { id: "tools.search", text: "Search…", group: "Tools › Mapping", window: true, shortcut: "Ctrl+Shift+F",
          keywords: "search find index type key keys action name profile profiles uses where used vjoy xbox osc mouse mode device listen",
          run: function() { openSearch(null) } },
        // Health (01 S197, D-01-HEALTH): bindings with a problem, why, and the fix.
        { id: "tools.health", text: "Health…", group: "Tools › Mapping", window: true,
          keywords: "health problems broken missing not found used twice no bindings not plugged unplugged vjoy check fix",
          run: function() { openTool("DialogHealth.qml") } },
        // The OSC Monitor (D-09-OSC-MONITOR, 09 S138): the OSC page with
        // its Monitor shown.
        { id: "tools.oscMonitor", text: "OSC Monitor", group: "Tools",
          keywords: "osc messages traffic network incoming outgoing",
          run: function() { openOscMonitor() } },
        // Screen Saver Mode (12 S1): Gremlin's own keyboard-and-mouse idle
        // clock that starts the screen saver or powers off the displays.
        { id: "tools.screenSaverMode", text: "Screen Saver Mode…", group: "Tools", window: true,
          keywords: "screen saver idle display off power oled burn-in awake monitor sleep",
          run: function() { openTool("WindowScreenSaverMode.qml") } },
        { id: "tools.history", text: "History", group: "Tools", window: true,
          keywords: "undo restore versions changes saved",
          run: function() { openToolWith("DialogHistory.qml", { filter: "" }) } },
        { id: "tools.options", text: "Options", group: "Tools", window: true, keywords: "settings preferences profile macro startup mode vjoy scripts",
          run: function() { openTool("DialogOptions.qml") } },

        // Debug
        { id: "debug.liveLog", text: "Live Log Reader", group: "Debug", window: true,
          run: function() { openTool("DialogLiveLog.qml") } },
        // Control tracing (D-01-TRACE): the same switch as the Live Log
        // Reader's Trace tab; it keeps running with the window closed.
        { id: "debug.tracing", text: "Tracing", group: "Debug",
          keywords: "trace controls stick vjoy hidhide out of step",
          checked: function() { return _tracing.on },
          run: function() { _tracing.toggle() } },
        // The main window's state to system.log (01 S178): changes nothing.
        { id: "debug.saveWindowState", text: "Save Window State", group: "Debug",
          keywords: "window tray pages blank state trace",
          run: function() {
              if (typeof windowTrace !== "undefined" && windowTrace)
                  windowTrace.saveWindowState()
          } },

        // Help
        { id: "help.guide", text: "Help", group: "Help", window: true, shortcut: "F1",
          run: function() { openToolWith("DialogHelp.qml", { chapter: "" }) } },
        { id: "help.updates", text: "Check for Updates", group: "Help", window: true,
          run: function() {
              openTool("DialogUpdate.qml")
              if (updater && updater.state !== "downloading" && updater.state !== "ready")
                  updater.check(true)
          } },
        { id: "help.whatsNew", text: "What's New…", group: "Help", window: true,
          keywords: "release notes changes version",
          run: function() {
              if (whatsNew)
                  whatsNew.showCurrentNotes()
              openTool("WindowWhatsNew.qml")
          } },
        { id: "help.diagnostics", text: "Save Diagnostics…", group: "Help", window: true,
          keywords: "zip logs report problem support",
          run: function() { openTool("DialogSaveDiagnostics.qml") } },
        { id: "help.about", text: "About", group: "Help", window: true,
          run: function() { openTool("DialogAbout.qml") } }
    ]
}
