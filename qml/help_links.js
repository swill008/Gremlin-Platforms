// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help links to the program (01 S139, D-01-HELP-LINKS): parsing, the list of
// commands an "Open ›" link may run, and greying the links that can't be
// shown now. Style.helpLinks (set by Main.qml) does the checking and showing.

.pragma library

// Commands (qml/main_commands.js) that only open a window or a page. Never
// anything that saves, loads, runs, deletes, clears, restores or quits.
var _allowedOpen = [
    "view.home", "view.configuration", "view.scripts", "view.settings",
    "tools.vjoyViewer", "tools.xboxViewer",
    "tools.calibration", "tools.hidhide", "tools.configureInput",
    "tools.configureOutput", "tools.deviceInfo", "tools.deviceLibrary",
    "tools.devicePack",
    "tools.logical", "tools.buttonMap", "tools.autoMapper", "tools.manageModes",
    "tools.history", "tools.options",
    "debug.liveLog",
    "help.about"
]

function allowedOpen() {
    return _allowedOpen.slice()
}

function isAllowedOpen(id) {
    return _allowedOpen.indexOf(String(id)) >= 0
}

// {kind, parts}: kind "topic" | "open" | "show" | "other"; parts are the
// pieces after the colon ("show:menu/File/Exit" -> ["menu", "File", "Exit"]).
function parse(link) {
    var s = String(link || "")
    var colon = s.indexOf(":")
    var scheme = colon > 0 ? s.substring(0, colon) : ""
    var rest = colon > 0 ? s.substring(colon + 1) : s
    if (scheme === "topic")
        return { kind: "topic", parts: [rest] }
    if (scheme === "open")
        return { kind: "open", parts: [rest] }
    if (scheme === "show")
        return { kind: "show", parts: rest.length ? rest.split("/") : [] }
    return { kind: "other", parts: [s] }
}

// An open: or show: link.
function isProgramLink(link) {
    var kind = parse(link).kind
    return kind === "open" || kind === "show"
}

var _anchor = /<a\b([^>]*)>([\s\S]*?)<\/a>/gi
var _href = /\bhref\s*=\s*"([^"]*)"/i

function _decode(s) {
    return String(s).replace(/&amp;/g, "&").replace(/&quot;/g, "\"")
                    .replace(/&lt;/g, "<").replace(/&gt;/g, ">")
}

// Every link's href in the HTML, in order.
function allLinks(html) {
    var out = []
    String(html || "").replace(_anchor, function(all, attrs) {
        var m = _href.exec(attrs)
        if (m)
            out.push(_decode(m[1]))
        return all
    })
    return out
}

// Only the open: and show: hrefs.
function programLinks(html) {
    return allLinks(html).filter(isProgramLink)
}

// The HTML with every link that has a reason in reasons ({href: reason})
// drawn in the given colour, not underlined. The text and the link stay, so
// hovering it shows why and clicking it says so.
function decorate(html, reasons, color) {
    if (!reasons)
        return String(html || "")
    return String(html || "").replace(_anchor, function(all, attrs, inner) {
        var m = _href.exec(attrs)
        if (!m || !reasons[_decode(m[1])])
            return all
        var style = "color:" + color + "; text-decoration:none"
        return "<a" + attrs + " style=\"" + style + "\"><span style=\"" + style + "\">"
            + inner + "</span></a>"
    })
}
