// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: the Logical Device.
// Written to claude/plans/help-style-guide.md: each topic opens with what
// it's for, then "How to", "What you see" and "Good to know" (empty sections
// left out).

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
            body: "<p>The Logical Device is a virtual device inside the program. Your physical controls feed its buttons, axes and hats. Each of its controls also has actions of its own.</p>"
                + "<p>Use it to combine several physical controls before you send them on. The path is: physical control → <b>Assign Hardware</b> → Logical Device control → its actions.</p>"
                + "<h4>How to</h4>"
                + "<ul>"
                + "<li>Open it with <b>Logical Device</b> on the toolbar <a href=\"show:toolbar/Logical Device\">Show me ›</a>.</li>"
                + "<li>Or choose <b>Tools › Mapping › Logical Device</b> <a href=\"open:tools.logical\">Open ›</a>.</li>"
                + "</ul>"
                + _good([
                    "Controls are named by type and number: Button 1, Axis 1, Hat 1.",
                    "You can't edit it while the profile runs; the page says \"Profile running: stop it to edit\".",
                    "At Stop and at the start of each Run, its axes go to 0, buttons go up and hats go to center. See <a href=\"topic:getting-started-what-stop-releases\">What Stop lets go of</a>.",
                    "Its card always shows on <a href=\"topic:home-devices-home\">Home</a>.",
                    "To give its card a picture, right-click the card and choose <b>Add Image…</b> in the menu's <b>Device</b> section. Later you can choose <b>Change Image…</b> or <b>Remove Image</b>.",
                    "Every profile uses the same Logical Device; see " + _link("logical-device-saved", "Where the Logical Device is saved") + "."
                ]),
            related: ["logical-device-add-controls", "logical-device-assign-hardware", "modes-modes",
                      "logical-device-send-to-xbox-vjoy", "logical-device-saved"]
        },
        {
            id: "logical-device-saved",
            section: main,
            title: "Where the Logical Device is saved",
            body: "<p>The Logical Device has its own file, shared by every profile, the same way the Keyboard has one. Loading another profile keeps the same controls, groups and names.</p>"
                + "<h4>How to</h4>"
                + "<ul>"
                + "<li>Save it with <b>File › Save Profile</b> (<b>Ctrl+S</b>) <a href=\"show:menu/File/Save Profile\">Show me ›</a>. It saves the Logical Device too when it changed.</li>"
                + "<li>Keep other layouts in the " + _link("device-library-built-in", "Device Library") + ". It lists the Logical Device under <b>Internal inputs</b>, with <b>Save to Device Library…</b>, <b>Restore…</b> and <b>Export…</b>.</li>"
                + "<li>Bring in a Logical Device file from someone else with the Device Library's <b>File › Import Device…</b>, then choose <b>Restore…</b>.</li>"
                + "<li>Go back to an earlier save in <a href=\"topic:tools-history\">History</a> (<b>Tools › History</b>). You can restore the Logical Device there on its own.</li>"
                + "</ul>"
                + _good([
                    "Its unsaved changes count toward the <b>*</b> in the title and the save question. <b>Discard</b> there throws them away too.",
                    "Each control keeps its own identity for good. Actions that send to a control follow it, even after a rename or a new number.",
                    "An action that names a missing control is flagged, with an offer to add the control. It is never removed or moved to another control.",
                    "A macro step that names a missing Logical Device control is kept when you save.",
                    "If one control can't be read, it is skipped and kept in the file unchanged. A <b>Logical Device</b> notice names it.",
                    "If the whole file can't be read, a notice says so. The file is never saved over.",
                    "If the profile saves but the Logical Device file can't be written, a message says so. Its changes stay unsaved; save again to retry."
                ]),
            related: ["logical-device-about", "logical-device-undo", "device-library-built-in", "tools-history"]
        },
        {
            id: "logical-device-add-controls",
            section: main,
            title: "Add buttons, axes and hats",
            body: "<p>Add the controls the Logical Device needs.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click empty space on the Logical Device page.</li>"
                + "<li>Open <b>Add Inputs</b>.</li>"
                + "<li>Next to <b>Buttons</b>, <b>Axes</b> or <b>Hats</b>, set how many (up to 180).</li>"
                + "<li>Choose <b>Add</b>.</li>"
                + "</ol>"
                + _good([
                    "To take it back, choose <b>Undo</b> (<b>Ctrl+Z</b>).",
                    "Importing a device file in <b>Export / Import Device</b> can add the controls it needs. <b>Restore Import</b> removes them again. See " + _link("home-devices-device-pack-import", "Import a device file") + "."
                ]),
            related: ["logical-device-about", "logical-device-rename-control", "logical-device-undo"]
        },
        {
            id: "logical-device-rename-control",
            section: main,
            title: "Rename a control",
            body: "<p>Give a control your own name beside its system name.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the control and choose <b>Rename</b>.</li>"
                + "<li>Type the name, then press <b>Enter</b>.</li>"
                + "</ol>"
                + _good([
                    "<b>Hide system name</b> shows only your name.",
                    "To remove your name, right-click the control and choose <b>Row › Clear Name</b>. It asks first; the system name stays."
                ]),
            related: ["logical-device-group-controls", "logical-device-menus"]
        },
        {
            id: "logical-device-delete-control",
            section: main,
            title: "Delete a control",
            body: "<p>Deleting removes a control from the Logical Device, with its hardware links and its actions.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Select the control. Shift-click to select several; the menu's title then counts them.</li>"
                + "<li>Right-click and choose <b>Row › Delete</b>.</li>"
                + "<li>A box asks first. Confirm with the red <b>Delete Row</b>; for several rows it says how many.</li>"
                + "</ol>"
                + _good(["<b>Cancel</b> has the focus, so <b>Enter</b> and <b>Esc</b> both cancel.",
                         "To take it back, choose <b>Undo</b> (<b>Ctrl+Z</b>)."]),
            related: ["logical-device-undo", "logical-device-menus"]
        },
        {
            id: "logical-device-group-controls",
            section: main,
            title: "Group and order controls",
            body: "<p>Groups keep related controls together on the page.</p>"
                + "<h4>How to</h4>"
                + "<ul>"
                + "<li>New group: right-click empty space, open <b>Groups</b>, type a name in <b>New Group</b>, then press <b>Enter</b>.</li>"
                + "<li>Put controls in a group: select them, right-click and open <b>Group</b>. Type a name in <b>Group as</b>, or choose a group under <b>Move to</b>.</li>"
                + "<li>Rename a group: right-click its header and choose <b>Rename Group</b>.</li>"
                + "<li>Move or delete a group: open <b>Groups</b> and choose <b>Move Group Up</b>, <b>Move Group Down</b> or <b>Delete Group</b>.<ul>"
                + "<li>Delete Group asks first. Its controls stay, in Ungrouped.</li>"
                + "</ul></li>"
                + "<li>Fold a group: click its header.</li>"
                + "<li>Drag a control by its grey handle onto another control or onto a group header.<ul>"
                + "<li>Drop on the top half to put it before, the bottom half to put it after.</li>"
                + "<li>Drag a header to move the whole group.</li>"
                + "</ul></li>"
                + "<li>Sort: right-click empty space, open <b>Order</b>, then choose <b>By System Name</b>, <b>By Your Name</b> or <b>Group Names A to Z</b>.</li>"
                + "</ul>",
            related: ["logical-device-find-control", "logical-device-menus"]
        },
        {
            id: "logical-device-find-control",
            section: main,
            title: "Find a control",
            body: "<p><b>Find</b> filters the list, so you see only the controls you want.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Press <b>Ctrl+F</b> or click the Find box.</li>"
                + "<li>Type a system name, your name or a group name.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>A line under the box says \"N found\" or \"Nothing matches\".</li>"
                + "<li><b>×</b> or <b>Esc</b> clears the typing.</li>"
                + "<li>Filters by type: buttons, axes or hats.</li>"
                + "<li><b>Ungrouped</b>: only controls that aren't in a group.</li>"
                + "<li><b>No hardware writer</b>: only controls that no physical control feeds.</li>"
                + "<li><b>No bindings in this mode</b>: only controls with no actions in the current mode.</li>"
                + "<li><b>Clear</b> resets the filters. When nothing is listed, <b>Clear Filters</b> does the same.</li>"
                + "</ul>"
                + _good(["The hardware list in <b>Assign Hardware</b> has its own <b>Search</b> box, with the same \"N found\" line and <b>×</b>."]),
            related: ["logical-device-group-controls"]
        },
        {
            id: "logical-device-undo",
            section: main,
            title: "Undo a change on the Logical Device",
            body: "<p><b>Undo</b> and <b>Redo</b> step back and forward through changes to the controls and groups. Up to 50 steps are kept.</p>"
                + "<h4>How to</h4>"
                + "<ul>"
                + "<li>Choose <b>Undo</b> or <b>Redo</b> under the Find filters, or beside the right-click menu's title.</li>"
                + "<li>Keys: <b>Ctrl+Z</b> to undo; <b>Ctrl+Y</b> or <b>Ctrl+Shift+Z</b> to redo.</li>"
                + "</ul>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Beside the buttons, \"Last change: <i>change</i>\" names the newest change.</li>"
                + "<li>After an Undo, it reads \"Undone: <i>change</i>\".</li>"
                + "</ul>"
                + _good([
                    "To see a control's saved changes, right-click it and choose <b>History</b>; see <a href=\"topic:tools-history\">History</a>.",
                    "Undo steps stay when you load another profile. Steps that changed the old profile's actions or hardware links are dropped.",
                    "All Undo steps are cleared when a mode is deleted or when you <b>Discard</b> unsaved changes.",
                    "They are also cleared when the Logical Device is reloaded: a Device Library <b>Restore…</b>, an import, or a History restore."
                ]),
            related: ["logical-device-menus"]
        },
        {
            id: "logical-device-assign-hardware",
            section: main,
            title: "Feed a control from hardware",
            body: "<p><b>Assign Hardware</b> picks the physical controls that feed a Logical Device control.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the control and choose <b>Assign Hardware</b>.<ul>"
                + "<li>It lists the physical controls of the same type that are ticked in their device's <a href=\"topic:home-devices-input-modules\">Module Setup</a>.</li>"
                + "<li>For a button, it lists keyboard keys and OSC addresses too.</li>"
                + "</ul></li>"
                + "<li>Type in <b>Search</b> to filter the list.</li>"
                + "<li>Tick a control. It gets a " + _link("device-bindings-actions-map-to-logical-device", "Map to Logical Device") + " action in the current mode.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<p>The control shows its source on a row under it. Turn on <b>Show written by</b> in <b>Appearance…</b> to see it.</p>"
                + "<ul>"
                + "<li>On that row, an axis can be set to absolute or relative and given a scale.</li>"
                + "<li>A button can be inverted with <b>Invert</b>.</li>"
                + "</ul>"
                + _good([
                    "To remove the link, untick the control.",
                    "You can tick two physical controls for one Logical Device control. Their values are not added up: the newest one wins. An axis takes whichever stick moved last; a button is released when either source is released.",
                    "To combine two axes into one value, put a " + _link("device-bindings-actions-merge-axis", "Merge Axis") + " on one of the stick axes, and add Map to Logical Device inside it.",
                    "Assign Hardware only picks what feeds the control; it never lists vJoy or Xbox. To send on, see " + _link("logical-device-send-to-xbox-vjoy", "Send a control to Xbox or vJoy") + "."
                ]),
            related: ["device-bindings-actions-map-to-logical-device", "logical-device-add-action",
                      "logical-device-send-to-xbox-vjoy"]
        },
        {
            id: "logical-device-add-action",
            section: main,
            title: "Add an action to a control",
            body: "<p>A Logical Device control has actions of its own. You set them up in the same editor as on the Device Bindings page.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the control and choose <b>Add Action</b>. The action editor opens beside the list.</li>"
                + "<li>Choose the action and set it up.</li>"
                + "<li>Choose <b>OK</b>.</li>"
                + "</ol>"
                + _good([
                    "To change an action, click its row.",
                    "Right-click an action row to <b>Open</b> or <b>Delete</b> it. Delete asks first; <b>Undo</b> puts it back.",
                    "Actions belong to the current <a href=\"topic:modes-modes\">mode</a>."
                ]),
            related: ["device-bindings-actions-add-action", "device-bindings-actions-choose-action",
                      "logical-device-send-to-xbox-vjoy"]
        },
        {
            id: "logical-device-send-to-xbox-vjoy",
            section: main,
            title: "Send a control to Xbox or vJoy",
            body: "<p>A Logical Device control sends on to the Xbox controller or vJoy through an action, not through Assign Hardware.</p>"
                + "<p>The whole path: physical control → Assign Hardware → Logical Device control → Map to Xbox or Map to vJoy → Xbox 360 Controller or vJoy device.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the control (for example Hat 1) and choose <b>Add Action</b>.</li>"
                + "<li>Choose <b>Map to Xbox</b> or <b>Map to vJoy</b>.</li>"
                + "<li>Pick the <b>Target</b>. The list offers only what fits: a hat can drive the D-pad, a button or a stick.</li>"
                + "<li>Choose <b>OK</b>.</li>"
                + "</ol>"
                + "<h4>Example: send to vJoy</h4>"
                + "<ol>"
                + "<li>Tick the vJoy outputs you will use in " + _link("home-devices-vjoy-output", "Output Module Setup") + " <a href=\"show:menu/Tools/Device Setup/Output Module Setup\">Show me ›</a>, then choose <b>Save Module</b>. The output list offers only ticked outputs.</li>"
                + "<li>Right-click Axis 1 on the Logical Device and choose <b>Add Action</b>.</li>"
                + "<li>Choose <b>Map to vJoy</b>, pick the vJoy device, then an axis (for example X). Choose <b>OK</b>.</li>"
                + "<li>Save the profile and choose <b>Run</b> <a href=\"show:toolbar/Run\">Show me ›</a>; see " + _link("getting-started-run", "Run and Stop") + ".</li>"
                + "</ol>"
                + _good([
                    "Map to vJoy needs the <b>vJoy</b> driver; see " + _link("device-bindings-actions-map-to-vjoy", "Map to vJoy") + ".",
                    "Map to Xbox needs the <b>ViGEmBus</b> driver (it lets games see an Xbox 360 controller); see <a href=\"topic:home-devices-xbox-output\">Xbox output module</a>.",
                    "If Map to Xbox isn't in the list, <b>Actions offered</b> in " + _link("options-profile-options", "Options") + " may hide it. <a href=\"show:option/Actions offered\">Show me ›</a>"
                ]),
            related: ["device-bindings-actions-map-to-xbox", "device-bindings-actions-map-to-vjoy",
                      "home-devices-vjoy-output", "logical-device-assign-hardware"]
        },
        {
            id: "logical-device-appearance",
            section: main,
            title: "Change how the Logical Device page looks",
            body: "<p><b>Appearance</b> changes how the page looks, never what it does.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose <b>Appearance…</b> on the page or in its right-click menu.</li>"
                + "<li>Change the sections: <b>Shown</b>, <b>Handles</b>, <b>List</b>, <b>Group</b>, <b>Parent Row</b>, <b>Action Row</b>, <b>Text</b> and <b>Selection</b>.</li>"
                + "<li>Choose <b>Save Appearance</b>.</li>"
                + "</ol>"
                + _good([
                    "The look is saved for this page, in the program settings.",
                    "<b>Reset Appearance</b> restores the built-in look."
                ]),
            related: ["device-bindings-actions-appearance"]
        },
        {
            id: "logical-device-menus",
            section: main,
            title: "Logical Device menus",
            body: "<p>What each right-click menu on the Logical Device page holds.</p>"
                + "<h4>What you see</h4>"
                + "<table>"
                + "<tr><th>Right-click on</th><th>Menu</th></tr>"
                + "<tr><td>Empty space</td><td><b>Appearance…</b>, then the sections <b>Add Inputs</b>, <b>Groups</b> (<b>New Group</b>) and <b>Order</b>. <b>Undo</b> and <b>Redo</b> sit beside the title.</td></tr>"
                + "<tr><td>A control</td><td><b>Add Action</b>, <b>Rename</b>, <b>Assign Hardware</b> and <b>History</b>. Then <b>Row</b> (<b>Clear Name</b>, <b>Delete</b>) and <b>Group</b> (<b>Group as</b>, <b>Move to</b>).</td></tr>"
                + "<tr><td>A group header</td><td><b>Rename Group</b>, then <b>Groups</b>: <b>Move Group Up</b>, <b>Move Group Down</b>, <b>Delete Group</b>.</td></tr>"
                + "<tr><td>An action row</td><td><b>Open</b> and <b>Delete</b>.</td></tr>"
                + "</table>"
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
            body: "<p>The profile is running, and editing is locked while it runs. Choose <b>Stop</b> <a href=\"show:toolbar/Stop\">Show me ›</a>, then edit. See <a href=\"topic:getting-started-run\">Run and Stop</a>.</p>",
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
            id: "logical-device-q-loop",
            section: questions,
            title: "Why was a loop between controls stopped?",
            body: "<p>A control's actions sent back to itself, directly or through other controls (for example Axis 1 → Axis 2 → Axis 1). A macro's Logical Device step can do the same to the control the macro sits on.</p>"
                + "<p>The program stops a loop after 8 hops so it can't freeze. One hop is one control sending to the next.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open the controls the notice names.</li>"
                + "<li>Change the Map to Logical Device action or macro step that sends back along the loop.</li>"
                + "</ol>"
                + _good([
                    "The count follows each input through the chain, so a slow loop is stopped too, even through a macro.",
                    "Fast presses on a button that isn't in a loop are never stopped.",
                    "The notice names the loop, for example \"Axis 1 → Axis 1\". It shows once per Run, and one warning goes to <b>user.log</b>.",
                    "Map to Logical Device never offers the control it sits on; see " + _link("device-bindings-actions-map-to-logical-device", "Map to Logical Device") + ".",
                    "If a saved action targets its own control, the picker marks it \"(this control: blocked by the loop guard)\". Pick another control."
                ]),
            related: ["device-bindings-actions-map-to-logical-device", "logical-device-add-action"]
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
            related: ["logical-device-add-controls", "device-bindings-actions-macro", "device-bindings-actions-condition"]
        }
    ]
}
