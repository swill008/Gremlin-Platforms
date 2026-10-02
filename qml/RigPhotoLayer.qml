// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

import QtQuick
import QtQml
import QtQuick.Controls
import QtQuick.Layouts
import Gremlin.Style

// The background photo in the Button Map editor, posed by scale, offset and rotation.
Item {
    id: _photoWell
    property var ed: null
    property var linesCanvas: null
    z: 0
    visible: !ed.photoHidden
    x: ed.innerPageRect().x
    y: ed.innerPageRect().y
    width: ed.innerPageRect().w
    height: ed.innerPageRect().h
    clip: false

    Item {
        id: _photoXform
        anchors.fill: parent
        transform: [
            Translate {
                x: ed.photoOffX * ed.spaceRect().w
                y: ed.photoOffY * ed.spaceRect().h
            },
            Rotation {
                origin.x: _photoXform.width * 0.5
                origin.y: _photoXform.height * 0.5
                angle: ed.photoRot
            },
            Scale {
                origin.x: _photoXform.width * 0.5
                origin.y: _photoXform.height * 0.5
                xScale: ed.photoScale
                yScale: ed.photoScale
            }
        ]

        Image {
            id: _pagePhoto
            anchors.fill: parent
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            cache: true
            source: (ed.face && ed.face.photoOverride && ed.face.photoOverride.length)
                    ? ed.face.photoOverride
                    : Qt.resolvedUrl("images/vkb_gladiator_rig.jpg")
            onStatusChanged: {
                if (status === Image.Ready && linesCanvas)
                    linesCanvas.requestPaint()
            }
        }
    }
}
