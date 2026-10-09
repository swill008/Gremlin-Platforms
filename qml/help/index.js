// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// The Help book (01 S128): one file per chapter, joined here in reading order.

.pragma library

.import "getting_started.js" as GettingStarted
.import "home_devices.js" as HomeDevices
.import "configuration_actions.js" as ConfigurationActions
.import "logical_device.js" as LogicalDevice
.import "osc.js" as Osc
.import "modes.js" as Modes
.import "button_map.js" as ButtonMap
.import "device_library.js" as DeviceLibrary
.import "tools.js" as Tools
.import "options_profile.js" as OptionsProfile

function _modules() {
    return [GettingStarted, HomeDevices, ConfigurationActions, LogicalDevice, Osc,
            Modes, ButtonMap, DeviceLibrary, Tools, OptionsProfile]
}

var _book = null

// Built once. A chapter that is missing its header or whose topics() throws
// is left out rather than emptying the whole book.
function _load() {
    if (_book !== null)
        return _book
    var book = []
    var modules = _modules()
    for (var i = 0; i < modules.length; ++i) {
        var module = modules[i]
        if (!module || !module.chapter || typeof module.topics !== "function")
            continue
        var list = []
        try {
            list = module.topics() || []
        } catch (error) {
            console.warn("Help chapter " + module.chapter.id + ": " + error)
            continue
        }
        var topics = []
        for (var j = 0; j < list.length; ++j) {
            var source = list[j]
            var topic = {}
            for (var key in source)
                topic[key] = source[key]
            if (!topic.related)
                topic.related = []
            topic.chapter = module.chapter.title
            topic.chapterId = module.chapter.id
            topics.push(topic)
        }
        book.push({ id: module.chapter.id, title: module.chapter.title,
                    topics: topics })
    }
    _book = book
    return _book
}

// [{id, title}] in reading order.
function chapters() {
    var book = _load()
    var result = []
    for (var i = 0; i < book.length; ++i)
        result.push({ id: book[i].id, title: book[i].title })
    return result
}

// One chapter's topics; "" (or nothing) gives the whole book.
function topics(chapterId) {
    var book = _load()
    var result = []
    for (var i = 0; i < book.length; ++i) {
        if (chapterId && book[i].id !== chapterId)
            continue
        result = result.concat(book[i].topics)
    }
    return result
}

function find(topicId) {
    var all = topics("")
    for (var i = 0; i < all.length; ++i) {
        if (all[i].id === topicId)
            return all[i]
    }
    return null
}
