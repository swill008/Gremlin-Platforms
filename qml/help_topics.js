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

        topic("Configuration", "Actions",
            "<p>Configuration is where one physical input gets its actions. The actions are stored in the profile. They are written to disk when you save the profile.</p>"
            + "<p>View → Configuration opens the focused device. Add Action on an input opens the editor for that input. Build the action, then press OK. The action appears under that input. Delete removes it. Close pane after OK closes the editor when OK succeeds.</p>"
            + "<p>Leaving an input that has changes asks you to save or discard them. Save here means keep the action in the profile. It does not replace File → Save Profile.</p>"),
        topic("Configuration", "Containers",
            "<p>Some actions hold other actions. Chain runs the next action in a list on each press, then starts over. Condition runs its action only when the condition is true. Tempo uses one action for a short press and another for a long press. Double Tap uses one action for a single press and another for a quick second press. Smart Toggle turns a momentary press into on, then off.</p>"
            + "<p>Add the container first, then add the actions it should run. A hat can use Hat as Buttons so each direction is its own button. Unmapped directions do nothing.</p>"),
        topic("Configuration", "Display options",
            "<p>Display options change how this device’s configuration list looks. They do not change the actions. The look is stored in that device’s module file. Whether the panel is open is stored with the program, separately for each device.</p>"
            + "<p>Show Editor opens the panel. Hide Editor closes it. The sections start closed. Open one heading, or use Open all. Changes show immediately and stay on the screen until Save View Settings. A successful save says “Saved to the module file.” The bottom of the window names the file.</p>"
            + "<p>Reset View to Default is the red button. It returns the built-in look. It does not save. Save View Settings keeps that look. Copy View from… copies the display look from another input module onto this one. That copy is not kept until Save View Settings.</p>"
            + "<p>Hide Editor, the panel’s close mark, or opening another device asks when there are unsaved changes. Save writes the module file. Discard returns to the last save. Leave the configuration page with Home. The first visit opens the panel. After that, the program restores whether you left it open or closed.</p>"
            + "<p><b>Screen.</b> Sets the background of the configuration list. Choose a color, or choose an image. The image covers the color. Clear removes either one.</p>"
            + "<p><b>Shown.</b> Chooses what appears on each row. Show child rows lists the actions under a control. Show live bars draws the axis position. Its color is Live bar. Show LED dots lights a button or hat while it is pressed. Show summary lists the actions in one line. Summary size sets the size of that line.</p>"
            + "<p><b>List.</b> Sets the space around the whole list, and the space between groups. A group is one control and the actions under it. Space between groups is the gap before the next control.</p>"
            + "<p><b>Group.</b> Sets the card around one control and its actions. Space inside the group is the gap between that control and its actions, and between the actions. Padding is the space around the card. Alignment places the card on the left, in the center, or on the right. Corner radius rounds the card. Color is the card background. It starts clear, so the card is invisible until you choose a color.</p>"
            + "<p><b>Parent row.</b> Sets the control row itself. Height, padding, alignment, corner radius, and name width change that row. Row color is its fill. Line around the row is its outline. The child rows use that same outline.</p>"
            + "<p><b>Child row.</b> Sets each action row under a control. It has its own height, padding, alignment, corner, name width, and row color. It does not have its own outline. It uses the line from Parent row.</p>"
            + "<p><b>Text.</b> Sets the words. Parent text size and Bold names change the control name. Child text size changes the action names. Text color is the main words. Muted text is the quieter words, such as the type and the destination.</p>"
            + "<p><b>Selection.</b> Sets the row you have selected. Fill of a selected row is its background. Line around a selected row replaces the normal outline while that row is selected.</p>"
            + "<p><b>Editor.</b> Sets the action editor that opens beside a control. Alignment, padding, and the gap below the row place it. Corner radius, border width, and the border color draw its edge. Show accent bar adds a bar on the side. Accent width and Accent bar set that bar.</p>"
            + "<p>An output device uses Output Module View — Display Editor. That panel has its own options for pads, hats, meters, and buttons. Reset View to Default, Copy View from…, and Save View Settings work the same way. The look is stored in that device’s module file.</p>"),

        topic("Logical Device", "Logical Device",
            "<p>The Logical Device page is one device you build in the profile. A physical control can be mapped to a button, axis, or hat on this page. That logical control then has its own actions, in the same way a physical input does.</p>"
            + "<p>Open it with Logical Device on the toolbar. Help → Logical Device opens this guide on this section. Configuring mode, at the top right, chooses the mode you are editing. The buttons, axes, hats, and groups stay when you change mode. The actions on a control belong to the selected mode.</p>"
            + "<p>The system name is fixed. A button is always Button 1, an axis is Axis 1, and a hat is Hat 1. The number is the identity. A wire uses the type and the number, not a name you type.</p>"),
        topic("Logical Device", "Names",
            "<p>Right-click a hardware row and choose Rename to give it a second name. The name starts empty. The row then shows the system name and the name you typed. Hide system name, on that same prompt, shows only the name you typed. The system name is still the identity. Point at the name, and the system name appears, only when a second name is set.</p>"
            + "<p>Clear name removes the second name. It appears in the menu only when the row has one. The system name shows again. Two rows may use the same second name. That does not join them.</p>"),
        topic("Logical Device", "Groups",
            "<p>A group is a folder. A control belongs to one group. The list shows a header for each group, with the name and the counts. The controls sit under that header. Ungrouped has a header too. It cannot be renamed, moved, or deleted.</p>"
            + "<p>The caret on a header appears only when the group has rows under it. Click the caret to fold the group. The header stays. Click it again to show the rows.</p>"
            + "<p>Shift-click hardware rows to select more than one. Right-click one of them and use Group as. Type a name and press Enter. Those rows move into that group. If you do this to one row that is already in a named group, the program asks before it moves the row.</p>"
            + "<p>Move to group sends the selection to a group that already exists. New group creates an empty group. On a named group, Move group up and Move group down change its place. Rename group changes its name. Delete group does not delete the controls. They go to Ungrouped.</p>"),
        topic("Logical Device", "Adding controls",
            "<p>Right-click the list. Add Button, Add Axis, and Add Hat each have a count. It starts at 1. Type a number, or use the arrows. The highest count is 180. Press Enter, or click the words, to add that many. They are created in Ungrouped and take the next free numbers of that type. The menu stays open until you click away.</p>"),
        topic("Logical Device", "The menu",
            "<p>The right-click menu shows only the actions that apply to what you clicked. It does not grey out the rest.</p>"
            + "<p>On empty space the menu has Add Button, Add Axis, Add Hat, New group, Order by system name, Order by your name, Order group names A to Z, and Display. Undo and Redo appear only when there is a change to undo or redo.</p>"
            + "<p>On a hardware row, those stay, and the row actions appear: Add Action, Assign hardware, Rename, Group as, Move to group, and Delete. Clear name appears only when that row has a second name. Delete removes the control and every hardware link that points at it.</p>"
            + "<p>On a named group, the group actions appear: Move group up, Move group down, Rename group, and Delete group.</p>"
            + "<p>While Toggle is on, the edit actions are hidden. Display stays.</p>"),
        topic("Logical Device", "Assign hardware",
            "<p>Assign hardware opens its own window for the hardware row you clicked. It lists input devices. Search limits that list. The window already shows only the same kind of control: buttons for a button, axes for an axis, and hats for a hat. The keyboard is included. The logical device is not. A vJoy device is included only while its Settings switch is Input.</p>"
            + "<p>Each control has a checkbox. The device row checks or clears every control under it. A check adds Map to Logical Device on that physical control. It does not remove that control’s other actions. The logical row then shows Written by, with the device and the control. An axis also shows absolute or relative, and a scale. A button shows Invert. Unchecking removes only that one link.</p>"),
        topic("Logical Device", "Actions",
            "<p>Add Action adds one action for the current mode and opens the action editor beside the list. It is the same sequence editor used on a physical input. Press OK to keep the action in the profile. That does not replace File → Save Profile. Close pane after OK closes the editor when OK succeeds. The close mark asks when the editor has changes that are not saved.</p>"
            + "<p>The caret on a hardware row appears only when a list opens under it: an action, or a second Written by line. The first Written by line is already on the row, so it does not add a caret. Click the caret to show or hide that list. An action row shows the action name and, under it, the target. The row grows so that target is not on the bottom edge. The target uses the same name as the editor, so an Xbox A shows as A. An action row has nothing under it, so it has no caret. Click an action row to open it in the editor.</p>"),
        topic("Logical Device", "Find, order, and moving",
            "<p>Find limits the list. Type a system name, your name, or a group name. All types can be limited to Buttons, Axes, or Hats. Ungrouped shows only rows in Ungrouped. No hardware writer shows rows with no physical control mapped to them. No actions in this mode shows rows with no action in the current mode. Clear turns the filters off. A hidden row is not deleted.</p>"
            + "<p>Order by system name sorts the controls inside each group by number, with buttons, then axes, then hats. Order by your name sorts by the second name, and uses the system name when there is no second name. Order group names A to Z sorts the named groups. Ungrouped stays first.</p>"
            + "<p>The grey box at the left of a hardware row or a group header is the drag handle. The type icon sits to the right of that box. Drag a control onto another control. Drop on the top half to place it before that control, or on the bottom half to place it after. Drop on a group header to put it in that group. Drag a group header to move that group.</p>"),
        topic("Logical Device", "Display",
            "<p>Show Editor, to the right of Clear, opens Logical Device — Display Editor on the right. The button then says Hide Editor. That choice is kept. Display, at the bottom of the right-click menu, opens the same panel. It changes how this page looks. It does not change the controls or the actions. The sections start closed. Open one heading, or use Open all and Close all.</p>"
            + "<p>Changes show immediately. They are kept only when you press Save View Settings. A save says “Saved for this page.” The look is stored with the program, for this page. It is not in the profile and not in a module file.</p>"
            + "<p>Reset View to Default is the red button. It returns the built-in look, which is the look this page opened with. It does not save. The close mark asks when there are unsaved changes. Save writes them. Discard returns to the last save.</p>"
            + "<p><b>Shown.</b> Show action rows lists the actions under a control. Show written by lists the physical control on the row. Written-by size sets the size of that line.</p>" + "<p><b>Handles.</b> These change the arrow and the drag box only. They do not change the parent row or the action row. An action row has no arrow and no drag box. Caret size and Caret color change the arrow. The color starts the same as the text and uses the same chooser. Pad width, pad height, Pad color, and Pad corner change the drag box. The corner starts slightly round. The extra click area around the pad stays.</p>"
            + "<p><b>List.</b> Space between rows is the gap between every row. Padding is the space around the list. Same on all sides uses one size. Each side sets top, right, bottom, and left.</p>"
            + "<p><b>Group.</b> Space inside the group is the gap under each row in the group. Padding, corner radius, and color change the group header.</p>"
            + "<p><b>Parent row.</b> Height is the smallest a hardware row will be. The row grows when the caret, the drag pad, the name, the written-by line, or the padding needs more room. A group header and an action row do the same. A group header is at least 40. Padding, corner radius, and row color change that row.</p>"
            + "<p><b>Action row.</b> Height is the smallest an action row will be. It grows to fit the action name and the target. Indent past parent is how far that row sits to the right of the hardware row. Padding, corner radius, and row color are its own. An extra Written by row uses this same box.</p>"
            + "<p><b>Text.</b> Parent text size and Bold names change the hardware name. Group text size changes the header. Action name size changes the action name. Action target size and Action target change the line under it, such as the Xbox button. Text color is the main words. Muted text is the quieter line, such as Written by and the group counts.</p>"
            + "<p><b>Selection.</b> Fill of a selected row is its background. Line around a selected row is its outline while it is selected.</p>"),
        topic("Actions", "Map to Keyboard",
            "<p>Sends one or more keyboard keys when the input fires.</p>"
            + "<p>Choose the key, and whether the key is held while the input is held or tapped once.</p>"),
        topic("Actions", "Map to Mouse",
            "<p>Moves the mouse, clicks a mouse button, or turns the wheel.</p>"
            + "<p>Choose button, motion, or wheel, then the amount.</p>"),
        topic("Actions", "Map to vJoy",
            "<p>Sends the input to a vJoy axis, button, or hat. vJoy must already be installed. This program does not ship vJoy.</p>"
            + "<p>Choose the vJoy device and the output. Axes can be scaled. Buttons follow the physical press. Use the vJoy Viewer to watch the result.</p>"),
        topic("Actions", "Map to Logical Device",
            "<p>Sends the input to a logical output device created in this program.</p>"
            + "<p>Choose the logical device and the control on it.</p>"),
        topic("Actions", "Map to Xbox",
            "<p>Sends the input to a virtual Xbox controller. That output needs its own driver. This program does not ship that driver.</p>"
            + "<p>Choose the Xbox control. Use the Xbox Viewer to confirm the output while Gremlin-Platforms is on.</p>"),
        topic("Actions", "Macro",
            "<p>Plays a sequence of keys, buttons, mouse moves, and pauses.</p>"
            + "<p>Record or insert the steps. Set whether a new press waits, interrupts, or is ignored while the macro is still running.</p>"),
        topic("Actions", "Response Curve",
            "<p>Changes how an axis travels from one end to the other. The curve can be straight, bent, or inverted.</p>"
            + "<p>Add it to an axis. Edit the curve. Later actions and the mapped device see the curved output.</p>"),
        topic("Actions", "Split Axis",
            "<p>Turns one axis into two ranges, usually the two directions of a throttle or a split stick.</p>"
            + "<p>Set the center, and which side goes to which output.</p>"),
        topic("Actions", "Merge Axis",
            "<p>Combines two inputs into one axis.</p>"
            + "<p>Choose the two sources and how they are combined.</p>"),
        topic("Actions", "Axis Delta",
            "<p>Nudges an axis by a step instead of jumping to an absolute position. Use it when a button should trim an axis.</p>"
            + "<p>Choose the axis and the size of each step.</p>"),
        topic("Actions", "Dual Axis Deadzone",
            "<p>Applies one deadzone to a pair of axes, such as a stick’s X and Y, so a small circular or square center is ignored.</p>"
            + "<p>Set the size and the shape.</p>"),
        topic("Actions", "Change Mode",
            "<p>Switches the active mode while the input is held, or switches and stays.</p>"
            + "<p>Choose the mode. Modes are created in Tools → Mapping → Manage Modes. Only the current mode’s actions run.</p>"),
        topic("Actions", "Load Profile",
            "<p>Loads another profile when the input fires.</p>"
            + "<p>Choose the profile file.</p>"),
        topic("Actions", "Pause and Resume",
            "<p>Pauses Gremlin-Platforms, resumes it, or toggles that state from a button.</p>"
            + "<p>Choose pause, resume, or toggle.</p>"),
        topic("Actions", "Play Sound",
            "<p>Plays a sound file when the input fires.</p>"
            + "<p>Choose the file.</p>"),
        topic("Actions", "Text to Speech",
            "<p>Speaks a sentence when the input fires.</p>"
            + "<p>Type the sentence. The voice is chosen in Options.</p>"),
        topic("Actions", "Run Command",
            "<p>Starts a program or command when the input fires.</p>"
            + "<p>Choose the program. It runs on your machine with your own permissions.</p>"),
        topic("Actions", "Description",
            "<p>Stores a note on the input. It does not change the output.</p>"
            + "<p>Type the note so you can remember what the binding is for.</p>"),
        topic("Actions", "Reference",
            "<p>Points at another action so you do not have to rebuild it.</p>"
            + "<p>Choose the action it should follow.</p>"),
        topic("Modes", "Modes",
            "<p>A mode is a set of bindings. Only the current mode’s actions run. The same button can do different work in another mode.</p>"
            + "<p>Tools → Mapping → Manage Modes creates, renames, and removes modes. Configuring mode, in the toolbar, chooses which map you are editing. Executing mode, at the bottom, chooses which map runs. Change Mode switches that running mode from a button. Profile Settings chooses the mode used when the program is turned on. Use Heuristic picks the first mode, in alphabetical order, that has no parent. Last Active picks the mode this profile was running the last time it was on. Save the profile to keep the modes.</p>"),
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
