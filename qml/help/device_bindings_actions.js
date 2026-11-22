// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: the Device Bindings page and every action.
// Written to claude/plans/help-style-guide.md: each topic opens with what
// it's for, then "How to", "What you see" and "Good to know" (empty sections
// left out).

.pragma library

var chapter = { id: "device-bindings-actions", title: "Device Bindings and actions" }

function _how(items) {
    return "<h4>How to</h4><ol><li>" + items.join("</li><li>") + "</li></ol>"
}

function _see(items) {
    return "<h4>What you see</h4><ul><li>" + items.join("</li><li>") + "</li></ul>"
}

function _good(items) {
    return "<h4>Good to know</h4><ul><li>" + items.join("</li><li>") + "</li></ul>"
}

function _link(id, title) {
    return "<a href=\"topic:device-bindings-actions-" + id + "\">" + title + "</a>"
}

function topics() {
    var page = "Device Bindings page"
    var actions = "Actions"
    var questions = "Common questions"
    return [
        // ---- Device Bindings page ----
        {
            id: "device-bindings-actions-device-bindings-page",
            section: page,
            title: "The Device Bindings page",
            body: "<p>The Device Bindings page lists one device's inputs and the actions on each. It works like the <a href=\"topic:logical-device-about\">Logical Device</a> page, with the same Find bar, list, menus and action editor.</p>"
                + _how([
                    "Double-click a card on <a href=\"topic:home-devices-home\">Home</a>, or choose <b>View › Device Bindings</b> <a href=\"show:menu/View/Device Bindings\">Show me ›</a>.",
                    "Pick the mode you want to edit in the <b>Mode</b> box on the mode bar <a href=\"show:modebar\">Show me ›</a>.",
                    "Click an input's row to open all its actions in the editor beside the list.",
                    "Click an action's row to open only that action."
                ])
                + _see([
                    "The arrows beside the title step to the previous or next device.",
                    "Each input's row shows its <b>Note</b>. The rows under it show each action and where it sends: a vJoy output, keys, a mode or a file.",
                    "After the input's name, <b>Bindings [2]</b> gives the count in this mode. A box follows for each target, for example [vJoy 1 · Button 1].",
                    "The boxes line up in one column. If they don't all fit, the row ends with \"…\": point at it to see them all.",
                    "A row with nothing bound shows no Bindings count."
                ])
                + _good([
                    "The page lists only the inputs ticked in the device's <b>Module Setup…</b>. You add or remove inputs there, not here.",
                    "With no inputs ticked, the page says so. Right-click the page and choose Module Setup… to tick some.",
                    "<b>OK</b> puts an action in the open profile. It is written to disk when you choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a>.",
                    "Groups, order and custom names are kept in the device's <a href=\"topic:home-devices-module-files\">module file</a>, so every profile shows them. See " + _link("layout", "Group, order and name inputs") + ".",
                    "With <b>Show LED dots</b> and <b>Show live bars</b> on, a pressed input lights its row and the list jumps to it.",
                    "To change what each row shows, see " + _link("appearance-details", "Choose the details on groups and rows") + ".",
                    "The <b>Keyboard</b> card opens its own page. See " + _link("keyboard-page", "Set up keyboard keys") + ".",
                    "A vJoy or Xbox card opens its <b>Output View</b> instead. See " + _link("output-view", "Output View") + "."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-filter", "device-bindings-actions-layout",
                      "device-bindings-actions-menus", "modes-mode-box", "device-bindings-actions-appearance"]
        },
        {
            id: "device-bindings-actions-layout",
            section: page,
            title: "Group, order and name inputs",
            body: "<p>Groups, order and names keep a long list of inputs easy to find. They work as on the <a href=\"topic:logical-device-group-controls\">Logical Device</a> page.</p>"
                + _how([
                    "To rename an input, right-click it and choose <b>Rename</b>. Module Setup shows the same name.",
                    "To remove a custom name, right-click and choose <b>Row › Clear Name</b>. It asks first; the system name stays.",
                    "To group inputs, select them, right-click and open <b>Group</b>. Type a new name in <b>Group as</b>, or pick a group under <b>Move to</b>.",
                    "To add, move or delete groups, use <b>Groups</b> in the right-click menu.",
                    "To move an input, drag it by its handle. Drag a group by its header.",
                    "To sort, right-click, open <b>Order</b> and choose <b>By System Name</b>, <b>By Your Name</b> or <b>Group Names A to Z</b>."
                ])
                + _good([
                    "Deleting a group keeps its inputs. They move to <b>Ungrouped</b>.",
                    "These changes are saved when you save the profile (<b>Ctrl+S</b>). Until then the title shows <b>*</b>.",
                    "<b>Discard</b> in the save-changes box drops them.",
                    "They are kept in the device's module file, so every profile shows the same groups, order and names.",
                    "If the device's inputs or layout change somewhere else before you save, that newer version wins. A note says your unsaved changes for the device were dropped.",
                    "This can happen through History Restore, the Device Library, Export / Import Device or Module Setup.",
                    "Changing only the device's picture or device map keeps your changes.",
                    "<b>Undo</b> takes these changes back too. See " + _link("undo", "Undo a change on the Device Bindings page") + "."
                ]),
            related: ["device-bindings-actions-device-bindings-page", "device-bindings-actions-menus",
                      "device-bindings-actions-undo", "logical-device-group-controls"]
        },
        {
            id: "device-bindings-actions-menus",
            section: page,
            title: "Device Bindings page menus",
            body: "<p>What each right-click menu on the Device Bindings page holds. The Logical Device, Keyboard and OSC pages share the same menus.</p>"
                + "<h4>What you see</h4>"
                + "<table cellpadding=\"3\"><tr><th align=\"left\">Right-click on</th><th align=\"left\">Menu items</th></tr>"
                + "<tr><td>Empty space</td><td><b>Module Setup…</b>, <b>Appearance…</b>, <b>Groups</b> (<b>New Group</b>), <b>Order</b></td></tr>"
                + "<tr><td>An input</td><td><b>Add Action</b>, <b>Rename</b>, <b>History</b>, <b>Row</b> (<b>Clear Name</b>, <b>Delete actions…</b>), <b>Group</b> (<b>Group as</b>, <b>Move to</b>)</td></tr>"
                + "<tr><td>A group header</td><td><b>Rename Group</b>, <b>Groups</b> (<b>Move Group Up</b>, <b>Move Group Down</b>, <b>Delete Group</b>)</td></tr>"
                + "<tr><td>An action row</td><td><b>Open</b>, <b>Delete</b></td></tr>"
                + "</table>"
                + _good([
                    "<b>Undo</b> and <b>Redo</b> are always beside the menu's title.",
                    "<b>Delete actions…</b> asks first. The red <b>Delete Actions</b> removes every action on that input in this mode; the input stays.",
                    "Delete actions… isn't offered for the input open in the editor.",
                    "With several inputs selected, the menu's title counts them. Add Action, Rename and History are left out.",
                    "<b>History</b> opens <a href=\"topic:tools-history\">History</a> showing only that input in this mode."
                ]),
            related: ["device-bindings-actions-layout", "device-bindings-actions-delete-action", "logical-device-menus"]
        },
        {
            id: "device-bindings-actions-filter",
            section: page,
            title: "Filter the inputs",
            body: "<p>The <b>Find</b> bar above the list shows only the inputs you want to see.</p>"
                + _how([
                    "Type a system name, a custom name or a group name. <b>Ctrl+F</b> jumps to the box.",
                    "To show one kind of input, set the type box from <b>All inputs</b> to <b>Buttons</b>, <b>Axes</b> or <b>Hats</b>.",
                    "To clear the typing, choose <b>×</b> or press <b>Esc</b>."
                ])
                + _see([
                    "A line under the box says how many inputs are found.",
                    "The action box <b>Type</b> shows inputs with one kind of action, such as Map to vJoy, Macro or Change Mode.",
                    "The <b>Output</b> box shows inputs that send to one place. It lists only the places in use.",
                    "<b>Ungrouped</b> shows only inputs that aren't in a group.",
                    "<b>No bindings in this mode</b> shows only inputs with nothing bound.",
                    "<b>Binding output not found</b> shows only inputs that send to an output that isn't there. Their action rows show a red <b>⚠</b>: point at it to see why.",
                    "<b>Clear</b> resets every Find filter: the typing, the type box, the ticks and the Type and Output boxes."
                ])
                + _good([
                    "When nothing matches, the page says so. Choose <b>Clear Filters</b>, or Clear on the bar, to show everything again."
                ]),
            related: ["device-bindings-actions-device-bindings-page", "device-bindings-actions-add-action"]
        },
        {
            id: "device-bindings-actions-add-action",
            section: page,
            title: "Add an action to an input",
            body: "<p>An action says what an input does when you use it: press a button, move an axis or push a hat.</p>"
                + _how([
                    "Open the device's Device Bindings page.",
                    "Right-click the input's row and choose <b>Add Action</b>. The action editor opens beside the list.",
                    "Choose the action and set it up.",
                    "Choose <b>OK</b>.",
                    "To keep it on disk, choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> (<b>Ctrl+S</b>)."
                ])
                + _good([
                    "<b>Close pane after OK</b> closes the editor after OK. Drag the editor's left edge to make it wider.",
                    "If the editor has unsaved changes and you open another input or action, a box asks first:<ul>"
                        + "<li><b>Save</b> keeps the changes.</li>"
                        + "<li><b>Discard</b> drops them.</li>"
                        + "<li><b>Cancel</b> stays on the input you were editing.</li></ul>",
                    "Leaving the page asks the same.",
                    "If you switch modes while the editor is open, the editor stays on its mode. OK saves to that mode.",
                    "If that mode is deleted, the editor closes and a notice says why.",
                    "While the profile runs, you can't edit actions. <b>Run</b> asks first when the editor has changes."
                ]),
            related: ["device-bindings-actions-choose-action", "device-bindings-actions-right-click",
                      "device-bindings-actions-delete-action", "device-bindings-actions-undo"]
        },
        {
            id: "device-bindings-actions-right-click",
            section: page,
            title: "Add an action from the right-click menu",
            body: "<p>Right-click an action in the editor to add another action beside it.</p>"
                + _see([
                    "The first three items are the top three actions in your <b>Actions offered</b> list <a href=\"show:option/Actions offered\">Show me ›</a>.",
                    "The rest are grouped under <b>Add: Map to</b>, <b>Add: Axis and Hat</b>, <b>Add: Logic and Timing</b> and <b>Add: Other</b>.",
                    "<b>Delete</b> removes the action."
                ])
                + _good([
                    "Actions offered sets the order here and in the <b>Add Action</b> list."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-bindings",
            section: page,
            title: "Arrange the bindings on an input",
            body: "<p>An input can have more than one binding, each with its own actions.</p>"
                + _how([
                    "To label a binding, type a <b>Note</b> in its header. It shows on the input's row.",
                    "To change the order, drag a binding by its handle.",
                    "To remove a binding, choose the remove button in its header.",
                    "If it has actions, a box says how many go with it. Choose the red <b>Remove Binding</b> to confirm."
                ])
                + _good([
                    "Removing a binding can't be undone.",
                    "Each action has its own label box. If you leave it blank, no label shows.",
                    "On a button, some actions have switches for press and release. With both off, the action never runs and says so."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-treat-as"]
        },
        {
            id: "device-bindings-actions-treat-as",
            section: page,
            title: "Treat an axis or hat as a button",
            body: "<p><b>Treat as</b> in a binding's header lets an axis or a hat run button actions. A button or a key has no Treat as.</p>"
                + _how([
                    "Choose <b>Treat as</b> <b>Button</b>. Add Action now offers the button actions.",
                    "For an axis, set the range in <b>Activate between</b>. Entering the range presses; leaving it releases.",
                    "Set <b>when entered from</b>: <b>Anywhere</b>, <b>Above</b> (from higher values only) or <b>Below</b> (from lower values only).",
                    "For a hat, tick the directions under <b>Activate on</b>. Any of them presses the button."
                ])
                + _good([
                    "To go back, choose Treat as <b>Axis</b> or <b>Hat</b>.",
                    "If the binding has actions, changing Treat as asks first and says how many actions it removes.",
                    "Choose the red <b>Change and Remove</b> to go ahead. This can't be undone.",
                    "An axis already inside the range when you choose <b>Run</b> gives no press until it leaves and comes back."
                ]),
            related: ["device-bindings-actions-bindings", "device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-safety-net",
            section: page,
            title: "Unfinished actions and recovery copies",
            body: "<p>An action with a problem shows a warning or error icon on its row. Point at the icon to see why.</p>"
                + _see([
                    "A warning: the action still runs.",
                    "An error: the action is not finished. <b>Run</b> skips it.",
                    "When you save, an <b>Unfinished Actions</b> box lists them, each with its first error. They won't be saved.",
                    "Choose <b>Save without them</b> to save the rest, or <b>Cancel</b> to go back and finish them."
                ])
                + "<h4>Unsaved edits after the program closed unexpectedly</h4>"
                + "<p>While a profile has unsaved changes, the program saves a recovery copy about once a minute. This works for a new, never-saved profile too.</p>"
                + "<p>If the program closed with unsaved changes, <b>Unsaved Edits Found</b> appears the next time you open that profile or start the program. It names the profile and when the edits were made.</p>"
                + "<ul>"
                + "<li><b>Restore</b> opens the edits. Save the profile to keep them.</li>"
                + "<li><b>Discard</b> deletes them.</li>"
                + "<li><b>Not now</b> keeps them to be offered again later.</li>"
                + "</ul>"
                + _good([
                    "Recovery copies are in the recovery folder inside the data folder (<b>File › Open Data Folder</b> <a href=\"show:menu/File/Open Data Folder\">Show me ›</a>).",
                    "Saving, Discard or closing the program normally deletes the copy.",
                    "A Play Sound or Load Profile action whose file is missing is kept with a warning. It does nothing until the file is back.",
                    "A profile with an action this program doesn't know still opens. A message names the action; it is kept as it was but does nothing."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-q-not-kept",
                      "device-bindings-actions-play-sound", "device-bindings-actions-load-profile"]
        },
        {
            id: "device-bindings-actions-delete-action",
            section: page,
            title: "Delete an action",
            body: "<p>Deleting an action takes it off the input in the current mode only.</p>"
                + _how([
                    "Open the device's Device Bindings page.",
                    "Right-click the action's row and choose <b>Delete</b>.",
                    "A box asks first. Choose the red <b>Delete Action</b>."
                ])
                + _good([
                    "<b>Enter</b> and <b>Esc</b> both cancel, so you can't delete by accident.",
                    "If the editor is open on that input with unsaved changes, the box says so. Deleting closes the editor and drops them.",
                    "To delete every action of an input in this mode, right-click the input and choose <b>Row › Delete actions…</b>.",
                    "To take a delete back, see " + _link("undo", "Undo a change on the Device Bindings page") + ".",
                    "The profile on disk changes only when you save it."
                ]),
            related: ["device-bindings-actions-undo", "device-bindings-actions-add-action", "device-bindings-actions-menus"]
        },
        {
            id: "device-bindings-actions-undo",
            section: page,
            title: "Undo a change on the Device Bindings page",
            body: "<p><b>Undo</b> and <b>Redo</b> step back and forward through what OK and Delete changed. They also cover changes to groups, order and names.</p>"
                + _how([
                    "Choose Undo or Redo under the Find bar, or beside the right-click menu's title.",
                    "Or press <b>Ctrl+Z</b> to undo, and <b>Ctrl+Y</b> or <b>Ctrl+Shift+Z</b> to redo."
                ])
                + _see([
                    "Beside the buttons, \"Last change\" names the newest change. After an Undo it reads \"Undone\".",
                    "Point at a button to see the change it takes back or does again."
                ])
                + _good([
                    "Undo and Redo don't work while an action is open in the editor. Choose <b>OK</b> or close the editor first.",
                    "They don't work while the profile runs either.",
                    "Opening another device clears every step. Loading another profile keeps the steps for groups, order and names.",
                    "If a change can't be undone, it stays in the list and a notice says so.",
                    "Saved changes are also kept in <a href=\"topic:tools-history\">History</a> (<b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a>)."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-delete-action", "tools-history"]
        },
        {
            id: "device-bindings-actions-keyboard-page",
            section: page,
            title: "Set up keyboard keys",
            body: "<p>The <b>Keyboard</b> page lists the keys you added and the actions on each. It works like the Device Bindings page, with the same Find bar, menus, action editor and Undo.</p>"
                + _how([
                    "Double-click the Keyboard card on Home.",
                    "Choose <b>Add Key…</b> on the Find bar, then press the key. Hold <b>Esc</b> to stop.",
                    "Click the key's row to open its actions, or right-click it and choose <b>Add Action</b>.",
                    "Set up the action and choose <b>OK</b>."
                ])
                + _good([
                    "Add Key… is also in the right-click menu, under <b>Add Inputs</b>.",
                    "The keys you add are kept in the Keyboard's module file, so every profile lists them, with or without actions.",
                    "The key list, groups, order and names are saved when you save the profile.",
                    "To delete a key, right-click it and choose <b>Key › Delete</b>. It asks first; choose the red <b>Delete Key</b>.",
                    "This removes the key's actions in this mode. A key with no actions left in any mode leaves the list.",
                    "Delete shows only on a key with actions in this mode, or with no actions at all.",
                    "To name a key, right-click it and choose <b>Rename</b>. <b>Key › Clear Name</b> removes the name.",
                    "The key's <b>Note</b> shows on its row.",
                    "<b>Order</b> offers <b>By Key Name</b>, <b>By Your Name</b> and <b>Group Names A to Z</b>. See " + _link("layout", "Group, order and name inputs") + ".",
                    "Undo covers OK, Delete, Add Key and changes to groups, order and names. See " + _link("undo", "Undo a change on the Device Bindings page") + "."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-map-to-keyboard",
                      "device-bindings-actions-layout", "device-bindings-actions-menus"]
        },
        {
            id: "device-bindings-actions-output-view",
            section: page,
            title: "Output View",
            body: "<p>A vJoy or Xbox output device opens its <b>Output View</b> instead of a Device Bindings page. It shows, live, what the output module sends.</p>"
                + "<p>You don't edit bindings here. To change one, open the input device's Device Bindings page.</p>"
                + _see([
                    "On a vJoy card: each output and what sends to it.",
                    "On the Xbox card: one section for each Xbox pad that is on and bound.",
                    "Each Xbox section shows the pad's live picture, the devices that drive it, and what sends to each Xbox control."
                ])
                + _good([
                    "An action sending to an output that isn't ticked in Output Module Setup shows <b>(not claimed)</b>. Nothing is sent to that output."
                ]),
            related: ["device-bindings-actions-device-bindings-page", "device-bindings-actions-appearance",
                      "device-bindings-actions-map-to-vjoy", "device-bindings-actions-map-to-xbox"]
        },
        {
            id: "device-bindings-actions-appearance",
            section: page,
            title: "Change how a page looks",
            body: "<p>Appearance changes how a page looks, never what it does.</p>"
                + _how([
                    "Choose <b>Appearance…</b>. On a list page it is on the bar under the toolbar and in the right-click menu.",
                    "Change the sections you want. Changes show at once.",
                    "<b>Open All</b> and <b>Close All</b> expand or fold the sections.",
                    "Choose <b>Save Appearance</b> to keep the changes."
                ])
                + "<h4>What you see</h4>"
                + "<table cellpadding=\"3\"><tr><th align=\"left\">Section</th><th align=\"left\">What it changes</th></tr>"
                + "<tr><td><b>Shown</b></td><td>Which parts of the page show</td></tr>"
                + "<tr><td><b>Group details</b></td><td>The line under each group's name (see " + _link("appearance-details", "Choose the details on groups and rows") + ")</td></tr>"
                + "<tr><td><b>Row details</b></td><td>What each input's row shows after its name</td></tr>"
                + "<tr><td><b>Bindings</b></td><td>The Bindings count and target boxes: sizes, fonts, colors, border, corners and spacing</td></tr>"
                + "<tr><td><b>Live</b></td><td>The LED dots and live bars (Device Bindings page only)</td></tr>"
                + "<tr><td><b>Handles</b></td><td>The drag handles</td></tr>"
                + "<tr><td><b>List</b></td><td>The list as a whole</td></tr>"
                + "<tr><td><b>Rows</b></td><td>Alignment and width of the rows, and the space between groups</td></tr>"
                + "<tr><td><b>Group</b>, <b>Parent Row</b>, <b>Action Row</b></td><td>Row size, padding and colors</td></tr>"
                + "<tr><td><b>Text</b></td><td>The text</td></tr>"
                + "<tr><td><b>Selection</b></td><td>How a selected row looks</td></tr>"
                + "</table>"
                + "<p>Group details, Row details and Bindings aren't on the Xbox Output View.</p>"
                + "<h4>A look for each device</h4>"
                + "<ul>"
                + "<li>Each list page keeps its own look in the program's settings: Device Bindings, Logical Device, Keyboard, OSC and the Xbox Output View.</li>"
                + "<li>On Device Bindings, each device can have its own look. A device without one uses the shared Device Bindings look.</li>"
                + "<li>Save Appearance saves the look for the device shown.</li>"
                + "<li><b>Apply to all devices</b> makes the shown look the shared one, and clears every device's own look.</li>"
                + "<li><b>Copy from device…</b> loads the shared look or another device's look into the panel. Nothing is saved until you choose Save Appearance.</li>"
                + "</ul>"
                + "<h4>Output View</h4>"
                + "<p>An Output View's look is saved in that device's <a href=\"topic:home-devices-module-files\">module file</a>. Its sections are <b>Screen</b>, <b>Layout</b>, <b>Pads</b>, <b>Meters</b>, <b>Buttons</b> and <b>Colors</b>.</p>"
                + _good([
                    "<b>Reset Appearance</b> (red) goes back to the program's default look.",
                    "On Device Bindings, Reset Appearance resets only the device shown.",
                    "On an Output View, <b>Copy Appearance from…</b> copies another output device's look.",
                    "After a reset or a copy, choose Save Appearance to keep it.",
                    "When the window is too narrow for the list, the editor and the panel side by side, the panel closes. Choose Appearance… to open it again.",
                    "Closing the panel with unsaved changes asks first."
                ]),
            related: ["device-bindings-actions-appearance-details", "device-bindings-actions-device-bindings-page",
                      "device-bindings-actions-output-view", "logical-device-appearance"]
        },
        {
            id: "device-bindings-actions-appearance-details",
            section: page,
            title: "Choose the details on groups and rows",
            body: "<p>In <b>Appearance…</b>, <b>Group details</b> and <b>Row details</b> choose the extra facts the list shows. Counts are for the mode shown.</p>"
                + "<h4>Group details</h4>"
                + "<p>These set what the line under each group's name shows. Details use the Bindings count's style, in [brackets] when <b>Brackets</b> is on.</p>"
                + "<table cellpadding=\"3\"><tr><th align=\"left\">Setting</th><th align=\"left\">Shows</th><th align=\"left\">On by default</th></tr>"
                + "<tr><td><b>Controls by type</b></td><td>29 buttons · 6 axes · 1 hat</td><td>Yes</td></tr>"
                + "<tr><td><b>Bindings by type</b></td><td>[30 bindings] after each type</td><td>Yes</td></tr>"
                + "<tr><td><b>No bindings</b></td><td>[1 with no bindings]</td><td>No</td></tr>"
                + "<tr><td><b>Binding output not found</b></td><td>[1 binding output not found], in the warning color</td><td>No</td></tr>"
                + "<tr><td><b>Output devices</b></td><td>[outputs: vJoy 1, Xbox 360 1]</td><td>No</td></tr>"
                + "<tr><td><b>Action types</b></td><td>[30 Map to vJoy, 2 Macro]</td><td>No</td></tr>"
                + "<tr><td><b>Custom names</b></td><td>[5 custom names]</td><td>No</td></tr>"
                + "<tr><td><b>Other modes</b></td><td>[also in mode Combat]</td><td>No</td></tr>"
                + "<tr><td><b>Wrap details</b></td><td>On: a long line wraps. Off: one line ending \"…\"; point at it to see all.</td><td>No</td></tr>"
                + "<tr><td><b>Hide empty</b></td><td>Leaves out details that are 0. The type itself still shows.</td><td>No</td></tr>"
                + "</table>"
                + "<p>Example with the first three on: 29 buttons [30 bindings] · 6 axes [6 bindings] · [1 with no bindings]</p>"
                + "<h4>Row details</h4>"
                + "<table cellpadding=\"3\"><tr><th align=\"left\">Setting</th><th align=\"left\">Shows</th><th align=\"left\">On by default</th></tr>"
                + "<tr><td><b>Bindings and targets</b></td><td>Bindings [2] and a box for each target</td><td>Yes</td></tr>"
                + "<tr><td><b>Action types</b></td><td>[Map to vJoy, Map to Xbox]</td><td>No</td></tr>"
                + "<tr><td><b>Binding output not found</b></td><td>[binding output not found], in the warning color</td><td>No</td></tr>"
                + "<tr><td><b>Other modes</b></td><td>[also in mode Combat]</td><td>No</td></tr>"
                + "<tr><td><b>System name</b></td><td>[system name: Button 5], only on rows with a custom name</td><td>No</td></tr>"
                + "<tr><td><b>Has a condition</b></td><td>[has a condition]</td><td>No</td></tr>"
                + "<tr><td><b>No bindings</b></td><td>[no bindings], only on rows with none</td><td>No</td></tr>"
                + "<tr><td><b>Wrap details</b></td><td>On: a long row wraps. Off: one line ending \"…\"</td><td>No</td></tr>"
                + "</table>"
                + "<h4>Words used</h4>"
                + "<table cellpadding=\"3\"><tr><th align=\"left\">Word</th><th align=\"left\">Means</th></tr>"
                + "<tr><td><b>Binding output not found</b></td><td>The output a binding sends to isn't there. The device is missing or turned off, or doesn't have that button or axis.</td></tr>"
                + "<tr><td><b>No bindings</b></td><td>Nothing is bound in the mode shown.</td></tr>"
                + "<tr><td><b>Custom name</b></td><td>A name you give a control.</td></tr>"
                + "<tr><td><b>System name</b></td><td>The control's own name.</td></tr>"
                + "</table>"
                + _good([
                    "To hide the Bindings count and boxes, turn off Bindings and targets in Row details.",
                    "Group details and Row details aren't on the Xbox Output View."
                ]),
            related: ["device-bindings-actions-appearance", "device-bindings-actions-device-bindings-page",
                      "device-bindings-actions-filter"]
        },

        // ---- Actions ----
        {
            id: "device-bindings-actions-choose-action",
            section: actions,
            title: "Choose an action",
            body: "<p><b>Add Action</b> lists the actions that suit the input type: axis, button, hat or key.</p>"
                + _see([
                    "Most actions do one thing, such as " + _link("map-to-vjoy", "Map to vJoy") + " or " + _link("map-to-keyboard", "Map to Keyboard") + ".",
                    "Some actions hold other actions, for example Condition, Chain, Double Tap and Split Axis. Add that action first, then the actions it runs inside it.",
                    "The others that hold actions are Tempo, Smart Toggle, Merge Axis, Dual Axis Deadzone, Axis Delta and Hat as Buttons."
                ])
                + _good([
                    "<b>Actions offered</b> <a href=\"show:option/Actions offered\">Show me ›</a> in <a href=\"topic:options-profile-options\">Options</a> sets the order of the list. It can also hide actions you never use.",
                    "<b>Map to vJoy</b> is listed only when at least one vJoy device can be an output."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-right-click", "device-bindings-actions-reference", "options-profile-options"]
        },
        {
            id: "device-bindings-actions-map-to-vjoy",
            section: actions,
            title: "Map to vJoy",
            body: "<p>Sends the input to a vJoy axis, button or hat. vJoy is a virtual joystick driver that games read like a real stick.</p>"
                + _how([
                    "Pick the vJoy device, by its output module name, then the output.",
                    "For an axis, choose <b>Absolute</b> (the vJoy axis follows the input) or <b>Relative</b>.",
                    "<b>Relative</b> moves the vJoy axis steadily while the input is held off-center. <b>Speed</b> sets how fast.",
                    "For a button, tick <b>Invert activation</b> if you want pressed and released swapped."
                ])
                + _good([
                    "If you switch to another vJoy device, the same output is kept if that device has it ticked. If not, the first ticked output of the same kind is picked.",
                    "A new Map to vJoy starts on the first ticked output this mode doesn't use yet. When all are used, it starts on the first one.",
                    "The output list offers only outputs that are ticked in Output Module Setup and that the vJoy device really has.",
                    "A Relative axis stops when the input rests for 1 second, or when something else moves that vJoy axis.",
                    "An output that can't be sent shows in red, for example <b>⚠ Button 57</b>. Point at it to see why.",
                    "To fix it, pick another output from the list. Or tick that output in <a href=\"topic:home-devices-vjoy-output\">Output Module Setup</a> <a href=\"show:menu/Tools/Device Setup/Output Module Setup\">Show me ›</a>."
                ]),
            related: ["device-bindings-actions-map-to-xbox", "device-bindings-actions-map-to-logical-device",
                      "home-devices-vjoy-output", "device-bindings-actions-q-vjoy-not-claimed"]
        },
        {
            id: "device-bindings-actions-map-to-xbox",
            section: actions,
            title: "Map to Xbox",
            body: "<p>Sends the input to a virtual Xbox 360 controller. There is nothing to tick in Module Setup.</p>"
                + _how([
                    "In <b>Xbox</b>, pick the pad. It lists the pads turned on in <b>Xbox Setup</b>, and the pad this action already uses.",
                    "In <b>Target</b>, pick the Xbox control. It lists only the controls that suit the input.",
                    "For an axis on a trigger, choose <b>Full axis</b> or <b>Upper half</b>.",
                    "For a button, tick <b>Invert activation</b> if you want pressed and released swapped."
                ])
                + _see([
                    "Pad 1 is Xbox 360 Controller.",
                    "An axis drives sticks and triggers. A button or key drives buttons and triggers. A hat drives the D-pad, buttons and sticks.",
                    "<b>Full axis</b> uses the whole axis travel for the trigger.",
                    "<b>Upper half</b> uses only center to full, so the trigger is released at center."
                ])
                + _good([
                    "A button, key or hat on a trigger pulls it fully while pressed. A hat on a stick moves it in the hat's direction.",
                    "If a saved target doesn't suit the input any more, it stays in the list and keeps working.",
                    "A pad that is off in Xbox Setup shows a red ⚠ and isn't sent to. Turn it on there, or pick another pad.",
                    "Map to Xbox needs the <b>ViGEmBus</b> driver. Without it, the action shows a warning and stays in the profile. See <a href=\"topic:home-devices-xbox-output\">Xbox output module</a>.",
                    "To send a Logical Device control to Xbox, see <a href=\"topic:logical-device-send-to-xbox-vjoy\">Send a control to Xbox or vJoy</a>."
                ]),
            related: ["device-bindings-actions-map-to-vjoy", "logical-device-send-to-xbox-vjoy", "home-devices-xbox-output"]
        },
        {
            id: "device-bindings-actions-map-to-logical-device",
            section: actions,
            title: "Map to Logical Device",
            body: "<p>Sends the input to a control on the Logical Device, the program's own virtual device.</p>"
                + _how([
                    "Pick a Logical Device control of the same type.",
                    "For an axis, choose <b>Absolute</b> or <b>Relative</b>. With Relative, <b>Speed</b> sets how fast it moves.",
                    "For a button, tick <b>Invert activation</b> if you want pressed and released swapped."
                ])
                + _good([
                    "<b>Assign Hardware</b> on the Logical Device page creates these actions for you (<b>Tools › Mapping › Logical Device</b> <a href=\"show:menu/Tools/Mapping/Logical Device\">Show me ›</a>).",
                    "On a Logical Device control, you can't send the control to itself, so the list leaves it out.",
                    "If it is the only control of its type, a new control is made for the action.",
                    "A saved action that sends a control to itself shows that control, marked as blocked. It does nothing at Run; pick another control.",
                    "A loop between controls is stopped. See <a href=\"topic:logical-device-q-loop\">Why was a loop between controls stopped?</a>"
                ]),
            related: ["logical-device-assign-hardware", "logical-device-about", "logical-device-q-loop"]
        },
        {
            id: "device-bindings-actions-map-to-keyboard",
            section: actions,
            title: "Map to Keyboard",
            body: "<p>Holds keys down while the input is held, and lets go when the input is released.</p>"
                + _how([
                    "Choose <b>Record Keys</b>.",
                    "Press the keys for the <b>Key Combination</b>."
                ])
                + _good([
                    "Shift, Ctrl, Alt and Win are pressed first. The other keys follow in the order you pressed them.",
                    "The keys are pressed once and don't repeat while you hold the input. For a key that repeats, use a " + _link("macro", "Macro") + " with Repeat Mode <b>Hold</b>."
                ]),
            related: ["device-bindings-actions-macro", "device-bindings-actions-keyboard-page"]
        },
        {
            id: "device-bindings-actions-map-to-mouse",
            section: actions,
            title: "Map to Mouse",
            body: "<p>Clicks a mouse button or moves the pointer.</p>"
                + _how([
                    "Choose the <b>Mode</b>: <b>Button</b> clicks a mouse button, <b>Motion</b> moves the pointer.",
                    "For Button, record the mouse button. Wheel Up and Wheel Down are sent once per press.",
                    "For Motion on a button, set <b>Minimum speed (px/s)</b>, <b>Maximum speed (px/s)</b>, <b>Time to maximum speed (sec)</b> and <b>Direction (degrees)</b>.",
                    "For Motion on an axis, set <b>Control motion of</b> to <b>X Axis</b> or <b>Y Axis</b>."
                ])
                + _good([
                    "Motion from several inputs adds up. Two buttons pushing right move faster; left and right cancel out.",
                    "Each button or hat speeds up on its own, from its minimum to its maximum speed.",
                    "A mode change, <b>Pause</b> and <b>Stop</b> all stop the pointer.",
                    "After a mode change, the pointer keeps moving only if the new mode also moves the mouse from the same input.",
                    "With tracing on, the Trace tab shows a line for each mouse change.",
                    "A running profile never reads the mouse, so a mouse button can't run actions. It can only be sent."
                ]),
            related: ["device-bindings-actions-macro"]
        },
        {
            id: "device-bindings-actions-macro",
            section: actions,
            title: "Macro",
            body: "<p>Plays a list of steps: Joystick, Keyboard, Logical Device, Mouse Button, Mouse Motion, Pause and vJoy.</p>"
                + _how([
                    "To add steps one at a time, pick the kind of step in the box and choose <b>Add Step</b>.",
                    "For a Keyboard step, choose <b>Record Input</b> and press the key. Then pick <b>Press</b> or <b>Release</b> beside it. A step sends only one of them, so a key tap needs a Press step and a Release step.",
                    "To record steps, choose <b>Record Inputs</b> and tick what to record: Keyboard, Mouse, Axis, Button, Hat and Timings. Then start and stop the recording.",
                    "Choose the <b>Repeat Mode</b> (see below).",
                    "Tick <b>Exclusive</b> or <b>Pre-Emptive</b> if this macro must not play alongside others."
                ])
                + "<h4>What you see</h4>"
                + "<table cellpadding=\"3\"><tr><th align=\"left\">Choice</th><th align=\"left\">What it does</th></tr>"
                + "<tr><td><b>Single</b></td><td>Plays the steps once per press.</td></tr>"
                + "<tr><td><b>Count</b></td><td>Plays the steps the number of <b>Times</b> you set.</td></tr>"
                + "<tr><td><b>Toggle</b></td><td>One press starts repeating; the next press stops it.</td></tr>"
                + "<tr><td><b>Hold</b></td><td>Repeats while you hold the input. It always plays at least once.</td></tr>"
                + "<tr><td><b>Delay (sec)</b></td><td>The wait between repeats, for Count, Toggle and Hold.</td></tr>"
                + "<tr><td><b>Exclusive</b></td><td>Waits for any macro that is playing to finish. Other macros then wait until this one is done.</td></tr>"
                + "<tr><td><b>Pre-Emptive</b></td><td>Shows when Exclusive is ticked. The macro starts at once and pauses the others; they carry on when it ends.</td></tr>"
                + "</table>"
                + "<p>For example, a key that repeats while you hold a button: add a Keyboard step set to Press, then one for the same key set to Release. Choose Repeat Mode <b>Hold</b> and set <b>Delay (sec)</b> for the gap between key presses.</p>"
                + _good([
                    "<b>Delay (sec)</b> comes after the last step, before the steps play again. It doesn't change the wait between steps.",
                    "Between steps without a <b>Pause</b>, the macro waits for <b>Macro Default Delay</b> in <a href=\"topic:options-profile-profile-settings\">Profile Settings</a> <a href=\"show:menu/View/Profile Settings\">Show me ›</a>.",
                    "If the profile doesn't set one, it uses <b>Default delay</b> in Options <a href=\"show:option/Default delay\">Show me ›</a>.",
                    "A Joystick step acts like the stick itself. It only works for controls ticked in the stick's Module Setup.",
                    "New Joystick, Keyboard, Logical Device, Mouse Button and vJoy button steps start on <b>Press</b>.",
                    "A new vJoy step starts on the first ticked vJoy output. With none ticked, a notice asks you to tick one first.",
                    "A step the program can't read shows as <b>Unreadable step</b>. It does nothing and is saved unchanged; you can remove it.",
                    "Mouse buttons can be recorded as steps, but a mouse button is never an input. See " + _link("map-to-mouse", "Map to Mouse") + "."
                ]),
            related: ["device-bindings-actions-map-to-keyboard", "device-bindings-actions-map-to-mouse", "options-profile-profile-settings"]
        },
        {
            id: "device-bindings-actions-response-curve",
            section: actions,
            title: "Response Curve",
            body: "<p>Changes how an axis responds, for example to make the center gentler. The actions below it get the changed value.</p>"
                + _how([
                    "Choose the curve type (see below).",
                    "Drag the points, or type <b>X</b> and <b>Y</b>.",
                    "Set the <b>Deadzone</b>, the part of the travel that is ignored."
                ])
                + _see([
                    "<b>Piecewise Linear</b>: straight lines between the points.",
                    "<b>Cubic Spline</b>: a smooth curve through the points.",
                    "<b>Cubic Bezier Spline</b>: a smooth curve through the points, bent by each point's handles.",
                    "<b>Invert Curve</b> flips the curve.",
                    "<b>Symmetric</b> mirrors your edits around the center."
                ]),
            related: ["device-bindings-actions-dual-axis-deadzone", "device-bindings-actions-split-axis"]
        },
        {
            id: "device-bindings-actions-split-axis",
            section: actions,
            title: "Split Axis",
            body: "<p>Splits one axis into two parts, each with its own actions. <b>Split axis at</b> sets where the lower or left part ends and the upper or right part begins.</p>"
                + _good(["Each part is stretched to the full range, so each one works like a whole axis."]),
            related: ["device-bindings-actions-merge-axis", "device-bindings-actions-response-curve"]
        },
        {
            id: "device-bindings-actions-merge-axis",
            section: actions,
            title: "Merge Axis",
            body: "<p>Combines two axes into one value for the actions in its <b>Actions</b> list, for example two pedals into one rudder.</p>"
                + _how([
                    "Pick or create a <b>Merge axis instance</b>: a named merge setup that several inputs can share.",
                    "Pick the <b>First axis</b> and <b>Second axis</b>.",
                    "Choose the <b>Merge operation</b> (see below)."
                ])
                + _see([
                    "<b>Average</b>, <b>Minimum</b>, <b>Maximum</b> and <b>Sum</b> combine the two values that way.",
                    "<b>Maximum Deflection</b> uses whichever axis is furthest from center. When both are equally far, the second axis wins.",
                    "<b>Bidirectional</b> and <b>Prefer Center</b> are also offered."
                ])
                + _good([
                    "A new Merge Axis starts on its own setup, named \"Merge Axis 1\" or the next free number.",
                    "The <b>+</b> button makes a new setup and selects it. The pencil renames it.",
                    "The list offers the one you're editing, a new one, and any that other inputs already use. Deleted ones aren't listed.",
                    "If you pick one that another input uses, both inputs share it, and it keeps its name."
                ]),
            related: ["device-bindings-actions-split-axis", "device-bindings-actions-dual-axis-deadzone"]
        },
        {
            id: "device-bindings-actions-dual-axis-deadzone",
            section: actions,
            title: "Dual Axis Deadzone",
            body: "<p>Applies one deadzone to a pair of axes, such as a stick's X and Y. It has a round <b>Inner</b> deadzone and a square <b>Outer</b> limit.</p>"
                + _how([
                    "Pick or create a <b>Deadzone instance</b>: a named deadzone setup that several inputs can share.",
                    "Pick the two axes.",
                    "Add the actions for each axis's result to its own action list."
                ])
                + _good([
                    "A new Dual Axis Deadzone starts on its own setup, named \"Dual Axis Deadzone 1\" or the next free number.",
                    "The <b>+</b> button makes a new setup and selects it. The pencil renames it.",
                    "The list offers the one you're editing, a new one, and any that other inputs already use. Deleted ones aren't listed.",
                    "If you pick one that another input uses, both inputs share it, and it keeps its name."
                ]),
            related: ["device-bindings-actions-response-curve", "device-bindings-actions-merge-axis"]
        },
        {
            id: "device-bindings-actions-axis-delta",
            section: actions,
            title: "Axis Delta",
            body: "<p>Turns axis movement into button presses. Each time the axis moves by the <b>Change threshold</b>, it presses and releases one set of actions.</p>"
                + _see([
                    "<b>Positive change</b>: the actions for the axis value going up.",
                    "<b>Negative change</b>: the actions for the axis value going down."
                ])
                + _good([
                    "A new Axis Delta starts with the <b>Threshold</b> set in Options under <b>Axis Delta</b> <a href=\"show:option/Threshold\">Show me ›</a>."
                ]),
            related: ["device-bindings-actions-split-axis"]
        },
        {
            id: "device-bindings-actions-condition",
            section: actions,
            title: "Condition",
            body: "<p>Runs one action list when its conditions are true and another when they are false.</p>"
                + _how([
                    "Choose <b>Any</b> (one condition is enough) or <b>All</b> (every condition must be true).",
                    "Choose <b>Add Condition</b> and pick its kind: Joystick, Keyboard, Current Input, vJoy or Logical Device state.",
                    "Add the actions for true and for false."
                ])
                + _good([
                    "A condition on an input that isn't ticked in Module Setup sees it as not pressed or centered.",
                    "A condition on a stick plugged in later works once it is connected.",
                    "New button and key conditions start on <b>Pressed</b>.",
                    "A new vJoy condition starts on the first ticked vJoy output. With none ticked, it isn't added and a notice says why."
                ]),
            related: ["device-bindings-actions-chain", "device-bindings-actions-tempo"]
        },
        {
            id: "device-bindings-actions-chain",
            section: actions,
            title: "Chain",
            body: "<p>Each press runs the next <b>Sequence</b> of actions in turn.</p>"
                + _how([
                    "Choose <b>Add Chain Sequence</b> for each sequence, and add its actions.",
                    "Set <b>Timeout (sec, 0 = never)</b>."
                ])
                + _good([
                    "After the timeout passes with no press, the chain starts again at the first sequence."
                ]),
            related: ["device-bindings-actions-double-tap", "device-bindings-actions-condition"]
        },
        {
            id: "device-bindings-actions-double-tap",
            section: actions,
            title: "Double Tap",
            body: "<p>Gives a single tap and a double tap their own actions. Two taps within <b>Double-tap threshold (sec)</b> count as a double tap.</p>"
                + _see([
                    "<b>exclusive</b>: a single tap waits to see if a second tap comes. Then only the single-tap or the double-tap actions run.",
                    "<b>combined</b>: the single-tap actions run at once on every press. A double tap also runs the double-tap actions."
                ])
                + _good([
                    "A new Double Tap starts with the <b>Duration</b> set in Options under <b>Double Tap</b> <a href=\"show:option/Double Tap duration\">Show me ›</a>."
                ]),
            related: ["device-bindings-actions-tempo", "device-bindings-actions-chain"]
        },
        {
            id: "device-bindings-actions-tempo",
            section: actions,
            title: "Tempo",
            body: "<p>Gives a <b>Short press</b> and a <b>Long press</b> their own actions. A press longer than <b>Long-press threshold (sec)</b> is a long press.</p>"
                + _see([
                    "<b>Activate on</b> sets whether the actions run on <b>press</b> or on <b>release</b>."
                ])
                + _good([
                    "A new Tempo starts with the <b>Duration</b> set in Options under <b>Tempo</b> <a href=\"show:option/Tempo duration\">Show me ›</a>."
                ]),
            related: ["device-bindings-actions-double-tap", "device-bindings-actions-smart-toggle"]
        },
        {
            id: "device-bindings-actions-smart-toggle",
            section: actions,
            title: "Smart Toggle",
            body: "<p>One input works as a toggle or as a hold, depending on how long you press it.</p>"
                + _see([
                    "A quick press (let go within <b>Hold time (sec)</b>) turns its actions on until you press again.",
                    "A longer hold keeps them on only while you hold it."
                ])
                + _good([
                    "A new Smart Toggle starts with the <b>Duration</b> set in Options under <b>Smart Toggle</b> <a href=\"show:option/Smart Toggle duration\">Show me ›</a>."
                ]),
            related: ["device-bindings-actions-tempo"]
        },
        {
            id: "device-bindings-actions-hat-as-buttons",
            section: actions,
            title: "Hat as Buttons",
            body: "<p>Gives each hat direction its own action list.</p>"
                + _see([
                    "<b>Button mode</b>: <b>4 way</b> gives up, down, left and right. <b>8 way</b> adds the four diagonals."
                ])
                + _good([
                    "Switching from 8 way to 4 way asks first when the diagonals have actions. <b>Switch to 4 way</b> removes them."
                ]),
            related: ["device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-change-mode",
            section: actions,
            title: "Change Mode",
            body: "<p>Changes the running mode when you press the input. The program remembers the modes you have been in, so you can step back.</p>"
                + _how([
                    "In the <b>Mode</b> box <a href=\"show:modebar\">Show me ›</a>, pick the mode you press the input from. Add Change Mode to the input there.",
                    "Choose the kind. For Switch, pick the mode under <b>Switch to mode</b>; for Temporary, under <b>Temporarily switch to mode</b>. For Cycle, choose <b>Add Mode</b> for each mode in the list.",
                    "To come back, pick the mode you go to in the Mode box and add a Change Mode there too, such as Previous or Unwind. Temporary needs none."
                ])
                + "<h4>What you see</h4>"
                + "<table cellpadding=\"3\"><tr><th align=\"left\">Choice</th><th align=\"left\">What it does</th></tr>"
                + "<tr><td><b>Switch</b></td><td>Goes to the mode you pick.</td></tr>"
                + "<tr><td><b>Previous</b></td><td>Goes back to the mode you were in before this one. Pressing it again returns you, so it flips between two modes.</td></tr>"
                + "<tr><td><b>Unwind</b></td><td>Leaves this mode for the one before it. Each press steps one mode further back.</td></tr>"
                + "<tr><td><b>Cycle</b></td><td>Each press goes to the next mode in a list you make.</td></tr>"
                + "<tr><td><b>Temporary</b></td><td>Goes to a mode while you hold the input, and back when you let go.</td></tr>"
                + "</table>"
                + _good([
                    "Use Previous to flip between two modes with one button.",
                    "Use Unwind to go back along the way you came, one mode per press.",
                    "How the program remembers your path: see <a href=\"topic:modes-while-running\">How modes change while the profile runs</a>.",
                    "Cycle's first press goes to the mode after the current one. If the current mode isn't in the list, it goes to the first.",
                    "Cycle skips deleted modes.",
                    "Modes are added, renamed and deleted in <b>Manage Modes</b> <a href=\"show:modebar/Manage Modes\">Show me ›</a>. Renaming a mode updates the Change Mode actions that name it.",
                    "When you come back to a mode you were in earlier, <b>Mode cycle resolution</b> in Options decides how your path is shortened. See <a href=\"topic:modes-cycle-resolution\">Come back to a mode you passed</a>."
                ]),
            related: ["device-bindings-actions-load-profile", "modes-modes", "modes-manage", "modes-while-running", "modes-cycle-resolution"]
        },
        {
            id: "device-bindings-actions-load-profile",
            section: actions,
            title: "Load Profile",
            body: "<p>Loads another profile file when you press the input. Set <b>Profile filename</b>, or choose <b>Select File</b>.</p>"
                + _good([
                    "If a profile is running, the program stops it, loads the new one and runs that.",
                    "It doesn't load over unsaved changes. A notice, <b>Load Profile Waited</b>, asks you to save or discard them first.",
                    "If the file is missing, nothing is loaded and a notice says so.",
                    "A profile whose Load Profile file is missing still opens. The action shows a warning."
                ]),
            related: ["device-bindings-actions-change-mode", "getting-started-run"]
        },
        {
            id: "device-bindings-actions-pause-and-resume",
            section: actions,
            title: "Pause and Resume",
            body: "<p>Stops or restarts all actions while the profile keeps running.</p>"
                + _see([
                    "<b>Pause</b> stops all actions.",
                    "<b>Resume</b> starts them again.",
                    "<b>Toggle</b> pauses when running and resumes when paused."
                ])
                + _good([
                    "While paused, the status bar reads \"Running (Paused)\".",
                    "Pause and Resume actions keep working while paused, so you can resume.",
                    "Each <b>Run</b> starts un-paused.",
                    "A saved Pause and Resume action whose choice the program can't read loads as Pause. The system log says so."
                ]),
            related: ["device-bindings-actions-change-mode"]
        },
        {
            id: "device-bindings-actions-play-sound",
            section: actions,
            title: "Play Sound",
            body: "<p>Plays a WAV, MP3 or OGG file at the chosen <b>Volume</b>. Type the file's path in the box, or pick the file.</p>"
                + _good([
                    "<b>Playback mode</b> in Options <a href=\"show:option/Playback mode\">Show me ›</a> sets what happens when sounds overlap:<ul>"
                        + "<li><b>Sequential</b> plays them one after another.</li>"
                        + "<li><b>Interrupt</b> stops the one playing.</li>"
                        + "<li><b>Overlap</b> plays them together.</li></ul>",
                    "Sounds play only while the profile runs. <b>Stop</b> cuts them off.",
                    "A missing file shows a warning, and pressing the input plays nothing."
                ]),
            related: ["device-bindings-actions-text-to-speech"]
        },
        {
            id: "device-bindings-actions-text-to-speech",
            section: actions,
            title: "Text to Speech",
            body: "<p>Speaks the text you type. You can put it on a button or a keyboard key.</p>"
                + _how([
                    "Type the text.",
                    "Choose what happens when other speech is playing (see below).",
                    "Set <b>Volume</b>, <b>Rate</b> and <b>Pitch</b>."
                ])
                + _see([
                    "<b>Interrupt</b> stops the speech playing and speaks this at once.",
                    "<b>Queue Front</b> speaks this next, before other waiting speech.",
                    "<b>Queue Back</b> speaks this after all waiting speech."
                ])
                + _good([
                    "Typing <code>${current_mode}</code> in the text speaks the current mode's name.",
                    "Speech plays only while the profile runs. <b>Stop</b> cuts it off.",
                    "Choose the voice in Options under <b>Text to Speech</b> <a href=\"show:option/Voice selection\">Show me ›</a>. If that voice is gone, the Windows default voice speaks."
                ]),
            related: ["device-bindings-actions-play-sound"]
        },
        {
            id: "device-bindings-actions-send-osc",
            section: actions,
            title: "Send OSC",
            body: "<p>Sends an OSC message (a network message many control apps use), for example to light a Stream Deck key. You can put it on a button, a key or an axis.</p>"
                + _how([
                    "Choose the <b>Target</b>: one of OSC's targets, or <b>Reply to sender</b> (the address of the last message received).",
                    "Type the <b>Address</b>. It starts with \"/\".",
                    "Under <b>Values</b>, set each value to Fixed or Input value (see below).",
                    "Choose each value's type (see below).",
                    "On a button or key, choose whether it sends on press, on release or both."
                ])
                + _see([
                    "<b>Fixed</b>: sent as you type it.",
                    "<b>Input value</b>: 1 or 0 for a button. For an axis, a number from <b>Min:</b> to <b>Max:</b>, 0 to 1 unless you change them.",
                    "A new action starts with one Input value. <b>Add Value</b> adds a Fixed value; the remove button beside a value removes it.",
                    "<b>Auto</b> uses the type last received on that address, or Float. The others are <b>Int</b>, <b>Float</b>, <b>Bool</b> and <b>Text</b>."
                ])
                + _good([
                    "It sends only while the profile runs, and only while <b>OSC output (Send OSC actions and feedback)</b> is on.",
                    "That setting is on the <b>Output</b> tab of OSC's <b>OSC Setup…</b>, where the targets are set too. See <a href=\"topic:osc-output-tab\">Output tab</a>.",
                    "A target that was removed shows as <b>Missing target</b>: pick another one.",
                    "An address that doesn't start with \"/\" shows a warning.",
                    "Every message it sends shows in the OSC Monitor as <b>Out</b> (<b>Tools › OSC Monitor</b> <a href=\"show:menu/Tools/OSC Monitor\">Show me ›</a>).",
                    "For the value types and the type codes sent, see <a href=\"topic:osc-value-types\">OSC value types</a> and <a href=\"topic:osc-tech-out\">OSC values the program sends</a>."
                ]),
            related: ["osc-output-tab", "osc-value-types", "osc-send", "options-profile-osc"]
        },
        {
            id: "device-bindings-actions-run-command",
            section: actions,
            title: "Run Command",
            body: "<p>Starts a program. Set the <b>Executable</b> and its <b>Arguments</b>.</p>"
                + _good([
                    "Arguments are split on spaces. Put quotes around values that contain spaces.",
                    "The program runs with your own permissions.",
                    "If the program can't be started, the log says so once and nothing else happens."
                ]),
            related: ["device-bindings-actions-load-profile"]
        },
        {
            id: "device-bindings-actions-description",
            section: actions,
            title: "Description",
            body: "<p>A note on the input. It does nothing when you press the input.</p>",
            related: ["device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-reference",
            section: actions,
            title: "Reference",
            body: "<p>Reuses an action you already added, on an input of the same type.</p>"
                + _how([
                    "Pick the action. The list shows only actions you added yourself.",
                    "Choose to share it or duplicate it (see below)."
                ])
                + _see([
                    "Share: both inputs use the same action, so a change to one changes both.",
                    "Duplicate: a separate copy you can change on its own."
                ])
                + _good([
                    "A shared action's editor says <b>Shared with …</b> and names the other inputs.",
                    "<b>OK</b> changes a shared action for every input that uses it. <b>Undo</b> puts it back for all of them."
                ]),
            related: ["device-bindings-actions-choose-action", "device-bindings-actions-undo"]
        },

        // ---- Common questions ----
        {
            id: "device-bindings-actions-q-cannot-edit",
            section: questions,
            title: "Why can't I change an action?",
            body: "<p>Because the profile is running. You can't edit actions on the Device Bindings, Keyboard, OSC and Logical Device pages while it runs.</p>"
                + "<p>Choose <b>Stop</b> <a href=\"show:toolbar/Run\">Show me ›</a>, then edit. See <a href=\"topic:getting-started-run\">Run and Stop</a>.</p>",
            related: ["device-bindings-actions-add-action"]
        },
        {
            id: "device-bindings-actions-q-action-missing",
            section: questions,
            title: "Why is an action missing from the Add Action list?",
            body: "<p>The list shows only the actions that suit the input type. <b>Actions offered</b> in <a href=\"topic:options-profile-options\">Options</a> can also hide actions <a href=\"show:option/Actions offered\">Show me ›</a>.</p>",
            related: ["device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-q-not-kept",
            section: questions,
            title: "Why did my action not stay after I closed the program?",
            body: "<p><b>OK</b> keeps the action in the open profile only. Choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> (<b>Ctrl+S</b>) to write it to disk.</p>"
                + "<p>If the program closed unexpectedly before you saved, the edits may be offered back. See <a href=\"topic:device-bindings-actions-safety-net\">Unfinished actions and recovery copies</a>.</p>",
            related: ["device-bindings-actions-add-action"]
        },
        {
            id: "device-bindings-actions-q-unfinished",
            section: questions,
            title: "Why does Save say some actions are not finished?",
            body: "<p>Those actions have an error, so they can't be saved. Choose <b>Cancel</b> to go back and finish them, or <b>Save without them</b> to leave them out. See <a href=\"topic:device-bindings-actions-safety-net\">Unfinished actions and recovery copies</a>.</p>",
            related: ["device-bindings-actions-safety-net"]
        },
        {
            id: "device-bindings-actions-q-vjoy-not-claimed",
            section: questions,
            title: "Why is a Map to vJoy output red with ⚠?",
            body: "<p>The program can't send to that output. Point at it to see why:</p>"
                + "<ul>"
                + "<li>the output isn't ticked in the vJoy device's Output Module Setup,</li>"
                + "<li>the vJoy device doesn't have it, or</li>"
                + "<li>that vJoy device is turned off.</li>"
                + "</ul>"
                + "<p>To fix it, pick another output from the list. Or tick this output in <a href=\"topic:home-devices-vjoy-output\">Output Module Setup</a> <a href=\"show:menu/Tools/Device Setup/Output Module Setup\">Show me ›</a>.</p>"
                + "<p>To find them all, look at the device's card on Home, which counts them. The Find tick <b>Binding output not found</b> lists them.</p>"
                + "<p>To fix many at once, see <a href=\"topic:tools-health\">Find problems with Health</a>.</p>",
            related: ["device-bindings-actions-map-to-vjoy", "device-bindings-actions-filter"]
        },
        {
            id: "device-bindings-actions-q-same-action",
            section: questions,
            title: "How do I use the same action on two inputs?",
            body: "<p>Add a " + _link("reference", "Reference") + " action to the second input, and share the first input's action.</p>",
            related: ["device-bindings-actions-reference"]
        }
    ]
}
