# Glossary

One word for each idea in everything the user reads: menus, buttons, window
titles, messages, Options and help. Status: **approved 2026-10-02**; new text follows it.
Tracker refs in brackets.

| Idea | Use | Instead of (today) |
|---|---|---|
| Starting / stopping the profile [D1] | **Run** / **Stop**; status **Running** / **Stopped**; toolbar button "Run" (shows "Stop" while running); tray "Run Profile" / "Stop Profile" | Toggle, Toggle Active, Active, Not Running, Activate, Deactivate, "Activate Gremlin" |
| What an input does [D2, D11] | **action** (an input's actions); an input with none: **No actions** | mapping, wired, Unmapped, Not bound, Unbound, Empty ("wire" stays for Button Map lines) |
| The input device that feeds an output card | **Driven by: [device]**, or **Driven by: [nothing]** | Bound to: [Not bound] |
| The page where you edit a device's actions [D6] | **Configuration** (unchanged) | |
| The window for a device's module (claims, file, picture) [D6] | **Module Setup** ("Module Setup…" on the card and in Tools) | Configure input module / Configure output module |
| The editor for how a page looks (Home, Configuration, Logical) [D9] | **Appearance** ("Appearance…") | Show Editor, Display, Display Editor, View Settings, Display options |
| The current mode [D10] | one label, **Mode**, on the toolbar; the footer's duplicate goes | "Configuring mode" + "Executing mode" (always the same) |
| Hiding a card from Home [D3] | **Hide Card** / **Hidden Cards** | Hide device / Hidden devices (too close to HidHide) |
| Swapping which device a profile uses [D5] | card command **Swap Device…** (opens Swap Devices); "Assign hardware" stays only on the Logical page | Assign hardware… on the card |
| The free-text box in a binding's header [D7] | **Note** (the Description action keeps its name) | Description (same word as the action) |
| Adding to a macro [D8] | **Add Step** (other "Add Action" buttons all add an action, so they stay) | Add Action in the Macro editor |
| The program's name [D12] | **Gremlin-Platforms** in titles and the tray; "the program" in sentences; HidHide's switch "Gremlin-Platforms controls HidHide" | Gremlin, Gremlin control |
| Internal words [D13] | **output** (not dest), **device without a module** (not stub card), **device id** (not DILL), no raw group ids or slugs on screen | |
| Capitals [D15] | **Title Case** for menus, buttons and window titles (Windows style, and most of the program already); sentence case for messages, tooltips and help | a mix |
| Home layout [N15] | **Single list / Side by side / Stacked** everywhere | also Split None / Vertical / Horizontal |
| Options section for Home cards [N19] | **Home** (not "Display"); timing options named for what they time (e.g. "Highlight time", "Last input time") instead of each "Duration" | |
| Spelling [N20] | US English: **color**, **behavior** (Qt, Windows and most of the program) | colour in some places |
| File pickers [N20] | titled by what they do: "Open profile", "Save profile as", "Choose photo", "Import picture", "Export PNG" ... | "Please choose a file" and others |

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
| **Button Map** | A picture of a device with a **chip** per control, a **hotspot** on the photo for each and a **leader** line between them; unplaced chips wait in the **pool**. Layout only: it never changes actions. |
| **Wire** | Only the Button Map's lines showing where a pressed control goes while running. |
