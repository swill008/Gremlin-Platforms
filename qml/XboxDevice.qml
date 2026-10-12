// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI

// The Xbox output's Output View (03 S139, D-XBOX-PADS): one red line when
// the ViGEmBus driver is missing (the full check is in Xbox Setup), the
// Find bar once for every pad, then one section per pad that is on and has
// a Map to Xbox binding (any mode): its face, its chip rows and its control
// list. Each section folds and remembers it; all open the first time. One
// scroll for all of it; the list's own Appearance on the page bar.
Item {
    id: _root

    // The red line's "Open Xbox Setup" link; Main opens the window.
    signal xboxSetupRequested()

    // Pad number -> open; a pad not in it is open.
    property var padOpenMap: ({})
    readonly property int padSectionCount: _sections.count
    // The Find bar's "Only controls with something sending" tick.
    property bool findSending: false

    // The page's Appearance part (PageAppearance.qml): Main shows its
    // Appearance… / Hide Appearance button on the page bar.
    property alias displayOpen: _appear.displayOpen
    readonly property Component pageBar: _sections.count > 0 ? _appear.pageBar : null
    function toggleAppearance() { _appear.toggleAppearance() }
    function requestCloseDisplay() { _appear.requestCloseDisplay() }
    readonly property alias appearance: _appear

    readonly property bool running:
        !!(typeof backend !== "undefined" && backend && backend.gremlinActive)

    XboxPadSectionsModel { id: _pads }

    XboxDriverStatus { id: _driver }

    WindowPlacement { id: _place }

    function isPadOpen(pad) {
        return padOpenMap[String(pad)] !== false
    }

    function setPadOpen(pad, open) {
        var next = {}
        for (var key in padOpenMap)
            next[key] = padOpenMap[key]
        next[String(pad)] = !!open
        padOpenMap = next
        _place.saveToolRowState("xboxOutput", JSON.stringify({ open: next }))
    }

    // That pad's control list, or null when it has no section.
    function padList(pad) {
        for (var i = 0; i < _sections.count; ++i) {
            var section = _sections.itemAt(i)
            if (section && section.padId === pad)
                return section.list
        }
        return null
    }

    function _loadPadOpen() {
        var state = {}
        try {
            state = JSON.parse(_place.toolRowState("xboxOutput")) || {}
        } catch (e) {
            state = {}
        }
        padOpenMap = (state.open && typeof state.open === "object") ? state.open : {}
    }

    Component.onCompleted: _loadPadOpen()
    onVisibleChanged: if (visible) _driver.reload()

    // What the shared Find bar reads from its list: the count across pads,
    // nothing to undo, no "Can't be sent" tick.
    QtObject {
        id: _findLayout
        readonly property int parentCount: {
            var n = 0
            for (var i = 0; i < _sections.count; ++i) {
                var section = _sections.itemAt(i)
                if (section)
                    n += section.list.parentCount
            }
            return n
        }
        readonly property bool canUndo: false
        readonly property bool canRedo: false
        readonly property string undoTip: ""
        readonly property string redoTip: ""
        readonly property string lastChange: ""
        readonly property string undone: ""
        function setCantSendOnly(on) {}
        function undo() {}
        function redo() {}
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ScrollView {
            id: _scroll
            objectName: "xboxOutputScroll"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: Style.dp(360)
            Layout.margins: Style.dp(10)
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn

            Component.onCompleted: {
                _scroll.contentItem.boundsMovement = Flickable.StopAtBounds
                _scroll.contentItem.boundsBehavior = Flickable.StopAtBounds
            }

            ColumnLayout {
                id: _column
                width: _scroll.availableWidth - Style.dp(16)
                spacing: Style.dp(8)

                // Only when the driver is missing: the pads can't be sent.
                RowLayout {
                    objectName: "xboxDriverMissingRow"
                    visible: !_driver.ready
                    Layout.fillWidth: true
                    spacing: Style.dp(10)

                    JGText {
                        objectName: "xboxDriverMissing"
                        text: "ViGEmBus driver not found: the Xbox pads can't be sent."
                        color: Style.danger
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    AbstractButton {
                        id: _setupLink
                        objectName: "xboxOpenSetupLink"
                        text: "Open Xbox Setup"
                        hoverEnabled: true
                        implicitWidth: _linkText.implicitWidth
                        implicitHeight: _linkText.implicitHeight
                        Accessible.name: text
                        onClicked: _root.xboxSetupRequested()
                        contentItem: Label {
                            id: _linkText
                            text: _setupLink.text
                            color: Style.accent
                            font.underline: _setupLink.hovered
                        }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                }

                JGText {
                    objectName: "xboxOutputEmpty"
                    visible: _sections.count === 0
                    text: "No Xbox controller has a binding yet. Add a Map to Xbox action on Device Bindings to see it here."
                    opacity: 0.65
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                // Once for every pad section (S139).
                ControlFindBar {
                    id: _find
                    objectName: "xboxOutputFindBar"
                    visible: _sections.count > 0
                    Layout.fillWidth: true
                    layout: _findLayout
                    namePrefix: "xboxOutput"
                    placeholder: "Control or source"
                    showUndo: false
                    showCantSend: false
                    typeChoices: _pads.typeChoices
                    filters: _pads.filters
                    onChanged: _root.findSending = _find.isChecked("sending")
                }

                Repeater {
                    id: _sections
                    model: _pads
                    delegate: XboxPadCard {
                        Layout.fillWidth: true
                        open: _root.isPadOpen(padId)
                        running: _root.running
                        appear: _appear
                        findText: _find.text
                        findType: _find.typeValue
                        findSending: _root.findSending
                        filtering: _find.filtering
                        onToggleRequested: _root.setPadOpen(padId, !open)
                        onClearFilters: _find.clear()
                    }
                }
            }
        }

        // The list's own Appearance (05 S125, AP2), kept in program
        // settings under "xbox-output".
        PageAppearance {
            id: _appear
            objectName: "xboxOutputAppearance"
            visible: _sections.count > 0 && displayOpen
            pageKey: "xbox-output"
            buttonName: "xboxOutputAppearanceButton"
            title: "Xbox Output View — Appearance"
            liveOptions: true
        }
    }
}
