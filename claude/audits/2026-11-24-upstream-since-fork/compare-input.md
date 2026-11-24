# Upstream vs ours: input items (C-INPUT)

Read-only comparison, 2026-11-23 17:45-17:48 (agent C-INPUT). Upstream remote
`upstream`, merge base daf4057f. Items 1, 6 and 7 of the upstream-since-fork
list. Nothing in the program was changed.

Checks run (read-only, Poetry venv Python, temp USERPROFILE, Qt `offscreen`,
no windows): Windows' own scan codes for VK_F13..VK_F24 against our table; what
`key_from_code` returns for the real codes today and for the old codes after
the fix; whether QML ever calls a PySide6 property setter that has no getter.

---

## Item 1: 30151b96, F13-F24 key codes

**Upstream.** `gremlin/keyboard.py` `g_name_to_key`: the 12 entries `f13`..`f24`
used the virtual key codes 0x7C-0x87 as scan codes. Changed to the real scan
codes 0x64-0x6E (F13-F23) and 0x76 (F24). One file, 12 lines.

**Ours.** Same table, unchanged from the fork: `gremlin/keyboard.py` lines
417-428 still have 0x7C-0x87. **The bug is present.**

Proof (Windows `MapVirtualKeyExW(VK_F13..F24, MAPVK_VK_TO_VSC)` on this PC):
0x64, 0x65 ... 0x6E, 0x76, exactly upstream's values. Today
`key_from_code(0x64, False)` (a real F13 press) finds no table entry, falls
back to the layout lookup, gets no character and names the key **"0x7c"**; the
same for all 12 keys. It also caches that fake key under the name "0x7c" in
`g_name_to_key`.

What the user sees and what breaks in ours (wider than upstream's note):
- Input list / Keyboard bindings / Input Tester / Live / Macro and Map to
  Keyboard recording: a pressed F13 shows as "0x7c" (`input_to_ui_string`,
  `ui/keyboard_layout.py:62`, `ui/logical_layout.py:572`,
  `ui/module_model.py:2831`).
- **Keyboard input module claim (03 S23-S27), ours only.**
  `ModuleListModel._load_keyboard` (`ui/module_model.py:2781`) and
  `logical_layout.py:704` list keys from `g_name_to_key`, so the "F13" row
  has hwId 0x7C. A real F13 press arrives as 0x64, so a saved claim with F13
  ticked never matches it: F13 bindings are blocked once keys are chosen
  (S23). S27 then adds a second "0x7c"-named row for the real key.
- Output: Map to Keyboard / Macro / scripts given "F13" by name send
  `keybd_event(VK_F13, scan 0x7C)`. Programs that read the virtual key get F13;
  programs that read scan codes (DirectInput games) get scan 0x7C, which is not
  F13.

**Change.** Only `gremlin/keyboard.py`, the 12 table entries (take upstream's
values as is). No other code holds these numbers.

**Spec.** No statement names F13-F24 or these codes. 02 section 2 describes
the table; 03 S23-S27 (keyboard module) are supported by the fix, not changed.
03 S25 ("older files with bare scan codes should still work") is about the
storage form, not these values. No conflict. Spec line: `Spec: 03 S23` (claim
works for F13-F24) plus a section 10 gap entry on page 02 closed by it.

**Saved data (no migration wanted: unreleased rule).** Keys are stored as
scan code + extended flag (`scan-code` property in Map to Keyboard
`action_plugins/map_to_keyboard/__init__.py:164-178`, Condition
`condition.py:507/524`, Macro, keyboard claim hwIds, keyboard bindings'
input_id). What existing saved data would do after the fix:
- Saved from a **real key press** (bindings, recorded keys): already 0x64..0x76.
  They keep their meaning and now show "F13".."F24". Improvement only.
- Saved from a **name or the key list** (claim rows ticked from the list,
  keys typed by name, scripts' `key_from_name("F13")`): stored 0x7C-0x87. After
  the fix, `key_from_code(0x7C, False)` resolves through the layout to **"\t"
  with VK_TAB** on this PC (checked), and 0x7D-0x87 to keys named "0x0" (VK 0,
  0xC2 for 0x7E). So an old saved F13 in Map to Keyboard would **send Tab**,
  and F14-F24 would send nothing useful. Old claim hwIds 0x7C.. show as odd
  extra rows. Since the program is unreleased this is only the user's own test
  profiles/Library; re-pick the key once. Worth one line in the release notes
  and a check of the user's own profiles (search their profiles for
  `scan-code` values 124-135) before building. Not a blocker.
- Side note (not upstream's): the fallback caching the fake name ("0x7c",
  "\t") into `g_name_to_key` is a separate small wart; leave it unless the user
  asks.

**Tests pinning current behaviour.** None pin 0x7C-0x87.
`test/unit/test_script_suite.py::test_keyboard_reader_reacts_to_its_key_only`
uses `key_from_name("f13")` and feeds `(k.scan_code, k.is_extended)`, so it
stays green either way (it is self-consistent, which is why it never caught
this). `test/fixtures/scripts/scripts.json` mentions F13 in text only.

**New failing test** (`test/unit/test_keyboard_f13_f24.py`, suggested name):
1. For i in 13..24: `key_from_code(MapVirtualKeyExW(VK_Fi, 0, layout), False).name == f"F{i}"`
   (fails today: "0x7c").
2. Pure table check without Windows calls: `key_from_name("f13").scan_code == 0x64`,
   `key_from_name("f24").scan_code == 0x76`, and the 12 scan codes are unique
   and not already used by another entry (checked: 0x64-0x6E and 0x76 collide
   with nothing in our table).
3. Real path for the claim: keyboard module claim with F13 ticked from the
   key list passes an Event with identifier (0x64, False) through the input
   module gate (fails today).

**Risks.** Low. Japanese/Brazilian keys that really send 0x7B-0x7E (NoConvert,
Yen, Brazilian keypad ".") stop being misnamed "F14"/"F15" and get their
layout names: also a fix.

**Effort.** One small agent fix plus the test: 3-8 min (timings.md: agent fix).

---

## Item 6: 855eb31c and 2a773013, write-only Qt properties

**Upstream.** Gave getters to write-only properties:
- `LogicalDeviceSelectorModel.validTypes`: added `_get_valid_types`
  (`InputType.to_string` of `self._valid_types`) as `fget`.
- `AxisCalibration.guid`: added `_get_guid` (device guid or "").
- `DeviceListModel.deviceType`: getter + `deviceTypeChanged` signal.
- `LogicalDeviceManagementModel.guid`: `constant=True`.

**Ours.**
- `DeviceListModel.deviceType`: **already fixed** in ours (getter, notify,
  comment "QML drops a value set on a property it can't read",
  `ui/device.py:276-283`). Nothing to take.
- `LogicalDeviceManagementModel`: not present in ours (our Logical Device was
  rebuilt). Nothing to take.
- `LogicalDeviceSelectorModel.validTypes` (`ui/device.py:535`):
  `QtCore.Property(list, fset=_set_valid_types, notify=inputsChanged)`, no
  getter. **Bug present.**
- `AxisCalibration.guid` (`ui/device.py:1268`): no getter, **and our
  `_set_guid` is already a no-op (`return`, line 1094)**; our Calibration page
  picks the device through `moduleSlug`, and no QML sets `guid` on
  `AxisCalibration` (`qml/DialogCalibration.qml:374-377`). Dead code, no user
  effect.
- Same pattern elsewhere (not in upstream's commits, found by grep):
  `action_plugins/condition/comparator.py:98,102,130`,
  `action_plugins/double_tap/__init__.py:229,241`,
  `action_plugins/tempo/__init__.py:240,252` are decorator properties
  `@QtCore.Property(..., fset=...)`: these decorate the getter, so they do
  have one. Not affected.

Proof (off-screen PySide6 in our venv): a QML object `WO { validTypes: [...] }`
with a setter-only property never calls the setter (no error, no warning);
the same with a getter calls it. A `property alias validTypes: _m.validTypes`
to a setter-only property (our `qml/LogicalDeviceSelector.qml:22`) also never
calls it.

What the user sees today: `_valid_types` stays `[]`, and
`LogicalDevice.inputs_of_type([])` means "all types". So every Logical Device
picker lists **all** axes, buttons and hats, whatever it asked for:
- `qml/DialogHealth.qml:546` and `qml/DialogSearch.qml:1037` ask for one type
  (the start input's type) and get all: a button target can be offered an
  axis.
- `qml/ScriptConfiguration.qml:115` (script logical-input variable) ignores
  the variable's declared valid types.
- Condition (`ConditionAction.qml:283,312`) and Macro (`MacroAction.qml:379`)
  ask for all three anyway: no visible change.
`currentIdentifier`/`currentIndex` use the same `_valid_types`, so the
selection stays consistent today; after the fix the row numbers change with
the filter but are computed the same way, so it stays consistent.

**Change.**
- `gremlin/ui/device.py` `LogicalDeviceSelectorModel`: add
  `_get_valid_types` and pass `fget=` (take upstream's code).
- `AxisCalibration`: cleanest current design is to **remove** the dead
  `guid` property and the no-op `_set_guid` rather than add a getter
  (unreleased rule; nothing reads or sets it). Upstream's getter version would
  also do no harm. Small detail; lead may decide.

**Spec.** 06 owns `LogicalDeviceSelectorModel` (02 section 2 says so).
Filtering by declared type is what the pickers already ask for; no statement
says "all types". No conflict. Check page 06 and 05 (Health/Search target
pickers) for a statement to cite; if none, `Spec: 06 section 10 gap` added in
the same batch. Calibration guid removal: `Spec: none (no behaviour change)`.

**Saved data.** None: these are UI-only properties.

**Tests pinning current behaviour.** None found (`validTypes` in tests is the
VJoySelector's, a different model: `test_cant_send*.py`,
`test_output_picker_keeps_wire.py`, `test_vjoy_turned_off.py`). No test reads
`AxisCalibration.guid`.

**New failing test** (real QML path, off-screen, like
`test_cant_send.py:259`): create `LogicalDeviceSelector.qml` (or a
`LogicalDeviceSelectorModel` from QML) with `validTypes: ["button"]` on a
Logical Device holding one axis and one button; assert the model's
`rowCount()` is 1 (fails today: 2). A guard test that scans `gremlin/` and
`action_plugins/` for `QtCore.Property(` with `fset=` and no `fget=` would
stop this coming back (fits "design for change").

**Risks.** Low. A picker that relied on seeing every type would now be
filtered; the only one-type callers are Health and Search, where filtering is
the intent. Check those two dialogs live once.

**Effort.** One agent fix plus test and guard: 3-8 min (timings.md: agent fix).

---

## Item 7: 32eebedc, InputIdentifier.label names

**Upstream.** `InputIdentifier.label` built "Device - Axis 3" from
`InputType.to_string(...).capitalize()` + raw id. Now uses
`common.input_to_ui_string` ("X Axis", key names) and, for a real device,
`DeviceDatabase().get_mapping_by_uuid(guid).input_name(...)` so the Options
"Input names" setting (Numerical / Label / both) applies. Same commit also
reworked Kobold QML (`InputAssignButton.qml`, `MergeAxisAction.qml` widths and
"Click to assign current axis." text, `Metrics.qml`): that QML is upstream's
Kobold style, which we do not have; only the label part applies to us.

**Ours** (`gremlin/ui/device.py:76-99`). Same old string build, but the device
part already uses our one shown name (`device_names.shown_name`, GL-124, 02
S17) and refreshes on `deviceNamesChanged` (D-01-OWNER-NOTICES). **The bug is
present**: axes show "Axis 1" instead of "X Axis" (the name used everywhere
else through `input_to_ui_string`), device_db labels are never used, and a
keyboard identifier would read "Key (30, False)"-style raw text.
`osc_persist.py:85-104` wraps the label for the OSC device and otherwise calls
the original, so OSC is untouched by the change.

**Where the label is on screen (every place found):**
- Merge Axis: `action_plugins/merge_axis/MergeAxisAction.qml:181,203`
  (`firstAxis.label`, `secondAxis.label`).
- Dual Axis Deadzone: `action_plugins/dual_axis_deadzone/DualAxisDeadzoneAction.qml:200,217`
  (`axis1.label`, `axis2.label`), both through `action_plugins/axis_pair.py`
  `AxisView` (an `InputIdentifier`).
- Script page, physical-input variable: `gremlin/ui/script.py:377`
  `PhysicalInputVariableModel.label` -> `qml/ScriptConfiguration.qml:223`
  (the InputListener's text).
- `UIState.currentInput` (`ui/backend.py:164`) is an InputIdentifier; it is
  what Merge Axis / Dual Axis assign, so its label is what then shows.
- OSC page identifiers (`ui/osc_device_model.py:896`) go through the OSC
  override, unchanged.
- Logical Device pickers (`LogicalDeviceSelectorModel`, Condition, Macro,
  Script) show the Logical Device's own input labels, not
  `InputIdentifier.label`: unaffected.

**Change.** `gremlin/ui/device.py` `InputIdentifier.label` only: build the
input part with `common.input_to_ui_string`, and for a physical device apply
`DeviceDatabase().get_mapping_by_uuid(self.device_guid).input_name(...)` when
a mapping exists. **Keep our `shown_name`** for the device part (do not take
upstream's `dill.DILL.get_device_name`, which would undo 02 S17 / GL-124).
Wrap the lookup in `try` as `references.input_label` does, so an odd input
type never breaks a page. Better still (design for change, one owner): reuse
the one existing "input as shown" helper instead of a third copy; today the
same build exists in `references.input_label`, `ui/action_model.input_name`
and `Device` (`ui/device.py:421`). A single helper that applies the device_db
mapping, used by `InputIdentifier.label`, is the cleanest; the lead decides
whether that wider tidy rides along.

**Spec.** 02 S10: "label inputs from device_db.json by VID/PID when Options >
Input names asks for labels, and fall back to "Axis 3" style names
otherwise". The editors' labels not following that is a gap against S10 (fix
code, not spec). Two things to raise with the user (spec wording, rule 2):
1. S10's fallback example says "Axis 3" style; `input_to_ui_string` gives
   "X Axis" (axis_names long names) and the rest of the program already shows
   that. Taking upstream makes the editors match the rest; the S10 example
   text is then stale and should be reworded with the user's OK.
2. Refresh: the label notifies on `deviceNamesChanged` only. Once it depends
   on Options > Input names (`ui/general/display-mode`), changing that option
   would not refresh open editors until they reload (nothing listens to
   `display-mode` today: only `input_cache.py:91` reads it). Either accept
   (reopen the editor) or have the option change send the same notice; that
   is a behaviour choice for the user.

**Saved data.** None: the label is computed, never stored.

**Tests pinning current behaviour.**
- `test/unit/test_device_names_notice.py:91-100` ("Stick - Button 3") and
  `test/unit/test_batch3_C3a.py:514` ("My Stick - Button 3"): buttons give
  "Button 3" from `input_to_ui_string` too, and Numerical mode/no device_db
  entry keeps it, so they stay green as long as the test device has no
  device_db mapping and the option is the default. Check the option's default
  before relying on that.
- `test/unit/test_osc_refs.py:108` ("OSC - /fire"): OSC override, unchanged.
- `test/integration/action_plugins/conftest.py:91` builds identifiers by label;
  check it does not match axis labels by the old "Axis N" text.
- `test/unit/action_matrix/test_matrix_axis.py` labels are action labels, not
  this one.

**New failing test.** `InputIdentifier(stick_guid, InputType.JoystickAxis, 1).label`
== `"<shown name> - X Axis"` (fails today: "Axis 1"); with a device_db mapping
for that VID/PID and Input names = "Label", the label is the device_db name
(fails today). Drive the real path: assign `uiState.currentInput` into a Merge
Axis action and read `firstAxis.label`.

**Risks.** Low to medium: the label now reads Options and the device
database on each QML read (cheap, singleton lookups, main thread). The refresh
question above is the only behaviour gap.

**Effort.** Label fix plus tests: 3-8 min (timings.md: agent fix). With the
single shared helper replacing the three copies: 5-10 min (timings.md:
refactor).

---

## Summary

| Item | Bug in ours? | Files | Conflicts / spec | Saved data | Effort |
|---|---|---|---|---|---|
| 1 F13-F24 | Yes, plus keyboard claim never matches F13-F24 (ours only) | `gremlin/keyboard.py` table | none; supports 03 S23 | old name-picked F13 (0x7C) would send Tab after the fix; recorded keys improve | 3-8 min (agent fix) |
| 6 write-only props | `validTypes` yes (pickers show all types); `AxisCalibration.guid` dead (setter no-op); `deviceType` already fixed | `gremlin/ui/device.py` | none | none | 3-8 min (agent fix) |
| 7 label names | Yes | `gremlin/ui/device.py` `InputIdentifier.label` | keep our `shown_name` (02 S17); S10 example wording and display-mode refresh need the user | none | 3-8 min; 5-10 min with shared helper (refactor) |

Blockers: none. Two questions for the user before item 7 (S10 wording,
refresh on Input names change). Items 6 and 7 both touch `gremlin/ui/device.py`
(one owner, or stagger). Item 1 is independent.
