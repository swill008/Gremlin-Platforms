// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import QtQuick.Layouts

import Gremlin.Profile
import Gremlin.Style
import "helpers.js" as Helpers


Item {
    id: _root

    property ActionModel action
    property ActionModel parentAction
    property string containerName
    property int itemSpacing : 10
    property bool compactMode: false
    property var inputItemModel
    property var inputBinding

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
            Layout.bottomMargin: 10
            spacing: 10

            IconButton {
                id: _foldButton

                checkable: true
                checked: backend && _root.action && backend.isActionExpanded(
                    _root.action.id,
                    _root.action.sequenceIndex
                )
                text: checked ? bsi.icons.folded : bsi.icons.unfolded

                Layout.alignment: Qt.AlignVCenter
                Layout.leftMargin: -10

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
                font.pixelSize: 24

                text: _root.action ? _root.action.icon : ""
            }

            JGTextField {
                id: _headerLabel

                Layout.minimumWidth: 72
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
                font.pixelSize: 24

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
            height: _root.action && _root.action.lastInContainer ? 15 : 0
            Layout.fillWidth: true
        }
    }

    Component {
        id: _addItem
        MenuItem {
            property string actionName: ""
            text: actionName
            onTriggered: {
                if (_root.parentAction)
                    _root.parentAction.appendAction(actionName, _root.containerName || "children")
            }
        }
    }

    Menu {
        id: _actionMenu

        Menu {
            id: _addMenu
            title: "Add"
        }
        MenuItem {
            text: "Delete"
            enabled: !!(_root.parentAction && _root.action) || !!(_root.compactMode && _root.inputItemModel && _root.inputBinding)
            onTriggered: {
                if (_root.compactMode && _root.inputItemModel && _root.inputBinding)
                    _root.inputItemModel.deleteActionSequnce(_root.inputBinding)
                else if (_root.parentAction && _root.action)
                    _root.parentAction.removeAction(_root.action.sequenceIndex)
            }
        }

        onAboutToShow: {
            while (_addMenu.count > 0) {
                var old = _addMenu.takeItem(0)
                if (old)
                    old.destroy()
            }
            var names = (_root.parentAction && _root.parentAction.compatibleActions)
                    ? _root.parentAction.compatibleActions : []
            for (var i = 0; i < names.length; i++) {
                var item = _addItem.createObject(_addMenu, { "actionName": names[i] })
                if (item)
                    _addMenu.addItem(item)
            }
            _addMenu.enabled = names.length > 0
        }
    }

    MouseArea {
        x: _content.x + _header.x
        y: _content.y + _header.y
        width: _header.width
        height: _header.height
        z: 4
        acceptedButtons: Qt.RightButton
        onClicked: _actionMenu.popup()
    }

    MouseArea {
        id: _dragArea

        x: _header.x
        y: _header.y
        z: -1
        width: _header.width + 20
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
