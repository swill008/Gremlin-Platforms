// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.import "window_registry.js" as Registry

// One list for the whole program (each file that imports this script gets
// its own copy of it), so the Button Map's Options is the main window's.
var _openWindows = Registry.openWindows

function _applyProps(window, properties)
{
    if (!window || !properties)
        return
    for (var k in properties) {
        if (properties.hasOwnProperty(k))
            window[k] = properties[k]
    }
}

function createComponent(componentSpec, properties)
{
    let existing = _openWindows[componentSpec]
    if (existing) {
        _applyProps(existing, properties)
        existing.show()
        existing.raise()
        existing.requestActivate()
        return existing
    }

    let component = Qt.createComponent(componentSpec);
    // 3 = Component.Error, 1 = Component.Ready (QML types aren't visible in a
    // script that imports another script).
    if(component.status == 3) {
        console.log(component.errorString())
        return null
    }
    else if(component.status == 1)
    {
        // Keep a JS reference so axis-event churn cannot GC the window.
        // Parent null + transientParent null: stays up if the main window is minimized.
        var init = {"x": 100, "y": 300}
        _applyProps(init, properties)
        let window = component.createObject(null, init);
        if (!window)
            return null
        window.transientParent = null
        // Runs after the window's own onClosing. A window that kept itself open to
        // ask about unsaved work (close.accepted = false) must not be destroyed.
        window.closing.connect(function(close) {
            if (close && !close.accepted)
                return
            if (_openWindows[componentSpec] === window) {
                delete _openWindows[componentSpec]
            }
            Qt.callLater(function() { window.destroy() })
        })
        _openWindows[componentSpec] = window
        window.show();
        return window
    }
    return null
}

function toggleComponent(componentSpec)
{
    let existing = _openWindows[componentSpec]
    if (existing) {
        existing.close()
        return
    }
    createComponent(componentSpec)
}

function windowOf(componentSpec)
{
    return _openWindows[componentSpec] || null
}

// The main window (Main.qml registers itself at start).
function setMainWindow(window)
{
    _openWindows["Main.qml"] = window || null
}

function mainWindow()
{
    return _openWindows["Main.qml"] || null
}

// For tool windows that change bindings behind an open action pane
// (Auto Mapper Create, History Restore, Device Pack import): closes the
// panes first (asking when one has changes), then calls then(). Cancel
// there means then() is not called.
function closeActionPanes(then)
{
    var main = mainWindow()
    if (main && typeof main.closeActionPanes === "function") {
        main.closeActionPanes(then)
        return
    }
    if (typeof then === "function")
        then()
}

function capitalize(value)
{
    return value.replace(/\b\w/g, l => l.toUpperCase())
}

function selectText(value, text1, text2)
{
    return value ? text1 : text2
}

function safeText(text, backup)
{
    return !text ? backup : text
}

function fileDialogUrl(dialog)
{
    if (!dialog)
        return ""
    var src = ""
    try {
        if (dialog.selectedFile)
            src = dialog.selectedFile.toString ? dialog.selectedFile.toString() : ("" + dialog.selectedFile)
    } catch (e) {}
    if ((!src || !src.length) && dialog.selectedFiles && dialog.selectedFiles.length) {
        var first = dialog.selectedFiles[0]
        src = first && first.toString ? first.toString() : ("" + first)
    }
    if (!src || !src.length) {
        var cur = dialog.currentFile
        src = cur && cur.toString ? cur.toString() : (cur || "")
    }
    return src || ""
}

function hintIcon(type) {
    switch(type) {
        case 1:
            return "\uF433";
        case 2:
            return "\uF33B";
        case 3:
            return "\uF337";
        default:
            return "\uF505";
    }
}

function hintColor(type) {
    switch(type) {
        case 1:
            return "#3E65FF";
        case 2:
            return "#F0A30A";
        case 3:
            return "#A20025";
        default:
            return "#74008b";
    }
}

function determineHintIcon(userFeedback) {
    let highestSeverity = 0;
    for (let i = 0; i < userFeedback.length; i++) {
        if (userFeedback[i]["type"] > highestSeverity) {
            highestSeverity = userFeedback[i]["type"];
        }
    }
    return hintIcon(highestSeverity)
}

function determineHintColor(userFeedback) {
    let highestSeverity = 0;
    for (let i = 0; i < userFeedback.length; i++) {
        if (userFeedback[i]["type"] > highestSeverity) {
            highestSeverity = userFeedback[i]["type"];
        }
    }
    return hintColor(highestSeverity)
}

// A saved colour equal to a page's old fixed (dark) default was never
// changed by the user, so it follows Dark mode like a colour never set.
// Each page passes its own old default: they differed per page.
function userColour(saved, oldDefault) {
    var text = String(saved || "")
    return text.toLowerCase() === String(oldDefault).toLowerCase() ? "" : text
}
