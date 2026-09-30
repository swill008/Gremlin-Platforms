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

    // Various shared dimensions.
    property int tooltipMaxWidth: 500
    property int tooltipDelayMs: 500

    property int uiScale: 100

    function setUiScale(value) {
        var n = Math.round(Number(value))
        if (isNaN(n))
            n = 100
        if (n < 70)
            n = 70
        if (n > 200)
            n = 200
        if (n === uiScale)
            return
        uiScale = n
    }
}
