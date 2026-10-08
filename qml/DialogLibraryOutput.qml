// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// Change vJoy Output (10 S30-S32): a stick keeps its bindings; only the vJoy
// they send to changes, one row per vJoy it sends to.
Dialog {
    id: _dlg
    objectName: "libraryOutputDialog"
    title: "Change vJoy Output"
    anchors.centerIn: Overlay.overlay
    width: Math.min(parent ? parent.width - Style.dp(40) : Style.dp(680), Style.dp(680))
    height: Math.min(implicitHeight, parent ? parent.height - Style.dp(20) : implicitHeight)
    modal: true

    property var lib: null
    property string key: ""
    property string name: ""
    property string guid: ""
    property var profiles: []
    // From the plan: [{vjoy, inputs, to, changes}], the vJoy numbers to pick
    // from, and the stick that sends to a target vJoy now.
    property var rows: []
    property var vjoys: []
    property var other: ({})
    property var moves: ({})
    property var warnings: []
    property int profileTicket: 0
    property int planTicket: 0

    readonly property bool anyChange: rows.some(r => r.changes === true)

    function openFor(d) {
        if (!lib)
            return
        key = d.deviceKey
        name = d.kind === "setup" ? d.deviceName : d.name
        guid = d.guid || ""
        rows = []
        vjoys = []
        other = {}
        moves = {}
        warnings = []
        _swapOther.checked = false
        profiles = []
        // The open profile always, ticked (S30, D-10-PROFILES).
        profileTicket = lib.profilesUsing([guid], true)
        open()
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
        if (!visible || !lib)
            return
        planTicket = lib.planOutput(key, moves, _swapOther.checked, chosenProfiles())
    }
    // A row's choices: the vJoys that exist, and the one it sends to now.
    function choices(vjoy) {
        var out = vjoys.slice()
        if (out.indexOf(vjoy) < 0)
            out.push(vjoy)
        return out.sort((a, b) => a - b)
    }
    function move(vjoy, to) {
        var m = Object.assign({}, moves)
        m[String(vjoy)] = to
        moves = m
        replan()
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
            } else if (res.op === "planOutput" && res.ticket === _dlg.planTicket) {
                if (!res.ok) {
                    _dlg.warnings = [res.error]
                    return
                }
                _dlg.rows = res.rows || []
                // S30: only the vJoy devices that exist.
                _dlg.vjoys = _dlg.lib.vjoyNumbers()
                // The sticks that send to a target vJoy now (LC's "others":
                // [{guid, name, vjoy, to, inputs}]), each with its own from
                // and to (S30).
                _dlg.other = { text: _dlg.lib.alsoMoveText(res.others || []) }
                _dlg.warnings = res.warnings || []
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

            Label {
                objectName: "libraryOutputLead"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: _dlg.name + " keeps its bindings; only where they send changes."
                color: Style.fg
            }

            RowLayout {
                Layout.fillWidth: true
                Label { text: "Change it in these profiles"; color: Style.fgSoft; Layout.fillWidth: true }
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

            ColumnLayout {
                objectName: "libraryOutputRows"
                spacing: Style.dp(6)
                RowLayout {
                    spacing: Style.dp(12)
                    Label { Layout.preferredWidth: Style.dp(150); text: "Sends to"; font.pixelSize: Style.dp(12); color: Style.fgMuted }
                    Item { Layout.preferredWidth: Style.dp(16) }
                    Label { text: "Send to"; font.pixelSize: Style.dp(12); color: Style.fgMuted }
                }
                Repeater {
                    model: _dlg.rows
                    delegate: RowLayout {
                        id: _vrow
                        required property var modelData
                        spacing: Style.dp(12)
                        Label {
                            Layout.preferredWidth: Style.dp(150)
                            text: "vJoy " + _vrow.modelData.vjoy + " (" + _vrow.modelData.inputs + " inputs)"
                            color: Style.fg
                        }
                        Label { Layout.preferredWidth: Style.dp(16); text: "→"; color: Style.fg }
                        ComboBox {
                            Layout.preferredWidth: Style.dp(150)
                            objectName: "libraryOutputTo_" + _vrow.modelData.vjoy
                            readonly property var numbers: _dlg.choices(_vrow.modelData.vjoy)
                            model: numbers.map(n => "vJoy " + n)
                            currentIndex: numbers.indexOf(_vrow.modelData.to)
                            onActivated: (i) => _dlg.move(_vrow.modelData.vjoy, numbers[i])
                        }
                        Label {
                            text: _vrow.modelData.changes ? "changes" : "stays"
                            font.pixelSize: Style.dp(12)
                            color: _vrow.modelData.changes ? Style.infoText : Style.fgMuted
                        }
                    }
                }
            }
            Label {
                visible: _dlg.rows.length === 0
                text: _dlg.profiles.length ? "Its bindings send to no vJoy in the ticked profiles." : "Reading the profiles…"
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }

            Label {
                objectName: "libraryOutputChecking"
                visible: _dlg.lib !== null && _dlg.lib.planning
                text: "Checking…"
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }
            // Its text wraps: it can name several sticks (S30).
            RowLayout {
                Layout.fillWidth: true
                visible: (_dlg.other.text || "").length > 0
                spacing: 0
                CheckBox {
                    id: _swapOther
                    objectName: "libraryOutputSwapOther"
                    Layout.alignment: Qt.AlignTop
                    // Read by screen readers; shown by the label beside it.
                    property string label: _dlg.other.text || ""
                    Accessible.name: label
                    onToggled: _dlg.replan()
                }
                Label {
                    objectName: "libraryOutputSwapOtherText"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    wrapMode: Text.Wrap
                    text: _swapOther.label
                    color: Style.fg
                    MouseArea {
                        anchors.fill: parent
                        onClicked: { _swapOther.toggle(); _swapOther.toggled() }
                    }
                }
            }

            Rectangle {
                objectName: "libraryOutputWarnings"
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
                        Label { text: "Check these"; font.bold: true; color: Style.fgStrong }
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
                text: "An autosave of each stick that changes is kept first, and Undo puts them back."
                font.pixelSize: Style.dp(12)
                color: Style.fgMuted
            }
        }
    }

    footer: DialogButtonBox {
        Button { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
        Button {
            objectName: "libraryOutputGo"
            text: "Change"
            highlighted: true
            enabled: _dlg.anyChange && _dlg.lib && !_dlg.lib.busy
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
        }
    }
    onAccepted: lib.changeOutput(key, moves, _swapOther.checked && _swapOther.visible, chosenProfiles())
}
