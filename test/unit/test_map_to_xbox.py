# -*- coding: utf-8; -*-
from unittest import mock

import pytest

from action_plugins import map_to_xbox as mx
from gremlin.types import HatDirection
from vigem import xbox


@pytest.mark.parametrize(
    "current, pressed",
    [
        ((0, 0), False),
        ((0, 1), True),
        ((-1, -1), True),
        (HatDirection.Center, False),
        (HatDirection.East, True),
        (True, True),
        (False, False),
    ],
)
def test_hat_is_pressed_only_off_center(current: object, pressed: bool) -> None:
    assert mx._is_pressed(current) is pressed


@pytest.mark.parametrize(
    "current, full, upper",
    [(-1.0, -1.0, -1.0), (0.0, 0.0, -1.0), (0.5, 0.5, 0.0), (1.0, 1.0, 1.0)],
)
def test_trigger_range(current: float, full: float, upper: float) -> None:
    assert mx._trigger_value(current, mx.TRIGGER_FULL) == pytest.approx(full)
    assert mx._trigger_value(current, mx.TRIGGER_UPPER) == pytest.approx(upper)


def test_trigger_range_is_saved_and_old_profiles_stay_full() -> None:
    data = mx.MapToXboxData()
    assert data.trigger_range == mx.TRIGGER_FULL
    data.trigger_range = mx.TRIGGER_UPPER
    node = data._to_xml()
    loaded = mx.MapToXboxData()
    loaded._from_xml(node, None)
    assert loaded.trigger_range == mx.TRIGGER_UPPER

    for prop in list(node):
        if "trigger-range" in (prop.findtext("name") or ""):
            node.remove(prop)
    old = mx.MapToXboxData()
    old._from_xml(node, None)
    assert old.trigger_range == mx.TRIGGER_FULL


def test_available_checks_again_after_a_failure() -> None:
    proxy = xbox.XboxProxy.__new__(xbox.XboxProxy)
    proxy._busp = 0
    proxy._pads = {}
    proxy._available = None
    results = [False, True]
    with mock.patch.object(xbox.XboxProxy, "_probe", side_effect=results) as probe:
        assert proxy.available() is False
        assert proxy.available() is True
        assert proxy.available() is True
    assert probe.call_count == 2


def test_old_profile_without_trigger_range_logs_no_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    node = mx.MapToXboxData()._to_xml()
    for prop in list(node):
        if "trigger-range" in (prop.findtext("name") or ""):
            node.remove(prop)
    with caplog.at_level("ERROR"):
        loaded = mx.MapToXboxData()
        loaded._from_xml(node, None)
    assert loaded.trigger_range == mx.TRIGGER_FULL
    assert "trigger-range" not in caplog.text


# --- The pad list follows Xbox Setup's pad count (D-XBOX-PADS) ---------------


@pytest.fixture
def pads_world(qapp: object, tmp_path, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN001, ANN201
    """A temp modules folder with pad 1's Xbox module; the Xbox driver is
    reported there (faked) so only the pad count decides the ⚠."""
    from gremlin.modules import output, registry, store
    from test.unit._device_folders import put_module

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(output, "xbox_available", lambda: True)
    registry._cache.clear()
    put_module(
        folder,
        "Xbox 360 Controller",
        {
            "device": "Xbox 360 Controller",
            "direction": "dest",
            "claim": {"axes": [], "buttons": [], "hats": [], "keys": []},
        },
    )
    output.refresh()
    _settle(qapp)
    yield folder
    _settle(qapp)
    registry._cache.clear()
    output.refresh()
    _settle(qapp)


def _settle(qapp: object) -> None:  # noqa: ANN401
    for _ in range(5):
        qapp.processEvents()  # type: ignore[attr-defined]


def _editor(pad: int) -> tuple[object, object]:
    """The Map to Xbox editor's model for an action on this pad."""
    from action_plugins.root import RootData
    from gremlin.profile import InputItem, InputItemBinding, Profile
    from gremlin.types import InputType
    from gremlin.ui.profile import InputItemBindingModel

    action = mx.MapToXboxData(InputType.JoystickButton)
    action.xbox_device_id = pad
    profile = Profile()
    item = InputItem(profile.library)
    binding = InputItemBinding(item)
    binding.root_action = RootData(InputType.JoystickButton)
    binding.behavior = InputType.JoystickButton
    profile.library.add_action(binding.root_action)
    profile.library.add_action(action)
    binding.root_action.insert_action(action, "children")
    model = InputItemBindingModel(binding)
    am = next(m for m in model._action_models.values() if m.action_data is action)
    return model, am


def _pads(am: object) -> list[int]:
    return [c["value"] for c in am.padChoices]  # type: ignore[attr-defined]


def test_pad_list_is_the_pads_that_are_on(qapp: object, pads_world) -> None:  # noqa: ANN001
    from gremlin.modules import output

    output.set_xbox_pad_count(2)
    _settle(qapp)
    _keep, am = _editor(1)
    assert _pads(am) == [1, 2]
    assert am.padChoices[1]["label"] == output.xbox_pad_label(2)  # type: ignore[attr-defined]


def test_an_action_on_a_pad_outside_the_count_keeps_it_with_the_warning(
    qapp: object,
    pads_world,  # noqa: ANN001
) -> None:
    from gremlin.modules import output

    output.set_xbox_pad_count(2)
    _settle(qapp)
    _keep, am = _editor(3)
    assert _pads(am) == [1, 2, 3]
    assert am.cantSendText  # type: ignore[attr-defined]
    assert am.cantSendText == output.xbox_cant_send_text(3)  # type: ignore[attr-defined]
    assert "Xbox Setup" in am.cantSendText  # type: ignore[attr-defined]


def test_raising_the_count_updates_the_open_editor(
    qapp: object,
    pads_world,  # noqa: ANN001
) -> None:
    from gremlin.modules import output

    output.set_xbox_pad_count(2)
    _settle(qapp)
    _keep, am = _editor(3)
    seen: list[bool] = []
    am.cantSendTextChanged.connect(lambda: seen.append(True))  # type: ignore[attr-defined]
    output.set_xbox_pad_count(4)
    _settle(qapp)
    assert seen, "the open Map to Xbox editor wasn't told the pad count changed"
    assert _pads(am) == [1, 2, 3, 4]
    assert am.cantSendText == ""  # type: ignore[attr-defined]
