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
        topic("Tools", "Button Map",
            "<p>Button Map is a picture of one device, with a chip on each control. Moving a chip changes the picture, not the action bound to that control. The same layout is used live, and a press still lights the matching chip.</p>"
            + "<p>Tools → Mapping → Button Map opens a blank map. Choose the device from the menu. Right-click a device card and choose Button Map to open that device. File → Edit Mapping starts an edit. Drag chips from the pool onto the photo. Drag a chip to move it, and drag its dot to move the contact. Scroll to zoom. Drag with the middle button to pan.</p>"
            + "<p>File → Save writes the layout to that device’s module file. A successful save says “Saved to the module file.” File → Cancel drops the edit. Closing the window asks when the edit is not saved. Right-click a chip to rename it, change its shape, or set its colors. F1 in that window opens the editor’s own help. Undo and Redo in that window apply to the picture only.</p>"),
        topic("Tools", "Viewers",
            "<p>The viewers show live values. They do not change the profile.</p>"
            + "<p>Tools → Viewers → vJoy Viewer shows the vJoy device an input is driving. Tools → Viewers → Xbox Viewer shows the virtual Xbox control. The same viewers are on the toolbar. Leave one open while you move the stick.</p>"),
        topic("Tools", "Calibration",
            "<p>Calibration sets the center and the ends of an axis so the full travel is used. It is stored in that input module’s file, not in the profile.</p>"
            + "<p>Tools → Device setup → Calibration, or right-click an input module and choose Calibration. Choose the input module. Move the axis, or type the values. The axis shows Not saved until you press its save button. A successful save says “Saved to the module file.” Closing the window, or choosing another input module, asks when an axis is not saved. Save writes it. Discard returns to the last saved calibration. While that module is in use, the saved curve is applied to the live stick before any action sees it.</p>"),
        topic("Tools", "Device information",
            "<p>Device information shows the name and the identifiers Windows reports for a device.</p>"
            + "<p>Tools → Device setup → Device Information. Select the device. Use the identifiers when two devices look alike.</p>"),
        topic("Tools", "Auto Mapper",
            "<p>Auto Mapper builds a starting map. It copies the selected buttons, axes, and hats from an input module onto the same numbers on an output module. It does not match devices by name. It uses the order shown in the lists. The first checked input is wired to the first checked output. The second input is wired to the second output.</p>"
            + "<p>Choose the mode before you create the map. The new wires are stored only in that mode.</p>"
            + "<p>Combine onto Selected Outputs is for when you check more inputs than outputs. The output list starts over. Three input modules and one output module means all three inputs are wired to that one output.</p>"
            + "<p>Leave Combine onto Selected Outputs off when each input should have its own output. You check three input modules. You check two output modules. The first input is wired to the first output. The second input is wired to the second output. The third input has no output left, so it is skipped. No wires are created for that third input. Turn the switch on if that third input should still get a map. The output list starts over, and the third input is wired to the first output.</p>"
            + "<p>Overwrite used inputs replaces wires that already exist on those controls in the selected mode. Leave it off, and those wires stay as they are.</p>"),
        topic("Tools", "Swap Devices",
            "<p>Swap Devices moves a profile’s bindings from one physical device to another of the same kind.</p>"
            + "<p>Tools → Device setup → Swap Devices. Choose the device that is in the profile and the device that should take its place. Save the profile afterward.</p>"),
        topic("Tools", "Modules",
            "<p>A module file is the picture and the saved look for one device. Input modules are physical devices. Output modules are vJoy and the other outputs. The input module chooses the file. Button Map and both display-option panels use that same file.</p>"
            + "<p>Tools → Device setup → Configure input module edits an input. Tools → Device setup → Configure output module edits an output. Module file opens the file controls: the files in the current folder, Browse for File, and Delete. Checks, names, and the picture ask before the window closes if they are not saved. A successful save says “Saved to the module file.”</p>"
            + "<p>The picture set here is the one HiDHide uses until you choose a different picture for that device in HiDHide. Tools → Device setup → Device Pack saves a device, its map and pictures to a zip, or loads one onto a device you pick.</p>"),
        topic("Tools", "HiDHide",
            "<p>HiDHide hides selected controllers from other programs. Gremlin-Platforms does not install the driver. Tools → Device setup → HiDHide opens the window. Get HiDHide opens the download page. Test HiDHide opens the Windows game-controller panel so you can see whether a controller is still visible.</p>"
            + "<p>A new install leaves the driver alone. Gremlin control, HiDHide Enabled, Automatically Start, and Gaming devices only all start off. Each switch is saved on its own. Allow list is the starting program choice. No device starts checked, and the program list starts empty.</p>"
            + "<p>The top row shows whether the driver was found, its version, Get HiDHide, and Test HiDHide. The next row is Gremlin control, HiDHide Enabled, and Automatically Start. Gremlin control lets this program write the device list, the program list, Allow list or Block list, and HiDHide Enabled. HiDHide Enabled means the driver enforces both lists. Off means the driver is not hiding anything. Automatically Start turns Gremlin control and HiDHide Enabled on each time this program starts, and writes the saved lists.</p>"
            + "<p>Gaming devices only sits above the device list. On limits that list to game controllers. Off shows the wider list. A device can use the picture from its module. Change image or Add image replaces that picture for this list only, and the replacement is kept. The selector adds or removes that device. A device that is actually hidden is dimmed, and HIDDEN is drawn across the row.</p>"
            + "<p>Allow list means only the programs in the list can see the hidden controllers. Block list means the programs in the list cannot see them. Gremlin-Platforms can still see the devices in both modes. Add Program is under the program title and adds an executable. Remove takes it off the list. The window size, and the bar between the devices and the programs, are kept. Close the window with the title-bar control. Open it again to pick up a controller that was plugged in while it was open.</p>"
            + "<p><b>Testing.</b> Test HiDHide opens the Windows Game Controllers panel. That panel is not in the program list, so what it shows depends on the settings. With HiDHide Enabled on and Allow list chosen, a hidden controller should be missing from the panel. If it is still there, hiding is not working. With Block list chosen, the panel is not blocked, so hidden controllers still show; switch to Allow list to test. With HiDHide Enabled off, every controller shows. With Gremlin control off, the panel shows whatever the HiDHide program itself is set to. The panel reads the controller list only when it opens, so close it and open it again after a change.</p>"),
        topic("Tools", "Options",
            "<p>Options are program settings. They are not stored inside one profile.</p>"
            + "<p>Tools → Options. Action sequence ordering sets the order actions run. Highlight scope and highlight speed control how a live press is shown. Log level sets how much is written to the log. OSC input host, OSC output host, and OSC auto-release set the OSC connection and how long an OSC input stays down. Profile auto-loading opens a profile when a chosen program starts. Status cards resets the Home card sizes. Text to Speech chooses the voice used by the Text to Speech action.</p>"),
        topic("View", "Scripts",
            "<p>Scripts are extra logic stored with the profile.</p>"
            + "<p>View → Scripts opens the script page. Edit the script there, then save the profile.</p>"),
        topic("View", "Profile settings",
            "<p>Profile settings are options stored in the profile rather than for the whole program.</p>"
            + "<p>View → Profile Settings opens that page. Change the settings, then save the profile.</p>"),
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
