# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Batch 3, agent C2: shell, settings and scripts."""

from __future__ import annotations

import builtins
import pathlib
import threading
import time
import types
import uuid

import pytest
from PySide6 import QtCore

import joystick_gremlin as jg
from gremlin import audio_player, config, run_scope, user_script
from gremlin.ui import backend, option, ui_scale_option, windows_scale_option

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BACKEND = backend.Backend.klass


# --- GL-040: a script's top-level code runs under a time limit -------------


@pytest.fixture
def gate() -> types.SimpleNamespace:
    """An event a test script waits on; released at the end in any case."""
    event = threading.Event()
    builtins._c2_gate = event  # type: ignore[attr-defined]
    yield types.SimpleNamespace(event=event)
    event.set()
    del builtins._c2_gate  # type: ignore[attr-defined]


def _waiting_script(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "waits.py"
    path.write_text(
        "import builtins\n"
        "import gremlin.user_script as us\n"
        "builtins._c2_gate.wait(30)\n"
        "flag = us.BoolVariable('Flag', 'a flag', True, False)\n",
        encoding="utf-8",
    )
    return path


def test_a_script_that_waits_at_load_does_not_freeze_the_program(
    tmp_path: pathlib.Path, gate: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(user_script, "TOP_LEVEL_TIME_LIMIT", 0.3, raising=False)
    # Old code: the load waits for the script; let it go after 3 s.
    releaser = threading.Timer(3.0, gate.event.set)
    releaser.start()
    try:
        started = time.monotonic()
        script = user_script.Script(_waiting_script(tmp_path), "Waits")
        elapsed = time.monotonic() - started
    finally:
        releaser.cancel()
    assert elapsed < 2.0
    assert script.load_error == (
        "Its top-level code did not finish within 0.3 s (it may loop or wait)"
    )
    assert script.variables == {}
    # Once the code finishes, the script loads on the next try (each Run).
    gate.event.set()
    assert script.retry()
    assert "Flag" in script.variables


def test_a_script_error_at_load_is_still_reported(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "broken.py"
    path.write_text("x = 1 / 0\n", encoding="utf-8")
    script = user_script.Script(path, "Broken")
    assert script.load_error.startswith("ZeroDivisionError")


def test_a_script_loads_on_a_worker_thread(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "where.py"
    path.write_text(
        "import threading\n"
        "import gremlin.user_script as us\n"
        "main = threading.current_thread() is threading.main_thread()\n"
        "flag = us.BoolVariable('Flag', 'a flag', True, False)\n",
        encoding="utf-8",
    )
    script = user_script.Script(path, "Where")
    assert script.load_error == ""
    assert script.module.main is False
    assert "Flag" in script.variables


# --- GL-265 (user_script, audio): timed loops run on gremlin.clock ---------


def test_periodic_callbacks_run_on_the_program_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import clock

    now = [1000.0]
    calls: list[float] = []
    registry = user_script.PeriodicRegistry()

    def fake_sleep(seconds: float) -> None:
        now[0] += max(seconds, 0.01)
        if now[0] > 1050.0:
            registry._running = False

    monkeypatch.setattr(clock, "monotonic", lambda: now[0])
    monkeypatch.setattr(clock, "sleep", fake_sleep)
    registry.add(lambda: calls.append(now[0]), 10.0)
    registry._running = True
    registry._loop = token = object()
    loop = threading.Thread(
        target=registry._thread_loop, args=(run_scope.number(), token), daemon=True
    )
    loop.start()
    loop.join(3.0)
    registry._running = False
    loop.join(2.0)
    # Every 10 s of the program's clock (no real time passed).
    assert len(calls) >= 4


def test_the_sound_loop_waits_on_the_program_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import clock

    player = audio_player.AudioPlayer.__new__(audio_player.AudioPlayer)
    player._play_list = []
    player._currently_playing = []
    player._lock = threading.Lock()
    player._playback_mode = "Overlap"
    player._is_ready = True
    slept: list[float] = []

    def fake_sleep(seconds: float) -> None:
        slept.append(seconds)
        player._is_ready = False

    monkeypatch.setattr(clock, "sleep", fake_sleep)
    loop = threading.Thread(target=player._playback, daemon=True)
    loop.start()
    loop.join(2.0)
    player._is_ready = False
    loop.join(1.0)
    assert slept == [0.01]


# --- GL-278: the sound queue is locked -------------------------------------


def test_queueing_a_sound_waits_for_the_queue_lock() -> None:
    player = audio_player.AudioPlayer.__new__(audio_player.AudioPlayer)
    player._play_list = []
    player._currently_playing = []
    player._lock = threading.Lock()
    player._is_ready = True
    with player._lock:
        adder = threading.Thread(target=player.enqueue, args=("a.wav", 50))
        adder.start()
        adder.join(0.2)
        assert player._play_list == []  # held back while the lock is taken
    adder.join(2.0)
    assert player._play_list == [("a.wav", 50)]


# --- GL-205: Device change behavior shows Stop -----------------------------


_DEVICE_CHANGE = ("global", "general", "device-change-behavior")


def test_device_change_behavior_shows_stop_and_stores_disable() -> None:
    cfg = config.Configuration()
    if not cfg.exists(*_DEVICE_CHANGE):
        jg.register_config_options()
    before = cfg.value(*_DEVICE_CHANGE)
    model = option.ConfigEntryModel("global", "general", keys=[_DEVICE_CHANGE])
    index = model.index(0, 0)
    roles = {bytes(v.data()).decode(): k for k, v in model.roles.items()}
    try:
        choices = model.data(index, roles["properties"])["valid_options"]
        assert "Stop" in choices and "Disable" not in choices
        assert model.setData(index, "Stop", roles["value"])
        assert cfg.value(*_DEVICE_CHANGE) == "Disable"
        assert model.data(index, roles["value"]) == "Stop"
        # The stored choices themselves are unchanged.
        assert "Disable" in cfg.properties(*_DEVICE_CHANGE)["valid_options"]
    finally:
        cfg.set(*_DEVICE_CHANGE, before)


def test_device_change_behavior_description_names_stop() -> None:
    cfg = config.Configuration()
    if not cfg.exists(*_DEVICE_CHANGE):
        jg.register_config_options()
    text = cfg.description(*_DEVICE_CHANGE)
    assert "Stop" in text and "Disable" not in text


# --- GL-227: history limits say "checked at start" -------------------------


def test_history_limits_say_they_are_checked_at_start() -> None:
    cfg = config.Configuration()
    if not cfg.exists("global", "history", "keep-days"):
        jg.register_config_options()
    for name in ("keep-days", "max-megabytes"):
        assert "Checked at start." in cfg.description("global", "history", name)


# --- GL-215: --profile not found with no last profile -----------------------


def _process_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, last: str
) -> list[tuple[str, str]]:
    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        jg.gremlin.signal, "display_error",
        lambda message, detail="": shown.append((message, detail)),
    )

    class _Settings:
        def value(self, *_key: str) -> str:
            return last

    monkeypatch.setattr(jg, "Configuration", _Settings)
    opened: list[str] = []
    fake = types.SimpleNamespace(
        syslog=types.SimpleNamespace(warning=lambda *_a: None),
        backend=types.SimpleNamespace(
            loadProfile=opened.append,
            openLastProfile=opened.append,
            activate_gremlin=lambda *_a: None,
            minimize=lambda: None,
        ),
    )
    args = types.SimpleNamespace(
        profile=str(tmp_path / "missing.xml"), enable=False, start_minimized=False
    )
    jg.JoystickGremlinApp.process_cmd_args(fake, args)
    return shown


def test_missing_profile_with_no_last_profile_says_a_new_one_is_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    (_message, detail), = _process_args(monkeypatch, tmp_path, "")
    assert detail.endswith("A new profile is open.")
    assert "last profile" not in detail


def test_missing_profile_with_a_last_profile_says_it_was_opened(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    (_message, detail), = _process_args(monkeypatch, tmp_path, "C:/last.xml")
    assert detail.endswith("The last profile used was opened instead.")


# --- GL-237: one window scan for the second-copy check ---------------------


def test_window_titles_and_ids_come_from_one_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scans: list[None] = []

    def scan() -> list[tuple[int, str, bool]]:
        scans.append(None)
        return [(700, "Gremlin-Platforms R1", True), (701, "Gremlin-Platforms", False)]

    monkeypatch.setattr(jg, "_gremlin_windows", scan, raising=False)
    assert jg._gremlin_window_titles() == ["Gremlin-Platforms R1"]
    assert jg._window_process_ids() == {700, 701}
    assert len(scans) == 2


# --- GL-234: each setting defined once --------------------------------------


def test_ui_scale_settings_are_defined_once() -> None:
    source = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    for name in ('"ui-scale"', '"disable-windows-scaling"'):
        assert f'cfg.register(\n        "ui", "general", {name}' not in source
    cfg = config.Configuration()
    ui_scale_option.register()
    windows_scale_option.register()
    assert cfg.description("ui", "general", "ui-scale") == ui_scale_option.DESCRIPTION
    assert cfg.properties("ui", "general", "ui-scale") == {"min": 70, "max": 200}
    meta = option.MetaConfigOption()
    assert meta.description("ui", "general", "ui-scale") == ui_scale_option.DESCRIPTION
    assert (
        meta.description("ui", "general", "disable-windows-scaling")
        == windows_scale_option.DESCRIPTION
    )


# --- GL-236: the settings core imports no UI or module code ------------------


def test_settings_core_imports_no_ui_or_module_code() -> None:
    import ast

    tree = ast.parse((_ROOT / "gremlin" / "config.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
            imported += [f"{node.module}.{a.name}" for a in node.names]
        elif isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
    assert not [m for m in imported if m.startswith(("gremlin.ui", "gremlin.modules"))]


def test_settings_core_uses_what_the_program_hands_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    traced: list[tuple] = []
    written: list[pathlib.Path] = []
    monkeypatch.setattr(config, "_trace", lambda *a: traced.append(a))
    monkeypatch.setattr(config, "_title", lambda name, key: name.upper())
    monkeypatch.setattr(config, "_write_text", lambda p, t: written.append(p))
    assert config.settings_history_title(["a/b/zoom"]) == "Changed ZOOM"
    config.Configuration().save_now(str(tmp_path / "configuration.json"))
    assert written == [tmp_path / "configuration.json"]
    assert traced and traced[-1][:2] == ("SAVE", "Program Settings")


def test_the_program_hands_the_settings_core_its_helpers() -> None:
    assert config._trace is jg._settings_trace
    assert config._title is jg._settings_title
    assert config._write_text is jg._settings_write
    assert config.settings_history_title(["global/files/plugin-directory"]) == (
        "Changed Plugins folder"
    )


# --- GL-242: the foreground-program monitor runs only with auto-load on ----


def test_the_process_monitor_runs_only_while_auto_load_is_on() -> None:
    calls: list[str] = []
    setting = [False]
    fake = types.SimpleNamespace(
        config=types.SimpleNamespace(value=lambda *_k: setting[0]),
        process_monitor=types.SimpleNamespace(
            start=lambda: calls.append("start"), stop=lambda: calls.append("stop")
        ),
    )
    _BACKEND._sync_process_monitor(fake)
    setting[0] = True
    _BACKEND._sync_process_monitor(fake)
    assert calls == ["stop", "start"]


def test_the_process_monitor_restarts_with_one_loop() -> None:
    from gremlin import process_monitor

    monitor = process_monitor.ProcessMonitor()
    monitor.start()
    first = monitor._update_thread
    monitor.stop()
    monitor.start()
    second = monitor._update_thread
    try:
        assert first is not second
        first.join(2.0)
        assert not first.is_alive() and second.is_alive()
    finally:
        monitor.stop()
    assert not second.is_alive()


# --- GL-251: no re-save of a "converted" profile ---------------------------


def test_opening_a_profile_never_writes_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    from gremlin import profile

    written: list[object] = []
    monkeypatch.setattr(profile.Profile, "from_xml", lambda self, path: True)
    monkeypatch.setattr(
        profile.Profile, "to_xml", lambda self, path: written.append(path)
    )
    fake = types.SimpleNamespace(profile=None)
    _BACKEND._read_profile(fake, str(tmp_path / "p.xml"))
    assert written == []


# --- GL-252: no debug print for an action with no node ---------------------


def test_an_action_with_no_node_is_logged_not_printed(
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    from gremlin.base_classes import AbstractActionData

    fake = types.SimpleNamespace(
        id=uuid.uuid4(), is_valid=lambda: True, _to_xml=lambda: None
    )
    with caplog.at_level("WARNING", logger="system"):
        assert AbstractActionData.to_xml(fake) is None
    assert capsys.readouterr().out == ""
    assert "gave no node to save" in caplog.text


# --- GL-254: the Configuration pane's models are freed ---------------------


def test_only_the_newest_editor_models_are_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui.profile import InputItemModel

    freed: list[int] = []
    monkeypatch.setattr(
        InputItemModel, "deleteLater", lambda self: freed.append(self.enumeration_index)
    )
    owner = QtCore.QObject()
    owner._editor_models = []  # type: ignore[attr-defined]
    owner._KEPT_EDITOR_MODELS = _BACKEND._KEPT_EDITOR_MODELS  # type: ignore[attr-defined]
    item = types.SimpleNamespace()
    for index in range(20):
        _BACKEND._editor_model(owner, item, index)
    kept = _BACKEND._KEPT_EDITOR_MODELS
    assert freed == list(range(20 - kept))
    assert [m.enumeration_index for m in owner._editor_models] == list(
        range(20 - kept, 20)
    )


# --- GL-244 (backend part): program-made events don't highlight ------------


def test_a_program_made_event_does_not_highlight_an_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import shared_state
    from gremlin.signal import signal

    monkeypatch.setattr(shared_state, "suspend_input_highlighting", lambda: False)
    asked: list[object] = []
    fake = types.SimpleNamespace(
        config=types.SimpleNamespace(value=lambda *_k: True),
        joystick_change_monitor=types.SimpleNamespace(
            should_process=lambda e: asked.append(e) or True
        ),
        ui_state=types.SimpleNamespace(currentRoom="work", currentTab="physical",
                                       currentInput=None),
    )
    emitted: list[int] = []
    signal.setInputIndex.connect(emitted.append)
    try:
        event = types.SimpleNamespace(device_guid=uuid.uuid4(), synthetic=True)
        _BACKEND._highlight_input(fake, event)
    finally:
        signal.setInputIndex.disconnect(emitted.append)
    assert asked == [] and emitted == []


# --- GL-238: Module Setup is in the shared window list ---------------------


def test_module_setup_is_kept_in_the_shared_window_list() -> None:
    main = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    assert 'import "window_registry.js" as Registry' in main
    assert (
        "onConfigureWinChanged: "
        'Registry.track("DialogConfigureModule.qml", configureWin)'
        in main
    )
    registry = (_ROOT / "qml" / "window_registry.js").read_text(encoding="utf-8")
    assert "function track(name, window)" in registry
