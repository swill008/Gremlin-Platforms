// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// 01 S140: the one question before every delete, remove or clear.
//
//   import "confirm.js" as Confirm
//   Confirm.ask(host, { title, text, undoable, note, action, onAccept, onCancel })
//
// host is any Item in the asking window (or the Window itself). One question
// at a time per window: asking while one is open there does nothing and
// returns null. Returns the open ConfirmDialog otherwise.
.pragma library

var _component = null
var _open = []  // [{ root: window's root item, dialog }]

function _rootItem(host) {
    if (!host)
        return null
    // A Window: its content item. (Since Qt 6.7 a Window declared inside
    // another object has a parent too, so test for a Window property an
    // Item doesn't have, not for a missing parent.)
    if (host.contentItem !== undefined && host.visibility !== undefined)
        return host.contentItem
    var item = host
    while (item.parent)
        item = item.parent
    return item
}

function isOpen(host) {
    var root = _rootItem(host)
    for (var i = 0; i < _open.length; ++i) {
        if (_open[i].root === root)
            return true
    }
    return false
}

function _forget(dialog) {
    for (var i = _open.length - 1; i >= 0; --i) {
        if (_open[i].dialog === dialog)
            _open.splice(i, 1)
    }
}

function ask(host, options) {
    var opts = options || {}
    var root = _rootItem(host)
    if (!root) {
        console.warn("Confirm.ask: no window to ask in")
        return null
    }
    if (isOpen(root))
        return null
    if (!_component)
        _component = Qt.createComponent(Qt.resolvedUrl("ConfirmDialog.qml"))
    if (_component.status !== 1) {  // Component.Ready
        console.warn("Confirm.ask: " + _component.errorString())
        return null
    }
    var dialog = _component.createObject(root, {
        titleText: String(opts.title || ""),
        bodyText: String(opts.text || ""),
        undoable: !!opts.undoable,
        note: String(opts.note || ""),
        actionText: String(opts.action || "")
    })
    if (!dialog)
        return null
    _open.push({ root: root, dialog: dialog })
    var finish = function(fn) {
        _forget(dialog)
        dialog.destroy()
        if (typeof fn === "function")
            fn()
    }
    dialog.confirmed.connect(function() { finish(opts.onAccept) })
    dialog.cancelled.connect(function() { finish(opts.onCancel) })
    dialog.open()
    return dialog
}
