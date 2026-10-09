// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help, chapter "Device Library" (01 S128, 10 S42, D-01-ONE-HELP).
// Written to claude/help-style.md; on-screen labels in bold, exactly as shown.

.pragma library

var chapter = { id: "device-library", title: "Device Library" }

function topics() {
    return [
        // ---- Getting started ------------------------------------------------
        t("device-library-about", "Getting started", "What the Device Library is",
            "<p>The <b>Device Library</b> keeps every device the program has known, with copies of their settings and bindings. Use it to put an old stick's setup on a new stick, let two sticks trade places, or change which vJoy a stick sends to, and to go back afterwards.</p>"
            + "<ul>"
            + "<li><b>Devices</b>: sticks plugged in now, sticks set up here but unplugged, deleted sticks, sticks from someone else's Device Pack, and the program's built-in inputs.</li>"
            + "<li><b>Saved setups</b>: stored copies of a device's settings and bindings, each with a name and a description. You keep your own; the program keeps <b>autosaves</b> by itself before anything replaces or removes a stick's settings.</li>"
            + "</ul>"
            + "<p>Copying never changes the saved setup or the stick it came from.</p>",
            ["device-library-open", "device-library-saved-setups", "device-library-autosaves"]),
        t("device-library-open", "Getting started", "Open the Device Library",
            "<p>The Device Library opens in its own window. Open it in one of these ways:</p>"
            + "<ul>"
            + "<li>Choose <b>Device Library</b> on the toolbar <a href=\"show:toolbar/Device Library\">Show me ›</a>.</li>"
            + "<li>In the main window, choose <b>Tools › Device Setup › Device Library…</b> <a href=\"open:tools.deviceLibrary\">Open ›</a>.</li>"
            + "<li>Right-click a stick's card on Home and, in its Device section, choose <b>Copy Setup to Another Stick…</b>, <b>Swap with Another Stick…</b> or <b>Change vJoy Output…</b>. The window opens on that stick, with that dialog.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The card items are not on vJoy, Xbox, Keyboard, OSC or Logical Device cards.</li>"
            + "<li>In the Device Library, <b>Help</b> or <b>F1</b> opens this chapter of Help. <b>View Full Help</b> shows the whole book.</li>"
            + "</ul>",
            ["device-library-about", "device-library-window"]),
        t("device-library-window", "Getting started", "The Device Library window",
            "<p>The left side lists the devices; the right side shows the details of what you select. Drag the divider between them to change their widths.</p>"
            + "<ul>"
            + "<li><b>Filters</b> at the top: <b>Connected</b>, <b>Not connected</b>, <b>Deleted</b> and <b>Autosaves</b>. A ticked filter shows that kind; select one to hide it.</li>"
            + "<li>The <b>search box</b> under them finds devices and saved setups as you type. See <a href=\"topic:device-library-search\">Search the Device Library</a>.</li>"
            + "<li>The <b>list</b>: one row per device, with its saved setups under it. The built-in inputs come last, under their own heading.</li>"
            + "<li>The <b>details</b>: the name, the description, what it holds, and buttons for what you can do with it.</li>"
            + "<li>The message line above the status bar says how the last change went and lists anything to check: plain when it worked, red when it failed. After a delete it ends with an <b>Undo</b> link. A message stays until the next one.</li>"
            + "<li>The <b>status bar</b> shows how many devices and saved setups there are, how many autosaves are kept per stick, the library's size on disk (for example \"Library: 48 MB\"), the <b>Undo</b> and <b>Redo</b> buttons with the last change beside them (see <a href=\"topic:device-library-undo\">Undo and redo a change</a>) and the library folder.</li>"
            + "</ul>"
            + "<p>The menus:</p>"
            + "<ul>"
            + "<li><b>File</b>: <b>Import Device Pack…</b>, <b>Export Saved Setup…</b>, <b>Open Library Folder</b>, <b>Close</b>.</li>"
            + "<li><b>Edit</b>: <b>Undo</b> (<b>Ctrl+Z</b>), <b>Redo</b> (<b>Ctrl+Y</b>), <b>Rename…</b> (<b>F2</b>), <b>Delete…</b>, <b>Tidy Library…</b>.</li>"
            + "<li><b>Device</b>: <b>Save to Device Library…</b>, <b>Copy to Another Stick…</b>, <b>Swap with Another Stick…</b>, <b>Change vJoy Output…</b>.</li>"
            + "<li><b>View</b>: <b>Connected</b>, <b>Not Connected</b>, <b>Deleted</b> and <b>Autosaves</b> (the same as the filters), <b>Expand All</b>, <b>Collapse All</b>, <b>Search…</b> (<b>Ctrl+F</b>).</li>"
            + "<li><b>Settings</b>: <b>Device Library Settings…</b>.</li>"
            + "<li><b>Help</b>: <b>Help</b> (<b>F1</b>).</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The menus show only what you can use now: an item that doesn't apply is left out. For example, <b>Swap with Another Stick…</b> shows only when a stick that is plugged in is selected.</li>"
            + "<li>Right-click a row, or the empty space in the list, for a menu of what you can do there.</li>"
            + "</ul>",
            ["device-library-menus", "device-library-filters"]),
        t("device-library-menus", "Getting started", "Right-click menus",
            "<p>Each row has a right-click menu with what you can do with it now.</p>"
            + "<p>Right-clicking a row selects it first, as a click does (it is highlighted and its details show), then opens its menu. The <b>Menu</b> key or <b>Shift+F10</b> opens the same menu on the selected row. Right-clicking the empty space in the list opens the list's own menu.</p>"
            + "<p>A device's menu:</p>"
            + "<ul>"
            + "<li><b>Copy to Another Stick…</b> (from its current settings), <b>Swap with Another Stick…</b> (when it is plugged in), <b>Change vJoy Output…</b>, <b>Save to Device Library…</b> and <b>Export Current Setup…</b>.</li>"
            + "<li><b>Rename…</b> (<b>F2</b>) and <b>Edit Description</b>, which puts the cursor in its description.</li>"
            + "<li><b>Open Module Setup…</b>, <b>Open Button Map</b> and <b>Show on Home</b>, for a stick with a card on Home (plugged in, or set up here). They open in the main window.</li>"
            + "<li><b>Show in History</b>: <b>Tools › History</b>, showing only this device's changes.</li>"
            + "<li><b>Expand</b> or <b>Collapse</b>, when it has saved setups.</li>"
            + "<li>The delete items, by its state: <b>Remove from Library…</b> when it isn't connected; <b>Clear Setup…</b> and <b>Delete Saved Setups…</b> when it is.</li>"
            + "</ul>"
            + "<p>A saved setup's menu: <b>Copy to Another Stick…</b>, <b>Restore to This Stick…</b> (when its stick is plugged in), <b>Export…</b>, <b>Rename…</b>, <b>Edit Description</b>, <b>Show in History</b> (its device's changes), <b>Keep This Autosave</b> (autosaves only) and <b>Delete…</b>.</p>"
            + "<p>A built-in input's menu: <b>Save to Device Library…</b>, <b>Restore…</b>, <b>Export…</b>, <b>Rename…</b> and <b>Edit Description</b>. See <a href=\"topic:device-library-built-in\">Built-in inputs</a>.</p>"
            + "<p>The empty space's menu: <b>Import Device Pack…</b>, <b>Expand All</b>, <b>Collapse All</b> and <b>Device Library Settings…</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Every menu has small <b>Undo</b> and <b>Redo</b> buttons beside its title, the same as <b>Edit › Undo</b> and <b>Edit › Redo</b>.</li>"
            + "<li>A menu shows only what you can do now: an item that doesn't apply, or that has to wait while a change runs, is left out.</li>"
            + "<li>The menu's title names the device and its state, for example \"Left throttle · Connected\" or \"Old Warthog stick · Deleted\".</li>"
            + "<li>The delete items are red, and each asks first, naming exactly what goes, for example \"Remove Old Warthog stick and its 4 saved setups from the Library?\" (see <a href=\"topic:device-library-delete\">Delete or remove from the Device Library</a>). Rest the pointer on one to see what it does: <b>Clear Setup…</b> \"Its settings go; the stick stays plugged in\", <b>Delete Saved Setups…</b> \"Only the saved setups go; its settings stay\", <b>Remove from Library…</b> \"Gone from the Library, with its saved setups\".</li>"
            + "</ul>",
            ["device-library-delete", "device-library-undo", "device-library-history"]),

        // ---- Devices and saved setups --------------------------------------
        t("device-library-devices", "Devices and saved setups", "Devices",
            "<p>Each device row shows its name, its description, how many saved setups it has, and its state:</p>"
            + "<ul>"
            + "<li><b>Connected</b>: plugged in now.</li>"
            + "<li><b>Not connected</b>: set up here but unplugged, or a device that came only from someone else's Device Pack. You can copy from it, never to it.</li>"
            + "<li><b>Deleted</b>: removed with Delete Device on Home or Delete File in Module Setup since the Device Library has existed. Its autosave is kept under it. Sticks deleted before that are not listed.</li>"
            + "</ul>"
            + "<p>Select a device to see its name, description and state, its inputs (for example \"32 buttons, 6 axes, 1 hat\") and when it was last seen. The buttons under its details are <b>Save to Device Library…</b>, <b>Copy to Another Stick…</b>, <b>Swap with Another Stick…</b>, <b>Change vJoy Output…</b>, and the red <b>Remove from Library…</b> (not connected) or <b>Delete Saved Setups…</b> (connected).</p>"
            + "<p>Select the caret beside a device, or double-click the device, to show or hide its saved setups.</p>",
            ["device-library-saved-setups", "device-library-built-in", "device-library-twins"]),
        t("device-library-built-in", "Devices and saved setups", "Built-in inputs",
            "<p>The program's built-in inputs, Keyboard, OSC and the Logical Device, are listed last, under the <b>BUILT-IN INPUTS</b> heading. They are part of the program, so they are never plugged in, unplugged or removed.</p>"
            + "<ul>"
            + "<li>Their menu and buttons have only <b>Save to Device Library…</b>, <b>Restore…</b> (puts back their newest saved setup), <b>Export…</b>, <b>Rename…</b> and <b>Edit Description</b>.</li>"
            + "<li>They need nothing plugged in, so Restore always works. It brings back the saved setup: its settings in the profiles it came from, and for the Logical Device its layout and picture too. An autosave is kept first, and <b>Edit › Undo</b> takes the whole Restore back in one step.</li>"
            + "<li>Every profile uses the one Logical Device, so keep its other layouts here as saved setups. To bring in a Logical Device pack, choose <b>File › Import Device Pack…</b> (it is filed under the Logical Device), then <b>Restore…</b>.</li>"
            + "<li>They can't be copied, swapped, cleared or removed, and they have no state badge.</li>"
            + "<li>The filters never hide them; a search that matches none of them does.</li>"
            + "</ul>",
            ["device-library-devices", "device-library-menus"]),
        t("device-library-saved-setups", "Devices and saved setups", "Saved setups",
            "<p>A saved setup is a stored copy of a device's settings and bindings. A device's saved setups are listed under it, newest first.</p>"
            + "<p>A save mark shows the ones that are yours; an autosave mark shows the ones the program kept. The line under each name says how it was kept: <b>Saved by you</b>, <b>Kept automatically</b>, <b>Was an autosave, now yours</b>, or which pack it came from.</p>"
            + "<p>A saved setup holds any of these parts:</p>"
            + "<ul>"
            + "<li><b>Setup</b>: the module file's claims and friendly names.</li>"
            + "<li><b>Button Map</b> and its photo.</li>"
            + "<li><b>Appearance</b>.</li>"
            + "<li><b>Calibration</b>.</li>"
            + "<li><b>Bindings</b>: the stick's actions from one profile, in the modes saved, and the vJoy outputs they send to.</li>"
            + "</ul>"
            + "<p>Select one to see its name and description, when and why it was kept, exactly what it holds under <b>Holds</b> (for example \"Bindings from DCS.xml · modes Default, Landing · 212 actions\" and \"Sends to vJoy 1 (38 inputs)\"), a preview of its Button Map photo, and its <b>Activity</b>: when it was saved, when its description was edited, and which sticks it was copied to. The buttons under the details are <b>Copy to Another Stick…</b>, <b>Swap with Another Stick…</b>, <b>Change vJoy Output…</b>, <b>Export…</b> and <b>Delete…</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Activity covers only that saved setup; <b>Tools › History</b> keeps every saved change in the program.</li>"
            + "<li>A stick whose module file was damaged can still be kept: its saved setup holds <b>Setup (damaged file, kept as is)</b>. That file is never put on another stick; only its bindings can be copied.</li>"
            + "</ul>",
            ["device-library-save", "device-library-autosaves", "device-library-copy"]),
        t("device-library-rename", "Devices and saved setups", "Rename a device or saved setup",
            "<p>Every device and every saved setup has a name and a description you can change.</p>"
            + "<ol>"
            + "<li>Select the row.</li>"
            + "<li>Choose <b>Edit › Rename…</b>, press <b>F2</b>, or select the pencil beside the name.</li>"
            + "<li>Type the new name and press <b>Enter</b>. <b>Esc</b> keeps the old one.</li>"
            + "</ol>"
            + "<p>To change the description, edit it where it shows, in the box under the name (\"Add a description\" when it is empty), or choose <b>Edit Description</b>. It is kept when you select elsewhere or press <b>Esc</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A stick set up here has one name: renaming it in the Device Library renames its card on Home, and the other way round.</li>"
            + "<li>Renaming or describing an autosave makes it yours, so the autosave limit never removes it.</li>"
            + "</ul>",
            ["device-library-twins", "device-library-keep-autosave"]),
        t("device-library-save", "Devices and saved setups", "Save a setup to the Device Library",
            "<p>Keep a saved setup of your own to come back to later.</p>"
            + "<ol>"
            + "<li>Select a device.</li>"
            + "<li>Choose <b>Save to Device Library…</b> from the Device menu, its right-click menu or the button in its details.</li>"
            + "<li>Tick the profiles whose bindings to keep. The open profile is marked \"(open)\".</li>"
            + "<li>Press <b>Save</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>It keeps the stick's module file as it is now, and you get one saved setup per ticked profile, named after the profile. Rename it and add a description afterwards.</li>"
            + "<li>When no profile has bindings for the stick, only the module file is kept.</li>"
            + "<li>The device needs settings to save: a stick set up here or plugged in now, or a built-in input.</li>"
            + "</ul>",
            ["device-library-saved-setups", "device-library-rename", "device-library-export"]),

        // ---- Autosaves -----------------------------------------------------
        t("device-library-autosaves", "Autosaves", "When autosaves are kept",
            "<p>The program keeps an autosave of a stick by itself, without asking, whenever something is about to replace or remove its settings. Autosaves are always on: they are your way back.</p>"
            + "<ul>"
            + "<li><b>Delete Device</b> on Home: \"Autosave: stick deleted\".</li>"
            + "<li><b>Delete File</b> in Module Setup: \"Autosave: module file deleted\" (the setup only).</li>"
            + "<li>Before <b>Copy</b> changes the target stick: \"Autosave: before Copy from Old Warthog\".</li>"
            + "<li>Before <b>Swap</b>, one of each stick: \"Autosave: before Swap with Right stick\".</li>"
            + "<li>Before <b>Change vJoy Output</b>: \"Autosave: before Change vJoy Output (vJoy 1 → 2)\".</li>"
            + "<li>Before a <b>Device Pack</b> is imported onto the stick from Home: \"Autosave: before Device Pack My F-16\" (the pack's file name).</li>"
            + "<li>Before <b>Restore to This Stick…</b>: \"Autosave: before Restore of DCS F-16\".</li>"
            + "<li>Before <b>Undo</b> puts back a Copy, Swap, Change vJoy Output or Restore: \"Autosave: before Undo\".</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>An autosave holds everything the stick has: its module file and pictures, and its bindings in every mode from every profile the change touches.</li>"
            + "<li>If an autosave can't be written or read back, the change doesn't run and the message says why.</li>"
            + "</ul>",
            ["device-library-autosave-limit", "device-library-keep-autosave", "device-library-delete-device"]),
        t("device-library-autosave-limit", "Autosaves", "How many autosaves are kept",
            "<p>Only the newest 10 autosaves per stick are kept; when a new one is kept, the oldest goes.</p>"
            + "<ul>"
            + "<li>To change the number, choose <b>Settings › Device Library Settings…</b> and set \"Keep the newest … autosaves per stick\". The status bar shows the number in use.</li>"
            + "<li>Your own saved setups are never removed this way, nor is an autosave you renamed, described or kept with <b>Keep This Autosave</b>.</li>"
            + "<li>To hide autosaves from the list, untick the <b>Autosaves</b> filter.</li>"
            + "</ul>",
            ["device-library-keep-autosave", "device-library-settings"]),
        t("device-library-keep-autosave", "Autosaves", "Keep an autosave",
            "<p>Make an autosave yours so the autosave limit never removes it.</p>"
            + "<ol>"
            + "<li>Right-click the autosave.</li>"
            + "<li>Choose <b>Keep This Autosave</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Its line then reads <b>Was an autosave, now yours</b>, it shows a save mark, and its Activity says \"Kept as your own\".</li>"
            + "<li>Renaming or describing an autosave does the same.</li>"
            + "<li>The item shows only on autosaves that are not yours yet.</li>"
            + "</ul>",
            ["device-library-autosave-limit", "device-library-rename"]),
        t("device-library-delete-device", "Autosaves", "Delete Device and Delete File",
            "<p>Deleting a stick or its module file elsewhere in the program always keeps an autosave in the Device Library first.</p>"
            + "<ul>"
            + "<li><b>Delete Device</b> on Home keeps an autosave of the stick: its module file, its pictures and its bindings in every mode. There is no question about a copy. The stick then shows in the Device Library as <b>Deleted</b>, with its autosave under it.</li>"
            + "<li><b>Delete File</b> in Module Setup keeps an autosave of the module file (\"Autosave: module file deleted\").</li>"
            + "</ul>"
            + "<p>To use a deleted stick's setup again, select its autosave and choose <b>Copy to Another Stick…</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Both work even when the module file is damaged: the damaged file is kept exactly as it is.</li>"
            + "<li>In the Device Library, <b>Clear Setup…</b> on a connected stick is the same as Delete Device, and <b>Remove from Library…</b> runs Delete Device first for a stick whose module file is still here.</li>"
            + "</ul>",
            ["device-library-autosaves", "device-library-delete", "home-devices-delete-device"]),

        // ---- Changing sticks -----------------------------------------------
        t("device-library-copy", "Changing sticks", "Copy a setup to another stick",
            "<p><b>Copy to Another Stick…</b> puts a saved setup, or a stick's current settings, on a stick plugged in now.</p>"
            + "<ol>"
            + "<li>Select a saved setup or a device, then choose <b>Copy to Another Stick…</b>. Double-clicking a saved setup does the same.</li>"
            + "<li>Check <b>From</b>: the saved setup, or \"current settings\" for a device that is set up here or plugged in. For a device with neither, its newest saved setup is used.</li>"
            + "<li>Choose the <b>To</b> stick. Only sticks plugged in now are listed.</li>"
            + "<li>Under <b>What to copy</b>, tick the parts. Setup, Button Map, Appearance and Bindings start ticked; Calibration does not. Parts the saved setup doesn't hold are greyed out.</li>"
            + "<li>Under <b>Bindings go into these profiles</b>, tick the profiles. Every profile with bindings for either stick is listed; only the open profile starts ticked. <b>Tick All</b> ticks them all.</li>"
            + "<li>Under <b>Modes</b>, tick the modes. The ticked modes replace the target stick's bindings in those modes.</li>"
            + "<li>Press <b>Copy</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A warning box lists what won't copy because the target stick lacks it (buttons, hats, axes and the bindings on them). Those are left out; the rest copies.</li>"
            + "<li>An autosave of the target stick is kept first, and <b>Edit › Undo</b> puts it back. The saved setup and the stick it came from never change.</li>"
            + "<li>A stick that was never plugged in here can be copied from, never to.</li>"
            + "<li>To change which parts start ticked, see <a href=\"topic:device-library-settings\">Device Library Settings</a>.</li>"
            + "</ul>",
            ["device-library-restore", "device-library-profiles", "device-library-undo"]),
        t("device-library-restore", "Changing sticks", "Restore a saved setup to its stick",
            "<p><b>Restore to This Stick…</b> puts a saved setup back on the stick it belongs to, without choosing a To stick. That stick must be plugged in.</p>"
            + "<ol>"
            + "<li>Right-click the saved setup.</li>"
            + "<li>Choose <b>Restore to This Stick…</b>.</li>"
            + "<li>Press <b>Restore</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>It works as Copy does, with every part the saved setup holds (Calibration too, as it is the same stick), into the profiles it came from that are still there, in every mode it has.</li>"
            + "<li>An autosave of the stick is kept first (\"Autosave: before Restore of DCS F-16\"), and <b>Edit › Undo</b> puts it back.</li>"
            + "<li>To choose the parts, profiles and modes, or to put it on another stick, use <a href=\"topic:device-library-copy\">Copy a setup to another stick</a>.</li>"
            + "<li>On a built-in input (Keyboard, OSC, the Logical Device), <b>Restore…</b> puts back its newest saved setup with nothing plugged in, the Logical Device's layout and picture too. See <a href=\"topic:device-library-built-in\">Built-in inputs</a>.</li>"
            + "</ul>",
            ["device-library-copy", "device-library-undo"]),
        t("device-library-swap", "Changing sticks", "Swap two sticks",
            "<p><b>Swap with Another Stick…</b> lets two sticks trade places: each gets the other's settings. Both must be plugged in.</p>"
            + "<ol>"
            + "<li>Select a stick and choose <b>Swap with Another Stick…</b>.</li>"
            + "<li>Choose the other stick.</li>"
            + "<li>Under <b>What trades places</b>, tick the parts: the same as Copy (Setup, Button Map, Appearance, Calibration, Bindings).</li>"
            + "<li>Under <b>Swap bindings in these profiles</b>, tick the profiles. The open profile starts ticked; <b>Tick All</b> ticks them all.</li>"
            + "<li>Press <b>Swap</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Bindings swap with everything that points at the sticks: device references inside actions and script variables swap too.</li>"
            + "<li>The warning box (\"Some settings have nowhere to go\") lists, both ways, what one stick has that the other lacks; those bindings stay where they were. It also lists actions elsewhere that refer to a control one stick lacks, for example a Condition checking Left stick Axis 3 when Right stick has no Axis 3. That reference still moves with the swap, so check it.</li>"
            + "<li>The Keyboard, Logical Device, OSC and the Xbox controller can't be swapped, and a stick can't be swapped with itself.</li>"
            + "<li>An autosave of each stick is kept first, and <b>Edit › Undo</b> puts both back.</li>"
            + "</ul>",
            ["device-library-copy", "device-library-output", "device-library-profiles"]),
        t("device-library-output", "Changing sticks", "Change which vJoy a stick sends to",
            "<p><b>Change vJoy Output…</b> keeps a stick's bindings and changes only which vJoy they send to, for example so a game sees two sticks the other way round.</p>"
            + "<ol>"
            + "<li>Select a stick and choose <b>Change vJoy Output…</b>.</li>"
            + "<li>Under <b>Change it in these profiles</b>, tick the profiles. The open profile starts ticked; <b>Tick All</b> ticks them all.</li>"
            + "<li>Each vJoy the stick sends to has a row, such as \"vJoy 1 (38 inputs) → vJoy 2\". Pick where each sends; the row says <b>changes</b> or <b>stays</b>.</li>"
            + "<li>Press <b>Change</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>When another stick already sends to the vJoy you picked, a tick box offers to move it the other way, for example \"Also move Right stick from vJoy 2 to vJoy 1 (swap them)\".</li>"
            + "<li>The <b>Check these</b> box lists bindings that would send to an output the new vJoy's output module doesn't claim (they would send nothing), and macros and user scripts that name a vJoy number. Those are not changed: check them yourself.</li>"
            + "<li>An autosave of each stick that changes is kept first, and <b>Edit › Undo</b> puts them back.</li>"
            + "</ul>",
            ["device-library-swap", "device-library-profiles"]),
        t("device-library-profiles", "Changing sticks", "Profiles that aren't open",
            "<p>Copy, Swap and Change vJoy Output change the profiles you tick, open or not.</p>"
            + "<ul>"
            + "<li>The <b>open profile</b> is changed in memory. To keep the change, save it with <b>File › Save Profile</b> in the main window.</li>"
            + "<li>A ticked profile that isn't open is changed and saved on disk straight away. History keeps each save, so the whole file can be restored from <b>Tools › History</b>.</li>"
            + "<li>A profile that can't be read or written is named in the message and left as it was; the others still change.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The autosave kept first holds the stick's bindings from every profile the change touches, so Undo puts them all back.</li>"
            + "</ul>",
            ["device-library-copy", "device-library-undo"]),
        t("device-library-busy", "Changing sticks", "When the window is busy",
            "<p>Reading profiles, keeping autosaves and writing files run in the background, so the window keeps responding.</p>"
            + "<ul>"
            + "<li>The dialogs show <b>Reading the profiles…</b> and <b>Checking…</b> while they work out the profiles and the warnings. Wait for the warnings before you press Copy, Swap or Change.</li>"
            + "<li>While a change runs, the status bar shows <b>Working…</b>, and the menu items that would start another change are left out of the menus, and the buttons that would start one are greyed out. One change runs at a time.</li>"
            + "<li>A row that is being changed shows a small busy mark until the change is done.</li>"
            + "</ul>",
            ["device-library-qa-greyed"]),

        // ---- Undo and Redo -------------------------------------------------
        t("device-library-undo", "Undo and Redo", "Undo and redo a change",
            "<p><b>Edit › Undo</b> (<b>Ctrl+Z</b>) takes back the last change made in the Device Library; <b>Edit › Redo</b> (<b>Ctrl+Y</b>) makes it again. They work on every Library change: Copy, Swap, Change vJoy Output, Restore, Save, Remove from Library, Delete, Clear Setup, Rename and the others.</p>"
            + "<ul>"
            + "<li>Rest the pointer on <b>Undo</b> or <b>Redo</b> to see the change it acts on, for example \"Remove HID Remapper ACHB\". In the Edit menu each item shows only when there is something to undo or redo.</li>"
            + "<li>The status bar, after the library's size, has <b>Undo</b> and <b>Redo</b> buttons that do the same; each is greyed out when there is nothing to undo or redo. Beside them it shows <b>Last change:</b> and the change Undo would take back or, right after an Undo, <b>Undone:</b> and the change Redo would put back. It shows nothing until you make a change. A long name is cut short with …; rest the pointer on it to read it all.</li>"
            + "<li>Undo again to go further back through this session's Library changes, newest first; Redo goes forward again. A new change clears Redo.</li>"
            + "<li>The same <b>Undo</b> and <b>Redo</b> sit beside the title of every right-click menu.</li>"
            + "<li>After <b>Remove from Library…</b>, <b>Delete…</b> or <b>Clear Setup…</b>, the message line ends with an <b>Undo</b> link that does the same.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>While you type in a box, <b>Ctrl+Z</b> and <b>Ctrl+Y</b> undo the typing instead.</li>"
            + "<li>Each change is one entry in <b>Tools › History</b>, so older changes, and those from before the program started, can be put back there. See <a href=\"topic:device-library-history\">See a device's changes in History</a>.</li>"
            + "</ul>",
            ["device-library-history", "device-library-delete", "device-library-qa-go-back"]),
        t("device-library-history", "Undo and Redo", "See a device's changes in History",
            "<p><b>Tools › History</b> keeps every Library change, also from earlier sessions, and can put any of them back.</p>"
            + "<ol>"
            + "<li>Right-click a device or one of its saved setups.</li>"
            + "<li>Choose <b>Show in History</b>. History opens in the main window, showing only that device's changes.</li>"
            + "<li>Select a change and use <b>Restore Before</b> to put back how it was.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Each Library action is one History entry named for what it did, for example \"Removed Old Warthog stick from the Device Library\", \"Deleted saved setup DCS F-16\" or \"Saved Left throttle to the Device Library\". Restore puts back every file and setting it changed.</li>"
            + "</ul>",
            ["device-library-undo", "device-library-delete", "tools-history"]),

        // ---- Finding things ------------------------------------------------
        t("device-library-search", "Finding things", "Search the Device Library",
            "<p>The search box finds devices and saved setups as you type, in any case.</p>"
            + "<ol>"
            + "<li>Select the search box, press <b>Ctrl+F</b>, or choose <b>View › Search…</b>.</li>"
            + "<li>Type part of what you are looking for. The line under the box says \"N found\" or \"Nothing matches\".</li>"
            + "<li>To clear the search, select × in the box, or press <b>Esc</b>, which also leaves the box.</li>"
            + "</ol>"
            + "<p>It finds:</p>"
            + "<ul>"
            + "<li>device names and descriptions;</li>"
            + "<li>saved setup names and descriptions, and autosave reasons (\"stick deleted\", \"before Swap\");</li>"
            + "<li>what a saved setup holds (Setup, Button Map, Appearance, Calibration, Bindings);</li>"
            + "<li>profile names and mode names;</li>"
            + "<li>vJoy numbers (\"vJoy 2\").</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A device that has a matching saved setup opens to show it.</li>"
            + "</ul>",
            ["device-library-filters", "device-library-select"]),
        t("device-library-filters", "Finding things", "Filter the list",
            "<p>The filters <b>Connected</b>, <b>Not connected</b>, <b>Deleted</b> and <b>Autosaves</b> choose which rows the list shows.</p>"
            + "<ul>"
            + "<li>Each ticked filter shows that kind, so you can, for example, hide deleted sticks and autosaves. The View menu has the same four.</li>"
            + "<li><b>View › Expand All</b> shows every device's saved setups; <b>Collapse All</b> hides them.</li>"
            + "<li>The filters never hide the built-in inputs.</li>"
            + "</ul>",
            ["device-library-search", "device-library-window"]),
        t("device-library-select", "Finding things", "Select several rows",
            "<p>Select several rows to delete or remove them with one question.</p>"
            + "<ul>"
            + "<li>Ctrl-click adds a row to the selection or takes it away; Shift-click selects every row from the last one you selected to this one.</li>"
            + "<li>You can select several saved setups, or several devices, but not both: selecting a row of the other kind starts a new selection.</li>"
            + "<li><b>Delete…</b> (saved setups) or <b>Remove from Library…</b> (devices that aren't connected) acts on all of them, after one question that lists them. It is in the right-click menu, in <b>Edit › Delete…</b> and on the red <b>Delete…</b> button.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Devices are removed together only when none of them is connected.</li>"
            + "<li>Copy, Swap, Change vJoy Output, Restore, Rename and Export act on one row only: while several rows are selected they are left out of the menus and greyed out under the details.</li>"
            + "<li>When a plugged-in stick is among the selected devices, the right-click menu shows <b>Remove from Library…</b> greyed out. Rest the pointer on it to see why: \"Remove from Library works only on devices that aren't plugged in\".</li>"
            + "</ul>",
            ["device-library-delete"]),

        // ---- Sharing -------------------------------------------------------
        t("device-library-export", "Sharing", "Export a saved setup",
            "<p>Export writes a saved setup as a Device Pack (.zip) wherever you choose, ready to give to someone else.</p>"
            + "<ol>"
            + "<li>Select a saved setup.</li>"
            + "<li>Choose <b>Export…</b>, or <b>File › Export Saved Setup…</b>.</li>"
            + "<li>Choose where to save the file. The chooser opens in the folder you last used for a Device Pack.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>To share a stick's settings as they are now, right-click the device and choose <b>Export Current Setup…</b>. It writes a Device Pack of its current settings without keeping a saved setup first. It needs a stick set up here or plugged in.</li>"
            + "<li><b>File › Open Library Folder</b> opens the library's folder in File Explorer.</li>"
            + "</ul>",
            ["device-library-import", "device-library-qa-share"]),
        t("device-library-import", "Sharing", "Import a Device Pack",
            "<p>Importing adds a Device Pack (.zip) to the Device Library as a saved setup. Nothing changes on your sticks.</p>"
            + "<ol>"
            + "<li>Choose <b>File › Import Device Pack…</b> and pick the file, or drop the file on the window. The chooser opens in the folder you last used for a Device Pack.</li>"
            + "<li>To use it, select the new saved setup and choose <b>Copy to Another Stick…</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>It goes under the device it was made from when that device is in the Device Library; otherwise under a new <b>Not connected</b> device named after the pack.</li>"
            + "<li>The saved setup says where it came from (\"From Sam's pack\") and takes the pack's note as its description.</li>"
            + "</ul>",
            ["device-library-export", "device-library-copy", "home-devices-device-pack"]),

        // ---- Settings and tidying ------------------------------------------
        t("device-library-settings", "Settings and tidying", "Device Library Settings",
            "<p><b>Settings › Device Library Settings…</b> holds the Device Library's own settings:</p>"
            + "<ul>"
            + "<li><b>Keep the newest … autosaves per stick</b> (10 to start). Setups you saved, renamed or described are never removed.</li>"
            + "<li><b>Copy and Swap tick by default</b>: which parts start ticked (Setup, Button Map, Appearance and Bindings; Calibration off).</li>"
            + "<li><b>Library folder</b>: where the Device Library is kept. <b>Move…</b> picks another folder; the library moves there when you press <b>OK</b>.</li>"
            + "</ul>",
            ["device-library-autosave-limit", "device-library-tidy"]),
        t("device-library-tidy", "Settings and tidying", "Tidy the Device Library",
            "<p>Tidy Library frees space by removing old autosaves and empty deleted devices. The status bar shows how much space the library takes.</p>"
            + "<ol>"
            + "<li>Choose <b>Edit › Tidy Library…</b>.</li>"
            + "<li>Set the number of months: autosaves older than that are listed (6 to start), with deleted devices that have no saved setups. Each item shows its size and is ticked.</li>"
            + "<li>Untick what you want to keep.</li>"
            + "<li>Press the red <b>Remove from Library</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The window is the question: the line under the list says how many items are ticked and their size, and nothing is removed until you press Remove from Library. No second question follows.</li>"
            + "<li><b>Cancel</b> has the focus: <b>Enter</b> and <b>Esc</b> both cancel, so only a click on <b>Remove from Library</b> removes anything.</li>"
            + "<li>You can restore it from Tools › History, and right after, the <b>Undo</b> link on the message line does too.</li>"
            + "<li>Apart from this and the autosave limit, nothing in the library is removed without asking.</li>"
            + "</ul>",
            ["device-library-settings", "device-library-delete"]),
        t("device-library-delete", "Settings and tidying", "Delete or remove from the Device Library",
            "<p>Every delete asks first and names exactly what goes. What it does depends on what is selected:</p>"
            + "<ul>"
            + "<li>A saved setup: <b>Delete…</b> removes it from the Device Library.</li>"
            + "<li>A device that isn't connected (unplugged, deleted, or from a pack): <b>Remove from Library…</b> removes the device entirely: its module file and folder (pictures, Button Map photo, recovery copies), its saved setups and autosaves, its friendly name, its Home card settings and its calibration. Its bindings leave the open profile (kept only if you save that profile). You can restore it from Tools › History. If Delete Device can't run, nothing is removed and the message says why.</li>"
            + "<li>A connected stick: <b>Clear Setup…</b> is Delete Device on Home: an autosave is kept in the Device Library first, then its module file and its bindings go, and the stick stays plugged in with no setup. <b>Delete Saved Setups…</b> removes only its saved setups; the stick keeps its settings.</li>"
            + "</ul>"
            + "<p>To delete, select the row and choose the item from its right-click menu, choose <b>Edit › Delete…</b>, press the red button under the details, or press the <b>Delete</b> key.</p>"
            + "<p>The question's title names what goes, for example \"Remove Old Warthog stick and its 4 saved setups from the Library?\", and its last line is \"You can restore it from Tools › History.\" Its red button is named for the action: <b>Delete Saved Setup</b>, <b>Delete Saved Setups</b>, <b>Remove from Library</b> or <b>Clear Setup</b>. <b>Cancel</b> has the focus, and <b>Enter</b> and <b>Esc</b> both cancel, so only a click on the red button goes ahead.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The <b>Delete</b> key asks the same question: Delete… on a saved setup, Remove from Library… on a device that isn't connected. It does nothing on a connected stick or a built-in input, or while you type in a box.</li>"
            + "<li>On a device, the red button and <b>Edit › Delete…</b> run Remove from Library… or Delete Saved Setups… by its state. Clear Setup… is only in the device's right-click menu.</li>"
            + "<li>Each delete is one entry in <b>Tools › History</b>, however many files it touched, for example \"Removed Old Warthog stick from the Device Library\". Right after, the <b>Undo</b> link in the message line (or <b>Edit › Undo</b>) puts it all back.</li>"
            + "<li>Clear Setup… also keeps an autosave under the stick, ready for <b>Restore to This Stick…</b>.</li>"
            + "<li>To delete several rows with one question, see <a href=\"topic:device-library-select\">Select several rows</a>.</li>"
            + "</ul>",
            ["device-library-undo", "device-library-history", "device-library-select"]),
        t("device-library-twins", "Settings and tidying", "Renamed and twin sticks",
            "<p>A stick's name in the Device Library is its name on Home. Rename it in either place and both change; dialogs, autosave names and the Undo item use that name.</p>"
            + "<p>Two sticks with the same name (twins) are told apart by a short id after the name, in the list and in the To lists: for example \"Right stick [EEEE0006]\". Rename one of them to tell them apart at a glance.</p>",
            ["device-library-rename"]),

        // ---- Common questions ----------------------------------------------
        t("device-library-qa-new-stick", "Common questions", "My stick broke: how do I put its setup on the new one?",
            "<p>Plug in the new stick. In the Device Library, open the old stick's row, select a saved setup (or its \"Autosave: stick deleted\" if you deleted it) and choose <b>Copy to Another Stick…</b> with the new stick as To. Untick Calibration unless the sticks are the same model. The warning box lists any controls the new stick doesn't have.</p>"
            + "<p>See <a href=\"topic:device-library-copy\">Copy a setup to another stick</a>.</p>",
            ["device-library-copy"]),
        t("device-library-qa-share", "Common questions", "How do I give my setup to a friend?",
            "<p>Select the saved setup and press <b>Export…</b>, then send the .zip. Your friend imports it with <b>File › Import Device Pack…</b> (or drops it on their Device Library) and copies it onto their stick. To share the stick's settings as they are now, right-click the device and choose <b>Export Current Setup…</b>.</p>"
            + "<p>See <a href=\"topic:device-library-export\">Export a saved setup</a>.</p>",
            ["device-library-export", "device-library-import"]),
        t("device-library-qa-cant-copy", "Common questions", "Why can't I copy to this stick?",
            "<p>Copy and Swap work only onto sticks plugged in now, so the To list shows nothing else. Plug the stick in and open the dialog again. A device that came from someone's pack has never been plugged in here: you can copy from it, not to it. Built-in inputs can't be copied to.</p>"
            + "<p>See <a href=\"topic:device-library-copy\">Copy a setup to another stick</a>.</p>",
            ["device-library-copy", "device-library-devices"]),
        t("device-library-qa-where", "Common questions", "Where did my old setup go?",
            "<ul>"
            + "<li>A deleted stick shows as <b>Deleted</b>, with its autosave under it. Make sure the Deleted and Autosaves filters are ticked and the search box is empty.</li>"
            + "<li>Clear Setup… keeps \"Autosave: stick deleted\" under the stick: right-click it and choose <b>Restore to This Stick…</b>.</li>"
            + "<li>Copy, Swap, Change vJoy Output, Restore and a Device Pack import keep an autosave first; search for the change (\"before Restore\").</li>"
            + "<li>Only the newest autosaves per stick are kept. Choose <b>Keep This Autosave</b>, or rename or describe one, to keep it for good.</li>"
            + "<li>Anything removed with Delete…, Delete Saved Setups… or Remove from Library…: <b>Edit › Undo</b> puts it back, or <b>Tools › History</b> for an older one.</li>"
            + "</ul>",
            ["device-library-autosaves", "device-library-filters", "device-library-history"]),
        t("device-library-qa-go-back", "Common questions", "How do I go back after a change?",
            "<p>Choose <b>Edit › Undo</b> (<b>Ctrl+Z</b>) to take back the last Library change, and again for the one before. For a change from before the program started, right-click the row, choose <b>Show in History</b> and restore it there. For a stick's earlier settings, right-click the autosave it kept and choose <b>Restore to This Stick…</b> (the stick must be plugged in). A profile that wasn't open was saved, so History can also restore the whole file.</p>"
            + "<p>See <a href=\"topic:device-library-undo\">Undo and redo a change</a>.</p>",
            ["device-library-undo", "device-library-history", "device-library-restore"]),
        t("device-library-qa-greyed", "Common questions", "Why are the buttons greyed out?",
            "<p>The window is busy: a dialog shows <b>Checking…</b>, or the status bar shows <b>Working…</b> while a change runs. Wait for it to finish. Otherwise the selection doesn't allow it: Swap with Another Stick… needs a stick that is plugged in, Export… needs a saved setup, and Save to Device Library… needs a stick set up here or plugged in. With several rows selected only delete works. The menus leave out what doesn't apply instead of greying it out; one exception is <b>Remove from Library…</b> with a plugged-in stick among several selected devices.</p>"
            + "<p>See <a href=\"topic:device-library-busy\">When the window is busy</a>.</p>",
            ["device-library-busy", "device-library-select"])
    ]
}

function t(id, section, title, body, related) {
    return { id: id, section: section, title: title, body: body, related: related || [] }
}
