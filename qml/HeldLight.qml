// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

// A light that stays on for at least minimumMs once switched on, so a press
// shorter than one redraw is still seen (upstream 736129eb). A held press
// stays lit as long as it is held.
QtObject {
    property bool on: false
    property int minimumMs: 100
    // On, or switched on within the last minimumMs.
    readonly property bool shown: on || _hold.running

    onOnChanged: if (on) _hold.restart()

    property Timer _hold: Timer { interval: minimumMs }
}
