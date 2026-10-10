# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 11: random steps on the four list pages, fixed seeds.

The Configuration (pJoy Pro), Logical Device, Keyboard and OSC pages are
opened through their Home cards and driven with random steps through the
page models' own slots: add an input or key, an action in the pane (OK or
x), Rename and Clear Name, groups (add, move into, rename, delete, up,
down, sort), reorder, Undo / Redo, delete an input or an action, switch
page or mode, File > Save then reopen, Discard then reopen. The seeds are
fixed, so a failure replays the same way (SHAKE-JOURNEYS-08; the audit's
throwaway fuzz_journey.py made into a regular test).

After every step: no Python exception and no Qt / QML warning; the title's
"*" is the exact unsaved state. Undo then Redo gives the same rows. After
Save nothing is unsaved, and after reopening every page shows the same
rows and groups. After Discard and reopen nothing is unsaved.

Spec: 05 S122, S127, S128, S129 (held layout, Undo, Save); 04 S5 (title
"*").
"""

from __future__ import annotations

import json
import pathlib
import random
import sys
import traceback
from typing import Any

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import Journey, run_journey, step  # noqa: E402

SEEDS = (1, 2, 3, 4, 5)
STEPS = 40

PAGES = ["config", "logical", "keyboard", "osc"]
SLUG = {
    "config": "pjoy_pro",
    "logical": "logical",
    "keyboard": "keyboard",
    "osc": "osc",
}
TAB = {"config": "physical", "logical": "logical", "keyboard": "keyboard", "osc": "osc"}
PANE_FN = {
    "config": "configurationPane()",
    "logical": "logicalPane()",
    "keyboard": "keyboardPane()",
    "osc": "oscPane()",
}
SCANS = [0x10, 0x11, 0x12, 0x13, 0x1E, 0x1F, 0x20, 0x21, 0x2C, 0x2D]
NAMES = ["Fire", "Gear", "Flaps", "Trim", "Zoom", "", "Ünï", "A b"]
GROUPS = ["G1", "G2", "Stick", "Panel"]
CHOICES = [
    "switch_page", "add", "add", "action_ok", "action_discard", "rename",
    "clear_name", "undo_redo", "undo", "redo", "add_group", "move_to_group",
    "rename_group", "delete_group", "reorder", "sort", "switch_mode", "save",
    "save", "discard_reopen", "delete_input", "delete_action",
]  # fmt: skip

QT_MSGS: list[str] = []
PY_EXC: list[str] = []


def _install_hooks() -> None:
    from PySide6 import QtCore

    def hook(kind, exc, tb) -> None:  # noqa: ANN001
        PY_EXC.append("".join(traceback.format_exception(kind, exc, tb))[-1500:])

    sys.excepthook = hook
    prev: list[Any] = [None]

    def handler(mode, context, message) -> None:  # noqa: ANN001
        if mode not in (QtCore.QtMsgType.QtDebugMsg, QtCore.QtMsgType.QtInfoMsg):
            QT_MSGS.append(f"{mode.name}: {message} ({context.file}:{context.line})")
        if prev[0] is not None:
            try:
                prev[0](mode, context, message)
            except Exception:  # noqa: BLE001, S110 - the previous handler's own
                pass

    prev[0] = QtCore.qInstallMessageHandler(handler)


def _row_diff(a: list[dict], b: list[dict]) -> dict:
    ka = {r["key"]: r for r in a}
    kb = {r["key"]: r for r in b}
    out: dict[str, Any] = {
        "only_before": sorted(set(ka) - set(kb))[:8],
        "only_after": sorted(set(kb) - set(ka))[:8],
    }
    changed = {
        k: {f: [ka[k].get(f), kb[k].get(f)] for f in set(ka[k]) | set(kb[k])
            if ka[k].get(f) != kb[k].get(f)}
        for k in ka
        if k in kb and ka[k] != kb[k]
    }  # fmt: skip
    out["changed"] = dict(list(changed.items())[:6])
    if not out["only_before"] and not out["only_after"] and not changed:
        out["order"] = [[r["key"] for r in a][:40], [r["key"] for r in b][:40]]
    return out


class _Random:
    """One seed's random walk over the pages."""

    def __init__(self, j: Journey, seed: int) -> None:
        self.j = j
        self.seed = seed
        self.page = ""
        self.url = ""
        self.idx = 0
        self.ops: list[dict] = []
        self.failures: list[dict] = []

    # --- the page ------------------------------------------------------------

    def model(self) -> Any:  # noqa: ANN401
        from gremlin.ui.hardware_layout import HardwareLayoutModel
        from gremlin.ui.keyboard_layout import KeyboardLayoutModel
        from gremlin.ui.logical_layout import LogicalLayoutModel
        from gremlin.ui.osc_layout import OscLayoutModel

        cls = {
            "config": HardwareLayoutModel,
            "logical": LogicalLayoutModel,
            "keyboard": KeyboardLayoutModel,
            "osc": OscLayoutModel,
        }[self.page]
        item = self.j.ev(PANE_FN[self.page])
        return None if item is None else item.findChild(cls)

    def open_page(self, page: str) -> None:
        j = self.j
        self.page = page
        j.ev(
            f"openConfigurationForCard(_moduleModel.cardMap({json.dumps(SLUG[page])}))"
        )
        j.wait_until(
            lambda: j.backend.uiState.currentTab == TAB[page], f"tab {page}", 10
        )
        j.wait_until(lambda: self.model() is not None, f"model {page}", 10)
        j.settle()

    def rows(self) -> list[dict]:
        return [
            {k: v for k, v in r.items() if isinstance(v, (str, int, float, bool))}
            for r in self.j.catalog_rows(self.model())
        ]

    def parents(self) -> list[str]:
        return [r["key"] for r in self.rows() if r.get("rowKind") == "parent"]

    def children(self) -> list[tuple[str, int]]:
        return [
            (r["parentKey"], int(r["sequenceIndex"]))
            for r in self.rows()
            if r.get("rowKind") not in ("parent", "group")
            and int(r.get("sequenceIndex", -1)) >= 0
        ]

    def group_names(self) -> list[str]:
        groups = self.model().property("groups") or []
        return [g["name"] for g in groups if g.get("name")]

    # --- checks --------------------------------------------------------------

    def fail(self, kind: str, detail: object) -> None:
        self.failures.append(
            {
                "seed": self.seed,
                "step": self.idx,
                "op": self.ops[-1] if self.ops else None,
                "kind": kind,
                "detail": detail,
            }
        )

    def check_logs(self) -> None:
        if PY_EXC:
            self.fail("python-exception", PY_EXC[:])
            PY_EXC.clear()
        if QT_MSGS:
            self.fail("qt-warning", QT_MSGS[:])
            QT_MSGS.clear()

    def check_title(self) -> None:
        j = self.j
        j.settle()
        exact = bool(j.backend.profileContainsUnsavedChanges)
        shown = bool(j.ev("refreshProfileDirty(); profileDirty"))
        title = str(j.win.title())
        if shown != exact or title.startswith("* ") != exact:
            self.fail("title-star", {"exact": exact, "cheap": shown, "title": title})

    # --- steps ---------------------------------------------------------------

    def gen(self, rng: random.Random) -> dict:
        """A random step with arguments for the state now."""
        parents = self.parents()
        groups = self.group_names()
        op = rng.choice(CHOICES)
        p = rng.choice(parents) if parents else ""
        if op == "switch_page":
            return {"op": op, "page": rng.choice(PAGES)}
        if op == "add":
            if self.page == "logical":
                kind = rng.choice(["button", "axis", "hat"])
                return {"op": op, "type": kind, "n": rng.randint(1, 3)}
            if self.page == "keyboard":
                return {"op": op, "scan": rng.choice(SCANS)}
            if self.page == "osc":
                addr = f"/f/{rng.randint(1, 30)}"
                return {"op": op, "addr": addr, "mode": rng.choice(["button", "axis"])}
            return {"op": "action_ok", "key": p, "out": rng.randint(1, 30)}
        if op in ("action_ok", "action_discard"):
            return {"op": op, "key": p, "out": rng.randint(1, 30)}
        if op == "rename":
            return {"op": op, "key": p, "name": rng.choice(NAMES)}
        if op == "clear_name":
            return {"op": op, "key": p}
        if op == "add_group":
            return {"op": op, "name": rng.choice(GROUPS)}
        if op == "move_to_group":
            count = min(len(parents), rng.randint(1, 3))
            keys = rng.sample(parents, k=count) if parents else []
            return {"op": op, "keys": keys, "group": rng.choice([*groups, ""])}
        if op == "rename_group":
            old = rng.choice(groups) if groups else ""
            return {
                "op": op,
                "old": old,
                "new": rng.choice(GROUPS) + rng.choice(["", "x"]),
            }
        if op == "delete_group":
            return {"op": op, "name": rng.choice(groups) if groups else ""}
        if op == "reorder":
            dst = rng.choice(parents) if parents else ""
            how = rng.choice(["before", "after", "into", "row"])
            return {"op": op, "src": p, "dst": dst, "method": how}
        if op == "sort":
            how = rng.choice(["name", "system", "groups", "up", "down"])
            return {"op": op, "how": how, "group": rng.choice(groups) if groups else ""}
        if op == "switch_mode":
            return {"op": op, "mode": rng.choice(["Default", "Combat"])}
        if op == "delete_input":
            return {"op": op, "keys": [p] if p else []}
        if op == "delete_action":
            children = self.children()
            key, seq = rng.choice(children) if children else ("", -1)
            return {"op": op, "key": key, "seq": seq}
        return {"op": op}

    def do(self, op: dict) -> None:  # noqa: C901, PLR0912, PLR0915 - one branch per step
        j = self.j
        m = self.model()
        kind = op["op"]
        if kind == "switch_page":
            self.open_page(op["page"])
        elif kind == "add":
            if self.page == "logical":
                m.addMany(op["type"], op["n"], "", "")
            elif self.page == "keyboard":
                m.addKey(
                    [[op["scan"], False]], j.backend.uiState.currentMode or "Default"
                )
            elif self.page == "osc":
                from gremlin.ui.osc_device_model import OscDeviceManagementModel

                add = (
                    j.win.findChild(OscDeviceManagementModel)
                    or OscDeviceManagementModel()
                )
                add.createConfiguredInput({"address": op["addr"], "mode": op["mode"]})
        elif kind in ("action_ok", "action_discard"):
            if not op["key"] or op["key"] not in self.parents():
                return
            m.beginNewAction(op["key"])
            pane = m.paneModel
            if pane is None or pane.rowCount() == 0:
                m.endPane()
                return
            root = pane.data(pane.index(0, 0), 0x0100 + 1).rootAction
            if "Map to vJoy" not in list(root.compatibleActions):
                m.endPane()
                return
            root.appendAction("Map to vJoy", "children")
            editor = root.getActions("children")[-1]
            editor.vjoyDeviceId = 1
            editor.vjoyInputId = op["out"]
            if kind == "action_ok":
                m.commitPane()
            else:
                m.discardPane()
            m.endPane()
        elif kind == "rename":
            if op["key"]:
                m.setUserName(op["key"], op["name"])
        elif kind == "clear_name":
            if op["key"]:
                m.setUserName(op["key"], "")
        elif kind == "undo":
            if m.property("canUndo"):
                m.undo()
        elif kind == "redo":
            if m.property("canRedo"):
                m.redo()
        elif kind == "undo_redo":
            if m.property("canUndo"):
                before = self.rows()
                label = m.property("undoTip")
                m.undo()
                j.settle()
                m.redo()
                j.settle()
                after = self.rows()
                if before != after:
                    self.fail(
                        "undo-redo-rows",
                        {"undoTip": label, "diff": _row_diff(before, after)},
                    )
        elif kind == "add_group":
            m.addGroup(op["name"])
        elif kind == "move_to_group":
            keys = [k for k in op["keys"] if k in self.parents()]
            if keys and op["group"] in [*self.group_names(), ""]:
                m.setSelection(keys)
                m.moveSelected(op["group"])
        elif kind == "rename_group":
            if op["old"]:
                m.renameGroup(op["old"], op["new"])
        elif kind == "delete_group":
            if op["name"]:
                m.removeGroup(op["name"])
        elif kind == "reorder":
            if op["src"] and op["dst"]:
                if op["method"] == "row":
                    m.moveRow(op["src"], op["dst"])
                else:
                    m.moveParent(op["src"], op["dst"], op["method"])
        elif kind == "sort":
            how = op["how"]
            if how == "name":
                m.sortByName()
            elif how == "system":
                m.sortBySystem()
            elif how == "groups":
                m.sortGroupNames()
            elif how == "up" and op["group"]:
                m.moveGroupUp(op["group"])
            elif how == "down" and op["group"]:
                m.moveGroupDown(op["group"])
        elif kind == "switch_mode":
            j.backend.uiState.setCurrentMode(op["mode"])
        elif kind == "save":
            self.save_and_check()
        elif kind == "discard_reopen":
            # What Main's Discard calls, then the profile opened again.
            j.backend.discardLogicalDevice()
            j.backend.discardOscDevice()
            j.backend.discardConfigurationLayouts()
            self.reopen()
            if bool(j.backend.profileContainsUnsavedChanges):
                self.fail("unsaved-after-discard-reopen", True)
        elif kind == "delete_input":
            keys = [k for k in op["keys"] if k in self.parents()]
            if keys:
                m.deleteParents(keys)
        elif kind == "delete_action":
            if (
                op["key"]
                and op["seq"] >= 0
                and (op["key"], op["seq"]) in self.children()
            ):
                m.deleteAction(op["key"], op["seq"])

    def reopen(self) -> None:
        """The profile opened again, on the mode shown before (Last Active
        with no Run record opens the top-listed mode, 04 S52)."""
        j = self.j
        mode_before = j.backend.uiState.currentMode
        j.backend.newProfile()
        j.backend.loadProfile(self.url)
        j.settle()
        j.backend.uiState.setCurrentMode(mode_before)
        j.settle()
        self.open_page(self.page)

    def save_and_check(self) -> None:
        j = self.j
        page_now = self.page
        shown = {}
        for page in PAGES:
            self.open_page(page)
            shown[page] = (self.rows(), self.model().property("groups"))
        unfinished = list(j.backend.unfinishedActions())
        if unfinished:
            self.fail("unfinished-at-save", unfinished)
        j.ev("saveCurrentProfile(); true")
        j.settle()
        if bool(j.backend.profileContainsUnsavedChanges):
            self.fail("unsaved-after-save", True)
        self.check_title()
        self.reopen()
        for page in PAGES:
            self.open_page(page)
            again = (self.rows(), self.model().property("groups"))
            if again != shown[page]:
                self.fail(
                    "save-reopen-differs",
                    {
                        "page": page,
                        "groups": "same"
                        if again[1] == shown[page][1]
                        else [shown[page][1], again[1]],
                        "diff": _row_diff(shown[page][0], again[0]),
                    },
                )
        self.open_page(page_now)


def story(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin import util
    from gremlin.ui.profile import ModeHierarchyModel

    _install_hooks()
    ModeHierarchyModel().newMode("Combat")
    failures: list[dict] = []
    steps = 0
    kinds: dict[str, int] = {}
    pages: set[str] = set()
    for seed in SEEDS:
        walk = _Random(j, seed)
        path = util.profiles_dir() / f"random_{seed}.xml"
        walk.url = QtCore.QUrl.fromLocalFile(str(path)).toString()
        assert j.backend.saveProfile(walk.url)
        walk.open_page("config")
        PY_EXC.clear()
        QT_MSGS.clear()  # start-up messages are other tests' to check
        rng = random.Random(seed)
        for i in range(STEPS):
            walk.idx = i
            op = walk.gen(rng)
            walk.ops.append(op)
            kinds[op["op"]] = kinds.get(op["op"], 0) + 1
            pages.add(walk.page)
            try:
                walk.do(op)
                j.settle()
            except Exception as exc:  # noqa: BLE001 - recorded as a failure
                walk.fail(
                    "raised",
                    f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-1500:]}",
                )
            walk.check_logs()
            try:
                walk.check_title()
            except Exception as exc:  # noqa: BLE001 - recorded as a failure
                walk.fail("check-raised", f"{type(exc).__name__}: {exc}")
        steps += len(walk.ops)
        failures += walk.failures
        # The next seed starts from a saved profile.
        j.ev("saveCurrentProfile(); true")
        j.settle()
    j.out["steps"] = steps
    j.out["kinds"] = kinds
    j.out["pages"] = sorted(pages)
    j.out["failures"] = failures


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


# --- pytest side ----------------------------------------------------------------


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j11"))


def _of(run: dict, *kinds: str) -> list[dict]:
    return [f for f in step(run, "failures") if f["kind"] in kinds]


def test_every_step_ran_on_every_page(run: dict) -> None:
    assert step(run, "steps") == len(SEEDS) * STEPS
    assert step(run, "pages") == sorted(PAGES)
    kinds = step(run, "kinds")
    # The seeds reach Save + reopen, Discard + reopen and Undo + Redo.
    assert kinds.get("save", 0) >= 3, kinds
    assert kinds.get("discard_reopen", 0) >= 1, kinds
    assert kinds.get("undo_redo", 0) >= 3, kinds


def test_no_exception_and_no_qt_warning(run: dict) -> None:
    found = _of(run, "raised", "check-raised", "python-exception", "qt-warning")
    assert found == [], json.dumps(found, indent=1)[:4000]


def test_the_title_star_is_the_unsaved_state(run: dict) -> None:
    found = _of(run, "title-star", "unsaved-after-save", "unsaved-after-discard-reopen")
    assert found == [], json.dumps(found, indent=1)[:4000]


def test_undo_then_redo_gives_the_same_rows(run: dict) -> None:
    found = _of(run, "undo-redo-rows")
    assert found == [], json.dumps(found, indent=1)[:4000]


def test_save_and_reopen_shows_the_same_pages(run: dict) -> None:
    found = _of(run, "save-reopen-differs", "unfinished-at-save")
    assert found == [], json.dumps(found, indent=1)[:4000]


if __name__ == "__main__":
    main()
