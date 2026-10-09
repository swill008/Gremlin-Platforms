// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// A file or folder chooser that opens in the last folder used for its kind
// of file and remembers the chosen folder (01 S143, D-01-SHARED-PIECES).
//
//   FilePicker {
//       id: _pick
//       kind: "device-pack"        // see gremlin/ui/folder_memory.py KINDS
//       mode: "open"               // "open" | "save" | "folder"
//       title: "Open Device Pack"
//       nameFilters: ["Device packs (*.zip)"]
//       folder: _hw.exportFolderUrl()   // used when nothing is remembered
//       onPicked: (selected) => ...
//   }
//   _pick.open()

import QtCore
import QtQuick
import QtQuick.Dialogs

import Gremlin.UI

import "helpers.js" as Helpers

Item {
    id: _root

    // Which memory slot: device-pack, picture, profile, script, export,
    // module-file, log, diagnostics, template, other.
    property string kind: "other"
    property string mode: "open"
    property string title: ""
    property var nameFilters: []
    property string defaultSuffix: ""
    property string acceptLabel: ""
    // Save: the suggested file (its name is kept, in the remembered folder).
    property url currentFile
    // The folder to open in when none is remembered for this kind.
    property url folder
    // The last pick (file, or folder in "folder" mode).
    readonly property url selected: _root._selected
    property url _selected

    signal picked(url selected)
    signal cancelled()

    width: 0
    height: 0
    visible: false

    // The folder the dialog opens in: remembered, else the given one, else
    // the suggested file's folder.
    function startFolder() {
        var remembered = _memory.lastFolder(kind)
        if (remembered)
            return remembered
        var given = String(folder)
        if (given)
            return given
        var file = String(currentFile)
        var cut = file.lastIndexOf("/")
        return cut > 0 ? file.substring(0, cut) : ""
    }

    function dialog() {
        return mode === "folder" ? _folderDialog : _fileDialog
    }

    // Sets the dialog up without showing it.
    function prepare() {
        var start = startFolder()
        if (mode === "folder") {
            if (start)
                _folderDialog.currentFolder = start
            return _folderDialog
        }
        _fileDialog.fileMode = mode === "save" ? FileDialog.SaveFile : FileDialog.OpenFile
        if (start)
            _fileDialog.currentFolder = start
        var file = String(currentFile)
        if (mode === "save" && file) {
            var name = file.substring(file.lastIndexOf("/") + 1)
            // With nothing remembered or given, suggest the name in the
            // user's Documents folder rather than dropping it.
            var base = start ? String(start)
                : String(StandardPaths.writableLocation(StandardPaths.DocumentsLocation))
            if (base && name)
                _fileDialog.selectedFile = base + "/" + name
        }
        return _fileDialog
    }

    function open() {
        prepare().open()
    }

    function _accept(url) {
        if (!url)
            return
        _memory.remember(kind, url)
        _selected = url
        picked(url)
    }

    FolderMemory {
        id: _memory
    }

    FileDialog {
        id: _fileDialog
        objectName: "filePickerFileDialog"
        title: _root.title
        nameFilters: _root.nameFilters
        defaultSuffix: _root.defaultSuffix
        acceptLabel: _root.acceptLabel
        onAccepted: _root._accept(Helpers.fileDialogUrl(_fileDialog))
        onRejected: _root.cancelled()
    }

    FolderDialog {
        id: _folderDialog
        objectName: "filePickerFolderDialog"
        title: _root.title
        acceptLabel: _root.acceptLabel
        // The chosen folder; the shown one if the dialog gave none.
        onAccepted: _root._accept(String(selectedFolder) || String(currentFolder))
        onRejected: _root.cancelled()
    }
}
