// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

function clamp(val, min, max) {
    return Math.min(Math.max(val, min), max)
}

function x2u(x, parent_x, size, offset) {
    return parent_x + ((x + 1) / 2 * size) - offset
}

function y2v(y, parent_y, size, offset) {
    return parent_y + (size - ((y + 1) / 2 * size)) - offset
}

// The -2 is required for the x and y coordinate provided
// by QML to actually be correct and result in no change
// without mouse motion
function u2x(u, offset, size) {
    return (2 * ((u + offset - 2) / size)) - 1
}

function v2y(v, offset, size) {
    return (-2 * ((v + offset - 2) / size)) + 1
}