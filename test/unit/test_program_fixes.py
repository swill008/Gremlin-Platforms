# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Program and update problems (3 Oct review, APP6, APP7, APP9, APP10,
APP12, APP14).

- Played sounds stayed in memory with their decoded audio, and decoding ran
  on the event thread (APP6).
- An update that failed left the program closed and said nothing (APP7).
- Every start ran three PowerShell process scans, about 4 seconds (APP9).
- A relative --profile path was read from the install folder, and a missing
  one was ignored without a word (APP10).
- A failed write of the download (a full disk) was reported as a checksum
  mismatch, and a failed rename crashed (APP12).
- Live in the Live Log Reader drew the whole view again for every new line
  and dropped any selection (APP14).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import argparse
import json
import os
import pathlib
import subprocess
import threading
from types import SimpleNamespace
from unittest import mock

import pytest
from PySide6 import QtCore

_ROOT = pathlib.Path(__file__).parents[2]
_app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


# APP6 ---------------------------------------------------------------------


class _Sample:
    made: list[str] = []

    def __init__(self, file_name: str, volume: int) -> None:
        _Sample.made.append(file_name)
        self.done = False

    def play(self) -> None:
        pass

    def cancel(self) -> None:
        self.done = True

    def block(self, still_wanted: object) -> None:
        pass


@pytest.fixture
def player(monkeypatch: pytest.MonkeyPatch) -> object:
    from gremlin import audio_player

    _Sample.made = []
    monkeypatch.setattr(audio_player, "AudioSample", _Sample)
    p = object.__new__(audio_player.AudioPlayer)
    p._play_list = []
    p._currently_playing = []
    p._playback_mode = "Overlap"
    p._is_ready = True
    p._lock = threading.Lock()
    return p


def _one_round(player: object, monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import audio_player

    def stop(_seconds: float) -> None:
        player._is_ready = False

    monkeypatch.setattr(audio_player.clock, "sleep", stop)
    player._is_ready = True
    player._playback()


def test_sounds_are_decoded_on_the_playback_thread(
    player: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    player.enqueue("beep.wav", 80)
    assert _Sample.made == []  # queuing (the event thread) decodes nothing
    _one_round(player, monkeypatch)
    assert _Sample.made == ["beep.wav"]


def test_finished_sounds_are_let_go(
    player: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    player.enqueue("a.wav", 80)
    _one_round(player, monkeypatch)
    assert len(player._currently_playing) == 1  # still playing
    player._currently_playing[0].done = True
    _one_round(player, monkeypatch)
    assert player._currently_playing == []  # with its decoded audio


def test_a_sound_that_cannot_be_decoded_is_logged_once(
    player: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import audio_player

    def bad(file_name: str, volume: int) -> None:
        raise RuntimeError("cannot decode")

    monkeypatch.setattr(audio_player, "AudioSample", bad)
    with mock.patch.object(audio_player, "log_once") as logged:
        player.enqueue("damaged.wav", 80)
        _one_round(player, monkeypatch)
    assert "could not play 'damaged.wav'" in logged.call_args.args[3]
    assert player._currently_playing == []


# APP7 ---------------------------------------------------------------------


@pytest.fixture
def updates(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    from gremlin import updater

    monkeypatch.setattr(updater, "updates_dir", lambda: tmp_path)
    return tmp_path


def test_the_update_being_installed_is_noted(
    monkeypatch: pytest.MonkeyPatch, updates: pathlib.Path
) -> None:
    from gremlin.ui import update_model

    monkeypatch.setattr(QtCore.QProcess, "startDetached", lambda *args: True)
    setup = updates / "Gremlin-Platforms-R1-99.0.0-Setup.exe"
    setup.write_bytes(b"x")
    model = update_model.UpdateModel()
    model._release = SimpleNamespace(version="99.0.0")
    model._ready_path = setup
    model.setInstallOnExit(True)
    assert model.start_pending_install()
    assert model._config.value(*update_model._PENDING) == "99.0.0"
    assert model._config.value(*update_model._PENDING_SETUP) == str(setup)


def test_a_failed_update_is_told_with_try_again(updates: pathlib.Path) -> None:
    from gremlin.ui import update_model

    model = update_model.UpdateModel()
    setup = updates / "Gremlin-Platforms-R1-99.0.0-Setup.exe"
    model._config.set(*update_model._PENDING, "99.0.0")
    model._config.set(*update_model._PENDING_SETUP, str(setup))
    offered = []
    model.offerUpdate.connect(lambda: offered.append(1))
    with mock.patch.object(model, "check") as check:
        model.startup()
    check.assert_not_called()  # the failure is shown, not a new offer
    assert model.state == "failed" and offered == [1]
    assert model.failedVersion == "99.0.0"
    assert model.failedLog == str(setup.with_suffix(".log"))
    assert model._config.value(*update_model._PENDING) == ""  # told once
    with mock.patch.object(model, "check") as check:
        model.retryUpdate()
    check.assert_called_once_with(True)
    # The check finds that version: it is downloaded (or the kept, checked
    # download used) and installed.
    model._kind = update_model.updater.INSTALLED
    release = SimpleNamespace(version="99.0.0", setup=object(), page_url="")
    reply = mock.Mock()
    reply.error.return_value = update_model.QtNetwork.QNetworkReply.NetworkError.NoError
    reply.readAll.return_value = QtCore.QByteArray(b"{}")
    with (
        mock.patch.object(update_model.updater, "parse_release", return_value=release),
        mock.patch.object(model, "download") as download,
    ):
        model._on_checked(reply)
    download.assert_called_once()


def test_a_finished_update_is_not_a_failure(updates: pathlib.Path) -> None:
    from gremlin import util
    from gremlin.ui import update_model

    model = update_model.UpdateModel()
    model._config.set(*update_model._PENDING, util.get_code_version())
    assert model._note_failed_update() is False
    assert model.state == "idle"


def test_setup_starts_the_previous_version_again_when_an_update_fails() -> None:
    iss = (_ROOT / "installer" / "gremlin_platforms.iss").read_text(encoding="utf-8")
    deinit = iss[iss.index("procedure DeinitializeSetup;"):]
    deinit = deinit[: deinit.index("\nend;") + 5]
    assert "not Finished and LaunchAfterSilentUpdate" in deinit
    assert "ExecAsOriginalUser(AppExe" in deinit
    assert "AppExe := AppFile('{#MyAppExeName}');" in iss


def test_the_update_dialog_has_the_failed_state() -> None:
    qml = (_ROOT / "qml" / "DialogUpdate.qml").read_text(encoding="utf-8")
    assert 'case "failed":' in qml
    assert "updater.retryUpdate()" in qml


# APP9 ---------------------------------------------------------------------


def test_a_clean_start_runs_no_process_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    import joystick_gremlin as jg

    scans = []
    monkeypatch.setattr(
        jg, "_command_line_process_ids", lambda: scans.append(1) or set()
    )
    monkeypatch.setattr(jg, "acquire_instance_lock", lambda: "lock")
    monkeypatch.setattr(jg, "_gremlin_window_titles", lambda: [])
    assert jg._check_second_copy() == ("lock", True)
    assert scans == []


def test_the_process_scan_runs_once_per_check(monkeypatch: pytest.MonkeyPatch) -> None:
    import joystick_gremlin as jg

    scans = []
    monkeypatch.setattr(
        jg, "_command_line_process_ids", lambda: scans.append(1) or {700}
    )
    monkeypatch.setattr(jg, "_process_image_name", lambda pid: "python.exe")
    monkeypatch.setattr(jg, "acquire_instance_lock", lambda: None)

    def titles() -> list[str]:
        # Two python windows, each asks whether it runs Gremlin.
        assert jg._is_gremlin_process(700) and not jg._is_gremlin_process(800)
        return ["Gremlin-Platforms R1"]

    monkeypatch.setattr(jg, "_gremlin_window_titles", titles)
    monkeypatch.setattr(jg, "_window_process_ids", lambda: {700})
    monkeypatch.setattr(jg, "_this_process_tree", lambda: {os.getpid()})
    monkeypatch.setattr(jg, "_lock_owner_pid", lambda: None)
    prompts = []
    monkeypatch.setattr(
        jg, "_confirm_second_instance",
        lambda held, wins, pids: prompts.append(pids) or "quit",
    )
    assert jg._check_second_copy() == (None, False)
    assert prompts == [[700]] and scans == [1]
    assert jg._scan_cache is None  # outside the check, scans are fresh


# APP10 --------------------------------------------------------------------


def _start_with_profile(
    monkeypatch: pytest.MonkeyPatch, launch: pathlib.Path, profile: str,
    last: pathlib.Path,
) -> tuple[list, list]:
    import joystick_gremlin as jg

    monkeypatch.setattr(jg, "launch_dir", str(launch))
    monkeypatch.setattr(
        jg, "Configuration",
        lambda: SimpleNamespace(value=lambda *key: str(last)),
    )
    loaded: list = []
    told: list = []
    monkeypatch.setattr(
        jg.gremlin.signal, "display_error", lambda *a: told.append(a)
    )
    app = SimpleNamespace(
        backend=SimpleNamespace(
            loadProfile=loaded.append, openLastProfile=loaded.append
        ),
        syslog=mock.Mock(),
    )
    args = argparse.Namespace(profile=profile, enable=False, start_minimized=False)
    jg.JoystickGremlinApp.process_cmd_args(app, args)
    return loaded, told


def test_a_relative_profile_is_read_from_where_the_program_started(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    (tmp_path / "profiles").mkdir()
    wanted = tmp_path / "profiles" / "flight.xml"
    wanted.write_text("<profile/>")
    loaded, told = _start_with_profile(
        monkeypatch, tmp_path, "profiles/flight.xml", tmp_path / "last.xml"
    )
    assert loaded == [os.path.normpath(str(wanted))] and told == []


def test_a_missing_profile_is_told_and_the_last_one_opens(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    last = tmp_path / "last.xml"
    last.write_text("<profile/>")
    loaded, told = _start_with_profile(monkeypatch, tmp_path, "gone.xml", last)
    assert loaded == [str(last)]
    assert told[0][0] == "Profile not found."
    assert str(tmp_path / "gone.xml") in told[0][1]


# APP12 --------------------------------------------------------------------


def _downloading(
    model: object, part: pathlib.Path, write: object
) -> None:
    model._release = SimpleNamespace(
        version="99.0.0", page_url="",
        setup=SimpleNamespace(name="Setup.exe", size=1, sha256="x", url=""),
    )
    reply = mock.Mock()
    reply.readAll.return_value = QtCore.QByteArray(b"data")
    reply.error.return_value = (
        __import__("PySide6.QtNetwork").QtNetwork.QNetworkReply.NetworkError.NoError
    )
    model._reply = reply
    model._file = SimpleNamespace(
        write=write, flush=lambda: True, close=lambda: None,
        fileName=lambda: str(part),
        errorString=lambda: "There is not enough space on the disk",
    )


def test_a_full_disk_is_reported_as_one(
    updates: pathlib.Path,
) -> None:
    from gremlin.ui import update_model

    part = updates / "Setup.part"
    part.write_bytes(b"da")  # what got written before the disk filled
    model = update_model.UpdateModel()
    _downloading(model, part, write=lambda data: -1)
    model._on_data()
    model._reply.abort.assert_called_once()  # no point downloading the rest
    model._on_downloaded()
    assert model.state == "error"
    assert model.errorText.startswith("Could not save the download")
    assert "not enough space" in model.errorText and "checksum" not in model.errorText
    assert not part.exists()


def test_a_download_that_cannot_be_renamed_says_so(
    updates: pathlib.Path,
) -> None:
    from gremlin.ui import update_model

    part = updates / "Setup.part"
    part.write_bytes(b"x")
    model = update_model.UpdateModel()
    _downloading(model, part, write=lambda data: data.size())
    with (
        mock.patch.object(update_model.updater, "file_matches", return_value=True),
        mock.patch.object(
            pathlib.Path, "rename", side_effect=PermissionError("in use")
        ),
    ):
        model._on_downloaded()
    assert model.state == "error"
    assert "Could not save the download" in model.errorText


def test_an_updates_folder_that_cannot_be_made_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui import update_model

    folder = mock.Mock()
    folder.mkdir.side_effect = PermissionError("denied")
    monkeypatch.setattr(update_model.updater, "updates_dir", lambda: folder)
    model = update_model.UpdateModel()
    model._kind = update_model.updater.INSTALLED
    model._release = SimpleNamespace(version="99.0.0", setup=SimpleNamespace())
    model.download()
    assert model.state == "error" and "Could not save the download" in model.errorText


# APP14 --------------------------------------------------------------------

_LIVE = r"""
import json, os, sys, time
sys.path.insert(0, '.')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6 import QtCore, QtGui, QtQml, QtQuick
from gremlin.ui import live_debug
app = QtGui.QGuiApplication([])
engine = QtQml.QQmlApplicationEngine()
engine.loadData(b'''
import QtQuick
TextEdit { width: 800; height: 600; textFormat: TextEdit.RichText
  readOnly: true; wrapMode: TextEdit.NoWrap }
''')
view = engine.rootObjects()[0]
live_debug.MAX_SESSION = 300
log = live_debug.DebugLog()
log._logging_on = lambda: True
log._session = []
log._live = True
log._file = 'all'
log._apply()
holder = view.property('textDocument')
log.attachView(holder)
redraws = []
log.changed.connect(lambda: redraws.append(1))
def show():
    view.setProperty('text', log.html)
show()
feed = []
def take_new():
    new = feed.pop(0) if feed else []
    log._session.extend(new)
    del log._session[:-live_debug.MAX_SESSION]  # as the feed's own does
    return new
log._take_new = take_new
def lines(n, start):
    return [(1 if i % 5 else 3, 'System', f'line {i}') for i in range(start, start + n)]
feed.append(lines(250, 0))
log.refresh()
# The user selects line 1 to copy it.
doc = holder.textDocument()
text = doc.toPlainText()
start = text.index('line 1\n')
view.select(start, start + len('line 1'))
times = []
for k in range(10):
    feed.append(lines(25, 250 + k * 25))
    t = time.perf_counter()
    log.refresh()
    times.append(time.perf_counter() - t)
plain = holder.textDocument().toPlainText().split('\n')
print(json.dumps({
    'redraws': len(redraws),
    'first': plain[0], 'last': plain[-1], 'count': len(plain),
    'shown': [t for _r, t in log._shown][:1] + [t for _r, t in log._shown][-1:],
    'selected': view.property('selectedText'),
    'shownCount': log.shownCount, 'total': log.totalCount,
    'red': doc.toHtml().count('#f87171'),
    'slowest_ms': max(times) * 1000,
}))
"""


def test_live_adds_rows_without_drawing_the_view_again() -> None:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    env.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    done = subprocess.run(
        [sys.executable, "-c", _LIVE], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["redraws"] == 0  # every Live line was added, none redrawn
    # 500 lines, the view keeps the last 300: the top ones dropped off.
    assert out["count"] == 300 and out["first"] == "line 200"
    assert out["last"] == "line 499"
    assert out["shown"] == ["line 200", "line 499"]
    assert out["shownCount"] == 300 and out["total"] == 300
    assert out["red"] == 60  # every fifth line is an error, in color
    assert out["selected"] == "line 1" or out["selected"] == ""
    assert out["slowest_ms"] < 100


def test_the_view_holds_redraws_while_text_is_selected() -> None:
    qml = (_ROOT / "qml" / "DialogLiveLog.qml").read_text(encoding="utf-8")
    assert "if (_view.selectedText.length > 0) {" in qml
    assert "_area.show(_area.source())" in qml
    assert "_debug.attachView(_debugView.document)" in qml
    assert "function onAppended() { _debugView.added() }" in qml
