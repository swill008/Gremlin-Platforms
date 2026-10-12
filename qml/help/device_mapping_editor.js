// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help, chapter "Device Mapping Editor" (01 S128, D-01-ONE-HELP).
// Written to claude/help-style.md; on-screen labels in bold, exactly as shown.

.pragma library

var chapter = { id: "device-mapping-editor", title: "Device Mapping Editor" }

function topics() {
    return [
        // ---- Getting started ------------------------------------------------
        t("device-mapping-editor-about", "Getting started", "What the Device Mapping Editor is",
            "<p>The Device Mapping Editor shows a device's map: a picture of one device with a chip on each control. While the profile runs, a press lights its chip, and the chip shows where the control's wire goes (shown as <b>(not claimed)</b> when the output is not claimed). Chips can also show what each control does in the profile.</p>"
            + "<ul>"
            + "<li>The line from a chip to its control on the photo is its <b>leader</b>; the dot on the control is its <b>hotspot</b>.</li>"
            + "<li>Chips not yet placed wait in the <b>pool</b>.</li>"
            + "<li>Chips are layout only: moving, renaming or deleting one never changes the actions in the profile.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>In the Device Mapping Editor, <b>Help</b> or <b>F1</b> opens this chapter of Help. <b>View Full Help</b> shows the whole book.</li>"
            + "</ul>",
            ["device-mapping-editor-open", "device-mapping-editor-edit", "device-mapping-editor-action-labels"]),
        t("device-mapping-editor-open", "Getting started", "Open the Device Mapping Editor",
            "<p>The Device Mapping Editor opens in its own window, on one device.</p>"
            + "<ol>"
            + "<li>Open it from a device card's right-click menu, <b>Mapping Editor</b> on the toolbar <a href=\"show:toolbar/Mapping Editor\">Show me ›</a>, or <b>Tools › Mapping › Device Mapping Editor</b> <a href=\"show:menu/Tools/Mapping/Device Mapping Editor\">Show me ›</a> <a href=\"open:tools.deviceMappingEditor\">Open ›</a>.</li>"
            + "<li>To show another device, choose it from <b>File › Device</b>. The device shown has a tick. Opened from the toolbar or the Tools menu, the window starts with no device and says \"Choose a device from the File menu.\"</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Switching device while you have unsaved edits asks to save first; <b>Cancel</b> stays on the current device.</li>"
            + "<li><b>File › Device</b> doesn't list vJoy or Xbox outputs; their cards still open their device map.</li>"
            + "<li>There is one Device Mapping Editor window: opening it for another device reuses it.</li>"
                + "<li>The Device Mapping Editor closes when its device is deleted.</li>"
            + "<li>Before you edit, the map is live: rest the pointer on a chip to see which control it is, and drag with the left or middle button to pan.</li>"
            + "<li>Until you edit, a slim line under the menu bar reads \"View only. To edit this device map, choose File › Edit Mapping.\" Select its <b>Edit Mapping</b> link to start editing. With no device chosen it reads \"No device chosen. Choose one from File › Device, then File › Edit Mapping to edit its device map.\" Its <b>File › Device</b> link opens that menu. The line goes while you edit and comes back after Save or Cancel.</li>"
            + "<li>Every command is in the menu bar, with its key beside it; commands that don't apply right now are greyed out. <b>Help › Keyboard Shortcuts…</b> (<b>Ctrl+K</b>) lists every key.</li>"
            + "</ul>",
            ["device-mapping-editor-edit", "device-mapping-editor-menus", "device-mapping-editor-keys"]),
        t("device-mapping-editor-edit", "Getting started", "Edit and save a device map",
            "<p>Editing places chips on the photo and draws on the map. Nothing is written until you save.</p>"
            + "<ol>"
            + "<li>Choose <b>File › Edit Mapping</b>, or the <b>Edit Mapping</b> link in the \"View only\" line under the menu bar.</li>"
            + "<li>Drag chips from the pool, the <b>Chips</b> panel at the map's left edge, onto the photo. Type in the pool's filter to find a control by name, number or output.</li>"
            + "<li>Choose <b>File › Save</b> (<b>Ctrl+S</b>) to write the layout to the device's module file, or <b>File › Cancel</b> to leave without saving.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Save reads the layout back and says \"Saved to the module file.\" on the message line under the map. When it can't write it, the line says in red \"Not written. It is still only on this screen.\" A message stays until the next one.</li>"
            + "<li>Cancel and closing ask first when there are unsaved edits; choosing Save there saves and leaves editing.</li>"
            + "<li>While editing, <b>Undo</b> (<b>Ctrl+Z</b>) and <b>Redo</b> (<b>Ctrl+Y</b>) are at the top of the <b>Edit</b> menu and of every right-click menu. They work only while editing, back as many steps as <b>Undo steps</b> in Device Map Options (80 at first).</li>"
            + "<li>Most of this chapter is about editing.</li>"
            + "<li>What Save writes, and what is kept at once, is listed in <a href=\"topic:device-mapping-editor-options\">Device Map Options</a>.</li>"
            + "</ul>",
            ["device-mapping-editor-chips", "device-mapping-editor-keys", "device-mapping-editor-options"]),
        t("device-mapping-editor-side-panels", "Getting started", "Chips and Layers side panels",
            "<p>The Device Mapping Editor has the menu bar and two side panels: <b>Chips</b> (the pool) at the map's left edge <a href=\"show:devicemappingeditor/chipsSide\">Show me ›</a>, and on the right the panel with <b>Layers</b> <a href=\"show:devicemappingeditor/layersSide\">Show me ›</a>, and <b>Properties</b> under it <a href=\"show:devicemappingeditor/propsPanel\">Show me ›</a>. Folded, each side panel is a bar down its edge with the panel's tab (its name and pin) and an arrow pointing toward the map.</p>"
            + "<ul>"
            + "<li>Click the tab, or anywhere on the bar (its tooltip reads \"Show the chips\" or \"Show the layers\"), and the panel slides out at the width it had last; it slides back into the bar when it folds. The panel's header has its name, a pin (<b>Pin</b> or <b>Unpin</b>) and a fold arrow (<b>Fold</b>) that folds it back into its edge.</li>"
            + "<li>Pinned, the panel stays out beside the map, and the map gets narrower so nothing is covered.</li>"
            + "<li>Unpinned, the panel slides out over the map and folds again when you click the map or the other bar.</li>"
            + "<li>Drag a panel's inner edge (the one facing the map) to make it wider or narrower, between its smallest and largest width.</li>"
            + "<li>When something is selected, <b>Properties</b> shows under Layers in the right panel. Drag the divider between them to give one more room. <b>View › Properties</b> (<b>F4</b>) shows or hides it.</li>"
            + "<li>The side panels can't be dragged, floated or locked.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The bars show only while editing (<b>File › Edit Mapping</b>); when editing starts again they come back as you left them.</li>"
            + "<li>While you edit the background, Chips folds by itself, and comes back when you go back to the foreground.</li>"
            + "<li><b>View › Chips</b> (<b>F6</b>) and <b>View › Layers</b> (<b>F7</b>) bring their panel out or fold it while editing; <b>Ctrl+F</b> brings the Layers panel out.</li>"
            + "<li>When the window is too narrow for the map and the pinned panels, Chips unpins and folds first, then Layers; they come back when there is room again.</li>"
            + "<li>Each panel's width, pin and whether it is out, and where the Layers/Properties divider sits, are kept for next time. <b>View › Reset Panels</b> puts them back as they start (Chips out and pinned, Layers folded).</li>"
            + "</ul>",
            ["device-mapping-editor-menus", "device-mapping-editor-chips", "device-mapping-editor-layers", "device-mapping-editor-properties"]),
        t("device-mapping-editor-menus", "Getting started", "Device Mapping Editor menus",
            "<p>Every Device Mapping Editor command is in the menu bar, with its key beside it. Before a device is chosen, <b>File › Device</b> lists the devices; the editing commands work once you choose <b>File › Edit Mapping</b>. Commands that don't apply to what is selected are greyed out, and <b>Insert</b>, <b>Arrange</b> and <b>Leader</b> open only while editing. The menus read, from left to right:</p>"
            + "<ul>"
            + "<li><b>File</b> <a href=\"show:devicemappingeditor/dmeMenuFile\">Show me ›</a>: <b>Edit Mapping</b> (<b>Ctrl+E</b>), <b>Save</b> (<b>Ctrl+S</b>), <b>Cancel</b> (<b>Ctrl+Shift+W</b>), <b>History</b> (<b>Ctrl+H</b>); <b>Device</b>; <b>Templates</b> (<b>Save Layout as Template…</b> <b>Ctrl+Shift+S</b>, <b>Apply Template</b>, <b>Manage Templates…</b> <b>Ctrl+Shift+T</b>); <b>Print &amp; Export…</b> (<b>Ctrl+P</b>); <b>Close</b> (<b>Ctrl+W</b>).</li>"
            + "<li><b>Edit</b> <a href=\"show:devicemappingeditor/dmeMenuEdit\">Show me ›</a>: <b>Undo</b> (<b>Ctrl+Z</b>), <b>Redo</b> (<b>Ctrl+Y</b>); <b>Cut</b> (<b>Ctrl+X</b>), <b>Copy</b> (<b>Ctrl+C</b>), <b>Paste</b> (<b>Ctrl+V</b>), <b>Paste Picture</b> (<b>Ctrl+Shift+V</b>), <b>Duplicate</b> (<b>Ctrl+D</b>), <b>Delete</b>; <b>Select All</b> (<b>Ctrl+A</b>); <b>Background</b> › <b>Edit Background</b> (<b>Ctrl+B</b>), <b>Add Picture to Background…</b> (<b>Ctrl+I</b>), <b>Clear Background</b>; <b>Copy Device Map from Device</b>, <b>Mirror Layout</b> (<b>Ctrl+M</b>), <b>Reset Layout</b>; <b>Device Map Options…</b> (<b>Ctrl+,</b>).</li>"
            + "<li><b>View</b> <a href=\"show:devicemappingeditor/dmeMenuView\">Show me ›</a>: <b>Zoom In</b> (<b>Ctrl+=</b>), <b>Zoom Out</b> (<b>Ctrl+-</b>), <b>Zoom to Fit Page</b> (<b>Ctrl+1</b>), <b>Zoom to Selection</b> (<b>Ctrl+2</b>), <b>Fit to Photo Frame</b> (<b>Ctrl+3</b>), <b>Reset View</b> (<b>Ctrl+0</b>); <b>Chips</b> (<b>F6</b>), <b>Layers</b> (<b>F7</b>), <b>Properties</b> (<b>F4</b>), <b>Search layers…</b> (<b>Ctrl+F</b>); <b>Rulers</b> (<b>Ctrl+R</b>), <b>Show Guides</b> (<b>Ctrl+;</b>), <b>Clear Guides</b>, <b>Grid</b>, <b>Snap to Grid</b> (<b>Ctrl+Shift+'</b>), <b>Snap to Entities</b> (<b>Ctrl+Shift+;</b>); <b>Show Print Area</b>, <b>Set Print Area</b> (or <b>Alt</b>+drag), <b>Clear Print Area</b>, <b>Print Area Color…</b>; <b>Reset Panels</b>.</li>"
            + "<li><b>Insert</b> <a href=\"show:devicemappingeditor/dmeMenuInsert\">Show me ›</a>: <b>Shape</b>, <b>Line</b> and <b>Text</b> (text box, callout, table), <b>Picture…</b>, <b>Shape Around Selection</b>, and <b>Stop Drawing</b> (<b>Esc</b>).</li>"
            + "<li><b>Arrange</b> <a href=\"show:devicemappingeditor/dmeMenuArrange\">Show me ›</a>: <b>Bring to Front</b> (<b>Ctrl+Shift+]</b>), <b>Bring Forward</b> (<b>Ctrl+]</b>), <b>Send Backward</b> (<b>Ctrl+[</b>), <b>Send to Back</b> (<b>Ctrl+Shift+[</b>); <b>Move to Background</b> or <b>Move to Foreground</b> (<b>Ctrl+Shift+B</b>); <b>Flip Horizontally</b> (<b>Shift+H</b>), <b>Flip Vertically</b> (<b>Shift+V</b>), rotate by a step (<b>Ctrl+Alt+Right</b> and <b>Ctrl+Alt+Left</b>); <b>Reset Shape</b>, <b>Reset Crop</b>; <b>Group Selected</b> (<b>Ctrl+G</b>), <b>Break Group</b> (<b>Ctrl+Shift+G</b>), <b>Edit Group</b>; <b>Lock</b> or <b>Unlock</b> (<b>Ctrl+L</b>), <b>Unlock All</b> (<b>Ctrl+Shift+L</b>), <b>Hide</b> (<b>Ctrl+Shift+H</b>), <b>Rename</b> (<b>F2</b>); <b>Align</b> and <b>Distribute</b>; <b>Crop</b>, <b>Edit Points</b> and snap points.</li>"
            + "<li><b>Leader</b> <a href=\"show:devicemappingeditor/dmeMenuLeader\">Show me ›</a>: <b>Add Leader</b>, <b>Add Callout</b>, <b>Add Pointer</b>, <b>Add Straight Spine</b> and <b>Add Curved Spine</b>; the leader end commands (<b>Detach Chip End</b>, <b>Reconnect to This Chip</b>, <b>Branch from This End</b>, <b>Clear All Spines</b>, <b>Delete Leader</b> and the hotspot ones); and the callout commands (<b>Detach from Chip</b>, <b>Remove Pointer</b>, <b>Detach from Chips</b>).</li>"
            + "<li><b>Format</b> <a href=\"show:devicemappingeditor/dmeMenuFormat\">Show me ›</a>: <b>Copy Format</b> (<b>Ctrl+Alt+C</b>), <b>Paste Format</b> (<b>Ctrl+Alt+V</b>), <b>Clear Formatting</b>, <b>Save This Style…</b>; the color items; <b>Edit Text…</b> (<b>Enter</b>); <b>Table</b> (insert or delete rows, columns and cells, the ID column, delete the table) and <b>Table Cell</b>; <b>Chip Text</b> and <b>Labels Mode</b>.</li>"
            + "<li><b>Help</b> <a href=\"show:devicemappingeditor/dmeMenuHelp\">Show me ›</a>: <b>Help</b> (<b>F1</b>), <b>Keyboard Shortcuts…</b> (<b>Ctrl+K</b>).</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li><b>Cut</b> copies the selection and deletes it, as one Undo step.</li>"
            + "<li>The Insert, Arrange, Leader and Format menus hold the same commands as the right-click menus, for the selection. A ☆ at the end of a command's row adds it to the right-click menu's Favourites, and <b>Repeat</b> on the right-click menu runs the last command again (see <a href=\"topic:device-mapping-editor-context-menu\">Right-click menu</a>).</li>"
            + "<li><b>Reset Layout</b> clears everything from the map: chips go back to the pool, and leaders, hotspots, drawings, text boxes, pictures and tables are removed. It asks first (\"Reset the layout?\"); the red <b>Reset Layout</b> clears it, and actions are not changed. <b>Ctrl+Z</b> brings the layout back, and <b>File › Cancel</b> leaves editing without keeping the reset; <b>Save</b> makes the empty map the live one.</li>"
            + "<li><b>Fit to Photo Frame</b> shrinks an older, oversized layout to the photo frame.</li>"
            + "</ul>",
            ["device-mapping-editor-keys", "device-mapping-editor-side-panels", "device-mapping-editor-print", "device-mapping-editor-background"]),
        t("device-mapping-editor-options", "Getting started", "Device Map Options",
            "<p><b>Device Map Options</b> holds the Device Mapping Editor's own settings; they are not in the program's main Options. They apply to every device.</p>"
            + "<p>Open it with <b>Edit › Device Map Options…</b> (<b>Ctrl+,</b>) <a href=\"show:devicemappingeditor/dmeMenuEdit\">Show me ›</a>. It is a small window of its own, with a <b>×</b> to close it and a pin: unpinned, a click anywhere else closes it; pinned, it stays open, and the pin is kept for next time. The groups are down its left; the chosen group's settings sit on the right (drag the divider between them to widen the list; its width is kept), one line each, with each setting's description on its ⓘ. Changes apply and are kept at once, and the window opens on the group you used last.</p>"
            + "<ul>"
            + "<li><b>Labels</b>: <b>Chip text</b>, <b>Description first</b>, <b>Several actions</b> and <b>No actions</b>. See <a href=\"topic:device-mapping-editor-action-labels\">Show actions on chips</a>.</li>"
            + "<li><b>Editing</b>: <b>Mirror pictures</b>, whether Mirror Layout and Copy Device Map from Device also flip pictures (off: pictures only move, so text in them still reads); <b>Undo steps</b>, how far Undo can go back (80 at first); <b>Rotate snap</b>, the degrees per step when Shift is held while turning an item or drawing a line; <b>Press to find</b> and <b>Find axes</b>.</li>"
            + "<li><b>Recovery copies</b>: with <b>Keep recovery copies</b> on (the default), a recovery copy of unsaved edits is kept every <b>Seconds between recovery copies</b> (60 at first) while you edit. If the program closes before you save, opening the device again offers <b>Restore</b> (the edits open for editing; save to keep them), <b>Discard</b>, or <b>Not now</b>. Save and Discard remove the copy.</li>"
            + "<li><b>View</b>: <b>Zoom speed</b>, how fast the mouse wheel zooms; <b>Rulers</b>, shown or not (also <b>View › Rulers</b>).</li>"
            + "<li><b>Colors</b>: <b>Recent colors</b>, how many the color picker keeps.</li>"
            + "<li><b>Right-click menu</b>: <b>Favourites shown</b>, how many favourites the top of the right-click menu shows (5 at first, up to 15; 0 turns them off). See <a href=\"topic:device-mapping-editor-context-menu\">Right-click menu</a>.</li>"
            + "<li><b>Library</b>: the saved styles and layout templates, to rename or delete. Deleting a style asks first (\"Delete saved style “Name”?\", \"Items that use it keep their look.\"); the red <b>Delete Style</b> deletes it.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>While editing, the map (background and foreground), the print area, the print settings and the guides are written to the module file only by Save; Cancel takes them back.</li>"
            + "<li>The view (zoom and pan), the grid settings and Show Guides are kept with the device's map at once, also while editing, and Cancel leaves them. Outside editing, Print &amp; Export's settings are kept at once. Rulers is a setting of the program, kept at once.</li>"
            + "</ul>",
            ["device-mapping-editor-edit", "device-mapping-editor-styles"]),
        t("device-mapping-editor-unplugged", "Getting started", "Unplugged sticks and damaged module files",
            "<p>A stick's device map shows only while the stick is connected.</p>"
            + "<ul>"
            + "<li>For an unplugged stick the map is covered with \"Connect &lt;name&gt; to see its device map.\" It loads by itself when the stick connects.</li>"
            + "<li>An unplugged stick's map still exports from <b>Print &amp; Export…</b>.</li>"
            + "<li>Outputs (vJoy, Xbox), Keyboard, Logical Device and OSC need no stick and always show.</li>"
                + "<li>A device with no background shows none; it never borrows another device's background.</li>"
            + "<li>Unplugging a stick while you edit keeps the edit on screen: \"&lt;name&gt; is disconnected. You can still save or cancel this edit.\"</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>When the device's module file is damaged, the map shows empty and Save is refused with the reason; Cancel leaves the damaged file as it is. To set the device up again, choose <b>Start Fresh…</b> on its card; the damaged file is kept as a copy.</li>"
            + "<li>If the Device Mapping Editor itself fails to start, the map shows \"The Device Mapping Editor could not load.\" The reason is written to qt.log (<b>Debug › Live Log Reader</b> <a href=\"show:menu/Debug/Live Log Reader\">Show me ›</a>, <b>Debug</b> tab, <b>Qt</b>).</li>"
            + "</ul>",
            ["device-mapping-editor-open", "device-mapping-editor-edit", "device-mapping-editor-print"]),

        // ---- The map -------------------------------------------------------
        t("device-mapping-editor-view", "The map", "Zoom, pan and use the grid",
            "<p>Zoom and pan to work on part of the map; the grid helps line items up.</p>"
            + "<ul>"
            + "<li>Scroll to zoom (50% to 600%); the <b>Zoom speed</b> setting in Device Map Options sets how fast. Drag with the middle button to pan.</li>"
            + "<li><b>View › Reset View</b> or <b>Ctrl+0</b> returns to 100%. <b>View › Zoom to Fit Page</b> (<b>Ctrl+1</b>) shows the whole page; <b>View › Zoom to Selection</b> (<b>Ctrl+2</b>) fills the view with what is selected.</li>"
            + "<li><b>View › Zoom In</b> (<b>Ctrl+=</b>) and <b>View › Zoom Out</b> (<b>Ctrl+-</b>) zoom a step at a time.</li>"
            + "<li><b>View › Grid</b> has <b>Show Grid</b> (<b>Ctrl+'</b>) and the grid <b>Size</b>. <b>View › Snap to Grid</b> (<b>Ctrl+Shift+'</b>) and <b>View › Snap to Entities</b> (<b>Ctrl+Shift+;</b>: edges and middles of other items, with guide lines) turn snapping on or off. Hold <b>Alt</b> while dragging to skip snapping.</li>"
            + "<li><b>View › Chips</b> (<b>F6</b>) and <b>View › Layers</b> (<b>F7</b>) bring out or fold the two side panels; <b>View › Properties</b> (<b>F4</b>) shows or hides Properties under Layers.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The view and the grid settings are kept with the device's map at once, while editing too; Cancel leaves them, and History doesn't list them.</li>"
            + "</ul>",
            ["device-mapping-editor-rulers", "device-mapping-editor-layers", "device-mapping-editor-properties"]),
        t("device-mapping-editor-rulers", "The map", "Use rulers and guides",
            "<p>Guides are lines you place to line items up.</p>"
            + "<ol>"
            + "<li>Choose <b>View › Rulers</b> (<b>Ctrl+R</b>) to show rulers along the top and left of the map while editing, marked in percent of the page.</li>"
            + "<li>Drag down out of the top ruler for a horizontal guide, or right out of the left ruler for a vertical one.</li>"
            + "<li>Drag a guide to move it; drop it on its ruler or off the page to remove it.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Items you move snap their edges or middles to a guide before anything else, and points (drawing, hotspots, line ends) snap to guides too; hold <b>Ctrl</b> while dragging to skip snapping.</li>"
            + "<li>Guides are kept with the device's map. Guides added, moved or removed while editing wait for Save: Undo steps through them and Cancel takes them back.</li>"
            + "<li><b>View › Show Guides</b> (<b>Ctrl+;</b>) hides and shows them, and <b>View › Clear Guides</b> removes them all. They never print or export.</li>"
            + "</ul>",
            ["device-mapping-editor-view"]),
        t("device-mapping-editor-background", "The map", "Background and foreground",
            "<p>A device map has two planes: the <b>Background</b>, the artwork behind everything, and the <b>Foreground</b> in front of it.</p>"
            + "<ul>"
            + "<li>The background holds pictures, shapes, lines and text, in any number of layers. Its bottom picture is the device's photo. Chips, groups, hotspots, leaders and tables stay in the foreground.</li>"
            + "<li>To edit the background, choose <b>Edit › Background › Edit Background</b>, right-click an empty part of the map and choose <b>Edit Background</b>, press <b>Ctrl+B</b>, or double-click the <b>Background</b> row at the bottom of Layers <a href=\"show:devicemappingeditor/dmeBgRow\">Show me ›</a>. While you edit the background, a banner reads \"Editing the background\" <a href=\"show:devicemappingeditor/dmeBgBanner\">Show me ›</a>; <b>Done</b>, <b>Exit Background Editing</b> on the same right-click menu, <b>Esc</b> or <b>Ctrl+B</b> go back to the foreground.</li>"
            + "<li>While you edit the background, the foreground shows faintly and can't be clicked. Clear <b>Show foreground faintly</b> on the banner to hide it. While you edit the foreground, the background shows but can't be clicked.</li>"
            + "<li><b>Edit › Background › Add Picture to Background…</b> (<b>Ctrl+I</b>) puts a picture on top of the background, fitted to the photo frame. <b>Background › Clear Background</b> removes every background layer.</li>"
            + "<li>To move items to the other plane, right-click them and choose <b>Move to Background</b> or <b>Move to Foreground</b> (<b>Ctrl+Shift+B</b>); the Layers panel's menu and the <b>Arrange</b> menu have them too. Kinds the background can't hold are greyed out, and their tooltip says why.</li>"
            + "<li>A picture's <b>Look</b> in Properties sets <b>Brightness</b> and <b>Contrast</b> (either way), <b>Greyscale</b> and <b>Opacity</b>, so the chips stand out against a busy picture. <b>Reset Shape</b> takes off a picture's crop, turn, flip and skew, and gives it back its own proportions.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Add Picture to Background, Clear Background and each move are one step for Undo, and Cancel puts back the background you started with.</li>"
            + "<li>The status line says <b>Foreground</b> or <b>Background</b> while editing.</li>"
            + "<li>In the foreground, the <b>Background</b> row in Layers has an <b>eye</b> that hides the background on screen only (the status line says <b>Background hidden</b>), a <b>lock</b> that locks every background layer, and an <b>Opacity</b> slider for how strongly it shows on screen. The eye, the slider and Show foreground faintly are the same for every map and never print.</li>"
            + "<li>Chips snapped to a snap point on a background picture follow it when it moves.</li>"
            + "<li>Print &amp; Export prints both planes; clear <b>Include background</b> to leave the background out.</li>"
            + "</ul>",
            ["device-mapping-editor-layers", "device-mapping-editor-pictures", "device-mapping-editor-print"]),
        t("device-mapping-editor-select", "The map", "Select items and find a control",
            "<p>Select items to move, style or delete them.</p>"
            + "<ul>"
            + "<li>Click an item to select it; Shift-click or Ctrl-click adds or removes; drag on empty space for a box selection. <b>Edit › Select All</b> (<b>Ctrl+A</b>) selects everything.</li>"
            + "<li>A click only selects: an item starts to move once you drag it a few pixels, so a click never shifts it or adds an Undo step.</li>"
            + "<li>Arrow keys nudge the selection by 1 px; Shift+Arrow nudges by 10 px.</li>"
            + "<li>Hold <b>Shift</b> while dragging to keep the move horizontal, vertical or at 45°; hold <b>Ctrl</b> to skip snapping. <b>Alt</b>+drag an item to drag a copy of the selection and leave the originals where they are (one Undo step).</li>"
            + "<li>While you move, resize or turn something, a small box beside the pointer shows how far it has moved, its size or its angle, in the units Properties uses.</li>"
            + "<li><b>Esc</b> while dragging cancels the drag: everything goes back to where it was, and nothing is added to Undo.</li>"
            + "<li><b>Press to find</b>: while editing, press a button or hat on the device and its chip is selected and scrolled into view (a group member selects its group). A control not on the map yet is shown in the pool, filtered by name; a hidden one is pointed to the Layers panel. Turn it off, or let a pushed axis count too (<b>Find axes</b>), in Device Map Options.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Undo and Redo are also at the top of every right-click menu.</li>"
            + "<li><b>Edit › Cut</b> (<b>Ctrl+X</b>) copies the selection and deletes it, as one Undo step; <b>Edit › Paste</b> (<b>Ctrl+V</b>) puts it back.</li>"
            + "</ul>",
            ["device-mapping-editor-keys", "device-mapping-editor-layers"]),
        t("device-mapping-editor-keys", "The map", "Device Mapping Editor keys",
            "<p><b>Help › Keyboard Shortcuts…</b> (<b>Ctrl+K</b>) <a href=\"show:devicemappingeditor/dmeMenuHelp\">Show me ›</a> opens a small window that lists every Device Mapping Editor key.</p>"
            + "<ul>"
            + "<li>The commands that have a key are grouped by menu (File, Edit, Insert, Arrange, Format, View, Background, Help), each with its key. The same keys show beside the commands in the menus; <a href=\"topic:device-mapping-editor-menus\">Device Mapping Editor menus</a> lists them all.</li>"
            + "<li>The <b>Mouse</b> group lists what you do with the mouse, such as <b>Alt</b>+drag on an empty part of the map to set the print area, <b>Alt</b>+drag on an item to drag a copy, <b>Ctrl</b> while dragging to skip snapping, and <b>Shift</b> while moving to keep to 45° steps.</li>"
            + "<li>The <b>Keys</b> group lists the keys that are not menu commands: the arrow keys nudge the selection by 1 px (<b>Shift</b>+arrow by 10 px), <b>Enter</b> finishes a path or a crop, <b>Backspace</b> takes back the last path point, and <b>Esc</b> cancels a drag, the tool, a crop (putting it back as it was), a rename or a group edit.</li>"
            + "<li>Type in its search box to show only the lines that match.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The window is a list to read: it runs nothing. Use the key, or the menu, to run a command.</li>"
            + "<li>Close it with the <b>×</b> on its title bar. Unpinned, a click anywhere else closes it too; pin it to keep it open (the pin is kept for next time).</li>"
            + "<li>A key works while its command can be used, and never while you type in a text box.</li>"
            + "<li>Commands that pick from a list (devices, templates, grid sizes and the like) and commands that clear a lot at once (<b>Reset Layout</b>, <b>Clear Background</b>, <b>Clear Print Area</b>, <b>Clear Guides</b>) have no key.</li>"
            + "<li>The Device Mapping Editor has no Command Palette.</li>"
            + "</ul>",
            ["device-mapping-editor-menus", "device-mapping-editor-select", "device-mapping-editor-context-menu"]),

        // ---- Chips ---------------------------------------------------------
        t("device-mapping-editor-chips", "Chips", "Place and style chips",
            "<p>A chip shows a control's name (Button 10, Axis 1, Hat 1) or its friendly name.</p>"
            + "<ol>"
            + "<li>Drag a chip from the pool onto the photo; drag it again to move it.</li>"
            + "<li>Double-click a chip to edit its name. <b>Shift+Enter</b> starts a second row.</li>"
            + "<li>Right-click it to style it.</li>"
            + "</ol>"
            + "<p>A chip's right-click menu has:</p>"
            + "<ul>"
            + "<li><b>Rename</b> and <b>Delete Chip</b> (back to the pool; <b>Delete</b> or <b>Backspace</b> does the same).</li>"
            + "<li><b>Chip Style</b>: font size, chip size, <b>Round</b>, <b>Square</b> or <b>Circle</b>, Filled or Hollow, and <b>Highlight on press</b>. A <b>Circle</b> is always a true circle: it grows to fit its label (<b>Circle Size</b> › <b>Auto</b>), or keeps a size you choose and makes the text smaller to fit.</li>"
            + "<li><b>Colors</b>: Fill Color…, Outline Color… and Text Color…, and <b>Pressed Fill…</b>, <b>Pressed Outline…</b> and <b>Pressed Text…</b> used while the control is held.</li>"
            + "<li><b>Hotspot</b> and <b>Leader Ends</b> (see <a href=\"topic:device-mapping-editor-hotspots\">Hotspots and leaders</a>), and <b>Arrange</b> (stacking, Lock, Hide).</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>To take chips off the map, drag them back onto the pool: the pool lights up, and letting go removes them. With several chips selected, they all go; a group goes whole, and while a group is being edited the member you drag leaves it. Locked chips stay. Undo brings them back.</li>"
            + "<li>The pool's filter box is on its top row, with <b>Reset</b> and <b>Chip only</b> on the row below. Tick <b>Chip only</b> (also in Device Map Options) to place chips on their own, with no leader and no hotspot. Add them later from the chip's menu (<b>Leader</b> › <b>Add Leader</b>, <b>Hotspot</b> › <b>Hide Hotspot</b>).</li>"
            + "<li><b>Ctrl+D</b> duplicates the selection; <b>Ctrl+C</b> and <b>Ctrl+V</b> copy and paste it inside the editor, and <b>Ctrl+X</b> cuts it (copies it, then deletes it). <b>Arrange › Rename</b> (<b>F2</b>) renames the selected chip. Copied chips stay copied when another device's map opens, so you can paste them there.</li>"
            + "</ul>",
            ["device-mapping-editor-hotspots", "device-mapping-editor-groups", "device-mapping-editor-styles"]),
        t("device-mapping-editor-action-labels", "Chips", "Show actions on chips",
            "<p>Chips can show what each control does in the profile instead of its name, so the map reads as a binding sheet: <b>Gear up</b> or <b>Ctrl+G</b> beside the button, not Button 23.</p>"
            + "<ol>"
            + "<li>Choose <b>Format › Chip Text</b> and pick <b>Name</b>, <b>Action</b>, or <b>Name and action</b> (also in Device Map Options › Labels).</li>"
            + "<li>Choose <b>Format › Labels Mode</b> and pick the mode whose actions to show, or <b>Follow the Program</b>: the running mode while the profile runs, otherwise the mode chosen in the program.</li>"
            + "</ol>"
            + "<p>What each action shows:</p>"
            + "<ul>"
            + "<li><b>Description</b>: its text. With Device Map Options › Labels › <b>Description first</b> on (the default), it stands for the whole binding.</li>"
            + "<li><b>Map to Keyboard</b>: the keys, such as Ctrl+G. <b>Map to vJoy</b> and <b>Map to Xbox</b>: the output, such as vJoy 1 B5. <b>Change Mode</b>: → and the target mode, or Cycle, Previous mode, Unwind mode. <b>Text to Speech</b>: what it says. Mouse, Macro, Load profile, Run command, Sound, Pause / resume and Logical Device show those words.</li>"
            + "<li>Actions inside Chain, Tempo, Double Tap, Condition and the like give their text; response curves and deadzones give none.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li><b>Several actions</b> shows the first one's text, or all of them joined with +. <b>No actions</b> sets what a chip shows when its control does nothing in that mode: its name, nothing, or a dash.</li>"
            + "<li>A control with no actions in a mode shows its parent mode's, as the running profile does.</li>"
            + "<li>Labels follow the profile as you edit it. Renaming a chip still edits its name.</li>"
            + "<li>The chosen Labels Mode follows a rename of that mode, goes back to <b>Follow the Program</b> when the mode is deleted, and is forgotten when the Device Mapping Editor closes.</li>"
            + "</ul>",
            ["device-mapping-editor-chips", "device-mapping-editor-options"]),
        t("device-mapping-editor-hotspots", "Chips", "Hotspots and leaders",
            "<p>Each chip has a <b>hotspot</b>, the mark on the photo at the physical control, and a <b>leader</b> line between them. Drag the chip and the hotspot separately.</p>"
            + "<p>A chip's <b>Hotspot</b> section sets how the mark looks: <b>Size</b>; <b>Shape</b> (Round, Square, Diamond, Triangle pointing along the leader, Ring, Target, Crosshair, Plus, X, Pin, or None for no mark); <b>Fill</b> (Filled, Hollow, Half); <b>Line</b> (Thin, Medium, Thick); <b>Opacity</b>; <b>Halo</b>, a soft glow that stands out on busy photos; <b>Number</b>, the control's number inside; <b>Highlight on press</b>, the <b>Pressed Color…</b> while the control is held; <b>Pulse on press</b>, a ring that grows from it on each press; <b>Show on live map</b>, off to see it only while editing; and <b>Hotspot Color…</b>.</p>"
            + "<p>To bend a leader:</p>"
            + "<ol>"
            + "<li>Select the leader.</li>"
            + "<li>Drag a segment to bend it; that adds a curve point (a spine).</li>"
            + "<li>To delete a spine, hold the right button on it for about half a second.</li>"
            + "</ol>"
            + "<p>Right-click a leader for <b>Add Leader</b> (another line from the same chip) and <b>Delete leader</b>. Its <b>Leader</b> section has <b>Leader Color…</b>, <b>Weight</b>, <b>Add Straight Spine</b>, <b>Add Curved Spine</b>, <b>Convert Spine</b>, <b>This Segment</b> or <b>All Segments</b> (Curved or Straight), <b>Branch from This End</b>, <b>Clear All Spines</b> and <b>Delete Spine</b>. <b>Leader Ends</b> detaches the chip end or the hotspot end, and reconnects it.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Spines show only while editing; the lines stay on the live map.</li>"
            + "<li>In the Layers panel, open a chip to hide or lock its hotspot or one leader on its own.</li>"
            + "</ul>",
            ["device-mapping-editor-chips", "device-mapping-editor-layers"]),
        t("device-mapping-editor-groups", "Chips", "Group chips",
            "<p>A group moves as one, keeping its chips where you put them.</p>"
            + "<ol>"
            + "<li>Line the chips up first with <b>Align</b>, the arrow keys or by dragging.</li>"
            + "<li>Select two or more chips (Shift-click, or drag a box on empty space).</li>"
            + "<li>Choose <b>Group Selected</b> on the right-click menu, or <b>Arrange › Group Selected</b> (<b>Ctrl+G</b>).</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Break Group</b> (<b>Ctrl+Shift+G</b>, also on the Arrange menu) splits it. <b>Edit Group</b> lets you move and style one member; <b>Done Editing Group</b> or <b>Esc</b> ends that.</li>"
            + "<li><b>Align Members</b> arranges a group Left, Center, Right or Free (Free keeps your own arrangement; new groups start as Free).</li>"
            + "<li>To turn a group, select it and drag the round handle above it, or right-click and choose <b>Turn group</b>. Its chips swing round the group's middle and stay upright so they still read; the hotspot stays on the photo.</li>"
            + "<li>Right-click a five-chip hat group: <b>Style</b> › <b>Format</b> shows it as <b>Plus</b>, <b>Mini hat</b> or <b>Radial</b>; <b>Clear Format</b> removes it.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Grouping chips or text boxes together with a table packs them into the table. See <a href=\"topic:device-mapping-editor-tables\">Add a table</a>.</li>"
            + "</ul>",
            ["device-mapping-editor-align", "device-mapping-editor-tables"]),
        t("device-mapping-editor-mirror", "Chips", "Mirror the layout",
            "<p><b>Edit › Mirror Layout</b> turns the whole map left to right while editing.</p>"
            + "<ul>"
            + "<li>Every chip, group, drawing and picture goes to the other side of the page, with its hotspot, leader bends and loose leader ends.</li>"
            + "<li>Shapes and lines are mirrored, so an arrow points the other way; text boxes, tables and the arrangement inside a group stay as they are, so they still read.</li>"
            + "<li>Pictures move but are only flipped when Device Map Options › Editing › <b>Mirror pictures</b> is on.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>One Undo puts it back.</li>"
            + "<li>To lay out a left-hand stick from a right-hand one, see <a href=\"topic:device-mapping-editor-copy-from-device\">Copy a device map from another device</a>.</li>"
            + "</ul>",
            ["device-mapping-editor-copy-from-device"]),
        t("device-mapping-editor-copy-from-device", "Chips", "Copy a device map from another device",
            "<p>Start a map from another device's layout.</p>"
            + "<ol>"
            + "<li>While editing, choose <b>Edit › Copy Device Map from Device</b>. It lists the other devices that have a device map.</li>"
            + "<li>Pick one. Tick <b>Mirror left to right</b> for the other hand's stick.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>It replaces this map's foreground: chips, leaders and drawings. This device's background stays, unless you tick <b>Copy the background too</b>.</li>"
            + "<li>One Undo puts the old layout back, mirrored or not, and nothing is saved until you save.</li>"
            + "</ul>",
            ["device-mapping-editor-mirror", "device-mapping-editor-templates"]),
        t("device-mapping-editor-templates", "Chips", "Use layout templates",
            "<p>A template keeps a map's chips, leaders and drawings under a name, to put on any device.</p>"
            + "<ul>"
            + "<li><b>Save Layout as Template…</b> keeps this map's layout under a name. A name already used asks before replacing it (<b>Replace Template</b>). An empty map can't be saved as a template.</li>"
            + "<li><b>Apply Template</b> puts one on the device you are editing. It asks first; Undo puts the old layout back.</li>"
            + "<li><b>Manage Templates…</b> renames, deletes, exports a template to a file to share, and imports one. An imported template whose name is taken gets a number. Delete asks first (\"Delete template “Name”?\", \"Layouts made from it are not changed.\"); the red <b>Delete Template</b> deletes it, and this can't be undone. A rename or export that fails says why in red on the message line.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>When a rename or export fails, the message names the file, the folder and the reason.</li>"
            + "<li>A template keeps where its pictures are, not the picture files themselves.</li>"
            + "<li>Device Map Options › <b>Library</b> also renames and deletes templates.</li>"
            + "</ul>",
            ["device-mapping-editor-copy-from-device", "device-mapping-editor-styles"]),

        // ---- Drawing -------------------------------------------------------
        t("device-mapping-editor-context-menu", "Drawing", "Right-click menu",
            "<p>While editing, the right-click menu shows only what applies to what you right-clicked: a chip, a group, a leader, a shape, a line, a picture, a text box, a table, several selected items, or empty canvas.</p>"
            + "<ul>"
            + "<li>It opens small: the item's name with <b>Undo</b> and <b>Redo</b>, a few actions, then sections such as Chip style or Arrowheads.</li>"
            + "<li>Select a section to open it; one is open at a time, and the menu reopens on the section you used last for that kind of item.</li>"
            + "<li>Rows of values (sizes, widths, opacity) change straight away and leave the menu open; other actions close it.</li>"
            + "</ul>"
            + "<h4>Always there</h4>"
            + "<ul>"
            + "<li><b>Repeat</b> is the first row once you have run a command: its label names it, such as <b>Repeat \"Rotate +90°\"</b>, and it runs that command again on what is selected now. It repeats the last command run from a menu, a right-click menu or a key; never Undo, Redo, Copy, Select All or a View command, and it shows only when that command applies.</li>"
            + "<li>Every item has <b>Cut</b> (<b>Ctrl+X</b>) beside Copy, <b>Show in Layers</b> (opens Layers at the item's row and highlights it) <a href=\"show:devicemappingeditor/layersSide\">Show me ›</a> and <b>Properties…</b> (<b>F4</b>) <a href=\"show:devicemappingeditor/propsPanel\">Show me ›</a>.</li>"
            + "<li>Empty canvas has <b>Paste Here</b>, which puts the middle of the pasted items on the spot you right-clicked, and <b>Select All</b> (<b>Ctrl+A</b>). Cut, Select All and Paste are in the <b>Edit</b> menu too <a href=\"show:devicemappingeditor/dmeMenuEdit\">Show me ›</a>.</li>"
            + "</ul>"
            + "<h4>Favourites</h4>"
            + "<ul>"
            + "<li>Hover a command's row in a right-click menu or in the menu bar's Insert, Arrange, Leader, Format or Edit menu (Cut, Copy, Paste, Duplicate, Delete, Select All) and select the <b>☆</b> at its end to add it to your favourites; a ★ means it is one already, and selecting it takes it off. Rows that pick a value (colours, sizes, sliders) have no ☆.</li>"
            + "<li>An item's own <b>Hide</b> and <b>Lock</b> rows (Hide Chip, Lock Chip, Hide Shape and so on) have the ☆ too. As a favourite, Hide or Lock acts on everything selected, not only the item you right-clicked. The rows that hide or lock only a hotspot or a leader line have no ☆.</li>"
            + "<li>Favourites are listed at the very top of every right-click menu under <b>Favourites</b>, in the order you added them, and only those that apply to what you right-clicked. Select the <b>×</b> at a favourite's end to remove it.</li>"
            + "<li>One list for every device, kept for next time; it belongs to the program, not to a device's map.</li>"
            + "<li>Device Map Options › <b>Right-click menu</b> › <b>Favourites shown</b> sets how many show (5 at first, up to 15); 0 hides the Favourites section. Open Options from <b>Edit › Device Map Options…</b> (<b>Ctrl+,</b>) <a href=\"show:devicemappingeditor/dmeMenuEdit\">Show me ›</a>.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Keys: <b>Up</b> and <b>Down</b> move, <b>Enter</b> acts, <b>Right</b> and <b>Left</b> open or close a section or step a row of values, <b>Esc</b> closes.</li>"
            + "<li>The <b>Insert</b>, <b>Arrange</b> and <b>Format</b> menus in the menu bar hold the same commands for the selection, with their keys (see <a href=\"topic:device-mapping-editor-menus\">Device Mapping Editor menus</a>).</li>"
            + "<li>Near a window edge the menu opens the other way, and it scrolls when it is taller than the window.</li>"
            + "</ul>",
            ["device-mapping-editor-menus", "device-mapping-editor-keys"]),
        t("device-mapping-editor-shapes", "Drawing", "Draw shapes",
            "<p>Shapes mark areas of the photo or frame groups of chips.</p>"
            + "<ol>"
            + "<li>Choose <b>Insert</b>, or right-click empty canvas and choose <b>Draw</b>, and pick a <b>Shape</b>: Rectangle, Rounded, Ellipse, Triangle, Diamond, Arrow or Double arrow.</li>"
            + "<li>Drag on the photo to draw it; hold <b>Shift</b> to keep its proportions, <b>Alt</b> to draw it out from the center (where you pressed), or both for a perfect shape from the center.</li>"
            + "<li>The tool stays on for the next one until <b>Stop Drawing</b> or <b>Esc</b>.</li>"
            + "</ol>"
            + "<p>Right-click a shape for <b>Duplicate</b> and <b>Delete</b>, then sections: <b>Shape</b> (change the kind), <b>Fill and Outline</b> (Filled or Hollow, Fill Color…, Outline Color…, Width, outline Solid, Dashed or Dotted, Opacity), <b>Rotate and Flip</b> and <b>Arrange</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>With chips selected, <b>Shape Around Selection</b> draws a shape around them that moves with them; its <b>Padding</b> sets the gap, and Arrange › <b>Detach from Chips</b> frees it.</li>"
            + "</ul>",
            ["device-mapping-editor-transform", "device-mapping-editor-rotate", "device-mapping-editor-lines"]),
        t("device-mapping-editor-lines", "Drawing", "Draw lines and arrows",
            "<p>Lines and arrows point at parts of the photo.</p>"
            + "<ol>"
            + "<li>Choose <b>Insert</b>, or right-click empty canvas and choose <b>Draw</b> › <b>Line</b>, and pick <b>Line</b> or <b>Arrow</b>.</li>"
            + "<li>Drag from one end to the other; hold <b>Shift</b> to keep to 45° steps.</li>"
            + "</ol>"
            + "<ul>"
            + "<li>A selected line has a handle on each end; drag one to move that end (<b>Shift</b> for 45° steps). To turn a line, move its ends.</li>"
            + "<li>Its <b>Arrowheads</b> section sets the <b>Start</b> and <b>End</b> to None, Solid or Hollow; <b>Swap Heads</b> turns them round.</li>"
            + "<li>Its <b>Line</b> section has Color…, Width, Outline (Solid, Dashed or Dotted) and Opacity, and <b>Flip</b> mirrors it.</li>"
            + "</ul>",
            ["device-mapping-editor-paths", "device-mapping-editor-shapes"]),
        t("device-mapping-editor-paths", "Drawing", "Draw paths and freehand",
            "<p>A path goes through several points; freehand follows the pointer.</p>"
            + "<ol>"
            + "<li>Choose <b>Path</b> on the <b>Insert</b> menu, or <b>Draw</b> › <b>Line</b> › <b>Path</b> on the right-click menu.</li>"
            + "<li>Click each point. Click the first point again to close the shape, or double-click, press <b>Enter</b> or right-click to finish an open path. <b>Shift</b> keeps each segment to 45° steps.</li>"
            + "<li>The tool stays on for the next path; <b>Esc</b> stops it.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Draw</b> › <b>Line</b> › <b>Freehand</b> draws while the button is held down. When you let go, the stroke is tidied (fewer points, same shape) and smoothed.</li>"
            + "<li>A selected path shows a small round handle on each point: drag one to move it. Its box's handles resize the whole path, and it turns and flips like a shape.</li>"
            + "<li>Right-click a path: <b>Path</b> › <b>Closed</b> and <b>Smooth</b>; <b>Line</b> › color, width, Solid, Dashed or Dotted, opacity; an open path has <b>Arrowheads</b> at its start and end, a closed one a <b>Fill</b> (Filled or Hollow, Fill color…).</li>"
            + "</ul>",
            ["device-mapping-editor-lines", "device-mapping-editor-transform"]),
        t("device-mapping-editor-rotate", "Drawing", "Rotate, flip and resize items",
            "<p>Shapes, text boxes and pictures can be turned, flipped and resized.</p>"
            + "<ul>"
            + "<li>A selected item has a round handle above it: drag it to turn the item to any angle, with <b>Shift</b> for steps (15° unless Device Map Options › Editing › <b>Rotate snap</b> says otherwise).</li>"
            + "<li>The <b>Rotate and Flip</b> section has an <b>Angle</b> to type, <b>Turn to</b> 0°, 90°, 180° or 270°, <b>Rotate −15°</b> and <b>Rotate +15°</b>, and <b>Flip Horizontally</b> and <b>Flip Vertically</b>. The <b>Arrange</b> menu has them with keys: <b>Flip Horizontally</b> (<b>Shift+H</b>), <b>Flip Vertically</b> (<b>Shift+V</b>), and a rotate step (<b>Ctrl+Alt+Right</b> or <b>Ctrl+Alt+Left</b>). Properties takes an exact Angle.</li>"
            + "<li>Drag the square handles to resize. A turned item resizes along its own sides, and the opposite side stays where it is. A picture always fills its box, so its handles stay on its edges.</li>"
            + "<li>From a corner, pictures and shapes keep their proportions; hold <b>Shift</b> to resize freely. Text boxes, callouts, tables and lines resize freely, and keep their proportions with <b>Shift</b>.</li>"
            + "<li>A side handle stretches the item one way only. Hold <b>Alt</b> on any handle to resize from the center. Drag a handle past the opposite edge to mirror the item.</li>"
            + "<li><b>Ctrl+Shift</b>+drag a side handle to skew the item along that side.</li>"
            + "<li>The pointer turns into a two-headed arrow over a resize handle and a hand over the round handle.</li>"
            + "<li>In <b>Properties</b>, the link button between <b>Width</b> and <b>Height</b> (on to start with) keeps the proportions: change one and the other follows.</li>"
            + "</ul>"
            + "<p>To turn several items together:</p>"
            + "<ol>"
            + "<li>Select two or more items. A dashed box goes round them with one round handle above it.</li>"
            + "<li>Drag the handle to turn them all about their middle (the angle shows beside the handle), or use the right-click menu's <b>Turn together</b> to turn them by a step, a quarter turn or a half turn.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Several selected items also have eight square handles on their dashed box: a corner resizes them all and keeps the box's proportions (<b>Shift</b> frees it), a side stretches, <b>Alt</b> resizes from the center. Pictures and shapes grow and shrink; chips, hotspots and text keep their size and only move. It is one Undo step.</li>"
            + "<li>Turning together: shapes, text boxes and pictures turn, lines swing round with both ends, and chips, groups and tables move round but stay upright so they still read. Hotspots stay on the photo; locked items stay put. Turning there and back puts them where they were.</li>"
            + "<li>Lines turn by moving their ends. Tables, chips and hotspots do not turn on their own.</li>"
            + "</ul>",
            ["device-mapping-editor-transform", "device-mapping-editor-groups"]),
        t("device-mapping-editor-transform", "Drawing", "Reshape, bend and skew items",
            "<p>Transform handles change an item's shape beyond resizing.</p>"
            + "<ol>"
            + "<li>Right-click a shape, picture or text box and choose <b>Transform</b> › <b>Handles</b>.</li>"
            + "<li>Pick the handles to show. Only the choices that suit the item appear.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Resize</b>: the box's eight handles and the rotate handle, as usual.</li>"
            + "<li><b>Shape</b>: blue diamonds that reshape the item. On a block arrow or double arrow, one at the head sets the head's length (drag along) and width (drag out), one on the shaft sets its thickness. On a rounded rectangle it sets the corners' roundness; on a triangle, where its point is.</li>"
            + "<li><b>Tips</b> (block arrows): a diamond on each end. Drag one anywhere and the arrow stretches and turns to reach it; <b>Shift</b> keeps to angle steps.</li>"
            + "<li><b>Bend</b> (block arrows): a diamond on the middle of the shaft. Drag it to curve the arrow; the box grows so the arrow keeps its thickness.</li>"
            + "<li><b>Skew</b>: a diamond on the top edge leans the item sideways, one on the right edge leans it up or down. With any handles shown, <b>Ctrl+Shift</b>+drag a side handle skews too.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li><b>Edit Points</b> turns a shape into a path with a handle on every corner, looking as it does now (shaped, bent, skewed, turned), so any corner can be moved; it is then a path, not an arrow.</li>"
            + "<li><b>Reset Shape</b> (also on the <b>Arrange</b> menu) takes away the shaping, bend and skew, and gives a picture back its own proportions (keeping its width and center). Undo steps back through all of it.</li>"
            + "<li>The choice goes back to Resize when you select something else.</li>"
            + "</ul>",
            ["device-mapping-editor-shapes", "device-mapping-editor-rotate"]),
        t("device-mapping-editor-text-boxes", "Drawing", "Add a text box",
            "<p>Text boxes add notes and titles to the map.</p>"
            + "<ol>"
            + "<li>Choose <b>Text box</b> on the <b>Insert</b> menu, or <b>Draw</b> › <b>Box</b> › <b>Text box</b> on the right-click menu, then drag.</li>"
            + "<li>Double-click the text box (or choose <b>Format › Edit Text…</b>, <b>Enter</b>) and type.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Text</b>: Font size, Bold, Word wrap, <b>Scale font with box</b>, and alignment Across (Left, Center, Right) and Down (Top, Middle, Bottom).</li>"
            + "<li><b>Box</b>: preset Size (Caption, Small, Medium, Large, Title, Wide), Theme (Dark, Hollow, Sheet), Text Color…, Fill Color…, Outline Color…, Fill opacity and Outline opacity.</li>"
            + "<li><b>Copy and Paint Format</b>: <b>Copy Format</b> (<b>Format › Copy Format</b>, <b>Ctrl+Alt+C</b>) takes this box's look; <b>Format › Paste Format</b> (<b>Ctrl+Alt+V</b>) puts it on the selection; <b>Paint format</b> puts it on the next boxes you select; <b>Clear Formatting</b> resets it; <b>Copy Text</b> copies the words.</li>"
            + "</ul>",
            ["device-mapping-editor-callouts", "device-mapping-editor-styles"]),
        t("device-mapping-editor-callouts", "Drawing", "Add a callout",
            "<p>A callout is a text box with a pointer.</p>"
            + "<ol>"
            + "<li>Choose <b>Callout</b> on the <b>Insert</b> menu (or <b>Draw</b> › <b>Box</b> › <b>Callout</b>) and drag the box, or select a chip and choose <b>Leader › Add Callout</b> (also on its right-click menu) for one beside the chip, pointing at it and showing its text.</li>"
            + "<li>Select the callout to see the round handle at the pointer's tip. Drag it anywhere to point at a spot on the photo, or drop it on a chip so the pointer follows that chip when it moves (the handle is filled while it does).</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Everything a text box does, a callout does too: typing, fonts, themes, colors, paint format, turning.</li>"
            + "<li>The pointer leaves the side of the box facing its tip.</li>"
            + "<li>The text box's <b>Pointer</b> section: <b>Detach from Chip</b> keeps the pointer where it is without following, <b>Remove Pointer</b> makes it a plain text box, and on a plain text box <b>Add Pointer</b> makes it a callout.</li>"
            + "</ul>",
            ["device-mapping-editor-text-boxes"]),
        t("device-mapping-editor-tables", "Drawing", "Add a table",
            "<p>Tables list controls and their uses beside the photo.</p>"
            + "<ol>"
            + "<li>Choose <b>Table</b> on the <b>Insert</b> menu, or <b>Draw</b> › <b>Box</b> › <b>Table</b> on the right-click menu, then drag.</li>"
            + "<li>Double-click a cell to type in it.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Rows and Columns</b>: Insert Row Above, Delete This Row, Insert Column Left, Delete This Column, and an <b>ID column</b>. The inserts are on the <b>Insert</b> menu too, and the cell formats on the <b>Format</b> menu.</li>"
            + "<li><b>Cell</b>: <b>Free position</b> lets a cell be dragged out of the grid; <b>Independent of table</b> keeps it still when the table moves; <b>Spawn Empty Cell</b> adds a loose cell; <b>Delete This Cell</b>; <b>Place Across</b> and <b>Place Down</b> park a cell at a side.</li>"
            + "<li><b>Look</b>: Theme (Dark, Hollow, Sheet) and font size.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Select a table with chips or text boxes on it and choose <b>Group Selected</b>: they are packed into the table and move with it. <b>Break Group</b> takes them out again; <b>Delete Table</b> removes it.</li>"
            + "</ul>",
            ["device-mapping-editor-groups", "device-mapping-editor-text-boxes"]),
        t("device-mapping-editor-pictures", "Drawing", "Add pictures",
            "<p>Pictures in the foreground sit over the background, for logos, icons or close-ups; pictures can also be moved to the background (see <a href=\"topic:device-mapping-editor-background\">Background and foreground</a>).</p>"
            + "<ul>"
            + "<li><b>Insert › Import Picture…</b> (or <b>Draw</b> › <b>Import Picture…</b> on the right-click menu) adds a picture file.</li>"
            + "<li><b>Edit › Paste Picture</b> (<b>Ctrl+Shift+V</b>), or <b>Paste Picture</b> in the canvas's Draw section, adds the picture on the clipboard: a copied picture, or picture files copied in File Explorer. <b>Ctrl+V</b> pastes a picture too when it was copied after your last chip copy.</li>"
            + "<li>Drag picture files from File Explorer onto the map while editing: each lands where you drop it, at its own shape.</li>"
            + "</ul>"
            + "<p>A picture moves, resizes, turns and flips like a shape. Its <b>Picture</b> section has:</p>"
            + "<ul>"
            + "<li><b>Crop</b>: the handles turn blue and cut the picture instead of scaling it; what stays does not move. <b>Shift</b> on a corner keeps the crop's proportions. <b>Enter</b> or selecting something else ends it and keeps the crop; <b>Esc</b> ends it and puts the crop back as it was. <b>Reset Crop</b> (also on the <b>Arrange</b> menu) shows the whole picture again; Properties takes exact crop values.</li>"
            + "<li><b>Add snap point</b> (then select a spot on the picture) and <b>Clear Snap Points</b>: chips snap to these points.</li>"
            + "<li>Opacity.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Pictures are saved beside the device's module file.</li>"
            + "<li>A picture dropped while not editing is refused: \"Click Edit Mapping first, then drop the picture again.\"</li>"
            + "</ul>",
            ["device-mapping-editor-rotate", "device-mapping-editor-background"]),
        t("device-mapping-editor-styles", "Drawing", "Save and apply styles",
            "<p>A look you use often can be kept under a name and put on other items.</p>"
            + "<ol>"
            + "<li>Select a chip, shape, line, path or text box and choose <b>Format › Save This Style…</b>, or right-click it and choose <b>Saved Styles</b> › <b>Save This Style…</b>.</li>"
            + "<li>Give it a name, such as Weapons, red. A style of the same name and kind is replaced.</li>"
            + "<li>To use it, select items of that kind, open the same section and choose <b>Apply</b> beside the style. It is one step for Undo.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A chip's style holds its chip, text, pressed, hotspot and leader colors and sizes; a shape's its fill and outline; a line's its color, width, outline and arrowheads; a text box's its format.</li>"
            + "<li>Styles are shared by every device. <b>Edit › Device Map Options…</b> › <b>Library</b> renames and deletes them (it asks first; items that use a deleted style keep their look), and the layout templates too.</li>"
            + "</ul>",
            ["device-mapping-editor-templates", "device-mapping-editor-options"]),

        // ---- Panels --------------------------------------------------------
        t("device-mapping-editor-layers", "Panels", "Layers panel",
            "<p>The <b>Layers</b> panel <a href=\"show:devicemappingeditor/layersSide\">Show me ›</a> folds into the map's right edge, with Properties under it; click its bar, choose <b>View › Layers</b> (<b>F7</b>) or press <b>Ctrl+F</b> to bring it out (see <a href=\"topic:device-mapping-editor-side-panels\">Chips and Layers side panels</a>). It shows the items of the plane you are editing, top of the stack first. In the foreground it ends with a folded <b>Background</b> row; while you edit the background it lists only the background layers (see <a href=\"topic:device-mapping-editor-background\">Background and foreground</a>).</p>"
            + "<ul>"
            + "<li>The <b>eye</b> hides an item: it is not drawn, on the live map either, and is left out of exports.</li>"
            + "<li>The <b>lock</b> keeps an item in place: clicks pass through it, and it is not moved, nudged or deleted. <b>Arrange › Lock / Unlock</b> (<b>Ctrl+L</b>) locks or unlocks the selection; <b>Arrange › Unlock All</b> (<b>Ctrl+Shift+L</b>) unlocks everything; <b>Arrange › Hide</b> (<b>Ctrl+Shift+H</b>) hides the selection.</li>"
            + "<li>Open a chip (the arrow) to hide or lock its hotspot or each leader on its own. Locking or hiding the chip covers them all.</li>"
            + "<li>Drag a row up or down to change what is on top. The right-click menu's <b>Arrange</b> section and the <b>Arrange</b> menu do the same a step at a time: <b>Bring to Front</b> (<b>Ctrl+Shift+]</b>), <b>Bring Forward</b> (<b>Ctrl+]</b>), <b>Send Backward</b> (<b>Ctrl+[</b>), <b>Send to Back</b> (<b>Ctrl+Shift+[</b>).</li>"
            + "<li>Select a row to select the item (Ctrl or Shift to add); a right-click selects it too before its menu opens (a row in a selection keeps the selection). Double-click a drawing's row to name it.</li>"
            + "<li><b>Show all</b> and <b>Unlock all</b> undo every hide and lock.</li>"
            + "<li><b>Delete</b> on an open group's row removes the whole group.</li>"
            + "</ul>",
            ["device-mapping-editor-search-layers", "device-mapping-editor-properties"]),
        t("device-mapping-editor-search-layers", "Panels", "Search and filter layers",
            "<p>Find rows in the Layers panel by name or kind.</p>"
            + "<ol>"
            + "<li>Press <b>Ctrl+F</b> or choose <b>View › Search layers…</b>. Layers comes out if it is folded.</li>"
            + "<li>Type in <b>Search layers…</b>, the box under the panel's header.</li>"
            + "<li>Press <b>Enter</b> to select every match on the map and bring the first into view. <b>Esc</b> or the box's <b>×</b> clears it.</li>"
            + "</ol>"
            + "<p>It finds, in any case and anywhere in: the row's name, the control (Button 12, Hat 1, X Axis, even when the chip has a friendly name), what the chip shows (its action or description), and the kind of row.</p>"
            + "<p>Under the box, one toggle per kind of row: <b>All · Chips · Groups · Hotspots · Leaders · Shapes · Lines · Pictures · Text · Tables</b>; while you edit the background, <b>Shapes · Lines · Pictures · Text</b>. Turn on any number of kinds to show only those; with none on, every row shows and <b>All</b> lights; <b>All</b> turns them all off again. The search looks only in the kinds that are on.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A matching hotspot, leader or group member shows under its chip or group, which is dimmed when it doesn't match itself.</li>"
            + "<li>While a filter is on, a line says how many rows match (12 of 148) or <b>No layers match</b>. The eye, lock, rename, drag and delete work on the rows shown.</li>"
            + "<li>A group member found by the search can be selected, but its eye and lock are greyed out and it can't be deleted: hide, lock or delete the whole group from its row.</li>"
            + "<li><b>Ctrl+F</b> works only while editing, as Layers shows only then.</li>"
            + "<li>The kinds and the search stay while the Device Mapping Editor is open, also when another device's map is shown; they go back to none and empty when the Device Mapping Editor closes.</li>"
            + "</ul>",
            ["device-mapping-editor-layers"]),
        t("device-mapping-editor-properties", "Panels", "Properties panel",
            "<p><b>Properties</b> <a href=\"show:devicemappingeditor/propsPanel\">Show me ›</a> shows the selected item's exact values while editing. It sits in the right side panel, under Layers, and shows when something is selected. Drag the divider between Layers and Properties to give one more room; where it sits is kept for next time. <b>View › Properties</b> (<b>F4</b>) shows or hides it. Positions and sizes are in percent of the page.</p>"
            + "<ul>"
            + "<li>A shape or picture: X, Y, Width, Height and Angle, then fill, colors, line width, outline and opacity; a picture also has Crop left, top, right and bottom.</li>"
            + "<li>A line: Start and End X and Y, color, width, outline and the Start and End heads.</li>"
            + "<li>A chip: its place and its hotspot's, font size, chip size and colors.</li>"
            + "<li>Several items: only the style shows, and a change applies to all of them.</li>"
            + "</ul>"
            + "<p>Type a number and press <b>Enter</b>, or select a color to open the color picker.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A locked item's values show but do not change.</li>"
            + "</ul>",
            ["device-mapping-editor-layers", "device-mapping-editor-colors"]),
        t("device-mapping-editor-align", "Panels", "Align and distribute items",
            "<p>Line items up or space them evenly.</p>"
            + "<ol>"
            + "<li>Select several items and right-click one of them.</li>"
            + "<li>In <b>Align and Distribute</b>, line them up <b>Across</b> (Left, Center, Right) or <b>Down</b> (Top, Middle, Bottom) by their edges or middles, or choose <b>Space Out</b> to leave equal gaps between three or more.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Locked items stay where they are.</li>"
            + "</ul>",
            ["device-mapping-editor-groups"]),
        t("device-mapping-editor-colors", "Panels", "Choose colors",
            "<p>The color picker opens from Colors, Fill color…, Outline color… and the Properties swatches.</p>"
            + "<ul>"
            + "<li>Drag in the square and the bar, or select a swatch; the change shows at once.</li>"
            + "<li><b>Recent</b> shows the colors you used last, on any device. Device Map Options › Colors sets how many.</li>"
            + "<li><b>Pick from Map</b> closes the picker; select anywhere in the window to take the color there (right-click or <b>Esc</b> gives up).</li>"
            + "</ul>",
            ["device-mapping-editor-properties", "device-mapping-editor-styles"]),

        // ---- Print and export ----------------------------------------------
        t("device-mapping-editor-print", "Print and export", "Print or export the map",
            "<p><b>File › Print &amp; Export…</b> (<b>Ctrl+P</b>) has every print and export in one place.</p>"
            + "<ol>"
            + "<li>Open <b>Print &amp; Export…</b>. A preview shows the page as it will come out.</li>"
            + "<li>Choose the paper (Letter, Legal, Tabloid, A3, A4, A5), its orientation, the margins, the page and whether to include the background. Under <b>Custom</b> are the scale and <b>Freeform (As Drawn)</b>.</li>"
            + "<li>Press <b>Print…</b>, <b>Export PDF…</b>, <b>Export PNG…</b> or <b>Export JPG…</b>.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Scale</b>: the size in pixels of every export and print. 100% is the bottom background picture's own size, pixel for pixel (without one, the page 1920 pixels wide). The window shows the pixels, and on a paper how many dots an inch they print at: the print area fills the paper inside its margins.</li>"
            + "<li><b>Freeform (As Drawn)</b> sets no paper: the print area keeps whatever shape you draw (Paper, Orientation and Margins grey out), and a PDF gets a page of that shape, at 96 pixels an inch.</li>"
            + "<li><b>Page</b>: <b>Dark</b>, as on screen, or <b>Light</b>, a white page where every color has its lightness turned over, so dark chips come out light with dark text and a dark red becomes a light red, while pictures stay as they are. The screen does not change.</li>"
            + "<li><b>Include background</b> (on at first) prints the background under the foreground; clear it to leave the background out.</li>"
            + "<li>The preview follows the print area as it moves or is resized on the map, and sharpens a moment after it stops. In the preview, drag the picture to move the print area and turn the mouse wheel to zoom: in makes the print area smaller, out larger, about the pointer, keeping its shape.</li>"
            + "<li><b>Print…</b> prints the print area as Export draws it, on the chosen paper and margins. Windows' printer dialog comes first. With <b>Freeform (As Drawn)</b> it goes on the paper chosen in the printer dialog, turned to landscape when wider than tall.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The settings are kept with the map and are the same for every print and export. The size of the window or the screen's scale makes no difference.</li>"
            + "<li>Every print and export takes the print area, whatever the zoom. Selection marks, handles, guides and the grid are left off, and so are hidden items. Lines and text are drawn at the export's size, not enlarged. A PDF goes on the chosen paper, inside its margins.</li>"
            + "<li>While an export is still being written, Print &amp; Export shows <b>Exporting…</b> and the Export buttons wait: one export runs at a time.</li>"
            + "<li>An export's longest side is at most 16384 pixels; a larger Scale is made smaller to fit.</li>"
            + "<li>When an export can't be written, the message line says why in red, with the file, the folder and the reason, such as a read-only folder or a file open in another program.</li>"
            + "<li>An unplugged stick's map still exports.</li>"
            + "</ul>",
            ["device-mapping-editor-print-area"]),
        t("device-mapping-editor-print-area", "Print and export", "Set the print area",
            "<p>The print area is the part of the page every export and print takes.</p>"
            + "<ol>"
            + "<li>Hold <b>Alt</b> and drag on an empty part of the map, or choose <b>View › Set Print Area</b>, then drag.</li>"
            + "<li>Show it with <b>View › Show Print Area</b> while editing: everything outside is dimmed, with handles to resize it and its border to move it. Choose it again to hide it.</li>"
            + "<li>To go back to the whole page, choose <b>View › Clear Print Area</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li><b>View › Print Area Color…</b> sets the color of the print area's frame on screen.</li>"
            + "<li>With a paper chosen, it keeps the paper's shape, so what it frames fills the page.</li>"
            + "<li>It never shows on the live map.</li>"
            + "<li>A print area drawn or changed while editing waits for Save: Undo steps through it and Cancel takes it back. It is kept with the map.</li>"
            + "</ul>",
            ["device-mapping-editor-print"]),

        // ---- Common questions ----------------------------------------------
        t("device-mapping-editor-qa-actions", "Common questions", "Does moving a chip change my bindings?",
            "<p>No. Chips are layout only: moving, renaming or deleting one never changes the actions in the profile. See <a href=\"topic:device-mapping-editor-about\">What the Device Mapping Editor is</a>.</p>",
            ["device-mapping-editor-about"]),
        t("device-mapping-editor-qa-find-control", "Common questions", "How do I find which chip is a control?",
            "<p>While editing, press the button or hat on the device: its chip is selected and scrolled into view. Or press <b>Ctrl+F</b> and type the control's name. See <a href=\"topic:device-mapping-editor-select\">Select items and find a control</a>.</p>",
            ["device-mapping-editor-select", "device-mapping-editor-search-layers"]),
        t("device-mapping-editor-qa-other-hand", "Common questions", "How do I lay out the other hand's stick?",
            "<p>Open the other stick, choose <b>Edit Mapping</b>, then <b>Edit › Copy Device Map from Device</b> with <b>Mirror left to right</b> ticked. See <a href=\"topic:device-mapping-editor-copy-from-device\">Copy a device map from another device</a>.</p>",
            ["device-mapping-editor-copy-from-device", "device-mapping-editor-mirror"]),
        t("device-mapping-editor-qa-lost-edits", "Common questions", "The program closed before I saved: are my edits gone?",
            "<p>Not when <b>Keep recovery copies</b> is on in Device Map Options (<b>Recovery copies</b>; on by default): open the device again and choose <b>Restore</b>, then save. See <a href=\"topic:device-mapping-editor-options\">Device Map Options</a>.</p>",
            ["device-mapping-editor-options", "device-mapping-editor-edit"]),
        t("device-mapping-editor-qa-connect", "Common questions", "Why does the Device Mapping Editor say \"Connect\" instead of showing the map?",
            "<p>The stick is unplugged. Plug it in and the map loads by itself. See <a href=\"topic:device-mapping-editor-unplugged\">Unplugged sticks and damaged module files</a>.</p>",
            ["device-mapping-editor-unplugged"]),
        t("device-mapping-editor-qa-export-part", "Common questions", "How do I print only part of the map?",
            "<p>Set a print area: hold <b>Alt</b> and drag around the part you want, then use <b>Print &amp; Export…</b>. See <a href=\"topic:device-mapping-editor-print-area\">Set the print area</a>.</p>",
            ["device-mapping-editor-print-area", "device-mapping-editor-print"])
    ]
}

function t(id, section, title, body, related) {
    return { id: id, section: section, title: title, body: body, related: related || [] }
}
