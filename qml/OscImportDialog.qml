// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style

// Import (09 S162): OSC messages typed or pasted one per line, or read from
// a file: a .txt fills the box, a TouchOSC layout (.tosc) shows a preview
// list with check boxes; OK adds the ticked controls through the same add
// path (existing ones are skipped) and the page shows the added/skipped report.
Popup {
    id: _root

    // OscDeviceManagementModel: previewTouchOsc / readImportText.
    property var deviceModel: null
    // The TouchOSC file being previewed ("" = the typed messages).
    property string toscPath: ""
    property string toscName: ""
    // previewTouchOsc's rows ({index, address, label, mode, kindText,
    // ticked, exists}) and skipped notes.
    property var toscRows: []
    property var toscSkipped: []
    // index -> ticked
    property var _ticked: ({})
    readonly property bool previewing: toscPath.length > 0
    readonly property var chosen: {
        var out = []
        for (var i = 0; i < toscRows.length; i++) {
            var row = toscRows[i]
            if (!row.exists && _ticked[row.index] === true)
                out.push(row.index)
        }
        return out
    }
    readonly property int addable: toscRows.filter(function(r) { return !r.exists }).length

    signal accepted(string text)
    signal touchOscAccepted(string path, var chosen)
    // The page's file chooser (.txt or .tosc); its pick comes back to loadFile().
    signal chooseFileRequested()

    parent: Overlay.overlay
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Style.dp(16)
    width: previewing ? Style.dp(620) : Style.dp(460)

    // A Button Map card (osc_style.md): card fill, strong line, round corners.
    background: Rectangle {
        color: Style.bgCard
        border.color: Style.lineStrong
        border.width: 1
        radius: Style.dp(8)
    }

    function resetFields() {
        _messages.text = ""
        _backToText()
        _error.clear()
    }

    function _backToText() {
        toscPath = ""
        toscName = ""
        toscRows = []
        toscSkipped = []
        _ticked = ({})
    }

    // From TouchOSC Layout… and Choose File…: the file chooser.
    function chooseFile() {
        chooseFileRequested()
    }

    function _fileName(path) {
        var text = decodeURIComponent(String(path)).replace(/\\/g, "/")
        return text.substring(text.lastIndexOf("/") + 1)
    }

    // A chosen file: .tosc -> the preview list; anything else -> its lines
    // in the box.
    function loadFile(path) {
        _error.clear()
        var text = String(path)
        if (/\.tosc$/i.test(text))
            return previewTouchOsc(text)
        if (!deviceModel || typeof deviceModel.readImportText !== "function") {
            _error.show("This file can't be read here. Paste its lines into the box.", true)
            return false
        }
        var got = deviceModel.readImportText(text) || {}
        if (got.error && String(got.error).length) {
            _error.show(String(got.error), true)
            return false
        }
        _backToText()
        _messages.text = String(got.text || "")
        return true
    }

    function previewTouchOsc(path) {
        if (!deviceModel)
            return false
        var res = deviceModel.previewTouchOsc(String(path)) || {}
        if (res.error && String(res.error).length) {
            _error.show(String(res.error), true)
            return false
        }
        var rows = res.rows || []
        var ticked = {}
        for (var i = 0; i < rows.length; i++)
            ticked[rows[i].index] = rows[i].ticked === true && !rows[i].exists
        toscRows = rows
        toscSkipped = res.skipped || []
        _ticked = ticked
        toscName = _fileName(path)
        toscPath = String(path)
        return true
    }

    function setTicked(index, on) {
        var next = Object.assign({}, _ticked)
        next[index] = on
        _ticked = next
    }

    function tickAll(on) {
        var next = {}
        for (var i = 0; i < toscRows.length; i++)
            next[toscRows[i].index] = on && !toscRows[i].exists
        _ticked = next
    }

    function accept() {
        if (previewing) {
            if (chosen.length === 0)
                return false
            touchOscAccepted(toscPath, chosen)
        } else {
            accepted(_messages.text)
        }
        close()
        return true
    }

    contentItem: ColumnLayout {
        spacing: Style.dp(10)

        Label {
            objectName: "oscImportTitle"
            text: _root.previewing ? "TouchOSC layout: " + _root.toscName : "New OSC messages:"
            font.bold: true
            font.pixelSize: Style.dp(16)
            color: Style.fgStrong
            elide: Text.ElideMiddle
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Style.dp(8)
            Button {
                objectName: "oscImportFile"
                text: "Choose File…"
                onClicked: _root.chooseFile()
            }
            Label {
                text: "A text file (.txt), one message per line, or a TouchOSC layout (.tosc)."
                color: Style.fgMuted
                font.pixelSize: Style.dp(12)
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        TextArea {
            id: _messages
            objectName: "oscImportText"
            visible: !_root.previewing
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(90)
            wrapMode: TextEdit.NoWrap
            placeholderText: "/button/1"
        }

        Rectangle {
            visible: !_root.previewing
            Layout.fillWidth: true
            implicitHeight: _help.implicitHeight + Style.dp(16)
            color: Style.noteFill
            border.color: Style.noteLine
            radius: Style.dp(4)

            Label {
                id: _help
                anchors.fill: parent
                anchors.margins: Style.dp(8)
                wrapMode: Text.WordWrap
                color: Style.noteText
                objectName: "oscImportHelp"
                text: "Enter new OSC messages one per line.\n" +
                      "Messages must start with a forward slash (/).\n" +
                      "Add a suffix after a space or a comma to set the type, such as /osc_msg A or /osc_msg, A. " +
                      "A: axis. B: button (0 = released, not 0 = pressed). BNP: button that presses on each message and releases after the delay. " +
                      "C: change (presses when the value changes). E: encoder, added as an encoder axis (format Auto). " +
                      "No suffix: button. An unknown suffix is added as a button and named in the result.\n" +
                      "Messages already in the list are skipped."
            }
        }

        // The TouchOSC preview (S162): one row per input it would add.
        RowLayout {
            visible: _root.previewing
            Layout.fillWidth: true
            spacing: Style.dp(8)
            Label {
                objectName: "oscToscCount"
                text: _root.chosen.length + " of " + _root.addable + " ticked"
                color: Style.fgMuted
                Layout.fillWidth: true
            }
            Button {
                objectName: "oscToscTickAll"
                text: "Tick All"
                implicitHeight: Style.dp(28)
                onClicked: _root.tickAll(true)
            }
            Button {
                objectName: "oscToscTickNone"
                text: "Tick None"
                implicitHeight: Style.dp(28)
                onClicked: _root.tickAll(false)
            }
        }

        Rectangle {
            visible: _root.previewing
            Layout.fillWidth: true
            Layout.preferredHeight: Style.dp(300)
            color: Style.bgWell
            border.color: Style.line
            border.width: 1
            radius: Style.dp(4)
            clip: true

            ListView {
                id: _toscList
                objectName: "oscToscList"
                anchors.fill: parent
                anchors.margins: 1
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: _root.toscRows
                ScrollBar.vertical: ScrollBar {
                    policy: _toscList.contentHeight > _toscList.height ? ScrollBar.AsNeeded
                                                                       : ScrollBar.AlwaysOff
                }

                delegate: Rectangle {
                    id: _toscRow
                    required property var modelData
                    required property int index
                    width: ListView.view.width
                    height: Style.dp(30)
                    color: _toscHover.hovered ? Style.bgRaised : Style.clear
                    HoverHandler { id: _toscHover }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Style.dp(6)
                        anchors.rightMargin: Style.dp(10)
                        spacing: Style.dp(8)
                        CheckBox {
                            objectName: "oscToscTick" + _toscRow.index
                            enabled: !_toscRow.modelData.exists
                            checked: _root._ticked[_toscRow.modelData.index] === true
                            onClicked: _root.setTicked(_toscRow.modelData.index, checked)
                        }
                        Label {
                            text: _toscRow.modelData.label
                            color: _toscRow.modelData.exists ? Style.fgMuted : Style.fg
                            elide: Text.ElideRight
                            Layout.preferredWidth: Style.dp(170)
                        }
                        Label {
                            text: _toscRow.modelData.address
                            font.family: Style.monoFont
                            font.pixelSize: Style.dp(12)
                            color: _toscRow.modelData.exists ? Style.fgMuted : Style.fgStrong
                            elide: Text.ElideMiddle
                            Layout.fillWidth: true
                        }
                        Label {
                            text: _toscRow.modelData.exists ? "already in the list"
                                                            : _toscRow.modelData.kindText
                            color: Style.fgMuted
                            font.italic: _toscRow.modelData.exists
                            font.pixelSize: Style.dp(12)
                        }
                    }
                }
            }

            EmptyState {
                anchors.centerIn: parent
                visible: _root.toscRows.length === 0
                text: "This layout has no controls that send OSC."
            }
        }

        // What the layout leaves out, one note per control.
        Label {
            objectName: "oscToscSkipped"
            visible: _root.previewing && _root.toscSkipped.length > 0
            text: "Skipped: " + _root.toscSkipped.join("; ")
            color: Style.fgMuted
            font.pixelSize: Style.dp(12)
            wrapMode: Text.WordWrap
            maximumLineCount: 4
            elide: Text.ElideRight
            Layout.fillWidth: true
        }

        MessageLine {
            id: _error
            objectName: "oscImportError"
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Button {
                objectName: "oscImportBack"
                visible: _root.previewing
                text: "Back to Typed Messages"
                onClicked: _root._backToText()
            }
            Item { Layout.fillWidth: true }
            Button {
                objectName: "oscImportOk"
                text: _root.previewing
                      ? (_root.chosen.length === 1 ? "Add 1 Input" : "Add " + _root.chosen.length + " Inputs")
                      : "OK"
                highlighted: true
                enabled: !_root.previewing || _root.chosen.length > 0
                onClicked: _root.accept()
            }
            Button {
                text: "Cancel"
                onClicked: _root.close()
            }
        }
    }
}
