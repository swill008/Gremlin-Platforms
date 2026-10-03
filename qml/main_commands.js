// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The main window's commands (Gremlin.Menus commands.js): each one defined
// once, with its name, shortcut and when it can be used. The menu bar, the
// shortcuts and the command palette are built from this list.
// Code-behind for Main.qml (imported without .pragma library): it uses the
// window's ids and functions directly.

function _room() {
    return uiState ? String(uiState.currentRoom || "") : ""
}

function _openRoom(room) {
    leaveDisplayThen(function() {
        if (uiState) {
            uiState.setCurrentRoom(room)
            uiState.setCurrentTab(room)
        }
    })
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
        { id: "file.exit", text: "Exit", group: "File", keywords: "quit close",
          run: function() { quitGremlin() } },

        // View
        { id: "view.home", text: "Home", group: "View", keywords: "devices cards status",
          enabled: function() { return _room() !== "status" },
          run: function() { closeWorkRoom() } },
        { id: "view.configuration", text: "Configuration", group: "View", keywords: "bindings",
          run: function() { openConfigurationForFocus() } },
        { id: "view.layout.single", text: "Single List", group: "View › Home layout",
          checked: _layout("none"), run: function() { _moduleModel.setSplitMode("none") } },
        { id: "view.layout.side", text: "Side by Side", group: "View › Home layout",
          checked: _layout("vertical"), run: function() { _moduleModel.setSplitMode("vertical") } },
        { id: "view.layout.stacked", text: "Stacked", group: "View › Home layout",
          checked: _layout("horizontal"), run: function() { _moduleModel.setSplitMode("horizontal") } },
        { id: "view.hidden", text: "Hidden Cards…", group: "View", keywords: "unhide",
          enabled: function() { return _moduleModel.hiddenList().length > 0 },
          run: function() { openHiddenDevices() } },
        { id: "view.scripts", text: "Scripts", group: "View",
          enabled: function() { return _room() !== "scripts" },
          run: function() { _openRoom("scripts") } },
        { id: "view.settings", text: "Profile Settings", group: "View",
          enabled: function() { return _room() !== "settings" },
          run: function() { _openRoom("settings") } },
        { id: "view.palette", text: "Command Palette…", group: "View", shortcut: "Ctrl+K",
          palette: false, run: function() { _commandPalette.open() } },

        // Tools
        { id: "tools.vjoyViewer", text: "vJoy Viewer", group: "Tools › Viewers",
          run: function() { toggleTool("DialogInputViewer.qml") } },
        { id: "tools.xboxViewer", text: "Xbox Viewer", group: "Tools › Viewers",
          run: function() { toggleTool("DialogXboxViewer.qml") } },
        { id: "tools.calibration", text: "Calibration", group: "Tools › Device setup",
          run: function() { openTool("DialogCalibration.qml") } },
        { id: "tools.hidhide", text: "HidHide", group: "Tools › Device setup", keywords: "hide devices",
          run: function() { openTool("DialogHardwareHide.qml") } },
        { id: "tools.configureInput", text: "Input Module Setup", group: "Tools › Device setup",
          run: function() { openConfigureModule("source") } },
        { id: "tools.configureOutput", text: "Output Module Setup", group: "Tools › Device setup",
          run: function() { openConfigureModule("dest") } },
        { id: "tools.deviceInfo", text: "Device Information", group: "Tools › Device setup",
          run: function() { openTool("DialogDeviceInformation.qml") } },
        { id: "tools.swapDevices", text: "Swap Devices", group: "Tools › Device setup",
          run: function() { openTool("DialogSwapDevices.qml") } },
        { id: "tools.devicePack", text: "Device Pack", group: "Tools › Device setup",
          run: function() { openTool("DialogDevicePack.qml") } },
        { id: "tools.logical", text: "Logical Device", group: "Tools › Mapping",
          enabled: function() {
              return !(uiState && uiState.currentRoom === "configuration" && uiState.currentTab === "logical")
          },
          run: function() { openLogicalDevice() } },
        { id: "tools.buttonMap", text: "Button Map", group: "Tools › Mapping",
          run: function() { openBlankButtonMap() } },
        { id: "tools.autoMapper", text: "Auto Mapper", group: "Tools › Mapping",
          run: function() { openTool("DialogAutoMapper.qml") } },
        { id: "tools.manageModes", text: "Manage Modes", group: "Tools › Mapping",
          run: function() { openTool("DialogManageModes.qml") } },
        { id: "tools.options", text: "Options", group: "Tools", keywords: "settings preferences",
          run: function() { openTool("DialogOptions.qml") } },

        // Debug
        { id: "debug.liveLog", text: "Live Log Reader", group: "Debug",
          run: function() { openTool("DialogLiveLog.qml") } },

        // Help
        { id: "help.guide", text: "User Guide", group: "Help", shortcut: "F1",
          run: function() { openTool("DialogHelp.qml") } },
        { id: "help.updates", text: "Check for Updates", group: "Help",
          run: function() {
              openTool("DialogUpdate.qml")
              if (updater && updater.state !== "downloading" && updater.state !== "ready")
                  updater.check(true)
          } },
        { id: "help.about", text: "About", group: "Help",
          run: function() { openTool("DialogAbout.qml") } }
    ]
}
