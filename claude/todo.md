# To do

Work that is known and parked. Each item names its tracker ref (UI issues
tracker) so the details stay in one place.

## Next up (added 2026-10-03)

- [ ] **Hidden Cards in the Home menu, no window.** Remove the Hidden Cards
  window (`qml/DialogHiddenDevices.qml`) and View → Hidden Cards…
  (`qml/main_commands.js` `view.hidden`). In the Home right-click menu
  (`qml/StatusPage.qml`, next to Unhide All Cards), make **Hidden Cards** a
  submenu that slides out and lists each hidden card by name; clicking one
  unhides it. Nothing hidden: the submenu shows "No hidden cards" (disabled).
  Unhide All Cards stays. Update help (`qml/help_topics.js`: Home topics and
  the "Not on Home" troubleshooting line) and keep the glossary words (Hide
  Card / Hidden Cards).

## OSC (parked 2026-10-02: leave OSC alone for now)

- [ ] **B15 – Default ports clash and disagree.** The program listens on 8000
  when nothing is set (`gremlin/osc.py` `DEFAULT_PORT`), Options shows 8001
  (`gremlin/ui/osc_option.py` `OscInputHostModel.port_default`), and output
  also defaults to 8000 (`DEFAULT_OUTPUT_PORT`). Suggested: input 8000,
  output 9000 (the usual OSC convention), one constant used everywhere.
- [ ] **B16 – OSC Add has controls that do nothing.** "Change" is saved as
  Axis; "message vs data" and "Trigger on message" with its delay are never
  passed on (`qml/OscAddDialog.qml`, `qml/OscDevice.qml` only sends the
  address and Button/Axis). The backend has no per-input settings for these;
  auto-release and its delay exist only as global options. Choose: build
  per-input support, or hide the controls until it exists.
- [ ] **B17 – OSC import promises change and encoder types.** Import turns
  C and E suffixes into plain axes (`gremlin/ui/osc_device_model.py`
  `_parse_import_line`), while `qml/OscImportDialog.qml` says otherwise.
  Goes with B16: real types, or fix the text.
