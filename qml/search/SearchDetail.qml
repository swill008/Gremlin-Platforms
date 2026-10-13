// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Gremlin.Style
import "search_text.js" as SearchText

// The Search window's right side: the picked result in full (where it is,
// its binding, the mode chain, what else sends to the same output) with
// Open, Open in Device Mapping Editor and Search for this target.
Rectangle {
    id: _detail

    // The picked result's row (its roles) and SearchModel.detail(row).
    property var row: null
    property var info: ({})

    signal openClicked()
    signal mappingEditorClicked()
    signal searchTargetClicked()
    signal closeClicked()

    function f(name, fallback) {
        return SearchText.field(_detail.row, name, fallback)
    }

    function g(name, fallback) {
        return SearchText.field(_detail.info, name, fallback)
    }

    function listText(value) {
        if (value === undefined || value === null)
            return ""
        if (typeof value === "string")
            return value
        if (value.length !== undefined)
            return Array.prototype.join.call(value, "\n")
        return String(value)
    }

    readonly property string where: {
        var parts = [f("sourceName", ""), f("deviceName", ""), f("mode", "")]
        return parts.filter(function(p) { return String(p).length }).join(" · ")
    }
    readonly property string targets: listText(f("targets", []))
    readonly property string notes: listText(g("notes", f("notes", [])))
    readonly property string inheritedFrom: String(g("inheritedFrom", f("inheritedFrom", "")))

    color: Style.bgWell
    border.color: Style.line
    implicitWidth: Style.dp(280)

    component Heading: Label {
        Layout.fillWidth: true
        color: Style.fgMuted
        font.bold: true
        font.pixelSize: Style.menuTextPx
        topPadding: Style.dp(8)
    }

    component Body: Label {
        Layout.fillWidth: true
        color: Style.fg
        wrapMode: Text.Wrap
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.dp(10)
        spacing: Style.dp(4)

        RowLayout {
            Layout.fillWidth: true
            Label {
                objectName: "searchDetailTitle"
                Layout.fillWidth: true
                text: _detail.row ? _detail.f("inputLabel", "") : "Details"
                color: Style.fgStrong
                font.bold: true
                elide: Text.ElideRight
            }
            ToolButton {
                objectName: "searchDetailClose"
                text: "×"
                focusPolicy: Qt.NoFocus
                ToolTip.visible: hovered
                ToolTip.text: "Hide the details"
                onClicked: _detail.closeClicked()
            }
        }

        Body {
            visible: !_detail.row
            text: "Pick a result to see it here."
            color: Style.fgMuted
        }

        ScrollView {
            visible: !!_detail.row
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: Style.dp(2)

                Body {
                    visible: String(_detail.f("customName", "")).length > 0
                    text: _detail.f("customName", "")
                    color: Style.fgSoft
                }
                Heading { text: "Where" }
                Body { objectName: "searchDetailWhere"; text: _detail.where }
                Body {
                    objectName: "searchDetailInherited"
                    visible: text.length > 0
                    text: _detail.inheritedFrom.length > 0
                          ? "Inherited from " + _detail.inheritedFrom : ""
                    color: Style.fgSoft
                }
                Heading { text: "Action"; visible: _detail.f("actionName", "") !== "" }
                Body {
                    visible: text.length > 0
                    text: _detail.f("actionName", "")
                }
                Heading { text: "Binding" }
                Body {
                    objectName: "searchDetailBinding"
                    text: _detail.listText(_detail.g("bindingText", _detail.f("text", "")))
                    font.family: Style.monoFont
                }
                Heading { text: "Sends to"; visible: _detail.targets.length > 0 }
                Body { visible: text.length > 0; text: _detail.targets }
                // The text typed into the action, which Search also looks in.
                Heading {
                    objectName: "searchDetailNotesHeading"
                    text: "Notes"
                    visible: _detail.notes.length > 0
                }
                Body {
                    objectName: "searchDetailNotes"
                    visible: text.length > 0
                    text: _detail.notes
                }
                Heading {
                    text: "Mode chain"
                    visible: _modes.text.length > 0
                }
                Body {
                    id: _modes
                    visible: text.length > 0
                    text: {
                        var chain = _detail.g("modeChain", [])
                        return typeof chain === "string" ? chain
                             : Array.prototype.join.call(chain || [], " › ")
                    }
                }
                Heading {
                    text: "Used twice with"
                    visible: _clash.text.length > 0
                }
                Body {
                    id: _clash
                    objectName: "searchDetailClash"
                    visible: text.length > 0
                    color: Style.warn
                    text: _detail.listText(_detail.g("clashPartners", []))
                }
                Body {
                    visible: text.length > 0
                    color: Style.danger
                    text: _detail.f("notFound", false) ? String(_detail.f("why", "")) : ""
                }
            }
        }

        ColumnLayout {
            visible: !!_detail.row
            Layout.fillWidth: true
            spacing: Style.dp(4)
            Button {
                objectName: "searchDetailOpen"
                Layout.fillWidth: true
                text: "Open"
                focusPolicy: Qt.NoFocus
                onClicked: _detail.openClicked()
            }
            Button {
                objectName: "searchDetailMappingEditor"
                Layout.fillWidth: true
                text: "Open in Device Mapping Editor"
                focusPolicy: Qt.NoFocus
                enabled: String(_detail.f("deviceName", "")).length > 0
                onClicked: _detail.mappingEditorClicked()
            }
            Button {
                objectName: "searchDetailTarget"
                Layout.fillWidth: true
                text: "Search for this target"
                focusPolicy: Qt.NoFocus
                enabled: _detail.targets.length > 0
                onClicked: _detail.searchTargetClicked()
            }
        }
    }
}
