# Fresh-reader FR3 (2026-11-22, 07:33-07:35)

Help read: qml/help/osc.js (whole), plus the topics it links to for vJoy and
Trace: device-bindings-actions-map-to-vjoy, device-bindings-actions-q-vjoy-not-claimed,
home-devices-vjoy-output (home_devices.js), tools-trace and tools-trace-osc (tools.js).

## Task 1: a Stream Deck key (through Companion) presses vJoy 1 button 5 over OSC

Could do it: **yes, with small guesses**.

Steps:
1. Home, double-click the OSC card; **OSC Setup…**, Server tab: Listen for OSC messages on, note port 8001 (options-profile-osc).
2. Companion: Generic OSC connection, host 127.0.0.1, port 8001, UDP; key press action Send integer `/sd/fire` 1, release action Send integer `/sd/fire` 0 (osc-companion).
3. OSC page, right-click the list, **Add Inputs › Listen**, press the key, choose **Button**, **OK** (osc-companion).
4. In the action pane, **Add Action › Map to vJoy**, pick the vJoy 1 device "by its output module name", output Button 5 (options-profile-osc step 8, device-bindings-actions-map-to-vjoy).
5. If Button 5 isn't offered: right-click the vJoy card, **Module Setup…**, tick Button 5, **Save Module** (home-devices-vjoy-output).
6. **Run**. Press the key; the game sees vJoy 1 button 5.

Problems:
- Got stuck briefly. osc.js, osc-companion: the key-press steps end at "Choose Button, then OK." They never say to add the Map to vJoy action or press Run. I had to go back to options-profile-osc steps 8-9 to find them. Fix: add the two steps "Add Action › Map to vJoy" and "Run" to osc-companion.
- Had to guess. device_bindings_actions.js, device-bindings-actions-map-to-vjoy: "Pick the vJoy device, by its output module name". It doesn't say what the name looks like, or whether "vJoy 1" means vJoy device 1. Fix: give an example name, for example "vJoy 1 (vJoy Device 1)".
- Had to guess. Map to vJoy says the list "offers only outputs that are ticked in Output Module Setup". It doesn't say that a fresh vJoy device may have nothing ticked, so Button 5 could simply be missing from the list. Fix: one line in osc-companion, or in Map to vJoy: "Button 5 not listed? Tick it in the vJoy card's Module Setup."
- Slow to read. The same setup is spread over options-profile-osc, osc-companion and osc-checklist, with steps repeated and partly different. Fix: give osc-companion the full path from start to Run, and link to it from the other two.
- Had to guess about names. "Module Setup", "Input Module Setup" (the title bar), "OSC Setup…" and "Open OSC Module Setup" all name one window (osc-about, osc-setup-window). Fix: one name, with the others listed once in osc-setup-window.

## Task 2: the Stream Deck key lights up while vJoy 1 button 5 is held (feedback)

Could do it: **with guesses**.

Steps:
1. Companion: turn on the OSC Listener, port 12321 (osc-companion, second step list).
2. OSC Setup, Output tab: **Add Companion**, then **Check Companion setup** (osc-output-tab).
3. OSC page: right-click the `/sd/fire` input, **Feedback › Companion feedback › Key color** (osc-feedback-rows).
4. Open the row. Change **Source** to **vJoy button**, device vJoy 1, number 5 (my guess: see below). Set the Address to the key's page/row/column, for example `/location/1/0/0/style/bgcolor` (osc-tech-companion).
5. Leave Off/On blank to keep #333333 and #2a7a46, or type colors. Run the profile.

Problems:
- Got stuck. osc.js, osc-companion: there are steps for "Show the program's mode on a key" only. "To show an input's own state on a key instead, use Companion feedback". Nothing covers lighting a key from a vJoy button. Fix: add a short how-to, "Light a key while a vJoy button is held", with the steps above.
- Had to guess. osc-feedback-rows: Key color "sends this input's value to a Companion key". The row's source is the OSC input, not vJoy 1 button 5. The Help doesn't say whether to change Source to **vJoy button** on that row, or how to start a row with no input (the only "not tied to an input" route is Companion custom variable, and that sends the mode only). Fix: say that you can change any row's Source, and give a menu route for a new row that isn't tied to an input.
- Had to guess. osc-feedback-rows: "It starts on page 1, row 0, column 0. Change these in the row's Address." It doesn't say which part of the address is which until osc-tech-companion, two sections later. Fix: show the address pattern `/location/<page>/<row>/<column>/style/bgcolor` right there.
- Topics disagree in tone. osc-companion says Key color "overwrite[s] the key's own style" and that custom variables are "the cleaner route". But there is no custom-variable route for a vJoy button. Fix: either say a custom variable can carry any source, or say Key color is the way for a vJoy source.
- Had to guess. There are two Companion ports: the connection's Target Port 8001 (Companion to the program) and the OSC Listener on 12321 (the program to Companion). Also "Listen for Feedback ... with a source port other than 8001". It isn't clear which one feedback needs. Fix: a two-row table in osc-companion: "Companion → program: 8001; program → Companion: 12321 (OSC Listener)".

## Task 3: it doesn't work; find out why using only the troubleshooting

Could do it: **with guesses**. It's fine for "nothing arrives". It's weak when the input fires but the game or key doesn't react.

Path I took (osc-troubleshooting):
1. The OSC card's second line ("Listening on …" or "Server not started …").
2. OSC Monitor: In rows arrive? The Input column names `/sd/fire`?
3. Profile running; the input has actions; Trigger on message if the key never releases.
4. Companion doesn't update: OSC Listener, Feedback switches, **Check Companion setup**.
5. Trace: Debug › Live Log Reader › Trace, tick OSC, Tracing on, read the BLOCKED lines.

Problems:
- Got stuck. osc.js, osc-troubleshooting has no case for "the input presses but the game sees no vJoy button". The list stops at the OSC side. Map to vJoy's red ⚠ / "(not claimed)" (device-bindings-actions-q-vjoy-not-claimed, home-devices-vjoy-output) and getting-started-nothing-reaches-vjoy aren't linked. Fix: add a section "The input fires, but the game sees nothing": a red ⚠ output, an output not ticked in the vJoy Module Setup, the profile not running, plus links.
- Had to guess. Its Trace steps say to tick "Receive, Inputs, Output, Feedback". Only tools-trace-osc says that the **Inputs** area shows what the actions send ("OUTPUT or BLOCKED lines"). That is the line that would show the vJoy press. Fix: in osc-troubleshooting, say "Inputs shows the vJoy output; Feedback shows the key color sent".
- Got stuck. The "Companion doesn't update" section is about custom variables and Reply to sender. It doesn't cover a Key color row: a wrong page/row/column in the Address, a Source still on the OSC input instead of vJoy button 5, or a wrong Type (osc-value-types says key color "wants numbers"). Fix: add those three lines.
- Slow to read. One cause has two different messages: the Server tab's "Could not bind OSC on host:port." and the card's "Server not started: port 8001 is in use". It reads like two problems. Fix: say they are the same, in one place.
- Minor. osc-checklist: "allow incoming UDP on port 8001" assumes the default port. Fix: "on your Port (default 8001)".

## Top 3 problems
1. osc-troubleshooting stops at the OSC side. Nothing covers "the OSC input fires but vJoy or the game sees nothing", and there are no links to Map to vJoy ⚠ / not claimed.
2. There is no how-to for lighting a Companion key from a vJoy button. osc-feedback-rows doesn't say that a row's Source can be changed from "this input" to vJoy button, and there's no route to a new row with no input.
3. osc-companion's key-press steps end at OK. Adding Map to vJoy, ticking the output in the vJoy Module Setup, and Run all live in other topics.
