// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Getting started (incl. general troubleshooting).
// The model page for claude/plans/help-style-guide.md: each topic opens with
// what it's for, then "How to", "What you see" and "Good to know" (empty
// sections left out).

.pragma library

var chapter = { id: "getting-started", title: "Getting started" }

function topics() {
    return [
        {
            id: "getting-started-overview",
            section: "Getting started",
            title: "How Gremlin-Platforms works",
            body: "<p>Gremlin-Platforms turns your controllers into the virtual devices a game reads. Every input follows one path:</p>"
                + "<p>Your stick → input module → actions → output module → vJoy or Xbox driver → game</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Input module</b>: one per controller. It holds the buttons, axes and hats the program may use. An input that isn't ticked there is ignored.</li>"
                + "<li><b>Actions</b>: kept in the profile. They say what each input does: send it to vJoy or Xbox, press keys, move the mouse, run a macro, change mode, and more.</li>"
                + "<li><b>Output module</b>: one per vJoy device, plus one for the Xbox controller. It is the only part that talks to the driver.</li>"
                + "<li><b>Logical Device</b>: a virtual device inside the program. Actions can send to it, and it has actions of its own.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>vJoy</b> is a virtual joystick driver: games read its devices like a real stick.</li>"
                + "<li><b>ViGEmBus</b> does the same for an Xbox 360 controller.</li>"
                + "</ul>",
            related: ["getting-started-first-setup", "getting-started-main-window", "logical-device-about", "getting-started-saved-where"]
        },
        {
            id: "getting-started-first-setup",
            section: "Getting started",
            title: "Set up your first profile",
            body: "<p>These steps take you from a plugged-in stick to a running profile.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Install <b>vJoy</b>, and <b>ViGEmBus</b> if you want an Xbox controller. Setup offers both; you can also do it later in <b>Tools › Drivers</b> <a href=\"open:tools.drivers\">Open ›</a>.</li>"
                + "<li>On <b>Home</b>, right-click your stick and choose <b>Module › Module Setup…</b>.</li>"
                + "<li>Press each control you will use (or tick it), then choose <b>Save Module</b>.</li>"
                + "<li>Right-click each vJoy device, choose Module › Module Setup… again, tick the outputs you will use and choose Save Module.</li>"
                + "<li>Double-click your stick to open <b>Device Bindings</b>.</li>"
                + "<li>Choose <b>Add Action</b> on an input, pick an action such as <b>Map to vJoy</b>, and choose <b>OK</b>.</li>"
                + "<li>Choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> (<b>Ctrl+S</b>).</li>"
                + "<li>Choose <b>Run</b> <a href=\"show:toolbar/Run\">Show me ›</a> on the toolbar.</li>"
                + "<li>Open the <b>vJoy Viewer</b> <a href=\"open:tools.vjoyViewer\">Open ›</a> to check that your moves arrive.</li>"
                + "<li>For Xbox, open the Xbox 360 Controller's <b>Output View</b> <a href=\"open:view.xboxOutput\">Open ›</a> instead.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The Xbox controller needs no Module Setup.</li>"
                + "<li>Module Setup also opens from <b>Tools › Device Setup › Input Module Setup</b> <a href=\"show:menu/Tools/Device Setup/Input Module Setup\">Show me ›</a>. For a vJoy device, use <b>Output Module Setup</b> in the same menu.</li>"
                + "<li><b>Tools › Mapping › Auto Mapping Tool</b> <a href=\"open:tools.autoMappingTool\">Open ›</a> creates the Map to vJoy actions for a whole device in one step. See <a href=\"topic:tools-auto-mapping-tool\">Create actions with the Auto Mapping Tool</a>.</li>"
                + "</ul>",
            related: ["getting-started-overview", "getting-started-setup-drivers", "home-devices-input-modules", "device-bindings-actions-add-action", "getting-started-run"]
        },
        {
            id: "getting-started-main-window",
            section: "Getting started",
            title: "The main window",
            body: "<p>The main window shows one page at a time, such as Home or Device Bindings, under a toolbar and a mode bar.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Title bar: the program's name and version, then the profile's name, for example \"Gremlin-Platforms R2 X.Y.Z - Flight.xml\".<ul>"
                + "<li>A * before the profile's name means it has unsaved changes.</li>"
                + "<li>A profile not saved yet is called \"Untitled\".</li>"
                + "<li>Other windows show their own name after the program's, for example \"Gremlin-Platforms R2 X.Y.Z - Device Library\".</li>"
                + "</ul></li>"
                + "<li>Toolbar, left to right:<ul>"
                + "<li><b>Home</b>: the device cards.</li>"
                + "<li><b>Run</b>: runs the profile. It reads <b>Stop</b> while the profile runs.</li>"
                + "<li><b>vJoy Viewer</b>: opens the viewer, or closes it when it is open.</li>"
                + "<li><b>Input Tester</b>: starts the Input Tester, which shows what other programs see through HidHide.</li>"
                + "<li><b>Search</b>: finds keys, actions, names and outputs in every profile (see <a href=\"topic:tools-search\">Search your profiles</a>).</li>"
                + "<li><b>Mapping Editor</b>: opens a blank Device Mapping Editor.</li>"
                + "<li><b>Device Library</b>: every device and its saved setups.</li>"
                + "<li><b>Logical Device</b>: the Logical Device's page.</li>"
                + "<li><b>Options</b>: the program's settings.</li>"
                + "</ul></li>"
                + "<li>Mode bar, under the toolbar on every page: the <b>Mode</b> box and <b>Manage Modes</b> <a href=\"show:modebar/Manage Modes\">Show me ›</a> on the left. The open page's own controls follow, such as <b>Compact view</b> and <b>Layout</b> on Home.</li>"
                + "<li>Bottom bar: the status (Running or Stopped) and what the last save wrote.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>In a narrow window the toolbar shows icons only. Point at one to see its name.</li>"
                + "<li>In a narrow window the page's controls on the mode bar scroll sideways. Mode and Manage Modes stay put.</li>"
                + "<li><b>F1</b> opens Help with the whole book (see <a href=\"topic:getting-started-using-help\">Use Help</a>).</li>"
                + "</ul>",
            related: ["getting-started-run", "modes-mode-box", "getting-started-menus", "home-devices-home"]
        },
        {
            id: "getting-started-install",
            section: "Getting started",
            title: "Install the program",
            body: "<p>Each release on GitHub has two downloads: an installer and a portable copy. The installer also sets up the drivers the program needs.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Download Gremlin-Platforms-R2-X.Y.Z-Setup.exe from the release page on GitHub and run it.</li>"
                + "<li>Choose a folder. The suggested one is %LOCALAPPDATA%\\Programs\\Gremlin-Platforms; any folder you can write to works.</li>"
                + "<li>On the <b>Drivers</b> page, choose the drivers and vJoy devices you want (see <a href=\"topic:getting-started-setup-drivers\">Setup's Drivers page</a>).</li>"
                + "<li>Finish setup. Its last page lists each driver's result.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The program installs for your Windows user only. It needs no administrator rights; only the drivers do.</li>"
                + "<li>Setup adds a Start menu entry, an optional desktop shortcut, and an uninstaller in the Apps page of Windows Settings.</li>"
                + "<li>The program folder holds gremlin_platforms.exe (the program) and Gremlin Input Tester.exe (the <b>Input Tester</b>).</li>"
                + "<li>It also holds Gremlin Device Helper.exe, a small helper that does the work that needs administrator rights, such as installing drivers.</li>"
                + "<li>A licenses folder in the program folder holds the license notices of the third-party parts the program includes.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The portable copy is Gremlin-Platforms-R2-X.Y.Z.zip. Unzip it anywhere outside Program Files and run gremlin_platforms.exe.</li>"
                + "<li>The Input Tester shows what other programs see through HidHide. Open it from the toolbar or <b>Tools › Viewers › Input Tester…</b>; it has no Start menu entry.</li>"
                + "<li>An update replaces the programs and the license notices.</li>"
                + "<li>Uninstalling Gremlin-Platforms leaves vJoy, ViGEmBus, HidHide and the Microsoft Visual C++ Runtime installed.</li>"
                + "<li>Updates and uninstalling never touch your profiles, modules or settings. They are kept in your Gremlin Platforms folder.</li>"
                + "</ul>",
            related: ["getting-started-setup-drivers", "getting-started-check-updates", "getting-started-saved-where", "tools-drivers"]
        },
        {
            id: "getting-started-setup-drivers",
            section: "Getting started",
            title: "Setup's Drivers page",
            body: "<p>After you choose a folder, setup shows a <b>Drivers</b> page. It installs or updates the drivers the program needs, and sets up your vJoy devices.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Check the driver rows. Missing drivers are ticked for you; tick an older one to update it.</li>"
                + "<li>Under <b>vJoy devices</b>, choose a <b>Preset</b>, or change the device rows. To add a device, choose <b>+ Add device</b>, the list's last row.</li>"
                + "<li>Choose <b>Next</b>. Windows asks for administrator permission once for all the ticked drivers.</li>"
                + "<li>When setup ends, read each driver's result. If a driver asks for a restart of Windows, setup offers one.</li>"
                + "<li>Then, in the program, set up each new vJoy device's output module: only the outputs ticked there are sent to vJoy. See <a href=\"topic:home-devices-vjoy-output\">Set up a vJoy output module</a>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Microsoft Visual C++ Runtime</b>: the first row, with its version or <b>not installed</b>. The program needs it, so setup always installs it when it is missing.</li>"
                + "<li><b>Check and download an updated Visual C++ Runtime</b>: tick it to get Microsoft's newest copy. Setup uses it only when it is newer and signed by Microsoft.</li>"
                + "<li><b>vJoy</b>, <b>ViGEmBus</b> and <b>HidHide</b>: one row each, with the installed version, <b>not installed</b>, or <b>update available</b>: <i>old</i> → <i>new</i>. A driver that is up to date has no box.</li>"
                + "<li><b>vJoy devices</b>: a <b>Preset</b> box and one row per device, ending with <b>+ Add device</b>. <b>Tools › Drivers</b> also has a <b>Devices</b> number box; setup doesn't, by design. The presets, rows and buttons are explained in <a href=\"topic:tools-drivers-vjoy-devices\">Set up vJoy devices</a>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>At least one device stays while vJoy is installed. Your current vJoy devices are kept as they are unless you edit them; removing rows deletes those devices.</li>"
                + "<li>While the devices change, running games lose them until the game restarts. Close your games first.</li>"
                + "<li>Updating vJoy can lose devices made with older vJoy tools. Setup notes them first and offers to repair any it lost: see <a href=\"topic:tools-drivers-vjoy-update\">Keep your vJoy devices through a vJoy update</a>.</li>"
                + "<li>Updating HidHide needs two restarts of Windows. Setup removes the old version and asks for the first; the program installs the new one at its next start and asks for the second.</li>"
                + "<li>Devices are not hidden between the two HidHide restarts.</li>"
                + "<li>Setup checks every driver before running it. For vJoy and HidHide, it also looks for a newer version on that driver's own GitHub page.</li>"
                + "<li>The Visual C++ Runtime has its own administrator prompt, before the drivers' one. Only setup installs or updates it.</li>"
                + "<li>A driver step that fails never stops the program's own install.</li>"
                + "<li><b>Tools › Drivers</b> has the same driver and device rows (see <a href=\"topic:tools-drivers\">Install and update the drivers (Drivers)</a>).</li>"
                + "</ul>"
                + "<p>You can change all of this later in <b>Tools › Drivers</b> <a href=\"open:tools.drivers\">Open ›</a>.</p>",
            related: ["getting-started-install", "tools-drivers", "tools-drivers-vjoy-devices", "tools-drivers-vjoy-update", "home-devices-vjoy-output", "tools-hidhide"]
        },
        {
            id: "getting-started-check-updates",
            section: "Getting started",
            title: "Check for updates",
            body: "<p>The program can tell you about a newer version and install it for you.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Help › Check for Updates</b> <a href=\"show:menu/Help/Check for Updates\">Show me ›</a>. It asks GitHub for the latest release and shows what's new in it.</li>"
                + "<li>On an installed copy, choose <b>Update Now</b>. The program downloads and checks the installer, closes (asking about unsaved changes), installs, and starts the new version.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The New, Changed and Fixed notes. If you skipped versions, each one's notes follow under \"What's new in &lt;version&gt;\", newest first.</li>"
                + "<li><b>Full release notes on GitHub</b>: opens the release page.</li>"
                + "<li><b>Skip This Version</b>: stops the program offering that version.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>When the notes can't be loaded, the window shows \"Release notes unavailable.\" Updating still works.</li>"
                + "<li>Closing the window during a download cancels it and deletes the part already downloaded.</li>"
                + "<li>If an update didn't finish, the next start says so, with setup's log and <b>Try Again</b>. Your previous version is put back.</li>"
                + "<li>After an update, a bar under the toolbar shows <b>Updated to &lt;version&gt;</b> once. Its <b>What's New</b> button opens the release notes that came with the program, so they work offline.</li>"
                + "<li><b>Help › What's New…</b> <a href=\"show:menu/Help/What's New…\">Show me ›</a> opens the same notes for the version you are running.</li>"
                + "<li>Update Now shows no Drivers page and never changes a driver. To change drivers, run setup yourself or use <b>Tools › Drivers</b> <a href=\"open:tools.drivers\">Open ›</a>.</li>"
                + "<li>With <b>Check for updates</b> <a href=\"show:option/Check for updates\">Show me ›</a> on in <b>Options</b> (on by default), the program also checks at start. It only speaks up when there is a newer version.</li>"
                + "<li>A portable copy, or one run from source, only points you to the release page.</li>"
                + "</ul>",
            related: ["getting-started-install", "options-profile-options", "tools-drivers"]
        },
        {
            id: "getting-started-run",
            section: "Getting started",
            title: "Run and stop the profile",
            body: "<p>Running the profile sends your actions to vJoy, Xbox and the Logical Device. While it is stopped, you only edit.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Run</b> <a href=\"show:toolbar/Run\">Show me ›</a> on the toolbar. The button then reads <b>Stop</b> and uses the accent color.</li>"
                + "<li>Nudge any throttle, pedal or slider that rests away from the middle. The program only knows an axis's position after it moves.</li>"
                + "<li>To stop, choose Stop. Stop never asks.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The bottom bar's <b>Status</b>: Running, Stopped, or Running (Paused). It adds \"unsaved changes\" when the running profile has some.</li>"
                + "<li>While Run is starting, the status reads <b>Starting</b>.</li>"
                + "<li>The <b>Mode</b> box on the mode bar picks the mode that runs (see <a href=\"topic:modes-mode-box\">Choose the mode you edit and run</a>).</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>If an action editor has unsaved changes, Run asks first: <b>Save</b>, <b>Discard</b> or <b>Cancel</b>. Run always uses the saved profile.</li>"
                + "<li>Until an axis moves, the program sends it as centered.</li>"
                + "<li>If Run fails partway, the program stops by itself, shows one error, and the status reads Stopped.</li>"
                + "<li>While the profile runs, the action editors are locked (\"Profile running: stop it to edit\").</li>"
                + "<li>Run uses a copy of the profile taken when you press it. Changes you make while it runs apply at the next Run.</li>"
                + "<li>Your controls keep working even when the window is busy or frozen. Only what the window shows waits.</li>"
                + "<li>Running does not hide controllers from games. Use <b>HidHide</b> <a href=\"open:tools.hidhide\">Open ›</a> for that.</li>"
                + "<li>A controller plugged in or removed while running is handled by <b>Device change behavior</b> <a href=\"show:option/Device change behavior\">Show me ›</a> in <b>Options</b>: Stop, Ignore, or Reload.</li>"
                + "</ul>",
            related: ["getting-started-what-stop-releases", "modes-mode-box", "tools-hidhide", "getting-started-nothing-reaches-vjoy"]
        },
        {
            id: "getting-started-what-stop-releases",
            section: "Getting started",
            title: "What Stop lets go of",
            body: "<p>Stop, and closing the program, end everything the profile was doing, so nothing stays pressed or moving.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Keys held by Map to Keyboard, a macro or a script are released, last pressed first.</li>"
                + "<li>Mouse buttons still held are released, and mouse motion stops.</li>"
                + "<li>Macros end at their next step; a Pause step ends at once.</li>"
                + "<li>Sounds and speech stop, and nothing waiting to play is played.</li>"
                + "<li>Tempo, Double Tap and Smart Toggle never act after Stop.</li>"
                + "<li>Each vJoy device is left at rest: every button up, every hat centered, every axis centered.</li>"
                + "<li>Each Xbox pad is unplugged.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li>The next Run starts clean: nothing from the last Run carries over.</li></ul>",
            related: ["getting-started-run", "device-bindings-actions-macro", "device-bindings-actions-play-sound"]
        },
        {
            id: "getting-started-menus",
            section: "Getting started",
            title: "Menus, keys and the Command Palette",
            body: "<p>Menus, lists and boxes work the same way everywhere in the program.</p>"
                + "<h4>What you see</h4>"
                + "<table>"
                + "<tr><th>Key</th><th>What it does</th></tr>"
                + "<tr><td><b>Up</b>, <b>Down</b></td><td>Move in a menu or a list.</td></tr>"
                + "<tr><td><b>Right</b>, <b>Left</b></td><td>Open or close a menu section, or step through a row of choices.</td></tr>"
                + "<tr><td><b>Enter</b></td><td>Run the menu item, or pick the list entry.</td></tr>"
                + "<tr><td><b>Esc</b></td><td>Close a menu. Leave a text box (what you typed is kept). Close Options, Help, About and Check for Updates.</td></tr>"
                + "<tr><td><b>Ctrl+F</b></td><td>Go to the search box. In the box, Esc clears it and leaves it.</td></tr>"
                + "<tr><td><b>F2</b></td><td>Rename. The whole name is selected; Enter or a click elsewhere saves, Esc keeps the old name.</td></tr>"
                + "<tr><td><b>Ctrl+K</b></td><td>Open the <b>Command Palette</b>.</td></tr>"
                + "<tr><td><b>Ctrl+N</b>, <b>Ctrl+O</b></td><td>New profile, load a profile.</td></tr>"
                + "<tr><td><b>Ctrl+S</b>, <b>Ctrl+Shift+S</b></td><td>Save the profile, save it under a new name.</td></tr>"
                + "<tr><td><b>F1</b></td><td>Open Help.</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Menus only show what you can use now. For example, <b>View › Home</b> is left out while you are on Home.</li>"
                + "<li>Rarely an item is grayed out. Point at it to see why.</li>"
                + "<li>Right-click menus start with the name of what you clicked and its most used commands. Sections (▸) follow and open one at a time.</li>"
                + "<li>The section you opened last opens again next time. Some right-click menus show <b>Undo</b> and <b>Redo</b> beside the name.</li>"
                + "<li>Before anything is deleted, removed or cleared, a question names what goes. It says whether you can restore it from <b>Tools › History</b>.</li>"
                + "<li>In that question <b>Cancel</b> is the default, so Enter and Esc both cancel. Only a click on the red button (for example <b>Delete Device</b>) goes ahead.</li>"
                + "<li>Search boxes in Help, History, Options, the Logical Device page, Layers and the Device Library work alike. × clears the box.</li>"
                + "<li>The line under a search box says \"N found\" or \"Nothing matches\" (in Help, \"N topics match\").</li>"
                + "<li>Dropdown lists of 10 or more entries have a search box. Type part of a name, then pick with Up, Down and Enter.</li>"
                + "<li>The Command Palette (also <b>View › Command Palette…</b> <a href=\"show:menu/View/Command Palette\">Show me ›</a>) lists every menu command you can use now, with its shortcut. Type part of a name and press Enter.</li>"
                + "<li>A file or folder chooser opens in the folder you last used for that kind of file, even after a restart.</li>"
                + "<li>Windows that listen to your stick, such as Module Setup, ignore Esc, because a stick button can send it. Click away instead.</li>"
                + "</ul>",
            related: ["getting-started-main-window", "getting-started-using-help", "home-devices-card-menu"]
        },
        {
            id: "getting-started-profiles",
            section: "Getting started",
            title: "Work with profiles",
            body: "<p>A profile holds the modes, the actions on every input, the profile settings and the list of scripts.</p>"
                + "<h4>How to</h4>"
                + "<ul>"
                + "<li>To start a new profile, choose <b>File › New Profile</b> <a href=\"show:menu/File/New Profile\">Show me ›</a> (<b>Ctrl+N</b>). It is called \"Untitled\" and has one mode, \"Default\".</li>"
                + "<li>To open one, choose <b>File › Load Profile…</b> <a href=\"show:menu/File/Load Profile\">Show me ›</a> (<b>Ctrl+O</b>), or pick it from <b>File › Recent</b> (the last 5 you opened or saved).</li>"
                + "<li>To save, choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> (<b>Ctrl+S</b>). The first save of a new profile opens <b>File › Save Profile As…</b> <a href=\"show:menu/File/Save Profile As\">Show me ›</a> (<b>Ctrl+Shift+S</b>).</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The chooser opens in the folder you last used for a profile, or the profiles folder the first time.</li>"
                + "<li>New, Load, Recent and closing the program ask <b>Save</b>, <b>Discard</b> or <b>Cancel</b>, but only when there are unsaved changes.</li>"
                + "<li>An open Appearance panel with changes asks about those first.</li>"
                + "<li>A save that would leave out unfinished actions asks first (see <a href=\"topic:device-bindings-actions-safety-net\">Unfinished actions and recovery copies</a>).</li>"
                + "<li>While you have unsaved changes, the program keeps a recovery copy about every minute. Save, Discard and a normal close remove it.</li>"
                + "<li>If the program closes unexpectedly, opening that profile again offers the changes back (\"Unsaved Edits Found\": <b>Restore</b>, Discard or <b>Not now</b>). A profile never saved is offered at the next start.</li>"
                + "<li>A profile that won't load (damaged, or from an unknown version) shows why, and the open profile stays open.</li>"
                + "<li>A Recent file that won't open offers <b>Forget It</b> or <b>Keep</b>. Forget It takes it off Recent and the start-up list but doesn't delete the file; Keep leaves it there.</li>"
                + "<li>With <b>Load profiles automatically</b> <a href=\"show:option/Load profiles automatically\">Show me ›</a> on in <b>Options</b>, the profile you chose for a program loads and runs when that program comes to the front. See <a href=\"topic:options-profile-auto-load\">Load a profile automatically for a game</a>.</li>"
                + "</ul>",
            related: ["getting-started-start-up", "getting-started-saved-where", "options-profile-options", "modes-modes"]
        },
        {
            id: "getting-started-start-up",
            section: "Getting started",
            title: "What opens when the program starts",
            body: "<p>At start the program opens the profile you used last. It can also start by itself when you sign in to Windows.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>A profile given on the command line comes first (see <a href=\"topic:getting-started-command-line\">Start the program from a command line</a>).</li>"
                + "<li>If the last profile won't open, a new, empty profile opens instead, and the program says why.<ul>"
                + "<li><b>Forget It</b>: takes that profile off the start-up and <b>Recent</b> lists. The file itself stays.</li>"
                + "<li><b>Keep</b>: tries it again next time.</li>"
                + "</ul></li>"
                + "<li>If the program closed unexpectedly with unsaved changes, opening the profile offers them back (\"Unsaved Edits Found\"; see <a href=\"topic:device-bindings-actions-safety-net\">Unfinished actions and recovery copies</a>).</li>"
                + "<li>With <b>Start Gremlin-Platforms when Windows starts</b> on in <b>Options</b>, the program starts minimized when you sign in to Windows. It does not start Run.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The tray menu's <b>Start with Windows</b> is the same setting; the two always agree. It is off at first.</li>"
                + "<li>With <b>Minimize to tray</b> <a href=\"show:option/Minimize to tray\">Show me ›</a> on, the program starts in the tray instead.</li>"
                + "<li>If Windows' own Startup Apps list has the program switched off, both show it unticked with the note <b>Turned off in Windows' Startup Apps</b>. Ticking it then opens that Windows page.</li>"
                + "<li>Some messages come at most once, after the main window is up: the update check, a \"Settings Reset\" notice, and \"vJoy is not installed or not running\".</li>"
                + "<li>If an entry in the Logical Device or OSC files can't be read, it is skipped and the rest load. A note titled <b>Logical Device</b> or <b>OSC</b> names it.</li>"
                + "<li>The skipped entry stays in the file when you save, so nothing is lost.</li>"
                + "</ul>",
            related: ["getting-started-profiles", "getting-started-command-line", "options-profile-tray", "getting-started-wont-start"]
        },
        {
            id: "getting-started-command-line",
            section: "Getting started",
            title: "Start the program from a command line",
            body: "<p>A shortcut or a script can start the program with a profile, running, or out of sight. For example:</p>"
                + "<p><code>gremlin_platforms.exe --profile \"My flight.xml\" --enable --start-minimized</code></p>"
                + "<h4>What you see</h4>"
                + "<table>"
                + "<tr><th>Option</th><th>What it does</th></tr>"
                + "<tr><td><code>--profile &lt;file&gt;</code></td><td>Opens that profile.</td></tr>"
                + "<tr><td><code>--enable</code></td><td>Runs the profile once it is loaded.</td></tr>"
                + "<tr><td><code>--start-minimized</code></td><td>Starts minimized, or in the tray when <b>Minimize to tray</b> <a href=\"show:option/Minimize to tray\">Show me ›</a> is on.</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A relative path (no drive letter) is read from the folder the program was started in.</li>"
                + "<li>If the file doesn't exist, the program says \"Profile not found.\" It opens the last profile instead, or a new one when there is none.</li>"
                + "<li>Without <code>--profile</code>, the program opens the profile you used last (see <a href=\"topic:getting-started-start-up\">What opens when the program starts</a>).</li>"
                + "<li>In a shortcut, put the options after the program's path in the shortcut's <b>Target</b> box.</li>"
                + "</ul>",
            related: ["getting-started-start-up", "getting-started-run", "options-profile-tray"]
        },
        {
            id: "getting-started-close",
            section: "Getting started",
            title: "Close the program",
            body: "<p><b>File › Exit</b> <a href=\"show:menu/File/Exit\">Show me ›</a>, the tray's <b>Exit</b> and the X on the main window close the program the same way.</p>"
                + "<h4>What you see</h4>"
                + "<ol>"
                + "<li>A <b>Module Setup</b> or <b>Calibration</b> window with unsaved work asks first.</li>"
                + "<li>Then any open Appearance panel with changes asks, then the profile: <b>Save</b>, <b>Discard</b> or <b>Cancel</b>.</li>"
                + "<li>Then the Device Mapping Editor asks about its own changes.</li>"
                + "<li>Then the profile stops (see <a href=\"topic:getting-started-what-stop-releases\">What Stop lets go of</a>) and the program closes.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Cancel at any step keeps the program open, and calls off a restart or update that was waiting.</li>"
                + "<li><b>File › Exit</b> always closes the program.</li>"
                + "<li>With <b>Minimize to tray</b> <a href=\"show:option/Minimize to tray\">Show me ›</a> on, the X hides the window to the tray and the profile keeps running. With it off, the X closes the program.</li>"
                + "<li>While the window is in the tray, the program gives memory back to Windows (see <a href=\"topic:options-profile-tray\">Keep the program running in the tray</a>).</li>"
                + "<li>The main window's place and size are kept for next time.</li>"
                + "</ul>",
            related: ["getting-started-profiles", "options-profile-tray", "getting-started-what-stop-releases"]
        },
        {
            id: "getting-started-saved-where",
            section: "Getting started",
            title: "What is saved where",
            body: "<p>The program saves four things separately. Saving one does not save the others, except where noted.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Profile</b> (<b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a>): modes, actions, profile settings and scripts.</li>"
                + "<li><b>Logical Device</b>: its own file, shared by every profile. File › Save Profile saves it too when it changed (see <a href=\"topic:logical-device-saved\">Where the Logical Device is saved</a>).</li>"
                + "<li><b>Module</b>, one file per device: which controls the program uses, their names, the device picture, the device map, calibration, and a vJoy Output View's Appearance.<ul>"
                + "<li>Module Setup, the Device Mapping Editor, Calibration and the Appearance panels save it.</li>"
                + "<li>Saving an output module also saves the profile, when the profile already has a file.</li>"
                + "</ul></li>"
                + "<li>Program settings: Options, the Home layout and card sizes, window sizes and HidHide choices.<ul>"
                + "<li>They also hold the Appearance of the list pages (Device Bindings, Logical Device, Keyboard, OSC) and of the Xbox 360 Controller's Output View.</li>"
                + "<li>They are kept in your Gremlin Platforms folder (%USERPROFILE%\\Gremlin Platforms), even when you move the data folder.</li>"
                + "</ul></li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>File › Open Data Folder</b> <a href=\"show:menu/File/Open Data Folder\">Show me ›</a> opens the data folder chosen in Options.</li>"
                + "<li><b>File › Open Program Folder</b> <a href=\"show:menu/File/Open Program Folder\">Show me ›</a> opens the folder the program runs from.</li>"
                + "<li>After every save the bottom bar names the file that was written. Every save is also kept in <b>Tools › History</b> <a href=\"open:tools.history\">Open ›</a>.</li>"
                + "<li>A settings file that can't be read is kept as a copy, and the program starts with default settings. It says so once (\"Settings Reset\", with the copy's path).</li>"
                + "<li>A single setting that can't be read goes back to its default.</li>"
                + "</ul>",
            related: ["getting-started-profiles", "home-devices-module-files", "tools-history", "options-profile-options"]
        },
        {
            id: "getting-started-using-help",
            section: "Getting started",
            title: "Use Help",
            body: "<p>Help is one book in chapters. It explains every window and setting, and can point you to them.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Press <b>F1</b> or choose <b>Help › Help</b> <a href=\"show:menu/Help/Help\">Show me ›</a>. In the main window this opens the whole book.</li>"
                + "<li>Type in <b>Search Help…</b> (<b>Ctrl+F</b>). Topics with all your words, in any order, stay in the list, each with its count.</li>"
                + "<li>Press <b>Enter</b> or <b>F3</b> for the next match, and <b>Shift+F3</b> for the previous one, on into the next topic.</li>"
                + "<li>Press <b>Esc</b>, or × in the box, to clear the search. Help keeps the topic you were on.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The line under the box says \"N topics match\", or \"No topic mentions '…'\" when none does.</li>"
                + "<li>The open topic marks every match, and \"k of n\" shows where you are.</li>"
                + "<li>Chapter headings: click one to fold or unfold it. <b>Expand all</b> and <b>Collapse all</b> do every chapter.</li>"
                + "<li>The handle beside the list: drag it to change the list's width, up to half the window. Double-click it for the default width.</li>"
                + "<li>\"Open ›\" links open that window or Options page.</li>"
                + "<li>\"Show me ›\" links point at a menu item, a toolbar or mode bar button, or a setting, without choosing it. Help stays open beside it.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>In the Device Mapping Editor or the Device Library, F1 opens that window's chapter only. <b>View Full Help</b> shows the whole book.</li>"
                + "<li>When Help shows one chapter, <b>Search all of Help</b> adds matching topics from the other chapters.</li>"
                + "<li>In the whole book only the open topic's chapter starts unfolded. A search unfolds every chapter with a match until you clear it.</li>"
                + "<li>Help keeps the list's width for next time.</li>"
                + "<li>A grayed link can't be used now. Point at it to see why.</li>"
                + "<li><b>Help › About</b> <a href=\"open:help.about\">Open ›</a> shows the version and the program's GitHub page.</li>"
                + "</ul>",
            related: ["getting-started-menus", "getting-started-main-window"]
        },

        {
            id: "getting-started-nothing-reaches-vjoy",
            section: "Troubleshooting",
            title: "Nothing reaches vJoy",
            body: "<p>Your stick moves, but the vJoy Viewer or the game shows nothing. Check these in order.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Is vJoy installed? If a message says \"vJoy is not installed or not running\", choose <b>Open Drivers</b> in it. Install vJoy, then restart the program.</li>"
                + "<li>Is the profile running? The toolbar button reads <b>Stop</b> <a href=\"show:toolbar/Run\">Show me ›</a>, and the bottom bar reads Running.</li>"
                + "<li>Is the input ticked in its stick's <b>Module Setup</b>? Inputs that aren't ticked are ignored.</li>"
                + "<li>On <b>Device Bindings</b>, does the output read <b>(not claimed)</b>? Tick that output in <b>Output Module Setup</b> <a href=\"open:tools.configureOutput\">Open ›</a>.</li>"
                + "<li>Is the action in the running mode (the <b>Mode</b> box <a href=\"show:modebar\">Show me ›</a> under the toolbar)? Only that mode's actions, and its parents', run.</li>"
                + "<li>Still stuck? system.log in the logs folder notes each blocked output once. <b>Logs folder</b> <a href=\"show:option/Logs folder\">Show me ›</a> in <b>Options</b> says where it is.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li>\"vJoy N is in use by another program.\" means another program holds that vJoy device. The program tries again every 3 seconds and carries on by itself once the device is free.</li></ul>",
            related: ["getting-started-run", "home-devices-input-modules", "home-devices-vjoy-output", "modes-modes"]
        },
        {
            id: "getting-started-xbox-does-nothing",
            section: "Troubleshooting",
            title: "Xbox does nothing",
            body: "<p>The game doesn't see the Xbox controller, or it doesn't move. Check these in order.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the Xbox card and choose <b>Xbox Setup…</b>. It must say <b>ViGEmBus driver found</b>; if not, it says what to do.</li>"
                + "<li>Is the profile running? The pad appears only while it runs, once a <b>Map to Xbox</b> action first sends something.</li>"
                + "<li>Is the action Map to Xbox with the right pad and <b>Target</b>?</li>"
                + "<li>Is that pad on in Xbox Setup? A pad that is off shows a red ⚠.</li>"
                + "</ol>",
            related: ["home-devices-xbox-output", "device-bindings-actions-map-to-xbox", "tools-viewers", "getting-started-run"]
        },
        {
            id: "getting-started-key-does-not-fire",
            section: "Troubleshooting",
            title: "A key binding does nothing",
            body: "<p>A keyboard key has an action, but pressing it does nothing.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open <b>Input Module Setup</b> <a href=\"open:tools.configureInput\">Open ›</a> on the <b>Keyboard</b>.</li>"
                + "<li>Check that the key is ticked, then choose <b>Save Module</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li>Once you have saved the Keyboard's Module Setup, only the keys ticked there work.</li></ul>",
            related: ["home-devices-input-modules"]
        },
        {
            id: "getting-started-device-missing",
            section: "Troubleshooting",
            title: "A device is missing or seen twice",
            body: "<p>Find the case that matches what you see.</p>"
                + "<ul>"
                + "<li>Not on Home: right-click empty space on Home and check <b>Hidden Cards</b>.</li>"
                + "<li>A game sees both the stick and vJoy: hide the stick with <b>HidHide</b> <a href=\"open:tools.hidhide\">Open ›</a>.</li>"
                + "<li>Your bindings belong to a stick you replaced: open the <b>Device Library</b> <a href=\"open:tools.deviceLibrary\">Open ›</a> and use <b>Copy to Another Stick…</b> from the old stick.</li>"
                + "<li>When both sticks are plugged in, <b>Swap with Another Stick…</b> swaps their bindings.</li>"
                + "<li>A vJoy device is gone after a vJoy update: see <a href=\"topic:tools-drivers-vjoy-update\">Keep your vJoy devices through a vJoy update</a>.</li>"
                + "</ul>",
            related: ["home-devices-hidden-cards", "tools-hidhide", "home-devices-backups", "tools-drivers-vjoy-update"]
        },
        {
            id: "getting-started-wont-start",
            section: "Troubleshooting",
            title: "The program doesn't start",
            body: "<p>What you see tells you what went wrong.</p>"
                + "<ul>"
                + "<li>If the program can't start its controller reader, a page says \"An error occurred during startup:\" with the reason. <b>OK</b> closes the program.</li>"
                + "<li>Any other failure at start shows the box \"Gremlin-Platforms could not start.\" with the reason, the last lines of the error and the logs folder.</li>"
                + "<li>In that box, press <b>Ctrl+C</b> to copy the message for a problem report.</li>"
                + "<li>If nothing starts at all on a new PC, run setup again. Or install the <b>Microsoft Visual C++ Runtime</b> yourself (Microsoft calls it the Visual C++ 2015-2022 Redistributable, x64).</li>"
                + "<li>If it asks about another copy, see <a href=\"topic:getting-started-another-copy\">Another copy is already running</a>.</li>"
                + "</ul>",
            related: ["getting-started-another-copy", "getting-started-error-messages", "getting-started-save-diagnostics"]
        },
        {
            id: "getting-started-another-copy",
            section: "Troubleshooting",
            title: "Another copy is already running",
            body: "<p>Only one copy of the program can own vJoy. When you start a copy while another runs, it asks what to do.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Yes</b>: closes the other copies and starts this one. Changes not saved in the other copies are lost.</li>"
                + "<li><b>No</b>: starts this copy anyway. vJoy may not respond, and the History may miss some entries.</li>"
                + "<li><b>Cancel</b>: doesn't start this copy.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The question lists the other copies' process IDs and open windows.</li>"
                + "<li>A copy running with no visible window may be hung; Yes closes it too.</li>"
                + "<li>If the other copy can't be closed, the question starts \"The other copy could not be closed.\" and asks again.</li>"
                + "</ul>",
            related: ["getting-started-wont-start", "tools-history"]
        },
        {
            id: "getting-started-error-messages",
            section: "Troubleshooting",
            title: "An error message appears",
            body: "<p>Error boxes say what happened. Their details wrap, and <b>Copy Details</b> copies them.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>\"An unhandled exception occurred.\" means something went wrong that the program didn't expect. The details are also written to system.log in the logs folder.</li>"
                + "<li>If the program closes suddenly, crash.log in the logs folder records where it stopped. Earlier crashes are kept in the same file.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A sudden close doesn't lose unsaved profile changes. The next open of the profile offers them back (see <a href=\"topic:device-bindings-actions-safety-net\">Unfinished actions and recovery copies</a>).</li>"
                + "<li>To report a problem, save one zip with <b>Help › Save Diagnostics…</b> <a href=\"show:menu/Help/Save Diagnostics\">Show me ›</a>.</li>"
                + "</ul>",
            related: ["getting-started-save-diagnostics", "tools-live-log"]
        },
        {
            id: "getting-started-save-diagnostics",
            section: "Troubleshooting",
            title: "Save diagnostics for a problem report",
            body: "<p>Save Diagnostics puts what a problem report needs in one zip file.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Help › Save Diagnostics…</b> <a href=\"show:menu/Help/Save Diagnostics\">Show me ›</a>, or <b>Save Diagnostics…</b> on the <b>Debug</b> tab of the <b>Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a>.</li>"
                + "<li>To add the open profile, tick <b>Include the open profile</b>.</li>"
                + "<li>Choose <b>Save…</b> and pick where to save the zip.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<p>The zip holds:</p>"
                + "<ul>"
                + "<li>the program's logs, with trace.log when you have used Tracing</li>"
                + "<li>the main window's state and its last 200 window events</li>"
                + "<li>the program's current state, as tracing records it</li>"
                + "<li>your settings</li>"
                + "<li>the device list: names, IDs, kinds, and whether each is connected</li>"
                + "<li>the program and Windows versions</li>"
                + "<li>the <b>Input Tester</b>'s log and results, when you have used it</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The open profile is left out unless you tick the box.</li>"
                + "<li>Your user name in folder paths is replaced by &lt;user&gt;.</li>"
                + "<li>The save opens in the folder you last saved diagnostics to, or on the Desktop the first time.</li>"
                + "<li>When it is done it says where the zip went. If it can't be written, it says which file, which folder and why.</li>"
                + "</ul>",
            related: ["tools-live-log", "getting-started-error-messages"]
        },

        {
            id: "getting-started-q-first-steps",
            section: "Common questions",
            title: "Where do I start?",
            body: "<p>Set up an input module for your stick and an output module for vJoy (Xbox needs none). Then add actions and choose <b>Run</b>. See <a href=\"topic:getting-started-first-setup\">Set up your first profile</a>.</p>",
            related: ["getting-started-first-setup"]
        },
        {
            id: "getting-started-q-not-saved",
            section: "Common questions",
            title: "Why is my change gone after I restart?",
            body: "<p>Actions, modes and profile settings are kept only when you save the profile with <b>File › Save Profile</b>. If the program closed unexpectedly, open the profile again and choose <b>Restore</b> in \"Unsaved Edits Found\". See <a href=\"topic:getting-started-saved-where\">What is saved where</a>.</p>",
            related: ["getting-started-saved-where"]
        },
        {
            id: "getting-started-q-empty-at-start",
            section: "Common questions",
            title: "Why did an empty profile open at start?",
            body: "<p>The profile you used last didn't open, and the program said why. Choose <b>Keep</b> to try it again next time, or load it with <b>File › Load Profile…</b>. See <a href=\"topic:getting-started-start-up\">What opens when the program starts</a>.</p>",
            related: ["getting-started-start-up"]
        },
        {
            id: "getting-started-q-game-no-input",
            section: "Common questions",
            title: "Why doesn't my game see any input?",
            body: "<p>The profile must be running, and the input must be ticked in its stick's Module Setup. For vJoy, the output must be ticked in its Module Setup too. See <a href=\"topic:getting-started-nothing-reaches-vjoy\">Nothing reaches vJoy</a>.</p>",
            related: ["getting-started-nothing-reaches-vjoy", "getting-started-xbox-does-nothing"]
        },
        {
            id: "getting-started-q-report-problem",
            section: "Common questions",
            title: "How do I report a problem?",
            body: "<p>Save one zip with <b>Help › Save Diagnostics…</b> and send it with your report. See <a href=\"topic:getting-started-save-diagnostics\">Save diagnostics for a problem report</a>.</p>",
            related: ["getting-started-save-diagnostics"]
        }
    ]
}
