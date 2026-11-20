# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Read-only report on input delay from trace.log (+ trace.log.1) and system.log.

    python tools/latency_report.py [trace.log] [--system system.log]
    python tools/latency_report.py --compare before.log after.log
    python tools/latency_report.py trace.log --legacy

Per session (a Tracing on, or the clock going back): one table per hop from
the TIMING summary lines (median / p95 / p99 weighted by the events in each
interval, max = largest), the TIMING stall list, and the watchdog stalls
("Not responding" / "Responding again") from system.log and from trace.log
EVENT lines, marking which of them overlap. --legacy pairs RAW -> WIRING and
WIRING -> OUTPUT lines of the same control (ms resolution) for logs made
before Timing existed. Stdlib only; never writes anything.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

_TRACE = re.compile(
    r"^(\d\d):(\d\d):(\d\d)\.(\d{3})\s+(.*?)\s{2,}"
    r"(RAW|WIRING|OUTPUT|EVENT|TIMING)\s+(.*)$"
)
_SUMMARY = re.compile(
    r"^(\d{4}-\d\d-\d\d) (\d+) s: ([\d,]+) events \((\d+) devices?\)(.*)$"
)
_HOP = re.compile(
    r"^(.+?) median ([\d,.]+) ms p95 ([\d,.]+) p99 ([\d,.]+) max ([\d,.]+)$"
)
_STALL = re.compile(
    r"queue wait ([\d,.]+) ms \(events held: ([\d,]+); first held at "
    r"(\d\d):(\d\d):(\d\d)\.(\d{3})(?:; waited for [^)]*)?\)"
)
_SYS = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+\w+\s+(.*)$")
_NOT_RESP = re.compile(r"Not responding for (\d+) s")
_RESP_AGAIN = re.compile(r"Responding again after (\d+) s")
HOPS = ("driver to emit", "queue wait", "gate to wiring", "actions", "end to end")
_DAY = 86400.0


def _num(text: str) -> float:
    return float(text.replace(",", ""))


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolated percentile (p in 0..100); 0.0 for no values."""
    if not values:
        return 0.0
    v = sorted(values)
    k = (len(v) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


@dataclass
class Rec:
    t: float  # seconds since midnight
    control: str
    point: str
    text: str


@dataclass
class Watch:
    start: dt.datetime
    length: float | None  # seconds, None = never recovered
    source: str


@dataclass
class Session:
    recs: list[Rec] = field(default_factory=list)
    date: dt.date | None = None
    # hop -> list of (events in interval, median, p95, p99, max)
    hops: dict[str, list[tuple[int, float, float, float, float]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    intervals: int = 0
    events: int = 0
    stalls: list[tuple[dt.datetime | None, str, float, int]] = field(
        default_factory=list
    )  # (start, clock text, ms, held)
    watch: list[Watch] = field(default_factory=list)

    @property
    def first(self) -> str:
        return _clock(self.recs[0].t) if self.recs else "-"

    @property
    def last(self) -> str:
        return _clock(self.recs[-1].t) if self.recs else "-"


def _clock(t: float) -> str:
    t = t % _DAY
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{t % 60:06.3f}"


def parse_trace(lines: list[str]) -> list[Session]:
    """Split trace lines into sessions and pull out summaries, stalls, EVENTs."""
    sessions: list[Session] = []
    cur: Session | None = None
    prev = 0.0
    offset = 0.0  # days rolled over inside the session, in seconds
    for raw in lines:
        m = _TRACE.match(raw.rstrip("\r\n"))
        if not m:
            continue
        h, mi, s, ms = (int(m.group(i)) for i in range(1, 5))
        t = h * 3600 + mi * 60 + s + ms / 1000.0
        rec = Rec(t, m.group(5).strip(), m.group(6), m.group(7).strip())
        new = cur is None
        if cur is not None:
            back = prev - (t + offset)
            if back > 12 * 3600:
                offset += _DAY
            elif back > 1.0:
                new = True
        if rec.point == "EVENT" and rec.text.startswith("Tracing on"):
            new = True
        if new:
            cur = Session()
            sessions.append(cur)
            offset = 0.0
        assert cur is not None
        prev = t + offset
        cur.recs.append(rec)
        if rec.point == "TIMING":
            _take_timing(cur, rec)
    for ses in sessions:
        _fix_dates(ses)
    return sessions


def _take_timing(ses: Session, rec: Rec) -> None:
    m = _SUMMARY.match(rec.text)
    if m:
        if ses.date is None:
            ses.date = dt.date.fromisoformat(m.group(1))
        n = int(m.group(3).replace(",", ""))
        ses.intervals += 1
        ses.events += n
        for part in m.group(5).split(" · "):
            hm = _HOP.match(part.strip())
            if hm:
                ses.hops[hm.group(1)].append(
                    (
                        n,
                        _num(hm.group(2)),
                        _num(hm.group(3)),
                        _num(hm.group(4)),
                        _num(hm.group(5)),
                    )
                )
        return
    sm = _STALL.search(rec.text)
    if sm:
        first = int(sm.group(3)) * 3600 + int(sm.group(4)) * 60 + int(sm.group(5))
        first += int(sm.group(6)) / 1000.0
        ses.stalls.append(
            (None, _clock(first), _num(sm.group(1)), int(sm.group(2).replace(",", "")))
        )


def _at(date: dt.date, clock: str) -> dt.datetime:
    h, m, rest = clock.split(":")
    return dt.datetime.combine(date, dt.time()) + dt.timedelta(
        hours=int(h), minutes=int(m), seconds=float(rest)
    )


def _fix_dates(ses: Session) -> None:
    """Dates the stalls and the trace's watchdog EVENT lines (midnight aware)."""
    if ses.date is None:
        return
    day0 = ses.date
    first_t = ses.recs[0].t if ses.recs else 0.0
    # a stall "first held" earlier on the clock than the session start is after midnight
    fixed = []
    for _, clock, ms, held in ses.stalls:
        at = _at(day0, clock)
        if _clock_secs(clock) < first_t - 12 * 3600:
            at += dt.timedelta(days=1)
        fixed.append((at, clock, ms, held))
    ses.stalls = fixed
    last_t = None
    day = day0
    for r in ses.recs:
        if last_t is not None and last_t - r.t > 12 * 3600:
            day += dt.timedelta(days=1)
        last_t = r.t
        if r.point == "EVENT":
            at = _at(day, _clock(r.t))
            _watch_line(ses.watch, at, r.text, "trace")


def _clock_secs(clock: str) -> float:
    h, m, s = clock.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _watch_line(out: list[Watch], at: dt.datetime, text: str, source: str) -> None:
    n = _NOT_RESP.search(text)
    if n:
        out.append(Watch(at - dt.timedelta(seconds=int(n.group(1))), None, source))
        return
    r = _RESP_AGAIN.search(text)
    if r and out and out[-1].length is None and out[-1].source == source:
        out[-1].length = float(r.group(1))


def parse_system(lines: list[str]) -> list[Watch]:
    out: list[Watch] = []
    for raw in lines:
        m = _SYS.match(raw.rstrip("\r\n"))
        if m:
            at = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            _watch_line(out, at, m.group(2), "system")
    return out


def _overlap(
    a0: dt.datetime, a1: dt.datetime, b0: dt.datetime, b1: dt.datetime
) -> bool:
    return a0 <= b1 and b0 <= a1


def _watch_in(ses: Session, all_watch: list[Watch]) -> list[Watch]:
    """Watchdog stalls inside the session's time window, trace and system merged."""
    if ses.date is None or not ses.recs:
        return list(ses.watch)
    t0 = _at(ses.date, ses.first)
    span = ses.recs[-1].t - ses.recs[0].t
    if span < 0:
        span += _DAY
    t1 = t0 + dt.timedelta(seconds=span + 1)
    found = [
        w
        for w in all_watch
        if _overlap(w.start, w.start + dt.timedelta(seconds=w.length or 0), t0, t1)
    ]
    for w in ses.watch:  # trace EVENT lines not already seen in system.log
        if not any(abs((w.start - o.start).total_seconds()) <= 2 for o in found):
            found.append(w)
    return sorted(found, key=lambda w: w.start)


def aggregate(
    ses_list: list[Session],
) -> dict[str, tuple[int, float, float, float, float]]:
    """hop -> (events, median, p95, p99, max): weighted by interval events."""
    out = {}
    for hop in HOPS:
        rows = [r for s in ses_list for r in s.hops.get(hop, [])]
        if not rows:
            continue
        w = sum(r[0] for r in rows) or 1
        out[hop] = (
            sum(r[0] for r in rows),
            *(sum(r[0] * r[i] for r in rows) / w for i in (1, 2, 3)),
            max(r[4] for r in rows),
        )
    return out


def _fmt(v: float) -> str:
    return f"{v:.2f}" if v < 10 else f"{v:.1f}" if v < 100 else f"{v:,.0f}"


def _table(rows: dict[str, tuple[int, float, float, float, float]]) -> list[str]:
    out = [
        f"  {'hop':<16}{'events':>10}{'median':>9}{'p95':>9}{'p99':>9}{'max':>9}  (ms)"
    ]
    for hop, (n, a, b, c, d) in rows.items():
        out.append(
            f"  {hop:<16}{n:>10,}{_fmt(a):>9}{_fmt(b):>9}{_fmt(c):>9}{_fmt(d):>9}"
        )
    return out


def report(ses_list: list[Session], watch: list[Watch]) -> str:
    out: list[str] = []
    for i, ses in enumerate(ses_list, 1):
        if not ses.hops and not ses.stalls and not ses.watch:
            continue
        date = ses.date.isoformat() if ses.date else "undated"
        out.append(
            f"Session {i}: {date} {ses.first} - {ses.last}, "
            f"{ses.intervals} summaries, {ses.events:,} events"
        )
        if ses.hops:
            out += _table(aggregate([ses]))
            out.append(
                "  (median, p95, p99: mean of the 10 s values weighted by events)"
            )
        else:
            out.append("  no TIMING summary lines")
        wd = _watch_in(ses, watch)
        out.append("  TIMING stalls (queue wait over 50 ms):")
        if not ses.stalls:
            out.append("    none")
        for at, clock, ms, held in ses.stalls:
            hit = ""
            if at is not None:
                end = at + dt.timedelta(milliseconds=ms)
                hits = [
                    w
                    for w in wd
                    if _overlap(
                        at, end, w.start, w.start + dt.timedelta(seconds=w.length or 0)
                    )
                ]
                if hits:
                    hit = "  <- watchdog " + ", ".join(_wtext(w) for w in hits)
            out.append(f"    {clock}  {ms:,.0f} ms  held {held:,}{hit}")
        out.append("  Watchdog stalls (system.log / trace EVENT):")
        if not wd:
            out.append("    none" if ses.date else "    unknown (session has no date)")
        for w in wd:
            out.append(f"    {_wtext(w)}  [{w.source}]")
        out.append("")
    if not out:
        return "No TIMING lines found (older log? try --legacy).\n"
    return "\n".join(out)


def _wtext(w: Watch) -> str:
    length = "never recovered" if w.length is None else f"{w.length:.0f} s"
    return f"{w.start:%Y-%m-%d %H:%M:%S} for {length}"


def compare(before: list[Session], after: list[Session]) -> str:
    a, b = aggregate(before), aggregate(after)
    out = [f"{'hop':<16}{'':<8}{'before':>10}{'after':>10}{'change':>10}  (ms)"]
    for hop in HOPS:
        if hop not in a and hop not in b:
            continue
        for k, name in ((1, "median"), (2, "p95"), (3, "p99"), (4, "max")):
            x = a[hop][k] if hop in a else None
            y = b[hop][k] if hop in b else None
            ch = "" if x is None or y is None else f"{y - x:+.2f}"
            xs = "-" if x is None else _fmt(x)
            ys = "-" if y is None else _fmt(y)
            out.append(f"{hop if k == 1 else '':<16}{name:<8}{xs:>10}{ys:>10}{ch:>10}")
    sa = sum(len(s.stalls) for s in before)
    sb = sum(len(s.stalls) for s in after)
    out.append(f"TIMING stalls: before {sa}, after {sb}")
    return "\n".join(out) + "\n"


def legacy(lines: list[str]) -> str:
    """Pair RAW -> WIRING and WIRING -> OUTPUT of one control (ms resolution)."""
    pend_raw: dict[str, float] = {}
    pend_wir: dict[str, float] = {}
    deltas: dict[tuple[str, str], list[float]] = defaultdict(list)
    for raw in lines:
        m = _TRACE.match(raw.rstrip("\r\n"))
        if not m:
            continue
        t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        t += int(m.group(4)) / 1000.0
        ctl, point = m.group(5).strip(), m.group(6)
        kind = next((k for k in ("Axis", "Button", "Hat") if k in ctl), "Other")
        if point == "RAW":
            pend_raw[ctl] = t
        elif point == "WIRING":
            r = pend_raw.pop(ctl, None)
            if r is not None and 0 <= t - r <= 1.0:
                deltas[("RAW to WIRING", kind)].append((t - r) * 1000)
            pend_wir[ctl] = t
        elif point == "OUTPUT":
            w = pend_wir.pop(ctl, None)
            if w is not None and 0 <= t - w <= 1.0:
                deltas[("WIRING to OUTPUT", kind)].append((t - w) * 1000)
    out = [
        f"{'pair':<18}{'kind':<8}{'pairs':>8}{'median':>8}{'p95':>8}"
        f"{'p99':>8}{'max':>8}  (ms)"
    ]
    if not deltas:
        return "No RAW / WIRING / OUTPUT pairs found.\n"
    for (pair, kind), v in sorted(deltas.items()):
        out.append(
            f"{pair:<18}{kind:<8}{len(v):>8,}{_fmt(percentile(v, 50)):>8}"
            f"{_fmt(percentile(v, 95)):>8}{_fmt(percentile(v, 99)):>8}{_fmt(max(v)):>8}"
        )
    out.append(
        "(only pairs under 1 s apart; axis RAW lines are rate-limited, "
        "so axis pairs are rough)"
    )
    return "\n".join(out) + "\n"


def _read(path: Path) -> list[str]:
    """The file's lines, with its rotated .1 sibling first when there is one."""
    lines: list[str] = []
    older = path.with_name(path.name + ".1")
    for p in (older, path):
        if p.is_file():
            lines += p.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines


def _system_for(trace: Path, given: str | None) -> list[Watch]:
    path = Path(given) if given else trace.with_name("system.log")
    return parse_system(_read(path)) if path.name.startswith("system") else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "trace", nargs="?", help="trace.log (default: the Gremlin Platforms folder)"
    )
    ap.add_argument("--system", help="system.log (default: next to trace.log)")
    ap.add_argument(
        "--legacy", action="store_true", help="pair RAW/WIRING/OUTPUT lines"
    )
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    args = ap.parse_args(argv)
    if args.compare:
        b, a = (Path(p) for p in args.compare)
        sys.stdout.write(compare(parse_trace(_read(b)), parse_trace(_read(a))))
        return 0
    path = (
        Path(args.trace)
        if args.trace
        else (Path.home() / "Gremlin Platforms" / "logs" / "trace.log")
    )
    if not path.is_file():
        sys.stderr.write(f"not found: {path}\n")
        return 2
    lines = _read(path)
    if args.legacy:
        sys.stdout.write(legacy(lines))
    else:
        sys.stdout.write(report(parse_trace(lines), _system_for(path, args.system)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
