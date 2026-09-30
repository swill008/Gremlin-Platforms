// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls.Universal as U
import Gremlin.Style

Item {
    objectName: "colorInformation"

    U.Universal.theme: Style.theme

    // Capture color values of interest from the Universal theme to expose to
    // Python.
    property color accent: U.Universal.accent
    property color background: U.Universal.background
    property color foreground: U.Universal.foreground
    property bool isDarkTheme: U.Universal.theme === U.Universal.Dark
}
