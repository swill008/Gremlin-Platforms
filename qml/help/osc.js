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
                    "OSC is an internal input, like the Keyboard and the Logical Device. Its page lists your OSC inputs: one per address you use. Each input gets actions on the Device Bindings page like any button or axis.",
                    "OSC is a module with its own module file, like the Keyboard and the Logical Device, not a program setting: its inputs, settings, targets and Feedback rows are kept in that file, and one list of OSC inputs is used by every profile.",
                    "The program listens on a network port (8001 unless you change it). Your app sends to this PC's address and that port.",
                    "The program can also send: the " + _link("device-bindings-actions-send-osc", "Send OSC") + " action, and " + _link("osc-feedback-tab", "Feedback") + ", which shows the program's state on your device.",
                    "Settings are in OSC's Module Setup window (<b>OSC Setup…</b> on the OSC page), in four tabs: <b>Server</b>, <b>Output</b>, <b>Feedback</b> and <b>Discovery</b>. Feedback rows are added and edited on the OSC page."
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
                    "On the OSC page, right-click the list and choose <b>Add Inputs</b> › <b>Listen</b>, and press the button or move the control in your app once. The address it sent fills in. Choose the mode (<b>Button</b>, <b>Axis</b>, <b>Change</b> or <b>Encoder</b>), then <b>OK</b>.",
                    "The new input is selected and opens in the action pane: choose <b>Add Action</b> and add actions as on any device, for example Map to vJoy.",
                    "Choose <b>Run</b>" + _show("toolbar/Run") + ". Messages now press and move your actions."
                ])
                + _good([
                    "Nothing arriving? Open the <b>OSC Monitor</b> (" + _link("osc-monitor", "Watch messages with the OSC Monitor") + ") and see " + _link("osc-troubleshooting", "When OSC doesn't work") + ".",
                    "To show the program's state on the device too, see " + _link("osc-feedback-tab", "Feedback tab") + ".",
                    "Options shows one line for OSC, <b>OSC settings are in OSC › Module Setup.</b>" + _show("option/" + _oscOption) + ", with the button <b>Open OSC Module Setup</b>, which opens this window."
                ]),
            related: ["osc-about", "osc-server-tab", "osc-add-input", "osc-checklist"]
        },
        {
            id: "osc-card-line",
            section: main,
            title: "The OSC card on Home",
            body: "<p>OSC means Open Sound Control. The OSC card on Home keeps the short name; hover its title to see the full name, which also shows in grey under the title of OSC's Device Bindings page.</p>"
                + "<p>The card's second line shows what the OSC server is doing:</p>"
                + _list([
                    "\"Listening on 192.168.1.5:8001\": the port is open on that address. With <b>Host</b> blank it reads \"Listening on all addresses, port 8001\".",
                    "\"From 192.168.1.20: /fire 1\": a message arrived, from that sender, with its address and first value (long text is cut with \"…\"). The line changes at most 4 times a second while many messages arrive, and goes back to \"Listening on …\" 3 seconds after the last one.",
                    "\"Server not started: port 8001 is in use\" (in the warning colour): the port couldn't be opened. The reason can also be \"<i>address</i> is not an address of this PC\" or \"Windows refused port <i>n</i>\". It stays until the server starts, for example after you change the <b>Port</b> or <b>Host</b> on the Server tab.",
                    "\"Not listening (Listen for OSC messages is off)\": OSC input is turned off on the Server tab.",
                    "\"Not listening yet\": shown for a moment while the program starts, before the port opens."
                ])
                + _good([
                    "For a failure, see " + _link("osc-troubleshooting", "When OSC doesn't work") + "."
                ]),
            related: ["osc-about", "osc-server-tab", "osc-troubleshooting", "osc-monitor"]
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
                    "Or, in Options, choose <b>Open OSC Module Setup</b> beside <b>OSC settings are in OSC › Module Setup.</b>" + _show("option/" + _oscOption)
                ])
                + "<p>The tabs: " + _link("osc-server-tab", "Server") + " (where the program listens), " + _link("osc-output-tab", "Output") + " (where it sends), " + _link("osc-feedback-tab", "Feedback") + " (state sent to devices) and " + _link("osc-discovery-tab", "Discovery") + " (finding devices on the network).</p>"
                + _good([
                    "Changes take effect at once, also while the profile runs.",
                    "The settings, targets and Feedback rows are kept in OSC's module file. Save to Device Library, Restore, Export and Export / Import Device carry them, and <a href=\"topic:tools-history\">History</a> keeps every save.",
                    "A change here or on the OSC page marks the profile changed (<b>*</b> in the title): <b>File › Save Profile</b>" + _show("menu/File/Save Profile") + " (Ctrl+S) saves OSC's file too, and <b>Discard</b> throws the OSC changes away."
                ]),
            related: ["osc-server-tab", "osc-output-tab", "osc-feedback-tab", "osc-discovery-tab"]
        },
        {
            id: "osc-server-tab",
            section: setup,
            title: "Server tab",
            body: "<p>Where and how the program listens for OSC messages.</p>"
                + _list([
                    "<b>Listen for OSC messages</b>: turns OSC input on. On, the port is open the whole time the program is open, running or not; off, the port closes at once and the program never opens it. On unless you turn it off.",
                    "<b>Host</b>: leave it blank (<b>All addresses on this PC</b>) to listen on every network address of this PC. That keeps working when the PC's address changes. Or type one IP address or computer name to listen only there; the program checks it before saving.",
                    "<b>Port</b>: the UDP port your app sends to. 8001 unless you change it.",
                    "This PC's addresses with the port (for example 192.168.1.10:8001), each with <b>Copy</b>, under <b>Use one of these in your app:</b>. Type one of them into your app as its destination.",
                    "<b>Auto-release address-only messages after</b> … <b>ms (default delay)</b>: ticked, a message with no value presses a Button input, then releases it after this delay; unticked, it presses and stays pressed. Ticked and 250 ms unless you change them (0 to 10000 ms). The delay is also used by Change and Message + data inputs. An input's own <b>Trigger on message</b> and delay override it.",
                    "<b>Pad address-only messages (treat them as value 1.0)</b>: a message with no value counts as the value 1.0. A Button input then presses and stays pressed until a 0 comes, unless it has <b>Trigger on message</b>. Off unless you turn it on.",
                    "<b>Allowed senders</b>: OSC is accepted only from the IP addresses and ranges listed, for example 192.168.1.5 or 192.168.1.0/24 (a range). Type one and choose <b>Add</b>; <b>Remove</b> asks first. Empty (the default): OSC from every sender is accepted. See " + _link("osc-allow-senders", "Accept OSC only from some senders") + "."
                ])
                + _good([
                    "The port opens when the program starts and stays open until you quit or turn <b>Listen for OSC messages</b> off: see " + _link("osc-tech-network", "OSC network and ports") + ".",
                    "If the port can't be opened, for example because another program uses it, the program shows one error when it starts (and again at Run only for a profile that uses OSC inputs), and Run still runs the rest of the profile: \"Could not bind OSC on host:port.\", with the host and port. Its detail names the program holding the port when Windows can tell (\"Port 8001 is in use by <i>name</i> (PID <i>n</i>).\"), else \"Port 8001 is in use by another program.\". The error is also written to the log."
                ]),
            related: ["osc-setup-window", "osc-output-tab", "osc-tech-network", "osc-troubleshooting"]
        },
        {
            id: "osc-output-tab",
            section: setup,
            title: "Output tab",
            body: "<p>Where the program sends OSC messages: the " + _link("device-bindings-actions-send-osc", "Send OSC") + " action and " + _link("osc-feedback-tab", "Feedback") + ".</p>"
                + _list([
                    "<b>OSC output (Send OSC actions and feedback)</b>: the master switch for everything OSC sends. Off, nothing is sent. On unless you turn it off.",
                    "<b>Reply to sender</b>: lets a Send OSC action or Feedback row send back to whoever sent the last message (that message's IP address and port). On unless you turn it off.",
                    "<b>Targets</b>: the places OSC sends to, each with a name, a host and a port. The first, <b>Default</b>, is 127.0.0.1 port 8000 unless you change it. With no targets, the list says \"No targets yet. Add one below.\"",
                    "To add a target, fill in the row below the list: <b>Name</b>, <b>IP address or computer name</b> and the port (8000 unless you change it), then <b>Add Target</b>. <b>Edit</b> puts a target in that row: change it, then <b>Save Target</b>, or <b>Cancel</b>. <b>Remove</b> asks first. Names must differ; renaming a target keeps the actions and rows that use it.",
                    "<b>Add Companion</b>: adds a target named Companion at 127.0.0.1 port 12321, the port of Companion's own OSC listener, or updates it when it exists, and says which it did. See " + _link("osc-companion", "Use with Companion") + ".",
                    "<b>Check Companion setup</b>: checks, line by line, what Companion needs from OSC here and changes nothing: OSC on and the port open (naming a program that holds it), OSC output on, a Companion target, its port (a port other than 12321 is marked <b>Check</b>, since you may have changed it in Companion) and, when there are Feedback rows, Feedback on. Each line says <b>OK</b>, or <b>Fix</b> with what to change."
                ])
                + _good([
                    "A target is the device's own address and the port it listens on, never this PC's.",
                    "Removing a target that actions or rows use: those send nothing until you pick another target. A Send OSC action shows <b>Missing target</b>."
                ]),
            related: ["osc-setup-window", "device-bindings-actions-send-osc", "osc-feedback-tab", "osc-tech-out"]
        },
        {
            id: "osc-feedback-tab",
            section: setup,
            title: "Feedback tab",
            body: "<p>Feedback sends the program's state to your OSC device, so its keys, lights and faders can show it: the current mode, a vJoy button, a gear lever axis, a Smart Toggle, whether the profile is paused.</p>"
                + "<p>The rows themselves are added and edited on the OSC page: see " + _link("osc-feedback-rows", "Feedback rows on the OSC page") + ". This tab holds the switches that apply to every row.</p>"
                + _list([
                    "<b>Send feedback to OSC devices</b>: turns Feedback on. On unless you turn it off; with no rows it sends nothing.",
                    "<b>Send everything again at:</b> <b>Run start</b>, <b>Mode change</b>, <b>Profile switch</b>: sends every row's value again at those moments, so the device shows the right state. All ticked unless you untick them.",
                    "<b>Send everything again when a message comes to</b> (the sync address, \"/gremlin/sync\" unless you change it): a device can ask for every row again by sending this address. Ticked unless you untick it. Capitals don't matter.",
                    "<b>At most</b> … <b>messages per second per address</b>: 50 unless you change it; a whole number, 1 or more.",
                    "The list of rows (read-only): each row's <b>On</b> or <b>Off</b>, address, source and where it sends. With no rows it says \"No feedback rows. Add them on the OSC page: right-click an input, Add Feedback.\" <b>Edit on the OSC page</b> takes you there.",
                    "<b>Companion custom variable…</b>: asks the <b>Variable name</b> (gremlin_mode unless you change it; no spaces) and, with <b>Add Row</b>, adds a row that sends the current mode's name to <code>/custom-variable/</code><i>name</i><code>/value</code> as Text, to the Companion target (added when missing). Create the custom variable in Companion first."
                ])
                + _good([
                    "How rows send, step by step: " + _link("osc-feedback-how", "How Feedback sends") + ".",
                    "Feedback sends only while the profile runs and while <b>OSC output (Send OSC actions and feedback)</b> is on.",
                    "On the OSC page, right-click empty space in the list and choose <b>Feedback settings…</b> to open this tab."
                ]),
            related: ["osc-feedback-rows", "osc-feedback-how", "osc-output-tab", "osc-companion"]
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
            id: "osc-page",
            section: inputs,
            title: "The OSC page",
            body: "<p>The OSC page lists every OSC input, one row per input, titled by its address (and its custom name, when you give one). It works like the Logical Device page.</p>"
                + _list([
                    "Under each address a line sums up its settings in the Add window's words, for example its mode, source value and delay. A pattern input says how many addresses it has seen, for example \"Pattern · 3 addresses seen\".",
                    "Each row shows the input's live value (a button pressed or not, an axis's value) and when a message last reached it (\"last seen 3 s ago\", or \"never\"), also with no Run while the port is open. On an axis input, <b>Invert</b> turns it the other way.",
                    "A pressed OSC button tints its row until it is released. While the profile is stopped the page also scrolls to the row and flashes it, as the Device Bindings page does for a stick; while it runs the row only tints. Faders and encoders only tint. <b>Input highlighting</b> in <b>Options</b> turns the scrolling off.",
                    "The input's actions for the current mode are its child rows, then its Feedback rows. Click a row to open it in the action pane; a new input shows <b>No actions</b> and <b>Add Action</b>.",
                    "Right-click for the menu: the input's own rows (" + _link("osc-edit-inputs", "Change, order or delete OSC inputs") + "), <b>Add Feedback</b> and <b>Companion feedback</b>, the <b>Row</b>, <b>Group</b> and <b>Groups</b> sections, <b>Add Inputs</b> (<b>Add…</b>, <b>Import…</b>, <b>From TouchOSC Layout…</b>, <b>Listen</b>, <b>Clear…</b>) and <b>Order</b>.",
                    "The page bar: <b>OSC Setup…</b> opens OSC's Module Setup, <b>Monitor</b> shows the " + _link("osc-monitor", "OSC Monitor") + " at the bottom of the page, and <b>Appearance…</b> sets how this page looks (its own look, apart from the Logical Device page's).",
                    "Find searches the address, custom name or the group. Its type box shows <b>All types</b>, <b>Buttons</b> or <b>Axes</b>, and its filters show only <b>Ungrouped</b> inputs, inputs with <b>No bindings in this mode</b>, or <b>Patterns</b>.",
                    "Groups may hold buttons and axes together. Drag rows to set your own order.",
                    "The page has its own Undo and Redo for every change made on it (adding, importing, addresses, settings, names, groups, order, deleting, clearing, actions and Feedback rows)."
                ])
                + _good([
                    "The page is locked while the profile runs, except Feedback rows: those can be changed while it runs, and a change takes effect at once.",
                    "The page has no <b>Hide system name</b>: the address is the input and always shows.",
                    "The Device Mapping Editor and the OSC card on Home show an OSC input by its address, for example /fire, not by a number."
                ]),
            related: ["osc-add-input", "osc-edit-inputs", "osc-feedback-rows", "osc-monitor"]
        },
        {
            id: "osc-add-input",
            section: inputs,
            title: "Add an OSC input",
            body: "<p>An OSC input turns one kind of message into a button or an axis.</p>"
                + _steps([
                    "On the <b>OSC</b> page, right-click the list and choose <b>Add Inputs</b> › <b>Add…</b>. The <b>OSC Input Mapper</b> window opens.",
                    "Type the address under <b>OSC message:</b> (it starts with \"/\"), or choose <b>Listen</b> and send one message from your app. Listen ends when that message arrives and fills in the address and its values (<b>Parameters:</b>). While it waits, the <b>Listening for OSC</b> box shows where OSC listens and where it sends (\"OSC output: On\" or \"Off\", and \"Targets:\" with each target's name, host and port, or \"none\"); its <b>Stop</b> stops listening.",
                    "Choose the <b>Action mode:</b> <b>Button</b>, <b>Axis</b>, <b>Change</b> or <b>Encoder</b>. See " + _link("osc-modes", "OSC input modes and data styles") + ".",
                    "Choose <b>Message only</b>, or <b>Message + data</b> to match the values in <b>Data:</b> too.",
                    "If the message has several values, choose which one to read in <b>Source value:</b> (P1, P2 …).",
                    "For an axis, set <b>Min:</b> and <b>Max:</b> (0 and 1 unless you change them; Min must be less than Max) and, under <b>Shaping</b>, a deadzone if you want one. For a button, tick <b>Trigger on message</b> to press and release on any message, and set its delay in ms (250 unless you change it; the 1/10s to 1s buttons fill it in).",
                    "Choose <b>OK</b>. The new input is selected and opens in the action pane; add its actions."
                ])
                + _good([
                    "Adding an input that already exists (the same address, and in Message + data the same values) selects the one already there; it doesn't make a second one.",
                    "Several inputs can share an address when their data or source value differ, for example /pad with P1 and /pad with P2.",
                    "The address may be a pattern such as <code>/deck/*</code>: one input answers every matching address. See " + _link("osc-patterns", "OSC address patterns") + ".",
                    "Listen works also when the profile isn't running. A Listen belongs to the window that started it: only that window takes the message, and cancelling or closing another window leaves it running.",
                    "If OSC is off or the port can't be opened, Listen says \"Could not start OSC listener.\": turn OSC on and check its host and port in OSC › Module Setup.",
                    "With <b>Allowed senders</b> set on the Server tab, Listen takes messages only from those senders.",
                    "To add many at once, see " + _link("osc-capture-import", "Capture or import many addresses") + "."
                ]),
            related: ["osc-modes", "osc-capture-import", "osc-edit-inputs", "osc-patterns"]
        },
        {
            id: "osc-capture-import",
            section: inputs,
            title: "Capture or import many addresses",
            body: "<h4>Bulk capture</h4>"
                + "<p>In the Add window (<b>OSC Input Mapper</b>), tick <b>Bulk capture</b>. Every new address that arrives becomes an input with the window's settings, until you untick it. Use it to press every key of a Stream Deck once. The same address twice within 0.3 seconds counts once. An address an input already answers (exactly or through a pattern) is skipped, and the window says how many: \"Skipped <i>n</i> already answered\". In Message + data, only an input with the same values counts.</p>"
                + "<h4>Import</h4>"
                + _steps([
                    "On the OSC page, right-click the list and choose <b>Add Inputs</b> › <b>Import…</b>.",
                    "In <b>New OSC messages:</b>, type or paste one address per line, or <b>Choose File…</b> to read a text file (.txt) with one message per line. After an address, add a space or a comma and a suffix to set the mode.",
                    "Choose <b>OK</b>. The result line says how many were added and skipped."
                ])
                + _table(["Suffix", "Makes", "Example"], [
                    ["(none) or B", "a Button", "<code>/key/1</code> or <code>/key/1 B</code>"],
                    ["BNP", "a Button with Trigger on message (presses and releases on any message)", "<code>/key/2 BNP</code>"],
                    ["A", "an Axis", "<code>/fader/1, A</code>"],
                    ["C", "a Change input", "<code>/scene C</code>"],
                    ["E", "an Encoder (an axis, format Auto)", "<code>/knob/1 E</code>"]
                ])
                + "<h4>TouchOSC layout</h4>"
                + _steps([
                    "Right-click the list and choose <b>Add Inputs</b> › <b>From TouchOSC Layout…</b> (or <b>Choose File…</b> in Import) and pick the layout's .tosc file.",
                    "The window lists every control that sends OSC, with the input it makes; one already in the list says so. Tick the ones you want (<b>Tick All</b>, <b>Tick None</b>).",
                    "Choose the button that adds them (\"Add 1 Input\", \"Add 5 Inputs\" and so on). <b>Back to Typed Messages</b> returns to the typed list."
                ])
                + _list([
                    "A fader, radial or encoder becomes an Axis, with the control's range; an XY pad or radar becomes two Axis inputs; a button becomes a Button; a radio or pager becomes a Change input.",
                    "The controls inside a grid or group are added. Labels, text and boxes are skipped, and the window names what it skipped.",
                    "Import adds inputs only, never a target: for feedback, add the phone as a target on the <b>Output</b> tab."
                ])
                + _good([
                    "Lines that don't start with \"/\" are skipped (the result names them), and so are addresses that already exist.",
                    "An unknown suffix makes a Button, and the result names the line."
                ]),
            related: ["osc-add-input", "osc-modes", "osc-touchosc", "osc-edit-inputs"]
        },
        {
            id: "osc-edit-inputs",
            section: inputs,
            title: "Change, order or delete OSC inputs",
            body: "<p>Right-click an input on the OSC page for its menu. Select several inputs to act on all of them.</p>"
                + _list([
                    "<b>Change Address…</b>: edits the address. It must start with \"/\" and can't be blank or a duplicate; the window says why on its own line before it closes. The input keeps its actions, its custom name and every link to it.",
                    "<b>Edit Settings…</b>: opens the same choices as Add, in the <b>OSC Input Settings</b> window. The input keeps its actions. With several inputs selected it reads \"Edit Settings of 3 Inputs…\" (with their number): a setting they don't share shows blank, and only what you change is applied to each. An input that can't change mode (below) is named and left as it is. One Undo step.",
                    "<b>Copy for Companion</b>: copies, as text, the settings for Companion's Generic OSC connection (Target Hostname or IP, Target Port, Protocol UDP, Listen for Feedback on, Source Port 9001) and the key actions for this input, to follow while you set up Companion. See " + _link("osc-companion", "Use with Companion") + ".",
                    "<b>Send Test Press</b> (a button input) or <b>Send Test Value</b> (an axis input: type a value from −1 to 1, then <b>Send</b>): gives the input a message as if it came from the network, so you can try its actions without the app. It fires actions only while the profile runs, shows in the live value, and is not listed in the OSC Monitor. On a pattern input it uses the last address that input received.",
                    "<b>Delete…</b>: asks first (<b>Delete Input</b>), then removes the input and its actions in every mode. Undo puts it back, and you can restore it from <b>Tools › History</b>" + _show("menu/Tools/History") + ".",
                    "<b>History</b>: opens History with only this input's saved changes.",
                    "<b>Order</b> › <b>By Address</b>: orders the inputs A to Z by address within each group. Dragging rows sets your own order; the order is kept in OSC's file.",
                    "<b>Add Inputs</b> › <b>Clear…</b>: removes every OSC input and its actions from OSC's list, which every profile uses, after asking (<b>Clear OSC Inputs</b>). One Undo step."
                ])
                + _good([
                    "An input that has actions can't switch between Axis and the button modes (Button, Change, Message + data, an encoder's pulses): remove its actions first, since an axis and a button take different actions. Switching among the button modes is fine.",
                    "Editing is locked while the profile runs, except Feedback rows."
                ]),
            related: ["osc-page", "osc-add-input", "osc-modes", "tools-history"]
        },
        {
            id: "osc-patterns",
            section: inputs,
            title: "OSC address patterns",
            body: "<p>An input's address may be an OSC pattern, so one input answers many addresses: <code>/deck/*</code> answers <code>/deck/1</code>, <code>/deck/2</code> and so on.</p>"
                + _table(["Pattern", "Matches", "Example"], [
                    ["<code>*</code>", "any characters, or none, within one part of the address", "<code>/deck/*</code>"],
                    ["<code>?</code>", "any one character", "<code>/key/?</code>"],
                    ["<code>[ ]</code>", "one of the characters listed, or a range; with an exclamation mark first, any one character but those", "<code>/key/[1-4]</code>"],
                    ["<code>{ }</code>", "one of the words listed", "<code>/{fire,jump}</code>"]
                ])
                + _list([
                    "The input keeps its state for each address: a button is pressed while any of its addresses is pressed, an axis takes the last value received, and Change and encoder inputs keep the last value of each address.",
                    "When an exact input and a pattern input both match a message, the exact input gets it and the pattern doesn't. Pattern inputs that overlap all fire.",
                    "No pattern character crosses a \"/\", and capitals don't matter.",
                    "A message whose own address is a pattern reaches the exact inputs it matches, never pattern inputs.",
                    "In the Add window, a pattern says how many of the addresses seen so far it matches: \"Matches <i>n</i> of the addresses seen\".",
                    "Scripts and conditions can tell which address sent an event: see " + _link("osc-scripts", "OSC in conditions, macros and scripts") + "."
                ])
                + _good([
                    "A stray <code>]</code> or <code>}</code> (with no opening <code>[</code> or <code>{</code>) is refused, saying where. A space or <code>#</code> is refused in every address.",
                    "Send OSC and Feedback rows send to one exact address: a pattern there is refused, saying why. <b>Add Feedback</b> on a pattern input starts the row's address as <code>/gremlin/feedback</code>.",
                    "<b>Copy for Companion</b> on a pattern input uses an address it has seen, since Companion sends one exact address per key."
                ]),
            related: ["osc-add-input", "osc-tech-addresses", "osc-capture-import"]
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
                + "<h4>Shaping an axis</h4>"
                + _list([
                    "<b>Invert</b> (the box on an axis input's row) turns the axis the other way.",
                    "<b>Deadzone low:</b> and <b>high:</b> (under <b>Shaping</b> in the Add window, for an Axis or an Encoder with Axis output): values from low to high, around the center, give 0, and the rest is stretched back to the full range. Low is from −0.99 to 0, high from 0 to 0.99; 0 and 0 is no deadzone. For example −0.1 and 0.1.",
                    "Both apply before any action."
                ])
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
                    "<b>Format:</b> <b>Auto</b> works it out from what arrives: only 1 and 0 mean clockwise and counter-clockwise; once a negative or any other value arrives, it reads +n and −n until the profile runs again. Choose <b>1 = clockwise, 0 = counter-clockwise</b> or <b>+n and −n</b> to set it yourself.",
                    "<b>+n and −n</b>: the value is how many steps it turned, + clockwise and − counter-clockwise. <code>/knob 3</code> is 3 steps clockwise; <code>/knob -1</code> one step back.",
                    "<b>Output:</b> <b>Axis</b> moves an axis by the <b>Step size:</b> (0.05 unless you change it, up to 2) for each step, and stops at the ends.",
                    "<b>Output:</b> <b>Pulses clockwise</b> or <b>Pulses counter-clockwise</b> makes a button that presses, and releases after <b>Release after:</b> (100 ms unless you change it), once for each step that way. Turn the knob fast and the pulses queue (up to 32).",
                    "<b>Acceleration:</b> <b>Off</b> (unless you change it), <b>Low</b>, <b>Medium</b> or <b>High</b>. Turning fast multiplies the step size or the pulses, up to 8 times; Off counts every turn once. The exact rule is in " + _link("osc-tech-timing", "OSC timing and limits") + "."
                ])
                + _good([
                    "For both directions as buttons, add two inputs on the same address: one with Pulses clockwise and one with Pulses counter-clockwise.",
                    "Import's E suffix makes an Encoder axis with Format Auto."
                ]),
            related: ["osc-modes", "osc-capture-import", "osc-tech-in", "osc-tech-timing"]
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
            related: ["osc-tech-in", "osc-tech-out", "device-bindings-actions-send-osc"]
        },

        // ---- Sending OSC ----
        {
            id: "osc-send",
            section: sending,
            title: "Send OSC from an input",
            body: "<p>To send a message when you press a button or move an axis, add the " + _link("device-bindings-actions-send-osc", "Send OSC") + " action to it. It sends to a target from the <b>Output</b> tab, or to <b>Reply to sender</b>.</p>"
                + "<p>To keep a device in step with the program's state instead, add " + _link("osc-feedback-rows", "Feedback rows") + ": they send only when something changes.</p>"
                + "<p>Scripts can send OSC to a named target too: see " + _link("osc-scripts", "OSC in conditions, macros and scripts") + ".</p>",
            related: ["device-bindings-actions-send-osc", "osc-output-tab", "osc-feedback-rows"]
        },
        {
            id: "osc-feedback-rows",
            section: sending,
            title: "Feedback rows on the OSC page",
            body: "<p>Each Feedback row sends one value to one address. Rows are added and edited on the OSC page; the " + _link("osc-feedback-tab", "Feedback tab") + " holds the switches for all of them.</p>"
                + "<h4>Add a row</h4>"
                + _list([
                    "Right-click an input › <b>Add Feedback</b>: a row that sends this input's value back to <b>Reply to sender</b>, at the input's own address (a pattern input: <code>/gremlin/feedback</code>).",
                    "Right-click an input › <b>Companion feedback</b> › <b>Key text</b> or <b>Key color</b>: a row that sends this input's value to the Companion target (added when there is none), to the key at page 1, row 0, column 0: <code>/location/1/0/0/style/text</code> as Text, or <code>/location/1/0/0/style/bgcolor</code> with an <b>Off</b> color #333333 and an <b>On</b> color #2a7a46. Change the page, row and column in the row's <b>Address</b> (pages count from 1, rows and columns from 0). The page reminds you: \"Turn on Companion's OSC Listener (Settings › OSC) first.\"",
                    "OSC Setup › <b>Feedback</b> › <b>Companion custom variable…</b>: a row that sends the current mode's name to a Companion custom variable."
                ])
                + "<h4>Where rows show</h4>"
                + _list([
                    "A row whose source is an OSC input shows under that input, after its actions; so does a row whose source is an action on that input. Any other row is in the group <b>Feedback not tied to an input</b> at the bottom.",
                    "<b>Show under this input</b> in the row's editor puts it under another input; <b>By its source</b> (the default) follows the rules above.",
                    "Each row reads \"Sends <i>what</i> to <i>target</i> · <i>address</i>\", for example \"Sends this input's value to the sender · /fire\", with a <b>Send this feedback</b> box to turn it off.",
                    "Click a row to edit it in the pane. Right-click it for <b>Open</b>, <b>Turn Off</b> (or <b>Turn On</b>), <b>Duplicate</b> and <b>Delete…</b> (asks first)."
                ])
                + "<h4>Each row</h4>"
                + _list([
                    "<b>Source</b>: <b>Current mode</b> (the mode's name, as text); <b>vJoy button</b> or <b>vJoy axis</b> (pick the vJoy device and type the number); <b>Logical Device control</b> (<b>Pick a control</b>); <b>OSC input</b> (<b>Pick an OSC input</b>: its own value, sent back); <b>Action state</b> (<b>Pick an action</b>: a Smart Toggle's on or off, or a Tempo's last press, long = on and short = off); or <b>Running / Paused</b> (on while the profile runs, off while it is paused; nothing is sent while no profile runs).",
                    "<b>Send to</b>: a target from the Output tab, or <b>Reply to sender</b>.",
                    "<b>Type</b>: <b>Auto</b>, <b>Int</b>, <b>Float</b>, <b>Bool</b> (true/false) or <b>Text</b>; see " + _link("osc-value-types", "OSC value types") + ".",
                    "<b>Address</b>: the OSC address to send, for example <code>/led/gear</code>. It starts with \"/\", has no spaces or <code>#</code>, and can't be a pattern.",
                    "<b>Min</b> and <b>Max</b>: a button sends Max when pressed and Min when released; an axis sends its position from Min (one end) to Max (the other end). 0 and 1 unless you change them.",
                    "<b>Off</b> and <b>On</b>: for an on/off source, the exact values sent instead of Min and Max, for example <code>#333333</code> and <code>#2a7a46</code>, a number, or text. Blank uses Min and Max. A color written #rrggbb (or r g b) sent to a Companion key color (an address ending /style/bgcolor or /style/color) goes as three whole numbers, r g b; to any other address it is sent as written."
                ])
                + _good([
                    "Rows can be added, changed and turned off while the profile runs; a change takes effect at once.",
                    "Adding, changing or removing a row is one step of the OSC page's Undo. Making the Companion target for Key text or Key color is not: Undo removes the row and keeps the target.",
                    "An Action state row whose action isn't in the open profile sends nothing and says \"This action is not in the current profile\". When the action is used in several places, the state is on if any of them is on. With no Smart Toggle or Tempo in the profile, the picker says so.",
                    "How rows send, step by step: " + _link("osc-feedback-how", "How Feedback sends") + "."
                ]),
            related: ["osc-feedback-tab", "osc-feedback-how", "osc-companion", "osc-value-types"]
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
            related: ["osc-feedback-rows", "osc-feedback-tab", "osc-tech-timing", "osc-companion"]
        },
        {
            id: "osc-monitor",
            section: sending,
            title: "Watch messages with the OSC Monitor",
            body: "<p>The <b>OSC Monitor</b> lists the last 200 OSC messages in and out. Use it to see what an app really sends.</p>"
                + "<p>It is a panel at the bottom of the OSC page, folded unless you unfold it: choose <b>Monitor</b> in the page bar, or click the panel's heading. <b>Tools › OSC Monitor</b>" + _show("menu/Tools/OSC Monitor") + " opens the OSC page with the panel unfolded. Drag its grip to set its height (remembered); <b>×</b> hides it until you choose Monitor again. <b>Pop out</b> shows it in a window of its own; closing that window puts it back in the page.</p>"
                + _list([
                    "Columns: <b>Time</b>, <b>In / Out</b>, <b>Address</b>, <b>Values</b>, <b>From / To</b> (the other side's address and port) and <b>Input</b> (the inputs it matched, or no input). Point at a cut-off address to see it whole.",
                    "<b>Pause</b> stops adding new messages; <b>Resume</b> shows them again. <b>Clear</b> empties the list. Type in the filter (address, value, from / to or input) to show only matching rows.",
                    "<b>Show outgoing</b>: also lists what the program sends (Send OSC and Feedback). On unless you turn it off.",
                    "On a no input row, <b>Add as Input…</b> (on the row, or in its right-click menu) opens Add with the address and values filled in. Hidden while the profile runs.",
                    "A sync message shows with Sync in the <b>Input</b> column. A message from a sender not on <b>Allowed senders</b> shows as blocked; right-click it › <b>Allow this sender</b> adds it to the list."
                ])
                + _good([
                    "While the panel is unfolded on the OSC page, or popped out, the port stays open, also when the profile isn't running. Folding it or leaving the OSC page frees the port, unless a Run or Listen still needs it.",
                    "Send Test Press and Send Test Value are not network messages, so they don't show here.",
                    "Incoming addresses show in lower case."
                ]),
            related: ["osc-add-input", "osc-troubleshooting", "osc-tech-network"]
        },

        // ---- How to ----
        {
            id: "osc-companion",
            section: howto,
            title: "Use with Companion",
            body: "<p>Bitfocus Companion, with its Generic OSC connection, works with the program in both directions. Nothing in the program depends on Companion: these steps only fill in ordinary OSC settings.</p>"
                + "<h4>Stream Deck key presses an input</h4>"
                + _steps([
                    "On the OSC page, choose <b>Copy for Companion</b> in an input's menu and paste the text somewhere to read: it lists the settings below for that input.",
                    "In Companion, add a <i>Generic OSC</i> connection. <i>Target Hostname or IP</i>: 127.0.0.1 if Companion runs on this PC, else an address from the <b>Server</b> tab. <i>Target Port</i>: 8001 (the program's <b>Port</b>). <i>Protocol</i>: UDP.",
                    "On a key, add a press action <i>Send integer</i> with path <code>/sd/fire</code> and value 1, and a release action <i>Send integer</i> <code>/sd/fire</code> value 0.",
                    "In the program, right-click the OSC page's list › <b>Add Inputs</b> › <b>Listen</b>, press the key, choose <b>Button</b>, <b>OK</b>."
                ])
                + "<p>Other Companion sends work too: float (Axis), string (Message + data), several values (Source value P1, P2), boolean, no value (use Trigger on message, since there is no release), and rotary keys (Encoder).</p>"
                + "<h4>Show the program's state on keys</h4>"
                + _steps([
                    "In Companion: <i>Settings › OSC</i>, turn on the <i>OSC Listener</i> (off unless you turn it on; port 12321).",
                    "In Companion, create a custom variable, for example gremlin_mode.",
                    "In the program, <b>OSC Setup…</b> › <b>Output</b>: <b>Add Companion</b>, then <b>Check Companion setup</b> and fix any line that isn't OK.",
                    "On the <b>Feedback</b> tab, choose <b>Companion custom variable…</b>, keep gremlin_mode and choose <b>Add Row</b>. The row sends <b>Current mode</b> to the Companion target at <code>/custom-variable/gremlin_mode/value</code> as <b>Text</b>.",
                    "In Companion, put <code>$(custom:gremlin_mode)</code> in a key's text, or use it in an expression feedback to color the key.",
                    "Run the profile. The key shows the mode name."
                ])
                + "<p>To show an input's own state on a key instead, right-click the input on the OSC page › <b>Companion feedback</b> › <b>Key text</b> or <b>Key color</b>, and set the key's page, row and column in the row's address. See " + _link("osc-feedback-rows", "Feedback rows on the OSC page") + ".</p>"
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
                    "In the program, right-click the OSC page's list › <b>Add Inputs</b> › <b>From TouchOSC Layout…</b> and choose the layout's .tosc file to add its controls at once (see " + _link("osc-capture-import", "Capture or import many addresses") + "). Or use <b>Listen</b> and touch each control once, or tick <b>Bulk capture</b> and touch them all. Faders and XY pads are <b>Axis</b>; their range is usually 0 to 1.",
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
            id: "osc-allow-senders",
            section: howto,
            title: "Accept OSC only from some senders",
            body: "<p>On a shared network you can let only your own devices reach the program.</p>"
                + _steps([
                    "Open <b>OSC Setup…</b> › <b>Server</b>.",
                    "Under <b>Allowed senders</b>, type a device's IP address (for example 192.168.1.5) or a range (for example 192.168.1.0/24, every address from 192.168.1.0 to 192.168.1.255), then <b>Add</b>.",
                    "Add every device that sends to the program. 127.0.0.1 is this PC itself, for an app such as Companion running here."
                ])
                + _list([
                    "With the list empty (the default), OSC from every sender is accepted.",
                    "With anything on the list, a message from any other sender reaches nothing: no input, no Listen or Bulk capture, no Feedback sync. The OSC Monitor still lists it as blocked; right-click it › <b>Allow this sender</b> to add that sender.",
                    "<b>Remove</b> asks first. Removing the last entry means every sender is accepted again."
                ])
                + _good([
                    "The list is kept in OSC's module file and travels with it (Device Library, Export, Export / Import Device, History)."
                ]),
            related: ["osc-server-tab", "osc-monitor", "osc-checklist"]
        },
        {
            id: "osc-scripts",
            section: howto,
            title: "OSC in conditions, macros and scripts",
            body: "<p>OSC inputs can be used wherever a stick input can.</p>"
                + _list([
                    "Conditions: in a <b>Joystick</b> condition, choose an input with <b>OSC input…</b> (listed by address). The condition reads the input's last value. There is no separate OSC condition.",
                    "Macros: <b>Add Step</b> › <b>OSC</b> plays an OSC input's press, release or value as if it had arrived. Record opens the port while it records; an OSC step plays as it is and is not recorded again.",
                    "Scripts: a script variable for an OSC input (<code>OscInputVariable</code>) puts its callback on that input, like a stick input; a new one starts with no input chosen. The event's <code>osc_address</code> is the address that was received, so a pattern input's script can tell which address sent it.",
                    "Scripts that send OSC: a callback with a parameter named <code>osc</code> gets the program's OSC sender. <code>osc.send(\"Companion\", \"/my/address\", 1, types=[\"int\"])</code> sends to the target with that name (any capitals); <code>types</code> is optional (auto, int, float, bool or text for each value)."
                ])
                + _good([
                    "Scripts send only to named targets from the Output tab, never to a raw host and port.",
                    "A send that can't go (no target with that name, a pattern or bad address, OSC output off, or no Run) returns False and is written to the log once."
                ]),
            related: ["osc-patterns", "osc-output-tab", "osc-send"]
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
                    "<b>Listen for OSC messages</b> is on (Server tab): the port is then open whenever the program is open.",
                    "If <b>Allowed senders</b> on the Server tab lists anything, the app's address is on it.",
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
                    "Unfold the <b>OSC Monitor</b> on the OSC page. The port is open while <b>Listen for OSC messages</b> is on, so if nothing shows there, the messages don't reach this PC. Messages that show as blocked come from a sender not on <b>Allowed senders</b> (Server tab).",
                    "Look at the OSC card on Home first: its second line says whether the server is listening, and why not (" + _link("osc-card-line", "The OSC card on Home") + ").",
                    "Check the app's host and port against the <b>Server</b> tab, and that <b>Listen for OSC messages</b> is on.",
                    "Check the firewall (see " + _link("osc-checklist", "Connection checklist") + ").",
                    "\"Could not bind OSC on host:port.\": another program uses that port; the error's detail names it when Windows can tell. Close it or choose another <b>Port</b> (and set the same in the app).",
                    "A typed <b>Host</b> that isn't this PC's current address can't listen. Leave it blank."
                ])
                + "<h4>Messages arrive, but nothing happens</h4>"
                + _list([
                    "The Monitor's <b>Input</b> says no input: the address (or data) doesn't match an input. Use <b>Add as Input…</b>.",
                    "To try an input's actions without the app, right-click it › <b>Send Test Press</b> or <b>Send Test Value</b> while the profile runs.",
                    "The profile isn't running (<b>Run</b>" + _show("toolbar/Run") + "), or the open profile gives the OSC inputs no actions: with no OSC inputs in use, Run doesn't open the port.",
                    "A Button that never releases: the app sends only on press. Tick <b>Trigger on message</b>."
                ])
                + "<h4>Companion doesn't update</h4>"
                + _list([
                    "Companion's <i>OSC Listener</i> is off (Settings › OSC), or the custom variable doesn't exist yet.",
                    "The Feedback row sends to <b>Reply to sender</b> but Companion's Generic OSC connection has <i>Listen for Feedback</i> off: send to the Companion target (port 12321) instead.",
                    "<b>OSC output (Send OSC actions and feedback)</b> or <b>Send feedback to OSC devices</b> is off, or the profile isn't running.",
                    "<b>Check Companion setup</b> on the Output tab goes through these line by line."
                ])
                + "<h4>Trace OSC step by step</h4>"
                + _list([
                    "Open <b>Debug › Live Log Reader</b>, choose the <b>Trace</b> tab and tick the <b>OSC</b> row, or only the areas you need: <b>Receive</b>, <b>Inputs</b>, <b>Output</b>, <b>Feedback</b>, <b>Setup and files</b>.",
                    "Turn <b>Tracing</b> on" + _show("menu/Debug/Tracing") + ", then send from the app or run the profile.",
                    "Each step writes a line; a <b>BLOCKED</b> line says what stopped the message and why, for example \"send refused: OSC output is Off\" or \"/fader1: no input answers\".",
                    "See " + _link("tools-trace", "Follow your controls with Trace") + " for every area and the limits."
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
                    "Whenever the program is open and <b>Listen for OSC messages</b> is on: from start-up until you quit, with or without a running profile. The OSC page shows live values and Listen works without the Monitor.",
                    "A stopped profile still runs no actions: messages update the live values, the Monitor and Listen only.",
                    "Never while <b>Listen for OSC messages</b> is off: turning it off closes the port at once and frees it for other programs.",
                    "Changing the host or port moves the open port at once."
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
                    "An input's address matches a message's address exactly, unless the input's address is an OSC pattern (<code>*</code>, <code>?</code>, <code>[ ]</code>, <code>{ }</code>): see " + _link("osc-patterns", "OSC address patterns") + ". An exact input wins over a pattern input for the same message.",
                    "A space or <code>#</code> is refused in every address, incoming and outgoing. Addresses the program sends can't be patterns.",
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
                    "Encoder 1 = clockwise, 0 = counter-clockwise: 0 turns back, anything else turns forward one step. +n and −n: the number is the steps. Auto starts as 1/0 and switches to +n/−n when a value other than 0 or 1 arrives, until the next Run.",
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
            related: ["osc-value-types", "device-bindings-actions-send-osc", "osc-feedback-how"]
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
                    ["Encoder acceleration", "Off", "Low, Medium or High"],
                    ["Sync address", "/gremlin/sync", "on unless you turn it off"]
                ])
                + "<p>Encoder acceleration counts the steps turned in the last 0.1 s and multiplies the step size (or the pulses) by 1 + <i>factor</i> × (steps − 1), at most 8 times. The factor is 0.5 for <b>Low</b>, 1 for <b>Medium</b> and 2 for <b>High</b>; <b>Off</b> is 0.</p>",
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
                    "OSC's inputs and settings are kept only in OSC's module file; a profile keeps only the actions it gives them. Profiles from older versions open, but OSC inputs or settings stored in them are not read.",
                    "Any change to OSC marks the profile changed (<b>*</b>): <b>File › Save Profile</b>" + _show("menu/File/Save Profile") + " saves OSC's file too, and Discard throws the OSC changes away.",
                    "OSC's inputs, settings, targets and Feedback rows travel with Save to Device Library, Restore, Export and Export / Import Device, and every save is in History.",
                    "The port is open while the program is open and <b>Listen for OSC messages</b> is on, and closes at quit.",
                    "Deleting an input asks first; you can restore it from <b>Tools › History</b>" + _show("menu/Tools/History") + "."
                ]),
            related: ["osc-about", "osc-tech-network", "device-library-built-in", "tools-history"]
        },

        // ---- Common questions ----
        {
            id: "osc-q-nothing",
            section: questions,
            title: "Why does nothing happen when my app sends OSC?",
            body: "<p>Open the <b>OSC Monitor</b>" + _show("menu/Tools/OSC Monitor") + ". If nothing shows, check the address, port and firewall; if the Input column says no input, add an input for that address. See " + _link("osc-troubleshooting", "When OSC doesn't work") + ".</p>",
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
            body: "<p>It has actions made for a button. Remove its actions first, then change the mode. See " + _link("osc-edit-inputs", "Change, order or delete OSC inputs") + ".</p>",
            related: ["osc-edit-inputs"]
        }
    ]
}
