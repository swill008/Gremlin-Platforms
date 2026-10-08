// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// Copy to Another Stick (10 S22-S25): From, To (sticks plugged in now),
// What to copy, the profiles and modes, and what won't copy.
Dialog {
    id: _dlg
    objectName: "libraryCopyDialog"
    title: "Copy to Another Stick"
    anchors.centerIn: Overlay.overlay
    width: Math.min(parent ? parent.width - Style.dp(40) : Style.dp(660), Style.dp(660))
    height: Math.min(implicitHeight, parent ? parent.height - Style.dp(20) : implicitHeight)
    modal: true

    property var lib: null
    property string sourceKey: ""
    property string sourceDevice: ""
    property string fromText: ""
    property string sourceGuid: ""
    // From a device's current settings (S22) rather than a saved setup.
    property bool isCurrent: false
    property var holds: []
    property var sticks: []
    property var parts: ({})
    property var profiles: []
    property var modes: []
    property var warnings: []
    property bool planned: false
    property int profileTicket: 0
    property int planTicket: 0

    readonly property var target: _to.currentIndex >= 0 && _to.currentIndex < sticks.length ? sticks[_to.currentIndex] : null

    // d: the window's details of a saved setup, or of a device (its
    // current settings: what it holds and its modes come with the plan).
    function openFor(d) {
        if (!lib)
            return
        isCurrent = d.kind === "device"
        sourceKey = d.key
        sourceDevice = d.deviceKey
        sourceGuid = d.guid || ""
        fromText = isCurrent ? d.name + "  ›  current settings" : d.deviceName + "  ›  " + d.name
        holds = isCurrent ? lib.partList.map(p => p.key) : (d.holds || [])
        var m = []
        for (var i = 0; i < (d.modes || []).length; i++)
            m.push({ name: d.modes[i], checked: true })
        modes = m
        var defaults = lib.settings().default_parts || []
        var p = {}
        for (var j = 0; j < lib.partList.length; j++) {
            var key = lib.partList[j].key
            p[key] = holds.indexOf(key) >= 0 && defaults.indexOf(key) >= 0
        }
        parts = p
        sticks = lib.connectedSticks()
        // Another stick first; the same stick last (putting an older setup back).
        var pick = 0
        for (var k = 0; k < sticks.length; k++) {
            if (sticks[k].key !== sourceDevice) { pick = k; break }
        }
        _to.currentIndex = sticks.length ? pick : -1
        warnings = []
        planned = false
        askProfiles()
        open()
    }

    function askProfiles() {
        profiles = []
        var guids = [sourceGuid]
        if (target)
            guids.push(target.guid)
        // The open profile always, ticked (S23, D-10-PROFILES).
        profileTicket = lib.profilesUsing(guids, true)
    }

    function chosenParts() {
        var out = []
        for (var k in parts)
            if (parts[k])
                out.push(k)
        return out
    }
    function chosenProfiles() {
        var out = []
        for (var i = 0; i < profiles.length; i++)
            // The open profile that was never saved has path "" (S33).
            if (profiles[i].checked && (profiles[i].path.length || profiles[i].open))
                out.push(profiles[i].path)
        return out
    }
    function chosenModes() {
        var out = []
        for (var i = 0; i < modes.length; i++)
            if (modes[i].checked)
                out.push(modes[i].name)
        return out
    }
    // Current settings: what they hold and the modes with bindings in the
    // ticked profiles, from the plan. True when that added modes (planned
    // again with them).
    function takeCurrent(res) {
        if (res.holds) {
            holds = res.holds
            var p = Object.assign({}, parts)
            for (var k in p)
                p[k] = p[k] && holds.indexOf(k) >= 0
            parts = p
        }
        var list = modes.slice()
        var added = false
        var found = res.sourceModes || []
        for (var i = 0; i < found.length; i++) {
            if (!list.some(m => m.name === found[i])) {
                list.push({ name: found[i], checked: true })
                added = true
            }
        }
        if (!added)
            return false
        modes = list
        replan()
        return true
    }
    function replan() {
        if (!visible || !target || !lib)
            return
        planned = false
        planTicket = lib.planCopy(sourceKey, target.key, chosenParts(), chosenProfiles(), chosenModes())
    }

    Connections {
        target: _dlg.lib
        function onResult(res) {
            if (res.op === "profiles" && res.ticket === _dlg.profileTicket) {
                var list = []
                for (var i = 0; i < (res.profiles || []).length; i++) {
                    var p = res.profiles[i]
                    list.push({ name: p.name, path: p.path, open: p.open === true, checked: p.open === true })
                }
                _dlg.profiles = list
                _dlg.replan()
            } else if (res.op === "planCopy" && res.ticket === _dlg.planTicket) {
                if (res.ok && _dlg.isCurrent && _dlg.takeCurrent(res))
                    return
                _dlg.warnings = res.ok ? (res.warnings || []) : [res.error]
                _dlg.planned = true
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Style.dp(8)

            GridLayout {
                columns: 2
                Layout.fillWidth: true
                columnSpacing: Style.dp(16)
                Label { text: "From"; color: Style.fgSoft }
                Label { objectName: "libraryCopyFrom"; text: _dlg.fromText; font.bold: true; color: Style.fgStrong }
                Label { text: "To"; color: Style.fgSoft }
                ComboBox {
                    id: _to
                    objectName: "libraryCopyTo"
                    Layout.fillWidth: true
                    model: _dlg.sticks.map(s => s.label)
                    onActivated: _dlg.askProfiles()
                }
            }
            Label {
                text: _dlg.sticks.length ? "Only sticks plugged in now are listed." : "No stick is plugged in now: plug one in to copy onto it."
                font.pixelSize: Style.dp(12)
                color: _dlg.sticks.length ? Style.fgMuted : Style.warn
            }

            Label { text: "What to copy"; font.bold: true; color: Style.fgStrong; Layout.topMargin: Style.dp(4) }
            Flow {
                Layout.fillWidth: true
                spacing: Style.dp(12)
                Repeater {
                    model: _dlg.lib ? _dlg.lib.partList : []
                    delegate: CheckBox {
                        required property var modelData
                        objectName: "libraryCopyPart_" + modelData.key
                        text: modelData.label
                        enabled: _dlg.holds.indexOf(modelData.key) >= 0
                        checked: _dlg.parts[modelData.key] === true
                        onToggled: {
                            var p = Object.assign({}, _dlg.parts)
                            p[modelData.key] = checked
                            _dlg.parts = p
                            _dlg.replan()
                        }
                    }
                }
            }

            ColumnLayout {
                visible: _dlg.parts["bindings"] === true
                Layout.fillWidth: true
                Layout.leftMargin: Style.dp(24)
                spacing: Style.dp(2)
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Bindings go into these profiles"; color: Style.fgSoft; Layout.fillWidth: true }
                    Button {
                        text: "Tick All"
                        flat: true
                        font.pixelSize: Style.dp(12)
                        onClicked: {
                            _dlg.profiles = _dlg.profiles.map(p => Object.assign({}, p, { checked: true }))
                            _dlg.replan()
                        }
                    }
                }
                Repeater {
                    model: _dlg.profiles
                    delegate: CheckBox {
                        required property var modelData
                        required property int index
                        text: modelData.name + (modelData.open ? "  (open)" : "")
                        checked: modelData.checked
                        onToggled: {
                            var list = _dlg.profiles.slice()
                            list[index] = Object.assign({}, list[index], { checked: checked })
                            _dlg.profiles = list
                            _dlg.replan()
                        }
                    }
                }
                Label {
                    visible: _dlg.profiles.length === 0
                    text: "Reading the profiles…"
                    font.pixelSize: Style.dp(12)
                    color: Style.fgMuted
                }
                Label {
                    text: "Profiles that aren't open are changed and saved; History keeps each save."
                    font.pixelSize: Style.dp(12)
                    color: Style.fgMuted
                }
                RowLayout {
                    visible: _dlg.modes.length > 0
                    spacing: Style.dp(12)
                    Label { text: "Modes"; color: Style.fgSoft }
                    Repeater {
                        model: _dlg.modes
                        delegate: CheckBox {
                            required property var modelData
                            required property int index
                            text: modelData.name
                            checked: modelData.checked
                            onToggled: {
                                var list = _dlg.modes.slice()
                                list[index] = Object.assign({}, list[index], { checked: checked })
                                _dlg.modes = list
                                _dlg.replan()
                            }
                        }
                    }
                }
            }

            Label {
                objectName: "libraryCopyChecking"
                visible: _dlg.lib !== null && _dlg.lib.planning
                text: "Checking…"
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }
            // What won't copy (S23).
            Rectangle {
                objectName: "libraryCopyWarnings"
                visible: _dlg.warnings.length > 0
                Layout.fillWidth: true
                implicitHeight: _warn.implicitHeight + Style.dp(20)
                color: Style.bgWell
                border.color: Style.warn
                radius: Style.dp(4)
                ColumnLayout {
                    id: _warn
                    anchors.fill: parent
                    anchors.margins: Style.dp(10)
                    spacing: Style.dp(2)
                    RowLayout {
                        Text { text: ""; font.family: Style.iconFont; color: Style.warn }
                        Label {
                            text: _dlg.warnings.length === 1 ? "1 thing won't copy" : _dlg.warnings.length + " things won't copy"
                            font.bold: true
                            color: Style.fgStrong
                        }
                    }
                    Repeater {
                        model: _dlg.warnings
                        delegate: Label {
                            required property var modelData
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            text: "•  " + modelData
                            font.pixelSize: Style.dp(12)
                            color: Style.fg
                        }
                    }
                }
            }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                visible: _dlg.target !== null
                text: (_dlg.target ? _dlg.target.name : "") + "'s settings are replaced. An autosave of them is kept first, and Undo puts them back."
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }
        }
    }

    footer: DialogButtonBox {
        Button { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
        Button {
            objectName: "libraryCopyGo"
            text: "Copy"
            highlighted: true
            enabled: _dlg.target !== null && _dlg.chosenParts().length > 0 && _dlg.lib && !_dlg.lib.busy
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
        }
    }
    onAccepted: lib.copy(sourceKey, target.key, chosenParts(), chosenProfiles(), chosenModes())
}
