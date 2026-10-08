// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// Swap with Another Stick (10 S26-S29): two sticks plugged in now trade the
// ticked parts; warnings for both directions.
Dialog {
    id: _dlg
    objectName: "librarySwapDialog"
    title: "Swap with Another Stick"
    anchors.centerIn: Overlay.overlay
    width: Math.min(parent ? parent.width - Style.dp(40) : Style.dp(680), Style.dp(680))
    height: Math.min(implicitHeight, parent ? parent.height - Style.dp(20) : implicitHeight)
    modal: true

    property var lib: null
    property string firstKey: ""
    property string firstName: ""
    property string firstGuid: ""
    property var sticks: []
    property var parts: ({})
    property var profiles: []
    property var warnings: []
    property int profileTicket: 0
    property int planTicket: 0

    readonly property var second: _other.currentIndex >= 0 && _other.currentIndex < sticks.length ? sticks[_other.currentIndex] : null

    function openFor(d) {
        if (!lib)
            return
        firstKey = d.deviceKey
        firstName = d.kind === "setup" ? d.deviceName : d.name
        firstGuid = d.guid || ""
        // The other sticks plugged in now; never the same stick (S29).
        sticks = lib.connectedSticks().filter(s => s.key !== firstKey)
        _other.currentIndex = sticks.length ? 0 : -1
        var defaults = lib.settings().default_parts || []
        var p = {}
        for (var j = 0; j < lib.partList.length; j++)
            p[lib.partList[j].key] = defaults.indexOf(lib.partList[j].key) >= 0
        parts = p
        warnings = []
        askProfiles()
        open()
    }

    function askProfiles() {
        profiles = []
        var guids = [firstGuid]
        if (second)
            guids.push(second.guid)
        // The open profile always, ticked (S27, D-10-PROFILES).
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
    function replan() {
        if (!visible || !second || !lib)
            return
        planTicket = lib.planSwap(firstKey, second.key, chosenParts(), chosenProfiles())
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
            } else if (res.op === "planSwap" && res.ticket === _dlg.planTicket) {
                _dlg.warnings = res.ok ? (res.warnings || []) : [res.error]
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

            RowLayout {
                Layout.fillWidth: true
                spacing: Style.dp(10)
                Label { objectName: "librarySwapFirst"; text: _dlg.firstName; font.bold: true; color: Style.fgStrong }
                Text { text: ""; font.family: Style.iconFont; font.pixelSize: Style.dp(16); color: Style.info }
                ComboBox {
                    id: _other
                    objectName: "librarySwapOther"
                    Layout.fillWidth: true
                    model: _dlg.sticks.map(s => s.label)
                    onActivated: _dlg.askProfiles()
                }
            }
            Label {
                text: _dlg.sticks.length ? "Both sticks must be plugged in. Each one gets the other's settings." : "No other stick is plugged in now."
                font.pixelSize: Style.dp(12)
                color: _dlg.sticks.length ? Style.fgMuted : Style.warn
            }

            Label { text: "What trades places"; font.bold: true; color: Style.fgStrong; Layout.topMargin: Style.dp(4) }
            Flow {
                Layout.fillWidth: true
                spacing: Style.dp(12)
                Repeater {
                    model: _dlg.lib ? _dlg.lib.partList : []
                    delegate: CheckBox {
                        required property var modelData
                        objectName: "librarySwapPart_" + modelData.key
                        text: modelData.label
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
                    Label { text: "Swap bindings in these profiles"; color: Style.fgSoft; Layout.fillWidth: true }
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
                    text: "Profiles that aren't open are changed and saved; History keeps each save."
                    font.pixelSize: Style.dp(12)
                    color: Style.fgMuted
                }
            }

            Label {
                objectName: "librarySwapChecking"
                visible: _dlg.lib !== null && _dlg.lib.planning
                text: "Checking…"
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }
            Rectangle {
                objectName: "librarySwapWarnings"
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
                        Label { text: "Some settings have nowhere to go"; font.bold: true; color: Style.fgStrong }
                    }
                    Repeater {
                        model: _dlg.warnings
                        delegate: Label {
                            required property var modelData
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            text: modelData
                            font.pixelSize: Style.dp(12)
                            color: Style.fg
                        }
                    }
                }
            }
            Label {
                text: "An autosave of each stick is kept first, and Undo puts both back."
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }
        }
    }

    footer: DialogButtonBox {
        Button { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
        Button {
            objectName: "librarySwapGo"
            text: "Swap"
            highlighted: true
            enabled: _dlg.second !== null && _dlg.chosenParts().length > 0 && _dlg.lib && !_dlg.lib.busy
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
        }
    }
    onAccepted: lib.swap(firstKey, second.key, chosenParts(), chosenProfiles())
}
