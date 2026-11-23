// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Options and profile (Options, Profile Settings, Scripts).
// Written to claude/plans/help-style-guide.md: each topic opens with what
// it's for, then "How to", "What you see" and "Good to know".

.pragma library

var chapter = { id: "options-profile", title: "Options and profile" }

function topics() {
    return [
        {
            id: "options-profile-options",
            section: "Options",
            title: "Options",
            body: "<p><b>Options</b> holds the program's own settings. They are not stored in the profile; the profile's settings are in <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b> <a href=\"open:tools.options\">Open ›</a>, or <b>Options</b> on the toolbar.</li>"
                + "<li>Pick a section on the left.</li>"
                + "<li>Or type in <b>Search options</b> (<b>Ctrl+F</b>) to find a setting in any section.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>General</b>: startup and the tray, devices, vJoy, diagnostics and History. See <a href=\"topic:options-profile-general\">General options</a>.</li>"
                + "<li><b>Interface</b>: dark mode, size, input names and input highlighting. See <a href=\"topic:options-profile-interface\">Interface options</a>.</li>"
                + "<li><b>Actions</b>: which actions the add-action menus offer, and the settings of each action. See <a href=\"topic:options-profile-add-action-menu\">Choose the actions you can add</a>.</li>"
                + "<li><b>Profiles</b>: load a profile automatically when a game comes to the front. See <a href=\"topic:options-profile-auto-load\">Load a profile automatically for a game</a>.</li>"
                + "<li><b>Home</b>: the <b>Cards</b> group sets how the device cards look, and <b>Reset All Card Sizes</b>.</li>"
                + "<li><b>OSC</b>: a button that opens OSC's own Module Setup, where its settings are. See the <a href=\"topic:osc-about\">OSC</a> chapter.</li>"
                + "<li><b>Folders</b>: where the program keeps its files. See <a href=\"topic:options-profile-folders\">Change where files are kept</a>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The line under the search box says how many settings match, or \"Nothing matches\".</li>"
                + "<li>× clears the search box. <b>Esc</b> clears it and leaves the box.</li>"
                + "<li>Not in Options: the Device Library's folder is in <b>Device Library Settings</b>.</li>"
                + "<li>Not in Options: the Device Mapping Editor's settings are in its <b>Edit › Device Map Options…</b>.</li>"
                + "</ul>",
            related: ["options-profile-general", "options-profile-interface", "options-profile-profile-settings", "getting-started-saved-where"]
        },
        {
            id: "options-profile-general",
            section: "Options",
            title: "General options",
            body: "<p>The <b>General</b> section of Options covers startup, devices, vJoy, diagnostics and History.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Startup and Tray</b>:<ul>"
                + "<li><b>Start Gremlin-Platforms when Windows starts</b>: opens the program minimized each time you sign in to Windows. Off at first. See <a href=\"topic:options-profile-start-with-windows\">Start the program with Windows</a>.</li>"
                + "<li><b>Check for updates</b> <a href=\"show:option/Check for updates\">Show me ›</a>: looks online for a new version each time the program starts.</li>"
                + "<li><b>Minimize to tray</b>: closing or minimizing the window keeps the program running in the tray. See <a href=\"topic:options-profile-tray\">Keep the program running in the tray</a>.</li>"
                + "<li><b>HidHide</b>: a pointer only. To turn HidHide on each time the program starts, use <b>Automatically Start</b> in <b>Tools › Device Setup › HidHide</b> <a href=\"open:tools.hidhide\">Open ›</a>.</li>"
                + "</ul></li>"
                + "<li><b>Devices</b>:<ul>"
                + "<li><b>Device change behavior</b> <a href=\"show:option/Device change behavior\">Show me ›</a>: what happens when a device is plugged in or out while the profile runs.<ul>"
                + "<li><b>Stop</b>: the profile stops.</li>"
                + "<li><b>Ignore</b>: the profile keeps running as it is.</li>"
                + "<li><b>Reload</b> (the default): the profile stops and runs again with the new devices.</li>"
                + "</ul></li>"
                + "<li><b>Refresh axes when Run starts</b> <a href=\"show:option/Refresh axes when Run starts\">Show me ›</a>: sends every axis's current position again when you choose Run.</li>"
                + "<li><b>Refresh axis on mode change</b> <a href=\"show:option/Refresh axis on mode change\">Show me ›</a>: does the same when the mode changes.</li>"
                + "</ul></li>"
                + "<li><b>vJoy</b>:<ul>"
                + "<li><b>Keep vJoy devices awake</b> <a href=\"show:option/Keep vJoy devices awake\">Show me ›</a>: while the profile runs, sends to each vJoy device again after 60 seconds with no change. Only for older vJoy versions that stop responding when idle. Off at first.</li>"
                + "</ul></li>"
                + "<li><b>Diagnostics</b>: <b>Diagnostic logs</b> and <b>Log When Not Responding</b>. See <a href=\"topic:options-profile-diagnostics\">Diagnostic logs</a>.</li>"
                + "<li><b>History</b>:<ul>"
                + "<li><b>Days to keep changes</b> <a href=\"show:option/Days to keep changes\">Show me ›</a>: how long <b>Tools › History</b> keeps each change.</li>"
                + "<li><b>Largest history file (MB)</b> <a href=\"show:option/Largest history file (MB)\">Show me ›</a>: how big the history file may grow.</li>"
                + "</ul></li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An axis you haven't moved since the program started is sent as centered until it moves.</li>"
                + "<li>With <b>Keep vJoy devices awake</b> on, Windows counts each send as input, so it turns the displays on about once a minute while the profile runs. Leave it off unless your vJoy stops responding.</li>"
                + "<li>A change to <b>Keep vJoy devices awake</b> takes effect the next time you choose <b>Run</b>.</li>"
                + "</ul>",
            related: ["options-profile-options", "options-profile-tray", "options-profile-start-with-windows", "tools-hidhide", "tools-history"]
        },
        {
            id: "options-profile-tray",
            section: "Options",
            title: "Keep the program running in the tray",
            body: "<p>With <b>Minimize to tray</b> on, the program keeps running in the Windows system tray when you minimize or close its window. It is off at first.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>General</b>.</li>"
                + "<li>Under <b>Startup and Tray</b>, turn on <b>Minimize to tray</b> <a href=\"show:option/Minimize to tray\">Show me ›</a>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The tray icon shows one picture while the profile is stopped and another while it runs.</li>"
                + "<li>A left click brings the window back as it was: windowed, maximized or full screen.</li>"
                + "<li>A right click opens the <b>tray menu</b>:<ul>"
                + "<li><b>Show Gremlin-Platforms</b> or <b>Hide Gremlin-Platforms</b>: brings the window back or hides it.</li>"
                + "<li><b>Screen Saver Mode</b>: turns Screen Saver Mode on or off. See <a href=\"topic:tools-screen-saver-mode\">Let the screen rest with Screen Saver Mode</a>.</li>"
                + "<li><b>Turn displays off now</b>: turns your monitors off at once. Moving the mouse doesn't stop it until the displays are off, and for 2 seconds after.</li>"
                + "<li><b>Run Profile</b> or <b>Stop Profile</b>: runs or stops the profile.</li>"
                + "<li><b>Start with Windows</b>: a tick item. See <a href=\"topic:options-profile-start-with-windows\">Start the program with Windows</a>.</li>"
                + "<li><b>Exit Gremlin-Platforms</b>: quits the program.</li>"
                + "</ul></li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The first time the window's X hides it, a tray notice says the program is still running. It shows only once.</li>"
                + "<li>To quit, choose <b>File › Exit</b> <a href=\"show:menu/File/Exit\">Show me ›</a> or <b>Exit Gremlin-Platforms</b> in the tray menu.</li>"
                + "<li>Exit from the tray brings the window back first, so you can answer any question about unsaved changes.</li>"
                + "<li>While it's in the tray, the program closes its pages to give memory back to Windows (<b>Release memory in the tray</b>). They open again when the window comes back. The profile keeps running.</li>"
                + "<li>The Device Bindings page stays open while it has unsaved display edits.</li>"
                + "<li>If Windows brings the window back by itself, for example after a monitor reconnects, the window stays on screen.</li>"
                + "<li>The tray icon comes back by itself if Windows Explorer restarts.</li>"
                + "<li>To start the program straight into the tray, use <code>--start-minimized</code> with Minimize to tray on. See <a href=\"topic:getting-started-command-line\">Start the program from a command line</a>.</li>"
                + "</ul>",
            related: ["options-profile-start-with-windows", "options-profile-general", "getting-started-command-line", "getting-started-run"]
        },
        {
            id: "options-profile-start-with-windows",
            section: "Options",
            title: "Start the program with Windows",
            body: "<p>The program can open by itself each time you sign in to Windows. It is off at first.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>General</b>.</li>"
                + "<li>Under <b>Startup and Tray</b>, turn on <b>Start Gremlin-Platforms when Windows starts</b>.</li>"
                + "<li>Or right-click the tray icon and tick <b>Start with Windows</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Both places are one setting: a change in one shows in the other.</li>"
                + "<li>At sign-in the program opens minimized and doesn't start Run.</li>"
                + "<li>With <b>Minimize to tray</b> on, it opens in the tray.</li>"
                + "<li>It needs no administrator permission.</li>"
                + "<li>Windows' own <b>Startup Apps</b> page lists the program while this is on.</li>"
                + "<li>Turning it off, or uninstalling the program, removes it from that list.</li>"
                + "<li>If you turned the program off in Windows' Startup Apps:<ul>"
                + "<li>In Options, the switch shows off with the note <b>Turned off in Windows' Startup Apps</b>.</li>"
                + "<li>In the tray menu, <b>Start with Windows</b> shows unticked.</li>"
                + "<li>Turning it on in either place opens Windows' Startup Apps page, so you can turn it back on there.</li>"
                + "</ul></li>"
                + "</ul>",
            related: ["options-profile-tray", "options-profile-general", "getting-started-command-line"]
        },
        {
            id: "options-profile-interface",
            section: "Options",
            title: "Interface options",
            body: "<p>The <b>Interface</b> section of Options sets how the program looks and how inputs are named. It has two groups: <b>Display</b> (dark mode and size) and <b>Inputs</b> (input names and input highlighting).</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Dark mode</b> <a href=\"show:option/Dark mode\">Show me ›</a>: dark colors, in every window at once.</li>"
                + "<li><b>UI scale</b> and <b>Ignore Windows display scaling</b>: the size of the program. See <a href=\"topic:options-profile-ui-scale\">Change the size of the program</a>.</li>"
                + "<li><b>Input names</b> <a href=\"show:option/Input names\">Show me ›</a>: how inputs are named on screen.<ul>"
                + "<li><b>Numerical</b>: the number name, such as \"Axis 3\".</li>"
                + "<li><b>Label</b>: the name the program knows for that control on your device model.</li>"
                + "<li><b>Numerical and Label</b>: both. This is the usual choice.</li>"
                + "</ul></li>"
                + "<li><b>Input highlighting</b> <a href=\"show:option/Input highlighting\">Show me ›</a>: using a control selects its input on screen, when that device's page is open.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A control with no known label always shows its number name.</li>"
                + "</ul>",
            related: ["options-profile-ui-scale", "options-profile-options"]
        },
        {
            id: "options-profile-ui-scale",
            section: "Options",
            title: "Change the size of the program",
            body: "<p>The program follows the Windows display scale. To choose its size yourself, turn Windows scaling off for it.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>Interface</b>.</li>"
                + "<li>Turn on <b>Ignore Windows display scaling</b> <a href=\"show:option/Ignore Windows display scaling\">Show me ›</a>.</li>"
                + "<li>A <b>Restart Required</b> box opens. Choose <b>Restart</b> to restart now, <b>Later</b> to use it at the next start, or <b>Cancel</b> to undo the change.</li>"
                + "<li>Drag <b>UI scale</b> <a href=\"show:option/UI scale\">Show me ›</a> to a size from 70% to 200%, in steps of 5.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The program resizes when you let go of the slider. No restart is needed.</li>"
                + "<li>While Windows scaling is on, the UI scale slider is grayed out at 100%.</li>"
                + "<li>Turning Ignore Windows display scaling off again opens the same box.</li>"
                + "</ul>",
            related: ["options-profile-interface", "options-profile-options"]
        },
        {
            id: "options-profile-add-action-menu",
            section: "Options",
            title: "Choose the actions you can add",
            body: "<p>The <b>Add Action Menu</b> in Options sets which actions the add-action menus offer, and in what order.</p><p>Each action with settings also has its own group: <b>Macro</b>, <b>Change Mode</b>, <b>Double Tap</b>, <b>Smart Toggle</b>, <b>Tempo</b>, <b>Axis Delta</b>, <b>Play Sound</b> and <b>Text to Speech</b>.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>Actions</b>.</li>"
                + "<li>Under <b>Actions offered</b> <a href=\"show:option/Actions offered\">Show me ›</a>, tick an action to offer it, or clear the tick to leave it out.</li>"
                + "<li>Drag an action by its handle to move it. Actions move only within their own group.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The line under the list says how many actions are offered, for example \"12 of 20 offered\".</li>"
                + "<li><b>Reset to Default</b> offers every action again: Map to vJoy, Macro and Response Curve first, the rest by name.</li>"
                + "<li>Every change is saved at once.</li>"
                + "<li>The rest of the Actions section holds each action's own settings, such as Macro's <b>Default delay</b>.</li>"
                + "</ul>",
            related: ["options-profile-options", "device-bindings-actions-add-action"]
        },
        {
            id: "options-profile-diagnostics",
            section: "Options",
            title: "Diagnostic logs",
            body: "<p>The program writes what it does to log files. They help when you report a problem.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Diagnostic logs</b> <a href=\"show:option/Diagnostic logs\">Show me ›</a>: how much the program writes. It starts at <b>Warning</b>.<ul>"
                + "<li><b>Off</b>: nothing except errors, which still go to system.log.</li>"
                + "<li><b>ALL</b>: the most detail. It also turns on <b>red debug mode</b>, a red frame with the badge <b>DEBUG</b>.</li>"
                + "<li><b>Info</b>: what the program does, without the finest detail.</li>"
                + "<li><b>Warning</b>: only problems and warnings.</li>"
                + "<li><b>Error</b>: only errors.</li>"
                + "</ul></li>"
                + "<li><b>Log When Not Responding</b> <a href=\"show:option/Log When Not Responding\">Show me ›</a>: when the program freezes for 5 seconds, it writes where it got stuck to system.log. Off at first.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Both take effect at once.</li>"
                + "<li>Log When Not Responding watches the window and the input thread, the part that handles your controls.</li>"
                + "<li>It writes once per freeze, and again when the program responds.</li>"
                + "<li>Your controls keep working while the window is frozen. Only what the window shows waits.</li>"
                + "<li>Diagnostic logs is the same setting as in the <b>Live Log Reader</b>: a change in one shows in the other.</li>"
                + "<li>A change to the logs folder takes effect at the next start. See <a href=\"topic:options-profile-folders\">Change where files are kept</a>.</li>"
                + "</ul>",
            related: ["options-profile-general", "options-profile-folders"]
        },
        {
            id: "options-profile-auto-load",
            section: "Options",
            title: "Load a profile automatically for a game",
            body: "<p><b>Auto-load</b> loads and runs the profile you chose for a game, or any other program, when that program comes to the front.</p>"
                + "<h4>How to</h4>"
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
                + "<li>The trash button asks before removing a row that has a program or a profile.<ul>"
                + "<li>A <b>Remove auto-load entry?</b> box asks: the red <b>Remove Entry</b> removes it; <b>Cancel</b> or <b>Esc</b> keeps it.</li>"
                + "<li>You can get it back from <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a>.</li>"
                + "<li>An empty row is removed at once.</li>"
                + "</ul></li>"
                + "<li>A full program path matches that program exactly.</li>"
                + "<li>Other text matches any program whose path contains it, capitals ignored.<ul>"
                + "<li>The text is a regular expression (a search pattern), so you can match several programs with one row.</li>"
                + "<li>A blank or invalid pattern matches nothing. Rows turned off are skipped.</li>"
                + "</ul></li>"
                + "<li>When the program comes back to the front and its profile is already open, the profile isn't loaded again. If it was stopped, it runs.</li>"
                + "<li>Auto-load never switches while you have unsaved changes.<ul>"
                + "<li>Instead it stops the running profile and shows an <b>Auto-load Waited</b> notice, once for that profile.</li>"
                + "<li>Save or discard your changes. It switches the next time the program comes to the front.</li>"
                + "<li>Your unsaved changes are not lost meanwhile. See <a href=\"topic:device-bindings-actions-safety-net\">Unfinished actions and recovery copies</a>.</li>"
                + "</ul></li>"
                + "<li>When the chosen profile file is missing, a notice says so once, and the running profile stops.</li>"
                + "<li>When a program with no profile comes to the front, the running profile stops.</li>"
                + "<li>To keep it running in these cases, turn on <b>Keep running when the program loses focus</b> <a href=\"show:option/Keep running when the program loses focus\">Show me ›</a>.</li>"
                + "<li>Clicking into this program's own window doesn't count as another program.</li>"
                + "</ul>",
            related: ["options-profile-profile-settings", "getting-started-profiles"]
        },
        {
            id: "options-profile-folders",
            section: "Options",
            title: "Change where files are kept",
            body: "<p>The <b>Folders</b> section of Options shows where the program keeps its files.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Options</b>, then <b>Folders</b>.</li>"
                + "<li>Choose <b>Select</b> beside a folder and pick another folder.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The data folder, and the profiles, modules, scripts, export, logs, history and plugins folders.</li>"
                + "<li><b>Reset</b> beside a folder puts the default folder back.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A change to the logs folder <a href=\"show:option/Logs folder\">Show me ›</a> takes effect at the next start.</li>"
                + "<li>So does a change to the plugins folder <a href=\"show:option/Plugins folder\">Show me ›</a>.</li>"
                + "<li>A folder that can't be created or opened is replaced by the default folder.</li>"
                + "</ul>",
            related: ["options-profile-options", "getting-started-saved-where"]
        },
        {
            id: "options-profile-profile-settings",
            section: "Profile",
            title: "Profile Settings",
            body: "<p><b>View › Profile Settings</b> <a href=\"open:view.settings\">Open ›</a> holds the settings stored in the profile. Save the profile to keep them.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Startup Mode</b>: the mode the profile opens in, also when auto-load loads it.<ul>"
                + "<li><b>Last Active</b> (the usual choice): the mode the profile last ran in.</li>"
                + "<li>A profile that has never run, or was moved or renamed, opens in the top mode of the Manage Modes list.</li>"
                + "<li>A mode by name: always opens that mode.</li>"
                + "</ul></li>"
                + "<li><b>Macro Default Delay</b>: the pause between macro steps.<ul>"
                + "<li>While <b>Use the Options default (Options → Actions → Macro)</b> is ticked, the profile uses <b>Default delay</b> <a href=\"show:option/Default delay\">Show me ›</a> from Options.</li>"
                + "<li>The box is then grayed and shows that value.</li>"
                + "<li>Clear the tick to give the profile its own delay.</li>"
                + "</ul></li>"
                + "<li><b>vJoy Behavior</b>: treat each vJoy device as an output (the default) or as an input.<ul>"
                + "<li>A vJoy device set to input is listed with your physical devices.</li>"
                + "<li>It is not offered in vJoy Initial Values.</li>"
                + "</ul></li>"
                + "<li><b>vJoy Initial Values</b>: axis values set each time the profile starts. Then moving a physical axis that sends to that vJoy axis takes over.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Run</b> starts in the mode shown in the <b>Mode</b> box. To start somewhere else, change it there. See <a href=\"topic:modes-mode-box\">Choose the mode you edit and run</a>.</li>"
                + "</ul>",
            related: ["modes-mode-box", "modes-manage", "getting-started-profiles"]
        },
        {
            id: "options-profile-scripts",
            section: "Profile",
            title: "Add scripts to a profile",
            body: "<p>Scripts are Python files that run with the profile. They are saved with the profile.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>View › Scripts</b> <a href=\"open:view.scripts\">Open ›</a>.</li>"
                + "<li>Choose <b>Add Script</b> and pick a .py file. The chooser opens in the folder you last picked a script from.</li>"
                + "<li>If you like, rename the script and set its variables on that page.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Important: a script runs on the input thread, the part that handles your controls.<ul>"
                + "<li>Don't touch the program's windows from a script.</li>"
                + "<li>Use the <code>stick</code>, <code>vjoy</code>, <code>keyboard</code> and <code>osc</code> objects the script is given.</li>"
                + "</ul></li>"
                + "<li>Each script you add gets its own name. You can add the same file more than once.</li>"
                + "<li>The trash button asks first, in a <b>Remove script</b> box.<ul>"
                + "<li>The red <b>Remove Script</b> removes it from the profile; the script file itself isn't deleted.</li>"
                + "<li><b>Cancel</b> or <b>Esc</b> keeps it. Removing can't be undone.</li>"
                + "</ul></li>"
                + "<li>A script runs only when the variables it requires are set. It is loaded fresh each time you choose <b>Run</b>.</li>"
                + "<li>A script inside the scripts folder is saved by its place in that folder. Others keep their full path.</li>"
                + "<li>A script's <code>vjoy</code> object can only use the vJoy outputs ticked in their output modules.</li>"
                + "<li>A Keyboard variable reacts to exactly the key you chose. Numpad 1 is not End, and Numpad Enter is not Enter.</li>"
                + "<li>A script can use OSC inputs like stick inputs. A new OSC input variable starts with no input chosen.</li>"
                + "<li><code>osc.send</code> sends only to an OSC target by its name, never to a typed host and port.</li>"
                + "<li>It sends nothing and returns False when:<ul>"
                + "<li>OSC output is off, or the profile isn't running;</li>"
                + "<li>there's no target with that name (capitals ignored);</li>"
                + "<li>the address isn't a plain OSC address.</li>"
                + "</ul>The last two also write a warning to user.log.</li>"
                + "</ul>",
            related: ["options-profile-scripts-cant-load", "getting-started-profiles", "home-devices-vjoy-output"]
        },
        {
            id: "options-profile-scripts-cant-load",
            section: "Profile",
            title: "When a script can't load",
            body: "<p>A profile still opens when one of its scripts can't load. For example, the file is missing, has an error, or no longer fits its saved settings.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The script and its saved settings are kept.</li>"
                + "<li>The <b>Scripts</b> page shows the reason under it, starting \"Can't load:\".</li>"
                + "<li>At <b>Run</b>, the script is tried again. If it still can't load, it is skipped and the rest of the profile runs.</li>"
                + "<li>If a script needs a missing plugin, Run says the profile could not run because a user plugin is missing.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The reason also goes to the log.</li>"
                + "<li>Fix the script, then choose Run again.</li>"
                + "</ul>",
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
            id: "options-profile-q-start-with-windows",
            section: "Common questions",
            title: "How do I start the program when Windows starts?",
            body: "<p>Turn on <b>Start Gremlin-Platforms when Windows starts</b> in Options, or tick <b>Start with Windows</b> in the tray menu. See <a href=\"topic:options-profile-start-with-windows\">Start the program with Windows</a>.</p>",
            related: ["options-profile-start-with-windows"]
        },
        {
            id: "options-profile-q-auto-load-waited",
            section: "Common questions",
            title: "Why didn't my profile load when my game came to the front?",
            body: "<ul>"
                + "<li>The open profile has unsaved changes. Save or discard them, then bring the game to the front again.</li>"
                + "<li>The profile file is missing.</li>"
                + "<li><b>Load profiles automatically</b> is off, or the game's row is turned off.</li>"
                + "</ul>"
                + "<p>See <a href=\"topic:options-profile-auto-load\">Load a profile automatically for a game</a>.</p>",
            related: ["options-profile-auto-load"]
        },
        {
            id: "options-profile-q-settings-lost",
            section: "Common questions",
            title: "Why did my Profile Settings not stay?",
            body: "<p>Profile Settings are stored in the profile. Save the profile to keep them. See <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>.</p>",
            related: ["options-profile-profile-settings", "getting-started-saved-where"]
        }
    ]
}
