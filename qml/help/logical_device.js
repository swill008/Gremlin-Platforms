// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: the Logical Device.

.pragma library

var chapter = { id: "logical-device", title: "Logical Device" }

function _good(items) {
    return "<h4>Good to know</h4><ul><li>" + items.join("</li><li>") + "</li></ul>"
}

function _link(id, title) {
    return "<a href=\"topic:" + id + "\">" + title + "</a>"
}

function topics() {
    var main = "Logical Device"
    var questions = "Common questions"
    return [
        {
            id: "logical-device-about",
            section: main,
            title: "The Logical Device",
            body: "<p>The Logical Device is a virtual device inside the program. Physical inputs feed its buttons, axes and hats, and each of its controls has actions of its own. Use it to combine several physical controls before sending them on.</p>"
                + "<ul>"
                + "<li>To open it, choose <b>Logical Device</b> on the toolbar <a href=\"show:toolbar/Logical Device\">Show me ›</a>, or <b>Tools › Mapping › Logical Device</b> <a href=\"open:tools.logical\">Open ›</a>.</li>"
                + "<li>Controls are named by type and number: Button 1, Axis 1, Hat 1.</li>"
                + "<li>The path is: physical control › Assign Hardware › Logical Device control › its actions.</li>"
                + "</ul>"
                + _good([
                    "Editing is locked while the profile runs (\"Profile running: stop it to edit\").",
                    "Its values go back to neutral at Stop and at the start of each Run: axes at 0, buttons up, hats centred.",
                    "Its card shows on <a href=\"topic:home-devices-home\">Home</a> once it has a module file."
                ]),
            related: ["logical-device-add-controls", "logical-device-assign-hardware", "modes-modes",
                      "logical-device-send-to-xbox-vjoy"]
        },
        {
            id: "logical-device-add-controls",
            section: main,
            title: "Add buttons, axes and hats",
            body: "<p>Add the controls the Logical Device needs.</p>"
                + "<ol>"
                + "<li>Right-click empty space on the Logical Device page.</li>"
                + "<li>Open <b>Add Inputs</b>.</li>"
                + "<li>Next to <b>Buttons</b>, <b>Axes</b> or <b>Hats</b>, set how many (up to 180), then choose <b>Add</b>.</li>"
                + "</ol>"
                + _good([
                    "To take it back, choose <b>Undo</b> (<b>Ctrl+Z</b>).",
                    "A Device Pack import can add the inputs its wires need; <b>Undo Import</b> removes them again. See " + _link("home-devices-device-pack-import", "Put a Device Pack on a device") + "."
                ]),
            related: ["logical-device-about", "logical-device-rename-control", "logical-device-undo"]
        },
        {
            id: "logical-device-rename-control",
            section: main,
            title: "Rename a control",
            body: "<p>Give a control your own name beside its system name.</p>"
                + "<ol>"
                + "<li>Right-click the control and choose <b>Rename</b>.</li>"
                + "<li>Type the name, then press <b>Enter</b>.</li>"
                + "</ol>"
                + _good([
                    "<b>Hide system name</b> shows only your name.",
                    "To remove your name, right-click the control and choose <b>Row</b> › <b>Clear Name</b>. It asks first (\"Clear the name of Button 2?\"); the red <b>Clear Name</b> removes your name, and the system name stays."
                ]),
            related: ["logical-device-group-controls", "logical-device-menus"]
        },
        {
            id: "logical-device-delete-control",
            section: main,
            title: "Delete a control",
            body: "<p>Deleting removes a control from the Logical Device.</p>"
                + "<ol>"
                + "<li>Select the control. Shift-click to select several; the menu's title then counts them.</li>"
                + "<li>Right-click and choose <b>Row</b> › <b>Delete</b>.</li>"
                + "<li>The question \"Delete Button 2?\" (or \"Delete 3 rows?\") says its hardware links and its actions go with it. Choose the red <b>Delete Row</b>; for several rows the button says how many.</li>"
                + "</ol>"
                + _good(["<b>Cancel</b> has the focus: <b>Enter</b> and <b>Esc</b> both cancel.",
                         "To take it back, choose <b>Undo</b> (<b>Ctrl+Z</b>)."]),
            related: ["logical-device-undo", "logical-device-menus"]
        },
        {
            id: "logical-device-group-controls",
            section: main,
            title: "Group and order controls",
            body: "<p>Groups keep related controls together on the page.</p>"
                + "<ul>"
                + "<li>New group: right-click empty space, open <b>Groups</b>, type a name in <b>New Group</b>, then press <b>Enter</b>.</li>"
                + "<li>Put controls in a group: select them, right-click, open <b>Group</b>, then type a name in <b>Group as</b> or choose <b>Move to</b> a group.</li>"
                + "<li>Change a group: right-click its header and choose <b>Rename Group</b>, or open <b>Groups</b> for <b>Move Group Up</b>, <b>Move Group Down</b> or <b>Delete Group</b>. Delete Group asks first (\"Delete group Throttle?\"); its controls stay, in Ungrouped.</li>"
                + "<li>Fold a group: click its header.</li>"
                + "<li>Drag a control by its grey handle onto another control (top half = before, bottom half = after) or onto a group header. Drag a header to move the group.</li>"
                + "<li>Sort: right-click empty space, open <b>Order</b>, then choose <b>By System Name</b>, <b>By Your Name</b> or <b>Group Names A to Z</b>.</li>"
                + "</ul>",
            related: ["logical-device-find-control", "logical-device-menus"]
        },
        {
            id: "logical-device-find-control",
            section: main,
            title: "Find a control",
            body: "<p><b>Find</b> filters the list.</p>"
                + "<ul>"
                + "<li>Type a system name, your name or a group (<b>Ctrl+F</b> goes to the box). A line under it says \"N found\" or \"Nothing matches\"; <b>×</b> or <b>Esc</b> clears the typing.</li>"
                + "<li>Filter by type, Ungrouped, <b>No hardware writer</b> or <b>No actions in this mode</b>.</li>"
                + "<li><b>Clear</b> resets the filter. When nothing is listed, <b>Clear Filters</b> does the same.</li>"
                + "</ul>"
                + _good(["The hardware list in <b>Assign Hardware</b> has its own <b>Search</b> box, with the same \"N found\" line and <b>×</b>."]),
            related: ["logical-device-group-controls"]
        },
        {
            id: "logical-device-undo",
            section: main,
            title: "Undo a change on the Logical Device",
            body: "<p><b>Undo</b> and <b>Redo</b> step back and forward through changes to the controls and groups.</p>"
                + "<ul>"
                + "<li>Choose <b>Undo</b> or <b>Redo</b> under the Find filters, or beside the right-click menu's title.</li>"
                + "<li>Beside them, \"Last change: <i>change</i>\" names the newest change, or \"Undone: <i>change</i>\" after an Undo.</li>"
                + "<li>Or press <b>Ctrl+Z</b>, and <b>Ctrl+Y</b> or <b>Ctrl+Shift+Z</b>.</li>"
                + "</ul>"
                + _good([
                    "To see a control's saved changes, right-click it and choose <b>History</b>; see <a href=\"topic:tools-history\">History</a>."
                ]),
            related: ["logical-device-menus"]
        },
        {
            id: "logical-device-assign-hardware",
            section: main,
            title: "Feed a control from hardware",
            body: "<p><b>Assign Hardware</b> picks the physical controls that feed a Logical Device control.</p>"
                + "<ol>"
                + "<li>Right-click the control and choose <b>Assign Hardware</b>. It lists claimed physical controls of the same type (for a button, keyboard keys and OSC too).</li>"
                + "<li>Type in <b>Search</b> to filter the list.</li>"
                + "<li>Tick a control. It gets a " + _link("configuration-actions-map-to-logical-device", "Map to Logical Device") + " action in the current mode.</li>"
                + "</ol>"
                + "<p>The control then lists the source on a row under it (shown while <b>Show written by</b> is on in <b>Appearance…</b>). On that row an axis has absolute or relative and a scale; a button has <b>Invert</b>.</p>"
                + _good([
                    "To remove the link, untick the control.",
                    "Assign Hardware only picks what feeds the control; it never lists outputs. To send on, see " + _link("logical-device-send-to-xbox-vjoy", "Send a control to Xbox or vJoy") + "."
                ]),
            related: ["configuration-actions-map-to-logical-device", "logical-device-add-action",
                      "logical-device-send-to-xbox-vjoy"]
        },
        {
            id: "logical-device-add-action",
            section: main,
            title: "Add an action to a control",
            body: "<p>A Logical Device control has actions of its own, set up in the same editor as on the Configuration page.</p>"
                + "<ol>"
                + "<li>Right-click the control and choose <b>Add Action</b>. The action editor opens beside the list.</li>"
                + "<li>Choose the action, set it up, then choose <b>OK</b>.</li>"
                + "</ol>"
                + _good([
                    "To change an action, click its row. Right-click the row to <b>Open</b> or <b>Delete</b> it. Delete asks first (\"Delete action …?\"); the red <b>Delete Action</b> removes it, and <b>Undo</b> puts it back.",
                    "Actions belong to the current <a href=\"topic:modes-modes\">mode</a>."
                ]),
            related: ["configuration-actions-add-action", "configuration-actions-choose-action",
                      "logical-device-send-to-xbox-vjoy"]
        },
        {
            id: "logical-device-send-to-xbox-vjoy",
            section: main,
            title: "Send a control to Xbox or vJoy",
            body: "<p>A Logical Device control sends on to the Xbox controller or vJoy through an action, not through Assign Hardware.</p>"
                + "<ol>"
                + "<li>Right-click the control (for example Hat 1) and choose <b>Add Action</b>.</li>"
                + "<li>Choose <b>Map to Xbox</b> or <b>Map to vJoy</b>.</li>"
                + "<li>Pick the <b>Target</b> (a hat can drive the D-pad, a button or a stick), then choose <b>OK</b>.</li>"
                + "</ol>"
                + "<p>The whole path: physical control › Assign Hardware › Logical Device control › Map to Xbox › Xbox 360 Controller.</p>"
                + _good([
                    "Map to Xbox needs the <b>ViGEmBus</b> driver; see <a href=\"topic:home-devices-xbox-output\">Xbox output module</a>.",
                    "If Map to Xbox isn't in the list, <b>Actions offered</b> <a href=\"show:option/Actions offered\">Show me ›</a> in " + _link("options-profile-options", "Options") + " may hide it."
                ]),
            related: ["configuration-actions-map-to-xbox", "configuration-actions-map-to-vjoy",
                      "logical-device-assign-hardware"]
        },
        {
            id: "logical-device-appearance",
            section: main,
            title: "Change how the Logical Device page looks",
            body: "<p>Appearance changes how the page looks, never what it does.</p>"
                + "<ol>"
                + "<li>Choose <b>Appearance…</b> on the page or in its right-click menu.</li>"
                + "<li>Change the sections: <b>Shown</b>, <b>Handles</b>, <b>List</b>, <b>Group</b>, <b>Parent Row</b>, <b>Action Row</b>, <b>Text</b> and <b>Selection</b>.</li>"
                + "<li>Choose <b>Save Appearance</b>.</li>"
                + "</ol>"
                + _good([
                    "The look is saved for this page, in the program settings.",
                    "<b>Reset Appearance</b> restores the built-in look."
                ]),
            related: ["configuration-actions-appearance"]
        },
        {
            id: "logical-device-menus",
            section: main,
            title: "Logical Device menus",
            body: "<p>What each right-click menu on the Logical Device page holds.</p>"
                + "<ul>"
                + "<li>Empty space: <b>Appearance…</b>, then the sections <b>Add Inputs</b>, <b>Groups</b> (<b>New Group</b>) and <b>Order</b>. <b>Undo</b> and <b>Redo</b> sit beside the menu's title.</li>"
                + "<li>A control: <b>Add Action</b>, <b>Rename</b>, <b>Assign Hardware</b> and <b>History</b>, then <b>Row</b> (<b>Clear Name</b>, <b>Delete</b>) and <b>Group</b> (<b>Group as</b>, and <b>Move to</b> each group).</li>"
                + "<li>A group header: <b>Rename Group</b>, then <b>Groups</b> › <b>Move Group Up</b>, <b>Move Group Down</b> or <b>Delete Group</b>.</li>"
                + "<li>An action row: <b>Open</b> and <b>Delete</b>.</li>"
                + "</ul>"
                + _good(["With several controls selected, the menu's title counts them and <b>History</b> is left out."]),
            related: ["logical-device-group-controls", "logical-device-undo"]
        },

        // ---- Common questions ----
        {
            id: "logical-device-q-xbox-missing",
            section: questions,
            title: "Why does Assign Hardware not list Xbox or vJoy?",
            body: "<p>Assign Hardware picks what feeds a control, never where it goes. Add a Map to Xbox or Map to vJoy action to the control instead.</p>",
            related: ["logical-device-send-to-xbox-vjoy"]
        },
        {
            id: "logical-device-q-locked",
            section: questions,
            title: "Why can't I change the Logical Device?",
            body: "<p>The profile is running. Editing is locked while it runs (\"Profile running: stop it to edit\"). Choose <b>Stop</b>, then edit; see <a href=\"topic:getting-started-run\">Run and Stop</a>.</p>",
            related: ["logical-device-about"]
        },
        {
            id: "logical-device-q-feed",
            section: questions,
            title: "How do I get my stick's buttons onto the Logical Device?",
            body: "<p>Right-click a Logical Device control, choose <b>Assign Hardware</b> and tick the stick's control.</p>",
            related: ["logical-device-assign-hardware"]
        },
        {
            id: "logical-device-q-no-controls",
            section: questions,
            title: "Why is the Logical Device page empty?",
            body: "<p>It has no buttons, axes or hats yet. Right-click empty space and use <b>Add Inputs</b>.</p>",
            related: ["logical-device-add-controls"]
        },
        {
            id: "logical-device-q-add-control-first",
            section: questions,
            title: "Why does a macro or condition say \"Add a Logical Device control first.\"?",
            body: "<p>The Logical Device has no controls yet, and nothing is created for you. Add a button, axis or hat first; see " + _link("logical-device-add-controls", "Add buttons, axes and hats") + ".</p>",
            related: ["logical-device-add-controls", "configuration-actions-macro", "configuration-actions-condition"]
        }
    ]
}
