# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Log When Not Responding: where the program is stuck when it freezes.

A timer on the main loop ticks every BEAT_MS. A watchdog thread checks it
once a second: when it hasn't ticked for THRESHOLD_S, it writes "Not
responding" and the stack of every thread to system.log, once per freeze,
and "Responding again" when the ticks come back. The option is off by
default and takes effect at once.

While the input thread runs, the same thread also reads its heartbeat
(input_thread.silent_for): past the same limit it writes "Input thread not
responding" with the stacks and recent events, and "Input thread responding
again", once per stall.

It can only write while the stuck main thread lets other threads run: a
call that holds Python's lock (GIL) while it waits is logged once it
returns.
"""

from __future__ import annotations

import ctypes
import faulthandler
import logging
import os
import sys
import tempfile
import threading

from PySide6 import QtCore

from gremlin import clock, input_thread, threads

OPTION = ("global", "general", "log-when-not-responding")
THRESHOLD_S = 5.0
BEAT_MS = 250

_log = logging.getLogger("system")


def thread_stacks() -> str:
    """Every thread's stack, with the thread names."""
    names = ", ".join(
        f"{t.name} = 0x{t.ident:08x}" for t in threading.enumerate() if t.ident
    )
    with tempfile.TemporaryFile("w+", encoding="utf-8") as out:
        faulthandler.dump_traceback(file=out, all_threads=True)
        out.seek(0)
        return f"Threads: {names}\n{out.read()}"


# Wait Chain Traversal (advapi32): what Windows says a thread is waiting on.
WCT_MAX_NODE_COUNT = 16
WCTP_GETINFO_ALL_FLAGS = 0xF
_OBJECT_TYPES = (
    "CriticalSection", "SendMessage", "Mutex", "Alpc", "Com", "ThreadWait",
    "ProcessWait", "Thread", "ComActivation", "Unknown", "SocketIo", "SmbIo",
)
_OBJECT_STATUSES = (
    "NoAccess", "Running", "Blocked", "PidOnly", "PidOnlyRpcss", "Owned",
    "NotOwned", "Abandoned", "Unknown", "Error",
)

_main_thread_id: int | None = None


class _LockObject(ctypes.Structure):
    _fields_ = [
        ("ObjectName", ctypes.c_wchar * 128),
        ("Timeout", ctypes.c_longlong),
        ("Alertable", ctypes.c_int),
    ]


class _ThreadObject(ctypes.Structure):
    _fields_ = [
        ("ProcessId", ctypes.c_uint32),
        ("ThreadId", ctypes.c_uint32),
        ("WaitTime", ctypes.c_uint32),
        ("ContextSwitches", ctypes.c_uint32),
    ]


class _NodeUnion(ctypes.Union):
    _fields_ = [("LockObject", _LockObject), ("ThreadObject", _ThreadObject)]


class WaitChainNodeInfo(ctypes.Structure):
    """WAITCHAIN_NODE_INFO."""

    _fields_ = [
        ("ObjectType", ctypes.c_uint32),
        ("ObjectStatus", ctypes.c_uint32),
        ("u", _NodeUnion),
    ]


def _enum_name(names: tuple[str, ...], value: int) -> str:
    return names[value - 1] if 1 <= value <= len(names) else f"#{value}"


def format_wait_chain(
    nodes: list[WaitChainNodeInfo],
    is_cycle: bool,
    thread_names: dict[int, str] | None = None,
) -> str:
    """The "Main thread wait chain (Windows):" block, one line per node."""
    names = thread_names or {}
    lines = ["Main thread wait chain (Windows):"]
    for n in nodes:
        kind = _enum_name(_OBJECT_TYPES, n.ObjectType)
        status = _enum_name(_OBJECT_STATUSES, n.ObjectStatus)
        text = f"  {kind}, {status}"
        if kind == "Thread":
            pid, tid = n.u.ThreadObject.ProcessId, n.u.ThreadObject.ThreadId
            if pid == os.getpid():
                name = names.get(tid)
                text += f", this process, thread {tid}" + (f" ({name})" if name else "")
            else:
                text += f", process {pid}, thread {tid}"
        else:
            obj = n.u.LockObject.ObjectName
            if obj:
                text += f", {obj}"
        lines.append(text)
    if is_cycle:
        lines.append("  deadlock cycle")
    return "\n".join(lines)


def _query_wait_chain(thread_id: int) -> tuple[list[WaitChainNodeInfo], bool]:
    """Asks Windows for the wait chain of a thread (raises on failure)."""
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.OpenThreadWaitChainSession.restype = wintypes.HANDLE
    advapi.OpenThreadWaitChainSession.argtypes = [wintypes.DWORD, ctypes.c_void_p]
    advapi.GetThreadWaitChain.restype = wintypes.BOOL
    advapi.GetThreadWaitChain.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
        ctypes.POINTER(wintypes.BOOL),
    ]
    advapi.CloseThreadWaitChainSession.argtypes = [wintypes.HANDLE]
    session = advapi.OpenThreadWaitChainSession(0, None)
    if not session:
        raise OSError(f"OpenThreadWaitChainSession failed ({ctypes.get_last_error()})")
    try:
        nodes = (WaitChainNodeInfo * WCT_MAX_NODE_COUNT)()
        count = wintypes.DWORD(WCT_MAX_NODE_COUNT)
        cycle = wintypes.BOOL(0)
        ok = advapi.GetThreadWaitChain(
            session, None, WCTP_GETINFO_ALL_FLAGS, thread_id,
            ctypes.byref(count), nodes, ctypes.byref(cycle),
        )
        if not ok:
            raise OSError(f"GetThreadWaitChain failed ({ctypes.get_last_error()})")
        return list(nodes[: min(count.value, WCT_MAX_NODE_COUNT)]), bool(cycle.value)
    finally:
        advapi.CloseThreadWaitChainSession(session)


def wait_chain_block() -> str:
    """What Windows reports the main thread is waiting on, as plain text.
    Windows only (empty elsewhere); never raises. Runs on the watchdog thread."""
    if sys.platform != "win32":
        return ""
    try:
        tid = _main_thread_id or threading.main_thread().native_id
        if not tid:
            raise RuntimeError("main thread id unknown")
        nodes, cycle = _query_wait_chain(tid)
        names = {t.native_id: t.name for t in threading.enumerate() if t.native_id}
        return format_wait_chain(nodes, cycle, names)
    except Exception as e:
        return f"Main thread wait chain: not available ({e})"


# Native stack (Windows x64): the thread is suspended only to copy its
# registers and stack; walking and naming happen after it is resumed, on a
# copy, so nothing that may take a lock runs while it is stopped.
NATIVE_FRAMES = 48
NATIVE_SAMPLE_GAP_S = 0.3
_STACK_COPY_MAX = 512 * 1024
_CONTEXT_SIZE = 0x4D0
_CONTEXT_FULL = 0x10000B
_OFF_FLAGS, _OFF_RSP, _OFF_RBP, _OFF_RIP = 0x30, 0x98, 0xA0, 0xF8
# THREAD_SUSPEND_RESUME, THREAD_GET_CONTEXT, THREAD_QUERY_INFORMATION
_THREAD_ACCESS = 0x0002 | 0x0008 | 0x0040


def _native_supported() -> bool:
    import platform

    return (
        sys.platform == "win32"
        and ctypes.sizeof(ctypes.c_void_p) == 8
        and platform.machine().upper() in ("AMD64", "X86_64")
    )


class _Address64(ctypes.Structure):
    _fields_ = [
        ("Offset", ctypes.c_uint64),
        ("Segment", ctypes.c_uint16),
        ("Mode", ctypes.c_int),
    ]


class _StackFrame64(ctypes.Structure):
    _fields_ = [
        ("AddrPC", _Address64),
        ("AddrReturn", _Address64),
        ("AddrFrame", _Address64),
        ("AddrStack", _Address64),
        ("AddrBStore", _Address64),
        ("FuncTableEntry", ctypes.c_void_p),
        ("Params", ctypes.c_uint64 * 4),
        ("Far", ctypes.c_int),
        ("Virtual", ctypes.c_int),
        ("Reserved", ctypes.c_uint64 * 3),
        ("KdHelp", ctypes.c_uint64 * 32),
    ]


class _Native:
    """The Windows functions used, loaded once."""

    def __init__(self) -> None:
        from ctypes import wintypes

        vp, u64, dw = ctypes.c_void_p, ctypes.c_uint64, wintypes.DWORD
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Called while the thread is suspended: PyDLL keeps the GIL held, so
        # the suspended thread can't be holding it when we need it back.
        held = ctypes.PyDLL("kernel32")
        ntdll = ctypes.WinDLL("ntdll")
        self.suspend, self.resume = held.SuspendThread, held.ResumeThread
        for f in (self.suspend, self.resume):
            f.restype, f.argtypes = dw, [vp]
        self.get_context = held.GetThreadContext
        self.get_context.restype, self.get_context.argtypes = wintypes.BOOL, [vp, vp]
        self.move = held.RtlMoveMemory
        self.move.restype, self.move.argtypes = None, [vp, vp, ctypes.c_size_t]
        self.open_thread = k32.OpenThread
        self.open_thread.restype, self.open_thread.argtypes = (
            vp,
            [dw, wintypes.BOOL, dw],
        )
        self.close = k32.CloseHandle
        self.close.argtypes = [vp]
        self.process = k32.GetCurrentProcess
        self.process.restype = vp
        self.read = k32.ReadProcessMemory
        self.read.restype = wintypes.BOOL
        self.read.argtypes = [
            vp,
            u64,
            vp,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self.module_from = k32.GetModuleHandleExW
        self.module_from.restype = wintypes.BOOL
        self.module_from.argtypes = [dw, vp, ctypes.POINTER(vp)]
        self.module_name = k32.GetModuleFileNameW
        self.module_name.restype, self.module_name.argtypes = (
            dw,
            [vp, wintypes.LPWSTR, dw],
        )
        self.query_thread = ntdll.NtQueryInformationThread
        self.query_thread.restype = ctypes.c_long
        self.query_thread.argtypes = [vp, ctypes.c_int, vp, ctypes.c_ulong, vp]
        self.lookup = ntdll.RtlLookupFunctionEntry
        self.lookup.restype, self.lookup.argtypes = vp, [u64, ctypes.POINTER(u64), vp]
        dbghelp = ctypes.WinDLL("dbghelp")
        self.read_cb = ctypes.WINFUNCTYPE(
            wintypes.BOOL, vp, u64, vp, dw, ctypes.POINTER(dw)
        )
        self.table_cb = ctypes.WINFUNCTYPE(vp, vp, u64)
        self.base_cb = ctypes.WINFUNCTYPE(u64, vp, u64)
        self.walk = dbghelp.StackWalk64
        self.walk.restype = wintypes.BOOL
        self.walk.argtypes = [
            dw,
            vp,
            vp,
            ctypes.POINTER(_StackFrame64),
            vp,
            self.read_cb,
            self.table_cb,
            self.base_cb,
            vp,
        ]
        self.walk_lock = threading.Lock()  # dbghelp is single-threaded


_native: _Native | None = None
_exports: dict[int, tuple[str, list[int], list[str]]] = {}


def _api() -> _Native:
    global _native
    if _native is None:
        _native = _Native()
    return _native


def _module_of(address: int) -> int:
    api = _api()
    handle = ctypes.c_void_p()
    # FROM_ADDRESS | UNCHANGED_REFCOUNT
    if not api.module_from(0x4 | 0x2, ctypes.c_void_p(address), ctypes.byref(handle)):
        return 0
    return handle.value or 0


def _module_exports(base: int) -> tuple[str, list[int], list[str]]:
    """(file name, sorted export addresses, their names), parsed once per module
    from its export table in memory."""
    cached = _exports.get(base)
    if cached is not None:
        return cached
    api = _api()
    buf = ctypes.create_unicode_buffer(520)
    n = api.module_name(ctypes.c_void_p(base), buf, 520)
    name = os.path.basename(buf.value[:n]) if n else f"0x{base:x}"
    addrs: list[int] = []
    names: list[str] = []
    try:
        u16 = lambda off: ctypes.c_uint16.from_address(base + off).value  # noqa: E731
        u32 = lambda off: ctypes.c_uint32.from_address(base + off).value  # noqa: E731
        nt = u32(0x3C)
        if u16(0) == 0x5A4D and u32(nt) == 0x4550 and u16(nt + 24) == 0x20B:
            exp_rva, exp_size = u32(nt + 24 + 112), u32(nt + 24 + 116)
            if exp_rva:
                ordinal_base, n_funcs, n_names = (
                    u32(exp_rva + 16),
                    u32(exp_rva + 20),
                    u32(exp_rva + 24),
                )
                funcs, name_rvas, ords = (
                    u32(exp_rva + 28),
                    u32(exp_rva + 32),
                    u32(exp_rva + 36),
                )
                by_index = {
                    u16(ords + 2 * i): ctypes.string_at(
                        base + u32(name_rvas + 4 * i)
                    ).decode("ascii", "replace")
                    for i in range(n_names)
                }
                pairs = []
                for i in range(n_funcs):
                    rva = u32(funcs + 4 * i)
                    # forwarders point into the export table: skip them
                    if rva and not exp_rva <= rva < exp_rva + exp_size:
                        pairs.append(
                            (base + rva, by_index.get(i, f"#{ordinal_base + i}"))
                        )
                pairs.sort()
                addrs = [a for a, _ in pairs]
                names = [s for _, s in pairs]
    except Exception:
        addrs, names = [], []
    _exports[base] = (name, addrs, names)
    return _exports[base]


def name_address(address: int) -> str:
    """`module!nearest_export+0xoff` for a code address in this process."""
    import bisect

    base = _module_of(address)
    if not base:
        return f"0x{address:x}"
    name, addrs, names = _module_exports(base)
    i = bisect.bisect_right(addrs, address) - 1
    if i >= 0:
        return f"{name}!{names[i]}+0x{address - addrs[i]:x}"
    return f"{name}+0x{address - base:x}"


def _capture(tid: int) -> tuple[ctypes.Array, int, ctypes.Array, int, int]:
    """Suspends the thread, copies its registers and stack, resumes it.
    Returns (context buffer, aligned context address, stack copy, copied
    stack start, copied length)."""
    api = _api()
    if tid == threading.get_native_id():
        raise RuntimeError("can't sample the watchdog thread itself")
    handle = api.open_thread(_THREAD_ACCESS, False, tid)
    if not handle:
        raise OSError(f"OpenThread failed ({ctypes.get_last_error()})")
    try:
        # The stack's top (StackBase in the thread's TEB), read before suspending.
        info = (ctypes.c_uint64 * 6)()
        status = api.query_thread(handle, 0, info, ctypes.sizeof(info), None)
        if status != 0:
            raise OSError(
                f"NtQueryInformationThread failed (0x{status & 0xFFFFFFFF:x})"
            )
        top = ctypes.c_uint64()
        got = ctypes.c_size_t()
        if not api.read(
            api.process(), info[1] + 8, ctypes.byref(top), 8, ctypes.byref(got)
        ):
            raise OSError("stack base not readable")
        raw = (ctypes.c_ubyte * (_CONTEXT_SIZE + 16))()
        ctx = (ctypes.addressof(raw) + 15) & ~15
        ctypes.c_uint32.from_address(ctx + _OFF_FLAGS).value = _CONTEXT_FULL
        stack = (ctypes.c_ubyte * _STACK_COPY_MAX)()
        stack_at = ctypes.addressof(stack)
        rsp_at = ctx + _OFF_RSP
        top_value = top.value
        # The suspended window: only these calls, no allocation of note.
        if api.suspend(handle) == 0xFFFFFFFF:
            raise OSError(f"SuspendThread failed ({ctypes.get_last_error()})")
        try:
            ok = api.get_context(handle, ctx)
            rsp = ctypes.c_uint64.from_address(rsp_at).value
            length = top_value - rsp if ok and rsp < top_value else 0
            if length > _STACK_COPY_MAX:
                length = _STACK_COPY_MAX
            if length:
                api.move(stack_at, rsp, length)
        finally:
            api.resume(handle)
        if not ok:
            raise OSError("GetThreadContext failed")
        if not length:
            raise RuntimeError("stack pointer outside the stack")
        return raw, ctx, stack, rsp, length
    finally:
        api.close(handle)


def _walk(ctx: int, stack: ctypes.Array, start: int, length: int) -> list[int]:
    """Return addresses, walked by dbghelp over the copied stack (reads
    outside it go to ReadProcessMemory, which fails safely)."""
    api = _api()
    copy_at = ctypes.addressof(stack)
    proc = api.process()

    def read(_h: object, addr: int, buf: int, size: int, done: object) -> int:
        try:
            if start <= addr and addr + size <= start + length:
                ctypes.memmove(buf, copy_at + (addr - start), size)
                n = size
            else:
                got = ctypes.c_size_t()
                if not api.read(proc, addr, buf, size, ctypes.byref(got)):
                    return 0
                n = got.value
            if done:
                done[0] = n  # type: ignore[index]
            return 1
        except Exception:
            return 0

    def table(_h: object, addr: int) -> int:
        try:
            base = ctypes.c_uint64()
            return api.lookup(addr, ctypes.byref(base), None) or 0
        except Exception:
            return 0

    def module_base(_h: object, addr: int) -> int:
        try:
            return _module_of(addr)
        except Exception:
            return 0

    callbacks = (api.read_cb(read), api.table_cb(table), api.base_cb(module_base))
    frame = _StackFrame64()
    frame.AddrPC.Offset = ctypes.c_uint64.from_address(ctx + _OFF_RIP).value
    frame.AddrFrame.Offset = ctypes.c_uint64.from_address(ctx + _OFF_RSP).value
    frame.AddrStack.Offset = frame.AddrFrame.Offset
    frame.AddrPC.Mode = frame.AddrFrame.Mode = frame.AddrStack.Mode = 3  # flat
    pcs: list[int] = []
    with api.walk_lock:
        for _ in range(NATIVE_FRAMES):
            if not api.walk(
                0x8664, proc, None, ctypes.byref(frame), ctx, *callbacks, None
            ):
                break
            pc = frame.AddrPC.Offset
            if not pc or (pcs and pc == pcs[-1] and frame.AddrStack.Offset == 0):
                break
            pcs.append(pc)
    return pcs


def sample_native_stack(thread_id: int) -> list[str]:
    """One sample of a thread's native stack, innermost first, each frame
    named by `name_address`. Raises on failure."""
    raw, ctx, stack, start, length = _capture(thread_id)
    pcs = _walk(ctx, stack, start, length)
    del raw
    if not pcs:
        raise RuntimeError("no frames")
    return [name_address(pc) for pc in pcs]


def native_stack_block(thread_id: int | None = None, samples: int = 2) -> str:
    """The main thread's native stack, sampled `samples` times about
    NATIVE_SAMPLE_GAP_S apart (a loop changes between samples, one long call
    doesn't). Windows x64 only (empty elsewhere); never raises. Runs on the
    watchdog thread, never the thread it samples."""
    if not _native_supported():
        return ""
    try:
        tid = thread_id or _main_thread_id or threading.main_thread().native_id
        if not tid:
            raise RuntimeError("main thread id unknown")
        lines = [f"Main thread native stack (Windows, {samples} samples):"]
        errors: list[str] = []
        for i in range(samples):
            if i:
                threading.Event().wait(NATIVE_SAMPLE_GAP_S)
            lines.append(f"  Sample {i + 1}:")
            try:
                lines += [f"    {f}" for f in sample_native_stack(tid)]
            except Exception as e:
                errors.append(str(e))
                lines.append(f"    not available ({e})")
        if len(errors) == samples:
            raise RuntimeError(errors[0])
        return "\n".join(lines)
    except Exception as e:
        return f"Main thread native stack: not available ({e})"

# Thread facts (Windows): the thread's CPU time over a short window and what
# lives on it. Another thread's message queue can't be read, so the windows
# it owns and where the low-level hooks are installed stand in for it.
CPU_WINDOW_S = 0.5
_THREAD_QUERY_LIMITED_INFORMATION = 0x0800


def _thread_cpu_ms(handle: int) -> tuple[float, float]:
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ft = [wintypes.FILETIME() for _ in range(4)]
    k32.GetThreadTimes.argtypes = [wintypes.HANDLE] + [ctypes.c_void_p] * 4
    if not k32.GetThreadTimes(handle, *[ctypes.byref(f) for f in ft]):
        raise OSError(f"GetThreadTimes failed ({ctypes.get_last_error()})")

    def ms(f: wintypes.FILETIME) -> float:
        return ((f.dwHighDateTime << 32) | f.dwLowDateTime) / 10000.0

    return ms(ft[2]), ms(ft[3])


def cpu_block(thread_id: int | None = None) -> str:
    """The thread's kernel and user CPU time over CPU_WINDOW_S: kernel time
    means busy in Windows, user time busy in Qt or Python. Windows only
    (empty elsewhere); never raises; runs on the watchdog thread."""
    if sys.platform != "win32":
        return ""
    handle = 0
    try:
        tid = thread_id or _main_thread_id or threading.main_thread().native_id
        if not tid:
            raise RuntimeError("main thread id unknown")
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenThread.restype = ctypes.c_void_p
        k32.OpenThread.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = k32.OpenThread(_THREAD_QUERY_LIMITED_INFORMATION, 0, tid) or 0
        if not handle:
            raise OSError(f"OpenThread failed ({ctypes.get_last_error()})")
        k0, u0 = _thread_cpu_ms(handle)
        t0 = clock.monotonic()
        threading.Event().wait(CPU_WINDOW_S)
        k1, u1 = _thread_cpu_ms(handle)
        took = max(clock.monotonic() - t0, 0.001)
        kernel, user = k1 - k0, u1 - u0
        pct = (kernel + user) / (took * 1000.0) * 100.0
        return (
            f"Main thread CPU over {CPU_WINDOW_S:g} s: kernel {kernel:.0f} ms, "
            f"user {user:.0f} ms ({pct:.0f} % of one core)"
        )
    except Exception as e:
        return f"Main thread CPU: not available ({e})"
    finally:
        if handle:
            try:
                ctypes.WinDLL("kernel32").CloseHandle(ctypes.c_void_p(handle))
            except Exception:
                pass


def windows_block(thread_id: int | None = None) -> str:
    """The top-level windows the thread owns (class names) and its GUI state
    flags and window handles. Windows only (empty elsewhere); never raises;
    runs on the watchdog thread."""
    if sys.platform != "win32":
        return ""
    try:
        from ctypes import wintypes

        tid = thread_id or _main_thread_id or threading.main_thread().native_id
        if not tid:
            raise RuntimeError("main thread id unknown")
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumThreadWindows.argtypes = [wintypes.DWORD, proc, wintypes.LPARAM]
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        classes: dict[str, int] = {}
        total = [0]

        def each(hwnd: int, _lparam: int) -> bool:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            classes[buf.value] = classes.get(buf.value, 0) + 1
            total[0] += 1
            return True

        user32.EnumThreadWindows(tid, proc(each), 0)
        # no windows for a thread that doesn't exist, or one without any
        if not total[0] and not any(t.native_id == tid for t in threading.enumerate()):
            raise RuntimeError("thread not found or owns no windows")
        listed = ", ".join(f"{k}: {v}" for k, v in sorted(classes.items()))
        lines = [f"Main thread windows: {total[0]} ({listed})"]

        class GUIThreadInfo(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
                ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
                ("rcCaret", wintypes.RECT),
            ]

        info = GUIThreadInfo()
        info.cbSize = ctypes.sizeof(info)
        user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.c_void_p]
        if user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
            lines.append(
                f"Main thread GUI state: flags 0x{info.flags:X}, "
                f"active {info.hwndActive or 0:#x}, focus {info.hwndFocus or 0:#x}, "
                f"capture {info.hwndCapture or 0:#x}, "
                f"menu {info.hwndMenuOwner or 0:#x}, "
                f"move/size {info.hwndMoveSize or 0:#x}"
            )
        else:
            lines.append(
                "Main thread GUI state: not available "
                f"(GetGUIThreadInfo failed ({ctypes.get_last_error()}))"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Main thread windows: not available ({e})"


def hooks_block(thread_id: int | None = None) -> str:
    """Whether a low-level keyboard or mouse hook is installed on the main
    thread, from the program's own state (each hook runs on its own thread).
    Never raises; runs on the watchdog thread."""
    try:
        tid = thread_id or _main_thread_id or threading.main_thread().native_id
        from gremlin import windows_event_hook as weh
        from gremlin.common import SingletonMetaclass

        parts: list[str] = []
        on_main = False
        for name, cls in (("keyboard", weh.KeyboardHook), ("mouse", weh.MouseHook)):
            hook = SingletonMetaclass._instances.get(cls)
            thread = getattr(hook, "_listen_thread", None)
            if hook is None or thread is None or not getattr(hook, "_running", False):
                parts.append(f"{name} not installed")
            elif thread.native_id == tid:
                on_main = True
                parts.append(f"{name} on the main thread")
            else:
                parts.append(f"{name} on its own thread '{thread.name}'")
        return (
            f"Low-level hooks on the main thread: {'yes' if on_main else 'no'} "
            f"({'; '.join(parts)})"
        )
    except Exception as e:
        return f"Low-level hooks on the main thread: not available ({e})"


def _recent_block() -> str:
    """The recent events and the last known window state, as plain text
    (no Qt calls: this runs on the watchdog thread)."""
    parts: list[str] = []
    try:
        from gremlin import trace

        lines = trace.recent_lines()
        parts.append("Recent events:\n" + ("\n".join(lines) if lines else "(none)"))
    except Exception:
        pass
    try:
        from gremlin.ui import window_trace

        known = window_trace.last_known()
        parts.append(
            "Last known window state:\n"
            + "\n".join(f"  {k}: {v}" for k, v in dict(known).items())
        )
    except Exception:
        pass
    return "\n".join(parts)


def _note(text: str, area: str = "Main window") -> None:
    """The stall to the window events, and to trace.log while Timing is on."""
    try:
        from gremlin.ui import window_trace

        window_trace.note(area, text)
    except Exception:
        pass


def _event(text: str) -> None:
    try:
        from gremlin import trace

        if trace.timing_on():
            trace.event(text)
    except Exception:
        pass


class Watchdog(QtCore.QObject):
    """See the module notes. Made and started on the main thread."""

    def __init__(self, threshold_s: float = THRESHOLD_S) -> None:
        super().__init__()
        self._threshold = threshold_s
        self._last_beat = clock.monotonic()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(BEAT_MS)
        self._timer.timeout.connect(self._beat)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        global _main_thread_id
        _main_thread_id = threading.main_thread().native_id
        self._last_beat = clock.monotonic()
        self._timer.start()
        self._stop.clear()
        self._thread = threads.start(
            "not-responding watchdog", self._watch, stop=self._stop.set
        )

    def stop(self) -> None:
        self._timer.stop()
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _beat(self) -> None:
        self._last_beat = clock.monotonic()

    def _check_input_thread(self, stalled_since: float | None) -> float | None:
        """One check of the input thread's heartbeat; returns the new
        stalled-since beat time (None when it is responding). Never raises."""
        try:
            if not input_thread.is_running():
                return None  # not running (or stopped meanwhile): nothing to watch
            silent = input_thread.silent_for()
            if stalled_since is None and silent >= self._threshold:
                text = f"Input thread not responding for {silent:.0f} s."
                _note(f"stall began: no heartbeat for {silent:.0f} s", "Input thread")
                _event(text)
                _log.warning(
                    f"{text} Where every thread is:\n"
                    + thread_stacks()
                    + "\n"
                    + _recent_block()
                )
                return clock.monotonic() - silent
            if stalled_since is not None and silent < self._threshold:
                beat = input_thread.last_beat()
                took = (beat if beat is not None else clock.monotonic()) - stalled_since
                text = f"Input thread responding again after {took:.0f} s"
                _note(f"stall ended after {took:.0f} s", "Input thread")
                _event(text)
                _log.warning(text)
                return None
        except Exception:
            _log.debug("Input thread check failed", exc_info=True)
        return stalled_since

    def _watch(self) -> None:
        frozen_since: float | None = None
        input_stalled_since: float | None = None
        while not self._stop.wait(min(1.0, self._threshold / 2)):
            input_stalled_since = self._check_input_thread(input_stalled_since)
            last = self._last_beat
            silent = clock.monotonic() - last
            if frozen_since is None and silent >= self._threshold:
                frozen_since = last
                text = f"Not responding for {silent:.0f} s."
                _note(f"stall began: no main-loop tick for {silent:.0f} s")
                _event(text)
                _log.warning(
                    f"{text} Where every thread is:\n"
                    + thread_stacks()
                    + ("\n" + wait_chain_block()).rstrip("\n")
                    + ("\n" + native_stack_block()).rstrip("\n")
                    + ("\n" + cpu_block()).rstrip("\n")
                    + ("\n" + windows_block()).rstrip("\n")
                    + ("\n" + hooks_block()).rstrip("\n")
                    + "\n"
                    + _recent_block()
                )
            elif frozen_since is not None and silent < self._threshold:
                text = f"Responding again after {last - frozen_since:.0f} s"
                _note(f"stall ended after {last - frozen_since:.0f} s")
                _event(text)
                _log.warning(text)
                frozen_since = None


_watchdog: Watchdog | None = None


def apply() -> None:
    """Starts or stops the watchdog to match the option (main thread)."""
    global _watchdog
    from gremlin.config import Configuration

    wanted = bool(Configuration().value(*OPTION))
    if wanted:
        if _watchdog is None:
            _watchdog = Watchdog()
        _watchdog.start()
    elif _watchdog is not None:
        _watchdog.stop()
