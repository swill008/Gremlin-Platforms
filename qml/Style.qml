// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

pragma Singleton

import QtQuick
import QtQuick.Controls.Universal

Item {
    function removeAlpha(color) {
        return Qt.rgba(color.r, color.g, color.b, 1.0)
    }

    property bool isDarkMode: false

    // Color definitions.
    property var accent: Universal.accent
    property var theme: isDarkMode ? Universal.Dark : Universal.Light
    property var background: isDarkMode ? Universal.foreground : Universal.background
    property var foreground: isDarkMode ? Universal.background : Universal.foreground
    property var backgroundShade: isDarkMode ? Qt.tint(background, "#40ffffff") : Qt.tint(foreground, "#b0ffffff")
    property var lowColor: isDarkMode ? Qt.hsva(0.0, 0.0, 0.2, 1.0) : Qt.hsva(0.0, 0.0, 0.8, 1.0)
    property var medColor: isDarkMode ? Qt.hsva(0.0, 0.0, 0.4, 1.0) : Qt.hsva(0.0, 0.0, 0.6, 1.0)
    property var error: "#A20025"
    property var warning: "#F0A30A"

    // Colour tokens for the app's own screens. Dark values are the palette
    // those screens were drawn with; light values are the same roles for a
    // light page. Use a token, never a colour literal, so Dark mode switches
    // every screen.
    readonly property var _dark: ({
        bgWell: "#09090B", bgPage: "#111113", bgCard: "#18181B",
        bgRaised: "#27272A", bgSelected: "#1F2A37",
        line: "#3F3F46", lineStrong: "#52525B",
        fgStrong: "#F4F4F5", fg: "#E4E4E7", fgSoft: "#D4D4D8",
        fgMuted: "#A1A1AA", fgDisabled: "#71717A",
        ok: "#22C55E", okStrong: "#16A34A", okBright: "#4ADE80",
        okText: "#86EFAC", okTextStrong: "#BBF7D0",
        okFill: "#14532D", okFillDeep: "#052E16",
        warn: "#FBBF24",
        danger: "#DC2626", dangerHover: "#B91C1C",
        dangerText: "#F87171", dangerTextSoft: "#FCA5A5", dangerFill: "#7F1D1D",
        info: "#3B82F6", infoText: "#60A5FA", live: "#38BDF8",
        infoFill: "#1E3A5F", infoFillDeep: "#0F2744"
    })
    readonly property var _light: ({
        bgWell: "#F4F4F5", bgPage: "#FAFAFA", bgCard: "#FFFFFF",
        bgRaised: "#F4F4F5", bgSelected: "#DBEAFE",
        line: "#D4D4D8", lineStrong: "#A1A1AA",
        fgStrong: "#09090B", fg: "#18181B", fgSoft: "#3F3F46",
        fgMuted: "#52525B", fgDisabled: "#A1A1AA",
        ok: "#16A34A", okStrong: "#15803D", okBright: "#16A34A",
        okText: "#15803D", okTextStrong: "#14532D",
        okFill: "#DCFCE7", okFillDeep: "#F0FDF4",
        warn: "#D97706",
        danger: "#DC2626", dangerHover: "#B91C1C",
        dangerText: "#DC2626", dangerTextSoft: "#B91C1C", dangerFill: "#FEE2E2",
        info: "#2563EB", infoText: "#2563EB", live: "#0284C7",
        infoFill: "#DBEAFE", infoFillDeep: "#EFF6FF"
    })
    readonly property var _scheme: isDarkMode ? _dark : _light

    // Surfaces, from recessed to raised.
    readonly property color bgWell: _scheme.bgWell
    readonly property color bgPage: _scheme.bgPage
    readonly property color bgCard: _scheme.bgCard
    readonly property color bgRaised: _scheme.bgRaised
    readonly property color bgSelected: _scheme.bgSelected
    readonly property color line: _scheme.line
    readonly property color lineStrong: _scheme.lineStrong
    // Text.
    readonly property color fgStrong: _scheme.fgStrong
    readonly property color fg: _scheme.fg
    readonly property color fgSoft: _scheme.fgSoft
    readonly property color fgMuted: _scheme.fgMuted
    readonly property color fgDisabled: _scheme.fgDisabled
    // Text on a saturated fill, and on a light swatch, in both modes.
    readonly property color onColor: "#FFFFFF"
    readonly property color onLight: "#111111"
    readonly property color clear: "#00000000"
    // Backdrop behind a modal dialog.
    readonly property color dim: "#66000000"
    // Delete buttons: white text on red in both modes.
    readonly property color dangerPressed: "#991B1B"
    readonly property color dangerBright: "#EF4444"
    // Status: live/claimed (ok), highlight (warn), delete/error (danger), info.
    readonly property color ok: _scheme.ok
    readonly property color okStrong: _scheme.okStrong
    readonly property color okBright: _scheme.okBright
    readonly property color okText: _scheme.okText
    readonly property color okTextStrong: _scheme.okTextStrong
    readonly property color okFill: _scheme.okFill
    readonly property color okFillDeep: _scheme.okFillDeep
    readonly property color warn: _scheme.warn
    readonly property color danger: _scheme.danger
    readonly property color dangerHover: _scheme.dangerHover
    readonly property color dangerText: _scheme.dangerText
    readonly property color dangerTextSoft: _scheme.dangerTextSoft
    readonly property color dangerFill: _scheme.dangerFill
    readonly property color info: _scheme.info
    readonly property color infoText: _scheme.infoText
    readonly property color live: _scheme.live
    readonly property color infoFill: _scheme.infoFill
    readonly property color infoFillDeep: _scheme.infoFillDeep

    // A token with transparency, e.g. Style.alpha(Style.ok, 0.4).
    function alpha(c, a) {
        return Qt.rgba(c.r, c.g, c.b, a)
    }

    // Spinbox presets.
    property int decimalsPrecise: 4
    property int decimalsStandard: 2

    // UI scale in percent. It follows the Options slider when Windows scaling
    // is disabled and stays at 100 otherwise.
    readonly property int uiScale: backend ? backend.uiScale : 100

    // Converts a size given at 100% into pixels at the current UI scale.
    function dp(x) {
        return Math.round(x * uiScale / 100)
    }

    // Program text size in pixels.
    readonly property int fontSize: dp(15)

    // Various shared dimensions.
    property int tooltipMaxWidth: dp(500)
    property int tooltipDelayMs: 500
}
