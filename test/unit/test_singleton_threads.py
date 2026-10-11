# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Shared singletons are built once even when threads ask at the same time."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator

import pytest

from gremlin.common import SingletonDecorator, SingletonMetaclass

_JOIN_S = 5.0


def _race(make: Callable[[], object], count: int = 4) -> list:
    """Calls make() from several threads released together; returns results."""
    gate = threading.Barrier(count)
    results: list = []
    lock = threading.Lock()

    def run() -> None:
        gate.wait(timeout=_JOIN_S)
        obj = make()
        with lock:
            results.append(obj)

    threads = [threading.Thread(target=run, daemon=True) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=_JOIN_S)
        assert not t.is_alive()
    return results


@pytest.fixture
def clean_instances() -> Iterator[list[type]]:
    made: list[type] = []
    yield made
    for cls in made:
        SingletonMetaclass._instances.pop(cls, None)


def test_metaclass_two_threads_build_one_instance(clean_instances: list[type]) -> None:
    built: list[object] = []

    class Slow(metaclass=SingletonMetaclass):
        def __init__(self) -> None:
            built.append(self)
            time.sleep(0.05)

    clean_instances.append(Slow)
    results = _race(Slow)
    assert len(built) == 1
    assert len(results) == 4
    assert all(r is built[0] for r in results)
    assert SingletonMetaclass._instances[Slow] is built[0]


def test_decorator_two_threads_build_one_instance() -> None:
    built: list[object] = []

    @SingletonDecorator
    class Slow:
        def __init__(self) -> None:
            built.append(self)
            time.sleep(0.05)

    results = _race(Slow)
    assert len(built) == 1
    assert all(r is built[0] for r in results)


def test_metaclass_nested_construction_on_one_thread(
    clean_instances: list[type],
) -> None:
    class Inner(metaclass=SingletonMetaclass):
        pass

    class Outer(metaclass=SingletonMetaclass):
        def __init__(self) -> None:
            self.inner = Inner()

    clean_instances.extend([Inner, Outer])
    outer = Outer()
    assert outer.inner is Inner()
    assert Outer() is outer


def test_decorator_nested_construction_on_one_thread() -> None:
    @SingletonDecorator
    class Inner:
        pass

    @SingletonDecorator
    class Outer:
        def __init__(self) -> None:
            self.inner = Inner()

    outer = Outer()
    assert outer.inner is Inner()
    assert Outer() is outer


def test_metaclass_different_classes_do_not_block(clean_instances: list[type]) -> None:
    """A slow constructor of one class doesn't hold up another class."""
    started = threading.Event()
    release = threading.Event()

    class Blocking(metaclass=SingletonMetaclass):
        def __init__(self) -> None:
            started.set()
            release.wait(timeout=_JOIN_S)

    class Quick(metaclass=SingletonMetaclass):
        pass

    clean_instances.extend([Blocking, Quick])
    t = threading.Thread(target=Blocking, daemon=True)
    t.start()
    try:
        assert started.wait(timeout=_JOIN_S)
        got: list[object] = []
        q = threading.Thread(target=lambda: got.append(Quick()), daemon=True)
        q.start()
        q.join(timeout=1.0)
        assert not q.is_alive(), "Quick() waited on Blocking's constructor"
        assert got and got[0] is Quick()
    finally:
        release.set()
        t.join(timeout=_JOIN_S)
    assert not t.is_alive()


def test_metaclass_pop_rebuilds(clean_instances: list[type]) -> None:
    """Tests pop _instances to get a fresh object; that still works."""

    class Fresh(metaclass=SingletonMetaclass):
        pass

    clean_instances.append(Fresh)
    first = Fresh()
    SingletonMetaclass._instances.pop(Fresh)
    second = Fresh()
    assert second is not first
    assert Fresh() is second
