# Profile Settings restyle (planning, 2026-11-23)

The user: "the page layout looks old and not the theme we now use in our
program." qml/ProfileSettings.qml still has the original two-column layout;
the Options window uses the shared ConfigGroup cards and OptionEntryCard rows.

- settings.png: the real page today (gremlin-ctl window screenshot).
- options.png: the real Options window, the look to match (colours sampled).
- profile-settings-mockup.png: the proposal drawn on the real screenshot
  (user asked: "do an image generation using the actual image of the
  window"); made by the scratch script make_mock.py (PIL), not by the program.

Open questions (in the chat): rebuild with the Options pieces or restyle in
place; Initial Values layout (card per vJoy / picker / table); number format
0.00 and "s"; stay a main-window page or become a window.

## Answers (user, 2026-11-23: "1b, 2a, 3a, 4a, 5a, 6a")

1b. Name stays **Profile Settings** (glossary word unchanged).
2a. Toolbar icon: a document with a small gear.
3a. The toolbar button sits right after Options.
4a. Profile Settings becomes its own window, a twin of Options (left list
    General / vJoy / Scripts, ConfigGroup cards and OptionEntryCard rows),
    saved with the profile; View › Profile Settings and View › Scripts open
    it at their section; the old main-window pages go.
5a. vJoy Initial Values: one card per vJoy, axes in two columns.
6a. Numbers: two decimals (0.00); the delay with its unit (0.050 s).

Status: planning only; waiting for the user's "build". The spec changes
(pages 01 and 04: entry points, toolbar S58, the two pages retired) are
written when the build starts.

## Build contract (2026-11-23, "1a, 2a, 3a, build it"; spec 04 S96-S98, 01 S58/S65, D-04-PROFILE-WINDOW)

Buttons: Profile Settings and Scripts both open the one window at their
section; menu: Tools › Profile Settings… and Scripts… after Options; View
loses both.

- `qml/DialogProfileSettings.qml` (agent WINDOW): ApplicationWindow, title
  "Profile Settings", objectName "profileSettingsWindow", property
  `string section` ("general" | "vjoy" | "scripts"); left list like
  DialogOptions with items objectName "profileSettingsSection:<id>"; under
  the heading the open profile's name and "Saved with the profile (Save
  Profile)". Right pane: `ProfileSettingsGeneral.qml`, `ProfileSettingsVJoy.qml`
  (WINDOW, from today's ProfileSettings.qml, which goes) and
  `ScriptManager.qml` (agent SCRIPTS).
- `ScriptManager.qml` / `ScriptConfiguration.qml` (agent SCRIPTS): restyled
  with the shared pieces; the root fills its parent, no page title or Home
  button of its own; same models and objectNames for its controls.
- `qml/Main.qml`, `qml/main_commands.js` (agent SHELL): `openProfileSettings(section)`
  opens the one window (or raises it) at that section; commands
  `tools.profileSettings` ("Profile Settings…", window: true, "general") and
  `tools.scripts` ("Scripts…", window: true, "scripts") in Tools after
  Options; `view.settings` / `view.scripts` and the two main-window pages
  removed (no old ids kept); toolbar buttons after Options, objectNames
  "profileSettingsToolbarButton", "scriptsToolbarButton".
- Initial Values boxes keep `vjoyInitialValue:<vjoy id>:<axis>`.
- Help links become `open:tools.profileSettings` / `open:tools.scripts`
  (agent DOCS).

## Change (user, 2026-11-23: "1a, 2a, 3a, 4a, build it")

Two separate windows: Profile Settings (left list General / vJoy) and
Scripts (`qml/DialogScripts.qml`, title "Scripts", objectName
"scriptsWindow": script list on the left, the picked script's variables on
the right). `openScripts()` in Main.qml; `tools.scripts` runs it. The three
Scripts texts kept.
