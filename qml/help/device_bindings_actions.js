// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: the Device Bindings page and every action.

.pragma library

var chapter = { id: "device-bindings-actions", title: "Device Bindings and actions" }

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
            body: "<p>The Device Bindings page lists the claimed inputs of one device and the actions on each. It works like the <a href=\"topic:logical-device-about\">Logical Device</a> page: the same Find bar, list, right-click menus and action editor.</p>"
                + "<ul>"
                + "<li>To open it, double-click a card on <a href=\"topic:home-devices-home\">Home</a>, or choose <b>View › Device Bindings</b> <a href=\"show:menu/View/Device Bindings\">Show me ›</a>.</li>"
                + "<li>The arrows beside the title step to the previous or next device.</li>"
                + "<li>Actions belong to the mode in the <b>Mode</b> box <a href=\"show:modebar\">Show me ›</a>, on the mode bar under the toolbar; see <a href=\"topic:modes-mode-box\">Choose the mode you edit and run</a>.</li>"
                + "<li>Each input's row shows its <b>Note</b>. The rows under it name each action and where it goes: the vJoy output, the keys, the mode or the file.</li>"
                + "<li>After the input's name, <b>Bindings</b> shows how many are bound in this mode and a box for each target, for example <b>Bindings [2]</b> [vJoy 1 · Button 1] [Xbox 360 Controller · A]. They line up in one column on every row. When there are more boxes than fit, the row ends with \"…\"; hover it to see every target. A row with nothing bound shows nothing. Change the look, or turn it off with <b>Show bindings</b>, in the <b>Bindings</b> section of <b>Appearance…</b>.</li>"
                + "<li>Click an input's row to open all its actions in the editor beside the list, or an action's row to open only that action.</li>"
                + "<li>Inputs come from the claims in <b>Module Setup</b>, so they can't be added or removed here. With no claimed inputs, the page says \"No inputs are claimed for this device.\": right-click it and choose <b>Module Setup…</b>.</li>"
                + "</ul>"
                + _good([
                    "<b>OK</b> keeps an action in the profile; <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> writes it to disk.",
                    "Groups, order and your names are kept in the device's <a href=\"topic:home-devices-module-files\">module file</a>, shared by every profile; see " + _link("layout", "Group, order and name inputs") + ".",
                    "With <b>Show LED dots</b> and <b>Show live bars</b> on in <b>Appearance…</b>, a pressed input lights its row and the list jumps to it.",
                    "The <b>Keyboard</b> card opens its own page; see " + _link("keyboard-page", "Set up keyboard keys") + ".",
                    "An output device opens its <b>Output View</b> instead; see " + _link("output-view", "Output View") + "."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-filter", "device-bindings-actions-layout",
                      "device-bindings-actions-menus", "modes-modes", "device-bindings-actions-appearance"]
        },
        {
            id: "device-bindings-actions-layout",
            section: page,
            title: "Group, order and name inputs",
            body: "<p>Groups, order and names keep a long list of inputs easy to find. They work as on the <a href=\"topic:logical-device-group-controls\">Logical Device</a> page.</p>"
                + "<ul>"
                + "<li>Rename: right-click the input and choose <b>Rename</b>. This is the input's name in Module Setup too.</li>"
                + "<li>Remove your name: right-click and choose <b>Row</b> › <b>Clear Name</b>. It asks first (\"Clear the name of <i>input</i>?\"); the system name stays.</li>"
                + "<li>Put inputs in a group: select them, right-click, open <b>Group</b>, then type a name in <b>Group as</b> or choose <b>Move to</b> a group. New groups, moving and deleting groups are under <b>Groups</b>; deleting a group keeps its inputs, in Ungrouped.</li>"
                + "<li>Drag an input by its handle, or a group by its header, to move it.</li>"
                + "<li>Sort: right-click, open <b>Order</b>, then choose <b>By System Name</b>, <b>By Your Name</b> or <b>Group Names A to Z</b>.</li>"
                + "</ul>"
                + "<h4>When they are saved</h4>"
                + "<p>Group, order and name changes are kept for <b>File › Save Profile</b> (<b>Ctrl+S</b>), as on the Logical Device and OSC pages. Until then the title shows <b>*</b>, and <b>Discard</b> on the save-changes question drops them.</p>"
                + _good([
                    "They are saved in the device's module file, so every profile shows the same groups, order and names.",
                    "If something else changes that device's layout or claims before you save (History Restore, the Device Library, an Export / Import Device import, or Module Setup), the newer file wins: your unsaved changes for it are dropped with the note \"The layout changed elsewhere; your unsaved changes for <i>device</i> were dropped.\" A change to only a picture or the device map keeps them.",
                    "<b>Undo</b> takes these changes back too; see " + _link("undo", "Undo a change on the Device Bindings page") + "."
                ]),
            related: ["device-bindings-actions-device-bindings-page", "device-bindings-actions-menus",
                      "device-bindings-actions-undo", "logical-device-group-controls"]
        },
        {
            id: "device-bindings-actions-menus",
            section: page,
            title: "Device Bindings page menus",
            body: "<p>What each right-click menu on the Device Bindings page holds. The Logical Device, Keyboard and OSC pages share the same menus.</p>"
                + "<ul>"
                + "<li>Empty space: <b>Module Setup…</b> and <b>Appearance…</b>, then <b>Groups</b> (<b>New Group</b>) and <b>Order</b>. <b>Undo</b> and <b>Redo</b> sit beside the menu's title.</li>"
                + "<li>An input: <b>Add Action</b>, <b>Rename</b> and <b>History</b>, then <b>Row</b> (<b>Clear Name</b>, <b>Delete actions…</b>) and <b>Group</b> (<b>Group as</b>, and <b>Move to</b> each group).</li>"
                + "<li>A group header: <b>Rename Group</b>, then <b>Groups</b> › <b>Move Group Up</b>, <b>Move Group Down</b> or <b>Delete Group</b>.</li>"
                + "<li>An action row: <b>Open</b> and <b>Delete</b>.</li>"
                + "</ul>"
                + _good([
                    "<b>Delete actions…</b> asks first (\"Delete the actions of <i>input</i>?\"): every action of the input in this mode goes, and the input stays. It isn't offered for the input open in the editor.",
                    "With several inputs selected, the menu's title counts them and <b>Add Action</b>, <b>Rename</b> and <b>History</b> are left out.",
                    "<b>History</b> opens <a href=\"topic:tools-history\">History</a> showing only that input in this mode."
                ]),
            related: ["device-bindings-actions-layout", "device-bindings-actions-delete-action", "logical-device-menus"]
        },
        {
            id: "device-bindings-actions-filter",
            section: page,
            title: "Filter the inputs",
            body: "<p>The <b>Find</b> bar above the list shows only the inputs you want to see.</p>"
                + "<ul>"
                + "<li>Type a system name, your name or a group (<b>Ctrl+F</b> goes to the box). A line under it says how many are found; <b>×</b> or <b>Esc</b> clears the typing.</li>"
                + "<li>The first box shows all inputs, or only buttons, axes or hats.</li>"
                + "<li><b>Clear</b> resets every Find filter: it empties the search and sets the first box, the ticks under the bar and the <b>Type</b> and <b>Output</b> boxes back to show everything.</li>"
                + "<li>The action box <b>Type</b> shows inputs with one kind of action, such as Map to vJoy, Macro or Change Mode. To find inputs with none, use <b>No actions in this mode</b>.</li>"
                + "<li>The <b>Output</b> box shows inputs that send to one place. It lists only the places in use.</li>"
                + "<li>Under the bar, <b>Ungrouped</b> and <b>No actions in this mode</b> narrow the list further. <b>Can't be sent</b> shows only inputs with a Map to vJoy the program can't send; their action rows show a red <b>⚠</b> (hover it to see why).</li>"
                + "</ul>"
                + _good([
                    "When nothing matches, the page says \"Nothing matches the Find filters.\" Choose <b>Clear Filters</b>, or <b>Clear</b> on the bar, to reset everything."
                ]),
            related: ["device-bindings-actions-device-bindings-page", "device-bindings-actions-add-action"]
        },
        {
            id: "device-bindings-actions-add-action",
            section: page,
            title: "Add an action to an input",
            body: "<p>An action says what an input does when it fires.</p>"
                + "<ol>"
                + "<li>Open the device's Device Bindings page.</li>"
                + "<li>Right-click the input's row and choose <b>Add Action</b>. The action editor opens beside the list.</li>"
                + "<li>Choose the action and set it up.</li>"
                + "<li>Choose <b>OK</b>.</li>"
                + "<li>To keep it on disk, choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> (<b>Ctrl+S</b>).</li>"
                + "</ol>"
                + _good([
                    "Clicking an input's row opens all its actions in the editor; clicking a row under it opens only that action.",
                    "<b>Close pane after OK</b> closes the editor when OK succeeds. Drag the editor's left edge to make it wider.",
                    "Opening another input or action (a row click, <b>Open</b> or <b>Add Action</b>) while the editor has changes that are not saved asks first (\"The action editor has changes that are not saved.\"): <b>Save</b> keeps them, <b>Discard</b> drops them, and <b>Cancel</b> keeps the editor on its input with the selection put back. Leaving the page asks the same.",
                    "If you pick another mode while the editor is open, it stays on the mode it was opened in: OK still writes there. If that mode is deleted, the editor closes with the notice \"The mode <i>name</i> was deleted, so its action editor closed.\"",
                    "While the profile runs, the actions are locked (\"Profile running: stop it to edit\"). <b>Run</b> asks first about an action editor with changes."
                ]),
            related: ["device-bindings-actions-choose-action", "device-bindings-actions-right-click",
                      "device-bindings-actions-delete-action", "device-bindings-actions-undo"]
        },
        {
            id: "device-bindings-actions-right-click",
            section: page,
            title: "Add an action from the right-click menu",
            body: "<p>Right-click an action in the editor to add another action beside it.</p>"
                + "<ul>"
                + "<li>The first items add the 3 actions at the top of your <b>Actions offered</b> list.</li>"
                + "<li>The rest are grouped under <b>Add: Map to</b>, <b>Add: Axis and Hat</b>, <b>Add: Logic and Timing</b> and <b>Add: Other</b>.</li>"
                + "<li><b>Delete</b> removes the action.</li>"
                + "</ul>"
                + _good([
                    "<b>Actions offered</b> <a href=\"show:option/Actions offered\">Show me ›</a> sets the order, the same as the <b>Add Action</b> list."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-bindings",
            section: page,
            title: "Arrange the bindings on an input",
            body: "<p>An input can have more than one binding, each with its own actions.</p>"
                + "<ul>"
                + "<li>Type a <b>Note</b> in the binding's header. It shows on the input's row.</li>"
                + "<li>Drag a binding by its handle to change the order.</li>"
                + "<li>To remove a binding, choose the remove button in its header (\"Remove this binding and all its actions\"). A binding with actions asks first: \"Remove this binding?\" says how many actions go with it, and the red <b>Remove Binding</b> removes it. This can't be undone.</li>"
                + "<li>Each action has its own label box. A label you leave blank stays blank.</li>"
                + "</ul>"
                + _good([
                    "On a button, actions that allow it have switches for press and release. With both off, the action shows \"Off: never runs\"."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-treat-as"]
        },
        {
            id: "device-bindings-actions-treat-as",
            section: page,
            title: "Treat an axis or hat as a button",
            body: "<p><b>Treat as</b> in a binding's header lets an axis or a hat fire button actions. A button or a key has no Treat as.</p>"
                + "<ol>"
                + "<li>Choose <b>Treat as</b> <b>Button</b>. The binding now offers the button actions in <b>Add Action</b>.</li>"
                + "<li>For an axis, set <b>Activate between</b> and <b>when entered from</b> (<b>Anywhere</b>, <b>Above</b> or <b>Below</b>). Entering the range presses; leaving it releases.</li>"
                + "<li>For a hat, pick the directions under <b>Activate on</b>. Any of them presses the button.</li>"
                + "</ol>"
                + _good([
                    "To go back, choose <b>Treat as</b> <b>Axis</b> or <b>Hat</b>.",
                    "Changing Treat as either way on a binding that has actions asks first (\"Treat as Button?\", \"Treat as Axis?\" or \"Treat as Hat?\") and says how many actions the change removes. The red <b>Change and Remove</b> changes it and removes those actions. This can't be undone.",
                    "An axis already inside the range when you choose <b>Run</b> gives no press until it leaves and comes back."
                ]),
            related: ["device-bindings-actions-bindings", "device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-safety-net",
            section: page,
            title: "Unfinished actions and recovery copies",
            body: "<p>An action with a problem shows a warning or error icon on its row. Point at the icon to see why.</p>"
                + "<ul>"
                + "<li>A warning still runs. An error means the action is not finished.</li>"
                + "<li>Before saving, \"Unfinished Actions\" lists them, each with its first error, and says they will be left out of the saved profile. Choose <b>Save without them</b> to save the rest, or <b>Cancel</b> to go back and finish them.</li>"
                + "<li><b>Run</b> skips unfinished actions.</li>"
                + "</ul>"
                + "<h4>Unsaved edits after the program closed unexpectedly</h4>"
                + "<p>While a profile has unsaved changes, the program keeps a recovery copy of them about every minute, in the recovery folder inside the data folder (<b>File › Open Data Folder</b> <a href=\"show:menu/File/Open Data Folder\">Show me ›</a>). A profile that was never saved gets one too. Saving, <b>Discard</b> and closing the program normally remove it.</p>"
                + "<p>If the program closed with unsaved changes, the next time that profile opens (or when the program starts again), \"Unsaved Edits Found\" says \"The profile <i>name</i> has edits from <i>date</i> at <i>time</i> that were never saved, probably because the program closed unexpectedly.\"</p>"
                + "<ul>"
                + "<li><b>Restore</b> opens the edits. Save the profile to keep them (<b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a>).</li>"
                + "<li><b>Discard</b> deletes them.</li>"
                + "<li><b>Not now</b> keeps them to be offered again later.</li>"
                + "</ul>"
                + _good([
                    "A Play Sound or Load Profile action whose file is missing is kept with a warning. Pressing it does nothing until the file is back or you choose another.",
                    "A profile with an action this program doesn't know still opens. A message names it; the action is kept and saved as it was, but does nothing."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-q-not-kept",
                      "device-bindings-actions-play-sound", "device-bindings-actions-load-profile"]
        },
        {
            id: "device-bindings-actions-delete-action",
            section: page,
            title: "Delete an action",
            body: "<p>Deleting an action takes it off the input in the current mode.</p>"
                + "<ol>"
                + "<li>Open the device's Device Bindings page.</li>"
                + "<li>Right-click the action's row and choose <b>Delete</b>.</li>"
                + "<li>The question \"Delete action <i>action</i>?\" says it goes from this input in this mode. Choose the red <b>Delete Action</b>.</li>"
                + "</ol>"
                + _good([
                    "<b>Cancel</b> has the focus: <b>Enter</b> and <b>Esc</b> both cancel.",
                    "If the editor is open on that input with changes that are not saved, the question says so: deleting closes the editor and drops those changes.",
                    "To delete every action of an input in this mode, right-click the input and choose <b>Row</b> › <b>Delete actions…</b>.",
                    "To take the delete back, choose <b>Undo</b> (<b>Ctrl+Z</b>). Saved deletes can also be put back from History.",
                    "The profile on disk changes only when you save it."
                ]),
            related: ["device-bindings-actions-undo", "device-bindings-actions-add-action", "device-bindings-actions-menus"]
        },
        {
            id: "device-bindings-actions-undo",
            section: page,
            title: "Undo a change on the Device Bindings page",
            body: "<p><b>Undo</b> and <b>Redo</b> step back and forward through what <b>OK</b> and <b>Delete</b> changed, and through changes to groups, order and names.</p>"
                + "<ul>"
                + "<li>Choose <b>Undo</b> or <b>Redo</b> under the Find bar, or beside the right-click menu's title. Or press <b>Ctrl+Z</b>, and <b>Ctrl+Y</b> or <b>Ctrl+Shift+Z</b>.</li>"
                + "<li>Beside them, \"Last change: <i>change</i>\" names the newest change, or \"Undone: <i>change</i>\" after an Undo. Pointing at a button names the change it takes back or does again.</li>"
                + "</ul>"
                + _good([
                    "Opening another device clears every step. Loading another profile keeps the steps for groups, order and names.",
                    "Undo and Redo wait while an action is open in the editor.",
                    "If a step can't be played, it stays in the list and a notice says \"That change couldn't be put back.\"",
                    "Saved changes are also kept in the <a href=\"topic:tools-history\">History</a> (<b>Tools › History</b> <a href=\"show:menu/Tools/History\">Show me ›</a>)."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-delete-action", "tools-history"]
        },
        {
            id: "device-bindings-actions-keyboard-page",
            section: page,
            title: "Set up keyboard keys",
            body: "<p>The <b>Keyboard</b> page lists the keys you added and the actions on each. It works like the Device Bindings page: the same Find bar, list, right-click menus, action editor and Undo.</p>"
                + "<ol>"
                + "<li>Double-click the <b>Keyboard</b> card on Home.</li>"
                + "<li>Choose <b>Add Key…</b> on the Find bar (or right-click and choose <b>Add Inputs</b> › <b>Add Key… (press the key)</b>), then press the key. Hold <b>Esc</b> to stop.</li>"
                + "<li>Click the key's row to open its actions in the editor beside the list, or right-click it and choose <b>Add Action</b>.</li>"
                + "<li>Choose <b>OK</b>.</li>"
                + "</ol>"
                + _good([
                    "The keys you add are kept in the Keyboard's module file, so every profile lists them, with or without actions. The key list, groups, order and names are saved at <b>File › Save Profile</b>.",
                    "Right-click a key and choose <b>Key</b> › <b>Delete</b>. It asks first (\"Delete key A?\", \"Its actions in this mode go with it.\"); the red <b>Delete Key</b> removes only its actions in this mode, and a key left with no actions in any mode leaves the list. <b>Undo</b> puts it back. Delete is offered only on keys with actions in this mode, or with none in any mode.",
                    "To give a key a name of your own, right-click it and choose <b>Rename</b>; <b>Key</b> › <b>Clear Name</b> removes it. This is the key's name in the Keyboard's Module Setup too. The key's <b>Note</b> shows on its row.",
                    "<b>Undo</b> and <b>Redo</b> step through OK, Delete, Add Key and changes to groups, order and names, as on the Device Bindings page.",
                    "Groups and <b>Order</b> (<b>By Key Name</b>, <b>By Your Name</b>, <b>Group Names A to Z</b>) work as on the Device Bindings page; see " + _link("layout", "Group, order and name inputs") + ".",
                    "A key binding fires only for keys the Keyboard <a href=\"topic:home-devices-input-modules\">input module</a> claims."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-map-to-keyboard",
                      "device-bindings-actions-layout", "device-bindings-actions-menus"]
        },
        {
            id: "device-bindings-actions-output-view",
            section: page,
            title: "Output View",
            body: "<p>A vJoy output device opens its <b>Output View</b> in place of a Device Bindings page: a live view of what its output module sends. The Xbox card's <b>Output View</b> shows a section for each Xbox pad that is on and bound: its live picture, the devices that drive it, and, for each Xbox control, what sends to it.</p>"
                + "<p>You don't edit bindings here: it shows what the input modules' actions send. To change one, open the input device's Device Bindings page.</p>"
                + _good([
                    "A wire to an output the output module doesn't claim is shown as <b>(not claimed)</b> and sends nothing."
                ]),
            related: ["device-bindings-actions-device-bindings-page", "device-bindings-actions-appearance",
                      "device-bindings-actions-map-to-vjoy", "device-bindings-actions-map-to-xbox"]
        },
        {
            id: "device-bindings-actions-appearance",
            section: page,
            title: "Change how a page looks",
            body: "<p>Appearance changes how a page looks, never what it does.</p>"
                + "<ol>"
                + "<li>On the page, choose <b>Appearance…</b> (on a list page it is on the bar under the toolbar and in the right-click menu). Changes show at once.</li>"
                + "<li>Change the sections you want. <b>Open All</b> and <b>Close All</b> expand or fold them.</li>"
                + "<li>Choose <b>Save Appearance</b> to keep the changes.</li>"
                + "</ol>"
                + "<h4>List pages</h4>"
                + "<p>The Device Bindings, Logical Device, Keyboard and OSC pages and the Xbox 360 Controller's Output View each keep their own Appearance, saved for that page in the program settings (\"Saved for this page.\").</p>"
                + "<p>On the Device Bindings page the Appearance is kept for each device: <b>Save Appearance</b> saves the look of the device shown only. A device with no look of its own uses the shared Device Bindings look. <b>Apply to all devices</b> (next to Save Appearance, on this page only) makes the shown look the shared one and clears every device's own look, so all devices show it.</p>"
                + "<p>Sections: <b>Shown</b>, <b>Bindings</b> (<b>Show bindings</b> and the look of the \"Bindings [n]\" count and target boxes after each row's name: sizes, fonts, colors, border, square or rounded corners, spacing, with its own reset; not on the Xbox list), <b>Live</b> (Device Bindings page), <b>Handles</b>, <b>List</b>, <b>Rows</b> (alignment and width of input and action rows, space between groups), <b>Group</b>, <b>Parent Row</b> and <b>Action Row</b> (row size, padding, colors), <b>Text</b> and <b>Selection</b>.</p>"
                + "<h4>Output View</h4>"
                + "<p>An Output View's look is saved in that device's <a href=\"topic:home-devices-module-files\">module file</a>. Sections: <b>Screen</b>, <b>Layout</b>, <b>Pads</b>, <b>Meters</b>, <b>Buttons</b> and <b>Colors</b>.</p>"
                + _good([
                    "<b>Reset Appearance</b> (red) puts back the look the program starts with. On the Device Bindings page it resets the device shown only, and keeps that as the device's own look. On an Output View, <b>Copy Appearance from…</b> copies another output device's look; there, both still need Save Appearance.",
                    "When the window is too narrow for the list, the action editor and the Appearance panel side by side, the Appearance panel closes. Choose <b>Appearance…</b> to open it again.",
                    "Closing the panel with changes that are not saved asks first (\"Appearance changes are not saved.\")."
                ]),
            related: ["device-bindings-actions-device-bindings-page", "device-bindings-actions-output-view",
                      "logical-device-appearance"]
        },

        // ---- Actions ----
        {
            id: "device-bindings-actions-choose-action",
            section: actions,
            title: "Choose an action",
            body: "<p><b>Add Action</b> lists the actions that suit the input type: axis, button, hat or key.</p>"
                + "<ul>"
                + "<li>Container actions (Condition, Chain, Double Tap, Tempo, Smart Toggle, Split Axis, Merge Axis, Dual Axis Deadzone, Axis Delta, Hat as Buttons) hold other actions. Add the container first, then the actions inside it.</li>"
                + "<li>Every other action does one thing, such as " + _link("map-to-vjoy", "Map to vJoy") + " or " + _link("map-to-keyboard", "Map to Keyboard") + ".</li>"
                + "</ul>"
                + _good([
                    "<b>Actions offered</b> <a href=\"show:option/Actions offered\">Show me ›</a> in <a href=\"topic:options-profile-options\">Options</a> sets the order of the list and can hide actions you never use.",
                    "<b>Map to vJoy</b> is offered only when a vJoy device can be an output."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-right-click", "device-bindings-actions-reference", "options-profile-options"]
        },
        {
            id: "device-bindings-actions-map-to-vjoy",
            section: actions,
            title: "Map to vJoy",
            body: "<p>Sends the input to a vJoy axis, button or hat.</p>"
                + "<ol>"
                + "<li>Pick the vJoy device by its output module name, then the output. Picking another vJoy device keeps the same output if that device claims it, otherwise it takes that device's first claimed output of the same kind.</li>"
                + "<li>For an axis, choose <b>Absolute</b>, or <b>Relative</b> with <b>Speed</b>: the axis moves while the input is held off-center.</li>"
                + "<li>For a button, tick <b>Invert activation</b>.</li>"
                + "</ol>"
                + _good([
                    "A Relative axis stops when the input rests for 1 second, or when something else moves that vJoy axis.",
                    "Only outputs claimed by the vJoy output module are sent. An output the program can't send (not claimed, not on that vJoy device, or that vJoy turned off) shows in red as <b>⚠</b> and its name, for example <b>⚠ Button 57</b>. Hover it to see why, for example \"vJoy 1's Button 57 is not Found (vJoy 1 has Buttons 1–56).\" or \"vJoy 2 is not Found.\"",
                    "To fix it, pick another output from the list: it offers only what the vJoy output module includes. To send to that output instead, claim it in <a href=\"topic:home-devices-vjoy-output\">Output Module Setup</a> (<b>Tools › Device Setup › Output Module Setup</b> <a href=\"show:menu/Tools/Device Setup/Output Module Setup\">Show me ›</a>).",
                    "A new Map to vJoy starts on the first claimed output this mode doesn't use yet. When every claimed output is used, it starts on the first one.",
                    "The output list offers only claimed outputs the vJoy device really has."
                ]),
            related: ["device-bindings-actions-map-to-xbox", "device-bindings-actions-map-to-logical-device",
                      "home-devices-vjoy-output"]
        },
        {
            id: "device-bindings-actions-map-to-xbox",
            section: actions,
            title: "Map to Xbox",
            body: "<p>Sends the input to the virtual Xbox 360 controller. There is nothing to claim.</p>"
                + "<ul>"
                + "<li><b>Xbox</b>: the pad: the pads that are on in <b>Xbox Setup</b> (Xbox 360 Controller is pad 1), plus the pad the action already uses.</li>"
                + "<li><b>Target</b>: the controls that fit the input. An axis drives sticks and triggers; a button or key drives buttons and triggers; a hat drives the D-pad, buttons and sticks.</li>"
                + "<li>Axis on a trigger: <b>Full axis</b> (−1 → 0%, +1 → 100%) or <b>Upper half</b> (center → 0%).</li>"
                + "<li>Button: <b>Invert activation</b>.</li>"
                + "</ul>"
                + _good([
                    "A button, key or hat on a trigger pulls it fully while pressed and lets go on release. A hat on a stick moves it in the hat's direction.",
                    "A target saved earlier that no longer fits stays in the list and still works.",
                    "A pad that is off in <b>Xbox Setup</b> shows a red ⚠ and isn't sent to; turn it on there or pick a pad that is on.",
                    "Map to Xbox needs the <b>ViGEmBus</b> driver; see <a href=\"topic:home-devices-xbox-output\">Xbox output module</a>. Without it the action shows a warning (\"ViGEmBus / ViGEmClient.dll not available.\") and stays in the profile.",
                    "To send a Logical Device control to Xbox, see " + "<a href=\"topic:logical-device-send-to-xbox-vjoy\">Send a control to Xbox or vJoy</a>" + "."
                ]),
            related: ["device-bindings-actions-map-to-vjoy", "logical-device-send-to-xbox-vjoy", "home-devices-xbox-output"]
        },
        {
            id: "device-bindings-actions-map-to-logical-device",
            section: actions,
            title: "Map to Logical Device",
            body: "<p>Sends the input to a control on the Logical Device.</p>"
                + "<ol>"
                + "<li>Pick a logical control of the same type.</li>"
                + "<li>For an axis, choose <b>Absolute</b>, or <b>Relative</b> with <b>Speed</b>.</li>"
                + "<li>For a button, tick <b>Invert activation</b> if you need it.</li>"
                + "</ol>"
                + _good([
                    "<b>Assign Hardware</b> on the Logical Device (<b>Tools › Mapping › Logical Device</b> <a href=\"show:menu/Tools/Mapping/Logical Device\">Show me ›</a>) creates these actions for you.",
                    "On a Logical Device control, the list never offers that same control, and a new action never starts on it. If it is the only control of its type, a new one is made for the action.",
                    "A saved action that sends a control to itself shows that control selected, marked \"(this control: blocked by the loop guard)\". It does nothing when the profile runs; pick another control.",
                    "A loop between controls is stopped; see " + "<a href=\"topic:logical-device-q-loop\">Why was a loop between controls stopped?</a>" + "."
                ]),
            related: ["logical-device-assign-hardware", "logical-device-about", "logical-device-q-loop"]
        },
        {
            id: "device-bindings-actions-map-to-keyboard",
            section: actions,
            title: "Map to Keyboard",
            body: "<p>Holds the recorded keys while the input is held and releases them when it is released.</p>"
                + "<ol>"
                + "<li>Choose <b>Record Keys</b>.</li>"
                + "<li>Press the keys for the <b>Key Combination</b>.</li>"
                + "</ol>"
                + _good([
                    "Modifiers (Shift, Ctrl, Alt and Win) are pressed first, then the other keys in the order you pressed them when recording."
                ]),
            related: ["device-bindings-actions-macro", "device-bindings-actions-keyboard-page"]
        },
        {
            id: "device-bindings-actions-map-to-mouse",
            section: actions,
            title: "Map to Mouse",
            body: "<p>Clicks a mouse button or moves the pointer. Choose the <b>Mode</b>:</p>"
                + "<ul>"
                + "<li><b>Button</b> clicks a recorded mouse button. Wheel Up and Wheel Down are included and are sent once per press.</li>"
                + "<li><b>Motion</b> moves the pointer. On a button, set <b>Minimum speed</b>, <b>Maximum speed</b>, <b>Time to maximum speed</b> and <b>Direction</b>. On an axis, set <b>Control motion of</b> to X Axis or Y Axis.</li>"
                + "</ul>"
                + _good([
                    "Motion from several inputs adds up: two buttons pushing right move the pointer faster, and left and right cancel out.",
                    "Each button or hat speeds up on its own, from its <b>Minimum speed</b> to its <b>Maximum speed</b>.",
                    "A mode change, <b>Pause</b> and <b>Stop</b> all stop the pointer. After a mode change it moves on only if the new mode moves the mouse with the same input.",
                    "With Tracing on, the Trace tab shows one line per change, such as \"Mouse motion 400 px/s heading 90°\", \"Mouse motion stopped\", \"Mouse Left = pressed\" or \"Mouse wheel up\".",
                    "Mouse buttons are for sending only. They can be recorded here and in a macro, but a running profile never reads the mouse, so a mouse button can't fire actions."
                ]),
            related: ["device-bindings-actions-macro"]
        },
        {
            id: "device-bindings-actions-macro",
            section: actions,
            title: "Macro",
            body: "<p>Plays a list of steps: Joystick, Keyboard, Logical Device, Mouse Button, Mouse Motion, Pause and vJoy.</p>"
                + "<ul>"
                + "<li>To add steps one at a time, choose <b>Add Step</b>.</li>"
                + "<li>To record them, choose <b>Record Inputs</b>, pick what to record (Keyboard, Mouse, Axis, Button, Hat and Timings), then start and stop the recording.</li>"
                + "<li><b>Repeat Mode</b>: Single, Count, Toggle or Hold, with a delay between repeats.</li>"
                + "<li><b>Exclusive</b> waits for running macros, then blocks others; <b>Pre-Emptive</b> pauses them instead.</li>"
                + "</ul>"
                + _good([
                    "A Joystick step acts like the stick itself: it only does something for controls the stick's input module claims.",
                    "New Joystick, Keyboard, Logical Device, Mouse Button and vJoy button steps start on <b>Pressed</b>.",
                    "A new vJoy step starts on the first output a vJoy output module claims. If none is claimed, the step is added with the notice \"Claim an output on a vJoy output module first.\"",
                    "A step the program can't read shows as <b>Unreadable step</b>, for example \"Unknown step type 'X': kept as it was, does nothing.\" It does nothing when the macro plays, and saving keeps it unchanged. You can remove it.",
                    "Mouse buttons can be recorded as steps, but a mouse button is never an input of its own; see " + _link("map-to-mouse", "Map to Mouse") + ".",
                    "Where there is no Pause step, the macro waits between steps for <b>Macro Default Delay</b> in <a href=\"topic:options-profile-profile-settings\">Profile Settings</a> (<b>View › Profile Settings</b> <a href=\"show:menu/View/Profile Settings\">Show me ›</a>). Unless the profile sets its own, that is <b>Default delay</b> <a href=\"show:option/Default delay\">Show me ›</a> in Options."
                ]),
            related: ["device-bindings-actions-map-to-keyboard", "device-bindings-actions-map-to-mouse", "options-profile-profile-settings"]
        },
        {
            id: "device-bindings-actions-response-curve",
            section: actions,
            title: "Response Curve",
            body: "<p>Reshapes an axis before the actions after it.</p>"
                + "<ol>"
                + "<li>Choose <b>Piecewise Linear</b>, <b>Cubic Spline</b> or <b>Cubic Bezier Spline</b>.</li>"
                + "<li>Drag the points, or type <b>X</b> and <b>Y</b>.</li>"
                + "<li>Set the <b>Deadzone</b>.</li>"
                + "</ol>"
                + _good([
                    "The curve passes through every point you set. On a <b>Cubic Bezier Spline</b>, each point's handles bend the curve between the points.",
                    "<b>Invert Curve</b> flips the curve.",
                    "<b>Symmetric</b> mirrors your edits around the center."
                ]),
            related: ["device-bindings-actions-dual-axis-deadzone", "device-bindings-actions-split-axis"]
        },
        {
            id: "device-bindings-actions-split-axis",
            section: actions,
            title: "Split Axis",
            body: "<p>Splits one axis at <b>Split axis at</b> into a lower or left part and an upper or right part, each with its own action list.</p>"
                + _good(["Each part is rescaled to the full range."]),
            related: ["device-bindings-actions-merge-axis", "device-bindings-actions-response-curve"]
        },
        {
            id: "device-bindings-actions-merge-axis",
            section: actions,
            title: "Merge Axis",
            body: "<p>Combines two axes into one value for the actions in its <b>Actions</b> list.</p>"
                + "<ol>"
                + "<li>Pick or create a <b>Merge axis instance</b>.</li>"
                + "<li>Pick the <b>First axis</b> and <b>Second axis</b>.</li>"
                + "<li>Choose the <b>Merge operation</b>: Average, Minimum, Maximum, Sum, Bidirectional, Prefer Center or Maximum Deflection.</li>"
                + "</ol>"
                + _good([
                    "A new Merge Axis starts on its own instance, named \"Merge Axis 1\" (or the next free number).",
                    "The <b>+</b> button beside the list makes a new merge axis instance and selects it. The pencil renames it.",
                    "The list offers the one you are editing, a new one, and those other inputs use; never deleted ones.",
                    "Picking one another input uses shares it: it keeps its own name.",
                    "<b>Maximum Deflection</b> uses whichever axis is furthest from center; when both are equally far, the second axis wins."
                ]),
            related: ["device-bindings-actions-split-axis", "device-bindings-actions-dual-axis-deadzone"]
        },
        {
            id: "device-bindings-actions-dual-axis-deadzone",
            section: actions,
            title: "Dual Axis Deadzone",
            body: "<p>Applies one deadzone to a pair of axes, such as a stick's X and Y: a circular <b>Inner</b> deadzone and a square <b>Outer</b> limit.</p>"
                + "<ol>"
                + "<li>Pick or create a <b>Deadzone instance</b>.</li>"
                + "<li>Pick the two axes.</li>"
                + "<li>Add the actions for each axis's result to its own action list.</li>"
                + "</ol>"
                + _good([
                    "A new Dual Axis Deadzone starts on its own instance, named \"Dual Axis Deadzone 1\" (or the next free number).",
                    "The <b>+</b> button beside the list makes a new deadzone instance and selects it. The pencil renames it.",
                    "The list offers the one you are editing, a new one, and those other inputs use; never deleted ones.",
                    "Picking one another input uses shares it: it keeps its own name."
                ]),
            related: ["device-bindings-actions-response-curve", "device-bindings-actions-merge-axis"]
        },
        {
            id: "device-bindings-actions-axis-delta",
            section: actions,
            title: "Axis Delta",
            body: "<p>Turns axis movement into button presses. Each time the axis moves by <b>Change threshold</b>, it pulses the actions under <b>Positive change</b> or <b>Negative change</b>.</p>"
                + _good([
                    "A new Axis Delta starts with the <b>Threshold</b> <a href=\"show:option/Threshold\">Show me ›</a> set in Options under <b>Axis Delta</b>."
                ]),
            related: ["device-bindings-actions-split-axis"]
        },
        {
            id: "device-bindings-actions-condition",
            section: actions,
            title: "Condition",
            body: "<p>Runs one action list when its conditions are true and another when they are false.</p>"
                + "<ol>"
                + "<li>Choose <b>Any</b> or <b>All</b>.</li>"
                + "<li>Choose <b>Add Condition</b> and pick its kind: Joystick, Keyboard, Current Input, vJoy or Logical Device state.</li>"
                + "<li>Add the actions for true and for false.</li>"
                + "</ol>"
                + _good([
                    "A condition reads inputs through their input module: an input the module doesn't claim reads as at rest.",
                    "A condition on a stick plugged in later works once it is connected.",
                    "New button and key conditions start on <b>Pressed</b>.",
                    "A new vJoy condition starts on the first output a vJoy output module claims. If none is claimed, it isn't added and the notice says \"Claim an output on a vJoy output module first.\""
                ]),
            related: ["device-bindings-actions-chain", "device-bindings-actions-tempo"]
        },
        {
            id: "device-bindings-actions-chain",
            section: actions,
            title: "Chain",
            body: "<p>Each press runs the next <b>Sequence</b> in turn.</p>"
                + "<ul>"
                + "<li><b>Add Chain Sequence</b> adds a sequence.</li>"
                + "<li>After <b>Timeout (sec, 0 = never)</b> without a press, it starts again at the first sequence.</li>"
                + "</ul>",
            related: ["device-bindings-actions-double-tap", "device-bindings-actions-condition"]
        },
        {
            id: "device-bindings-actions-double-tap",
            section: actions,
            title: "Double Tap",
            body: "<p>Gives a single tap and a double tap their own actions. Two taps within <b>Double-tap threshold (sec)</b> count as a double tap.</p>"
                + "<ul>"
                + "<li><b>exclusive</b> waits to see if a second tap comes.</li>"
                + "<li><b>combined</b> runs the single-tap actions on every press.</li>"
                + "</ul>"
                + _good([
                    "A new Double Tap starts with the <b>Duration</b> <a href=\"show:option/Double Tap duration\">Show me ›</a> set in Options under <b>Double Tap</b>."
                ]),
            related: ["device-bindings-actions-tempo", "device-bindings-actions-chain"]
        },
        {
            id: "device-bindings-actions-tempo",
            section: actions,
            title: "Tempo",
            body: "<p>Gives a <b>Short press</b> and a <b>Long press</b> their own actions. A press longer than <b>Long-press threshold (sec)</b> is a long press.</p>"
                + "<ul><li><b>Activate on</b> sets whether the actions run on press or on release.</li></ul>"
                + _good([
                    "A new Tempo starts with the <b>Duration</b> <a href=\"show:option/Tempo duration\">Show me ›</a> set in Options under <b>Tempo</b>."
                ]),
            related: ["device-bindings-actions-double-tap", "device-bindings-actions-smart-toggle"]
        },
        {
            id: "device-bindings-actions-smart-toggle",
            section: actions,
            title: "Smart Toggle",
            body: "<p>A quick press, released within <b>Hold time (sec)</b>, latches its actions on until the next press. A longer hold acts only while held.</p>"
                + _good([
                    "A new Smart Toggle starts with the <b>Duration</b> <a href=\"show:option/Smart Toggle duration\">Show me ›</a> set in Options under <b>Smart Toggle</b>."
                ]),
            related: ["device-bindings-actions-tempo"]
        },
        {
            id: "device-bindings-actions-hat-as-buttons",
            section: actions,
            title: "Hat as Buttons",
            body: "<p>Gives each hat direction its own action list. Set <b>Button mode</b> to <b>4 way</b> or <b>8 way</b>.</p>"
                + _good([
                    "Switching from 8 way to 4 way asks first when the diagonal directions have actions, and removes them on <b>Switch to 4 way</b>."
                ]),
            related: ["device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-change-mode",
            section: actions,
            title: "Change Mode",
            body: "<p>Changes the running mode. Choose one:</p>"
                + "<ul>"
                + "<li><b>Switch</b> to a mode.</li>"
                + "<li><b>Previous</b> mode.</li>"
                + "<li><b>Unwind</b> one step.</li>"
                + "<li><b>Cycle</b> through a list.</li>"
                + "<li><b>Temporary</b>: only while held.</li>"
                + "</ul>"
                + _good([
                    "Cycle's first press moves to the mode after the current one, or to the first in the list if the current mode isn't in it. Deleted modes are skipped.",
                    "Modes are added, renamed and deleted in <b>Manage Modes</b> <a href=\"show:modebar/Manage Modes\">Show me ›</a>. Renaming a mode updates the Change Mode actions that name it.",
                    "<b>Mode cycle resolution</b> <a href=\"show:option/Mode cycle resolution\">Show me ›</a> decides where a loop back to an earlier mode lands."
                ]),
            related: ["device-bindings-actions-load-profile", "modes-modes", "modes-manage"]
        },
        {
            id: "device-bindings-actions-load-profile",
            section: actions,
            title: "Load Profile",
            body: "<p>Loads another profile file when the input fires. Set <b>Profile filename</b>, or choose <b>Select File</b>.</p>"
                + _good([
                    "While the profile runs, it stops, loads the new profile and runs it.",
                    "It doesn't load over unsaved changes: a notice, \"Load Profile Waited\", asks you to save or discard them first.",
                    "If the file is missing, nothing is loaded and a notice says so. A profile whose Load Profile file is missing still opens; the action shows a warning."
                ]),
            related: ["device-bindings-actions-change-mode", "getting-started-run"]
        },
        {
            id: "device-bindings-actions-pause-and-resume",
            section: actions,
            title: "Pause and Resume",
            body: "<p>Choose <b>Pause</b>, <b>Resume</b> or <b>Toggle</b> to stop or restart the processing of all actions.</p>"
                + _good([
                    "While paused, the status reads Running (Paused).",
                    "Pause and Resume actions keep working while paused, so you can resume.",
                    "Each <b>Run</b> starts un-paused.",
                    "A saved Pause and Resume action whose choice the program can't read loads as <b>Pause</b>; the system log says so."
                ]),
            related: ["device-bindings-actions-change-mode"]
        },
        {
            id: "device-bindings-actions-play-sound",
            section: actions,
            title: "Play Sound",
            body: "<p>Plays a WAV, MP3 or OGG file at the chosen <b>Volume</b>. Type the file's path in the box that says \"File to play\", or pick the file.</p>"
                + _good([
                    "<b>Playback mode</b> <a href=\"show:option/Playback mode\">Show me ›</a> sets what happens when sounds overlap: <b>Sequential</b> plays them one after another, <b>Interrupt</b> stops the one playing, <b>Overlap</b> plays them together.",
                    "Sounds play only while the profile runs. <b>Stop</b> cuts them off.",
                    "A missing file shows a warning; pressing the input plays nothing."
                ]),
            related: ["device-bindings-actions-text-to-speech"]
        },
        {
            id: "device-bindings-actions-text-to-speech",
            section: actions,
            title: "Text to Speech",
            body: "<p>Speaks the text you type. You can put it on a button or a keyboard key.</p>"
                + "<ol>"
                + "<li>Type the text.</li>"
                + "<li>Choose <b>Interrupt</b>, <b>Queue Front</b> or <b>Queue Back</b>.</li>"
                + "<li>Set <b>Volume</b>, <b>Rate</b> and <b>Pitch</b>.</li>"
                + "</ol>"
                + _good([
                    "Typing ${current_mode} in the text speaks the current mode's name.",
                    "Speech plays only while the profile runs. <b>Stop</b> cuts it off.",
                    "Choose the voice in Options under <b>Text to Speech</b> <a href=\"show:option/Voice selection\">Show me ›</a>. If that voice is no longer installed, the Windows default voice speaks."
                ]),
            related: ["device-bindings-actions-play-sound"]
        },
        {
            id: "device-bindings-actions-send-osc",
            section: actions,
            title: "Send OSC",
            body: "<p>Sends an OSC message, for example to light a Stream Deck key or move a fader in another program. You can put it on a button, a key or an axis.</p>"
                + "<ol>"
                + "<li>Choose the <b>Target</b>: one of OSC's targets, or <b>Reply to sender</b> (the IP address and port of the last message received).</li>"
                + "<li>Type the <b>Address</b>. It starts with \"/\".</li>"
                + "<li>Under <b>Values</b>, each value is <b>Fixed</b> (sent as typed) or <b>Input value</b> (the input's own value: 1 or 0 for a button, and for an axis a number between <b>Min:</b> and <b>Max:</b>, 0 and 1 unless you change them). A new action has one Input value. <b>Add Value</b> adds a Fixed value; the remove button beside a value removes it.</li>"
                + "<li>Choose each value's type: <b>Auto</b> (the type last received on that address, else Float), <b>Int</b>, <b>Float</b>, <b>Bool</b> or <b>Text</b>.</li>"
                + "<li>On a button or key, choose whether it sends on press, on release or both.</li>"
                + "</ol>"
                + _good([
                    "It sends only while the profile runs, and only while <b>OSC output (Send OSC actions and feedback)</b> is on in OSC's Module Setup (<b>Output</b> tab).",
                    "A target that was removed shows as <b>Missing target</b>: pick another one. An address that doesn't start with \"/\" shows \"An OSC address starts with /.\"",
                    "Every message it sends shows in the OSC Monitor (<b>Tools › OSC Monitor</b> <a href=\"show:menu/Tools/OSC Monitor\">Show me ›</a>) as <b>Out</b>.",
                    "Targets are set on the <b>Output</b> tab of <b>OSC Setup…</b>; see <a href=\"topic:osc-output-tab\">Output tab</a>.",
                    "Value types and the exact type codes sent: <a href=\"topic:osc-value-types\">OSC value types</a> and <a href=\"topic:osc-tech-out\">OSC values the program sends</a>."
                ]),
            related: ["osc-output-tab", "osc-value-types", "osc-send", "options-profile-osc"]
        },
        {
            id: "device-bindings-actions-run-command",
            section: actions,
            title: "Run Command",
            body: "<p>Starts a program. Set the <b>Executable</b> and its <b>Arguments</b>.</p>"
                + _good([
                    "Arguments are split on spaces; put quotes around values that contain spaces. The empty box says \"Quote values with spaces\"; point at it for the full hint.",
                    "The program runs with your own permissions.",
                    "If the program can't be started, the log says so once and nothing else happens."
                ]),
            related: ["device-bindings-actions-load-profile"]
        },
        {
            id: "device-bindings-actions-description",
            section: actions,
            title: "Description",
            body: "<p>A note on the input. It does nothing when the input fires.</p>",
            related: ["device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-reference",
            section: actions,
            title: "Reference",
            body: "<p>Reuses an existing action of the same input type.</p>"
                + "<ol>"
                + "<li>Pick the action.</li>"
                + "<li>Share it, so both inputs use the same action, or duplicate it, to get an independent copy.</li>"
                + "</ol>"
                + _good([
                    "The list offers only actions you added. The hidden action that holds an input's actions is never listed.",
                    "A shared action's editor says <b>Shared with …</b> and names the other inputs. <b>OK</b> changes it for every input that uses it, and <b>Undo</b> puts it back for all of them."
                ]),
            related: ["device-bindings-actions-choose-action", "device-bindings-actions-undo"]
        },

        // ---- Common questions ----
        {
            id: "device-bindings-actions-q-cannot-edit",
            section: questions,
            title: "Why can't I change an action?",
            body: "<p>The profile is running. While it runs, the Device Bindings, Keyboard, OSC and Logical Device pages are locked (\"Profile running: stop it to edit\"). Choose <b>Stop</b> <a href=\"show:toolbar/Run\">Show me ›</a>, then edit; see <a href=\"topic:getting-started-run\">Run and Stop</a>.</p>",
            related: ["device-bindings-actions-add-action"]
        },
        {
            id: "device-bindings-actions-q-action-missing",
            section: questions,
            title: "Why is an action missing from the Add Action list?",
            body: "<p>The list shows only the actions that suit the input type, and <a href=\"topic:options-profile-options\">Options</a> › Actions › Add Action Menu › <b>Actions offered</b> <a href=\"show:option/Actions offered\">Show me ›</a> can hide actions.</p>",
            related: ["device-bindings-actions-choose-action"]
        },
        {
            id: "device-bindings-actions-q-not-kept",
            section: questions,
            title: "Why did my action not stay after I closed the program?",
            body: "<p><b>OK</b> keeps the action in the open profile only. Choose <b>File › Save Profile</b> <a href=\"show:menu/File/Save Profile\">Show me ›</a> (<b>Ctrl+S</b>) to write it to disk. If the program closed unexpectedly before you saved, the edits may be offered back; see <a href=\"topic:device-bindings-actions-safety-net\">Unfinished actions and recovery copies</a>.</p>",
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
            body: "<p>The program can't send to that output: the vJoy output module doesn't include it, the vJoy device doesn't have it, or that vJoy is turned off. Hover the output to see which. Pick another output from the list, which offers only what the module includes. The input's device card on Home says how many bindings can't be sent, and the Find tick <b>Can't be sent</b> lists them. To keep the output, claim it in <a href=\"topic:home-devices-vjoy-output\">Output Module Setup</a> (<b>Tools › Device Setup › Output Module Setup</b> <a href=\"show:menu/Tools/Device Setup/Output Module Setup\">Show me ›</a>).</p>",
            related: ["device-bindings-actions-map-to-vjoy"]
        },
        {
            id: "device-bindings-actions-q-same-action",
            section: questions,
            title: "How do I use the same action on two inputs?",
            body: "<p>Add a " + _link("reference", "Reference") + " action to the second input and share the first input's action.</p>",
            related: ["device-bindings-actions-reference"]
        }
    ]
}
