"""N3: a device change racing the live-physical bind must not drop claims."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from gremlin import device_initialization
from gremlin.modules import runtime


class _Mod:
    is_output = False
    claim = {"claimed": True}


def _bus(monkeypatch: pytest.MonkeyPatch, physical: Callable[[], Any]) -> Any:  # noqa: ANN401
    monkeypatch.setattr(device_initialization, "physical_devices", physical)
    monkeypatch.setattr(runtime.registry, "for_device", lambda name, guid: _Mod())
    return runtime.InputModuleRuntime.klass.__new__(runtime.InputModuleRuntime.klass)


def _dev() -> SimpleNamespace:
    return SimpleNamespace(device_guid="{AAAA}", name="Stick")


def test_one_race_still_binds_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def physical() -> list[SimpleNamespace]:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("dictionary changed size during iteration")
        return [_dev()]

    bus = _bus(monkeypatch, physical)
    claims, dest, passthrough = {}, set(), set()
    bus._bind_live_physical(claims, dest, passthrough)
    assert len(calls) == 2
    assert len(claims) == 1


def test_persistent_failure_raises_so_reload_keeps_old_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def physical() -> list[SimpleNamespace]:
        raise RuntimeError("dictionary changed size during iteration")

    bus = _bus(monkeypatch, physical)
    with pytest.raises(RuntimeError):
        bus._bind_live_physical({}, set(), set())
