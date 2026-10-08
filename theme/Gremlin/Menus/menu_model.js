// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.pragma library
.import "commands.js" as Commands

// Builds what a ContextMenu shows. A menu is
//   { kind, title, header, quick, sections }
// kind      the kind of thing clicked; the menu reopens the section last used
//           for it
// title     the bold first line (what was clicked); empty for none
// header    small buttons beside the title, e.g. Undo and Redo:
//           [{ label, enabled, run }]
// quick     the most used rows, always shown
// sections  collapsible groups of rows, one open at a time
//
// Rows (each builder returns null when the row has nothing to do here, and
// null rows and empty sections are dropped):
//   action  a command to run; closes the menu
//   toggle  on or off; the menu stays open
//   choice  a row of values as small buttons; the menu stays open
//   number  a value to type (optionally with ‹ › steps and a button)
//   entry   text to type, Enter applies it

function _clean(items) {
    return (items || []).filter(function(it) { return !!it })
}

function menu(kind, title, quick, sections, header) {
    return {
        kind: kind || "",
        title: title || "",
        header: _clean(header),
        quick: _clean(quick),
        sections: _clean(sections)
    }
}

// A collapsible group; null when none of its rows apply.
function section(key, title, items) {
    var rows = _clean(items)
    return rows.length ? { key: key, title: title, items: rows } : null
}

function _on(enabled) {
    return enabled === undefined ? true : !!enabled
}

// opts: danger (red text, for deletes), hint (shown on the right, e.g. a
// shortcut), keepOpen (the menu stays open after it runs).
function action(text, run, enabled, opts) {
    var o = opts || {}
    return {
        kind: "action", text: text, run: run, enabled: _on(enabled),
        danger: !!o.danger, hint: o.hint || "", keepOpen: !!o.keepOpen
    }
}

// A grey line that explains why nothing else is offered; never runs, and
// shown even where unavailable items are hidden.
function note(text) {
    return {
        kind: "action", text: text, run: function() {}, enabled: false,
        danger: false, hint: "", keepOpen: true, note: true
    }
}

function toggle(text, checked, run, enabled) {
    return { kind: "toggle", text: text, checked: !!checked, run: run, enabled: _on(enabled) }
}

// values and labels: the choices (labels default to the values). current: the
// chosen value, or a function(value) -> bool. set: function(value).
function pick(text, values, labels, current, set, enabled) {
    var opts = []
    for (var i = 0; i < values.length; i++) {
        var v = values[i]
        var on = typeof current === "function" ? !!current(v) : v === current
        opts.push({ value: v, text: labels ? labels[i] : String(v), checked: on })
    }
    return { kind: "choice", text: text, options: opts, run: set, enabled: _on(enabled) }
}

// opts: step (shows ‹ › buttons), go (a button that runs with the value, e.g.
// "Add"; without it Enter applies the typed value), integer, closeOnGo.
function number(text, value, min, max, suffix, set, enabled, opts) {
    var o = opts || {}
    return {
        kind: "number", text: text, value: value, min: min, max: max,
        suffix: suffix || "", run: set, enabled: _on(enabled),
        step: o.step || 0, go: o.go || "", integer: !!o.integer, closeOnGo: !!o.closeOnGo
    }
}

// Text to type; Enter runs it. opts: placeholder, keepOpen.
function entry(text, run, enabled, opts) {
    var o = opts || {}
    return {
        kind: "entry", text: text, run: run, enabled: _on(enabled),
        placeholder: o.placeholder || "", keepOpen: !!o.keepOpen
    }
}

// A program-wide command as a row, with its shortcut on the right; null when
// it is hidden now. text: a different name for this menu.
function command(id, text) {
    var c = Commands.get(id)
    if (!c || !Commands.isVisible(id))
        return null
    if (Commands.isCheckable(id))
        return toggle(text || c.text, Commands.isChecked(id), function() { Commands.trigger(id) }, Commands.isEnabled(id))
    return action(text || c.text, function() { Commands.trigger(id) }, Commands.isEnabled(id),
                  { hint: c.shortcut || "" })
}

// The section last opened for each kind of thing, for this session, shared
// by every context menu.
var _last = {}

function lastSection(kind) {
    return _last[kind] || ""
}

function rememberSection(kind, key) {
    _last[kind] = key
}
