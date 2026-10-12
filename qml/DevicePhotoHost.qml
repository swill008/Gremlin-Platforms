// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import Gremlin.Device

// The device's background picture (07 S157): devicePhotoMaker
// (gremlin/ui/device_photo.py) asks for one device at a time; this hidden
// renderer draws its whole visible background, cut to its own extent, on
// black and on white, and saves both as PNGs (outPath and
// "<outPath less .png>.white.png"). The maker makes the transparent picture
// from the two, adds the staleness key and writes it into the device's
// folder.
// Held once by Main.qml, out of sight.
Item {
    id: _host

    width: 0
    height: 0
    visible: true

    // The maker, or null where the program has none (a test's own window).
    readonly property var maker: typeof devicePhotoMaker !== "undefined" ? devicePhotoMaker : null
    // The renderer, for tests.
    readonly property alias renderer: _render

    // Look copies (07 S43) and picture sizes (07 S83), as in the editor.
    HardwareProfile { id: _hw }

    RigRenderer {
        id: _render
        sizeOf: function(url) {
            return (typeof _hw.pictureSize === "function") ? _hw.pictureSize(url) : null
        }
    }

    // A stored picture reference ("pictures/<name>") as an address in the
    // folder given.
    function srcUrlOf(src, picturesUrl) {
        var s = String(src || "").replace(/\\/g, "/")
        if (!s.length)
            return ""
        if (s.indexOf("file:") === 0 || s.indexOf("qrc:") === 0)
            return s
        var name = s.indexOf("pictures/") === 0 ? s.slice("pictures/".length) : s
        var base = String(picturesUrl || "")
        if (base.length && base.charAt(base.length - 1) !== "/")
            base += "/"
        return base + name.split("/").map(encodeURIComponent).join("/")
    }

    // The module file's nodes with each picture's address and look copy.
    function hydrate(nodesJson, picturesUrl) {
        var list = []
        try {
            list = JSON.parse(nodesJson || "[]")
        } catch (err) {
            return null
        }
        if (!Array.isArray(list))
            return null
        for (var i = 0; i < list.length; i++) {
            var n = list[i]
            if (!n || n.shape !== "image" || !n.src)
                continue
            n.srcUrl = srcUrlOf(n.src, picturesUrl)
            var look = n.look || {}
            if (look.bright || look.contrast || look.grey) {
                var copy = _hw.adjustedPhotoUrl(n.srcUrl, {
                    bright: look.bright || 0, contrast: look.contrast || 0, grey: look.grey || 0
                })
                if (copy)
                    n.lookUrl = String(copy)
            }
        }
        return list
    }

    // A path from a file address or a plain path.
    function localPath(p) {
        var path = String(p || "")
        if (path.indexOf("file:") === 0) {
            path = decodeURIComponent(path.replace(/^file:\/\//, ""))
            if (/^\/[A-Za-z]:/.test(path))
                path = path.slice(1)
        }
        return path
    }

    // Where the picture on white goes: beside outPath, "<name>.white.png".
    function whitePathOf(path) {
        return String(path).replace(/\.png$/i, "") + ".white.png"
    }

    // One job: drawn on black (saved at outPath) and on white (saved at
    // whitePathOf(outPath)); the maker makes the transparent picture from
    // the two (a grab keeps no transparency off-screen) and hears the
    // outcome through rendered(token, ok). done(ok) is called as well when
    // given (tests).
    function render(token, nodesJson, picturesUrl, side, outPath, done) {
        var list = hydrate(nodesJson, picturesUrl)
        function finish(ok) {
            if (_host.maker && _host.maker.rendered)
                _host.maker.rendered(token, ok)
            if (typeof done === "function")
                done(ok)
        }
        if (list === null) {
            finish(false)
            return
        }
        _render.enqueue({
            snap: _render.snapshotOf(JSON.stringify(list)),
            onlyBg: true,
            transparent: true,
            fitBackground: true,
            side: side,
            light: false,
            includeBg: true,
            preview: "",
            onPicture: function(onBlack, onWhite) {
                var path = localPath(outPath)
                finish(!!onBlack && !!onWhite && path.length > 0
                       && onBlack.saveToFile(path) && onWhite.saveToFile(whitePathOf(path)))
            }
        })
    }

    Connections {
        target: _host.maker
        ignoreUnknownSignals: true
        function onRenderWanted(token, nodesJson, picturesUrl, side, outPath) {
            _host.render(token, nodesJson, picturesUrl, side, outPath)
        }
    }

    Component.onCompleted: {
        if (maker)
            maker.hostReady = true
    }
}
