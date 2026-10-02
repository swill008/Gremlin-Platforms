// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.pragma library

// Every program-wide command, defined once: its name, shortcut, where it sits
// in the menus and when it can be used. The menu bar, the shortcuts and the
// command palette are all built from this list, so a command is available in
// all of them or in none.
//
// A command:
//   id        unique, e.g. "file.save"
//   text      what menus and the palette show
//   group     the palette's grouping, e.g. "File" (usually the menu's name)
//   shortcut  optional key sequence, e.g. "Ctrl+S"; shown in menus
//   keywords  optional extra words the palette matches
//   run       function()
//   enabled   optional function() -> bool (default: always)
//   visible   optional function() -> bool (default: always)
//   checked   optional function() -> bool, for on/off commands
//   palette   false keeps it out of the palette (default: listed)
//   owner     who defined it, so a closing page can take its commands away

var _order = []
var _byId = {}

function define(spec) {
    if (!spec || !spec.id)
        return
    if (!_byId[spec.id])
        _order.push(spec.id)
    _byId[spec.id] = spec
}

// Defines a list of commands for one owner (a window or a page).
function defineAll(specs, owner) {
    for (var i = 0; i < specs.length; i++) {
        var s = specs[i]
        if (owner !== undefined)
            s.owner = owner
        define(s)
    }
}

// Takes away every command an owner defined.
function removeOwner(owner) {
    var keep = []
    for (var i = 0; i < _order.length; i++) {
        var c = _byId[_order[i]]
        if (c && c.owner === owner)
            delete _byId[_order[i]]
        else
            keep.push(_order[i])
    }
    _order = keep
}

function clear() {
    _order = []
    _byId = {}
}

function get(id) {
    return _byId[id] || null
}

function all() {
    var out = []
    for (var i = 0; i < _order.length; i++)
        out.push(_byId[_order[i]])
    return out
}

function _call(fn, fallback) {
    if (typeof fn !== "function")
        return fallback
    try {
        return !!fn()
    } catch (e) {
        return false
    }
}

function isVisible(id) {
    var c = get(id)
    return !!c && _call(c.visible, true)
}

function isEnabled(id) {
    var c = get(id)
    return !!c && _call(c.enabled, true)
}

// Shown and usable now: what menus show and the palette lists.
function isAvailable(id) {
    return isVisible(id) && isEnabled(id)
}

function isChecked(id) {
    var c = get(id)
    return !!c && _call(c.checked, false)
}

function isCheckable(id) {
    var c = get(id)
    return !!c && typeof c.checked === "function"
}

function textOf(id) {
    var c = get(id)
    return c ? c.text : ""
}

function shortcutOf(id) {
    var c = get(id)
    return c && c.shortcut ? c.shortcut : ""
}

// Runs a command if it can be used now. Returns whether it ran.
function trigger(id) {
    var c = get(id)
    if (!c || !isAvailable(id))
        return false
    c.run()
    return true
}

// Commands that have a shortcut, for the window to bind.
function withShortcuts() {
    return all().filter(function(c) { return !!c.shortcut })
}

// How well a command matches what was typed: every word must appear in its
// name, group or keywords; a match at the start of the name ranks first.
function _score(c, words) {
    var name = String(c.text).toLowerCase()
    var hay = (name + " " + String(c.group || "") + " " + String(c.keywords || "")).toLowerCase()
    var score = 0
    for (var i = 0; i < words.length; i++) {
        var at = hay.indexOf(words[i])
        if (at < 0)
            return -1
        if (name.indexOf(words[i]) === 0)
            score += 3
        else if (name.indexOf(" " + words[i]) >= 0 || name.indexOf(words[i]) >= 0)
            score += 2
        else
            score += 1
    }
    return score
}

// The palette's list: available commands matching the text, best first;
// everything (in menu order) when the text is empty. owners: only the
// commands of these owners (a window's own), or all when empty.
function search(text, owners) {
    var words = String(text || "").toLowerCase().split(/\s+/).filter(Boolean)
    var out = []
    var list = all()
    for (var i = 0; i < list.length; i++) {
        var c = list[i]
        if (c.palette === false || !isAvailable(c.id))
            continue
        if (owners && owners.length && owners.indexOf(c.owner) < 0)
            continue
        var s = words.length ? _score(c, words) : 0
        if (s >= 0)
            out.push({ cmd: c, score: s, at: i })
    }
    out.sort(function(a, b) { return b.score - a.score || a.at - b.at })
    return out.map(function(r) { return r.cmd })
}

// Commands for every row of a menu (and its submenus) that is not already a
// command: a window with its own menus lists them in the palette this way.
// The commands hold the rows, so the window takes them away again
// (removeOwner) when the palette closes and when it closes itself.
function defineFromMenu(menu, owner, path) {
    if (!menu)
        return
    if (typeof menu.beforeShow === "function")
        menu.beforeShow()
    for (var i = 0; i < menu.count; i++) {
        var item = menu.itemAt(i)
        // Separators have no text.
        if (!item || item.text === undefined || !String(item.text).length)
            continue
        if (item.subMenu) {
            defineFromMenu(item.subMenu, owner, path.concat([item.text]))
            continue
        }
        if ((item.command && item.command.length) || item.inPalette === false)
            continue
        _defineRow(item, owner, path, i)
    }
}

function _defineRow(item, owner, path, at) {
    var group = path.join(" › ")
    define({
        id: owner + ":" + group + "/" + at + "/" + item.text,
        text: String(item.text),
        group: group,
        shortcut: item.hint || "",
        owner: owner,
        enabled: function() { return item.enabled },
        visible: function() { return item.shown !== false },
        checked: item.checkable ? function() { return item.checked } : undefined,
        run: function() {
            // As a click does: a check row flips before it reports.
            if (item.checkable)
                item.toggle()
            item.triggered()
        }
    })
}

// The same for each menu of a menu bar.
function defineFromMenuBar(bar, owner) {
    for (var i = 0; bar && i < bar.count; i++) {
        var menu = bar.menuAt(i)
        if (menu && menu.enabled)
            defineFromMenu(menu, owner, [menu.title])
    }
}

// How many commands an owner has (tests: a closed window leaves none).
function countOwner(owner) {
    var n = 0
    for (var i = 0; i < _order.length; i++) {
        if (_byId[_order[i]].owner === owner)
            n++
    }
    return n
}
