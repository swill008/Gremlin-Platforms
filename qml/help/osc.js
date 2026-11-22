// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: OSC. Its settings, inputs, sending, Feedback, the OSC
// Monitor, how-tos and the technical reference. Written to
// claude/plans/help-style-guide.md: each topic opens with what it's for,
// then "How to", "What you see" and "Good to know" (empty sections left out).

.pragma library

var chapter = { id: "osc", title: "OSC" }

function _good(items) {
    return "<h4>Good to know</h4>" + _list(items)
}

function _howto(items) {
    return "<h4>How to</h4>" + _steps(items)
}

function _see(items) {
    return "<h4>What you see</h4>" + _list(items)
}

function _link(id, title) {
    return "<a href=\"topic:" + id + "\">" + title + "</a>"
}

// A "Show me ›" link to a menu item, toolbar button or setting.
function _show(target) {
    return " <a href=\"show:" + target + "\">Show me ›</a>"
}

// Options finds the OSC line by its setting's name, "Module setup".
var _oscOption = "Module setup"

function _list(items) {
    return "<ul><li>" + items.join("</li><li>") + "</li></ul>"
}

function _steps(items) {
    return "<ol><li>" + items.join("</li><li>") + "</li></ol>"
}

// Plain table markup: the style block in DialogHelp.qml gives every table
// the same look and a natural width.
function _table(head, rows) {
    var html = "<table><tr>"
    for (var i = 0; i < head.length; ++i)
        html += "<th>" + head[i] + "</th>"
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
    var portRule = _link("osc-tech-network", "When the port is open")
    return [
        // ---- OSC ----
        {
            id: "osc-about",
            section: main,
            title: "OSC and the program",
            body: "<p>OSC (Open Sound Control) lets apps and devices send short messages over your network. Stream Decks (through Bitfocus Companion), phone apps such as TouchOSC, lighting desks and music software use it.</p>"
                + "<p>The program reads OSC messages as button presses and axis moves. It can also send OSC messages back.</p>"
                + "<h4>What you see</h4>"
                + _list([
                    "Each message has an <i>address</i> such as <code>/fire</code>, and zero or more <i>values</i> such as <code>1</code> or <code>0.75</code>.",
                    "OSC is one of the program's internal inputs, like the Keyboard. Its page lists one input per address you use.",
                    "You give each OSC input actions, like any button or axis.",
                    "OSC's inputs and settings are shared by every profile.",
                    "The program listens on a network port (default 8001). Your app sends to this PC's address and that port.",
                    "The program sends with the " + _link("device-bindings-actions-send-osc", "Send OSC") + " action and with " + _link("osc-feedback-tab", "Feedback") + ", which shows the program's state on your device.",
                    "All OSC settings are in one window, OSC's <b>Module Setup</b>, opened with <b>OSC Setup…</b> on the OSC page. See " + _link("osc-setup-window", "Open OSC's Module Setup") + "."
                ])
                + _good([
                    "Start with " + _link("options-profile-osc", "Set up OSC") + ".",
                    "To make a connection by hand, see " + _link("osc-checklist", "Connection checklist") + "."
                ]),
            related: ["options-profile-osc", "osc-add-input", "osc-checklist", "osc-companion"]
        },
        {
            id: "options-profile-osc",
            section: main,
            title: "Set up OSC",
            body: "<p>These steps get messages from an app into the program in a few minutes.</p>"
                + _howto([
                    "On <b>Home</b>, double-click the <b>OSC</b> card to open the OSC page.",
                    "Choose <b>OSC Setup…</b>. On the <b>Server</b> tab, check that <b>Listen for OSC messages</b> is on.",
                    "Note this PC's address and the <b>Port</b> (default 8001). <b>Copy</b> copies both.",
                    "In your app, set the OSC destination to that address and port. If the app runs on this PC, use 127.0.0.1.",
                    "On the OSC page, right-click the list and choose <b>Add Inputs › Listen</b>.",
                    "Press the button or move the control in your app once. Its address fills in.",
                    "Choose the mode (<b>Button</b>, <b>Axis</b>, <b>Change</b> or <b>Encoder</b>), then <b>OK</b>.",
                    "The new input opens in the action pane. Choose <b>Add Action</b> and add an action, for example Map to vJoy.",
                    "Choose <b>Run</b>" + _show("toolbar/Run") + ". Your app's messages now run the actions."
                ])
                + _good([
                    "Nothing arriving? Watch the " + _link("osc-monitor", "OSC Monitor") + " and see " + _link("osc-troubleshooting", "When OSC doesn't work") + ".",
                    "To show the program's state on the device too, see " + _link("osc-feedback-tab", "Feedback tab") + ".",
                    "In Options, the OSC line has a button, <b>Open OSC Module Setup</b>" + _show("option/" + _oscOption) + ", that opens OSC's Module Setup too."
                ]),
            related: ["osc-about", "osc-server-tab", "osc-add-input", "osc-checklist"]
        },
        {
            id: "osc-card-line",
            section: main,
            title: "The OSC card on Home",
            body: "<p>The OSC card's second line shows what the OSC server is doing.</p>"
                + _see([
                    "\"Listening on 192.168.1.5:8001\": the port is open on that address. With <b>Host</b> blank it reads \"Listening on all addresses, port 8001\".",
                    "\"From 192.168.1.20: /fire 1\": a message arrived, with its sender, address and first value. Long text ends with \"…\".",
                    "\"Server not started: port 8001 is in use\", in the warning color: the port couldn't be opened.",
                    "\"Not listening (Listen for OSC messages is off)\": OSC input is turned off on the <b>Server</b> tab.",
                    "\"Not listening yet\": shown for a moment while the program starts."
                ])
                + _good([
                    "The line goes back to \"Listening on …\" 3 seconds after the last message.",
                    "\"Server not started\" can also say the address isn't one of this PC's, or that Windows refused the port.",
                    "\"Server not started\" stays until the server starts, for example after you change the <b>Port</b> or <b>Host</b>.",
                    "Point at the card's title to see OSC's full name. It also shows in grey under the title of the OSC page.",
                    "For a failure, see " + _link("osc-troubleshooting", "When OSC doesn't work") + "."
                ]),
            related: ["osc-about", "osc-server-tab", "osc-troubleshooting", "osc-monitor"]
        },

        // ---- OSC Setup ----
        {
            id: "osc-setup-window",
            section: setup,
            title: "Open OSC's Module Setup",
            body: "<p>All OSC settings are in one window with four tabs, OSC's <b>Module Setup</b>. This Help always calls it that. Its title bar says <b>Input Module Setup</b>, and the buttons that open it say <b>OSC Setup…</b>, <b>Module Setup…</b> and <b>Open OSC Module Setup</b>: all three open the same window.</p>"
                + _howto([
                    "On the OSC page, choose <b>OSC Setup…</b>.",
                    "Or, on Home, right-click the <b>OSC</b> card and choose <b>Module Setup…</b>.",
                    "Or, in Options, choose <b>Open OSC Module Setup</b>" + _show("option/" + _oscOption) + "."
                ])
                + _see([
                    _link("osc-server-tab", "Server") + ": where the program listens.",
                    _link("osc-output-tab", "Output") + ": where the program sends.",
                    _link("osc-feedback-tab", "Feedback") + ": the program's state sent to your devices.",
                    _link("osc-discovery-tab", "Discovery") + ": finding OSC devices on your network."
                ])
                + _good([
                    "Changes take effect at once, also while the profile runs.",
                    "A change here or on the OSC page marks the profile changed (<b>*</b> in the title).",
                    "<b>File › Save Profile</b>" + _show("menu/File/Save Profile") + " (Ctrl+S) saves the OSC changes too. <b>Discard</b> throws them away.",
                    "OSC's settings travel with Save to Device Library, Restore, Export and Export / Import Device.",
                    "<a href=\"topic:tools-history\">History</a> keeps every save of OSC's settings."
                ]),
            related: ["osc-server-tab", "osc-output-tab", "osc-feedback-tab", "osc-discovery-tab"]
        },
        {
            id: "osc-server-tab",
            section: setup,
            title: "Server tab",
            body: "<p>The <b>Server</b> tab sets where and how the program listens for OSC messages.</p>"
                + _see([
                    "<b>Listen for OSC messages</b>: turns OSC input on (on by default). While it is on, the port stays open as long as the program is open. Turn it off to close the port at once.",
                    "<b>Host</b>: leave it blank (<b>All addresses on this PC</b>) to listen on every network address of this PC. This keeps working when the PC's address changes.<ul>"
                        + "<li>Or type one IP address or computer name to listen only there. The program checks it before saving.</li></ul>",
                    "<b>Port</b>: the UDP port your app sends to (default 8001). UDP is the kind of network message OSC uses.",
                    "<b>Use one of these in your app:</b> this PC's addresses with the port, for example 192.168.1.10:8001. <b>Copy</b> copies one.",
                    "<b>Auto-release address-only messages after … ms</b>: some apps send only an address with no value, for example <code>/fire</code>.<ul>"
                        + "<li>When this is ticked, such a message presses a Button input and releases it after the delay.</li>"
                        + "<li>When it is unticked, the button stays pressed.</li>"
                        + "<li>Ticked by default, with 250 ms (from 0 to 10000).</li>"
                        + "<li>Change and Message + data inputs use the same delay.</li>"
                        + "<li>An input's own <b>Trigger on message</b> setting overrides this one.</li></ul>",
                    "<b>Pad address-only messages</b>: treats a message with no value as the value 1.0. A Button then stays pressed until the app sends 0. Off by default.",
                    "<b>Allowed senders</b>: OSC is accepted only from the addresses listed. Empty (the default) accepts every sender. See " + _link("osc-allow-senders", "Accept OSC only from some senders") + "."
                ])
                + _good([
                    "For when the port opens and closes, see " + portRule + ".",
                    "If the port can't be opened, the program shows \"Could not bind OSC on host:port.\" when it starts. Usually another program uses the port.",
                    "That error names the other program when Windows can tell. The rest of the profile still runs, and the error is also written to the log."
                ]),
            related: ["osc-setup-window", "osc-output-tab", "osc-tech-network", "osc-troubleshooting"]
        },
        {
            id: "osc-output-tab",
            section: setup,
            title: "Output tab",
            body: "<p>The <b>Output</b> tab sets where the program sends OSC messages: the " + _link("device-bindings-actions-send-osc", "Send OSC") + " action and " + _link("osc-feedback-tab", "Feedback") + ".</p>"
                + _howto([
                    "To add a target, fill in the row below the list: <b>Name</b>, <b>IP address or computer name</b> and the port (default 8000).",
                    "Choose <b>Add Target</b>.",
                    "To change a target, choose <b>Edit</b>, change the row, then <b>Save Target</b> (or <b>Cancel</b>).",
                    "To remove a target, choose <b>Remove</b>. It asks first."
                ])
                + _see([
                    "<b>OSC output (Send OSC actions and feedback)</b>: the main switch for everything OSC sends (on by default). When it is off, nothing is sent.",
                    "<b>Reply to sender</b>: lets a Send OSC action or a Feedback row reply to whoever sent the last message. On by default.",
                    "<b>Targets</b>: the places OSC sends to, each with a name, a host and a port. The first, <b>Default</b>, is 127.0.0.1 port 8000.",
                    "<b>Add Companion</b>: adds a target named Companion at 127.0.0.1 port 12321, the port Companion listens on. If it already exists, it is updated.",
                    "<b>Check Companion setup</b>: checks what Companion needs and changes nothing. Each line says <b>OK</b>, or <b>Fix</b> with what to change.<ul>"
                        + "<li>It checks that OSC is on and the port is open, and that OSC output is on.</li>"
                        + "<li>It checks for a Companion target on port 12321. Another port is marked <b>Check</b>, since you may have changed it in Companion.</li>"
                        + "<li>When you have Feedback rows, it checks that Feedback is on.</li></ul>"
                ])
                + _good([
                    "A target is the device's own address and the port it listens on, never this PC's.",
                    "Target names must differ. Renaming a target keeps the actions and Feedback rows that use it.",
                    "When you remove a target, the actions and rows that use it send nothing until you pick another. A Send OSC action shows <b>Missing target</b>.",
                    "See " + _link("osc-companion", "Use with Companion") + " for the whole Companion setup."
                ]),
            related: ["osc-setup-window", "device-bindings-actions-send-osc", "osc-feedback-tab", "osc-tech-out"]
        },
        {
            id: "osc-feedback-tab",
            section: setup,
            title: "Feedback tab",
            body: "<p>Feedback sends the program's state to your OSC device, so its keys, lights and faders can show it. Examples are the current mode, a vJoy button or whether the profile is paused.</p>"
                + "<p>You add and edit the rows on the OSC page (see " + _link("osc-feedback-rows", "Feedback rows on the OSC page") + "). This tab holds the switches for every row.</p>"
                + _see([
                    "<b>Send feedback to OSC devices</b>: turns Feedback on (on by default). With no rows it sends nothing.",
                    "<b>Send everything again at:</b> <b>Run start</b>, <b>Mode change</b> and <b>Profile switch</b>. At those moments every row's value is sent again, so the device shows the right state. All ticked by default.",
                    "<b>Send everything again when a message comes to</b> the sync address (default <code>/gremlin/sync</code>). A device can ask for every row again by sending to it. Ticked by default.",
                    "<b>At most … messages per second per address</b>: default 50, a whole number of 1 or more.",
                    "The list of rows, read-only: each row's <b>On</b> or <b>Off</b>, address, source and target. <b>Edit on the OSC page</b> takes you there.",
                    "<b>Companion custom variable…</b>: adds a row that sends the current mode's name to a Companion custom variable.<ul>"
                        + "<li>The default name is gremlin_mode, with no spaces.</li>"
                        + "<li>If there is no Companion target yet, it adds one.</li>"
                        + "<li>Create the variable in Companion first.</li></ul>"
                ])
                + _good([
                    "Feedback sends only while the profile runs and <b>OSC output (Send OSC actions and feedback)</b> is on.",
                    "On the OSC page, right-click empty space in the list and choose <b>Feedback settings…</b> to open this tab.",
                    "How rows send, step by step: " + _link("osc-feedback-how", "How Feedback sends") + "."
                ]),
            related: ["osc-feedback-rows", "osc-feedback-how", "osc-output-tab", "osc-companion"]
        },
        {
            id: "osc-discovery-tab",
            section: setup,
            title: "Discovery tab",
            body: "<p>The <b>Discovery</b> tab lets the program and OSC apps on your network find each other, so you don't have to type addresses.</p>"
                + _see([
                    "<b>Announce this PC</b>: lets OSC apps on your network find this PC and its port. Off by default.",
                    "<b>Find OSC devices</b>: lists the OSC apps on your network that announce themselves. Off by default.",
                    "<b>Add as Target</b>, beside each device found: adds it to the targets on the Output tab, with its name, address and port."
                ])
                + _good([
                    "Only apps that announce themselves are found. Many apps don't; add those as a target by hand.",
                    "\"Discovery is not available on this PC.\" means the program couldn't start network discovery here. Everything else works.",
                    "The technical names are in " + _link("osc-tech-network", "OSC network and ports") + "."
                ]),
            related: ["osc-output-tab", "osc-tech-network", "osc-checklist"]
        },

        // ---- OSC inputs ----
        {
            id: "osc-page",
            section: inputs,
            title: "The OSC page",
            body: "<p>The OSC page lists every OSC input, one row per input, titled by its address. It works like the Logical Device page.</p>"
                + "<h4>What each row shows</h4>"
                + _list([
                    "The address, and the custom name when you give one.",
                    "A short line with the input's settings, for example its mode and delay. A pattern input says how many addresses it has seen.",
                    "The live value: a button pressed or not, or an axis's position. It updates even when the profile isn't running.",
                    "When a message last arrived, for example \"last seen 3 s ago\", or \"never\".",
                    "<b>Invert</b>, on an axis input: turns the axis the other way.",
                    "The input's actions for the current mode as child rows, then its Feedback rows. Click a row to open it in the action pane."
                ])
                + "<h4>Menus and the page bar</h4>"
                + _list([
                    "Right-click an input for <b>Change Address…</b>, <b>Edit Settings…</b>, <b>Copy for Companion</b>, <b>Send Test…</b> and <b>Delete…</b>. See " + _link("osc-edit-inputs", "Change, order or delete OSC inputs") + ".",
                    "<b>Feedback</b> in the same menu: <b>Add Feedback</b> and <b>Companion feedback</b>.",
                    "<b>Add Inputs</b>: <b>Add…</b>, <b>Import…</b>, <b>From TouchOSC Layout…</b>, <b>Listen</b> and <b>Clear…</b>.",
                    "The menu also has the <b>Row</b>, <b>Group</b>, <b>Groups</b> and <b>Order</b> sections.",
                    "The page bar: <b>OSC Setup…</b> opens OSC's Module Setup, and <b>Monitor</b> shows the " + _link("osc-monitor", "OSC Monitor") + ".",
                    "<b>Appearance…</b> in the page bar sets how this page looks, apart from the Logical Device page."
                ])
                + "<h4>Find, groups and order</h4>"
                + _list([
                    "Find searches the address, the custom name and the group.",
                    "Its type box shows <b>All types</b>, <b>Buttons</b> or <b>Axes</b>.",
                    "Its filters show only <b>Ungrouped</b> inputs, inputs with <b>No bindings in this mode</b>, or <b>Patterns</b>.",
                    "Groups may hold buttons and axes together. Drag rows to set your own order."
                ])
                + "<h4>Undo and locking</h4>"
                + _list([
                    "The page has its own Undo and Redo for every change made on it.",
                    "The page is locked while the profile runs. Feedback rows are the exception: you can change them while it runs."
                ])
                + _good([
                    "A pressed OSC button tints its row. When the profile is stopped, the page also scrolls to the row and flashes it.",
                    "<b>Input highlighting</b> in Options turns the scrolling off. Faders and encoders only tint.",
                    "The page has no <b>Hide system name</b>: the address is the input and always shows.",
                    "The Device Mapping Editor and the OSC card show an OSC input by its address, for example /fire."
                ]),
            related: ["osc-add-input", "osc-edit-inputs", "osc-feedback-rows", "osc-monitor"]
        },
        {
            id: "osc-add-input",
            section: inputs,
            title: "Add an OSC input",
            body: "<p>An OSC input turns one kind of message into a button or an axis.</p>"
                + _howto([
                    "On the <b>OSC</b> page, right-click the list and choose <b>Add Inputs › Add…</b>. The <b>OSC Input Mapper</b> window opens.",
                    "Type the address under <b>OSC message:</b> (it starts with \"/\"). Or choose <b>Listen</b> and send one message from your app: the address and its values fill in.",
                    "Choose the <b>Action mode:</b> <b>Button</b>, <b>Axis</b>, <b>Change</b> or <b>Encoder</b>. See " + _link("osc-modes", "OSC input modes") + ".",
                    "Choose <b>Message only</b>, or <b>Message + data</b> to match the values in <b>Data:</b> too.",
                    "If the message has several values, choose which one to read in <b>Source value:</b> (P1, P2 …).",
                    "For an axis, set <b>Min:</b> and <b>Max:</b> (default 0 and 1). Under <b>Shaping</b>, add a deadzone if you want one.",
                    "For a button, tick <b>Trigger on message</b> to press and release on any message. Set its delay in ms (default 250).",
                    "Choose <b>OK</b>. The new input opens in the action pane; add its actions."
                ])
                + _good([
                    "While Listen waits, its <b>Listening for OSC</b> box shows where OSC listens and sends. <b>Stop</b> cancels.",
                    "Listen works even when the profile isn't running. Only the window that started Listen gets the message.",
                    "If OSC is off or the port can't be opened, Listen says \"Could not start OSC listener.\". Check the <b>Server</b> tab.",
                    "With <b>Allowed senders</b> set, Listen takes messages only from those senders.",
                    "Min must be less than Max. The 1/10s to 1s buttons fill in the delay.",
                    "Adding an input that already exists selects the one already there; it doesn't make a second one.",
                    "Several inputs can share an address when their data or source value differ, for example /pad with P1 and /pad with P2.",
                    "The address may be a pattern such as <code>/deck/*</code>. See " + _link("osc-patterns", "OSC address patterns") + ".",
                    "To add many at once, see " + _link("osc-capture-import", "Capture or import many addresses") + "."
                ]),
            related: ["osc-modes", "osc-capture-import", "osc-edit-inputs", "osc-patterns"]
        },
        {
            id: "osc-capture-import",
            section: inputs,
            title: "Capture or import many addresses",
            body: "<p>Three ways add many OSC inputs at once: capture them as they arrive, type a list, or read a TouchOSC layout.</p>"
                + "<h4>Bulk capture</h4>"
                + _steps([
                    "In the Add window (<b>OSC Input Mapper</b>), tick <b>Bulk capture</b>.",
                    "Press every key or move every control once, for example on a Stream Deck.",
                    "Untick <b>Bulk capture</b> to stop."
                ])
                + _list([
                    "Each new address becomes an input with the window's settings.",
                    "The same address twice within 0.3 seconds counts once.",
                    "Addresses that already have an input are skipped. The window says how many: \"Skipped <i>n</i> already answered\"."
                ])
                + "<h4>Import a list</h4>"
                + _steps([
                    "On the OSC page, right-click the list and choose <b>Add Inputs › Import…</b>.",
                    "In <b>New OSC messages:</b>, type or paste one address per line. Or choose <b>Choose File…</b> to read a text file (.txt).",
                    "To set the mode, add a space or comma and a suffix after the address (see the table).",
                    "Choose <b>OK</b>. The result line says how many were added and skipped."
                ])
                + _table(["Suffix", "Example", "Makes"], [
                    ["none, or B", "<code>/key/1</code>", "a Button"],
                    ["BNP", "<code>/key/2 BNP</code>", "a Button with Trigger on message"],
                    ["A", "<code>/fader/1, A</code>", "an Axis"],
                    ["C", "<code>/scene C</code>", "a Change input"],
                    ["E", "<code>/knob/1 E</code>", "an Encoder axis, format Auto"]
                ])
                + "<h4>Read a TouchOSC layout</h4>"
                + _steps([
                    "Right-click the list and choose <b>Add Inputs › From TouchOSC Layout…</b>, then pick the layout's .tosc file.",
                    "The window lists every control that sends OSC, with the input it makes. Tick the ones you want.",
                    "Choose the button that adds them, for example \"Add 5 Inputs\"."
                ])
                + _list([
                    "A fader, radial or encoder becomes an Axis, with the control's range.",
                    "An XY pad or radar becomes two Axis inputs.",
                    "A button becomes a Button; a radio or pager becomes a Change input.",
                    "Controls inside a grid or group are added. Labels, text and boxes are skipped, and the window names them."
                ])
                + _good([
                    "Lines that don't start with \"/\" are skipped, and the result names them. So are addresses that already exist.",
                    "An unknown suffix makes a Button, and the result names the line.",
                    "Import adds inputs only. For feedback, add the phone as a target on the <b>Output</b> tab.",
                    "<b>Back to Typed Messages</b> returns from a layout to the typed list."
                ]),
            related: ["osc-add-input", "osc-modes", "osc-touchosc", "osc-edit-inputs"]
        },
        {
            id: "osc-edit-inputs",
            section: inputs,
            title: "Change, order or delete OSC inputs",
            body: "<p>Right-click an input on the OSC page for its menu. Select several inputs to change all of them.</p>"
                + _see([
                    "<b>Change Address…</b>: edits the address. It must start with \"/\" and can't be blank or a copy of another. The input keeps its actions and name.",
                    "<b>Edit Settings…</b>: the same choices as Add, in the <b>OSC Input Settings</b> window. The input keeps its actions.<ul>"
                        + "<li>With several inputs selected, a setting they don't share shows blank. Only what you change is applied.</li></ul>",
                    "<b>Copy for Companion</b>: copies the settings to type into Companion for this input. See " + _link("osc-companion", "Use with Companion") + ".",
                    "<b>Send Test Press</b> (a button) or <b>Send Test Value</b> (an axis, from −1 to 1): tries the input's actions without the app.<ul>"
                        + "<li>It runs actions only while the profile runs. The OSC Monitor doesn't list it.</li></ul>",
                    "<b>Delete…</b>: asks first, then removes the input and its actions in every mode.",
                    "<b>History</b>: opens History with only this input's saved changes.",
                    "<b>Order › By Address</b>: sorts the inputs A to Z within each group.",
                    "<b>Add Inputs › Clear…</b>: removes every OSC input and its actions, after asking. Every profile uses this list."
                ])
                + _good([
                    "Every change here is one Undo step, even on several inputs.",
                    "After a delete, Undo puts the input back. You can also restore it from <b>Tools › History</b>" + _show("menu/Tools/History") + ".",
                    "An input with actions can't switch between an axis and a button (Button, Change or encoder pulses). Remove its actions first.",
                    "Switching among the button modes is fine.",
                    "An input that can't change mode is named and left as it is.",
                    "Editing is locked while the profile runs, except Feedback rows."
                ]),
            related: ["osc-page", "osc-add-input", "osc-modes", "tools-history"]
        },
        {
            id: "osc-patterns",
            section: inputs,
            title: "OSC address patterns",
            body: "<p>An input's address may be a pattern, so one input answers many addresses. For example <code>/deck/*</code> answers <code>/deck/1</code>, <code>/deck/2</code> and so on.</p>"
                + _table(["Pattern", "Example", "Matches"], [
                    ["<code>*</code>", "<code>/deck/*</code>", "any characters, or none"],
                    ["<code>?</code>", "<code>/key/?</code>", "any one character"],
                    ["<code>[ ]</code>", "<code>/key/[1-4]</code>", "one of the characters or a range"],
                    ["<code>[ ]</code> with an exclamation mark first", "–", "any one character but those"],
                    ["<code>{ }</code>", "<code>/{fire,jump}</code>", "one of the words listed"]
                ])
                + _good([
                    "No pattern character crosses a \"/\", and capitals don't matter.",
                    "A button is pressed while any of its addresses is pressed. An axis takes the last value received.",
                    "When an exact input and a pattern input both match a message, only the exact input gets it.",
                    "Pattern inputs that overlap all get the message.",
                    "In the Add window, a pattern says how many of the addresses seen so far it matches.",
                    "A stray <code>]</code> or <code>}</code> is refused, saying where. A space or <code>#</code> is refused in every address.",
                    "Send OSC and Feedback rows send to one exact address, never a pattern.",
                    "<b>Copy for Companion</b> on a pattern input uses an address it has seen.",
                    "Scripts can tell which address sent an event: see " + _link("osc-scripts", "OSC in conditions, macros and scripts") + "."
                ]),
            related: ["osc-add-input", "osc-tech-addresses", "osc-capture-import"]
        },
        {
            id: "osc-modes",
            section: inputs,
            title: "OSC input modes",
            body: "<p>The mode decides what a message does. The examples show the address, then its values.</p>"
                + _table(["Mode", "What it does", "Example"], [
                    ["<b>Button</b>", "The chosen value presses when it isn't 0 and releases at 0. A message with no value presses, then releases after the delay.", "<code>/fire 1</code> presses, <code>/fire 0</code> releases"],
                    ["<b>Button</b> with <b>Trigger on message</b>", "Any message presses, then releases after the delay. For apps that send only on press.", "<code>/flaps</code>"],
                    ["<b>Axis</b>", "The chosen value moves the axis from <b>Min:</b> to <b>Max:</b>. Values past either end stop at the end.", "Min 0, Max 1: <code>/throttle 0.5</code> is the middle"],
                    ["<b>Change</b>", "Presses, then releases after the delay, each time the value differs from the last one.", "<code>/scene 1</code>, <code>/scene 2</code>: two presses"],
                    ["<b>Encoder</b>", "Reads which way a knob turned. See " + _link("osc-encoder", "OSC encoders") + ".", "<code>/knob 1</code> clockwise"]
                ])
                + "<h4>Message + data</h4>"
                + "<p><b>Message + data</b> is an extra choice for any button mode. The input reacts only when the message's values equal <b>Data:</b>. For example, with Data <code>3 go</code>, <code>/scene 3 go</code> presses and <code>/scene 4 go</code> doesn't.</p>"
                + "<h4>Source value</h4>"
                + "<p>A message can carry several values. <b>Source value:</b> picks the one to read: P1 is the first, P2 the second. For example, <code>/pad 7 0.75</code> has P1 = 7 and P2 = 0.75.</p>"
                + "<h4>Shaping an axis</h4>"
                + _list([
                    "<b>Invert</b>, the box on an axis input's row, turns the axis the other way.",
                    "<b>Deadzone low:</b> and <b>high:</b>, under <b>Shaping</b> in the Add window: values between them, around the center, give 0.<ul>"
                        + "<li>The rest is stretched back to the full range. For example −0.1 and 0.1.</li>"
                        + "<li>Low is from −0.99 to 0, high from 0 to 0.99. Both 0 means no deadzone.</li></ul>",
                    "Both apply before any action."
                ])
                + _good([
                    "An Axis ignores a message with no number.",
                    "In Change, the first message counts as a change.",
                    "Text counts as a number when it is one: \"1\" and 1 are the same. Other text presses a Button, and empty text releases it.",
                    "True presses and False releases a Button.",
                    "The delay is the input's own (default 250 ms), or the <b>Server</b> tab's default.",
                    "A new press restarts the delay, so a held key that keeps sending stays pressed."
                ]),
            related: ["osc-add-input", "osc-encoder", "osc-tech-in", "osc-tech-samples"]
        },
        {
            id: "osc-encoder",
            section: inputs,
            title: "OSC encoders",
            body: "<p>An <b>Encoder</b> input reads a knob that turns without end, such as a Stream Deck+ dial.</p>"
                + _see([
                    "<b>Format:</b> how the knob reports a turn.<ul>"
                        + "<li><b>1 = clockwise, 0 = counter-clockwise</b>: each message is one step.</li>"
                        + "<li><b>+n and −n</b>: the value is the number of steps. <code>/knob 3</code> is three steps clockwise; <code>/knob -1</code> is one step back.</li>"
                        + "<li><b>Auto</b> (the default) starts as 1 and 0. Once another value arrives, it reads steps until the next Run.</li></ul>",
                    "<b>Output:</b> <b>Axis</b>: moves an axis by the <b>Step size:</b> for each step (default 0.05, up to 2). It stops at the ends.",
                    "<b>Output:</b> <b>Pulses clockwise</b> or <b>Pulses counter-clockwise</b>: a button that presses once for each step that way.<ul>"
                        + "<li>Each pulse releases after <b>Release after:</b> (default 100 ms).</li>"
                        + "<li>Turn the knob fast and the pulses wait their turn, up to 32.</li></ul>",
                    "<b>Acceleration:</b> <b>Off</b> (the default), <b>Low</b>, <b>Medium</b> or <b>High</b>. Turning fast multiplies the steps, up to 8 times."
                ])
                + _good([
                    "For both directions as buttons, add two inputs on the same address: one with Pulses clockwise, one with Pulses counter-clockwise.",
                    "Import's E suffix makes an Encoder axis with Format Auto.",
                    "The exact acceleration rule is in " + _link("osc-tech-timing", "OSC timing and limits") + "."
                ]),
            related: ["osc-modes", "osc-capture-import", "osc-tech-in", "osc-tech-timing"]
        },
        {
            id: "osc-value-types",
            section: inputs,
            title: "OSC value types",
            body: "<p>Every OSC value has a type. The program reads all the common ones and lets you choose what it sends.</p>"
                + _table(["Type", "Read as", "To send it, choose"], [
                    ["Integer (whole number)", "a number", "<b>Int</b>"],
                    ["Float (decimal)", "a number", "<b>Float</b>"],
                    ["True / False", "1 / 0", "<b>Bool</b>"],
                    ["Text", "a number when it is one, else text", "<b>Text</b>"],
                    ["None", "no value", "–"]
                ])
                + "<p><b>Auto</b> sends the same type that last arrived at that address for that value (P1, P2 …). It sends Float if nothing has arrived yet.</p>"
                + _good([
                    "In Feedback, text such as a mode name is always sent as text.",
                    "Many apps need a set type: Companion's key color wants numbers, a text field wants Text. Choose the type the receiving app expects.",
                    "Exact type codes are in " + _link("osc-tech-in", "OSC values the program reads") + " and " + _link("osc-tech-out", "OSC values the program sends") + "."
                ]),
            related: ["osc-tech-in", "osc-tech-out", "device-bindings-actions-send-osc"]
        },

        // ---- Sending OSC ----
        {
            id: "osc-send",
            section: sending,
            title: "Send OSC from an input",
            body: "<p>To send a message when you press a button or move an axis, give it the " + _link("device-bindings-actions-send-osc", "Send OSC") + " action. It sends to a target from the <b>Output</b> tab, or to <b>Reply to sender</b>.</p>"
                + "<p>To keep a device in step with the program's state instead, add " + _link("osc-feedback-rows", "Feedback rows") + ". They send only when something changes.</p>"
                + "<p>Scripts can send OSC to a named target too: see " + _link("osc-scripts", "OSC in conditions, macros and scripts") + ".</p>",
            related: ["device-bindings-actions-send-osc", "osc-output-tab", "osc-feedback-rows"]
        },
        {
            id: "osc-feedback-rows",
            section: sending,
            title: "Feedback rows on the OSC page",
            body: "<p>Each Feedback row sends one value to one address. You add and edit rows on the OSC page; the " + _link("osc-feedback-tab", "Feedback tab") + " holds the switches for all of them.</p>"
                + "<h4>Add a row</h4>"
                + _list([
                    "Right-click an input and choose <b>Add Feedback</b>. The row sends this input's value back to the sender, at the input's own address.",
                    "Right-click an input and choose <b>Companion feedback › Key text</b> or <b>Key color</b>. The row sends this input's value to a Companion key.<ul>"
                        + "<li>It starts on page 1, row 0, column 0. Change these in the row's <b>Address</b>: <code>/location/</code><i>page</i>/<i>row</i>/<i>column</i><code>/style/bgcolor</code> for Key color, <code>…/style/text</code> for Key text.</li>"
                        + "<li>Pages count from 1; rows and columns count from 0.</li>"
                        + "<li>Key color uses #333333 for off and #2a7a46 for on.</li>"
                        + "<li>If there is no Companion target yet, it adds one.</li>"
                        + "<li>Turn on Companion's OSC Listener first.</li></ul>",
                    "On the <b>Feedback</b> tab, choose <b>Companion custom variable…</b>. The row sends the current mode's name to a Companion custom variable.",
                    "Every row's <b>Source</b> can be changed afterwards, so a row added from an input can send a vJoy button instead (see below)."
                ])
                + "<h4>Light a key while vJoy 1 button 5 is held</h4>"
                + _steps([
                    "In Companion, turn on the <i>OSC Listener</i> (port 12321). In the program, choose <b>Add Companion</b> on the " + _link("osc-output-tab", "Output tab") + ".",
                    "On the OSC page, right-click any input and choose <b>Feedback › Companion feedback › Key color</b>.",
                    "Click the new row. Set <b>Source</b> to <b>vJoy button</b>, pick vJoy device 1 and type 5.",
                    "Set the key in the <b>Address</b>, for example <code>/location/1/0/2/style/bgcolor</code> for page 1, row 0, column 2. Choose <b>OK</b>.",
                    "Leave <b>Off</b> and <b>On</b> as they are (#333333 and #2a7a46), or type your own colors.",
                    "Run the profile. The key turns green while vJoy 1 button 5 is pressed."
                ])
                + "<p>With its source on vJoy, the row moves to <b>Feedback not tied to an input</b>. Use <b>Show under this input</b> to keep it under the input.</p>"
                + "<h4>Where rows show</h4>"
                + _list([
                    "A row whose source is an OSC input, or an action on it, shows under that input, after its actions.",
                    "Any other row is in the group <b>Feedback not tied to an input</b> at the bottom.",
                    "<b>Show under this input</b>, in the row's editor, puts it under another input. <b>By its source</b> (the default) follows the rules above.",
                    "Each row reads like \"Sends this input's value to the sender · /fire\". Its <b>Send this feedback</b> box turns it off.",
                    "Click a row to edit it. Right-click it for <b>Open</b>, <b>Turn Off</b> (or <b>Turn On</b>), <b>Duplicate</b> and <b>Delete…</b>."
                ])
                + "<h4>Each row's settings</h4>"
                + _list([
                    "<b>Source</b>: what the row sends.<ul>"
                        + "<li><b>Current mode</b>: the mode's name, as text.</li>"
                        + "<li><b>vJoy button</b> or <b>vJoy axis</b>: pick the vJoy device and type the number.</li>"
                        + "<li><b>Logical Device control</b>: choose <b>Pick a control</b>.</li>"
                        + "<li><b>OSC input</b>: choose <b>Pick an OSC input</b>; its own value is sent back.</li>"
                        + "<li><b>Action state</b>: choose <b>Pick an action</b>. A Smart Toggle sends on or off; a Tempo sends on for a long press and off for a short one.</li>"
                        + "<li><b>Running / Paused</b>: on while the profile runs, off while it is paused.</li></ul>",
                    "<b>Send to</b>: a target from the Output tab, or <b>Reply to sender</b>.",
                    "<b>Type</b>: <b>Auto</b>, <b>Int</b>, <b>Float</b>, <b>Bool</b> or <b>Text</b>. See " + _link("osc-value-types", "OSC value types") + ".",
                    "<b>Address</b>: the address to send to, for example <code>/led/gear</code>. It starts with \"/\" and has no spaces or <code>#</code>.",
                    "<b>Min</b> and <b>Max</b> (default 0 and 1): a button sends Max when pressed and Min when released. An axis sends its position from Min to Max.",
                    "<b>Off</b> and <b>On</b>: for an on/off source, the values sent instead of Min and Max. They can be a number, text or a color such as <code>#333333</code>. Blank uses Min and Max."
                ])
                + _good([
                    "You can add, change and turn off rows while the profile runs. A change takes effect at once.",
                    "Adding, changing or removing a row is one step of the OSC page's Undo.",
                    "Undo after Key text or Key color removes the row but keeps the Companion target it made.",
                    "Colors sent to a Companion key's color address go as three numbers: red, green and blue.",
                    "An Action state row whose action isn't in the open profile sends nothing, and says so.",
                    "When that action is used in several places, the state is on if any of them is on.",
                    "Running / Paused sends nothing while no profile runs.",
                    "How rows send, step by step: " + _link("osc-feedback-how", "How Feedback sends") + "."
                ]),
            related: ["osc-feedback-tab", "osc-feedback-how", "osc-companion", "osc-value-types"]
        },
        {
            id: "osc-feedback-how",
            section: sending,
            title: "How Feedback sends",
            body: "<p>While the profile runs, the program checks every Feedback row's source every 10 ms. A row sends only when its value changes.</p>"
                + _list([
                    "Each address sends at most the set number of messages a second (default 50). A value held back goes out as soon as the limit allows, always the newest one.",
                    "Every row sends again at <b>Run start</b>, <b>Mode change</b> and <b>Profile switch</b>, when they are ticked.",
                    "A message to the sync address (default <code>/gremlin/sync</code>) sends every row again. Rows set to <b>Reply to sender</b> go to the device that asked.",
                    "If a row can't send yet (output off, or nobody to reply to), it sends as soon as it can."
                ])
                + _good([
                    "A device that starts after the program can send the sync address to get the whole state.",
                    "The sync message never reaches an input. The OSC Monitor lists it with Sync."
                ]),
            related: ["osc-feedback-rows", "osc-feedback-tab", "osc-tech-timing", "osc-companion"]
        },
        {
            id: "osc-monitor",
            section: sending,
            title: "Watch messages with the OSC Monitor",
            body: "<p>The <b>OSC Monitor</b> lists the last 200 OSC messages in and out. Use it to see what an app really sends.</p>"
                + _howto([
                    "On the OSC page, choose <b>Monitor</b> in the page bar, or click the panel's heading at the bottom of the page.",
                    "Or choose <b>Tools › OSC Monitor</b>" + _show("menu/Tools/OSC Monitor") + ". It opens the OSC page with the panel unfolded.",
                    "Drag the panel's grip to set its height. <b>×</b> hides it until you choose Monitor again.",
                    "To give it a window of its own, choose <b>Pop out</b>. Closing that window puts it back in the page."
                ])
                + _see([
                    "Columns: <b>Time</b>, <b>In / Out</b>, <b>Address</b>, <b>Values</b>, <b>From / To</b> and <b>Input</b>.",
                    "<b>From / To</b> is the other side's address and port. <b>Input</b> names the inputs the message matched, or says no input.",
                    "<b>Pause</b> stops adding new messages; <b>Resume</b> shows them again. <b>Clear</b> empties the list.",
                    "The filter box shows only rows that match what you type.",
                    "<b>Show outgoing</b>: also lists what the program sends. On by default.",
                    "<b>Add as Input…</b>, on a row whose Input says no input: opens Add with the address and values filled in. Hidden while the profile runs.",
                    "A sync message shows Sync in the <b>Input</b> column.",
                    "A message from a sender not on <b>Allowed senders</b> shows as blocked. Right-click it and choose <b>Allow this sender</b> to add it."
                ])
                + _good([
                    "The Monitor shows messages whenever the port is open. See " + portRule + ".",
                    "Send Test Press and Send Test Value are not network messages, so they don't show here.",
                    "Incoming addresses show in lower case. Point at a cut-off address to see it whole."
                ]),
            related: ["osc-add-input", "osc-troubleshooting", "osc-tech-network"]
        },

        // ---- How to ----
        {
            id: "osc-companion",
            section: howto,
            title: "Use with Companion",
            body: "<p>Bitfocus Companion, with its Generic OSC connection, works with the program in both directions. These steps only fill in ordinary OSC settings.</p>"
                + "<h4>Make a Stream Deck key press an input</h4>"
                + _steps([
                    "In Companion, add a <i>Generic OSC</i> connection. Set <i>Target Hostname or IP</i> to 127.0.0.1 if Companion runs on this PC. Otherwise use this PC's address from the <b>Server</b> tab.",
                    "Set <i>Target Port</i> to the program's <b>Port</b> (default 8001), and <i>Protocol</i> to UDP.",
                    "On a key, add a press action <i>Send integer</i> with path <code>/sd/fire</code> and value 1.",
                    "Add a release action <i>Send integer</i> with the same path and value 0.",
                    "In the program, right-click the OSC page's list and choose <b>Add Inputs › Listen</b>.",
                    "Press the key in Companion. Choose <b>Button</b>, then <b>OK</b>. The new input opens in the action pane.",
                    "Choose <b>Add Action › Map to vJoy</b>, pick the vJoy device and the output, for example Button 5. See " + _link("device-bindings-actions-map-to-vjoy", "Map to vJoy") + ".",
                    "Button 5 not offered, or shown in red with ⚠? Tick it in the vJoy device's Output Module Setup and choose <b>Save Module</b>. See " + _link("home-devices-vjoy-output", "Set up a vJoy output module") + ".",
                    "Choose <b>Run</b>" + _show("toolbar/Run") + ". Pressing the key now presses vJoy's button.",
                    "Optional: choose <b>Copy for Companion</b> in the input's menu for a written list of these settings."
                ])
                + "<p>Companion uses two ports, one for each direction:</p>"
                + _table(["Direction", "Port", "Set in"], [
                    ["Companion → the program", "8001 (the program's <b>Port</b>)", "Companion's Generic OSC connection, <i>Target Port</i>"],
                    ["The program → Companion", "12321", "Companion's <i>OSC Listener</i>; the program's Companion target (<b>Add Companion</b>)"]
                ])
                + "<p>Feedback, Key text and Key color all use 12321.</p>"
                + "<p>Other Companion sends work too:</p>"
                + _table(["Companion sends", "Use this in the program"], [
                    ["float", "<b>Axis</b>"],
                    ["string", "<b>Message + data</b>"],
                    ["several values", "<b>Source value:</b> P1, P2 …"],
                    ["boolean", "<b>Button</b>"],
                    ["no value", "<b>Trigger on message</b>, since there is no release"],
                    ["rotary key", "<b>Encoder</b>"]
                ])
                + "<h4>Show the program's mode on a key</h4>"
                + _steps([
                    "In Companion's settings, open the OSC section and turn on the <i>OSC Listener</i>. It uses port 12321.",
                    "In Companion, create a custom variable, for example gremlin_mode.",
                    "In the program, choose <b>OSC Setup…</b> and open the <b>Output</b> tab. Choose <b>Add Companion</b>.",
                    "Choose <b>Check Companion setup</b> and fix any line that isn't OK.",
                    "On the <b>Feedback</b> tab, choose <b>Companion custom variable…</b>, keep gremlin_mode and choose <b>Add Row</b>.",
                    "In Companion, put <code>$(custom:gremlin_mode)</code> in a key's text.",
                    "Run the profile. The key shows the mode name."
                ])
                + "<p>To show an input's own state or a vJoy button on a key instead, use <b>Companion feedback › Key color</b>. See " + _link("osc-feedback-rows", "Feedback rows on the OSC page") + ".</p>"
                + _good([
                    "Custom variables must exist in Companion first. Companion ignores unknown names without a word.",
                    "Key text and Key color overwrite the key's own style in Companion. Custom variables don't, so they are the cleaner route for the mode name; to light a key from a vJoy button or an input, use Key color.",
                    "You can also use the variable in a Companion expression feedback to color the key.",
                    "Companion has no OSC command to change pages or to add to a variable. Use a Companion key with its own page action.",
                    "<b>Reply to sender</b> reaches Companion only when its connection has <i>Listen for Feedback</i> on, with a source port other than 8001.",
                    "Companion can't send doubles or bundles, and matches addresses exactly. The program reads everything it sends."
                ]),
            related: ["osc-feedback-tab", "osc-output-tab", "osc-tech-companion", "osc-q-companion"]
        },
        {
            id: "osc-touchosc",
            section: howto,
            title: "Use with TouchOSC or a phone app",
            body: "<p>Phone and tablet apps such as TouchOSC send OSC over Wi-Fi.</p>"
                + _howto([
                    "Put the phone and the PC on the same network.",
                    "In the app's OSC connection, set the host to this PC's address (from the <b>Server</b> tab).",
                    "Set the app's send port to the program's <b>Port</b> (default 8001).",
                    "If you want feedback, set the app's receive port, for example 9000.",
                    "In the program, right-click the OSC page's list and choose <b>Add Inputs › From TouchOSC Layout…</b>. Pick the layout's .tosc file.",
                    "For feedback, add a target on the <b>Output</b> tab with the phone's address and the app's receive port.",
                    "Add Feedback rows that send to the addresses the controls use, so faders and buttons follow the program."
                ])
                + _good([
                    "Instead of the layout file, you can use <b>Listen</b> or <b>Bulk capture</b>. See " + _link("osc-capture-import", "Capture or import many addresses") + ".",
                    "Faders and XY pads are <b>Axis</b> inputs. Their range is usually 0 to 1.",
                    "An XY pad sends two values: add two Axis inputs on the same address, one on P1 and one on P2.",
                    "If the app replies on the same port it sends from, <b>Reply to sender</b> works instead of a target.",
                    "A phone's address can change. A fixed address set in your router helps."
                ]),
            related: ["osc-checklist", "osc-modes", "osc-feedback-tab"]
        },
        {
            id: "osc-allow-senders",
            section: howto,
            title: "Accept OSC only from some senders",
            body: "<p>On a shared network you can let only your own devices reach the program.</p>"
                + _howto([
                    "Choose <b>OSC Setup…</b> on the OSC page and open the <b>Server</b> tab.",
                    "Under <b>Allowed senders</b>, type a device's IP address, for example 192.168.1.5. Choose <b>Add</b>.",
                    "Or type a range: 192.168.1.0/24 means every address from 192.168.1.0 to 192.168.1.255.",
                    "Add every device that sends to the program. 127.0.0.1 is this PC, for an app such as Companion running here."
                ])
                + _good([
                    "With the list empty (the default), every sender is accepted.",
                    "With anything on the list, a message from any other sender reaches nothing: no input, no Listen and no Feedback sync.",
                    "The OSC Monitor still lists a blocked message. Right-click it and choose <b>Allow this sender</b> to add that sender.",
                    "<b>Remove</b> asks first. Removing the last entry accepts every sender again."
                ]),
            related: ["osc-server-tab", "osc-monitor", "osc-checklist"]
        },
        {
            id: "osc-scripts",
            section: howto,
            title: "OSC in conditions, macros and scripts",
            body: "<p>OSC inputs can be used wherever a stick input can.</p>"
                + _list([
                    "Conditions: in a <b>Joystick</b> condition, choose an input with <b>OSC input…</b>. The condition reads the input's last value.",
                    "Macros: <b>Add Step › OSC</b> plays an OSC input's press, release or value as if it had arrived.",
                    "Macros: Record captures OSC presses and values too. An OSC step plays as it is and is not recorded again.",
                    "Scripts: a script variable for an OSC input (<code>OscInputVariable</code>) gets that input's events, like a stick input.",
                    "The event's <code>osc_address</code> is the address received, so a pattern input's script can tell which address sent it.",
                    "Scripts that send OSC: a callback with a parameter named <code>osc</code> gets the program's OSC sender.",
                    "<code>osc.send(\"Companion\", \"/my/address\", 1, types=[\"int\"])</code> sends to the target with that name.",
                    "<code>types</code> is optional. Give auto, int, float, bool or text for each value."
                ])
                + _good([
                    "There is no separate OSC condition.",
                    "Scripts send only to named targets from the Output tab, never to a raw host and port.",
                    "A send that can't go returns False and is written to the log once. Causes are a missing target, a bad address, OSC output off, or no Run."
                ]),
            related: ["osc-patterns", "osc-output-tab", "osc-send"]
        },
        {
            id: "osc-checklist",
            section: howto,
            title: "Connection checklist",
            body: "<p>Check these in order when you connect any OSC app.</p>"
                + _steps([
                    "<b>Listen for OSC messages</b> is on, on the <b>Server</b> tab.",
                    "This PC's address and port: on the Server tab, under <b>Use one of these in your app:</b>.",
                    "Same network: the app's device and this PC are on the same network. If the app runs on this PC, use 127.0.0.1.",
                    "Firewall: Windows may ask once to let the program receive on the network. Allow it for private networks.",
                    "If you said no, allow incoming UDP on port 8001 in Windows Defender Firewall.",
                    "The app sends to that address and port, over UDP.",
                    "If <b>Allowed senders</b> lists anything, the app's address is on it.",
                    "To send back: the target is the device's own address and the port the app listens on (not 8001).",
                    "Watch the <b>OSC Monitor</b>. Rows marked In show that messages arrive; Out rows show what is sent and where."
                ]),
            related: ["osc-tech-network", "osc-troubleshooting", "osc-monitor"]
        },
        {
            id: "osc-troubleshooting",
            section: howto,
            title: "When OSC doesn't work",
            body: "<p>Work down the list for what you see. Each line names a cause and its fix.</p>"
                + "<h4>Nothing arrives</h4>"
                + _list([
                    "Look at the OSC card on Home first. Its second line says whether the server is listening, and why not. See " + _link("osc-card-line", "The OSC card on Home") + ".",
                    "Watch the <b>OSC Monitor</b>. If nothing shows there, the messages don't reach this PC.",
                    "Messages shown as blocked come from a sender not on <b>Allowed senders</b>.",
                    "Check the app's host and port against the <b>Server</b> tab, and that <b>Listen for OSC messages</b> is on.",
                    "Check the firewall. See " + _link("osc-checklist", "Connection checklist") + ".",
                    "\"Could not bind OSC on host:port.\": another program uses that port. Close it, or choose another <b>Port</b> and set the same in the app.",
                    "A typed <b>Host</b> that isn't this PC's current address can't listen. Leave it blank."
                ])
                + "<h4>Messages arrive, but nothing happens</h4>"
                + _list([
                    "The Monitor's <b>Input</b> says no input: the address or data doesn't match an input. Use <b>Add as Input…</b>.",
                    "The profile isn't running (<b>Run</b>" + _show("toolbar/Run") + "), or the open profile gives these OSC inputs no actions.",
                    "A Button that never releases: the app sends only on press. Tick <b>Trigger on message</b>.",
                    "To try an input's actions without the app, right-click it and choose <b>Send Test Press</b> or <b>Send Test Value</b> while the profile runs."
                ])
                + "<h4>The input is pressed, but the game sees no vJoy button</h4>"
                + _list([
                    "The Map to vJoy output is red with ⚠, or reads <b>(not claimed)</b>: tick it in the vJoy device's Output Module Setup. See " + _link("device-bindings-actions-q-vjoy-not-claimed", "Why is a Map to vJoy output red with ⚠?") + " and " + _link("home-devices-q-not-claimed", "What does \"(not claimed)\" mean?") + ".",
                    "The profile isn't running, or the action is in another mode.",
                    "Check vJoy itself: see " + _link("getting-started-nothing-reaches-vjoy", "Nothing reaches vJoy") + ".",
                    "In Trace (below), the <b>Inputs</b> area shows what the input's actions send: an OUTPUT line for the vJoy press, or BLOCKED with the reason."
                ])
                + "<h4>Companion doesn't update</h4>"
                + _list([
                    "Companion's <i>OSC Listener</i> is off (in Companion's OSC settings), or the custom variable doesn't exist yet.",
                    "The Feedback row sends to <b>Reply to sender</b>, but Companion's connection has <i>Listen for Feedback</i> off. Send to the Companion target instead.",
                    "<b>OSC output (Send OSC actions and feedback)</b> or <b>Send feedback to OSC devices</b> is off, or the profile isn't running.",
                    "<b>Check Companion setup</b> on the Output tab goes through these line by line.",
                    "A Key color row lights the wrong key, or none: check the page, row and column in its <b>Address</b> (<code>/location/</code><i>page</i>/<i>row</i>/<i>column</i><code>/style/bgcolor</code>; pages count from 1, rows and columns from 0).",
                    "A Key color row meant to follow a vJoy button still has its <b>Source</b> on the OSC input. Set it to <b>vJoy button</b>."
                ])
                + "<h4>Trace OSC step by step</h4>"
                + _steps([
                    "Open <b>Debug › Live Log Reader</b> <a href=\"open:debug.liveLog\">Open ›</a> and choose the <b>Trace</b> tab.",
                    "Tick the <b>OSC</b> row, or only the areas you need: <b>Receive</b>, <b>Inputs</b>, <b>Output</b>, <b>Feedback</b>, <b>Setup and files</b>.",
                    "Turn <b>Tracing</b> on" + _show("menu/Debug/Tracing") + ", then send from the app or run the profile.",
                    "Read the lines. <b>Inputs</b> shows what the actions send, such as the vJoy output; <b>Feedback</b> shows each key color or value sent. A <b>BLOCKED</b> line says what stopped the message and why, for example \"send refused: OSC output is Off\"."
                ])
                + _good([
                    "See " + _link("tools-trace", "Follow your controls with Trace") + " for every area and its limits."
                ]),
            related: ["osc-checklist", "osc-monitor", "osc-companion", "osc-tech-network", "tools-trace"]
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
                    ["Listening port", "default 8001 (1 to 65535)"],
                    ["Default target", "127.0.0.1 port 8000"],
                    ["Companion target", "127.0.0.1 port 12321 (<b>Add Companion</b>)"],
                    ["Reply to sender", "the IP address and source port of the last message received"],
                    ["Sends from", "a port chosen by Windows for each target"],
                    ["Discovery service type", "<code>_osc._udp.local.</code>"],
                    ["Announced name", "Gremlin-Platforms on <i>PC name</i>, on the listening port"]
                ])
                + "<h4>When the port is open</h4>"
                + _list([
                    "The port is open whenever the program is open and <b>Listen for OSC messages</b> is on. This holds with or without a running profile.",
                    "So live values, the Monitor and Listen work without Run. A stopped profile still runs no actions.",
                    "Turning <b>Listen for OSC messages</b> off closes the port at once and frees it for other programs.",
                    "Changing the host or port moves the open port at once. Quitting the program closes it."
                ])
                + _good([
                    "Windows Defender Firewall may ask once for incoming UDP when the port first opens.",
                    "Two programs can't listen on the same UDP port on one PC."
                ]),
            related: ["osc-checklist", "osc-server-tab", "osc-output-tab", "osc-discovery-tab"]
        },
        {
            id: "osc-tech-addresses",
            section: tech,
            title: "OSC address rules",
            body: "<p>How the program checks and matches addresses.</p>"
                + _list([
                    "An address must start with \"/\" and can't be blank, for example <code>/sd/fire</code>.",
                    "Matching ignores capitals: <code>/Fire</code> and <code>/fire</code> are the same input. Incoming addresses are made lower case.",
                    "An input's address matches a message's address exactly, unless it is a pattern. See " + _link("osc-patterns", "OSC address patterns") + ".",
                    "An exact input wins over a pattern input for the same message.",
                    "A space or <code>#</code> is refused in every address, in and out. Addresses the program sends can't be patterns.",
                    "In Message + data, the values must match too, with the same number of values.<ul>"
                        + "<li>Numbers compare as numbers (\"1\" equals 1.0); anything else as exact text.</li>"
                        + "<li>True and False compare as the text True and False.</li></ul>",
                    "Bundles are unpacked, and each message in them is handled in turn. A bundle with a future time tag waits until that time.",
                    "The address <code>/noop</code> is ignored.",
                    "The sync address (default <code>/gremlin/sync</code>) ignores capitals. Feedback answers it, and it never reaches an input."
                ]),
            related: ["osc-tech-in", "osc-modes", "osc-tech-samples"]
        },
        {
            id: "osc-tech-in",
            section: tech,
            title: "OSC values the program reads",
            body: "<p>How each OSC type tag (the code for a value's type) is read.</p>"
                + _table(["Type tag", "Type", "Read as"], [
                    ["<code>i</code>, <code>h</code>", "int32, int64", "number"],
                    ["<code>f</code>, <code>d</code>", "float32, float64 (double)", "number"],
                    ["<code>s</code>", "string", "a number when the text is one, else text"],
                    ["<code>T</code>, <code>F</code>", "true, false", "1 and 0"],
                    ["<code>N</code>", "nil", "no value"],
                    ["<code>b</code>, <code>t</code>, <code>r</code>, <code>m</code>, arrays", "blob, time tag, color, MIDI, <code>[ ]</code>", "not a number: an Axis ignores it, a Button presses"]
                ])
                + "<p>Other type tags are skipped, and the values after them may read wrongly. Avoid them.</p>"
                + "<h4>By mode</h4>"
                + _list([
                    "Button: 0, False or empty text releases; anything else presses.",
                    "Button with no value: press, then release after the delay (default 250 ms). With auto-release off, it presses and holds.",
                    "Axis: (value − Min) ÷ (Max − Min) × 2 − 1, so Min gives −1 and Max gives +1. Outside the range it stays at −1 or +1.",
                    "Axis with a value that isn't a number: ignored.",
                    "Change: compares with the input's last value, numbers as numbers, else as text.",
                    "Encoder 1 = clockwise, 0 = counter-clockwise: 0 turns back one step, anything else turns forward one step.",
                    "Encoder +n and −n: the number is the steps. Auto switches to this when a value other than 0 or 1 arrives.",
                    "Pad address-only messages: a message with no value reads as 1.0."
                ]),
            related: ["osc-modes", "osc-encoder", "osc-tech-out", "osc-value-types"]
        },
        {
            id: "osc-tech-out",
            section: tech,
            title: "OSC values the program sends",
            body: "<p>The type tag sent for each type you choose.</p>"
                + _table(["Type chosen", "Type tag sent", "Notes"], [
                    ["<b>Int</b>", "<code>i</code> (<code>h</code> past 32 bits)", "rounded to a whole number"],
                    ["<b>Float</b>", "<code>f</code>", "32-bit float; never a double"],
                    ["<b>Bool</b>", "<code>T</code> or <code>F</code>", "true, yes and on are True; false, no, off and blank are False; a number is True unless 0"],
                    ["<b>Text</b>", "<code>s</code>", "numbers as short text, for example 1 or 0.5; a fixed Send OSC value goes as typed"],
                    ["<b>Auto</b>", "the type last received at that address for that value", "<code>f</code> when nothing has arrived"]
                ])
                + _list([
                    "Every message is one UDP packet with one message. The program never sends bundles.",
                    "A value that can't be turned into the chosen type is sent as text.",
                    "For a value position never received, Auto uses the type of the last value that was.",
                    "Feedback: a button sends Max when pressed and Min when released. An axis sends Min to Max for −1 to +1.",
                    "Feedback: a hat sends its direction's name as text, and the mode sends its name as text.",
                    "Nothing is sent while the profile isn't running, or while <b>OSC output (Send OSC actions and feedback)</b> is off."
                ]),
            related: ["osc-value-types", "device-bindings-actions-send-osc", "osc-feedback-how"]
        },
        {
            id: "osc-tech-timing",
            section: tech,
            title: "OSC timing and limits",
            body: "<p>Defaults and limits for OSC's timed settings.</p>"
                + _table(["Setting", "Default", "Range"], [
                    ["Auto-release delay (address-only, Trigger on message, Change, Message + data)", "250 ms", "0 to 10000 ms"],
                    ["Encoder pulse <b>Release after:</b>", "100 ms", "0 to 10000 ms"],
                    ["Feedback messages per second per address", "50", "1 or more"],
                    ["Feedback source check", "every 10 ms", "–"],
                    ["Encoder step size", "0.05", "above 0, up to 2"],
                    ["Encoder pulses waiting", "–", "up to 32"],
                    ["OSC Monitor list", "last 200 messages", "–"],
                    ["Encoder acceleration", "Off", "Low, Medium or High"],
                    ["Sync address", "<code>/gremlin/sync</code>, on", "–"]
                ])
                + "<p>Encoder acceleration counts the steps turned in the last 0.1 s. It multiplies the step size (or the pulses) by 1 + <i>factor</i> × (steps − 1), at most 8 times.</p>"
                + "<p>The factor is 0.5 for <b>Low</b>, 1 for <b>Medium</b> and 2 for <b>High</b>; <b>Off</b> is 0.</p>",
            related: ["osc-feedback-how", "osc-server-tab", "osc-encoder"]
        },
        {
            id: "osc-tech-companion",
            section: tech,
            title: "Companion OSC addresses",
            body: "<p>Companion's own OSC listener (port 12321) takes these addresses. The program's Companion rows use the first three.</p>"
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
                    "Companion's OSC Listener is off by default."
                ]),
            related: ["osc-companion", "osc-feedback-tab", "osc-tech-out"]
        },
        {
            id: "osc-tech-samples",
            section: tech,
            title: "Sample OSC messages",
            body: "<p>Example messages and what they do, with default settings.</p>"
                + _table(["Address", "Type tags", "Values", "Effect"], [
                    ["<code>/fire</code>", "<code>,i</code>", "1", "Button input presses"],
                    ["<code>/fire</code>", "<code>,i</code>", "0", "Button input releases"],
                    ["<code>/fire</code>", "<code>,</code>", "(none)", "Button input presses, then releases after 250 ms"],
                    ["<code>/gear</code>", "<code>,T</code>", "True", "Button input presses"],
                    ["<code>/throttle</code>", "<code>,f</code>", "0.75", "Axis (Min 0, Max 1) moves three quarters of the way (0.5 on the −1 to +1 axis)"],
                    ["<code>/pad</code>", "<code>,if</code>", "7 0.75", "Axis on P2 reads 0.75"],
                    ["<code>/scene</code>", "<code>,is</code>", "3 go", "Message + data input with Data 3 go presses"],
                    ["<code>/knob</code>", "<code>,i</code>", "-2", "Encoder (+n and −n) turns 2 steps counter-clockwise"],
                    ["<code>/gremlin/sync</code>", "<code>,</code>", "(none)", "Feedback sends every row again"],
                    ["<code>/custom-variable/gremlin_mode/value</code>", "<code>,s</code>", "Flight", "sent to Companion: the mode name"]
                ]),
            related: ["osc-modes", "osc-tech-in", "osc-tech-network"]
        },

        // ---- Good to know ----
        {
            id: "osc-good-to-know",
            section: "More about OSC",
            title: "Good to know about OSC",
            body: _list([
                    "At <b>Stop</b>, any OSC button still held is released before the profile stops.",
                    "OSC's inputs and settings are kept apart from profiles. A profile keeps only the actions it gives them.",
                    "For saving OSC changes and where they travel, see " + _link("osc-setup-window", "Open OSC's Module Setup") + ".",
                    "For when the port is open, see " + portRule + ".",
                    "Deleting an input asks first. You can restore it from <b>Tools › History</b>" + _show("menu/Tools/History") + "."
                ]),
            related: ["osc-about", "osc-tech-network", "device-library-built-in", "tools-history"]
        },

        // ---- Common questions ----
        {
            id: "osc-q-nothing",
            section: questions,
            title: "Why does nothing happen when my app sends OSC?",
            body: "<p>Open the <b>OSC Monitor</b>" + _show("menu/Tools/OSC Monitor") + ". If nothing shows, check the address, port and firewall. If the Input column says no input, add an input for that address.</p>"
                + "<p>See " + _link("osc-troubleshooting", "When OSC doesn't work") + ".</p>",
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
            body: "<p>The app sends a press but never a 0. Tick <b>Trigger on message</b> on the input, so it releases after the delay. See " + _link("osc-modes", "OSC input modes") + ".</p>",
            related: ["osc-modes"]
        },
        {
            id: "osc-q-axis",
            section: questions,
            title: "Why can't I change an OSC input to Axis?",
            body: "<p>An input with actions can't switch between axis and button. Remove its actions first, then change the mode. See " + _link("osc-edit-inputs", "Change, order or delete OSC inputs") + ".</p>",
            related: ["osc-edit-inputs"]
        }
    ]
}
