# Contract: fix a binding from Search; name unplugged devices (2026-11-22)

User: "stop the ci and release, and fix this, then release 1a, 2a". Spec: 01 S195
(new), 04 S32a (changed). Small details chosen by the lead (reported): Remove
asks Remove / Cancel; Change target… only for Map to vJoy; Undo lives in the
Search window until the profile is saved or closed; the Open message wording.

## 1. Profile edits (owner: EDIT; new `gremlin/binding_edit.py` + its test)

Works on the open profile only (no device card, no Device Bindings page):
```python
def describe(row_ref) -> str             # "the Map to vJoy binding from Z Axis of HID Remapper 2DGG (Default mode)"
def remove_binding(row_ref) -> Undo        # removes that action from that input/mode; returns an undo record
def change_vjoy_target(row_ref, vjoy_id: int, kind: str, control_id: int) -> Undo
def undo(record: Undo) -> None             # puts it back exactly
```
`row_ref` = what a Search result row already carries to identify the profile,
device, input, mode and action (read gremlin/ui/search_model.py / gremlin/usages.py
to pick it; report the shape). Each edit marks the profile changed through the
existing "unsaved changes" path, and tells the program that bindings changed
(find the signal the Device Bindings page uses), so Search, Home and the
can't-be-sent checks refresh. Device names for unplugged devices: a helper
`device_name(guid) -> str` (module name, then the profile's stored name, then
the id), used by NOTICE too.

## 2. Search window (owner: SEARCHUI; `gremlin/ui/search_model.py`, the Search window QML, tests)

Right-click menu and side panel: **Remove binding…** (ask, then
binding_edit.remove_binding), **Change target…** (Map to vJoy only: a small box
with the action editor's vJoy device/input pickers, sendable entries only;
reuse the existing QML picker component), **Undo** (Ctrl+Z) of the last Search
edits until the profile is saved or closed. **Open** on an unplugged device
shows the spec's message instead of doing nothing.

## 3. Notice (owner: NOTICE; `gremlin/ui/backend.py` `_cant_send_notice`, its test)

Names each source device with binding_edit.device_name (or the same rule), never
its id.

## 4. Tests (owner: E2E; new test file)

Real path: a profile with a binding on an unplugged device sending to a missing
vJoy -> Search lists it -> remove (asks) -> gone, profile changed, health counts
updated -> Undo -> back; Change target to an existing vJoy -> no longer "not
found"; the notice names the device; Open on the unplugged device shows the message.

## 5. Docs (owner: DOCS)

Help (tools.js Search topic, to the style guide), glossary rows (Remove binding…,
Change target…), decision row D-01-SEARCH-FIX-BINDING, map sections, to-do 0l
done, release notes 1.1.1.
