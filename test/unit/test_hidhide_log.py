# -*- coding: utf-8; -*-
import logging
from unittest.mock import patch


def test_messages_reach_the_system_log(caplog):
    from gremlin.ui import hidhide as hh
    with caplog.at_level(logging.DEBUG, logger="system"):
        hh._hh_log("detail")
        hh._hh_log("step", logging.INFO)
    assert [(r.name, r.levelno, r.getMessage()) for r in caplog.records] == [
        ("system", logging.DEBUG, "HiDHide detail"),
        ("system", logging.INFO, "HiDHide step"),
    ]


def test_missing_driver_at_start_is_a_warning(caplog):
    from gremlin.ui import hidhide as hh
    with patch.object(hh, "_ensure_options"), patch.object(
        hh, "_start_enabled", return_value=True
    ), patch.object(hh, "driver_present", return_value=False):
        with caplog.at_level(logging.WARNING, logger="system"):
            hh.apply_on_start()
    assert [r.getMessage() for r in caplog.records] == [
        "HiDHide start skipped, driver not present",
    ]
