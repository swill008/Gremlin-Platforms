// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.pragma library

function topics() {
    return [
        topic("Start", "Overview",
            "<p>Gremlin-Platforms reads your physical controllers and runs the actions in the loaded profile. A game or another program then sees the result, usually through vJoy, a logical device, or an Xbox controller.</p>"
            + "<p>Start from Home, or open a profile with File → Load Profile. Open Configuration for a device and use Add Action on an input. Turn Gremlin-Platforms on with Toggle when those actions should run. Turn it off when the physical devices should be left alone.</p>"),
        topic("Start", "What is saved where",
            "<p>Four stores are kept separate. Saving one does not save the others.</p>"
            + "<p><b>Profile.</b> Modes, bindings, and actions. File → Save Profile writes this file. File → Save Profile As writes a new one. Closing the program asks when the profile has changes that are not saved.</p>"
            + "<p><b>Module file.</b> One file for each device. It holds the device picture, the configuration list’s look, and an output device’s look. The input module chooses which file that device uses. Button Map, Configure input module, and Configure output module write this file. Display options are written only when you press Save with module.</p>"
            + "<p><b>Program settings.</b> Options, the Home layout, window sizes, and HiDHide choices. These are kept for the program, not inside one profile.</p>"
            + "<p><b>Calibration.</b> The center and the ends of an axis. Save on that axis writes it. Closing Calibration, or choosing another device, asks when an axis is not saved.</p>"),
        topic("Start", "Toggle",
            "<p>Toggle makes the loaded profile live. While it is off, you are only editing. While it is on, inputs run their actions.</p>"
            + "<p>Use Toggle on the toolbar. It uses the accent color while Gremlin-Platforms is on. Turn it off before you change hardware, or before you close a game, if you want the physical devices visible again.</p>"),
        topic("Start", "Profiles",
            "<p>A profile stores modes and the actions bound to each device.</p>"
            + "<p>File → New Profile starts an empty profile. File → Load Profile opens one. File → Recent lists profiles you have opened. File → Save Profile writes the current file. A successful save says “Saved to the profile.” Options can also open a profile when a chosen program starts. File → Exit closes Gremlin-Platforms.</p>"),
        topic("Home", "Home",
            "<p>Home lists input devices and output devices. Each card is one device.</p>"
            + "<p>View → Home, or Home on the toolbar, returns here. Select a card to work on that device. Right-click a card for Button Map and the other actions for that device.</p>"
            + "<p>View → Home layout sets the arrangement: Single list, Side by side, or Stacked. The choice is kept.</p>"),
        topic("Home", "Control display",
            "<p>Control display is the extra live view of a device’s inputs. It can stay open while you work.</p>"
            + "<p>View → Control Display pins it for the device you are focused on. Choose it again to change that pin. The program remembers that you left it open.</p>"),
        topic("Home", "Hidden devices",
            "<p>Hidden devices removes a card from Home. It does not hide the device from Windows or from other programs. Use HiDHide for that.</p>"
            + "<p>View → Hidden devices. Turn a device off to take its card off Home. Turn it on to put the card back.</p>"),
        topic("Configuration", "Actions",
            "<p>Configuration is where one physical input gets its actions. The actions are stored in the profile. They are written to disk when you save the profile.</p>"
            + "<p>View → Configuration opens the focused device. Add Action on an input opens the editor for that input. Build the action, then press OK. The action appears under that input. Delete removes it. Close pane after OK closes the editor when OK succeeds.</p>"
            + "<p>Leaving an input that has changes asks you to save or discard them. Save here means keep the action in the profile. It does not replace File → Save Profile.</p>"
            + "<p>Tools → Action Editor opens the same actions in a window. Opened from the menu, it can show the whole device. Opened for one input, it shows that input only.</p>"),
        topic("Configuration", "Containers",
            "<p>Some actions hold other actions. Chain runs the next action in a list on each press, then starts over. Condition runs its action only when the condition is true. Tempo uses one action for a short press and another for a long press. Double Tap uses one action for a single press and another for a quick second press. Smart Toggle turns a momentary press into on, then off.</p>"
            + "<p>Add the container first, then add the actions it should run. A hat can use Hat as Buttons so each direction is its own button. Unmapped directions do nothing.</p>"),
        topic("Configuration", "Display options",
            "<p>Display options change how this device’s configuration list looks. They do not change the actions. The look is stored in that device’s module file. Whether the panel is open is stored with the program, separately for each device.</p>"
            + "<p>Edit Display Options opens the panel. Changes show immediately and stay on the screen until Save with module. A successful save says “Saved to the module file.” Reset returns the built-in look and still needs Save with module if you want that kept.</p>"
            + "<p>Hide Display Options, Close, or opening another device asks when there are unsaved changes. Save writes the module file. Discard returns to the last save. The first visit opens the panel. After that, the program restores whether you left it open or closed.</p>"
            + "<p>An output device has its own display options for pads, hats, meters, and buttons. Those are saved the same way, into that device’s module file.</p>"),
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
            + "<p>Choose the mode. Modes are created in Tools → Manage Modes. Only the current mode’s actions run.</p>"),
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
            + "<p>Tools → Manage Modes creates, renames, and removes modes. The mode box in the toolbar is the one you are editing. Executing mode, at the bottom, is the one that runs. Change Mode switches that running mode from a button. Profile Settings chooses the mode used when the program is turned on. Use Heuristic picks the first mode, in alphabetical order, that has no parent. Last Active picks the mode this profile was running the last time it was on. Save the profile to keep the modes.</p>"),
        topic("Tools", "Button Map",
            "<p>Button Map is a picture of one device, with a chip on each control. Moving a chip changes the picture, not the action bound to that control. The same layout is used live, and a press still lights the matching chip.</p>"
            + "<p>Tools → Button Map opens a blank map. Choose the device from the menu. Right-click a device card and choose Button Map to open that device. File → Edit Mapping starts an edit. Drag chips from the pool onto the photo. Drag a chip to move it, and drag its dot to move the contact. Scroll to zoom. Drag with the middle button to pan.</p>"
            + "<p>File → Save writes the layout to that device’s module file. A successful save says “Saved to the module file.” File → Cancel drops the edit. Closing the window asks when the edit is not saved. Right-click a chip to rename it, change its shape, or set its colors. F1 in that window opens the editor’s own help. Undo and Redo in that window apply to the picture only.</p>"),
        topic("Tools", "Viewers",
            "<p>The viewers show live values. They do not change the profile.</p>"
            + "<p>Tools → Device Viewer shows every control on a device. Tools → vJoy Viewer shows the vJoy device an input is driving. Tools → Xbox Viewer shows the virtual Xbox control. The same viewers are on the toolbar. Leave one open while you move the stick.</p>"),
        topic("Tools", "Calibration",
            "<p>Calibration sets the center and the ends of an axis so the full travel is used. It is stored with the program, not in the profile.</p>"
            + "<p>Tools → Calibration. Choose the device. Move the axis, or type the values. The axis shows Not saved until you press its save button. A successful save says “Saved to calibration.” Closing the window, or choosing another device, asks when an axis is not saved. Save writes it. Discard returns to the last saved calibration.</p>"),
        topic("Tools", "Device information",
            "<p>Device information shows the name and the identifiers Windows reports for a device.</p>"
            + "<p>Tools → Device Information. Select the device. Use the identifiers when two devices look alike.</p>"),
        topic("Tools", "Auto Mapper",
            "<p>Auto Mapper builds a starting map. It copies the selected buttons, axes, and hats from an input module onto the same numbers on an output module. It does not match devices by name. It uses the order shown in the lists. The first checked input is wired to the first checked output. The second input is wired to the second output.</p>"
            + "<p>Choose the mode before you create the map. The new wires are stored only in that mode.</p>"
            + "<p>Combine onto Selected Outputs is for when you check more inputs than outputs. The output list starts over. Three input modules and one output module means all three inputs are wired to that one output.</p>"
            + "<p>Leave Combine onto Selected Outputs off when each input should have its own output. You check three input modules. You check two output modules. The first input is wired to the first output. The second input is wired to the second output. The third input has no output left, so it is skipped. No wires are created for that third input. Turn the switch on if that third input should still get a map. The output list starts over, and the third input is wired to the first output.</p>"
            + "<p>Overwrite used inputs replaces wires that already exist on those controls in the selected mode. Leave it off, and those wires stay as they are.</p>"),
        topic("Tools", "Swap Devices",
            "<p>Swap Devices moves a profile’s bindings from one physical device to another of the same kind.</p>"
            + "<p>Tools → Swap Devices. Choose the device that is in the profile and the device that should take its place. Save the profile afterward.</p>"),
        topic("Tools", "Modules",
            "<p>A module file is the picture and the saved look for one device. Input modules are physical devices. Output modules are vJoy and the other outputs. The input module chooses the file. Button Map and both display-option panels use that same file.</p>"
            + "<p>Tools → Configure input module edits an input. Tools → Configure output module edits an output. Module file opens the file controls: the files in the current folder, Browse for File, and Delete. Checks, names, and the picture ask before the window closes if they are not saved. A successful save says “Saved to the module file.”</p>"
            + "<p>The picture set here is the one HiDHide uses until you choose a different picture for that device in HiDHide. Tools → Import devices reads a device file. Tools → Export devices writes the selected device.</p>"),
        topic("Tools", "HiDHide",
            "<p>HiDHide hides selected controllers from other programs. Gremlin-Platforms does not install the driver. Tools → HiDHide opens the window. Get HiDHide opens the download page. Test opens the Windows game-controller panel so you can see whether a controller is still visible.</p>"
            + "<p>The top row shows whether the driver was found, its version, and Gremlin control. Gremlin control starts off. While it is off, this window does not change the driver. Turn it on to let Gremlin-Platforms apply the device list, the program list, Allow list or Block list, and HiDHide Enabled. Those choices are kept, and they are written to the driver while Gremlin control is on. They stay when you exit.</p>"
            + "<p>HiDHide Enabled means the driver enforces both lists. Off means the driver is installed but it is not hiding anything. Gaming devices only limits the list to game controllers. Turn it off and press Refresh to look at a wider list.</p>"
            + "<p>A device can use the picture from its module. Change image or Add image replaces that picture for this list only, and the replacement is kept. The selector adds or removes that device. A device that is actually hidden is dimmed, and HIDDEN is drawn across the row.</p>"
            + "<p>Allow list means only the programs in the list can see the hidden controllers. Block list means the programs in the list cannot see them. Gremlin-Platforms can still see the devices in both modes. Add Program adds an executable. Remove takes it off the list. The window size, and the bar between the devices and the programs, are kept.</p>"),
        topic("Tools", "Options",
            "<p>Options are program settings. They are not stored inside one profile.</p>"
            + "<p>Tools → Options. Action sequence ordering sets the order actions run. Highlight scope and highlight speed control how a live press is shown. Log level sets how much is written to the log. OSC input host, OSC output host, and OSC auto-release set the OSC connection and how long an OSC input stays down. Profile auto-loading opens a profile when a chosen program starts. Status cards resets the Home card sizes. Text to Speech chooses the voice used by the Text to Speech action.</p>"),
        topic("View", "Scripts",
            "<p>Scripts are extra logic stored with the profile.</p>"
            + "<p>View → Scripts opens the script page. Edit the script there, then save the profile.</p>"),
        topic("View", "Profile settings",
            "<p>Profile settings are options stored in the profile rather than for the whole program.</p>"
            + "<p>View → Profile Settings opens that page. Change the settings, then save the profile.</p>")
    ]
}

function topic(section, title, body) {
    return { "section": section, "title": title, "body": body }
}
