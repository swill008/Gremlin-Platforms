# -*- coding: utf-8; -*-
from unittest.mock import patch

NXT = [
    r"HID\VID_231D&PID_0200\c&2633fd88&0&0000",
    r"HID\VID_231D&PID_2210\8&d3db654&0&0000",
    r"HID\VID_231D&PID_2220\8&26b5150d&0&0000",
    r"HID\VID_231D&PID_2234\8&336e2a8d&0&0000",
    r"HID\VID_231D&PID_3201\c&2165acce&0&0000",
]
PARENT = r"USB\VID_231D&PID_2234\7&2BDEAFD4&0&4"


def test_nxt_interfaces_share_usb_parent_group():
    from gremlin import hidhide_driver as hh
    with patch.object(hh, "_container_id", return_value="per-child"), patch.object(
        hh, "_parent_instance", return_value=PARENT
    ):
        keys = {hh._group_key(k, 0x231D, None) for k in NXT}
    assert len(keys) == 1, keys
    assert next(iter(keys)) == "base:" + PARENT.upper()


def test_different_usb_parents_stay_apart():
    from gremlin import hidhide_driver as hh
    def parent(inst):
        if "PID_0200" in inst:
            return r"USB\VID_231D&PID_AAAA\EVO"
        return PARENT
    with patch.object(hh, "_container_id", return_value=""), patch.object(
        hh, "_parent_instance", side_effect=parent
    ):
        a = hh._group_key(NXT[0], 0x231D, 0x200)
        b = hh._group_key(NXT[3], 0x231D, 0x2234)
    assert a != b


def test_no_parent_does_not_merge_whole_vendor():
    from gremlin import hidhide_driver as hh
    with patch.object(hh, "_container_id", return_value=""), patch.object(
        hh, "_parent_instance", return_value=""
    ):
        keys = {hh._group_key(k, 0x231D, None) for k in NXT}
    assert len(keys) == 5


def test_devices_sort_by_name_then_id():
    from gremlin.ui import hidhide as hh
    rows = [
        {"name": "VKBsim Gladiator EVO R", "instanceId": r"HID\B"},
        {"name": "HID-compliant game controller", "instanceId": r"HID\Z"},
        {"name": "Elgato Stream Deck", "instanceId": r"HID\C"},
        {"name": "hid-compliant game controller", "instanceId": r"HID\A"},
    ]
    assert [r["instanceId"] for r in hh._sorted_devices(rows)] == [
        r"HID\C", r"HID\A", r"HID\Z", r"HID\B",
    ]


def test_saved_programs_load_sorted():
    import json
    from gremlin.ui import hidhide as hh
    saved = json.dumps([
        {"name": "Star Citizen", "path": r"C:\sc.exe"},
        {"name": "DCS", "path": r"C:\dcs.exe"},
        {"name": "elite", "path": r"C:\ed.exe"},
    ])
    with patch.object(hh, "_ensure_options"), patch.object(
        hh.config.Configuration, "value", return_value=saved
    ):
        names = [r["name"] for r in hh._load_games()]
    assert names == ["DCS", "elite", "Star Citizen"]
