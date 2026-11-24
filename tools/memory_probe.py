# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Memory probe for PYSIDE-WRAPPERS (claude/audits/2026-11-24-upstream-since-fork,
compare-measure.md item 15): do the Python wrappers PySide keeps for
QML-made objects cost memory, and do they keep profiles or devices alive?

Each scenario runs in its own process, off-screen, with a temporary
USERPROFILE, the stand-in hardware (test/fake_hardware.py) and the fake vJoy
of the journey harness (test/journeys/_harness.py): nothing reaches the PC.

    python tools/memory_probe.py                    # A B C D in parallel
    python tools/memory_probe.py --scenarios A,D --reps 10
    python tools/memory_probe.py --child A ...      # one scenario (internal)

Scenarios: A profile load (two profiles in turn), B page switch (Device
Bindings, Keyboard, Logical Device, OSC, Home), C action pane open and close
on a row with Change Mode and Macro, D windows opened and closed, E (not
in the default set) C and A together: profile load, then the pane.

A run is 2 warm-up repetitions, then 3 blocks of --reps repetitions; after
the warm-up and after each block a reading: private bytes, Python heap
(tracemalloc), counts of the QML-made Python types (valid and kept shells),
what the shells' __dict__ reach, QObject count, live Profile count. Raw
readings go to --out as JSON.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import gc
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Types whose presence behind a kept shell means a real hold (plan item 15).
HEAVY = {
    "Profile", "InputItem", "InputItemBinding", "ModeHierarchy", "Mode",
    "Device", "DeviceSummary", "Library", "Settings", "TreeNode",
}  # fmt: skip

WINDOWS = [
    "DialogOptions.qml", "DialogInputViewer.qml", "DialogManageModes.qml",
    "DialogDeviceInformation.qml", "DialogCalibration.qml", "DialogLiveLog.qml",
    "DialogDeviceMappingEditor.qml",
]  # fmt: skip


# +-------------------------------------------------------------------------
# | Measuring


class _Counters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.wintypes.DWORD),
        ("PageFaultCount", ctypes.wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def memory_mb() -> float:
    """The process's private memory, in MB (as in
    test/unit/device_mapping_editor_lifecycle_smoke.py)."""
    counters = _Counters()
    counters.cb = ctypes.sizeof(counters)
    current = ctypes.windll.kernel32.GetCurrentProcess
    current.restype = ctypes.wintypes.HANDLE
    info = ctypes.windll.psapi.GetProcessMemoryInfo
    info.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.POINTER(_Counters),
        ctypes.wintypes.DWORD,
    ]
    info.restype = ctypes.wintypes.BOOL
    info(current(), ctypes.byref(counters), counters.cb)
    return counters.PrivateUsage / (1024 * 1024)


def qml_made_types() -> list[str]:
    """Python types registered with QmlElement that QML files instantiate."""
    decorated = re.compile(r"QmlElement\s*\n(?:\s*@.*\n)*\s*class\s+(\w+)")
    names: set[str] = set()
    for folder in ("gremlin", "action_plugins", "theme"):
        for path in (ROOT / folder).rglob("*.py"):
            names.update(decorated.findall(path.read_text("utf-8", "replace")))
    made: set[str] = set()
    for folder in ("qml", "action_plugins", "theme"):
        for path in (ROOT / folder).rglob("*.qml"):
            text = path.read_text("utf-8", "replace")
            for name in names:
                if name not in made and re.search(rf"(?<![\w.]){name}\s*\{{", text):
                    made.add(name)
    return sorted(made)


def _reach(starts: list[Any], shells: set[int]) -> dict:
    """Everything reachable from the shells' __dict__: unique objects and
    bytes (sys.getsizeof), stopping at modules, classes, functions, code and
    live Qt objects (alive anyway); the HEAVY types met on the way."""
    import types as pytypes

    import shiboken6

    stop = (
        pytypes.ModuleType, type, pytypes.FunctionType, pytypes.BuiltinFunctionType,
        pytypes.CodeType, pytypes.FrameType, pytypes.MethodDescriptorType,
        pytypes.WrapperDescriptorType, pytypes.GetSetDescriptorType,
    )  # fmt: skip
    seen: set[int] = set()
    size = 0
    count = 0
    heavy: dict[str, int] = {}
    heavy_live: dict[str, int] = {}
    kinds: dict[str, int] = {}
    todo = list(starts)
    while todo:
        obj = todo.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        if isinstance(obj, stop):
            continue
        name = type(obj).__name__
        is_wrapper = isinstance(obj, shiboken6.Shiboken.Object)
        if is_wrapper and shiboken6.isValid(obj):
            if name in HEAVY:
                heavy_live[name] = heavy_live.get(name, 0) + 1
            continue  # a live Qt object: not kept by the shell
        if is_wrapper and id(obj) in shells:
            continue  # another shell: counted as its own start
        if name in HEAVY:
            heavy[name] = heavy.get(name, 0) + 1
        try:
            size += sys.getsizeof(obj)
        except Exception:
            pass
        count += 1
        kinds[name] = kinds.get(name, 0) + 1
        try:
            todo.extend(gc.get_referents(obj))
        except Exception:
            pass
    top = sorted(kinds.items(), key=lambda kv: -kv[1])[:8]
    return {
        "objects": count, "bytes": size, "heavy": heavy,
        "heavy_live_reached": heavy_live, "top_kinds": top,
    }  # fmt: skip


def reading(app: Any, names: list[str]) -> dict:  # noqa: ANN401
    import tracemalloc

    import shiboken6
    from PySide6 import QtCore, QtGui

    sys.path.insert(0, str(ROOT / "test" / "journeys"))
    from _harness import pump  # type: ignore[import-not-found]

    js_gc = os.environ.get("MEMPROBE_JS_GC") == "1"
    for _ in range(2):
        if js_gc and getattr(app, "engine", None) is not None:
            app.engine.collectGarbage()  # the QML engine's JavaScript heap
        pump(150)
        gc.collect()
    wanted = set(names)
    valid: dict[str, int] = {}
    kept: dict[str, int] = {}
    shell_objs: list[Any] = []
    profiles = 0
    for obj in gc.get_objects():
        cls = type(obj)
        name = cls.__name__
        if name == "Profile" and cls.__module__ == "gremlin.profile":
            profiles += 1
        if name not in wanted:
            continue
        if shiboken6.isValid(obj):
            valid[name] = valid.get(name, 0) + 1
        else:
            kept[name] = kept.get(name, 0) + 1
            shell_objs.append(obj)
    shell_ids = {id(o) for o in shell_objs}
    starts: list[Any] = []
    by_type: dict[str, list[Any]] = {}
    for obj in shell_objs:
        try:
            d = object.__getattribute__(obj, "__dict__")
        except Exception:
            continue
        starts.append(d)
        by_type.setdefault(type(obj).__name__, []).append(d)
    reach = _reach(starts, shell_ids)
    reach_by_type = {
        name: {k: v for k, v in _reach(ds, shell_ids).items() if k != "top_kinds"}
        | {"dict_keys": sorted({k for d in ds[:50] for k in d.keys()})[:25]}
        for name, ds in by_type.items()
    }
    del shell_objs, starts, by_type
    qobjects = 0
    qclasses: dict[str, int] = {}
    engine = getattr(app, "engine", None)
    roots = list(engine.rootObjects()) if engine is not None else []
    windows = list(QtGui.QGuiApplication.allWindows())
    seen: set[int] = set()
    for root in roots + windows:
        for obj in [root, *root.findChildren(QtCore.QObject)]:
            key = shiboken6.getCppPointer(obj)[0]
            if key not in seen:
                seen.add(key)
                qobjects += 1
                cname = obj.metaObject().className()
                qclasses[cname] = qclasses.get(cname, 0) + 1
    heap = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else 0
    return {
        "private_mb": round(memory_mb(), 2),
        "py_heap_mb": round(heap / (1024 * 1024), 3),
        "valid": valid,
        "kept": kept,
        "kept_total": sum(kept.values()),
        "valid_total": sum(valid.values()),
        "reach": reach,
        "reach_by_type": reach_by_type,
        "qobjects": qobjects,
        "qobject_classes": qclasses,
        "windows": len(windows),
        "profiles": profiles,
        "gc_objects": len(gc.get_objects()),
    }


# +-------------------------------------------------------------------------
# | The scenarios (child process)


def _build_profiles(j: Any) -> tuple[str, str]:  # noqa: ANN401
    """Two saved profiles: p1 with three modes, Change Mode and Macro on
    20 buttons in each mode; p2 with Map to vJoy and Change Mode."""
    from PySide6 import QtCore

    from gremlin import plugin_manager, util
    from gremlin.types import InputType

    pm = plugin_manager.PluginManager()
    uid = j.stick().device_guid.uuid
    urls = []
    for n, modes in ((1, ("Ground", "Air", "Space")), (2, ("Taxi", "Cruise"))):
        j.backend.newProfile()
        profile = j.profile
        for name in modes:
            profile.modes.add_mode(name)
            profile.modes.set_parent(name, "Default")
        for mode in ("Default", *modes):
            for button in range(1, 21):
                item = profile.get_input_item(
                    uid, InputType.JoystickButton, button, mode, True
                )
                root = item.add_item_binding().root_action
                change = pm.create_instance("Change Mode", InputType.JoystickButton)
                root.insert_action(change, "children")
                if n == 1:
                    root.insert_action(
                        pm.create_instance("Macro", InputType.JoystickButton),
                        "children",
                    )
                else:
                    vj = pm.create_instance("Map to vJoy", InputType.JoystickButton)
                    vj.vjoy_device_id = 1
                    vj.vjoy_input_id = button
                    vj.vjoy_input_type = InputType.JoystickButton
                    root.insert_action(vj, "children")
        path = util.profiles_dir() / f"memprobe{n}.xml"
        url = QtCore.QUrl.fromLocalFile(str(path)).toString()
        assert j.backend.saveProfile(url), f"profile {n} not saved"
        urls.append(url)
    return urls[0], urls[1]


def child(scenario: str, reps: int, warm: int, blocks: int) -> None:
    sys.path.insert(0, str(ROOT / "test" / "journeys"))
    from _harness import Journey, pump  # type: ignore[import-not-found]

    names = qml_made_types()

    def before(j: Any) -> None:  # noqa: ANN401
        j.input_module()
        j.vjoy_module()

    j = Journey(before)

    def say(text: str) -> None:
        print(f"[{scenario}] {time.strftime('%H:%M:%S')} {text}", flush=True)

    def story(j: Any) -> None:  # noqa: ANN401
        import tracemalloc

        out = j.out
        out["scenario"] = scenario
        out["types"] = names
        out["readings"] = []
        out["rep_seconds"] = []
        say(f"{len(names)} QML-made Python types")
        rep = _setup(j, scenario, pump, say)
        for _ in range(warm):
            rep()
        say("warm-up done")
        tracemalloc.start(1)
        snaps = []
        r = reading(j.app, names)
        r["block"] = 0
        out["readings"].append(r)
        print("READING " + json.dumps(r, default=str), flush=True)
        for block in range(1, blocks + 1):
            started = time.monotonic()
            for _ in range(reps):
                rep()
            out["rep_seconds"].append(round((time.monotonic() - started) / reps, 3))
            r = reading(j.app, names)
            r["block"] = block
            out["readings"].append(r)
            print("READING " + json.dumps(r, default=str), flush=True)
            say(
                f"block {block}: private {r['private_mb']} MB, heap "
                f"{r['py_heap_mb']} MB, shells {r['kept_total']}, valid "
                f"{r['valid_total']}, qobjects {r['qobjects']}, profiles "
                f"{r['profiles']}"
            )
            if block in (1, blocks):
                gc.collect()
                snaps.append(tracemalloc.take_snapshot())
        if len(snaps) == 2:
            diff = snaps[1].compare_to(snaps[0], "lineno")
            out["tracemalloc_top"] = [str(s) for s in diff[:15]]
        tracemalloc.stop()

    j.run(story)


def _setup(j: Any, scenario: str, pump: Any, say: Any) -> Any:  # noqa: ANN401
    """Returns one repetition of the scenario."""
    if scenario == "A":
        p1, p2 = _build_profiles(j)

        def rep() -> None:
            j.backend.loadProfile(p1)
            pump(500)
            j.backend.loadProfile(p2)
            pump(500)

        return rep

    if scenario == "B":
        j.open_device_bindings("pjoy_pro")
        tabs = (("keyboard", "keyboard"), ("logical", "logical"), ("osc", "osc"),
                ("pjoy_pro", "physical"))  # fmt: skip

        def rep() -> None:
            for slug, tab in tabs:
                j.ev(
                    f"openDeviceBindingsForCard(_moduleModel.cardMap({json.dumps(slug)}))"
                )
                j.wait_until(lambda: j.backend.uiState.currentTab == tab, tab, 10)
                pump(150)
            j.ev('uiState.setCurrentRoom("status")')
            j.wait_until(lambda: j.ev("uiState.currentRoom") == "status", "Home", 10)
            pump(150)
            j.ev(
                f"openDeviceBindingsForCard(_moduleModel.cardMap({json.dumps('pjoy_pro')}))"
            )
            j.wait_until(
                lambda: j.ev("uiState.currentRoom") == "configuration", "pages", 10
            )
            pump(150)

        return rep

    if scenario == "C":
        from gremlin import plugin_manager
        from gremlin.types import InputType

        pm = plugin_manager.PluginManager()
        for name in ("Ground", "Air"):
            j.profile.modes.add_mode(name)
            j.profile.modes.set_parent(name, "Default")
        uid = j.stick().device_guid.uuid
        button = InputType.JoystickButton
        item = j.profile.get_input_item(uid, button, 1, "Default", True)
        root = item.add_item_binding().root_action
        root.insert_action(pm.create_instance("Change Mode", button), "children")
        root.insert_action(pm.create_instance("Macro", button), "children")
        catalog = j.open_device_bindings("pjoy_pro")

        def rep() -> None:
            j.open_input(catalog, "button", 1)
            pump(250)
            catalog.endPane()
            j.wait_until(lambda: catalog.paneModel is None, "pane closed", 10)
            pump(150)

        return rep

    if scenario == "E":
        # C and A together: a pane on a Change Mode row, then a profile
        # load; do old profiles' mode trees stay behind the shells?
        p1, p2 = _build_profiles(j)
        urls = [p1, p2]

        def rep() -> None:
            for url in urls:
                j.backend.loadProfile(url)
                pump(300)
                catalog = j.open_device_bindings("pjoy_pro")
                j.open_input(catalog, "button", 1)
                pump(250)
                catalog.endPane()
                j.wait_until(lambda: catalog.paneModel is None, "pane closed", 10)
                pump(150)

        return rep

    if scenario == "D":
        usable = []
        for qml in WINDOWS:
            try:
                j.ev(f'Helpers.createComponent("{qml}")')
                pump(600)
                j.ev(f'Helpers.windowOf("{qml}").close()')
                pump(300)
                usable.append(qml)
            except Exception as exc:  # noqa: BLE001
                say(f"skipped {qml}: {exc}")
                j.out.setdefault("skipped", []).append(f"{qml}: {exc}")
        j.out["windows_cycled"] = usable
        say(f"windows: {usable}")

        def rep() -> None:
            for qml in usable:
                j.ev(f'Helpers.createComponent("{qml}")')
                pump(250)
                j.ev(f'Helpers.windowOf("{qml}").close()')
                pump(150)

        return rep

    raise ValueError(scenario)


# +-------------------------------------------------------------------------
# | Parent: one process per scenario, in parallel


def parent(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(ROOT / "test"))
    import proc_tree  # type: ignore[import-not-found]

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    threads = []

    def one(scenario: str) -> None:
        home = pathlib.Path(tempfile.mkdtemp(prefix=f"memprobe_{scenario}_"))
        (home / "Gremlin Platforms").mkdir(parents=True, exist_ok=True)
        env = dict(
            os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
            GREMLIN_OFFLINE="1", HTTPS_PROXY="http://127.0.0.1:9",
            PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1",
            QT_QPA_FONTDIR=os.environ.get(
                "QT_QPA_FONTDIR",
                os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")),
        )  # fmt: skip
        env.pop("GREMLIN_TEST_HANG_LIMIT", None)
        cmd = [sys.executable, str(pathlib.Path(__file__).resolve()), "--child",
               scenario, "--reps", str(args.reps), "--warm", str(args.warm),
               "--blocks", str(args.blocks)]  # fmt: skip
        tree = proc_tree.popen(
            cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        )  # fmt: skip
        log = (out_dir / f"{scenario}.log").open("w", encoding="utf-8")
        result = None
        deadline = time.monotonic() + args.timeout
        timer = threading.Timer(args.timeout, tree.kill)
        timer.start()
        try:
            for line in tree.process.stdout:
                log.write(line)
                if line.startswith("RESULT "):
                    result = json.loads(line[len("RESULT ") :])
                elif not line.startswith("READING "):
                    print(f"[{scenario}] {line.rstrip()}"[:400], flush=True)
            tree.process.wait(max(1, deadline - time.monotonic()))
        finally:
            timer.cancel()
            tree.close()
            log.close()
        results[scenario] = result or {"error": "no RESULT line (see log)"}
        (out_dir / f"{scenario}.json").write_text(
            json.dumps(results[scenario], indent=1, default=str), encoding="utf-8"
        )
        print(f"[{scenario}] finished", flush=True)

    for scenario in args.scenarios.split(","):
        t = threading.Thread(target=one, args=(scenario,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    for scenario, res in results.items():
        if "error" in res:
            tail = res.get("traceback", "")[-1500:]
            print(f"[{scenario}] ERROR {res['error']}\n{tail}")
            continue
        for r in res["readings"]:
            print(
                f"[{scenario}] block {r['block']}: private {r['private_mb']} MB"
                f" heap {r['py_heap_mb']} MB shells {r['kept_total']}"
                f" valid {r['valid_total']} qobjects {r['qobjects']}"
                f" profiles {r['profiles']} reach {r['reach']['objects']} obj"
                f" / {r['reach']['bytes']} B heavy {r['reach']['heavy']}"
            )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--child", default="")
    parser.add_argument("--scenarios", default="A,B,C,D")
    parser.add_argument("--reps", type=int, default=25)
    parser.add_argument("--warm", type=int, default=2)
    parser.add_argument("--blocks", type=int, default=3)
    parser.add_argument(
        "--js-gc",
        action="store_true",
        help="run the QML engine's JavaScript garbage collector before each reading",
    )
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--out", default=str(pathlib.Path(tempfile.gettempdir()) / "memory_probe")
    )
    args = parser.parse_args()
    if args.js_gc:
        os.environ["MEMPROBE_JS_GC"] = "1"  # the children inherit it
    if args.child:
        try:
            child(args.child, args.reps, args.warm, args.blocks)
        except Exception:
            print("RESULT " + json.dumps({"error": traceback.format_exc()}), flush=True)
            os._exit(1)
        return 0
    return parent(args)


if __name__ == "__main__":
    sys.exit(main())
