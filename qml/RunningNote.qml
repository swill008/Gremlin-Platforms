// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// Shown at the top of a tool window while the profile runs: the window
// stays usable, and this says when its changes apply.
Label {
    // Module Setup: a saved module is used at once, also while running
    // (03 Q1, S36, S108). The other tool windows apply at the next Run (08 S100).
    property bool appliesAtOnce: false

    visible: !!(backend && backend.gremlinActive)
    Layout.fillWidth: true
    wrapMode: Text.WordWrap
    color: Style.warn
    font.pixelSize: Style.dp(12)
    text: appliesAtOnce
        ? "The profile is running. Saved changes work at once."
        : "The profile is running. Changes here take effect the next time it starts."
}
