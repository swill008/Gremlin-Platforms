# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Child process for harness.open_editors: the program off-screen (journey
harness: temporary home, fake stick, fake vJoy, no hooks), the pJoy Pro's
Configuration page, and for each request its pane opened on control 1 of
the kind, the action added as Add Action adds it, and its editor QML waited
for. Prints RESULT {"editors": [...]}.

    python test/unit/action_matrix/_editor_child.py <requests.json>
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "journeys"))
from _harness import Journey  # noqa: E402  # pyright: ignore[reportMissingImports]


def _warning(text: str) -> bool:
    low = text.lower()
    return any(
        w in low
        for w in (
            "warning",
            "error",
            "typeerror",
            "referenceerror",
            "cannot",
            "unable",
            "undefined",
            "binding loop",
            "is not a",
            "qml",
        )
    )


def story(j: Journey) -> None:
    from PySide6 import QtCore

    jobs = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    messages: list[str] = []

    def capture(mode, context, text: str) -> None:  # noqa: ANN001
        where = f"{context.file}:{context.line}: " if context and context.file else ""
        messages.append(where + str(text))

    QtCore.qInstallMessageHandler(capture)
    j.win.setWidth(1600)
    j.win.setHeight(950)
    catalog = j.open_configuration("pjoy_pro")
    page = j.ev("catalogPane()")
    editors: list[dict] = []
    j.out["editors"] = editors
    for job in jobs:
        kind = "button" if job["input"] == "key" else job["input"]
        got: dict = {"tag": job["tag"], "ok": False, "warnings": [], "shot": ""}
        editors.append(got)
        mark = len(messages)
        try:
            hid = j.device_index(catalog, kind, 1)
            j.ev(f"openAdvancedPane({hid}); true", page)
            j.wait_until(lambda: catalog.paneModel is not None, "the pane")
            root = j.wait_until(lambda: j.pane_actions(catalog)[0], "the root action")
            if job["tag"] != "root":
                before = len(j.pane_actions(catalog))
                root.appendAction(job["name"], "children")
                j.wait_until(
                    lambda: len(j.pane_actions(catalog)) > before, "the new action"
                )
            model = j.pane_actions(catalog)[-1]
            url = QtCore.QUrl(model.qmlPath)
            stem = pathlib.Path(url.toLocalFile() or model.qmlPath).stem
            if job["tag"] == "root":
                # The pane shows a binding's root through RootActionNode
                # (InputItemBinding.qml), RootAction.qml no longer exists (R1).
                stem = "RootActionNode"
            got["qml"] = stem

            def editor(stem: str = stem) -> object:
                for item in j.walk(j.win.contentItem()):
                    name = item.metaObject().className()
                    if name.startswith(stem + "_QML") or name == stem:
                        return item
                return None

            item = j.wait_until(editor, f"the {stem} editor", timeout=10)
            j.QTest.qWait(400)  # bindings settle, the pane slides in
            got["ok"] = item is not None
            if job.get("shot"):
                path = pathlib.Path(job["shot"])
                path.parent.mkdir(parents=True, exist_ok=True)
                got["shot"] = str(path) if j.win.grabWindow().save(str(path)) else ""
        except Exception as exc:  # noqa: BLE001
            got["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            seen = messages[mark:]
            got["warnings"] = [m for m in seen if _warning(m)]
            got["plugin_warnings"] = [
                m for m in got["warnings"] if job.get("folder") and job["folder"] in m
            ]
            catalog.discardPane()
            catalog.endPane()
            j.settle()


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


if __name__ == "__main__":
    main()
