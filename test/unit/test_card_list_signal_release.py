"""A Home card list leaves no program-wide connection behind once deleted
(FLK-SWAP): inputItemChanged was connected through a lambda, which held the
list and could never be dropped, so every list ever made kept reloading."""

import gc

from PySide6 import QtCore

from gremlin.signal import signal
from gremlin.ui.module_model import ModuleListModel

_SIGNAL = QtCore.SIGNAL("inputItemChanged(int)")


def _make_and_delete() -> None:
    model = ModuleListModel()
    model.deleteLater()
    del model
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    gc.collect()


def test_a_deleted_card_list_drops_its_input_item_connection(qtbot) -> None:  # noqa: ANN001
    # A first list may make program-wide helpers that stay connected for the
    # whole process (made once, on first use): make one before counting, so
    # only this test's list moves the count, whatever ran before.
    _make_and_delete()
    before = signal.receivers(_SIGNAL)
    model = ModuleListModel()
    assert signal.receivers(_SIGNAL) > before
    model.deleteLater()
    del model
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    gc.collect()
    # Other lists made by earlier tests may be freed meanwhile: never more
    # than before (a leak would leave this list's connection behind).
    assert signal.receivers(_SIGNAL) <= before
