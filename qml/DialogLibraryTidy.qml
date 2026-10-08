// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// Tidy Library (10 S38): lists what it would remove (autosaves older than a
// number of months, deleted devices with no saved setups) and removes only
// what is still ticked, after Remove.
Dialog {
    id: _dlg
    objectName: "libraryTidyDialog"
    title: "Tidy Library"
    anchors.centerIn: Overlay.overlay
    width: Math.min(parent ? parent.width - Style.dp(40) : Style.dp(600), Style.dp(600))
    height: Math.min(implicitHeight, parent ? parent.height - Style.dp(20) : implicitHeight)
    modal: true

    property var lib: null
    property var items: []

    readonly property var ticked: items.filter(i => i.checked)
    readonly property int tickedBytes: ticked.reduce((n, i) => n + (i.bytes || 0), 0)

    function openNow() {
        if (!lib)
            return
        _months.value = 6
        preview()
        open()
    }
    function preview() {
        var list = lib.tidyPreview(_months.value)
        items = list.map(i => Object.assign({}, i, { checked: true }))
    }
    function sizeText(n) {
        if (n < 1024 * 1024)
            return Math.max(1, Math.round(n / 1024)) + " KB"
        return (n / (1024 * 1024)).toFixed(1) + " MB"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Style.dp(8)

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(10)
            Label { text: "Autosaves older than"; color: Style.fg }
            SpinBox {
                id: _months
                objectName: "libraryTidyMonths"
                from: 1
                to: 60
                value: 6
                editable: true
                onValueModified: _dlg.preview()
            }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "months, and deleted devices with no saved setups"; color: Style.fg }
        }

        ListView {
            id: _list
            objectName: "libraryTidyList"
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(220)
            clip: true
            model: _dlg.items
            ScrollBar.vertical: ScrollBar {}
            delegate: RowLayout {
                required property var modelData
                required property int index
                width: ListView.view.width
                CheckBox {
                    Layout.fillWidth: true
                    text: modelData.label
                    checked: modelData.checked
                    onToggled: {
                        var list = _dlg.items.slice()
                        list[index] = Object.assign({}, list[index], { checked: checked })
                        _dlg.items = list
                    }
                }
                Label { text: _dlg.sizeText(modelData.bytes || 0); font.pixelSize: Style.dp(12); color: Style.fgMuted }
            }
            Label {
                anchors.centerIn: parent
                visible: _dlg.items.length === 0
                text: "Nothing to tidy."
                color: Style.fgMuted
            }
        }
        Label {
            objectName: "libraryTidySummary"
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: _dlg.ticked.length
                  ? _dlg.ticked.length + (_dlg.ticked.length === 1 ? " item" : " items") + " ticked ("
                    + _dlg.sizeText(_dlg.tickedBytes) + "). Nothing is removed until you press Remove."
                  : "Nothing is ticked."
            font.pixelSize: Style.dp(12)
            color: Style.fgMuted
        }
    }

    footer: DialogButtonBox {
        Button { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
        Button {
            id: _remove
            objectName: "libraryTidyRemove"
            text: "Remove"
            enabled: _dlg.ticked.length > 0 && _dlg.lib && !_dlg.lib.busy
            contentItem: Label {
                text: _remove.text
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: _remove.enabled ? Style.dangerText : Style.fgDisabled
            }
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
        }
    }
    onAccepted: lib.tidy(ticked.map(i => i.key))
}
