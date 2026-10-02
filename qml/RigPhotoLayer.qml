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
    // The photo as chosen, before any look is applied.
    // No photo chosen: nothing (the stock Gladiator photo comes in as an
    // override, only for Gladiator devices).
    readonly property url baseUrl: (ed.face && ed.face.photoOverride && ed.face.photoOverride.length)
                                   ? ed.face.photoOverride
                                   : ""
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
        opacity: 1 - ed.photoFade
        // Scale and turn about the photo's own centre, then move it: moving
        // first turned an offset photo round the frame's centre instead.
        transform: [
            Scale {
                origin.x: _photoXform.width * 0.5
                origin.y: _photoXform.height * 0.5
                xScale: ed.photoScale
                yScale: ed.photoScale
            },
            Rotation {
                origin.x: _photoXform.width * 0.5
                origin.y: _photoXform.height * 0.5
                angle: ed.photoRot
            },
            Translate {
                x: ed.photoOffX * ed.spaceRect().w
                y: ed.photoOffY * ed.spaceRect().h
            }
        ]

        Image {
            id: _pagePhoto
            anchors.fill: parent
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            cache: true
            // An adjusted copy when the look is changed (the window makes it).
            source: ed.photoLookUrl.length ? ed.photoLookUrl : _photoWell.baseUrl
            onStatusChanged: {
                if (status === Image.Ready && linesCanvas)
                    linesCanvas.requestPaint()
            }

        }
    }
}
