// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: OSC (D-01-HELP-OSC). Its settings, inputs, sending,
// Feedback, the OSC Monitor, how-tos and the technical reference.

.pragma library

var chapter = { id: "osc", title: "OSC" }

function _good(items) {
    return "<h4>Good to know</h4><ul><li>" + items.join("</li><li>") + "</li></ul>"
}

function _link(id, title) {
    return "<a href=\"topic:" + id + "\">" + title + "</a>"
}

function _list(items) {
    return "<ul><li>" + items.join("</li><li>") + "</li></ul>"
}

function _steps(items) {
    return "<ol><li>" + items.join("</li><li>") + "</li></ol>"
}

function _table(head, rows) {
    var html = "<table cellpadding=\"3\"><tr>"
    for (var i = 0; i < head.length; ++i)
        html += "<th align=\"left\">" + head[i] + "</th>"
    html += "</tr>"
    for (var r = 0; r < rows.length; ++r) {
        html += "<tr>"
        for (var c = 0; c < rows[r].length; ++c)
            html += "<td>" + rows[r][c] + "</td>"
        html += "</tr>"
    }
    return html + "</table>"
}

function topics() {
    var main = "OSC"
    var setup = "OSC Setup"
    var inputs = "OSC inputs"
    var sending = "Sending OSC"
    var howto = "How to"
    var tech = "Technical reference"
    var questions = "Common questions"
    return [
        // ---- OSC ----
        {
            id: "osc-about",
            section: main,
            title: "OSC and the program",
            body: "<p>OSC (Open Sound Control) is a small network message format. Stream Decks (through Bitfocus Companion), phone and tablet apps such as TouchOSC, lighting desks and music software send it. The program reads OSC messages as button presses and axis moves, and can send OSC messages back.</p>"
                + "<p>Each message has an <i>address</i> such as <code>/fire</code> and zero or more <i>values</i> such as <code>1</code> or <code>0.75</code>.</p>"
                + _list([
                    "OSC is an internal input, like the Keyboard and the Logical Device. Its page lists your OSC inputs: one per address you use. Each input gets actions on the Configuration page like any button or axis.",
                    "One list of OSC inputs is kept in OSC's own module file and used by every profile.",
                    "The program listens on a network port (8001 unless you change it). Your app sends to this PC's address and that port.",
                    "The program can also send: the " + _link("configuration-actions-send-osc", "Send OSC") + " action, and " + _link("osc-feedback-tab", "Feedback") + ", which shows the program's state on your device.",
                    "Settings are in OSC's Module Setup window (<b>OSC Setup…</b> on the OSC page), in four tabs: <b>Server</b>, <b>Output</b>, <b>Feedback</b> and <b>Discovery</b>."
                ])
                + _good([
                    "Start with " + _link("options-profile-osc", "Set up OSC") + ".",
                    "To make a connection by hand, see " + _link("osc-checklist", "Connection checklist") + " and the " + _link("osc-tech-network", "OSC network and ports") + " reference."
                ]),
            related: ["options-profile-osc", "osc-add-input", "osc-checklist", "osc-companion"]
        },
        {
            id: "options-profile-osc",
            section: main,
            title: "Set up OSC",
            body: "<p>Get messages from an app into the program in a few minutes.</p>"
                + _steps([
                    "Open the <b>OSC</b> page (the <b>OSC</b> card on Home).",
                    "Choose <b>OSC Setup…</b>. On the <b>Server</b> tab, check that <b>Listen for OSC messages</b> is on, and note this PC's address and the <b>Port</b> (8001 unless you change it). <b>Copy</b> puts an address and the port on the clipboard.",
                    "In your app, set the OSC destination (host or IP) to that address and the port to that port. If the app runs on this PC, use 127.0.0.1.",
                    "On the OSC page, choose <b>Add</b>, then <b>Listen</b>, and press the button or move the control in your app once. The address it sent fills in. Choose the mode (<b>Button</b>, <b>Axis</b>, <b>Change</b> or <b>Encoder</b>), then <b>OK</b>.",
                    "Select the new input and add actions to it, as on any device: for example Map to vJoy.",
                    "Choose <b>Run</b>. Messages now press and move your actions."
                ])
                + _good([
                    "Nothing arriving? Open the <b>OSC Monitor</b> (" + _link("osc-monitor", "Watch messages with the OSC Monitor") + ") and see " + _link("osc-troubleshooting", "When OSC doesn't work") + ".",
                    "To show the program's state on the device too, see " + _link("osc-feedback-tab", "Feedback tab") + ".",
                    "Options shows one line for OSC, <b>OSC settings are in OSC › Module Setup.</b>, with the button <b>Open OSC Module Setup</b>, which opens this window."
                ]),
            related: ["osc-about", "osc-server-tab", "osc-add-input", "osc-checklist"]
        },

        // ---- OSC Setup ----
        {
            id: "osc-setup-window",
            section: setup,
            title: "Open the OSC Setup window",
            body: "<p>All of OSC's settings are in one window with four tabs: OSC's Module Setup (its title is <b>Input Module Setup</b>).</p>"
                + _list([
                    "On the OSC page, choose <b>OSC Setup…</b>.",
                    "Or open the <b>OSC</b> card's menu on Home and choose <b>Module Setup…</b>.",
                    "Or, in Options, choose <b>Open OSC Module Setup</b> beside <b>OSC settings are in OSC › Module Setup.</b>"
                ])
                + "<p>The tabs: " + _link("osc-server-tab", "Server") + " (where the program listens), " + _link("osc-output-tab", "Output") + " (where it sends), " + _link("osc-feedback-tab", "Feedback") + " (state sent to devices) and " + _link("osc-discovery-tab", "Discovery") + " (finding devices on the network).</p>"
                + _good([
                    "Changes take effect at once, also while the profile runs.",
                    "The settings, targets and Feedback rows are kept in OSC's module file. Save to Device Library, Restore, Export and Device Pack carry them, and <a href=\"topic:tools-history\">History</a> keeps every save."
                ]),
            related: ["osc-server-tab", "osc-output-tab", "osc-feedback-tab", "osc-discovery-tab"]
        },
        {
            id: "osc-server-tab",
            section: setup,
            title: "Server tab",
            body: "<p>Where and how the program listens for OSC messages.</p>"
                + _list([
                    "<b>Listen for OSC messages</b>: turns OSC input on. Off, the program never opens the port. On unless you turn it off.",
                    "<b>Host</b>: leave it blank (<b>All addresses on this PC</b>) to listen on every network address of this PC. That keeps working when the PC's address changes. Or type one IP address or computer name to listen only there; the program checks it before saving.",
                    "<b>Port</b>: the UDP port your app sends to. 8001 unless you change it.",
                    "This PC's addresses with the port (for example 192.168.1.10:8001), each with <b>Copy</b>, under <b>Use one of these in your app:</b>. Type one of them into your app as its destination.",
                    "<b>Auto-release address-only messages after</b> … <b>ms (default delay)</b>: ticked, a message with no value presses a Button input, then releases it after this delay; unticked, it presses and stays pressed. Ticked and 250 ms unless you change them (0 to 10000 ms). The delay is also used by Change and Message + data inputs. An input's own <b>Trigger on message</b> and delay override it.",
                    "<b>Pad address-only messages (treat them as value 1.0)</b>: a message with no value counts as the value 1.0. A Button input then presses and stays pressed until a 0 comes, unless it has <b>Trigger on message</b>. Off unless you turn it on."
                ])
                + _good([
                    "The port opens only when needed: see " + _link("osc-tech-network", "OSC network and ports") + ".",
                    "If the port can't be opened, for example because another program uses it, Run still runs the rest of the profile and shows one error: \"Could not bind OSC on host:port.\", with the host and port."
                ]),
            related: ["osc-setup-window", "osc-output-tab", "osc-tech-network", "osc-troubleshooting"]
        },
        {
            id: "osc-output-tab",
            section: setup,
            title: "Output tab",
            body: "<p>Where the program sends OSC messages: the " + _link("configuration-actions-send-osc", "Send OSC") + " action and " + _link("osc-feedback-tab", "Feedback") + ".</p>"
                + _list([
                    "<b>OSC output (Send OSC actions and feedback)</b>: the master switch for everything OSC sends. Off, nothing is sent. On unless you turn it off.",
                    "<b>Reply to sender</b>: lets a Send OSC action or Feedback row send back to whoever sent the last message (that message's IP address and port). On unless you turn it off.",
                    "<b>Targets</b>: the places OSC sends to, each with a name, a host and a port. The first, <b>Default</b>, is 127.0.0.1 port 8000 unless you change it. With no targets, the list says \"No targets yet. Add one below.\"",
                    "To add a target, fill in the row below the list: <b>Name</b>, <b>IP address or computer name</b> and the port (8000 unless you change it), then <b>Add Target</b>. <b>Edit</b> puts a target in that row: change it, then <b>Save Target</b>, or <b>Cancel</b>. <b>Remove</b> asks first. Names must differ; renaming a target keeps the actions and rows that use it.",
                    "<b>Add Companion</b>: adds (or puts back) a target named Companion at 127.0.0.1 port 12321, the port of Companion's own OSC listener. See " + _link("osc-companion", "Use with Companion") + "."
                ])
                + _good([
                    "A target is the device's own address and the port it listens on, never this PC's.",
                    "Removing a target that actions or rows use: those send nothing until you pick another target. A Send OSC action shows <b>Missing target</b>."
                ]),
            related: ["osc-setup-window", "configuration-actions-send-osc", "osc-feedback-tab", "osc-tech-out"]
        },
        {
            id: "osc-feedback-tab",
            section: setup,
            title: "Feedback tab",
            body: "<p>Feedback sends the program's state to your OSC device, so its keys, lights and faders can show it: the current mode, a vJoy button, a gear lever axis.</p>"
                + _list([
                    "<b>Send feedback to OSC devices</b>: turns Feedback on. On unless you turn it off; with no rows it sends nothing.",
                    "<b>Send everything again at:</b> <b>Run start</b>, <b>Mode change</b>, <b>Profile switch</b>: sends every row's value again at those moments, so the device shows the right state. All ticked unless you untick them.",
                    "<b>Send everything again when a message comes to</b> (the sync address, \"/gremlin/sync\" unless you change it): a device can ask for every row again by sending this address. Ticked unless you untick it. Capitals don't matter.",
                    "<b>At most</b> … <b>messages per second per address</b>: 50 unless you change it; a whole number, 1 or more.",
                    "<b>Add Row</b> › <b>Blank row</b> adds a row that sends the current mode to <b>Reply to sender</b> at <code>/gremlin/mode</code>; change it to suit. <b>Add Row</b> › <b>Companion</b> adds a ready-made one (below). <b>Remove</b> removes a row after asking (<b>Remove Row</b>); you can restore it from Tools › History. Untick <b>Send this row</b> to stop a row without removing it. With no rows, the tab says \"No feedback rows. Add a row to send a value to an OSC device when it changes.\""
                ])
                + "<h4>Each row</h4>"
                + _list([
                    "<b>Source</b>: <b>Current mode</b> (the mode's name, as text), <b>vJoy button</b> or <b>vJoy axis</b> (pick the vJoy device and type the number), <b>Logical Device control</b> (<b>Pick a control</b>), or <b>OSC input</b> (<b>Pick an OSC input</b>: its own value, sent back).",
                    "<b>Send to</b>: a target from the Output tab, or <b>Reply to sender</b>.",
                    "<b>Address</b>: the OSC address to send, for example <code>/led/gear</code>. It starts with \"/\" and has no spaces.",
                    "<b>Min:</b> and <b>Max:</b>: a button sends Max when pressed and Min when released; an axis sends its position from Min (one end) to Max (the other end). 0 and 1 unless you change them.",
                    "<b>Off:</b> and <b>On:</b>: for an on/off source, the exact values sent instead of Min and Max, for example <code>#333333</code> and <code>#2a7a46</code>, a number, or text. Blank uses Min and Max. A color written #rrggbb (or r g b) sent to a Companion key color (an address ending /style/bgcolor or /style/color) goes as three whole numbers, r g b.",
                    "<b>Type</b>: <b>Auto</b>, <b>Int</b>, <b>Float</b>, <b>Bool</b> (true/false) or <b>Text</b>; see " + _link("osc-value-types", "OSC value types") + "."
                ])
                + "<h4>Companion templates</h4>"
                + "<p>Choose <b>Add Row</b> › <b>Companion</b>, then one of these. A short window asks for the few details; <b>Add Row</b> adds the row with its address, target (the Companion target, added when missing) and type:</p>"
                + _list([
                    "<b>Custom variable…</b>: asks the <b>Variable name</b> (gremlin_mode unless you change it; no spaces) and sends the current mode to <code>/custom-variable/</code><i>name</i><code>/value</code> as text. Create the custom variable in Companion first.",
                    "<b>Key text…</b>: asks the <b>Page</b>, <b>Row</b> and <b>Column</b> (1, 0 and 0 unless you change them; pages count from 1, rows and columns from 0) and sends the current mode to <code>/location/</code><i>page</i>/<i>row</i>/<i>column</i><code>/style/text</code> as text.",
                    "<b>Key color (off/on)…</b>: asks the key and an <b>Off color</b> and <b>On color</b> (#333333 and #2a7a46 unless you change them; #rrggbb), and sends to <code>/location/</code><i>page</i>/<i>row</i>/<i>column</i><code>/style/bgcolor</code>. Its source starts as vJoy button 1 of the first vJoy device: change it to the button you want shown."
                ])
                + _good([
                    "How rows send, step by step: " + _link("osc-feedback-how", "How Feedback sends") + ".",
                    "Feedback sends only while the profile runs and while <b>OSC output (Send OSC actions and feedback)</b> is on.",
                    "For Key text and Key color, turn on Companion's OSC Listener (Settings › OSC) first."
                ]),
            related: ["osc-feedback-how", "osc-output-tab", "osc-companion", "osc-value-types"]
        },
        {
            id: "osc-discovery-tab",
            section: setup,
            title: "Discovery tab",
            body: "<p>Lets the program and OSC apps on the same network find each other, so you don't have to type addresses.</p>"
                + _list([
                    "<b>Announce this PC</b>: lets OSC apps on your network find this PC and its port. Off unless you turn it on.",
                    "<b>Find OSC devices</b>: lists OSC apps on your network that announce themselves. Off unless you turn it on.",
                    "Each device found has <b>Add as Target</b>, which adds it to the Targets on the Output tab with its name, address and port."
                ])
                + _good([
                    "Only apps that announce themselves are found. Many apps don't; add those as a target by hand.",
                    "\"Discovery is not available on this PC.\" means the program couldn't start network discovery here; everything else works.",
                    "The technical names are in " + _link("osc-tech-network", "OSC network and ports") + "."
                ]),
            related: ["osc-output-tab", "osc-tech-network", "osc-checklist"]
        },

        // ---- OSC inputs ----
        {
            id: "osc-add-input",
            section: inputs,
            title: "Add an OSC input",
            body: "<p>An OSC input turns one kind of message into a button or an axis.</p>"
                + _steps([
                    "On the <b>OSC</b> page, choose <b>Add</b>.",
                    "Type the address under <b>OSC message:</b> (it starts with \"/\"), or choose <b>Listen</b> and send one message from your app. Listen ends when that message arrives and fills in the address and its values (<b>Parameters:</b>); <b>Stop</b> in the Listening box stops listening.",
                    "Choose the <b>Action mode:</b> <b>Button</b>, <b>Axis</b>, <b>Change</b> or <b>Encoder</b>. See " + _link("osc-modes", "OSC input modes and data styles") + ".",
                    "Choose <b>Message only</b>, or <b>Message + data</b> to match the values in <b>Data:</b> too.",
                    "If the message has several values, choose which one to read in <b>Source value:</b> (P1, P2 …).",
                    "For an axis, set <b>Min:</b> and <b>Max:</b> (0 and 1 unless you change them; Min must be less than Max). For a button, tick <b>Trigger on message</b> to press and release on any message, and set its delay in ms (250 unless you change it; the 1/10s to 1s buttons fill it in).",
                    "Choose <b>OK</b>. The new input is selected; add its actions."
                ])
                + _good([
                    "Several inputs can share an address when their data or source value differ, for example /pad with P1 and /pad with P2.",
                    "Listen opens the port for that one message, also when the profile isn't running, and closes it again afterwards.",
                    "To add many at once, see " + _link("osc-capture-import", "Capture or import many addresses") + "."
                ]),
            related: ["osc-modes", "osc-capture-import", "osc-edit-inputs", "osc-monitor"]
        },
        {
            id: "osc-capture-import",
            section: inputs,
            title: "Capture or import many addresses",
            body: "<h4>Bulk capture</h4>"
                + "<p>In the Add window (<b>OSC Input Mapper</b>), tick <b>Bulk capture</b>. Every new address that arrives becomes an input with the window's settings, until you untick it. Use it to press every key of a Stream Deck once.</p>"
                + "<h4>Import</h4>"
                + _steps([
                    "On the OSC page, choose <b>Import</b>.",
                    "In <b>New OSC messages:</b>, type or paste one address per line. After an address, add a space or a comma and a suffix to set the mode.",
                    "Choose <b>OK</b>. The result line says how many were added and skipped."
                ])
                + _table(["Suffix", "Makes", "Example"], [
                    ["(none) or B", "a Button", "<code>/key/1</code> or <code>/key/1 B</code>"],
                    ["BNP", "a Button with Trigger on message (presses and releases on any message)", "<code>/key/2 BNP</code>"],
                    ["A", "an Axis", "<code>/fader/1, A</code>"],
                    ["C", "a Change input", "<code>/scene C</code>"],
                    ["E", "an Encoder (an axis, format Auto)", "<code>/knob/1 E</code>"]
                ])
                + _good([
                    "Lines that don't start with \"/\" are skipped (the result names them), and so are addresses that already exist.",
                    "An unknown suffix makes a Button, and the result names the line."
                ]),
            related: ["osc-add-input", "osc-modes", "osc-edit-inputs"]
        },
        {
            id: "osc-edit-inputs",
            section: inputs,
            title: "Change, sort or delete OSC inputs",
            body: "<p>Each input's pencil on the OSC page opens a menu; the buttons below the list act on the whole list.</p>"
                + _list([
                    "<b>Change Address…</b>: edits the address. It must start with \"/\" and can't be blank; a duplicate is refused with the reason. The input keeps its actions.",
                    "<b>Edit Settings…</b>: opens the same choices as Add, in the <b>OSC Input Settings</b> window. The input keeps its actions.",
                    "<b>Copy for Companion</b>: copies, as text, the settings for Companion's Generic OSC connection (Target Hostname or IP, Target Port, Protocol UDP, Listen for Feedback on, Source Port 9001) and the key actions for this input, to follow while you set up Companion. See " + _link("osc-companion", "Use with Companion") + ".",
                    "The input's delete button asks first (<b>Delete</b>). You can restore it from Tools › History.",
                    "<b>Sort</b>: orders the list A to Z by address.",
                    "<b>Clear…</b>: removes every OSC input and its actions, after asking (<b>Clear OSC Inputs</b>)."
                ])
                + _good([
                    "An input that has actions can't switch between Axis and the button modes (Button, Change, Message + data, an encoder's pulses): remove its actions first, since an axis and a button take different actions. Switching among the button modes is fine.",
                    "Select an input to see its actions on the right.",
                    "Editing is locked while the profile runs."
                ]),
            related: ["osc-add-input", "osc-modes", "tools-history"]
        },
        {
            id: "osc-modes",
            section: inputs,
            title: "OSC input modes and data styles",
            body: "<p>The mode decides what a message does. Examples show the address, then its values.</p>"
                + _table(["Mode", "What it does", "Example message"], [
                    ["<b>Button</b>", "The value at the source presses when it isn't 0 and releases at 0. A message with no value presses, then releases after the delay.", "<code>/fire 1</code> presses, <code>/fire 0</code> releases; <code>/fire</code> presses and releases"],
                    ["<b>Button</b> + <b>Trigger on message</b>", "Any message to the address presses, then releases after the delay (250 ms unless you change it). For apps that send only on press.", "<code>/flaps</code> or <code>/flaps 1</code>"],
                    ["<b>Axis</b>", "The value at the source, from <b>Min:</b> to <b>Max:</b>, moves the axis from one end to the other. Values past Min or Max stop at the end. A message with no number is ignored.", "Min 0, Max 1: <code>/throttle 0.5</code> is the middle"],
                    ["<b>Change</b>", "Presses (then releases after the delay) each time the value differs from the last one. The first message counts.", "<code>/scene 1</code>, <code>/scene 2</code>: two presses; <code>/scene 2</code> again: none"],
                    ["<b>Message + data</b>", "Presses (then releases after the delay) only when the message's values equal <b>Data:</b>.", "Data <code>3 go</code>: <code>/scene 3 go</code> presses, <code>/scene 4 go</code> doesn't"],
                    ["<b>Encoder</b>", "Reads which way a knob turned. See " + _link("osc-encoder", "OSC encoders") + ".", "<code>/knob 1</code> clockwise, <code>/knob 0</code> counter-clockwise"]
                ])
                + "<h4>Source value</h4>"
                + "<p>A message can carry several values. <b>Source value:</b> picks the one to read: P1 is the first, P2 the second. Example: <code>/pad 7 0.75</code> has P1 = 7 and P2 = 0.75; an axis on P2 reads 0.75.</p>"
                + _good([
                    "Text counts as a number when it is one: \"1\" and 1 are the same. Other text presses a Button (empty text releases it).",
                    "True presses and False releases a Button.",
                    "The delay is the input's own, or the <b>Server</b> tab's default.",
                    "A new press restarts the release delay, so a held key that keeps sending stays pressed."
                ]),
            related: ["osc-add-input", "osc-encoder", "osc-tech-in", "osc-tech-samples"]
        },
        {
            id: "osc-encoder",
            section: inputs,
            title: "OSC encoders",
            body: "<p>An <b>Encoder</b> input reads a knob that turns without end, such as a Stream Deck+ dial.</p>"
                + _list([
                    "<b>Format:</b> <b>Auto</b> works it out from what arrives: only 1 and 0 mean clockwise and counter-clockwise; once a negative or any other value arrives, it reads +n and −n from then on. Choose <b>1 = clockwise, 0 = counter-clockwise</b> or <b>+n and −n</b> to set it yourself.",
                    "<b>+n and −n</b>: the value is how many steps it turned, + clockwise and − counter-clockwise. <code>/knob 3</code> is 3 steps clockwise; <code>/knob -1</code> one step back.",
                    "<b>Output:</b> <b>Axis</b> moves an axis by the <b>Step size:</b> (0.05 unless you change it, up to 2) for each step, and stops at the ends.",
                    "<b>Output:</b> <b>Pulses clockwise</b> or <b>Pulses counter-clockwise</b> makes a button that presses, and releases after <b>Release after:</b> (100 ms unless you change it), once for each step that way. Turn the knob fast and the pulses queue (up to 32)."
                ])
                + _good([
                    "For both directions as buttons, add two inputs on the same address: one with Pulses clockwise and one with Pulses counter-clockwise.",
                    "Import's E suffix makes an Encoder axis with Format Auto."
                ]),
            related: ["osc-modes", "osc-capture-import", "osc-tech-in"]
        },
        {
            id: "osc-value-types",
            section: inputs,
            title: "OSC value types",
            body: "<p>Every OSC value has a type. The program reads all the common ones and lets you choose what it sends.</p>"
                + _table(["Type", "Reads as", "Sent when you choose"], [
                    ["Integer (whole number)", "a number", "<b>Int</b>"],
                    ["Float (decimal)", "a number", "<b>Float</b>"],
                    ["True / False", "1 / 0", "<b>Bool</b>"],
                    ["Text", "a number when it is one, else text", "<b>Text</b>"],
                    ["None", "no value at that place", "–"]
                ])
                + "<p><b>Auto</b> sends the type last received on that address at that place (capitals don't matter), and Float when nothing has come there yet. In Feedback, text such as a mode name is always sent as text.</p>"
                + _good([
                    "Many apps need a set type: Companion's key color wants numbers, a text field wants Text. Choose the type the receiving app expects.",
                    "Exact type codes are in " + _link("osc-tech-in", "OSC values the program reads") + " and " + _link("osc-tech-out", "OSC values the program sends") + "."
                ]),
            related: ["osc-tech-in", "osc-tech-out", "configuration-actions-send-osc"]
        },

        // ---- Sending OSC ----
        {
            id: "osc-send",
            section: sending,
            title: "Send OSC from an input",
            body: "<p>To send a message when you press a button or move an axis, add the " + _link("configuration-actions-send-osc", "Send OSC") + " action to it. It sends to a target from the <b>Output</b> tab, or to <b>Reply to sender</b>.</p>"
                + "<p>To keep a device in step with the program's state instead, use " + _link("osc-feedback-tab", "Feedback") + ": it sends only when something changes.</p>",
            related: ["configuration-actions-send-osc", "osc-output-tab", "osc-feedback-tab"]
        },
        {
            id: "osc-feedback-how",
            section: sending,
            title: "How Feedback sends",
            body: "<p>While the profile runs, the program checks every Feedback row's source every 10 ms.</p>"
                + _list([
                    "A row sends when its value changes. An unchanged value is not sent again.",
                    "Each address sends at most the set number of messages a second (50 unless you change it). A value held back goes out as soon as the limit allows, always the newest one.",
                    "Every row sends again at <b>Run start</b>, <b>Mode change</b> and <b>Profile switch</b>, when ticked.",
                    "A message to the sync address (\"/gremlin/sync\" unless you change it) sends every row again. Rows set to <b>Reply to sender</b> go to the device that asked. The sync message never reaches an input; the OSC Monitor lists it with Sync.",
                    "If a send can't go out (output off, or nobody to reply to yet), the row sends once it can."
                ])
                + _good([
                    "A device that starts after the program can send the sync address to get the whole state."
                ]),
            related: ["osc-feedback-tab", "osc-tech-timing", "osc-companion"]
        },
        {
            id: "osc-monitor",
            section: sending,
            title: "Watch messages with the OSC Monitor",
            body: "<p>The <b>OSC Monitor</b> lists the last 200 OSC messages in and out. Use it to see what an app really sends.</p>"
                + "<p>Choose <b>Monitor</b> on the OSC page, or <b>Tools › OSC Monitor</b>.</p>"
                + _list([
                    "Columns: <b>Time</b>, <b>In / Out</b>, <b>Address</b>, <b>Values</b>, <b>From / To</b> (the other side's address and port) and <b>Input</b> (the inputs it matched, or no input). Point at a cut-off address to see it whole.",
                    "<b>Pause</b> stops adding new messages; <b>Resume</b> shows them again. <b>Clear</b> empties the list. Type in the filter to show only matching rows.",
                    "<b>Show outgoing</b>: also lists what the program sends (Send OSC and Feedback). On unless you turn it off.",
                    "On a no input row, <b>Add as Input…</b> opens Add with the address and values filled in.",
                    "A sync message shows with Sync in the <b>Input</b> column."
                ])
                + _good([
                    "While the Monitor is open, the port stays open, also when the profile isn't running. Close it to free the port.",
                    "Incoming addresses show in lower case."
                ]),
            related: ["osc-add-input", "osc-troubleshooting", "osc-tech-network"]
        },

        // ---- How to ----
        {
            id: "osc-companion",
            section: howto,
            title: "Use with Companion",
            body: "<p>Bitfocus Companion (version 3 or later, with the Generic OSC connection) works with the program in both directions.</p>"
                + "<h4>Stream Deck key presses an input</h4>"
                + _steps([
                    "On the OSC page, choose <b>Copy for Companion</b> in an input's menu and paste the text somewhere to read: it lists the settings below for that input.",
                    "In Companion, add a <i>Generic OSC</i> connection. <i>Target Hostname or IP</i>: 127.0.0.1 if Companion runs on this PC, else an address from the <b>Server</b> tab. <i>Target Port</i>: 8001 (the program's <b>Port</b>). <i>Protocol</i>: UDP.",
                    "On a key, add a press action <i>Send integer</i> with path <code>/sd/fire</code> and value 1, and a release action <i>Send integer</i> <code>/sd/fire</code> value 0.",
                    "In the program, <b>Add</b> › <b>Listen</b>, press the key, choose <b>Button</b>, <b>OK</b>."
                ])
                + "<p>Other Companion sends work too: float (Axis), string (Message + data), several values (Source value P1, P2), boolean, no value (use Trigger on message, since there is no release), and rotary keys (Encoder).</p>"
                + "<h4>Show the program's state on keys</h4>"
                + _steps([
                    "In Companion: <i>Settings › OSC</i>, turn on the <i>OSC Listener</i> (off unless you turn it on; port 12321).",
                    "In Companion, create a custom variable, for example gremlin_mode.",
                    "In the program, <b>OSC Setup…</b> › <b>Output</b>: <b>Add Companion</b>.",
                    "On the <b>Feedback</b> tab, choose <b>Add Row</b> › <b>Companion</b> › <b>Custom variable…</b> and keep gremlin_mode. The row sends <b>Current mode</b> to the Companion target at <code>/custom-variable/gremlin_mode/value</code> as <b>Text</b>.",
                    "In Companion, put <code>$(custom:gremlin_mode)</code> in a key's text, or use it in an expression feedback to color the key.",
                    "Run the profile. The key shows the mode name."
                ])
                + _good([
                    "Custom variables must exist in Companion first; Companion ignores unknown names without a word.",
                    "Key text and Key color change the key's saved style for good; custom variables don't, so they are the cleaner route.",
                    "Companion has no OSC command to change pages or to add to a variable: use a Companion key with its own page action, and send whole values.",
                    "<b>Reply to sender</b> reaches Companion only when its Generic OSC connection has <i>Listen for Feedback</i> on with a source port. Use any free port but 8001.",
                    "Companion can't send doubles or bundles, and matches addresses exactly. The program reads everything it sends."
                ]),
            related: ["osc-feedback-tab", "osc-output-tab", "osc-tech-companion", "osc-q-companion"]
        },
        {
            id: "osc-touchosc",
            section: howto,
            title: "Use with TouchOSC or a phone app",
            body: "<p>Phone and tablet apps such as TouchOSC send OSC over Wi-Fi.</p>"
                + _steps([
                    "Put the phone and the PC on the same network.",
                    "In the app's OSC connection, set the host to this PC's address (from the <b>Server</b> tab, <b>Copy</b>) and the send port to the program's <b>Port</b> (8001).",
                    "Set the app's receive port, for example 9000, if you want feedback.",
                    "In the program, <b>Add</b> › <b>Listen</b> and touch each control once, or tick <b>Bulk capture</b> and touch them all. Faders and XY pads are <b>Axis</b>; their range is usually 0 to 1.",
                    "For feedback, add a target with the phone's address and the app's receive port on the <b>Output</b> tab, or use <b>Reply to sender</b> when the app sends from the port it listens on.",
                    "Add Feedback rows that send to the same addresses the controls use, so faders and buttons follow the program."
                ])
                + _good([
                    "A phone's address can change; a fixed address set in the router helps.",
                    "An XY pad sends two values: add two Axis inputs on the same address, one on P1 and one on P2."
                ]),
            related: ["osc-checklist", "osc-modes", "osc-feedback-tab"]
        },
        {
            id: "osc-test",
            section: howto,
            title: "Test OSC without a device",
            body: "<p>The program's source folder has a small sender, <code>tools/osc_send.py</code>, that sends messages to 127.0.0.1 port 8001. Run it from PowerShell or a command prompt.</p>"
                + _table(["To test", "Command"], [
                    ["Button", "<code>python tools/osc_send.py press /btn/1 --hold 0.5</code>"],
                    ["Button by hand", "<code>python tools/osc_send.py send /btn/1 1</code>, then <code>… send /btn/1 0</code>"],
                    ["Trigger on message", "<code>python tools/osc_send.py tap /fire</code>"],
                    ["Axis 0 to 1", "<code>python tools/osc_send.py sweep /fader/1 --from 0 --to 1 --steps 20</code>"],
                    ["Change", "<code>python tools/osc_send.py send /mode 1</code>, then <code>… send /mode 2</code>"],
                    ["Message + data", "<code>python tools/osc_send.py send /scene 3 go</code>"],
                    ["Source P2", "<code>python tools/osc_send.py send /pad 7 0.75</code>"],
                    ["Feedback sync", "<code>python tools/osc_send.py send /gremlin/sync</code>"],
                    ["Another PC or port", "add <code>--host 192.168.1.20 --port 8001</code> before the command"]
                ])
                + _good([
                    "Numbers become int or float values; anything else is sent as text.",
                    "<code>--dry-run</code> prints the message and sends nothing.",
                    "Keep the <b>OSC Monitor</b> open to see each message arrive."
                ]),
            related: ["osc-monitor", "osc-modes", "osc-tech-samples"]
        },
        {
            id: "osc-checklist",
            section: howto,
            title: "Connection checklist",
            body: "<p>Check these in order when connecting any OSC app.</p>"
                + _steps([
                    "This PC's address and port: <b>OSC Setup…</b> › <b>Server</b>, under <b>Use one of these in your app:</b> and <b>Port</b> (8001).",
                    "Same network: the app's device and this PC are on the same network (or the app runs on this PC: use 127.0.0.1).",
                    "Firewall: Windows may ask once to let the program receive on the network. Allow it for private networks. If you said no, allow UDP in on the port in Windows Defender Firewall.",
                    "The app sends to that address and port, over UDP.",
                    "Something opens the port: a running profile with OSC inputs that have actions, Listen, Bulk capture or the OSC Monitor.",
                    "To send back: the program's target is the device's own address and the port the app listens on (not 8001).",
                    "Watch the <b>OSC Monitor</b>: In rows prove messages arrive; Out rows show what is sent and where."
                ]),
            related: ["osc-tech-network", "osc-troubleshooting", "osc-monitor"]
        },
        {
            id: "osc-troubleshooting",
            section: howto,
            title: "When OSC doesn't work",
            body: "<h4>Nothing arrives</h4>"
                + _list([
                    "Open the <b>OSC Monitor</b>. It opens the port, so if nothing shows there, the messages don't reach this PC.",
                    "Check the app's host and port against the <b>Server</b> tab, and that <b>Listen for OSC messages</b> is on.",
                    "Check the firewall (see " + _link("osc-checklist", "Connection checklist") + ").",
                    "\"Could not bind OSC on host:port.\": another program uses that port. Close it or choose another <b>Port</b> (and set the same in the app).",
                    "A typed <b>Host</b> that isn't this PC's current address can't listen. Leave it blank."
                ])
                + "<h4>Messages arrive, but nothing happens</h4>"
                + _list([
                    "The Monitor's <b>Input</b> says no input: the address (or data) doesn't match an input. Use <b>Add as Input…</b>.",
                    "The profile isn't running, or the open profile gives the OSC inputs no actions: with no OSC inputs in use, Run doesn't open the port.",
                    "A Button that never releases: the app sends only on press. Tick <b>Trigger on message</b>."
                ])
                + "<h4>Companion doesn't update</h4>"
                + _list([
                    "Companion's <i>OSC Listener</i> is off (Settings › OSC), or the custom variable doesn't exist yet.",
                    "The Feedback row sends to <b>Reply to sender</b> but Companion's Generic OSC connection has <i>Listen for Feedback</i> off: send to the Companion target (port 12321) instead.",
                    "<b>OSC output (Send OSC actions and feedback)</b> or <b>Send feedback to OSC devices</b> is off, or the profile isn't running."
                ]),
            related: ["osc-checklist", "osc-monitor", "osc-companion", "osc-tech-network"]
        },

        // ---- Technical reference ----
        {
            id: "osc-tech-network",
            section: tech,
            title: "OSC network and ports",
            body: "<p>Exact facts for setting up a connection.</p>"
                + _table(["Item", "Value"], [
                    ["Protocol", "OSC 1.0 over UDP (IPv4). No TCP, no SLIP."],
                    ["Listens on", "<b>Host</b> blank = 0.0.0.0 (every address of this PC); else the typed IP address or name"],
                    ["Listening port", "8001 unless you change it (1 to 65535)"],
                    ["Default target", "127.0.0.1 port 8000"],
                    ["Companion target", "127.0.0.1 port 12321 (<b>Add Companion</b>)"],
                    ["Reply to sender", "the IP address and source port of the last message received"],
                    ["Sends from", "a port chosen by Windows for each target"],
                    ["Discovery service type", "<code>_osc._udp.local.</code>"],
                    ["Announced name", "Gremlin-Platforms on <i>PC name</i>, on the listening port"]
                ])
                + "<h4>When the port is open</h4>"
                + _list([
                    "While a profile runs that uses OSC inputs (they have actions or are assigned to the Logical Device).",
                    "During Listen (until its message arrives or <b>Stop</b>) and while <b>Bulk capture</b> is ticked.",
                    "While the OSC Monitor is open.",
                    "Never while <b>Listen for OSC messages</b> is off. At Stop and at quit, the port closes."
                ])
                + _good([
                    "Windows Defender Firewall may ask once for inbound UDP when the port first opens.",
                    "Two programs can't listen on the same UDP port on one PC."
                ]),
            related: ["osc-checklist", "osc-server-tab", "osc-output-tab", "osc-discovery-tab"]
        },
        {
            id: "osc-tech-addresses",
            section: tech,
            title: "OSC address rules",
            body: _list([
                    "An address must start with \"/\" and can't be blank, for example <code>/sd/fire</code>.",
                    "Matching ignores capitals: <code>/Fire</code> and <code>/fire</code> are the same input. Incoming addresses are made lower case on arrival.",
                    "The whole address must match exactly. OSC patterns (<code>*</code>, <code>?</code>, <code>[ ]</code>, <code>{ }</code>) are not expanded: they are plain characters.",
                    "In Message + data, the values must match too: the same number of values, numbers compared as numbers (\"1\" equals 1.0), anything else as exact text. True and False compare as the text True and False.",
                    "Bundles are unpacked and each message in them handled in turn. A bundle with a time tag in the future waits until that time.",
                    "The address <code>/noop</code> is ignored.",
                    "The sync address (\"/gremlin/sync\" unless you change it) is matched without regard to capitals, answered by Feedback and never reaches an input, also while the profile isn't running."
                ]),
            related: ["osc-tech-in", "osc-modes", "osc-tech-samples"]
        },
        {
            id: "osc-tech-in",
            section: tech,
            title: "OSC values the program reads",
            body: _table(["Type tag", "Type", "Read as"], [
                    ["<code>i</code>, <code>h</code>", "int32, int64", "number"],
                    ["<code>f</code>, <code>d</code>", "float32, float64 (double)", "number"],
                    ["<code>s</code>", "string", "a number when the text is one, else text"],
                    ["<code>T</code>, <code>F</code>", "true, false", "1 and 0"],
                    ["<code>N</code>", "nil", "no value at that place"],
                    ["<code>b</code>, <code>t</code>, <code>r</code>, <code>m</code>, arrays", "blob, time tag, color, MIDI, <code>[ ]</code>", "not a number: an Axis ignores it, a Button presses"]
                ])
                + "<p>Other type tags are skipped, and values after them may read wrongly: avoid them.</p>"
                + "<h4>By mode</h4>"
                + _list([
                    "Button: the value at the source; 0 (or False, or empty text) releases, anything else presses. No value: press, then release after the delay (250 ms unless you change it), or press and hold when auto-release is off.",
                    "Axis: (value − Min) ÷ (Max − Min) × 2 − 1, so Min gives −1 and Max gives +1; outside the range it stays at −1 or +1. Not a number: ignored. Min must be less than Max.",
                    "Change: compares with this input's last value, numbers as numbers, else as text; the first message counts as a change.",
                    "Encoder 1 = clockwise, 0 = counter-clockwise: 0 turns back, anything else turns forward one step. +n and −n: the number is the steps. Auto starts as 1/0 and switches for good to +n/−n when a value other than 0 or 1 arrives.",
                    "Pad address-only messages: a message with no value reads as 1.0."
                ]),
            related: ["osc-modes", "osc-encoder", "osc-tech-out", "osc-value-types"]
        },
        {
            id: "osc-tech-out",
            section: tech,
            title: "OSC values the program sends",
            body: _table(["Type chosen", "Type tag sent", "Notes"], [
                    ["<b>Int</b>", "<code>i</code> (<code>h</code> past 32 bits)", "rounded to a whole number"],
                    ["<b>Float</b>", "<code>f</code>", "32-bit float; never a double"],
                    ["<b>Bool</b>", "<code>T</code> or <code>F</code>", "no data bytes; text true, yes, on is True; false, no, off or blank is False; a number is True unless 0"],
                    ["<b>Text</b>", "<code>s</code>", "Numbers as short text, for example 1 or 0.5 (Feedback and Send OSC alike); a fixed Send OSC value goes as typed"],
                    ["<b>Auto</b>", "as last received on that address (any capitals) and place; past the last value received, the last value's type", "<code>f</code> when nothing has come there"]
                ])
                + _list([
                    "Every message is one UDP packet with one message; the program never sends bundles.",
                    "A value that can't be turned into the chosen type is sent as text.",
                    "Feedback: a button sends Max when pressed and Min when released; an axis sends Min..Max for −1..+1; a hat sends its direction's name as text; the mode sends its name as text.",
                    "Nothing is sent while the profile isn't running or while <b>OSC output (Send OSC actions and feedback)</b> is off."
                ]),
            related: ["osc-value-types", "configuration-actions-send-osc", "osc-feedback-how"]
        },
        {
            id: "osc-tech-timing",
            section: tech,
            title: "OSC timing and limits",
            body: _table(["Setting", "Default", "Range"], [
                    ["Auto-release delay (address-only, Trigger on message, Change, Message + data)", "250 ms", "0 to 10000 ms"],
                    ["Encoder pulse <b>Release after:</b>", "100 ms", "0 to 10000 ms"],
                    ["Feedback messages per second per address", "50", "1 or more"],
                    ["Feedback source check", "every 10 ms", "–"],
                    ["Encoder step size", "0.05", "above 0, up to 2"],
                    ["Encoder pulses waiting", "–", "up to 32"],
                    ["OSC Monitor list", "last 200 messages", "–"],
                    ["Sync address", "/gremlin/sync", "on unless you turn it off"]
                ]),
            related: ["osc-feedback-how", "osc-server-tab", "osc-encoder"]
        },
        {
            id: "osc-tech-companion",
            section: tech,
            title: "Companion OSC addresses",
            body: "<p>Companion's own OSC listener (port 12321) takes these addresses. The program's Companion templates use the first three.</p>"
                + _table(["Address", "Values", "Effect"], [
                    ["<code>/custom-variable/</code><i>name</i><code>/value</code>", "one text or number", "sets the custom variable (it must exist)"],
                    ["<code>/location/</code><i>page</i>/<i>row</i>/<i>column</i><code>/style/text</code>", "one value", "sets the key's text (kept)"],
                    ["<code>/location/</code><i>page</i>/<i>row</i>/<i>column</i><code>/style/bgcolor</code>", "r g b (0–255) or text \"#ff0000\"", "sets the key's background color (kept)"],
                    ["<code>/location/</code><i>page</i>/<i>row</i>/<i>column</i><code>/style/color</code>", "r g b or \"#ff0000\"", "sets the key's text color (kept)"],
                    ["<code>/location/</code><i>page</i>/<i>row</i>/<i>column</i><code>/press</code>, <code>/down</code>, <code>/up</code>", "none", "presses a key"],
                    ["<code>…/rotate-left</code>, <code>…/rotate-right</code>", "none", "turns an encoder key"]
                ])
                + _good([
                    "Pages count from 1; rows and columns from 0.",
                    "Companion's OSC Listener is off unless you turn it on."
                ]),
            related: ["osc-companion", "osc-feedback-tab", "osc-tech-out"]
        },
        {
            id: "osc-tech-samples",
            section: tech,
            title: "Sample OSC messages",
            body: _table(["Address", "Type tags", "Values", "Effect"], [
                    ["<code>/fire</code>", "<code>,i</code>", "1", "Button input presses"],
                    ["<code>/fire</code>", "<code>,i</code>", "0", "Button input releases"],
                    ["<code>/fire</code>", "<code>,</code>", "(none)", "Button input presses, then releases after 250 ms"],
                    ["<code>/gear</code>", "<code>,T</code>", "True", "Button input presses"],
                    ["<code>/throttle</code>", "<code>,f</code>", "0.75", "Axis (Min 0, Max 1) moves to 0.5 (three quarters along)"],
                    ["<code>/pad</code>", "<code>,if</code>", "7 0.75", "Axis on P2 reads 0.75"],
                    ["<code>/scene</code>", "<code>,is</code>", "3 go", "Message + data input with Data 3 go presses"],
                    ["<code>/knob</code>", "<code>,i</code>", "-2", "Encoder (+n and −n) turns 2 steps counter-clockwise"],
                    ["<code>/gremlin/sync</code>", "<code>,</code>", "(none)", "Feedback sends every row again"],
                    ["<code>/custom-variable/gremlin_mode/value</code>", "<code>,s</code>", "Flight", "sent to Companion: the mode name"]
                ]),
            related: ["osc-modes", "osc-tech-in", "osc-test"]
        },

        // ---- Good to know ----
        {
            id: "osc-good-to-know",
            section: "More about OSC",
            title: "Good to know about OSC",
            body: _list([
                    "At <b>Stop</b>, any OSC button still held is released before the profile stops.",
                    "Profiles from older versions keep working: their OSC inputs are added to OSC's list the first time you open them, and a copy of the old file is kept beside it when you first save.",
                    "OSC's inputs, settings, targets and Feedback rows travel with Save to Device Library, Restore, Export and Device Pack, and every save is in History.",
                    "The port opens only when something needs it, and closes again after.",
                    "Deleting an input asks first; you can restore it from Tools › History."
                ]),
            related: ["osc-about", "osc-tech-network", "device-library-built-in", "tools-history"]
        },

        // ---- Common questions ----
        {
            id: "osc-q-nothing",
            section: questions,
            title: "Why does nothing happen when my app sends OSC?",
            body: "<p>Open the <b>OSC Monitor</b>. If nothing shows, check the address, port and firewall; if the Input column says no input, add an input for that address. See " + _link("osc-troubleshooting", "When OSC doesn't work") + ".</p>",
            related: ["osc-troubleshooting", "osc-monitor"]
        },
        {
            id: "osc-q-companion",
            section: questions,
            title: "Why doesn't Companion show the mode?",
            body: "<p>Companion's OSC Listener must be on, the custom variable must exist, and the Feedback row must send to the Companion target. See " + _link("osc-companion", "Use with Companion") + ".</p>",
            related: ["osc-companion", "osc-troubleshooting"]
        },
        {
            id: "osc-q-stuck",
            section: questions,
            title: "Why does my OSC button stay pressed?",
            body: "<p>The app sends a press but never a 0. Tick <b>Trigger on message</b> on the input, so it releases after the delay. See " + _link("osc-modes", "OSC input modes and data styles") + ".</p>",
            related: ["osc-modes"]
        },
        {
            id: "osc-q-axis",
            section: questions,
            title: "Why can't I change an OSC input to Axis?",
            body: "<p>It has actions made for a button. Remove its actions first, then change the mode. See " + _link("osc-edit-inputs", "Change, sort or delete OSC inputs") + ".</p>",
            related: ["osc-edit-inputs"]
        }
    ]
}
