// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

.import "helpers.js" as Helpers

// Opens the Device Library window (10 S2), or brings it to the front, on
// a device and one of its dialogs: action "" (just the window), "copy",
// "swap" or "output" (the card menu items, 03 S88).
function openDeviceLibrary(deviceName, guid, action)
{
    var window = Helpers.createComponent("WindowDeviceLibrary.qml")
    if (window && typeof window.openOn === "function")
        window.openOn(String(deviceName || ""), String(guid || ""), String(action || ""))
    return window
}
