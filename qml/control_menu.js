// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.pragma library
.import Gremlin.Menus 1.0 as Menus
.import "helpers.js" as Helpers

// The right-click menus the four list pages share (Device Bindings, Logical
// Device, Keyboard, OSC). Each page passes itself and the bits only it has;
// the order, labels and enabled rules of the shared rows live here.
//
// standardMenu(page, opts): the menu for a row, a group or the empty list.
// Read from page: editorLocked, actionOpen, _menuOnRow, _menuOnGroup,
// _menuKey, _menuTitle, _menuUser, _groupName, _picked, displayOpen (set),
// and the handlers _renameRow, _renameGroup, _openHistory, _groupAs,
// _askDeleteGroup, _askClearName(key, title, user).
// opts:
//   layout            the page's layout model (undo/redo, groups, sorting)
//   kind              "logical": the menu kinds are kind, kind-row, kind-group
//   pageTitle         title on the empty list
//   manyNoun          "rows": the title for several picked rows ("3 rows")
//   addAction()       the Add Action row
//   picked            the picked keys, when the page has no _picked
//   renameGroup()     overrides page._renameGroup
//   clearName()       overrides page._askClearName(key, title, user)
//   clearNameEnabled(st)  default: the row has a name of the user's
//   rowSingleOnly     Add Action and Rename only for one row
//   quickAfterAdd(st)     rows after Add Action
//   quickBeforeHistory(st) rows after Rename, before History
//   quickEnd(st)      rows before Appearance…
//   rowTitle          the Row section's title (default "Row")
//   rowItems(st)      rows after Clear Name in the Row section
//   sortSystemLabel   "By System Name" / "By Key Name" / "By Address"
//   extraSections(st) [{ at, section }], at: "start", "afterRow",
//                     "afterGroup", "afterGroups", "end"
// A row (one picked) also gets Find uses… after History when the layout has
// findQuery(key) (ControlLayoutModel): Search filled in on that input.
// st (passed to the hooks): { locked, onRow, onGroup, onEmpty, many, count,
// keys } where onRow/onGroup are false while locked, onEmpty is the click
// on neither, and keys are the picked keys (or the clicked one).

function _M() {
    return Menus.MenuModel
}

function _call(fn, st) {
    if (!fn)
        return []
    var out = typeof fn === "function" ? fn(st) : fn
    return out || []
}

function state(page, opts) {
    var o = opts || {}
    var locked = !!page.editorLocked
    var picked = o.picked !== undefined ? o.picked : (page._picked || [])
    var count = picked.length
    return {
        locked: locked,
        onRow: !!page._menuOnRow && !locked,
        onGroup: !!page._menuOnGroup && !locked,
        onEmpty: !page._menuOnRow && !page._menuOnGroup,
        many: count > 1,
        count: count,
        keys: count > 0 ? picked.slice() : [page._menuKey]
    }
}

function standardMenu(page, opts) {
    var M = _M()
    var o = opts || {}
    var L = o.layout
    var st = state(page, o)
    var onRow = st.onRow, onGroup = st.onGroup, many = st.many, locked = st.locked
    var kind = onRow ? o.kind + "-row" : (onGroup ? o.kind + "-group" : o.kind)
    var title = onRow ? (many ? st.count + " " + o.manyNoun : page._menuTitle)
                      : (onGroup ? page._groupName : o.pageTitle)
    var header = locked ? [] : [
        { label: "Undo", enabled: L.canUndo && !page.actionOpen, run: function() { L.undo() } },
        { label: "Redo", enabled: L.canRedo && !page.actionOpen, run: function() { L.redo() } }
    ]

    var quick = []
    if (onRow) {
        var single = !o.rowSingleOnly || !many
        if (single)
            quick.push(M.action("Add Action", function() { o.addAction() }))
        quick = quick.concat(_call(o.quickAfterAdd, st))
        if (single)
            quick.push(M.action("Rename", function() { page._renameRow() }))
        quick = quick.concat(_call(o.quickBeforeHistory, st))
        if (!many)
            quick.push(M.action("History", function() { page._openHistory() }))
        if (!many && typeof L.findQuery === "function")
            quick.push(findUsesItem(_withTitle(L.findQuery(page._menuKey), page._menuTitle)))
    }
    if (onGroup)
        quick.push(M.action("Rename Group", function() {
            if (o.renameGroup) o.renameGroup()
            else page._renameGroup()
        }))
    quick = quick.concat(_call(o.quickEnd, st))
    quick.push(M.action("Appearance…", function() { page.displayOpen = true }))

    var moveTo = []
    if (onRow) {
        var groups = L.groups || []
        for (var i = 0; i < groups.length; i++) {
            (function(g) {
                moveTo.push(M.action("Move to " + g.title, function() {
                    // After the menu has closed; the move rebuilds the list.
                    Qt.callLater(function() { L.moveSelected(g.name) })
                }))
            })(groups[i])
        }
    }

    var extra = _call(o.extraSections, st)
    var at = function(where) {
        return extra.filter(function(e) { return e && e.at === where })
                    .map(function(e) { return e.section })
    }
    var clearOn = o.clearNameEnabled ? !!o.clearNameEnabled(st)
                                     : (page._menuUser || "").length > 0
    var sections = at("start")
    sections.push(onRow ? M.section("row", o.rowTitle || "Row", [
        M.action("Clear Name", function() {
            if (o.clearName) o.clearName()
            else page._askClearName(page._menuKey, page._menuTitle, page._menuUser)
        }, clearOn)
    ].concat(_call(o.rowItems, st))) : null)
    sections = sections.concat(at("afterRow"))
    sections.push(onRow ? M.section("group", "Group", [
        M.entry("Group as", function(name) { page._groupAs(name) }, true,
                { placeholder: "Name, then Enter" })
    ].concat(moveTo)) : null)
    sections = sections.concat(at("afterGroup"))
    sections.push(locked ? null : M.section("groups", "Groups", [
        M.entry("New Group", function(name) { L.addGroup(name) }, true,
                { placeholder: "Name, then Enter", keepOpen: true }),
        onGroup ? M.action("Move Group Up", function() { L.moveGroupUp(page._groupName) }) : null,
        onGroup ? M.action("Move Group Down", function() { L.moveGroupDown(page._groupName) }) : null,
        onGroup ? M.action("Delete Group", function() { page._askDeleteGroup(page._groupName) }, true,
                           { danger: true }) : null
    ]))
    sections = sections.concat(at("afterGroups"))
    sections.push(locked ? null : M.section("order", "Order", [
        M.action(o.sortSystemLabel || "By System Name", function() { L.sortBySystem() }),
        M.action("By Your Name", function() { L.sortByName() }),
        M.action("Group Names A to Z", function() { L.sortGroupNames() })
    ]))
    sections = sections.concat(at("end"))
    return M.menu(kind, title, quick, sections, header)
}

// The row's query with its title (the input's system name) for the text.
function _withTitle(query, title) {
    if (!query || !query.kind)
        return null
    var q = {}
    for (var k in query)
        q[k] = query[k]
    q.title = String(title || "")
    return q
}

// An action row's menu: Open and Delete. opts: kind ("logical" gives
// "logical-action"), title, open(), remove().
function actionMenu(opts) {
    var M = _M()
    return M.menu(opts.kind + "-action", opts.title, [
        M.action("Open", function() { opts.open() }),
        M.action("Delete", function() { opts.remove() }, true, { danger: true })
    ])
}

// Find uses… (Search, D-01-SEARCH-INDEX): opens the main window's Search
// with text in the box, e.g. 'vjoy:"1 button 2"' or 'mode:"Default"'. An
// old-style query dict is turned into that text (searchTextOf). False when
// there is no main window to ask.
function openSearch(textOrQuery) {
    var main = Helpers.mainWindow()
    if (!main || typeof main.openSearch !== "function")
        return false
    main.openSearch(searchTextOf(textOrQuery))
    return true
}

// gremlin.types.InputType by its word, as the list keys spell it.
var _INPUT_TYPE = { axis: 2, button: 3, hat: 4 }
var _TYPE_WORD = { 1: "key", 2: "axis", 3: "button", 4: "hat" }

function inputTypeOf(word) {
    return _INPUT_TYPE[String(word)] || 0
}

// A prefix's value in quotes (a quote inside is dropped).
function quoted(text) {
    return '"' + String(text).replace(/"/g, "") + '"'
}

function _words(parts) {
    return parts.filter(function(p) {
        return p !== null && p !== undefined && typeof p !== "object" && String(p).length > 0
    }).join(" ")
}

// The Search box text for textOrQuery: text as it is; an old-style query
// dict as prefix text: {kind: "mode", mode} -> mode:"<mode>", {kind:
// "action", actionTag} -> action:"<tag>", {kind: "output", output, outputId,
// inputType, inputId, outputKey} -> <output>:"<id> <type> <input>", {kind:
// "input", deviceGuid, inputType, inputId, title} -> device:"<name>" <input>
// (a key: key:"<title>"). The device's name comes from the main window's
// searchDeviceName(guid). "" for nothing.
function searchTextOf(textOrQuery) {
    var q = textOrQuery
    if (q === null || q === undefined)
        return ""
    if (typeof q === "string")
        return q
    var kind = String(q.kind || "")
    if (kind === "mode")
        return q.mode ? "mode:" + quoted(q.mode) : ""
    if (kind === "action")
        return q.actionTag ? "action:" + quoted(q.actionTag) : ""
    if (kind === "output") {
        var out = String(q.output || "")
        if (!out.length)
            return ""
        var value = (out === "osc" || out === "mouse")
            ? _words([q.outputKey, q.inputId])
            : _words([q.outputId, _TYPE_WORD[Number(q.inputType)], q.inputId])
        return value.length ? out + ":" + quoted(value) : out + ":"
    }
    if (kind === "input") {
        var type = Number(q.inputType)
        var title = String(q.title || "")
        if (type === 1 && title.length)
            return "key:" + quoted(title)
        var main = Helpers.mainWindow()
        var name = (main && typeof main.searchDeviceName === "function")
            ? String(main.searchDeviceName(String(q.deviceGuid || "")) || "") : ""
        var what = title.length ? title : _words([_TYPE_WORD[type], q.inputId])
        return _words([name.length ? "device:" + quoted(name) : "", what])
    }
    return ""
}

// The Find uses… row; off without something to search for.
function findUsesItem(textOrQuery) {
    var text = searchTextOf(textOrQuery)
    return _M().action("Find uses…", function() { openSearch(text) }, text.length > 0)
}

// A menu of only Find uses…, for the views without a row menu of their own
// (vJoy Viewer chips, Xbox Output View rows, Manage Modes).
function findUsesMenu(kind, title, query) {
    return _M().menu(kind, title, [findUsesItem(query)])
}
