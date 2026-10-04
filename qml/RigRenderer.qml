// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Window
import Gremlin.Style

// Every print and export of the Button Map, and Print & Export's preview,
// is drawn by this hidden copy of the map, never by the map on screen. The
// copy is made only while a picture is taken, outside the window, at the
// picture's own size: lines and text are drawn at that size, not enlarged,
// and the print area is all it holds, so nothing is cut out afterwards (on
// a screen scaled past 100% that cut used to miss part of the area). The
// map on screen keeps its zoom and its editing marks the whole time.
//
// Jobs wait their turn: a preview waits behind an export. A job is
//   { snap: snapshot(editor), pixels: { w, h }, light: bool,
//     pages: [{ labels, textMode, title }],
//     onPage: function(index, grabResult or null), onDone: function() }
Item {
    id: _r

    // Out of sight, left of the window.
    x: -width - 10000
    y: 0
    width: 1
    height: 1

    property var _queue: []
    property var _job: null
    readonly property bool busy: _job !== null
    // Longest side of the copy, in device pixels: its canvases are this big
    // at most (past it the picture is enlarged to the size asked for).
    readonly property int maxSide: 8192
    readonly property real dpr: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1

    // What a picture is drawn from, taken when it is asked for: later
    // changes on screen don't reach a job already waiting.
    function snapshot(e) {
        var f = e ? e.face : null
        var keys = ["photoScale", "photoOffX", "photoOffY", "photoRot", "photoHidden", "photoFade",
                    "photoBright", "photoContrast", "photoGrey", "photoLookUrl", "chipTextMode",
                    "actionLabels", "unboundText", "savedStyles", "printArea"]
        var props = {}
        for (var i = 0; e && i < keys.length; i++)
            props[keys[i]] = e[keys[i]]
        return {
            nodes: JSON.stringify(e ? (e.nodes || []) : []),
            props: props,
            photo: f ? String(f.photoOverride || "") : "",
            dest: f ? { btn: f.destBtn, axis: f.destAxis, hat: f.destHat } : null,
            chipRows: f ? f.chipRows : [],
            w: e ? e.width : 1,
            h: e ? e.height : 1,
            area: e ? e.printAreaRect() : { x: 0, y: 0, w: 1, h: 1 }
        }
    }

    function enqueue(job) {
        var q = _queue.slice()
        // Only the latest preview is worth drawing.
        if (job.preview)
            q = q.filter(function(j) { return !j.preview })
        q.push(job)
        // Exports first.
        q.sort(function(a, b) { return (a.preview ? 1 : 0) - (b.preview ? 1 : 0) })
        _queue = q
        Qt.callLater(_next)
    }

    function _next() {
        if (_job || !_queue.length)
            return
        var q = _queue.slice()
        var j = q.shift()
        _queue = q
        var s = j.snap
        // The picture's size on screen units: grabbed at the screen's scale,
        // it comes back at the pixels asked for.
        j.L = { w: Math.max(1, j.pixels.w / dpr), h: Math.max(1, j.pixels.h / dpr) }
        var k = j.L.w / Math.max(1, s.area.w)
        var cap = maxSide / dpr / Math.max(1, s.w, s.h)
        j.k = Math.max(0.05, Math.min(k, cap))
        j.i = 0
        j.state = "load"
        j.ticks = 0
        _job = j
        _faceLoader.active = true
    }

    function _editor() {
        return _faceLoader.item ? _faceLoader.item.editorItem : null
    }

    function _setUp() {
        var j = _job
        var f = _faceLoader.item
        if (!j || !f)
            return
        var s = j.snap
        f.width = s.w * j.k
        f.height = s.h * j.k
        if (s.dest) {
            f.destBtn = s.dest.btn
            f.destAxis = s.dest.axis
            f.destHat = s.dest.hat
            f.destTick++
        }
        f.chipRows = s.chipRows
        f.photoOverride = s.photo
        f.editorNodes = JSON.parse(s.nodes)
    }

    // Once the editor is there: the map's look, then the print area as this
    // item's own size.
    function _applyEditor(e) {
        var j = _job
        e.exportZoom = j.k
        e.exporting = true
        e.printLight = !!j.light
        var p = j.snap.props
        for (var key in p)
            e[key] = p[key]
        var f = _faceLoader.item
        var r = e.printAreaRect()
        width = Math.max(1, r.w)
        height = Math.max(1, r.h)
        f.x = -r.x
        f.y = -r.y
        j.applied = true
    }

    // Nothing still loading: the photo, pictures on the map.
    function _loading(item) {
        if (!item || !item.visible)
            return false
        if (item.status === Image.Loading && item.sourceSize !== undefined)
            return true
        var kids = item.children
        for (var i = 0; i < kids.length; i++) {
            if (_loading(kids[i]))
                return true
        }
        return false
    }

    function _showPage() {
        var j = _job
        var e = _editor()
        var p = j.pages[j.i] || {}
        if (p.labels !== undefined && p.labels !== null)
            e.actionLabels = p.labels
        if (p.textMode)
            e.chipTextMode = p.textMode
        e.exportTitle = p.title || ""
        e.bump()
        e.repaint()
        j.state = "settle"
        j.ticks = 0
    }

    function _grab() {
        var j = _job
        j.state = "grab"
        var ok = _r.grabToImage(function(result) {
            _r._pageDone(result)
        }, Qt.size(Math.max(1, Math.round(j.L.w)), Math.max(1, Math.round(j.L.h))))
        if (!ok)
            _pageDone(null)
    }

    function _pageDone(result) {
        var j = _job
        if (!j)
            return
        if (j.onPage)
            j.onPage(j.i, result)
        j.i++
        if (j.i < j.pages.length) {
            _showPage()
            return
        }
        _finish()
    }

    function _finish() {
        var j = _job
        _faceLoader.active = false
        width = 1
        height = 1
        _job = null
        if (j && j.onDone)
            j.onDone()
        Qt.callLater(_next)
    }

    Rectangle {
        anchors.fill: parent
        visible: _r.busy
        color: (_r._job && _r._job.light) ? Style.paper : Style.background
    }

    Loader {
        id: _faceLoader
        active: false
        sourceComponent: Component {
            VkbRigFace {
                host: null
                editing: false
                zoom: 1
                panX: 0
                panY: 0
                rulersOn: false
            }
        }
        onLoaded: _r._setUp()
    }

    // Waits for the copy to be ready (its chips placed, the photo and
    // pictures loaded), then a few frames for its canvases, then grabs.
    Timer {
        interval: 40
        repeat: true
        running: _r.busy
        onTriggered: {
            var j = _r._job
            var e = _r._editor()
            if (!j || !e)
                return
            j.ticks++
            if (j.state === "load") {
                if (!j.applied) {
                    _r._applyEditor(e)
                    return
                }
                // Ready, or given up waiting (a photo that never loads).
                if ((e.seeded && !_r._loading(_faceLoader.item)) || j.ticks > 200)
                    _r._showPage()
            } else if (j.state === "settle") {
                if (j.ticks >= 3 && !_r._loading(_faceLoader.item))
                    _r._grab()
                else if (j.ticks > 200)
                    _r._grab()
            }
        }
    }
}
