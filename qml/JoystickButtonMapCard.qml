// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import Gremlin.Device
import Gremlin.Style

Item {
    id: _root

    property string deviceGuid: ""
    property string title: ""
    property string pairLabel: ""
    property bool editing: false
    property var editorNodes: []
    property string photoOverride: ""
    readonly property var editorItem: _face.editorItem
    property alias zoom: _face.zoom
    property alias panX: _face.panX
    property alias panY: _face.panY
    readonly property alias viewPct: _face.viewPct
    readonly property alias zoomFit: _face.zoomFit
    readonly property alias zoomMin: _face.zoomMin
    readonly property alias zoomMax: _face.zoomMax
    function resetView() { _face.resetView() }
    function clampPan() { if (_face.clampPan) _face.clampPan() }

    property int axisStamp: _live && _live.axisStamp !== undefined ? _live.axisStamp : (_live ? _live.stamp : 0)
    property int buttonStamp: _live && _live.buttonStamp !== undefined ? _live.buttonStamp : (_live ? _live.stamp : 0)
    property int hatStamp: _live && _live.hatStamp !== undefined ? _live.hatStamp : (_live ? _live.stamp : 0)
    property int liveStamp: buttonStamp + axisStamp + hatStamp + _buttons.count + _axes.count + _hats.count

    PairLiveThrottle {
        id: _live
        guid: _root.deviceGuid
    }

    MappedButtonModel {
        id: _buttons
        guid: _root.deviceGuid
    }

    MappedAxisModel {
        id: _axes
        guid: _root.deviceGuid
    }

    MappedHatModel {
        id: _hats
        guid: _root.deviceGuid
    }

    HardwareProfile {
        id: _inventory
        onProfileLabelsChanged: _root.refreshChipRows()
    }

    // The pool rows. A live press only checks a cheap key (module file time,
    // profile generation, what the device reports); the module file and the
    // profile are read again only when it changed (07 RB8).
    property var chipRows: []
    property string _rowsKey: "\u0000"

    function refreshChipRows() {
        var key = _inventory.chipsKey(deviceGuid)
        if (key === _rowsKey)
            return
        _rowsKey = key
        chipRows = deviceGuid.length ? (_inventory.chips(deviceGuid) || []) : []
    }

    onLiveStampChanged: refreshChipRows()
    onDeviceGuidChanged: refreshChipRows()
    Component.onCompleted: refreshChipRows()

    function hwAxis(id) {
        if (!_live) {
            return 0
        }
        return axisStamp >= 0 ? _live.axisValue(id) : 0
    }
    function hwButton(id) {
        if (!_live) {
            return 0
        }
        return buttonStamp >= 0 ? _live.buttonValue(id) : 0
    }
    function hwHat(id) {
        if (!_live) {
            return 0
        }
        return hatStamp >= 0 ? _live.hatValue(id) : 0
    }

    VkbRigFace {
        id: _face
        anchors.fill: parent
        host: _root
        liveStamp: _root.liveStamp
        buttons: _buttons
        axes: _axes
        hats: _hats
        chipRows: _root.chipRows
        editing: _root.editing
        editorNodes: _root.editorNodes
        photoOverride: _root.photoOverride
    }
}
