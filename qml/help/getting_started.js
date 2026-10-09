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
            related: ["getting-started-first-setup", "home-devices-input-modules", "logical-device-about", "getting-started-saved-where"]
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
                + "<li>Choose <b>File › Save Profile</b> (<b>Ctrl+S</b>).</li>"
                + "<li>Choose <b>Run</b> to run the profile. Use the <b>vJoy Viewer</b> or <b>Xbox Viewer</b> to watch the result.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li><b>Tools › Mapping › Auto Mapper</b> creates the Map to vJoy actions for a whole device in one step (see <a href=\"topic:tools-auto-mapper\">Create actions with the Auto Mapper</a>).</li></ul>",
            related: ["getting-started-overview", "home-devices-input-modules", "configuration-actions-add-action", "getting-started-run"]
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
                + "<li>Choose <b>Help › Check for Updates</b>. It asks GitHub for the latest release.</li>"
                + "<li>On an installed copy, choose <b>Update Now</b>. It downloads the installer, checks it against the SHA-256 checksum GitHub reports, closes the program the usual way (asking about unsaved changes), installs, and starts the new version.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>When <b>Check for updates</b> is on in <b>Options</b> (<b>General</b>, <b>Startup and Tray</b>; on by default), the program also checks when it starts and only speaks up when there is a newer version.</li>"
                + "<li><b>Skip This Version</b> stops the startup check from offering that version.</li>"
                + "<li>The window shows the release notes of the new version and of any versions in between, newest first; without a connection it says \"Release notes unavailable.\"</li>"
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
                + "<li>Choose <b>Run</b> on the toolbar. While the profile runs, the button reads <b>Stop</b> and uses the accent color.</li>"
                + "<li>After pressing Run, move each throttle, brake pedal or slider that rests away from the middle a little (see Good to know).</li>"
                + "<li>To stop, choose <b>Stop</b>. Stop never asks.</li>"
                + "</ol>"
                + "<p>The bottom bar shows <b>Status</b> (Running, Stopped, or Running (Paused), and 'unsaved changes' when the running profile has some) and what the last save wrote. The <b>Mode</b> box picks the mode that runs (see <a href=\"topic:modes-mode-box\">Choose the mode you edit and run</a>).</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>When an action editor has changes that are not saved, Run asks first: <b>Save</b>, <b>Discard</b> or <b>Cancel</b>. The profile runs as saved.</li>"
                + "<li>While the profile runs, the action editors are locked (\"Profile running: stop it to edit\").</li>"
                + "<li>The program knows where an axis is only after that axis has moved. Until then it treats the axis as centered, so a control resting away from the middle is sent as center at first. Sticks and rudders that rest at center are not affected.</li>"
                + "<li>Running does not hide controllers from games; use HidHide for that.</li>"
                + "<li>What happens when a controller is plugged in or removed while running is set by <b>Device change behavior</b> in <b>Options</b> (<b>General</b>, <b>Devices</b>): Stop, Ignore, or Reload.</li>"
                + "</ul>",
            related: ["modes-mode-box", "tools-hidhide", "options-profile-options", "getting-started-nothing-reaches-vjoy"]
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
                + "<li>Dropdown lists of 10 or more entries have a search box: type part of a name, <b>Up</b> and <b>Down</b> move, <b>Enter</b> picks.</li>"
                + "<li><b>Command Palette</b>: <b>Ctrl+K</b> (or <b>View › Command Palette…</b>) lists every menu command you can use now. Type part of a name and press <b>Enter</b>. Shortcuts show beside the commands.</li>"
                + "<li>To leave a text box you are typing in, press <b>Esc</b> or click anywhere outside it. What you typed is kept. In Module Setup, Esc does nothing, as sticks can send it; click away instead.</li>"
                + "<li>To rename, press <b>F2</b> or choose <b>Rename</b>: the cursor goes in the name with all of it selected, so you can type the new one straight away. <b>Enter</b> or a click elsewhere saves it; <b>Esc</b> keeps the old name.</li>"
                + "</ul>"
                + "<p>Shortcuts in the main window:</p>"
                + "<ul>"
                + "<li><b>Ctrl+N</b> new profile, <b>Ctrl+O</b> load, <b>Ctrl+S</b> save, <b>Ctrl+Shift+S</b> save as.</li>"
                + "<li><b>Ctrl+K</b> Command Palette, <b>F1</b> Help.</li>"
                + "</ul>",
            related: ["getting-started-profiles", "home-devices-card-menu"]
        },
        {
            id: "getting-started-profiles",
            section: "Getting started",
            title: "Work with profiles",
            body: "<p>A profile holds the modes, the actions on every input, the profile settings, and the list of scripts.</p>"
                + "<ul>"
                + "<li><b>File › New Profile</b> (<b>Ctrl+N</b>) starts an empty profile.</li>"
                + "<li><b>File › Load Profile…</b> (<b>Ctrl+O</b>) opens one; <b>File › Recent</b> lists the ones you opened before.</li>"
                + "<li><b>File › Save Profile</b> (<b>Ctrl+S</b>) and <b>File › Save Profile As…</b> (<b>Ctrl+Shift+S</b>) write it to disk.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Closing the program or loading another profile asks first when there are unsaved changes.</li>"
                + "<li><b>Load profiles automatically</b> in <b>Options</b> (<b>Profiles</b>, <b>Auto-load</b>) loads a profile when a chosen program starts.</li>"
                + "</ul>",
            related: ["getting-started-saved-where", "options-profile-profile-settings", "modes-modes", "options-profile-scripts"]
        },
        {
            id: "getting-started-saved-where",
            section: "Getting started",
            title: "What is saved where",
            body: "<p>The program keeps three separate stores. Saving one does not save the others, except where noted.</p>"
                + "<ul>"
                + "<li>Profile (<b>File › Save Profile</b>): modes, actions, profile settings, scripts.</li>"
                + "<li>Module file, one per device: claims, friendly names, the device picture, the Button Map layout, the Appearance of its Configuration page or Output View, and its calibration. Input and Output Module Setup, the Button Map, Calibration and the Appearance panels write it. Saving an output module also saves the profile when the profile already has a file.</li>"
                + "<li>Program settings: Options, Home layout and card sizes, window sizes, HidHide choices, and the Logical Device's Appearance.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>After every save the bottom bar names the file that was written.</li>"
                + "<li>Every save is also kept in the History (<b>Tools › History</b>).</li>"
                + "</ul>",
            related: ["getting-started-profiles", "home-devices-module-files", "tools-history", "options-profile-options"]
        },

        {
            id: "getting-started-nothing-reaches-vjoy",
            section: "Troubleshooting",
            title: "Nothing reaches vJoy",
            body: "<p>Check these in order.</p>"
                + "<ol>"
                + "<li>Is the profile running? The toolbar button should read <b>Stop</b> and the bottom bar Running.</li>"
                + "<li>Is the input claimed in its input module? Inputs that are not claimed are ignored.</li>"
                + "<li>Does the wire show <b>(not claimed)</b>? Claim that output in <b>Output Module Setup</b>.</li>"
                + "<li>Is the action in the running mode (the <b>Mode</b> box under the toolbar)? Only that mode's actions, and its parents', run.</li>"
                + "<li>system.log in the Logs folder (see the folders in <b>Options</b>) notes each blocked output once.</li>"
                + "</ol>",
            related: ["getting-started-run", "home-devices-input-modules", "home-devices-vjoy-output", "modes-modes"]
        },
        {
            id: "getting-started-xbox-does-nothing",
            section: "Troubleshooting",
            title: "Xbox does nothing",
            body: "<p>Check these in order.</p>"
                + "<ol>"
                + "<li>Open the Xbox page or the <b>Xbox Viewer</b>: the check at the top must say <b>ViGEmBus driver found</b>. If not, it says what to do.</li>"
                + "<li>The pad exists only while the profile runs and after a Map to Xbox action has sent.</li>"
                + "<li>Check that the action is <b>Map to Xbox</b> with <b>Xbox 360 Controller</b> and the right <b>Target</b>.</li>"
                + "</ol>",
            related: ["home-devices-xbox-output", "configuration-actions-map-to-xbox", "tools-viewers", "getting-started-run"]
        },
        {
            id: "getting-started-key-does-not-fire",
            section: "Troubleshooting",
            title: "A key binding does not fire",
            body: "<p>Open <b>Input Module Setup</b> on <b>Keyboard</b> and check the key is claimed. Once you save a keyboard choice, only claimed keys fire.</p>",
            related: ["home-devices-input-modules"]
        },
        {
            id: "getting-started-device-missing",
            section: "Troubleshooting",
            title: "A device is missing or seen twice",
            body: "<ul>"
                + "<li>Not on Home: right-click empty space on Home and check <b>Hidden Cards</b>.</li>"
                + "<li>A game sees both the physical stick and vJoy: hide the physical stick with HidHide.</li>"
                + "<li>Bindings belong to a device that was replaced: open the <b>Device Library</b> and use <b>Copy to Another Stick…</b> from the old stick (or <b>Swap with Another Stick…</b> when both are plugged in).</li>"
                + "</ul>",
            related: ["home-devices-hidden-cards", "tools-hidhide", "home-devices-backups"]
        },
        {
            id: "getting-started-save-diagnostics",
            section: "Troubleshooting",
            title: "Save diagnostics for a problem report",
            body: "<p>Save Diagnostics puts everything needed for a problem report in one zip: the program's logs, its settings, the device list (names, ids, kinds, connected) and the program and Windows versions.</p>"
                + "<ol>"
                + "<li>Choose <b>Help › Save Diagnostics…</b> (or <b>Save Diagnostics…</b> on the Live Log Reader's <b>Debug</b> tab).</li>"
                + "<li>To add the open profile, tick <b>Include the open profile</b>.</li>"
                + "<li>Choose <b>Save…</b> and pick where. It starts on the Desktop.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Your user name in folder paths is replaced by &lt;user&gt;.</li>"
                + "<li>When it is done it says where the zip went; if it can't be written it says which file, which folder and why.</li>"
                + "</ul>",
            related: ["tools-live-log"]
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
            body: "<p>Actions, modes and profile settings are kept only when you save the profile with <b>File › Save Profile</b>. See <a href=\"topic:getting-started-saved-where\">What is saved where</a>.</p>",
            related: ["getting-started-saved-where"]
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
