// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import Gremlin.Style

Item {
    id: _root

    property int padId: 1
    property var live: null
    property int stamp: 0

    implicitWidth: Style.dp(520)
    implicitHeight: Style.dp(410)

    readonly property real _ox: _img.x + (_img.width - _img.paintedWidth) * 0.5
    readonly property real _oy: _img.y + (_img.height - _img.paintedHeight) * 0.5
    readonly property real _pw: Math.max(1, _img.paintedWidth)
    readonly property real _ph: Math.max(1, _img.paintedHeight)

    function v(name) {
        if (!live || typeof live.xboxValue !== "function")
            return 0
        return stamp >= 0 ? live.xboxValue(padId, name) : 0
    }
    function on(name) {
        return stamp >= 0 && v(name) > 0.5
    }
    function px(nx) { return _ox + nx * _pw }
    function py(ny) { return _oy + ny * _ph }
    function pw(n) { return n * _pw }
    function ph(n) { return n * _ph }

    Image {
        id: _img
        anchors.fill: parent
        source: Qt.resolvedUrl("images/xbox360_two_panel.jpg")
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        cache: true
        visible: status === Image.Ready
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 0
        text: _img.status === Image.Error ? "Xbox face image missing" : ("Xbox 360  " + padId)
        color: "#94a3b8"
        font.pixelSize: Style.dp(11)
        z: 4
    }

    // Always-visible outline; fills only when live.
    component Hotspot: Rectangle {
        property real nx
        property real ny
        property real nw
        property real nh
        property bool lit: false
        property color glow: "#22C55E"
        property color fill: "#6622C55E"

        x: px(nx) - pw(nw) * 0.5
        y: py(ny) - ph(nh) * 0.5
        width: pw(nw)
        height: ph(nh)
        color: lit ? fill : "#00000000"
        border.width: lit ? Style.dp(3) : Style.dp(2)
        border.color: lit ? glow : Qt.rgba(glow.r, glow.g, glow.b, 0.55)
        radius: Math.min(width, height) * 0.35
    }

    Hotspot { nx: 0.264; ny: 0.180; nw: 0.16; nh: 0.09; lit: on("left_shoulder"); glow: "#86EFAC"; fill: "#6622C55E"; radius: Style.dp(8) }
    Hotspot { nx: 0.763; ny: 0.179; nw: 0.16; nh: 0.09; lit: on("right_shoulder"); glow: "#86EFAC"; fill: "#6622C55E"; radius: Style.dp(8) }

    Hotspot {
        nx: 0.262; ny: 0.305; nw: 0.07
        nh: 0.13 + 0.04 * Math.min(1.0, Math.max(0.0, v("left_trigger")))
        lit: v("left_trigger") > 0.08
        glow: "#38BDF8"; fill: "#8838BDF8"; radius: Style.dp(6)
    }
    Hotspot {
        nx: 0.769; ny: 0.312; nw: 0.07
        nh: 0.13 + 0.04 * Math.min(1.0, Math.max(0.0, v("right_trigger")))
        lit: v("right_trigger") > 0.08
        glow: "#38BDF8"; fill: "#8838BDF8"; radius: Style.dp(6)
    }

    Item {
        x: px(0.292) - pw(0.12) * 0.5
        y: py(0.580) - pw(0.12) * 0.5
        width: pw(0.12); height: width
        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: on("left_thumb") ? "#3322C55E" : "#00000000"
            border.width: on("left_thumb") ? Style.dp(3) : Style.dp(2)
            border.color: on("left_thumb") ? "#22C55E" : "#99EAB308"
        }
        Rectangle {
            width: parent.width * 0.22
            height: width
            radius: width / 2
            color: "#f8fafc"
            opacity: 0.9
            x: (parent.width - width) * 0.5 + parent.width * 0.28 * Math.max(-1, Math.min(1, v("left_stick_x")))
            y: (parent.height - height) * 0.5 - parent.height * 0.28 * Math.max(-1, Math.min(1, v("left_stick_y")))
        }
    }

    Item {
        x: px(0.620) - pw(0.12) * 0.5
        y: py(0.728) - pw(0.12) * 0.5
        width: pw(0.12); height: width
        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: on("right_thumb") ? "#3322C55E" : "#00000000"
            border.width: on("right_thumb") ? Style.dp(3) : Style.dp(2)
            border.color: on("right_thumb") ? "#22C55E" : "#99EAB308"
        }
        Rectangle {
            width: parent.width * 0.22
            height: width
            radius: width / 2
            color: "#f8fafc"
            opacity: 0.9
            x: (parent.width - width) * 0.5 + parent.width * 0.28 * Math.max(-1, Math.min(1, v("right_stick_x")))
            y: (parent.height - height) * 0.5 - parent.height * 0.28 * Math.max(-1, Math.min(1, v("right_stick_y")))
        }
    }

    Hotspot { nx: 0.388; ny: 0.685; nw: 0.038; nh: 0.042; lit: on("dpad_up"); glow: "#f8fafc"; fill: "#66f8fafc"; radius: Style.dp(3) }
    Hotspot { nx: 0.388; ny: 0.775; nw: 0.038; nh: 0.042; lit: on("dpad_down"); glow: "#f8fafc"; fill: "#66f8fafc"; radius: Style.dp(3) }
    Hotspot { nx: 0.353; ny: 0.730; nw: 0.038; nh: 0.042; lit: on("dpad_left"); glow: "#f8fafc"; fill: "#66f8fafc"; radius: Style.dp(3) }
    Hotspot { nx: 0.423; ny: 0.730; nw: 0.038; nh: 0.042; lit: on("dpad_right"); glow: "#f8fafc"; fill: "#66f8fafc"; radius: Style.dp(3) }

    Hotspot { nx: 0.512; ny: 0.594; nw: 0.095; nh: 0.095 * _pw / _ph; lit: on("guide"); glow: "#4ade80"; fill: "#00000000"; radius: width / 2 }

    Hotspot { nx: 0.728; ny: 0.520; nw: 0.05; nh: 0.055 * _pw / _ph; lit: on("y"); glow: "#facc15"; fill: "#66fde047"; radius: width / 2 }
    Hotspot { nx: 0.782; ny: 0.586; nw: 0.05; nh: 0.055 * _pw / _ph; lit: on("b"); glow: "#f87171"; fill: "#66f87171"; radius: width / 2 }
    Hotspot { nx: 0.728; ny: 0.650; nw: 0.05; nh: 0.055 * _pw / _ph; lit: on("a"); glow: "#4ade80"; fill: "#664ade80"; radius: width / 2 }
    Hotspot { nx: 0.672; ny: 0.581; nw: 0.05; nh: 0.055 * _pw / _ph; lit: on("x"); glow: "#60a5fa"; fill: "#6660a5fa"; radius: width / 2 }

    Hotspot { nx: 0.428; ny: 0.592; nw: 0.045; nh: 0.032; lit: on("back"); glow: "#86EFAC"; fill: "#6622C55E"; radius: Style.dp(6) }
    Hotspot { nx: 0.596; ny: 0.592; nw: 0.045; nh: 0.032; lit: on("start"); glow: "#86EFAC"; fill: "#6622C55E"; radius: Style.dp(6) }
}
