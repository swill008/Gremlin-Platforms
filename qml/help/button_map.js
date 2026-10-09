// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help, chapter "Button Map" (01 S128, D-01-ONE-HELP).
// Written to claude/help-style.md; on-screen labels in bold, exactly as shown.

.pragma library

var chapter = { id: "button-map", title: "Button Map" }

function topics() {
    return [
        // ---- Getting started ------------------------------------------------
        t("button-map-about", "Getting started", "What Button Map is",
            "<p>Button Map is a picture of one device with a chip on each control. While the profile runs, a press lights its chip, and the chip shows where the control's wire goes (shown as <b>(not claimed)</b> when the output is not claimed). Chips can also show what each control does in the profile.</p>"
            + "<ul>"
            + "<li>The line from a chip to its control on the photo is its <b>leader</b>; the dot on the control is its <b>hotspot</b>.</li>"
            + "<li>Chips not yet placed wait in the <b>pool</b>.</li>"
            + "<li>Chips are layout only: moving, renaming or deleting one never changes the actions in the profile.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>In the Button Map, <b>Help</b> or <b>F1</b> opens this chapter of Help. <b>View Full Help</b> shows the whole book.</li>"
            + "</ul>",
            ["button-map-open", "button-map-edit", "button-map-action-labels"]),
        t("button-map-open", "Getting started", "Open the Button Map",
            "<p>The Button Map opens in its own window, on one device.</p>"
            + "<ol>"
            + "<li>Open it from a device card's right-click menu, the toolbar, or <b>Tools › Mapping › Button Map</b>.</li>"
            + "<li>To show another device, choose it from <b>File › Device</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Before you edit, the map is live: rest the pointer on a chip to see which control it is, and drag with the left or middle button to pan.</li>"
            + "<li>The menus show only what you can use right now, with shortcuts beside their commands. <b>View › Command Palette</b> (<b>Ctrl+K</b>) lists every menu command you can use now: type part of a name and press <b>Enter</b>.</li>"
            + "</ul>",
            ["button-map-edit", "button-map-menus"]),
        t("button-map-edit", "Getting started", "Edit and save a Button Map",
            "<p>Editing places chips on the photo and draws on the map. Nothing is written until you save.</p>"
            + "<ol>"
            + "<li>Choose <b>File › Edit Mapping</b>.</li>"
            + "<li>Drag chips from the pool beside the map onto the photo. Type in the pool's filter to find a control by name.</li>"
            + "<li>Choose <b>File › Save</b> (<b>Ctrl+S</b>) to write the layout to the device's module file, or <b>File › Cancel</b> to leave without saving.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Closing with unsaved edits asks first.</li>"
            + "<li>Most of this chapter is about editing.</li>"
            + "<li>What Save writes, and what is kept at once, is listed in <a href=\"topic:button-map-options\">Button Map Options</a>.</li>"
            + "</ul>",
            ["button-map-chips", "button-map-keys", "button-map-options"]),
        t("button-map-tool-rows", "Getting started", "Arrange the tool rows",
            "<p>Four <b>tool rows</b> frame the map and hold the tools as tabs: one under the menus, one under the map, and one down each side between them (their tabs read up the left one and down the right one).</p>"
            + "<ul>"
            + "<li>The tabs are Chips, Properties, Layers, Command Palette, Print Area, and Options on the top row. A tab opens its tool and hides it again.</li>"
            + "<li>An open tool's panel is joined to its tab, opening from where the tab sits (under a top-row tab, over a bottom-row one, beside a side-row one), and moves with it. The panel opened or selected last is in front.</li>"
            + "<li>The Chips pool runs the length of the map along its row (as wide as the map, or as tall from a side row). Print Area has no panel; its tab lights up while the frame shows.</li>"
            + "<li><b>Pin</b> keeps the tool open when you select the map; unpinned, it hides. <b>Lock</b> stops it being moved or resized.</li>"
            + "<li>Unlocked, drag a tab anywhere along its row or onto another row (the row it would land on lights up). It snaps to the edges, the middle and a small grid, and its panel goes with it.</li>"
            + "<li>Unlocked, a panel's edge facing the map, its far edge along the row and their corner resize it. The Options panel starts as large as its settings need.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li><b>View › Reset Tool Rows</b> puts every tab back on the row it starts on (Options on the top one, the rest on the bottom), docks every panel, and gives every panel its first size.</li>"
            + "<li>All of this is kept for next time.</li>"
            + "</ul>",
            ["button-map-float", "button-map-options"]),
        t("button-map-float", "Getting started", "Float a tool panel",
            "<p>Any tool with a panel can float over the map where you put it.</p>"
            + "<ol>"
            + "<li>Drag its tab off every row onto the map, or right-click the tab and choose <b>Float</b>.</li>"
            + "<li>Unlocked, drag the title bar to move it, and any edge or corner to resize it.</li>"
            + "<li>To dock it again, drop the title bar on a tool row, double-click the title bar, or right-click its tab and choose <b>Dock</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A floating panel has a title bar with its name, pin, lock and close. Its tab stays on its row, with a small floating mark, and shows or hides it.</li>"
            + "<li>Closing it hides it; it floats in the same place next time.</li>"
            + "<li>Print Area has no panel and never floats; the Command Palette floats where it was let go.</li>"
            + "</ul>",
            ["button-map-tool-rows"]),
        t("button-map-menus", "Getting started", "Button Map menus",
            "<p>The Button Map's menus show only what you can use at that moment. Before a device is chosen, <b>File › Device</b> lists the devices; the editing items appear once you choose <b>File › Edit Mapping</b>. The Photo menu works while editing.</p>"
            + "<ul>"
            + "<li><b>File</b>: <b>Edit Mapping</b>, <b>Save</b> (<b>Ctrl+S</b>), <b>Cancel</b>, <b>Reset Layout</b>, <b>Fit to Photo Frame</b>, <b>Print &amp; Export…</b> (<b>Ctrl+P</b>), <b>Close</b>. The last row shows the device's module file.</li>"
            + "<li><b>Edit</b>: Undo, Redo, <b>Copy Button Map from Device</b>, <b>Mirror Layout</b>, <b>Set Print Area</b>, <b>Clear Print Area</b>, <b>Paste Picture</b>, the templates, and <b>Button Map Options…</b>.</li>"
            + "<li><b>View</b>: zoom, <b>Grid</b>, <b>Rulers</b>, guides, <b>Layers</b>, <b>Properties</b>, <b>Print Area</b>, <b>Chip Text</b>, <b>Labels Mode</b>, <b>Command Palette</b> and <b>Reset Tool Rows</b>.</li>"
            + "<li><b>Photo</b>: <b>Choose Photo…</b>, <b>Clear Photo</b>, <b>Move Photo</b>, <b>Adjust Photo…</b>, <b>Reset Photo</b>.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li><b>Reset Layout</b> clears everything from the map: chips go back to the pool, and leaders, hotspots, drawings, text boxes, pictures and tables are removed. It asks first, and actions are not changed. <b>Ctrl+Z</b> brings the layout back; save afterwards to make the empty map the live one.</li>"
            + "<li><b>Fit to Photo Frame</b> shrinks an older, oversized layout to the photo.</li>"
            + "</ul>",
            ["button-map-keys", "button-map-print", "button-map-photo"]),
        t("button-map-options", "Getting started", "Button Map Options",
            "<p><b>Button Map Options</b> holds the Button Map's own settings; they are not in the program's main Options. They apply to every device.</p>"
            + "<p>Open it with <b>Options</b> on the top tool row, or <b>Edit › Button Map Options…</b>. The groups are down its left; the chosen group's settings sit on the right, one line each, with each setting's description on its ⓘ. Changes apply and are kept at once, and the pane opens on the group you used last. Like every tool it can be pinned, locked, moved with its tab, or resized by its edges.</p>"
            + "<ul>"
            + "<li><b>Labels</b>: <b>Chip text</b>, <b>Description first</b>, <b>Several actions</b> and <b>No actions</b>. See <a href=\"topic:button-map-action-labels\">Show actions on chips</a>.</li>"
            + "<li><b>Editing</b>: <b>Mirror pictures</b>, whether Mirror Layout and Copy Button Map from Device also flip pictures (off: pictures only move, so text in them still reads); <b>Undo steps</b>, how far Undo can go back; <b>Rotate snap</b>, the degrees per step when Shift is held while turning an item or drawing a line; <b>Press to find</b> and <b>Find axes</b>.</li>"
            + "<li><b>Autosave</b>: keeps a recovery copy of unsaved edits every <b>Seconds between recovery copies</b> while you edit. If the program closes before you save, opening the device again offers <b>Restore</b> (the edits open for editing; save to keep them), <b>Discard</b>, or <b>Not now</b>. Save and Discard remove the copy.</li>"
            + "<li><b>View</b>: <b>Zoom speed</b>, how fast the mouse wheel zooms; <b>Rulers</b>, shown or not (also <b>View › Rulers</b>).</li>"
            + "<li><b>Colors</b>: <b>Recent colors</b>, how many the color picker keeps.</li>"
            + "<li><b>Library</b>: the saved styles and layout templates, to rename or delete.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>While editing, the map, the photo, the print area, the print settings and the guides are written to the module file only by Save; Cancel takes them back.</li>"
            + "<li>The view (zoom and pan), the grid settings and Show Guides are kept with the device's map at once, also while editing, and Cancel leaves them. Outside editing, Print &amp; Export's settings are kept at once. Rulers is a setting of the program, kept at once.</li>"
            + "</ul>",
            ["button-map-edit", "button-map-styles"]),

        // ---- The map -------------------------------------------------------
        t("button-map-view", "The map", "Zoom, pan and use the grid",
            "<p>Zoom and pan to work on part of the map; the grid helps line items up.</p>"
            + "<ul>"
            + "<li>Scroll to zoom (50% to 600%); the <b>Zoom speed</b> setting in Button Map Options sets how fast. Drag with the middle button to pan.</li>"
            + "<li><b>View › Reset View (View 100%)</b> or <b>Ctrl+0</b> returns to 100%. <b>View › Zoom to Fit Page</b> (<b>Ctrl+1</b>) shows the whole page; <b>View › Zoom to Selection</b> (<b>Ctrl+2</b>) fills the view with what is selected.</li>"
            + "<li><b>View › Grid</b>: <b>Show Grid</b>, <b>Snap to Grid</b>, <b>Snap to Entities</b> (edges and middles of other items, with guide lines), and the grid <b>Size</b>. Hold <b>Alt</b> while dragging to skip snapping.</li>"
            + "<li><b>View › Layers</b> and <b>View › Properties</b> show the two side panels.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The view and the grid settings are kept with the device's map at once, while editing too; Cancel leaves them, and History doesn't list them.</li>"
            + "</ul>",
            ["button-map-rulers", "button-map-layers", "button-map-properties"]),
        t("button-map-rulers", "The map", "Use rulers and guides",
            "<p>Guides are lines you place to line items up.</p>"
            + "<ol>"
            + "<li>Choose <b>View › Rulers</b> to show rulers along the top and left of the map while editing, marked in percent of the page.</li>"
            + "<li>Drag down out of the top ruler for a horizontal guide, or right out of the left ruler for a vertical one.</li>"
            + "<li>Drag a guide to move it; drop it on its ruler or off the page to remove it.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Items you move snap their edges or middles to a guide before anything else, and points (drawing, hotspots, line ends) snap to guides too; <b>Alt</b> skips snapping.</li>"
            + "<li>Guides are kept with the device's map. Guides added, moved or removed while editing wait for Save: Undo steps through them and Cancel takes them back.</li>"
            + "<li><b>View › Show Guides</b> hides and shows them, and <b>View › Clear Guides</b> removes them all. They never print or export.</li>"
            + "</ul>",
            ["button-map-view"]),
        t("button-map-photo", "The map", "Change the photo",
            "<p>The photo is the device picture under everything else.</p>"
            + "<ul>"
            + "<li><b>Photo › Choose Photo…</b> uses another picture; <b>Photo › Clear Photo</b> removes the photo.</li>"
            + "<li><b>Photo › Move Photo</b> drags it (<b>Esc</b> leaves the tool); <b>Adjust Photo…</b> sets its size, offset and rotation; <b>Reset Photo</b> puts it back.</li>"
            + "<li><b>Adjust Photo…</b> also sets its <b>Look</b>, so the chips stand out against a busy picture: <b>Brightness</b> and <b>Contrast</b> (either way), <b>Greyscale</b> and <b>Fade</b>. <b>Reset Look</b> puts them back; Reset Photo leaves the look alone.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Choose Photo and Clear Photo are steps for Undo, and Cancel puts back the photo you started with.</li>"
            + "<li>The look is saved with the layout, shows on the live map and in exports, and Undo steps through it.</li>"
            + "<li>The photo has its own row at the bottom of the Layers panel, so it can be hidden or locked like any item.</li>"
            + "</ul>",
            ["button-map-layers", "button-map-pictures"]),
        t("button-map-select", "The map", "Select items and find a control",
            "<p>Select items to move, style or delete them.</p>"
            + "<ul>"
            + "<li>Select an item to select it; Shift-click or Ctrl-click adds or removes; drag on empty space for a box selection.</li>"
            + "<li>Arrow keys nudge the selection; Shift+Arrow nudges by the grid size.</li>"
            + "<li><b>Press to find</b>: while editing, press a button or hat on the device and its chip is selected and scrolled into view (a group member selects its group). A control not on the map yet is shown in the pool, filtered by name; a hidden one is pointed to the Layers panel. Turn it off, or let a pushed axis count too (<b>Find axes</b>), in Button Map Options.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Undo and Redo are also at the top of every right-click menu.</li>"
            + "</ul>",
            ["button-map-keys", "button-map-layers"]),
        t("button-map-keys", "The map", "Button Map keys",
            "<p>Keys that work while you edit the Button Map:</p>"
            + "<ul>"
            + "<li><b>Ctrl+S</b> Save</li>"
            + "<li><b>Ctrl+Z</b> Undo; <b>Ctrl+Y</b> or <b>Ctrl+Shift+Z</b> Redo</li>"
            + "<li><b>Ctrl+D</b> Duplicate; <b>Ctrl+C</b> Copy; <b>Ctrl+V</b> Paste (a picture copied after the last chip copy pastes as a picture); <b>Ctrl+Shift+V</b> Paste picture</li>"
            + "<li><b>Ctrl+G</b> Group; <b>Ctrl+Shift+G</b> Break group</li>"
            + "<li><b>Ctrl+L</b> Lock or unlock the selection; <b>Ctrl+Shift+L</b> Unlock everything</li>"
            + "<li><b>Delete</b> or <b>Backspace</b> Remove the selection</li>"
            + "<li><b>Ctrl+1</b> Zoom to fit page; <b>Ctrl+2</b> Zoom to selection; <b>Ctrl+0</b> Reset view to 100%</li>"
            + "<li><b>Ctrl+P</b> Print &amp; Export</li>"
            + "<li><b>Alt</b> while dragging: no snapping; <b>Shift</b> while drawing: keep proportions or 15° steps</li>"
            + "<li><b>Esc</b> Cancel the tool, crop, rename or group edit</li>"
            + "<li><b>Ctrl+K</b> Command palette</li>"
            + "<li><b>Ctrl+F</b> Search layers (opens Layers)</li>"
            + "<li><b>F1</b> Help, on this chapter</li>"
            + "</ul>",
            ["button-map-select", "button-map-context-menu"]),

        // ---- Chips ---------------------------------------------------------
        t("button-map-chips", "Chips", "Place and style chips",
            "<p>A chip shows a control's name (Button 10, Axis 1, Hat 1) or its friendly name.</p>"
            + "<ol>"
            + "<li>Drag a chip from the pool onto the photo; drag it again to move it.</li>"
            + "<li>Double-click a chip to edit its name.</li>"
            + "<li>Right-click it to style it.</li>"
            + "</ol>"
            + "<p>A chip's right-click menu has:</p>"
            + "<ul>"
            + "<li><b>Rename</b> and <b>Delete Chip</b> (back to the pool; <b>Delete</b> or <b>Backspace</b> does the same).</li>"
            + "<li><b>Chip Style</b>: font size, chip size, <b>Round</b>, <b>Square</b> or <b>Circle</b>, Filled or Hollow, and <b>Highlight on press</b>. A <b>Circle</b> is always a true circle: it grows to fit its label (<b>Circle Size</b> › <b>Auto</b>), or keeps a size you choose and makes the text smaller to fit.</li>"
            + "<li><b>Colors</b>: Fill Color…, Outline Color… and Text Color…, and <b>Pressed Fill…</b>, <b>Pressed Outline…</b> and <b>Pressed Text…</b> used while the control is held.</li>"
            + "<li><b>Hotspot</b> and <b>Leader Ends</b> (see <a href=\"topic:button-map-hotspots\">Hotspots and leaders</a>), and <b>Arrange</b> (stacking, Lock, Hide).</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>To take chips off the map, drag them back onto the pool: the pool lights up, and letting go removes them. With several chips selected, they all go; a group goes whole, and while a group is being edited the member you drag leaves it. Locked chips stay. Undo brings them back.</li>"
            + "<li>Tick <b>Chip only</b> beside the pool filter (also in Button Map Options) to place chips on their own, with no leader and no hotspot. Add them later from the chip's menu (<b>Leader</b> › <b>Add Leader</b>, <b>Hotspot</b> › <b>Hide Hotspot</b>).</li>"
            + "<li><b>Ctrl+D</b> duplicates the selection; <b>Ctrl+C</b> and <b>Ctrl+V</b> copy and paste it inside the editor.</li>"
            + "</ul>",
            ["button-map-hotspots", "button-map-groups", "button-map-styles"]),
        t("button-map-action-labels", "Chips", "Show actions on chips",
            "<p>Chips can show what each control does in the profile instead of its name, so the map reads as a binding sheet: <b>Gear up</b> or <b>Ctrl+G</b> beside the button, not Button 23.</p>"
            + "<ol>"
            + "<li>Choose <b>View › Chip Text</b> and pick <b>Name</b>, <b>Action</b>, or <b>Name and action</b> (also in Button Map Options › Labels).</li>"
            + "<li>Choose <b>View › Labels Mode</b> and pick the mode whose actions to show, or <b>Follow the Program</b>: the running mode while the profile runs, otherwise the mode chosen in the program.</li>"
            + "</ol>"
            + "<p>What each action shows:</p>"
            + "<ul>"
            + "<li><b>Description</b>: its text. With Button Map Options › Labels › <b>Description first</b> on (the default), it stands for the whole binding.</li>"
            + "<li><b>Map to Keyboard</b>: the keys, such as Ctrl+G. <b>Map to vJoy</b> and <b>Map to Xbox</b>: the output, such as vJoy 1 B5. <b>Change Mode</b>: → and the target mode, or Cycle, Previous mode, Unwind mode. <b>Text to Speech</b>: what it says. Mouse, Macro, Load profile, Run command, Sound, Pause / resume and Logical Device show those words.</li>"
            + "<li>Actions inside Chain, Tempo, Double Tap, Condition and the like give their text; response curves and deadzones give none.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li><b>Several actions</b> shows the first one's text, or all of them joined with +. <b>No actions</b> sets what a chip shows when its control does nothing in that mode: its name, nothing, or a dash.</li>"
            + "<li>A control with no actions in a mode shows its parent mode's, as the running profile does.</li>"
            + "<li>Labels follow the profile as you edit it. Renaming a chip still edits its name.</li>"
            + "</ul>",
            ["button-map-chips", "button-map-options"]),
        t("button-map-hotspots", "Chips", "Hotspots and leaders",
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
            ["button-map-chips", "button-map-layers"]),
        t("button-map-groups", "Chips", "Group chips",
            "<p>A group moves as one, keeping its chips where you put them.</p>"
            + "<ol>"
            + "<li>Line the chips up first with <b>Align</b>, the arrow keys or by dragging.</li>"
            + "<li>Select two or more chips (Shift-click, or drag a box on empty space).</li>"
            + "<li>Choose <b>Group Selected</b> (<b>Ctrl+G</b>).</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Break Group</b> (<b>Ctrl+Shift+G</b>) splits it. <b>Edit Group</b> lets you move and style one member; <b>Done Editing Group</b> or <b>Esc</b> ends that.</li>"
            + "<li><b>Align Members</b> arranges a group Left, Center, Right or Free (Free keeps your own arrangement; new groups start as Free).</li>"
            + "<li>To turn a group, select it and drag the round handle above it, or right-click and choose <b>Turn group</b>. Its chips swing round the group's middle and stay upright so they still read; the hotspot stays on the photo.</li>"
            + "<li>Right-click a five-chip hat group: <b>Style</b> › <b>Format</b> shows it as <b>Plus</b>, <b>Mini hat</b> or <b>Radial</b>; <b>Clear Format</b> removes it.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Grouping chips or text boxes together with a table packs them into the table. See <a href=\"topic:button-map-tables\">Add a table</a>.</li>"
            + "</ul>",
            ["button-map-align", "button-map-tables"]),
        t("button-map-mirror", "Chips", "Mirror the layout",
            "<p><b>Edit › Mirror Layout</b> turns the whole map left to right while editing.</p>"
            + "<ul>"
            + "<li>Every chip, group, drawing and picture goes to the other side of the page, with its hotspot, leader bends and loose leader ends.</li>"
            + "<li>Shapes and lines are mirrored, so an arrow points the other way; text boxes, tables and the arrangement inside a group stay as they are, so they still read.</li>"
            + "<li>Pictures move but are only flipped when Button Map Options › Editing › <b>Mirror pictures</b> is on.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>One Undo puts it back.</li>"
            + "<li>To lay out a left-hand stick from a right-hand one, see <a href=\"topic:button-map-copy-from-device\">Copy a Button Map from another device</a>.</li>"
            + "</ul>",
            ["button-map-copy-from-device"]),
        t("button-map-copy-from-device", "Chips", "Copy a Button Map from another device",
            "<p>Start a map from another device's layout.</p>"
            + "<ol>"
            + "<li>While editing, choose <b>Edit › Copy Button Map from Device</b>. It lists the other devices that have a Button Map.</li>"
            + "<li>Pick one. Tick <b>Mirror left to right</b> for the other hand's stick.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>It replaces this map's chips, leaders and drawings. This device's photo stays.</li>"
            + "<li>One Undo puts the old layout back, mirrored or not, and nothing is saved until you save.</li>"
            + "</ul>",
            ["button-map-mirror", "button-map-templates"]),
        t("button-map-templates", "Chips", "Use layout templates",
            "<p>A template keeps a map's chips, leaders and drawings under a name, to put on any device.</p>"
            + "<ul>"
            + "<li><b>Save Layout as Template…</b> keeps this map's layout under a name.</li>"
            + "<li><b>Apply Template</b> puts one on the device you are editing. It asks first; Undo puts the old layout back.</li>"
            + "<li><b>Manage Templates…</b> renames, deletes, exports a template to a file to share, and imports one.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A template keeps where its pictures are, not the picture files themselves.</li>"
            + "<li>Button Map Options › <b>Library</b> also renames and deletes templates.</li>"
            + "</ul>",
            ["button-map-copy-from-device", "button-map-styles"]),

        // ---- Drawing -------------------------------------------------------
        t("button-map-context-menu", "Drawing", "Right-click menu",
            "<p>While editing, the right-click menu shows only what applies to what you right-clicked: a chip, a group, a leader, a shape, a line, a picture, a text box, a table, several selected items, or empty canvas.</p>"
            + "<ul>"
            + "<li>It opens small: the item's name with <b>Undo</b> and <b>Redo</b>, a few actions, then sections such as Chip style or Arrowheads.</li>"
            + "<li>Select a section to open it; one is open at a time, and the menu reopens on the section you used last for that kind of item.</li>"
            + "<li>Rows of values (sizes, widths, opacity) change straight away and leave the menu open; other actions close it.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Keys: <b>Up</b> and <b>Down</b> move, <b>Enter</b> acts, <b>Right</b> and <b>Left</b> open or close a section or step a row of values, <b>Esc</b> closes.</li>"
            + "<li>Near a window edge the menu opens the other way, and it scrolls when it is taller than the window.</li>"
            + "</ul>",
            ["button-map-keys"]),
        t("button-map-shapes", "Drawing", "Draw shapes",
            "<p>Shapes mark areas of the photo or frame groups of chips.</p>"
            + "<ol>"
            + "<li>Right-click empty canvas, choose <b>Draw</b>, and pick a <b>Shape</b>: Rectangle, Rounded, Ellipse, Triangle, Diamond, Arrow or Double arrow.</li>"
            + "<li>Drag on the photo to draw it; hold <b>Shift</b> to keep its proportions.</li>"
            + "<li>The tool stays on for the next one until <b>Stop Drawing</b> or <b>Esc</b>.</li>"
            + "</ol>"
            + "<p>Right-click a shape for <b>Duplicate</b> and <b>Delete</b>, then sections: <b>Shape</b> (change the kind), <b>Fill and Outline</b> (Filled or Hollow, Fill Color…, Outline Color…, Width, outline Solid, Dashed or Dotted, Opacity), <b>Rotate and Flip</b> and <b>Arrange</b>.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>With chips selected, <b>Shape Around Selection</b> draws a shape around them that moves with them; its <b>Padding</b> sets the gap, and Arrange › <b>Detach from Chips</b> frees it.</li>"
            + "</ul>",
            ["button-map-transform", "button-map-rotate", "button-map-lines"]),
        t("button-map-lines", "Drawing", "Draw lines and arrows",
            "<p>Lines and arrows point at parts of the photo.</p>"
            + "<ol>"
            + "<li>Right-click empty canvas, choose <b>Draw</b> › <b>Line</b>, and pick <b>Line</b> or <b>Arrow</b>.</li>"
            + "<li>Drag from one end to the other; hold <b>Shift</b> to keep to 15° steps.</li>"
            + "</ol>"
            + "<ul>"
            + "<li>A selected line has a handle on each end; drag one to move that end (<b>Shift</b> for 15° steps). To turn a line, move its ends.</li>"
            + "<li>Its <b>Arrowheads</b> section sets the <b>Start</b> and <b>End</b> to None, Solid or Hollow; <b>Swap Heads</b> turns them round.</li>"
            + "<li>Its <b>Line</b> section has Color…, Width, Outline (Solid, Dashed or Dotted) and Opacity, and <b>Flip</b> mirrors it.</li>"
            + "</ul>",
            ["button-map-paths", "button-map-shapes"]),
        t("button-map-paths", "Drawing", "Draw paths and freehand",
            "<p>A path goes through several points; freehand follows the pointer.</p>"
            + "<ol>"
            + "<li>Choose <b>Draw</b> › <b>Line</b> › <b>Path</b>.</li>"
            + "<li>Click each point. Click the first point again to close the shape, or double-click, press <b>Enter</b> or right-click to finish an open path. <b>Shift</b> keeps each segment to angle steps.</li>"
            + "<li>The tool stays on for the next path; <b>Esc</b> stops it.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Draw</b> › <b>Line</b> › <b>Freehand</b> draws while the button is held down. When you let go, the stroke is tidied (fewer points, same shape) and smoothed.</li>"
            + "<li>A selected path shows a small round handle on each point: drag one to move it. Its box's handles resize the whole path, and it turns and flips like a shape.</li>"
            + "<li>Right-click a path: <b>Path</b> › <b>Closed</b> and <b>Smooth</b>; <b>Line</b> › color, width, Solid, Dashed or Dotted, opacity; an open path has <b>Arrowheads</b> at its start and end, a closed one a <b>Fill</b> (Filled or Hollow, Fill color…).</li>"
            + "</ul>",
            ["button-map-lines", "button-map-transform"]),
        t("button-map-rotate", "Drawing", "Rotate, flip and resize items",
            "<p>Shapes, text boxes and pictures can be turned, flipped and resized.</p>"
            + "<ul>"
            + "<li>A selected item has a round handle above it: drag it to turn the item to any angle, with <b>Shift</b> for steps (15° unless Button Map Options › Editing › <b>Rotate snap</b> says otherwise).</li>"
            + "<li>The <b>Rotate and Flip</b> section has an <b>Angle</b> to type, <b>Turn to</b> 0°, 90°, 180° or 270°, <b>Rotate −15°</b> and <b>Rotate +15°</b>, and <b>Flip Horizontally</b> and <b>Flip Vertically</b>. Properties takes an exact Angle.</li>"
            + "<li>Drag the square handles to resize. A turned item resizes along its own sides, and the opposite side stays where it is. From a corner, a shape keeps its proportions when <b>Shift</b> is held; a picture keeps them unless <b>Shift</b> is held.</li>"
            + "</ul>"
            + "<p>To turn several items together:</p>"
            + "<ol>"
            + "<li>Select two or more items. A dashed box goes round them with one round handle above it.</li>"
            + "<li>Drag the handle to turn them all about their middle (the angle shows beside the handle), or use the right-click menu's <b>Turn together</b> to turn them by a step, a quarter turn or a half turn.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Turning together: shapes, text boxes and pictures turn, lines swing round with both ends, and chips, groups and tables move round but stay upright so they still read. Hotspots stay on the photo; locked items stay put. Turning there and back puts them where they were.</li>"
            + "<li>Lines turn by moving their ends. Tables, chips and hotspots do not turn on their own.</li>"
            + "</ul>",
            ["button-map-transform", "button-map-groups"]),
        t("button-map-transform", "Drawing", "Reshape, bend and skew items",
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
            + "<li><b>Skew</b>: a diamond on the top edge leans the item sideways, one on the right edge leans it up or down.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li><b>Edit Points</b> turns a shape into a path with a handle on every corner, looking as it does now (shaped, bent, skewed, turned), so any corner can be moved; it is then a path, not an arrow.</li>"
            + "<li><b>Reset Shape</b> takes away the shaping, bend and skew. Undo steps back through all of it.</li>"
            + "<li>The choice goes back to Resize when you select something else.</li>"
            + "</ul>",
            ["button-map-shapes", "button-map-rotate"]),
        t("button-map-text-boxes", "Drawing", "Add a text box",
            "<p>Text boxes add notes and titles to the map.</p>"
            + "<ol>"
            + "<li>Choose <b>Draw</b> › <b>Box</b> › <b>Text box</b>, then drag.</li>"
            + "<li>Double-click the text box (or choose <b>Edit Text…</b>) and type.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Text</b>: Font size, Bold, Word wrap, <b>Scale font with box</b>, and alignment Across (Left, Center, Right) and Down (Top, Middle, Bottom).</li>"
            + "<li><b>Box</b>: preset Size (Caption, Small, Medium, Large, Title, Wide), Theme (Dark, Hollow, Sheet), Text Color…, Fill Color…, Outline Color…, Fill opacity and Outline opacity.</li>"
            + "<li><b>Copy and Paint Format</b>: <b>Copy Format</b> takes this box's look; <b>Paint format</b> puts it on the next boxes you select; <b>Clear Formatting</b> resets it; <b>Copy Text</b> copies the words.</li>"
            + "</ul>",
            ["button-map-callouts", "button-map-styles"]),
        t("button-map-callouts", "Drawing", "Add a callout",
            "<p>A callout is a text box with a pointer.</p>"
            + "<ol>"
            + "<li>Choose <b>Draw</b> › <b>Box</b> › <b>Callout</b> and drag the box, or right-click a chip and choose <b>Add Callout</b> for one beside the chip, pointing at it and showing its text.</li>"
            + "<li>Select the callout to see the round handle at the pointer's tip. Drag it anywhere to point at a spot on the photo, or drop it on a chip so the pointer follows that chip when it moves (the handle is filled while it does).</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Everything a text box does, a callout does too: typing, fonts, themes, colors, paint format, turning.</li>"
            + "<li>The pointer leaves the side of the box facing its tip.</li>"
            + "<li>The text box's <b>Pointer</b> section: <b>Detach from Chip</b> keeps the pointer where it is without following, <b>Remove Pointer</b> makes it a plain text box, and on a plain text box <b>Add Pointer</b> makes it a callout.</li>"
            + "</ul>",
            ["button-map-text-boxes"]),
        t("button-map-tables", "Drawing", "Add a table",
            "<p>Tables list controls and their uses beside the photo.</p>"
            + "<ol>"
            + "<li>Choose <b>Draw</b> › <b>Box</b> › <b>Table</b>, then drag.</li>"
            + "<li>Double-click a cell to type in it.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Rows and Columns</b>: Insert Row Above, Delete This Row, Insert Column Left, Delete This Column, and an <b>ID column</b>.</li>"
            + "<li><b>Cell</b>: <b>Free position</b> lets a cell be dragged out of the grid; <b>Independent of table</b> keeps it still when the table moves; <b>Spawn Empty Cell</b> adds a loose cell; <b>Delete This Cell</b>; <b>Place Across</b> and <b>Place Down</b> park a cell at a side.</li>"
            + "<li><b>Look</b>: Theme (Dark, Hollow, Sheet) and font size.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Select a table with chips or text boxes on it and choose <b>Group Selected</b>: they are packed into the table and move with it. <b>Break Group</b> takes them out again; <b>Delete Table</b> removes it.</li>"
            + "</ul>",
            ["button-map-groups", "button-map-text-boxes"]),
        t("button-map-pictures", "Drawing", "Add pictures",
            "<p>Pictures sit on top of the photo, for logos, icons or close-ups.</p>"
            + "<ul>"
            + "<li><b>Draw</b> › <b>Import Picture…</b> adds a picture file.</li>"
            + "<li><b>Edit › Paste Picture</b> (<b>Ctrl+Shift+V</b>), or <b>Paste Picture</b> in the canvas's Draw section, adds the picture on the clipboard: a copied picture, or picture files copied in File Explorer. <b>Ctrl+V</b> pastes a picture too when it was copied after your last chip copy.</li>"
            + "<li>Drag picture files from File Explorer onto the map while editing: each lands where you drop it, at its own shape.</li>"
            + "</ul>"
            + "<p>A picture moves, resizes, turns and flips like a shape. Its <b>Picture</b> section has:</p>"
            + "<ul>"
            + "<li><b>Crop</b>: the handles turn blue and cut the picture instead of scaling it; what stays does not move. <b>Esc</b> or selecting something else ends it. <b>Reset Crop</b> shows the whole picture again; Properties takes exact crop values.</li>"
            + "<li><b>Add snap point</b> (then select a spot on the picture) and <b>Clear Snap Points</b>: chips snap to these points.</li>"
            + "<li>Opacity.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Pictures are saved beside the device's module file.</li>"
            + "</ul>",
            ["button-map-rotate", "button-map-photo"]),
        t("button-map-styles", "Drawing", "Save and apply styles",
            "<p>A look you use often can be kept under a name and put on other items.</p>"
            + "<ol>"
            + "<li>Right-click a chip, shape, line, path or text box and choose <b>Saved Styles</b> › <b>Save This Style…</b>.</li>"
            + "<li>Give it a name, such as Weapons, red. A style of the same name and kind is replaced.</li>"
            + "<li>To use it, select items of that kind, open the same section and choose <b>Apply</b> beside the style. It is one step for Undo.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A chip's style holds its chip, text, pressed, hotspot and leader colors and sizes; a shape's its fill and outline; a line's its color, width, outline and arrowheads; a text box's its format.</li>"
            + "<li>Styles are shared by every device. <b>Edit › Button Map Options…</b> › <b>Library</b> renames and deletes them, and the layout templates too.</li>"
            + "</ul>",
            ["button-map-templates", "button-map-options"]),

        // ---- Panels --------------------------------------------------------
        t("button-map-layers", "Panels", "Layers panel",
            "<p><b>View › Layers</b> shows every item while editing, top of the stack first, then the photo.</p>"
            + "<ul>"
            + "<li>The <b>eye</b> hides an item: it is not drawn, on the live map either, and is left out of exports.</li>"
            + "<li>The <b>lock</b> keeps an item in place: clicks pass through it, and it is not moved, nudged or deleted. <b>Ctrl+L</b> locks or unlocks the selection; <b>Ctrl+Shift+L</b> unlocks everything.</li>"
            + "<li>Open a chip (the arrow) to hide or lock its hotspot or each leader on its own. Locking or hiding the chip covers them all.</li>"
            + "<li>Drag a row up or down to change what is on top. The right-click menu's <b>Arrange</b> section does the same a step at a time: Bring to Front, Bring Forward, Send Back, Send to Back.</li>"
            + "<li>Select a row to select the item (Ctrl or Shift to add); a right-click selects it too before its menu opens (a row in a selection keeps the selection). Double-click a drawing's row to name it.</li>"
            + "<li><b>Show all</b> and <b>Unlock all</b> undo every hide and lock.</li>"
            + "</ul>",
            ["button-map-search-layers", "button-map-properties"]),
        t("button-map-search-layers", "Panels", "Search and filter layers",
            "<p>Find rows in the Layers panel by name or kind.</p>"
            + "<ol>"
            + "<li>Press <b>Ctrl+F</b> or choose <b>View › Search layers…</b>. Layers opens if it is closed.</li>"
            + "<li>Type in <b>Search layers…</b>, the box under the panel's header.</li>"
            + "<li>Press <b>Enter</b> to select every match on the map and bring the first into view. <b>Esc</b> or the box's <b>×</b> clears it.</li>"
            + "</ol>"
            + "<p>It finds, in any case and anywhere in: the row's name, the control (Button 12, Hat 1, X Axis, even when the chip has a friendly name), what the chip shows (its action or description), and the kind of row.</p>"
            + "<p>Under the box, one toggle per kind of row: <b>All · Chips · Groups · Hotspots · Leaders · Shapes · Lines · Pictures · Text · Tables · Photo</b>. Turn on any number of kinds to show only those; with none on, every row shows and <b>All</b> lights; <b>All</b> turns them all off again. The search looks only in the kinds that are on.</p>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>A matching hotspot, leader or group member shows under its chip or group, which is dimmed when it doesn't match itself.</li>"
            + "<li>While a filter is on, a line says how many rows match (12 of 148) or <b>No layers match</b>. The eye, lock, rename, drag and delete work on the rows shown.</li>"
            + "<li>The kinds and the search stay while the Button Map is open, also when another device's map is shown; they go back to none and empty when the Button Map closes.</li>"
            + "</ul>",
            ["button-map-layers"]),
        t("button-map-properties", "Panels", "Properties panel",
            "<p><b>View › Properties</b> shows the selected item's exact values while editing. Positions and sizes are in percent of the page.</p>"
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
            ["button-map-layers", "button-map-colors"]),
        t("button-map-align", "Panels", "Align and distribute items",
            "<p>Line items up or space them evenly.</p>"
            + "<ol>"
            + "<li>Select several items and right-click one of them.</li>"
            + "<li>In <b>Align and Distribute</b>, line them up <b>Across</b> (Left, Center, Right) or <b>Down</b> (Top, Middle, Bottom) by their edges or middles, or choose <b>Space Out</b> to leave equal gaps between three or more.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>Locked items stay where they are.</li>"
            + "</ul>",
            ["button-map-groups"]),
        t("button-map-colors", "Panels", "Choose colors",
            "<p>The color picker opens from Colors, Fill color…, Outline color… and the Properties swatches.</p>"
            + "<ul>"
            + "<li>Drag in the square and the bar, or select a swatch; the change shows at once.</li>"
            + "<li><b>Recent</b> shows the colors you used last, on any device. Button Map Options › Colors sets how many.</li>"
            + "<li><b>Pick from Map</b> closes the picker; select anywhere in the window to take the color there (right-click or <b>Esc</b> gives up).</li>"
            + "</ul>",
            ["button-map-properties", "button-map-styles"]),

        // ---- Print and export ----------------------------------------------
        t("button-map-print", "Print and export", "Print or export the map",
            "<p><b>File › Print &amp; Export…</b> (<b>Ctrl+P</b>) has every print and export in one place.</p>"
            + "<ol>"
            + "<li>Open <b>Print &amp; Export…</b>. A preview shows the page as it will come out.</li>"
            + "<li>Choose the paper (Letter, Legal, Tabloid, A3, A4, A5), its orientation, the margins and the background. Under <b>Custom</b> are the scale and <b>Freeform (As Drawn)</b>.</li>"
            + "<li>Press <b>Print…</b>, <b>Export PDF…</b>, <b>Export PNG…</b> or <b>Export JPG…</b>.</li>"
            + "</ol>"
            + "<ul>"
            + "<li><b>Scale</b>: the size in pixels of every export and print. 100% is the photo's own size, pixel for pixel (without a photo, the page 1920 pixels wide). The window shows the pixels, and on a paper how many dots an inch they print at: the print area fills the paper inside its margins.</li>"
            + "<li><b>Freeform (As Drawn)</b> sets no paper: the print area keeps whatever shape you draw (Paper, Orientation and Margins grey out), and a PDF gets a page of that shape, at 96 pixels an inch.</li>"
            + "<li><b>Background</b>: <b>Dark</b>, as on screen, or <b>Light</b>, a white page where every color has its lightness turned over, so dark chips come out light with dark text and a dark red becomes a light red, while the photo stays as it is. The screen does not change.</li>"
            + "<li>The preview follows the print area as it moves or is resized on the map, and sharpens a moment after it stops. In the preview, drag the picture to move the print area and turn the mouse wheel to zoom: in makes the print area smaller, out larger, about the pointer, keeping its shape. Not while the print area is locked.</li>"
            + "<li><b>Print…</b> prints the print area as Export draws it, on the chosen paper and margins. Windows' printer dialog comes first. With <b>Freeform (As Drawn)</b> it goes on the paper chosen in the printer dialog, turned to landscape when wider than tall.</li>"
            + "</ul>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>The settings are kept with the map and are the same for every print and export. The size of the window or the screen's scale makes no difference.</li>"
            + "<li>Every print and export takes the print area, whatever the zoom. Selection marks, handles, guides and the grid are left off, and so are hidden items. Lines and text are drawn at the export's size, not enlarged. A PDF goes on the chosen paper, inside its margins.</li>"
            + "<li>While an export is still being written, Print &amp; Export shows <b>Exporting…</b> and the Export buttons wait.</li>"
            + "</ul>",
            ["button-map-print-area"]),
        t("button-map-print-area", "Print and export", "Set the print area",
            "<p>The print area is the part of the page every export and print takes.</p>"
            + "<ol>"
            + "<li>Hold <b>Alt</b> and drag on an empty part of the map, or choose <b>Edit › Set Print Area</b>, then drag.</li>"
            + "<li>Show it with <b>Print Area</b> on a tool row (or <b>View › Print Area</b>) while editing: everything outside is dimmed, with handles to resize it and its border to move it.</li>"
            + "<li>To go back to the whole page, choose <b>Edit › Clear Print Area</b>.</li>"
            + "</ol>"
            + "<h4>Good to know</h4>"
            + "<ul>"
            + "<li>With a paper chosen, it keeps the paper's shape, so what it frames fills the page.</li>"
            + "<li>It never shows on the live map.</li>"
            + "<li>A print area drawn or changed while editing waits for Save: Undo steps through it and Cancel takes it back. It is kept with the map.</li>"
            + "</ul>",
            ["button-map-print"]),

        // ---- Common questions ----------------------------------------------
        t("button-map-qa-actions", "Common questions", "Does moving a chip change my bindings?",
            "<p>No. Chips are layout only: moving, renaming or deleting one never changes the actions in the profile. See <a href=\"topic:button-map-about\">What Button Map is</a>.</p>",
            ["button-map-about"]),
        t("button-map-qa-find-control", "Common questions", "How do I find which chip is a control?",
            "<p>While editing, press the button or hat on the device: its chip is selected and scrolled into view. Or press <b>Ctrl+F</b> and type the control's name. See <a href=\"topic:button-map-select\">Select items and find a control</a>.</p>",
            ["button-map-select", "button-map-search-layers"]),
        t("button-map-qa-other-hand", "Common questions", "How do I lay out the other hand's stick?",
            "<p>Open the other stick, choose <b>Edit Mapping</b>, then <b>Edit › Copy Button Map from Device</b> with <b>Mirror left to right</b> ticked. See <a href=\"topic:button-map-copy-from-device\">Copy a Button Map from another device</a>.</p>",
            ["button-map-copy-from-device", "button-map-mirror"]),
        t("button-map-qa-lost-edits", "Common questions", "The program closed before I saved: are my edits gone?",
            "<p>Not when <b>Autosave</b> is on in Button Map Options: open the device again and choose <b>Restore</b>, then save. See <a href=\"topic:button-map-options\">Button Map Options</a>.</p>",
            ["button-map-options", "button-map-edit"]),
        t("button-map-qa-export-part", "Common questions", "How do I print only part of the map?",
            "<p>Set a print area: hold <b>Alt</b> and drag around the part you want, then use <b>Print &amp; Export…</b>. See <a href=\"topic:button-map-print-area\">Set the print area</a>.</p>",
            ["button-map-print-area", "button-map-print"])
    ]
}

function t(id, section, title, body, related) {
    return { id: id, section: section, title: title, body: body, related: related || [] }
}
