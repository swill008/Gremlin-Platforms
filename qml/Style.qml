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
    property var background: isDarkMode ? Universal.foreground : _light.window
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
        bgRaised: "#27272A", bgSelected: "#1F2A37", bgHover: "#2F4B6B",
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
        infoFill: "#1E3A5F", infoFillDeep: "#0F2744",
        alert: "#F97316", noteFill: "#8A7A2A", noteLine: "#C4B44A",
        onLive: "#0B1220"
    })
    // Light mode is a grey mode: no white surfaces, cards a little lighter
    // than the window, status colours a step darker to read on grey.
    readonly property var _light: ({
        window: "#AAAAAD",
        bgWell: "#A0A0A4", bgPage: "#A4A4A8", bgCard: "#B5B5B8",
        bgRaised: "#ADADB0", bgSelected: "#99A6B8", bgHover: "#8FA6C4",
        line: "#86868D", lineStrong: "#6A6A72",
        fgStrong: "#09090B", fg: "#18181B", fgSoft: "#303036",
        fgMuted: "#36363C", fgDisabled: "#5A5A62",
        ok: "#166534", okStrong: "#14532D", okBright: "#166534",
        okText: "#14532D", okTextStrong: "#052E16",
        okFill: "#99B6A2", okFillDeep: "#A6BAAC",
        warn: "#92400E",
        danger: "#DC2626", dangerHover: "#B91C1C",
        dangerText: "#991B1B", dangerTextSoft: "#7F1D1D", dangerFill: "#BCA0A0",
        info: "#1E40AF", infoText: "#1E40AF", live: "#075985",
        infoFill: "#9CAABE", infoFillDeep: "#A6AFBD",
        alert: "#9A3412", noteFill: "#B8B085", noteLine: "#8A6D05",
        onLive: "#FFFFFF",
        // Built-in controls, which are white in stock light mode.
        field: "#B8B8BA", popup: "#B2B2B5", item: "#99B6B6B9", scroll: "#9D9DA1",
        bar: "#A0A0A4"
    })
    readonly property var _scheme: isDarkMode ? _dark : _light

    // Surfaces, from recessed to raised.
    readonly property color bgWell: _scheme.bgWell
    readonly property color bgPage: _scheme.bgPage
    readonly property color bgCard: _scheme.bgCard
    readonly property color bgRaised: _scheme.bgRaised
    readonly property color bgSelected: _scheme.bgSelected
    // Under the pointer (or the keyboard) in menus: clearly set apart from
    // the raised surface they sit on.
    readonly property color bgHover: _scheme.bgHover
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
    // A button drawn over a device photo: the same in both themes (the
    // photos are dark), white text on see-through black.
    readonly property color photoButton: "#99000000"
    readonly property color photoButtonHover: "#CC000000"
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
    // Something needs attention (e.g. a missing driver).
    readonly property color alert: _scheme.alert
    // Help notes: a yellow box with dark text in both modes.
    readonly property color noteFill: _scheme.noteFill
    readonly property color noteLine: _scheme.noteLine
    readonly property color noteText: "#1B1B1B"
    // Text on a live (sky blue) fill.
    readonly property color onLive: _scheme.onLive
    // Line colours for axis charts; readable on light and dark.
    readonly property var series: [
        "#1f77b4", "#d62728", "#2ca02c", "#ff7f0e",
        "#7f7f7f", "#bcbd22", "#17becf", "#9467bd",
    ]

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

    // A window size (already scaled) limited to the screen the window is on,
    // so a large UI scale never makes a window, or its smallest size, bigger
    // than the screen. Pass the window's Screen attached object.
    function fitWidth(w, screen) {
        if (!screen || !(screen.desktopAvailableWidth > 0))
            return w
        var room = Math.min(screen.width > 0 ? screen.width : Infinity, screen.desktopAvailableWidth)
        return Math.min(w, Math.max(640, room - 40))
    }
    function fitHeight(h, screen) {
        if (!screen || !(screen.desktopAvailableHeight > 0))
            return h
        var room = Math.min(screen.height > 0 ? screen.height : Infinity, screen.desktopAvailableHeight)
        return Math.min(h, Math.max(480, room - 60))
    }

    // Program text size in pixels.
    readonly property int fontSize: dp(15)

    // Menus, dropdown lists and the command palette (Gremlin.Menus): one look
    // everywhere, the Button Map's. A raised surface with a strong line, rows
    // that light up under the pointer with an accent bar on the left.
    readonly property color menuBg: bgRaised
    readonly property color menuLine: lineStrong
    readonly property color menuDivider: line
    readonly property color menuHover: bgHover
    readonly property color menuAccent: accent
    readonly property color menuText: fg
    readonly property color menuTextStrong: fgStrong
    readonly property color menuTextSoft: fgSoft
    readonly property color menuTextOff: fgDisabled
    readonly property color menuHint: fgMuted
    readonly property color menuDanger: dangerText
    readonly property int menuRowH: dp(24)
    readonly property int menuTextPx: dp(13)
    readonly property int menuRadius: dp(6)
    readonly property int menuPad: dp(4)
    readonly property int menuWidth: dp(300)
    readonly property int menuBarW: dp(3)
    readonly property int menuIndent: dp(22)

    // Various shared dimensions.
    property int tooltipMaxWidth: dp(500)
    property int tooltipDelayMs: 500
}
