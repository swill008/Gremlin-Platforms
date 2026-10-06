# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Guard: what a Run starts goes through gremlin/run_scope.py (map 3, 5).

run_scope is the one owner of the Run number, of the timers and loops a
Run starts and of the keys and buttons it holds, so Stop can end them all.
These checks read the source and fail when something goes around it:

- no main-thread timer (threads.main_timer) outside run_scope and threads;
- no QTimer.singleShot in base_classes or the action plugins (a pulse
  release or an action timer would outlive Stop);
- no second Run counter (_next_run_number) anywhere;
- no thread or thread timer started straight from an action plugin;
- keys pressed down are tracked: send_key_down is defined only in
  keyboard.py and registers the key with run_scope.hold, and only
  keyboard.py and sendinput.py send keys to Windows themselves.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_OWNERS = {"gremlin/run_scope.py", "gremlin/threads.py"}


def _program_files() -> Iterator[Path]:
    yield _ROOT / "joystick_gremlin.py"
    for folder in ("gremlin", "action_plugins"):
        yield from sorted((_ROOT / folder).rglob("*.py"))


def _rel(path: Path) -> str:
    return path.relative_to(_ROOT).as_posix()


def _tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _called(node: ast.Call) -> str:
    """The called name: "main_timer" for threads.main_timer(...)."""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _dotted(node: ast.Call) -> str:
    try:
        return ast.unparse(node.func)
    except Exception:
        return ""


def _calls(path: Path) -> Iterator[ast.Call]:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Call):
            yield node


def test_no_main_thread_timer_outside_run_scope() -> None:
    found = [
        f"{_rel(p)}:{c.lineno}"
        for p in _program_files()
        if _rel(p) not in _OWNERS
        for c in _calls(p)
        if _called(c) == "main_timer"
    ]
    assert found == [], "use run_scope.timer: " + ", ".join(found)


def test_no_single_shot_timer_in_actions_or_base_classes() -> None:
    files = [_ROOT / "gremlin" / "base_classes.py"]
    files += sorted((_ROOT / "action_plugins").rglob("*.py"))
    found = [
        f"{_rel(p)}:{c.lineno}"
        for p in files
        for c in _calls(p)
        if _dotted(c).endswith("QTimer.singleShot")
    ]
    assert found == [], "use run_scope.timer: " + ", ".join(found)


def test_one_run_counter() -> None:
    found = [
        _rel(p)
        for p in _program_files()
        if "_next_run_number" in p.read_text(encoding="utf-8")
    ]
    assert found == []


def test_action_plugins_start_no_threads_themselves() -> None:
    found = [
        f"{_rel(p)}:{c.lineno}"
        for p in sorted((_ROOT / "action_plugins").rglob("*.py"))
        for c in _calls(p)
        if _dotted(c) in {"threads.start", "threads.timer", "gremlin.threads.start"}
        or _dotted(c).endswith(("threading.Thread", "threading.Timer"))
    ]
    assert found == [], "use run_scope.loop / run_scope.timer: " + ", ".join(found)


def test_send_key_down_is_keyboards_and_tracked() -> None:
    defined = [
        _rel(p)
        for p in _program_files()
        for node in ast.walk(_tree(p))
        if isinstance(node, ast.FunctionDef) and node.name == "send_key_down"
    ]
    assert defined == ["gremlin/keyboard.py"]
    keyboard = _tree(_ROOT / "gremlin" / "keyboard.py")
    function = next(
        n
        for n in ast.walk(keyboard)
        if isinstance(n, ast.FunctionDef) and n.name == "send_key_down"
    )
    held = [
        n
        for n in ast.walk(function)
        if isinstance(n, ast.Call) and _dotted(n) == "run_scope.hold"
    ]
    assert held, "keyboard.send_key_down must register the key with run_scope.hold"


def test_only_keyboard_and_sendinput_send_keys_to_windows() -> None:
    allowed = {"gremlin/keyboard.py", "gremlin/sendinput.py"}
    found = [
        f"{_rel(p)}:{c.lineno}"
        for p in _program_files()
        if _rel(p) not in allowed
        for c in _calls(p)
        if _called(c) in {"keybd_event", "SendInput"}
    ]
    assert found == [], ", ".join(found)
