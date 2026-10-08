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
            + "<li>On <b>Home</b>, right-click each physical device and choose <b>Module</b> → <b>Module Setup…</b>. Press the controls you will use, or tick them, then <b>Save Module</b>.</li>"
            + "<li>Right-click each vJoy device and choose <b>Module</b> → <b>Module Setup…</b>. Tick the outputs you will use, then <b>Save Module</b>. The Xbox controller needs no setup.</li>"
            + "<li>Double-click a physical device to open <b>Configuration</b>. Use <b>Add Action</b> on an input, for example Map to vJoy, then <b>OK</b>.</li>"
            + "<li><b>File → Save Profile</b> (Ctrl+S).</li>"
            + "<li>Press <b>Run</b> to run the profile. Use the <b>vJoy Viewer</b> or <b>Xbox Viewer</b> to watch the result.</li>"
            + "</ol>"
            + "<p>Tools → Mapping → <b>Auto Mapper</b> can create the Map to vJoy actions for a whole device in one step.</p>"),
        topic("Getting Started", "Installing and updating",
            "<p>Each release on GitHub has two downloads:</p>"
            + "<ul>"
            + "<li><b>Gremlin-Platforms-R1-X.Y.Z-Setup.exe</b>, the installer. It installs for your Windows user only and needs no administrator rights. The suggested folder is %LOCALAPPDATA%\\Programs\\Gremlin-Platforms; you can choose another folder you can write to. It adds a Start menu entry, an optional desktop shortcut, and an uninstaller in Settings → Apps.</li>"
            + "<li><b>Gremlin-Platforms-R1-X.Y.Z.zip</b>, the portable copy. Unzip it anywhere outside Program Files and run gremlin_platforms.exe.</li>"
            + "</ul>"
            + "<p><b>Help → Check for Updates</b> asks GitHub for the latest release. When Options → General → Startup and Tray → <b>Check for updates</b> is on (the default), it also checks when the program starts and only speaks up when there is a newer version.</p>"
            + "<p>An installed copy offers <b>Update Now</b>: it downloads the installer, checks it against the SHA-256 checksum GitHub reports, closes the program the usual way (asking about unsaved changes), installs, and starts the new version. <b>Skip This Version</b> stops the startup check from offering that version. The window shows the release notes of the new version and of any versions in between, newest first; without a connection it says \"Release notes unavailable.\" A portable copy, or one run from source, only points you to the release page.</p>"
            + "<p>Updates and uninstalling never touch your profiles, modules or settings; they are kept in your Gremlin Platforms folder (see What is saved where).</p>"),
        topic("Getting Started", "Run and status",
            "<p><b>Run</b> on the toolbar runs the loaded profile; while it runs the button reads <b>Stop</b>. While it is off you are only editing; nothing is sent to vJoy or Xbox. The button uses the accent color while the profile runs.</p>"
            + "<p>The bottom bar shows <b>Status</b> (Running, Stopped, or Running (Paused), and 'unsaved changes' when the running profile has some) and what the last save wrote. The toolbar's <b>Mode</b> is the mode you edit and the mode that runs; while the profile runs, picking a mode there switches the running profile to it.</p>"
            + "<p>When an action editor has changes that are not saved, Run asks first: <b>Save</b>, <b>Discard</b> or <b>Cancel</b>. The profile runs as saved, and while it runs the action editors are locked (“Profile running: stop it to edit”). Stop never asks.</p>"
            + "<p>When you press <b>Run</b>, the program knows where an axis is only after that axis has moved. Until then it treats the axis as centered, so a throttle, brake pedal or slider resting away from the middle is sent as center at first. After pressing Run, move each of those controls a little and it is sent where it really is. Sticks and rudders that rest at center are not affected.</p>"
            + "<p>Running does not hide controllers from games; use <b>HidHide</b> for that. What happens when a controller is plugged in or removed while running is set by Options → General → Devices → <b>Device change behavior</b> (Stop, Ignore, or Reload).</p>"),
        topic("Getting Started", "Menus and the command palette",
            "<p>Every menu in the program works the same way, in light and dark mode:</p>"
            + "<ul>"
            + "<li><b>Only what you can use.</b> Menus leave out what does not apply right now (View → <b>Home</b> while you are on Home, File → <b>Recent</b> before you have opened a profile). Nothing is greyed out.</li>"
            + "<li><b>Right-click menus</b> start with the name of what you clicked and its most used commands, then <b>sections</b> (▸) that open one at a time. The section you opened last opens again next time. Some show <b>Undo</b> and <b>Redo</b> beside the name.</li>"
            + "<li><b>Keys</b>: Up and Down move, Right and Left open or close a section or step a row of choices, Enter runs, Esc closes.</li>"
            + "<li><b>Dropdown lists</b> of ten or more entries have a search box: type part of a name, Up and Down move, Enter picks.</li>"
            + "<li><b>Command Palette</b>: Ctrl+K (or View → <b>Command Palette…</b>) lists every menu command you can use now. Type part of a name and press Enter. Shortcuts show beside the commands.</li>"
            + "<li><b>Shortcuts</b>: Ctrl+N new profile, Ctrl+O load, Ctrl+S save, Ctrl+Shift+S save as, Ctrl+K command palette, F1 this guide.</li>"
            + "</ul>"),
        topic("Getting Started", "Profiles",
            "<p>A profile holds the modes, the actions on every input, the profile settings, and the list of scripts.</p>"
            + "<ul>"
            + "<li><b>File → New Profile</b> (Ctrl+N), <b>Load Profile…</b> (Ctrl+O), <b>Recent</b>, <b>Save Profile</b> (Ctrl+S), <b>Save Profile As…</b> (Ctrl+Shift+S).</li>"
            + "<li>Closing the program or loading another profile asks first when there are unsaved changes.</li>"
            + "<li>Options → Profiles → Auto-load → <b>Load profiles automatically</b> loads a profile when a chosen program starts.</li>"
            + "</ul>"),
        topic("Getting Started", "What is saved where",
            "<p>Three separate stores. Saving one does not save the others, except where noted.</p>"
            + "<ul>"
            + "<li><b>Profile</b> (File → Save Profile): modes, actions, profile settings, scripts.</li>"
            + "<li><b>Module File</b>, one per device: claims, friendly names, the device picture, the Button Map layout, the Appearance of its Configuration page or Output View, and its calibration. Input/Output Module Setup, Button Map, Calibration, and the display editors write it. Saving an output module also saves the profile when the profile already has a file.</li>"
            + "<li><b>Program settings</b>: Options, Home layout and card sizes, window sizes, HidHide choices, and the Logical Device's Appearance.</li>"
            + "</ul>"
            + "<p>After every save the bottom bar names the file that was written. Every save is also kept in the <b>History</b> (Tools → History).</p>"),

        topic("Devices and Modules", "Home",
            "<p>Home shows one card per device: your physical devices, the <b>Keyboard</b>, <b>OSC</b>, each vJoy device, the Xbox controller, and the <b>Logical Device</b> once it has a module file. A connected device without a module shows as a card without a module (Options → Home → Show devices without a module).</p>"
            + "<ul>"
            + "<li><b>Double-click</b> a card to open its Configuration page (or <b>Output View</b> for an output).</li>"
            + "<li><b>Right-click</b> a card for its menu; the card shows as picked first, as a click does (a card in a Shift selection keeps the selection, for menu items that act on all of it). It starts with Open Configuration (Output View on an output card), Button Map and Hide Card, then the sections <b>Module</b> (Module Setup…, Auto Mapper, Calibration), <b>View</b> (the vJoy Viewer or Xbox Viewer, Device Information), <b>Cards</b> (Stack Selected Cards, Unstack, Unstack All, Reset Size, Reset All Card Sizes) and <b>Device</b> (Start Fresh… for a damaged module file, Copy Setup to Another Stick…, Swap with Another Stick…, Change vJoy Output…, which open the <b>Device Library</b> on that stick, Reset Card Layout, which clears its size and stacking, and Delete Device).</li>"
            + "<li>Items that don't apply to a card are left out. vJoy cards have no Calibration, Copy Setup to Another Stick…, Swap with Another Stick…, Change vJoy Output… or Delete Device. The Xbox card has no Module Setup, Auto Mapper, Calibration, Device Information, Copy Setup to Another Stick…, Swap with Another Stick…, Change vJoy Output… or Delete Device. The Keyboard and OSC cards have no Auto Mapper, Calibration, Device Information, Copy Setup to Another Stick…, Swap with Another Stick… or Change vJoy Output…. The Logical Device card has no Module Setup, Auto Mapper, Calibration, Device Information, Copy Setup to Another Stick…, Swap with Another Stick… or Change vJoy Output….</li>"
            + "<li><b>Delete Device</b> asks twice and is refused while the profile runs (stop it first). It removes the device's module file, its pictures and its actions in every mode. The actions are removed from the open profile, which is left with unsaved changes: save the profile to keep that. There is no question about a copy: an autosave of the stick (\"Autosave: stick deleted\") is always kept in the <b>Device Library</b> first, and if it can't be kept, nothing is deleted (see Device Library).</li>"
            + "<li><b>Shift-click</b> cards, then <b>Stack Selected Cards</b>, to group them.</li>"
            + "<li>Each card's <b>last:</b> line shows the latest input it passed or output it sent.</li>"
            + "<li><b>Compact view</b> and <b>Layout</b> (Single list, Side by side, or Stacked; also View → <b>Home Layout</b>) change how the cards are laid out. Right-click empty space for <b>Unhide All Cards</b>, <b>Reset All Card Sizes</b>, <b>Hidden Cards</b> (each hidden card; click one to unhide it) and <b>Layout</b>.</li>"
            + "</ul>"),
        topic("Devices and Modules", "Input modules",
            "<p>An input module decides which controls of a physical device exist for Gremlin-Platforms. Only <b>claimed</b> controls reach your actions, the viewers, and the Auto Mapper.</p>"
            + "<p>Open it from the card menu or Tools → Device Setup → <b>Input Module Setup</b>. Press a control on the device to claim it, or tick it; untick to release it. Give a control a <b>Friendly name</b> if you like. <b>Undo</b> and <b>Redo</b> (Ctrl+Z, Ctrl+Y) step back through the ticks and names until you open another device. <b>Save Module</b> writes the module file; <b>Cancel</b> discards.</p>"
            + "<p><b>Keyboard</b> is an input module too. Key bindings only fire for keys it claims. Until you save a choice, every key is claimed. Typing in Windows and games is never affected.</p>"
            + "<p>Calibration for a stick is stored in its input module (see Calibration).</p>"),
        topic("Devices and Modules", "vJoy output modules",
            "<p>Each vJoy device has an output module. It is the firewall in front of the vJoy driver: only outputs it <b>claims</b> are sent.</p>"
            + "<p>Open it from the card menu or Tools → Device Setup → <b>Output Module Setup</b>. Tick the axes, buttons, and hats you will use, then <b>Save Module</b>. The vJoy driver sets the maximum; the output module sets what Gremlin-Platforms may use.</p>"
            + "<p>A wire to an output that is not claimed sends nothing. It is kept, and shown as <b>(not claimed)</b> on the Configuration page, Button Map chips, the viewers, and in Map to vJoy, and the log notes it once. Claim the output to make it work.</p>"),
        topic("Devices and Modules", "Xbox output module",
            "<p>The Xbox controller (<b>Xbox 360 Controller</b>, pad 1) is a virtual Xbox 360 pad provided by the <b>ViGEmBus</b> driver. Its output module passes every control straight to the driver; there is nothing to claim.</p>"
            + "<p>Send to it with the <b>Map to Xbox</b> action: click <b>Add Action</b> on the input's row on the Configuration page (or right-click a Logical Device control and choose <b>Add Action</b>), then <b>Map to Xbox</b>. Its page (double-click the card) shows which inputs drive each control. The <b>Xbox Viewer</b> shows the live pad. The pad appears when a Map to Xbox action first sends while the profile runs, and is removed when the profile stops.</p>"
            + "<p>The page and the Xbox Viewer check the driver at their top, as HidHide does: <b>ViGEmBus driver found</b> with its version, or what is wrong (not installed, installed but not running, ViGEmClient.dll missing) and what to do. <b>Get ViGEmBus</b> opens the Nefarius releases page; <b>Test ViGEmBus</b> opens Windows Game Controllers, where the pad shows while the profile runs. The check shows even when nothing is mapped to Xbox yet.</p>"),
        topic("Devices and Modules", "Module files and Device Pack",
            "<p>Each device has its own module file, found by the device first and then by its name. In Input/Output Module Setup, <b>Module File</b> shows the current file and offers <b>Import from</b> (copy another file into this device's file), <b>Browse for File</b>, <b>Open Modules Folder</b>, and <b>Delete File</b>. <b>Import Image…</b> sets the device picture.</p>"
            + "<p>Tools → Device Setup → <b>Device Pack</b> shares a working copy of a device's setup.</p>"
            + "<p><b>Export</b> saves the device's module file, pictures, and its wires (with their actions and the output modules they send to) to a zip. Untick modes under <b>Wires in these modes</b> to leave them out. <b>Made by</b> and <b>Note</b> are shown to whoever imports the pack. <b>Show Folder</b> opens where it was saved.</p>"
            + "<p><b>Import</b> puts a pack on the device you choose under <b>Put this pack on</b>. Import adds the pack's checked controls to the ones checked here; none are unchecked. The other ticked pieces replace only what they hold (a control's name, an axis's calibration, the map), and each ticked mode under <b>Wires</b> replaces the device's wires and actions in that mode (other modes and other devices are left alone). Before anything changes, a warning lists what will be added and replaced, any controls the device doesn't have (left out), and wires to Logical Device inputs that don't exist here, which it can create. An output put on another vJoy (an output's name box) takes its wires with it. Modes are created under their parent from the pack. If a driver the pack's wires need isn't found (vJoy, a vJoy device, or the Xbox driver ViGEmBus), the import screen says so as soon as the pack is opened, and the warning says it again.</p>"
            + "<p><b>Map settings</b> holds <b>Map view</b> (pan, zoom, grid and guides) and <b>Print area and print settings</b>; both are unticked unless you tick them. The device photo comes with where it sits on the map.</p>"
            + "<p>The previous module file is kept in the <b>imported</b> folder, and the profile changes on disk only when you save it. <b>Undo Import</b> puts the last import back until you import again, open another pack, or close the window. If a file the import wrote was saved again since, it asks first, because those later changes are lost. A pack made by a newer version of the program is refused.</p>"),
        topic("Devices and Modules", "Deleted devices and backups",
            "<p>Nothing is thrown away for good. The copies stay until you delete them yourself.</p>"
            + "<ul>"
            + "<li><b>Delete Device</b> always keeps an autosave of the stick in the <b>Device Library</b> first (\"Autosave: stick deleted\"): its module file, its pictures and its bindings in every mode. If the autosave can't be written or read back, nothing is deleted. The stick then shows in the Device Library as <b>Deleted</b>.</li>"
            + "<li><b>Delete File</b> in Module Setup asks first and keeps an autosave of the module file in the Device Library (\"Autosave: module file deleted\"); if it can't be kept, nothing is deleted. The device's pictures stay.</li>"
            + "<li><b>Device Pack</b> import and Module Setup's <b>Import from</b> keep the file they replace in the <b>imported</b> folder inside the modules folder.</li>"
            + "<li><b>Start Fresh…</b> moves a damaged module file aside and keeps it as a copy.</li>"
            + "</ul>"
            + "<p>To put a deleted stick's setup on another stick, open Tools → Device Setup → <b>Device Library…</b>, pick its autosave and use <b>Copy to Another Stick…</b>. A saved setup can also be exported as a Device Pack and imported with Tools → Device Setup → <b>Device Pack</b>.</p>"),
        topic("Devices and Modules", "Hidden cards",
            "<p>Hiding a card only removes it from Home. It does not hide the device from Windows or games; use HidHide for that.</p>"
            + "<p>Hide a card with <b>Hide Card</b> in its right-click menu. To bring one back, right-click empty space on Home and open <b>Hidden Cards</b>: it lists each hidden card, and clicking one unhides it. <b>Unhide All Cards</b> brings them all back.</p>"),

        topic("Configuration", "Adding actions",
            "<p>The Configuration page lists the claimed inputs of one device and the actions on each. Open it by double-clicking a card, or View → <b>Configuration</b>. The arrows beside the title step to the previous or next device.</p>"
            + "<ul>"
            + "<li><b>Add Action</b> on an input opens the action editor beside it. Build the action and press <b>OK</b>. <b>Close pane after OK</b> closes the editor when OK succeeds.</li>"
            + "<li><b>Delete</b> removes an action. Leaving an input with unsaved editor changes asks first.</li>"
            + "<li><b>Undo</b> and <b>Redo</b> (beside Output, or Ctrl+Z and Ctrl+Y) step back through what OK and Delete changed, until you open another device or profile. They wait while an action is open in the editor.</li>"
            + "<li>Actions belong to the mode shown in <b>Mode</b> on the toolbar.</li>"
            + "<li><b>Move inputs with no actions to the end</b> lists them together under a <b>No actions</b> heading.</li>"
            + "<li>OK keeps the action in the profile; File → <b>Save Profile</b> writes it to disk.</li>"
            + "<li>While the profile runs the actions are locked (“Profile running: stop it to edit”). Run asks first about an action editor with changes.</li>"
            + "</ul>"
            + "<p>The <b>Keyboard</b> page lists the keys you added (<b>Add Key</b>). The editor below the list is a draft of the selected key: <b>OK</b> writes it, <b>Cancel</b> puts it back, and <b>Undo</b> and <b>Redo</b> step back through each OK (asking first when the draft has changes). Choosing another key, or deleting one, while the draft has changes asks first.</p>"
            + "<p>An output device opens its <b>Output View</b> instead: a live view of what its output module sends, labelled “View only — shows what the input modules' actions send.”</p>"),
        topic("Configuration", "Appearance",
            "<p>Appearance changes how a Configuration page or Output View looks, not what it does. The look is saved in that device's module file. The Xbox, Keyboard and OSC pages have no Appearance.</p>"
            + "<p><b>Appearance…</b> opens the panel. Changes show at once and are kept only with <b>Save Appearance</b>. <b>Reset Appearance</b> (red) restores the built-in look; <b>Copy Appearance from…</b> copies another device's look. Both still need Save Appearance. Closing the panel with unsaved changes asks first.</p>"
            + "<p>On the Configuration page the sections are <b>Screen</b> (background color or image), <b>Shown</b> (child rows, live bars, LED dots, summary), <b>List</b> and <b>Group</b> (spacing and group cards), <b>Parent Row</b> and <b>Child Row</b> (row size, padding, colors), <b>Text</b>, <b>Selection</b>, and <b>Editor</b> (the action editor beside a row). On the Output View they are <b>Screen</b>, <b>Layout</b>, <b>Pads</b>, <b>Meters</b>, <b>Buttons</b> and <b>Colors</b>. Use <b>Open All</b> / <b>Close All</b> to expand them.</p>"),

        topic("Actions", "Choosing an action",
            "<p><b>Add Action</b> lists the actions that suit the input type (axis, button, hat, or key). Container actions hold other actions; add the container first, then the actions inside it.</p>"
            + "<p>Options → Actions → Add Action Menu → <b>Actions offered</b> sets the order of that list and can hide actions you never use.</p>"),
        topic("Actions", "Map to vJoy",
            "<p>Sends the input to a vJoy axis, button, or hat. Pick the vJoy device (by output module name) and the output.</p>"
            + "<ul><li>Axis: <b>Absolute</b>, or <b>Relative</b> with <b>Speed</b> (the axis moves while the input is held off-center).</li>"
            + "<li>Button: <b>Invert activation</b>.</li>"
            + "<li>Only outputs claimed by the vJoy output module are sent. An unclaimed output shows <b>Output not claimed</b>.</li></ul>"),
        topic("Actions", "Map to Xbox",
            "<p>Sends the input to the virtual Xbox 360 controller (needs <b>ViGEmBus</b>). Every control is available; there is nothing to claim.</p>"
            + "<ul><li><b>Xbox</b>: the Xbox output module (Xbox 360 Controller).</li>"
            + "<li><b>Target</b>: any of the 22 controls — sticks, triggers, buttons, D-pad.</li>"
            + "<li>Trigger: <b>Full axis</b> (−1 → 0%, +1 → 100%) or <b>Upper half</b> (center → 0%).</li>"
            + "<li>Button: <b>Invert activation</b>.</li></ul>"),
        topic("Actions", "Map to Logical Device",
            "<p>Sends the input to a control on the Logical Device. Pick the logical control of the same type. Axis: <b>Absolute</b> or <b>Relative</b> with <b>Speed</b>. Button: <b>Invert activation</b>. The Logical Device page's <b>Assign Hardware</b> creates these actions for you.</p>"),
        topic("Actions", "Map to Keyboard",
            "<p>Holds the recorded keys while the input is held and releases them when it is released. Use <b>Record Keys</b> to set the <b>Key Combination</b>; modifiers are pressed first.</p>"),
        topic("Actions", "Map to Mouse",
            "<p><b>Mode</b>: <b>Button</b> clicks a recorded mouse button (Wheel Up/Down included, sent once per press). <b>Motion</b> moves the pointer: <b>Minimum speed</b>, <b>Maximum speed</b>, <b>Time to maximum speed</b>, and <b>Direction</b> for a button; <b>Control motion of</b> X Axis or Y Axis for an axis.</p>"
            + "<p>Mouse buttons are for sending only: they can be recorded here and in a macro, but a running profile never reads the mouse, so a mouse button can't fire actions.</p>"),
        topic("Actions", "Macro",
            "<p>Plays a list of steps: Joystick, Keyboard, Logical Device, Mouse Button, Mouse Motion, Pause, and vJoy. Add them with <b>Add Action</b>, or <b>Record Inputs</b> (choose Keyboard, Mouse, Axis, Button, Hat, and Timings, then Start/Stop Recording).</p>"
            + "<p>A <b>Joystick</b> step acts like the stick itself: it only does something for controls the stick's input module claims. Mouse buttons can be recorded as steps, but a mouse button is never an input of its own (see Map to Mouse).</p>"
            + "<ul><li><b>Repeat Mode</b>: Single, Count, Toggle, or Hold, with a delay between repeats.</li>"
            + "<li><b>Exclusive</b> waits for running macros, then blocks others; <b>Pre-Emptive</b> pauses them instead.</li></ul>"),
        topic("Actions", "Response Curve",
            "<p>Reshapes an axis before the actions after it. Choose <b>Piecewise Linear</b>, <b>Cubic Spline</b>, or <b>Cubic Bezier Spline</b>, drag the points or type <b>X</b>/<b>Y</b>, and set the <b>Deadzone</b>. <b>Invert Curve</b> flips it; <b>Symmetric</b> mirrors edits around the center.</p>"),
        topic("Actions", "Split Axis",
            "<p>Splits one axis at <b>Split axis at</b> into a lower/left part and an upper/right part, each with its own action list. Each part is rescaled to the full range.</p>"),
        topic("Actions", "Merge Axis",
            "<p>Combines two axes into one value for the actions in its <b>Actions</b> list. Pick or create a <b>Merge axis instance</b>, the <b>First axis</b> and <b>Second axis</b>, and the <b>Merge operation</b>: Average, Minimum, Maximum, Sum, Bidirectional, or Prefer Center.</p>"),
        topic("Actions", "Dual Axis Deadzone",
            "<p>Applies one deadzone to a pair of axes, such as a stick's X and Y: a circular <b>Inner</b> deadzone and a square <b>Outer</b> limit. Pick or create a <b>Deadzone instance</b> and the two axes; each axis has its own action list for the result.</p>"),
        topic("Actions", "Axis Delta",
            "<p>Turns axis movement into button presses. Each time the axis moves by <b>Change threshold</b>, it pulses the actions under <b>Positive change</b> or <b>Negative change</b>.</p>"),
        topic("Actions", "Condition",
            "<p>Runs one action list when its conditions are true and another when false. Choose <b>Any</b> or <b>All</b>, then <b>Add Condition</b>: Joystick, Keyboard, Current Input, vJoy, or Logical Device state.</p>"),
        topic("Actions", "Chain",
            "<p>Each press runs the next <b>Sequence</b> in turn (<b>Add Chain Sequence</b> adds one). After <b>Timeout (sec, 0 = never)</b> without a press it starts again at the first.</p>"),
        topic("Actions", "Double Tap",
            "<p>Separate actions for a single tap and a double tap within <b>Double-tap threshold (sec)</b>. <b>exclusive</b> waits to see if a second tap comes; <b>combined</b> runs the single-tap actions on every press.</p>"),
        topic("Actions", "Tempo",
            "<p>Separate actions for a <b>Short press</b> and a <b>Long press</b> (longer than <b>Long-press threshold (sec)</b>). <b>Activate on</b> press or release.</p>"),
        topic("Actions", "Smart Toggle",
            "<p>A quick press (released within <b>Hold time (sec)</b>) latches its actions on until the next press; a longer hold acts only while held.</p>"),
        topic("Actions", "Hat as Buttons",
            "<p>Gives each hat direction its own action list. <b>Button mode</b>: <b>4 way</b> or <b>8 way</b>.</p>"),
        topic("Actions", "Change Mode",
            "<p>Changes the running mode: <b>Switch</b> to a mode, <b>Previous</b> mode, <b>Unwind</b> one step, <b>Cycle</b> through a list, or <b>Temporary</b> (only while held).</p>"),
        topic("Actions", "Load Profile",
            "<p>Loads another profile file when the input fires. Set <b>Profile filename</b> or use <b>Select File</b>.</p>"),
        topic("Actions", "Pause and Resume",
            "<p><b>Pause</b>, <b>Resume</b>, or <b>Toggle</b> the processing of all actions.</p>"),
        topic("Actions", "Play Sound",
            "<p>Plays a WAV, MP3, or OGG file at the chosen <b>Volume</b>. Options → Actions → Play Sound sets what happens when sounds overlap.</p>"),
        topic("Actions", "Text to Speech",
            "<p>Speaks the text you type. It can be put on a button or a keyboard key. Choose <b>Interrupt</b>, <b>Queue Front</b>, or <b>Queue Back</b>, and set <b>Volume</b>, <b>Rate</b>, and <b>Pitch</b>. The voice is set in Options → Actions → Text to Speech.</p>"),
        topic("Actions", "Run Command",
            "<p>Starts a program: <b>Executable</b> plus <b>Arguments</b> (split on spaces; quote values that contain spaces). It runs with your own permissions.</p>"),
        topic("Actions", "Description",
            "<p>A note on the input. It does nothing when the input fires.</p>"),
        topic("Actions", "Reference",
            "<p>Reuses an existing action of the same input type. Pick it, then either share it (both inputs use the same action) or duplicate it (an independent copy).</p>"
            + "<p>A shared action's editor says <b>Shared with …</b> and names the other inputs: OK changes it for every input that uses it, and Undo puts it back for all of them.</p>"),

        topic("Logical Device", "Logical Device",
            "<p>The Logical Device is a virtual device inside the program. Its buttons, axes, and hats are fed by physical inputs (<b>Assign Hardware</b> or Map to Logical Device) and have actions of their own. Use it to combine several physical controls before sending them on.</p>"
            + "<p>Open it with <b>Logical Device</b> on the toolbar or Tools → Mapping → Logical Device. Controls are identified by type and number (Button 1, Axis 1, Hat 1). <b>Rename</b> adds your own name; <b>Hide system name</b> shows only yours; <b>Clear Name</b> removes it.</p>"
            + "<p>Editing is locked while the profile runs (“Profile running: stop it to edit”).</p>"),
        topic("Logical Device", "Controls, groups, and the menu",
            "<ul>"
            + "<li>Right-click empty space: <b>Appearance…</b>, then the sections <b>Add Inputs</b> (Buttons, Axes and Hats, each with a count up to 180 and <b>Add</b>), <b>Groups</b> (<b>New Group</b>) and <b>Order</b> (By System Name, By Your Name, Group Names A to Z). <b>Undo</b> and <b>Redo</b> sit beside the menu's title.</li>"
            + "<li>Right-click a control: <b>Add Action</b>, <b>Rename</b> and <b>Assign Hardware</b>, then <b>Row</b> (<b>Clear Name</b>, <b>Delete</b>) and <b>Group</b> (<b>Group as</b>, and <b>Move to</b> each group). Shift-click selects several; the menu's title then counts them.</li>"
            + "<li>Right-click a group: <b>Rename Group</b>, then <b>Groups</b> → <b>Move Group Up</b>, <b>Move Group Down</b> or <b>Delete Group</b> (its controls go to Ungrouped). Click a group header to fold it.</li>"
            + "<li>Drag a control by its grey handle onto another control (top half = before, bottom half = after) or onto a group header. Drag a header to move the group.</li>"
            + "<li><b>Find</b> filters by name, type, Ungrouped, <b>No hardware writer</b>, or <b>No actions in this mode</b>; <b>Clear</b> resets it.</li>"
            + "<li>Undo/Redo: Ctrl+Z and Ctrl+Y (or Ctrl+Shift+Z).</li>"
            + "</ul>"),
        topic("Logical Device", "Assign hardware and actions",
            "<p><b>Assign Hardware</b> lists claimed physical controls of the same type (keyboard keys for a button; OSC too). Tick a control to add a Map to Logical Device action to it in the current mode; untick to remove that link. <b>Search</b> filters the list.</p>"
            + "<p>The control then shows <b>Written by</b> with the source. On that line an axis has Absolute/Relative and a scale; a button has <b>Invert</b>.</p>"
            + "<p><b>Add Action</b> opens the action editor beside the list, the same editor as on the Configuration page. Click an action row to edit it; right-click it to <b>Open</b> or <b>Delete</b> it.</p>"),
        topic("Logical Device", "Sending to Xbox or vJoy",
            "<p>A Logical Device control sends on to the Xbox controller or vJoy through an action, not through Assign Hardware. Assign Hardware only picks what feeds the control; it never lists outputs.</p>"
            + "<ol>"
            + "<li>Right-click the control (for example Hat 1) and choose <b>Add Action</b>.</li>"
            + "<li>Choose <b>Map to Xbox</b> (or <b>Map to vJoy</b>).</li>"
            + "<li>Pick the Target (a hat can drive the D-pad, a button, or a stick) and press <b>OK</b>.</li>"
            + "</ol>"
            + "<p>The whole path: physical control → Assign Hardware → Logical Device control → Map to Xbox → Xbox 360 Controller. Map to Xbox needs <b>ViGEmBus</b>; see <b>Xbox output module</b>.</p>"
            + "<p>Map to Xbox not in the list? Options → Actions → Add Action Menu → <b>Actions offered</b> may hide it.</p>"),
        topic("Logical Device", "Appearance",
            "<p><b>Appearance…</b> (also in the menu) opens the Logical Device appearance panel. Its sections — Shown, Handles, List, Group, Parent Row, Action Row, Text, Selection — change how the page looks. Changes are kept with <b>Save Appearance</b> (saved for this page, in the program settings); <b>Reset Appearance</b> restores the built-in look.</p>"),
        topic("Modes", "Modes",
            "<p>A mode is a set of actions. The same button can do different things in different modes. A mode can <b>inherit</b> from a parent: anything it does not map itself uses the parent's actions.</p>"
            + "<ul>"
            + "<li><b>Manage Modes</b> (toolbar, or Tools → Mapping): add, rename, and remove modes, and set <b>Inherits from</b>. Deleting a mode removes its actions too; <b>Undo Delete Mode</b> brings back the mode deleted last, with its actions, while the same profile is open.</li>"
            + "<li><b>Mode</b> on the toolbar picks the mode you edit and the mode Run starts in; while running it shows the mode that runs, and picking another mode there switches the running profile to it.</li>"
            + "<li>The <b>Change Mode</b> action switches mode while the profile runs.</li>"
            + "<li>Modes are part of the profile; save the profile to keep them.</li>"
            + "</ul>"),
        topic("Tools", "Button Map",
            "<p>Button Map is a picture of a device with a chip on each control. A press lights its chip, and chips can show what each control does in the profile. Moving a chip changes only the picture, never the actions.</p>"
            + "<p>Open it from a device card's right-click menu, the toolbar, or Tools → Mapping → <b>Button Map</b>. It has its own guide: <b>F1</b> or Help → Button Map Guide in the Button Map window explains everything it does.</p>"),
        topic("Tools", "Viewers",
            "<p>The viewers show live values; they change nothing. Open them from the toolbar, Tools → Viewers, or a card's menu.</p>"
            + "<ul>"
            + "<li><b>vJoy Viewer</b>: each physical device beside the vJoy device it drives. The physical side shows claimed inputs; the vJoy side shows what the vJoy output module sent (claimed outputs, while the profile runs).</li>"
            + "<li><b>Xbox Viewer</b>: the Xbox 360 Controller with every control, and which inputs drive it. The ViGEmBus check is at its top.</li>"
            + "</ul>"),
        topic("Tools", "Calibration",
            "<p>Sets the center and the ends of each axis so its full travel is used. It is stored in the device's input module and applied before any action sees the axis.</p>"
            + "<p>Tools → Device Setup → <b>Calibration</b>, or a card's menu. Choose the input module. Every axis is listed; one the input module doesn't claim is marked <b>(not claimed)</b>. For each axis, move the stick and use <b>Calibrate Center</b> and <b>Calibrate Extrema</b>, or type the values. <b>Undo</b> and <b>Redo</b> (Ctrl+Z, Ctrl+Y) step back through each axis's changes (a value typed, Reset, a calibration started) until you choose another module. An axis shows <b>Not saved</b> until you press its save button. Leaving with unsaved axes asks first.</p>"),
        topic("Tools", "Device Information",
            "<p>Tools → Device Setup → <b>Device Information</b> lists every device Windows reports: Name, Axes, Buttons, Hats, VID, PID, Joystick ID, and Device ID. Use it to tell identical devices apart.</p>"),
        topic("Tools", "History",
            "<p><b>Tools → History</b> lists every saved change, newest first: profile saves (each input whose actions changed, and other parts such as modes and the Logical Device), module files (checked controls and names, calibration, Appearance, the Button Map), and the settings you choose in Options, HidHide and OSC. Window sizes and places, and the Button Map's zoom, guides and print area, aren't kept.</p>"
            + "<p>Pick a change to see it <b>Before</b> and <b>After</b>. <b>Show</b> narrows the list to one kind; <b>Search</b> finds a device, input or file. <b>History</b> in an editor opens it for just what that editor shows: on the Configuration page (the selected input), on a Logical Device control's menu, in Module Setup, in the Button Map's File menu, and in Options.</p>"
            + "<p><b>Restore Before</b> or <b>Restore After</b> puts that version back (it asks first). An input's actions go back into the open profile, unsaved: open that profile first, and save it to keep them; the restore shows in the History at that Save Profile. A module file, with its pictures, and settings are saved at once, and the restore is a new change in the History at once. A whole profile (on its save's entry) is written as a copy next to the profile, to open with File → Load Profile…; it stays next to the profile until you delete it, and is not a change in the History.</p>"
            + "<p>The history is kept in the <b>history</b> folder of the data folder. Options → General → History sets how many days it keeps changes (90) and how big each of its files may grow (20 MB); the oldest go first. Both are checked when the program starts. The whole profile is kept for the newest 20 saves of each profile.</p>"),
        topic("Tools", "Auto Mapper",
            "<p>Creates Map to vJoy actions in one step: each claimed input of an input module gets an action to the same number on a vJoy output module.</p>"
            + "<ol>"
            + "<li>Tools → Mapping → <b>Auto Mapper</b> (or a card's menu).</li>"
            + "<li>Tick the input modules and output modules. The first ticked input goes to the first ticked output, the second to the second, and so on.</li>"
            + "<li>Choose <b>Select Mode</b> (it starts on the toolbar's mode), then <b>Create 1:1 Actions</b>. The result names the mode the actions went into, and says so when the toolbar shows another mode.</li>"
            + "</ol>"
            + "<ul>"
            + "<li>Only outputs the output module claims are used. Skipped controls are listed with the reason (not claimed, not on the vJoy device, or already used by another input in this mode). When the output module claims none of them, the result says so.</li>"
            + "<li><b>Also claim the matching outputs on the output module</b> (off by default) claims what the new actions need first.</li>"
            + "<li><b>Overwrite used inputs</b> replaces existing actions on those inputs; off keeps them.</li>"
            + "<li><b>Combine onto selected outputs</b> reuses the outputs when you tick more inputs than outputs.</li>"
            + "</ul>"),
        topic("Tools", "Device Library",
            "<p>The <b>Device Library</b> keeps every device the program has known: sticks plugged in now (<b>Connected</b>), sticks set up here but unplugged, and sticks from someone else's Device Pack (<b>Not connected</b>), and deleted sticks (<b>Deleted</b>). Open it with the <b>Device Library…</b> button on Home or Tools → Device Setup → <b>Device Library…</b>. A card's menu opens it on that stick.</p>"
            + "<ul>"
            + "<li><b>Saved setups</b>: stored copies of a device's settings and bindings, each with a name and a description. Open a device's row to see them, newest first. <b>Save to Device Library…</b> keeps one of your own: the module file now, and the bindings from the profiles you tick.</li>"
            + "<li><b>Autosaves</b>: the program keeps one by itself before anything replaces or removes a stick's settings: Delete Device, Delete File, Copy, Swap, Change vJoy Output and a Device Pack import. Each is named for why it was kept (for example \"Autosave: stick deleted\"). The newest 10 per stick are kept (Device Library Settings); renaming or describing one makes it yours, and yours are never removed that way.</li>"
            + "<li><b>Copy to Another Stick…</b> (on a card: <b>Copy Setup to Another Stick…</b>) puts a saved setup, or a device's settings, on a stick plugged in now: tick what to copy (Setup, Button Map, Appearance, Calibration, Bindings), the profiles and the modes. What the target stick doesn't have is listed and left out. The source never changes. A stick never plugged in here can be copied from, never to.</li>"
            + "<li><b>Swap with Another Stick…</b>: two sticks plugged in now trade the ticked parts. References inside actions and script variables swap too. The Keyboard, Logical Device, OSC and Xbox can't be swapped.</li>"
            + "<li><b>Change vJoy Output…</b>: a stick keeps its bindings; only the vJoy they send to changes. It can also move the stick that used that vJoy the other way. Bindings to an output the vJoy's output module doesn't claim, and macros and scripts that name a vJoy, are listed for you to check.</li>"
            + "<li><b>Undo</b> (the Device Library's Edit menu) puts the last Copy, Swap or Change vJoy Output back from the autosaves it kept, even after a restart.</li>"
            + "</ul>"
            + "<p>The open profile is changed in memory: save it to keep the change. Ticked profiles that aren't open are changed and saved on disk, each save a History entry. The library's folder is chosen in Device Library Settings.</p>"
            + "<p>The Device Library has its own guide: in its window, choose Help › <b>Device Library Guide</b> or press <b>F1</b>.</p>"),
        topic("Tools", "HidHide",
            "<p>HidHide hides physical controllers from games so they only see vJoy or Xbox. Gremlin-Platforms always sees them. The HidHide driver is a separate install (<b>Get HidHide</b>).</p>"
            + "<p>Tools → Device Setup → <b>HidHide</b>:</p>"
            + "<ul>"
            + "<li><b>Gremlin-Platforms controls HidHide</b> lets this program write HidHide's settings. <b>HidHide Enabled</b> turns hiding on. <b>Automatically Start</b> applies both each time the program starts.</li>"
            + "<li>Tick the devices to hide. <b>Gaming devices only</b> shortens the list. A hidden device is dimmed and marked HIDDEN.</li>"
            + "<li><b>Allow list</b>: only the listed programs see hidden devices. <b>Block list</b>: the listed programs do not. Add programs with <b>Add Program</b>.</li>"
            + "<li><b>Test HidHide</b> opens the Windows Game Controllers panel. With Allow list on, a hidden device should be missing there. Reopen the panel after each change.</li>"
            + "</ul>"
            + "<p>All switches start off on a new install.</p>"),
        topic("Tools", "Live Log Reader",
            "<p>Debug → <b>Live Log Reader</b> has three tabs.</p>"
            + "<ul>"
            + "<li><b>Config</b> follows the program's activity log (logs.txt): which profiles, modules and settings files were read and saved, and when. Use it to check how a file loads.</li>"
            + "<li><b>Debug</b> shows the diagnostic logs in the Logs folder: <b>System</b> (system.log: errors, warnings, blocked outputs), <b>Scripts</b> (user.log), <b>Events</b> (event.log), <b>All logs</b> (every file together in time order, each line tagged with its log: [System], [Scripts], [Events], [Qt]) and <b>Qt</b> (qt.log: Qt's own messages, such as QML warnings, each with the time; also shown in the console when the program is started from one; moved to qt.log.1 at start-up once over 1 MB, at most 5 MB a session). <b>Show</b> picks the lowest level shown, <b>Find</b> narrows it to entries with that text, and warnings and errors are in color. For a large file only the last 512 KB is shown at first; <b>Load Whole File</b> reads all of it. <b>Clear Log</b> empties the shown file (it asks first). What gets written is the <b>Diagnostic logs</b> level at the bottom of the tab (the same setting as Options → General → Diagnostics; changing either changes both, at once). <b>Show</b> only filters what is already in the file: a level the program is not writing has no lines to show.</li>"
            + "<li><b>Live</b> (the red button on the Debug tab) catches every line the program logs, as it happens, at full detail, whatever the Diagnostic logs level (the files keep that level). It keeps what is on screen and adds a <i>Live started</i> line; new lines are tagged [System], [Scripts] or [Events], and <b>Log</b> → <b>All logs</b> shows them together. Show and Find work as always and can be changed while Live runs. Tick <b>Start empty</b> to clear the view when Live starts. <b>Clear View</b> empties the view (never a file); <b>Save Feed…</b> saves it to a text file. Stopping Live leaves the session on screen; <b>Show Log File</b> goes back to the file.</li>"
            + "<li><b>Input Monitor</b>: click <b>Monitor</b> and use your devices with the profile running. Each input shows as it happens: the device and input, its value, the mode, and the actions it ran (Map to vJoy and Map to Xbox say where they send it), or <i>no actions</i> (untick <b>Inputs with no actions</b> to hide those). An axis shows about ten values a second. Nothing is written to a file.</li>"
            + "</ul>"
            + "<p><b>Red debug mode</b>: while Diagnostic logs is <b>ALL</b> or Live runs, every window has a red frame and a <b>DEBUG</b> badge at the top (click it to open the Live Log Reader). Button Map exports and prints never include it. Live and the Input Monitor stop when the Live Log Reader closes.</p>"),

        topic("Options and Profile", "Options",
            "<p>Tools → <b>Options</b> (or <b>Options</b> on the toolbar). Program settings, not stored in the profile; the profile's own are on its <b>Profile Settings</b> tab.</p>"
            + "<p>Pick a section on the left, or type in <b>Search options</b> to find a setting in any section.</p>"
            + "<ul>"
            + "<li><b>General</b>: <b>Startup and Tray</b> (<b>Check for updates</b>; <b>Minimize to tray</b>, where minimizing or closing the window keeps the program running in the tray, exit from File → Exit or the tray menu; and <b>HidHide</b>, a pointer: to turn HidHide on each time the program starts, use <b>Automatically Start</b> in Tools → Device Setup → HidHide), <b>Devices</b> (<b>Device change behavior</b>: Stop, Ignore, or Reload; <b>Refresh axes when Run starts</b> and on mode change; an axis not moved since the program started is sent as center until it moves), <b>Diagnostics</b> (<b>Diagnostic logs</b>, <b>Log When Not Responding</b>) and <b>History</b> (<b>Days to keep changes</b>, <b>Largest history file (MB)</b>).</li>"
            + "<li><b>Interface</b>: <b>Display</b> (Dark mode, UI scale, Ignore Windows display scaling) and <b>Inputs</b> (Input names, Input highlighting, which stays on the device page you have open, and Action details).</li>"
            + "<li><b>Actions</b>: the <b>Add Action Menu</b> (which actions it offers and their order), then Macro, Change Mode, Double Tap, Smart Toggle, Tempo, Axis Delta, Play Sound and Text to Speech.</li>"
            + "<li><b>Profiles</b>: <b>Auto-load</b>: Load profiles automatically when a chosen program starts, the programs and their profiles, and Keep running when the program loses focus.</li>"
            + "<li><b>Home</b>: <b>Cards</b>: Compact view, Show devices without a module, Keep last value after release, and <b>Reset All Card Sizes</b>.</li>"
            + "<li><b>OSC</b>: <b>Connection</b> (Enabled, Input host and port, Output address) and <b>Messages</b> (auto-release of address-only messages, the delay presets, and treating address-only messages as 1.0).</li>"
            + "<li><b>Folders</b>: the data folder, and the profiles, modules, scripts, export, logs, history and plugins folders (the Device Library's folder is in Device Library Settings). <b>Select</b> picks another folder; <b>Reset</b> puts the default back.</li>"
            + "</ul>"
            + "<p>The Button Map's settings are in the Button Map: Edit → <b>Button Map Options…</b>.</p>"),
        topic("Options and Profile", "Profile Settings",
            "<p>View → <b>Profile Settings</b>. Stored in the profile; save the profile to keep them.</p>"
            + "<ul>"
            + "<li><b>Startup Mode</b>: the mode the profile is in when it is loaded, including when a program auto-loads it. <b>Use Heuristic</b> picks the first mode, in alphabetical order, that has no parent; <b>Last Active</b> picks the mode the profile was using the last time it ran; a mode by name picks that mode. <b>Run</b> starts in the mode shown in the toolbar, so change the toolbar mode to start somewhere else.</li>"
            + "<li><b>Macro Default Delay</b>: the pause between macro steps.</li>"
            + "<li><b>vJoy Behavior</b>: treat each vJoy device as an output (default) or as an input.</li>"
            + "<li><b>vJoy Initial Values</b>: axis values set when the profile starts.</li>"
            + "</ul>"),
        topic("Options and Profile", "Scripts",
            "<p>View → <b>Scripts</b> adds Python scripts to the profile. <b>Add Script</b> picks a .py file; each script can be renamed and its variables set on that page. Scripts are saved with the profile. A script's <b>vjoy</b> object can only use outputs the vJoy output modules claim.</p>"),
        topic("Troubleshooting", "Nothing reaches vJoy",
            "<ul>"
            + "<li>Is the profile running? The toolbar button should read <b>Stop</b> and the bottom bar <b>Running</b>.</li>"
            + "<li>Is the input <b>claimed</b> in its input module? Unclaimed inputs are ignored.</li>"
            + "<li>Does the wire show <b>(not claimed)</b>? Claim that output in Output Module Setup.</li>"
            + "<li>Is the action in the running <b>Mode</b> (on the toolbar)? Only that mode's actions (and its parents') run.</li>"
            + "<li><b>system.log</b> in the Logs folder (Options → Folders) notes each blocked output once.</li>"
            + "</ul>"),
        topic("Troubleshooting", "Xbox does nothing",
            "<ul>"
            + "<li>Open the Xbox page or the Xbox Viewer: the check at the top must say <b>ViGEmBus driver found</b>. If not, it says what to do.</li>"
            + "<li>The pad exists only while the profile runs and after a Map to Xbox action has sent.</li>"
            + "<li>Check the action uses <b>Map to Xbox</b> with <b>Xbox 360 Controller</b> and the right Target.</li>"
            + "</ul>"),
        topic("Troubleshooting", "A key binding does not fire",
            "<p>Open Input Module Setup on <b>Keyboard</b> and check the key is claimed. Once you save a keyboard choice, only claimed keys fire.</p>"),
        topic("Troubleshooting", "A device is missing or seen twice",
            "<ul>"
            + "<li>Not on Home: right-click empty space on Home and check <b>Hidden Cards</b>.</li>"
            + "<li>A game sees both the physical stick and vJoy: hide the physical stick with <b>HidHide</b>.</li>"
            + "<li>Bindings belong to a device that was replaced: open the <b>Device Library</b> and use <b>Copy to Another Stick…</b> from the old stick (or <b>Swap with Another Stick…</b> when both are plugged in).</li>"
            + "</ul>"),
        topic("Troubleshooting", "Save Diagnostics",
            "<p>Help → <b>Save Diagnostics…</b> (or <b>Save Diagnostics…</b> on the Live Log Reader's Debug tab) saves one zip to send with a problem report: the program's logs, its settings, the device list (names, ids, kinds, connected) and the program and Windows versions. <b>Save…</b> asks where, starting on the Desktop. The open profile is left out unless you tick <b>Include the open profile</b>. Your user name in folder paths is replaced by &lt;user&gt;. When it is done it says where the zip went; if it can't be written it says which file, which folder and why.</p>")
    ]
}

// The Button Map's own guide (its Help menu and F1): only the Button Map.
function buttonMapTopics() {
    return [
        topic("Getting started", "Overview",
            "<p>Button Map is a picture of one device with a chip on each control. While the profile runs, a press lights its chip, and the chip shows where the control's wire goes (shown as <b>(not claimed)</b> when the output is not claimed). The line from a chip to its control on the photo is its <b>leader</b>. Chips are layout only: moving, renaming or deleting one never changes the actions in the profile.</p>"
            + "<p>Pick the device from the <b>File</b> menu. Before you edit, the map is live: hover a chip to see which control it is, and drag with the left or middle button to pan.</p>"
            + "<p><b>File → Edit Mapping</b> starts editing. The pool beside the map lists the device's controls; drag a chip from it onto the photo, and filter it by name. <b>File → Save</b> (Ctrl+S) writes the layout to the device's module file; <b>File → Cancel</b> leaves without saving. Closing with unsaved edits asks first.</p>"
            + "<p>The menus show only what you can use right now, with shortcuts beside their commands. <b>View → Command Palette</b> (Ctrl+K) lists every menu command you can use now: type part of a name and press Enter.</p>"
            + "<p>Four <b>tool rows</b> frame the map: one under the menus, one under the map, and one down each side between them (their tabs read up the left one and down the right one). They hold the tools as tabs (Chips, Properties, Layers, Command Palette, Print Area, and Options on the top row). A tab opens its tool and hides it again; an open tool's panel is joined to its tab, opening from where the tab sits (under a top-row tab, over a bottom-row one, beside a side-row one) and moving with it. The Chips pool runs the length of the map along its row (as wide as the map, or as tall from a side row), its tab joining it where it sits; Print Area has no panel, and its tab lights up while the frame shows. <b>Pin</b> keeps the tool open when you click the map; unpinned, it hides. <b>Lock</b> stops it being moved or resized. Unlocked, drag a tab anywhere along its row or onto another row (the row it would land on lights up); it snaps to the edges, the middle and a small grid, and its panel goes with it. Unlocked, a panel's edge facing the map, its far edge along the row and their corner resize it; the Options panel starts as large as its settings need. The panel opened or clicked last is in front. Any tool with a panel can <b>float</b>: drag its tab off every row onto the map (or right-click the tab → <b>Float</b>). A floating panel sits over the map where you put it, with a title bar showing its name, pin, lock and close; its tab stays on its row, with a small floating mark, and shows or hides it. Unlocked, drag the title bar to move it and any edge or corner to resize it; drop the title bar on a tool row to dock it there, or double-click the title bar (or right-click its tab → <b>Dock</b>) to put it back on its row. Closing it hides it; it floats in the same place next time. Print Area has no panel and never floats; the Command Palette floats where it was let go. <b>View → Reset Tool Rows</b> puts every tab back on the row it starts on (Options on the top one, the rest on the bottom), docks every panel, and gives every panel its first size. All of this is kept for next time.</p>"
            + "<p>Most of this guide is about editing. <b>Help → Button Map Guide</b> or <b>F1</b> opens it.</p>"),
        topic("Getting started", "File menu and export",
            "<p>The Button Map's menus show only what you can use at that moment: before a device is chosen File → <b>Device</b> lists the devices, and the editing items appear once you choose File → Edit Mapping. The Photo menu works while editing.</p>"
            + "<ul>"
            + "<li><b>Edit Mapping</b>, <b>Save</b> (Ctrl+S), <b>Cancel</b>.</li>"
            + "<li><b>Reset Layout</b> clears everything from the map: chips go back to the pool, and leaders, hotspots, drawings, text boxes, pictures and tables are removed (it asks first). Actions are not changed. Ctrl+Z brings the layout back; save afterwards to make the empty map the live one.</li>"
            + "<li><b>Fit to Photo Frame</b> shrinks an older, oversized layout to the photo.</li>"
            + "<li>Photo → <b>Choose Photo…</b> uses another picture as the photo; <b>Clear Photo</b> removes the photo. Undo puts the previous photo back, and Cancel puts back the photo you started with.</li>"
            + "<li><b>Print &amp; Export…</b> (Ctrl+P) has every print and export in one place: a preview of the page as it will come out, the paper (Letter, Legal, Tabloid, A3, A4, A5), its orientation, the margins, the background, and under <b>Custom</b> the scale and <b>Freeform (As Drawn)</b>, and the buttons <b>Print…</b>, <b>Export PDF…</b>, <b>Export PNG…</b> and <b>Export JPG…</b>. The settings are kept with the map and are the same for every print and export.</li>"
            + "<li><b>Scale</b>: the size in pixels of every export and print. 100% is the photo's own size, pixel for pixel (without a photo, the page 1920 pixels wide). The window shows the pixels, and on a paper how many dots an inch they print at: the print area fills the paper inside its margins. <b>Freeform (As Drawn)</b> sets no paper: the print area keeps whatever shape you draw (Paper, Orientation and Margins grey out), and a PDF gets a page of that shape, at 96 pixels an inch. The size of the window or the screen's scale makes no difference.</li>"
            + "<li>The preview follows the print area as it moves or is resized on the map, and sharpens a moment after it stops. In the preview, drag the picture to move the print area (the picture follows the hand) and turn the mouse wheel to zoom: in makes the print area smaller, out larger, about the pointer, keeping its shape. The print area on the map follows, and is kept with the map. Not while the print area is locked.</li>"
            + "<li><b>Background</b>: <b>Dark</b>, as on screen, or <b>Light</b>, a white page where every color has its lightness turned over, so dark chips come out light with dark text and a dark red becomes a light red, while the photo stays as it is. The screen does not change.</li>"
            + "<li><b>Print Area</b>: every export and print takes only this part of the page. <b>Alt+drag</b> on an empty part of the map (or <b>Edit → Set Print Area</b>, then drag) draws it; <b>Print Area</b> on a tool row (or <b>View → Print Area</b>) shows it while editing (never on the live map), everything outside dimmed, with handles to resize it and its border to move it. With a paper chosen it keeps the paper's shape, so what it frames fills the page. <b>Edit → Clear Print Area</b> goes back to the whole page. A print area drawn or changed while editing waits for Save: Undo steps through it and Cancel takes it back.</li>"
            + "<li>Every print and export takes the print area, whatever the zoom. Selection marks, handles, guides and the grid are left off, and so are hidden items. Lines and text are drawn at the export's size, not enlarged. A PDF goes on the chosen paper, inside its margins.</li>"
            + "<li><b>Edit → Copy Button Map from Device</b> lists the other devices that have a Button Map. Pick one to replace this map's chips, leaders and drawings with it, mirrored left to right if you like (for the other hand's stick). This device's photo stays; one Undo puts the old layout back, mirrored or not, and nothing is saved until you save.</li>"
            + "<li><b>Templates</b>: <b>Save Layout as Template…</b> keeps this map's chips, leaders and drawings under a name; <b>Apply Template</b> puts one on any device (it asks first; Undo puts the old layout back); <b>Manage Templates…</b> renames, deletes, exports a template to a file to share, and imports one. A template keeps where its pictures are, not the picture files themselves.</li>"
            + "<li><b>Print…</b> prints the print area as Export draws it, on the chosen paper and margins. Windows' printer dialog comes first. With <b>Freeform (As Drawn)</b> it goes on the paper chosen in the printer dialog, turned to landscape when wider than tall.</li>"
            + "<li><b>Close</b>. The last row shows the device's module file.</li>"
            + "</ul>"),
        topic("Getting started", "Button Map Options",
            "<p><b>Options</b> on the top tool row, or <b>Edit → Button Map Options…</b>, opens the Button Map's settings in a panel joined to its tab (they are not in the program's main Options), as large as its settings need. The groups are down its left; the chosen group's settings sit on the right, one line each, with each setting's description on its ⓘ. Changes apply and are kept at once, and the pane opens on the group you used last. Like every tool it can be pinned, locked, moved with its tab (to the other row too), or resized by its edges. They apply to every device.</p>"
            + "<ul>"
            + "<li><b>Labels</b>: <b>Chip text</b>, <b>Description first</b>, <b>Several actions</b> and <b>No actions</b> (see Action labels).</li>"
            + "<li><b>Editing</b>: <b>Mirror pictures</b>, whether Mirror Layout and Copy Button Map from Device also flip pictures (off: pictures only move, so text in them still reads); <b>Undo steps</b>, how far Undo can go back; <b>Rotate snap</b>, the degrees per step when Shift is held while turning an item or drawing a line; <b>Press to find</b> and <b>Find axes</b> (see Selecting, undo and keys).</li>"
            + "<li><b>Autosave</b>: <b>Autosave</b> keeps a recovery copy of unsaved edits every <b>Seconds between recovery copies</b> while you edit. If the program closes before you save, opening the device again offers <b>Restore</b> (the edits open for editing; save to keep them), <b>Discard</b>, or <b>Not now</b>. Save and Discard remove the copy.</li>"
            + "<li><b>What Save writes</b>: while editing, the map, the photo, the print area, the print settings and the guides are written to the module file only by Save; Cancel takes them back. The view (zoom and pan), the grid settings and Show Guides are kept with the device's map at once, also while editing, and Cancel leaves them. Outside editing, Print &amp; Export's settings are kept at once. Rulers is a setting of the program, kept at once.</li>"
            + "<li><b>View</b>: <b>Zoom speed</b>, how fast the mouse wheel zooms; <b>Rulers</b>, shown or not (also View → Rulers).</li>"
            + "<li><b>Colors</b>: <b>Recent colors</b>, how many the color picker keeps.</li>"
            + "<li><b>Library</b>: the saved styles and layout templates, to rename or delete.</li>"
            + "</ul>"),
        topic("The map", "View, zoom and grid",
            "<p>Scroll to zoom (50% to 600%); the <b>Zoom speed</b> setting in Button Map Options sets how fast. Drag with the middle button to pan. View → <b>Reset View (View 100%)</b> or Ctrl+0 returns to 100%. View → <b>Zoom to Fit Page</b> (Ctrl+1) shows the whole page; View → <b>Zoom to Selection</b> (Ctrl+2) fills the view with what is selected.</p>"
            + "<p>View → <b>Grid</b>: <b>Show Grid</b>, <b>Snap to Grid</b>, <b>Snap to Entities</b> (edges and middles of other items, with guide lines), and the grid <b>Size</b>. Hold <b>Alt</b> while dragging to skip snapping.</p>"
            + "<p>The view (zoom and pan) and the grid settings are kept with the device's map at once, while editing too; Cancel leaves them, and History doesn't list them.</p>"
            + "<p>View → <b>Layers</b> and View → <b>Properties</b> show the two side panels (see Layers and Properties panel).</p>"),
        topic("The map", "Rulers and guides",
            "<p>View → <b>Rulers</b> shows rulers along the top and left of the map while editing, marked in percent of the page (as the Properties panel measures).</p>"
            + "<p>Drag down out of the top ruler for a horizontal guide, or right out of the left ruler for a vertical one. Items you move snap their edges or middles to a guide before anything else, and points (drawing, hotspots, line ends) snap to guides too; Alt skips snapping. Drag a guide to move it; drop it on its ruler or off the page to remove it.</p>"
            + "<p>Guides are kept with the device's map. Guides added, moved or removed while editing wait for Save: Undo steps through them and Cancel takes them back. View → <b>Show Guides</b> hides and shows them, and View → <b>Clear Guides</b> removes them all. They never print or export.</p>"),
        topic("The map", "The photo",
            "<p>The photo is the device picture under everything else. Photo → <b>Move Photo</b> drags it (Esc leaves the tool); <b>Adjust Photo…</b> sets its size, offset and rotation; <b>Reset Photo</b> puts it back.</p>"
            + "<p><b>Adjust Photo…</b> also sets its <b>Look</b>, so the chips stand out against a busy picture: <b>Brightness</b> and <b>Contrast</b> (either way), <b>Greyscale</b> and <b>Fade</b>. <b>Reset Look</b> puts them back; Reset photo leaves the look alone. The look is saved with the layout, shows on the live map and in exports, and Undo steps through it.</p>"
            + "<p>Photo → <b>Choose Photo…</b> uses another picture; <b>Clear Photo</b> removes the photo. Both are steps for Undo, and Cancel puts back the photo you started with. The photo has its own row at the bottom of the Layers panel, so it can be hidden or locked like any item.</p>"),
        topic("The map", "Selecting, undo and keys",
            "<p><b>Press to find</b>: while editing, press a button or hat on the device and its chip is selected and scrolled into view (a group member selects its group). A control that is not on the map yet is shown in the pool, filtered by name; a hidden one is pointed to the Layers panel. Turn it off, or let a pushed axis count too, in Button Map Options.</p>"
            + "<p>Click selects; Shift-click or Ctrl-click adds or removes; drag on empty space for a box selection. Arrow keys nudge the selection; Shift+Arrow nudges by the grid size. Undo and Redo are also at the top of every right-click menu.</p>"
            + "<ul>"
            + "<li><b>Ctrl+S</b> Save</li>"
            + "<li><b>Ctrl+Z</b> Undo; <b>Ctrl+Y</b> or <b>Ctrl+Shift+Z</b> Redo</li>"
            + "<li><b>Ctrl+D</b> Duplicate; <b>Ctrl+C</b> Copy; <b>Ctrl+V</b> Paste (a picture copied after the last chip copy pastes as a picture); <b>Ctrl+Shift+V</b> Paste picture</li>"
            + "<li><b>Ctrl+G</b> Group; <b>Ctrl+Shift+G</b> Break group</li>"
            + "<li><b>Ctrl+L</b> Lock or unlock the selection; <b>Ctrl+Shift+L</b> Unlock everything</li>"
            + "<li><b>Delete</b> or <b>Backspace</b> Remove the selection</li>"
            + "<li><b>Ctrl+1</b> Zoom to fit page; <b>Ctrl+2</b> Zoom to selection</li>"
            + "<li><b>Ctrl+P</b> Print &amp; Export</li>"
            + "<li><b>Ctrl+0</b> Reset view to 100%; <b>Alt</b> while dragging: no snapping; <b>Shift</b> while drawing: keep proportions or 15° steps</li>"
            + "<li><b>Esc</b> Cancel the tool, crop, rename or group edit</li>"
            + "<li><b>Ctrl+K</b> Command palette</li>"
            + "<li><b>Ctrl+F</b> Search layers (opens Layers)</li>"
            + "<li><b>F1</b> This guide</li>"
            + "</ul>"),
        topic("Chips", "Chips",
            "<p>A chip shows a control's name (Button 10, Axis 1, Hat 1) or its friendly name. Drag one from the pool onto the photo; drag it again to move it. Click a chip to select it; double-click it to edit its name. Tick <b>Chip only</b> beside the pool filter (also in Button Map Options) to place chips on their own, with no leader and no hotspot; add them later from the chip's menu (Leader → Add Leader, Hotspot → Hide Hotspot).</p>"
            + "<p>Right-click a chip for:</p>"
            + "<ul>"
            + "<li><b>Rename</b> and <b>Delete Chip</b> (back to the pool; Delete or Backspace does the same).</li>"
            + "<li>Or drag a chip back onto the pool: the pool lights up, and letting go takes the chip off the map. With several chips selected, they all go; a group goes whole, and while a group is being edited the member you drag leaves it. Locked chips stay. Undo brings them back.</li>"
            + "<li><b>Chip Style</b>: font size, chip size, <b>Round</b>, <b>Square</b> or <b>Circle</b>, Filled or Hollow, and <b>Highlight on press</b>. A <b>Circle</b> is always a true circle: it grows to fit its label (<b>Circle Size</b> → <b>Auto</b>), or keeps a size you choose and makes the text smaller to fit.</li>"
            + "<li><b>Colors</b>: Fill Color…, Outline Color… and Text Color…, and <b>Pressed Fill…</b>, <b>Pressed Outline…</b> and <b>Pressed Text…</b> used while the control is held.</li>"
            + "<li><b>Hotspot</b> and <b>Leader Ends</b> (see Hotspots and leaders), <b>Arrange</b> (stacking, Lock, Hide).</li>"
            + "</ul>"
            + "<p>Ctrl+D duplicates the selection; Ctrl+C and Ctrl+V copy and paste it inside the editor.</p>"),
        topic("Chips", "Action labels",
            "<p>Chips can show what each control does in the profile instead of its name, so the map reads as a binding sheet: <b>Gear up</b> or <b>Ctrl+G</b> beside the button, not Button 23. View → <b>Chip Text</b> picks <b>Name</b>, <b>Action</b>, or <b>Name and action</b> (also in Button Map Options → Labels). Renaming a chip still edits its name.</p>"
            + "<p>The text comes from the control's actions in one mode. View → <b>Labels Mode</b> picks the mode, or <b>Follow the Program</b>: the running mode while the profile runs, otherwise the mode chosen in the program. A control with no actions in a mode shows its parent mode's, as the running profile does.</p>"
            + "<ul>"
            + "<li><b>Description</b>: its text. With Button Map Options → Labels → <b>Description first</b> on (the default), it stands for the whole binding.</li>"
            + "<li><b>Map to Keyboard</b>: the keys, such as Ctrl+G. <b>Map to vJoy</b> and <b>Map to Xbox</b>: the output, such as vJoy 1 B5. <b>Change Mode</b>: → and the target mode, or Cycle, Previous mode, Unwind mode. <b>Text to Speech</b>: what it says. Mouse, Macro, Load profile, Run command, Sound, Pause / resume and Logical Device show those words.</li>"
            + "<li>Actions inside Chain, Tempo, Double Tap, Condition and the like give their text; response curves and deadzones give none.</li>"
            + "</ul>"
            + "<p><b>Several actions</b> shows the first one's text, or all of them joined with +. <b>No actions</b> sets what a chip shows when its control does nothing in that mode: its name, nothing, or a dash. Labels follow the profile as you edit it.</p>"),
        topic("Chips", "Hotspots and leaders",
            "<p>Each chip has a <b>hotspot</b>, the dot on the photo marking the physical control, and a <b>leader</b> line between them. Drag the chip and the hotspot separately. A chip's <b>Hotspot</b> section sets how the mark looks: <b>Size</b>; <b>Shape</b> (Round, Square, Diamond, Triangle pointing along the leader, Ring, Target, Crosshair, Plus, X, Pin, or None for no mark); <b>Fill</b> (Filled, Hollow, Half); <b>Line</b> (Thin, Medium, Thick); <b>Opacity</b>; <b>Halo</b>, a soft glow that stands out on busy photos; <b>Number</b>, the control's number inside; <b>Highlight on press</b>, the <b>Pressed Color…</b> while the control is held; <b>Pulse on press</b>, a ring that grows from it on each press; <b>Show on live map</b>, off to see it only while editing; and <b>Hotspot Color…</b>.</p>"
            + "<p>Click a leader to select it. Drag a segment to bend it; that adds a curve point (a spine). Click a spine to select it; hold the right button on a spine for about half a second to delete it.</p>"
            + "<p>Right-click a leader for <b>Add Leader</b> (another line from the same chip) and <b>Delete leader</b>. Its <b>Leader</b> section has <b>Leader Color…</b>, <b>Weight</b>, <b>Add Straight Spine</b>, <b>Add Curved Spine</b>, <b>Convert Spine</b>, <b>This Segment</b> or <b>All Segments</b> (Curved or Straight), <b>Branch from This End</b>, <b>Clear All Spines</b> and <b>Delete Spine</b>. <b>Leader Ends</b> detaches the chip end or the hotspot end, and reconnects it.</p>"
            + "<p>Spines show only while editing; the lines stay on the live map. In the Layers panel, open a chip to hide or lock its hotspot or one leader on its own.</p>"),
        topic("Chips", "Groups and 5-way formats",
            "<p>Select two or more chips (Shift-click, or drag a box on empty space) and choose <b>Group Selected</b> (Ctrl+G). The chips stay exactly where you put them (line them up first with <b>Align</b>, the arrow keys or by dragging), and the group moves as one. <b>Break Group</b> (Ctrl+Shift+G) splits it. <b>Edit Group</b> lets you move and style one member; <b>Done Editing Group</b> or Esc ends that.</p>"
            + "<p><b>Align Members</b> arranges a group Left, Center, Right or Free (Free keeps your own arrangement; new groups start as Free).</p>"
            + "<p><b>Turn a group</b>: select it and drag the round handle above it, or right-click → <b>Turn group</b>. Its chips swing round the group's middle and stay upright so they still read; the hotspot stays on the photo.</p>"
            + "<p>Right-click a five-chip hat group: <b>Style</b> → <b>Format</b> shows it as <b>Plus</b>, <b>Mini hat</b> or <b>Radial</b>; <b>Clear Format</b> removes it.</p>"
            + "<p>Grouping chips or text boxes together with a table packs them into the table (see Tables).</p>"),
        topic("Chips", "Mirror layout",
            "<p><b>Edit → Mirror Layout</b> turns the whole map left to right while editing: every chip, group, drawing and picture goes to the other side of the page, with its hotspot, leader bends and loose leader ends. Shapes and lines are mirrored, so an arrow points the other way; text boxes, tables and the arrangement inside a group stay as they are, so they still read. Pictures move but are only flipped when Button Map Options → Editing → Mirror pictures is on. One Undo puts it back.</p>"
            + "<p>To lay out a left-hand stick from a right-hand one, open the left stick and use <b>Edit → Copy Button Map from Device</b> with Mirror left to right ticked.</p>"),
        topic("Drawing", "Right-click menu",
            "<p>While editing, the menu shows only what applies to what you right-clicked: a chip, a group, a leader, a shape, a line, a picture, a text box, a table, several selected items, or empty canvas.</p>"
            + "<p>It opens small: the item's name with <b>Undo</b> and <b>Redo</b>, a few actions, then sections such as Chip style or Arrowheads. Click a section to open it; one is open at a time, and the menu reopens on the section you used last for that kind of item. Rows of values (sizes, widths, opacity) change straight away and leave the menu open; other actions close it.</p>"
            + "<p>Keys: Up and Down move, Enter acts, Right and Left open or close a section or step a row of values, Esc closes. Near a window edge the menu opens the other way, and it scrolls when it is taller than the window.</p>"),
        topic("Drawing", "Drawing shapes",
            "<p>Right-click empty canvas → <b>Draw</b> and pick a <b>Shape</b>: Rectangle, Rounded, Ellipse, Triangle, Diamond, Arrow or Double arrow. Drag on the photo to draw it; hold Shift to keep its proportions. The tool stays on for the next one until <b>Stop Drawing</b> or Esc.</p>"
            + "<p>With chips selected, <b>Shape Around Selection</b> draws a shape around them that moves with them; its <b>Padding</b> sets the gap, and Arrange → <b>Detach from Chips</b> frees it.</p>"
            + "<p>Right-click a shape for <b>Duplicate</b> and <b>Delete</b>, then sections: <b>Shape</b> (change the kind), <b>Fill and Outline</b> (Filled or Hollow, Fill Color…, Outline Color…, Width, outline Solid, Dashed or Dotted, Opacity), <b>Rotate and Flip</b> and <b>Arrange</b>.</p>"),
        topic("Drawing", "Lines and arrows",
            "<p>Draw → <b>Line</b> picks <b>Line</b> or <b>Arrow</b>. Drag from one end to the other; hold Shift to keep to 15° steps.</p>"
            + "<p>A selected line has a handle on each end; drag one to move that end (Shift for 15° steps). To turn a line, move its ends.</p>"
            + "<p>Its <b>Arrowheads</b> section sets the <b>Start</b> and <b>End</b> to None, Solid or Hollow; <b>Swap Heads</b> turns them round. Its <b>Line</b> section has Color…, Width, Outline (Solid, Dashed or Dotted) and Opacity, and <b>Flip</b> mirrors it.</p>"),
        topic("Drawing", "Paths and freehand",
            "<p>Draw → <b>Line</b> → <b>Path</b> draws through several points: click each point; click the first point again to close the shape, or double-click, press Enter or right-click to finish an open path. Shift keeps each segment to angle steps. The tool stays on for the next path; Esc stops it.</p>"
            + "<p>Draw → <b>Line</b> → <b>Freehand</b> draws while the button is held down. When you let go, the stroke is tidied (fewer points, same shape) and smoothed.</p>"
            + "<p>A selected path shows a small round handle on each point: drag one to move it. Its box's handles resize the whole path, and it turns and flips like a shape.</p>"
            + "<p>Right-click a path: <b>Path</b> → <b>Closed</b> and <b>Smooth</b>; <b>Line</b> → color, width, Solid, Dashed or Dotted, opacity; an open path has <b>Arrowheads</b> at its start and end, a closed one a <b>Fill</b> (Filled or Hollow, Fill color…).</p>"),
        topic("Drawing", "Rotate, flip and resize",
            "<p>Shapes, text boxes and pictures can be turned. A selected one has a round handle above it: drag it to turn the item to any angle, with Shift for steps (15° unless Button Map Options → Editing → Rotate snap says otherwise). The <b>Rotate and Flip</b> section has an <b>Angle</b> to type, <b>Turn to</b> 0°, 90°, 180° or 270°, <b>Rotate −15°</b> and <b>Rotate +15°</b>, and <b>Flip Horizontally</b> and <b>Flip Vertically</b>. Properties takes an exact Angle.</p>"
            + "<p>Drag the square handles to resize. A turned item resizes along its own sides, and the opposite side stays where it is. From a corner, a shape keeps its proportions when Shift is held; a picture keeps them unless Shift is held.</p>"
            + "<p><b>Several items together</b>: with two or more selected, a dashed box goes round them with one round handle above it. Drag it to turn them all about their middle (the angle shows beside the handle): shapes, text boxes and pictures turn, lines swing round with both ends, and chips, groups and tables move round but stay upright so they still read. Hotspots stay on the photo; locked items stay put. The right-click menu's <b>Turn together</b> turns them by a step, a quarter turn or a half turn. Turning there and back puts them where they were. One selected group turns the same way (see Groups and 5-way formats).</p>"
            + "<p>Lines turn by moving their ends. Tables, chips and hotspots do not turn on their own.</p>"),
        topic("Drawing", "Transform: shape, tips, bend, skew",
            "<p>Right-click a shape, picture or text box → <b>Transform</b> → <b>Handles</b> picks which handles the selected item shows. Only the choices that suit the item appear, and the choice goes back to Resize when you select something else.</p>"
            + "<ul>"
            + "<li><b>Resize</b>: the box's eight handles and the rotate handle, as usual.</li>"
            + "<li><b>Shape</b>: blue diamonds that reshape the item. On a block arrow or double arrow, one at the head sets the head's length (drag along) and width (drag out), one on the shaft sets its thickness. On a rounded rectangle it sets the corners' roundness; on a triangle, where its point is.</li>"
            + "<li><b>Tips</b> (block arrows): a diamond on each end. Drag one anywhere and the arrow stretches and turns to reach it; Shift keeps to angle steps.</li>"
            + "<li><b>Bend</b> (block arrows): a diamond on the middle of the shaft. Drag it to curve the arrow; the box grows so the arrow keeps its thickness.</li>"
            + "<li><b>Skew</b>: a diamond on the top edge leans the item sideways, one on the right edge leans it up or down.</li>"
            + "</ul>"
            + "<p><b>Edit Points</b> turns a shape into a path with a handle on every corner, looking as it does now (shaped, bent, skewed, turned), so any corner can be moved; it is then a path, not an arrow. <b>Reset Shape</b> takes away the shaping, bend and skew. Undo steps back through all of it.</p>"),
        topic("Drawing", "Text boxes",
            "<p>Draw → <b>Box</b> → <b>Text box</b>, then drag. Double-click a text box (or <b>Edit Text…</b>) to type.</p>"
            + "<ul>"
            + "<li><b>Text</b>: Font size, Bold, Word wrap, <b>Scale font with box</b>, and alignment Across (Left, Center, Right) and Down (Top, Middle, Bottom).</li>"
            + "<li><b>Box</b>: preset Size (Caption, Small, Medium, Large, Title, Wide), Theme (Dark, Hollow, Sheet), Text Color…, Fill Color…, Outline Color…, Fill opacity and Outline opacity.</li>"
            + "<li><b>Copy and Paint Format</b>: <b>Copy Format</b> takes this box's look; <b>Paint format</b> puts it on the next boxes you click; <b>Clear Formatting</b> resets it; <b>Copy Text</b> copies the words.</li>"
            + "</ul>"),
        topic("Drawing", "Callouts",
            "<p>A callout is a text box with a pointer. Draw → <b>Box</b> → <b>Callout</b>, then drag the box; or right-click a chip → <b>Add Callout</b> for one beside the chip, pointing at it and showing its text. Everything a text box does, a callout does too: typing, fonts, themes, colors, paint format, turning.</p>"
            + "<p>Select a callout to see the round handle at the pointer's tip. Drag it anywhere to point at a spot on the photo; drop it on a chip and the pointer follows that chip when it moves (the handle is filled while it does). The pointer leaves the side of the box facing its tip.</p>"
            + "<p>The text box's <b>Pointer</b> section: <b>Detach from Chip</b> keeps the pointer where it is without following, <b>Remove Pointer</b> makes it a plain text box, and on a plain text box <b>Add Pointer</b> makes it a callout.</p>"),
        topic("Drawing", "Tables",
            "<p>Draw → <b>Box</b> → <b>Table</b>, then drag. Double-click a cell to type in it.</p>"
            + "<ul>"
            + "<li><b>Rows and Columns</b>: Insert Row Above, Delete This Row, Insert Column Left, Delete This Column, and an <b>ID column</b>.</li>"
            + "<li><b>Cell</b>: <b>Free position</b> lets a cell be dragged out of the grid; <b>Independent of table</b> keeps it still when the table moves; <b>Spawn Empty Cell</b> adds a loose cell; <b>Delete This Cell</b>; <b>Place Across</b> and <b>Place Down</b> park a cell at a side.</li>"
            + "<li><b>Look</b>: Theme (Dark, Hollow, Sheet) and font size.</li>"
            + "</ul>"
            + "<p>Select a table with chips or text boxes on it and choose <b>Group Selected</b>: they are packed into the table and move with it. <b>Break Group</b> takes them out again; <b>Delete Table</b> removes it.</p>"),
        topic("Drawing", "Pictures",
            "<p>Draw → <b>Import Picture…</b> adds a picture file on top of the photo. Edit → <b>Paste Picture</b> (Ctrl+Shift+V), or <b>Paste Picture</b> in the canvas's Draw section, adds the picture on the clipboard: a copied picture, or picture files copied in File Explorer. <b>Ctrl+V</b> pastes a picture too when it was copied after your last chip copy. You can also <b>drag picture files</b> from File Explorer onto the map while editing: each lands where you drop it, at its own shape. Pictures are saved beside the device's module file.</p>"
            + "<p>A picture moves, resizes, turns and flips like a shape (see Rotate, flip and resize). Its <b>Picture</b> section has:</p>"
            + "<ul>"
            + "<li><b>Crop</b>: the handles turn blue and cut the picture instead of scaling it; what stays does not move. Esc or selecting something else ends it. <b>Reset Crop</b> shows the whole picture again; Properties takes exact crop values.</li>"
            + "<li><b>Add snap point</b> (then click the picture) and <b>Clear Snap Points</b>: chips snap to these points.</li>"
            + "<li>Opacity.</li>"
            + "</ul>"),
        topic("Drawing", "Saved styles",
            "<p>A look you use again and again can be kept under a name. Right-click a chip, shape, line, path or text box → <b>Saved Styles</b> → <b>Save This Style…</b> and give it a name, such as Weapons, red. A style of the same name and kind is replaced.</p>"
            + "<p>The same section then lists the saved styles for that kind of item: <b>Apply</b> one to put its look on everything selected of that kind, as one step for Undo. A chip's style holds its chip, text, pressed, hotspot and leader colors and sizes; a shape's its fill and outline; a line's its color, width, outline and arrowheads; a text box's its format.</p>"
            + "<p>Styles are shared by every device. Edit → Button Map Options… → <b>Library</b> renames and deletes them, and the layout templates too.</p>"),
        topic("Panels", "Layers panel",
            "<p>View → <b>Layers</b> shows every item while editing, top of the stack first, then the photo.</p>"
            + "<ul>"
            + "<li>The <b>eye</b> hides an item: it is not drawn, on the live map either, and is left out of exports.</li>"
            + "<li>The <b>lock</b> keeps an item in place: clicks pass through it, and it is not moved, nudged or deleted. Ctrl+L locks or unlocks the selection; Ctrl+Shift+L unlocks everything.</li>"
            + "<li>Open a chip (the arrow) to hide or lock its hotspot or each leader on its own. Locking or hiding the chip covers them all.</li>"
            + "<li>Drag a row up or down to change what is on top. The right-click menu's <b>Arrange</b> section does the same a step at a time: Bring to Front, Bring Forward, Send Back, Send to Back.</li>"
            + "<li>Click a row to select the item (Ctrl or Shift to add); a right-click selects it too before its menu opens (a row in a selection keeps the selection). Double-click a drawing's row to name it.</li>"
            + "<li><b>Show all</b> and <b>Unlock all</b> undo every hide and lock.</li>"
            + "</ul>"
            + "<p><b>Search layers…</b>, the box under the panel's header, finds rows as you type, in any case and anywhere in: the row's name, the control (Button 12, Hat 1, X Axis, even when the chip has a friendly name), what the chip shows (its action or description), and the kind of row. Ctrl+F (or View → <b>Search layers…</b>) goes to the box, opening Layers if it is closed. <b>Esc</b> or the box's <b>×</b> clears it; <b>Enter</b> selects every match on the map and brings the first into view.</p>"
            + "<p>Under the box, one toggle per kind of row: <b>All · Chips · Groups · Hotspots · Leaders · Shapes · Lines · Pictures · Text · Tables · Photo</b>. Turn on any number of kinds to show only those; with none on, every row shows and <b>All</b> lights; <b>All</b> turns them all off again. The search looks only in the kinds that are on. A matching hotspot, leader or group member shows under its chip or group, which is dimmed when it doesn't match itself. While a filter is on, a line says how many rows match (12 of 148) or <b>No layers match</b>. The eye, lock, rename, drag and delete work on the rows shown.</p>"
            + "<p>The kinds and the search stay while the Button Map is open, also when another device's map is shown; they go back to none and empty when the Button Map closes.</p>"),
        topic("Panels", "Properties panel",
            "<p>View → <b>Properties</b> shows the selected item's exact values while editing. Positions and sizes are in percent of the page.</p>"
            + "<ul>"
            + "<li>A shape or picture: X, Y, Width, Height and Angle, then fill, colors, line width, outline and opacity; a picture also has Crop left, top, right and bottom.</li>"
            + "<li>A line: Start and End X and Y, color, width, outline and the Start and End heads.</li>"
            + "<li>A chip: its place and its hotspot's, font size, chip size and colors.</li>"
            + "<li>Several items: only the style shows, and a change applies to all of them.</li>"
            + "</ul>"
            + "<p>Type a number and press Enter, or click a color to open the color picker. A locked item's values show but do not change.</p>"),
        topic("Panels", "Align and distribute",
            "<p>Select several items and right-click one of them. <b>Align and Distribute</b> lines them up <b>Across</b> (Left, Center, Right) or <b>Down</b> (Top, Middle, Bottom) by their edges or middles. <b>Space Out</b> leaves equal gaps between three or more. Locked items stay where they are.</p>"),
        topic("Panels", "Colors",
            "<p>The color picker opens from Colors, Fill color…, Outline color… and the Properties swatches. Drag in the square and the bar, or click a swatch; the change shows at once.</p>"
            + "<p><b>Recent</b> shows the colors you used last, on any device. <b>Pick from Map</b> closes the picker; click anywhere in the window to take the color there (right-click or Esc gives up).</p>")
    ]
}

function topic(section, title, body) {
    return { "section": section, "title": title, "body": body }
}

// The Device Library's own guide (its Help menu and F1): only the Device
// Library (10 S42).
function deviceLibraryTopics() {
    return [
        topic("Getting started", "What the Device Library is",
            "<p>The <b>Device Library</b> keeps every device the program has known, and copies of their settings and bindings. With it you can put an old stick's setup on a new stick, let two sticks trade places, or change which vJoy a stick sends to, and go back if you change your mind.</p>"
            + "<ul>"
            + "<li><b>Devices</b>: sticks plugged in now, sticks set up here but unplugged, deleted sticks, and sticks from someone else's Device Pack.</li>"
            + "<li><b>Saved setups</b>: stored copies of a device's settings and bindings, each with a name and a description. You keep your own; the program keeps <b>autosaves</b> by itself before anything replaces or removes a stick's settings.</li>"
            + "</ul>"
            + "<p>Copying never changes the saved setup or the stick it came from.</p>"
            + "<p>Open it in any of three ways:</p>"
            + "<ul>"
            + "<li>The <b>Device Library…</b> button on Home.</li>"
            + "<li>Tools › Device Setup › <b>Device Library…</b> in the main window.</li>"
            + "<li>A stick's card menu, in its Device section: <b>Copy Setup to Another Stick…</b>, <b>Swap with Another Stick…</b> or <b>Change vJoy Output…</b> open the window on that stick, with that dialog. They are not on vJoy, Xbox, Keyboard, OSC or Logical Device cards.</li>"
            + "</ul>"
            + "<p>Help › <b>Device Library Guide</b> or <b>F1</b> in the window opens this guide.</p>"),
        topic("Getting started", "The window",
            "<p>The left side lists the devices; the right side shows the details of what you select. Drag the divider between them to change their widths.</p>"
            + "<ul>"
            + "<li><b>Filters</b> at the top: <b>Connected</b>, <b>Not connected</b>, <b>Deleted</b> and <b>Autosaves</b>. A ticked filter shows that kind; click one to hide it.</li>"
            + "<li>The <b>search box</b> under them finds devices and saved setups as you type (see Search).</li>"
            + "<li>The <b>list</b>: one row per device, with its saved setups under it.</li>"
            + "<li>The <b>details</b>: the name, the description, what it holds, and the buttons for what you can do with it.</li>"
            + "<li>The line above the status bar says how the last change went, and lists anything you should check.</li>"
            + "<li>The <b>status bar</b> shows how many devices and saved setups there are, how many autosaves are kept per stick, the library's size on disk (for example \"Library: 48 MB\") and the library folder.</li>"
            + "</ul>"
            + "<p>The menus:</p>"
            + "<ul>"
            + "<li><b>File</b>: <b>Import Device Pack…</b>, <b>Export Saved Setup…</b>, <b>Open Library Folder</b>, <b>Close</b>.</li>"
            + "<li><b>Edit</b>: <b>Undo</b> (named for the change, see Undo and Redo), <b>Rename…</b> (F2), <b>Delete…</b>, <b>Tidy Library…</b>.</li>"
            + "<li><b>Device</b>: <b>Save to Device Library…</b>, <b>Copy to Another Stick…</b>, <b>Swap with Another Stick…</b>, <b>Change vJoy Output…</b>.</li>"
            + "<li><b>View</b>: <b>Connected</b>, <b>Not Connected</b>, <b>Deleted</b> and <b>Autosaves</b> (the same as the filters), <b>Expand All</b>, <b>Collapse All</b>, <b>Search…</b> (Ctrl+F).</li>"
            + "<li><b>Settings</b>: <b>Device Library Settings…</b>.</li>"
            + "<li><b>Help</b>: <b>Device Library Guide</b> (F1).</li>"
            + "</ul>"
            + "<p>Menu items you can't use right now are greyed out: for example Swap with Another Stick… needs a stick that is plugged in.</p>"
            + "<p>Right-click a row, or the empty space in the list, for a menu of what you can do with it (see Right-click menus).</p>"),
        topic("Getting started", "Right-click menus",
            "<p>Right-clicking a row selects it first, as a click does (it is highlighted and its details show), then opens its menu. The <b>Menu</b> key or <b>Shift+F10</b> opens the same menu on the selected row. Right-clicking the empty space in the list opens the list's own menu.</p>"
            + "<p>A device's menu:</p>"
            + "<ul>"
            + "<li><b>Copy to Another Stick…</b> (from its current settings), <b>Swap with Another Stick…</b> (when it is plugged in), <b>Change vJoy Output…</b>, <b>Save to Device Library…</b> and <b>Export Current Setup…</b> (see Export a saved setup).</li>"
            + "<li><b>Rename…</b> (F2) and <b>Edit Description</b>, which puts the cursor in its description.</li>"
            + "<li><b>Open Module Setup…</b>, <b>Open Button Map</b> and <b>Show on Home</b>, for a stick with a card on Home (plugged in, or set up here): they open in the main window.</li>"
            + "<li><b>Expand</b> or <b>Collapse</b>, when it has saved setups.</li>"
            + "<li>The delete items, by its state: <b>Remove from Library…</b> when it isn't connected; <b>Clear Setup…</b> and <b>Delete Saved Setups…</b> when it is (see Delete and Remove from Library).</li>"
            + "</ul>"
            + "<p>A saved setup's menu: <b>Copy to Another Stick…</b>, <b>Restore to This Stick…</b> (when its stick is plugged in), <b>Export…</b>, <b>Rename…</b>, <b>Edit Description</b>, <b>Keep This Autosave</b> (autosaves only) and <b>Delete…</b>.</p>"
            + "<p>The empty space's menu: <b>Import Device Pack…</b>, <b>Expand All</b>, <b>Collapse All</b> and <b>Device Library Settings…</b>.</p>"
            + "<p>A menu shows only what you can do now: an item that doesn't apply, or that has to wait while a change runs, is left out. The delete items are red, and each asks first, naming exactly what goes, for example \"Remove Old Warthog stick and its 4 saved setups from the Library?\".</p>"),
        topic("Devices and saved setups", "Devices",
            "<p>Each device row shows its name, its description, how many saved setups it has, and its state:</p>"
            + "<ul>"
            + "<li><b>Connected</b>: plugged in now.</li>"
            + "<li><b>Not connected</b>: set up here but unplugged, or a device that came only from someone else's Device Pack. You can copy from it, never to it.</li>"
            + "<li><b>Deleted</b>: removed with Delete Device on Home. Its autosave is kept under it.</li>"
            + "</ul>"
            + "<p>Select a device to see its name, description and state, what inputs it has (for example \"32 buttons, 6 axes, 1 hat\") and when it was last seen.</p>"
            + "<p>The buttons under a device's details: <b>Save to Device Library…</b>, <b>Copy to Another Stick…</b>, <b>Swap with Another Stick…</b>, <b>Change vJoy Output…</b>, and the red <b>Remove from Library…</b> (not connected) or <b>Delete Saved Setups…</b> (connected).</p>"
            + "<p>Click the caret beside a device, or double-click the device, to show or hide its saved setups.</p>"),
        topic("Devices and saved setups", "Saved setups",
            "<p>A device's saved setups are listed under it, newest first. A save mark shows the ones that are yours; an autosave mark shows the ones the program kept. The line under each name says how it was kept: <b>Saved by you</b>, <b>Kept automatically</b>, <b>Was an autosave, now yours</b>, or which pack it came from.</p>"
            + "<p>A saved setup holds any of these parts:</p>"
            + "<ul>"
            + "<li><b>Setup</b>: the module file's claims and friendly names.</li>"
            + "<li><b>Button Map</b> and its photo.</li>"
            + "<li><b>Appearance</b>.</li>"
            + "<li><b>Calibration</b>.</li>"
            + "<li><b>Bindings</b>: the stick's actions from one profile, in the modes saved, and the vJoy outputs they send to.</li>"
            + "</ul>"
            + "<p>Select one to see its name and description, when and why it was kept, exactly what it holds (under <b>Holds</b>, for example \"Bindings from DCS.xml · modes Default, Landing · 212 actions\" and \"Sends to vJoy 1 (38 inputs)\"), a preview of its Button Map photo, and its <b>Activity</b>: when it was saved, when its description was edited, and which sticks it was copied to. (Activity is only about that saved setup; Tools → History keeps every saved change in the program.)</p>"
            + "<p>The buttons under the details: <b>Copy to Another Stick…</b>, <b>Swap with Another Stick…</b>, <b>Change vJoy Output…</b>, <b>Export…</b> and <b>Delete…</b>.</p>"
            + "<p>A stick whose module file was damaged can still be kept: its saved setup holds <b>Setup (damaged file, kept as is)</b>. That file is never put on another stick; only its bindings can be copied.</p>"),
        topic("Devices and saved setups", "Names and descriptions",
            "<p>Every device and every saved setup can be renamed and given a description.</p>"
            + "<ul>"
            + "<li><b>Rename…</b> (Edit menu, <b>F2</b>, or the pencil beside the name): type the new name and press Enter; Esc keeps the old one.</li>"
            + "<li>The <b>description</b> is edited where it shows, in the box under the name (\"Add a description\" when it is empty). It is kept when you click elsewhere.</li>"
            + "</ul>"
            + "<p>A stick set up here has one name: renaming it in the Device Library renames its card on Home, and the other way round.</p>"
            + "<p>Renaming or describing an autosave makes it yours: the autosave limit never removes it.</p>"),
        topic("Devices and saved setups", "Save to Device Library",
            "<p>Select a device and choose <b>Save to Device Library…</b> (Device menu, or the button in its details) to keep a saved setup of your own.</p>"
            + "<ul>"
            + "<li>It keeps the stick's module file as it is now, and its bindings from the profiles you tick. The open profile is marked \"(open)\".</li>"
            + "<li>You get one saved setup per ticked profile, named after the profile. Rename it and add a description afterwards.</li>"
            + "<li>When no profile has bindings for the stick, only the module file is kept.</li>"
            + "</ul>"
            + "<p>The device needs settings to save: a stick set up here or plugged in now.</p>"),
        topic("Autosaves", "When autosaves are kept",
            "<p>The program keeps an autosave of a stick by itself, without asking, whenever something is about to replace or remove its settings. Autosaves are always on: they are your way back.</p>"
            + "<ul>"
            + "<li><b>Delete Device</b> on Home: \"Autosave: stick deleted\".</li>"
            + "<li><b>Delete File</b> in Module Setup: \"Autosave: module file deleted\" (the setup only).</li>"
            + "<li>Before <b>Copy</b> changes the target stick: \"Autosave: before Copy from Old Warthog\".</li>"
            + "<li>Before <b>Swap</b>, one of each stick: \"Autosave: before Swap with Right stick\".</li>"
            + "<li>Before <b>Change vJoy Output</b>: \"Autosave: before Change vJoy Output (vJoy 1 → 2)\".</li>"
            + "<li>Before a <b>Device Pack</b> is imported onto the stick from Home: \"Autosave: before Device Pack My F-16\" (the pack's file name).</li>"
            + "<li>Before <b>Restore to This Stick…</b>: \"Autosave: before Restore of DCS F-16\".</li>"
            + "<li>Before <b>Undo</b> puts a change back: \"Autosave: before Undo\".</li>"
            + "</ul>"
            + "<p>An autosave holds everything the stick has: its module file and pictures, and its bindings in every mode from every profile the change touches.</p>"
            + "<p>If an autosave can't be written or read back, the change doesn't run and the message says why.</p>"),
        topic("Autosaves", "How many are kept",
            "<p>Only the newest 10 autosaves per stick are kept; when a new one is kept, the oldest goes. Change the number in <b>Device Library Settings…</b> (\"Keep the newest … autosaves per stick\"). The status bar shows the number in use.</p>"
            + "<p>Your own saved setups are never removed this way, nor is an autosave you renamed, described or kept with Keep This Autosave: it becomes yours.</p>"
            + "<p>Turn off the <b>Autosaves</b> filter to hide autosaves from the list.</p>"),
        topic("Autosaves", "Keep This Autosave",
            "<p>Right-click an autosave and choose <b>Keep This Autosave</b> to make it yours in one step, as renaming or describing it does. The autosave limit then never removes it.</p>"
            + "<p>Its line then reads <b>Was an autosave, now yours</b>, it shows a save mark, and its Activity says \"Kept as your own\". The item shows only on autosaves that are not yours yet.</p>"),
        topic("Autosaves", "Delete Device and Delete File",
            "<p><b>Delete Device</b> on Home always keeps an autosave of the stick first: its module file, its pictures and its bindings in every mode. There is no question about a copy. The stick then shows in the Device Library as <b>Deleted</b>, with its autosave under it.</p>"
            + "<p><b>Delete File</b> in Module Setup keeps an autosave of the module file (\"Autosave: module file deleted\").</p>"
            + "<p>Both work even when the module file is damaged: the damaged file is kept exactly as it is.</p>"
            + "<p>In the Device Library, <b>Clear Setup…</b> on a connected stick is the same as Delete Device, and Remove from Library… runs Delete Device first for a stick whose module file is still here.</p>"
            + "<p>To use a deleted stick's setup again, select its autosave and choose <b>Copy to Another Stick…</b>.</p>"),
        topic("Changing sticks", "Copy to Another Stick",
            "<p><b>Copy to Another Stick…</b> puts a saved setup, or a stick's current settings, on a stick plugged in now. Double-clicking a saved setup opens it too.</p>"
            + "<ul>"
            + "<li><b>From</b>: the saved setup, or \"current settings\" when you chose a device that is set up here or plugged in. For a device with neither, its newest saved setup is used.</li>"
            + "<li><b>To</b>: only sticks plugged in now are listed. A stick that was never plugged in here can be copied from, never to.</li>"
            + "<li><b>What to copy</b>: Setup, Button Map, Appearance and Bindings are ticked; Calibration is not (change these defaults in Device Library Settings…). Parts the saved setup doesn't hold are greyed out.</li>"
            + "<li><b>Bindings go into these profiles</b>: every profile with bindings for either stick. Only the open profile is ticked to start; <b>Tick All</b> ticks them all.</li>"
            + "<li><b>Modes</b>: the ticked modes replace the target stick's bindings in those modes.</li>"
            + "<li>A warning box lists what won't copy because the target stick lacks it (buttons, hats, axes and the bindings on them). Those are left out; the rest copies.</li>"
            + "</ul>"
            + "<p>Press <b>Copy</b>. An autosave of the target stick is kept first, and Edit › Undo puts it back. The saved setup and the stick it came from never change.</p>"),
        topic("Changing sticks", "Restore to This Stick",
            "<p><b>Restore to This Stick…</b>, in a saved setup's right-click menu, puts the saved setup back on the stick it belongs to, without choosing a To stick. That stick must be plugged in.</p>"
            + "<ul>"
            + "<li>It works as Copy does: every part the saved setup holds (Calibration too, as it is the same stick), into the profiles it came from that are still there, in every mode it has.</li>"
            + "<li>It asks first; press <b>Restore</b>.</li>"
            + "<li>An autosave of the stick is kept first (\"Autosave: before Restore of DCS F-16\"), and Edit › Undo puts it back.</li>"
            + "</ul>"
            + "<p>To choose the parts, profiles and modes, or to put it on another stick, use Copy to Another Stick… instead.</p>"),
        topic("Changing sticks", "Swap with Another Stick",
            "<p><b>Swap with Another Stick…</b> lets two sticks trade places: each gets the other's settings. Both must be plugged in.</p>"
            + "<ul>"
            + "<li><b>What trades places</b>: the same parts as Copy (Setup, Button Map, Appearance, Calibration, Bindings).</li>"
            + "<li><b>Swap bindings in these profiles</b>: as Copy, the open profile ticked; <b>Tick All</b> ticks them all.</li>"
            + "<li>Bindings swap with everything that points at the sticks: device references inside actions and script variables swap too.</li>"
            + "<li>The warning box (\"Some settings have nowhere to go\") lists, both ways, what one stick has that the other lacks; those bindings stay where they were. It also lists actions elsewhere that refer to a control one stick lacks, for example a Condition checking Left stick Axis 3 when Right stick has no Axis 3: that reference still moves with the swap, so check it.</li>"
            + "</ul>"
            + "<p>The Keyboard, Logical Device, OSC and the Xbox controller can't be swapped, and a stick can't be swapped with itself.</p>"
            + "<p>Press <b>Swap</b>. An autosave of each stick is kept first, and Edit › Undo puts both back.</p>"),
        topic("Changing sticks", "Change vJoy Output",
            "<p><b>Change vJoy Output…</b> keeps a stick's bindings and changes only which vJoy they send to, for example so a game sees two sticks the other way round.</p>"
            + "<ul>"
            + "<li><b>Change it in these profiles</b>: the open profile ticked; <b>Tick All</b> ticks them all.</li>"
            + "<li>One row per vJoy the stick sends to, such as \"vJoy 1 (38 inputs) → vJoy 2\". Pick where each sends; the row says <b>changes</b> or <b>stays</b>.</li>"
            + "<li>When another stick already sends to the vJoy you picked, a tick box offers to move it the other way, for example \"Also move Right stick from vJoy 2 to vJoy 1 (swap them)\".</li>"
            + "<li>The <b>Check these</b> box lists bindings that would send to an output the new vJoy's output module doesn't claim (they would send nothing), and macros and user scripts that name a vJoy number. Those are not changed: check them yourself.</li>"
            + "</ul>"
            + "<p>Press <b>Change</b>. An autosave of each stick that changes is kept first, and Edit › Undo puts them back.</p>"),
        topic("Changing sticks", "Profiles that aren't open",
            "<p>Copy, Swap and Change vJoy Output change the profiles you tick.</p>"
            + "<ul>"
            + "<li>The <b>open profile</b> is changed in memory: save it with File → Save Profile in the main window to keep the change.</li>"
            + "<li>A ticked profile that isn't open is changed and saved on disk straight away. History keeps each save, so the whole file can be restored from History.</li>"
            + "<li>A profile that can't be read or written is named in the message and left as it was; the others still change.</li>"
            + "</ul>"
            + "<p>The autosave kept first holds the stick's bindings from every profile the change touches, so Undo puts them all back.</p>"),
        topic("Changing sticks", "When the window is busy",
            "<p>Reading profiles, keeping autosaves and writing files run in the background, so the window keeps responding.</p>"
            + "<ul>"
            + "<li>The dialogs show <b>Reading the profiles…</b> and <b>Checking…</b> while they work out the profiles and the warnings. Wait for the warnings before you press Copy, Swap or Change.</li>"
            + "<li>While a change runs, the status bar shows <b>Working…</b> and the menu items that would start another change are greyed out (left out of the right-click menus). One change runs at a time.</li>"
            + "<li>A row that is being changed shows a small busy mark until the change is done.</li>"
            + "</ul>"),
        topic("Undo and Redo", "Undo and Redo",
            "<p>Edit › <b>Undo</b> puts the last Copy, Swap, Change vJoy Output or Restore back, by copying the autosaves it kept onto their sticks: every part they hold, into the profiles they came from.</p>"
            + "<ul>"
            + "<li>The menu item names the change, for example \"Undo Copy DCS F-16 to Right stick\".</li>"
            + "<li>Right after an Undo it reads \"Redo Copy DCS F-16 to Right stick\": choose it to make the change again.</li>"
            + "<li>Undo keeps its own autosave first (\"Autosave: before Undo\").</li>"
            + "<li>It still works after you close the window or restart the program, until another change replaces it.</li>"
            + "</ul>"
            + "<p>Only the last change can be undone here. For an older one, right-click the autosave it kept and choose <b>Restore to This Stick…</b>, or use <b>Copy to Another Stick…</b>.</p>"),
        topic("Finding things", "Search",
            "<p>Type in the search box (<b>Ctrl+F</b> or View › <b>Search…</b> goes there; <b>Esc</b> clears it). It finds, in any case:</p>"
            + "<ul>"
            + "<li>device names and descriptions;</li>"
            + "<li>saved setup names and descriptions, and autosave reasons (\"stick deleted\", \"before Swap\");</li>"
            + "<li>what a saved setup holds (Setup, Button Map, Appearance, Calibration, Bindings);</li>"
            + "<li>profile names and mode names;</li>"
            + "<li>vJoy numbers (\"vJoy 2\").</li>"
            + "</ul>"
            + "<p>A device that has a matching saved setup opens to show it.</p>"),
        topic("Finding things", "Filters and the list",
            "<p>The filters <b>Connected</b>, <b>Not connected</b>, <b>Deleted</b> and <b>Autosaves</b> work together: each one that is ticked shows that kind, so you can, for example, hide deleted sticks and autosaves. The View menu has the same four.</p>"
            + "<p>View › <b>Expand All</b> shows every device's saved setups; <b>Collapse All</b> hides them.</p>"),
        topic("Finding things", "Selecting several rows",
            "<p>Ctrl-click adds a row to the selection or takes it away; Shift-click selects every row from the last one you clicked to this one. You can select several saved setups, or several devices, but not both: clicking a row of the other kind starts a new selection.</p>"
            + "<ul>"
            + "<li><b>Delete…</b> (saved setups) or <b>Remove from Library…</b> (devices that aren't connected) acts on all of them, after one question that lists them. It is in the right-click menu, in Edit › Delete… and on the red <b>Delete…</b> button.</li>"
            + "<li>Devices are removed together only when none of them is connected.</li>"
            + "<li>Copy, Swap, Change vJoy Output, Restore, Rename and Export act on one row only: while several rows are selected they are greyed out, or left out of the menu and the details.</li>"
            + "</ul>"),
        topic("Sharing", "Export a saved setup",
            "<p>Select a saved setup and choose <b>Export…</b> (or File › <b>Export Saved Setup…</b>). It is written as a Device Pack (.zip) wherever you pick, ready to give to a friend.</p>"
            + "<p>To share a stick's settings as they are now, right-click the device and choose <b>Export Current Setup…</b>: it writes a Device Pack of its current settings, without keeping a saved setup first. It needs a stick set up here or plugged in.</p>"
            + "<p>File › <b>Open Library Folder</b> opens the library's folder in File Explorer.</p>"),
        topic("Sharing", "Import a Device Pack",
            "<p>File › <b>Import Device Pack…</b>, or dropping a Device Pack (.zip) on the window, adds it as a saved setup:</p>"
            + "<ul>"
            + "<li>under the device it was made from, when that device is in the Device Library;</li>"
            + "<li>otherwise under a new <b>Not connected</b> device named after the pack.</li>"
            + "</ul>"
            + "<p>The saved setup says where it came from (\"From Sam's pack\") and takes the pack's note as its description. Nothing changes on your sticks: to use it, select it and choose <b>Copy to Another Stick…</b>.</p>"),
        topic("Settings and tidying", "Device Library Settings",
            "<p>Settings › <b>Device Library Settings…</b> holds:</p>"
            + "<ul>"
            + "<li><b>Keep the newest … autosaves per stick</b> (10 to start). Setups you saved, renamed or described are never removed.</li>"
            + "<li><b>Copy and Swap tick by default</b>: which parts start ticked (Setup, Button Map, Appearance and Bindings; Calibration off).</li>"
            + "<li><b>Library folder</b>: where the Device Library is kept. <b>Move…</b> picks another folder; the library moves there when you press <b>OK</b>.</li>"
            + "</ul>"),
        topic("Settings and tidying", "Tidy Library",
            "<p>The status bar shows how much space the library takes. Edit › <b>Tidy Library…</b> lists what it could remove: autosaves older than a number of months you choose (6 to start), and deleted devices with no saved setups. Each item shows its size and is ticked; untick what you want to keep.</p>"
            + "<p>Nothing is removed until you press <b>Remove</b>. Apart from this and the autosave limit, nothing in the library is removed without asking.</p>"),
        topic("Settings and tidying", "Delete and Remove from Library",
            "<p>Every delete asks first and names exactly what goes. What it does depends on what is selected:</p>"
            + "<ul>"
            + "<li>A saved setup: <b>Delete…</b> removes it from the Device Library.</li>"
            + "<li>A device that isn't connected (unplugged, deleted, or from a pack): <b>Remove from Library…</b> removes the device and all its saved setups. If its module file is still here, that goes first, as Delete Device on Home does: an autosave is kept first. If Delete Device can't run, nothing is removed and the message says why.</li>"
            + "<li>A connected stick: <b>Clear Setup…</b> is Delete Device on Home: an autosave is kept in the Device Library first, then its module file and its bindings go, and the stick stays plugged in with no setup. <b>Delete Saved Setups…</b> removes only its saved setups; the stick keeps its settings.</li>"
            + "</ul>"
            + "<p>Edit › <b>Delete…</b> and the red button under the details follow the same rules. On a device the button reads Remove from Library… or Delete Saved Setups… by its state, and Edit › Delete… does the same. Clear Setup… is only in the device's right-click menu.</p>"
            + "<p>To delete several rows with one question, see Selecting several rows.</p>"
            + "<p>Removing and deleting from the Library can't be undone. Clear Setup… can: its autosave is under the stick, ready for <b>Restore to This Stick…</b>.</p>"),
        topic("Renamed and twin sticks", "Renamed and twin sticks",
            "<p>A stick's name in the Device Library is its name on Home. Rename it in either place and both change; dialogs, autosave names and the Undo item use that name.</p>"
            + "<p>Two sticks with the same name (twins) are told apart by a short id after the name, in the list and in the To lists: for example \"Right stick [EEEE0006]\". Rename one of them to tell them apart more easily.</p>"),
        topic("Common questions", "My stick broke: how do I put its setup on the new one?",
            "<p>Plug in the new stick. In the Device Library, open the old stick's row, select a saved setup (or its \"Autosave: stick deleted\" if you deleted it) and choose <b>Copy to Another Stick…</b> with the new stick as To. Untick Calibration unless the sticks are the same model. The warning box lists any controls the new stick doesn't have.</p>"),
        topic("Common questions", "How do I give my setup to a friend?",
            "<p>Select the saved setup and press <b>Export…</b>. Send them the .zip: they import it with File › <b>Import Device Pack…</b> (or drop it on their Device Library) and copy it onto their stick.</p>"
            + "<p>To share the stick's settings as they are now, right-click the device and choose <b>Export Current Setup…</b>, or keep them with <b>Save to Device Library…</b> and export that saved setup.</p>"),
        topic("Common questions", "Why can't I copy to this stick?",
            "<p>Copy and Swap only work onto sticks plugged in now: the To list shows nothing else. Plug the stick in and open the dialog again. A device that came from someone's pack has never been plugged in here, so you can copy from it but not to it.</p>"),
        topic("Common questions", "Where did my old setup go?",
            "<ul>"
            + "<li>A deleted stick shows as <b>Deleted</b>, with its autosave under it. Make sure the Deleted and Autosaves filters are ticked and the search box is empty.</li>"
            + "<li>Clear Setup… keeps \"Autosave: stick deleted\" under the stick: right-click it and choose Restore to This Stick….</li>"
            + "<li>Copy, Swap, Change vJoy Output, Restore and a Device Pack import keep an autosave first; search for the change (\"before Restore\").</li>"
            + "<li>Only the newest autosaves per stick are kept (Device Library Settings…). Choose <b>Keep This Autosave</b>, or rename or describe one, to keep it for good.</li>"
            + "<li>Saved setups removed with Delete…, Delete Saved Setups… or Remove from Library… are gone for good.</li>"
            + "</ul>"),
        topic("Common questions", "I made a mistake: how do I go back?",
            "<p>Edit › <b>Undo</b> puts the last Copy, Swap, Change vJoy Output or Restore back, even after a restart. For an older change, right-click the autosave it kept and choose <b>Restore to This Stick…</b> (the stick must be plugged in), or copy it onto the stick with Copy to Another Stick…. After Clear Setup…, restore its \"Autosave: stick deleted\" the same way. A profile that wasn't open was saved, so History can also restore the whole file.</p>"),
        topic("Common questions", "Why are the buttons greyed out?",
            "<p>The window is busy: a dialog shows <b>Checking…</b>, or the status bar shows <b>Working…</b> while a change runs. Wait for it to finish. Otherwise the selection doesn't allow it: Swap with Another Stick… needs a stick that is plugged in, Export… needs a saved setup, and Save to Device Library… needs a stick set up here or plugged in. With several rows selected only delete works.</p>"
            + "<p>The right-click menus leave out what doesn't apply instead of greying it out.</p>")
    ]
}
