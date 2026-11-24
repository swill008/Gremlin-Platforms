// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Tools (viewers, calibration, device information, History,
// Auto Mapping Tool, HidHide, Drivers, Input Tester, Search, Health, Screen Saver
// Mode, Live Log Reader). Device Mapping Editor and Device Library have
// chapters of their own. Written to claude/plans/help-style-guide.md: each
// topic opens with what it's for, then "How to", "What you see" and "Good to
// know" (empty sections left out).

.pragma library

var chapter = { id: "tools", title: "Tools" }

function topics() {
    return [
        {
            id: "tools-viewers",
            section: "Devices",
            title: "Watch live values in the viewers",
            body: "<p>The viewers show live values. They only look; they change nothing.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>vJoy Viewer</b> <a href=\"open:tools.vjoyViewer\">Open ›</a>: each physical device beside the vJoy device it drives.<ul>"
                + "<li>The physical side shows the inputs the input module uses.</li>"
                + "<li>The vJoy side shows what was sent to vJoy while the profile runs.</li>"
                + "<li>Every source that sends to vJoy gets a card, OSC and the Logical Device included.</li>"
                + "<li>Use it as a quick \"did it register?\" check. Device Bindings shows the full bindings.</li>"
                + "</ul></li>"
                + "<li>The Xbox 360 Controller's <b>Output View</b> <a href=\"open:view.xboxOutput\">Open ›</a>: one section for each Xbox pad that is on and bound.<ul>"
                + "<li>Each section shows the pad's live picture, the devices that drive it and the inputs that send to each control.</li>"
                + "<li>The ViGEmBus check and the number of pads are in <b>Xbox Setup</b>. See <a href=\"topic:home-devices-xbox-output\">Xbox output module</a>.</li>"
                + "</ul></li>"
                + "<li><b>Input Tester…</b> <a href=\"show:menu/Tools/Viewers/Input Tester…\">Show me ›</a>: a separate program that shows which controllers your games can see. See <a href=\"topic:tools-input-tester\">Check what a game sees (Input Tester)</a>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The vJoy Viewer also opens from the toolbar and from a card's menu.</li>"
                + "</ul>",
            related: ["home-devices-xbox-output", "home-devices-vjoy-output", "tools-input-monitor"]
        },
        {
            id: "tools-calibration",
            section: "Devices",
            title: "Calibrate axes",
            body: "<p>Calibration sets the center and the ends of each axis, so its full travel is used. It is applied before any action sees the axis.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Device Setup › Calibration</b> <a href=\"open:tools.calibration\">Open ›</a>, or <b>Calibration</b> in a card's menu.</li>"
                + "<li>Choose the input module. Every axis is listed.</li>"
                + "<li>For each axis, move the stick and use <b>Calibrate Center</b> and <b>Calibrate Extrema</b>. You can also type the values.</li>"
                + "<li>Press the axis's save button, or <b>Save All</b> to save every unsaved axis at once.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Not saved</b>: the axis has changes you haven't saved yet.</li>"
                + "<li><b>(not claimed)</b>: the input module doesn't use this axis.</li>"
                + "<li>The message line at the bottom: what the last save did, or in red why nothing was written. It stays until the next message.</li>"
                + "<li><b>Undo</b> and <b>Redo</b> (<b>Ctrl+Z</b>, <b>Ctrl+Y</b>): until you choose another module, they step back and forward through each axis's changes.</li>"
                + "<li>Beside them, \"Last change: <i>axis</i>, <i>what</i>\" names the newest change, or \"Undone: a change to <i>axis</i>\" after an Undo.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An axis put back to its saved values is no longer unsaved.</li>"
                + "<li>An axis that can't work isn't saved, and the message line says why and what to do.<ul>"
                + "<li>For example, when its lowest and highest values are the same, or its center is outside them.</li>"
                + "</ul></li>"
                + "<li>Leaving with unsaved axes asks first.</li>"
                + "</ul>",
            related: ["home-devices-input-modules", "getting-started-saved-where"]
        },
        {
            id: "tools-device-information",
            section: "Devices",
            title: "Device Information",
            body: "<p><b>Tools › Device Setup › Device Information</b> <a href=\"open:tools.deviceInfo\">Open ›</a> lists every device Windows reports. Use it to tell identical devices apart.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>For each device: Name, Axes, Buttons, Hats, VID, PID, Joystick ID and Device ID.</li>"
                + "<li>A vJoy device the program leaves out is marked \"left out (see message)\".</li>"
                + "<li>The program's own Xbox pads are marked \"this program's Xbox pad\".</li>"
                + "</ul>",
            related: ["home-devices-home"]
        },
        {
            id: "tools-auto-mapping-tool",
            section: "Devices",
            title: "Create actions with the Auto Mapping Tool",
            body: "<p>The Auto Mapping Tool creates Map to vJoy actions in one step. Each input of an input module gets an action to the same number on a vJoy output module.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Mapping › Auto Mapping Tool</b> <a href=\"open:tools.autoMappingTool\">Open ›</a>, or <b>Auto Mapping Tool</b> in a card's menu.</li>"
                + "<li>Tick the input modules and output modules. The first ticked input goes to the first ticked output, the second to the second, and so on.</li>"
                + "<li>Choose <b>Select Mode</b>. It starts on the mode shown in the Mode box.</li>"
                + "<li>Choose <b>Create 1:1 Actions</b>. The result names the mode the actions went into.</li>"
                + "<li>Save the profile to keep the new actions.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Combine onto selected outputs</b>: reuses the ticked outputs in turn when there are more inputs than outputs.</li>"
                + "<li><b>Also claim the matching outputs on the output module</b> (off at first): turns on the outputs the new actions need first.</li>"
                + "<li><b>Overwrite used inputs</b>: off keeps existing actions; on replaces them. The choice is remembered.<ul>"
                + "<li>With it on, <b>Create 1:1 Actions</b> asks first. The red <b>Replace Actions</b> removes every action on those inputs in that mode, macros included.</li>"
                + "<li><b>Enter</b> and <b>Esc</b> cancel the question.</li>"
                + "</ul></li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The new actions aren't saved yet. To take them back, load the profile again without saving.</li>"
                + "<li>The result says so when the Mode box shows another mode than the one the actions went into.</li>"
                + "<li>Only outputs the output module uses are filled. Each skipped control is listed with the reason.<ul>"
                + "<li>The reasons: the output module doesn't use it, the vJoy device doesn't have it, or another input in this mode already uses it.</li>"
                + "</ul></li>"
                + "<li>\"Already used\" counts every input of the profile in that mode, including sticks that aren't plugged in and the Logical Device.</li>"
                + "<li>It also counts Map to vJoy actions inside other actions, such as Condition, Chain and Tempo.</li>"
                + "<li>A vJoy device read back as an input (set in Options) can't be sent to. The result says \"vJoy <i>N</i> is used as an input\".</li>"
                + "<li>An input module left without an output is named in the result. Tick more outputs, or turn on <b>Combine onto selected outputs</b>.</li>"
                + "<li>While the profile runs, the changes take effect the next time it starts.</li>"
                + "<li><b>Esc</b> doesn't close the window, so a stick that sends Esc can't close it by accident.</li>"
                + "</ul>",
            related: ["getting-started-first-setup", "home-devices-vjoy-output", "modes-mode-box"]
        },
        {
            id: "tools-hidhide",
            section: "Devices",
            title: "Hide controllers from games with HidHide",
            body: "<p>HidHide (a separate driver) hides your physical controllers from games, so they see only vJoy or the Xbox pads. Gremlin-Platforms always sees them.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Device Setup › HidHide</b> <a href=\"open:tools.hidhide\">Open ›</a>.</li>"
                + "<li>Turn on <b>Gremlin-Platforms controls HidHide</b>, so this program can change HidHide's settings.</li>"
                + "<li>Turn on <b>HidHide Enabled</b> to turn hiding on.</li>"
                + "<li>Tick the devices to hide. A hidden device is dimmed and marked HIDDEN.</li>"
                + "<li>Choose the list. For hiding your sticks from your games, keep <b>Allow list</b> (the default):<ul>"
                + "<li><b>Allow list</b>: leave your game off the list. Every program not on it, every game and every copy of a game included, can't see the hidden devices.</li>"
                + "<li><b>Block list</b>: add your game with <b>Add Program</b>. Only the programs on the list can't see the hidden devices, so list each copy of the game.</li>"
                + "</ul></li>"
                + "<li>Choose <b>Test HidHide</b> to open the Windows Game Controllers panel. With Allow list, a hidden device should be missing there.<ul>"
                + "<li>With Block list, the panel still shows it, because the panel isn't on the list. Use the Input Tester instead.</li>"
                + "</ul></li>"
                + "<li>Start the game. See <a href=\"topic:tools-hidhide-timing\">Start the game after a HidHide change</a>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Gremlin-Platforms controls HidHide</b>: until it is on, the settings show but can't be changed.<ul>"
                + "<li>While it is on, the lists here replace HidHide's own lists. Anything you added in HidHide's own window is removed.</li>"
                + "</ul></li>"
                + "<li><b>HidHide Enabled</b>: turns hiding on and off. If the driver refuses, the switch flips back and the error shows.</li>"
                + "<li><b>Automatically Start</b>: applies both switches each time the program starts. All switches start off.</li>"
                + "<li><b>Gaming devices only</b>: shortens the device list.</li>"
                + "<li><b>Allow list</b> (the default): only the listed programs, and this program, see hidden devices.</li>"
                + "<li><b>Block list</b>: the listed programs don't see hidden devices; every other program does.</li>"
                + "<li><b>Add Program</b>: adds a program to the list. Removing one asks first; the red <b>Remove Program</b> removes it.</li>"
                + "<li><b>Input Tester</b>: shows what a game sees. See <a href=\"topic:tools-input-tester\">Check what a game sees (Input Tester)</a>.</li>"
                + "<li><b>Add Input Tester to the list</b>: shown while the tester isn't on the list. It adds the tester like <b>Add Program</b>.</li>"
                + "<li><b>Update path</b>: shown when the list has an older copy of the tester. It puts the current one on the list.</li>"
                + "<li><b>Restart Input Tester</b>: shown by the warning that the tester was started before the last HidHide change. It opens a fresh tester; close the old window.</li>"
                + "<li><b>Last Status</b>, under the buttons: the Input Tester's last result.</li>"
                + "<li><b>Reset Devices…</b>: restarts your sticks. See <a href=\"topic:tools-hidhide-reset\">Restart your sticks with Reset Devices</a>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Without the driver, the page says \"HidHide is not installed\". <b>Tools › Drivers</b> installs it: see <a href=\"topic:tools-drivers\">Install and update the drivers (Drivers)</a>.</li>"
                + "<li>HidHide hides only HID devices: the controllers games read through DirectInput or raw input.</li>"
                + "<li>Xbox controllers that games read through XInput, this program's own Xbox pads included, aren't HID devices. HidHide doesn't hide them.</li>"
                + "<li>Turning <b>Gremlin-Platforms controls HidHide</b> off leaves HidHide as it is. To show hidden devices again, untick them first.</li>"
                + "<li>The page warns when a listed game is running from another folder.</li>"
                + "<li>While HidHide's own window (HidHide Configuration Client) is open, no other program can talk to HidHide. The page says so: close HidHide's window.</li>"
                + "<li>The exact rules are in <a href=\"topic:tools-tech-hidhide\">How HidHide decides</a>.</li>"
                + "</ul>",
            related: ["tools-hidhide-timing", "tools-hidhide-reset", "tools-input-tester", "tools-tech-hidhide", "home-devices-hidden-cards", "getting-started-device-missing", "tools-q-game-sees-both"]
        },
        {
            id: "tools-hidhide-timing",
            section: "Devices",
            title: "Start the game after a HidHide change",
            body: "<p>HidHide checks a program only when the program opens a device. A game that already has a stick open keeps it after any HidHide change. So set HidHide up first, then start the game.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Change HidHide on its page <a href=\"open:tools.hidhide\">Open ›</a>.</li>"
                + "<li>Restart any listed game that was running, or use <b>Reset Devices…</b> (see <a href=\"topic:tools-hidhide-reset\">Restart your sticks with Reset Devices</a>).</li>"
                + "<li>Restart the Input Tester too, if it is open: <b>Restart Input Tester</b> on this page, or <b>Restart tester</b> in the tester's own window.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The page warns when a listed program that is running was started before the last HidHide change. Restart it so the change applies.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>This covers every change: hidden devices, the program list, <b>HidHide Enabled</b> and Allow or Block.</li>"
                + "<li>Programs started after a change get the new settings.</li>"
                + "<li>HidHide has no \"check again\" command. Unplugging the stick and plugging it back in also makes every program open it again.<ul>"
                + "<li>Don't do this in the middle of a game.</li>"
                + "</ul></li>"
                + "<li>Turned <b>HidHide Enabled</b> off and back on?<ul>"
                + "<li>No listed program was running while it was off: there is nothing to do.</li>"
                + "<li>A listed game was running, or started, while it was off: restart it, or use <b>Reset Devices…</b>.</li>"
                + "<li>This program never needs either: it always sees your devices.</li>"
                + "</ul></li>"
                + "<li>A program is listed by its full path. Capital letters don't matter, and spaces are fine.</li>"
                + "<li>A copy of the game in another folder, such as a test build (PTU) beside the main one (LIVE), is a different program. List each copy.</li>"
                + "<li>A hidden device is known by its Windows device path. In another USB port, a stick can get a new path that isn't hidden.<ul>"
                + "<li>The Input Tester and the Trace tab's HidHide row show this.</li>"
                + "</ul></li>"
                + "</ul>",
            related: ["tools-hidhide", "tools-hidhide-reset", "tools-input-tester", "tools-tech-hidhide"]
        },
        {
            id: "tools-hidhide-reset",
            section: "Devices",
            title: "Restart your sticks with Reset Devices",
            body: "<p><b>Reset Devices…</b> restarts your sticks in Windows, as if you unplugged them and plugged them back in. Every program then opens them again and HidHide checks them anew. You don't have to restart the game.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Center your sticks.</li>"
                + "<li>On the HidHide page <a href=\"open:tools.hidhide\">Open ›</a>, choose <b>Reset Devices…</b>, the red button by the <b>Devices</b> heading.</li>"
                + "<li>Tick the devices to restart. The hidden ones are ticked for you.</li>"
                + "<li>Choose <b>Reset N Devices</b>. Windows may ask for administrator permission, once for all of them.</li>"
                + "<li>Read each row's result.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Your plugged-in USB game controllers, never vJoy or this program's Xbox pads.</li>"
                + "<li>The tags <b>hidden</b> and <b>in the profile</b>, where they apply.</li>"
                + "<li>The list follows plugging and unplugging while the window is open.</li>"
                + "<li>Xbox pads aren't ticked: their row says they can't be restarted live. You can still tick one.</li>"
                + "<li>The name of any listed game that is running.</li>"
                + "</ul>"
                + "<table><tr><th>Result</th><th>What it means</th></tr>"
                + "<tr><td><b>reset ✓ · back after N.N s</b></td><td>The device restarted and came back.</td></tr>"
                + "<tr><td><b>reset ✓ · not back after 10 s</b></td><td>The device restarted but hasn't come back yet.</td></tr>"
                + "<tr><td><b>needs a Windows restart, or unplug it and plug it back in</b></td><td>Windows can't restart this device while it runs. Unplugging it does the same job.</td></tr>"
                + "<tr><td><b>not found</b></td><td>The device was already gone.</td></tr>"
                + "<tr><td><b>permission declined</b></td><td>You said No to Windows, so nothing was reset.</td></tr>"
                + "<tr><td><b>failed</b></td><td>The restart failed. The row gives the code.</td></tr>"
                + "<tr><td><b>back ✓ (plugged back in)</b></td><td>A device that wasn't back has come back.</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Use it after you change HidHide while a game or the Input Tester runs.</li>"
                + "<li>Use it also when the Input Tester shows <b>Programs can see it: should be hidden</b> for a stick you hid.</li>"
                + "<li>The button is also next to each \"started before the last HidHide change\" warning.</li>"
                + "<li>While a stick restarts (about 2-3 seconds), the program keeps its axes where they were and releases its buttons.</li>"
                + "<li>A running game loses the stick for that moment. Don't do this in the middle of a game.</li>"
                + "<li>Some controllers, such as an Xbox One controller, can only be restarted by unplugging them.</li>"
                + "<li>A reset doesn't change HidHide's settings, so no \"started before\" warning follows.</li>"
                + "<li>A running Input Tester sees the sticks come back and checks them again.</li>"
                + "<li>The results are also written to the system log.</li>"
                + "</ul>",
            related: ["tools-hidhide", "tools-hidhide-timing", "tools-tech-hidhide"]
        },
        {
            id: "tools-drivers",
            section: "Devices",
            title: "Install and update the drivers (Drivers)",
            body: "<p>The program needs three drivers: <b>vJoy</b> (virtual joysticks games can read), <b>ViGEmBus</b> (virtual Xbox 360 pads) and <b>HidHide</b> (hides your controllers from games). <b>Tools › Drivers</b> installs and updates them, and sets up the vJoy devices.</p>"
                + "<p>Setup has the same page: see <a href=\"topic:getting-started-setup-drivers\">Setup's Drivers page</a>.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Drivers</b> <a href=\"open:tools.drivers\">Open ›</a>.</li>"
                + "<li>Tick the drivers to install or update.</li>"
                + "<li>Set up the vJoy devices. See <a href=\"topic:tools-drivers-vjoy-devices\">Set up vJoy devices</a>.</li>"
                + "<li>Choose <b>Apply</b>. The box <b>Apply driver changes</b> says what will happen and when. Choose <b>OK</b>.</li>"
                + "<li>The program may then ask more questions, in this order:<ul>"
                + "<li><b>Run is on</b>: a profile is running, and Run stops while the vJoy devices change. <b>Yes</b> stops Run; <b>No</b> changes nothing.</li>"
                + "<li><b>vJoy update and your devices</b>: vJoy is being updated, and the box names the devices the program has noted. Choose <b>OK</b>.</li>"
                + "<li><b>Devices in use</b>: a device you change or remove is in use by another program. <b>Yes</b> changes it anyway; <b>No</b> goes back.</li>"
                + "<li><b>Devices that can't be told apart</b>: two devices have the same numbers of axes, buttons and hats. <b>Yes</b> goes ahead; <b>No</b> goes back.</li>"
                + "</ul></li>"
                + "<li>Windows asks for administrator permission.</li>"
                + "<li>A progress line shows each step, such as \"Installing vJoy 2.2.2.0…\". Each driver then shows its result.</li>"
                + "<li>When Windows needs a restart, choose <b>Restart now</b> or <b>Restart later</b>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>One row for each driver: vJoy, ViGEmBus and HidHide.</li>"
                + "<li>Each row shows what is installed now: <b>not installed</b>, a version number, or <b>update available</b>: <i>old</i> → <i>new</i>.</li>"
                + "<li>A missing driver has its box ticked. An older driver has an update box, unticked: tick it to update.</li>"
                + "<li>A driver that is the same version or newer has no box and is never touched.</li>"
                + "<li>Under <b>vJoy devices</b>, the device list. See <a href=\"topic:tools-drivers-vjoy-devices\">Set up vJoy devices</a>.</li>"
                + "<li>Rows marked <b>lost in the vJoy update</b>, each with <b>Repair</b>. See <a href=\"topic:tools-drivers-vjoy-update\">Keep your vJoy devices through a vJoy update</a>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The program carries its own copy of each driver: vJoy 2.2.2.0, ViGEmBus 1.22.0 and HidHide 1.5.230.</li>"
                + "<li>For vJoy and HidHide, it also checks the project's GitHub page for a newer version.<ul>"
                + "<li>It uses a newer version only when Windows shows it is signed by the project itself.</li>"
                + "<li>The signers are Brunner Elektronik AG for vJoy and Nefarius Software Solutions for HidHide.</li>"
                + "<li>Otherwise, or with no internet connection, it uses its own copy.</li>"
                + "</ul></li>"
                + "<li>ViGEmBus has no newer version: the project has ended, and 1.22.0 is the last one.</li>"
                + "<li>Before a copy runs, it is checked against a stored fingerprint. A copy that doesn't match is never run.</li>"
                + "<li>A step that fails never stops the others. Each result gives the reason.</li>"
                + "<li>The program itself never runs as administrator. A small helper, <b>Gremlin Device Helper</b>, does the driver work.</li>"
                + "<li>Updating HidHide takes two restarts. See <a href=\"topic:tools-drivers-hidhide-update\">Update HidHide in two restarts</a>.</li>"
                + "<li>When vJoy or ViGEmBus is missing, the message about it has <b>Open Drivers</b>, which opens this window.<ul>"
                + "<li>Install the driver, then restart the program.</li>"
                + "</ul></li>"
                + "<li>The program's own update (<b>Update Now</b>) never changes a driver.</li>"
                + "<li>Uninstalling Gremlin-Platforms leaves the three drivers installed.</li>"
                + "<li>Setup also checks the Microsoft Visual C++ Runtime. Tools › Drivers doesn't.</li>"
                + "</ul>",
            related: ["tools-drivers-vjoy-devices", "tools-drivers-vjoy-update", "tools-drivers-hidhide-update", "getting-started-setup-drivers", "tools-hidhide", "home-devices-vjoy-output", "home-devices-xbox-output"]
        },
        {
            id: "tools-drivers-vjoy-devices",
            section: "Devices",
            title: "Set up vJoy devices",
            body: "<p>vJoy devices are the virtual joysticks your bindings send to, and that games read. In <b>Tools › Drivers</b>, you choose how many there are and what each one has.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open <b>Tools › Drivers</b> <a href=\"open:tools.drivers\">Open ›</a>.</li>"
                + "<li>Under <b>vJoy devices</b>, choose a <b>Preset</b>, or set the number in <b>Devices</b>.</li>"
                + "<li>In each row, tick the device's axes and choose its buttons and hats.</li>"
                + "<li>To add a device, choose <b>+ Add device</b>, the last row of the list.</li>"
                + "<li>To remove a device, choose <b>✕</b> at the end of its row.</li>"
                + "<li>Choose <b>Apply</b>. See <a href=\"topic:tools-drivers\">Install and update the drivers (Drivers)</a>.</li>"
                + "<li>Then set up each new device's output module: only the outputs ticked there are sent to vJoy. See <a href=\"topic:home-devices-vjoy-output\">Set up a vJoy output module</a>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Preset</b>:<ul>"
                + "<li><b>1 device, full</b> (the default): one device with all 8 axes, 128 buttons and 4 hats.</li>"
                + "<li><b>2 devices, full</b>: two such devices, vJoy 1 with 128 buttons and vJoy 2 with 127.</li>"
                + "<li><b>Custom</b>: you set up each device yourself, up to 16. Changing any row switches <b>Preset</b> to <b>Custom</b>.</li>"
                + "</ul></li>"
                + "<li><b>Devices</b>: how many devices, from 1 to 16. Choosing fewer removes the highest-numbered devices.</li>"
                + "<li>The device list: one row per device, with the column headings once at the top.</li>"
                + "<li>Each row: the device's name, eight axis tick boxes, its buttons (0 to 128), its hats (0 to 4) and <b>✕</b>.</li>"
                + "<li>The tick boxes are the axes X Axis, Y Axis, Z Axis, X Rotation, Y Rotation, Z Rotation, Slider 1 and Slider 2.<ul>"
                + "<li>Their short names read <b>X</b>, <b>Y</b>, <b>Z</b>, <b>Rx</b>, <b>Ry</b>, <b>Rz</b>, <b>S1</b> and <b>S2</b>.</li>"
                + "</ul></li>"
                + "<li><b>+ Add device</b>: shows in gray what it adds, such as \"vJoy 3 · 126 buttons\". It is gone at 16 devices.</li>"
                + "<li>A device name in red: another program is using that device. Point at it to read <b>in use by another program</b>.</li>"
                + "<li>Under the list: a hint, and a line such as \"Showing 1-4 of 6 devices\".</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Each new device gets one button fewer than the one before: vJoy 1 has 128, and vJoy 16 has 113.<ul>"
                + "<li>The program tells vJoy devices apart only by their numbers of axes, buttons and hats.</li>"
                + "<li>Two devices with the same three numbers can't both be used.</li>"
                + "</ul></li>"
                + "<li>Every device keeps at least one axis: the last ticked box can't be unticked.</li>"
                + "<li>The devices vJoy already has are shown as they are. They change only when you edit them.</li>"
                + "<li>When you edit, a line warns that running games lose the vJoy devices until they restart. Close your games first.</li>"
                + "<li>All devices are set up in one go, so the vJoy driver restarts only once.</li>"
                + "<li>The program doesn't need a restart: it reads the new device list by itself, as when you plug in a stick. Running games do need a restart.</li>"
                + "<li>If Apply stopped Run, start it again when the results show.</li>"
                + "<li>After the set-up, the program reads each device back from vJoy. If one isn't what you asked for, its result says it failed.</li>"
                + "<li>The program's own devices are never marked as in use.</li>"
                + "<li>When the list is longer than the window, it scrolls. The heading, the boxes and <b>Apply</b> stay in view.</li>"
                + "</ul>",
            related: ["tools-drivers", "tools-drivers-vjoy-update", "home-devices-vjoy-output"]
        },
        {
            id: "tools-drivers-vjoy-update",
            section: "Devices",
            title: "Keep your vJoy devices through a vJoy update",
            body: "<p>Updating vJoy can lose vJoy devices that were set up with older vJoy tools. The program notes your devices before the update and checks them afterwards, so you can put back any it lost.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>In <b>Tools › Drivers</b> <a href=\"open:tools.drivers\">Open ›</a>, tick vJoy's update box and choose <b>Apply</b>.</li>"
                + "<li>The box <b>vJoy update and your devices</b> names the devices the program has noted. Choose <b>OK</b>.</li>"
                + "<li>After the update, the program checks the devices again.</li>"
                + "<li>If one is missing or different, the box <b>The vJoy update lost a device</b> names it. Choose <b>Repair Now</b> or <b>Repair Later</b>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<table><tr><th>Choice</th><th>What it does</th></tr>"
                + "<tr><td><b>Repair Now</b></td><td>Puts the lost devices back exactly as they were. It removes nothing.</td></tr>"
                + "<tr><td><b>Repair Later</b></td><td>Keeps each lost device in the list, marked <b>lost in the vJoy update</b>.</td></tr>"
                + "<tr><td><b>Repair</b></td><td>On a lost device's row: puts that device back at once, without <b>Apply</b>.</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The check runs only for an update of vJoy, not for a fresh install.</li>"
                + "<li>If the devices can't be read before the update, the box says so. Check them in Tools › Drivers afterwards.</li>"
                + "<li>If you also changed the device list, the check runs after both the update and your changes.<ul>"
                + "<li>A device you removed on purpose isn't reported as lost.</li>"
                + "</ul></li>"
                + "<li>A lost device that is back with the same layout drops off the list by itself.</li>"
                + "<li>A device that only the update added, such as the new driver's own vJoy 1, is left alone. The results name it.</li>"
                + "<li>A repair is one more driver step, so Windows asks for administrator permission again.</li>"
                + "<li>After a repair, as after Apply, the program reads the devices again by itself. Running games need a restart.</li>"
                + "</ul>",
            related: ["tools-drivers", "tools-drivers-vjoy-devices", "home-devices-vjoy-output"]
        },
        {
            id: "tools-drivers-hidhide-update",
            section: "Devices",
            title: "Update HidHide in two restarts",
            body: "<p>HidHide can't be updated in one go: Windows has to restart between removing the old HidHide and installing the new one. Until both restarts are done, your devices aren't hidden.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>In <b>Tools › Drivers</b> <a href=\"open:tools.drivers\">Open ›</a>, tick HidHide's update box and choose <b>Apply</b>.</li>"
                + "<li><i>Step 1 of 2.</i> A box says the old HidHide is removed now and the new one installed after a restart. Choose <b>Continue</b>.</li>"
                + "<li>The old HidHide is removed. Windows asks you to restart.</li>"
                + "<li><i>Step 2 of 2.</i> At its next start, the program asks you to finish the HidHide update. Choose <b>Install now</b>.</li>"
                + "<li>Windows asks for administrator permission, and the new HidHide is installed.</li>"
                + "<li>Windows asks for one more restart.</li>"
                + "<li>Open the HidHide page <a href=\"open:tools.hidhide\">Open ›</a> to check that your devices are hidden again.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Skip HidHide update</b> in step 1 leaves HidHide as it is.</li>"
                + "<li><b>Later</b> in step 2 waits. Until you finish, <b>Home</b> says \"HidHide update not finished: devices aren't hidden\", with <b>Finish update</b>.</li>"
                + "<li>Windows asks for the first restart even when HidHide's own uninstaller doesn't.</li>"
                + "</ul>",
            related: ["tools-drivers", "tools-hidhide"]
        },
        {
            id: "tools-input-tester",
            section: "Devices",
            title: "Check what a game sees (Input Tester)",
            body: "<p>HidHide never hides anything from this program, so this program can't show you what a game sees. The <b>Gremlin Input Tester</b> is a small separate program that HidHide treats like a game. Treat it like your game, and it shows which controllers that game can see: with <b>Block list</b>, put it on the list; with <b>Allow list</b>, leave it off.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open <b>Tools › Device Setup › HidHide</b> <a href=\"open:tools.hidhide\">Open ›</a>, with <b>Gremlin-Platforms controls HidHide</b> on.</li>"
                + "<li>With <b>Block list</b>, choose <b>Add Input Tester to the list</b>. With <b>Allow list</b>, skip this step: a listed tester sees the hidden devices, as any listed program does.</li>"
                + "<li>Choose <b>Input Tester</b> on that page or on the toolbar <a href=\"show:toolbar/Input Tester\">Show me ›</a>.</li>"
                + "<li>Read the top line: <b>✓ Pass: programs see only what they should</b>, or <b>✗ Problem:</b> with what is wrong.</li>"
                + "<li>Move a stick: its values move, and the row's <b>activity dot</b> blinks.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The top line. A problem reads, for example, \"programs can see 1 stick that should be hidden\".</li>"
                + "<li>The blue line under it says what HidHide's list means for this window.</li>"
                + "<li>The tabs <b>Devices</b> and <b>Logs</b>. See <a href=\"topic:tools-input-tester-logs\">The Input Tester's logs</a>.</li>"
                + "<li>The device rows, each with a verdict. See <a href=\"topic:tools-input-tester-rows\">Read the Input Tester's rows</a>.</li>"
                + "<li><b>All devices</b>: shows every device at once.</li>"
                + "<li><b>Follow input</b>: chooses the device you move for you. It waits 1 second before it jumps to another device.</li>"
                + "<li><b>Copy result</b>: copies the verdict and every row as text, ready to paste into a message.</li>"
                + "<li>Buttons 1-128 and hats 1-4. With more buttons than fit, they scroll.<ul>"
                + "<li>With <b>Follow input</b> on, a button you press scrolls into view.</li>"
                + "</ul></li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Start the tester after a HidHide change. See <a href=\"topic:tools-hidhide-timing\">Start the game after a HidHide change</a>.</li>"
                + "<li>After a change, a yellow line in the tester says HidHide changed after it started. Choose <b>Restart tester</b> there: a fresh tester opens and the old one closes. The HidHide page's <b>Restart Input Tester</b> also opens a fresh one, but leaves the old window open.</li>"
                + "<li>If Steam is running and can see your hidden sticks, a yellow line says so. Steam Input can pass a hidden stick on to a game.<ul>"
                + "<li>Add steam.exe to HidHide's Block list, or turn off Steam Input for your game.</li>"
                + "</ul></li>"
                + "<li>The HidHide page shows the tester's result as <b>Last Status</b>. The trace's HidHide row writes it too.</li>"
                + "<li>If HidHide's list has an older copy of the tester, the HidHide page says so. <b>Update path</b> puts the current one on the list.</li>"
                + "<li>Opened on its own, the tester shows what it sees without a Pass or Problem. Open it from this program to compare.</li>"
                + "<li>The tester only reads; it changes nothing. It is installed next to this program as <b>Gremlin Input Tester.exe</b>.</li>"
                + "<li>The exact rules are in <a href=\"topic:tools-tech-hidhide\">How HidHide decides</a>.</li>"
                + "</ul>",
            related: ["tools-input-tester-rows", "tools-input-tester-logs", "tools-hidhide", "tools-tech-hidhide", "tools-trace", "tools-q-game-sees-both"]
        },
        {
            id: "tools-input-tester-rows",
            section: "Devices",
            title: "Read the Input Tester's rows",
            body: "<p>Each row in the Input Tester is one device, with a verdict on whether programs can see it. Choose a row to see its values.</p>"
                + "<h4>What you see</h4>"
                + "<table><tr><th>Verdict</th><th>What it means</th></tr>"
                + "<tr><td><b>Hidden from programs</b></td><td>A hidden stick the tester can't see, as it should be. The row is grayed.</td></tr>"
                + "<tr><td><b>Programs can see it: should be hidden</b> (red)</td><td>A game on the list can see this stick as well as vJoy. Tick it on the HidHide page, then choose <b>Restart tester</b>.</td></tr>"
                + "<tr><td><b>Programs can see it</b></td><td>A device programs should see, such as a vJoy device or an Xbox pad.</td></tr>"
                + "<tr><td><b>Programs can see it · not in use</b></td><td>A vJoy device that no output uses.</td></tr>"
                + "<tr><td><b>Programs can't see it: should be shown</b> (red)</td><td>A device programs should see but can't. Check it's plugged in and its output is on.</td></tr>"
                + "<tr><td><b>Not set up in Gremlin</b></td><td>A device this program doesn't use. It is not a problem.</td></tr>"
                + "</table>"
                + "<ul>"
                + "<li>Each row says what it <b>Should be</b>: \"hidden from programs\" or \"seen by programs\".</li>"
                + "<li>When the tester can't see a device, the row says why, such as \"Missing: programs can't see it.\"</li>"
                + "<li>The sections: <b>YOUR CONTROLLERS</b>, <b>GREMLIN'S VIRTUAL JOYSTICKS (vJoy)</b> and <b>XBOX CONTROLLERS</b>.</li>"
                + "<li><b>Show details</b>: adds <b>ALL GAME DEVICES IN WINDOWS</b>, every game device Windows lists.</li>"
                + "<li>The bar at the bottom counts the joysticks, Xbox controllers and game devices this window sees.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>For a stick that should be hidden, also check that <b>HidHide Enabled</b> is on and the game is on the list.</li>"
                + "<li>Two identical sticks are told apart: the tester matches each device by its Windows device path first. See <a href=\"topic:tools-tech-hidhide\">How HidHide decides</a>.</li>"
                + "<li>This program's Xbox pads are matched by the Xbox slot each one got. A pad without a slot yet gets no verdict.</li>"
                + "<li>When a device is read again or changes layout, the tester shows what it has now.</li>"
                + "</ul>",
            related: ["tools-input-tester", "tools-input-tester-logs", "tools-q-game-sees-both"]
        },
        {
            id: "tools-input-tester-logs",
            section: "Devices",
            title: "The Input Tester's logs",
            body: "<p>The Input Tester's <b>Logs</b> tab shows its own log and this program's logs. Use it to see why a device was or wasn't opened.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Log</b>: picks the log to show.<ul>"
                + "<li><b>Tester log (tester.log)</b>: each device the tester tried to open, and what happened.</li>"
                + "<li><b>Gremlin trace.log</b> and <b>Gremlin system.log</b>: this program's trace and system log.</li>"
                + "<li><b>DirectInput reader (dill_debug.log)</b>: the log of the part that reads your sticks.</li>"
                + "</ul></li>"
                + "<li><b>Follow</b>: stays at the end as lines arrive.</li>"
                + "<li><b>Find</b>: searches the lines.</li>"
                + "<li><b>Show</b>: <b>All</b> lines, or only <b>Warnings</b>.</li>"
                + "<li><b>Copy</b>: copies the lines shown.</li>"
                + "<li><b>Open folder</b>: opens the log's folder.</li>"
                + "</ul>"
                + "<table><tr><th>Tester log line</th><th>What it means</th></tr>"
                + "<tr><td><b>open → ok</b></td><td>The tester can see the device, so a game on the same list can see it too.</td></tr>"
                + "<tr><td><b>access denied (5)</b></td><td>HidHide hides the device from the tester. For a stick you hid, that's what you want.</td></tr>"
                + "<tr><td>\"left out: not a game device\"</td><td>A keyboard, mouse or other device the tester doesn't show.</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>On the <b>Devices</b> tab, a device HidHide hides shows as a dimmed \"left out\" row.</li>"
                + "<li>Other \"left out\" lines give their own reason.</li>"
                + "<li>A big file shows its last 512 KB.</li>"
                + "<li>Opened from this program, the tester writes tester.log in the tester folder of the program's data folder.<ul>"
                + "<li>The log grows up to 1 MB. Then one older copy, tester.log.1, is kept.</li>"
                + "</ul></li>"
                + "<li>Opened on its own, the tester keeps its log in the window only.</li>"
                + "<li><b>Save Diagnostics…</b> includes the tester's logs, what this program expects it to see and its last result.</li>"
                + "</ul>",
            related: ["tools-input-tester", "tools-input-tester-rows", "getting-started-save-diagnostics"]
        },

        {
            id: "tools-history",
            section: "History",
            title: "See saved changes in History",
            body: "<p>History lists every saved change, newest first, under day headings. Each row shows the change's title, its time and its area.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › History</b> <a href=\"open:tools.history\">Open ›</a>.</li>"
                + "<li>Pick a change. The right side says in plain words what restoring it will do.</li>"
                + "<li>To see the change line by line, choose <b>Show full before/after</b>. See <a href=\"topic:tools-history-compare\">Compare Before and After</a>.</li>"
                + "<li>To put an earlier version back, see <a href=\"topic:tools-history-restore\">Restore an earlier version</a>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The kinds of changes:<ul>"
                + "<li>Profile saves: each input whose actions changed, and parts such as modes and scripts.</li>"
                + "<li>Module files: checked controls and names, calibration, Appearance, the device map and the Logical Device.</li>"
                + "<li>The Device Library's list and saved setups, labelled <b>Device Library</b>.</li>"
                + "<li>The settings you choose in Options, HidHide and OSC.</li>"
                + "</ul></li>"
                + "<li>Day headings: <b>Today</b>, <b>Yesterday</b>, then the date.</li>"
                + "<li>Folded rows: several changes in a row to the same thing share one row that says how many it holds. Open it to see each one.</li>"
                + "<li><b>Show</b>: narrows the list to <b>All</b>, <b>Profile</b>, <b>Module files</b>, <b>Device Mapping Editor</b> or <b>Settings</b>.</li>"
                + "<li><b>Search</b> (<b>Ctrl+F</b>): finds a device, input or file in each change's title and subject.<ul>"
                + "<li>A line under it says \"N found\" or \"Nothing matches\". <b>×</b> or <b>Esc</b> clears it.</li>"
                + "</ul></li>"
                + "<li>A bar \"N new changes · Show\" when changes are saved while you look. Choose <b>Show</b> or <b>Refresh</b> to add them.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>History</b> in an editor shows only that editor's changes. <b>Show All</b> shows everything again.<ul>"
                + "<li>You find it on Device Bindings (for the selected input), on a Logical Device control's menu and in Module Setup.</li>"
                + "<li>It is also in the Device Mapping Editor's File menu and in Options.</li>"
                + "</ul></li>"
                + "<li><b>Tools › History</b> from the menu always shows every change.</li>"
                + "<li>Your selection and scroll position stay while you look.</li>"
                + "<li>Window sizes and positions, and the Device Mapping Editor's zoom, grid, guides and print area, are saved but never listed in History.</li>"
                + "<li><b>Days to keep changes</b> <a href=\"show:option/Days to keep changes\">Show me ›</a> (90) sets how long changes are kept.</li>"
                + "<li><b>Largest history file (MB)</b> <a href=\"show:option/Largest history file (MB)\">Show me ›</a> (20) sets how big each history file may grow. The oldest changes go first.</li>"
                + "<li>The history folder is set on the <b>Folders</b> page of Options <a href=\"show:option/History folder\">Show me ›</a>.<ul>"
                + "<li>After you move it, older changes stay in the old folder, and History shows only the new one.</li>"
                + "</ul></li>"
                + "<li>The whole profile is kept for the newest 20 saves of each profile.</li>"
                + "<li>A damaged line in a history file is skipped. Every other change still shows.</li>"
                + "<li>While the profile runs, a restore takes effect the next time it starts.</li>"
                + "</ul>",
            related: ["tools-history-compare", "tools-history-restore", "tools-history-clear", "getting-started-saved-where"]
        },
        {
            id: "tools-history-compare",
            section: "History",
            title: "Compare Before and After",
            body: "<p><b>Show full before/after</b> shows a change in History as <b>Before</b> and <b>After</b>, side by side and lined up row for row.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>In <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a>, pick a change.</li>"
                + "<li>Choose <b>Show full before/after</b>.</li>"
                + "<li>Use <b>Previous Change</b> and <b>Next Change</b> to move between the changed lines.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>A changed line has a soft tint and a thin bar on its left edge: red on Before, green on After.</li>"
                + "<li>Inside a changed line, the words that changed have a stronger tint. Unchanged lines stay plain.</li>"
                + "<li><b>Previous Change</b> and <b>Next Change</b> move both sides together. Each is off when there is no change that way.</li>"
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
            body: "<p>Restore puts back the version before or after a saved change.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a> and pick the change.</li>"
                + "<li>Choose <b>Restore to before this change</b> to undo it.</li>"
                + "<li>To put back the version after it instead, choose the link <b>Restore to after this change</b>.</li>"
                + "<li>Either one asks first. Confirm to restore.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>A restore adds no new row. The change you restored gets the tag <b>Restored · HH:MM</b>.</li>"
                + "<li>If you then undo that restore, the tag says <b>Reapplied · HH:MM</b>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An input's actions go back into the open profile, unsaved. Open that profile first, and save it to keep them.<ul>"
                + "<li>History records the restore when you save the profile.</li>"
                + "</ul></li>"
                + "<li>A module file, with its pictures, and settings are saved at once, and the restore is recorded at once.</li>"
                + "<li>The Logical Device and OSC have their own module files, so their entries can be restored on their own.</li>"
                + "<li>A Device Library change: only that change is undone. Later changes to the Library stay.</li>"
                + "<li>A whole profile, on its save's entry, is written as a copy next to the profile.<ul>"
                + "<li>Open the copy with <b>File › Load Profile…</b> <a href=\"show:menu/File/Load Profile\">Show me ›</a>. It stays until you delete it.</li>"
                + "<li>If that folder is outside your profiles folder, it asks first. Only the red <b>Write Here</b> writes the copy there.</li>"
                + "</ul></li>"
                + "<li>A part of a profile, such as modes, Profile Settings or scripts, can't be restored on its own.<ul>"
                + "<li>Restore the profile's save instead, below it in the list.</li>"
                + "</ul></li>"
                + "<li>A \"Created\" change can't be restored to Before, nor a \"Deleted\" one to After. Those buttons are off.</li>"
                + "<li>A version no longer kept can't be restored.</li>"
                + "</ul>",
            related: ["tools-history", "tools-history-compare", "getting-started-profiles"]
        },
        {
            id: "tools-history-clear",
            section: "History",
            title: "Clear History",
            body: "<p><b>Clear History…</b>, the red button in History, deletes every saved change and the kept copies used to restore them. This can't be undone.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Stop the profile. While it runs, the button is off.</li>"
                + "<li>Open <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a> and choose <b>Clear History…</b>.</li>"
                + "<li>A box says how many changes and how many MB of kept copies go. Choose the red <b>Clear History</b>.</li>"
                + "<li>The message line says \"History cleared.\"</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Cancel</b> has the focus in the box: <b>Enter</b> and <b>Esc</b> both cancel.</li>"
                + "<li>Your profiles, module files and Device Library stay as they are.</li>"
                + "<li>The Device Library's Undo steps for this session go too.</li>"
                + "<li>History keeps a red \"History cleared\" entry with the date and what was deleted.<ul>"
                + "<li>Nothing before it can be restored or undone, so it has no Restore buttons.</li>"
                + "<li>History's own clean-up never removes it. Each later clearing adds another.</li>"
                + "</ul></li>"
                + "</ul>",
            related: ["tools-history", "device-library-undo"]
        },
        {
            id: "tools-search",
            section: "Search",
            title: "Search your profiles",
            body: "<p><b>Search</b> finds keys, actions, names and outputs as you type, in every profile. Each result says in which profile, on which device, in which mode and on which input it is.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Search</b> on the toolbar <a href=\"show:toolbar/Search\">Show me ›</a>, or press <b>Ctrl+Shift+F</b>. Search opens in a window of its own.</li>"
                + "<li>Type. Results show as you type.</li>"
                + "<li>Click a result, or select it and press <b>Enter</b>. The mode changes, the device's page opens and the row flashes.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Listen</b>, the first button, left of the box: press a stick control or a key, or send an OSC message, and Search looks for it.<ul>"
                + "<li>Search shows <b>Heard: …</b>. <b>Esc</b> stops listening.</li>"
                + "<li>OSC is heard only while <b>Listen for OSC messages</b> is on.</li>"
                + "</ul></li>"
                + "<li>The box. You don't need the whole word: the letters you type, in order, are enough (<b>gr tog</b> finds \"Gear toggle\").</li>"
                + "<li>Exact matches and matches at the start of a word come first. The matching letters are highlighted.</li>"
                + "<li>Your recent searches open in the drop-down under the empty box when you click into it.<ul>"
                + "<li>Use <b>Up</b> and <b>Down</b> to pick one, and <b>Enter</b> to search it again.</li>"
                + "<li><b>Clear recent searches</b>, at the end of the list, empties it.</li>"
                + "</ul></li>"
                + "<li>Prefixes look in one place only: <b>key:</b>, <b>vjoy:</b>, <b>xbox:</b>, <b>osc:</b>, <b>mouse:</b>, <b>mode:</b>, <b>profile:</b>, <b>device:</b> or <b>action:</b>.<ul>"
                + "<li>Put a name with spaces in quotes, for example <b>device:\"T.16000M\"</b>.</li>"
                + "<li>The <b>?</b> button lists the prefixes with an example each.</li>"
                + "</ul></li>"
                + "<li>Three buttons beside the box, off at first: <b>Aa</b> (Match case), <b>ab</b> (Whole word) and <b>.*</b> (Regular expression).<ul>"
                + "<li>Letters-in-order matching is off while Regular expression is on.</li>"
                + "</ul></li>"
                + "<li><b>Suggestion list while typing</b>, under the search bar beside the status line, is off at first. Turn it on to see suggestions under the box.</li>"
                + "<li><b>Look in</b>, in the sidebar: <b>All profiles</b>, <b>This profile only</b> or <b>Device Library</b>.</li>"
                + "<li><b>Show</b>, in the sidebar: <b>Keys</b>, <b>Actions</b>, <b>Names</b>, <b>vJoy</b>, <b>Xbox</b> or <b>OSC</b>, each with its number of results.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Before you type, Search shows a short welcome with example searches. It goes as soon as you type or results show.</li>"
                + "<li>Search looks in the open profile too, with its unsaved changes, marked <b>(open)</b>. It also looks in the Device Library's saved setups.</li>"
                + "<li>Search changes a binding only when you choose <b>Remove binding…</b> or <b>Change target…</b>. See <a href=\"topic:tools-search-fix\">Fix a binding from Search</a>.</li>"
                + "<li>To find problems, such as outputs that aren't there, use <b>Health</b>. See <a href=\"topic:tools-health\">Find problems with Health</a>.</li>"
                + "<li>It also opens from <b>Tools › Mapping › Search…</b> <a href=\"show:menu/Tools/Mapping/Search…\">Show me ›</a>.</li>"
                + "<li>Right-click a row, a vJoy Viewer chip, an Xbox Output View row or a mode in Manage Modes, and choose <b>Find uses…</b>.</li>"
                + "<li>Right-click a Home card and choose <b>Search this device</b>. Search opens with the text filled in.</li>"
                + "<li>Keys: <b>Up</b> and <b>Down</b> move through the results. <b>Esc</b> clears the box, and <b>Esc</b> again closes Search.</li>"
                + "<li>Search remembers its size and position, your last search, <b>Look in</b>, the filters and the three buttons.</li>"
                + "<li>The <b>Find</b> bar on a page only filters that page. Search looks through all your profiles.</li>"
                + "<li>Reading the results: see <a href=\"topic:tools-search-results\">Read Search results</a>.</li>"
                + "</ul>",
            related: ["tools-search-results", "tools-search-fix", "tools-health", "tools-history", "tools-viewers"]
        },
        {
            id: "tools-search-results",
            section: "Search",
            title: "Read Search results",
            body: "<p>Search groups its results by profile, then by device. Each line shows the input, the mode and the action.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Each group heading has a count, such as \"3 uses\". Click a heading to fold it; <b>Fold all</b> and <b>Unfold all</b> do every group.</li>"
                + "<li>Click the <b>Input</b>, <b>Mode</b> or <b>Action</b> column heading to sort by it.</li>"
                + "<li>The <b>Input</b> and <b>Mode</b> columns keep the same width, so every line lines up with the headings.</li>"
                + "<li>An action's text shows in full. In a narrow window it is cut in the middle, so the number at the end stays.</li>"
                + "<li>The <b>Details</b> pane on the right shows the selected result in full: its actions and the modes it comes through.<ul>"
                + "<li>With nothing selected, it says \"Pick a result to see it here.\"</li>"
                + "<li>Under <b>Notes</b>, any text you typed into the action.</li>"
                + "<li>Close the pane with its ×. Search remembers whether it is open.</li>"
                + "</ul></li>"
                + "<li>Right-click a result for <b>Open</b>, <b>Open in Device Mapping Editor</b>, <b>Copy as text</b> and <b>Search for this target</b>.<ul>"
                + "<li>The menu and the pane also have <b>Remove binding…</b> and <b>Change target…</b>. See <a href=\"topic:tools-search-fix\">Fix a binding from Search</a>.</li>"
                + "</ul></li>"
                + "<li><b>Inherited from &lt;mode&gt;</b> on a line means the binding is set in that mode and used here, because this mode inherits it.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An inherited binding is listed in every mode that uses it.</li>"
                + "<li>A result in another profile asks you to save the open profile first, if it has unsaved changes. Then that profile opens.</li>"
                + "<li>A Device Library result opens the Device Library on that setup.</li>"
                + "<li>For a device with no input module, Search offers <b>Open Device Mapping Editor</b> instead. Search stays open.</li>"
                + "<li>With nothing found, Search says what it looked for and where. It offers \"Did you mean …?\" for a likely typing mistake.<ul>"
                + "<li>One-click fixes follow, such as <b>Search all profiles</b> or <b>Clear filters</b>.</li>"
                + "</ul></li>"
                + "<li>Search reads your profiles in the background. Meanwhile the line under the box says <b>Indexing N of M profiles…</b>.<ul>"
                + "<li>The results found so far are shown.</li>"
                + "<li>A profile it can't read is listed with the reason. The others are still searched.</li>"
                + "</ul></li>"
                + "<li>Changes you make, saved or not, show up in the results.</li>"
                + "<li>Search shows no problem marks. Health does: see <a href=\"topic:tools-health\">Find problems with Health</a>.</li>"
                + "</ul>",
            related: ["tools-search", "tools-search-fix", "tools-health"]
        },
        {
            id: "tools-search-fix",
            section: "Search",
            title: "Fix a binding from Search",
            body: "<p>Remove a binding, or send it to another vJoy output, right from a Search result. This works even when the device isn't plugged in.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the result in Search, or select it and use the pane on the right.</li>"
                + "<li>To delete it, choose <b>Remove binding…</b>. A box names the binding and asks: <b>Remove</b> or <b>Cancel</b>.</li>"
                + "<li>To send it somewhere else, choose <b>Change target…</b>. Pick the vJoy device and input, then confirm.</li>"
                + "<li>Save the profile to keep the change.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>For a device that isn't plugged in, search its name or its output, then use the same two choices.</li>"
                + "<li><b>Change target…</b> is there for <b>Map to vJoy</b> actions only. Its lists show only outputs that can be sent.</li>"
                + "<li><b>Undo</b> (<b>Ctrl+Z</b>) in the Search window takes back your Search changes, until you save or close the profile.</li>"
                + "<li>A fix marks the profile as changed. Search and Health update at once.</li>"
                + "<li>While the profile runs, a box says the binding can't be changed. Choose <b>Stop</b> first.</li>"
                + "<li><b>Open</b> on a device that isn't plugged in can't show its page. A message says so and points to these two choices.</li>"
                + "<li>Plug the device in to edit its bindings on its own page.</li>"
                + "<li>To fix many problems at once, use Health. See <a href=\"topic:tools-health\">Find problems with Health</a>.</li>"
                + "</ul>",
            related: ["tools-search", "tools-search-results", "tools-health"]
        },
        {
            id: "tools-health",
            section: "Health",
            title: "Find problems with Health",
            body: "<p><b>Health</b> lists the bindings that have a problem, such as an output that isn't there. It says why, and lets you fix them, one or many at a time.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Health</b> on the toolbar, after Search <a href=\"show:toolbar/Health\">Show me ›</a>, or choose <b>Tools › Mapping › Health…</b> <a href=\"show:menu/Tools/Mapping/Health…\">Show me ›</a>. Health opens in a window of its own.</li>"
                + "<li>In the sidebar, tick the checks you want to see.</li>"
                + "<li>Click a line. The <b>Why</b> panel on the right says what is wrong and what you can do.</li>"
                + "<li>Right-click the line and choose a fix, such as <b>Change target…</b>.</li>"
                + "<li>Save the profile to keep the change.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<table><tr><th>Check</th><th>What it means</th></tr>"
                + "<tr><td><b>Binding output not found</b></td><td>The output isn't there: the device is missing or off, or doesn't have that button or axis.</td></tr>"
                + "<tr><td><b>Used twice</b></td><td>Two or more inputs send to the same output in the same mode of the same profile.</td></tr>"
                + "<tr><td><b>No bindings</b></td><td>Nothing is bound to the input in that mode.</td></tr>"
                + "<tr><td><b>Not plugged in</b></td><td>That device isn't connected now.</td></tr>"
                + "</table>"
                + "<ul>"
                + "<li>The toolbar button shows, in red, how many bindings in the open profile have an output that isn't found. With none, it is gray with no number.</li>"
                + "<li><b>Look in</b>: <b>This profile only</b> (the default) or <b>All profiles</b>. Each check shows its count.</li>"
                + "<li>Lines are grouped by profile, then device, with <b>Input</b>, <b>Mode</b> and <b>Action</b> columns, as in Search.</li>"
                + "<li>A ⚠ in the action marks the problem. Point at it to see the reason. A device that isn't connected shows <b>Not plugged in</b>.</li>"
                + "<li><b>Why</b>: the reason, and what you can do, with links such as <b>Tools › Drivers</b> <a href=\"open:tools.drivers\">Open ›</a>.</li>"
                + "<li>The right-click menu: <b>Open</b>, <b>Change target…</b>, <b>Remove binding…</b> and <b>Copy as text</b>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>To remove several bindings together, pick them with <b>Ctrl+click</b> or <b>Shift+click</b>, then right-click and choose <b>Remove binding…</b>. <b>Change target…</b> works on one line at a time.</li>"
                + "<li><b>Undo</b> (<b>Ctrl+Z</b>) takes the whole change back, until you save or close the profile.</li>"
                + "<li>While the profile runs, a box says the binding can't be changed. Choose <b>Stop</b> first.</li>"
                + "<li>A fix updates Health and the toolbar count at once.</li>"
                + "<li>The Device Bindings page keeps its own red ⚠ and its Find tick <b>Binding output not found</b>.</li>"
                + "<li>For one binding, you can also fix it from Search. See <a href=\"topic:tools-search-fix\">Fix a binding from Search</a>.</li>"
                + "</ul>",
            related: ["tools-search-fix", "tools-search", "tools-drivers", "getting-started-nothing-reaches-vjoy"]
        },
        {
            id: "tools-screen-saver-mode",
            section: "Screen Saver Mode",
            title: "Let the screen rest with Screen Saver Mode",
            body: "<p>Some devices, such as some throttles, flight panels and microphones, report to Windows many times a second even when nobody touches them. Windows then never starts its screen saver or turns the displays off, which risks burn-in on an OLED monitor. <b>Screen Saver Mode</b> keeps its own idle time from your keyboard and mouse only, and acts on it.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Tools › Screen Saver Mode…</b> <a href=\"open:tools.screenSaverMode\">Open ›</a>.</li>"
                + "<li>Turn on <b>Screen Saver Mode</b>. It is off until you turn it on, and the program remembers your choice.</li>"
                + "<li>On the <b>Wake PC</b> tab, choose the keyboards and mice that count. See <a href=\"topic:tools-screen-saver-wake-pc\">Choose the keyboards and mice that wake the PC</a>.</li>"
                + "<li>On the <b>Settings</b> tab, turn off the timer you don't want.</li>"
                + "<li>Type a timer's wait, or leave it empty to use Windows' own time.</li>"
                + "<li>To try it, press <b>Test now</b>, to the right of the <b>Screen Saver Mode</b> switch. It is grayed until the mode is on.<ul>"
                + "<li>After a 5-second countdown, shown as <b>Cancel test (N)</b>, it switches off the devices set to <b>Automatic</b>, then turns the displays off and keeps them off. The timers' waits and holds don't apply.</li>"
                + "<li>During the countdown, <b>Cancel test (N)</b>, a key press, a mouse click or the mouse wheel stops the test. Moving the mouse doesn't.</li>"
                + "<li>Afterwards, your first key press or mouse movement turns the displays on again and switches the devices back on.</li>"
                + "</ul></li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Screen saver</b>: starts the screen saver chosen in Windows when your idle time reaches its wait.</li>"
                + "<li><b>Power off displays</b>: turns every display off when your idle time reaches its wait, and keeps them off.</li>"
                + "<li>Both timers are on at first. Each acts once when your idle time reaches its wait.</li>"
                + "<li>An empty wait uses Windows' time: the screen saver wait, or the power plan's time to turn off the display.<ul>"
                + "<li>Windows' times are read again each time the countdown starts, so the program picks up any change you make in Windows.</li>"
                + "<li>For example, set the screen saver after 5 minutes and the displays off after 15.</li>"
                + "</ul></li>"
                + "<li><b>Hold off during full-screen programs</b> (on at first): nothing happens while a full-screen game or a presentation is in front.</li>"
                + "<li>The status line, which shows your idle time beside Windows' idle time. See <a href=\"topic:tools-screen-saver-awake\">Find what keeps the PC awake</a>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>What counts as you: the keyboards and mice ticked on <b>Wake PC</b>, and keys and mouse movements other programs send.</li>"
                + "<li>What never counts: joysticks, gamepads, microphones, and the keys this program's own bindings send.</li>"
                + "<li>Any key or mouse movement that counts ends the screen saver or wakes the displays, and starts your idle time again.</li>"
                + "<li>If the power-off wait isn't longer than the screen saver's, the window warns that the screen saver won't show.</li>"
                + "<li>Nothing happens while a program asks Windows to keep the display on, as a playing video does. The status line says so.</li>"
                + "<li>Nothing happens while the PC is locked. Windows looks after a locked PC itself.</li>"
                + "<li>When a hold ends, the countdown starts again from that moment.</li>"
                + "<li>With no screen saver chosen in Windows, the <b>Screen saver</b> timer does nothing. <b>Power off displays</b> still works.</li>"
                + "<li>A timer whose Windows time is never, with no time typed, does nothing either.</li>"
                + "<li>Screen Saver Mode works only while Gremlin-Platforms is open, whether a profile runs or not, and also from the tray.</li>"
                + "<li>The tray icon's menu has <b>Screen Saver Mode</b> (the same switch) and <b>Turn displays off now</b>.<ul>"
                + "<li>After <b>Turn displays off now</b>, moving the mouse doesn't stop it until the displays are off, and for 2 seconds after.</li>"
                + "<li>A key press, a mouse click or the mouse wheel still stops it, or wakes the displays.</li>"
                + "</ul></li>"
                + "<li>If the keyboard and mouse can't be listened to, the window says so and nothing is done.</li>"
                + "<li>Changes to these settings aren't kept in History. They go to the trace's <b>State</b> block (see <a href=\"topic:tools-trace\">Follow your controls with Trace</a>).</li>"
                + "</ul>",
            related: ["tools-screen-saver-wake-pc", "tools-screen-saver-keep-off", "tools-screen-saver-awake", "tools-q-screen-stays-on", "tools-trace"]
        },
        {
            id: "tools-screen-saver-wake-pc",
            section: "Screen Saver Mode",
            title: "Choose the keyboards and mice that wake the PC",
            body: "<p>Some devices show up in Windows as a keyboard or mouse though you don't use them as one, such as a game controller with a mouse part. Their constant reports would keep your idle time at 0. On the <b>Wake PC</b> tab, you tick only the devices you really use.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>In <b>Tools › Screen Saver Mode…</b> <a href=\"open:tools.screenSaverMode\">Open ›</a>, open the <b>Wake PC</b> tab.</li>"
                + "<li>Press a key on your keyboard. Its row ticks itself.</li>"
                + "<li>Click a button on your mouse. Its row ticks itself.</li>"
                + "<li>Tick or untick any other row yourself.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The heading <b>Allow this device to wake the PC</b>, then one row per device, such as \"Steam Controller · mouse, keyboard\".</li>"
                + "<li>Each row says how it got its tick: <b>ticked when you pressed a key</b>, <b>ticked when you clicked</b>, <b>ticked by you</b> or <b>you unticked it</b>.</li>"
                + "<li><b>in use now</b>: the row lights up for about 2 seconds after its device sends a key, a click or mouse movement.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Every device starts unticked, including one you plug in later.</li>"
                + "<li>Moving the mouse or turning the wheel ticks nothing. Devices are noticed only while the tab is open.</li>"
                + "<li>A device that lights up while you touch nothing, such as a drifting game controller, is one to leave unticked.</li>"
                + "<li>Lighting up never changes a tick.</li>"
                + "<li>Your ticks are kept, also after a restart. A ticked device you unplug keeps its tick for when it comes back.</li>"
                + "<li>Input sent by programs, such as remote desktop, always counts. It comes with no device, so there is nothing to tick.</li>"
                + "<li>With nothing ticked, neither timer runs. The status line on <b>Settings</b> asks you to tick at least one keyboard or mouse.</li>"
                + "<li>Wake PC doesn't change the Devices list. The devices set to <b>Automatic</b> there are still switched off while the displays are off.</li>"
                + "</ul>",
            related: ["tools-screen-saver-mode", "tools-screen-saver-keep-off"]
        },
        {
            id: "tools-screen-saver-keep-off",
            section: "Screen Saver Mode",
            title: "Keep the displays off",
            body: "<p>The devices that never go quiet also make Windows switch the displays back on, a moment after they go off. Screen Saver Mode keeps them off in two ways: it turns them off again, and it can switch those devices off while the displays are off.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>In <b>Tools › Screen Saver Mode…</b> <a href=\"open:tools.screenSaverMode\">Open ›</a>, open the <b>Devices</b> tab and press <b>Refresh Devices</b>.</li>"
                + "<li>New devices start as <b>Automatic</b>: switched off while the displays are off. Set a device to <b>Manual</b> to leave it alone.</li>"
                + "<li>When Windows asks you to allow <b>Gremlin Device Helper</b>, choose Yes.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>After <b>Power off displays</b> acts, each time Windows turns the displays back on by itself, the program turns them off again.<ul>"
                + "<li>It does this at most once a second, until you press a key or move the mouse.</li>"
                + "<li>The status line says how many times it happened.</li>"
                + "</ul></li>"
                + "<li>When <b>Power off displays</b> acts, it first switches off each device set to <b>Automatic</b>.<ul>"
                + "<li>It waits until they are done, then turns the displays off, so the switching doesn't wake them.</li>"
                + "<li>Your first key or mouse movement switches the devices back on.</li>"
                + "</ul></li>"
                + "<li>The <b>Devices</b> tab, headed <b>Devices that never go quiet</b>: one row per device, with its reports a second, <b>Automatic</b> or <b>Manual</b>, and <b>Remove</b>.<ul>"
                + "<li>A device not found this time keeps its row and choice. It shows no rate, and reads, for example, \"Not found · last seen today 16:27\".</li>"
                + "<li>Below the list: when you last pressed <b>Refresh Devices</b>, such as \"Checked 16:27 · 4 found, 1 not found\".</li>"
                + "</ul></li>"
                + "<li><b>Wait for devices to switch off</b>, under the timers: the longest it waits for the devices, 1 to 60 seconds (10 at first).</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>If you never press <b>Refresh Devices</b>, nothing is switched off. Turning the displays off again still works.</li>"
                + "<li><b>Refresh Devices</b> adds new devices and updates the others. It never removes one. The list is kept, also after a restart.</li>"
                + "<li><b>Remove</b> takes a device off the list at once. If it is found again, it comes back as a new one.</li>"
                + "<li>A device keeps its row in any USB port. Two identical devices share one row and one choice.</li>"
                + "<li>Virtual devices (vJoy and this program's own Xbox pads) are never switched off. Their choice is locked.</li>"
                + "<li>Switching a device off needs administrator rights, so <b>Gremlin Device Helper</b>, a small separate program, does it.<ul>"
                + "<li>Windows asks you to allow it once each time the program starts. It closes with the program.</li>"
                + "<li>It only takes requests from this program, and only for the devices in the list.</li>"
                + "</ul></li>"
                + "<li>If you say no, or the helper can't run, the <b>Devices</b> tab says devices can't be disabled. Press <b>Try again</b> to be asked again.</li>"
                + "<li>Before each step, the program writes each device to a small record file, then checks with Windows and writes the result.</li>"
                + "<li>Only the devices the program switched off are switched on again. A device you switched off yourself is never touched.</li>"
                + "<li>If Windows needs a restart to switch a device off, the program switches it back on at once.</li>"
                + "<li>If the program closes or the PC restarts while devices are off, the program switches them on at its next start.</li>"
                + "<li>A device unplugged while switched off is switched on when you plug it in again.</li>"
                + "<li>OLED monitors still run their panel maintenance while they are off.</li>"
                + "</ul>",
            related: ["tools-screen-saver-mode", "tools-screen-saver-awake", "tools-screen-saver-wake-pc"]
        },
        {
            id: "tools-screen-saver-awake",
            section: "Screen Saver Mode",
            title: "Find what keeps the PC awake",
            body: "<p>Under <b>What keeps the PC awake</b>, Screen Saver Mode lists the devices, programs and system parts that keep Windows awake. The status table shows what Screen Saver Mode is doing.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open <b>Tools › Screen Saver Mode…</b> <a href=\"open:tools.screenSaverMode\">Open ›</a>.</li>"
                + "<li>On <b>Settings</b>, press <b>Refresh Programs</b> or <b>Refresh System</b>. For devices, press <b>Open Devices</b>, then <b>Refresh Devices</b>.</li>"
                + "<li>To test the whole sequence, press <b>Test now</b>. See <a href=\"topic:tools-screen-saver-mode\">Let the screen rest with Screen Saver Mode</a>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Devices</b>: the counts, such as \"4 automatic · 1 manual · 1 not found\", or \"No devices yet\". <b>Open Devices</b> opens the <b>Devices</b> tab.<ul>"
                + "<li><b>Refresh Devices</b>, on that tab, reads every device for about 4 seconds and adds the ones that never go quiet. See <a href=\"topic:tools-screen-saver-keep-off\">Keep the displays off</a>.</li>"
                + "</ul></li>"
                + "<li><b>Programs</b>: <b>Refresh Programs</b> lists the programs, drivers and services asking Windows to keep the display on.<ul>"
                + "<li>These hold Screen Saver Mode off until they stop.</li>"
                + "<li>One that also keeps the PC from sleeping says <b>also keeps the PC awake</b>.</li>"
                + "</ul></li>"
                + "<li><b>System</b>: <b>Refresh System</b> lists what keeps the PC from sleeping, without keeping the display on.</li>"
                + "<li><b>Ignore</b>, on each Programs and System row: on, Windows ignores that row's requests; off, it listens again.</li>"
                + "<li><b>Test now</b>: runs the real sequence after a 5-second countdown, shown as <b>Cancel test (N)</b>.</li>"
                + "</ul>"
                + "<table><tr><th>Status row</th><th>What it shows</th></tr>"
                + "<tr><td><b>Listener</b></td><td>Whether the program is listening to the keyboard and mouse.</td></tr>"
                + "<tr><td><b>Your idle time</b></td><td>The program's idle time, and <b>last reset by</b>: what last started it again.</td></tr>"
                + "<tr><td><b>Windows' idle time</b></td><td>Windows' own idle time. It stays near 0 while a device keeps Windows awake.</td></tr>"
                + "<tr><td><b>Screen saver</b></td><td>The screen saver timer.</td></tr>"
                + "<tr><td><b>Power off displays</b></td><td>The power-off timer. It reads \"switching devices off…\" while devices switch off.</td></tr>"
                + "<tr><td><b>Wake-ups</b></td><td>\"none this time\", or how often Windows turned the displays back on. From 3 times, a hint to look at Devices.</td></tr>"
                + "<tr><td><b>Hold</b></td><td>Why nothing happens now, such as a full-screen program in front.</td></tr>"
                + "<tr><td><b>Last time away</b></td><td>A summary of the last time the displays were off, such as \"Displays off 12 min 46 s · 1 wake-up\".</td></tr>"
                + "<tr><td><b>Devices back on</b></td><td>\"all back on\", or the device still switched off, with <b>Try again</b>.</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Refresh Devices</b> only reads the devices. None of them counts as you.</li>"
                + "<li>Windows gives the Programs and System lists only to administrators. Each press of their buttons asks for administrator rights.<ul>"
                + "<li>If you refuse, the section says so and nothing else happens.</li>"
                + "</ul></li>"
                + "<li>Each <b>Ignore</b> change asks for administrator rights. It is a Windows setting, so it stays while the program is closed.</li>"
                + "<li>A program is listed by its file name, such as RustDesk.exe.</li>"
                + "<li>A driver or service is listed by its full Windows name, marked (driver) or (service).<ul>"
                + "<li>For example, \"USB Audio 2.0 (USB\\VID_0DB0&amp;PID_CD0E…)\" for a sound device.</li>"
                + "<li>A line under it often says why, such as \"An audio stream is currently in use.\"</li>"
                + "</ul></li>"
                + "<li>During the test countdown, a key, a click or the mouse wheel cancels the test. Moving the mouse doesn't.</li>"
                + "<li><b>last reset by</b> names a device, with (keyboard) or (mouse), or input sent by a program. A jittery mouse shows up here.</li>"
                + "<li>Reporting a problem? On the Trace tab of <b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a>, tick <b>Screen Saver Mode</b> and turn <b>Tracing</b> on.<ul>"
                + "<li>Let it happen again, then send trace.log, or use <b>Save Diagnostics…</b>.</li>"
                + "</ul></li>"
                + "</ul>",
            related: ["tools-screen-saver-mode", "tools-screen-saver-keep-off", "tools-trace-rows", "tools-q-screen-stays-on"]
        },

        {
            id: "tools-live-log",
            section: "Live Log Reader",
            title: "Read the logs in the Live Log Reader",
            body: "<p>The Live Log Reader shows the program's logs, so you can see what it did and what went wrong. It has four tabs: <b>Config</b>, <b>Debug</b>, <b>Input Monitor</b> and <b>Trace</b>.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a>.</li>"
                + "<li>Choose a tab, and on <b>Debug</b> choose a log under <b>Log</b>.</li>"
                + "<li>Narrow the lines with <b>Show</b> and <b>Find</b>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Config</b>: which profiles, modules and settings files were read and saved, and when. Use it to check how a file loads.<ul>"
                + "<li>It starts empty at every start. <b>Copy All</b> copies it; <b>Clear Log</b> empties it after asking.</li>"
                + "</ul></li>"
                + "<li><b>Debug</b>: the diagnostic logs in the Logs folder.<ul>"
                + "<li><b>System</b> (system.log): errors, warnings and blocked outputs.</li>"
                + "<li><b>Scripts</b> (user.log) and <b>Events</b> (event.log).</li>"
                + "<li><b>Qt</b> (qt.log): messages from the program's window toolkit, each with the time.</li>"
                + "<li><b>All logs</b>: every file together in time order, each line tagged with its log.</li>"
                + "</ul></li>"
                + "<li><b>Show</b>: the lowest level shown. <b>Find</b>: only lines with that text, with a line saying \"N found\" or \"Nothing matches\".</li>"
                + "<li><b>Load Whole File</b>: a large file shows only its last 512 KB at first; this reads all of it.</li>"
                + "<li><b>Clear Log</b>: empties the shown file after asking. Only the red <b>Clear Log</b> in the question clears it.</li>"
                + "<li><b>Diagnostic logs</b> <a href=\"show:option/Diagnostic logs\">Show me ›</a>, at the bottom of the tab: what gets written. It is the same setting as in Options.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Warnings and errors are in color.</li>"
                + "<li><b>Show</b> only filters what is in the file. A level the program isn't writing has no lines to show.</li>"
                + "<li>Clearing a log can't be undone.</li>"
                + "<li>With <b>Log When Not Responding</b> <a href=\"show:option/Log When Not Responding\">Show me ›</a> on, system.log says when the program stops responding for 5 seconds.<ul>"
                + "<li>It says where the program was stuck, and when it responds again.</li>"
                + "<li>It also watches the input thread, which handles your controls, and writes \"Input thread not responding\" when that one stops.</li>"
                + "<li>The two are checked apart, because your controls can keep working while the window is frozen.</li>"
                + "</ul></li>"
                + "<li>qt.log moves to qt.log.1 at start-up once it is over 1 MB. It grows at most 5 MB a session.</li>"
                + "</ul>",
            related: ["tools-live", "tools-input-monitor", "tools-trace", "tools-red-debug-mode", "getting-started-save-diagnostics"]
        },
        {
            id: "tools-live",
            section: "Live Log Reader",
            title: "Watch every log line with Live",
            body: "<p><b>Live</b>, the red button on the Debug tab, shows every line the program logs as it happens, at full detail. The files keep the <b>Diagnostic logs</b> level.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>In <b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a>, open the <b>Debug</b> tab.</li>"
                + "<li>Tick <b>Start empty</b> if you want the view cleared when Live starts.</li>"
                + "<li>Choose <b>Live</b>. A <i>Live started</i> line is added, and new lines are tagged [System], [Scripts] or [Events].</li>"
                + "<li>To see them together, choose <b>All logs</b> under <b>Log</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Show</b> and <b>Find</b> work as always, also while Live runs.</li>"
                + "<li><b>Clear View</b> empties the view, never a file. <b>Save Feed…</b> saves the view to a text file.</li>"
                + "<li>Stopping Live leaves the lines on screen. <b>Show Log File</b> goes back to the file.</li>"
                + "<li>Live stops when the Live Log Reader closes.</li>"
                + "</ul>",
            related: ["tools-live-log", "tools-red-debug-mode"]
        },
        {
            id: "tools-input-monitor",
            section: "Live Log Reader",
            title: "Watch inputs with the Input Monitor",
            body: "<p>The <b>Input Monitor</b> tab shows each input as it happens: the device and input, its value, the mode and the actions it ran.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Run the profile.</li>"
                + "<li>In <b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a>, open the <b>Input Monitor</b> tab.</li>"
                + "<li>Choose <b>Monitor</b> and use your devices.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Map to vJoy and Map to Xbox say where they send the input.</li>"
                + "<li>An input with no actions shows <i>no bindings</i>. Untick <b>Inputs with no bindings</b> to hide those.</li>"
                + "<li>An axis shows about 10 values a second. Nothing is written to a file.</li>"
                + "<li>The Input Monitor stops when the Live Log Reader closes.</li>"
                + "</ul>",
            related: ["tools-live-log", "tools-viewers"]
        },
        {
            id: "tools-trace",
            section: "Live Log Reader",
            title: "Follow your controls with Trace",
            body: "<p>The <b>Trace</b> tab follows the controls you tick, step by step, from the stick to vJoy. Use it when a control stops working or acts oddly in a game: the trace shows where the input stopped.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open <b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a> and choose the <b>Trace</b> tab.</li>"
                + "<li>Tick the sticks to follow. Ticking a stick ticks all its controls; expand it to tick only some.</li>"
                + "<li>Tick any extra rows you need. See <a href=\"topic:tools-trace-rows\">The extra Trace rows</a>.</li>"
                + "<li>Turn <b>Tracing</b> on before you start the game. The switch is in the tab, and in <b>Debug › Tracing</b> <a href=\"show:menu/Debug/Tracing\">Show me ›</a>.</li>"
                + "<li>Play as usual. If a control misbehaves, look at the trace lines around that moment.</li>"
                + "<li>When everything works, turn <b>Tracing</b> off.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Each control shows where it goes in the open profile, such as \"→ vJoy 3 X\".</li>"
                + "<li>The trace lines. See <a href=\"topic:tools-trace-lines\">Read the trace lines</a>.</li>"
                + "<li><b>Find</b>, <b>Show</b> (<b>All</b> or <b>Warnings</b>) and <b>Points</b>: narrow the view.</li>"
                + "<li><b>Clear View</b>: empties the view, never the file. The tab keeps the last 5000 lines.</li>"
                + "<li><b>Options ▾</b>, at the right end of the tab bar, holds the trace options:<ul>"
                + "<li><b>Axis lines</b>: how many lines an axis writes a second, 0.1 to 50 (10 at first). Type a value, then press Enter.</li>"
                + "<li><b>Max size</b>: how big trace.log may grow, 1 to 1000 MB (5 MB at first).</li>"
                + "<li><b>Clear Trace File…</b>: deletes trace.log and its older copy after asking, and clears the view.</li>"
                + "</ul></li>"
                + "<li><b>Show Trace File</b>: opens trace.log.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>You can close the Live Log Reader: tracing keeps running, and the red frame shows it is on.</li>"
                + "<li>Keys on the keyboard aren't traced.</li>"
                + "<li>An axis always writes its last value when you let go of it. Lower <b>Axis lines</b> if the file fills too fast.</li>"
                + "<li>Tracing is off when the program starts, unless you tick <b>Keep tracing on after a restart</b>. Your ticks are kept.</li>"
                + "<li>The lines go to trace.log in the Logs folder. At its <b>Max size</b>, one older copy, trace.log.1, is kept.</li>"
                + "<li>When tracing turns on, and when part of the program's state changes, the trace writes a <b>State</b> block.<ul>"
                + "<li>It holds the profile, the ticks and the Screen Saver Mode settings. Save Diagnostics writes the same block.</li>"
                + "</ul></li>"
                + "<li>When tracing turns on, and at midnight, the trace writes a date line, such as \"--- 2026-11-23 ---\".</li>"
                + "<li><b>Save Diagnostics…</b> includes trace.log.</li>"
                + "<li>With tracing off, nothing is written and it costs nothing.</li>"
                + "</ul>",
            related: ["tools-trace-lines", "tools-trace-rows", "tools-trace-osc", "tools-input-monitor", "tools-hidhide", "tools-red-debug-mode", "getting-started-save-diagnostics", "osc-troubleshooting"]
        },
        {
            id: "tools-trace-lines",
            section: "Live Log Reader",
            title: "Read the trace lines",
            body: "<p>Each trace line has the time, the control, the <b>point</b> it was written at, and what happened there. Read the points in order to see where an input stopped.</p>"
                + "<h4>What you see</h4>"
                + "<table><tr><th>Point</th><th>What it says</th></tr>"
                + "<tr><td><b>RAW</b></td><td>The value as the program gets it from the stick's driver. No RAW line means the program never got the move.</td></tr>"
                + "<tr><td><b>WIRING</b></td><td>Whether the program uses the control, the mode, and the actions that ran, or \"no actions\".</td></tr>"
                + "<tr><td><b>OUTPUT</b></td><td>What was sent to vJoy, and whether it was written.</td></tr>"
                + "<tr><td><b>BLOCKED</b></td><td>Not sent: the vJoy output module doesn't use that output, or the vJoy device doesn't have it.</td></tr>"
                + "<tr><td><b>EVENT</b></td><td>Tracing on or off, Run and Stop, a device plugged in, unplugged or <b>changed layout</b>, and a mode change.</td></tr>"
                + "<tr><td><b>HIDHIDE</b></td><td>What the program asked HidHide and the answer, and changes made outside the program.</td></tr>"
                + "<tr><td><b>OUT OF STEP</b></td><td>The out-of-step check found a stick or a vJoy output that doesn't match.</td></tr>"
                + "<tr><td><b>OSC</b>, <b>WINDOW</b>, <b>TIMING</b></td><td>Lines from the extra rows. See <a href=\"topic:tools-trace-rows\">The extra Trace rows</a>.</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>With <b>Keep vJoy devices awake</b> on, each send to an idle vJoy device writes an OUTPUT line, such as \"vJoy 1 keep-alive reset (idle 60 s)\".</li>"
                + "<li>Map to Mouse writes one line per change, never one per pointer step, such as \"Mouse motion stopped\".</li>"
                + "<li>A device that changed layout shows its axes and buttons before and after.</li>"
                + "</ul>",
            related: ["tools-trace", "tools-trace-rows"]
        },
        {
            id: "tools-trace-rows",
            section: "Live Log Reader",
            title: "The extra Trace rows",
            body: "<p>Besides your sticks, the Trace tab has extra rows to tick. Each one follows another part of the program.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Out-of-step check</b>, on a stick: checks every second that the program gets that stick's moves.<ul>"
                + "<li>It reads the stick directly and compares with the last value the program got.</li>"
                + "<li>It also reads each vJoy axis back and compares with what the program last wrote.</li>"
                + "<li>A difference that lasts over a second is a warning, shown in yellow at the top. <b>Go to line</b> jumps to it.</li>"
                + "</ul></li>"
                + "<li><b>HidHide</b>: writes every HidHide request with its result, and checks HidHide every 5 seconds for outside changes.<ul>"
                + "<li>An outside change is, for example, <b>HidHide Enabled</b> turned off or a game taken off the list.</li>"
                + "<li>Each ticked stick is checked to be hidden. If it isn't, the trace says the game can see it.</li>"
                + "</ul></li>"
                + "<li><b>OSC</b>: follows OSC messages. See <a href=\"topic:tools-trace-osc\">Trace OSC messages</a>.</li>"
                + "<li><b>Screen Saver Mode</b>: the listener, the countdown, each hold and action, and each Refresh with Windows' answer.</li>"
                + "<li><b>Window</b>: the main window and its pages. Use it when the window goes blank, jumps screens or isn't where you left it.</li>"
                + "<li><b>Timing</b>: how long each stick event waits, how long its actions take, and how long until vJoy is written.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A stick you aren't touching is normal for the out-of-step check: it gets one quiet note, not a warning.</li>"
                + "<li>When the profile stops, vJoy is put back at rest, so a Stop never shows as out of step.</li>"
                + "<li>While HidHide's own window is open, the program can't read HidHide. The trace says so once.</li>"
                + "<li>Screen Saver Mode errors are written to the normal log too, even with tracing off.</li>"
                + "<li>When Windows turns the displays back on while they are kept off, the line names what woke them.<ul>"
                + "<li>It gives the last input Windows saw right before, its device and kind, and whether it counted.</li>"
                + "<li>It also gives the time since the program last wrote to vJoy or an Xbox pad.</li>"
                + "<li>Game controllers are listened to only while the displays are kept off, only to name them. They never count as input.</li>"
                + "</ul></li>"
                + "<li>The <b>Window</b> row writes:<ul>"
                + "<li>the window shown, hidden, minimized, maximized, restored or full screen;</li>"
                + "<li>moved or resized, in one line after it settles;</li>"
                + "<li>screens added, removed or changed;</li>"
                + "<li>the window hidden to the tray and shown again;</li>"
                + "<li>pages loaded and unloaded, and any that fail;</li>"
                + "<li>the displays off, on or dimmed, and the PC going to sleep and waking;</li>"
                + "<li>the start and end of a stall.</li>"
                + "</ul></li>"
                + "<li>Even with tracing off, the program keeps the last 200 window steps in memory, the <b>recent events</b>.<ul>"
                + "<li>They are written out by <b>Debug › Save Window State</b>, after a \"Not responding\" report and after a \"Window:\" warning.</li>"
                + "</ul></li>"
                + "<li><b>Debug › Save Window State</b> <a href=\"show:menu/Debug/Save Window State\">Show me ›</a> writes the window's state to the system log, changing nothing.<ul>"
                + "<li>It covers where the window is, which pages are loaded, the last display and sleep reports, and the recent events.</li>"
                + "<li>The same text goes into the Save Diagnostics zip.</li>"
                + "</ul></li>"
                + "<li><b>Timing</b> writes one TIMING line every 10 seconds, with typical and worst times and how busy the program was.</li>"
                + "<li>A stick event that waits over 50 ms writes one warning, with how long it waited and how many events were held.</li>"
                + "</ul>",
            related: ["tools-trace", "tools-trace-lines", "tools-trace-osc", "tools-hidhide", "tools-screen-saver-mode"]
        },
        {
            id: "tools-trace-osc",
            section: "Live Log Reader",
            title: "Trace OSC messages",
            body: "<p>The <b>OSC</b> row on the Trace tab follows OSC messages from the moment they arrive to what is sent back. It has five ticks, one per area; ticking <b>OSC</b> ticks all five.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Receive</b>: each message that arrives, with the sender, the address and its values.<ul>"
                + "<li>A sender not on <b>Allowed senders</b>, a broken packet or a wildcard address is BLOCKED, with the reason.</li>"
                + "<li>Also the port opening and closing, and what holds it when it can't open.</li>"
                + "</ul></li>"
                + "<li><b>Inputs</b>: which input an address reaches, such as \"/fader1 → OSC Axis 1 (axis)\", or that no input answers.<ul>"
                + "<li>Also the value before and after shaping, encoder ticks, and the event sent.</li>"
                + "<li>What the input's actions send shows as OUTPUT or BLOCKED lines, as for a ticked stick control.</li>"
                + "</ul></li>"
                + "<li><b>Output</b>: each message sent, with the target, address, values and what sent it.<ul>"
                + "<li>A refused send is BLOCKED with the reason, such as \"OSC output is Off\" or \"the profile isn't running\".</li>"
                + "</ul></li>"
                + "<li><b>Feedback</b>: each Feedback row sent, held back by the rate, refused or resent.</li>"
                + "<li><b>Setup and files</b>: OSC's file loaded or saved, settings put back to their defaults, Listen, Bulk capture, Run and Stop.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Each line's control reads \"OSC\" and the area, such as \"OSC Receive\".</li>"
                + "<li>OSC lines go only to the Trace tab and trace.log, never to Live.</li>"
                + "<li>A busy address writes at most <b>Axis lines</b> lines a second, and adds how many messages came between.</li>"
                + "<li>Expected refusals and drops, such as a sender not allowed, follow the same limit.</li>"
                + "<li>An error, such as a failed send, is written at most 10 times, then once more with \"(repeated…)\".</li>"
                + "<li>The counts start again when the profile runs or tracing turns on.</li>"
                + "</ul>",
            related: ["tools-trace", "tools-trace-rows", "osc-troubleshooting"]
        },
        {
            id: "tools-red-debug-mode",
            section: "Live Log Reader",
            title: "Red debug mode",
            body: "<p>While <b>Diagnostic logs</b> is <b>ALL</b>, Live runs or <b>Tracing</b> is on, every window has a red frame and a <b>DEBUG</b> badge at the top. It reminds you that the program is writing extra detail.</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Click the badge to open the Live Log Reader.</li>"
                + "<li>Device map exports and prints never include the frame.</li>"
                + "</ul>",
            related: ["tools-live", "tools-live-log", "tools-trace"]
        },

        // ---- Technical reference ----
        {
            id: "tools-tech-hidhide",
            section: "Technical reference",
            title: "How HidHide decides",
            body: "<p>Exact facts about the HidHide driver, for finding out why a program does or doesn't see a device.</p>"
                + "<table><tr><th>Item</th><th>What HidHide does</th></tr>"
                + "<tr><td>When it checks</td><td>Only when a program opens a device. A program that already has the device open keeps it after any change.</td></tr>"
                + "<tr><td><b>Allow list</b></td><td>Only the listed programs, and this program, can open hidden devices. Every other program is refused.</td></tr>"
                + "<tr><td><b>Block list</b></td><td>The listed programs are refused. Every program not on the list can open hidden devices.</td></tr>"
                + "<tr><td>Which program it judges</td><td>The program that opens the device. Windows' own system processes are never refused.</td></tr>"
                + "<tr><td>How a program is matched</td><td>By its full path: the same folder and file name. Capital letters are ignored. A copy in another folder is another program.</td></tr>"
                + "<tr><td>How a device is matched</td><td>By its Windows device path. Another USB port can give the stick a new path.</td></tr>"
                + "<tr><td>Commands</td><td>Read and set the program list, the hidden devices, <b>HidHide Enabled</b> and Allow or Block. There is no command to check running programs again.</td></tr>"
                + "<tr><td>Making it check again</td><td>Restart the program, use <b>Reset Devices…</b>, or unplug the stick and plug it back in.</td></tr>"
                + "<tr><td><b>Reset Devices…</b></td><td>Runs <code>pnputil /restart-device</code> on each ticked stick's USB device, in one step, so Windows asks at most once.</td></tr>"
                + "<tr><td>After a reset</td><td>A stick is back after about 2-3 seconds with the same Windows ids, so HidHide's hidden list still matches it.</td></tr>"
                + "<tr><td>Reset results</td><td>Code 3010 means Windows needs a restart for this device. A declined prompt (code 1223) touches nothing.</td></tr>"
                + "<tr><td>While a stick restarts</td><td>This program sees it unplugged and back. A running profile follows <b>Device change behavior</b> <a href=\"show:option/Device change behavior\">Show me ›</a> in Options.</td></tr>"
                + "<tr><td>HidHide's own window</td><td>While HidHide Configuration Client is open, other programs can't talk to HidHide.</td></tr>"
                + "<tr><td>A refused open</td><td>The program gets \"access denied (5)\". The Input Tester's <b>Logs</b> tab shows it: HidHide is working.</td></tr>"
                + "<tr><td>How the Input Tester matches</td><td>By Windows device path first, then Device ID, then VID, PID and name. Identical sticks are told apart.</td></tr>"
                + "</table>"
                + "<h4>What this means</h4>"
                + "<ul>"
                + "<li>Set HidHide up before you start the game. See <a href=\"topic:tools-hidhide-timing\">Start the game after a HidHide change</a>.</li>"
                + "<li>Another program that can see the stick may pass it on. Steam does this through Steam Input when it isn't blocked.</li>"
                + "<li>Whether a game gets the stick from Steam depends on that game's Steam Input setting. That's why the Input Tester has its Steam line.</li>"
                + "</ul>",
            related: ["tools-hidhide", "tools-hidhide-timing", "tools-hidhide-reset", "tools-input-tester", "tools-q-game-sees-both"]
        },

        {
            id: "tools-q-identical-sticks",
            section: "Common questions",
            title: "How do I tell two identical sticks apart?",
            body: "<p>Compare their Joystick ID and Device ID in <b>Tools › Device Setup › Device Information</b> <a href=\"show:menu/Tools/Device Setup/Device Information\">Show me ›</a>. See <a href=\"topic:tools-device-information\">Device Information</a>.</p>",
            related: ["tools-device-information"]
        },
        {
            id: "tools-q-game-sees-both",
            section: "Common questions",
            title: "Why does my game see my stick and vJoy?",
            body: "<p>Running the profile doesn't hide controllers. Hide the physical stick with HidHide: see <a href=\"topic:tools-hidhide\">Hide controllers from games with HidHide</a>.</p>"
                + "<p>If the stick is hidden and the game still sees it, check these:</p>"
                + "<ul>"
                + "<li>The game was started after the last HidHide change. See <a href=\"topic:tools-hidhide-timing\">Start the game after a HidHide change</a>.</li>"
                + "<li>The stick is ticked on the HidHide page, and <b>HidHide Enabled</b> is on.</li>"
                + "<li>The game's list entry is right. With <b>Allow list</b>, the game must <i>not</i> be on it; with <b>Block list</b>, it <i>must</i> be.</li>"
                + "<li>The list has the exact path the game runs from. A test build (PTU) is a different program.</li>"
                + "<li>The stick is in the USB port it was hidden in. Another port can give it a new path that isn't hidden.</li>"
                + "<li>Steam can pass a stick it sees on to a game. With <b>Block list</b>, add Steam to the list, or turn off Steam Input for the game.</li>"
                + "</ul>"
                + "<p>The Input Tester checks all of these at once: see <a href=\"topic:tools-input-tester\">Check what a game sees (Input Tester)</a>.</p>",
            related: ["tools-hidhide", "tools-input-tester", "tools-input-tester-rows", "tools-tech-hidhide"]
        },
        {
            id: "tools-q-older-version",
            section: "Common questions",
            title: "How do I get back an earlier version of a setting or binding?",
            body: "<p>Open <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a>, pick the change and restore it. See <a href=\"topic:tools-history-restore\">Restore an earlier version</a>.</p>",
            related: ["tools-history-restore", "tools-history"]
        },
        {
            id: "tools-q-undo-auto-mapping-tool",
            section: "Common questions",
            title: "How do I take back what the Auto Mapping Tool made?",
            body: "<p>Its actions aren't saved yet: load the profile again without saving. See <a href=\"topic:tools-auto-mapping-tool\">Create actions with the Auto Mapping Tool</a>.</p>",
            related: ["tools-auto-mapping-tool"]
        },
        {
            id: "tools-q-clear-history",
            section: "Common questions",
            title: "How do I delete everything in History?",
            body: "<p>Stop the profile, then choose <b>Clear History…</b> in <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a>. It can't be undone. See <a href=\"topic:tools-history-clear\">Clear History</a>.</p>",
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
        },
        {
            id: "tools-q-screen-stays-on",
            section: "Common questions",
            title: "Why does my screen never turn off or start the screen saver?",
            body: "<p>A device that never goes quiet, such as a throttle or a microphone, keeps Windows thinking someone is using the PC. A program asking Windows to keep the display on does the same.</p>"
                + "<p>Turn on <b>Screen Saver Mode</b> in <b>Tools › Screen Saver Mode…</b> <a href=\"open:tools.screenSaverMode\">Open ›</a>. To see what keeps the PC awake, see <a href=\"topic:tools-screen-saver-awake\">Find what keeps the PC awake</a>.</p>",
            related: ["tools-screen-saver-mode", "tools-screen-saver-awake"]
        }
    ]
}
