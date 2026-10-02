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
