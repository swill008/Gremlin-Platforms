// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Old entry points over the Help book (qml/help/index.js, 01 S128).

.pragma library

.import "help/index.js" as Book

function topics() {
    return Book.topics("")
}

function deviceMappingEditorTopics() {
    return Book.topics("device-mapping-editor")
}

function deviceLibraryTopics() {
    return Book.topics("device-library")
}

function topic(section, title, body) {
    return { "section": section, "title": title, "body": body }
}
