// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.pragma library

// Tool windows open right now, by file name. Shared by every helpers.js copy.
var openWindows = {}

// Keeps a window made outside helpers.js in the list (Module Setup, opened
// by Main.qml): name is its file name, window null takes it off.
function track(name, window)
{
    if (window)
        openWindows[name] = window
    else
        delete openWindows[name]
}
