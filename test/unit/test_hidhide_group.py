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
    from gremlin.ui import hidhide as hh
    with patch.object(hh, "_container_id", return_value="per-child"), patch.object(
        hh, "_parent_instance", return_value=PARENT
    ):
        keys = {hh._group_key(k, 0x231D, None) for k in NXT}
    assert len(keys) == 1, keys
    assert next(iter(keys)) == "base:" + PARENT.upper()


def test_different_usb_parents_stay_apart():
    from gremlin.ui import hidhide as hh
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
    from gremlin.ui import hidhide as hh
    with patch.object(hh, "_container_id", return_value=""), patch.object(
        hh, "_parent_instance", return_value=""
    ):
        keys = {hh._group_key(k, 0x231D, None) for k in NXT}
    assert len(keys) == 5
