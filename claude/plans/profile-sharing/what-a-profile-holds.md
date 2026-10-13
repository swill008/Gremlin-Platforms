# What a profile holds today (scouts P-INSIDE, P-OUTSIDE, 2026-10-13)

Inside the profile .xml (`<profile version="16">`, gremlin/profile.py _xml_text :1729, to_xml :1663, from_xml :1545):
- inputs: per device + input + mode with bindings; device by GUID (device-id); keyboard keys by scan code; OSC inputs by osc-uid (InputItem.to_xml :2074)
- bindings: Treat as, axis/hat-as-button settings, root action id (:2172)
- settings: startup mode, macro delay, vJoy devices used as input, vJoy start values (Settings.to_xml :289)
- library: every used action, flat, by id; type = plugin tag (Library.to_xml :1373)
- modes: the tree, by name (:2627)
- scripts: path to .py (relative to scripts\ when inside it) + variable values (user_script.py :980)
- devices: GUID -> display name at last save (:1472)
- No metadata: no name, author, description, date or app version.

Points outside the file: device GUIDs (inputs, Merge Axis, Dual Axis Deadzone, Condition, Macro); vJoy numbers; Xbox pad number; Logical Device uids (modules\Logical Device\module.json); OSC uids and Send OSC target names (modules\OSC\module.json); file paths (Play Sound, Run Command, Load Profile, scripts outside scripts\); action plugin tags; program settings (macro delay "use Options", voice, playback mode, refresh axes, Change Mode resolution, auto-load list, last mode per profile, device name aliases).

Outside, per device (modules\<Device Folder>\): module.json (claims, names, calibration, Output View, layout, device map), pictures\, device.json (id; never exported). Already carried by Export Device (.gmap, device_zip.py :12-29, device_pack._collect_wires :620) incl. the device's bindings per mode, the mode tree, OSC rows used, vJoy/Xbox output modules used; import re-keys to a chosen target device and can renumber vJoys / create Logical Device controls.

Machine-specific (cannot be copied): device GUIDs, vJoy driver setup (count, axes/buttons/hats), ViGEmBus, HidHide, keyboard layout, TTS voices, absolute paths.
Not carried today: the profile .xml as a whole (settings, modes without bindings, other devices), Logical Device labels/groups, OSC targets/feedback, scripts, user plugins, sound files, programs, Load Profile targets, program settings.
