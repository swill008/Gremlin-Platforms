// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Window
import Gremlin.UI

Item {
    id: _mem
    property Window host: null
    property string name: ""
    property int defaultWidth: 800
    property int defaultHeight: 600

    WindowPlacement { id: _place }

    function restore() {
        if (host && name.length)
            _place.restoreTool(host, name, defaultWidth, defaultHeight)
    }

    function save() {
        if (host && name.length)
            _place.saveTool(host, name)
    }

    Component.onCompleted: restore()

    Connections {
        target: host
        function onClosing() { _mem.save() }
        function onWidthChanged() { if (host && host.visible) _timer.restart() }
        function onHeightChanged() { if (host && host.visible) _timer.restart() }
    }

    Timer {
        id: _timer
        interval: 400
        repeat: false
        onTriggered: _mem.save()
    }
}
