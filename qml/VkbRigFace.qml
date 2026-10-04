// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Layouts
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
    property string photoOverride: ""
    readonly property var editorItem: _editorLoader.item

    property var destBtn: ({})
    property var destAxis: ({})
    property var destHat: ({})
    property int destTick: 0
    property real zoom: 2
    property real panX: 0
    property real panY: 0
    readonly property real zoomMin: 1.0
    readonly property real zoomMax: 8.0
    readonly property real zoomFit: 4 / 3
    // Wheel zoom speed in percent (Options → Button Map → View).
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

    readonly property real _pw: _img.paintedWidth
    readonly property real _ph: _img.paintedHeight
    readonly property real _ox: (_img.width - _pw) * 0.5
    readonly property real _oy: (_img.height - _ph) * 0.5
    readonly property real _layoutTok: _pw + _ph + _ox + _oy + width + height

    function photoPt(nx, ny) {
        return _img.mapToItem(_world, _ox + nx * _pw, _oy + ny * _ph)
    }

    function toPhoto(mx, my) {
        var p = _img.mapFromItem(_world, mx, my)
        if (_pw < 1 || _ph < 1) {
            return Qt.point(0, 0)
        }
        return Qt.point((p.x - _ox) / _pw, (p.y - _oy) / _ph)
    }

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

    // The whole page in view.
    function zoomToPage() {
        zoom = zoomMin
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

    function shortDest(s) {
        var t = String(s || "—")
        t = t.replace(/vJoy Device /g, "")
        t = t.replace(/vJoy /g, "")
        t = t.replace(/vJ\d+\s*/g, "")
        t = t.replace(/^\d+\s+/, "")
        t = t.replace(/Xbox 360 Controller /g, "")
        t = t.replace(/Xbox /g, "")
        t = t.replace(/X360 \d+\s*/g, "")
        t = t.replace(/Right Trigger/g, "RT")
        t = t.replace(/Left Trigger/g, "LT")
        t = t.replace(/Right Stick /g, "RS ")
        t = t.replace(/Left Stick /g, "LS ")
        t = t.replace(/Button /g, "B")
        t = t.replace(/ \+ /g, "+")
        t = t.replace(/ +/g, " ")
        t = t.trim()
        return t.length ? t : "—"
    }

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

    function pin(item, side) {
        if (!item) {
            return Qt.point(0, 0)
        }
        var x = side === "right" ? item.width : (side === "left" ? 0 : item.width * 0.5)
        var y = side === "top" ? 0 : item.height * 0.5
        return item.mapToItem(_world, x, y)
    }

    // Place a chip column at the photo's ny so the leader stays near-horizontal.
    function followY(pane, ny, h) {
        if (!pane || _ph < 8) {
            return 0
        }
        var p = photoPt(0.5, ny)
        var loc = pane.mapFromItem(_world, 0, p.y)
        var y = loc.y - h * 0.5
        if (y < 0) {
            y = 0
        }
        if (y + h > pane.height) {
            y = Math.max(0, pane.height - h)
        }
        return y
    }

    function below(item, gap, pane, ny, h) {
        var y = followY(pane, ny, h)
        if (item) {
            y = Math.max(y, item.y + item.height + gap)
        }
        if (pane && y + h > pane.height) {
            y = Math.max(0, pane.height - h)
        }
        return y
    }

    Repeater {
        model: _face.buttons
        Item {
            required property int identifier
            required property string vjoyLabel
            function bump() {
                var m = _face.destBtn
                m[identifier] = vjoyLabel
                _face.destBtn = m
                _face.destTick++
            }
            Component.onCompleted: bump()
            onVjoyLabelChanged: bump()
        }
    }
    Repeater {
        model: _face.axes
        Item {
            required property int identifier
            required property string vjoyLabel
            function bump() {
                var m = _face.destAxis
                m[identifier] = vjoyLabel
                _face.destAxis = m
                _face.destTick++
            }
            Component.onCompleted: bump()
            onVjoyLabelChanged: bump()
        }
    }
    Repeater {
        model: _face.hats
        Item {
            required property int identifier
            required property string vjoyLabel
            function bump() {
                var m = _face.destHat
                m[identifier] = vjoyLabel
                _face.destHat = m
                _face.destTick++
            }
            Component.onCompleted: bump()
            onVjoyLabelChanged: bump()
        }
    }

    component Tag: Rectangle {
        property int hwId: 0
        property string kind: "btn"
        property string prefix: ""

        readonly property string _dest: kind === "axis" ? _face.labelAxis(hwId)
                                      : kind === "hat" ? _face.labelHat(hwId)
                                      : _face.labelBtn(hwId)
        readonly property bool lit: {
            _face.liveStamp
            if (kind === "axis") {
                return Math.abs(_face.hwAxis(hwId)) > 0.12
            }
            if (kind === "hat") {
                return _face.hwHat(hwId) > 0.5
            }
            return _face.hwButton(hwId) > 0.5
        }

        implicitWidth: _lab.implicitWidth + Style.dp(10)
        implicitHeight: Style.dp(20)
        radius: Style.dp(4)
        color: lit ? "#14532D" : "#18181B"
        border.color: lit ? "#22C55E" : "#3F3F46"
        Text {
            id: _lab
            anchors.centerIn: parent
            color: lit ? "#BBF7D0" : "#E4E4E7"
            font.pixelSize: Style.dp(10)
            text: prefix + hwId + " → " + _dest
        }
    }

    component HatPlus: Item {
        property int up: 0
        property int down: 0
        property int leftId: 0
        property int rightId: 0
        property int center: 0

        implicitWidth: _g.implicitWidth
        implicitHeight: _g.implicitHeight
        width: implicitWidth
        height: implicitHeight

        Grid {
            id: _g
            columns: 3
            rows: 3
            spacing: Style.dp(3)
            horizontalItemAlignment: Grid.AlignHCenter
            verticalItemAlignment: Grid.AlignVCenter
            Item { width: Style.dp(8); height: Style.dp(8) }
            Tag { hwId: up }
            Item { width: Style.dp(8); height: Style.dp(8) }
            Tag { hwId: leftId }
            Tag { hwId: center }
            Tag { hwId: rightId }
            Item { width: Style.dp(8); height: Style.dp(8) }
            Tag { hwId: down }
            Item { width: Style.dp(8); height: Style.dp(8) }
        }
    }

    function pingEditor() {
        if (typeof _editorLoader === "undefined" || !_editorLoader)
            return
        var ed = _editorLoader.item
        if (!ed)
            return
        ed.bump()
    }

    // Photo keeps gutter panes so chipFx/chipFy match the JSON window fractions.
    // Live chips and leaders come from qml/maps/vkb_evo_r.json via VkbRigEditor.
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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(8)
        spacing: Style.dp(4)

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.dp(6)

            Item {
                id: _leftPane
                Layout.preferredWidth: Style.dp(280)
                Layout.maximumWidth: Style.dp(280)
                Layout.fillHeight: true
                clip: true
                opacity: _editorLoader.item ? 0 : 1
                enabled: !_editorLoader.item

                Column {
                    id: _leftHead
                    anchors.right: parent.right
                    anchors.rightMargin: Style.dp(2)
                    spacing: Style.dp(6)
                    y: {
                        _face._layoutTok
                        return _face.followY(_leftPane, 0.210, height)
                    }
                    onYChanged: _lines.requestPaint()
                    onHeightChanged: _lines.requestPaint()

                    Tag { id: _h1; kind: "hat"; hwId: 1; prefix: "H"; anchors.right: parent.right }
                    HatPlus { id: _p1115; up: 11; down: 13; leftId: 14; rightId: 12; center: 15; anchors.right: parent.right }
                    HatPlus { id: _p610; up: 6; down: 8; leftId: 9; rightId: 7; center: 10; anchors.right: parent.right }
                    Tag { id: _b3; hwId: 3; anchors.right: parent.right }
                }

                HatPlus {
                    id: _p1620
                    anchors.right: parent.right
                    anchors.rightMargin: Style.dp(2)
                    up: 16; down: 18; leftId: 19; rightId: 17; center: 20
                    y: {
                        _face._layoutTok
                        _leftHead.y
                        _leftHead.height
                        return _face.below(_leftHead, 10, _leftPane, 0.370, height)
                    }
                    onYChanged: _lines.requestPaint()
                }

                Column {
                    id: _axes
                    anchors.right: parent.right
                    anchors.rightMargin: Style.dp(2)
                    spacing: Style.dp(3)
                    y: {
                        _face._layoutTok
                        _p1620.y
                        _p1620.height
                        return _face.below(_p1620, 10, _leftPane, 0.575, height)
                    }
                    onYChanged: _lines.requestPaint()
                    Tag { kind: "axis"; hwId: 1; prefix: "A"; anchors.right: parent.right }
                    Tag { kind: "axis"; hwId: 2; prefix: "A"; anchors.right: parent.right }
                    Tag { kind: "axis"; hwId: 3; prefix: "A"; anchors.right: parent.right }
                }
            }

            Item {
                id: _stage
                Layout.fillWidth: true
                Layout.fillHeight: true

                Image {
                    id: _img
                    anchors.fill: parent
                    // No photo chosen shows none (not the Gladiator).
                    source: _face.photoOverride.length ? _face.photoOverride : ""
                    fillMode: Image.PreserveAspectFit
                    visible: !_editorLoader.item
                    asynchronous: true
                    cache: true
                    onStatusChanged: {
                        _lines.requestPaint()
                        if (status === Image.Ready)
                            Qt.callLater(_face.recoverView)
                        else
                            _face.pingEditor()
                    }
                    onPaintedWidthChanged: {
                        _lines.requestPaint()
                        _face.pingEditor()
                    }
                    onPaintedHeightChanged: {
                        _lines.requestPaint()
                        _face.pingEditor()
                    }
                }
            }

            Item {
                id: _rightPane
                Layout.preferredWidth: Style.dp(160)
                Layout.maximumWidth: Style.dp(160)
                Layout.fillHeight: true
                clip: true
                opacity: _editorLoader.item ? 0 : 1
                enabled: !_editorLoader.item

                Column {
                    id: _rightGrip
                    anchors.left: parent.left
                    anchors.leftMargin: Style.dp(2)
                    spacing: Style.dp(6)
                    y: {
                        _face._layoutTok
                        return _face.followY(_rightPane, 0.276, height)
                    }
                    onYChanged: _lines.requestPaint()
                    onHeightChanged: _lines.requestPaint()

                    Tag { id: _b4; hwId: 4 }
                    Column {
                        id: _p2122
                        spacing: Style.dp(3)
                        Tag { hwId: 21 }
                        Tag { hwId: 22 }
                    }
                    Column {
                        id: _p12
                        spacing: Style.dp(3)
                        Tag { hwId: 1 }
                        Tag { hwId: 2 }
                    }
                }

                Tag {
                    id: _b5
                    hwId: 5
                    anchors.left: parent.left
                    anchors.leftMargin: Style.dp(2)
                    y: {
                        _face._layoutTok
                        _rightGrip.y
                        _rightGrip.height
                        return _face.below(_rightGrip, 10, _rightPane, 0.420, height)
                    }
                    onYChanged: _lines.requestPaint()
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(48)
            opacity: _editorLoader.item ? 0 : 1
            enabled: !_editorLoader.item

            Row {
                id: _bottom
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Style.dp(14)

                Tag { id: _b28; hwId: 28; anchors.verticalCenter: parent.verticalCenter }
                Tag { id: _b27; hwId: 27; anchors.verticalCenter: parent.verticalCenter }
                Tag { id: _b29; hwId: 29; anchors.verticalCenter: parent.verticalCenter }
                Column {
                    id: _p2526
                    spacing: Style.dp(3)
                    Tag { hwId: 25 }
                    Tag { hwId: 26 }
                }
                Tag { id: _a4; kind: "axis"; hwId: 4; prefix: "A"; anchors.verticalCenter: parent.verticalCenter }
                Column {
                    id: _p2324
                    spacing: Style.dp(3)
                    Tag { hwId: 23 }
                    Tag { hwId: 24 }
                }
            }
        }
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
                console.warn("VkbRigEditor failed to load")
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

    Canvas {
        id: _lines
        anchors.fill: parent
        z: 1
        visible: !_editorLoader.item
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = "#A1A1AA"
            ctx.lineWidth = 1.1

            function stroke(item, nx, ny, side) {
                if (!item) {
                    return
                }
                var a = _face.pin(item, side)
                var b = _face.photoPt(nx, ny)
                ctx.beginPath()
                ctx.moveTo(a.x, a.y)
                ctx.lineTo(b.x, b.y)
                ctx.stroke()
                ctx.beginPath()
                ctx.arc(b.x, b.y, 3.5, 0, 6.3)
                ctx.fillStyle = "#F4F4F5"
                ctx.fill()
            }

            // Pixels from qml/vkb_evo_r_face_map.md on JPEG 899x920.
            stroke(_h1, 0.345, 0.180, "right")
            stroke(_p1115, 0.418, 0.175, "right")
            stroke(_p610, 0.412, 0.228, "right")
            stroke(_b3, 0.346, 0.254, "right")
            stroke(_p1620, 0.400, 0.370, "right")
            stroke(_axes, 0.429, 0.575, "right")
            stroke(_b4, 0.613, 0.247, "left")
            stroke(_p2122, 0.656, 0.280, "left")
            stroke(_p12, 0.617, 0.301, "left")
            stroke(_b5, 0.605, 0.420, "left")
            stroke(_b28, 0.574, 0.711, "top")
            stroke(_b27, 0.621, 0.709, "top")
            stroke(_b29, 0.654, 0.700, "top")
            stroke(_p2526, 0.623, 0.798, "top")
            stroke(_a4, 0.665, 0.798, "top")
            stroke(_p2324, 0.739, 0.798, "top")
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
    } // _viewport

    Timer {
        interval: 50
        running: true
        repeat: false
        onTriggered: _lines.requestPaint()
    }

    Connections {
        target: _face
        function onWidthChanged() {
            Qt.callLater(_face.recoverView)
            _lines.requestPaint()
        }
        function onHeightChanged() {
            Qt.callLater(_face.recoverView)
            _lines.requestPaint()
        }
        function onLiveStampChanged() {
            _lines.requestPaint()
            _face.pingEditor()
        }
        function onDestTickChanged() {
            _lines.requestPaint()
            _face.pingEditor()
        }
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
}
