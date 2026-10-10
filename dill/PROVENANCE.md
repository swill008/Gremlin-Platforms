# dill.dll: where it comes from

`dill/dill.dll` is upstream Joystick Gremlin's **dill2.dll** ("DILL v2.0"), renamed
(decision D-02-DILL2, spec 02 S139, user 2026-10-10, Route A).

| | |
|---|---|
| Upstream | https://github.com/WhiteMagic/JoystickGremlin, tag `Release_16` (commit `b99be37e7b0b973a38815a748daacc348d29660f`), file `dill/dill2.dll`, added in commit `a4bf778b0d` ("Dill2 and legacy swap support") |
| Size | 353,792 bytes |
| SHA-256 | `afa5373d3c57fa722ee60fc94faa9b3cff9404f60f3d5c09968f3577b6664948` |
| Built (PE time) | 2026-09-26 14:41 UTC |
| Reports itself as | "Initializing DILL v2.0" in `dill_debug.log` |
| Source | Not published (the public WhiteMagic/dill source ends at v1.5, master `eb66aea`) |
| Licence | dill: BSD-2-Clause (`licenses/dill.txt`); links spdlog (MIT, `licenses/spdlog.txt`) and fmt (MIT, `licenses/fmt.txt`) |
| Replaces | DILL v1.3 (SHA-256 `48b27c97f178a9917f10b8af5bca97ac6629f4b08523160af9d61c592e584ba9`), still in git history |

`test/unit/test_dill_provenance.py` checks that the shipped file has the SHA-256 above.
Evidence for the switch: the feasibility study (https://claude.ai/artifact/47FMc9945SC1sMYKwJn3h5).
