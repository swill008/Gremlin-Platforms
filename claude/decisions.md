# Decisions

The record of every decision the user has made about how the program should
behave. It exists so nothing is argued twice and every session applies the
same answers. The spec pages in `claude/program-map/` hold the full
statements; this file is the index of what was decided, when and why.

**Which wins.** A decision here (and in a page's section 12) wins over a
section 8 statement it contradicts, and over today's code. Where the code
differs, that is a gap (`claude/gap-list.md`), fixed through the plan in
`claude/system-maps.md`, starting with a failing test.

**Adding a decision.** Only the user makes decisions; agents propose them
with a recommendation and wait (change control, D-SYS-CC). When the user
answers:

1. Add a row to the right area table: **ID** (`D-<page>-Q<n>` for a spec
   page question, `D-SYS-<id>` for a system-maps decision, `D-STD-<word>`
   for a standing rule), **Date** (the day the user answered), **Decision**
   (what the program does, in plain words), **Why / rules out** (one line;
   "(recommended)" when the reason is the recommendation's), **Spec refs**
   (page, question, statements S<n>, system-maps id).
2. Update the spec page (section 8 statement and section 12) in the same
   change, so the page and this file agree.
3. **Superseding:** never delete a row. Mark the old row "Superseded by
   <new ID> (<date>)" at the start of its Decision cell, and give the new row
   "Supersedes <old ID>" in its Why cell.

Page numbers: 01 app shell, 02 devices and input, 03 modules, 04 profile and
modes, 05 actions and editors, 06 Run and outputs, 07 Button Map, 08 History,
Device Pack and Auto Mapper, 09 OSC, sound and the rest.

Pages 06, 05 and 03 were reviewed question by question. Pages 01, 02, 04,
07, 08 and 09 were approved "all as recommended" (2026-10-06): each of their
section 9 questions is decided as its **Recommend** says, listed below.

## Standing rules (user, earlier sessions)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-STD-LAYER | 2026-10-01 | Every input and output follows hardware -> input module -> wiring (Configuration) -> output module -> driver. Nothing skips a layer. Only the output module talks to vJoy or ViGEm; hardware is reached only through the input module; the UI (Home cards, Button Map, viewers) never touches a driver or hardware directly. | Direct driver polling from a Home card flooded system.log; rules out any UI or wiring code reading or writing vJoy/ViGEm/hardware itself. | system-maps maps 1-3; 06 Q9, 05 Q16, 02 Q10, Q11 |
| D-STD-LAYER-KBM | 2026-10-06 | Accepted exception: keyboard and mouse output (Map to Keyboard, Map to Mouse, macro steps) go straight to Windows. Held keys and buttons are tracked in one place (Run lifecycle `run_scope`). | No driver exists to own them (recommended); rules out treating these as layer breaks. | 06 Q9, 05 Q16 |
| D-STD-XBOX | 2026-10-01 | The Xbox 360 output module is a pass-through to ViGEm: no claims, no per-control enable, no "not claimed" labels. Every pad control is always available to Map to Xbox. Values still go through the output layer. | Xbox claims in 1.0.2 made Map to Xbox silently do nothing (GremlinEx model); rules out claim UI or claim checks for Xbox. | 05 G17; 03 Q18 |
| D-STD-GLOSSARY | 2026-10-02 | All text the user reads (menus, buttons, window titles, messages, Options, help) uses the words in `claude/glossary.md`. Title Case for menus, buttons and window titles; sentence case for messages, tooltips and help. Exception: the Home layout names "Single list / Side by side" (and "Stacked") stay as written. New ideas get a glossary row first, not a new synonym. | One word per idea, found six names for one idea in places; rules out Toggle/Activate, mapping/Unmapped and invented synonyms. | glossary.md (approved 2026-10-02); 03 S86 |
| D-STD-THREADS | 2026-10-04 | New or changed code starts threads and timers only through `gremlin.threads`; every wait has a limit (timeout, re-check the stop flag, log once); timed loops read time through `gremlin.clock`; the main thread never waits on a worker that may not end. | Keeps the program hang-proof; rules out raw `threading.Thread/Timer`, unbounded `join()`/`wait()`, `time.time()` in runtime loops. | AGENTS.md "Threads, Waits and Timing"; 09 Q14; 05 Q19 |
| D-STD-OSC | 2026-10-02 | OSC is parked: leave OSC code alone. Page 09's OSC questions are decided as recommended but are built only when OSC is picked up. | User's choice; rules out OSC changes riding along with other work. | todo.md "OSC"; 09 Q1-Q10, Q18; gap-list section 9 |
| D-STD-HOLD | earlier session | N22 (inconsistent action editor controls) and AU-56 (200% UI scale on a small screen cuts off windows) are on hold. | User's choice; rules out fixing them until the user takes them off hold. | todo.md "On hold"; GL-168, GL-201 |
| D-STD-DEBUG | 2026-10-03 | The Live Log Reader's Live feed stays as is (System, Scripts, Events loggers). More debug detail comes from adding tracing to the specific element under investigation. | User declined widening Live; rules out merging [Config]/[Qt] lines or program-wide edit logging into Live. | 01 (Live Log Reader) |
| D-STD-RELEASE | earlier session | Builds and releases happen only when the user says "build and release". | User's choice; rules out tagging, building installers or publishing on an agent's own initiative. | none |

## System decisions (system-maps.md)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-SYS-CC | 2026-10-06 | Change control: every change to behaviour or the program goes through the plan and the spec in `claude/program-map/`. A change that would alter the spec (a statement or a decision) goes to the user first; the spec is updated with the answer before coding. Functions may change as features are added or removed, but only through this route. | Quick patches kept breaking neighbouring paths; rules out behaviour changes that are not in the spec. | system-maps "The plan", "How we work" |
| D-SYS-F1 | 2026-10-06 | Device Pack import onto a damaged module file is refused, pointing to Start Fresh. | Every other save refuses a damaged file (recommended); rules out replacing it with a backup. | system-maps F1; 08 Q2 |
| D-SYS-F2 | 2026-10-06 | Home card positions stay keyed by device name. | (recommended) Rules out re-keying card order by device id. | system-maps F2; 03 Q17 |
| D-SYS-F3 | 2026-10-06 | Start Fresh (and a Device Pack's clean-up after a failed write) leaves a History entry. | (recommended) Every file change is traceable; rules out silent rewrites. | system-maps F3; 03 Q17; 08 Q12; 03 S69 |
| D-SYS-F4 | 2026-10-06 | Twin sticks are always looked up by device id; a missing id is logged. | Name lookups can reach the wrong twin's file (recommended); rules out name-only lookups. | system-maps F4; 03 Q17; 03 S6, S77 |
| D-SYS-A1 | 2026-10-06 | OK on a shared action (Merge Axis, Dual Axis Deadzone, Reference) changes it for every input using it, with a "Shared with ..." note. | Today OK splits it (AU-118); rules out a silent split. | system-maps A1; 05 Q1; 05 S62 |
| D-SYS-A2 | 2026-10-06 | Undo and History Restore of a shared action restore it for every input using it. | Matches A1 (recommended); rules out restoring one input's half. | system-maps A2 |
| D-SYS-A3 | 2026-10-06 | A Device Pack (wire) import that fails partway undoes everything it did and says so. | Today it leaves removed inputs gone and new modes behind (AU-118); rules out partial imports. | system-maps A3; 08 Q20 |
| D-SYS-A4 | 2026-10-06 | Picking a shared action in the pane edits a copy until OK, including Add Action -> Merge Axis "Reuse". | The live shared object must not change before OK (recommended); rules out live library objects in a draft. | system-maps A4; 05 Q1 |
| D-SYS-R1 | 2026-10-06 | Logical Device values go back to neutral at Stop (axis 0, button up, hat centre). | So S85 holds (recommended); rules out values carrying into the next Run. | system-maps R1; 06 Q1; 06 S85 |
| D-SYS-R2 | 2026-10-06 | Release callbacks waiting at Stop are dropped. | Held-output release and the driver reset already let go (recommended); rules out firing them in the next Run. | system-maps R2; 06 Q2 |
| D-SYS-R3 | 2026-10-06 | The next Run starts in the start (toolbar) mode with temporary modes cleared. | (recommended) Rules out Previous going back to a mode from before Run. | system-maps R3; 06 Q3; 04 Q4 |
| D-SYS-R4 | 2026-10-06 | At Stop, keys a script pressed are released only if they were sent during that Run. | (recommended) Rules out releasing keys the program did not press in this Run. | system-maps R4; 06 Q4; 06 S31 |

## 01 App shell (all as recommended, 2026-10-06)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-01-Q1 | 2026-10-06 | The X on the main window quits the program (after the usual questions), the same as File -> Exit, even with a tool window open. | Tool windows have no parent, so the program could keep running (recommended). | 01 Q1 |
| D-01-Q2 | 2026-10-06 | Exit always ends the program, also with Minimize to tray on; check once on a real screen before changing anything. | Help already says so (recommended); rules out Exit just hiding the window. | 01 Q2 |
| D-01-Q3 | 2026-10-06 | The window's place and size are saved whenever it hides to the tray. | `onClosing` does not run then (recommended). | 01 Q3; test-plan W-21, S-21 |
| D-01-Q4 | 2026-10-06 | Changing the Logs or data folder takes effect at the next start; readers and writers stay on the start-up folder until then, and the rows say so. | Live Log Reader read the new folder while logs stayed in the old (recommended). | 01 Q4 |
| D-01-Q5 | 2026-10-06 | A chosen data folder missing at start: use the default and say so once, like Settings Reset. | Today it switches silently (recommended). | 01 Q5 |
| D-01-Q6 | 2026-10-06 | If configuration.json cannot be written, show one notice per session ("Settings could not be saved: <reason>"). | Today the failure only reaches system.log (recommended). | 01 Q6 |
| D-01-Q7 | 2026-10-06 | History Restore of a setting that acts at once (Diagnostic logs level, UI scale) applies it at once, exactly as the Options control does. | (recommended) Rules out writing the value without applying it. | 01 Q7 |
| D-01-Q8 | 2026-10-06 | The "could not start" box covers every start-up failure, including module loading and user folder creation. | The 1.0.18 failure escaped it (recommended). | 01 Q8; APP3 |
| D-01-Q9 | 2026-10-06 | Second copy, Yes: if the other copy still holds the lock, say "The other copy could not be closed" and offer No / Cancel again. | Today it starts without the lock silently (recommended). | 01 Q9 |
| D-01-Q10 | 2026-10-06 | Tempo, Double Tap and Smart Toggle main-thread timers are listed like every other timer, so quit and Stop can cancel them; built in the Run lifecycle redesign. | (recommended) Closes with AU-116. | 01 Q10; AU-116 |
| D-01-Q11 | 2026-10-06 | `shutdown_cleanup` runs once per quit and stops only what exists. | It ran twice and created listeners just to stop them (recommended). | 01 Q11; 06 G16 |
| D-01-Q12 | 2026-10-06 | Keep the one general "settings changed" signal for now; split it by area only if it shows up as slow. | (recommended) Rules out a split without a measured need. | 01 Q12 |
| D-01-Q13 | 2026-10-06 | The User Guide's Options topic is updated to match the Options layout (`_LAYOUT`). | Help was behind the window (recommended). | 01 Q13 |
| D-01-Q14 | 2026-10-06 | Option text and file pickers use glossary words ("device without a module"; pickers titled by what they do). | Follows D-STD-GLOSSARY (recommended). | 01 Q14 |
| D-01-Q15 | 2026-10-06 | Diagnostic logs default to Warning. | (recommended) Kept as is. | 01 Q15 |
| D-01-Q16 | 2026-10-06 | No in the second-copy box stays (two copies may run). | The user's earlier wording; the box already warns about vJoy (recommended). | 01 Q16 |

## 02 Devices and input (all as recommended, 2026-10-06)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-02-Q1 | 2026-10-06 | The "vJoy as input" tick gets its own signal that refreshes device lists and input claims but never stops or restarts a Run. | (recommended) Rules out a tick restarting or stopping a Run. | 02 Q1; 04 Q12 |
| D-02-Q2 | 2026-10-06 | Device change behavior shows "Stop" instead of "Disable" on screen; the stored value is kept. | Glossary says Run / Stop (recommended). | 02 Q2 |
| D-02-Q3 | 2026-10-06 | A stored twin name is used only while the driver's name still matches its base name; entries for names no longer used are dropped. | (recommended) Rules out stale twin names winning forever. | 02 Q3 |
| D-02-Q4 | 2026-10-06 | Keys the program sends itself are ignored while a Run is active (bindings and recording); whether Listen sees them is decided once, when built. | One binding's key could fire another (recommended). | 02 Q4 |
| D-02-Q5 | 2026-10-06 | Mouse buttons stay macro/Listen only (no running profile gets mouse events); Help says so; the dead "injected" mouse filter is removed. | (recommended) | 02 Q5 |
| D-02-Q6 | 2026-10-06 | Device Information also lists left-out vJoy devices and Gremlin's own Xbox pads, marked "left out (see message)" / "Gremlin's Xbox pad". | The window is used to tell devices apart (recommended). | 02 Q6 |
| D-02-Q7 | 2026-10-06 | At Run, an axis not yet seen is read from the driver (through the input side) and then cached, so a throttle at 80% is not sent as centre. Hands-on check first that dill.dll does not already send starting values. | (recommended) Rules out sending a cached 0 for unseen axes. | 02 Q7 |
| D-02-Q8 | 2026-10-06 | Each event keeps the mode current when the hardware event arrives. | Matches what the user pressed (recommended); written down as intended. | 02 Q8 |
| D-02-Q9 | 2026-10-06 | Listen is cancelled only by holding Esc 1 s, in every case; Help names it. | (recommended) Rules out the short-tap cancel. | 02 Q9 |
| D-02-Q10 | 2026-10-06 | HidHide is a driver of its own: its driver client and enumeration move to a non-UI module; `HidHideModel` stays as the screen. Low priority. | (recommended) Applies D-STD-LAYER. | 02 Q10 |
| D-02-Q11 | 2026-10-06 | The Xbox driver package may read `dill.DILL` only through `gremlin/modules/hardware.py` (one door to the device driver). | So the guard can check it (recommended). | 02 Q11 |
| D-02-Q12 | 2026-10-06 | Device Information shows "Device ID", not "Device GUID". | Glossary (recommended). | 02 Q12 |
| D-02-Q13 | 2026-10-06 | Applying HidHide lists keeps overwriting HidHide's whole lists; the screen says so under "Gremlin-Platforms controls HidHide". | Gremlin is in control once turned on (recommended). | 02 Q13 |
| D-02-Q14 | 2026-10-06 | A HidHide device tick is saved only after the driver accepts it. | Matches HidHide Enabled (recommended). | 02 Q14 |
| D-02-Q15 | 2026-10-06 | Allow-list mode adding `python.exe` for source runs is accepted; mentioned in developer notes only. | (recommended) | 02 Q15 |
| D-02-Q16 | 2026-10-06 | Only the HidHide window's "Automatically Start" switch stays; Options points to it. | One setting had two switches (recommended). | 02 Q16; test-plan S-38 |
| D-02-Q17 | 2026-10-06 | The vJoy message ends "Then restart the program." | Glossary (recommended). | 02 Q17 |
| D-02-Q18 | 2026-10-06 | With auto-load on and Keep running off, focusing the program's own window counts as "no change" and does not stop the Run. | (recommended) | 02 Q18 |
| D-02-Q19 | 2026-10-06 | The process monitor runs only while auto-load is on. | (recommended) Rules out polling every second for nothing. | 02 Q19 |

## 03 Modules (reviewed, 2026-10-06)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-03-Q1 | 2026-10-06 | Module Setup's running note says "Saved changes work at once."; the live behaviour is kept. | The old note was wrong. | 03 Q1; 03 S36 |
| D-03-Q2 | 2026-10-06 | Module Setup Import Image works like the Button Map: the old picture is put back on Cancel. | Today it saves at once and Cancel cannot undo it. | 03 Q2; 07 Q5 |
| D-03-Q3 | 2026-10-06 | Save Module copies the photo to the library only when it changed; one write, one History entry. | Library grew by one picture per Save. | 03 Q3 |
| D-03-Q4 | 2026-10-06 | Delete Device removes the device's actions in memory and leaves the profile unsaved. | Rules out writing the whole profile and skipping the unfinished-actions check. | 03 Q4 |
| D-03-Q5 | 2026-10-06 | Delete Device always keeps a copy of the module file in deleted devices. | Matches Delete File. | 03 Q5 |
| D-03-Q6 | 2026-10-06 | Delete Device is refused while running ("Stop first"); Module Setup Save stays allowed. | It changes the running profile. | 03 Q6 |
| D-03-Q7 | 2026-10-06 | The Logical Device card has no Module Setup, Calibration, Auto Mapper, Device Information or Swap Device. | They don't work there. | 03 Q7 |
| D-03-Q8 | 2026-10-06 | Cards always show claimed counts. | Reload and refresh disagreed. | 03 Q8 |
| D-03-Q9 | 2026-10-06 | Calibration lists every axis; unclaimed ones are marked "not claimed". | Calibration is about the hardware. | 03 Q9 |
| D-03-Q10 | 2026-10-06 | Stacks keep cards that aren't showing, as card order does. | Rules out hidden or unplugged cards dropping out of a stack. | 03 Q10 |
| D-03-Q11 | 2026-10-06 | "Input Module Setup" / "Output Module Setup" are kept and added to the glossary. | The two Tools entries pick the kind. | 03 Q11 |
| D-03-Q12 | 2026-10-06 | Help's Home topic lists Keyboard, OSC and Logical Device cards. | Help was incomplete. | 03 Q12 |
| D-03-Q13 | 2026-10-06 | Import goes into the file the device uses (map 1). | Rules out writing a new own-name file for a renamed stick. | 03 Q13; 08 Q14 |
| D-03-Q14 | 2026-10-06 | Delete File keeps the pictures and says so in its confirm text. | They come back if the copy is imported. | 03 Q14 |
| D-03-Q15 | 2026-10-06 | Auto Mapper "Also claim": an output file that can't be written is skipped and listed. | Rules out making actions to outputs that stay unclaimed. | 03 Q15; 08 Q9 |
| D-03-Q16 | 2026-10-06 | Keyboard Module Setup ignores key presses while a text box has focus (check off-screen first). | Typing a name could tick keys. | 03 Q16 |
| D-03-Q17 | 2026-10-06 | F2, F3, F4 as recommended (see D-SYS-F2..F4). | Decided in system-maps. | 03 Q17 |
| D-03-Q18 | 2026-10-06 | Delete Device is left out of output (vJoy, Xbox) cards. | Output module files are not deleted anyway. | 03 Q18; 03 S93 |

## 04 Profile and modes (all as recommended, 2026-10-06)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-04-Q1 | 2026-10-06 | Load / New lands in the new profile's Startup Mode. Confirm with the HELP-BUG-HANDS-ON check; if it fails, set the open profile first, then work out the mode. | Help says so (recommended). | 04 Q1 |
| D-04-Q2 | 2026-10-06 | Last Active means the mode last used while running; toolbar picks while stopped do not count. | Matches help (recommended). | 04 Q2 |
| D-04-Q3 | 2026-10-06 | Auto-load over unsaved edits stops the running profile, as the missing-file case does, unless Keep running is on. | (recommended) Rules out the old profile running for the new program. | 04 Q3; 04 S35, S36 |
| D-04-Q4 | 2026-10-06 | The next Run uses the start mode with temporary modes cleared (D-SYS-R3). | (recommended) | 04 Q4; system-maps R3 |
| D-04-Q5 | 2026-10-06 | Picking a toolbar Mode while running switches the running profile (kept); Help says so. | It is useful (recommended). | 04 Q5; 04 S54 |
| D-04-Q6 | 2026-10-06 | Mode edits become undoable; at least Delete Mode, since it removes bindings. | (recommended) Rules out losing bindings with no way back. | 04 Q6 |
| D-04-Q7 | 2026-10-06 | A profile with an unknown action type opens; the unknown action is kept as-is and a warning shows. | Matches scripts and Play Sound (recommended). | 04 Q7; ACT11, ACT12; 05 G20 |
| D-04-Q8 | 2026-10-06 | Inputs saved in a mode not in the mode list are moved into a "Recovered" mode on load, or listed in a warning. | (recommended) Rules out inputs that never show and never run. | 04 Q8 |
| D-04-Q9 | 2026-10-06 | On load, add "Default" when the mode list is empty and warn about duplicate mode names. | (recommended) | 04 Q9 |
| D-04-Q10 | 2026-10-06 | An unknown Startup Mode in the file is treated as Use Heuristic on load. | The Startup Mode box failed (recommended). | 04 Q10 |
| D-04-Q11 | 2026-10-06 | vJoy Initial Values are always set at Run (D-06-Q7). | Help says "set when the profile starts" (recommended). | 04 Q11; 06 Q7 |
| D-04-Q12 | 2026-10-06 | Switching vJoy Behavior while running says "takes effect at the next Run" and does not touch the Run. | (recommended) Rules out it stopping or restarting a Run. | 04 Q12; 02 Q1 |
| D-04-Q13 | 2026-10-06 | A script's top-level code must not freeze the program at load: read its variables without running the whole script, or run it under a time limit (needs a design). | (recommended) | 04 Q13 |
| D-04-Q14 | 2026-10-06 | Profiles get a recovery copy: while unsaved changes exist, a copy is kept about every minute; on the next open of that profile (or at start after a crash) the program offers Restore / Discard / Not now, as the Button Map's Autosave does. Save, Discard and a clean close remove the copy. | User changed the recommendation ("ask") to yes; a crash lost every unsaved edit. | 04 Q14; 04 S94 |
| D-04-Q15 | 2026-10-06 | A missing Recent file offers Forget It, as start-up does. | (recommended) | 04 Q15 |
| D-04-Q16 | 2026-10-06 | `--profile` with a missing file and no last profile says "A new profile is open". | (recommended) Rules out claiming a last profile that doesn't exist. | 04 Q16 |
| D-04-Q17 | 2026-10-06 | The last-mode store is keyed by the resolved, case-folded path, as Recent is. | (recommended) | 04 Q17 |
| D-04-Q18 | 2026-10-06 | Device names are filled only at save, not in the unsaved check. | Plugging in a stick made the profile look unsaved (recommended). | 04 Q18; R14 |
| D-04-Q19 | 2026-10-06 | Measure the 1.5 s unsaved check on large profiles; switch to mark-dirty-on-edit if it is slow. | (recommended) | 04 Q19 |
| D-04-Q20 | 2026-10-06 | Swap Devices refuses "From" and "To" being the same id. | (recommended) | 04 Q20 |
| D-04-Q21 | 2026-10-06 | The look-alike mode name rule moves into `ModeHierarchy.add_mode`, so it covers Device Pack and scripts. | (recommended) Rules out "test mode" next to "Test Mode". | 04 Q21; R5 |

## 05 Actions and editors (reviewed, 2026-10-06)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-05-Q1 | 2026-10-06 | OK on a shared action changes it for every input using it; a shared action is edited as a copy until OK, including Add Action -> Merge Axis "Reuse" (D-SYS-A1, A4). | Rules out OK splitting a shared action. | 05 Q1; 05 S62 |
| D-05-Q2 | 2026-10-06 | Every built-in action plugin is always loaded; `can_create()` only decides what Add Action offers. Hands-on check on a PC without vJoy first. | Profiles with Map to vJoy failed to open without vJoy. | 05 Q2 |
| D-05-Q3 | 2026-10-06 | Run skips unfinished actions and logs one line each ("not finished: <action> on <input>"). | Matches what Save leaves out. | 05 Q3 |
| D-05-Q4 | 2026-10-06 | Check by hand that a new key can get its first action; if not, show one empty binding. | The "New Action Sequence" footer was removed; a new key may have no way to get an action. | 05 Q4 |
| D-05-Q5 | 2026-10-06 | The Keyboard page uses the same pane as the Configuration page (draft, OK, Undo); until then, ask before removing an action. | Supersedes S78. | 05 Q5; 05 S78 |
| D-05-Q6 | 2026-10-06 | Catalog text: "No actions", "1 action" / "N actions", Title Case type names from the plugins; the glossary test covers `binding_catalog.py`. | Follows D-STD-GLOSSARY. | 05 Q6 |
| D-05-Q7 | 2026-10-06 | Text to Speech lists Keyboard as an input type; test-plan S-34 is closed. | Writes the intent down; matches 09 Q11. | 05 Q7; 09 Q11 |
| D-05-Q8 | 2026-10-06 | History Restore, Auto Mapper and Device Pack import close the pane first, asking if it has changes. | Rules out OK writing over their changes. | 05 Q8 |
| D-05-Q9 | 2026-10-06 | Axis Delta uses the value shaped by earlier actions and treats 0 as a value. | Today it reads the raw value and skips exactly 0 (recommended). | 05 Q9 |
| D-05-Q10 | 2026-10-06 | Split Axis's change stays inside its two lists; actions after it see the input's value. | Supersedes S80's Split Axis part. | 05 Q10; 05 S80 |
| D-05-Q11 | 2026-10-06 | While running, the pane opens read-only with "Stop to edit" and no OK. | Rules out a live OK on greyed contents. | 05 Q11; test-plan S-13 |
| D-05-Q12 | 2026-10-06 | Chain's removed sequence releases its actions through the one removal rule. | Rules out actions left in the library. | 05 Q12 |
| D-05-Q13 | 2026-10-06 | The Load Profile action hands its request to the Run lifecycle owner, done after the event. | Rules out runtime calling the UI and Stop/Run from inside an event. | 05 Q13 |
| D-05-Q14 | 2026-10-06 | New Dual Axis Deadzones are numbered like Merge Axis. | All new Deadzones had the same name (recommended). | 05 Q14 |
| D-05-Q15 | 2026-10-06 | The input name becomes a field of `InputItem`; the import-time patches in `action_label.py` go. | Rules out rewriting InputItem and list models at import (recommended). | 05 Q15 |
| D-05-Q16 | 2026-10-06 | Keyboard/mouse output is an accepted exception (D-STD-LAYER-KBM); `XboxTarget` moves to the output module. | Plugins then import Xbox types from the output module. | 05 Q16; 06 Q9 |
| D-05-Q17 | 2026-10-06 | A macro Joystick step goes through the input module's claims like a real event. | Matches 06 Q14. | 05 Q17; 06 Q14 |
| D-05-Q18 | 2026-10-06 | The unused code listed in Q18 is removed in one clean-up commit. | No caller found; `addSequence` writes with no Undo step (recommended). | 05 Q18; C9 |
| D-05-Q19 | 2026-10-06 | Chain moves to `gremlin.clock`; the UI rate limit stays on `time.time()`. | Runtime timing must be steppable (D-STD-THREADS). | 05 Q19 |
| D-05-Q20 | 2026-10-06 | Catalog Delete asks (as the code does); test-plan IC-06 is marked superseded. | Code and WORKFLOW-3 (C8) already ask (recommended). | 05 Q20 |

## 06 Run and outputs (reviewed, 2026-10-06)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-06-Q1 | 2026-10-06 | Logical Device values go back to neutral at Stop (D-SYS-R1). | So S85 holds. | 06 Q1; 06 S85 |
| D-06-Q2 | 2026-10-06 | Release callbacks waiting at Stop are dropped (D-SYS-R2). | Held-output release and the driver reset already let go. | 06 Q2 |
| D-06-Q3 | 2026-10-06 | The next Run uses the toolbar mode, temporary modes cleared (D-SYS-R3). | Rules out Previous going back to a mode from before Run. | 06 Q3 |
| D-06-Q4 | 2026-10-06 | Script keys are released at Stop only if sent during a Run (D-SYS-R4). | Rules out releasing keys the program did not press in this Run. | 06 Q4; 06 S31 |
| D-06-Q5 | 2026-10-06 | A failed start runs Stop itself, shows one error, and the status reads Stopped. | Rules out double connections on a second Run and "Running" after a failure. | 06 Q5; RB17, RB18 |
| D-06-Q6 | 2026-10-06 | Run asks "Save or discard the open action first?" when an action editor is open, as leaving the page does. | Rules out an editor staying open through Run. | 06 Q6; RB14 |
| D-06-Q7 | 2026-10-06 | vJoy Initial Values are always written at Run through the output module; the refresh of physical axes may then overwrite them. | Rules out depending on a DirectInput readback of 0. | 06 Q7; 06 S8; RB1 |
| D-06-Q8 | 2026-10-06 | Play Sound and Text to Speech are ignored when no Run is on. | Rules out sound or speech after Stop. | 06 Q8; RB21 |
| D-06-Q9 | 2026-10-06 | Keyboard and mouse output going straight to Windows is an accepted, written exception to the layer rule; held keys and buttons tracked in one place (D-STD-LAYER-KBM). | No driver exists to own them. | 06 Q9 |
| D-06-Q10 | 2026-10-06 | The auto-pause on a vJoy error inside an action is removed. | The output layer's "logged once" and busy message are the signal. | 06 Q10 |
| D-06-Q11 | 2026-10-06 | Paused shows "Running (Paused)"; Stop then Run starts un-paused (kept). | Kept as is (recommended). | 06 Q11 |
| D-06-Q12 | 2026-10-06 | Output module changes saved while running apply at once (force `output.refresh()` on save), like input module changes. | Changes S53. | 06 Q12; 06 S53; 03 S36 |
| D-06-Q13 | 2026-10-06 | An axis already in range at Run gives no press until it leaves and re-enters (kept). | No surprise press at Run. | 06 Q13; S39 |
| D-06-Q14 | 2026-10-06 | A macro's Joystick step passes claimed controls only (kept); the Macro help says so. | The step pretends to be the physical stick, so the gate applies. | 06 Q14; 05 Q17 |
| D-06-Q15 | 2026-10-06 | No hidden Button 1 on an empty Logical Device; show "Add a Logical Device control first". | Rules out hidden creates and a failing condition on an empty device. | 06 Q15; RB12 |
| D-06-Q16 | 2026-10-06 | Reads never open a vJoy device; only writes do. | Same as the viewers. | 06 Q16; RB19 |
| D-06-Q17 | 2026-10-06 | Map to vJoy relative axis ends with its Run (on the Run number). | Rules out the loop carrying into the next Run. | 06 Q17; RB5 |
| D-06-Q18 | 2026-10-06 | The unused second Logical Device writer (`LogicalDeviceManagementModel.createInput/changeName/deleteInput`) is removed after a grep confirms no user. | It writes with no Undo. | 06 Q18 |
| D-06-Q19 | 2026-10-06 | No Xbox pad outside a Run, ever. | Closes with AU-116 (late timer plugged it back). | 06 Q19; AU-116 |

## 07 Button Map (all as recommended, 2026-10-06)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-07-Q1 | 2026-10-06 | View, zoom and grid stay instant; the print area, print setup and guides become part of the edit (written by Save, taken back by Cancel, undoable). Help says so. | They are part of the map (recommended). | 07 Q1 |
| D-07-Q2 | 2026-10-06 | A new photo waits beside the old one until Save; only Save writes `image`; History sees one entry per Save. | (recommended) Rules out History entries for unsaved photos. | 07 Q2 |
| D-07-Q3 | 2026-10-06 | Choose Photo and Clear Photo are undo steps (print area and guides too, per D-07-Q1). | (recommended) | 07 Q3 |
| D-07-Q4 | 2026-10-06 | Clear Photo leaves no photo; help says "Clear Photo removes the photo". | (recommended) | 07 Q4 |
| D-07-Q5 | 2026-10-06 | One owner for the device photo; Module Setup's photo waits for its Save and can be cancelled, as in the Button Map. | (recommended) Matches D-03-Q2. | 07 Q5; 03 Q2 |
| D-07-Q6 | 2026-10-06 | If the module file changes elsewhere: outside Edit, reload; in Edit, warn on Save ("the module file changed since you started editing") with Keep mine / Take theirs. | (recommended) Rules out silently writing the old map back. | 07 Q6 |
| D-07-Q7 | 2026-10-06 | Delete Device while its map is being edited closes the window without saving, with a short note. | (recommended) Rules out a new module file for a deleted device. | 07 Q7 |
| D-07-Q8 | 2026-10-06 | Chips for controls the device lacks are kept when copied; after the copy, say how many ("3 chips are for controls this device does not have"). | (recommended) | 07 Q8 |
| D-07-Q9 | 2026-10-06 | Labels Mode is kept per device for the session only. | (recommended) Confirms today. | 07 Q9 |
| D-07-Q10 | 2026-10-06 | The hard-coded EVO R name check goes; a typed chip name is always the user's. | (recommended) | 07 Q10 |
| D-07-Q11 | 2026-10-06 | Save and Cancel remove device-folder pictures no map uses; Delete Device removes its recovery copy and photo safety copy; the library gets "Remove unused" in Options -> Library. | (recommended) | 07 Q11 |
| D-07-Q12 | 2026-10-06 | If no built-in maps or photos ship, remove the stock-photo and legacy-copy code and fix the BM41 note; if some do, add them to the repo and installer. | (recommended) | 07 Q12; BM41 |
| D-07-Q13 | 2026-10-06 | Choose Photo and Import Picture open in the user's Pictures folder, or the last folder used. | Rules out creating folders in Program Files (recommended). | 07 Q13 |
| D-07-Q14 | 2026-10-06 | The page size is one constant, read on load; BM41's conversion uses it. | (recommended) | 07 Q14; BM41 |
| D-07-Q15 | 2026-10-06 | A recovery copy equal to the saved map is deleted without asking (kept). | (recommended) | 07 Q15; 07 S37 |
| D-07-Q16 | 2026-10-06 | Recovery copies at most every 10 s (kept); the option's minimum becomes 10. | So the screen agrees (recommended). | 07 Q16; 07 S33 |
| D-07-Q17 | 2026-10-06 | The glossary row for Button Map Options is updated (now a pane on the tool row). | (recommended) | 07 Q17; BM46 |
| D-07-Q18 | 2026-10-06 | Print & Export works outside Edit; paper and scale are written at once (kept). | A print setting, like the view (recommended). | 07 Q18 |
| D-07-Q19 | 2026-10-06 | A failed export says which file and why. | As Template export does (recommended). | 07 Q19 |

## 08 History, Device Pack and Auto Mapper (all as recommended, 2026-10-06)

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-08-Q1 | 2026-10-06 | Glossary and help text are changed to say when a Restore becomes a History entry (module files and settings at once; input restore at the next Save Profile; whole-profile restore not recorded). | (recommended) Rules out recording unsaved edits. | 08 Q1 |
| D-08-Q2 | 2026-10-06 | Device Pack import onto a damaged module file is refused, pointing to Start Fresh (D-SYS-F1). | (recommended) | 08 Q2; system-maps F1 |
| D-08-Q3 | 2026-10-06 | Device Pack import keeps adding (checked controls added, names one by one, chips for the same controls); help and warning say "adds the pack's checked controls". | Safer, nothing lost (recommended). | 08 Q3 |
| D-08-Q4 | 2026-10-06 | Device Pack and History windows show the running note, as the Auto Mapper does. | (recommended) | 08 Q4 |
| D-08-Q5 | 2026-10-06 | Undo Import asks before putting back a file that changed since the import. | (recommended) Rules out silently losing later saves. | 08 Q5 |
| D-08-Q6 | 2026-10-06 | Help adds "or open another pack" to when Undo Import ends. | (recommended) | 08 Q6 |
| D-08-Q7 | 2026-10-06 | The Auto Mapper counts every input in the profile and nested actions when deciding which vJoy outputs are used. | (recommended) Rules out two inputs sent to one output. | 08 Q7 |
| D-08-Q8 | 2026-10-06 | The Auto Mapper result reads "Made 36 actions; 0 inputs kept their actions." | Glossary words (recommended). | 08 Q8 |
| D-08-Q9 | 2026-10-06 | Auto Mapper "Also claim" skips outputs it could not claim and lists them as "not claimed". | (recommended) Same as D-03-Q15. | 08 Q9; 03 Q15 |
| D-08-Q10 | 2026-10-06 | Moving the history folder moves the history files, or Options says old entries stay in the old folder. | (recommended) | 08 Q10 |
| D-08-Q11 | 2026-10-06 | History size and age limits are checked at start only (accepted); the Options description says "checked at start". | Cheap; files are trimmed next start (recommended). | 08 Q11 |
| D-08-Q12 | 2026-10-06 | Start Fresh and the pack's clean-up after a failed write are recorded in History (D-SYS-F3). | (recommended) | 08 Q12; system-maps F3 |
| D-08-Q13 | 2026-10-06 | Before and After of a module file show readable lines, reusing the Device Pack rows. | Rules out raw JSON (recommended). | 08 Q13 |
| D-08-Q14 | 2026-10-06 | Restore of a module file goes through the module-file owner (map 1, `store.replace`). | After a rename or rebind the device may not use the restored file (recommended). | 08 Q14; 03 Q13 |
| D-08-Q15 | 2026-10-06 | Button Map > File > History filters by the device's own file name and all areas, as Module Setup does. | Twins were mixed and claim changes hidden (recommended). | 08 Q15 |
| D-08-Q16 | 2026-10-06 | The Configuration row's History filters by the open profile too; Show All widens it. | (recommended) | 08 Q16 |
| D-08-Q17 | 2026-10-06 | Deleted-device packs, Delete File copies and imported backups are kept forever (the user deletes them); help says where they are and how to bring a device back. | (recommended) | 08 Q17 |
| D-08-Q18 | 2026-10-06 | Output modules in a pack are imported within the vJoy device's real limits, listing what is left out. | (recommended) Rules out checks past the last button. | 08 Q18 |
| D-08-Q19 | 2026-10-06 | Export of a device with a damaged module file says it is damaged and points to Start Fresh. | (recommended) | 08 Q19 |
| D-08-Q20 | 2026-10-06 | A wire import that fails partway undoes everything it did and says so (D-SYS-A3). | (recommended) | 08 Q20; AU-118 |
| D-08-Q21 | 2026-10-06 | Undo Import keeps a created Logical Device input that now has actions, and says so. | (recommended) Rules out losing actions added after import. | 08 Q21 |

## 09 OSC, sound and the rest (all as recommended, 2026-10-06)

OSC questions (Q1-Q10, Q18) are decided but parked (D-STD-OSC): build them
only when OSC is picked up.

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-09-Q1 | 2026-10-06 | OSC (parked): input port 8000, output 9000, one constant each, used by the listener, Options and the Listening box. | (recommended) | 09 Q1; B15 |
| D-09-Q2 | 2026-10-06 | OSC (parked): hide the Add dialog controls that do nothing and fix the import text; build them later only if needed. | Small and honest (recommended). | 09 Q2; B16, B17 |
| D-09-Q3 | 2026-10-06 | OSC (parked): hide the output address until something sends OSC. | (recommended) | 09 Q3 |
| D-09-Q4 | 2026-10-06 | OSC (parked): OSC stays outside the module system; its Module Setup shows only friendly names, no claims. | (recommended) | 09 Q4; 03 gap 22 |
| D-09-Q5 | 2026-10-06 | OSC (parked): the listener opens only when the profile has OSC inputs, bound to 127.0.0.1 by default. | No firewall prompts for non-users (recommended). | 09 Q5; APP5 |
| D-09-Q6 | 2026-10-06 | OSC (parked): Delete on an OSC row gets Undo, as on the Logical Device page. | (recommended) | 09 Q6 |
| D-09-Q7 | 2026-10-06 | OSC (parked): Sort toggles A-Z / by type and number and is remembered. | (recommended) | 09 Q7 |
| D-09-Q8 | 2026-10-06 | OSC (parked): the friendly name on OSC rows is kept. | It shows on chips and in History (recommended). | 09 Q8 |
| D-09-Q9 | 2026-10-06 | OSC (parked): the python-osc error says "OSC is not available in this build"; the detail goes to the log. | Rules out developer text on screen (recommended). | 09 Q9 |
| D-09-Q10 | 2026-10-06 | OSC (parked): packets are dropped unless running or listening. | (recommended) | 09 Q10; APP13 |
| D-09-Q11 | 2026-10-06 | Text to Speech is allowed on keyboard keys, like Play Sound. | (recommended) Matches D-05-Q7. | 09 Q11; test-plan S-34 |
| D-09-Q12 | 2026-10-06 | If the saved voice is uninstalled, Options shows "(default)". | (recommended) | 09 Q12 |
| D-09-Q13 | 2026-10-06 | If Windows speech is not available, one warning goes to the log and the action's feedback. | (recommended) Rules out silent failure. | 09 Q13 |
| D-09-Q14 | 2026-10-06 | The `gremlin.clock` rule covers every loop that sleeps in a thread (audio, OSC debounce, auto-release); Qt timers on the main thread stay as they are. | (recommended) Scope of D-STD-THREADS. | 09 Q14 |
| D-09-Q15 | 2026-10-06 | The Options check box reads "Ignore Windows display scaling". | Matches its title and help (recommended). | 09 Q15 |
| D-09-Q16 | 2026-10-06 | Check action summary images off-screen at 200% and light mode first; fix with Style values only if visibly off. | (recommended) | 09 Q16 |
| D-09-Q17 | 2026-10-06 | Test-plan rows W-04..W-09 are retired in favour of TRAY-ONE and the glossary words. | (recommended) | 09 Q17 |
| D-09-Q18 | 2026-10-06 | OSC (parked): Options text "while the profile runs" and "the port your OSC sender sends to". | Glossary words (recommended). | 09 Q18 |
| D-09-Q19 | 2026-10-06 | `gremlin/fsm.py` and its test are removed, after the leftover list is agreed. | Used only by its own test (recommended). | 09 Q19 |
| D-09-Q20 | 2026-10-06 | The leftover table in page 09 section 2 is accepted; pages 01, 05, 07, 08 confirm their files. | (recommended) | 09 Q20 |

## Later decisions

| ID | Date | Decision | Why / rules out | Spec refs |
|---|---|---|---|---|
| D-06-S39-NORELEASE | 2026-10-06 | An axis-range button sends no release without a press (axis already in range at Run, then leaves: nothing sent) | A release with no press is a stray key-up for key or macro targets | 06 S39, Q13 |
| D-03-STALEID-ONE | 2026-10-06 | One stale-id rule everywhere: the id of a stick that isn't connected is kept, so the Button Map opens that stick's own module file (as Delete File and Device Pack do). | Rules out name-only lookups mixing twins (user, batch 1) | 03 S2, S9; decision F4 |
| D-05-DRAFT-OUTDATED | 2026-10-06 | OK in an action editor refuses, with a note, when the input was changed elsewhere (History Restore, Auto Mapper, Device Pack) while the editor was open. Those tools also close the editor first, asking if it has changes (batch 2). | Rules out silently overwriting a newer change (user, batch 1) | 05 Q8 |
| D-06-STOP-MODE | 2026-10-06 | After Stop the toolbar shows the last non-temporary mode; temporary modes end with Stop; the next Run starts in the toolbar mode. | (recommended; user, batch 1) | 06 R3; 04 S52, S53 |
| D-05-S69-Q7 | 2026-10-06 | 05 S69 reworded to follow decision 04 Q7: a profile with an unknown action type opens, the action is kept unchanged and a warning names the type. | The decision wins over the older statement | 05 S69; 04 Q7 |
| D-09-TTS-ENGINE | 2026-10-06 | The speech engine lives for the whole program (Options lists its voices); only its queue belongs to a Run. | GL-066 decided, no code change | 09; 06 G17 |
| D-04-Q13-TIMELIMIT | 2026-10-07 | A script's top-level code (run when a profile with the script loads, or when the script is added) runs on a worker thread with a time limit (about 5 s). If it doesn't finish, the script is marked as failed with a message and the program carries on. | Rules out the program freezing on a script that loops or waits (GL-040; user, batch 2 end) | 04 Q13, S87 |
| D-03-Q8-NOFILE | 2026-10-07 | A Home card for a device with no module file shows the device's own counts; cards with a module file show claimed counts. | Nothing is set up yet without a file (user, batch 2 end) | 03 Q8, S78 |
| D-01-Q9-REASK | 2026-10-07 | If the other copy can't be closed, the same Yes / No / Cancel box asks again, starting with "The other copy could not be closed."; Yes tries again, No starts without closing it, Cancel ends. | Windows has no No/Cancel-only box (user, batch 2 end) | 01 Q9 |
| D-07-RB10-NOEVOR | 2026-10-07 | Chip hover text no longer adds VKB EVO R part names on every device; EVO R part names come only from the EVO R template. | Device-specific data used for every device (user, batch 2 end) | 07 RB10, Q10 |
| D-02-S40-HANDLED | 2026-10-07 | A hardware event runs in the mode current when the main thread handles it (batch 1 GL-065 design); spec 02 S40 / D-02-Q8 reworded. | Keeps the input layer from asking the mode manager; differs only in a press/mode-change race (user, final phase) | 02 S40, Q8 |
| D-04-ALPHA-CASEFOLD | 2026-10-07 | "Alphabetical" ignores capitals: mode lists and Use Heuristic sort with casefold (alpha, Bravo, Default). | (user, final phase) | 04 S41, S52 |
| D-05-S43-BOTHROWS | 2026-10-07 | A binding's Note shows on the Configuration list's input row and on the Keyboard page's key row. | (user, final phase) | 05 S43 |
| D-04-Q13-RUNLIMIT | 2026-10-07 | The script top-level time limit (D-04-Q13-TIMELIMIT) also applies when Run reloads scripts; a script that doesn't finish is marked failed and the rest runs. | Program never freezes at Run (user, final phase) | 04 Q13, S87 |
| D-03-S41-PRESSES | 2026-10-07 | In Output Module Setup, pressing the vJoy's controls still ticks them and lights the row; spec 03 S41 reworded. | (user, final phase) | 03 S41 |
| D-03-S71-ALWAYS | 2026-10-07 | Keyboard and OSC cards always show on Home (not only with a module file or show-stubs). | (user, final phase) | 03 S71 |
| D-03-S102-PERAXIS | 2026-10-07 | One Calibration capture at a time per axis. | (recommended; user, final phase) | 03 S102 |
| D-09-S51-NEXTSOUND | 2026-10-07 | A playback mode change applies from the next sound the player starts. | (recommended; user, final phase) | 09 S51 |
| D-04-S86-RELATIVE | 2026-10-07 | A script inside the scripts folder is saved with a path relative to that folder; others keep the full path. | Profiles keep working when the data folder moves (user, final phase) | 04 S86 |
| D-02-Q6-WORDING | 2026-10-07 | Device Information says "this program's Xbox pad" (glossary D12). | (user, final phase) | 02 Q6 |
| D-02-GL243-FORGET | 2026-10-07 | A device is forgotten (twin name, alias, HidHide photo and links) when it has no module file and isn't plugged in at a scan; in-memory script objects stay. | (user, final phase) | 02 S13, S15; GL-243 |
| D-03-GL249-INPUT | 2026-10-07 | The startup device scan (device_initialization) counts as the input side; GL-249 closes with no change. | (user, final phase) | 03 7.2 |
| D-07-GL269-ALLMODES | 2026-10-07 | Button Map pool search keeps joining every mode's actions. | (user, final phase) | 07 GL-269 |
| D-07-GL274-LATER | 2026-10-07 | Picture library "Remove unused" is designed after the baseline. | (user, final phase) | 07 Q11, GL-274 |
| D-09-Q19-SUPERSEDED | 2026-10-07 | D-09-Q19 (remove gremlin/fsm.py) is superseded: fsm.py is used (double_tap, tempo, smart_toggle, hat_buttons, code_runner). | GL-279 correction | 09 Q19 |
| D-08-HISTORY-DIFF | 2026-10-07 | History Before/After highlights the deltas: changed lines tinted (red Before, green After, theme colours) with a thin left bar, changed words in a stronger tint, sides aligned row for row, and Previous/Next change buttons that move both sides. | Chosen over a white outline (invisible in the light theme, noisy, can't mark words) (user) | 08 S104, S30 |
| D-08-HISTORY-SELECT | 2026-10-07 | History Before/After text stays selectable one row at a time (each row is its own read-only text); no drag-select across rows, no Copy buttons. | It's a viewer of processed text; copying is rarely needed (user) | 08 S104 |
| D-REL-UNSIGNED | 2026-10-07 | Releases stay unsigned (no code-signing certificate); the release text keeps the SmartScreen note. | Won't fix (user) | release |
| D-07-EXPORT-BG | 2026-10-07 | Button Map exports (PDF, PNG, JPG) are encoded and written in the background; the window stays responsive and shows it is busy; failures reported as in Q19; one export at a time. | A large export froze the window (seen as a > 30 s stall on CI) (user) | 07 S101, Q19 |
