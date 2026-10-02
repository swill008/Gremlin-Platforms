// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal as U
import QtQuick.Layouts

import Gremlin.Profile
import Gremlin.Menus
import Gremlin.Style
import "helpers.js" as Helpers


Item {
    id: _root

    property ActionModel action
    property ActionModel parentAction
    property string containerName
    property int itemSpacing : Style.dp(10)
    property bool compactMode: false
    property var inputItemModel
    // Containers (Tempo, Chain, Condition...) don't pass it on: a nested node
    // takes the enclosing node's, so editors like Map to Mouse know the input.
    property var inputBinding: _enclosingBinding()

    function _enclosingBinding() {
        for (var p = parent; p; p = p.parent) {
            if (p.inputBinding !== undefined)
                return p.inputBinding
        }
        return null
    }

    implicitHeight: _content.height

    Connections {
        target: action

        function onActionChanged()
        {
        }
    }

    function loadDynamicItem()
    {
        if (!_root.action) {
            return
        }
        let component = Qt.createComponent(
            Qt.resolvedUrl(_root.action.qmlPath)
        )

        if(component.status == Component.Ready ||
                component.status == Component.Error
        )
        {
            finishCreation();
        }
        else
        {
            component.statusChanged.connect(finishCreation);
        }

        function finishCreation()
        {
            if(component.status === Component.Ready)
            {
                destroyDynamicItem()
                _action.dynamicItem = component.createObject(
                    _action,
                    {
                        action: _root.action
                    }
                );

                _action.dynamicItem.Layout.fillWidth = true
            }
            else if(component.status === Component.Error)
            {
                console.log(
                    "Error loading component: ", component.errorString()
                );
            }

            component.destroy()
        }
    }

    function destroyDynamicItem()
    {
        if(_action.dynamicItem != null)
        {
            _action.dynamicItem.destroy()
        }
    }

    ColumnLayout {
        id: _content

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: _root.action && _root.action.depth > 1 ?
            _foldButton.width + _root.itemSpacing : _root.itemSpacing

        Drag.active: _dragArea.drag.active
        Drag.dragType: Drag.Automatic
        Drag.supportedActions: Qt.MoveAction
        Drag.proposedAction: Qt.MoveAction
        Drag.mimeData: {
            "text/plain": _root.action ? _root.action.sequenceIndex.toString() : "",
            "type": "action",
            "root": _root.action ? _root.action.rootActionId : ""
        }
        Drag.onDragFinished: function(action)
        {
            if(action === Qt.IgnoreAction)
            {
                signal.reloadCurrentInputItem();
            }
        }

        RowLayout {
            id: _header

            Layout.fillWidth: true
            Layout.preferredHeight: _foldButton.height
            Layout.bottomMargin: Style.dp(10)
            spacing: Style.dp(10)

            IconButton {
                id: _foldButton

                checkable: true
                checked: backend && _root.action && backend.isActionExpanded(
                    _root.action.id,
                    _root.action.sequenceIndex
                )
                text: checked ? bsi.icons.folded : bsi.icons.unfolded

                Layout.alignment: Qt.AlignVCenter
                Layout.leftMargin: -Style.dp(10)

                onClicked: () => {
                    if (backend && _root.action) {
                        backend.setIsActionExpanded(
                            _root.action.id,
                            _root.action.sequenceIndex,
                            checked
                        )
                    }
                }
            }

            Label {
                id: _headerIcon

                font.family: "bootstrap-icons"
                font.pixelSize: Style.dp(24)

                text: _root.action ? _root.action.icon : ""
            }

            JGTextField {
                id: _headerLabel

                Layout.minimumWidth: Style.dp(72)
                Layout.fillWidth: true

                text: _root.action ? _root.action.actionLabel : ""

                onTextEdited: () => {
                    if (_root.action) {
                        _root.action.actionLabel = text
                    }
                }
            }

            TriggerMode {
                visible: _root.action && _root.action.actionBehavior === "button" &&
                    _root.action.canChangeActivation

                Layout.alignment: Qt.AlignVCenter

                pressChecked: _root.action && _root.action.activateOnPress
                releaseChecked: _root.action && _root.action.activateOnRelease

                onPressCheckedChanged: function() {
                    if (_root.action) {
                        _root.action.activateOnPress = pressChecked
                    }
                }
                onReleaseCheckedChanged: function() {
                    if (_root.action) {
                        _root.action.activateOnRelease = releaseChecked
                    }
                }
            }

            Label {
                visible: _root.action && _root.action.isValid != true

                font.family: "bootstrap-icons"
                font.pixelSize: Style.dp(24)

                text: bsi.icons.error
                color: Style.error

                HoverHandler {
                    onHoveredChanged: () => {
                        if (!_root.action) {
                            return
                        }
                        _hintsTooltip.parent = parent
                        _hintsTooltip.x = -_hintsTooltip.width - 5
                        _hintsTooltip.y = parent.height + 5
                        _hintsTooltip.hints = _root.action.userFeedback
                        _hintsTooltip.visible = hovered
                    }
                }
            }

            IconButton {
                id: _removeButton
                visible: !_root.compactMode

                text: bsi.icons.remove

                onClicked: {
                    if (_root.compactMode && _root.inputItemModel && _root.inputBinding) {
                        _root.inputItemModel.deleteActionSequnce(_root.inputBinding)
                    } else if (parentAction && _root.action) {
                        parentAction.removeAction(_root.action.sequenceIndex)
                    }
                }
            }
        }

        RowLayout {
            id: _action

            property var dynamicItem: null

            Layout.fillWidth: true
            Layout.leftMargin: _headerIcon.x

            visible: _foldButton.checked

            Binding {
                target: _action
                property: "implicitHeight"
                value: _action.dynamicItem === null ? 0 :
                    _action.dynamicItem.implicitHeight
                when: _action.dynamicItem !== null
            }

            Component.onCompleted: loadDynamicItem()
            Component.onDestruction: destroyDynamicItem()
        }

        Rectangle {
            color: "transparent"
            z: -1
            height: _root.action && _root.action.lastInContainer ? Style.dp(15) : 0
            Layout.fillWidth: true
        }
    }

    // What kind of action each is, for the Add sections. Anything not
    // listed (a new action) goes under Other.
    readonly property var _actionKinds: ({
        "Map to vJoy": "map", "Map to Xbox": "map", "Map to Keyboard": "map",
        "Map to Mouse": "map", "Map to Logical Device": "map",
        "Response Curve": "axis", "Axis Delta": "axis", "Dual Axis Deadzone": "axis",
        "Merge Axis": "axis", "Split Axis": "axis", "Hat as Buttons": "axis",
        "Condition": "logic", "Chain": "logic", "Double Tap": "logic", "Tempo": "logic",
        "Smart Toggle": "logic", "Macro": "logic", "Change Mode": "logic", "Reference": "logic"
    })

    // The action's right-click menu (Gremlin.Menus): the three actions used
    // most (the order set in Options) to add straight away, the rest by kind.
    function _menuModel() {
        var names = (parentAction && parentAction.compatibleActions) ? parentAction.compatibleActions : []
        var add = function(name) {
            return MenuModel.action(name, function() {
                if (_root.parentAction)
                    _root.parentAction.appendAction(name, _root.containerName || "children")
            })
        }
        var quick = names.slice(0, 3).map(function(n) { return MenuModel.action("Add " + n, add(n).run) })
        var groups = { map: [], axis: [], logic: [], other: [] }
        for (var i = 3; i < names.length; i++)
            groups[_actionKinds[names[i]] || "other"].push(add(names[i]))
        var canDelete = !!(parentAction && action) || !!(compactMode && inputItemModel && inputBinding)
        return MenuModel.menu("action-node", action ? action.name : "Action", quick, [
            MenuModel.section("add-map", "Add: map to", groups.map),
            MenuModel.section("add-axis", "Add: axis and hat", groups.axis),
            MenuModel.section("add-logic", "Add: logic and timing", groups.logic),
            MenuModel.section("add-other", "Add: other", groups.other),
            MenuModel.section("remove", "Remove", [
                MenuModel.action("Delete", function() {
                    if (_root.compactMode && _root.inputItemModel && _root.inputBinding)
                        _root.inputItemModel.deleteActionSequnce(_root.inputBinding)
                    else if (_root.parentAction && _root.action)
                        _root.parentAction.removeAction(_root.action.sequenceIndex)
                }, canDelete, { danger: true })
            ])
        ])
    }

    ContextMenu {
        id: _actionMenu
        build: _root._menuModel
    }

    MouseArea {
        x: _content.x + _header.x
        y: _content.y + _header.y
        width: _header.width
        height: _header.height
        z: 4
        acceptedButtons: Qt.RightButton
        onClicked: (mouse) => _actionMenu.openAt(_header, mouse.x, mouse.y)
    }

    MouseArea {
        id: _dragArea

        x: _header.x
        y: _header.y
        z: -1
        width: _header.width + Style.dp(20)
        height: _header.height

        drag.target: _content
        drag.axis: Drag.YAxis

        onPressed: function()
        {
            _content.grabToImage(function(result)
            {
                _content.Drag.imageSource = result.url
            })
        }
    }

    Loader {
        active: _root.action && _root.action.name !== "Root"

        sourceComponent: DragDropArea {
            y: (_action.visible ? _action.y + _action.height : _header.y +
                _header.height) - height/2 + itemSpacing/2

            target: _header
            validationCallback: function(drag) {
                return drag.getDataAsString("type") === "action" &&
                    _root.action &&
                    drag.getDataAsString("root") === _root.action.rootActionId
            }
            dropCallback: function(drop) {
                modelData.dropAction(drop.text, modelData.sequenceIndex, "append");
            }
        }
    }
}
