// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Device
import Gremlin.Style
import Gremlin.UI

// The Xbox output's Output View (03 S139): the ViGEmBus check, the live pad
// of each device that drives it (one card per device, in a section that
// folds and remembers it), then the controls in pad order with what sends
// to each: the shared Find bar and list, view only, with live bars and
// lights while the profile runs, and the list's own Appearance. One scroll
// for all of it.
Item {
    id: _root

    // The pad cards' section, open unless the user folded it.
    property bool padsOpen: true

    // The page's Appearance part (PageAppearance.qml): Main shows its
    // Appearance… / Hide Appearance button on the page bar.
    property alias displayOpen: _appear.displayOpen
    readonly property Component pageBar: _appear.pageBar
    function toggleAppearance() { _appear.toggleAppearance() }
    function requestCloseDisplay() { _appear.requestCloseDisplay() }
    readonly property alias appearance: _appear
    readonly property alias layout: _list

    XboxOutputListModel {
        id: _list
        // Polls what the Xbox output sends only while the profile runs and
        // the panel's Live section shows bars or lights.
        liveActive: !!(typeof backend !== "undefined" && backend && backend.gremlinActive)
                    && (_appear.showLiveBars || _appear.showLeds)
    }

    XboxViewerDeviceModel {
        id: _devices
    }

    WindowPlacement { id: _place }

    function _loadPadsOpen() {
        var state = {}
        try {
            state = JSON.parse(_place.toolRowState("xboxOutput")) || {}
        } catch (e) {
            state = {}
        }
        padsOpen = state.padsOpen !== false
    }

    function setPadsOpen(open) {
        padsOpen = open
        _place.saveToolRowState("xboxOutput", JSON.stringify({ padsOpen: open }))
    }

    function pairTitle(guid, name) {
        return name && name.length ? name : guid
    }

    Component.onCompleted: {
        _loadPadsOpen()
        _devices.reload()
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

                XboxDriverCheck {
                    Layout.fillWidth: true
                }

                // The pad cards' section heading: click to fold or open it.
                AbstractButton {
                    id: _padsHeading
                    objectName: "xboxPadsHeading"
                    Layout.fillWidth: true
                    implicitHeight: _headRow.implicitHeight + Style.dp(8)
                    hoverEnabled: true
                    Accessible.name: (_root.padsOpen ? "Fold " : "Open ") + "Live pads"
                    onClicked: _root.setPadsOpen(!_root.padsOpen)

                    background: Rectangle {
                        radius: Style.dp(3)
                        color: _padsHeading.hovered ? Style.bgWell : "transparent"
                    }

                    contentItem: RowLayout {
                        id: _headRow
                        spacing: Style.dp(6)

                        Label {
                            text: _root.padsOpen ? "▾" : "▸"
                            font.pixelSize: Style.dp(13)
                        }
                        Label {
                            text: "Live pads"
                            font.bold: true
                            font.pixelSize: Style.dp(13)
                        }
                        Label {
                            text: _devices ? "(" + _devices.count + ")" : ""
                            opacity: 0.55
                            font.pixelSize: Style.dp(11)
                        }
                        Item { Layout.fillWidth: true }
                    }
                }

                JGText {
                    visible: _root.padsOpen && (!_devices || _devices.count === 0)
                    text: "No Map to Xbox actions on connected devices."
                    opacity: 0.65
                }

                Repeater {
                    model: _root.padsOpen ? _devices : null
                    delegate: XboxViewerCard {
                        required property string guid
                        required property string name
                        // The card's own property, filled from the row.
                        required pairLabel

                        Layout.fillWidth: true
                        deviceGuid: guid
                        title: _root.pairTitle(guid, name)
                    }
                }

                // The controls in pad order, each with what sends to it
                // (S139): the shared list, view only, no groups.
                ControlFindBar {
                    id: _find
                    Layout.fillWidth: true
                    layout: _list
                    namePrefix: "xboxOutput"
                    placeholder: "Control or source"
                    showUndo: false
                    showCantSend: false
                    typeChoices: _list.typeChoices
                    filters: _list.filters
                    onChanged: _root._applyFind()
                }

                ControlTree {
                    id: _tree
                    objectName: "xboxOutputTree"
                    Layout.fillWidth: true
                    // Full height in the page's scroll: the pads and the rows
                    // scroll together (S139).
                    Layout.preferredHeight: Math.max(listHeight, Style.dp(80))
                    ownScroll: false
                    readOnly: true
                    showGroups: false
                    layout: _list
                    namePrefix: "xboxOutput"
                    emptyText: "No Xbox controls."
                    filtering: _find.filtering
                    liveDecoration: true
                    liveState: _list
                    liveBars: _appear.showLiveBars
                    liveLeds: _appear.showLeds
                    colorLive: _appear.colorLive
                    parentHeight: _appear.parentHeight
                    childHeight: _appear.childHeight
                    rowSpacing: _appear.rowSpacing
                    groupInside: _appear.groupInside
                    parentAlign: _appear.parentAlign
                    parentWidthPct: _appear.parentWidthPct
                    childAlign: _appear.childAlign
                    childWidthPct: _appear.childWidthPct
                    groupSpacing: _appear.groupSpacing
                    listPadShape: _appear.listPadShape
                    listPad: _appear.listPad
                    listPadTop: _appear.listPadTop
                    listPadRight: _appear.listPadRight
                    listPadBottom: _appear.listPadBottom
                    listPadLeft: _appear.listPadLeft
                    groupPadShape: _appear.groupPadShape
                    groupPad: _appear.groupPad
                    groupPadTop: _appear.groupPadTop
                    groupPadRight: _appear.groupPadRight
                    groupPadBottom: _appear.groupPadBottom
                    groupPadLeft: _appear.groupPadLeft
                    groupRadius: _appear.groupRadius
                    colorGroup: _appear.colorGroup
                    parentPadShape: _appear.parentPadShape
                    parentPad: _appear.parentPad
                    parentPadTop: _appear.parentPadTop
                    parentPadRight: _appear.parentPadRight
                    parentPadBottom: _appear.parentPadBottom
                    parentPadLeft: _appear.parentPadLeft
                    parentRadius: _appear.parentRadius
                    colorParent: _appear.colorParent
                    parentIndent: _appear.parentIndent
                    childIndent: _appear.childIndent
                    childPadShape: _appear.childPadShape
                    childPad: _appear.childPad
                    childPadTop: _appear.childPadTop
                    childPadRight: _appear.childPadRight
                    childPadBottom: _appear.childPadBottom
                    childPadLeft: _appear.childPadLeft
                    childRadius: _appear.childRadius
                    colorChild: _appear.colorChild
                    showChildren: _appear.showChildren
                    showSummary: _appear.showSummary
                    summaryFont: _appear.summaryFont
                    parentFont: _appear.parentFont
                    groupFont: _appear.groupFont
                    childFont: _appear.childFont
                    targetFont: _appear.targetFont
                    colorActionTarget: _appear.colorActionTarget
                    parentBold: _appear.parentBold
                    colorText: _appear.colorText
                    colorMuted: _appear.colorMuted
                    colorSelected: _appear.colorSelected
                    colorSelectBorder: _appear.colorSelectBorder
                    colorBorder: _appear.colorBorder
                    caretSize: _appear.caretSize
                    colorCaret: _appear.colorCaret
                    gripWidth: _appear.gripWidth
                    gripHeight: _appear.gripHeight
                    gripRadius: _appear.gripRadius
                    colorGrip: _appear.colorGrip
                    onClearFilters: _find.clear()
                }
            }
        }

        // The list's own Appearance (05 S125, AP2), kept in program
        // settings under "xbox-output".
        PageAppearance {
            id: _appear
            objectName: "xboxOutputAppearance"
            pageKey: "xbox-output"
            buttonName: "xboxOutputAppearanceButton"
            title: "Xbox Output View — Appearance"
            liveOptions: true
        }
    }

    // +---------------------------------------------------------------------
    // | Find

    function _applyFind() {
        _list.setFilter(_find.text, _find.typeValue, _find.isChecked("sending"))
    }
}
