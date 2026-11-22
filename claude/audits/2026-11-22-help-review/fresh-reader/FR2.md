# Fresh-reader report: FR2 (2026-11-22)

Read only qml/help/*.js strings (mainly device_bindings_actions.js and modes.js;
grepped the rest for macro, repeat, mode, previous, temporary). Start 07:33.

## Task 1: one stick button sends a key that repeats while held (Macro)

Could do it: with guesses.

Steps I'd take:
1. Home: double-click the stick's card (device-bindings-actions-device-bindings-page).
2. Right-click the button's row, Add Action, choose Macro (device-bindings-actions-add-action).
3. Add Step, pick a Keyboard step, set the key (how? see problem 1b).
4. Repeat Mode: Hold. Set Delay (sec) for the gap between repeats.
5. OK, then File > Save Profile.

Problems:
- 1a. Stuck/guess: a Keyboard step "start[s] on Pressed" (device-bindings-actions-macro,
  "New Joystick, Keyboard ... steps start on Pressed."). For a repeating key I need
  press then release. Does one step press and release, or do I add a second step set
  to Released? Not said. Fix: add a How-to example "A key that repeats while held:
  add a Keyboard step (Pressed), a Pause, a Keyboard step (Released); Repeat Mode Hold."
- 1b. Stuck: how a Keyboard step's key is chosen (record a key? pick from a list?) is
  not described anywhere; only Record Inputs for whole recordings. Fix: one line per
  step kind, or at least for Keyboard.
- 1c. Guess: two delays. "Delay (sec): The wait between repeats" vs Macro Default Delay
  "Between steps without a Pause". Does Delay add to the step delay? Fix: one sentence
  saying how they combine.
- 1d. Guess: Map to Keyboard "Holds keys down while the input is held"
  (device-bindings-actions-map-to-keyboard). Would that already repeat like a held
  keyboard key? A newcomer may pick it and wonder. Fix: add "It doesn't repeat; for a
  repeating key use a Macro with Repeat Mode Hold" and link Macro.
- 1e. Guess: "Hold ... always plays at least once" - on press, or does a short tap
  play the full step list including release? Minor.

## Task 2: a button switches to "Landing"; another goes back to where you were

Could do it: with guesses.

Steps I'd take:
1. Manage Modes on the mode bar, Add Mode, rename it Landing (modes-manage).
2. Mode box: pick my normal mode (e.g. Default). Button A: Add Action > Change Mode > Switch, pick Landing.
3. Mode box: pick Landing. Button B: Add Action > Change Mode > Previous (or Unwind).
4. OK, Save Profile, Run, test.

Problems:
- 2a. Stuck/guess: nowhere says the "go back" action must be bound in the Landing mode
  (or a parent of it). I only worked it out from "Only the actions of the running mode
  and its parents run" (modes-q-button-does-nothing). This is the main trap. Fix: in
  device-bindings-actions-change-mode add "Put the action in the mode you press it
  from" plus a short worked example (button A in Flight, button B in Landing).
- 2b. Guess: Previous or Unwind for "go back"? Both topics define them, but neither says
  which to use for a simple "back". Previous flips back to Landing if pressed twice;
  Unwind doesn't. Fix: one line "To just go back, use Unwind; Previous toggles."
- 2c. Stuck: device-bindings-actions-change-mode has no How to; it never says where you
  pick the target mode for Switch/Temporary or build Cycle's list. Fix: add How-to steps.
- 2d. Guess: Add Mode doesn't say what the new mode is called, or what parent it gets by
  default (modes-manage "To add a mode, choose Add Mode."). If Landing inherits from my
  normal mode, button A still switches to Landing from Landing. Fix: say the default
  name and parent.
- 2e. Slow/link: the path concept that Previous/Unwind depend on is explained only in
  modes-while-running, but change-mode's related list omits modes-while-running.
  Fix: add it to related and link it in the body.
- 2f. Two wordings: change-mode gives its own Oldest/Newest summary, modes-cycle-resolution
  another ("your path goes back to the first time..."). Not contradictory but reads as
  two explanations; slow. Fix: keep one, link the other.

## Task 3: a button switches to a mode only while it is held

Could do it: yes (target-picking step guessed, as 2c).

Steps I'd take:
1. In the normal mode, button C: Add Action > Change Mode > Temporary, pick the mode.
2. OK, Save, Run; hold to enter, release to return.

Problems:
- 3a. Guess: if the temporary mode also binds button C (or doesn't), does releasing
  still return? "Letting go returns to the mode before" (modes-while-running) suggests
  yes, but the release happens in the other mode. Fix: "Letting go always returns,
  whatever the held mode binds on that input."
- 3b. Guess: "At Stop, a Temporary mode ends, and the mode under it becomes the mode
  shown." "Under it" can read as its parent mode (Manage Modes uses "under" for children:
  "Modes under it move up one level"). Fix: "the mode you were in before it".
- 3c. Same as 2c: no How-to for picking the mode.

## Top 3 problems

1. Change Mode has no How-to and never says the "go back" action must sit in the mode
   you press it from (2a, 2c) - device-bindings-actions-change-mode.
2. Macro doesn't explain a Keyboard step (choose key, Pressed vs Released) nor give the
   "repeat a key while held" recipe; Map to Keyboard doesn't say it won't repeat
   (1a, 1b, 1d) - device-bindings-actions-macro / -map-to-keyboard.
3. Path/back behaviour is split across three topics with differing wording and missing
   links; no advice on Previous vs Unwind (2b, 2e, 2f, 3b) - modes-while-running,
   modes-cycle-resolution, device-bindings-actions-change-mode.

Start 07:33, end 07:34.
