// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// test_control_menu.py: each page's options for ControlMenu.standardMenu,
// exactly as in the SB-MENU contract. One block per page after its marker.

// == logical ==
        return ControlMenu.standardMenu(_root, {
            layout: _layout, kind: "logical", pageTitle: "Logical Device", manyNoun: "rows",
            addAction: function() { _openNewPane(_menuKey, _menuTitle) },
            quickBeforeHistory: function(st) { return [MenuModel.action("Assign Hardware", _assignHardware)] },
            rowItems: function(st) {
                return [MenuModel.action(st.many ? "Delete " + st.count + " rows" : "Delete", function() {
                    _askDeleteRows(_picked.length > 0 ? _picked.slice() : [_menuKey], _menuTitle)
                }, true, { danger: true })]
            },
            extraSections: function(st) {
                var add = function(label, what) {
                    return MenuModel.number(label, 1, 1, 180, "", function(n) { _addCounted(what, n) }, !st.locked,
                                            { step: 1, go: "Add", integer: true })
                }
                return [{ at: "afterGroup", section: MenuModel.section("add", "Add Inputs",
                          [add("Buttons", "button"), add("Axes", "axis"), add("Hats", "hat")]) }]
            }
        })

// == device-bindings ==
        return ControlMenu.standardMenu(_root, {
            layout: _layout, kind: "device-bindings",
            pageTitle: deviceName.length ? deviceName : "Device Bindings", manyNoun: "inputs",
            addAction: function() { addAction(_menuKey, _menuTitle) },
            quickEnd: function(st) { return [MenuModel.action("Module Setup…", function() { openModuleSetup() })] },
            rowItems: function(st) {
                return [!st.many && _layout.canDelete(_menuKey)
                    ? MenuModel.action("Delete actions…", function() { _askDeleteActions(_menuKey, _menuTitle) },
                                       true, { danger: true })
                    : null]
            }
        })

// == keyboard ==
        return ControlMenu.standardMenu(_root, {
            layout: _layout, kind: "keyboard", pageTitle: "Keyboard", manyNoun: "keys",
            picked: _tree.picked,
            addAction: function() { addAction(_menuKey, _menuTitle) },
            renameGroup: function() { _groupDialog.text = _groupName; _groupDialog.visible = true },
            clearName: function() { _layout.setUserName(_menuKey, "") },
            rowTitle: "Key", sortSystemLabel: "By Key Name",
            rowItems: function(st) {
                var doomed = _deletable()
                return [MenuModel.action(doomed.length > 1 ? "Delete " + doomed.length + " keys" : "Delete",
                                         function() { _askDelete(doomed, _menuTitle) }, doomed.length > 0,
                                         { danger: true })]
            },
            extraSections: function(st) {
                return [{ at: "afterGroup", section: MenuModel.section("add", "Add Inputs", [
                    MenuModel.action("Add Key… (press the key)", function() { Qt.callLater(_root.addKey) },
                                     !st.locked)]) }]
            }
        })

// == osc ==
        return ControlMenu.standardMenu(_root, {
            layout: _layout, kind: "osc", pageTitle: "OSC", manyNoun: "inputs", rowSingleOnly: true,
            addAction: function() { _openNewPane(_menuKey, _menuTitle) },
            quickAfterAdd: function(st) {
                return st.many ? [] : [MenuModel.action("Add Feedback", function() { addFeedback(_menuKey) })]
            },
            quickBeforeHistory: function(st) {
                var q = []
                if (!st.many)
                    q.push(MenuModel.action("Change Address…", function() { _askChangeAddress(_menuKey) }))
                q.push(MenuModel.action(st.many ? "Edit Settings of " + st.count + " Inputs…" : "Edit Settings…",
                                        function() { editSettings(_selectedKeys()) }))
                if (!st.many) {
                    q.push(MenuModel.action("Copy for Companion", function() { copyForCompanion(_menuKey) }))
                    if (_menuKey.indexOf(":axis:") >= 0)
                        q.push(MenuModel.number("Send Test Value", 0.5, -1, 1, "", function(v) {
                            sendTestValue(_menuKey, v) }, true, { step: 0.1, go: "Send" }))
                    else
                        q.push(MenuModel.action("Send Test Press", function() { sendTestPress(_menuKey) }))
                }
                return q
            },
            quickEnd: function(st) {
                return st.onEmpty ? [MenuModel.action("Feedback settings…", function() { openFeedbackSettings() })] : []
            },
            clearNameEnabled: function(st) { return _menuUser.length > 0 && !st.many },
            rowItems: function(st) {
                return [MenuModel.action(st.many ? "Delete " + st.count + " inputs…" : "Delete…", function() {
                    _askDeleteRows(_selectedKeys(), _menuTitle) }, true, { danger: true })]
            },
            sortSystemLabel: "By Address",
            extraSections: function(st) {
                return [
                    { at: "start", section: st.onRow && !st.many ? MenuModel.section("companion", "Companion feedback", [
                        MenuModel.action("Key text", function() { addCompanionFeedback(_menuKey, "text") }),
                        MenuModel.action("Key color", function() { addCompanionFeedback(_menuKey, "color") })]) : null },
                    { at: "afterGroup", section: st.locked ? null : MenuModel.section("add", "Add Inputs", [
                        MenuModel.action("Add…", function() { openAdd() }),
                        MenuModel.action("Import…", function() { openImport() }),
                        MenuModel.action("From TouchOSC Layout…", function() { openTouchOsc() }),
                        MenuModel.action("Listen", function() { listen() }),
                        MenuModel.action("Clear…", function() { askClear() }, _devices.rowCount() > 0,
                                         { danger: true })]) }
                ]
            }
        })
