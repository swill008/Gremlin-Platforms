# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Which tests touch the files changed since the last commit
(run_tests.py --changed).

A quick check while working; the full run before a commit stays. A test is
chosen when it:

- is itself a changed test file;
- imports a changed module, or imports a module that imports it (two
  steps: further out nearly every test would be chosen; the full run
  catches the rest). joystick_gremlin and conftest.py import nearly
  everything, so the search does not go through them;
- names a changed QML or JavaScript file, or a QML file that uses one
  (VkbRigEditor uses rig_menu.js, the Button Map window uses VkbRigEditor).
  Tests that start the whole program count as naming Main.qml;
- runs a helper script (button_map_window_smoke.py) chosen the same way,
  or one that imports a chosen helper (button_map_fixes_smoke.py imports
  rig_editor_harness.py);
- names another changed file (the installer script) by its file name.

A changed conftest.py runs its whole folder.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

_ROOT = pathlib.Path(__file__).parents[1]
# Where the program's Python lives (and joystick_gremlin.py at the top).
_CODE = ["gremlin", "action_plugins", "vjoy", "vigem", "dill", "test"]
_QML = ["qml", "theme"]
_TESTS = ["test/unit", "test/action_interaction", "test/integration"]
# Imported by nearly everything: not searched through.
_HUBS = {"joystick_gremlin", "test.unit.conftest", "test.conftest"}
# Steps from a changed module to the tests that use it.
_DEPTH = 2
_IMPORT = re.compile(
    r"(?:^|[\s;'\"(])(?:from\s+([\w.]+)\s+import\s+([\w\s,()*]+)|import\s+([\w.]+))"
)
_SPLIT = re.compile(r"[\s,()]+")
_WHOLE_APP = re.compile(r"JoystickGremlinApp\(|qml/Main\.qml|\"Main\.qml\"")


def changed_files() -> list[str]:
    """Files changed since the last commit, untracked ones included."""
    def git(*args: str) -> list[str]:
        out = subprocess.run(
            ["git", *args], cwd=_ROOT, capture_output=True, text=True, check=False
        ).stdout
        return [line.strip() for line in out.splitlines() if line.strip()]

    files = git("diff", "--name-only", "HEAD") + git(
        "ls-files", "--others", "--exclude-standard"
    )
    return sorted({f.replace("\\", "/") for f in files})


def _module_of(rel: str) -> str:
    return rel[:-3].replace("/", ".").removesuffix(".__init__")


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8", errors="replace")


def _python_files() -> dict[str, str]:
    """Module name: path, for the program's and the tests' Python."""
    found = {"joystick_gremlin": "joystick_gremlin.py"}
    for folder in _CODE:
        for path in (_ROOT / folder).rglob("*.py"):
            rel = path.relative_to(_ROOT).as_posix()
            if "/.venv/" not in rel and "__pycache__" not in rel:
                found[_module_of(rel)] = rel
    return found


_SHORT: dict[int, dict[str, str]] = {}


def _short_names(modules: dict[str, str]) -> dict[str, str]:
    """Test scripts by their own name (test.unit.x as x)."""
    if id(modules) not in _SHORT:
        _SHORT[id(modules)] = {
            m.split(".")[-1]: m for m in modules if m.startswith("test.")
        }
    return _SHORT[id(modules)]


def _imports(text: str, modules: dict[str, str]) -> set[str]:
    """The known modules a file imports (also inside code strings that a
    test runs in another process)."""
    out: set[str] = set()
    for m in _IMPORT.finditer(text):
        base, names, plain = m.group(1), m.group(2), m.group(3)
        if plain:
            parts = plain.split(".")
            for i in range(len(parts), 0, -1):
                name = ".".join(parts[:i])
                if name in modules:
                    out.add(name)
                    break
            else:
                # A test script beside another (import rig_editor_harness).
                if plain in _short_names(modules):
                    out.add(_short_names(modules)[plain])
            continue
        # from gremlin import util: gremlin.util, not the whole package.
        subs = [f"{base}.{n}" for n in _SPLIT.split(names or "")
                if n and f"{base}.{n}" in modules]
        out.update(subs)
        if base in modules and not subs:
            out.add(base)
    return out


def _word(name: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(name)}\b")


def choose(changed: list[str]) -> tuple[list[str], list[str]]:
    """(targets for run_tests, reasons to show)."""
    modules = _python_files()
    texts = {rel: _read(rel) for rel in modules.values()}
    tests = sorted(
        p.relative_to(_ROOT).as_posix()
        for folder in _TESTS for p in (_ROOT / folder).rglob("test_*.py")
    )
    test_texts = {t: texts.get(t) or _read(t) for t in tests}
    helpers = {m: r for m, r in modules.items()
               if r.startswith("test/") and not r.split("/")[-1].startswith("test_")
               and not r.endswith("conftest.py")}
    importers: dict[str, set[str]] = {}
    for module, rel in modules.items():
        for used in _imports(texts[rel], modules):
            importers.setdefault(used, set()).add(module)
    qml_files = {
        p.stem: p.relative_to(_ROOT).as_posix()
        for folder in _QML for p in (_ROOT / folder).rglob("*")
        if p.suffix in (".qml", ".js")
    }
    qml_texts = {stem: _read(rel) for stem, rel in qml_files.items()}

    targets: set[str] = set()
    reasons: list[str] = []
    chosen_helpers: dict[str, str] = {}  # helper module: why

    def pick(test: str, why: str) -> None:
        if test not in targets:
            targets.add(test)
            reasons.append(f"{test}  ({why})")

    for rel in changed:
        name = rel.split("/")[-1]
        if rel in tests:
            pick(rel, "changed")
        elif name == "conftest.py":
            folder = rel.rsplit("/", 1)[0]
            for t in tests:
                if t.startswith(folder + "/"):
                    pick(t, f"{rel} changed")
        elif rel.endswith(".py") and _module_of(rel) in modules:
            start = _module_of(rel)
            seen, front = {start}, {start}
            for _ in range(_DEPTH):
                nxt: set[str] = set()
                for cur in front:
                    for user in importers.get(cur, ()):
                        if user not in seen:
                            seen.add(user)
                            if user not in _HUBS:
                                nxt.add(user)
                front = nxt
            for module in seen:
                if modules[module] in tests:
                    pick(modules[module], f"imports {start}")
                elif module in helpers:
                    chosen_helpers.setdefault(module, f"uses {start}")
        elif name.rsplit(".", 1)[0] in qml_files:
            stem = name.rsplit(".", 1)[0]
            seen, todo = {stem}, [stem]
            while todo:
                word = _word(todo.pop())
                for other, text in qml_texts.items():
                    if other not in seen and word.search(text):
                        seen.add(other)
                        todo.append(other)
            words = [_word(q) for q in seen]
            for t, text in test_texts.items():
                for qml, word in zip(seen, words, strict=True):
                    if word.search(text) or (qml == "Main" and _WHOLE_APP.search(text)):
                        via = "" if qml == stem else f", which uses {name}"
                        pick(t, f"uses {qml}{via}")
                        break
            for helper, path in helpers.items():
                if any(word.search(texts[path]) for word in words):
                    chosen_helpers.setdefault(helper, f"uses {name}")
        else:
            # Anything else a test names by file name (the installer script).
            for t, text in test_texts.items():
                if name in text:
                    pick(t, f"names {name}")

    # Helpers that import a chosen helper, then the tests that run them.
    todo = list(chosen_helpers)
    while todo:
        cur = todo.pop()
        for user in importers.get(cur, ()):
            if user in helpers and user not in chosen_helpers:
                chosen_helpers[user] = chosen_helpers[cur]
                todo.append(user)
    for helper, why in chosen_helpers.items():
        script = modules[helper].split("/")[-1]
        word = _word(helper.split(".")[-1])
        for t, text in test_texts.items():
            if script in text or word.search(text):
                pick(t, f"runs {script}, which {why}")
    return sorted(targets), reasons
