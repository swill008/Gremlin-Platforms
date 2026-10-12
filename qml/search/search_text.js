// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Text helpers for the Search window's parts: matched characters lit,
// model fields read by name.
.pragma library

function escape(text) {
    return String(text === undefined || text === null ? "" : text)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

// text as rich text with the spans ([start, end) pairs) lit in colour.
function highlight(text, spans, colour, ink) {
    var s = String(text === undefined || text === null ? "" : text)
    if (!spans || !spans.length)
        return escape(s)
    var sorted = spans.slice().map(function(p) {
        return [Math.max(0, Number(p[0])), Math.min(s.length, Number(p[1]))]
    }).sort(function(a, b) { return a[0] - b[0] })
    var out = ""
    var at = 0
    for (var i = 0; i < sorted.length; i++) {
        var a = Math.max(at, sorted[i][0])
        var b = sorted[i][1]
        if (b <= a)
            continue
        out += escape(s.substring(at, a))
        out += "<span style=\"background-color:" + colour + "; color:" + ink + "\">"
            + escape(s.substring(a, b)) + "</span>"
        at = b
    }
    return out + escape(s.substring(at))
}

// A SearchModel role name (camelCase) as its SearchRow field name.
function snake(name) {
    return name.replace(/[A-Z]/g, function(c) { return "_" + c.toLowerCase() })
}

// A field of a model row or dict (the model's camelCase role names).
function field(row, name, fallback) {
    if (!row)
        return fallback
    var v = row[name]
    return v === undefined || v === null ? fallback : v
}

// The spans of one field in a row's highlights ({field: [[start, end], …]}).
function spans(row, name) {
    var h = field(row, "highlights", null)
    return h ? (h[name] || []) : []
}
