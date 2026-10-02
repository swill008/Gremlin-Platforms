// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.pragma library

function topics() {
    return [
        topic("Getting Started", "Overview",
            "<p>Gremlin-Platforms turns your physical controllers into the virtual devices a game reads. Every input follows one path:</p>"
            + "<p><b>Physical device → input module → actions (profile) → output module → vJoy or Xbox driver → game</b></p>"
            + "<ul>"
            + "<li><b>Input module.</b> One per physical device. It claims the buttons, axes, and hats Gremlin-Platforms may use. An input that is not claimed is ignored.</li>"
            + "<li><b>Actions.</b> Stored in the profile. They say what each claimed input does: send it to vJoy or Xbox, press keys, run a macro, change mode, and so on.</li>"
            + "<li><b>Output module.</b> One per vJoy device, plus one for the Xbox controller. It is the only part that talks to the driver.</li>"
            + "</ul>"
            + "<p>Actions can also press keys, move the mouse, or send to the Logical Device, a virtual device that lives inside the program and has actions of its own.</p>"),
        topic("Getting Started", "First setup",
            "<ol>"
            + "<li>Install <b>vJoy</b> and configure its devices. For an Xbox controller, install <b>ViGEmBus</b>. Neither driver ships with this program.</li>"
            + "<li>On <b>Home</b>, right-click each physical device and choose <b>Configure input module</b>. Press the controls you will use, or tick them, then <b>Save module</b>.</li>"
            + "<li>Right-click each vJoy device and choose <b>Configure output module</b>. Tick the outputs you will use, then <b>Save module</b>. The Xbox controller needs no setup.</li>"
            + "<li>Double-click a physical device to open <b>Configuration</b>. Use <b>Add Action</b> on an input, for example Map to vJoy, then <b>OK</b>.</li>"
            + "<li><b>File → Save Profile</b> (Ctrl+S).</li>"
            + "<li>Press <b>Toggle</b> to run the profile. Use the <b>vJoy Viewer</b> or <b>Xbox Viewer</b> to watch the result.</li>"
            + "</ol>"
            + "<p>Tools → Mapping → <b>Auto Mapper</b> can create the Map to vJoy actions for a whole device in one step.</p>"),
        topic("Getting Started", "Installing and updating",
            "<p>Each release on GitHub has two downloads:</p>"
            + "<ul>"
            + "<li><b>Gremlin-Platforms-R1-X.Y.Z-Setup.exe</b>, the installer. It installs for your Windows user only and needs no administrator rights. The suggested folder is %LOCALAPPDATA%\\Programs\\Gremlin-Platforms; you can choose another folder you can write to. It adds a Start menu entry, an optional desktop shortcut, and an uninstaller in Settings → Apps.</li>"
            + "<li><b>Gremlin-Platforms-R1-X.Y.Z.zip</b>, the portable copy. Unzip it anywhere outside Program Files and run gremlin_platforms.exe.</li>"
            + "</ul>"
            + "<p><b>Help → Check for Updates</b> asks GitHub for the latest release. When Options → Global → <b>Check for updates</b> is on (the default), it also checks when the program starts and only speaks up when there is a newer version.</p>"
            + "<p>An installed copy offers <b>Update now</b>: it downloads the installer, checks it against the SHA-256 checksum GitHub reports, closes the program the usual way (asking about unsaved changes), installs, and starts the new version. <b>Skip this version</b> stops the startup check from offering that version. A portable copy, or one run from source, only points you to the release page.</p>"
            + "<p>Updates and uninstalling never touch your profiles, modules or settings; they are kept in your Gremlin Platforms folder (see What is saved where).</p>"),
        topic("Getting Started", "Toggle and status",
            "<p><b>Toggle</b> on the toolbar runs or stops the loaded profile. While it is off you are only editing; nothing is sent to vJoy or Xbox. The button uses the accent color while the profile runs.</p>"
            + "<p>The bottom bar shows <b>Status</b> (Active, Not Running, or Paused), the <b>Executing mode</b>, and what the last save wrote.</p>"
            + "<p>Toggle does not hide controllers from games; use <b>HiDHide</b> for that. What happens when a controller is plugged in or removed while running is set by Options → Global → <b>Device change behavior</b> (Reload, Ignore, or Disable).</p>"),
        topic("Getting Started", "Profiles",
            "<p>A profile holds the modes, the actions on every input, the profile settings, and the list of scripts.</p>"
            + "<ul>"
            + "<li><b>File → New Profile</b> (Ctrl+N), <b>Load Profile</b> (Ctrl+O), <b>Recent</b>, <b>Save Profile</b> (Ctrl+S), <b>Save Profile As</b>.</li>"
            + "<li>Closing the program or loading another profile asks first when there are unsaved changes.</li>"
            + "<li>Options → Profile → <b>Enable auto loading</b> loads a profile when a chosen program starts.</li>"
            + "</ul>"),
        topic("Getting Started", "What is saved where",
            "<p>Three separate stores. Saving one does not save the others, except where noted.</p>"
            + "<ul>"
            + "<li><b>Profile</b> (File → Save Profile): modes, actions, profile settings, scripts.</li>"
            + "<li><b>Module file</b>, one per device: claims, friendly names, the device picture, the Button Map layout, the display look of its Configuration page or Output View, and its calibration. Configure input/output module, Button Map, Calibration, and the display editors write it. Saving an output module also saves the profile when the profile already has a file.</li>"
            + "<li><b>Program settings</b>: Options, Home layout and card sizes, window sizes, HiDHide choices, and the Logical Device display look.</li>"
            + "</ul>"
            + "<p>After every save the bottom bar names the file that was written.</p>"),

        topic("Devices and Modules", "Home",
            "<p>Home shows one card per device: your physical devices, each vJoy device, and the Xbox controller.</p>"
            + "<ul>"
            + "<li><b>Double-click</b> a card to open its Configuration page (or <b>Output View</b> for an output).</li>"
            + "<li><b>Right-click</b> a card for: Open Configuration, Button Map, Configure input/output module, Auto Mapper, the viewer, Calibration, Device Information, Assign hardware…, stacking, Reset size, Hide device, Clear module settings, and Delete Device.</li>"
            + "<li><b>Shift-click</b> cards, then <b>Stack selected cards</b>, to group them.</li>"
            + "<li>Each card's <b>last:</b> line shows the latest input it passed or output it sent.</li>"
            + "<li><b>Compact view</b> and <b>Split</b> (None, Vertical, Horizontal) change the layout; View → <b>Home layout</b> chooses Single list, Side by side, or Stacked. Right-click empty space for <b>Unhide all devices</b> and <b>Reset all card sizes</b>.</li>"
            + "</ul>"),
        topic("Devices and Modules", "Input modules",
            "<p>An input module decides which controls of a physical device exist for Gremlin-Platforms. Only <b>claimed</b> controls reach your actions, the viewers, and the Auto Mapper.</p>"
            + "<p>Open it from the card menu or Tools → Device setup → <b>Configure input module</b>. Press a control on the device to claim it, or tick it; untick to release it. Give a control a <b>Friendly name</b> if you like. <b>Save module</b> writes the module file; <b>Cancel</b> discards.</p>"
            + "<p><b>Keyboard</b> is an input module too. Key bindings only fire for keys it claims. Until you save a choice, every key is claimed. Typing in Windows and games is never affected.</p>"
            + "<p>Calibration for a stick is stored in its input module (see Calibration).</p>"),
        topic("Devices and Modules", "vJoy output modules",
            "<p>Each vJoy device has an output module. It is the firewall in front of the vJoy driver: only outputs it <b>claims</b> are sent.</p>"
            + "<p>Open it from the card menu or Tools → Device setup → <b>Configure output module</b>. Tick the axes, buttons, and hats you will use, then <b>Save module</b>. The vJoy driver sets the maximum; the output module sets what Gremlin-Platforms may use.</p>"
            + "<p>A wire to an output that is not claimed sends nothing. It is kept, and shown as <b>(not claimed)</b> on the Configuration page, Button Map chips, the viewers, and in Map to vJoy, and the log notes it once. Claim the output to make it work.</p>"),
        topic("Devices and Modules", "Xbox output module",
            "<p>The Xbox controller (<b>Xbox 360 Controller</b>, pad 1) is a virtual Xbox 360 pad provided by the <b>ViGEmBus</b> driver. Its output module passes every control straight to the driver; there is nothing to claim.</p>"
            + "<p>Send to it with the <b>Map to Xbox</b> action. Its page (double-click the card) shows whether ViGEmBus is ready and which inputs drive each control. The <b>Xbox Viewer</b> shows the live pad. The pad appears when a Map to Xbox action first sends while the profile runs, and is removed when Toggle is turned off.</p>"),
        topic("Devices and Modules", "Module files and Device Pack",
            "<p>Each device has its own module file, found by the device first and then by its name. In Configure input/output module, <b>Module file</b> shows the current file and offers <b>Import from</b> (copy another file into this device's file), <b>Browse for File</b>, <b>Open configuration folder</b>, and <b>Delete file</b>. <b>Import image…</b> sets the device picture.</p>"
            + "<p>Tools → Device setup → <b>Device Pack</b> shares a device setup. <b>Export</b> saves a device's module file and pictures to a zip. <b>Import</b> loads a zip onto a device you choose under <b>Put this pack on</b>.</p>"),
        topic("Devices and Modules", "Hidden devices",
            "<p>Hiding a card only removes it from Home. It does not hide the device from Windows or games; use HiDHide for that.</p>"
            + "<p>Hide a card with its <b>×</b> or <b>Hide device</b> in its menu. View → <b>Hidden devices…</b> lists hidden cards with <b>Unhide</b> and <b>Unhide all</b>.</p>"),

        topic("Configuration", "Adding actions",
            "<p>The Configuration page lists the claimed inputs of one device and the actions on each. Open it by double-clicking a card, or View → <b>Configuration</b>. The arrows beside the title step to the previous or next device.</p>"
            + "<ul>"
            + "<li><b>Add Action</b> on an input opens the action editor beside it. Build the action and press <b>OK</b>. <b>Close pane after OK</b> closes the editor when OK succeeds.</li>"
            + "<li><b>Delete</b> removes an action. Leaving an input with unsaved editor changes asks first.</li>"
            + "<li>Actions belong to the mode shown in <b>Configuring mode</b> on the toolbar.</li>"
            + "<li><b>Move empty to Unmapped</b> lists inputs with no actions under an Unmapped heading.</li>"
            + "<li>OK keeps the action in the profile; File → <b>Save Profile</b> writes it to disk.</li>"
            + "</ul>"
            + "<p>An output device opens its <b>Output View</b> instead: a live view of what its output module sends, labelled “View only — driven by input module mappings.”</p>"),
        topic("Configuration", "Display options",
            "<p>Display options change how a Configuration page or Output View looks, not what it does. The look is saved in that device's module file.</p>"
            + "<p><b>Show Editor</b> opens the panel. Changes show at once and are kept only with <b>Save View Settings</b>. <b>Reset View to Default</b> (red) restores the built-in look; <b>Copy View from…</b> copies another device's look. Both still need Save View Settings. Closing the panel with unsaved changes asks first.</p>"
            + "<p>Sections: <b>Screen</b> (background color or image), <b>Shown</b> (child rows, live bars, LED dots, summary), <b>List</b> and <b>Group</b> (spacing and group cards), <b>Parent row</b> and <b>Child row</b> (row size, padding, colors), <b>Text</b>, <b>Selection</b>, and <b>Editor</b> (the action editor beside a row). Use <b>Open all</b> / <b>Close all</b> to expand them.</p>"),

        topic("Actions", "Choosing an action",
            "<p><b>Add Action</b> lists the actions that suit the input type (axis, button, hat, or key). Container actions hold other actions; add the container first, then the actions inside it.</p>"
            + "<p>Options → Action → <b>Action list</b> sets the order of that list and can hide actions you never use.</p>"),
        topic("Actions", "Map to vJoy",
            "<p>Sends the input to a vJoy axis, button, or hat. Pick the vJoy device (by output module name) and the output.</p>"
            + "<ul><li>Axis: <b>Absolute</b>, or <b>Relative</b> with <b>Scaling</b> (the axis moves while the input is held off-center).</li>"
            + "<li>Button: <b>Invert activation</b>.</li>"
            + "<li>Only outputs claimed by the vJoy output module are sent. An unclaimed output shows <b>Output not claimed</b>.</li></ul>"),
        topic("Actions", "Map to Xbox",
            "<p>Sends the input to the virtual Xbox 360 controller (needs <b>ViGEmBus</b>). Every control is available; there is nothing to claim.</p>"
            + "<ul><li><b>Xbox</b>: the Xbox output module (Xbox 360 Controller).</li>"
            + "<li><b>Target</b>: any of the 22 controls — sticks, triggers, buttons, D-pad.</li>"
            + "<li>Trigger: <b>Full axis</b> (−1 → 0%, +1 → 100%) or <b>Upper half</b> (center → 0%).</li>"
            + "<li>Button: <b>Invert</b>.</li></ul>"),
        topic("Actions", "Map to Logical Device",
            "<p>Sends the input to a control on the Logical Device. Pick the logical control of the same type. Axis: <b>Absolute</b> or <b>Relative</b> with <b>Scaling</b>. Button: <b>Invert activation</b>. The Logical Device page's <b>Assign hardware</b> creates these actions for you.</p>"),
        topic("Actions", "Map to Keyboard",
            "<p>Holds the recorded keys while the input is held and releases them when it is released. Use <b>Record Keys</b> to set the <b>Key Combination</b>; modifiers are pressed first.</p>"),
        topic("Actions", "Map to Mouse",
            "<p><b>Mode</b>: <b>Button</b> clicks a recorded mouse button (Wheel Up/Down included, sent once per press). <b>Motion</b> moves the pointer: <b>Minimum speed</b>, <b>Maximum speed</b>, <b>Time to maximum speed</b>, and <b>Direction</b> for a button; <b>Control motion of</b> X Axis or Y Axis for an axis.</p>"),
        topic("Actions", "Macro",
            "<p>Plays a list of steps: Joystick, Keyboard, Logical Device, Mouse Button, Mouse Motion, Pause, and vJoy. Add them with <b>Add Action</b>, or <b>Record Inputs</b> (choose Keyboard, Mouse, Axis, Button, Hat, and Timings, then Start/Stop Recording).</p>"
            + "<ul><li><b>Repeat Mode</b>: Single, Count, Toggle, or Hold, with a delay between repeats.</li>"
            + "<li><b>Exclusive</b> waits for running macros, then blocks others; <b>Pre-Emptive</b> pauses them instead.</li></ul>"),
        topic("Actions", "Response Curve",
            "<p>Reshapes an axis before the actions after it. Choose <b>Piecewise Linear</b>, <b>Cubic Spline</b>, or <b>Cubic Bezier Spline</b>, drag the points or type <b>X</b>/<b>Y</b>, and set the <b>Deadzone</b>. <b>Invert Curve</b> flips it; <b>Symmetric</b> mirrors edits around the center.</p>"),
        topic("Actions", "Split Axis",
            "<p>Splits one axis at <b>Split axis at</b> into a lower/left part and an upper/right part, each with its own action list. Each part is rescaled to the full range.</p>"),
        topic("Actions", "Merge Axis",
            "<p>Combines two axes into one value for the actions in its <b>Actions</b> list. Pick or create a <b>Merge axis instance</b>, the <b>First axis</b> and <b>Second axis</b>, and the <b>Merge operation</b>: Average, Minimum, Maximum, Sum, Bidirectional, or Prefercenter.</p>"),
        topic("Actions", "Dual Axis Deadzone",
            "<p>Applies one deadzone to a pair of axes, such as a stick's X and Y: a circular <b>Inner</b> deadzone and a square <b>Outer</b> limit. Pick or create a <b>Deadzone instance</b> and the two axes; each axis has its own action list for the result.</p>"),
        topic("Actions", "Axis Delta",
            "<p>Turns axis movement into button presses. Each time the axis moves by <b>Change threshold</b>, it pulses the actions under <b>Positive change</b> or <b>Negative change</b>.</p>"),
        topic("Actions", "Condition",
            "<p>Runs one action list when its conditions are true and another when false. Choose <b>Any</b> or <b>All</b>, then <b>Add Condition</b>: Joystick, Keyboard, Current Input, vJoy, or Logical Device state.</p>"),
        topic("Actions", "Chain",
            "<p>Each press runs the next <b>Chain Sequence</b> in turn. After <b>Timeout (sec)</b> without a press it starts again at the first.</p>"),
        topic("Actions", "Double Tap",
            "<p>Separate actions for a single tap and a double tap within <b>Double-tap threshold (sec)</b>. <b>exclusive</b> waits to see if a second tap comes; <b>combined</b> runs the single-tap actions on every press.</p>"),
        topic("Actions", "Tempo",
            "<p>Separate actions for a <b>Short press</b> and a <b>Long press</b> (longer than <b>Long-press threshold (sec)</b>). <b>Activate on</b> press or release.</p>"),
        topic("Actions", "Smart Toggle",
            "<p>A quick press (released within <b>Toggle delay</b>) latches its actions on until the next press; a longer hold acts only while held.</p>"),
        topic("Actions", "Hat as Buttons",
            "<p>Gives each hat direction its own action list. <b>Button mode</b>: <b>4 way</b> or <b>8 way</b>.</p>"),
        topic("Actions", "Change Mode",
            "<p>Changes the running mode: <b>Switch</b> to a mode, <b>Previous</b> mode, <b>Unwind</b> one step, <b>Cycle</b> through a list, or <b>Temporary</b> (only while held).</p>"),
        topic("Actions", "Load Profile",
            "<p>Loads another profile file when the input fires. Set <b>Profile filename</b> or use <b>Select File</b>.</p>"),
        topic("Actions", "Pause and Resume",
            "<p><b>Pause</b>, <b>Resume</b>, or <b>Toggle</b> the processing of all actions.</p>"),
        topic("Actions", "Play Sound",
            "<p>Plays a WAV, MP3, or OGG file at the chosen <b>Volume</b>. Options → Action → Play-Sound sets what happens when sounds overlap.</p>"),
        topic("Actions", "Text to Speech",
            "<p>Speaks the text you type. Choose <b>Interrupt</b>, <b>Queue Front</b>, or <b>Queue Back</b>, and set <b>Volume</b>, <b>Rate</b>, and <b>Pitch</b>. The voice is set in Options → Action → Text-To-Speech.</p>"),
        topic("Actions", "Run Command",
            "<p>Starts a program: <b>Executable</b> plus <b>Arguments</b> (split on spaces; quote values that contain spaces). It runs with your own permissions.</p>"),
        topic("Actions", "Description",
            "<p>A note on the input. It does nothing when the input fires.</p>"),
        topic("Actions", "Reference",
            "<p>Reuses an existing action of the same input type. Pick it, then either share it (both inputs use the same action) or duplicate it (an independent copy).</p>"),

        topic("Logical Device", "Logical Device",
            "<p>The Logical Device is a virtual device inside the program. Its buttons, axes, and hats are fed by physical inputs (<b>Assign hardware</b> or Map to Logical Device) and have actions of their own. Use it to combine several physical controls before sending them on.</p>"
            + "<p>Open it with <b>Logical Device</b> on the toolbar or Tools → Mapping → Logical Device. Controls are identified by type and number (Button 1, Axis 1, Hat 1). <b>Rename</b> adds your own name; <b>Hide system name</b> shows only yours; <b>Clear name</b> removes it.</p>"
            + "<p>Editing is locked while the profile runs (“Running”).</p>"),
        topic("Logical Device", "Controls, groups, and the menu",
            "<ul>"
            + "<li>Right-click empty space: <b>Add Button</b>, <b>Add Axis</b>, <b>Add Hat</b> (with a count up to 180), <b>New group</b>, the three <b>Order</b> commands, Undo/Redo, and <b>Display</b>.</li>"
            + "<li>Right-click a control: <b>Add Action</b>, <b>Assign hardware</b>, <b>Rename</b>, <b>Group as</b>, <b>Move to group</b>, <b>Delete</b>. Shift-click selects several.</li>"
            + "<li>Right-click a group: move it up or down, rename, or delete it (its controls go to Ungrouped). Click a group header to fold it.</li>"
            + "<li>Drag a control by its grey handle onto another control (top half = before, bottom half = after) or onto a group header. Drag a header to move the group.</li>"
            + "<li><b>Find</b> filters by name, type, Ungrouped, <b>No hardware writer</b>, or <b>No actions in this mode</b>; <b>Clear</b> resets it.</li>"
            + "<li>Undo/Redo: Ctrl+Z and Ctrl+Y (or Ctrl+Shift+Z).</li>"
            + "</ul>"),
        topic("Logical Device", "Assign hardware and actions",
            "<p><b>Assign hardware</b> lists claimed physical controls of the same type (keyboard keys for a button; OSC too). Tick a control to add a Map to Logical Device action to it in the current mode; untick to remove that link. <b>Search</b> filters the list.</p>"
            + "<p>The control then shows <b>Written by</b> with the source. On that line an axis has Absolute/Relative and a scale; a button has <b>Invert</b>.</p>"
            + "<p><b>Add Action</b> opens the action editor beside the list, the same editor as on the Configuration page. Click an action row to edit it; right-click it to delete it.</p>"),
        topic("Logical Device", "Display",
            "<p><b>Show Editor</b> (or <b>Display</b> in the menu) opens the Logical Device display editor. Its sections — Shown, Handles, List, Group, Parent row, Action row, Text, Selection — change how the page looks. Changes are kept with <b>Save View Settings</b> (saved for this page, in the program settings); <b>Reset View to Default</b> restores the built-in look.</p>"),
        topic("Modes", "Modes",
            "<p>A mode is a set of actions. The same button can do different things in different modes. A mode can <b>inherit</b> from a parent: anything it does not map itself uses the parent's actions.</p>"
            + "<ul>"
            + "<li><b>Manage Modes</b> (toolbar, or Tools → Mapping): add, rename, and remove modes, and set <b>Inherits from</b>.</li>"
            + "<li><b>Configuring mode</b> on the toolbar picks the mode you edit and the mode Toggle starts in. The bottom bar shows the <b>Executing mode</b>.</li>"
            + "<li>The <b>Change Mode</b> action switches mode while the profile runs.</li>"
            + "<li>Modes are part of the profile; save the profile to keep them.</li>"
            + "</ul>"),
        topic("Tools", "Viewers",
            "<p>The viewers show live values; they change nothing. Open them from the toolbar, Tools → Viewers, or a card's menu.</p>"
            + "<ul>"
            + "<li><b>vJoy Viewer</b>: each physical device beside the vJoy device it drives. The physical side shows claimed inputs; the vJoy side shows what the vJoy output module sent (claimed outputs, while the profile runs).</li>"
            + "<li><b>Xbox Viewer</b>: the Xbox 360 Controller with every control, and which inputs drive it.</li>"
            + "</ul>"),
        topic("Tools", "Calibration",
            "<p>Sets the center and the ends of each axis so its full travel is used. It is stored in the device's input module and applied before any action sees the axis.</p>"
            + "<p>Tools → Device setup → <b>Calibration</b>, or a card's menu. Choose the input module. For each axis, move the stick and use <b>Calibrate center</b> and <b>Calibrate extrema</b>, or type the values. An axis shows <b>Not saved</b> until you press its save button. Leaving with unsaved axes asks first.</p>"),
        topic("Tools", "Device Information",
            "<p>Tools → Device setup → <b>Device Information</b> lists every device Windows reports: Name, Axes, Buttons, Hats, VID, PID, Joystick ID, and Device GUID. Use it to tell identical devices apart.</p>"),
        topic("Tools", "Auto Mapper",
            "<p>Creates Map to vJoy actions in one step: each claimed input of an input module is wired to the same number on a vJoy output module.</p>"
            + "<ol>"
            + "<li>Tools → Mapping → <b>Auto Mapper</b> (or a card's menu).</li>"
            + "<li>Tick the input modules and output modules. The first ticked input goes to the first ticked output, the second to the second, and so on.</li>"
            + "<li>Choose <b>Select Mode</b>, then <b>Create 1:1 mappings</b>.</li>"
            + "</ol>"
            + "<ul>"
            + "<li>Only outputs the output module claims are used. Skipped controls are listed with the reason (not claimed, or not on the vJoy device).</li>"
            + "<li><b>Also claim the matching outputs on the output module</b> (off by default) claims what the mappings need first.</li>"
            + "<li><b>Overwrite used inputs</b> replaces existing actions on those inputs; off keeps them.</li>"
            + "<li><b>Combine onto Selected Outputs</b> reuses the outputs when you tick more inputs than outputs.</li>"
            + "</ul>"),
        topic("Tools", "Swap Devices",
            "<p>Swaps every binding between two devices, for example after replacing a stick. Tools → Device setup → <b>Swap Devices</b>: choose <b>From profile device</b> and <b>To connected device</b>, then <b>Swap Bindings</b>. References inside actions and script variables are swapped too. Save the profile afterwards.</p>"),
        topic("Tools", "HiDHide",
            "<p>HiDHide hides physical controllers from games so they only see vJoy or Xbox. Gremlin-Platforms always sees them. The HiDHide driver is a separate install (<b>Get HiDHide</b>).</p>"
            + "<p>Tools → Device setup → <b>HiDHide</b>:</p>"
            + "<ul>"
            + "<li><b>Gremlin control</b> lets this program write HiDHide's settings. <b>HiDHide Enabled</b> turns hiding on. <b>Automatically Start</b> applies both each time the program starts.</li>"
            + "<li>Tick the devices to hide. <b>Gaming devices only</b> shortens the list. A hidden device is dimmed and marked HIDDEN.</li>"
            + "<li><b>Allow list</b>: only the listed programs see hidden devices. <b>Block list</b>: the listed programs do not. Add programs with <b>Add Program</b>.</li>"
            + "<li><b>Test HiDHide</b> opens the Windows Game Controllers panel. With Allow list on, a hidden device should be missing there. Reopen the panel after each change.</li>"
            + "</ul>"
            + "<p>All switches start off on a new install.</p>"),
        topic("Tools", "Live Log Reader",
            "<p>Debug → <b>Live Log Reader</b> follows the program's activity log (logs.txt): what was read and saved, and when. The system log (system.log) in the Logs folder records errors and blocked outputs.</p>"),

        topic("Button Map", "Overview",
            "<p>Button Map is a picture of one device with a chip on each control. While the profile runs, a press lights its chip, and wires show where the control goes (shown as <b>(not claimed)</b> when the output is not claimed). Chips are layout only: moving, renaming or deleting one never changes the actions in the profile.</p>"
            + "<p>Open it from a device card's right-click menu, the toolbar, or Tools → Mapping → <b>Button Map</b>, then pick the device from its File menu. Before you edit, the map is live: hover a chip to see which control it is, and drag with the left or middle button to pan.</p>"
            + "<p><b>File → Edit Mapping</b> starts editing. The pool beside the map lists the device's controls; drag a chip from it onto the photo, and filter it by name. <b>File → Save</b> (Ctrl+S) writes the layout to the device's module file; <b>File → Cancel</b> leaves without saving. Closing with unsaved edits asks first.</p>"
            + "<p>Everything below is about editing. <b>Help → Button Map guide</b> or <b>F1</b> in the Button Map window opens this section.</p>"),
        topic("Button Map", "File menu and export",
            "<ul>"
            + "<li><b>Edit Mapping</b>, <b>Save</b> (Ctrl+S), <b>Cancel</b>.</li>"
            + "<li><b>Reset layout</b> sends every chip, leader and hotspot back to the pool (it asks first). The mappings are not changed; save afterwards to make the empty layout the live map.</li>"
            + "<li><b>Fit to photo frame</b> shrinks an older, oversized layout to the photo.</li>"
            + "<li><b>Choose background…</b> uses another picture as the photo; <b>Clear image</b> goes back to the module's picture.</li>"
            + "<li><b>Export PDF…</b>, <b>Export PNG…</b>, <b>Export JPG…</b> save the whole page, whatever the zoom, on the window's background colour. Selection marks, handles, guides and the grid are left off, and so are hidden items. <b>Export size</b> picks 1×, 2× (the default) or 3× the size on screen; a PDF page keeps the on-screen size and gets the extra detail.</li>"
            + "<li><b>Export modes…</b> writes one page per mode, each chip showing what its control does in that mode (Action labels; if chips show names, the export shows actions). Tick the modes, choose PDF (one file, a page per mode), PNG or JPG (a file per mode, named after the file you choose plus the mode). Each page can carry its mode's name at the top.</li>"
            + "<li><b>Close</b>. The last row shows the device's module file.</li>"
            + "</ul>"
            + "<p>To copy a whole device setup, layout included, to another computer, use Tools → Device setup → <b>Device Pack</b>. Hidden items travel in the pack and stay hidden.</p>"),
        topic("Button Map", "View, zoom and grid",
            "<p>Scroll to zoom (75% to 600%). Drag with the middle button to pan. View → <b>Reset view (View 100%)</b> or Ctrl+0 returns to 100%.</p>"
            + "<p>View → <b>Grid</b>: <b>Show grid</b>, <b>Snap to grid</b>, <b>Snap to entities</b> (edges and middles of other items, with guide lines), and the grid <b>Size</b>. Hold <b>Alt</b> while dragging to skip snapping.</p>"
            + "<p>View → <b>Layers</b> and View → <b>Properties</b> show the two side panels (see Layers and Properties panel).</p>"),
        topic("Button Map", "The photo",
            "<p>The photo is the device picture under everything else. Photo → <b>Move photo</b> drags it (Esc leaves the tool); <b>Adjust photo…</b> sets its size, offset and rotation; <b>Reset photo</b> puts it back.</p>"
            + "<p>File → <b>Choose background…</b> uses another picture; <b>Clear image</b> returns to the module's picture. The photo has its own row at the bottom of the Layers panel, so it can be hidden or locked like any item.</p>"),
        topic("Button Map", "Chips",
            "<p>A chip shows a control's name (Button 10, Axis 1, Hat 1) or its friendly name. Drag one from the pool onto the photo; drag it again to move it.</p>"
            + "<p>Right-click a chip for:</p>"
            + "<ul>"
            + "<li><b>Rename</b> and <b>Delete chip</b> (back to the pool; Delete or Backspace does the same).</li>"
            + "<li><b>Chip style</b>: font size, chip size, Round or Square, Filled or Hollow, and <b>Highlight on press</b>.</li>"
            + "<li><b>Colours</b>: Fill colour…, Outline colour… and Text colour…, and <b>Pressed fill…</b>, <b>Pressed outline…</b> and <b>Pressed text…</b> used while the control is held.</li>"
            + "<li><b>Hotspot</b> and <b>Leader ends</b> (see Hotspots and leaders), <b>Arrange</b> (stacking, Lock, Hide).</li>"
            + "</ul>"
            + "<p>Ctrl+D duplicates the selection; Ctrl+C and Ctrl+V copy and paste it inside the editor.</p>"),
        topic("Button Map", "Action labels",
            "<p>Chips can show what each control does in the profile instead of its name, so the map reads as a binding sheet: <b>Gear up</b> or <b>Ctrl+G</b> beside the button, not Button 23. View → <b>Chip text</b> picks <b>Name</b>, <b>Action</b>, or <b>Name and action</b> (also in Editor options → Labels). Renaming a chip still edits its name.</p>"
            + "<p>The text comes from the control's actions in one mode. View → <b>Labels mode</b> picks the mode, or <b>Follow the program</b>: the running mode while the profile runs, otherwise the mode shown in the main window. A control with no actions in a mode shows its parent mode's, as the running profile does.</p>"
            + "<ul>"
            + "<li><b>Description</b>: its text. With Editor options → Labels → <b>Description first</b> on (the default), it stands for the whole binding.</li>"
            + "<li><b>Map to Keyboard</b>: the keys, such as Ctrl+G. <b>Map to vJoy</b> and <b>Map to Xbox</b>: the output, such as vJoy 1 B5. <b>Change Mode</b>: → and the target mode, or Cycle, Previous mode, Unwind mode. <b>Text to Speech</b>: what it says. Mouse, Macro, Load profile, Run command, Sound, Pause / resume and Logical Device show those words.</li>"
            + "<li>Actions inside Chain, Tempo, Double Tap, Condition and the like give their text; response curves and deadzones give none.</li>"
            + "</ul>"
            + "<p><b>Several actions</b> shows the first one's text, or all of them joined with +. <b>Unbound</b> sets what a chip shows when its control does nothing in that mode: its name, nothing, or a dash. Labels follow the profile as you edit it.</p>"),
        topic("Button Map", "Hotspots and leaders",
            "<p>Each chip has a <b>hotspot</b>, the dot on the photo marking the physical control, and a <b>leader</b> line between them. Drag the chip and the hotspot separately. A chip's <b>Hotspot</b> section sets the dot's size, shape, fill and colour.</p>"
            + "<p>Click a leader to select it. Drag a segment to bend it; that adds a curve point (a spine). Click a spine to select it; hold the right button on a spine for about half a second to delete it.</p>"
            + "<p>Right-click a leader for <b>Add leader</b> (another line from the same chip) and <b>Delete leader</b>. Its <b>Leader</b> section has <b>Leader colour…</b>, <b>Weight</b>, <b>Add straight spine</b>, <b>Add curved spine</b>, <b>Convert spine</b>, <b>This segment</b> or <b>All segments</b> (Curved or Straight), <b>Branch from this end</b>, <b>Clear all spines</b> and <b>Delete spine</b>. <b>Leader ends</b> detaches the chip end or the hotspot end, and reconnects it.</p>"
            + "<p>Spines show only while editing; the lines stay on the live map. In the Layers panel, open a chip to hide or lock its hotspot or one leader on its own.</p>"),
        topic("Button Map", "Groups and 5-way formats",
            "<p>Select two or more chips (Shift-click, or drag a box on empty space) and choose <b>Group selected</b> (Ctrl+G). A group moves as one. <b>Break group</b> (Ctrl+Shift+G) splits it. <b>Edit group</b> lets you move and style one member; <b>Done editing group</b> or Esc ends that.</p>"
            + "<p><b>Align members</b> arranges a group Left, Centre, Right or Free.</p>"
            + "<p>Right-click a five-chip hat group: <b>5-way</b> styles it as <b>Plus</b>, <b>Mini hat</b>, <b>Named card</b> or <b>Radial</b>; <b>Clear format</b> removes the style.</p>"
            + "<p>Grouping chips or text boxes together with a table packs them into the table (see Tables).</p>"),
        topic("Button Map", "Right-click menu",
            "<p>While editing, the menu shows only what applies to what you right-clicked: a chip, a group, a leader, a shape, a line, a picture, a text box, a table, several selected items, or empty canvas.</p>"
            + "<p>It opens small: the item's name with <b>Undo</b> and <b>Redo</b>, a few actions, then sections such as Chip style or Arrowheads. Click a section to open it; one is open at a time, and the menu reopens on the section you used last for that kind of item. Rows of values (sizes, widths, opacity) change straight away and leave the menu open; other actions close it.</p>"
            + "<p>Keys: Up and Down move, Enter acts, Right and Left open or close a section or step a row of values, Esc closes. Near a window edge the menu opens the other way, and it scrolls when it is taller than the window.</p>"),
        topic("Button Map", "Drawing shapes",
            "<p>Right-click empty canvas → <b>Draw</b> and pick a <b>Shape</b>: Rectangle, Rounded, Ellipse, Triangle, Diamond, Arrow or Double arrow. Drag on the photo to draw it; hold Shift to keep its proportions. The tool stays on for the next one until <b>Stop drawing</b> or Esc.</p>"
            + "<p>With chips selected, <b>Shape around selection</b> draws a shape around them that moves with them; its <b>Padding</b> sets the gap, and Arrange → <b>Detach from chips</b> frees it.</p>"
            + "<p>Right-click a shape for <b>Duplicate</b> and <b>Delete</b>, then sections: <b>Shape</b> (change the kind), <b>Fill and outline</b> (Filled or Hollow, Fill colour…, Outline colour…, Width, outline Solid, Dashed or Dotted, Opacity), <b>Rotate and flip</b> and <b>Arrange</b>.</p>"),
        topic("Button Map", "Lines and arrows",
            "<p>Draw → <b>Line</b> picks <b>Line</b> or <b>Arrow</b>. Drag from one end to the other; hold Shift to keep to 15° steps.</p>"
            + "<p>A selected line has a handle on each end; drag one to move that end (Shift for 15° steps). To turn a line, move its ends.</p>"
            + "<p>Its <b>Arrowheads</b> section sets the <b>Start</b> and <b>End</b> to None, Solid or Hollow; <b>Swap heads</b> turns them round. Its <b>Line</b> section has Colour…, Width, Outline (Solid, Dashed or Dotted) and Opacity, and <b>Flip</b> mirrors it.</p>"),
        topic("Button Map", "Rotate, flip and resize",
            "<p>Shapes and pictures can be turned. A selected one has a round handle above it: drag it to turn the item, with Shift for 15° steps. The <b>Rotate and flip</b> section has an <b>Angle</b> to type, <b>Turn to</b> 0°, 90°, 180° or 270°, <b>Rotate −15°</b> and <b>Rotate +15°</b>, and <b>Flip horizontally</b> and <b>Flip vertically</b>. Properties takes an exact Angle.</p>"
            + "<p>Drag the square handles to resize. A turned item resizes along its own sides, and the opposite side stays where it is. From a corner, a shape keeps its proportions when Shift is held; a picture keeps them unless Shift is held.</p>"
            + "<p>Lines turn by moving their ends. Text boxes and tables, chips and hotspots do not turn.</p>"),
        topic("Button Map", "Text boxes",
            "<p>Draw → <b>Box</b> → <b>Text box</b>, then drag. Double-click a text box (or <b>Edit text…</b>) to type.</p>"
            + "<ul>"
            + "<li><b>Text</b>: Font size, Bold, Word wrap, <b>Scale font with box</b>, and alignment Across (Left, Centre, Right) and Down (Top, Middle, Bottom).</li>"
            + "<li><b>Box</b>: preset Size (Caption, Small, Medium, Large, Title, Wide), Theme (Dark, Hollow, Sheet), Text colour…, Fill colour…, Outline colour…, Fill opacity and Outline opacity.</li>"
            + "<li><b>Copy and paint format</b>: <b>Copy format</b> takes this box's look; <b>Paint format</b> puts it on the next boxes you click; <b>Clear formatting</b> resets it; <b>Copy text</b> copies the words.</li>"
            + "</ul>"),
        topic("Button Map", "Tables",
            "<p>Draw → <b>Box</b> → <b>Table</b>, then drag. Double-click a cell to type in it.</p>"
            + "<ul>"
            + "<li><b>Rows and columns</b>: Insert row above, Delete this row, Insert column left, Delete this column, and an <b>ID column</b>.</li>"
            + "<li><b>Cell</b>: <b>Free position</b> lets a cell be dragged out of the grid; <b>Independent of table</b> keeps it still when the table moves; <b>Spawn empty cell</b> adds a loose cell; <b>Delete this cell</b>; <b>Place across</b> and <b>Place down</b> park a cell at a side.</li>"
            + "<li><b>Look</b>: Theme (Dark, Hollow, Sheet) and font size.</li>"
            + "</ul>"
            + "<p>Select a table with chips or text boxes on it and choose <b>Group selected</b>: they are packed into the table and move with it. <b>Break group</b> takes them out again; <b>Delete table</b> removes it.</p>"),
        topic("Button Map", "Pictures",
            "<p>Draw → <b>Import picture…</b> adds a picture file on top of the photo. Edit → <b>Paste picture</b> (Ctrl+Shift+V), or <b>Paste picture</b> in the canvas's Draw section, adds the picture on the clipboard. Pictures are saved beside the device's module file.</p>"
            + "<p>A picture moves, resizes, turns and flips like a shape (see Rotate, flip and resize). Its <b>Picture</b> section has:</p>"
            + "<ul>"
            + "<li><b>Crop</b>: the handles turn blue and cut the picture instead of scaling it; what stays does not move. Esc or selecting something else ends it. <b>Reset crop</b> shows the whole picture again; Properties takes exact crop values.</li>"
            + "<li><b>Add snap point</b> (then click the picture) and <b>Clear snap points</b>: chips snap to these points.</li>"
            + "<li>Opacity.</li>"
            + "</ul>"),
        topic("Button Map", "Layers panel",
            "<p>View → <b>Layers</b> shows every item while editing, top of the stack first, then the photo.</p>"
            + "<ul>"
            + "<li>The <b>eye</b> hides an item: it is not drawn, on the live map either, and is left out of exports. A Device Pack keeps it, still hidden.</li>"
            + "<li>The <b>lock</b> keeps an item in place: clicks pass through it, and it is not moved, nudged or deleted. Ctrl+L locks or unlocks the selection; Ctrl+Shift+L unlocks everything.</li>"
            + "<li>Open a chip (the arrow) to hide or lock its hotspot or each leader on its own. Locking or hiding the chip covers them all.</li>"
            + "<li>Drag a row up or down to change what is on top. The right-click menu's <b>Arrange</b> section does the same a step at a time: Bring to front, Bring forward, Send back, Send to back.</li>"
            + "<li>Click a row to select the item (Ctrl or Shift to add); double-click a drawing's row to name it.</li>"
            + "<li><b>Show all</b> and <b>Unlock all</b> undo every hide and lock. The filter shows only Chips, Drawings, Pictures, or Text &amp; tables.</li>"
            + "</ul>"),
        topic("Button Map", "Properties panel",
            "<p>View → <b>Properties</b> shows the selected item's exact values while editing. Positions and sizes are in percent of the page.</p>"
            + "<ul>"
            + "<li>A shape or picture: X, Y, Width, Height and Angle, then fill, colours, line width, outline and opacity; a picture also has Crop left, top, right and bottom.</li>"
            + "<li>A line: Start and End X and Y, colour, width, outline and the Start and End heads.</li>"
            + "<li>A chip: its place and its hotspot's, font size, chip size and colours.</li>"
            + "<li>Several items: only the style shows, and a change applies to all of them.</li>"
            + "</ul>"
            + "<p>Type a number and press Enter, or click a colour to open the colour picker. A locked item's values show but do not change.</p>"),
        topic("Button Map", "Align and distribute",
            "<p>Select several items and right-click one of them. <b>Align and distribute</b> lines them up <b>Across</b> (Left, Centre, Right) or <b>Down</b> (Top, Middle, Bottom) by their edges or middles. <b>Space out</b> leaves equal gaps between three or more. Locked items stay where they are.</p>"),
        topic("Button Map", "Colours",
            "<p>The colour picker opens from Colours, Fill colour…, Outline colour… and the Properties swatches. Drag in the square and the bar, or click a swatch; the change shows at once.</p>"
            + "<p><b>Recent</b> shows the colours you used last, on any device. <b>Pick from map</b> closes the picker; click anywhere in the window to take the colour there (right-click or Esc gives up).</p>"),
        topic("Button Map", "Editor options",
            "<p><b>Edit → Editor options…</b> in the Button Map opens Options at its <b>Button Map</b> section; the same settings are under Options in the main window. They apply to every device.</p>"
            + "<ul>"
            + "<li><b>Labels</b>: <b>Chip text</b>, <b>Description first</b>, <b>Several actions</b> and <b>Unbound</b> (see Action labels).</li>"
            + "<li><b>Editing</b>: <b>Undo steps</b>, how far Undo can go back; <b>Rotate snap</b>, the degrees per step when Shift is held while turning an item or drawing a line; <b>Press to find</b> and <b>Find axes</b> (see Selecting, undo and keys).</li>"
            + "<li><b>Autosave</b>: <b>Autosave</b> keeps a recovery copy of unsaved edits every <b>Autosave seconds</b> while you edit. If the program closes before you save, opening the device again offers <b>Restore</b> (the edits open for editing; save to keep them), <b>Discard</b>, or <b>Not now</b>. Save and Discard remove the copy; the module file is only written by Save.</li>"
            + "<li><b>Export</b>: <b>Export size</b>, 1x, 2x or 3x (also File → Export size); <b>Mode title</b>, the mode's name at the top of each Export modes page.</li>"
            + "<li><b>Colours</b>: <b>Recent colours</b>, how many the colour picker keeps.</li>"
            + "</ul>"),
        topic("Button Map", "Selecting, undo and keys",
            "<p><b>Press to find</b>: while editing, press a button or hat on the device and its chip is selected and scrolled into view (a group member selects its group). A control that is not on the map yet is shown in the pool, filtered by name; a hidden one is pointed to the Layers panel. Turn it off, or let a pushed axis count too, in Editor options.</p>"
            + "<p>Click selects; Shift-click or Ctrl-click adds or removes; drag on empty space for a box selection. Arrow keys nudge the selection; Shift+Arrow nudges by the grid size. Undo and Redo are also at the top of every right-click menu.</p>"
            + "<ul>"
            + "<li><b>Ctrl+S</b> Save</li>"
            + "<li><b>Ctrl+Z</b> Undo; <b>Ctrl+Y</b> or <b>Ctrl+Shift+Z</b> Redo</li>"
            + "<li><b>Ctrl+D</b> Duplicate; <b>Ctrl+C</b> Copy; <b>Ctrl+V</b> Paste; <b>Ctrl+Shift+V</b> Paste picture</li>"
            + "<li><b>Ctrl+G</b> Group; <b>Ctrl+Shift+G</b> Break group</li>"
            + "<li><b>Ctrl+L</b> Lock or unlock the selection; <b>Ctrl+Shift+L</b> Unlock everything</li>"
            + "<li><b>Delete</b> or <b>Backspace</b> Remove the selection</li>"
            + "<li><b>Ctrl+0</b> Reset view to 100%; <b>Alt</b> while dragging: no snapping; <b>Shift</b> while drawing: keep proportions or 15° steps</li>"
            + "<li><b>Esc</b> Cancel the tool, crop, rename or group edit</li>"
            + "<li><b>F1</b> This guide</li>"
            + "</ul>"),
        topic("Options and Profile", "Options",
            "<p>Tools → <b>Options</b> (or the gear on the toolbar). Program settings, not stored in the profile.</p>"
            + "<ul>"
            + "<li><b>Global</b>: Close to tray, Minimize to tray, <b>Check for updates</b> (when the program starts; see Installing and updating), <b>Device change behavior</b> (Reload, Ignore, Disable), Hidhide on start, axis refresh on activation and mode change, Debug log level, and <b>Files</b> (data, profiles, modules, logs and other folders).</li>"
            + "<li><b>User Interface</b>: Dark mode, UI scale, Disable Windows scaling, Display mode (numbers and/or labels), Input highlighting and Highlight source.</li>"
            + "<li><b>Action</b>: the Action list order, and settings for Axis Delta, Change Mode, Double Tap, Macro, Play Sound, Smart Toggle, Tempo, and Text-To-Speech (voice).</li>"
            + "<li><b>Profile</b>: Enable auto loading — load a profile when a chosen program starts — and Remain active on focus loss.</li>"
            + "<li><b>OSC Connection</b>: Enabled, Input host and port, Output address, and press timing.</li>"
            + "<li><b>Display</b>: Home card options and <b>Reset all card sizes</b>.</li>"
            + "<li><b>Auto Mapper</b>: Overwrite used inputs and Remember overwrite.</li>"
            + "</ul>"),
        topic("Options and Profile", "Profile Settings",
            "<p>View → <b>Profile Settings</b>. Stored in the profile; save the profile to keep them.</p>"
            + "<ul>"
            + "<li><b>Startup Mode</b>: the mode the profile is in when it is loaded, including when a program auto-loads it. <b>Use Heuristic</b> picks the first mode, in alphabetical order, that has no parent; <b>Last Active</b> picks the mode the profile was using the last time it ran; a mode by name picks that mode. <b>Toggle</b> starts in the mode shown in the toolbar, so change the toolbar mode to start somewhere else.</li>"
            + "<li><b>Macro Default Delay</b>: the pause between macro steps.</li>"
            + "<li><b>vJoy Behavior</b>: treat each vJoy device as an output (default) or as an input.</li>"
            + "<li><b>vJoy Initial Values</b>: axis values set when the profile starts.</li>"
            + "</ul>"),
        topic("Options and Profile", "Scripts",
            "<p>View → <b>Scripts</b> adds Python scripts to the profile. <b>Add Script</b> picks a .py file; each script can be renamed and its variables set on that page. Scripts are saved with the profile. A script's <b>vjoy</b> object can only use outputs the vJoy output modules claim.</p>"),
        topic("Troubleshooting", "Nothing reaches vJoy",
            "<ul>"
            + "<li>Is <b>Toggle</b> on? The bottom bar should say Active.</li>"
            + "<li>Is the input <b>claimed</b> in its input module? Unclaimed inputs are ignored.</li>"
            + "<li>Does the wire show <b>(not claimed)</b>? Claim that output in Configure output module.</li>"
            + "<li>Is the action in the <b>Executing mode</b>? Only that mode's actions (and its parents') run.</li>"
            + "<li><b>system.log</b> in the Logs folder (Options → Global → Files) notes each blocked output once.</li>"
            + "</ul>"),
        topic("Troubleshooting", "Xbox does nothing",
            "<ul>"
            + "<li>Open the Xbox page: it must say <b>ViGEmBus ready</b>. If not, install ViGEmBus.</li>"
            + "<li>The pad exists only while the profile runs (Toggle on) and after a Map to Xbox action has sent.</li>"
            + "<li>Check the action uses <b>Map to Xbox</b> with <b>Xbox 360 Controller</b> and the right Target.</li>"
            + "</ul>"),
        topic("Troubleshooting", "A key binding does not fire",
            "<p>Open Configure input module on <b>Keyboard</b> and check the key is claimed. Once you save a keyboard choice, only claimed keys fire.</p>"),
        topic("Troubleshooting", "A device is missing or seen twice",
            "<ul>"
            + "<li>Not on Home: check View → <b>Hidden devices…</b>.</li>"
            + "<li>A game sees both the physical stick and vJoy: hide the physical stick with <b>HiDHide</b>.</li>"
            + "<li>Bindings belong to a device that was replaced: use <b>Swap Devices</b>.</li>"
            + "</ul>")
    ]
}

function topic(section, title, body) {
    return { "section": section, "title": title, "body": body }
}
