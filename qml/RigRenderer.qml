// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Window
import Gremlin.Style

// Every print and export of the device map, and Print & Export's preview,
// is drawn by this hidden copy of the map, never by the map on screen. The
// copy is made only while a picture is taken, outside the window, at the
// picture's own size: lines and text are drawn at that size, not enlarged,
// and the print area is all it holds, so nothing is cut out afterwards (on
// a screen scaled past 100% that cut used to miss part of the area). The
// map on screen keeps its zoom and its editing marks the whole time.
//
// Both planes print at full strength, background underneath (07 S87,
// S123): the copy starts in Foreground mode with the background shown and
// the foreground at full strength, whatever the screen's view settings.
//
// Jobs wait their turn: a preview waits behind an export. A job is
//   { snap: snapshot(editor, whole), pixels: { w, h }, light: bool,
//     includeBg: bool (absent: true; false leaves the background out),
//     preview: "" or its kind, onPicture: function(grabResult or null) }
// A preview replaces a waiting one of its kind; drop(kind) takes it away.
//
// The device's background picture (07 S157, DevicePhotoHost) is a job made
// from snapshotOf(nodes) with, in place of pixels:
//   onlyBg: true (only the visible background nodes), transparent: true (no
//   page colour: grabbed on black and on white, onPicture(onBlack,
//   onWhite)), fitBackground: true (the area is the background's
//   own extent, backgroundArea), side: the longest side in pixels (no more
//   than the most detailed picture gives at 100%, at least 64).
Item {
    id: _r

    // Out of sight, left of the window.
    x: -width - 10000
    y: 0
    width: 1
    height: 1

    property var _queue: []
    property var _job: null
    // A picture's own size from its address, { w, h } (HardwareProfile
    // .pictureSize), for 100% (07 S83). null: only the bottom background
    // picture's size is known (the editor's photoNatural).
    property var sizeOf: null
    // The device's background picture's page, in editor pixels: the page's
    // 16:9 (07 S157).
    readonly property int bgPageW: 1600
    readonly property int bgPageH: 900
    readonly property int bgMinSide: 64
    readonly property bool busy: _job !== null
    // Longest side of the copy, in device pixels: its canvases are this big
    // at most (past it the picture is enlarged to the size asked for).
    readonly property int maxSide: 8192
    readonly property real dpr: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1

    // What a picture is drawn from, taken when it is asked for: later
    // changes on screen don't reach a job already waiting. whole: the whole
    // page, whatever the print area.
    function snapshot(e, whole) {
        var f = e ? e.face : null
        // The pictures, both planes, are nodes: no photo of its own.
        var keys = ["chipTextMode", "actionLabels", "unboundText", "savedStyles", "printArea"]
        var props = {}
        for (var i = 0; e && i < keys.length; i++)
            props[keys[i]] = e[keys[i]]
        if (whole)
            props.printArea = null
        return {
            nodes: JSON.stringify(e ? (e.nodes || []) : []),
            props: props,
            dest: f ? { btn: f.destBtn, axis: f.destAxis, hat: f.destHat } : null,
            chipRows: f ? f.chipRows : [],
            w: e ? e.width : 1,
            h: e ? e.height : 1,
            area: e ? (whole ? e.spaceRect() : e.printAreaRect()) : { x: 0, y: 0, w: 1, h: 1 }
        }
    }

    // A snapshot without an editor, for the device's background picture
    // (07 S157): the whole page at bgPageW x bgPageH, no chips; the area is
    // set once the copy is loaded (fitBackground).
    function snapshotOf(nodesJson) {
        var text = typeof nodesJson === "string" ? nodesJson : JSON.stringify(nodesJson || [])
        return {
            nodes: text || "[]",
            props: { printArea: null },
            dest: null,
            chipRows: [],
            w: bgPageW,
            h: bgPageH,
            area: { x: 0, y: 0, w: bgPageW, h: bgPageH }
        }
    }

    // A background node the device's background picture draws: on the
    // background plane and not hidden, as in an export (07 S157).
    function isVisibleBackground(n) {
        return !!(n && n.plane === "background" && !n.hidden)
    }

    // The nodes a job draws: without Include background, no background
    // node (07 S123); onlyBg: the visible background nodes alone (07 S157).
    function jobNodes(snapNodes, includeBg, onlyBg) {
        var list = JSON.parse(snapNodes || "[]")
        if (onlyBg === true)
            return list.filter(isVisibleBackground)
        if (includeBg !== false)
            return list
        return list.filter(function(n) { return !(n && n.plane === "background") })
    }

    // A node's box as drawn, in editor pixels: skewed about its middle
    // (RigDrawItem's transform), then turned by rot about its middle (the
    // editor's wrapper).
    function _drawnBox(e, n) {
        var g = e.nodeBox(n)
        var cx = g.x + g.w / 2
        var cy = g.y + g.h / 2
        var k = n.skew
        var kx = k ? Number(k[0]) || 0 : 0
        var ky = k ? Number(k[1]) || 0 : 0
        var a = (Number(n.rot) || 0) * Math.PI / 180
        var cs = Math.cos(a)
        var sn = Math.sin(a)
        var pts = [[-g.w / 2, -g.h / 2], [g.w / 2, -g.h / 2], [g.w / 2, g.h / 2], [-g.w / 2, g.h / 2]]
        var x0 = 1e12, y0 = 1e12, x1 = -1e12, y1 = -1e12
        for (var i = 0; i < pts.length; i++) {
            var dx = pts[i][0] + kx * pts[i][1]
            var dy = ky * pts[i][0] + pts[i][1]
            var x = cx + dx * cs - dy * sn
            var y = cy + dx * sn + dy * cs
            x0 = Math.min(x0, x)
            y0 = Math.min(y0, y)
            x1 = Math.max(x1, x)
            y1 = Math.max(y1, y)
        }
        return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }
    }

    // The visible background's extent as drawn, in page fractions kept on
    // the page: { fx, fy, fw, fh }, null when there is none (07 S157).
    function backgroundArea(e) {
        if (!e)
            return null
        var s = e.spaceRect()
        var list = e.nodes || []
        var x0 = 1e12, y0 = 1e12, x1 = -1e12, y1 = -1e12
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (!isVisibleBackground(n))
                continue
            var b = _drawnBox(e, n)
            x0 = Math.min(x0, b.x)
            y0 = Math.min(y0, b.y)
            x1 = Math.max(x1, b.x + b.w)
            y1 = Math.max(y1, b.y + b.h)
        }
        if (x1 < x0 || !(s.w > 0) || !(s.h > 0))
            return null
        var fx0 = Math.max(0, Math.min(1, (x0 - s.x) / s.w))
        var fy0 = Math.max(0, Math.min(1, (y0 - s.y) / s.h))
        var fx1 = Math.max(0, Math.min(1, (x1 - s.x) / s.w))
        var fy1 = Math.max(0, Math.min(1, (y1 - s.y) / s.h))
        if (!(fx1 > fx0) || !(fy1 > fy0))
            return null
        return { fx: fx0, fy: fy0, fw: fx1 - fx0, fh: fy1 - fy0 }
    }

    // A picture's own size: sizeOf when set, else the editor's reading of
    // its bottom background picture (no other picture's size is known then).
    function _naturalOf(e, n) {
        var nat = null
        if (typeof sizeOf === "function")
            nat = sizeOf(n.srcUrl || "")
        else if (e.bottomPicture && e.photoNatural && e.bottomPicture() === n)
            nat = e.photoNatural()
        var w = nat ? Number(nat.w !== undefined ? nat.w : nat.width) || 0 : 0
        var h = nat ? Number(nat.h !== undefined ? nat.h : nat.height) || 0 : 0
        return { w: w, h: h }
    }

    // Picture pixels for each editor pixel of the most detailed visible
    // background picture (0: none known). A picture fills its box (07
    // S140), its crop leaving part of it there; turning and skew move the
    // box, not its size.
    function detail(e) {
        if (!e)
            return 0
        var list = e.nodes || []
        var best = 0
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (!isVisibleBackground(n) || n.shape !== "image")
                continue
            var nat = _naturalOf(e, n)
            if (!(nat.w > 0 && nat.h > 0))
                continue
            var g = e.drawGeom(n)
            if (!(g.w > 0 && g.h > 0))
                continue
            var c = n.crop || null
            var keepW = c ? Math.max(0.02, 1 - (c.l || 0) - (c.r || 0)) : 1
            var keepH = c ? Math.max(0.02, 1 - (c.t || 0) - (c.b || 0)) : 1
            best = Math.max(best, nat.w * keepW / g.w, nat.h * keepH / g.h)
        }
        return best
    }

    // Export pixels for each editor pixel on screen (07 S83): at 100% the
    // visible background picture with the most detail shows at its own
    // pixels; with none, the page 1920 px wide. The same export at any
    // window size or screen scale.
    function exportFactor(e, scalePct) {
        if (!e)
            return 1
        // A binding on this follows layer changes.
        e.tick
        var scale = Math.max(10, Math.min(800, Number(scalePct) || 100)) / 100
        var s = e.spaceRect()
        // Read only: Print & Export's pixels is a binding on this function.
        var d = detail(e)
        if (d > 0)
            return scale * d
        return scale * 1920 / Math.max(1, s.w)
    }

    function enqueue(job) {
        var q = _queue.slice()
        // Only the latest preview of each kind is worth drawing.
        if (job.preview)
            q = q.filter(function(j) { return j.preview !== job.preview })
        q.push(job)
        // Exports first.
        q.sort(function(a, b) { return (a.preview ? 1 : 0) - (b.preview ? 1 : 0) })
        _queue = q
        Qt.callLater(_next)
    }

    // A waiting preview of this kind is no longer wanted.
    function drop(kind) {
        _queue = _queue.filter(function(j) { return j.preview !== kind })
    }

    function _next() {
        if (_job || !_queue.length)
            return
        var q = _queue.slice()
        var j = q.shift()
        _queue = q
        var s = j.snap
        // The device's background picture: sized again once its area is
        // known (_fit); until then the page at the longest side asked for.
        if (j.fitBackground && !j.pixels) {
            var side = Math.max(1, Number(j.side) || 1024)
            j.pixels = { w: side, h: Math.max(1, Math.round(side * s.h / Math.max(1, s.w))) }
        }
        // The picture's size on screen units: grabbed at the screen's scale,
        // it comes back at the pixels asked for.
        j.L = { w: Math.max(1, j.pixels.w / dpr), h: Math.max(1, j.pixels.h / dpr) }
        var k = j.L.w / Math.max(1, s.area.w)
        var cap = maxSide / dpr / Math.max(1, s.w, s.h)
        j.k = Math.max(0.05, Math.min(k, cap))
        j.state = "load"
        j.ticks = 0
        _ground = j.transparent ? "black" : ""
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
        f.editorNodes = _r.jobNodes(s.nodes, j.includeBg, j.onlyBg)
    }

    // The device's background picture (07 S157): the area becomes the
    // background's own extent, the pixels its shape at the longest side
    // asked for (no more than the most detailed picture gives at 100%, at
    // least bgMinSide), and the copy is sized for them. false: nothing to
    // draw.
    function _fit(e) {
        var j = _job
        var a = backgroundArea(e)
        if (!a)
            return false
        var s = e.spaceRect()
        var aw = a.fw * s.w
        var ah = a.fh * s.h
        var asked = Math.max(1, Number(j.side) || 1024)
        var side = asked
        var d = detail(e)
        if (d > 0)
            side = Math.min(side, Math.round(Math.max(aw, ah) * d))
        side = Math.max(Math.min(bgMinSide, asked), side)
        var w = aw >= ah ? side : Math.max(1, Math.round(side * aw / ah))
        var h = aw >= ah ? Math.max(1, Math.round(side * ah / aw)) : side
        j.pixels = { w: w, h: h }
        j.snap.props = { printArea: a }
        j.L = { w: Math.max(1, w / dpr), h: Math.max(1, h / dpr) }
        // The area is aw editor pixels wide now: the copy grows to show it
        // L.w wide, within maxSide.
        var k = j.k * j.L.w / Math.max(1e-6, aw)
        var cap = maxSide / dpr / Math.max(1, j.snap.w, j.snap.h)
        j.k = Math.max(0.05, Math.min(k, cap))
        var f = _faceLoader.item
        f.width = j.snap.w * j.k
        f.height = j.snap.h * j.k
        j.fitted = true
        return true
    }

    // Once the editor is there: the map's look, then the print area as this
    // item's own size.
    function _applyEditor(e) {
        var j = _job
        e.exportZoom = j.k
        e.exporting = true
        e.printLight = !!j.light
        // Screen-only plane views never print (07 S87, S120).
        if ("editPlane" in e)
            e.editPlane = "foreground"
        if ("showFgFaint" in e)
            e.showFgFaint = false
        if ("bgViewHidden" in e)
            e.bgViewHidden = false
        if ("bgViewOpacity" in e)
            e.bgViewOpacity = 1
        // Big pictures at their own pixels, not the screen's copy (07 S124).
        if ("fullResolution" in e)
            e.fullResolution = true
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

    // Nothing still loading: the pictures on the map.
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

    // Drawn: a few frames for its canvases, then the picture.
    function _settle() {
        var j = _job
        var e = _editor()
        e.bump()
        e.repaint()
        j.state = "settle"
        j.ticks = 0
    }

    // A transparent job is grabbed twice, on black then on white: a grab
    // keeps no transparency everywhere (the software scene graph, used
    // off-screen, grabs onto opaque black), and the two together give each
    // pixel's colour and strength (DevicePhotoHost hands both on).
    function _grab() {
        var j = _job
        var white = j.state === "white"
        j.state = "grab"
        var ok = _r.grabToImage(function(result) {
            if (j.transparent && !white) {
                j.onBlack = result
                _r._ground = "white"
                j.state = "white"
                j.ticks = 0
                return
            }
            if (j.transparent)
                _r._finish(j.onBlack, result)
            else
                _r._finish(result)
        }, Qt.size(Math.max(1, Math.round(j.L.w)), Math.max(1, Math.round(j.L.h))))
        if (!ok)
            _finish(null)
    }

    // onPicture(grab) for a job; a transparent one: onPicture(on black,
    // on white). null: no picture.
    function _finish(result, onWhite) {
        var j = _job
        if (!j)
            return
        _faceLoader.active = false
        width = 1
        height = 1
        _ground = ""
        _job = null
        if (j.onPicture) {
            if (j.transparent)
                j.onPicture(result || null, result ? (onWhite || null) : null)
            else
                j.onPicture(result)
        }
        Qt.callLater(_next)
    }

    // A transparent job's ground: "black", then "white" ("" otherwise).
    property string _ground: ""

    // The page colour behind; for the device's background picture the
    // ground of each of its two grabs (07 S157).
    Rectangle {
        anchors.fill: parent
        visible: _r.busy
        color: _r._ground === "black" ? Style.ink
             : _r._ground === "white" ? Style.paper
             : (_r._job && _r._job.light) ? Style.paper : Style.background
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

    // Waits for the copy to be ready (its chips placed, the
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
                if (j.fitBackground && !j.fitted) {
                    // Its nodes first, then the area they cover.
                    if (!e.seeded && j.ticks <= 200)
                        return
                    if (!_r._fit(e))
                        _r._finish(null)
                    return
                }
                if (!j.applied) {
                    _r._applyEditor(e)
                    return
                }
                // Ready, or given up waiting (a picture that never loads).
                if ((e.seeded && !_r._loading(_faceLoader.item)) || j.ticks > 200)
                    _r._settle()
            } else if (j.state === "white") {
                // The white ground drawn: the second grab.
                if (j.ticks >= 2)
                    _r._grab()
            } else if (j.state === "settle") {
                if (j.ticks >= 3 && !_r._loading(_faceLoader.item))
                    _r._grab()
                else if (j.ticks > 200)
                    _r._grab()
            }
        }
    }
}
