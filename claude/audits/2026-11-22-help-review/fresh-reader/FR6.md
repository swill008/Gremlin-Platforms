# Fresh reader FR6 (2026-11-22, 07:34 to 07:35)

Help only (qml/help/*.js, strings read as a reader would).

## Task 1: Save my stick's setup and give it to a friend with the same stick

Could do it: **with guesses**

Steps I would take:
1. Open the Device Library (toolbar **Device Library**, or Tools › Device Setup › Device Library…).
2. Select my stick, choose **Save to Device Library…**, tick the profiles, press **Save**.
3. Select the new saved setup, choose **Export…**, pick where to save the .gmap file.
4. Send the file. My friend chooses **File › Import Device…** in their Device Library, selects the new saved setup, chooses **Copy to Another Stick…** with their stick as To, and presses **Copy**.

Problems:
- **Two sharing routes, nothing says which to use.** Device Library Export (device_library.js `device-library-export`) and Export / Import Device (home_devices.js `home-devices-device-pack`) both write a .gmap file. Quote: "saves a copy of a device's setup as one device file (.gmap)". The second adds Made by / Note and "the output modules those actions send to". Importing is also two routes: Library Import then Copy, or the Import tab with "Onto an existing device". I can't tell whether the files differ, or which my friend should use. Fix: one short topic, "Which way to share?", linked from both, naming the difference and recommending one.
- **The common question skips the first step.** `device-library-qa-share` begins "Select the saved setup and press Export…", but it never says to make one first. `device-library-devices` says Export is "grayed out on a device". Fix: step 0, "Save to Device Library… first, or use Export Current Setup…", with a link to `device-library-save`.
- **Same model, different unit: does it go under my friend's stick?** `device-library-import`: "It goes under the device it was made from, when that device is in the Device Library". I had to guess whether my friend's own stick of the same model counts as "the device it was made from". Otherwise it goes under a new Not connected device. Fix: say plainly what happens with the same model on another PC.
- **Calibration and vJoy on the friend's PC.** `device-library-qa-new-stick` says "Untick Calibration unless the sticks are the same model". So should my friend copy my calibration? Calibration belongs to one physical unit. Also, bindings hold "the vJoy outputs they send to". Nothing says what happens when the friend's vJoy devices differ. Fix: add a "Good to know" line in `device-library-qa-share` covering calibration and differing vJoy devices.

## Task 2: I broke my setup: get back an earlier autosave

Could do it: **with guesses**

Steps I would take:
1. Open the Device Library and expand my stick. Make sure the **Autosaves** filter is ticked.
2. Find an autosave (named "Autosave: before …"), right-click it, choose **Restore to This Stick…**, press **Restore**.
3. If there is no autosave: Tools › History, pick the save, **Restore to before this change**, then save the profile.

Problems:
- **Autosaves don't cover ordinary edits, and the Help never says so in one place.** `device-library-autosaves` lists only Library actions, Delete Device and imports: "whenever something is about to replace or remove its settings". If I broke my setup by editing bindings and saving, I found no autosave and had to work out that History is the way back. `device-library-qa-go-back` comes closest but has no autosave-versus-History rule. Fix: put one line at the top of `device-library-autosaves`, for example "Editing and saving bindings makes no autosave; use Tools › History for those."
- **Clear Setup's autosave name disagrees between topics.** `device-library-qa-where` says "Clear Setup… keeps "Autosave: stick deleted" under the stick". `device-library-autosaves` names "stick deleted" for **Delete Device** only and doesn't list Clear Setup at all. Fix: add Clear Setup to the list, with its own name.
- **Restore to This Stick is left out of the menu when the stick is unplugged.** `device-library-menus` says "(when its stick is plugged in)", and `device-library-qa-grayed` says menus "leave out what doesn't apply". A reader with an unplugged stick sees no Restore item and gets no hint. Fix: in `device-library-restore`, add "Not in the menu? Plug the stick in."
- **Slow to read.** The way back is spread over six topics: autosaves, autosave-limit, restore, qa-where, qa-go-back and home-devices-backups. Each repeats part of the others. Fix: make `device-library-qa-go-back` the single decision list (last change / Library change / stick settings / profile edit) and link to it from the rest.

## Task 3: Combine two sticks into one Logical Device and send it to vJoy

Could do it: **with guesses**

Steps I would take:
1. Make sure each stick's controls are ticked in its Module Setup, and the vJoy outputs in Output Module Setup.
2. Open the Logical Device (toolbar). Right-click empty space › **Add Inputs**, and add the axes and buttons.
3. For each Logical Device control, right-click › **Assign Hardware**, and tick the stick control (stick A's axis, stick B's buttons).
4. On each Logical Device control, right-click › **Add Action** › **Map to vJoy**, pick the vJoy device and output, **OK**.
5. Save the profile, then Run.

Problems:
- **What happens when two physical controls feed one Logical Device control?** `logical-device-about` says "Use it to combine several physical controls before you send them on". Assign Hardware lets me tick several. Nothing says whether they add up, the last one wins, or I need a Merge axis. Fix: one "Good to know" line in `logical-device-assign-hardware`, linking to Merge axis (`device-bindings-actions-merge-axis` or similar) for two axes into one.
- **The send-to path shows only Xbox.** `logical-device-send-to-xbox-vjoy` gives "physical control → Assign Hardware → Logical Device control → Map to Xbox → Xbox 360 Controller". It has no vJoy example. Nor does it say that the vJoy output must be ticked in Output Module Setup; that is only in `device-bindings-actions-map-to-vjoy`: "ticked in Output Module Setup". Fix: add the vJoy path and the Output Module Setup requirement here.
- **Modes: guess.** Assign Hardware's action goes "in the current mode", and the Logical Device's own actions "belong to the current mode". I had to guess whether both must be in the same mode, and whether Default carries into child modes. Fix: one line saying which mode to be in when setting up both halves.
- **Does the stick still send directly as well?** Nothing says whether a stick control that feeds the Logical Device can also keep its own Map to vJoy, which would send twice. Fix: a "Good to know" line in `logical-device-assign-hardware`.

## Top 3 problems

1. Two parallel share routes (Device Library Export/Import versus Tools › Export / Import Device), with no word on which to use or how they differ (`device-library-qa-share`, `home-devices-device-pack`).
2. Autosaves versus History: the Help never says that ordinary edits make no autosave. The way back is spread over six repeating topics, and the Clear Setup autosave name disagrees between `device-library-qa-where` and `device-library-autosaves`.
3. Logical Device "combine": it never says what two sources on one control do (sum, last-wins or Merge axis). The send path has only an Xbox example, without the vJoy Output Module Setup step (`logical-device-assign-hardware`, `logical-device-send-to-xbox-vjoy`).
