// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help search (01 S137, D-01-GUIDE-SEARCH): pure functions over a list of
// topics ({title, body}); the Help window owns which topics are searched.

.pragma library

var _BLOCK = /^(br|p|div|li|ul|ol|h[1-6]|tr|td|th|table|hr|blockquote|pre|dt|dd)$/i

var _NAMED = { amp: "&", lt: "<", gt: ">", quot: "\"", apos: "'", nbsp: " ",
               rsaquo: "›", lsaquo: "‹", hellip: "…", mdash: "—", ndash: "–",
               middot: "·", times: "×", rarr: "→", larr: "←", copy: "©" }

// Lower-cased non-empty words of the text ([] for blank).
function words(text) {
    var trimmed = String(text === undefined || text === null ? "" : text).trim()
    if (trimmed === "")
        return []
    return trimmed.toLowerCase().split(/\s+/).filter(function (w) { return w !== "" })
}

function _entity(html, i) {
    // An entity at html[i] === "&": {text, end} or null.
    var m = /^&(#x[0-9a-f]+|#[0-9]+|[a-z][a-z0-9]*);/i.exec(html.substr(i, 12))
    if (!m)
        return null
    var name = m[1]
    var text = null
    if (name[0] === "#") {
        var code = name[1] === "x" || name[1] === "X"
            ? parseInt(name.substr(2), 16) : parseInt(name.substr(1), 10)
        if (code > 0 && code <= 0x10FFFF)
            text = String.fromCodePoint(code)
    } else if (_NAMED.hasOwnProperty(name.toLowerCase())) {
        text = _NAMED[name.toLowerCase()]
    }
    return text === null ? null : { text: text, end: i + m[0].length }
}

// The visible text of html, with each visible character's html range
// ({s, e}, or null for the space a block tag stands for).
function _scan(html) {
    html = String(html || "")
    var chars = []
    var ranges = []
    var i = 0
    while (i < html.length) {
        var c = html[i]
        if (c === "<") {
            var close = html.indexOf(">", i)
            if (close < 0)
                close = html.length - 1
            var name = /^<\/?\s*([a-z0-9]+)/i.exec(html.substring(i, close + 1))
            if (name && _BLOCK.test(name[1])) {
                chars.push(" ")
                ranges.push(null)
            }
            i = close + 1
        } else if (c === "&" && _entity(html, i)) {
            var ent = _entity(html, i)
            for (var k = 0; k < ent.text.length; ++k) {
                chars.push(ent.text[k])
                ranges.push({ s: i, e: ent.end })
            }
            i = ent.end
        } else {
            chars.push(c)
            ranges.push({ s: i, e: i + 1 })
            i += 1
        }
    }
    return { text: chars.join(""), ranges: ranges }
}

// The topic body's visible text (tags removed, entities decoded).
function plain(html) {
    return _scan(html).text
}

function _lower(text) {
    // Lower case keeping one character per character, so positions match.
    var out = ""
    for (var i = 0; i < text.length; ++i) {
        var l = text[i].toLowerCase()
        out += l.length === 1 ? l : text[i]
    }
    return out
}

// Matches [{start, end}] of any word in text, in order, never overlapping;
// [] unless every word occurs at least once in text.
function _matches(text, ws, requireAll) {
    var lower = _lower(text)
    var found = []
    for (var w = 0; w < ws.length; ++w) {
        var word = ws[w]
        var from = lower.indexOf(word)
        if (from < 0 && requireAll)
            return []
        while (from >= 0) {
            found.push({ start: from, end: from + word.length })
            from = lower.indexOf(word, from + word.length)
        }
    }
    found.sort(function (a, b) { return a.start - b.start || b.end - a.end })
    var kept = []
    var reach = -1
    for (var f = 0; f < found.length; ++f) {
        if (found[f].start >= reach) {
            kept.push(found[f])
            reach = found[f].end
        }
    }
    return kept
}

// Number of matches of any word in title + body when every word occurs at
// least once (title or body), else 0.
function countIn(topic, ws) {
    if (!topic || !ws || ws.length === 0)
        return 0
    var title = String(topic.title || "")
    var body = plain(topic.body)
    var both = _lower(title + " " + body)
    for (var w = 0; w < ws.length; ++w) {
        if (both.indexOf(ws[w]) < 0)
            return 0
    }
    return _matches(title, ws, false).length + _matches(body, ws, false).length
}

// [{index, count}] in topic order, topics with count > 0 only; [] for blank
// text, meaning no filter (show every topic).
function filter(topics, text) {
    var ws = words(text)
    var out = []
    if (ws.length === 0 || !topics)
        return out
    for (var i = 0; i < topics.length; ++i) {
        var n = countIn(topics[i], ws)
        if (n > 0)
            out.push({ index: i, count: n })
    }
    return out
}

function _escapeAttr(value) {
    return String(value).replace(/[^#0-9a-zA-Z(),.% ]/g, "")
}

// The body html with every match of the text's words wrapped in a coloured
// span, the current (0-based) one in currentColor. Spans never cut a tag or
// an entity; a match running across tags (e.g. into <b>) gets one span per
// piece but counts once. Returns {html, total}.
function highlight(html, text, current, matchColor, currentColor, textColor) {
    html = String(html || "")
    var ws = words(text)
    if (ws.length === 0)
        return { html: html, total: 0 }
    var scan = _scan(html)
    var found = _matches(scan.text, ws, false)
    var normal = _escapeAttr(matchColor || "yellow")
    var strong = _escapeAttr(currentColor || "orange")
    var fg = textColor ? ";color:" + _escapeAttr(textColor) : ""
    var inserts = []   // {pos, close, order, text}
    for (var m = 0; m < found.length; ++m) {
        var colour = m === current ? strong : normal
        var open = "<span style=\"background-color:" + colour + fg + "\">"
        var piece = null
        for (var c = found[m].start; c < found[m].end; ++c) {
            var r = scan.ranges[c]
            if (r === null)
                continue
            if (piece !== null && piece.e === r.s) {
                piece.e = r.e
            } else if (piece === null || piece.e !== r.e) {
                if (piece !== null) {
                    inserts.push({ pos: piece.s, close: false, text: open })
                    inserts.push({ pos: piece.e, close: true, text: "</span>" })
                }
                piece = { s: r.s, e: r.e }
            }
        }
        if (piece !== null) {
            inserts.push({ pos: piece.s, close: false, text: open })
            inserts.push({ pos: piece.e, close: true, text: "</span>" })
        }
    }
    // Stable order: by position, a close before an open at the same place.
    inserts.sort(function (a, b) {
        return a.pos - b.pos || (a.close === b.close ? 0 : (a.close ? -1 : 1))
    })
    var out = ""
    var at = 0
    for (var k = 0; k < inserts.length; ++k) {
        out += html.substring(at, inserts[k].pos) + inserts[k].text
        at = inserts[k].pos
    }
    out += html.substring(at)
    return { html: out, total: found.length }
}
