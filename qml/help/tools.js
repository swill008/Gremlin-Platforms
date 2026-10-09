// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Tools (viewers, calibration, device information, History,
// Auto Mapper, HidHide, Live Log Reader). Button Map and Device Library
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
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An axis put back to its saved values is no longer unsaved.</li>"
                + "<li>An axis that would never move is not saved, and the reason shows: \"Not saved: the axis's lowest and highest values are the same.\" or \"Not saved: the axis's center is outside its lowest and highest values.\" Calibrate it again, then save.</li>"
                + "<li><b>Undo</b> and <b>Redo</b> (<b>Ctrl+Z</b>, <b>Ctrl+Y</b>) step back through each axis's changes (a value typed, Reset, a calibration started) until you choose another module.</li>"
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
                + "<li><b>Overwrite used inputs</b> replaces existing actions on those inputs; off keeps them. With it on, <b>Create 1:1 Actions</b> asks first, then removes every action on those inputs in that mode, macros included. The choice is remembered for next time.</li>"
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
                + "<li><b>Automatically Start</b> applies both switches each time the program starts. All switches start off on a new install.</li>"
                + "</ul>",
            related: ["home-devices-hidden-cards", "getting-started-device-missing", "tools-q-game-sees-both"]
        },

        {
            id: "tools-history",
            section: "History",
            title: "See saved changes in History",
            body: "<p><b>Tools › History</b> <a href=\"open:tools.history\">Open ›</a> lists every saved change, newest first.</p>"
                + "<ul>"
                + "<li>Profile saves: each input whose actions changed, and other parts such as modes and the Logical Device.</li>"
                + "<li>Module files: checked controls and names, calibration, Appearance, the Button Map.</li>"
                + "<li>The Device Library's list and saved setups, labelled <b>Device Library</b>.</li>"
                + "<li>The settings you choose in Options, HidHide and OSC.</li>"
                + "</ul>"
                + "<ol>"
                + "<li>Pick a change to see it <b>Before</b> and <b>After</b>. See <a href=\"topic:tools-history-compare\">Compare Before and After</a>.</li>"
                + "<li>To narrow the list to one kind, use <b>Show</b>: <b>All</b>, <b>Profile</b>, <b>Module files</b>, <b>Button Map</b> or <b>Settings</b>. To find a device, input or file, type in <b>Search</b>; it looks in each change's title and in what it is about.</li>"
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
                + "<li>A part of a profile (modes, the Logical Device, OSC, Profile Settings, scripts) can't be restored on its own: \"Put this back with Restore on the profile's save, below it in the list.\"</li>"
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
                + "<li>The question says how many changes and how many MB of kept copies go. Choose <b>Clear History</b> to go ahead; <b>Cancel</b> is the default.</li>"
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
            body: "<p><b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a> has three tabs: <b>Config</b>, <b>Debug</b> and <b>Input Monitor</b>.</p>"
                + "<ul>"
                + "<li><b>Config</b> follows the program's activity log (logs.txt): which profiles, modules and settings files were read and saved, and when. Use it to check how a file loads. It starts empty at every start; <b>Clear Log</b> empties it (it asks first) and <b>Copy All</b> copies it.</li>"
                + "<li><b>Debug</b> shows the diagnostic logs in the Logs folder: <b>System</b> (system.log: errors, warnings, blocked outputs), <b>Scripts</b> (user.log), <b>Events</b> (event.log), <b>All logs</b> (every file together in time order, each line tagged with its log: [System], [Scripts], [Events], [Qt]) and <b>Qt</b> (qt.log: Qt's own messages, such as QML warnings, each with the time).</li>"
                + "</ul>"
                + "<p>On the Debug tab:</p>"
                + "<ul>"
                + "<li><b>Show</b> picks the lowest level shown and <b>Find</b> narrows it to entries with that text. Warnings and errors are in color.</li>"
                + "<li>For a large file only the last 512 KB is shown at first; <b>Load Whole File</b> reads all of it.</li>"
                + "<li><b>Clear Log</b> empties the shown file. It asks first.</li>"
                + "<li>What gets written is the <b>Diagnostic logs</b> <a href=\"show:option/Diagnostic logs\">Show me ›</a> level at the bottom of the tab, the same setting as in Options (<b>General</b>, <b>Diagnostics</b>); changing either changes both, at once.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Show</b> only filters what is already in the file: a level the program is not writing has no lines to show.</li>"
                + "<li>With <b>Log When Not Responding</b> <a href=\"show:option/Log When Not Responding\">Show me ›</a> on, system.log also says when the program stops responding for 5 seconds, where it was stuck, and when it responds again.</li>"
                + "<li>Qt's messages also show in the console when the program is started from one. qt.log moves to qt.log.1 at start-up once over 1 MB, and grows at most 5 MB a session.</li>"
                + "</ul>",
            related: ["tools-live", "tools-input-monitor", "tools-red-debug-mode", "getting-started-save-diagnostics"]
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
            id: "tools-red-debug-mode",
            section: "Live Log Reader",
            title: "Red debug mode",
            body: "<p>While <b>Diagnostic logs</b> is <b>ALL</b> or Live runs, every window has a red frame and a <b>DEBUG</b> badge at the top.</p>"
                + "<ul>"
                + "<li>Click the badge to open the Live Log Reader.</li>"
                + "<li>Button Map exports and prints never include it.</li>"
                + "</ul>",
            related: ["tools-live", "tools-live-log"]
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
            body: "<p>Running the profile does not hide controllers. Hide the physical stick with HidHide. See <a href=\"topic:tools-hidhide\">Hide controllers from games with HidHide</a>.</p>",
            related: ["tools-hidhide"]
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
            body: "<p>Diagnostic logs is set to ALL or Live is running. See <a href=\"topic:tools-red-debug-mode\">Red debug mode</a>.</p>",
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
