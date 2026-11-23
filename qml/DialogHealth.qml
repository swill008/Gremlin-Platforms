// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts
import QtQuick.Window

import Gremlin.Device
import Gremlin.Menus
import Gremlin.Style
import Gremlin.UI
import Gremlin.Util
import "confirm.js" as Confirm
import "helpers.js" as Helpers
import "search"
import "search/search_text.js" as SearchText

// Health (01 S197, D-01-HEALTH): Search's layout for the bindings with a
// problem. Left: Look in and the four checks with counts; middle: the
// lines grouped profile › device with the ⚠ and the "Not plugged in" chip
// (SearchResultRow with showStatus); right: Why, the reason and what can
// be done. The HealthModel (gremlin/ui/health_model.py) holds the lines;
// gremlin/health.py is the only owner of the findings. Right-click: Open,
// Change target…, Remove binding…, Copy as text; Ctrl/Shift+click pick
// several; Ctrl+Z takes the last change back until the profile is saved or
// closed. Opened by the command tools.health (toolbar Health button, menus).
ApplicationWindow {
    font.pixelSize: Style.fontSize
    id: _root

    ToolWindowMemory {
        host: _root
        name: "health"
        defaultWidth: Style.fitWidth(Style.dp(1100), Screen)
        defaultHeight: Style.fitHeight(Style.dp(640), Screen)
    }

    property bool leaveTextOnEscape: false

    minimumWidth: Style.fitWidth(Style.dp(640), Screen)
    minimumHeight: Style.fitHeight(Style.dp(420), Screen)
    color: Style.background
    U.Universal.theme: Style.theme
    title: "Health"

    readonly property alias health: _model
    // The last clicked line (the Why panel's), -1: none.
    property int current: -1
    property int whyRevision: 0

    HealthModel {
        id: _model
        onModelReset: { _root.current = -1; _root.whyRevision++ }
        onEditRefused: (title, why) => _root.tell(title, why)
    }

    onClosing: _model.close()

    function itemOf(index) {
        if (index < 0 || index >= _list.count)
            return null
        return _list.itemAtIndex(index)
    }

    // A click on a line: Ctrl adds or takes away, Shift picks a span.
    function pick(index, modifiers) {
        var mods = modifiers || 0
        _model.select(index, !!(mods & Qt.ControlModifier), !!(mods & Qt.ShiftModifier))
        current = index
        whyRevision++
    }

    // A line's fields, for Main.goToSearchRow (SearchRow names).
    function rowOf(index) {
        var roles = _model.get(index) || {}
        if (roles.rowKind !== "result")
            return null
        var row = { row: index }
        for (var name in roles)
            row[SearchText.snake(name)] = roles[name]
        return row
    }

    function open(index) {
        var row = rowOf(index)
        var main = Helpers.mainWindow()
        if (!row || !main)
            return
        var why = String(_model.openMessage(index) || "")
        if (why.length) {
            tell("", why)
            return
        }
        main.goToSearchRow(row)
    }

    function tell(title, text) {
        _message.title = String(title || "")
        _message.text = String(text || "")
        _message.open()
    }

    function askRemove() {
        var question = String(_model.removeQuestion() || "")
        if (!question.length)
            return null
        return Confirm.ask(_root, {
            title: question,
            note: "Undo (Ctrl+Z) in this window puts it back until the profile is saved or closed.",
            action: "Remove",
            onAccept: function() { _model.removeSelected() }
        })
    }

    function askChangeTarget() {
        var start = _model.changeTargetStart() || {}
        if (start.vjoyId === undefined)
            return
        _targetBox.start = start
        _targetBox.open()
    }

    function undo() {
        return _model.undo()
    }

    // A link in the fix text: the command that opens that place.
    function follow(link) {
        if (!Commands.trigger(String(link)))
            console.warn("Health: no command " + link)
    }

    function escapePressed() {
        if (_rowMenu.visible) { _rowMenu.close(); return }
        if (_targetBox.visible) { _targetBox.close(); return }
        if (_message.visible) { _message.close(); return }
        _root.close()
    }

    Shortcut {
        sequences: [StandardKey.Cancel]
        onActivated: _root.escapePressed()
    }
    Shortcut {
        sequences: [StandardKey.Undo]
        enabled: !!_model.canUndo
        onActivated: _root.undo()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        spacing: Style.dp(6)

        Label {
            objectName: "healthStatus"
            text: String(_model.statusText || "")
            color: Style.fgMuted
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.dp(6)

            // Look in and the checks.
            Rectangle {
                objectName: "healthSidebar"
                Layout.fillHeight: true
                Layout.preferredWidth: Style.dp(220)
                color: Style.bgWell
                border.color: Style.line

                component Heading: Label {
                    color: Style.fgMuted
                    font.bold: true
                    font.pixelSize: Style.menuTextPx
                    topPadding: Style.dp(10)
                    bottomPadding: Style.dp(2)
                }

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: Style.dp(8)
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: Style.dp(2)

                        Heading { text: "Look in"; topPadding: 0 }
                        Repeater {
                            model: _model.scopes
                            delegate: RadioButton {
                                required property var modelData
                                objectName: "healthLookIn:" + modelData.name
                                Layout.fillWidth: true
                                focusPolicy: Qt.NoFocus
                                text: modelData.label
                                checked: _model.lookIn === modelData.name
                                onClicked: {
                                    _model.lookIn = modelData.name
                                    checked = Qt.binding(() => _model.lookIn === modelData.name)
                                }
                            }
                        }

                        Heading { text: "Checks" }
                        Repeater {
                            model: _model.checks
                            delegate: CheckBox {
                                required property var modelData
                                objectName: "healthCheck:" + modelData.name
                                Layout.fillWidth: true
                                focusPolicy: Qt.NoFocus
                                checked: !!modelData.on
                                text: modelData.label + " (" + modelData.count + ")"
                                contentItem: Label {
                                    leftPadding: parent.indicator.width + parent.spacing
                                    text: parent.text
                                    wrapMode: Text.Wrap
                                    color: Style.fg
                                    verticalAlignment: Text.AlignVCenter
                                }
                                onToggled: _model.setCheck(modelData.name, checked)
                            }
                        }
                    }
                }
            }

            // The lines with a problem.
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Style.bgWell
                border.color: Style.line

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Style.dp(1)
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: _headings.implicitHeight + Style.dp(6)
                        color: Style.bgRaised
                        visible: _list.count > 0

                        RowLayout {
                            id: _headings
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: Style.dp(38)
                            anchors.rightMargin: Style.dp(8)
                            spacing: Style.dp(8)
                            Label {
                                objectName: "healthHead:input"
                                Layout.preferredWidth: _list.inputWidth - Style.dp(38)
                                Layout.minimumWidth: _list.inputWidth - Style.dp(38)
                                text: "Input"; color: Style.fgStrong; font.bold: true
                            }
                            Label {
                                objectName: "healthHead:mode"
                                Layout.preferredWidth: _list.modeWidth
                                Layout.minimumWidth: _list.modeWidth
                                text: "Mode"; color: Style.fgStrong; font.bold: true
                            }
                            Label {
                                objectName: "healthHead:action"
                                Layout.fillWidth: true
                                text: "Action"; color: Style.fgStrong; font.bold: true
                            }
                        }
                    }

                    JGListView {
                        id: _list
                        objectName: "healthResults"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: _model
                        readonly property real inputWidth: Math.max(Style.dp(120), width * 0.22)
                        readonly property real modeWidth: Math.max(Style.dp(70), width * 0.12)
                        delegate: SearchResultRow {
                            id: _line
                            inputWidth: _list.inputWidth
                            modeWidth: _list.modeWidth
                            current: !!model.selected
                            showStatus: true
                            notFound: !!model.notFound
                            why: String(model.why || "")
                            notPlugged: !!model.notPlugged
                            usedTwice: !!model.usedTwice

                            // Clicks with their keys (Ctrl/Shift); the row's
                            // own hover (the ⚠ reason) still shows.
                            MouseArea {
                                objectName: "healthLineMouse:" + _line.index
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                cursorShape: _line.heading ? Qt.ArrowCursor : Qt.PointingHandCursor
                                onClicked: (mouse) => {
                                    if (_line.heading) {
                                        _model.toggleFold(_line.index)
                                        return
                                    }
                                    if (mouse.button === Qt.RightButton) {
                                        if (!_line.model.selected)
                                            _root.pick(_line.index, 0)
                                        _rowMenu.popup()
                                        return
                                    }
                                    _root.pick(_line.index, mouse.modifiers)
                                }
                                onDoubleClicked: (mouse) => {
                                    if (!_line.heading && mouse.button === Qt.LeftButton)
                                        _root.open(_line.index)
                                }
                            }
                        }
                    }
                }

                Label {
                    objectName: "healthNone"
                    visible: _list.count === 0
                    anchors.centerIn: parent
                    width: Math.min(parent.width - Style.dp(40), Style.dp(420))
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.Wrap
                    text: "No problems found."
                    color: Style.fgMuted
                }
            }

            // Why: the reason and what can be done.
            Rectangle {
                id: _why
                objectName: "healthWhy"
                Layout.fillHeight: true
                Layout.preferredWidth: Style.dp(300)
                color: Style.bgWell
                border.color: Style.line

                readonly property var info: {
                    _root.whyRevision
                    return _root.current >= 0 ? (_model.why(_root.current) || {}) : {}
                }

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: Style.dp(10)
                    contentWidth: availableWidth
                    clip: true

                    ColumnLayout {
                        width: parent.width
                        spacing: Style.dp(8)

                        Label {
                            objectName: "healthWhyTitle"
                            text: "Why"
                            font.bold: true
                            color: Style.fgStrong
                        }
                        Label {
                            Layout.fillWidth: true
                            visible: !(_why.info.findings || []).length
                            wrapMode: Text.Wrap
                            text: "Pick a line to see why it is listed and what you can do."
                            color: Style.fgMuted
                        }
                        Repeater {
                            model: _why.info.findings || []
                            delegate: ColumnLayout {
                                required property var modelData
                                required property int index
                                Layout.fillWidth: true
                                spacing: Style.dp(4)
                                Label {
                                    objectName: "healthWhyReason:" + index
                                    Layout.fillWidth: true
                                    wrapMode: Text.Wrap
                                    text: String(modelData.why)
                                    color: Style.danger
                                }
                                Label {
                                    objectName: "healthWhyFix:" + index
                                    Layout.fillWidth: true
                                    wrapMode: Text.Wrap
                                    textFormat: Text.StyledText
                                    text: String(modelData.fixHtml)
                                    color: Style.fg
                                    linkColor: Style.accent
                                    onLinkActivated: (link) => _root.follow(link)
                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.NoButton
                                        cursorShape: parent.hoveredLink ? Qt.PointingHandCursor
                                                                        : Qt.ArrowCursor
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Label {
            objectName: "healthHints"
            Layout.fillWidth: true
            text: "Ctrl+click or Shift+click picks several · right-click to fix · Ctrl+Z undo · Esc close"
            color: Style.fgMuted
            font.pixelSize: Style.menuTextPx
        }
    }

    // A line's right-click menu (Search's, for the picked lines).
    ThemedMenu {
        id: _rowMenu
        objectName: "healthRowMenu"
        property var fixes: ({})
        onAboutToShow: fixes = _model.fixes()
        ThemedMenuItem {
            text: "Open"
            enabled: _model.selectedCount === 1
            onTriggered: _root.open(_root.current)
        }
        ThemedMenuItem {
            objectName: "healthChangeTarget"
            text: "Change target…"
            enabled: !!_rowMenu.fixes.changeTarget
            onTriggered: _root.askChangeTarget()
        }
        ThemedMenuItem {
            objectName: "healthRemoveBinding"
            text: "Remove binding…"
            enabled: !!_rowMenu.fixes.remove
            onTriggered: _root.askRemove()
        }
        ThemedMenuItem {
            text: "Copy as text"
            onTriggered: _model.copyText()
        }
        ThemedMenuItem {
            objectName: "healthUndo"
            text: "Undo"
            hint: "Ctrl+Z"
            visible: !!_model.canUndo
            height: visible ? implicitHeight : 0
            onTriggered: _root.undo()
        }
    }

    // Open on an unplugged device, a refused edit.
    Popup {
        id: _message
        objectName: "healthMessage"
        property alias text: _messageText.text
        property alias title: _messageTitle.text
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(_root.width - Style.dp(40), Style.dp(460))
        padding: Style.dp(16)
        background: Rectangle { color: Style.background; border.color: Style.line; radius: Style.dp(4) }
        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                id: _messageTitle
                objectName: "healthMessageTitle"
                Layout.fillWidth: true
                visible: text.length > 0
                wrapMode: Text.Wrap
                font.bold: true
                color: Style.fg
            }
            Label {
                id: _messageText
                objectName: "healthMessageText"
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                color: Style.fg
            }
            Button {
                Layout.alignment: Qt.AlignRight
                text: "OK"
                onClicked: _message.close()
            }
        }
    }

    // Change target…: the vJoy pickers (only what can be sent).
    Popup {
        id: _targetBox
        objectName: "healthTargetBox"
        property var start: ({})
        property int vjoyId: 0
        property string inputType: ""
        property int inputId: 0
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(_root.width - Style.dp(40), Style.dp(460))
        padding: Style.dp(16)
        onOpened: {
            vjoyId = Number(start.vjoyId || 0)
            inputType = String(start.inputType || "")
            inputId = Number(start.inputId || 0)
            _targetPicker.active = false
            _targetPicker.active = true
        }
        onClosed: _targetPicker.active = false
        background: Rectangle { color: Style.background; border.color: Style.line; radius: Style.dp(4) }
        contentItem: ColumnLayout {
            spacing: Style.dp(12)
            Label {
                Layout.fillWidth: true
                text: "Change target"
                font.bold: true
                color: Style.fg
            }
            Loader {
                id: _targetPicker
                active: false
                Layout.fillWidth: true
                Layout.minimumWidth: Style.dp(220)
                sourceComponent: VJoySelector {
                    validTypes: [String(_targetBox.start.inputType || "button")]
                    onSelectionChanged: (vjoyId, inputType, inputId) => {
                        _targetBox.vjoyId = vjoyId
                        _targetBox.inputType = inputType
                        _targetBox.inputId = inputId
                    }
                    Component.onCompleted: initialize(Number(_targetBox.start.vjoyId || 0),
                                                      String(_targetBox.start.inputType || ""),
                                                      Number(_targetBox.start.inputId || 0))
                }
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Style.dp(8)
                Button {
                    objectName: "healthTargetOk"
                    text: "Change"
                    enabled: _targetBox.vjoyId > 0
                    onClicked: {
                        _model.changeTarget(_targetBox.vjoyId, _targetBox.inputType,
                                            _targetBox.inputId)
                        _targetBox.close()
                    }
                }
                Button {
                    text: "Cancel"
                    onClicked: _targetBox.close()
                }
            }
        }
    }
}
