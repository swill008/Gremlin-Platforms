// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Window

// Escape closes the tool window it is in (an open menu or list closes
// first). Not for windows a stick is used in: some sticks send Esc.
Shortcut {
    property Window host: null

    sequences: [StandardKey.Cancel]
    onActivated: if (host) host.close()
}
