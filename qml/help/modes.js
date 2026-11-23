// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Modes. Written to claude/plans/help-style-guide.md: each
// topic opens with what it's for, then "How to", "What you see" and "Good to
// know" (empty sections left out).

.pragma library

var chapter = { id: "modes", title: "Modes" }

function _good(items) {
    return "<h4>Good to know</h4><ul><li>" + items.join("</li><li>") + "</li></ul>"
}

// Where Manage Modes is: the mode bar button.
var _manageModes = "<b>Manage Modes</b> <a href=\"show:modebar/Manage Modes\">Show me ›</a>"

function topics() {
    return [
        {
            id: "modes-modes",
            section: "Modes",
            title: "What modes are",
            body: "<p>A mode is a set of actions. The same button can do different things in different modes, for example one set for flying and one for landing.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Parent</b>: a mode can have a parent mode. Any input the mode doesn't map itself uses the parent's actions.</li>"
                + "<li><b>Mode</b> box: shows the one mode that runs at a time. See <a href=\"topic:modes-mode-box\">Choose the mode you edit and run</a>.</li>"
                + "<li><b>Change Mode</b>: an action that switches mode while the profile runs.</li>"
                + "</ul>"
                + _good([
                    "A profile always has at least one mode.",
                    "Modes are part of the profile. Save the profile to keep them.",
                    "For switching while the profile runs, see <a href=\"topic:modes-while-running\">How modes change while the profile runs</a>."
                ]),
            related: ["modes-manage", "modes-mode-box", "modes-while-running", "device-bindings-actions-change-mode"]
        },
        {
            id: "modes-manage",
            section: "Modes",
            title: "Add, rename and remove modes",
            body: "<p>In <b>Manage Modes</b> you add, rename and remove modes, and choose each mode's parent.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Choose " + _manageModes + " on the mode bar.</li>"
                + "<li>To add a mode, choose <b>Add Mode</b>.</li>"
                + "<li>To rename a mode, choose the pencil beside it.</li>"
                + "<li>To give a mode a parent, pick one in <b>Inherits from</b>. <b>(none)</b> makes it a top-level mode.</li>"
                + "</ol>"
                + _good([
                    "Manage Modes also opens from <b>Tools › Mapping › Manage Modes</b> <a href=\"show:menu/Tools/Mapping/Manage Modes\">Show me ›</a>.",
                    "A name can't be blank, and each name must be unique.",
                    "Capitals and extra spaces don't count, so \"Air Combat\" and \"AIR COMBAT\" are the same name. You can still change the capitals of a mode's own name.",
                    "Modes are listed alphabetically, ignoring capitals.",
                    "A mode can't have itself, or a mode under it, as its parent.",
                    "Renaming a mode also updates the <b>Change Mode</b> actions and the <b>Startup Mode</b> that name it.",
                    "You can change modes while the profile runs. Renames and deletes apply at once. Added modes and new parents apply at the next <b>Run</b>."
                ]),
            related: ["modes-delete", "modes-modes", "modes-mode-box"]
        },
        {
            id: "modes-delete",
            section: "Modes",
            title: "Delete a mode",
            body: "<p>Deleting a mode removes it and its bindings from the profile.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open " + _manageModes + ".</li>"
                + "<li>Choose the bin beside the mode.</li>"
                + "<li>A question names the mode and says how many bindings go with it. Choose the red <b>Delete Mode</b>.</li>"
                + "</ol>"
                + _good([
                    "Modes under it move up one level and keep their bindings.",
                    "If the <b>Startup Mode</b> named it, Startup Mode goes back to <b>Last Active</b>.",
                    "If the profile is running in that mode, it moves to another mode at once.",
                    "An action editor open in that mode closes, and a notice says so.",
                    "The last mode can't be deleted.",
                    "<b>Enter</b> and <b>Esc</b> both cancel the question.",
                    "To take the delete back, choose <b>Undo</b> in Manage Modes. See <a href=\"topic:modes-undo-delete\">Bring back a deleted mode</a>."
                ]),
            related: ["modes-undo-delete", "modes-manage", "options-profile-profile-settings"]
        },
        {
            id: "modes-undo-delete",
            section: "Modes",
            title: "Bring back a deleted mode",
            body: "<p>The <b>Undo</b> button in <b>Manage Modes</b> brings back the mode you deleted last. Choose it again to bring back the one before.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Open " + _manageModes + ".</li>"
                + "<li>Read the line beside <b>Undo</b> at the bottom. It names the mode Undo brings back.</li>"
                + "<li>Choose <b>Undo</b>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<p>The mode comes back with:</p>"
                + "<ul>"
                + "<li>its bindings,</li>"
                + "<li>its parent,</li>"
                + "<li>the modes that moved up when it was deleted,</li>"
                + "<li>the <b>Startup Mode</b>, if it named the mode.</li>"
                + "</ul>"
                + _good([
                    "Undo works while the same profile is open.",
                    "Pointing at Undo also names the mode it brings back.",
                    "<b>Redo</b> is grayed out here; it isn't used for modes.",
                    "If a mode can't come back, a notice says why."
                ]),
            related: ["modes-delete", "modes-manage"]
        },
        {
            id: "modes-mode-box",
            section: "Modes",
            title: "Choose the mode you edit and run",
            body: "<p>The <b>Mode</b> box <a href=\"show:modebar\">Show me ›</a>, on the mode bar under the toolbar, picks the mode you edit and the mode that runs.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>While the profile is stopped, it shows the mode you edit. <b>Run</b> starts in that mode.</li>"
                + "<li>While the profile runs, it shows the mode that runs. Picking another mode switches the running profile to it.</li>"
                + "<li>Actions you add belong to the mode shown.</li>"
                + "</ul>"
                + _good([
                    "When a profile is loaded, it opens in its <b>Startup Mode</b>, set in <b>Tools › Profile Settings…</b> <a href=\"open:tools.profileSettings\">Open ›</a>. See <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>.",
                    "An action editor with changes stays open when you pick another mode. Its title says which mode it edits."
                ]),
            related: ["modes-modes", "modes-while-running", "getting-started-run", "options-profile-profile-settings"]
        },

        {
            id: "modes-while-running",
            section: "Modes",
            title: "How modes change while the profile runs",
            body: "<p>While the profile runs, one mode is active at a time. <b>Change Mode</b> actions and the <b>Mode</b> box <a href=\"show:modebar\">Show me ›</a> move between modes.</p>"
                + "<p>During a Run the program remembers the modes you came through, in order. This is your path. Previous, Unwind and Temporary step along it.</p>"
                + "<h4>What you see</h4>"
                + "<p>A Change Mode action does one of these:</p>"
                + "<ul>"
                + "<li><b>Switch</b>: goes to the mode you chose.</li>"
                + "<li><b>Previous</b>: goes back to the mode you were in before this one. Press it again to swap back.</li>"
                + "<li><b>Unwind</b>: steps back one mode along your path and forgets the mode you leave. Press it again to go further back.</li>"
                + "<li><b>Cycle</b>: goes to the next mode in its list, and to the first after the last.</li>"
                + "<li><b>Temporary</b>: stays in a mode while you hold the input. Letting go returns to the mode before, whatever the held mode does with that input.</li>"
                + "</ul>"
                + "<p>For example, you went from Flight to Combat to Landing. Previous goes to Combat, and pressed again back to Landing. Unwind goes to Combat, and pressed again to Flight.</p>"
                + "<p>To go back, use Unwind. Previous swaps between the last two modes.</p>"
                + "<p>To set up the action, see <a href=\"topic:device-bindings-actions-change-mode\">Change Mode</a>.</p>"
                + _good([
                    "<b>Run</b> starts in the mode shown in the Mode box, with a new path each time.",
                    "If that mode is no longer in the profile, Run starts in the mode <b>Startup Mode</b> picks.",
                    "At the start of a Run there is nowhere to go back to, so Previous and Unwind do nothing.",
                    "An input with no actions in the running mode uses its parent's actions, through any number of levels.",
                    "A switch to a mode the profile doesn't have is ignored. The mode stays, and the log notes it once.",
                    "A vJoy or Logical Device button pressed in one mode is released when you let go, even after a mode change.",
                    "Map to Mouse motion stops on a mode change, unless the input has the same binding in the new mode.",
                    "With <b>Refresh axis on mode change</b> <a href=\"show:option/Refresh axis on mode change\">Show me ›</a> on, each axis's position is sent again after a mode change.",
                    "At <b>Stop</b>, a Temporary mode ends, and the mode you were in before the Temporary mode becomes the mode shown.",
                    "The mode the profile last ran in is kept for <b>Last Active</b>. Picking a mode in the Mode box while stopped doesn't count. See <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>.",
                    "When you come back to a mode on your path, see <a href=\"topic:modes-cycle-resolution\">Come back to a mode you passed</a>."
                ]),
            related: ["modes-modes", "modes-mode-box", "modes-cycle-resolution", "device-bindings-actions-change-mode", "getting-started-what-stop-releases"]
        },
        {
            id: "modes-cycle-resolution",
            section: "Modes",
            title: "Come back to a mode you passed",
            body: "<p>Sometimes you make the same mode change twice in one Run: into the same mode, from the same mode. <b>Mode cycle resolution</b> <a href=\"show:option/Mode cycle resolution\">Show me ›</a> then decides how your path is shortened.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Oldest</b> (the default): your path goes back to the first time you made that change. Everything after it is forgotten.</li>"
                + "<li><b>Newest</b>: the first time and everything before it are forgotten. The modes you came through since then stay.</li>"
                + "</ul>"
                + "<p>For example, you went Flight → Combat → Landing → Flight → Combat. With Oldest your path is now Flight, Combat. With Newest it is Landing, Flight, Combat.</p>"
                + _good([
                    "Previous and Unwind then step along the shortened path. In the example, Unwind after Newest goes to Flight, then to Landing. How they step: see <a href=\"topic:modes-while-running\">How modes change while the profile runs</a>.",
                    "It also applies to loops made by Temporary modes."
                ]),
            related: ["modes-while-running", "device-bindings-actions-change-mode"]
        },

        {
            id: "modes-q-button-does-nothing",
            section: "Common questions",
            title: "Why does a button do nothing in one mode?",
            body: "<p>Only the actions of the running mode and its parents run. Check the mode in the <b>Mode</b> box <a href=\"show:modebar\">Show me ›</a>, and that mode's parent. See <a href=\"topic:modes-while-running\">How modes change while the profile runs</a>.</p>",
            related: ["modes-modes", "modes-while-running", "getting-started-nothing-reaches-vjoy"]
        },
        {
            id: "modes-q-undo-delete",
            section: "Common questions",
            title: "I deleted a mode. Can I get it back?",
            body: "<p>Yes, while the same profile is open. The <b>Undo</b> button in Manage Modes brings it back with its bindings. See <a href=\"topic:modes-undo-delete\">Bring back a deleted mode</a>.</p>",
            related: ["modes-undo-delete"]
        },
        {
            id: "modes-q-cannot-delete",
            section: "Common questions",
            title: "Why can't I delete a mode?",
            body: "<p>It is the profile's only mode, and a profile always has at least one. Add another mode first. See <a href=\"topic:modes-delete\">Delete a mode</a>.</p>",
            related: ["modes-delete", "modes-manage"]
        },
        {
            id: "modes-q-start-mode",
            section: "Common questions",
            title: "How do I choose the mode a profile starts in?",
            body: "<p>When you load a profile, it opens in its <b>Startup Mode</b>, in <b>Tools › Profile Settings…</b> <a href=\"open:tools.profileSettings\">Open ›</a>. <b>Run</b> starts in whatever mode the <b>Mode</b> box shows. See <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>.</p>",
            related: ["modes-mode-box", "options-profile-profile-settings"]
        }
    ]
}
