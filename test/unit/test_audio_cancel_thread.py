# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Stop and Interrupt end a sound even while miniaudio's audio thread is
inside the sample generator (06 S49, S50), and the device is closed off the
audio thread (upstream 911444dd). No real audio device: miniaudio's device
and decoder are stand-ins, the audio thread is a feeder thread."""

from __future__ import annotations

import array
import threading
from collections.abc import Generator
from types import SimpleNamespace

import pytest

from gremlin import audio_player


class _Device:
    """Stands in for miniaudio.PlaybackDevice: start() feeds the generator
    from its own thread, like miniaudio's audio callback."""

    made: list[_Device] = []

    def __init__(self, **_kwargs: object) -> None:
        self.feeder: threading.Thread | None = None
        self.errors: list[BaseException] = []
        self.closed_on: list[threading.Thread] = []
        self.finished = threading.Event()
        _Device.made.append(self)

    def start(self, generator: Generator) -> None:
        def feed() -> None:
            try:
                while True:
                    generator.send(16)
            except StopIteration:
                pass
            except BaseException as exc:  # noqa: BLE001
                self.errors.append(exc)
            finally:
                self.finished.set()

        self.feeder = threading.Thread(target=feed, daemon=True)
        self.feeder.start()

    def close(self) -> None:
        self.closed_on.append(threading.current_thread())


@pytest.fixture
def stand_ins(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A sound whose stream blocks inside send() until the test lets it go."""
    inside = threading.Event()
    release = threading.Event()
    stop_blocking = threading.Event()

    def stream(*_args: object, **_kwargs: object) -> Generator:
        def gen() -> Generator:
            yield b""
            while True:
                if not stop_blocking.is_set():
                    inside.set()
                    release.wait(2.0)
                    stop_blocking.set()
                yield b"\0\0" * 16

        g = gen()
        next(g)
        return g

    decoded = SimpleNamespace(
        samples=array.array("h", [0] * 64),
        nchannels=1,
        sample_width=2,
        sample_rate=44100,
        sample_format=None,
    )
    _Device.made = []
    monkeypatch.setattr(audio_player.miniaudio, "decode_file", lambda _f: decoded)
    monkeypatch.setattr(audio_player.miniaudio, "stream_raw_pcm_memory", stream)
    monkeypatch.setattr(audio_player.miniaudio, "PlaybackDevice", _Device)
    yield SimpleNamespace(inside=inside, release=release)
    release.set()


def test_cancel_while_the_audio_thread_is_inside_the_generator_stops_it(
    stand_ins: SimpleNamespace,
) -> None:
    sample = audio_player.AudioSample("beep.wav", 80)
    sample.play()
    device = _Device.made[0]
    assert stand_ins.inside.wait(2.0)  # the audio thread is inside send()

    sample.cancel()  # Stop's thread: must not touch the running generator
    stand_ins.release.set()

    assert device.finished.wait(0.5), "the sound played on after cancel()"
    assert device.errors == []


def test_a_sound_that_ends_is_closed_off_the_audio_thread(
    stand_ins: SimpleNamespace,
) -> None:
    sample = audio_player.AudioSample("beep.wav", 80)
    sample.play()
    device = _Device.made[0]
    assert stand_ins.inside.wait(2.0)
    sample.cancel()
    stand_ins.release.set()
    assert device.finished.wait(0.5)

    assert sample.close_if_done()  # the playback thread closes it
    assert sample.done
    assert device.closed_on == [threading.current_thread()]
    assert device.feeder not in device.closed_on
    sample.close_if_done()
    assert len(device.closed_on) == 1  # closed once
