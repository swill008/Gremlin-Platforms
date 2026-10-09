// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Getting started (incl. general troubleshooting).

.pragma library

var chapter = { id: "getting-started", title: "Getting started" }

function topics() {
    return [
        {
            id: "getting-started-overview",
            section: "Getting started",
            title: "How Gremlin-Platforms works",
            body: "<p>Gremlin-Platforms turns your physical controllers into the virtual devices a game reads. Every input follows one path:</p>"
                + "<p>Physical device → input module → actions (profile) → output module → vJoy or Xbox driver → game</p>"
                + "<ul>"
                + "<li><b>Input module</b>: one per physical device. It claims the buttons, axes and hats Gremlin-Platforms may use. An input that is not claimed is ignored.</li>"
                + "<li><b>Actions</b>: stored in the profile. They say what each claimed input does: send it to vJoy or Xbox, press keys, run a macro, change mode, and so on.</li>"
                + "<li><b>Output module</b>: one per vJoy device, plus one for the Xbox controller. It is the only part that talks to the driver.</li>"
                + "</ul>"
                + "<p>Actions can also press keys, move the mouse, or send to the Logical Device, a virtual device inside the program with actions of its own.</p>",
            related: ["getting-started-first-setup", "getting-started-main-window", "logical-device-about", "getting-started-saved-where"]
        },
        {
            id: "getting-started-first-setup",
            section: "Getting started",
            title: "Set up your first profile",
            body: "<p>Use these steps to go from a plugged-in stick to a running profile.</p>"
                + "<ol>"
                + "<li>Install <b>vJoy</b> and configure its devices. For an Xbox controller, install <b>ViGEmBus</b>. Neither driver ships with this program.</li>"
                + "<li>On <b>Home</b>, right-click each physical device and choose <b>Module</b> › <b>Module Setup…</b>. Press the controls you will use, or tick them, then choose <b>Save Module</b>.</li>"
                + "<li>Right-click each vJoy device and choose <b>Module</b> › <b>Module Setup…</b>. Tick the outputs you will use, then choose <b>Save Module</b>. The Xbox controller needs no setup.</li>"
                + "<li>Double-click a physical device to open <b>Configuration</b>. Choose <b>Add Action</b> on an input, for example <b>Map to vJoy</b>, then <b>OK</b>.</li>"
                + "<li>Choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> (<b>Ctrl+S</b>).</li>"
                + "<li>Choose <b>Run</b> <a href=\"show:toolbar/Run\">Show me ›</a> on the toolbar. Use the <b>vJoy Viewer</b> <a href=\"open:tools.vjoyViewer\">Open ›</a> or <b>Xbox Viewer</b> <a href=\"open:tools.xboxViewer\">Open ›</a> to watch the result.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li><b>Tools › Mapping › Auto Mapper</b> <a href=\"open:tools.autoMapper\">Open ›</a> creates the Map to vJoy actions for a whole device in one step (see <a href=\"topic:tools-auto-mapper\">Create actions with the Auto Mapper</a>).</li></ul>",
            related: ["getting-started-overview", "home-devices-input-modules", "configuration-actions-add-action", "getting-started-run"]
        },
        {
            id: "getting-started-main-window",
            section: "Getting started",
            title: "The main window",
            body: "<p>The main window shows one page at a time (Home, Configuration and others) under a toolbar and a mode bar.</p>"
                + "<ul>"
                + "<li>Title bar: the program's name and version first, then the profile's name, for example \"Gremlin-Platforms R1 1.0.30 - Flight.xml\". A <b>*</b> before the profile's name means there are unsaved changes; a profile not saved yet is called \"Untitled\". Other windows show their own name after the program's, for example \"Gremlin-Platforms R1 1.0.30 - Device Library\".</li>"
                + "<li>Toolbar, left to right: <b>Home</b>, <b>Run</b> <a href=\"show:toolbar/Run\">Show me ›</a> (reads <b>Stop</b> while the profile runs), <b>vJoy Viewer</b> and <b>Xbox Viewer</b> (each opens its viewer, or closes it when it is open), <b>Button Map</b> (a blank Button Map), <b>Device Library</b> <a href=\"show:toolbar/Device Library\">Show me ›</a> (every device and its saved setups), <b>Logical Device</b> and <b>Options</b> <a href=\"show:toolbar/Options\">Show me ›</a>. In a narrow window the buttons show icons only; rest the pointer on one to see its name.</li>"
                + "<li>Mode bar, under the toolbar on every page: <b>Mode</b> <a href=\"show:modebar\">Show me ›</a>, its list and <b>Manage Modes</b> <a href=\"show:modebar/Manage Modes\">Show me ›</a> always on the left, then the open page's own controls (on Home: <b>Compact view</b> and <b>Layout</b>). When the window is narrow, the page's controls scroll sideways; Mode and Manage Modes stay put.</li>"
                + "<li>Bottom bar: the status (Running or Stopped) and what the last save wrote.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li><b>F1</b> opens Help with the whole book (see <a href=\"topic:getting-started-using-help\">Use Help</a>).</li></ul>",
            related: ["getting-started-run", "modes-mode-box", "getting-started-menus", "home-devices-home"]
        },
        {
            id: "getting-started-install",
            section: "Getting started",
            title: "Install and update the program",
            body: "<p>Each release on GitHub has two downloads:</p>"
                + "<ul>"
                + "<li>Gremlin-Platforms-R1-X.Y.Z-Setup.exe, the installer. It installs for your Windows user only and needs no administrator rights. The suggested folder is %LOCALAPPDATA%\\Programs\\Gremlin-Platforms; you can choose another folder you can write to. It adds a Start menu entry, an optional desktop shortcut, and an uninstaller in Windows Settings › Apps.</li>"
                + "<li>Gremlin-Platforms-R1-X.Y.Z.zip, the portable copy. Unzip it anywhere outside Program Files and run gremlin_platforms.exe.</li>"
                + "</ul>"
                + "<p>To check for a newer version:</p>"
                + "<ol>"
                + "<li>Choose <b>Help › Check for Updates</b> <a href=\"show:menu/Help/Check for Updates\">Show me ›</a>. It asks GitHub for the latest release and shows what's new in it.</li>"
                + "<li>On an installed copy, choose <b>Update Now</b>. It downloads the installer, checks it against the SHA-256 checksum GitHub reports, closes the program the usual way (asking about unsaved changes), installs, and starts the new version.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The window shows the New, Changed and Fixed notes. When you skipped versions, each one's notes follow under \"What's new in &lt;version&gt;\", newest first. <b>Full release notes on GitHub</b> opens the release page. Without notes or a connection it says \"Release notes unavailable.\" and updating still works.</li>"
                + "<li>Closing the window during a download cancels it and deletes the part already downloaded.</li>"
                + "<li>After an update the program says \"Updated\" once. If an update didn't finish, the next start opens this window to say so, with setup's log and <b>Try Again</b>; the previous version is put back.</li>"
                + "<li>With <b>Check for updates</b> <a href=\"show:option/Check for updates\">Show me ›</a> on in <b>Options</b> (on by default), the program also checks at start and only speaks up when there is a newer version. <b>Skip This Version</b> stops it offering that version.</li>"
                + "<li>A portable copy, or one run from source, only points you to the release page.</li>"
                + "<li>Updates and uninstalling never touch your profiles, modules or settings; they are kept in your Gremlin Platforms folder.</li>"
                + "</ul>",
            related: ["getting-started-saved-where", "options-profile-options"]
        },
        {
            id: "getting-started-run",
            section: "Getting started",
            title: "Run and stop the profile",
            body: "<p>Running the profile sends your actions to vJoy, Xbox and the Logical Device; while it is stopped you only edit.</p>"
                + "<ol>"
                + "<li>Choose <b>Run</b> <a href=\"show:toolbar/Run\">Show me ›</a> on the toolbar. While the profile runs, the button reads <b>Stop</b> and uses the accent color.</li>"
                + "<li>After pressing Run, move each throttle, brake pedal or slider that rests away from the middle a little (see Good to know).</li>"
                + "<li>To stop, choose <b>Stop</b>. Stop never asks.</li>"
                + "</ol>"
                + "<p>The bottom bar shows <b>Status</b> (Running, Stopped, or Running (Paused), and 'unsaved changes' when the running profile has some). The <b>Mode</b> box on the mode bar picks the mode that runs (see <a href=\"topic:modes-mode-box\">Choose the mode you edit and run</a>).</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>When an action editor has changes that are not saved, Run asks first: <b>Save</b>, <b>Discard</b> or <b>Cancel</b>. The profile runs as saved.</li>"
                + "<li>If Run fails partway, the program stops by itself, shows one error, and the status reads Stopped.</li>"
                + "<li>While the profile runs, the action editors are locked (\"Profile running: stop it to edit\").</li>"
                + "<li>The program knows where an axis is only after that axis has moved. Until then it treats the axis as centered, so a control resting away from the middle is sent as center at first.</li>"
                + "<li>Running does not hide controllers from games; use HidHide for that.</li>"
                + "<li>A controller plugged in or removed while running is handled by <b>Device change behavior</b> <a href=\"show:option/Device change behavior\">Show me ›</a> in <b>Options</b>: Stop, Ignore, or Reload.</li>"
                + "</ul>",
            related: ["getting-started-what-stop-releases", "modes-mode-box", "tools-hidhide", "getting-started-nothing-reaches-vjoy"]
        },
        {
            id: "getting-started-what-stop-releases",
            section: "Getting started",
            title: "What Stop lets go of",
            body: "<p>Stop, and closing the program, end everything the profile was doing, so nothing stays pressed or moving.</p>"
                + "<ul>"
                + "<li>Keys held by Map to Keyboard, a macro or a script are released, last pressed first.</li>"
                + "<li>Mouse buttons still held are released, and mouse motion stops.</li>"
                + "<li>Macros end at their next step; a Pause step ends at once.</li>"
                + "<li>Sounds and speech stop, and nothing waiting to play is played.</li>"
                + "<li>Tempo, Double Tap and Smart Toggle never fire after Stop.</li>"
                + "<li>Each vJoy device is left at rest: every button up, every hat centered, every axis centered. Each Xbox pad is unplugged.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li>The next Run starts clean: nothing from the last Run carries over.</li></ul>",
            related: ["getting-started-run", "configuration-actions-macro", "configuration-actions-play-sound"]
        },
        {
            id: "getting-started-menus",
            section: "Getting started",
            title: "Menus, keys and the Command Palette",
            body: "<p>Every menu in the program works the same way, in light and dark mode.</p>"
                + "<ul>"
                + "<li>Menus show only what you can use now. They leave out what does not apply (<b>View › Home</b> while you are on Home, <b>File › Recent</b> before you have opened a profile). Nothing is greyed out, except now and then an item whose tooltip says why it can't be used yet. Rest the pointer on an item to see its tooltip.</li>"
                + "<li>Right-click menus start with the name of what you clicked and its most used commands, then sections (▸) that open one at a time. The section you opened last opens again next time. Some show <b>Undo</b> and <b>Redo</b> beside the name.</li>"
                + "<li>In a menu, <b>Up</b> and <b>Down</b> move, <b>Right</b> and <b>Left</b> open or close a section or step a row of choices, <b>Enter</b> runs, <b>Esc</b> closes.</li>"
                + "<li>Every question before a delete, remove or clear names what goes and ends \"You can restore it from Tools › History.\" or \"This can't be undone.\" Its red button is named for the action, for example <b>Delete Device</b>; <b>Cancel</b> has the focus, and <b>Enter</b> and <b>Esc</b> both cancel, so only a click on the red button goes ahead.</li>"
                + "<li>Search boxes (Help, History, Options, the Logical Device page, Layers and the Device Library) work the same way: <b>Ctrl+F</b> goes to the box, × clears it, <b>Esc</b> clears it and leaves the box, and the line under it says \"N found\" or \"Nothing matches\" (in Help, \"N topics match\").</li>"
                + "<li>A file or folder chooser opens in the folder you last used for that kind of file (profiles, scripts, pictures, Device Packs, module files, exports, logs), even after a restart.</li>"
                + "<li>Dropdown lists of 10 or more entries have a search box: type part of a name, <b>Up</b> and <b>Down</b> move, <b>Enter</b> picks.</li>"
                + "<li><b>Command Palette</b>: <b>Ctrl+K</b> (or <b>View › Command Palette…</b> <a href=\"show:menu/View/Command Palette\">Show me ›</a>) lists every menu command you can use now. Type part of a name and press <b>Enter</b>. Shortcuts show beside the commands.</li>"
                + "<li>To leave a text box you are typing in, press <b>Esc</b> or click anywhere outside it. What you typed is kept. In Module Setup, Esc does nothing, as sticks can send it; click away instead.</li>"
                + "<li>To rename, press <b>F2</b> or choose <b>Rename</b>: the cursor goes in the name with all of it selected, so you can type the new one straight away. <b>Enter</b> or a click elsewhere saves it; <b>Esc</b> keeps the old name.</li>"
                + "<li><b>Esc</b> closes Options, Help, About and Check for Updates. Windows you use a stick in ignore Esc.</li>"
                + "</ul>"
                + "<p>Shortcuts in the main window:</p>"
                + "<ul>"
                + "<li><b>Ctrl+N</b> new profile, <b>Ctrl+O</b> load, <b>Ctrl+S</b> save, <b>Ctrl+Shift+S</b> save as.</li>"
                + "<li><b>Ctrl+K</b> Command Palette, <b>F1</b> Help.</li>"
                + "</ul>",
            related: ["getting-started-main-window", "getting-started-using-help", "home-devices-card-menu"]
        },
        {
            id: "getting-started-profiles",
            section: "Getting started",
            title: "Work with profiles",
            body: "<p>A profile holds the modes, the actions on every input, the profile settings, and the list of scripts.</p>"
                + "<ul>"
                + "<li><b>File › New Profile</b> (<b>Ctrl+N</b>) starts an empty profile, \"Untitled\", with one mode, \"Default\".</li>"
                + "<li><b>File › Load Profile…</b> <a href=\"show:menu/File/Load Profile\">Show me ›</a> (<b>Ctrl+O</b>) opens one; <b>File › Recent</b> lists the last 5 you opened or saved. The chooser opens in the folder you last used for a profile.</li>"
                + "<li><b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> (<b>Ctrl+S</b>) writes it to disk. The first save of a new profile opens <b>Save Profile As…</b> (<b>Ctrl+Shift+S</b>) in the folder you last used for a profile, or the profiles folder the first time.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>New, Load, Recent and closing the program ask <b>Save</b>, <b>Discard</b> or <b>Cancel</b> only when there are unsaved changes. Open Appearance panels with changes ask first.</li>"
                + "<li>A save that would leave out unfinished actions asks first (see <a href=\"topic:configuration-actions-safety-net\">Unfinished actions and recovery copies</a>).</li>"
                + "<li>While there are unsaved changes, the program keeps a recovery copy of them about every minute. If it closes unexpectedly, the next time you open that profile it offers them back (\"Unsaved Edits Found\": <b>Restore</b>, <b>Discard</b> or <b>Not now</b>). Save, Discard and a normal close remove the copy.</li>"
                + "<li>A profile that won't load (damaged or from an unknown version) shows why, and the profile that was open stays open. A Recent file that won't open offers <b>Forget It</b> (off Recent and start-up; the file stays) or <b>Keep</b>.</li>"
                + "<li>With <b>Load profiles automatically</b> <a href=\"show:option/Load profiles automatically\">Show me ›</a> on in <b>Options</b>, the profile chosen for a program loads and runs when that program comes to the front.</li>"
                + "</ul>",
            related: ["getting-started-start-up", "getting-started-saved-where", "options-profile-options", "modes-modes"]
        },
        {
            id: "getting-started-start-up",
            section: "Getting started",
            title: "What opens when the program starts",
            body: "<p>At start the program opens the profile you used last.</p>"
                + "<ul>"
                + "<li>A profile given on the command line wins (see <a href=\"topic:getting-started-command-line\">Start the program from a command line</a>).</li>"
                + "<li>If the last profile won't open, a new, empty profile is open instead and the program says why. Choose <b>Forget It</b> to take that profile off the start-up and <b>Recent</b> lists (the file itself stays), or <b>Keep</b> to try it again next time.</li>"
                + "<li>If the program closed unexpectedly with unsaved changes, opening the profile offers them back: \"Unsaved Edits Found\" (see <a href=\"topic:configuration-actions-safety-net\">Unfinished actions and recovery copies</a>).</li>"
                + "<li>The update check, a \"Settings Reset\" notice and the vJoy setup message each come at most once, after the main window is up.</li>"
                + "</ul>",
            related: ["getting-started-profiles", "getting-started-command-line", "getting-started-wont-start"]
        },
        {
            id: "getting-started-command-line",
            section: "Getting started",
            title: "Start the program from a command line",
            body: "<p>A shortcut or a script can start the program with a profile, running, or out of sight. For example:</p>"
                + "<p><code>gremlin_platforms.exe --profile \"My flight.xml\" --enable --start-minimized</code></p>"
                + "<ul>"
                + "<li><code>--profile &lt;file&gt;</code> opens that profile. A path that isn't full is read from the folder the program was started in. If the file doesn't exist, it says \"Profile not found.\" and opens the last profile instead (or a new one when there is none).</li>"
                + "<li><code>--enable</code> runs the profile once it is loaded.</li>"
                + "<li><code>--start-minimized</code> starts minimized, or in the tray when <b>Minimize to tray</b> <a href=\"show:option/Minimize to tray\">Show me ›</a> is on.</li>"
                + "</ul>",
            related: ["getting-started-start-up", "getting-started-run", "options-profile-tray"]
        },
        {
            id: "getting-started-close",
            section: "Getting started",
            title: "Close the program",
            body: "<p><b>File › Exit</b>, the tray's <b>Exit</b> and the X on the main window close the program the same way.</p>"
                + "<ol>"
                + "<li>A <b>Module Setup</b> or <b>Calibration</b> window with unsaved work asks first.</li>"
                + "<li>Then open panels ask, then the profile: <b>Save</b>, <b>Discard</b> or <b>Cancel</b>.</li>"
                + "<li>Then the Button Map asks about its own changes.</li>"
                + "<li>Then the profile stops (see <a href=\"topic:getting-started-what-stop-releases\">What Stop lets go of</a>) and the program closes.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Cancel</b> at any step keeps the program open, and calls off a restart or update that was waiting.</li>"
                + "<li>With <b>Minimize to tray</b> <a href=\"show:option/Minimize to tray\">Show me ›</a> on, the X hides the window to the tray and the profile keeps running. With it off, the X closes the program.</li>"
                + "<li>The main window's place and size are kept for next time.</li>"
                + "</ul>",
            related: ["getting-started-profiles", "options-profile-tray", "getting-started-what-stop-releases"]
        },
        {
            id: "getting-started-saved-where",
            section: "Getting started",
            title: "What is saved where",
            body: "<p>The program keeps three separate stores. Saving one does not save the others, except where noted.</p>"
                + "<ul>"
                + "<li>Profile (<b>File › Save Profile</b>): modes, actions, profile settings, scripts.</li>"
                + "<li>Module file, one per device: claims, friendly names, the device picture, the Button Map layout, the Appearance of its Configuration page or Output View, and its calibration. Input and Output Module Setup, the Button Map, Calibration and the Appearance panels write it. Saving an output module also saves the profile when the profile already has a file.</li>"
                + "<li>Program settings: Options, Home layout and card sizes, window sizes, HidHide choices, and the Logical Device's Appearance. They are kept in configuration.json in your Gremlin Platforms folder (%USERPROFILE%\\Gremlin Platforms), even when you move the data folder.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>File › Open Data Folder</b> <a href=\"show:menu/File/Open Data Folder\">Show me ›</a> opens the data folder chosen in Options; <b>File › Open Program Folder</b> <a href=\"show:menu/File/Open Program Folder\">Show me ›</a> opens the folder the program runs from.</li>"
                + "<li>After every save the bottom bar names the file that was written. Every save is also kept in the History (<b>Tools › History</b> <a href=\"open:tools.history\">Open ›</a>).</li>"
                + "<li>A settings file that can't be read is kept as configuration.json.bad-&lt;date and time&gt;; the program starts with default settings and says so once (\"Settings Reset\", with the copy's path). A single setting that can't be read goes back to its default.</li>"
                + "</ul>",
            related: ["getting-started-profiles", "home-devices-module-files", "tools-history", "options-profile-options"]
        },
        {
            id: "getting-started-using-help",
            section: "Getting started",
            title: "Use Help",
            body: "<p>Help is one book in chapters. <b>F1</b> or <b>Help › Help</b> <a href=\"show:menu/Help/Help\">Show me ›</a> in the main window opens the whole book; in the Button Map or the Device Library it opens that chapter only, and <b>View Full Help</b> shows the whole book.</p>"
                + "<ul>"
                + "<li>Search: type in <b>Search Help…</b> (<b>Ctrl+F</b>). The list keeps the topics that hold all your words, each with its count, and says \"N topics match\". In the open topic, <b>Enter</b> or <b>F3</b> goes to the next match and <b>Shift+F3</b> to the previous one. × in the box or <b>Esc</b> clears the search.</li>"
                + "<li>When Help shows one chapter, <b>Search all of Help</b> adds matching topics from the other chapters.</li>"
                + "<li>Click a chapter heading to fold or unfold it; <b>Expand all</b> and <b>Collapse all</b> do every chapter. Drag the handle beside the list to widen it; double-click the handle for the default width.</li>"
                + "<li>An \"Open ›\" link opens that window or Options page. A \"Show me ›\" link points at a menu item, toolbar button or setting without choosing it. A greyed link can't be used now; rest the pointer on it to see why.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li><b>Help › About</b> <a href=\"open:help.about\">Open ›</a> shows the version and the program's GitHub page.</li></ul>",
            related: ["getting-started-menus", "getting-started-main-window"]
        },

        {
            id: "getting-started-nothing-reaches-vjoy",
            section: "Troubleshooting",
            title: "Nothing reaches vJoy",
            body: "<p>Check these in order.</p>"
                + "<ol>"
                + "<li>Is vJoy installed? The message \"vJoy is not installed or not running\" means install vJoy, then restart the program.</li>"
                + "<li>Is the profile running? The toolbar button should read <b>Stop</b> <a href=\"show:toolbar/Run\">Show me ›</a> and the bottom bar Running.</li>"
                + "<li>Is the input claimed in its input module? Inputs that are not claimed are ignored.</li>"
                + "<li>Does the wire show <b>(not claimed)</b>? Claim that output in <b>Output Module Setup</b>.</li>"
                + "<li>Is the action in the running mode (the <b>Mode</b> box <a href=\"show:modebar\">Show me ›</a> under the toolbar)? Only that mode's actions, and its parents', run.</li>"
                + "<li>system.log in the logs folder (see the folders in <b>Options</b>) notes each blocked output once.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li>\"vJoy N is in use by another program.\" means another program holds that vJoy device. The program tries again every 3 seconds and carries on by itself once the device is free.</li></ul>",
            related: ["getting-started-run", "home-devices-input-modules", "home-devices-vjoy-output", "modes-modes"]
        },
        {
            id: "getting-started-xbox-does-nothing",
            section: "Troubleshooting",
            title: "Xbox does nothing",
            body: "<p>Check these in order.</p>"
                + "<ol>"
                + "<li>Open the Xbox page or the <b>Xbox Viewer</b> <a href=\"open:tools.xboxViewer\">Open ›</a>: the check at the top must say <b>ViGEmBus driver found</b>. If not, it says what to do.</li>"
                + "<li>The pad exists only while the profile runs and after a Map to Xbox action has sent.</li>"
                + "<li>Check that the action is <b>Map to Xbox</b> with <b>Xbox 360 Controller</b> and the right <b>Target</b>.</li>"
                + "</ol>",
            related: ["home-devices-xbox-output", "configuration-actions-map-to-xbox", "tools-viewers", "getting-started-run"]
        },
        {
            id: "getting-started-key-does-not-fire",
            section: "Troubleshooting",
            title: "A key binding does not fire",
            body: "<p>Open <b>Input Module Setup</b> <a href=\"open:tools.configureInput\">Open ›</a> on <b>Keyboard</b> and check the key is claimed. Once you save a keyboard choice, only claimed keys fire.</p>",
            related: ["home-devices-input-modules"]
        },
        {
            id: "getting-started-device-missing",
            section: "Troubleshooting",
            title: "A device is missing or seen twice",
            body: "<ul>"
                + "<li>Not on Home: right-click empty space on Home and check <b>Hidden Cards</b>.</li>"
                + "<li>A game sees both the physical stick and vJoy: hide the physical stick with HidHide.</li>"
                + "<li>Bindings belong to a device that was replaced: open the <b>Device Library</b> <a href=\"open:tools.deviceLibrary\">Open ›</a> and use <b>Copy to Another Stick…</b> from the old stick (or <b>Swap with Another Stick…</b> when both are plugged in).</li>"
                + "</ul>",
            related: ["home-devices-hidden-cards", "tools-hidhide", "home-devices-backups"]
        },
        {
            id: "getting-started-wont-start",
            section: "Troubleshooting",
            title: "The program doesn't start",
            body: "<ul>"
                + "<li>If the joystick driver can't start, a page says \"An error occurred during startup:\" with the reason. <b>OK</b> closes the program.</li>"
                + "<li>Any other failure at start shows a box, \"Gremlin-Platforms could not start.\", with the reason, the last lines of the error and the logs folder. Press <b>Ctrl+C</b> to copy the message for a problem report.</li>"
                + "<li>If it asks about another copy, see <a href=\"topic:getting-started-another-copy\">Another copy is already running</a>.</li>"
                + "</ul>",
            related: ["getting-started-another-copy", "getting-started-error-messages", "getting-started-save-diagnostics"]
        },
        {
            id: "getting-started-another-copy",
            section: "Troubleshooting",
            title: "Another copy is already running",
            body: "<p>Only one copy of the program can own vJoy. When you start a copy while another runs, it asks:</p>"
                + "<ul>"
                + "<li><b>Yes</b>: close the other copies and start this one. Changes not saved in the other copies are lost.</li>"
                + "<li><b>No</b>: start this copy anyway. vJoy may not respond, and the History may miss some entries.</li>"
                + "<li><b>Cancel</b>: don't start this copy.</li>"
                + "</ul>",
            related: ["getting-started-wont-start", "tools-history"]
        },
        {
            id: "getting-started-error-messages",
            section: "Troubleshooting",
            title: "An error message appears",
            body: "<ul>"
                + "<li>Error boxes say what happened; their details wrap, and <b>Copy Details</b> copies them.</li>"
                + "<li>\"An unhandled exception occurred.\" means something went wrong that the program didn't expect. The details are also written to system.log in the logs folder.</li>"
                + "<li>If the program closes suddenly, crash.log in the logs folder records where it stopped; earlier crashes are kept in the same file.</li>"
                + "<li>Unsaved profile changes are not lost in a sudden close: a recovery copy is kept about every minute, and the next open of the profile offers it back with <b>Restore</b>, <b>Discard</b> or <b>Not now</b> (see <a href=\"topic:configuration-actions-safety-net\">Unfinished actions and recovery copies</a>).</li>"
                + "</ul>"
                + "<p>To report it, save one zip with <b>Help › Save Diagnostics…</b> <a href=\"show:menu/Help/Save Diagnostics\">Show me ›</a>.</p>",
            related: ["getting-started-save-diagnostics", "tools-live-log"]
        },
        {
            id: "getting-started-save-diagnostics",
            section: "Troubleshooting",
            title: "Save diagnostics for a problem report",
            body: "<p>Save Diagnostics puts everything needed for a problem report in one zip: the program's logs, its settings, the device list (names, ids, kinds, connected) and the program and Windows versions.</p>"
                + "<ol>"
                + "<li>Choose <b>Help › Save Diagnostics…</b> <a href=\"show:menu/Help/Save Diagnostics\">Show me ›</a> (or <b>Save Diagnostics…</b> on the Live Log Reader's <b>Debug</b> tab).</li>"
                + "<li>To add the open profile, tick <b>Include the open profile</b>.</li>"
                + "<li>Choose <b>Save…</b> and pick where. It opens in the folder you last saved diagnostics to, or on the Desktop the first time.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Your user name in folder paths is replaced by &lt;user&gt;.</li>"
                + "<li>When it is done it says where the zip went; if it can't be written it says which file, which folder and why.</li>"
                + "</ul>",
            related: ["tools-live-log", "getting-started-error-messages"]
        },

        {
            id: "getting-started-q-first-steps",
            section: "Common questions",
            title: "Where do I start?",
            body: "<p>Set up an input module for your stick, an output module for vJoy, add actions and choose <b>Run</b>. See <a href=\"topic:getting-started-first-setup\">Set up your first profile</a>.</p>",
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
            body: "<p>The profile must be running, and the input and the output must both be claimed. See <a href=\"topic:getting-started-nothing-reaches-vjoy\">Nothing reaches vJoy</a>.</p>",
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
