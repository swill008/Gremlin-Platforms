// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help, chapter "Device Library" (01 S128, 10 S42, D-01-ONE-HELP).
// Written to claude/plans/help-style-guide.md: each topic opens with what
// it's for, then "How to", "What you see" and "Good to know" (empty
// sections left out); on-screen labels in bold, exactly as shown.

.pragma library

var chapter = { id: "device-library", title: "Device Library" }

function topics() {
    return [
        // ---- Getting started ------------------------------------------------
        t("device-library-about", "Getting started", "What the Device Library is",
            "<p>The <b>Device Library</b> keeps every device the program has known, with copies of their settings and bindings. You can always go back to an earlier copy.</p>"
            + "<p>Use it to:</p>"
            + "<ul>"
            + "<li>Put an old stick's setup on a new stick.</li>"
            + "<li>Let two sticks trade places.</li>"
            + "<li>Change which vJoy device a stick sends to. vJoy is the virtual joystick a game reads.</li>"
            + "</ul>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li><b>Devices</b>: every device the program knows.<ul>"
            + "<li>Sticks plugged in now.</li>"
            + "<li>Sticks set up here but unplugged.</li>"
            + "<li>Deleted sticks.</li>"
            + "<li>Sticks from someone else's device file.</li>"
            + "<li>The program's internal inputs: Keyboard, OSC and the Logical Device.</li>"
            + "</ul></li>"
            + "<li><b>Saved setups</b>: stored copies of a device's settings and bindings, each with a name and a description.</li>"
            + "<li>You keep saved setups of your own. The program keeps <b>autosaves</b> by itself, before anything replaces or removes a stick's settings.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Copying never changes the saved setup or the stick it came from.</li>"
            + "</ul>",
            ["device-library-open", "device-library-saved-setups", "device-library-autosaves"]),
        t("device-library-open", "Getting started", "Open the Device Library",
            "<p>The Device Library opens in its own window.</p>"
            + "<h4>How to</h4>"
            + "<ul>"
            + "<li>Choose <b>Device Library</b> on the toolbar <a href=\"show:toolbar/Device Library\">Show me ›</a>.</li>"
            + "<li>Or, in the main window, choose <b>Tools › Device Setup › Device Library…</b> <a href=\"open:tools.deviceLibrary\">Open ›</a>.</li>"
            + "<li>Or right-click a stick's card on Home. In its Device section, choose <b>Copy Setup to Another Stick…</b>, <b>Swap with Another Stick…</b> or <b>Change vJoy Output…</b>.<ul>"
            + "<li>The window then opens on that stick, with that dialog open.</li>"
            + "</ul></li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>These three card items aren't on vJoy, Xbox, Keyboard, OSC or Logical Device cards.</li>"
            + "<li>In the Device Library, <b>Help</b> or <b>F1</b> opens this chapter of Help. <b>View Full Help</b> shows the whole book.</li>"
            + "</ul>",
            ["device-library-about", "device-library-window"]),
        t("device-library-window", "Getting started", "The Device Library window",
            "<p>The left side lists the devices. The right side shows the details of what you select.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li><b>Filters</b> at the top: <b>Connected</b>, <b>Not connected</b>, <b>Deleted</b> and <b>Autosaves</b>. A ticked filter shows that kind of row. Untick it to hide them.</li>"
            + "<li>The <b>search box</b> under them finds devices and saved setups as you type. See <a href=\"topic:device-library-search\">Search the Device Library</a>.</li>"
            + "<li>The <b>list</b>: one row per device, with its saved setups under it. The internal inputs come last, under their own heading.</li>"
            + "<li>The <b>details</b>: the name, the description, what it holds, and buttons for what you can do with it.</li>"
            + "<li>The message line above the status bar says how the last change went: plain when it worked, red when it failed.<ul>"
            + "<li>It lists anything to check, and after a delete it ends with an <b>Undo</b> link.</li>"
            + "<li>A message stays until the next one.</li>"
            + "</ul></li>"
            + "<li>The <b>status bar</b> shows:<ul>"
            + "<li>How many devices and saved setups there are.</li>"
            + "<li>How many autosaves are kept per stick.</li>"
            + "<li>The library's size on disk, for example \"Library: 48 MB\".</li>"
            + "<li>The <b>Undo</b> and <b>Redo</b> buttons, with the last change beside them. See <a href=\"topic:device-library-undo\">Undo and redo a change</a>.</li>"
            + "<li>The library folder.</li>"
            + "</ul></li>"
            + "</ul>"
            + "<h4>Menus</h4>"
            + "<table>"
            + "<tr><th>Menu</th><th>What it has</th></tr>"
            + "<tr><td><b>File</b></td><td><b>Import Device…</b>, <b>Export Saved Setup…</b>, <b>Open Library Folder</b>, <b>Close</b></td></tr>"
            + "<tr><td><b>Edit</b></td><td><b>Undo</b> (<b>Ctrl+Z</b>), <b>Redo</b> (<b>Ctrl+Y</b>), <b>Rename…</b> (<b>F2</b>), <b>Delete…</b>, <b>Tidy Library…</b></td></tr>"
            + "<tr><td><b>Device</b></td><td><b>Save to Device Library…</b>, <b>Copy to Another Stick…</b>, <b>Swap with Another Stick…</b>, <b>Change vJoy Output…</b></td></tr>"
            + "<tr><td><b>View</b></td><td><b>Connected</b>, <b>Not Connected</b>, <b>Deleted</b> and <b>Autosaves</b> (the same as the filters), <b>Expand All</b>, <b>Collapse All</b>, <b>Search…</b> (<b>Ctrl+F</b>)</td></tr>"
            + "<tr><td><b>Settings</b></td><td><b>Device Library Settings…</b></td></tr>"
            + "<tr><td><b>Help</b></td><td><b>Help</b> (<b>F1</b>)</td></tr>"
            + "</table>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Drag the divider between the list and the details to change their widths. The program remembers where you put it.</li>"
            + "<li>The menus show only what you can use now: an item that doesn't apply is left out.<ul>"
            + "<li>For example, <b>Swap with Another Stick…</b> shows only when a plugged-in stick is selected.</li>"
            + "</ul></li>"
            + "<li>Right-click a row, or the empty space in the list, for a menu of what you can do there. See <a href=\"topic:device-library-menus\">Right-click menus</a>.</li>"
            + "<li>If a device's record can't be read, it is left out of the list and kept unchanged. A warning goes to the log.</li>"
            + "</ul>",
            ["device-library-menus", "device-library-filters"]),
        t("device-library-menus", "Getting started", "Right-click menus",
            "<p>Each row has a right-click menu with what you can do with it now. The empty space in the list has a menu of its own.</p>"
            + "<p>Right-clicking a row selects it first, as a click does, then opens its menu. The <b>Menu</b> key or <b>Shift+F10</b> opens the same menu on the selected row.</p>"
            + "<h4>A device</h4>"
            + "<ul>"
            + "<li><b>Copy to Another Stick…</b> (from its current settings), <b>Swap with Another Stick…</b> (when it is plugged in) and <b>Change vJoy Output…</b>.</li>"
            + "<li><b>Save to Device Library…</b> and <b>Export Current Setup…</b>.</li>"
            + "<li><b>Rename…</b> (<b>F2</b>), and <b>Edit Description</b>, which puts the cursor in its description.</li>"
            + "<li><b>Open Module Setup…</b>, <b>Open Device Mapping Editor</b> and <b>Show on Home</b> open in the main window. They show for a stick with a card on Home.</li>"
            + "<li><b>Show in History</b> opens <b>Tools › History</b>, showing only this device's changes.</li>"
            + "<li><b>Expand</b> or <b>Collapse</b>, when it has saved setups.</li>"
            + "<li>The delete items, by its state: <b>Remove from Library…</b> when it isn't connected; <b>Clear Setup…</b> and <b>Delete Saved Setups…</b> when it is.</li>"
            + "</ul>"
            + "<h4>A saved setup</h4>"
            + "<p><b>Copy to Another Stick…</b>, <b>Restore to This Stick…</b> (when its stick is plugged in), <b>Export…</b>, <b>Rename…</b>, <b>Edit Description</b>, <b>Show in History</b>, <b>Keep This Autosave</b> (autosaves only) and <b>Delete…</b>.</p>"
            + "<h4>An internal input</h4>"
            + "<p><b>Save to Device Library…</b>, <b>Restore…</b>, <b>Export…</b>, <b>Rename…</b> and <b>Edit Description</b>. See <a href=\"topic:device-library-built-in\">Internal inputs</a>.</p>"
            + "<h4>Empty space</h4>"
            + "<p><b>Import Device…</b>, <b>Expand All</b>, <b>Collapse All</b> and <b>Device Library Settings…</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Every menu has small <b>Undo</b> and <b>Redo</b> buttons beside its title. They work as <b>Edit › Undo</b> and <b>Edit › Redo</b> do.</li>"
            + "<li>An item that doesn't apply, or that must wait while a change runs, is left out. See <a href=\"topic:device-library-window\">The Device Library window</a>.</li>"
            + "<li>The menu's title names the device and its state, for example \"Left throttle · Connected\".</li>"
            + "<li>The delete items are red.</li>"
            + "<li>Each delete item asks first and names what goes, for example \"Remove Old Warthog stick and its 4 saved setups from the Library?\"</li>"
            + "<li>Rest the pointer on a delete item to see what it does. See <a href=\"topic:device-library-delete\">Delete or remove from the Device Library</a>.</li>"
            + "</ul>",
            ["device-library-delete", "device-library-undo", "device-library-history"]),

        // ---- Devices and saved setups --------------------------------------
        t("device-library-devices", "Devices and saved setups", "Devices",
            "<p>Each device row shows a small picture, the name, the description and how many saved setups it has. Its state is on the right.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li><b>Connected</b>: plugged in now.</li>"
            + "<li><b>Not connected</b>: set up here but unplugged, or a device that came only from someone else's device file. You can copy from it, never to it.</li>"
            + "<li><b>Deleted</b>: removed with <b>Delete Device</b> on Home or <b>Delete File</b> in Module Setup. Its autosave is listed under it.</li>"
            + "</ul>"
            + "<p>Select a device to see its name, description and state. The details also show its inputs, for example \"32 buttons, 6 axes, 1 hat\", and when it was last seen.</p>"
            + "<p>The buttons under the details:</p>"
            + "<ul>"
            + "<li><b>Save to Device Library…</b>: keep its settings as a saved setup.</li>"
            + "<li><b>Copy to Another Stick…</b>: put its settings on another stick.</li>"
            + "<li><b>Swap with Another Stick…</b>: let it trade places with another stick.</li>"
            + "<li><b>Change vJoy Output…</b>: change which vJoy device it sends to.</li>"
            + "<li><b>Export…</b>: grayed out on a device; select one of its saved setups to export it.</li>"
            + "<li>The red <b>Remove from Library…</b> (not connected) or <b>Delete Saved Setups…</b> (connected).</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Click the arrow beside a device, or double-click the device, to show or hide its saved setups.</li>"
            + "<li>The picture is the device's image, or the picture made from its device map. A device with neither shows its icon.</li>"
            + "</ul>",
            ["device-library-saved-setups", "device-library-built-in", "device-library-twins"]),
        t("device-library-built-in", "Devices and saved setups", "Internal inputs",
            "<p>Keyboard, OSC and the Logical Device are part of the program, so they are never plugged in, unplugged or removed. They are listed last, under <b>INTERNAL INPUTS</b>.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li>Their menu and buttons have only <b>Save to Device Library…</b>, <b>Restore…</b>, <b>Export…</b>, <b>Rename…</b> and <b>Edit Description</b>.</li>"
            + "<li><b>Restore…</b> puts back their newest saved setup. It always works, because nothing needs to be plugged in.</li>"
            + "<li>With nothing saved yet, the row says <i>Nothing saved yet…</i>, and <b>Save to Device Library…</b> is grayed out.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Restore brings back everything the saved setup holds, including the Keyboard's keys and the Logical Device's layout and picture.</li>"
            + "<li>An autosave is kept first, and <b>Edit › Undo</b> takes the whole Restore back in one step.</li>"
            + "<li>OSC's saved setups hold its inputs and its server settings.</li>"
            + "<li>Every profile uses the one Logical Device, so keep its other layouts here as saved setups.</li>"
            + "<li>To bring in someone else's Logical Device file, choose <b>File › Import Device…</b>, then <b>Restore…</b>. The file goes under the Logical Device.</li>"
            + "<li>They can't be copied, swapped, cleared or removed, and they have no state badge.</li>"
            + "<li>The filters never hide them. A search that matches none of them does.</li>"
            + "</ul>",
            ["device-library-devices", "device-library-menus"]),
        t("device-library-saved-setups", "Devices and saved setups", "Saved setups",
            "<p>A saved setup is a stored copy of a device's settings and bindings. A device's saved setups are listed under it, newest first.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li>A mark beside each name shows whether you saved it or the program kept it as an autosave.</li>"
            + "<li>The line under the name says how it was kept: <b>Saved by you</b>, <b>Kept automatically</b>, <b>Was an autosave, now yours</b>, or which device file it came from.</li>"
            + "</ul>"
            + "<p>A saved setup holds any of these parts:</p>"
            + "<ul>"
            + "<li><b>Setup</b>: which inputs the stick uses, and their names.</li>"
            + "<li><b>Device Map</b>: its background and foreground.</li>"
            + "<li><b>Appearance</b>.</li>"
            + "<li><b>Calibration</b>.</li>"
            + "<li><b>Bindings</b>: the stick's actions from one profile, in the modes saved, and the vJoy outputs they send to.</li>"
            + "</ul>"
            + "<p>Select one to see:</p>"
            + "<ul>"
            + "<li>Its name and description, and when and why it was kept.</li>"
            + "<li><b>Holds</b>: exactly what it holds, for example \"Bindings from DCS.xml · modes Default, Landing · 212 actions\".</li>"
            + "<li>A preview picture: the device's image, or else the saved setup's background.</li>"
            + "<li><b>Activity</b>: when it was saved, when its description was edited, and which sticks it was copied to.</li>"
            + "</ul>"
            + "<p>The buttons under the details are <b>Copy to Another Stick…</b>, <b>Swap with Another Stick…</b>, <b>Change vJoy Output…</b>, <b>Export…</b> and <b>Delete…</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Activity covers only that saved setup. <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a> keeps every saved change in the program.</li>"
            + "<li>A stick whose settings file was damaged can still be kept. Its saved setup then holds <b>Setup (damaged file, kept as is)</b>.</li>"
            + "<li>That damaged file is never put on another stick; only its bindings can be copied.</li>"
            + "</ul>",
            ["device-library-save", "device-library-autosaves", "device-library-copy"]),
        t("device-library-rename", "Devices and saved setups", "Rename a device or saved setup",
            "<p>Every device and every saved setup has a name and a description you can change.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Select the row.</li>"
            + "<li>Choose <b>Edit › Rename…</b>, press <b>F2</b>, or click the pencil beside the name.</li>"
            + "<li>Type the new name and press <b>Enter</b>. <b>Esc</b> keeps the old one.</li>"
            + "</ol>"
            + "<p>To change the description, edit it in the box under the name. It reads \"Add a description\" when it is empty. You can also choose <b>Edit Description</b> from the right-click menu.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Your description is kept when you click elsewhere, and also when you press <b>Esc</b>.</li>"
            + "<li>A stick set up here has one name. Renaming it in the Device Library renames its card on Home, and the other way round.</li>"
            + "<li>Renaming or describing an autosave makes it yours, so the autosave limit never removes it.</li>"
            + "</ul>",
            ["device-library-twins", "device-library-keep-autosave"]),
        t("device-library-save", "Devices and saved setups", "Save a setup to the Device Library",
            "<p>Keep a saved setup of your own to come back to later.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Select a device.</li>"
            + "<li>Choose <b>Save to Device Library…</b> from the Device menu, its right-click menu or the button in its details.</li>"
            + "<li>Tick the profiles whose bindings to keep. The open profile is marked \"(open)\".</li>"
            + "<li>Press <b>Save</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>You get one saved setup per ticked profile, named after the profile. Rename it and add a description afterwards.</li>"
            + "<li>Each one also holds the stick's setup as it is now.</li>"
            + "<li>When no profile has bindings for the stick, only its setup is kept.</li>"
            + "<li>The device needs settings to save: a stick set up here or plugged in now, or an internal input.</li>"
            + "</ul>",
            ["device-library-saved-setups", "device-library-rename", "device-library-export"]),

        // ---- Autosaves -----------------------------------------------------
        t("device-library-autosaves", "Autosaves", "When autosaves are kept",
            "<p>The program keeps an autosave of a stick by itself whenever something is about to replace or remove its settings. Autosaves are always on: they are your way back.</p>"
            + "<p>Editing bindings or settings and saving makes no autosave. <b>Tools › History</b> keeps those saves. See <a href=\"topic:device-library-qa-go-back\">Going back after a change</a>.</p>"
            + "<h4>What you see</h4>"
            + "<p>Each autosave is named for what caused it:</p>"
            + "<ul>"
            + "<li><b>Delete Device</b> on Home, or <b>Clear Setup…</b> in the Device Library: \"Autosave: stick deleted\".</li>"
            + "<li><b>Delete File</b> in Module Setup: \"Autosave: module file deleted\". It holds the setup only.</li>"
            + "<li>Before <b>Copy</b> changes the target stick: \"Autosave: before Copy from Old Warthog stick\".</li>"
            + "<li>Before <b>Swap</b>, one of each stick: \"Autosave: before Swap with Right stick\".</li>"
            + "<li>Before <b>Change vJoy Output</b>: \"Autosave: before Change vJoy Output (vJoy 1 → 2)\".</li>"
            + "<li>Before an import onto the stick in <b>Export / Import Device</b>: \"Autosave: before Import Device My F-16\", with the file's name.</li>"
            + "<li>Before <b>Restore to This Stick…</b>: \"Autosave: before Restore of DCS F-16\".</li>"
            + "<li>Before <b>Undo</b> puts back a Copy, Swap, Change vJoy Output or Restore: \"Autosave: before Undo\".</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>An autosave holds everything the stick has: its setup, its pictures, and its bindings in every mode of every profile the change touches.</li>"
            + "<li>If an autosave can't be written or read back, the change doesn't run and the message says why.</li>"
            + "</ul>",
            ["device-library-qa-go-back", "device-library-autosave-limit", "device-library-keep-autosave", "device-library-delete-device"]),
        t("device-library-autosave-limit", "Autosaves", "How many autosaves are kept",
            "<p>Only the newest 10 autosaves per stick are kept. When a new one is kept, the oldest goes.</p>"
            + "<h4>How to</h4>"
            + "<ul>"
            + "<li>To change the number, choose <b>Settings › Device Library Settings…</b> and set <b>Keep the newest … autosaves per stick</b>.</li>"
            + "<li>To hide autosaves from the list, untick the <b>Autosaves</b> filter.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The status bar shows the number in use.</li>"
            + "<li>Your own saved setups are never removed this way.</li>"
            + "<li>Nor is an autosave you renamed, described or kept with <b>Keep This Autosave</b>.</li>"
            + "</ul>",
            ["device-library-keep-autosave", "device-library-settings"]),
        t("device-library-keep-autosave", "Autosaves", "Keep an autosave",
            "<p>Make an autosave yours so the autosave limit never removes it.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Right-click the autosave.</li>"
            + "<li>Choose <b>Keep This Autosave</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Its line then reads <b>Was an autosave, now yours</b>, and its mark changes to your own.</li>"
            + "<li>Its Activity says \"Kept as your own\".</li>"
            + "<li>Renaming or describing an autosave does the same.</li>"
            + "<li>The item shows only on autosaves that are not yours yet.</li>"
            + "</ul>",
            ["device-library-autosave-limit", "device-library-rename"]),
        t("device-library-delete-device", "Autosaves", "Delete Device and Delete File",
            "<p>Deleting a stick or its setup elsewhere in the program always keeps an autosave in the Device Library first.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li><b>Delete Device</b> on Home keeps an autosave of the stick: its setup, its pictures and its bindings in every mode.</li>"
            + "<li>No question about a copy is asked. The stick then shows in the Device Library as <b>Deleted</b>, with its autosave under it.</li>"
            + "<li><b>Delete File</b> in Module Setup keeps an autosave of the stick's setup. See <a href=\"topic:device-library-autosaves\">When autosaves are kept</a>.</li>"
            + "</ul>"
            + "<h4>How to</h4>"
            + "<p>To use a deleted stick's setup again, select its autosave and choose <b>Copy to Another Stick…</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Both work even when the stick's settings file is damaged. The damaged file is kept exactly as it is.</li>"
            + "<li>In the Device Library, <b>Clear Setup…</b> does the same as Delete Device. See <a href=\"topic:device-library-delete\">Delete or remove from the Device Library</a>.</li>"
            + "</ul>",
            ["device-library-autosaves", "device-library-delete", "home-devices-delete-device"]),

        // ---- Changing sticks -----------------------------------------------
        t("device-library-copy", "Changing sticks", "Copy a setup to another stick",
            "<p><b>Copy to Another Stick…</b> puts a saved setup, or a stick's current settings, on a stick plugged in now.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Select a saved setup or a device, then choose <b>Copy to Another Stick…</b>. Double-clicking a saved setup does the same.</li>"
            + "<li>Check <b>From</b>: a saved setup, or \"current settings\" for a stick set up here or plugged in. A device with neither uses its newest saved setup.</li>"
            + "<li>Choose the <b>To</b> stick. Only sticks plugged in now are listed.</li>"
            + "<li>Under <b>What to copy</b>, tick the parts. Parts the saved setup doesn't hold are grayed out.</li>"
            + "<li>Under <b>Bindings go into these profiles</b>, tick the profiles. <b>Tick All</b> ticks them all.</li>"
            + "<li>Under <b>Modes</b>, tick the modes. The ticked modes replace the target stick's bindings in those modes.</li>"
            + "<li>Press <b>Copy</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Setup, Device Map, Appearance and Bindings start ticked; Calibration does not. See <a href=\"topic:device-library-settings\">Device Library Settings</a> to change that.</li>"
            + "<li>Every profile with bindings for either stick is listed. Only the open profile starts ticked.</li>"
            + "<li>A warning box lists what won't copy because the target stick lacks it, such as buttons, hats or axes. The rest copies.</li>"
            + "<li>An autosave of the target stick is kept first, and <b>Edit › Undo</b> puts it back.</li>"
            + "<li>The saved setup and the stick it came from never change.</li>"
            + "<li>A stick that was never plugged in here can be copied from, never to.</li>"
            + "</ul>",
            ["device-library-restore", "device-library-profiles", "device-library-undo"]),
        t("device-library-restore", "Changing sticks", "Restore a saved setup to its stick",
            "<p><b>Restore to This Stick…</b> puts a saved setup back on the stick it belongs to, so you don't choose a To stick. That stick must be plugged in.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Right-click the saved setup.</li>"
            + "<li>Choose <b>Restore to This Stick…</b>.</li>"
            + "<li>Press <b>Restore</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>It works as Copy does, with every part the saved setup holds. That includes Calibration, as it is the same stick.</li>"
            + "<li>The bindings go into the profiles they came from that are still there, in every mode saved.</li>"
            + "<li>An autosave of the stick is kept first (\"Autosave: before Restore of DCS F-16\"), and <b>Edit › Undo</b> puts it back.</li>"
            + "<li>To choose the parts, profiles and modes, or to use another stick, see <a href=\"topic:device-library-copy\">Copy a setup to another stick</a>.</li>"
            + "<li>Internal inputs have <b>Restore…</b> instead. See <a href=\"topic:device-library-built-in\">Internal inputs</a>.</li>"
            + "</ul>",
            ["device-library-copy", "device-library-undo"]),
        t("device-library-swap", "Changing sticks", "Swap two sticks",
            "<p><b>Swap with Another Stick…</b> lets two sticks trade places: each gets the other's settings. Both must be plugged in.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Select a stick and choose <b>Swap with Another Stick…</b>.</li>"
            + "<li>Choose the other stick.</li>"
            + "<li>Under <b>What trades places</b>, tick the parts. They are the same as for Copy.</li>"
            + "<li>Under <b>Swap bindings in these profiles</b>, tick the profiles. The open profile starts ticked; <b>Tick All</b> ticks them all.</li>"
            + "<li>Press <b>Swap</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Actions and script settings that name either stick are swapped too.</li>"
            + "<li>The warning box (\"Some settings have nowhere to go\") lists what one stick has and the other lacks. Those bindings stay where they were.</li>"
            + "<li>It also lists actions that check a control the other stick lacks, for example a Condition on Axis 3. These still move, so check them.</li>"
            + "<li>The Keyboard, Logical Device, OSC and the Xbox controller can't be swapped. A stick can't be swapped with itself.</li>"
            + "<li>An autosave of each stick is kept first, and <b>Edit › Undo</b> puts both back.</li>"
            + "</ul>",
            ["device-library-copy", "device-library-output", "device-library-profiles"]),
        t("device-library-output", "Changing sticks", "Change which vJoy a stick sends to",
            "<p><b>Change vJoy Output…</b> keeps a stick's bindings and changes only which vJoy device they send to. For example, a game can then see two sticks the other way round.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Select a stick and choose <b>Change vJoy Output…</b>.</li>"
            + "<li>Under <b>Change it in these profiles</b>, tick the profiles. The open profile starts ticked; <b>Tick All</b> ticks them all.</li>"
            + "<li>Each vJoy device the stick sends to has a row, such as \"vJoy 1 (38 inputs) → vJoy 2\". Pick where each one sends.</li>"
            + "<li>Each row says <b>changes</b> or <b>stays</b>.</li>"
            + "<li>Press <b>Change</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Another stick may already send to the vJoy device you picked. A tick box then offers to swap them, for example \"Also move Right stick from vJoy 2 to vJoy 1 (swap them)\".</li>"
            + "<li>The <b>Check these</b> box lists bindings to an output the new vJoy device doesn't have turned on. They would send nothing.</li>"
            + "<li>It also lists macros and user scripts that name a vJoy number. Those are not changed, so check them yourself.</li>"
            + "<li>An autosave of each stick that changes is kept first, and <b>Edit › Undo</b> puts them back.</li>"
            + "</ul>",
            ["device-library-swap", "device-library-profiles"]),
        t("device-library-profiles", "Changing sticks", "Profiles that aren't open",
            "<p>Copy, Swap and Change vJoy Output change the profiles you tick, open or not.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li>The <b>open profile</b> is changed in the program only. To keep the change, choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> in the main window.</li>"
            + "<li>A ticked profile that isn't open is changed and saved on disk straight away.</li>"
            + "<li>History keeps each of those saves, so the whole profile can be restored from <b>Tools › History</b>.</li>"
            + "<li>A profile that can't be read or written is named in the message and left as it was. The others still change.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The autosave kept first holds the stick's bindings from every profile the change touches, so Undo puts them all back.</li>"
            + "</ul>",
            ["device-library-copy", "device-library-undo"]),
        t("device-library-busy", "Changing sticks", "When the window is busy",
            "<p>Reading profiles, keeping autosaves and writing files happen in the background, so the window keeps responding.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li>The dialogs show <b>Reading the profiles…</b> and <b>Checking…</b> while they work out the profiles and the warnings.</li>"
            + "<li>Wait for the warnings before you press Copy, Swap or Change.</li>"
            + "<li>While a change runs, the status bar shows <b>Working…</b>. Items that would start another change are hidden or grayed out.</li>"
            + "<li>A row that is being changed shows a small busy mark until the change is done.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>One change runs at a time.</li>"
            + "</ul>",
            ["device-library-qa-grayed"]),

        // ---- Undo and Redo -------------------------------------------------
        t("device-library-undo", "Undo and Redo", "Undo and redo a change",
            "<p><b>Edit › Undo</b> (<b>Ctrl+Z</b>) takes back the last change made in the Device Library. <b>Edit › Redo</b> (<b>Ctrl+Y</b>) makes it again.</p>"
            + "<p>They work on every Library change, such as Copy, Swap, Change vJoy Output, Restore, Save, Delete and Rename.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li>Rest the pointer on <b>Undo</b> or <b>Redo</b> to see the change it acts on, for example \"Remove HID Remapper ACHB\".</li>"
            + "<li>In the Edit menu, each item shows only when there is something to undo or redo.</li>"
            + "<li>The status bar has the same <b>Undo</b> and <b>Redo</b> buttons. Each is grayed out when there is nothing to do.</li>"
            + "<li>Beside them, <b>Last change:</b> names what Undo would take back. After an Undo it says <b>Undone:</b> and names what Redo would put back.</li>"
            + "<li>A long name ends with …; rest the pointer on it to read it all.</li>"
            + "<li>The same <b>Undo</b> and <b>Redo</b> sit beside the title of every right-click menu.</li>"
            + "<li>After a delete, the message line ends with an <b>Undo</b> link that does the same.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Undo again to go further back through this session's Library changes, newest first. Redo goes forward again.</li>"
            + "<li>A new change clears Redo.</li>"
            + "<li>While you type in a box, <b>Ctrl+Z</b> and <b>Ctrl+Y</b> undo the typing instead.</li>"
            + "<li>Clear History in <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a> also empties Undo and Redo here.</li>"
            + "<li>Each change is one entry in Tools › History, so changes from earlier sessions can be put back there. See <a href=\"topic:device-library-history\">See a device's changes in History</a>.</li>"
            + "</ul>",
            ["device-library-history", "device-library-delete", "device-library-qa-go-back"]),
        t("device-library-history", "Undo and Redo", "See a device's changes in History",
            "<p><b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a> keeps every Library change, including ones from earlier sessions. It can put any of them back.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Right-click a device or one of its saved setups.</li>"
            + "<li>Choose <b>Show in History</b>. History opens in the main window, showing only that device's changes.</li>"
            + "<li>Select a change and choose <b>Restore to before this change</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Each Library change is one History entry named for what it did, for example \"Removed Old Warthog stick from the Device Library\".</li>"
            + "<li>Restore puts back only that change. Saved setups it removed come back, and ones it added go.</li>"
            + "<li>Every later change stays.</li>"
            + "</ul>",
            ["device-library-undo", "device-library-delete", "tools-history"]),

        // ---- Finding things ------------------------------------------------
        t("device-library-search", "Finding things", "Search the Device Library",
            "<p>The search box finds devices and saved setups as you type. Capital letters don't matter.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Click the search box, press <b>Ctrl+F</b>, or choose <b>View › Search…</b>.</li>"
            + "<li>Type part of what you are looking for. The line under the box says \"N found\" or \"Nothing matches\".</li>"
            + "<li>To clear the search, click × in the box, or press <b>Esc</b>, which also leaves the box.</li>"
            + "</ol>"
            + "<h4>What you see</h4>"
            + "<p>It finds:</p>"
            + "<ul>"
            + "<li>Device names and descriptions.</li>"
            + "<li>Saved setup names and descriptions, and autosave reasons, such as \"stick deleted\" or \"before Swap\".</li>"
            + "<li>What a saved setup holds: Setup, Device Map, Appearance, Calibration or Bindings.</li>"
            + "<li>Profile names and mode names.</li>"
            + "<li>vJoy numbers, such as \"vJoy 2\".</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A device that has a matching saved setup opens to show it.</li>"
            + "</ul>",
            ["device-library-filters", "device-library-select"]),
        t("device-library-filters", "Finding things", "Filter the list",
            "<p>The filters <b>Connected</b>, <b>Not connected</b>, <b>Deleted</b> and <b>Autosaves</b> choose which rows the list shows.</p>"
            + "<h4>How to</h4>"
            + "<ul>"
            + "<li>Untick a filter to hide that kind of row, for example deleted sticks or autosaves. Tick it again to show them.</li>"
            + "<li>The View menu has the same four.</li>"
            + "<li><b>View › Expand All</b> shows every device's saved setups; <b>Collapse All</b> hides them.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The filters never hide the internal inputs.</li>"
            + "</ul>",
            ["device-library-search", "device-library-window"]),
        t("device-library-select", "Finding things", "Select several rows",
            "<p>Select several rows to delete or remove them with one question.</p>"
            + "<h4>How to</h4>"
            + "<ul>"
            + "<li>Ctrl-click adds a row to the selection or takes it away.</li>"
            + "<li>Shift-click selects every row from the last one you selected to this one.</li>"
            + "<li>Then choose <b>Delete…</b> for saved setups, or <b>Remove from Library…</b> for devices that aren't connected.</li>"
            + "<li>It is in the right-click menu, in <b>Edit › Delete…</b> and on the red button.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>One question lists everything that goes.</li>"
            + "<li>You can select several saved setups, or several devices, but not both. A row of the other kind starts a new selection.</li>"
            + "<li>Devices are removed together only when none of them is connected.</li>"
            + "<li>Copy, Swap, Change vJoy Output, Restore, Rename and Export act on one row only. With several rows selected they are hidden or grayed out.</li>"
            + "<li>With a plugged-in stick among the selected devices, the right-click menu shows <b>Remove from Library…</b> grayed out. Rest the pointer on it to see why.</li>"
            + "</ul>",
            ["device-library-delete"]),

        // ---- Sharing -------------------------------------------------------
        t("device-library-export", "Sharing", "Export a saved setup",
            "<p>Export writes a saved setup as a device file (.gmap) wherever you choose, ready to give to someone else.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Select a saved setup.</li>"
            + "<li>Choose <b>Export…</b>, or <b>File › Export Saved Setup…</b>.</li>"
            + "<li>Choose where to save the file. The chooser opens in the folder you last used for a device file.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>To share a stick's settings as they are now, right-click the device and choose <b>Export Current Setup…</b>.</li>"
            + "<li>That writes a device file without keeping a saved setup first. It needs a stick set up here or plugged in.</li>"
            + "<li><b>File › Open Library Folder</b> opens the library's folder in File Explorer.</li>"
            + "</ul>",
            ["device-library-share-which", "device-library-import", "device-library-qa-share"]),
        t("device-library-import", "Sharing", "Import a device file into the Library",
            "<p>Importing adds a device file (.gmap) to the Device Library as a saved setup. Nothing changes on your sticks.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Choose <b>File › Import Device…</b> and pick the .gmap file, or drop it on the window.</li>"
            + "<li>To use it, select the new saved setup and choose <b>Copy to Another Stick…</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Only .gmap files can be imported.</li>"
            + "<li>The chooser opens in the folder you last used for a device file.</li>"
            + "<li>It goes under the device it was made from, when that device is in the Device Library.</li>"
            + "<li>Otherwise it goes under a new <b>Not connected</b> device, named after the file.</li>"
            + "<li>The saved setup says where it came from, for example \"From Sam's device file\". The file's note becomes its description.</li>"
            + "<li>A file that can't be read is refused, and the message says why. That includes a file with damaged parts inside.</li>"
            + "<li>A file that unpacks to more than 64 MB is refused too.</li>"
            + "<li>A very long device name is cut to 80 characters in the library's folder and file names. The list shows the full name.</li>"
            + "</ul>",
            ["device-library-share-which", "device-library-export", "device-library-copy"]),

        t("device-library-share-which", "Sharing", "Which way to share?",
            "<p>The Device Library and <b>Tools › Device Setup › Export / Import Device</b> <a href=\"open:tools.devicePack\">Open ›</a> write and read the same kind of device file (.gmap). A file made in one opens in the other.</p>"
            + "<h4>Which to use</h4>"
            + "<ul>"
            + "<li><b>Device Library</b>: to export a saved setup you keep, or to keep a file you were given as a saved setup. You choose later which parts, profiles and modes to copy onto a stick.</li>"
            + "<li><b>Export / Import Device</b>: to write Made by and a Note, and choose the modes and output modules that go in. Its import puts a file straight onto a device, as a new device or onto an existing one.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Before either one replaces a stick's settings, an autosave of the stick is kept.</li>"
            + "</ul>",
            ["device-library-export", "device-library-import", "home-devices-device-pack"]),

        // ---- Settings and tidying ------------------------------------------
        t("device-library-settings", "Settings and tidying", "Device Library Settings",
            "<p><b>Settings › Device Library Settings…</b> holds the Device Library's own settings.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li><b>Keep the newest … autosaves per stick</b>: how many autosaves each stick keeps (10 to start).</li>"
            + "<li><b>Copy and Swap tick by default</b>: which parts start ticked. To start, these are Setup, Device Map, Appearance and Bindings.</li>"
            + "<li><b>Library folder</b>: where the Device Library is kept. <b>Move…</b> picks another folder.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The library moves to the new folder when you press <b>OK</b>.</li>"
            + "<li>Setups you saved, renamed or described are never removed by the autosave limit.</li>"
            + "</ul>",
            ["device-library-autosave-limit", "device-library-tidy"]),
        t("device-library-tidy", "Settings and tidying", "Tidy the Device Library",
            "<p>Tidy Library frees space by removing old autosaves and empty deleted devices. The status bar shows how much space the library takes.</p>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Choose <b>Edit › Tidy Library…</b>.</li>"
            + "<li>Set the number of months (6 to start). Autosaves older than that are listed, with deleted devices that have no saved setups.</li>"
            + "<li>Each item shows its size and starts ticked. Untick what you want to keep.</li>"
            + "<li>Press the red <b>Remove from Library</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The Tidy Library box is the question. The line under the list says how many items are ticked and their size.</li>"
            + "<li>Nothing is removed until you press Remove from Library, and no second question follows.</li>"
            + "<li><b>Cancel</b> has the focus, so <b>Enter</b> and <b>Esc</b> both cancel.</li>"
            + "<li>To bring removed items back, use the <b>Undo</b> link on the message line right after, or <b>Tools › History</b> later.</li>"
            + "<li>Apart from Tidy and the autosave limit, nothing in the library is removed without asking.</li>"
            + "</ul>",
            ["device-library-settings", "device-library-delete"]),
        t("device-library-delete", "Settings and tidying", "Delete or remove from the Device Library",
            "<p>Every delete asks first and names exactly what goes. What it does depends on what is selected.</p>"
            + "<h4>What you see</h4>"
            + "<ul>"
            + "<li>A saved setup: <b>Delete…</b> removes it from the Device Library.</li>"
            + "<li>A device that isn't connected: <b>Remove from Library…</b> removes it entirely. That covers unplugged and deleted devices, and ones from a device file.</li>"
            + "<li>A connected stick: <b>Clear Setup…</b> does what <b>Delete Device</b> does on Home.<ul>"
            + "<li>An autosave is kept in the Device Library first. Then its setup and its bindings go.</li>"
            + "<li>The stick stays plugged in with no setup.</li>"
            + "</ul></li>"
            + "<li>A connected stick: <b>Delete Saved Setups…</b> removes only its saved setups. The stick keeps its settings.</li>"
            + "</ul>"
            + "<h4>How to</h4>"
            + "<ol>"
            + "<li>Select the row.</li>"
            + "<li>Choose the item from its right-click menu, choose <b>Edit › Delete…</b>, press the red button under the details, or press the <b>Delete</b> key.</li>"
            + "<li>The question names what goes, for example \"Remove Old Warthog stick and its 4 saved setups from the Library?\"</li>"
            + "<li>Press the red button, named for the action, to go ahead. <b>Cancel</b> has the focus, so <b>Enter</b> and <b>Esc</b> both cancel.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The question's last line reads <i>You can restore it from Tools › History.</i></li>"
            + "<li>Remove from Library takes everything about the device: its settings, pictures, saved setups, autosaves, name, Home card settings and calibration.</li>"
            + "<li>Its bindings leave the open profile. Save the profile to make that stick.</li>"
            + "<li>For a device still set up here, Remove from Library runs Delete Device first. If that can't run, nothing is removed and the message says why.</li>"
            + "<li>The <b>Delete</b> key does nothing on a connected stick or an internal input, or while you type in a box.</li>"
            + "<li>On a device, the red button and <b>Edit › Delete…</b> follow its state. Clear Setup… is only in the device's right-click menu.</li>"
            + "<li>Each delete is one entry in <b>Tools › History</b>, for example \"Removed Old Warthog stick from the Device Library\".</li>"
            + "<li>Right after, the <b>Undo</b> link on the message line, or <b>Edit › Undo</b>, puts it all back.</li>"
            + "<li>The autosave Clear Setup… keeps is ready for <b>Restore to This Stick…</b>.</li>"
            + "<li>To delete several rows with one question, see <a href=\"topic:device-library-select\">Select several rows</a>.</li>"
            + "</ul>",
            ["device-library-undo", "device-library-history", "device-library-select"]),
        t("device-library-twins", "Settings and tidying", "Renamed and twin sticks",
            "<p>A stick's name in the Device Library is its name on Home. Rename it in either place and both change.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Dialogs, autosave names and the Undo item use that name.</li>"
            + "<li>Two sticks with the same name (twins) have a short code after the name, for example \"Right stick [EEEE0006]\".</li>"
            + "<li>The code shows in the list and in the To lists. Rename one of them to tell them apart at a glance.</li>"
            + "</ul>",
            ["device-library-rename"]),

        // ---- Common questions ----------------------------------------------
        t("device-library-qa-new-stick", "Common questions", "My stick broke: how do I put its setup on the new one?",
            "<ol>"
            + "<li>Plug in the new stick.</li>"
            + "<li>In the Device Library, open the old stick's row.</li>"
            + "<li>Select a saved setup, or its \"Autosave: stick deleted\" if you deleted the stick.</li>"
            + "<li>Choose <b>Copy to Another Stick…</b> with the new stick as To.</li>"
            + "<li>Untick Calibration unless the sticks are the same model, then press <b>Copy</b>.</li>"
            + "</ol>"
            + "<p>The warning box lists any controls the new stick doesn't have. See <a href=\"topic:device-library-copy\">Copy a setup to another stick</a>.</p>",
            ["device-library-copy"]),
        t("device-library-qa-share", "Common questions", "How do I give my setup to a friend?",
            "<ol>"
            + "<li>Make a saved setup first: select the stick and choose <b>Save to Device Library…</b>. See <a href=\"topic:device-library-save\">Save a setup to the Device Library</a>.</li>"
            + "<li>Select the saved setup and press <b>Export…</b>.</li>"
            + "<li>Send the .gmap file to your friend.</li>"
            + "<li>Your friend chooses <b>File › Import Device…</b>, or drops the file on their Device Library, and copies it onto their stick.</li>"
            + "</ol>"
            + "<p>To share the stick's settings as they are now, right-click the device and choose <b>Export Current Setup…</b>. See <a href=\"topic:device-library-export\">Export a saved setup</a>.</p>",
            ["device-library-share-which", "device-library-export", "device-library-import"]),
        t("device-library-qa-cant-copy", "Common questions", "Why can't I copy to this stick?",
            "<p>Copy and Swap work only onto sticks plugged in now, so the To list shows nothing else. Plug the stick in and open the dialog again.</p>"
            + "<ul>"
            + "<li>A device from someone else's device file has never been plugged in here. You can copy from it, not to it.</li>"
            + "<li>Internal inputs can't be copied to.</li>"
            + "</ul>"
            + "<p>See <a href=\"topic:device-library-copy\">Copy a setup to another stick</a>.</p>",
            ["device-library-copy", "device-library-devices"]),
        t("device-library-qa-where", "Common questions", "Where did my old setup go?",
            "<ul>"
            + "<li>A deleted stick shows as <b>Deleted</b>, with its autosave under it. Check that the Deleted and Autosaves filters are ticked and the search box is empty.</li>"
            + "<li>Clear Setup… keeps \"Autosave: stick deleted\" under the stick. Right-click it and choose <b>Restore to This Stick…</b>.</li>"
            + "<li>Copy, Swap, Change vJoy Output, Restore and an import in Export / Import Device keep an autosave first. Search for the change, such as \"before Restore\".</li>"
            + "<li>Only the newest autosaves per stick are kept. Choose <b>Keep This Autosave</b>, or rename or describe one, to keep it for good.</li>"
            + "<li>Something removed with a delete item: <b>Edit › Undo</b> puts it back, or <b>Tools › History</b> for an older one.</li>"
            + "</ul>"
            + "<p>See <a href=\"topic:device-library-qa-go-back\">Going back after a change</a>.</p>",
            ["device-library-qa-go-back", "device-library-autosaves", "device-library-filters", "device-library-history"]),
        t("device-library-qa-go-back", "Common questions", "How do I go back after a change?",
            "<ul>"
            + "<li>The last change: choose <b>Edit › Undo</b> (<b>Ctrl+Z</b>), and again for the one before.</li>"
            + "<li>A change from an earlier session: right-click the row, choose <b>Show in History</b> and restore it there.</li>"
            + "<li>A stick's earlier settings: right-click the autosave it kept and choose <b>Restore to This Stick…</b>. The stick must be plugged in.</li>"
            + "<li>A profile that wasn't open: it was saved, so History can restore the whole profile.</li>"
            + "<li>Bindings or settings you edited and saved: no autosave is kept for those. In <b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a>, select the save and choose <b>Restore to before this change</b>.</li>"
            + "</ul>"
            + "<p>See <a href=\"topic:device-library-undo\">Undo and redo a change</a>.</p>",
            ["device-library-undo", "device-library-history", "device-library-restore"]),
        t("device-library-qa-grayed", "Common questions", "Why are the buttons grayed out?",
            "<p>Usually the window is busy. Wait for <b>Checking…</b> in a dialog, or <b>Working…</b> in the status bar, to finish.</p>"
            + "<p>Otherwise the selection doesn't allow it:</p>"
            + "<ul>"
            + "<li><b>Swap with Another Stick…</b> needs a stick that is plugged in.</li>"
            + "<li><b>Export…</b> needs a saved setup.</li>"
            + "<li><b>Save to Device Library…</b> needs a stick set up here or plugged in.</li>"
            + "<li>With several rows selected, only delete works.</li>"
            + "</ul>"
            + "<p>The menus leave out what doesn't apply instead of greying it out. See <a href=\"topic:device-library-busy\">When the window is busy</a>.</p>",
            ["device-library-busy", "device-library-select"])
    ]
}

function t(id, section, title, body, related) {
    return { id: id, section: section, title: title, body: body, related: related || [] }
}
