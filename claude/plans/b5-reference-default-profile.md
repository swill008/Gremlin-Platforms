# B5: Reference pick list labels; default profile (plan, 2026-11-23)

Source: claude/audits/2026-11-24-upstream-since-fork/compare-features.md items
12 and 13 (upstream d6e9b053, 2877b2e4). User answers: 16a labels and order
under 05 S60 without upstream's "unused actions last" (05 S57 never offers
them); 17a a Default profile file row; 18a a program whose own profile file
is missing loads the default after the one notice; 19a no start-up default
(start-up stays 04 S21); 20a auto-loaded profiles stay in Recent (04 S18).

## Reference pick list (05 S60, new statement)
Each entry "[mode] device - input › action", sorted with numbers by value
(Button 2 before Button 10), each action once; the pane's own unsaved draft
actions get the label too; names from our shown device name and the shared
input_label helper (B2). One natural_key in gremlin/common.py (three copies
today: logical_device.py, ui/hardware_layout.py import, ui/keyboard_layout.py;
the keyboard one has another shape: its sort order gets a test). Tooltips
"Share this action" / "Duplicate this action" (glossary rules out "link").
Live check: the input row refreshing after a pick (unverified).

## Default profile (02 S89/S90 reworded, new S90a)
Options > Profiles: the Keep running switch becomes one choice "When a
program with no profile comes to the front: Stop the profile / Keep running /
Load the default profile", plus a Default profile file row enabled only for
the third choice. Our rules stay: our own window coming to the front changes
nothing; unsaved edits wait with the Auto-load Waited notice; a missing file
gives one notice. A program whose own profile file is missing loads the
default after its notice (18a). No settings migration (unreleased).

## Split
| Agent | Files | Job |
|---|---|---|
| B5-REF | action_plugins/reference/, gremlin/references.py (label helper), gremlin/common.py natural_key + the three copies, reference QML tooltips | labels, order, drafts, one natural_key, keyboard sort test |
| B5-AUTO | gremlin/config.py (setting), the auto-load logic (find its owner: ui/backend.py / process monitor), joystick_gremlin.py if it reads the setting | the three-way choice, default profile, missing-file rule |
| B5-OPT | gremlin/ui/option.py rows, qml/OptionProfileAutoLoading.qml | the choice row and the Default profile file row (enabled only for the third choice) |
| B5-TESTS | test_profile_auto_loading, test_autoload_and_mode_prompts, test_backend_commands, test_option_list_saving, test_options_shared_pieces, test_write_less + new tests | old setting names updated; new behaviour tested |
| B5-DOC | 02/04/05 map, Help (options_profile.js, Reference topic), glossary | docs |
Lead: spec statements first, the Reference row live check, merge, tests, build.
