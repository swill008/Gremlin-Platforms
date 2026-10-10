# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every process a test starts goes through test/proc_tree.py.

subprocess.run(timeout=...) kills only the direct child. The venv's
python.exe is a launcher that starts the real interpreter, so on a timeout
or an error that interpreter (and whatever it started) kept running
(ORPHAN-PROCS). proc_tree.run / proc_tree.popen put the child in a Windows
Job Object that ends the whole tree.

A static check over the test files: no call starts a process any other way
(subprocess, os.system/popen/spawn*, asyncio subprocesses, QProcess).
"""

from __future__ import annotations

import ast
import pathlib

_TEST = pathlib.Path(__file__).resolve().parents[1]

# Files that start a child another way on purpose, each checked by hand.
_ALLOWED = {
    # The runner: ends its parts' trees itself (test_run_tests_tree.py);
    # the lead owns it.
    "run_tests.py": "the test runner, ends its own trees",
    # git only: no Python child, nothing that starts its own.
    "changed_tests.py": "git only",
    "unit/test_control_menu.py": "git show only",
    "unit/test_dependency_lock.py": "git ls-files only",
    "unit/test_spec_line.py": "git log only",
    # A PowerShell device query, no Python child.
    "integration/conftest.py": "PowerShell query only",
    # cmd.exe runs the batch file as the program's launcher would (check=True
    # on its exit code); no Python child.
    "unit/test_device_reset_core.py": "cmd.exe batch, as the program runs it",
    # Being changed by another agent (CRASH-G2, 2026-10-10); move it to
    # proc_tree when that work lands, then drop this line.
    "unit/test_handson_G2_options_labels.py": "in progress elsewhere (CRASH-G2)",
}

_SUBPROCESS = {
    "run", "Popen", "call", "check_call", "check_output",
    "getoutput", "getstatusoutput",
}
_OS = {"system", "popen", "startfile"}
_ASYNCIO = {"create_subprocess_exec", "create_subprocess_shell"}
_QPROCESS = {"start", "startDetached", "execute", "startCommand", "open"}


def _dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def problems(src: str) -> list[str]:
    """Each place in one file's source that starts a process without
    proc_tree: 'line: what'."""
    tree = ast.parse(src)
    out: list[str] = []
    # Names bound by `from subprocess import run` and the like.
    imported: dict[str, str] = {}
    qprocess_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in (
            "subprocess", "os", "asyncio",
        ):
            names = {"subprocess": _SUBPROCESS, "os": _OS, "asyncio": _ASYNCIO}
            for alias in node.names:
                if alias.name in names[node.module] or (
                    node.module == "os" and alias.name.startswith("spawn")
                ):
                    imported[alias.asname or alias.name] = (
                        f"{node.module}.{alias.name}"
                    )
        # p = QtCore.QProcess() / QProcess(): its .start() starts a child.
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and _dotted(node.value.func).split(".")[-1] == "QProcess"
        ):
            for target in node.targets:
                name = _dotted(target)
                if name:
                    qprocess_names.add(name)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted(node.func)
        parts = name.split(".")
        found = ""
        if name in imported:
            found = imported[name]
        elif len(parts) >= 2:
            owner, attr = parts[-2], parts[-1]
            if owner == "subprocess" and attr in _SUBPROCESS:
                found = name
            elif owner == "os" and (attr in _OS or attr.startswith("spawn")):
                found = name
            elif owner == "asyncio" and attr in _ASYNCIO:
                found = name
            elif attr in _QPROCESS and (
                owner == "QProcess" or ".".join(parts[:-1]) in qprocess_names
            ):
                found = name
        if found:
            out.append(f"{node.lineno}: {found}")
    return sorted(set(out), key=lambda p: int(p.split(":")[0]))


def _files() -> list[pathlib.Path]:
    return sorted(
        p for p in _TEST.rglob("*.py")
        if "hang_trace" not in p.parts
        and "__pycache__" not in p.parts
        and p.name != "proc_tree.py"
    )


def test_no_test_starts_a_child_without_proc_tree() -> None:
    found = []
    for path in _files():
        name = path.relative_to(_TEST).as_posix()
        if name in _ALLOWED:
            continue
        source = path.read_text(encoding="utf-8")
        found += [f"test/{name}:{p}" for p in problems(source)]
    assert not found, (
        "A child process that a timeout or error would leave running (the "
        "venv launcher's interpreter, its helpers); use proc_tree.run or "
        "proc_tree.popen (test/proc_tree.py):\n" + "\n".join(found)
    )


def test_the_allowed_files_still_need_their_exception() -> None:
    for name in _ALLOWED:
        path = _TEST / name
        assert path.is_file(), f"{name} is gone: remove it from _ALLOWED"
        assert problems(path.read_text(encoding="utf-8")), (
            f"{name} no longer starts a child without proc_tree: "
            "remove it from _ALLOWED"
        )


def test_the_check_finds_each_way_of_starting_one() -> None:
    bad = [
        "subprocess.run([sys.executable, 'x.py'], timeout=5)",
        "p = subprocess.Popen([sys.executable])",
        "subprocess.check_output(['x'])",
        "from subprocess import run\nrun(['x'])",
        "from subprocess import Popen as P\nP(['x'])",
        "os.system('x')",
        "os.spawnl(os.P_NOWAIT, 'x')",
        "await asyncio.create_subprocess_exec('x')",
        "QtCore.QProcess.startDetached('x', [])",
        "p = QtCore.QProcess()\np.start('x', [])",
        "self.p = QProcess()\nself.p.start('x')",
    ]
    for src in bad:
        assert problems(src), src
    good = [
        "proc_tree.run([sys.executable, 'x.py'], timeout=5, text=True)",
        "tree = proc_tree.popen([sys.executable])\ntree.close()",
        "mock.patch.object(QtCore.QProcess, 'startDetached', start)",
        "monkeypatch.setattr(QtCore.QProcess, 'startDetached', lambda *a: True)",
        "code = 'subprocess.run([sys.executable])'",
        "timer.start(100)",
    ]
    for src in good:
        assert not problems(src), src
