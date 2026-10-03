// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.pragma library

// What kind of action each is. The action's right-click menu adds actions
// under these headings, and Options → Actions → Add Action Menu lists them
// the same way, so the two always agree. An action not listed here (a new
// one) is "other".
var kinds = {
    "Map to vJoy": "map", "Map to Xbox": "map", "Map to Keyboard": "map",
    "Map to Mouse": "map", "Map to Logical Device": "map",
    "Response Curve": "axis", "Axis Delta": "axis", "Dual Axis Deadzone": "axis",
    "Merge Axis": "axis", "Split Axis": "axis", "Hat as Buttons": "axis",
    "Condition": "logic", "Chain": "logic", "Double Tap": "logic", "Tempo": "logic",
    "Smart Toggle": "logic", "Macro": "logic", "Change Mode": "logic", "Reference": "logic"
}

// The headings, in order.
var order = ["map", "axis", "logic", "other"]
var titles = { "map": "Map to", "axis": "Axis and Hat", "logic": "Logic and Timing", "other": "Other" }

// Not an action anyone adds (the top of every binding).
var internal = { "Root": true }

function kindOf(name) {
    return kinds[name] || "other"
}
