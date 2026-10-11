"""Calibration's History filter asks the window's list for the device's id
key (08 S43, D-03-DEVICE-FOLDERS): deviceIdOf gives the id key History
entries hold, "" for an unknown row."""

from gremlin.modules import store
from gremlin.ui import module_calibration


def test_device_id_of_gives_the_rows_id_key(monkeypatch, qapp) -> None:  # noqa: ANN001
    guid = "{6F1D2B61-D5A0-11CF-BFC7-444553540000}"
    rows = [{"key": "pJoy Pro", "name": "pJoy Pro", "guid": guid}]
    monkeypatch.setattr(module_calibration, "_source_modules", lambda: rows)
    model = module_calibration.CalibrationModuleModel()
    assert model.deviceIdOf("pjoy pro") == store.id_key("pJoy Pro", guid)
    assert model.deviceIdOf("nothing") == ""
