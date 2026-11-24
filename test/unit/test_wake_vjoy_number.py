# -*- coding: utf-8; -*-
"""S42 (12 Screen Saver Mode, D-12-WAKE-VJOY-NUMBER): the keep-off wake line
names a vJoy device by its number and an Xbox pad made by ViGEm, and says
whether this program holds or made it. Fake Windows only: no device is
opened and vJoy is never loaded."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from gremlin import screen_saver_mode as ssm


class _Api:
    """The device lookups _wake_text asks; nothing real."""

    def __init__(self) -> None:
        self.names: dict[int, str] = {}
        self.parts: dict[int, str] = {}
        self.outputs: dict[int, tuple[str, int]] = {}
        self.output_calls = 0

    def device_name(self, handle: int) -> str:
        return self.names.get(handle, "")

    def device_part(self, handle: int) -> str:
        return self.parts.get(handle, "")

    def device_output(self, handle: int) -> tuple[str, int]:
        self.output_calls += 1
        return self.outputs.get(handle, ("", 0))

    def device_physical_id(self, handle: int) -> str:
        return f"phys-{handle}"


@pytest.fixture
def mode(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Screen Saver Mode on a fake Windows and input clock; the output
    module replaced by a fake that says what Gremlin holds and plugged."""
    out = SimpleNamespace(held=[], pads=[], last_write_age_s=lambda: None)
    fake = SimpleNamespace(
        held_vjoy_ids=lambda: list(out.held),
        plugged_xbox_pads=lambda: list(out.pads),
        last_write_age_s=lambda: None,
    )
    monkeypatch.setitem(sys.modules, "gremlin.modules.output", fake)
    api = _Api()
    m = ssm.ScreenSaverMode(api=api, clock_=SimpleNamespace())  # type: ignore[arg-type]
    return SimpleNamespace(mode=m, api=api, out=out)


def _line(k: SimpleNamespace, handle: int) -> str:
    cause = f"{handle}\t{ssm.SEEN_CONTROLLER}\t0\t0.500"
    return k.mode._wake_text(cause, 0.0)  # noqa: SLF001


@pytest.mark.parametrize(
    "path",
    [
        r"\\?\HID#HIDCLASS&Col01#1&2d595ca7&4&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}",
        r"\\?\HID#HIDCLASS&COL01#1&2d595ca7&4&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}",
        r"\\?\HID#HIDCLASS&col01#1&2d595ca7&4&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}",
    ],
)
def test_the_hid_part_is_found_whatever_its_letter_case(path: str) -> None:
    assert ssm.device_part_of_path(path) == "Col01"


def test_a_vjoy_device_gremlin_holds_is_named_as_its_own_output(
    mode: SimpleNamespace,
) -> None:
    mode.api.names[5] = "vJoy Device"
    mode.api.outputs[5] = (ssm.MAKER_VJOY, 3)
    mode.out.held = [1, 3]
    assert "last input vJoy 3 (Gremlin's own output) 0.5 s before" in _line(mode, 5)


def test_a_vjoy_device_gremlin_does_not_hold_says_so(mode: SimpleNamespace) -> None:
    mode.api.outputs[5] = (ssm.MAKER_VJOY, 2)
    mode.out.held = [1, 3]
    assert (
        "last input vJoy 2 (game controller, not held by Gremlin) 0.5 s before"
        in _line(mode, 5)
    )


def test_vjoy_is_not_held_when_the_output_module_is_not_loaded(
    mode: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delitem(sys.modules, "gremlin.modules.output")
    mode.api.outputs[5] = (ssm.MAKER_VJOY, 1)
    assert "vJoy 1 (game controller, not held by Gremlin)" in _line(mode, 5)
    assert "gremlin.modules.output" not in sys.modules


def test_an_xbox_pad_made_by_vigem_while_gremlin_has_pads_plugged(
    mode: SimpleNamespace,
) -> None:
    mode.api.outputs[6] = (ssm.MAKER_VIGEM, 0)
    mode.out.pads = [1]
    assert "last input Xbox pad (Gremlin's own output) 0.5 s" in _line(mode, 6)


def test_an_xbox_pad_made_by_vigem_with_no_pads_from_gremlin(
    mode: SimpleNamespace,
) -> None:
    mode.api.outputs[6] = (ssm.MAKER_VIGEM, 0)
    assert "last input Xbox pad (game controller, not made by Gremlin) 0.5 s" in _line(
        mode, 6
    )


@pytest.mark.parametrize("found", [("", 0), (ssm.MAKER_VJOY, 0)])
def test_without_a_maker_or_number_the_line_stays_as_before(
    mode: SimpleNamespace, found: tuple[str, int]
) -> None:
    mode.api.names[7] = "VKB Gladiator"
    mode.api.parts[7] = "Col01"
    mode.api.outputs[7] = found
    assert "last input VKB Gladiator (game controller, Col01) 0.5 s" in _line(mode, 7)


def test_the_maker_is_looked_up_once_per_handle(mode: SimpleNamespace) -> None:
    mode.api.outputs[5] = (ssm.MAKER_VJOY, 2)
    for _ in range(3):
        _line(mode, 5)
    assert mode.api.output_calls == 1


@pytest.mark.parametrize(
    ("instance_id", "services", "maker"),
    [
        (r"HID\HIDCLASS&COL01\1&2D595CA7&4&0000", ["", "vjoy", ""], ssm.MAKER_VJOY),
        (
            r"HID\VID_045E&PID_028E&IG_00\2&1&0",
            ["", "xusb22", "ViGEmBus"],
            ssm.MAKER_VIGEM,
        ),
        # Another pad on ViGEmBus (not an Xbox 360 pad) is not named an Xbox pad.
        (r"HID\VID_054C&PID_05C4\2&1&0", ["", "HidUsb", "ViGEmBus"], ""),
        (r"HID\VID_231D&PID_2234\8&2FE8E01B&0&0000", ["", "HidUsb", "USBHUB3"], ""),
    ],
)
def test_the_maker_comes_from_the_driver_services_above_the_device(
    instance_id: str, services: list[str], maker: str
) -> None:
    assert ssm.maker_of(instance_id, services) == maker


def test_windows_api_reads_the_vjoy_number_without_opening_the_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = (
        r"\\?\HID#HIDCLASS&Col02#1&2d595ca7&4&0001"
        r"#{4d1e55b2-f16f-11cf-88cb-001111000030}"
    )
    seen: list[Any] = []
    monkeypatch.setattr(ssm, "raw_device_path", lambda h: path)
    monkeypatch.setattr(
        ssm, "device_maker", lambda iid: seen.append(iid) or ssm.MAKER_VJOY
    )
    monkeypatch.setattr(ssm, "hid_report_id", lambda h: 2)
    monkeypatch.setattr(
        ssm, "_hid_product", lambda *_a: pytest.fail("the device was opened")
    )
    assert ssm.WindowsApi().device_output(11) == (ssm.MAKER_VJOY, 2)
    assert seen == [r"HID\HIDCLASS&Col02\1&2d595ca7&4&0001"]
