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
