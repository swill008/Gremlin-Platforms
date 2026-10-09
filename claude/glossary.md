# Glossary

One word for each idea in everything the user reads: menus, buttons, window
titles, messages, Options and help. Status: **approved 2026-10-02**; new text follows it.
Tracker refs in brackets.

| Idea | Use | Instead of (today) |
|---|---|---|
| Starting / stopping the profile [D1] | **Run** / **Stop**; status **Running** / **Stopped**; toolbar button "Run" (shows "Stop" while running); tray "Run Profile" / "Stop Profile" | Toggle, Toggle Active, Active, Not Running, Activate, Deactivate, "Activate Gremlin" |
| What an input does [D2, D11] | **action** (an input's actions); an input with none: **No actions** | mapping, Unmapped, Not bound, Unbound, Empty |
| The input device that feeds an output card | **Driven by: [device]**, or **Driven by: [nothing]** | Bound to: [Not bound] |
| The page where you edit a device's actions [D6] | **Configuration** (unchanged) | |
| The window for a device's module (claims, file, picture) [D6] | **Module Setup** ("Module Setup…" on the card). Tools › Device Setup has **Input Module Setup** and **Output Module Setup** (they pick the kind), and the window is titled the same (03 Q11) | Configure input module / Configure output module |
| The Button Map's settings | **Button Map Options**: a pane on the Button Map's tool rows (the **Options** tab, or Edit → Button Map Options…), not in the main Options (07 Q17) | Editor options, Options → Button Map, a window of its own |
| The log window (Debug menu) | **Live Log Reader**, tabs **Config** / **Debug** / **Input Monitor** | Log viewer, Debug window |
| The zip of logs, settings, devices and versions for a problem report (Help menu, Debug tab) [01 S132] | **Save Diagnostics…**; the box **Include the open profile**; done: "Diagnostics saved to [path]."; failed: "Diagnostics not saved." with the file, folder and reason | Export logs, Support bundle, Report |
| Watching every log line as it happens | **Live** (red button on the Debug tab); **All logs** in the Log list; **Start empty**, **Clear View**, **Save Feed…**, **Show Log File** | Live capture, Tail, Stream |
| Watching inputs and the actions they ran | **Input Monitor** (tab), **Monitor** (its red button); an input with none shows **no actions** | Live capture, Event viewer, nothing bound, Unbound |
| How much the program writes to its log files | **Diagnostic logs** (Off / ALL / Info / Warning / Error) | Debug level, Log level |
| Writing where the program is stuck when it stops responding | **Log When Not Responding** (Options › Diagnostics; off by default) | Watchdog, Hang detection, Freeze logging |
| The red frame while debugging | **red debug mode**; badge **DEBUG** (shows while Diagnostic logs is ALL or Live runs) | Debug overlay, Vignette |
| The editor for how a page looks (Home, Configuration, Logical) [D9] | **Appearance** ("Appearance…") | Show Editor, Display, Display Editor, View Settings, Display options |
| The current mode [D10] | one label, **Mode**, on the toolbar; the footer's duplicate goes | "Configuring mode" + "Executing mode" (always the same) |
| Hiding a card from Home [D3] | **Hide Card** / **Hidden Cards** | Hide device / Hidden devices (too close to HidHide) |
| Putting one stick's setup on another (10) | card and Device menu commands **Copy Setup to Another Stick…** (card) / **Copy to Another Stick…** (Device Library), **Swap with Another Stick…**, **Change vJoy Output…**; "Assign hardware" stays only on the Logical page | Swap Device…, Swap Devices (replaced 2026-10-08), Assign hardware… on the card |
| The program's own inputs: Keyboard, OSC, Logical Device (03 S90b, 10 S6) [D-10-INTERNAL-NAME, 2026-10-09] | **Internal inputs**; Device Library heading **INTERNAL INPUTS**; Home cards keep their own words (HID, OSC, Logical) | Built-in inputs, BUILT-IN INPUTS |
| An OSC input's choices (09 S16) [D-09-OSC-INPUT, 2026-10-09; D-09-OSC-ENCODER] | modes **Button** / **Axis** / **Change** / **Encoder**; **Message only** / **Message + data** with **Data:**; **Source value:** (P1, P2 …); **Min:** / **Max:** (axis range); **Trigger on message** and its delay; row pencil menu **Change Address…** / **Edit Settings…** (window **OSC Input Settings**); Listening box button **Stop**; Import result **Added N, skipped M** | Cmd, Ok |
| An OSC encoder's settings (09 S108-S111) [D-09-OSC-ENCODER, 2026-10-09] | **Encoder** mode; **Format:** **Auto** / **1 = clockwise, 0 = counter-clockwise** / **+n and −n**; **Output:** **Axis** / **Pulses clockwise** / **Pulses counter-clockwise**; **Step size**; **Release after … ms** | rotary, knob, jog, delta |
| Watching OSC messages in and out (09 S90-S93) [D-09-OSC-MONITOR, 2026-10-09] | **OSC Monitor** (window; Tools › OSC Monitor, and the OSC page's **Monitor** button); **Pause**, **Clear**, **Show outgoing**; columns **In** / **Out**, **From** / **To**, **Input**; a message no input matched: **no input**; **Add as Input…** | OSC log, sniffer, traffic viewer, Unmapped |
| Where OSC sends (09 S94-S97) [D-09-OSC-OUTPUT, 2026-10-09] | a **target** (name, host, port) in the **Targets** list; the first is **Default**; **Reply to sender** (send back to whoever sent the last message); master switch **OSC output**; this PC's addresses with **Copy** | destination, dest, output host / output port, endpoint |
| The action that sends an OSC message (05 S109-S111) [D-09-OSC-OUTPUT, 2026-10-09] | **Send OSC**; editor **Target**, **Address**, **Values** (**Fixed** / **Input value**), **Add Value**, **Min:** / **Max:**; value types **Auto** / **Int** / **Float** / **Bool** / **Text** | OSC Out, Send Message |
| The program telling an OSC device its state (09 S102-S107) [D-09-OSC-FEEDBACK, 2026-10-09] | **Feedback** (section of OSC's Module Setup; switch **Send feedback to OSC devices**, **Send everything again at:**, **Add Row** / **Remove Row**), one row per thing sent, each with a **source**, a target, an address, **Min** / **Max** and a type; **Sync address** (default "/gremlin/sync"): a message there sends every row again | OSC output rows, echo rules, refresh address |
| Finding OSC devices on the network (09 S112-S114) [D-09-OSC-DISCOVERY, 2026-10-09] | **Announce this PC** / **Find OSC devices**; a found device's button **Add as Target** | zeroconf, Bonjour, mDNS (log only), Discover |
| OSC's settings window and its tabs (09 S116-S117, 03 S53d) [D-09-OSC-TABS, 2026-10-09] | OSC's **Module Setup**, tabs **Server** · **Output** · **Feedback** · **Discovery**; the OSC page's button **OSC Setup…** opens it; with no input selected the page says **Select an input to see its actions** | OSC Settings, OSC Options, Connection, Advanced |
| Helpers for Bitfocus Companion (09 S119-S125) [D-09-OSC-COMPANION, 2026-10-09] | **Add Companion** (Output tab: adds the target **Companion**, 127.0.0.1:12321); **Companion templates** on the Feedback tab: **Custom variable**, **Key text**, **Key colour**; **Copy for Companion** (an OSC input's row menu); **Export Companion Page…** reserved (not built, 09 S123); Companion's connection type is **Generic OSC** | Stream Deck preset, Companion mode, Companion profile, bank |
| What a Feedback row sends for off and on (09 S121) [D-09-OSC-COMPANION, 2026-10-09] | **off value** / **on value** (blank = Min/Max) | low/high, false/true value, colour A/B |

| The free-text box in a binding's header [D7] | **Note** (the Description action keeps its name) | Description (same word as the action) |
| Adding to a macro [D8] | **Add Step** (other "Add Action" buttons all add an action, so they stay) | Add Action in the Macro editor |
| The program's name [D12] | **Gremlin-Platforms** in titles and the tray; "the program" in sentences; HidHide's switch "Gremlin-Platforms controls HidHide" | Gremlin, Gremlin control |
| Internal words [D13] | **output** (not dest), **device without a module** (not stub card), **device id** (not DILL; Device Information's column is **Device ID**, not Device GUID), no raw group ids or slugs on screen | Device GUID, stub card |
| Capitals [D15] | **Title Case** for menus, buttons and window titles (Windows style, and most of the program already); sentence case for messages, tooltips and help | a mix |
| Home layout [N15] | **Single list / Side by side / Stacked** everywhere | also Split None / Vertical / Horizontal |
| Options section for Home cards [N19] | **Home** (not "Display"); timing options named for what they time (e.g. "Highlight time", "Last input time") instead of each "Duration" | |
| Spelling [N20] | US English: **color**, **behavior** (Qt, Windows and most of the program) | colour in some places |
| File pickers [N20] | titled by what they do, in Title Case like every window title (D15, GLOSSARY-4): "Open Profile", "Save Profile As", "Choose Photo", "Import Picture", "Export PNG", "Choose Logs Folder" ... | "Please choose a file", "Select a File", "Select a Folder" |
| An output a wire sends to but the output module doesn't claim | **(not claimed)** after its name (Configuration, chips, viewers, Map to vJoy, Calibration) | unclaimed, blocked |
| An action used by more than one input | **shared** action; its editor says **Shared with …** (OK changes it for every input) | linked, reference copy |
| Setting a device up again after its module file can't be read | **Start Fresh…** (card menu); the damaged file is kept as a copy | Reset module, Repair |
| A module file another window saved while the Button Map was being edited | title **Module File Changed**; buttons **Keep Mine** / **Take Theirs** / Cancel | Conflict |
| Taking back the last Device Pack import / mode delete | **Undo Import** (asks first) / **Undo Delete Mode** | Revert import, Restore mode |
| Release notes in the Update window (01 S133) | **What's new in <version>** (only when several versions); **Release notes unavailable.** when there are none or no connection; the window opens with the notes already there (D-01-UPDATE-NOTES-CACHE) | Getting the release notes…, Loading…, Fetching, No changelog |
| Filtering the Button Map's Layers panel (07 S102) | **Search layers…** (Ctrl+F); kind toggles **All · Chips · Groups · Hotspots · Leaders · Shapes · Lines · Pictures · Text · Tables · Photo**; "N of M" or **No layers match** | Find, Filter, Lookup |
| A Button Map export (PDF, PNG, JPG) still being written in the background (07 S101) | **Exporting…** (muted note in Print & Export; the Export buttons are disabled meanwhile); a failure is **Export Failed** with the reason (07 Q19) | Saving…, Busy, Please wait, Working… |
| Where Delete Device and Delete File keep their copies | the **Device Library** (its folder in Device Library Settings); deleted sticks show there as **Deleted**; pack imports keep the old file in the **imported** folder | deleted devices folder (removed 2026-10-08), trash, backup folder |

## Core terms

The ideas the program and its help are built on. Use these words with these
meanings; define a new idea here before it appears on screen.

| Term | Meaning |
|---|---|
| **Profile** | The file you load and save (File → Save): modes, actions, Profile Settings and scripts. |
| **Device** | A physical controller Windows reports (stick, throttle, pedals, keyboard), or a virtual one (vJoy, Xbox pad, the Logical Device). |
| **Card** | A device's tile on Home. Hiding a card (Hide Card) only takes it off Home. |
| **Module** / **module file** | A device's own file, one per device, kept apart from profiles: its claims, friendly names, picture, Button Map layout, Appearance and calibration. Set up in Module Setup. |
| **Input module** / **output module** | The module of a device that feeds the program (input) or that the program sends to (output: vJoy, Xbox). |
| **Claim** | Marking a control in Module Setup as one this setup uses. Only claimed inputs show in Configuration; only claimed vJoy outputs can be targets. (Xbox has no claims.) |
| **Control** | One button, axis, hat or key on a device. |
| **Input** | A control on an input device, as the profile sees it. |
| **Action** | What an input does: Map to vJoy, Map to Keyboard, Macro, Change Mode… An input with none shows **No actions**. |
| **Binding** | An input together with its actions, as edited on the Configuration page. |
| **Mode** | A named set of actions; one runs at a time (toolbar **Mode**). A mode uses its parent's actions for inputs it leaves empty. |
| **Run / Stop** | Running the profile sends to vJoy, Xbox and the Logical Device; stopped, you only edit. |
| **Logical Device** | A virtual device inside the program, fed by physical inputs, with actions of its own. |
| **Output View** | The read-only page of an output device: what its output module sends. |
| **Appearance** | How a page looks (Configuration, Output View, Logical Device); never what it does. |
| **History** | Every saved change (profile saves, module files, settings), kept in its own files so it can be seen later (Tools > History, or History in an editor). Not Undo: Undo steps back while editing; History keeps what was saved. |
| **Restore** | Putting back the version before or after a change from the History. A module file or settings restore is saved at once and is a new History entry at once; an input's actions go back into the open profile unsaved and show in the History at the next Save Profile; a whole-profile restore writes a copy next to the profile, which is not a History entry (08 Q1). |
| **Button Map** | A picture of a device with a **chip** per control, a **hotspot** on the photo for each and a **leader** line between them; unplaced chips wait in the **pool**. Layout only: it never changes actions. |
| **Device Library** | The window that keeps every device the program has known (connected, not connected, deleted; a device from someone else's pack is not connected) and its saved setups (10). Not the internal device library (dill). |
| **Saved setup** | A stored copy of a device's settings and bindings in the Device Library, with a name and a description: kept by you (**Save to Device Library…**) or automatically (an **autosave**). |
| **Autosave** | A saved setup the program keeps by itself before something replaces or removes a stick's settings (Delete Device, Delete File, Copy, Swap, Change vJoy Output, Device Pack); named "Autosave: <reason>"; the newest 10 per stick are kept. Always on: Edit › Undo puts the last change back from them. Renaming or describing one makes it yours. |
| **Remove from Library…** / **Clear Setup…** / **Delete Saved Setups…** | Device Library delete items (10 S15): Remove from Library… for a device that isn't connected (the device and its saved setups go); for a connected stick, Clear Setup… (same as Delete Device, autosave first) and Delete Saved Setups… (only its saved setups go). |
| **Restore to This Stick…** / **Keep This Autosave** | Device Library: put a saved setup back on its own stick (10 S48); make an autosave yours so the limit never removes it (10 S49). |
| **Device Library Guide** | The Device Library's own guide (Help menu, F1 in its window): the User Guide window showing only its topics (10 S42), like the Button Map Guide. |
| **Wire** | The link from a device's control, through its input module, to an output module (the wiring layer: hardware > input module > wiring > output module > driver). A wire carries the control's actions. Button Map lines are never wires: they are **leaders**. |
