# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every Python program a test starts keeps test/hang_trace on its path.

test/hang_trace/sitecustomize.py gives each child its guards: the real
dill.dll refused, the stand-in vJoy, a stack dump when it stalls. A child
env that sets PYTHONPATH to just the repository, or that doesn't start from
os.environ, drops them silently (DL1). Tests build the path with
test/child_env.py, or add to os.environ's PYTHONPATH themselves.

A static check over the test files: each env= given to a call starts from
os.environ (or child_env), and each place that sets PYTHONPATH keeps the
inherited one.
"""

from __future__ import annotations

import ast
import pathlib

_TEST = pathlib.Path(__file__).resolve().parents[1]

# Children that drop the guards on purpose, each checked by hand.
_ALLOWED = {
    # Proves `import dill` loads nothing with no guard in the way, and the
    # guarded child is refused; both paths go through one assignment.
    "unit/test_dill_safety.py",
    # Its child pytest installs test/vjoy_guard.py itself, by path.
    "unit/test_vjoy_guard.py",
}

# Text that shows the inherited PYTHONPATH (or test/hang_trace) is kept.
_KEEPS = (
    'environ.get("PYTHONPATH"',
    "environ.get('PYTHONPATH'",
    'environ["PYTHONPATH"]',
    "child_env.",
    "python_path(",
    "hang_trace",
    "HANG_TRACE",
)
# Text that shows an env starts from this process's environment.
_INHERITS = ("os.environ", "child_env(")


def _keeps(src: str) -> bool:
    return any(k in src for k in _KEEPS)


def _scopes(tree: ast.Module) -> list[ast.AST]:
    scopes: list[ast.AST] = [tree]
    scopes += [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    return scopes


def _own_nodes(scope: ast.AST) -> list[ast.AST]:
    """The nodes of scope, without those of functions inside it."""
    found: list[ast.AST] = []
    todo = list(ast.iter_child_nodes(scope))
    while todo:
        node = todo.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        found.append(node)
        todo.extend(ast.iter_child_nodes(node))
    return found


def problems(src: str) -> list[str]:
    """What drops the guards in one file's source: 'line: reason'."""
    tree = ast.parse(src)
    out: list[str] = []

    lines = src.splitlines(keepends=True)

    def text(node: ast.AST) -> str:
        # ast.get_source_segment splits the whole file on every call: slow.
        start, end = node.lineno - 1, node.end_lineno  # type: ignore[attr-defined]
        if start + 1 == end:
            return lines[start][node.col_offset:node.end_col_offset]  # type: ignore[attr-defined]
        return "".join(lines[start:end])

    for scope in _scopes(tree):
        nodes = _own_nodes(scope)
        assigned: dict[str, list[ast.Assign]] = {}
        for node in nodes:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned.setdefault(target.id, []).append(node)
        for node in nodes:
            # env= given to a call: it must start from os.environ.
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg != "env":
                        continue
                    value = kw.value
                    if isinstance(value, ast.Name):
                        earlier = [
                            a for a in assigned.get(value.id, [])
                            if a.lineno <= node.lineno
                        ]
                        if not earlier:
                            continue  # a parameter or fixture: checked where built
                        value = earlier[-1].value
                    if not any(i in text(value) for i in _INHERITS):
                        out.append(f"{node.lineno}: env= doesn't start from os.environ")
            # PYTHONPATH set as a dict key, keyword or item: must keep the old one.
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=True):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "PYTHONPATH"
                        and not _keeps(text(value))
                    ):
                        out.append(f"{key.lineno}: PYTHONPATH replaced, not kept")
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "PYTHONPATH" and not _keeps(text(kw.value)):
                        out.append(f"{kw.value.lineno}: PYTHONPATH replaced, not kept")
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "PYTHONPATH"
                        and not _keeps(text(node.value))
                    ):
                        out.append(f"{node.lineno}: PYTHONPATH replaced, not kept")
            # Dropped outright: env.pop("PYTHONPATH"), del env["PYTHONPATH"].
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "pop"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "PYTHONPATH"
            ):
                out.append(f"{node.lineno}: PYTHONPATH removed")
            if isinstance(node, ast.Delete) and "PYTHONPATH" in text(node):
                out.append(f"{node.lineno}: PYTHONPATH removed")
            # Filtered out: {k: v for k, v in os.environ.items() if k not in (...)}.
            if (
                isinstance(node, ast.Compare)
                and any(isinstance(op, ast.NotIn) for op in node.ops)
                and any(
                    isinstance(c, ast.Constant) and c.value == "PYTHONPATH"
                    for comp in node.comparators
                    if isinstance(comp, (ast.Tuple, ast.List, ast.Set))
                    for c in comp.elts
                )
            ):
                out.append(f"{node.lineno}: PYTHONPATH filtered out")
            # A Qt child: an empty QProcessEnvironment has no PYTHONPATH at all.
            if (
                isinstance(node, ast.Call)
                and text(node.func).endswith("QProcessEnvironment")
                and not node.args
            ):
                out.append(f"{node.lineno}: empty QProcessEnvironment")
    return sorted(set(out), key=lambda p: int(p.split(":")[0]))


def _files() -> list[pathlib.Path]:
    return sorted(
        p for p in _TEST.rglob("*.py")
        if "hang_trace" not in p.parts and "__pycache__" not in p.parts
    )


def test_no_test_starts_a_child_without_the_guards() -> None:
    found = []
    for path in _files():
        name = path.relative_to(_TEST).as_posix()
        if name in _ALLOWED:
            continue
        source = path.read_text(encoding="utf-8")
        found += [f"test/{name}:{p}" for p in problems(source)]
    assert not found, (
        "A child Python would lose test/hang_trace (dill/vJoy guards, hang "
        "dump); use test/child_env.py:\n" + "\n".join(found)
    )


def test_the_allowed_files_still_need_their_exception() -> None:
    for name in _ALLOWED:
        path = _TEST / name
        assert path.is_file(), f"{name} is gone: remove it from _ALLOWED"
        assert problems(path.read_text(encoding="utf-8")), (
            f"{name} no longer drops the guards: remove it from _ALLOWED"
        )


def test_the_check_finds_each_way_of_dropping_them() -> None:
    bad = [
        # The DL1 pattern (test_editor_load_error and others before the fix).
        'subprocess.run([], env={**os.environ, "PYTHONPATH": str(_ROOT)})',
        'env = dict(os.environ, PYTHONPATH=str(ROOT))\nsubprocess.run([], env=env)',
        'env = dict(os.environ)\nenv["PYTHONPATH"] = str(ROOT)\nrun([], env=env)',
        'env = dict(os.environ)\nenv.pop("PYTHONPATH", None)\nrun([], env=env)',
        'env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}',
        'subprocess.run([], env={"QT_QPA_PLATFORM": "offscreen"})',
        "e = QtCore.QProcessEnvironment()",
    ]
    for src in bad:
        assert problems(src), src
    good = [
        'run([], env={**os.environ, "PYTHONPATH": os.pathsep.join('
        '(str(R), os.environ.get("PYTHONPATH", "")))})',
        'run([], env={**os.environ, "PYTHONPATH": child_env.python_path(R)})',
        "run([], env=child_env.child_env(R, QT_QPA_PLATFORM='offscreen'))",
        'env = dict(os.environ, USERPROFILE="x")\nrun([], env=env)',
    ]
    for src in good:
        assert not problems(src), src
