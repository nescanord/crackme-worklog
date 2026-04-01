"""Canonical runtime helpers built on top of crackme_popup_context_probe.

These helpers are the recommended entry point for new probes. Historical
scripts may still import `crackme_popup_context_probe` directly, but new work
should use this file for cleaner composition and less duplicated boilerplate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import crackme_popup_context_probe as low


ANTIDEBUG_STUBS = [
    ('KERNEL32.DLL', 'kernel32.dll', 'CheckRemoteDebuggerPresent', bytes.fromhex('31C0C3')),
    ('KERNEL32.DLL', 'kernel32.dll', 'IsDebuggerPresent', bytes.fromhex('31C0C3')),
    ('USER32.dll', 'user32.dll', 'FindWindowW', bytes.fromhex('31C0C20800')),
]

SPIN_STUB = bytes.fromhex('EBFE')


@dataclass
class ProcessSession:
    process_info: object
    base: int
    console_handle: int | None = None


def launch_clean(exe_path: str, start_delay: float = 0.8) -> ProcessSession:
    pi = low.create_process(exe_path)
    low.time.sleep(start_delay)
    base, _ = low.module_base(pi.dwProcessId, low.os.path.basename(exe_path))

    for module_name, local_dll, proc_name, stub in ANTIDEBUG_STUBS:
        addr = low.try_remote_proc_va(pi.dwProcessId, module_name, local_dll, proc_name)
        if addr:
            low.patch_memory(pi.hProcess, addr, stub)

    return ProcessSession(process_info=pi, base=base)


def attach_console(session: ProcessSession) -> int:
    session.console_handle = low.open_console_input(session.process_info.dwProcessId)
    return session.console_handle


def send_password(session: ProcessSession, text: str, input_delay: float = 0.4) -> None:
    if session.console_handle is None:
        attach_console(session)
    low.time.sleep(input_delay)
    low.send_text(session.console_handle, text)


def patch_remote_api(session: ProcessSession, module_name: str, local_dll: str, proc_name: str, patch_bytes: bytes) -> tuple[int | None, bytes | None]:
    addr = low.try_remote_proc_va(session.process_info.dwProcessId, module_name, local_dll, proc_name)
    if not addr:
        return None, None
    original = low.read_memory(session.process_info.hProcess, addr, len(patch_bytes))
    low.patch_memory(session.process_info.hProcess, addr, patch_bytes)
    return addr, original


def restore_remote(session: ProcessSession, addr: int | None, original: bytes | None) -> None:
    if addr and original:
        low.patch_memory(session.process_info.hProcess, addr, original)


def wait_hit(session: ProcessSession, addr: int, span: int = 8, timeout: float = 5.0, interval: float = 0.01):
    end = low.time.time() + timeout
    while low.time.time() < end:
        for rec in low.snapshot_threads(session.process_info.dwProcessId):
            rip = int(rec['rip'], 16)
            if addr <= rip < addr + span:
                return rec
        low.time.sleep(interval)
    return None


def stack_qwords(session: ProcessSession, rsp: int, count: int = 12) -> list[int]:
    raw = low.read_memory(session.process_info.hProcess, rsp, count * 8)
    return [int.from_bytes(raw[i * 8:(i + 1) * 8], 'little') for i in range(len(raw) // 8)]


def preview_address(session: ProcessSession, addr: int, size: int = 96) -> dict:
    blob = low.read_memory(session.process_info.hProcess, addr, size)
    return {
        'addr': hex(addr),
        'ascii': ''.join(chr(b) if 32 <= b < 127 else '.' for b in blob),
        'hex': blob.hex(),
    }


def preview_registers(session: ProcessSession, hit: dict, registers: Iterable[str] = ('rcx', 'rdx', 'r8', 'r9'), size: int = 96) -> dict:
    out = {}
    for reg in registers:
        addr = int(hit[reg], 16)
        try:
            out[reg] = preview_address(session, addr, size=size)
        except Exception as exc:
            out[reg] = {'addr': hex(addr), 'error': str(exc)}
    return out


def write_json(path: str, payload: dict) -> None:
    with open(path, 'w', encoding='utf-8') as handle:
        low.json.dump(payload, handle, indent=2, ensure_ascii=False)


def close(session: ProcessSession) -> None:
    if session.console_handle:
        try:
            low.kernel32.CloseHandle(session.console_handle)
            low.kernel32.FreeConsole()
        except Exception:
            pass
    try:
        low.kernel32.TerminateProcess(session.process_info.hProcess, 0)
    except Exception:
        pass
    try:
        low.kernel32.CloseHandle(session.process_info.hThread)
        low.kernel32.CloseHandle(session.process_info.hProcess)
    except Exception:
        pass
