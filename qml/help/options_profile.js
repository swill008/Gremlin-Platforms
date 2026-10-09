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
                + "<li>Choose <b>Tools › Options</b> <a href=\"open:tools.options\">Open ›</a> (or <b>Options</b> on the toolbar).</li>"
                + "<li>Pick a section on the left, or type in <b>Search options</b> (<b>Ctrl+F</b>) to find a setting in any section. The line under the box says \"N found\" or \"Nothing matches\".</li>"
                + "</ol>"
                + "<ul>"
                + "<li><b>General</b>: <b>Startup and Tray</b>, <b>Devices</b>, <b>Diagnostics</b> and <b>History</b> (see <a href=\"topic:options-profile-general\">General options</a>).</li>"
                + "<li><b>Interface</b>: <b>Display</b> (Dark mode, UI scale, Ignore Windows display scaling) and <b>Inputs</b> (Input names, Input highlighting, which stays on the device page you have open, and Action details). See <a href=\"topic:options-profile-interface\">Interface options</a>.</li>"
                + "<li><b>Actions</b>: the <b>Add Action Menu</b> (which actions it offers and their order), then Macro, Change Mode, Double Tap, Smart Toggle, Tempo, Axis Delta, Play Sound and Text to Speech.</li>"
                + "<li><b>Profiles</b>: <b>Auto-load</b>: Load profiles automatically when a chosen program comes to the front, the programs and their profiles, and Keep running when the program loses focus. See <a href=\"topic:options-profile-auto-load\">Load a profile automatically for a game</a>.</li>"
                + "<li><b>Home</b>: <b>Cards</b>: Compact view, Show devices without a module, Keep last value after release, and <b>Reset All Card Sizes</b>.</li>"
                + "<li><b>OSC</b>: <b>Connection</b> (Enabled, Input host and port, Output address) and <b>Messages</b> (auto-release of address-only messages, the delay presets, and treating address-only messages as 1.0). See <a href=\"topic:options-profile-osc\">OSC options</a>.</li>"
                + "<li><b>Folders</b>: the data folder, and the profiles, modules, scripts, export, logs, history and plugins folders. See <a href=\"topic:options-profile-folders\">Change where files are kept</a>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>× in the search box clears it; <b>Esc</b> clears the typing and leaves the box.</li>"
                + "<li>The Device Library's folder is in Device Library Settings.</li>"
                + "<li>The Button Map's settings are in the Button Map: <b>Edit</b> › <b>Button Map Options…</b>.</li>"
                + "</ul>",
            related: ["options-profile-general", "options-profile-interface", "options-profile-profile-settings", "getting-started-saved-where"]
        },
        {
            id: "options-profile-general",
            section: "Options",
            title: "General options",
            body: "<p>The <b>General</b> section of Options covers startup, devices, diagnostics and History.</p>"
                + "<ul>"
                + "<li><b>Startup and Tray</b>: <b>Check for updates</b>; <b>Minimize to tray</b> <a href=\"show:option/Minimize to tray\">Show me ›</a>, where minimizing or closing the window keeps the program running in the tray (see <a href=\"topic:options-profile-tray\">Keep the program running in the tray</a>); and <b>HidHide</b>, a pointer: to turn HidHide on each time the program starts, use <b>Automatically Start</b> in <b>Tools › Device Setup › HidHide</b>.</li>"
                + "<li><b>Devices</b>: <b>Device change behavior</b> <a href=\"show:option/Device change behavior\">Show me ›</a> (Stop, Ignore, or Reload); <b>Refresh axes when Run starts</b> and on mode change. An axis not moved since the program started is sent as center until it moves.</li>"
                + "<li><b>Diagnostics</b>: <b>Diagnostic logs</b> and <b>Log When Not Responding</b>. See <a href=\"topic:options-profile-diagnostics\">Diagnostic logs</a>.</li>"
                + "<li><b>History</b>: <b>Days to keep changes</b> and <b>Largest history file (MB)</b>.</li>"
                + "</ul>",
            related: ["options-profile-options", "options-profile-tray", "tools-hidhide", "tools-history"]
        },
        {
            id: "options-profile-tray",
            section: "Options",
            title: "Keep the program running in the tray",
            body: "<p>With <b>Minimize to tray</b> on, the program keeps running in the Windows system tray when you minimize or close its window. It is off at first.</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>General</b>.</li>"
                + "<li>Under <b>Startup and Tray</b>, turn on <b>Minimize to tray</b> <a href=\"show:option/Minimize to tray\">Show me ›</a>.</li>"
                + "</ol>"
                + "<p>The tray icon:</p>"
                + "<ul>"
                + "<li>Shows one picture while the profile is stopped and another while it runs. Its tooltip is \"Gremlin-Platforms\".</li>"
                + "<li>A left click brings the window back as it was: windowed, maximized or full screen.</li>"
                + "<li>A right click opens its menu: <b>Show Gremlin-Platforms</b> or <b>Hide Gremlin-Platforms</b>, <b>Run Profile</b> or <b>Stop Profile</b>, and <b>Exit Gremlin-Platforms</b>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The first time the window's X hides it, a tray notice says \"Gremlin-Platforms is still running\". It shows only once.</li>"
                + "<li>To quit, choose <b>File › Exit</b> or <b>Exit Gremlin-Platforms</b> in the tray menu. Exit from the tray brings the window back first, so you can answer any question about unsaved changes.</li>"
                + "<li>While the window is in the tray, the program closes its pages to give memory back to Windows, and opens them again when you show the window. The profile keeps running the whole time. The Configuration page stays open while it has unsaved display edits.</li>"
                + "<li>The tray icon comes back by itself if Windows Explorer restarts.</li>"
                + "<li>To start the program straight into the tray, use the --start-minimized option with Minimize to tray on. See <a href=\"topic:getting-started-command-line\">Start the program from a command line</a>.</li>"
                + "</ul>",
            related: ["options-profile-general", "getting-started-command-line", "getting-started-run"]
        },
        {
            id: "options-profile-interface",
            section: "Options",
            title: "Interface options",
            body: "<p>The <b>Interface</b> section of Options sets how the program looks and how inputs are named.</p>"
                + "<ul>"
                + "<li><b>Dark mode</b> <a href=\"show:option/Dark mode\">Show me ›</a>: applies at once in every window.</li>"
                + "<li><b>UI scale</b> and <b>Ignore Windows display scaling</b>: the size of the program. See <a href=\"topic:options-profile-ui-scale\">Change the size of the program</a>.</li>"
                + "<li><b>Input names</b> <a href=\"show:option/Input names\">Show me ›</a>: <b>Numerical</b> (\"Axis 3\"), <b>Label</b> (the name the program knows for that control on your device model), or <b>Numerical and Label</b> (both, the usual choice). A control with no known label always shows its number name.</li>"
                + "<li><b>Input highlighting</b>: using a control on a device selects its input on screen, when that device's page is the one you have open.</li>"
                + "<li><b>Action details</b>: how each input's actions are shown, <b>Full</b> or <b>Count</b>.</li>"
                + "</ul>",
            related: ["options-profile-ui-scale", "options-profile-options"]
        },
        {
            id: "options-profile-ui-scale",
            section: "Options",
            title: "Change the size of the program",
            body: "<p>The program follows the Windows display scale. To choose its size yourself, turn Windows scaling off for it.</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>Interface</b>.</li>"
                + "<li>Turn on <b>Ignore Windows display scaling</b> <a href=\"show:option/Ignore Windows display scaling\">Show me ›</a>.</li>"
                + "<li>In <b>Restart Required</b>, choose <b>Restart</b> to restart now, <b>Later</b> to use it at the next start, or <b>Cancel</b> to undo the change.</li>"
                + "<li>Drag <b>UI scale</b> <a href=\"show:option/UI scale\">Show me ›</a> to a size from 70% to 200%, in steps of 5. The program resizes when you let go of the slider; no restart is needed.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>While Windows scaling is on, the <b>UI scale</b> slider is off and stays at 100%.</li>"
                + "<li>Turning <b>Ignore Windows display scaling</b> off again asks the same question.</li>"
                + "</ul>",
            related: ["options-profile-interface", "options-profile-options"]
        },
        {
            id: "options-profile-add-action-menu",
            section: "Options",
            title: "Choose the actions you can add",
            body: "<p>The <b>Add Action Menu</b> in Options sets which actions the add-action menus offer, and in what order.</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>Actions</b>.</li>"
                + "<li>Under <b>Actions offered</b> <a href=\"show:option/Actions offered\">Show me ›</a>, tick an action to offer it, or clear the tick to leave it out.</li>"
                + "<li>Drag an action by its handle to move it up or down among actions of its kind. Actions of other kinds keep their places.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The count under the list says how many are offered, in the form \"X of Y offered\".</li>"
                + "<li><b>Reset to Default</b> offers every action again, with Map to vJoy, Macro and Response Curve first and the rest by name.</li>"
                + "<li>Every change is saved at once.</li>"
                + "</ul>",
            related: ["options-profile-options", "configuration-actions-add-action"]
        },
        {
            id: "options-profile-diagnostics",
            section: "Options",
            title: "Diagnostic logs",
            body: "<p>The program writes what it does to log files, which help when you report a problem. <b>Diagnostic logs</b> sets how much it writes.</p>"
                + "<ul>"
                + "<li><b>Diagnostic logs</b> <a href=\"show:option/Diagnostic logs\">Show me ›</a>: <b>Off</b>, <b>ALL</b>, <b>Info</b>, <b>Warning</b> or <b>Error</b>. It starts at <b>Warning</b>. <b>Off</b> writes nothing except errors, which still go to system.log.</li>"
                + "<li><b>Log When Not Responding</b> <a href=\"show:option/Log When Not Responding\">Show me ›</a>: when the program stops responding for 5 seconds, it writes \"Not responding for N s\" and where each part of the program is stuck to system.log, once per freeze, then \"Responding again after N s\". It is off at first.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Both take effect at once.</li>"
                + "<li><b>Diagnostic logs</b> is the same setting as in the Live Log Reader: a change in one shows in the other.</li>"
                + "<li>A change to the logs folder takes effect at the next start. See <a href=\"topic:options-profile-folders\">Change where files are kept</a>.</li>"
                + "</ul>",
            related: ["options-profile-general", "options-profile-folders"]
        },
        {
            id: "options-profile-auto-load",
            section: "Options",
            title: "Load a profile automatically for a game",
            body: "<p>Auto-load loads and runs the profile you chose for a program when that program comes to the front.</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>Profiles</b>.</li>"
                + "<li>Turn on <b>Load profiles automatically</b> <a href=\"show:option/Load profiles automatically\">Show me ›</a>.</li>"
                + "<li>Under <b>Programs and their profiles</b>, choose <b>New Entry</b>.</li>"
                + "<li>Choose <b>Select Executable</b> to pick a running program, or <b>Browse Executable</b> to pick its file.</li>"
                + "<li>Choose <b>Select Profile</b> and pick the profile.</li>"
                + "<li>Make sure the row's switch shows <b>On</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Rows are saved as you change them.</li>"
                + "<li>The trash button on a row with a program or a profile asks first, for example \"Remove auto-load entry?\" with \"Profile X will no longer load for Y.\" Choose the red <b>Remove Entry</b> to remove it; <b>Cancel</b>, <b>Enter</b> or <b>Esc</b> keeps it. You can restore it from Tools › History. An empty row goes without asking.</li>"
                + "<li>A full program path matches that program first. Otherwise a row's text is a pattern matched against the program's path, capitals ignored. Blank or invalid patterns match nothing, and rows turned off are skipped.</li>"
                + "<li>When the program comes back to the front and its profile is already open, the profile is not loaded again.</li>"
                + "<li>Auto-load never switches over unsaved changes: it shows \"Auto-load Waited\" once for that profile. Save or discard the changes, and it switches next time.</li>"
                + "<li>When the chosen profile file is missing, it says so once and stops the running profile.</li>"
                + "<li>When a program with no profile comes to the front, the running profile stops. Turn on <b>Keep running when the program loses focus</b> <a href=\"show:option/Keep running when the program loses focus\">Show me ›</a> to keep it running in both cases.</li>"
                + "<li>Clicking into this program's own window doesn't count as another program.</li>"
                + "</ul>",
            related: ["options-profile-profile-settings", "getting-started-profiles"]
        },
        {
            id: "options-profile-osc",
            section: "Options",
            title: "OSC options",
            body: "<p>The <b>OSC</b> section of Options sets where the program listens for OSC messages and where it sends them.</p>"
                + "<ul>"
                + "<li><b>Enabled</b>: turns OSC on.</li>"
                + "<li><b>Input host</b> <a href=\"show:option/Input host\">Show me ›</a> and <b>Port</b>: the address the program listens on. The list offers this PC's IPv4 addresses, 127.0.0.1 and 0.0.0.0, and you can type another. The ↻ button scans this PC's addresses again.</li>"
                + "<li>Output address <a href=\"show:option/Output address\">Show me ›</a>: where the program sends OSC messages.</li>"
                + "<li><b>Messages</b>: auto-release of address-only messages, the delay presets, and treating address-only messages as 1.0.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>If the port can't be opened, for example because another program uses it, Run still runs the rest of the profile and shows one error: \"Could not bind OSC on host:port.\", with the host and port.</li>"
                + "</ul>",
            related: ["options-profile-options"]
        },
        {
            id: "options-profile-folders",
            section: "Options",
            title: "Change where files are kept",
            body: "<p>The <b>Folders</b> section of Options shows where the program keeps its files: the data folder, and the profiles, modules, scripts, export, logs, history and plugins folders.</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>Folders</b>.</li>"
                + "<li>Choose <b>Select</b> beside a folder and pick another folder.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Reset</b> puts the default folder back.</li>"
                + "<li>A change to the logs folder <a href=\"show:option/Logs folder\">Show me ›</a> or the plugins folder <a href=\"show:option/Plugins folder\">Show me ›</a> takes effect at the next start.</li>"
                + "<li>A folder that can't be made or reached is replaced by the default folder.</li>"
                + "</ul>",
            related: ["options-profile-options", "getting-started-saved-where"]
        },
        {
            id: "options-profile-profile-settings",
            section: "Profile",
            title: "Profile Settings",
            body: "<p><b>View › Profile Settings</b> <a href=\"open:view.settings\">Open ›</a> holds the settings stored in the profile. Save the profile to keep them.</p>"
                + "<ul>"
                + "<li><b>Startup Mode</b>: the mode the profile is in when it is loaded, including when a program auto-loads it. <b>Last Active</b> (the usual choice) opens the mode the profile last ran in; a profile with no last mode yet (new, moved, renamed or never run) opens in the top mode of the Manage Modes list. A mode by name always opens that mode.</li>"
                + "<li><b>Macro Default Delay</b>: the pause between macro steps. While <b>Use the Options default (Options → Actions → Macro)</b> is ticked, the profile uses <b>Default delay</b> <a href=\"show:option/Default delay\">Show me ›</a> from Options, and the box is greyed and shows that value. Clear the tick to give the profile its own delay, starting from the value shown.</li>"
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
                + "<li>Choose <b>View › Scripts</b> <a href=\"open:view.scripts\">Open ›</a>.</li>"
                + "<li>Choose <b>Add Script</b> and pick a .py file. The chooser opens in the folder you last picked a script from.</li>"
                + "<li>Rename the script and set its variables on that page, if you like.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Each script added gets a name, \"Instance 1\" at first. Names are unique per file, so the same file can be added more than once.</li>"
                + "<li>The trash button asks \"Remove script &lt;name&gt;?\": \"It leaves this profile with its settings here. The script file itself is not deleted.\" Choose the red <b>Remove Script</b> to remove it; <b>Cancel</b>, <b>Enter</b> or <b>Esc</b> keeps it. This can't be undone.</li>"
                + "<li>A script runs only when the variables it requires are set. It is loaded fresh each time you choose <b>Run</b>.</li>"
                + "<li>A script inside the scripts folder is saved by its place in that folder; others keep their full path.</li>"
                + "<li>A script's vjoy object can only use outputs the vJoy output modules claim.</li>"
                + "</ul>",
            related: ["options-profile-scripts-cant-load", "getting-started-profiles", "home-devices-vjoy-output"]
        },
        {
            id: "options-profile-scripts-cant-load",
            section: "Profile",
            title: "When a script can't load",
            body: "<p>A profile still opens when one of its scripts can't load, for example when the file is missing, has an error, or no longer fits its saved settings.</p>"
                + "<ul>"
                + "<li>The script and its saved settings are kept.</li>"
                + "<li>The <b>Scripts</b> page shows the reason under it, starting \"Can't load:\".</li>"
                + "<li>At <b>Run</b>, the script is tried again. If it still can't load, it is skipped, the reason goes to the log, and the rest of the profile runs.</li>"
                + "<li>If a script needs a plugin that is missing, Run shows \"Could not run the profile: a user plugin is missing.\"</li>"
                + "</ul>"
                + "<p>Fix the script, then choose <b>Run</b> again.</p>",
            related: ["options-profile-scripts", "options-profile-folders"]
        },

        {
            id: "options-profile-q-find-setting",
            section: "Common questions",
            title: "How do I find a setting?",
            body: "<p>Type part of its name in <b>Search options</b> (<b>Ctrl+F</b> in Options). See <a href=\"topic:options-profile-options\">Options</a>.</p>",
            related: ["options-profile-options"]
        },
        {
            id: "options-profile-q-tray",
            section: "Common questions",
            title: "How do I keep the program running when I close the window?",
            body: "<p>Turn on <b>Minimize to tray</b>. See <a href=\"topic:options-profile-tray\">Keep the program running in the tray</a>.</p>",
            related: ["options-profile-tray"]
        },
        {
            id: "options-profile-q-auto-load-waited",
            section: "Common questions",
            title: "Why didn't my profile load when my game came to the front?",
            body: "<p>The open profile has unsaved changes, the profile file is missing, or <b>Load profiles automatically</b> is off. Save or discard the changes and bring the game to the front again. See <a href=\"topic:options-profile-auto-load\">Load a profile automatically for a game</a>.</p>",
            related: ["options-profile-auto-load"]
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
