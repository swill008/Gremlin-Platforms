// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Tools (viewers, calibration, device information, History,
// Auto Mapper, HidHide, Input Tester, Live Log Reader). Button Map and Device Library
// have chapters of their own.

.pragma library

var chapter = { id: "tools", title: "Tools" }

function topics() {
    return [
        {
            id: "tools-viewers",
            section: "Devices",
            title: "Watch live values in the viewers",
            body: "<p>The viewers show live values; they change nothing. Open them from the toolbar, <b>Tools › Viewers</b>, or a card's menu.</p>"
                + "<ul>"
                + "<li><b>vJoy Viewer</b> <a href=\"open:tools.vjoyViewer\">Open ›</a>: each physical device beside the vJoy device it drives. The physical side shows claimed inputs; the vJoy side shows what the vJoy output module sent (claimed outputs, while the profile runs).</li>"
                + "<li><b>Xbox Viewer</b> <a href=\"open:tools.xboxViewer\">Open ›</a>: the Xbox 360 Controller with every control, and which inputs drive it. The ViGEmBus check is at its top.</li>"
                + "</ul>",
            related: ["home-devices-xbox-output", "home-devices-vjoy-output", "tools-input-monitor"]
        },
        {
            id: "tools-calibration",
            section: "Devices",
            title: "Calibrate axes",
            body: "<p>Calibration sets the center and the ends of each axis so its full travel is used. It is stored in the device's input module and applied before any action sees the axis.</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Device Setup › Calibration</b> <a href=\"open:tools.calibration\">Open ›</a>, or <b>Calibration</b> in a card's menu.</li>"
                + "<li>Choose the input module. Every axis is listed; one the input module doesn't claim is marked <b>(not claimed)</b>.</li>"
                + "<li>For each axis, move the stick and use <b>Calibrate Center</b> and <b>Calibrate Extrema</b>, or type the values.</li>"
                + "<li>Press the axis's save button, or <b>Save All</b> to save every unsaved axis at once. An axis shows <b>Not saved</b> until you do.</li>"
                + "</ol>"
                + "<p>What a save did shows on the message line at the bottom: \"Saved to the module file.\" or \"Saved every axis to the module file.\", or in red why nothing was written. It stays until the next message.</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An axis put back to its saved values is no longer unsaved.</li>"
                + "<li>An axis that would never move is not saved, and the reason shows on the message line: \"Not saved: the axis's lowest and highest values are the same. Move it through its full range, then save.\" or \"Not saved: the axis's center is outside its lowest and highest values. Calibrate the center and the full range again, then save.\"</li>"
                + "<li>An axis whose lowest value is above its highest is not saved either: \"Not saved. The lowest value is above the highest. Calibrate the full range again, then save.\"</li>"
                + "<li><b>Undo</b> and <b>Redo</b> (<b>Ctrl+Z</b>, <b>Ctrl+Y</b>) step back through each axis's changes (a value typed, Reset, a calibration started) until you choose another module. Beside them, \"Last change: <i>axis</i>, <i>what</i>\" names the newest change, or \"Undone: a change to <i>axis</i>\" after an Undo.</li>"
                + "<li>Leaving with unsaved axes asks first.</li>"
                + "</ul>",
            related: ["home-devices-input-modules", "getting-started-saved-where"]
        },
        {
            id: "tools-device-information",
            section: "Devices",
            title: "Device Information",
            body: "<p><b>Tools › Device Setup › Device Information</b> <a href=\"open:tools.deviceInfo\">Open ›</a> lists every device Windows reports: Name, Axes, Buttons, Hats, VID, PID, Joystick ID and Device ID. Use it to tell identical devices apart.</p>",
            related: ["home-devices-home"]
        },
        {
            id: "tools-auto-mapper",
            section: "Devices",
            title: "Create actions with the Auto Mapper",
            body: "<p>The Auto Mapper creates Map to vJoy actions in one step: each claimed input of an input module gets an action to the same number on a vJoy output module.</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Mapping › Auto Mapper</b> <a href=\"open:tools.autoMapper\">Open ›</a> (or <b>Auto Mapper</b> in a card's menu).</li>"
                + "<li>Tick the input modules and output modules. The first ticked input goes to the first ticked output, the second to the second, and so on.</li>"
                + "<li>Choose <b>Select Mode</b>. It starts on the mode shown in the Mode box.</li>"
                + "<li>Choose <b>Create 1:1 Actions</b>. The result names the mode the actions went into, and says so when the Mode box shows another mode.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The new actions are in the open profile and not saved yet. Save the profile to keep them; to take them back, load the profile again without saving.</li>"
                + "<li>Only outputs the output module claims are used. Skipped controls are listed with the reason (not claimed, not on the vJoy device, or already used by another input in this mode). When the output module claims none of them, the result says so.</li>"
                + "<li>An input module left without an output is named in the result: tick more outputs, or turn on <b>Combine onto selected outputs</b>, which reuses the outputs in turn.</li>"
                + "<li><b>Also claim the matching outputs on the output module</b> (off by default) claims what the new actions need first.</li>"
                + "<li><b>Overwrite used inputs</b> replaces existing actions on those inputs; off keeps them. With it on, <b>Create 1:1 Actions</b> asks first (\"Replace the actions in mode Default?\"); the red <b>Replace Actions</b> removes every action on those inputs in that mode, macros included, and puts the new actions there. <b>Enter</b> and <b>Esc</b> cancel. The choice is remembered for next time.</li>"
                + "<li>While the profile runs, the window says the changes take effect the next time it starts.</li>"
                + "<li><b>Esc</b> doesn't close the window, so a stick that sends Esc can't close it by accident.</li>"
                + "</ul>",
            related: ["getting-started-first-setup", "home-devices-vjoy-output", "modes-mode-box"]
        },
        {
            id: "tools-hidhide",
            section: "Devices",
            title: "Hide controllers from games with HidHide",
            body: "<p>HidHide hides physical controllers from games so they only see vJoy or Xbox. Gremlin-Platforms always sees them. The HidHide driver is a separate install (<b>Get HidHide</b>).</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Device Setup › HidHide</b> <a href=\"open:tools.hidhide\">Open ›</a>.</li>"
                + "<li>Turn on <b>Gremlin-Platforms controls HidHide</b> to let this program write HidHide's settings, and <b>HidHide Enabled</b> to turn hiding on.</li>"
                + "<li>Tick the devices to hide. <b>Gaming devices only</b> shortens the list. A hidden device is dimmed and marked HIDDEN.</li>"
                + "<li>Choose <b>Allow list</b> (only the listed programs see hidden devices) or <b>Block list</b> (the listed programs do not), and add programs with <b>Add Program</b>.</li>"
                + "<li>Choose <b>Test HidHide</b> to open the Windows Game Controllers panel. With Allow list on, a hidden device should be missing there. Reopen the panel after each change.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Until <b>Gremlin-Platforms controls HidHide</b> is on, the settings show but can't be changed, and the program changes nothing in HidHide.</li>"
                + "<li>Turning <b>Gremlin-Platforms controls HidHide</b> off leaves HidHide as it is: devices hidden then stay hidden. To show them again, untick them first.</li>"
                + "<li>If the HidHide driver refuses <b>HidHide Enabled</b>, the switch flips back and the error shows.</li>"
                + "<li>Removing a program from the list asks first: \"Remove <i>program</i> from the program list?\" The red <b>Remove Program</b> removes it; <b>Add Program</b> can put it back.</li>"
                + "<li>The devices are listed under the <b>Devices</b> heading.</li>"
                + "<li><b>Automatically Start</b> applies both switches each time the program starts. All switches start off on a new install.</li>"
                + "<li>To see what a listed game sees, use the <b>Input Tester</b> button: see <a href=\"topic:tools-input-tester\">Check what a game sees (Input Tester)</a>. The page also shows the <b>Last Input Tester result</b>, and warns when a listed game is running from another folder.</li>"
                + "</ul>"
                + "<h4>Set HidHide up first, then start the game</h4>"
                + "<ul>"
                + "<li>HidHide checks a program only when the program opens a device. A game that already has a stick open keeps it after any change: hidden devices, the program list, <b>HidHide Enabled</b> or Allow/Block. So set HidHide up first, then start the game. After a change, restart the game (and the Input Tester).</li>"
                + "<li>Changing HidHide while it is on is fine: programs started afterwards get the new setting.</li>"
                + "<li>HidHide has no \"check again\" command. To make it check a running program again, restart that program, or use <b>Reset Devices…</b> (below), or unplug the stick and plug it back in (Windows then closes every program's connection to it, and this program reads its devices again). Not while flying.</li>"
                + "<li>The page warns when a listed program that is running was started before the last HidHide change: restart it so the change applies. For the Input Tester it offers <b>Restart Input Tester</b>.</li>"
                + "<li>A program is listed by its full path: the same folder and file name (capital letters don't matter; spaces are fine). A copy of the game in another folder, such as a test build (PTU) beside the main one (LIVE), is a different program: list each copy.</li>"
                + "<li>A hidden device is known by its Windows device path. Plugged into another USB port, a stick can get a new path that isn't hidden. The Input Tester and the Trace tab's HidHide row show this.</li>"
                + "<li>While HidHide's own window (HidHide Configuration Client) is open, other programs can't talk to HidHide: only one at a time. This program may then show HidHide as not installed or not available. Close HidHide's window.</li>"
                + "</ul>"
                + "<h4>Reset Devices</h4>"
                + "<p>A game or the Input Tester that was started before a HidHide change still sees the sticks it opened. <b>Reset Devices…</b> (the red button by the <b>Devices</b> heading, and by each \"started before the last HidHide change\" warning) restarts the sticks in Windows, as if you unplugged them and plugged them back in, so every program opens them again and HidHide checks them anew. You don't have to restart the game.</p>"
                + "<ul>"
                + "<li>Use it after you change what is hidden, the program list or Allow/Block while a game or the tester is running, or when the Input Tester shows <b>Programs can see it: should be hidden</b> for a stick you hid.</li>"
                + "<li>The <b>Reset Devices</b> window lists your USB game controllers (never vJoy or Xbox pads). The hidden ones are ticked each time it opens; tick or untick others. Devices the program knows that aren't plugged in are greyed.</li>"
                + "<li>Center your sticks first. While a stick restarts (about 2-3 seconds) the program keeps its axes where they were and releases its buttons. A running game loses the stick for that moment; the window names any listed game that is running. Not while flying.</li>"
                + "<li>Choose <b>Reset N Devices</b>. Windows may ask for administrator permission, once for all the ticked devices (some PCs are set to not ask). If you say No, nothing is reset.</li>"
                + "<li>Each row then shows its result: <b>reset ✓ · back after N.N s</b>, <b>reset ✓ · not back after 10 s</b>, <b>needs a Windows restart, or unplug it and plug it back in</b>, <b>not found</b> (it was already gone), <b>permission declined</b> or <b>failed</b> with a code. The results are also in the system log.</li>"
                + "<li>Some devices can't be restarted while Windows is running; Windows then answers \"needs a restart\" (code 3010). Windows gave this answer for an Xbox One controller. Unplugging it and plugging it back in does the same job, without restarting Windows.</li>"
                + "<li>A reset doesn't change HidHide's settings. A running Input Tester sees the sticks come back and checks them again.</li>"
                + "</ul>"
                + "<p>The exact rules are in <a href=\"topic:tools-tech-hidhide\">How HidHide decides</a>.</p>",
            related: ["tools-input-tester", "tools-tech-hidhide", "home-devices-hidden-cards", "getting-started-device-missing", "tools-q-game-sees-both"]
        },
        {
            id: "tools-input-tester",
            section: "Devices",
            title: "Check what a game sees (Input Tester)",
            body: "<p>HidHide never hides anything from this program, so this program can't show what a game sees. The <b>Gremlin Input Tester</b> is a small separate program that HidHide treats like a game: put it on HidHide's list the same way as your game, and it shows exactly which controllers that game can see. It only reads; it changes nothing.</p>"
                + "<h4>Check a game</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Device Setup › HidHide</b> <a href=\"open:tools.hidhide\">Open ›</a>. With <b>Gremlin-Platforms controls HidHide</b> on, choose <b>Add Input Tester to the list</b> (shown while it isn't on the list). It goes on the same program list as your game.</li>"
                + "<li>Choose <b>Input Tester</b> on that page, or <b>Tools › Viewers › Input Tester…</b>. The tester opens and compares what it sees with what this program expects.</li>"
                + "<li>Read the top line: <b>✓ Pass: programs see only what they should</b> means a game on the same list sees what it should; <b>✗ Problem:</b> says in plain words what is wrong, such as \"programs can see 1 stick that should be hidden\". The blue line under it says what HidHide's list means for this window, for example that it's on the Block list, so your hidden sticks should not show up here.</li>"
                + "<li>Move a stick to see its values: axes, buttons and hats move, and the row's <b>activity dot</b> blinks. <b>All devices</b> shows every device at once. With <b>Follow input</b> on (the switch above the list), the device you move is chosen for you; it waits 1 s before jumping to another device, and does nothing while <b>All devices</b> is shown.</li>"
                + "</ol>"
                + "<h4>Start it again after a HidHide change</h4>"
                + "<p>HidHide checks a program only when the program opens a device. A tester (or a game) that was already running keeps the devices it opened, so after you change HidHide it can go on seeing a stick that is now hidden. Start the tester after the change, and restart a game that was running.</p>"
                + "<ul>"
                + "<li>When HidHide changed after the tester started, the tester shows a yellow line \"HidHide changed after this tester started …\" with <b>Restart tester</b>. Choose it: a fresh tester opens and the old one closes.</li>"
                + "<li>The HidHide page warns \"… was started (HH:MM) before the last HidHide change (HH:MM): restart it so the change applies.\" for each listed program that is running, games too. For the tester it offers <b>Restart Input Tester</b>, which opens a fresh tester; close the old window yourself. This program never closes another program.</li>"
                + "</ul>"
                + "<h4>The Logs tab</h4>"
                + "<p>The tester has two tabs, <b>Devices</b> and <b>Logs</b>. On <b>Logs</b>, choose a log under <b>Log</b>: <b>Tester log (tester.log)</b>, this program's <b>trace.log</b> and <b>system.log</b>, or <b>DirectInput reader (dill_debug.log)</b>. <b>Follow</b> keeps the view at the end while lines are added; <b>Find</b> searches; <b>Show</b> set to <b>Warnings</b> shows only warnings; <b>Copy</b> copies the lines shown; <b>Open folder</b> opens the log's folder. Big files show their last 512 KB. Opened on its own, the tester keeps its log in the window only.</p>"
                + "<p>The tester log lists each device the tester tried to open and what happened:</p>"
                + "<ul>"
                + "<li><b>open → ok</b>: the tester can see the device, so a game on the same list can see it too.</li>"
                + "<li><b>access denied (5)</b>: HidHide is hiding the device from the tester. For a stick you hide, that's what you want. On the Devices tab such a device shows as a dimmed row \"left out: access denied (hidden from this program)\".</li>"
                + "<li>\"left out: not a game device\": a keyboard, mouse or other device the tester doesn't show. Other \"left out\" lines give the reason.</li>"
                + "</ul>"
                + "<p>Save Diagnostics includes the tester log and the tester's last result.</p>"
                + "<p>Button 128 and hat 4 always show as off and centered: the DirectInput reader this program uses can't read them, in the tester or in the program.</p>"
                + "<h4>What each row says</h4>"
                + "<ul>"
                + "<li><b>Hidden from programs</b>: a hidden stick the tester can't see, as it should be (shown greyed).</li>"
                + "<li><b>Programs can see it: should be hidden</b> (red): a game on the list can see this stick as well as vJoy. The hint under the row says what to do: \"Tick it on Gremlin's HidHide page, then press Restart tester.\" Also check that <b>HidHide Enabled</b> is on and the game is on the list.</li>"
                + "<li><b>Programs can see it</b>: a device programs should see, such as a vJoy device or the Xbox pad. <b>Programs can see it · not in use</b> is a vJoy device no output uses.</li>"
                + "<li><b>Programs can't see it: should be shown</b> (red): a device programs should see but can't, such as a vJoy device hidden by mistake. The hint says: \"Check it's plugged in and that Gremlin's output for it is on.\"</li>"
                + "<li><b>Not set up in Gremlin</b>: a device this program doesn't use. It is not a problem.</li>"
                + "</ul>"
                + "<p>Choose a row to see its values. Each row says what it <b>Should be</b>: \"hidden from programs\" or \"seen by programs\". When the tester can't see the device, it says why: \"Hidden from programs, so there's nothing to show.\" or \"Missing: programs can't see it.\" The list is in sections: <b>YOUR CONTROLLERS</b>, <b>GREMLIN'S VIRTUAL JOYSTICKS (vJoy)</b> and <b>XBOX CONTROLLERS</b>. Every game device Windows lists (<b>ALL GAME DEVICES IN WINDOWS</b>) is under <b>Show details</b>, closed when the tester opens. The bar at the bottom says how many joysticks, Xbox controllers and game devices this window sees.</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>If Steam is running and isn't on the Block list, a yellow line says \"Steam is running and can see your sticks: Steam Input may pass them to other programs. Add steam.exe to HidHide's Block list, or turn off Steam Input for your game.\" It is not a problem by itself, but Steam Input can hand a hidden stick to a game.</li>"
                + "<li><b>Copy result</b> copies the verdict and every row as text, ready to paste into a message.</li>"
                + "<li>The result comes back to this program: the HidHide page shows the <b>Last Input Tester result</b>, and while tracing with the HidHide row ticked, the trace writes it as a HIDHIDE line.</li>"
                + "<li>HidHide goes by a game's full path. If a listed game is running from another folder (a test build such as PTU, for example), the HidHide page warns \"… is running from …, which isn't on the list\". Add that copy to the list too.</li>"
                + "<li>If the list has an older copy of the tester (after the program moved), the HidHide page says so; <b>Update path</b> puts the current one on the list.</li>"
                + "<li>Opened on its own, the tester shows what it sees without ✓ Pass or ✗ Problem; a device it can't see reads \"This window can't see it.\"</li>"
                + "<li>The tester must be its own program, <b>Gremlin Input Tester.exe</b>, installed next to this program. Run from the source code instead, HidHide would see <code>python.exe</code>, not the tester.</li>"
                + "</ul>"
                + "<p>How HidHide decides what the tester sees: <a href=\"topic:tools-tech-hidhide\">How HidHide decides</a>.</p>",
            related: ["tools-hidhide", "tools-tech-hidhide", "tools-trace", "tools-q-game-sees-both"]
        },

        {
            id: "tools-history",
            section: "History",
            title: "See saved changes in History",
            body: "<p><b>Tools › History</b> <a href=\"open:tools.history\">Open ›</a> lists every saved change, newest first.</p>"
                + "<ul>"
                + "<li>Profile saves: each input whose actions changed, and other parts such as modes and scripts.</li>"
                + "<li>Module files: checked controls and names, calibration, Appearance, the Button Map, and the Logical Device.</li>"
                + "<li>The Device Library's list and saved setups, labelled <b>Device Library</b>.</li>"
                + "<li>The settings you choose in Options, HidHide and OSC.</li>"
                + "</ul>"
                + "<ol>"
                + "<li>Pick a change to see it <b>Before</b> and <b>After</b>. See <a href=\"topic:tools-history-compare\">Compare Before and After</a>.</li>"
                + "<li>To narrow the list to one kind, use <b>Show</b>: <b>All</b>, <b>Profile</b>, <b>Module files</b>, <b>Button Map</b> or <b>Settings</b>. To find a device, input or file, type in <b>Search</b> (<b>Ctrl+F</b>); it looks in each change's title and in what it is about. A line under it says \"N found\" or \"Nothing matches\"; <b>×</b> or <b>Esc</b> clears it.</li>"
                + "</ol>"
                + "<p><b>History</b> in an editor opens it for only what that editor shows: on the Configuration page (the selected input), on a Logical Device control's menu, in Module Setup, in the Button Map's File menu, and in Options. <b>Show All</b> widens it again.</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Window sizes and places, and the Button Map's zoom, guides and print area, aren't kept.</li>"
                + "<li><b>Days to keep changes</b> <a href=\"show:option/Days to keep changes\">Show me ›</a> (90) and <b>Largest history file (MB)</b> <a href=\"show:option/Largest history file (MB)\">Show me ›</a> (20) in Options set how long changes are kept and how big each history file may grow; the oldest go first. Both are checked when the program starts.</li>"
                + "<li>The history is kept in the history folder, set on the <b>Folders</b> page of Options <a href=\"show:option/History folder\">Show me ›</a>. After you move it, the changes saved before stay in the old folder, and the window shows only the new one.</li>"
                + "<li>The whole profile is kept for the newest 20 saves of each profile.</li>"
                + "<li>While the profile runs, the window says changes here take effect the next time it starts.</li>"
                + "</ul>",
            related: ["tools-history-compare", "tools-history-restore", "tools-history-clear", "getting-started-saved-where"]
        },
        {
            id: "tools-history-compare",
            section: "History",
            title: "Compare Before and After",
            body: "<p>When you pick a change in History, <b>Before</b> and <b>After</b> show it side by side, lined up row for row.</p>"
                + "<ul>"
                + "<li>A changed line has a soft tint and a thin bar on its left edge: red on Before, green on After. Inside it, the words that changed have a stronger tint. Unchanged lines stay plain.</li>"
                + "<li><b>Previous Change</b> and <b>Next Change</b> move both sides together to the previous or next changed line.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A \"Created\" change has no Before, and a \"Deleted\" change no After.</li>"
                + "<li>A version no longer kept, such as an older save's whole profile, shows \"Not kept.\"</li>"
                + "</ul>",
            related: ["tools-history", "tools-history-restore"]
        },
        {
            id: "tools-history-restore",
            section: "History",
            title: "Restore an earlier version",
            body: "<p>Restore puts the version before or after a saved change back.</p>"
                + "<ol>"
                + "<li>Open <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a> and pick the change.</li>"
                + "<li>Choose <b>Restore Before</b> or <b>Restore After</b>. It asks first.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An input's actions go back into the open profile, unsaved: open that profile first, and save it to keep them. The restore shows in the History at that Save Profile.</li>"
                + "<li>A module file, with its pictures, and settings are saved at once, and the restore is a new change in the History at once.</li>"
                + "<li>A Device Library change: \"Restoring puts back the Device Library's list and its saved setups together.\"</li>"
                + "<li>A whole profile (on its save's entry) is written as a copy next to the profile, to open with <b>File › Load Profile…</b>. It stays next to the profile until you delete it, and is not a change in the History.</li>"
                + "<li>A part of a profile (modes, Profile Settings, scripts) can't be restored on its own: \"Put this back with Restore on the profile's save, below it in the list.\" The Logical Device and OSC have their own module files, so their entries can be restored on their own.</li>"
                + "<li>The Logical Device has its own file, so it is restored on its own, as a module file is.</li>"
                + "<li>A \"Created\" change can't be restored to Before, nor a \"Deleted\" one to After, and a version no longer kept can't be restored: those buttons are off.</li>"
                + "</ul>",
            related: ["tools-history", "tools-history-compare", "getting-started-profiles"]
        },
        {
            id: "tools-history-clear",
            section: "History",
            title: "Clear History",
            body: "<p><b>Clear History…</b>, the red button in History, deletes every saved change and the kept copies used to restore them.</p>"
                + "<ol>"
                + "<li>Stop the profile. While it runs, the button is off.</li>"
                + "<li>Open <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a> and choose <b>Clear History…</b>.</li>"
                + "<li>The question \"Clear History?\" says how many changes and how many MB of kept copies go. Choose the red <b>Clear History</b> to go ahead. <b>Cancel</b> has the focus: <b>Enter</b> and <b>Esc</b> both cancel.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Your profiles, module files and Device Library stay as they are. Only History goes, with the Device Library's Undo steps for this session.</li>"
                + "<li>No earlier change can be restored or undone afterwards. This can't be undone.</li>"
                + "<li>History keeps a red \"History cleared\" entry with the date and what was deleted. It has no Restore, and History's own clean-up never removes it. Each later clearing adds another.</li>"
                + "</ul>",
            related: ["tools-history", "device-library-undo"]
        },

        {
            id: "tools-live-log",
            section: "Live Log Reader",
            title: "Read the logs in the Live Log Reader",
            body: "<p><b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a> has four tabs: <b>Config</b>, <b>Debug</b>, <b>Input Monitor</b> and <b>Trace</b>.</p>"
                + "<ul>"
                + "<li><b>Config</b> follows the program's activity log (logs.txt): which profiles, modules and settings files were read and saved, and when. Use it to check how a file loads. It starts empty at every start; <b>Clear Log</b> empties it (it asks \"Clear the Config log?\" first) and <b>Copy All</b> copies it.</li>"
                + "<li><b>Debug</b> shows the diagnostic logs in the Logs folder: <b>System</b> (system.log: errors, warnings, blocked outputs), <b>Scripts</b> (user.log), <b>Events</b> (event.log), <b>All logs</b> (every file together in time order, each line tagged with its log: [System], [Scripts], [Events], [Qt]) and <b>Qt</b> (qt.log: Qt's own messages, such as QML warnings, each with the time).</li>"
                + "</ul>"
                + "<p>On the Debug tab:</p>"
                + "<ul>"
                + "<li><b>Show</b> picks the lowest level shown and <b>Find</b> narrows it to entries with that text; a line under it says \"N found\" or \"Nothing matches\". Warnings and errors are in color.</li>"
                + "<li>For a large file only the last 512 KB is shown at first; <b>Load Whole File</b> reads all of it.</li>"
                + "<li><b>Clear Log</b> empties the shown file. It asks first (\"Clear system.log?\", \"Every line in the file is removed.\"); only the red <b>Clear Log</b> in the question clears it. This can't be undone.</li>"
                + "<li>What gets written is the <b>Diagnostic logs</b> <a href=\"show:option/Diagnostic logs\">Show me ›</a> level at the bottom of the tab, the same setting as in Options (<b>General</b>, <b>Diagnostics</b>); changing either changes both, at once.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Show</b> only filters what is already in the file: a level the program is not writing has no lines to show.</li>"
                + "<li>With <b>Log When Not Responding</b> <a href=\"show:option/Log When Not Responding\">Show me ›</a> on, system.log also says when the program stops responding for 5 seconds, where it was stuck, and when it responds again.</li>"
                + "<li>Qt's messages also show in the console when the program is started from one. qt.log moves to qt.log.1 at start-up once over 1 MB, and grows at most 5 MB a session.</li>"
                + "</ul>",
            related: ["tools-live", "tools-input-monitor", "tools-trace", "tools-red-debug-mode", "getting-started-save-diagnostics"]
        },
        {
            id: "tools-live",
            section: "Live Log Reader",
            title: "Watch every log line with Live",
            body: "<p><b>Live</b>, the red button on the Debug tab, catches every line the program logs, as it happens, at full detail, whatever the Diagnostic logs level. The files keep that level.</p>"
                + "<ol>"
                + "<li>Tick <b>Start empty</b> to clear the view when Live starts, if you like.</li>"
                + "<li>Choose <b>Live</b>. It keeps what is on screen and adds a <i>Live started</i> line; new lines are tagged [System], [Scripts] or [Events].</li>"
                + "<li>To see them together, choose <b>Log</b> › <b>All logs</b>. <b>Show</b> and <b>Find</b> work as always and can be changed while Live runs.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Clear View</b> empties the view, never a file; <b>Save Feed…</b> saves it to a text file.</li>"
                + "<li>Stopping Live leaves the session on screen; <b>Show Log File</b> goes back to the file.</li>"
                + "<li>Live stops when the Live Log Reader closes.</li>"
                + "</ul>",
            related: ["tools-live-log", "tools-red-debug-mode"]
        },
        {
            id: "tools-input-monitor",
            section: "Live Log Reader",
            title: "Watch inputs with the Input Monitor",
            body: "<p>The <b>Input Monitor</b> tab shows each input as it happens: the device and input, its value, the mode, and the actions it ran.</p>"
                + "<ol>"
                + "<li>Run the profile.</li>"
                + "<li>On the <b>Input Monitor</b> tab, choose <b>Monitor</b> and use your devices.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Map to vJoy and Map to Xbox say where they send the input. An input with none shows <i>no actions</i>; untick <b>Inputs with no actions</b> to hide those.</li>"
                + "<li>An axis shows about 10 values a second. Nothing is written to a file.</li>"
                + "<li>The Input Monitor stops when the Live Log Reader closes.</li>"
                + "</ul>",
            related: ["tools-live-log", "tools-viewers"]
        },
        {
            id: "tools-trace",
            section: "Live Log Reader",
            title: "Follow your controls with Trace",
            body: "<p>The <b>Trace</b> tab follows the controls you tick, step by step, from the stick to vJoy. Use it when a control stops working or does something odd in a game: the trace shows where the input stopped.</p>"
                + "<h4>Use it while gaming</h4>"
                + "<ol>"
                + "<li>Open <b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a> and choose the <b>Trace</b> tab.</li>"
                + "<li>Tick the sticks you want to follow. Ticking a stick ticks all its axes, buttons and hats; expand it to tick only some. Keys on the keyboard aren't traced. Each control shows where it goes in the open profile, such as \"→ vJoy 3 X\".</li>"
                + "<li>Tick <b>Out-of-step check</b> on a stick to have the program check it every second (see below). Tick <b>HidHide</b> to follow HidHide too.</li>"
                + "<li>Turn <b>Tracing</b> on (the switch in the tab, or <b>Tracing</b> in the <b>Debug</b> menu) before you start the game. You can close the Live Log Reader: tracing keeps running, and the red frame shows it is on.</li>"
                + "<li>Play as usual. If a control misbehaves, open the Trace tab (or the trace file) and look at the lines around that moment.</li>"
                + "<li>When everything works, turn <b>Tracing</b> off.</li>"
                + "</ol>"
                + "<h4>What each line says</h4>"
                + "<p>Each line has the time, the control, the <b>point</b> it was written at, and what happened there:</p>"
                + "<ul>"
                + "<li><b>RAW</b>: the value as the program gets it from the stick's driver, before anything else. No RAW line means the program never got the move.</li>"
                + "<li><b>WIRING</b>: whether the control is claimed (or \"not claimed, dropped\"), the mode, and the actions that ran, or \"no actions\".</li>"
                + "<li><b>OUTPUT</b>: what was sent to vJoy and whether it was written. <b>BLOCKED</b> means it was not sent: the vJoy output is not claimed by its output module, or the vJoy device does not have it.</li>"
                + "<li><b>EVENT</b>: tracing on or off, Run and Stop, a device plugged in or unplugged, a mode change while the profile runs.</li>"
                + "<li><b>HIDHIDE</b>: what the program asked HidHide and the answer, and changes to HidHide made outside the program.</li>"
                + "<li><b>OUT OF STEP</b>: the check below found a stick or a vJoy output that doesn't match.</li>"
                + "</ul>"
                + "<p>An axis writes at most 10 lines a second; its last value is always written when you let go of it. <b>Axis lines</b> in <b>Options ▾</b> (Trace options, at the right end of the tab bar) sets that (10 by default): pick from the list or type 0.1 to 50 (0.5 is a line every 2 seconds), then press Enter; lower it if the file fills too fast.</p>"
                + "<h4>Out-of-step check</h4>"
                + "<ul>"
                + "<li>Every second it reads the stick directly and compares with the last value the program got. If they stay different for over a second, the program is not getting that stick's moves.</li>"
                + "<li>It also reads each vJoy axis back and compares with what the program last wrote. If they stay different, something else is changing vJoy or the write did not arrive.</li>"
                + "<li>A warning shows in yellow at the top of the tab; <b>Go to line</b> jumps to it. A stick you are not touching is normal: it gets one quiet note, not a warning.</li>"
                + "</ul>"
                + "<h4>The HidHide row</h4>"
                + "<ul>"
                + "<li>With <b>HidHide</b> ticked, every HidHide call the program makes is written with its result, and HidHide is checked every 5 seconds for changes made outside the program, such as the cloak turned off or a game taken off the list.</li>"
                + "<li>Each ticked stick is checked to be on HidHide's hidden list. If it is not, the game can see the stick as well as vJoy, and the trace says so.</li>"
                + "<li>While HidHide's own window is open, HidHide is <i>in use by another program</i> and the program can't read or change it; the trace says so once.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Tracing is always off when the program starts. Your ticks are kept.</li>"
                + "<li>The lines go to <b>trace.log</b> in the Logs folder (up to its <b>Max size</b>, then one older copy, trace.log.1). The status bar shows how big it is and its limit; <b>Max size</b> in <b>Options ▾</b> sets that limit (5 MB by default): pick a size or type one from 1 to 1000 MB; with the older copy, up to twice that is kept on disk. <b>Show Trace File</b> opens it, and <b>Save Diagnostics…</b> includes it.</li>"
                + "<li><b>Find</b>, <b>Show</b> (<b>All</b> or <b>Warnings</b>) and <b>Points</b> narrow the view; <b>Clear View</b> empties the view, never the file. The tab keeps the last 5000 lines.</li>"
                + "<li><b>Clear Trace File…</b>, also in <b>Options ▾</b>, empties the file itself: it asks first, then deletes trace.log and trace.log.1 and clears the view; it works while tracing is on.</li>"
                + "<li>With tracing off, nothing is written and it costs nothing.</li>"
                + "</ul>",
            related: ["tools-input-monitor", "tools-hidhide", "tools-red-debug-mode", "getting-started-save-diagnostics"]
        },
        {
            id: "tools-red-debug-mode",
            section: "Live Log Reader",
            title: "Red debug mode",
            body: "<p>While <b>Diagnostic logs</b> is <b>ALL</b>, Live runs or <b>Tracing</b> is on, every window has a red frame and a <b>DEBUG</b> badge at the top.</p>"
                + "<ul>"
                + "<li>Click the badge to open the Live Log Reader.</li>"
                + "<li>Button Map exports and prints never include it.</li>"
                + "</ul>",
            related: ["tools-live", "tools-live-log", "tools-trace"]
        },

        // ---- Technical reference ----
        {
            id: "tools-tech-hidhide",
            section: "Technical reference",
            title: "How HidHide decides",
            body: "<p>Exact facts about the HidHide driver (version 1.4.181), for finding out why a program does or doesn't see a device.</p>"
                + "<table><tr><th>Item</th><th>What HidHide does</th></tr>"
                + "<tr><td>When it checks</td><td>Only when a program opens a device. A program that already has the device open keeps it after any change (hidden devices, program list, <b>HidHide Enabled</b>, Allow/Block).</td></tr>"
                + "<tr><td><b>Allow list</b></td><td>Only the listed programs (and this program) can open hidden devices; every other program is refused.</td></tr>"
                + "<tr><td><b>Block list</b></td><td>The listed programs are refused; every program not on the list can open hidden devices.</td></tr>"
                + "<tr><td>Which program it judges</td><td>The program that opens the device. Windows' own system processes are never refused.</td></tr>"
                + "<tr><td>How a program is matched</td><td>By its full exe path: same folder and file name, capital letters ignored, spaces fine. A copy in another folder is another program.</td></tr>"
                + "<tr><td>How a device is matched</td><td>By its Windows device path. Another USB port can give the stick a new path.</td></tr>"
                + "<tr><td>Commands</td><td>Read and set the program list, the hidden devices, <b>HidHide Enabled</b> and Allow/Block. There is no command to check running programs again.</td></tr>"
                + "<tr><td>Making it check again</td><td>Restart the program, use <b>Reset Devices…</b>, or unplug and replug the stick (Windows closes every program's connection to it). Not while flying.</td></tr>"
                + "<tr><td><b>Reset Devices…</b></td><td>Runs <code>pnputil /restart-device</code> on each ticked stick's USB device (the parent of its HID devices), all in one process with administrator rights, so Windows asks at most once; this program itself never runs as administrator. A stick is back after about 2-3 seconds with the same Windows ids, so HidHide's hidden list still matches it. Results: 3010 is <b>needs a Windows restart, or unplug it and plug it back in</b> (Windows answered 3010 for an Xbox One controller); the temporary folder is deleted afterwards; a declined prompt (1223) touches nothing.</td></tr>"
                + "<tr><td>While a stick restarts</td><td>This program sees it unplugged and plugged in again: it releases the stick's buttons and centers its hats, keeps its axes at their last value, then reads its devices again. A running profile follows <b>Device change behavior</b> in Options.</td></tr>"
                + "<tr><td>HidHide's own window</td><td>While HidHide Configuration Client is open, other programs can't talk to HidHide.</td></tr>"
                + "<tr><td>A refused open</td><td>The program gets \"access denied (5)\". The Input Tester's <b>Logs</b> tab shows it: HidHide is working.</td></tr>"
                + "</table>"
                + "<h4>What this means</h4>"
                + "<ul>"
                + "<li>Set HidHide up first, then start the game. After any change, restart the game and the Input Tester.</li>"
                + "<li>Another program that can see the stick may pass it on. Steam does this through Steam Input when it isn't blocked; whether a game gets the stick depends on that game's Steam Input setting. That's why the Input Tester shows its Steam line.</li>"
                + "</ul>",
            related: ["tools-hidhide", "tools-input-tester", "tools-q-game-sees-both"]
        },

        {
            id: "tools-q-identical-sticks",
            section: "Common questions",
            title: "How do I tell two identical sticks apart?",
            body: "<p>Compare their Joystick ID and Device ID in <b>Tools › Device Setup › Device Information</b>. See <a href=\"topic:tools-device-information\">Device Information</a>.</p>",
            related: ["tools-device-information"]
        },
        {
            id: "tools-q-game-sees-both",
            section: "Common questions",
            title: "Why does my game see my stick and vJoy?",
            body: "<p>Running the profile does not hide controllers. Hide the physical stick with HidHide. See <a href=\"topic:tools-hidhide\">Hide controllers from games with HidHide</a>. To see what the game sees, use the Input Tester: see <a href=\"topic:tools-input-tester\">Check what a game sees (Input Tester)</a>.</p>"
                + "<p>If the stick is hidden and the game still sees it, check:</p>"
                + "<ul>"
                + "<li>The game was started after the last HidHide change. HidHide checks only when the game opens the stick; restart the game after any change.</li>"
                + "<li>The stick is ticked on the HidHide page and <b>HidHide Enabled</b> is on.</li>"
                + "<li>With <b>Allow list</b>, the game is not on the list; with <b>Block list</b>, it is on the list, with the exact path it runs from (a PTU copy is a different program).</li>"
                + "<li>The stick is in the USB port it was hidden in. Another port can give it a new path that isn't hidden.</li>"
                + "<li>Steam: another program that can see the stick may pass it on. With <b>Block list</b>, put Steam on the list or turn Steam Input off for the game.</li>"
                + "</ul>"
                + "<p>The Input Tester checks all of these at once. A stick it marks <b>Programs can see it: should be hidden</b> gets the hint \"Tick it on Gremlin's HidHide page, then press Restart tester.\"; if the Steam line shows, add steam.exe to HidHide's Block list or turn off Steam Input for your game. <b>Show details</b> lists every game device Windows has.</p>",
            related: ["tools-hidhide", "tools-input-tester", "tools-tech-hidhide"]
        },
        {
            id: "tools-q-older-version",
            section: "Common questions",
            title: "How do I get back an earlier version of a setting or binding?",
            body: "<p>Open <b>Tools › History</b>, pick the change and restore it. See <a href=\"topic:tools-history-restore\">Restore an earlier version</a>.</p>",
            related: ["tools-history-restore", "tools-history"]
        },
        {
            id: "tools-q-undo-auto-mapper",
            section: "Common questions",
            title: "How do I take back what the Auto Mapper made?",
            body: "<p>Its actions are not saved yet: load the profile again without saving. See <a href=\"topic:tools-auto-mapper\">Create actions with the Auto Mapper</a>.</p>",
            related: ["tools-auto-mapper"]
        },
        {
            id: "tools-q-clear-history",
            section: "Common questions",
            title: "How do I delete everything in History?",
            body: "<p>Stop the profile, then choose <b>Clear History…</b> in <b>Tools › History</b>. It can't be undone. See <a href=\"topic:tools-history-clear\">Clear History</a>.</p>",
            related: ["tools-history-clear"]
        },
        {
            id: "tools-q-red-frame",
            section: "Common questions",
            title: "Why is there a red frame around every window?",
            body: "<p>Diagnostic logs is set to ALL, Live is running or Tracing is on. See <a href=\"topic:tools-red-debug-mode\">Red debug mode</a>.</p>",
            related: ["tools-red-debug-mode"]
        },
        {
            id: "tools-q-axis-off",
            section: "Common questions",
            title: "Why doesn't my axis reach its ends?",
            body: "<p>Calibrate it. See <a href=\"topic:tools-calibration\">Calibrate axes</a>.</p>",
            related: ["tools-calibration"]
        }
    ]
}
