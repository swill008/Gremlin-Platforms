# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Start with Windows (01 S194): the HKCU Run value and the Options switch.
Every test uses a fake store; the real registry is refused under pytest."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import joystick_gremlin as jg
from gremlin import config, error, startup_entry
from gremlin.types import PropertyType
from gremlin.ui import option

_KEY = ("global", "general", "start-with-windows")


class FakeStore:
    def __init__(self, fail: bool = False) -> None:
        self.values: dict[str, str] = {}
        self.fail = fail

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def set(self, name: str, value: str) -> None:
        if self.fail:
            raise PermissionError("Access is denied")
        self.values[name] = value

    def delete(self, name: str) -> None:
        if self.fail:
            raise PermissionError("Access is denied")
        self.values.pop(name, None)


class _Present(FakeStore):
    def __init__(self) -> None:
        super().__init__()
        self.values["Gremlin-Platforms"] = "x"


class FakeApproved:
    """Read-only StartupApproved record; records every get."""

    def __init__(self, data: object = None, fail: bool = False) -> None:
        self.data = data
        self.fail = fail
        self.reads = 0

    def get(self, name: str) -> bytes | None:
        self.reads += 1
        if self.fail:
            raise PermissionError("Access is denied")
        return self.data if name == "Gremlin-Platforms" else None  # type: ignore[return-value]


@pytest.fixture
def approved(monkeypatch: pytest.MonkeyPatch) -> FakeApproved:
    fake = FakeApproved()
    monkeypatch.setattr(startup_entry, "_RealApprovedStore", lambda: fake)
    return fake


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []
    monkeypatch.setattr(
        startup_entry,
        "open_windows_startup_settings",
        lambda: calls.append(1) or True,
    )
    return calls


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, approved: FakeApproved) -> FakeStore:
    fake = FakeStore()
    monkeypatch.setattr(startup_entry, "_RealStore", lambda: fake)
    return fake


def test_command_is_the_exe_with_start_minimized() -> None:
    exe = r"C:\Program Files\Gremlin-Platforms\Gremlin-Platforms.exe"
    assert startup_entry.command(exe) == f'"{exe}" --start-minimized'


def test_command_frozen_uses_the_running_exe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\GP\Gremlin-Platforms.exe")
    assert startup_entry.command() == r'"C:\GP\Gremlin-Platforms.exe" --start-minimized'


def test_command_from_source_starts_the_entry_script() -> None:
    text = startup_entry.command()
    root = Path(startup_entry.__file__).resolve().parent.parent
    script = root / "joystick_gremlin.py"
    assert text.endswith(f'"{script}" --start-minimized')
    assert text.startswith('"')


def test_on_and_off_write_and_delete_the_value(store: FakeStore) -> None:
    assert not startup_entry.is_enabled()
    assert startup_entry.set_enabled(True)
    assert store.values == {"Gremlin-Platforms": startup_entry.command()}
    assert startup_entry.is_enabled()
    assert startup_entry.set_enabled(False)
    assert store.values == {}
    assert not startup_entry.is_enabled()
    # Off again with nothing there is still done.
    assert startup_entry.set_enabled(False)


def test_is_enabled_reads_any_command() -> None:
    fake = FakeStore()
    fake.values["Gremlin-Platforms"] = r'"D:\old\gp.exe"'
    assert startup_entry.is_enabled(fake, FakeApproved())
    fake.values.clear()
    fake.values["Other"] = "x"
    assert not startup_entry.is_enabled(fake, FakeApproved())


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (None, "on"),
        (b"", "on"),
        (b"\x02\x00\x00\x00", "on"),
        (b"\x06\x00", "on"),
        (b"\x03\x00\x00\x00", "off_in_windows"),
        (b"\x01", "off_in_windows"),
        ("garbage", "on"),
        (12, "on"),
    ],
)
def test_state_reads_the_first_byte(data: object, expected: str) -> None:
    fake = FakeStore()
    fake.values["Gremlin-Platforms"] = "x"
    assert startup_entry.state(fake, FakeApproved(data)) == expected
    assert startup_entry.is_enabled(fake, FakeApproved(data)) is (expected == "on")


def test_state_off_without_the_entry_even_if_record_is_odd() -> None:
    assert startup_entry.state(FakeStore(), FakeApproved(b"\x03")) == "off"


def test_state_unreadable_record_counts_as_absent() -> None:
    fake = FakeStore()
    fake.values["Gremlin-Platforms"] = "x"
    assert startup_entry.state(fake, FakeApproved(fail=True)) == "on"


def test_set_enabled_never_touches_the_approved_record(
    store: FakeStore, approved: FakeApproved
) -> None:
    assert not hasattr(approved, "set")
    assert startup_entry.set_enabled(True)
    assert startup_entry.set_enabled(False)
    assert approved.reads == 0


def test_windows_settings_are_refused_under_pytest() -> None:
    with pytest.raises(startup_entry.RealRegistryBlocked):
        startup_entry.open_windows_startup_settings()


def test_a_refused_write_returns_false_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeStore(fail=True)
    with caplog.at_level("WARNING", logger="system"):
        assert not startup_entry.set_enabled(True, fake)
    assert "Access is denied" in caplog.text
    assert fake.values == {}


def test_the_real_registry_is_refused_under_pytest() -> None:
    with pytest.raises(startup_entry.RealRegistryBlocked):
        startup_entry.is_enabled()
    with pytest.raises(startup_entry.RealRegistryBlocked):
        startup_entry.state(_Present())
    with pytest.raises(startup_entry.RealRegistryBlocked):
        startup_entry.set_enabled(True)


# --- The Options switch -----------------------------------------------------


def _model() -> tuple[option.ConfigEntryModel, dict[str, int]]:
    cfg = config.Configuration()
    try:
        cfg.description(*_KEY)
    except (KeyError, error.GremlinError):
        jg.register_config_options()
    model = option.ConfigEntryModel("global", "general", keys=[_KEY])
    roles = {bytes(v.data()).decode(): k for k, v in model.roles.items()}
    return model, roles


def test_option_is_in_startup_and_tray_with_its_label() -> None:
    general = dict(option._LAYOUT)["General"]  # noqa: SLF001
    assert _KEY in dict(general)["Startup and Tray"]
    assert option.entry_title("start-with-windows") == (
        "Start Gremlin-Platforms when Windows starts"
    )
    cfg = config.Configuration()
    _model()
    assert cfg.data_type(*_KEY) == PropertyType.Bool


def test_option_shows_windows_list_and_changes_it(store: FakeStore) -> None:
    model, roles = _model()
    index = model.index(0, 0)
    before = config.Configuration().value(*_KEY)
    try:
        assert model.data(index, roles["value"]) is False
        store.values["Gremlin-Platforms"] = "x"
        assert model.data(index, roles["value"]) is True
        store.values.clear()
        assert model.setData(index, True, roles["value"])
        assert "Gremlin-Platforms" in store.values
        assert model.data(index, roles["value"]) is True
        assert model.setData(index, False, roles["value"])
        assert store.values == {}
        assert model.data(index, roles["value"]) is False
    finally:
        config.Configuration().set(*_KEY, before)


def test_option_off_in_windows_shows_the_note_and_opens_settings(
    store: FakeStore, approved: FakeApproved, opened: list[int]
) -> None:
    model, roles = _model()
    index = model.index(0, 0)
    before = config.Configuration().value(*_KEY)
    try:
        # On: no note beyond the normal description.
        store.values["Gremlin-Platforms"] = "x"
        normal = model.data(index, roles["description"])
        assert startup_entry.NOTE_OFF_IN_WINDOWS not in str(normal)
        approved.data = b"\x03\x00"
        assert model.data(index, roles["value"]) is False
        assert model.data(index, roles["description"]) == (
            startup_entry.NOTE_OFF_IN_WINDOWS
        )
        changed: list[int] = []
        model.dataChanged.connect(lambda *_a: changed.append(1))
        assert not model.setData(index, True, roles["value"])
        assert opened == [1]
        assert changed
        # The Run value is left alone; nothing was written anywhere.
        assert store.values == {"Gremlin-Platforms": "x"}
        assert approved.data == b"\x03\x00"
        assert config.Configuration().value(*_KEY) == before
        # Turning it off from this state still removes the entry.
        assert model.setData(index, False, roles["value"])
        assert store.values == {}
        assert opened == [1]
    finally:
        config.Configuration().set(*_KEY, before)


def test_option_failure_puts_the_switch_back(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake = FakeStore(fail=True)
    monkeypatch.setattr(startup_entry, "_RealStore", lambda: fake)
    monkeypatch.setattr(startup_entry, "_RealApprovedStore", FakeApproved)
    model, roles = _model()
    index = model.index(0, 0)
    changed: list[int] = []
    model.dataChanged.connect(lambda *_a: changed.append(1))
    before = config.Configuration().value(*_KEY)
    with caplog.at_level("WARNING", logger="system"):
        assert not model.setData(index, True, roles["value"])
    assert changed, "the switch is told to read Windows' value again"
    assert model.data(index, roles["value"]) is False
    assert config.Configuration().value(*_KEY) == before
    assert "was not changed" in caplog.text
