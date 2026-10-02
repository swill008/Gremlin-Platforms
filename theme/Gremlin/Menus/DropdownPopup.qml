// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Templates as T
import QtQuick.Window

import Gremlin.Style

// A dropdown list's popup, in the menus' style. Long lists get a search box
// at the top: typing narrows the list, Up/Down move, Enter picks, Esc
// closes. Rows are DropdownRows.
T.Popup {
    id: _popup

    // The ComboBox this list belongs to.
    property var combo: null
    // Lists this long or longer get the search box.
    property int searchFrom: 10
    // Wheel steps by this many rows (0: smooth scrolling).
    property int scrollStep: 0
    readonly property bool searching: !!combo && combo.count >= searchFrom
    property string filter: ""
    // The row picked with the keyboard while typing in the search box.
    property int keyIndex: -1

    // Open below the box. Opened on top, the first entry sat under the pointer
    // and was highlighted instead of the current value.
    y: combo ? combo.height : 0
    width: combo ? combo.width : Style.dp(200)
    // The tallest the popup may be: the window less its margins.
    readonly property real _room: combo && combo.Window.window
                                  ? combo.Window.height - topMargin - bottomMargin : Style.dp(400)
    height: contentItem.implicitHeight + topPadding + bottomPadding
    topMargin: Style.dp(8)
    bottomMargin: Style.dp(8)
    padding: Style.dp(2)
    font: combo ? combo.font : Qt.font({})

    background: MenuSurface {}

    function _textAt(i) {
        return String(combo.textAt(i)).toLowerCase()
    }

    function _matches(i) {
        return !filter.length || _textAt(i).indexOf(filter.toLowerCase()) >= 0
    }

    // The next row that matches the search, from i in steps of step.
    function _next(i, step) {
        var n = combo ? combo.count : 0
        for (var k = 0; k < n; k++) {
            i += step
            if (i < 0 || i >= n)
                return -1
            if (_matches(i))
                return i
        }
        return -1
    }

    function _pick(i) {
        if (!combo || i < 0)
            return
        combo.currentIndex = i
        combo.activated(i)
        close()
    }

    onFilterChanged: {
        keyIndex = filter.length ? _next(-1, 1) : -1
        if (keyIndex >= 0)
            _list.positionViewAtIndex(keyIndex, ListView.Contain)
    }
    onOpened: {
        filter = ""
        _search.text = ""
        keyIndex = -1
        if (searching)
            _search.forceActiveFocus()
    }
    onClosed: {
        filter = ""
        _search.text = ""
        keyIndex = -1
    }

    contentItem: Column {
        spacing: 0

        Rectangle {
            id: _searchBox
            visible: _popup.searching
            width: parent.width
            height: visible ? Style.menuRowH + Style.dp(6) : 0
            color: Style.clear
            T.TextField {
                id: _search
                anchors.fill: parent
                anchors.margins: Style.dp(3)
                leftPadding: Style.dp(8)
                rightPadding: Style.dp(8)
                font.pixelSize: Style.menuTextPx
                color: Style.menuText
                selectionColor: Style.menuAccent
                selectedTextColor: Style.onColor
                verticalAlignment: Text.AlignVCenter
                background: Rectangle {
                    color: Style.bgWell
                    radius: Style.dp(4)
                    border.color: _search.activeFocus ? Style.menuAccent : Style.menuDivider
                }
                onTextChanged: _popup.filter = text.trim()
                Text {
                    visible: !_search.text.length
                    anchors.verticalCenter: parent.verticalCenter
                    x: _search.leftPadding
                    text: "Type to search"
                    font.pixelSize: Style.menuTextPx
                    color: Style.menuHint
                }
                Keys.onPressed: (e) => {
                    var start = _popup.keyIndex >= 0 ? _popup.keyIndex : (_popup.combo ? _popup.combo.currentIndex : -1)
                    if (e.key === Qt.Key_Down) {
                        var d = _popup._next(start, 1)
                        if (d >= 0)
                            _popup.keyIndex = d
                    } else if (e.key === Qt.Key_Up) {
                        var u = _popup._next(start, -1)
                        if (u >= 0)
                            _popup.keyIndex = u
                    } else if (e.key === Qt.Key_Return || e.key === Qt.Key_Enter) {
                        _popup._pick(_popup.keyIndex >= 0 ? _popup.keyIndex : _popup._next(-1, 1))
                    } else if (e.key === Qt.Key_Escape) {
                        _popup.close()
                    } else {
                        return
                    }
                    if (_popup.keyIndex >= 0)
                        _list.positionViewAtIndex(_popup.keyIndex, ListView.Contain)
                    e.accepted = true
                }
            }
        }

        ListView {
            id: _list
            width: parent.width
            height: Math.max(0, Math.min(contentHeight,
                                         _popup._room - _popup.topPadding - _popup.bottomPadding - _searchBox.height))
            clip: true
            model: _popup.combo ? _popup.combo.delegateModel : null
            currentIndex: _popup.combo ? _popup.combo.highlightedIndex : -1
            highlightMoveDuration: 0
            boundsBehavior: Flickable.StopAtBounds

            T.ScrollBar.vertical: T.ScrollBar {
                id: _bar
                // Only when the list is longer than the popup.
                visible: _list.contentHeight > _list.height + 1
                policy: T.ScrollBar.AlwaysOn
                width: Style.dp(6)
                contentItem: Rectangle {
                    radius: width / 2
                    color: _bar.pressed ? Style.menuAccent : Style.menuLine
                }
            }

            // Steps a few rows per wheel notch, for lists that ask for it.
            WheelHandler {
                enabled: _popup.scrollStep > 0
                onWheel: (event) => {
                    const topIndex = Math.max(0, _list.indexAt(0, _list.contentY + 1))
                    if (event.angleDelta.y > 0)
                        _list.positionViewAtIndex(Math.max(0, topIndex - _popup.scrollStep), ListView.Beginning)
                    else
                        _list.positionViewAtIndex(Math.min(_list.count - 1, topIndex + _popup.scrollStep), ListView.Beginning)
                    event.accepted = true
                }
            }
        }
    }
}
