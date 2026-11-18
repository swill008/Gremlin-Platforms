# Rust "middle path" study (2026-11-18, read-only)

User: "do a study to see what it would take for this option" (keep the Python program, move only hot
paths into Rust modules via PyO3/maturin). Four read-only agents (RS-INPUT, RS-OUTPUT, RS-BUILD,
RS-EVIDENCE), ~05:00-05:03; nothing changed, built or run. Rust effort figures are rough guesses
(timings.md has no Rust rows).

## Verdict
The evidence does not show a per-event Python cost worth Rust. From the user's own trace logs,
WIRING-to-OUTPUT per event: median 0 ms, p95/p99 1 ms (the log's resolution), max 93 ms (2,874 + 21,269
pairs). Every "Not responding" dump (37) is either the Qt main thread waiting on Windows (display
switching, 28 of them in the Screen Saver Mode sessions; same in any Qt program, SSM-MAIN-THREAD-PAUSE)
or a blocking Windows/driver call made on the main thread (vJoy init, TTS engine, power queries, the
helper pipe). Rust fixes none of those.

The real weakness: the input -> wiring -> output path runs on the Qt main thread
(gremlin/modules/runtime.py:102, gremlin/event_handler.py:864), so bindings, macros and timers freeze
whenever the main thread stalls. Moving that path to its own thread is a design change that can be done
in Python first; Rust only matters if, after that, measurements show the GIL adds noticeable delay.

## Candidates if Rust is still wanted (ranked)
| # | Piece | Verdict | Boundary | Rough effort |
|---|---|---|---|---|
| 1 | Screen Saver Mode raw-input listener (screen_saver_mode.py ~1195-1217, note_input) - every mouse move (up to 1000/s) runs Python | Port with redesign; self-contained, best first module | Rust keeps last-input time and counters; Python polls; rare events queued | ~1 week |
| 2 | SendInput + the 100 Hz mouse-motion loop (sendinput.py 203-353, 420-492) | Port with redesign; Python sleep jitter affects smoothness | set_velocity/clear/reset/press/release from Python per event; tick stays in Rust; OWN_KEY_MARK 0x47524D4C kept; run_scope keeps Stop | 3-5 days + tests |
| 3 | Joystick event pump (dill callback -> calibration -> cache -> batch) | Port with redesign; dill.dll itself stays (spec 02 S139-S141 pin it) | Rust takes the DLL callback without the GIL, Python pump thread builds Events and emits Qt signals | 1-2 weeks |
| 4 | Keyboard hook (windows_event_hook.py 153-253) | Low priority | Rust hook + queue to Python | ~1 week |
Stays in Python: vJoy/ViGEm writes (one driver call each; firewall, keep-alive and trace hang off them),
run_scope, macros, Tempo/Double Tap/Smart Toggle/pulses (Qt timers running Python actions), the
relative-axis loop (calls the vJoy firewall every step), EventHandler, the claim gate, threads/clock.

## Build and tooling (RS-BUILD)
- A new `native/` crate with its own pyproject (maturin, module `gremlin_native._core`), added to the
  root as a Poetry path dependency (develop = true) so `poetry sync` builds it in CI and the release.
- CI: windows-latest already has Rust and MSVC; pin the toolchain, add Swatinem/rust-cache, `cargo test`,
  `clippy -D warnings`, `fmt --check`, a check that the .pyd ships. Installer unchanged.
- PyInstaller: `hidden_imports` entry; VC runtime already shipped via vc_redist.
- Guards: `test_spec_line.py` _PROGRAM and `test_program_map_covers_files.py` units must learn `native/`
  (changes decision S156 - needs the user); `test/changed_tests.py` needs a `.rs` rule.
- Licences for Rust crates into licenses/ (S153).
- The user's PC needs Visual Studio Build Tools (C++) and rustup (the user installs).
- Rough effort before any Rust module: 2-4 hours.

## Risks
Tests pin Python internals (vjoy 247 files, macro 67, run_scope 41, sendinput 14; hooks, _window_proc,
note_input...); Rust threads can't see gremlin.clock's fake time (tests need a manual-step hook); Rust
threads sit outside gremlin.threads (need bounded stop); layer rule must hold (Rust only inside the
input/output module); a third language for the map, glossary and change control; an unsigned native .pyd
may raise antivirus false positives slightly (unverified).

## Measurements missing before deciding
1. Driver-callback -> vJoy-write latency at sub-millisecond resolution (perf_counter_ns probe).
2. CPU/GIL share at high input rates (4 sticks at 1 kHz; py-spy needs the user's OK).
3. Binding delay while the UI is busy (profile load, Device Library open).
4. The same after moving the input path off the Qt thread (Python only), before any Rust.

## Staged plan (if pursued)
| Stage | What | Rough effort |
|---|---|---|
| 0 | Probes 1-3 above (read-only logging, no behaviour change) | no timing data; ~1 batch |
| 1 | Move input -> wiring -> output off the Qt main thread, in Python (spec change: threads) | no timing data; several batches |
| 2 | Re-measure; stop here if latency is fine | 1 batch |
| 3 | Rust plumbing (native/, CI, guards; user approves S156 change) | 2-4 h |
| 4 | First module: SSM raw-input listener, or SendInput + mouse loop | 3-7 days each |
| 5 | Event pump only if stage 2 shows the GIL matters | 1-2 weeks |

Not verified: crate versions beyond search results (pyo3 0.29.x, maturin 1.14.0, vigem-client 0.1.4),
dill.dll threading/report rate, Poetry + maturin path dependency under package-mode = false, real build
times, cargo test with extension-module on pyo3 0.29.
