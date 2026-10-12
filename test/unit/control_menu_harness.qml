// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// test_control_menu.py: a stand-in list page. newMenu() gets the page's
// menu builder (control_menu_pages.js), oldMenu() (capture only) a page's
// old _layoutMenuModel body.
import QtQuick
import Gremlin.Menus
import "control_menu.js" as ControlMenu

Item {
    id: _root
    property bool editorLocked: false
    property bool actionOpen: false
    property bool displayOpen: false
    property string _menuKey: "dev:button:1"
    property string _menuTitle: "Button 1"
    property string _menuUser: "Fire"
    property string _groupName: "Weapons"
    property bool _menuOnRow: false
    property bool _menuOnGroup: false
    property var _picked: []
    property string deviceName: ""
    property string _actionTitle: "Remap"
    property var calls: []

    QtObject {
        id: _layout
        property bool canUndo: true
        property bool canRedo: false
        property bool canDel: true
        property var groups: [{ name: "g1", title: "Weapons" }, { name: "g2", title: "Flight" }]
        function canDelete(k) { return canDel }
        function undo() { _root.log("undo") }
        function redo() { _root.log("redo") }
        function addGroup(n) { _root.log("addGroup " + n) }
        function moveGroupUp(n) { _root.log("up " + n) }
        function moveGroupDown(n) { _root.log("down " + n) }
        function moveSelected(n) { _root.log("move " + n) }
        function sortBySystem() { _root.log("sortSystem") }
        function sortByName() { _root.log("sortName") }
        function sortGroupNames() { _root.log("sortGroups") }
        function setUserName(k, v) { _root.log("setUserName " + k + "=" + v) }
        function findQuery(k) { return { kind: "input", deviceGuid: "dev", inputType: 3, inputId: k } }
    }
    QtObject { id: _tree; property var picked: [] }
    QtObject { id: _devices; function rowCount() { return 2 } }
    QtObject { id: _groupDialog; property string text: ""; property bool visible: false }

    function log(s) { var c = calls.slice(); c.push(s); calls = c }
    function _deletable() {
        var keys = _tree.picked.length > 0 ? _tree.picked.slice() : [_menuKey]
        return keys.filter(function(k) { return _layout.canDelete(k) })
    }
    function _selectedKeys() { return _picked.length > 0 ? _picked.slice() : [_menuKey] }
    function _openNewPane(k, t) { log("newPane " + k) }
    function addAction(k, t) { log("addAction " + k) }
    function _assignHardware() { log("assign") }
    function _renameRow() { log("renameRow") }
    function _renameGroup() { log("renameGroup") }
    function _openHistory() { log("history") }
    function _groupAs(n) { log("groupAs " + n) }
    function _askDeleteGroup(n) { log("deleteGroup " + n) }
    function _askClearName(k, t, u) { log("clearName " + k + " " + t + " " + u) }
    function _askDeleteRows(keys, t) { log("deleteRows " + keys.join(",")) }
    function _addCounted(w, n) { log("add " + w + " " + n) }
    function openModuleSetup() { log("moduleSetup") }
    function _askDeleteActions(k, t) { log("deleteActions " + k) }
    function _askDelete(keys, t) { log("deleteKeys " + keys.join(",")) }
    function addKey() { log("addKey") }
    function addFeedback(k) { log("addFeedback " + k) }
    function _askChangeAddress(k) { log("changeAddress " + k) }
    function editSettings(keys) { log("editSettings " + keys.join(",")) }
    function copyForCompanion(k) { log("copy " + k) }
    function sendTestValue(k, v) { log("testValue " + k) }
    function sendTestPress(k) { log("testPress " + k) }
    function openFeedbackSettings() { log("feedbackSettings") }
    function addCompanionFeedback(k, w) { log("companion " + w) }
    function openAdd() { log("openAdd") }
    function openImport() { log("openImport") }
    function openTouchOsc() { log("touchOsc") }
    function listen() { log("listen") }
    function askClear() { log("askClear") }
    function _openPane(p, s, t) { log("openPane " + p + " " + s) }
    function openAction(p, s, t) { log("openAction " + p + " " + s) }
    function deleteActionAsked(p, s, t) { log("deleteAction " + p + " " + s) }
    function _askDeleteAction(p, s, t) { log("deleteAction " + p + " " + s) }

    function oldMenu() {
%OLD%
    }

    function newMenu() {
%NEW%
    }

    // A menu as plain text rows, for comparing.
    function dump(m) {
        function row(it) {
            var s = it.kind + "|" + it.text + "|" + (it.enabled ? "on" : "off")
            if (it.danger) s += "|danger"
            if (it.kind === "number")
                s += "|" + [it.value, it.min, it.max, it.step, it.go, it.integer].join(",")
            if (it.kind === "entry")
                s += "|" + it.placeholder + (it.keepOpen ? "|keepOpen" : "")
            return s
        }
        return JSON.stringify({
            kind: m.kind, title: m.title,
            header: m.header.map(function(h) { return h.label + "|" + (h.enabled ? "on" : "off") }),
            quick: m.quick.map(row),
            sections: m.sections.map(function(s) {
                return [s.key + "|" + s.title].concat(s.items.map(row))
            })
        })
    }

    function reset() {
        editorLocked = false; actionOpen = false; displayOpen = false
        _menuKey = "dev:button:1"; _menuUser = "Fire"
        _menuOnRow = false; _menuOnGroup = false
        _layout.canDel = true; _picked = []; _tree.picked = []; calls = []
        _groupDialog.visible = false
    }

    function setPicked(keys) { _picked = keys; _tree.picked = keys }

    function find(m, t) {
        var all = m.quick
        for (var s = 0; s < m.sections.length; s++)
            all = all.concat(m.sections[s].items)
        return all.filter(function(it) { return it.text === t })[0]
    }

    // Runs rows of the group and row menus; returns what the page was asked.
    function runRows() {
        reset()
        _menuOnGroup = true
        var m = newMenu()
        var names = ["Appearance…", "Delete Group", "Move Group Up", "By Your Name", "Rename Group"]
        names.forEach(function(t) { find(m, t).run() })
        m.header[0].run()
        _menuOnGroup = false
        _menuOnRow = true
        m = newMenu()
        find(m, "Clear Name").run()
        find(m, "Group as").run("Guns")
        return JSON.stringify({ calls: calls, displayOpen: displayOpen,
                                groupDialog: _groupDialog.visible })
    }

    function actionDump(kind) {
        var m = ControlMenu.actionMenu({ kind: kind, title: _actionTitle,
            open: function() { log("open") }, remove: function() { log("remove") } })
        calls = []
        m.quick[0].run()
        m.quick[1].run()
        return JSON.stringify({ menu: JSON.parse(dump(m)), calls: calls })
    }
}
