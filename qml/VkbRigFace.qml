// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import Gremlin.Style

Item {
    id: _face

    property var host: null
    property int liveStamp: 0
    property var buttons: null
    property var axes: null
    property var hats: null
    property var chipRows: []
    property bool editing: false
    property var editorNodes: []
    // The bottom background picture (07 S127): its load recovers the view.
    property string photoOverride: ""
    // Space is held (the window watches the key): in Edit a left-drag pans
    // (07 S14), in Foreground and Background mode alike.
    property bool spaceHeld: false
    readonly property var editorItem: _editorLoader.item

    property var destBtn: ({})
    property var destAxis: ({})
    property var destHat: ({})
    property int destTick: 0
    property real zoom: 2
    property real panX: 0
    property real panY: 0
    // Out to 50% of the usual view (zoomFit), for room around the page;
    // zoomPage: the page filling the view (Zoom to Fit Page).
    readonly property real zoomFit: 4 / 3
    readonly property real zoomMin: zoomFit / 2
    readonly property real zoomMax: 8.0
    readonly property real zoomPage: 1.0
    // Wheel zoom speed in percent (Device Map Options → View).
    property real zoomSpeed: 100
    readonly property real wheelBase: 1 + 0.0012 * Math.max(0.25, zoomSpeed / 100)
    readonly property real viewPct: zoom / zoomFit

    // Rulers along the top and left while editing, in percent of the page.
    // Drag out of one to add a guide (rig_rulers.js; the Ruler component
    // below).
    property bool rulersOn: false
    readonly property real rulerSize: Style.dp(18)

    // Editor x or y (the world's coordinates) to the view's, and back.
    function viewX(ex) { return panX + _world.width / 2 + (ex - _world.width / 2) * zoom }
    function viewY(ey) { return panY + _world.height / 2 + (ey - _world.height / 2) * zoom }
    function editorX(vx) { return (vx - panX - _world.width / 2) / zoom + _world.width / 2 }
    function editorY(vy) { return (vy - panY - _world.height / 2) / zoom + _world.height / 2 }


    function resetView() {
        zoom = zoomFit
        panX = 0
        panY = 0
        pingEditor()
    }

    function clampPan() {
        var vw = _viewport.width
        var vh = _viewport.height
        if (vw < 8 || vh < 8)
            return
        if (!(zoom >= zoomMin && zoom <= zoomMax))
            zoom = 1
        var W = _world.width
        var H = _world.height
        var z = zoom
        var mx = Math.min(vw * 0.20, vw * 0.5)
        var my = Math.min(vh * 0.20, vh * 0.5)
        // Scaled page must still overlap the viewport. Do not pull toward center.
        var maxPanX = vw - mx - W * 0.5 * (1 - z)
        var minPanX = mx - W * 0.5 * (1 + z)
        var maxPanY = vh - my - H * 0.5 * (1 - z)
        var minPanY = my - H * 0.5 * (1 + z)
        panX = Math.min(Math.max(panX, minPanX), maxPanX)
        panY = Math.min(Math.max(panY, minPanY), maxPanY)
    }

    function viewOffScreen() {
        var vw = _viewport.width
        var vh = _viewport.height
        if (vw < 8 || vh < 8)
            return false
        if (!(zoom >= zoomMin && zoom <= zoomMax))
            return true
        if (panX !== panX || panY !== panY)
            return true
        var W = _world.width
        var H = _world.height
        var z = zoom
        var left = panX + W * 0.5 * (1 - z)
        var right = panX + W * 0.5 * (1 + z)
        var top = panY + H * 0.5 * (1 - z)
        var bot = panY + H * 0.5 * (1 + z)
        if (right < 8 || left > vw - 8 || bot < 8 || top > vh - 8)
            return true
        return false
    }

    // Pans, without zooming, so an editor rect is in view (press to find).
    // Editor and world coordinates are the same; the world is scaled by
    // zoom about its centre and moved by panX and panY.
    function showEditorRect(x, y, w, h) {
        var vw = _viewport.width
        var vh = _viewport.height
        if (vw < 8 || vh < 8)
            return
        var W = _world.width
        var H = _world.height
        var z = zoom
        var left = panX + W / 2 + (x - W / 2) * z
        var top = panY + H / 2 + (y - H / 2) * z
        var margin = Math.min(vw, vh) * 0.05
        if (left >= margin && top >= margin && left + w * z <= vw - margin && top + h * z <= vh - margin)
            return
        panX = vw / 2 - W / 2 - (x + w / 2 - W / 2) * z
        panY = vh / 2 - H / 2 - (y + h / 2 - H / 2) * z
        clampPan()
        pingEditor()
    }

    // Zooms and pans so an editor rect fills the view, with a margin; never
    // smaller than the whole page (zoomMin) or past zoomMax.
    function fitEditorRect(x, y, w, h) {
        var vw = _viewport.width
        var vh = _viewport.height
        if (vw < 8 || vh < 8 || !(w > 0) || !(h > 0))
            return
        var W = _world.width
        var H = _world.height
        var z = Math.min(vw / (w * 1.25), vh / (h * 1.25))
        zoom = Math.max(zoomMin, Math.min(zoomMax, z))
        panX = vw / 2 - W / 2 - (x + w / 2 - W / 2) * zoom
        panY = vh / 2 - H / 2 - (y + h / 2 - H / 2) * zoom
        clampPan()
        pingEditor()
    }

    // The whole page in view, filling it.
    function zoomToPage() {
        zoom = zoomPage
        panX = 0
        panY = 0
        pingEditor()
    }

    function recoverView() {
        if (panX !== panX || panY !== panY || !(zoom >= zoomMin && zoom <= zoomMax))
            resetView()
        else
            clampPan()
        pingEditor()
    }

    function zoomAt(vx, vy, factor) {
        var z0 = zoom
        if (z0 < 0.01) z0 = 1
        var z1 = Math.max(zoomMin, Math.min(zoomMax, z0 * factor))
        if (Math.abs(z1 - z0) < 0.0001) {
            return
        }
        var W = _world.width
        var H = _world.height
        var vw = _viewport.width
        var vh = _viewport.height
        if (!(vx === vx) || !(vy === vy)) {
            vx = vw * 0.5
            vy = vh * 0.5
        }
        if (Math.abs(z1 - zoomFit) < 0.03)
            z1 = zoomFit
        else if (Math.abs(z1 - zoomPage) < 0.015)
            z1 = zoomPage
        else if (Math.abs(z1 - zoomMin) < 0.015)
            z1 = zoomMin
        var wx = (vx - panX - W * 0.5) / z0 + W * 0.5
        var wy = (vy - panY - H * 0.5) / z0 + H * 0.5
        zoom = z1
        panX = vx - (wx - W * 0.5) * z1 - W * 0.5
        panY = vy - (wy - H * 0.5) * z1 - H * 0.5
        clampPan()
        pingEditor()
    }

    function zoomAtItem(item, ix, iy, factor) {
        if (!item || !_viewport) {
            zoomAt(_viewport ? _viewport.width * 0.5 : 0, _viewport ? _viewport.height * 0.5 : 0, factor)
            return
        }
        var p = item.mapToItem(_viewport, ix, iy)
        zoomAt(p.x, p.y, factor)
    }

    function hwButton(id) { return host && host.hwButton ? host.hwButton(id) : 0 }
    function hwAxis(id) { return host && host.hwAxis ? host.hwAxis(id) : 0 }
    function hwHat(id) { return host && host.hwHat ? host.hwHat(id) : 0 }

    function labelBtn(id) {
        destTick
        var m = destBtn
        return (m && m[id]) ? m[id] : "—"
    }
    function labelAxis(id) {
        destTick
        var m = destAxis
        return (m && m[id]) ? m[id] : "—"
    }
    function labelHat(id) {
        destTick
        var m = destHat
        return (m && m[id]) ? m[id] : "—"
    }


    function pingEditor() {
        if (typeof _editorLoader === "undefined" || !_editorLoader)
            return
        var ed = _editorLoader.item
        if (!ed)
            return
        ed.bump()
    }

    // Live chips and leaders are drawn by VkbRigEditor.
    Item {
        id: _viewport
        anchors.fill: parent
        clip: true

        Item {
            id: _world
            width: parent.width
            height: parent.height
            x: _face.panX
            y: _face.panY
            transformOrigin: Item.Center
            scale: _face.zoom

    // The bottom background picture, hidden (the editor draws it): its load
    // and size tell the view to recover and the editor to redraw.
    Image {
        id: _img
        anchors.fill: parent
        visible: false
        // No background picture shows none (not the Gladiator).
        source: _face.photoOverride.length ? _face.photoOverride : ""
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        cache: true
        onStatusChanged: {
            if (status === Image.Ready)
                Qt.callLater(_face.recoverView)
            else
                _face.pingEditor()
        }
        onPaintedWidthChanged: _face.pingEditor()
        onPaintedHeightChanged: _face.pingEditor()
    }

    Loader {
        id: _editorLoader
        anchors.fill: parent
        z: 5
        active: true
        visible: status === Loader.Ready
        source: "VkbRigEditor.qml"
        onStatusChanged: {
            if (status === Loader.Error)
                console.warn("The Device Mapping Editor could not load: "
                             + Qt.createComponent(source).errorString())
        }
    }

    Binding { target: _editorLoader.item; property: "face"; value: _face; when: _editorLoader.status === Loader.Ready; restoreMode: Binding.RestoreNone }

    component Ruler: Canvas {
        id: _ruler
        property bool across: true
        // An inline component cannot see this file's ids: the view and the
        // editor come in as properties.
        property var face: null
        readonly property var ed: face ? face.editorItem : null
        z: 7
        visible: !!face && face.rulersOn && !!ed && ed.interactive
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.fillStyle = String(Style.bgCard)
            ctx.fillRect(0, 0, width, height)
            if (!ed)
                return
            var s = ed.spaceRect()
            ctx.strokeStyle = String(Style.fgMuted)
            ctx.fillStyle = String(Style.fgMuted)
            ctx.font = Math.round(Style.dp(9)) + "px sans-serif"
            ctx.lineWidth = 1
            // The page from 0 to 100 along this edge, at any zoom: numbered
            // marks about 60 px apart (steps of 1, 2 or 5 times a power of
            // ten), five small marks between them; only what this ruler
            // shows is drawn (the whole page at a high zoom is far wider).
            var along = across ? width : height
            var at0 = across ? x : y
            var p0 = across ? face.viewX(s.x) : face.viewY(s.y)
            var p100 = across ? face.viewX(s.x + s.w) : face.viewY(s.y + s.h)
            var perPct = (p100 - p0) / 100
            if (!(perPct > 0))
                return
            var step = 0.1
            var bases = [1, 2, 5]
            for (var e = -1; e <= 3 && step * perPct < Style.dp(60); e++) {
                for (var bi = 0; bi < bases.length; bi++) {
                    step = bases[bi] * Math.pow(10, e)
                    if (step * perPct >= Style.dp(60))
                        break
                }
            }
            var minor = step / 5
            var first = Math.floor(((at0 - p0) / perPct) / minor)
            var last = Math.ceil(((at0 + along - p0) / perPct) / minor)
            var decimals = step < 1 ? 1 : 0
            var depth = across ? height : width
            for (var k = first; k <= last; k++) {
                var pct = k * minor
                var v = p0 + pct * perPct - at0
                var big = k % 5 === 0
                var len = depth * (big ? 0.6 : 0.3)
                ctx.beginPath()
                if (across) {
                    ctx.moveTo(Math.round(v) + 0.5, height)
                    ctx.lineTo(Math.round(v) + 0.5, height - len)
                } else {
                    ctx.moveTo(width, Math.round(v) + 0.5)
                    ctx.lineTo(width - len, Math.round(v) + 0.5)
                }
                ctx.stroke()
                if (!big)
                    continue
                var label = pct.toFixed(decimals)
                if (across)
                    ctx.fillText(label, v + 2, Style.dp(9))
                else
                    ctx.fillText(label, 1, v - 2)
            }
            // The guides' places.
            ctx.fillStyle = String(Style.accent)
            var gl = across ? ed.rulerGuidesX : ed.rulerGuidesY
            for (var g = 0; g < gl.length; g++) {
                var gv = (across ? face.viewX(s.x + gl[g] * s.w) : face.viewY(s.y + gl[g] * s.h)) - at0
                if (across)
                    ctx.fillRect(gv - 1, 0, 3, height)
                else
                    ctx.fillRect(0, gv - 1, width, 3)
            }
        }
        Connections {
            target: _ruler.face
            function onPanXChanged() { _ruler.requestPaint() }
            function onPanYChanged() { _ruler.requestPaint() }
            function onZoomChanged() { _ruler.requestPaint() }
            function onRulersOnChanged() { _ruler.requestPaint() }
        }
        Connections {
            target: _ruler.ed
            function onRulerGuidesXChanged() { _ruler.requestPaint() }
            function onRulerGuidesYChanged() { _ruler.requestPaint() }
            function onWidthChanged() { _ruler.requestPaint() }
        }
        // Drag out a guide: down from the top ruler gives a horizontal one,
        // right from the left ruler a vertical one.
        MouseArea {
            anchors.fill: parent
            preventStealing: true
            property int index: -1
            readonly property string axis: _ruler.across ? "y" : "x"
            function fracAt(mouse) {
                var e = _ruler.ed
                var p = mapToItem(face, mouse.x, mouse.y)
                var s = e.spaceRect()
                return _ruler.across ? (face.editorY(p.y) - s.y) / s.h : (face.editorX(p.x) - s.x) / s.w
            }
            onPressed: (mouse) => {
                if (!_ruler.ed)
                    return
                // A new guide dragged out of the ruler is one Undo step,
                // made on release (07 S55a).
                if (_ruler.ed.beginGesture)
                    _ruler.ed.beginGesture()
                index = _ruler.ed.addRulerGuide(axis, Math.max(0, Math.min(1, fracAt(mouse))))
            }
            onPositionChanged: (mouse) => {
                if (index >= 0 && _ruler.ed)
                    _ruler.ed.moveRulerGuide(axis, index, fracAt(mouse))
            }
            onReleased: (mouse) => {
                if (index < 0 || !_ruler.ed)
                    return
                var p = mapToItem(face, mouse.x, mouse.y)
                var e = _ruler.ed
                var ex = face.editorX(p.x)
                var ey = face.editorY(p.y)
                // Let go on the ruler itself: no guide.
                if (contains(Qt.point(mouse.x, mouse.y)))
                    e.removeRulerGuide(axis, index)
                else
                    e.dropRulerGuide(axis, index, ex, ey)
                index = -1
                if (e.endGesture)
                    e.endGesture()
            }
            onCanceled: {
                index = -1
                if (_ruler.ed && _ruler.ed.endGesture)
                    _ruler.ed.endGesture()
            }
        }
    }


    Binding { target: _editorLoader.item; property: "nodes"; value: _face.editorNodes; when: _editorLoader.status === Loader.Ready; restoreMode: Binding.RestoreNone }
    Binding { target: _editorLoader.item; property: "interactive"; value: _face.editing; when: _editorLoader.status === Loader.Ready; restoreMode: Binding.RestoreNone }

    Connections {
        target: _face
        function onEditorNodesChanged() { _face.pingEditor() }
        function onEditingChanged() {
            var ed = _editorLoader.item
            if (!ed)
                return
            if (!_face.editing) {
                ed.selectedId = ""
                ed.selectedSpine = -1
            }
            ed.bump()
        }
    }


        } // _world

        WheelHandler {
            target: _viewport
            enabled: !_face.editing
            onWheel: (w) => {
                var dy = w.pixelDelta.y !== 0 ? w.pixelDelta.y : w.angleDelta.y
                if (dy === 0) {
                    w.accepted = false
                    return
                }
                _face.zoomAt(w.x, w.y, Math.pow(_face.wheelBase, dy))
                w.accepted = true
            }
        }

        // In Edit, Space + left-drag pans: over the editor while Space is
        // held, so no item is picked or moved (07 S14). A middle-drag pans
        // everywhere (_midPan).
        MouseArea {
            id: _spacePan
            objectName: "dmeSpacePan"
            anchors.fill: parent
            z: 20
            enabled: _face.editing && (_face.spaceHeld || pressed)
            visible: enabled
            acceptedButtons: Qt.LeftButton
            preventStealing: true
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            property real grabX: 0
            property real grabY: 0
            property real startX: 0
            property real startY: 0
            onPressed: (mouse) => {
                startX = mouse.x
                startY = mouse.y
                grabX = _face.panX
                grabY = _face.panY
            }
            onPositionChanged: (mouse) => {
                if (!pressed)
                    return
                _face.panX = grabX + mouse.x - startX
                _face.panY = grabY + mouse.y - startY
            }
        }

        DragHandler {
            id: _midPan
            acceptedButtons: _face.editing ? Qt.MiddleButton : (Qt.LeftButton | Qt.MiddleButton)
            target: null
            enabled: true
            property real grabX: 0
            property real grabY: 0
            onActiveChanged: {
                if (active) {
                    grabX = _face.panX
                    grabY = _face.panY
                }
            }
            onTranslationChanged: {
                if (!active)
                    return
                _face.panX = grabX + translation.x
                _face.panY = grabY + translation.y
            }
        }

        // A closed hand while _midPan pans (07 S14). The handler's own
        // cursorShape loses to the items above it (the editor's pointer
        // area), so this cursor-only area sits on top for the drag; it takes
        // no buttons.
        MouseArea {
            objectName: "dmePanCursor"
            anchors.fill: parent
            z: 21
            enabled: _midPan.active
            visible: enabled
            acceptedButtons: Qt.NoButton
            cursorShape: Qt.ClosedHandCursor
        }
    } // _viewport


    Connections {
        target: _face
        function onWidthChanged() { Qt.callLater(_face.recoverView) }
        function onHeightChanged() { Qt.callLater(_face.recoverView) }
        function onLiveStampChanged() { _face.pingEditor() }
        function onDestTickChanged() { _face.pingEditor() }
    }

    // The rulers on the view's top and left edges, outside the zoomed map
    // (inside it they were scaled and pushed off the edges at any zoom
    // above 1): they stay on the edges at every zoom and show the page's
    // place there.
    Ruler {
        face: _face
        across: true
        x: _face.rulerSize
        y: 0
        width: _face.width - _face.rulerSize
        height: _face.rulerSize
    }
    Ruler {
        face: _face
        across: false
        x: 0
        y: _face.rulerSize
        width: _face.rulerSize
        height: _face.height - _face.rulerSize
    }
    Rectangle {
        z: 7
        visible: _face.rulersOn && !!_editorLoader.item && _editorLoader.item.interactive
        width: _face.rulerSize
        height: _face.rulerSize
        color: Style.bgCard
    }

    // 07 S104: a failed editor load shows a plain error, no device layout;
    // outside the zoomed map so it stays readable.
    Text {
        objectName: "editorLoadError"
        anchors.centerIn: parent
        z: 6
        visible: _editorLoader.status === Loader.Error
        color: Style.fg
        font.pixelSize: Style.dp(14)
        text: "The Device Mapping Editor could not load."
    }
}
