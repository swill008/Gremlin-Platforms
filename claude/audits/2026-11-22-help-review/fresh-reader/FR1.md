# Fresh reader FR1 (2026-11-22)

Help only (qml/help/*.js). Started 07:33.

## Task 1: Set up two vJoy devices with different buttons after installing, then add a third later

Could do it: with guesses

Steps:
1. Run the Setup.exe and choose a folder (getting-started-install).
2. On setup's **Drivers** page, under **vJoy devices**, choose the **2 devices, full** preset. That gives 128 and 127 buttons, so the button counts already differ. Otherwise choose rows and set **Buttons** per row (getting-started-setup-drivers).
3. Choose **Next**, accept the administrator prompt, and read the results.
4. Later: **Tools › Drivers**, choose **+ Add device** (it shows "vJoy 3 · 126 buttons"), then **Apply**, **OK**, and answer **Run is on** if a profile is running (tools-drivers-vjoy-devices, tools-drivers).
5. Guess: right-click the new vJoy card, choose **Module Setup…**, tick its outputs and choose **Save Module** (home-devices-vjoy-output). Only reached through a related link.

Problems:
- Got stuck on what to do after adding a device. tools-drivers-vjoy-devices ends at Apply. It doesn't say whether the new device shows on Home straight away or only after a program restart. It also doesn't say that its outputs must be ticked in the output module before bindings work ("Only the outputs ticked there are sent to vJoy", home-devices-vjoy-output). Fix: add a last step, "Then set up its output module: see Set up a vJoy output module", and say whether a restart is needed.
- Two topics disagree. tools-drivers-vjoy-devices has a **Devices** count box ("choose a Preset, or set the number in Devices"). getting-started-setup-drivers never mentions that box, only "choose a Preset, or change the device rows." I had to guess whether setup has it. Fix: name the same controls in both topics, or say that setup has no Devices box.
- Had to guess whether I can set the button counts myself. "Each new device gets one button fewer than the one before" (tools-drivers-vjoy-devices) reads as if the counts are fixed. Only the row description "its buttons (0 to 128)" suggests I can change them. Fix: say "The program suggests one button fewer for each new device; you can change it."
- Slow to read. getting-started-setup-drivers repeats most of tools-drivers-vjoy-devices (preset list, rows, + Add device, the match warning) and adds the HidHide and C++ Runtime points. Fix: keep setup's topic to the steps and link to the Tools topic for the details.
- Small: the same thing is spelled "in grey" in getting-started-setup-drivers and "in gray" in tools-drivers-vjoy-devices.

## Task 2: You updated vJoy and a device went missing; get it back now, or later

Could do it: with guesses (yes when the update ran through setup or Tools › Drivers)

Steps:
1. When the box **The vJoy update lost a device** appears, choose **Repair Now** to put the device back now, or **Repair Later** to fix it later (tools-drivers-vjoy-update).
2. Later: open **Tools › Drivers**, find the row marked **lost in the vJoy update**, and choose **Repair**. Accept the administrator prompt.

Problems:
- Got stuck if I start from Troubleshooting. getting-started-device-missing ("A device is missing or seen twice") covers Hidden Cards, HidHide and replaced sticks. It says nothing about a vJoy device lost in an update, and doesn't link to tools-drivers-vjoy-update. home-devices-vjoy-left-out doesn't link to it either. Fix: add a case, "A vJoy device is gone after a vJoy update: see Keep your vJoy devices through a vJoy update."
- Got stuck if vJoy was updated outside the program, for example with vJoy's own installer. The Help only covers updates run from setup or Tools › Drivers ("The check runs only for an update of vJoy", tools-drivers-vjoy-update). Fix: say what to do then: add the device again in Tools › Drivers with the same axes, buttons and hats.
- Had to guess what happens after a repair. The topic doesn't say whether running games lose the devices, whether **Run** stops, or whether the program needs a restart before the device's card and bindings work again. Fix: add one line about each.
- Had to guess what the **Repair** button does. It's unclear whether it acts at once or waits for **Apply** like other edits. "On a lost device's row: puts that device back" (tools-drivers-vjoy-update). Fix: say "It works at once; no Apply needed" (or the opposite).
- Had to guess: "A lost device that is back with the same layout drops off the list by itself." Back how? By my own edit, or some other way? Fix: "If you set it up again yourself with the same axes, buttons and hats, the row goes away."
- A word is not explained: "older vJoy tools" ("lost vJoy devices that were set up with older vJoy tools"). Fix: name the tool, for example vJoy's Configure vJoy program, or drop the words.

## Task 3: Make the program start with Windows, and understand why the option might show off

Could do it: yes

Steps:
1. Choose **Tools › Options**, then **General**. Under **Startup and Tray**, turn on **Start Gremlin-Platforms when Windows starts**. Or tick **Start with Windows** in the tray menu (options-profile-start-with-windows).
2. Why it shows off: it is off at first. Or I switched the program off in Windows' Startup Apps, and the note **Turned off in Windows' Startup Apps** shows. Turning it on opens that Windows page, where I turn it back on.

Problems:
- Had to guess what happens after I turn it back on in Windows' Startup Apps. It's unclear whether the program's switch turns on by itself, and whether it does so straight away or only after a restart. Fix: add "When you turn it on there, the switch here shows on again."
- Slow to read: the same facts are in three places (getting-started-start-up, options-profile-start-with-windows, options-profile-q-start-with-windows). getting-started-start-up repeats four of the Good-to-know points. Fix: keep one line plus a link in getting-started-start-up.
- Had to guess whether this works for the portable copy. Only uninstalling is mentioned ("uninstalling the program, removes it from that list"). Fix: say whether the portable copy can use it, and what happens if its folder moves.

## Top 3 problems

1. The vJoy device topics stop at **Apply**. Nothing says to set up the new device's output module or whether the program needs a restart (tools-drivers-vjoy-devices; also after a Repair in tools-drivers-vjoy-update).
2. Troubleshooting "A device is missing or seen twice" (getting-started-device-missing) has no case or link for a vJoy device lost in an update. Nothing covers an update done outside the program.
3. The setup Drivers topic and the Tools › Drivers topic disagree (the **Devices** box) and largely repeat each other, so a reader has to compare them to find the differences.

Ended 07:34.
