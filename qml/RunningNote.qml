// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// Shown at the top of a tool window while the profile runs: the window
// stays usable, and this says when its changes apply.
Label {
    visible: !!(backend && backend.gremlinActive)
    Layout.fillWidth: true
    wrapMode: Text.WordWrap
    color: Style.warn
    font.pixelSize: Style.dp(12)
    text: "The profile is running. Changes here take effect the next time it starts."
}
