# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Guard (design for change): a signal that is emitted on the input thread
(InputModuleRuntime, EventHandler, ModeManager, RunControl) must reach its UI
receivers through an explicit QueuedConnection and a QObject slot, never a
lambda or plain function (an auto connection to a lambda runs on the emitting
thread, i.e. in the middle of the input path, on the wrong thread).

Scans gremlin/ and the plugins by syntax tree. A new viewer that connects
the wrong way fails here, with its file and line.

Inside the input path itself (the Run's own wiring, receivers that are
QObjects living on the input thread) direct connections are meant; those
files are listed in INPUT_SIDE with the reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Signals emitted on the input thread (attribute name on the emitting object).
RUNTIME_SIGNALS = {
    "event", "key_event",          # InputModuleRuntime
    "is_active",                   # EventHandler
    "mode_changed",                # ModeManager
    "runStarted", "runStopped",    # RunControl
}
# Objects (the call or name the signal hangs off) that are input-thread owners.
OWNERS = {
    "InputModuleRuntime", "EventHandler", "ModeManager", "RunControl",
    "run_control", "bus", "module_bus", "mm", "handler", "event_handler",
}
# Files whose connections are the input path's own wiring: receivers live on
# the input thread, so a direct connection is the design.
INPUT_SIDE = {
    "gremlin/code_runner.py": "Run wiring: start/stop run on the input thread",
    "gremlin/mode_manager.py": "the owner itself",
    "gremlin/event_handler.py": "the owner itself",
    "gremlin/modules/runtime.py": "the owner itself",
}
SCAN = ("gremlin", "action_plugins", "joystick_gremlin.py", "input_tester.py")


def _files() -> list[Path]:
    out: list[Path] = []
    for entry in SCAN:
        path = ROOT / entry
        out.extend([path] if path.is_file() else sorted(path.rglob("*.py")))
    return out


def _chain(node: ast.AST) -> list[str]:
    """['InputModuleRuntime', 'event', 'connect'] for X().event.connect."""
    names: list[str] = []
    while True:
        if isinstance(node, ast.Attribute):
            names.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Name):
            names.append(node.id)
            break
        else:
            break
    return list(reversed(names))


def _queued_names(tree: ast.AST) -> set[str]:
    """Names assigned a QueuedConnection (queued = ...ConnectionType.Queued...)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and "QueuedConnection" in ast.unparse(
            node.value
        ):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def _is_queued(call: ast.Call, names: frozenset[str] | set[str] = frozenset()) -> bool:
    texts = [ast.unparse(arg) for arg in call.args[1:]]
    texts += [ast.unparse(kw.value) for kw in call.keywords]
    return any("QueuedConnection" in text or text in names for text in texts)


def _receiver_problem(receiver: ast.AST) -> str | None:
    if isinstance(receiver, ast.Lambda):
        return "a lambda"
    if isinstance(receiver, ast.Name):
        return f"a plain function ({receiver.id})"
    return None


def offenders() -> list[str]:
    found: list[str] = []
    for path in _files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in INPUT_SIDE:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        queued_names = _queued_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "connect" or not node.args:
                continue
            chain = _chain(node.func.value)
            if not chain or chain[-1] not in RUNTIME_SIGNALS:
                continue
            if not (len(chain) >= 2 and chain[-2] in OWNERS
                    or chain[0] in OWNERS):
                continue
            problem = _receiver_problem(node.args[0])
            if problem is None and not _is_queued(node, queued_names):
                problem = "no QueuedConnection"
            if problem:
                where = f"{rel}:{node.lineno}: {'.'.join(chain)}.connect"
                found.append(f"{where}: {problem}")
    return found


def test_scanner_sees_a_bad_link() -> None:
    """The scan itself works: it flags a lambda and a missing QueuedConnection."""
    for source, expect in (
        ("InputModuleRuntime().event.connect(lambda e: None)", "a lambda"),
        ("InputModuleRuntime().event.connect(self.slot)", "no QueuedConnection"),
    ):
        call = ast.parse(source).body[0].value  # type: ignore[attr-defined]
        problem = _receiver_problem(call.args[0])
        if problem is None and not _is_queued(call):
            problem = "no QueuedConnection"
        assert problem == expect
    good = ast.parse(
        "InputModuleRuntime().event.connect(self.slot, "
        "QtCore.Qt.ConnectionType.QueuedConnection)"
    ).body[0].value  # type: ignore[attr-defined]
    assert _is_queued(good) and _receiver_problem(good.args[0]) is None


def test_no_direct_cross_thread_links() -> None:
    bad = offenders()
    assert not bad, (
        "Input-thread signals must be connected with an explicit "
        "QueuedConnection and a QObject slot:\n  " + "\n  ".join(bad)
    )
