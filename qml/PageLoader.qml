// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick

// A page Loader that tells the Window trace (01 S176, D-01-WINDOW-TRACE)
// when its page loads, unloads or fails to load. Handlers set where it is
// used run as well as these.
Loader {
    // The page's glossary name, e.g. "Home", "Device Bindings".
    property string traceName: ""

    function _tell(what) {
        if (traceName !== "" && typeof windowTrace !== "undefined" && windowTrace)
            windowTrace.page(traceName, what)
    }

    onActiveChanged: {
        if (!active)
            _tell("unloaded")
    }
    onLoaded: _tell("loaded")
    onStatusChanged: {
        if (status === Loader.Error)
            _tell("failed to load")
    }
}
