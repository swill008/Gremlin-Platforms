// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: the Configuration page and every action.

.pragma library

var chapter = { id: "configuration-actions", title: "Configuration and actions" }

function _good(items) {
    return "<h4>Good to know</h4><ul><li>" + items.join("</li><li>") + "</li></ul>"
}

function _link(id, title) {
    return "<a href=\"topic:configuration-actions-" + id + "\">" + title + "</a>"
}

function topics() {
    var page = "Configuration page"
    var actions = "Actions"
    var questions = "Common questions"
    return [
        // ---- Configuration page ----
        {
            id: "configuration-actions-configuration-page",
            section: page,
            title: "The Configuration page",
            body: "<p>The Configuration page lists the claimed inputs of one device and the actions on each.</p>"
                + "<ul>"
                + "<li>To open it, double-click a card on <a href=\"topic:home-devices-home\">Home</a>, or choose <b>View › Configuration</b>.</li>"
                + "<li>The arrows beside the title step to the previous or next device.</li>"
                + "<li>Actions belong to the mode shown in <b>Mode</b> on the toolbar; see <a href=\"topic:modes-mode-box\">the Mode box</a>.</li>"
                + "<li><b>Move inputs with no actions to the end</b> lists those inputs together under a <b>No actions</b> heading.</li>"
                + "</ul>"
                + _good([
                    "<b>OK</b> keeps an action in the profile; <b>File › Save Profile</b> writes it to disk.",
                    "The <b>Keyboard</b> card opens its own page; see " + _link("keyboard-page", "Set up keyboard keys") + ".",
                    "An output device opens its <b>Output View</b> instead; see " + _link("output-view", "Output View") + "."
                ]),
            related: ["configuration-actions-add-action", "configuration-actions-undo", "modes-modes",
                      "configuration-actions-appearance"]
        },
        {
            id: "configuration-actions-add-action",
            section: page,
            title: "Add an action to an input",
            body: "<p>An action says what an input does when it fires.</p>"
                + "<ol>"
                + "<li>Open the device's Configuration page.</li>"
                + "<li>On the input's row, choose <b>Add Action</b>. The action editor opens beside it.</li>"
                + "<li>Choose the action and set it up.</li>"
                + "<li>Choose <b>OK</b>.</li>"
                + "<li>To keep it on disk, choose <b>File › Save Profile</b> (<b>Ctrl+S</b>).</li>"
                + "</ol>"
                + _good([
                    "<b>Close pane after OK</b> closes the editor when OK succeeds.",
                    "Leaving an input with changes in the editor that are not saved asks first.",
                    "While the profile runs, the actions are locked (\"Profile running: stop it to edit\"). <b>Run</b> asks first about an action editor with changes."
                ]),
            related: ["configuration-actions-choose-action", "configuration-actions-delete-action",
                      "configuration-actions-undo"]
        },
        {
            id: "configuration-actions-delete-action",
            section: page,
            title: "Delete an action",
            body: "<p>Deleting an action takes it off the input in the current mode.</p>"
                + "<ol>"
                + "<li>Open the device's Configuration page and select the input.</li>"
                + "<li>Choose <b>Delete</b> on the action.</li>"
                + "</ol>"
                + _good([
                    "To take the delete back, choose <b>Undo</b> (<b>Ctrl+Z</b>).",
                    "The profile on disk changes only when you save it."
                ]),
            related: ["configuration-actions-undo", "configuration-actions-add-action"]
        },
        {
            id: "configuration-actions-undo",
            section: page,
            title: "Undo a change on the Configuration page",
            body: "<p><b>Undo</b> and <b>Redo</b> step back and forward through what <b>OK</b> and <b>Delete</b> changed.</p>"
                + "<ul>"
                + "<li>Choose <b>Undo</b> or <b>Redo</b> beside Output, or press <b>Ctrl+Z</b> or <b>Ctrl+Y</b>.</li>"
                + "</ul>"
                + _good([
                    "The steps are kept until you open another device or profile.",
                    "Undo and Redo wait while an action is open in the editor.",
                    "Saved changes are also kept in the <a href=\"topic:tools-history\">History</a> (<b>Tools › History</b>)."
                ]),
            related: ["configuration-actions-add-action", "configuration-actions-delete-action", "tools-history"]
        },
        {
            id: "configuration-actions-keyboard-page",
            section: page,
            title: "Set up keyboard keys",
            body: "<p>The <b>Keyboard</b> page lists the keys you added and the actions on each.</p>"
                + "<ol>"
                + "<li>Double-click the <b>Keyboard</b> card on Home.</li>"
                + "<li>Choose <b>Add Key</b> and pick the key.</li>"
                + "<li>Select the key. The editor below the list is a draft of it.</li>"
                + "<li>Choose <b>OK</b> to write the draft, or <b>Cancel</b> to put it back.</li>"
                + "</ol>"
                + _good([
                    "<b>Undo</b> and <b>Redo</b> step back through each OK, asking first when the draft has changes.",
                    "Choosing another key, or deleting one, while the draft has changes asks first.",
                    "A key binding fires only for keys the Keyboard <a href=\"topic:home-devices-input-modules\">input module</a> claims."
                ]),
            related: ["configuration-actions-add-action", "configuration-actions-map-to-keyboard"]
        },
        {
            id: "configuration-actions-output-view",
            section: page,
            title: "Output View",
            body: "<p>An output device (vJoy or the Xbox controller) opens its <b>Output View</b> in place of a Configuration page: a live view of what its output module sends.</p>"
                + "<p>It is labelled \"View only — shows what the input modules' actions send.\"</p>"
                + _good([
                    "A wire to an output the output module doesn't claim is shown as <b>(not claimed)</b> and sends nothing."
                ]),
            related: ["configuration-actions-configuration-page", "configuration-actions-appearance",
                      "configuration-actions-map-to-vjoy", "configuration-actions-map-to-xbox"]
        },
        {
            id: "configuration-actions-appearance",
            section: page,
            title: "Change how a page looks",
            body: "<p>Appearance changes how a Configuration page or Output View looks, never what it does. The look is saved in that device's <a href=\"topic:home-devices-module-files\">module file</a>.</p>"
                + "<ol>"
                + "<li>On the page, choose <b>Appearance…</b>. Changes show at once.</li>"
                + "<li>Change the sections you want. <b>Open All</b> and <b>Close All</b> expand or fold them.</li>"
                + "<li>Choose <b>Save Appearance</b> to keep the changes.</li>"
                + "</ol>"
                + "<p>Configuration page sections: <b>Screen</b> (background color or image), <b>Shown</b> (child rows, live bars, LED dots, summary), <b>List</b> and <b>Group</b> (spacing and group cards), <b>Parent Row</b> and <b>Child Row</b> (row size, padding, colors), <b>Text</b>, <b>Selection</b>, and <b>Editor</b> (the action editor beside a row).</p>"
                + "<p>Output View sections: <b>Screen</b>, <b>Layout</b>, <b>Pads</b>, <b>Meters</b>, <b>Buttons</b> and <b>Colors</b>.</p>"
                + _good([
                    "<b>Reset Appearance</b> (red) restores the built-in look; <b>Copy Appearance from…</b> copies another device's look. Both still need Save Appearance.",
                    "Closing the panel with changes that are not saved asks first.",
                    "The Xbox, Keyboard and OSC pages have no Appearance. The Logical Device has its own Appearance, kept in the program settings."
                ]),
            related: ["configuration-actions-configuration-page", "configuration-actions-output-view",
                      "logical-device-appearance"]
        },

        // ---- Actions ----
        {
            id: "configuration-actions-choose-action",
            section: actions,
            title: "Choose an action",
            body: "<p><b>Add Action</b> lists the actions that suit the input type: axis, button, hat or key.</p>"
                + "<ul>"
                + "<li>Container actions (Condition, Chain, Double Tap, Tempo, Smart Toggle, Split Axis, Merge Axis, Dual Axis Deadzone, Axis Delta, Hat as Buttons) hold other actions. Add the container first, then the actions inside it.</li>"
                + "<li>Every other action does one thing, such as " + _link("map-to-vjoy", "Map to vJoy") + " or " + _link("map-to-keyboard", "Map to Keyboard") + ".</li>"
                + "</ul>"
                + _good([
                    "<a href=\"topic:options-profile-options\">Options</a> › Actions › Add Action Menu › <b>Actions offered</b> sets the order of the list and can hide actions you never use."
                ]),
            related: ["configuration-actions-add-action", "configuration-actions-reference", "options-profile-options"]
        },
        {
            id: "configuration-actions-map-to-vjoy",
            section: actions,
            title: "Map to vJoy",
            body: "<p>Sends the input to a vJoy axis, button or hat.</p>"
                + "<ol>"
                + "<li>Pick the vJoy device by its output module name, then the output.</li>"
                + "<li>For an axis, choose <b>Absolute</b>, or <b>Relative</b> with <b>Speed</b>: the axis moves while the input is held off-center.</li>"
                + "<li>For a button, tick <b>Invert activation</b>.</li>"
                + "</ol>"
                + _good([
                    "Only outputs claimed by the vJoy output module are sent. An output that isn't claimed shows <b>Output not claimed</b>; claim it in <a href=\"topic:home-devices-vjoy-output\">Output Module Setup</a>."
                ]),
            related: ["configuration-actions-map-to-xbox", "configuration-actions-map-to-logical-device",
                      "home-devices-vjoy-output"]
        },
        {
            id: "configuration-actions-map-to-xbox",
            section: actions,
            title: "Map to Xbox",
            body: "<p>Sends the input to the virtual Xbox 360 controller. Every control is available; there is nothing to claim.</p>"
                + "<ul>"
                + "<li><b>Xbox</b>: the Xbox output module (Xbox 360 Controller).</li>"
                + "<li><b>Target</b>: any of the 22 controls: sticks, triggers, buttons, D-pad.</li>"
                + "<li>Trigger: <b>Full axis</b> (−1 → 0%, +1 → 100%) or <b>Upper half</b> (center → 0%).</li>"
                + "<li>Button: <b>Invert activation</b>.</li>"
                + "</ul>"
                + _good([
                    "Map to Xbox needs the <b>ViGEmBus</b> driver; see <a href=\"topic:home-devices-xbox-output\">Xbox output module</a>.",
                    "To send a Logical Device control to Xbox, see " + "<a href=\"topic:logical-device-send-to-xbox-vjoy\">Send a control to Xbox or vJoy</a>" + "."
                ]),
            related: ["configuration-actions-map-to-vjoy", "logical-device-send-to-xbox-vjoy", "home-devices-xbox-output"]
        },
        {
            id: "configuration-actions-map-to-logical-device",
            section: actions,
            title: "Map to Logical Device",
            body: "<p>Sends the input to a control on the Logical Device.</p>"
                + "<ol>"
                + "<li>Pick a logical control of the same type.</li>"
                + "<li>For an axis, choose <b>Absolute</b>, or <b>Relative</b> with <b>Speed</b>.</li>"
                + "<li>For a button, tick <b>Invert activation</b> if you need it.</li>"
                + "</ol>"
                + _good([
                    "<b>Assign Hardware</b> on the Logical Device creates these actions for you."
                ]),
            related: ["logical-device-assign-hardware", "logical-device-about"]
        },
        {
            id: "configuration-actions-map-to-keyboard",
            section: actions,
            title: "Map to Keyboard",
            body: "<p>Holds the recorded keys while the input is held and releases them when it is released.</p>"
                + "<ol>"
                + "<li>Choose <b>Record Keys</b>.</li>"
                + "<li>Press the keys for the <b>Key Combination</b>.</li>"
                + "</ol>"
                + _good(["Modifiers are pressed first."]),
            related: ["configuration-actions-macro", "configuration-actions-keyboard-page"]
        },
        {
            id: "configuration-actions-map-to-mouse",
            section: actions,
            title: "Map to Mouse",
            body: "<p>Clicks a mouse button or moves the pointer. Choose the <b>Mode</b>:</p>"
                + "<ul>"
                + "<li><b>Button</b> clicks a recorded mouse button. Wheel Up and Wheel Down are included and are sent once per press.</li>"
                + "<li><b>Motion</b> moves the pointer. On a button, set <b>Minimum speed</b>, <b>Maximum speed</b>, <b>Time to maximum speed</b> and <b>Direction</b>. On an axis, set <b>Control motion of</b> to X Axis or Y Axis.</li>"
                + "</ul>"
                + _good([
                    "Mouse buttons are for sending only. They can be recorded here and in a macro, but a running profile never reads the mouse, so a mouse button can't fire actions."
                ]),
            related: ["configuration-actions-macro"]
        },
        {
            id: "configuration-actions-macro",
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
                    "Mouse buttons can be recorded as steps, but a mouse button is never an input of its own; see " + _link("map-to-mouse", "Map to Mouse") + ".",
                    "The pause between steps is set by <b>Macro Default Delay</b> in <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>."
                ]),
            related: ["configuration-actions-map-to-keyboard", "configuration-actions-map-to-mouse", "options-profile-profile-settings"]
        },
        {
            id: "configuration-actions-response-curve",
            section: actions,
            title: "Response Curve",
            body: "<p>Reshapes an axis before the actions after it.</p>"
                + "<ol>"
                + "<li>Choose <b>Piecewise Linear</b>, <b>Cubic Spline</b> or <b>Cubic Bezier Spline</b>.</li>"
                + "<li>Drag the points, or type <b>X</b> and <b>Y</b>.</li>"
                + "<li>Set the <b>Deadzone</b>.</li>"
                + "</ol>"
                + _good([
                    "<b>Invert Curve</b> flips the curve.",
                    "<b>Symmetric</b> mirrors your edits around the center."
                ]),
            related: ["configuration-actions-dual-axis-deadzone", "configuration-actions-split-axis"]
        },
        {
            id: "configuration-actions-split-axis",
            section: actions,
            title: "Split Axis",
            body: "<p>Splits one axis at <b>Split axis at</b> into a lower or left part and an upper or right part, each with its own action list.</p>"
                + _good(["Each part is rescaled to the full range."]),
            related: ["configuration-actions-merge-axis", "configuration-actions-response-curve"]
        },
        {
            id: "configuration-actions-merge-axis",
            section: actions,
            title: "Merge Axis",
            body: "<p>Combines two axes into one value for the actions in its <b>Actions</b> list.</p>"
                + "<ol>"
                + "<li>Pick or create a <b>Merge axis instance</b>.</li>"
                + "<li>Pick the <b>First axis</b> and <b>Second axis</b>.</li>"
                + "<li>Choose the <b>Merge operation</b>: Average, Minimum, Maximum, Sum, Bidirectional or Prefer Center.</li>"
                + "</ol>",
            related: ["configuration-actions-split-axis", "configuration-actions-dual-axis-deadzone"]
        },
        {
            id: "configuration-actions-dual-axis-deadzone",
            section: actions,
            title: "Dual Axis Deadzone",
            body: "<p>Applies one deadzone to a pair of axes, such as a stick's X and Y: a circular <b>Inner</b> deadzone and a square <b>Outer</b> limit.</p>"
                + "<ol>"
                + "<li>Pick or create a <b>Deadzone instance</b>.</li>"
                + "<li>Pick the two axes.</li>"
                + "<li>Add the actions for each axis's result to its own action list.</li>"
                + "</ol>",
            related: ["configuration-actions-response-curve", "configuration-actions-merge-axis"]
        },
        {
            id: "configuration-actions-axis-delta",
            section: actions,
            title: "Axis Delta",
            body: "<p>Turns axis movement into button presses. Each time the axis moves by <b>Change threshold</b>, it pulses the actions under <b>Positive change</b> or <b>Negative change</b>.</p>",
            related: ["configuration-actions-split-axis"]
        },
        {
            id: "configuration-actions-condition",
            section: actions,
            title: "Condition",
            body: "<p>Runs one action list when its conditions are true and another when they are false.</p>"
                + "<ol>"
                + "<li>Choose <b>Any</b> or <b>All</b>.</li>"
                + "<li>Choose <b>Add Condition</b> and pick its kind: Joystick, Keyboard, Current Input, vJoy or Logical Device state.</li>"
                + "<li>Add the actions for true and for false.</li>"
                + "</ol>",
            related: ["configuration-actions-chain", "configuration-actions-tempo"]
        },
        {
            id: "configuration-actions-chain",
            section: actions,
            title: "Chain",
            body: "<p>Each press runs the next <b>Sequence</b> in turn.</p>"
                + "<ul>"
                + "<li><b>Add Chain Sequence</b> adds a sequence.</li>"
                + "<li>After <b>Timeout (sec, 0 = never)</b> without a press, it starts again at the first sequence.</li>"
                + "</ul>",
            related: ["configuration-actions-double-tap", "configuration-actions-condition"]
        },
        {
            id: "configuration-actions-double-tap",
            section: actions,
            title: "Double Tap",
            body: "<p>Gives a single tap and a double tap their own actions. Two taps within <b>Double-tap threshold (sec)</b> count as a double tap.</p>"
                + "<ul>"
                + "<li><b>exclusive</b> waits to see if a second tap comes.</li>"
                + "<li><b>combined</b> runs the single-tap actions on every press.</li>"
                + "</ul>",
            related: ["configuration-actions-tempo", "configuration-actions-chain"]
        },
        {
            id: "configuration-actions-tempo",
            section: actions,
            title: "Tempo",
            body: "<p>Gives a <b>Short press</b> and a <b>Long press</b> their own actions. A press longer than <b>Long-press threshold (sec)</b> is a long press.</p>"
                + "<ul><li><b>Activate on</b> sets whether the actions run on press or on release.</li></ul>",
            related: ["configuration-actions-double-tap", "configuration-actions-smart-toggle"]
        },
        {
            id: "configuration-actions-smart-toggle",
            section: actions,
            title: "Smart Toggle",
            body: "<p>A quick press, released within <b>Hold time (sec)</b>, latches its actions on until the next press. A longer hold acts only while held.</p>",
            related: ["configuration-actions-tempo"]
        },
        {
            id: "configuration-actions-hat-as-buttons",
            section: actions,
            title: "Hat as Buttons",
            body: "<p>Gives each hat direction its own action list. Set <b>Button mode</b> to <b>4 way</b> or <b>8 way</b>.</p>",
            related: ["configuration-actions-choose-action"]
        },
        {
            id: "configuration-actions-change-mode",
            section: actions,
            title: "Change Mode",
            body: "<p>Changes the running mode. Choose one:</p>"
                + "<ul>"
                + "<li><b>Switch</b> to a mode.</li>"
                + "<li><b>Previous</b> mode.</li>"
                + "<li><b>Unwind</b> one step.</li>"
                + "<li><b>Cycle</b> through a list.</li>"
                + "<li><b>Temporary</b>: only while held.</li>"
                + "</ul>",
            related: ["configuration-actions-load-profile", "modes-modes", "modes-manage"]
        },
        {
            id: "configuration-actions-load-profile",
            section: actions,
            title: "Load Profile",
            body: "<p>Loads another profile file when the input fires. Set <b>Profile filename</b>, or choose <b>Select File</b>.</p>",
            related: ["configuration-actions-change-mode", "getting-started-run"]
        },
        {
            id: "configuration-actions-pause-and-resume",
            section: actions,
            title: "Pause and Resume",
            body: "<p>Choose <b>Pause</b>, <b>Resume</b> or <b>Toggle</b> to stop or restart the processing of all actions.</p>"
                + _good(["While paused, the status reads Running (Paused)."]),
            related: ["configuration-actions-change-mode"]
        },
        {
            id: "configuration-actions-play-sound",
            section: actions,
            title: "Play Sound",
            body: "<p>Plays a WAV, MP3 or OGG file at the chosen <b>Volume</b>.</p>"
                + _good(["<a href=\"topic:options-profile-options\">Options</a> › Actions › Play Sound sets what happens when sounds overlap."]),
            related: ["configuration-actions-text-to-speech"]
        },
        {
            id: "configuration-actions-text-to-speech",
            section: actions,
            title: "Text to Speech",
            body: "<p>Speaks the text you type. You can put it on a button or a keyboard key.</p>"
                + "<ol>"
                + "<li>Type the text.</li>"
                + "<li>Choose <b>Interrupt</b>, <b>Queue Front</b> or <b>Queue Back</b>.</li>"
                + "<li>Set <b>Volume</b>, <b>Rate</b> and <b>Pitch</b>.</li>"
                + "</ol>"
                + _good(["The voice is set in <a href=\"topic:options-profile-options\">Options</a> › Actions › Text to Speech."]),
            related: ["configuration-actions-play-sound"]
        },
        {
            id: "configuration-actions-run-command",
            section: actions,
            title: "Run Command",
            body: "<p>Starts a program. Set the <b>Executable</b> and its <b>Arguments</b>.</p>"
                + _good([
                    "Arguments are split on spaces; put quotes around values that contain spaces.",
                    "The program runs with your own permissions."
                ]),
            related: ["configuration-actions-load-profile"]
        },
        {
            id: "configuration-actions-description",
            section: actions,
            title: "Description",
            body: "<p>A note on the input. It does nothing when the input fires.</p>",
            related: ["configuration-actions-choose-action"]
        },
        {
            id: "configuration-actions-reference",
            section: actions,
            title: "Reference",
            body: "<p>Reuses an existing action of the same input type.</p>"
                + "<ol>"
                + "<li>Pick the action.</li>"
                + "<li>Share it, so both inputs use the same action, or duplicate it, to get an independent copy.</li>"
                + "</ol>"
                + _good([
                    "A shared action's editor says <b>Shared with …</b> and names the other inputs. <b>OK</b> changes it for every input that uses it, and <b>Undo</b> puts it back for all of them."
                ]),
            related: ["configuration-actions-choose-action", "configuration-actions-undo"]
        },

        // ---- Common questions ----
        {
            id: "configuration-actions-q-cannot-edit",
            section: questions,
            title: "Why can't I change an action?",
            body: "<p>The profile is running. While it runs, the actions are locked (\"Profile running: stop it to edit\"). Choose <b>Stop</b>, then edit; see <a href=\"topic:getting-started-run\">Run and Stop</a>.</p>",
            related: ["configuration-actions-add-action"]
        },
        {
            id: "configuration-actions-q-action-missing",
            section: questions,
            title: "Why is an action missing from the Add Action list?",
            body: "<p>The list shows only the actions that suit the input type, and <a href=\"topic:options-profile-options\">Options</a> › Actions › Add Action Menu › <b>Actions offered</b> can hide actions.</p>",
            related: ["configuration-actions-choose-action"]
        },
        {
            id: "configuration-actions-q-not-kept",
            section: questions,
            title: "Why did my action not stay after I closed the program?",
            body: "<p><b>OK</b> keeps the action in the open profile only. Choose <b>File › Save Profile</b> (<b>Ctrl+S</b>) to write it to disk.</p>",
            related: ["configuration-actions-add-action"]
        },
        {
            id: "configuration-actions-q-vjoy-not-claimed",
            section: questions,
            title: "Why does Map to vJoy say Output not claimed?",
            body: "<p>The vJoy output module doesn't claim that output, so nothing is sent to it. Claim the output in <a href=\"topic:home-devices-vjoy-output\">Output Module Setup</a>.</p>",
            related: ["configuration-actions-map-to-vjoy"]
        },
        {
            id: "configuration-actions-q-same-action",
            section: questions,
            title: "How do I use the same action on two inputs?",
            body: "<p>Add a " + _link("reference", "Reference") + " action to the second input and share the first input's action.</p>",
            related: ["configuration-actions-reference"]
        }
    ]
}
