// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Options and profile (Options, Profile Settings, Scripts).

.pragma library

var chapter = { id: "options-profile", title: "Options and profile" }

function topics() {
    return [
        {
            id: "options-profile-options",
            section: "Options",
            title: "Options",
            body: "<p>Options holds the program's settings, which are not stored in the profile. The profile's own settings are in <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>.</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b> (or <b>Options</b> on the toolbar).</li>"
                + "<li>Pick a section on the left, or type in <b>Search options</b> to find a setting in any section.</li>"
                + "</ol>"
                + "<ul>"
                + "<li><b>General</b>: <b>Startup and Tray</b>, <b>Devices</b>, <b>Diagnostics</b> and <b>History</b> (see <a href=\"topic:options-profile-general\">General options</a>).</li>"
                + "<li><b>Interface</b>: <b>Display</b> (Dark mode, UI scale, Ignore Windows display scaling) and <b>Inputs</b> (Input names, Input highlighting, which stays on the device page you have open, and Action details).</li>"
                + "<li><b>Actions</b>: the <b>Add Action Menu</b> (which actions it offers and their order), then Macro, Change Mode, Double Tap, Smart Toggle, Tempo, Axis Delta, Play Sound and Text to Speech.</li>"
                + "<li><b>Profiles</b>: <b>Auto-load</b>: Load profiles automatically when a chosen program starts, the programs and their profiles, and Keep running when the program loses focus.</li>"
                + "<li><b>Home</b>: <b>Cards</b>: Compact view, Show devices without a module, Keep last value after release, and <b>Reset All Card Sizes</b>.</li>"
                + "<li><b>OSC</b>: <b>Connection</b> (Enabled, Input host and port, Output address) and <b>Messages</b> (auto-release of address-only messages, the delay presets, and treating address-only messages as 1.0).</li>"
                + "<li><b>Folders</b>: the data folder, and the profiles, modules, scripts, export, logs, history and plugins folders. <b>Select</b> picks another folder; <b>Reset</b> puts the default back.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The Device Library's folder is in Device Library Settings.</li>"
                + "<li>The Button Map's settings are in the Button Map: <b>Edit</b> › <b>Button Map Options…</b>.</li>"
                + "</ul>",
            related: ["options-profile-general", "options-profile-profile-settings", "getting-started-saved-where"]
        },
        {
            id: "options-profile-general",
            section: "Options",
            title: "General options",
            body: "<p>The <b>General</b> section of Options covers startup, devices, diagnostics and History.</p>"
                + "<ul>"
                + "<li><b>Startup and Tray</b>: <b>Check for updates</b>; <b>Minimize to tray</b>, where minimizing or closing the window keeps the program running in the tray (exit from <b>File › Exit</b> or the tray menu); and <b>HidHide</b>, a pointer: to turn HidHide on each time the program starts, use <b>Automatically Start</b> in <b>Tools › Device Setup › HidHide</b>.</li>"
                + "<li><b>Devices</b>: <b>Device change behavior</b> (Stop, Ignore, or Reload); <b>Refresh axes when Run starts</b> and on mode change. An axis not moved since the program started is sent as center until it moves.</li>"
                + "<li><b>Diagnostics</b>: <b>Diagnostic logs</b> and <b>Log When Not Responding</b>.</li>"
                + "<li><b>History</b>: <b>Days to keep changes</b> and <b>Largest history file (MB)</b>.</li>"
                + "</ul>",
            related: ["options-profile-options", "getting-started-install", "tools-hidhide", "tools-history"]
        },
        {
            id: "options-profile-profile-settings",
            section: "Profile",
            title: "Profile Settings",
            body: "<p><b>View › Profile Settings</b> holds the settings stored in the profile. Save the profile to keep them.</p>"
                + "<ul>"
                + "<li><b>Startup Mode</b>: the mode the profile is in when it is loaded, including when a program auto-loads it. <b>Last Active</b> (the usual choice) opens the mode the profile last ran in; a profile with no last mode yet (new, moved, renamed or never run) opens in the top mode of the Manage Modes list. A mode by name always opens that mode.</li>"
                + "<li><b>Macro Default Delay</b>: the pause between macro steps.</li>"
                + "<li><b>vJoy Behavior</b>: treat each vJoy device as an output (default) or as an input.</li>"
                + "<li><b>vJoy Initial Values</b>: axis values set when the profile starts.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li><b>Run</b> starts in the mode shown in the <b>Mode</b> box, so change it there to start somewhere else (see <a href=\"topic:modes-mode-box\">Choose the mode you edit and run</a>).</li></ul>",
            related: ["modes-mode-box", "modes-manage", "getting-started-profiles"]
        },
        {
            id: "options-profile-scripts",
            section: "Profile",
            title: "Add scripts to a profile",
            body: "<p>Scripts are Python files that run with the profile. They are saved with the profile.</p>"
                + "<ol>"
                + "<li>Choose <b>View › Scripts</b>.</li>"
                + "<li>Choose <b>Add Script</b> and pick a .py file.</li>"
                + "<li>Rename the script and set its variables on that page, if you like.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li>A script's vjoy object can only use outputs the vJoy output modules claim.</li></ul>",
            related: ["getting-started-profiles", "home-devices-vjoy-output"]
        },

        {
            id: "options-profile-q-find-setting",
            section: "Common questions",
            title: "How do I find a setting?",
            body: "<p>Type part of its name in <b>Search options</b>. See <a href=\"topic:options-profile-options\">Options</a>.</p>",
            related: ["options-profile-options"]
        },
        {
            id: "options-profile-q-tray",
            section: "Common questions",
            title: "How do I keep the program running when I close the window?",
            body: "<p>Turn on <b>Minimize to tray</b>. See <a href=\"topic:options-profile-general\">General options</a>.</p>",
            related: ["options-profile-general"]
        },
        {
            id: "options-profile-q-settings-lost",
            section: "Common questions",
            title: "Why did my Profile Settings not stay?",
            body: "<p>Profile Settings are stored in the profile; save the profile to keep them. See <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>.</p>",
            related: ["options-profile-profile-settings", "getting-started-saved-where"]
        }
    ]
}
