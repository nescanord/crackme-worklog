import argparse
import ctypes
import json
import os
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

CREATE_NEW_CONSOLE = 0x00000010
CREATE_UNICODE_ENVIRONMENT = 0x00000400
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
CONTEXT_AMD64 = 0x00100000
CONTEXT_CONTROL = CONTEXT_AMD64 | 0x1
CONTEXT_INTEGER = CONTEXT_AMD64 | 0x2
CONTEXT_FLOATING_POINT = CONTEXT_AMD64 | 0x8
CONTEXT_FULL = CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_FLOATING_POINT
WAIT_TIMEOUT = 0x102
VK_RETURN = 0x0D
PAGE_EXECUTE_READWRITE = 0x40


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD), ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD), ('dwFillAttribute', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD), ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.POINTER(ctypes.c_byte)), ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE)
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE), ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]


class M128A(ctypes.Structure):
    _fields_ = [('Low', ctypes.c_uint64), ('High', ctypes.c_int64)]


class XMM_SAVE_AREA32(ctypes.Structure):
    _fields_ = [
        ('ControlWord', wintypes.WORD), ('StatusWord', wintypes.WORD), ('TagWord', ctypes.c_byte), ('Reserved1', ctypes.c_byte),
        ('ErrorOpcode', wintypes.WORD), ('ErrorOffset', wintypes.DWORD), ('ErrorSelector', wintypes.WORD), ('Reserved2', wintypes.WORD),
        ('DataOffset', wintypes.DWORD), ('DataSelector', wintypes.WORD), ('Reserved3', wintypes.WORD),
        ('MxCsr', wintypes.DWORD), ('MxCsr_Mask', wintypes.DWORD), ('FloatRegisters', M128A * 8),
        ('XmmRegisters', M128A * 16), ('Reserved4', ctypes.c_byte * 96)
    ]


class DUMMYUNIONNAME(ctypes.Union):
    _fields_ = [('FltSave', XMM_SAVE_AREA32), ('Q', M128A * 16)]


class CONTEXT(ctypes.Structure):
    _anonymous_ = ('DUMMYUNIONNAME',)
    _fields_ = [
        ('P1Home', ctypes.c_uint64), ('P2Home', ctypes.c_uint64), ('P3Home', ctypes.c_uint64), ('P4Home', ctypes.c_uint64),
        ('P5Home', ctypes.c_uint64), ('P6Home', ctypes.c_uint64), ('ContextFlags', wintypes.DWORD), ('MxCsr', wintypes.DWORD),
        ('SegCs', wintypes.WORD), ('SegDs', wintypes.WORD), ('SegEs', wintypes.WORD), ('SegFs', wintypes.WORD),
        ('SegGs', wintypes.WORD), ('SegSs', wintypes.WORD), ('EFlags', wintypes.DWORD), ('Dr0', ctypes.c_uint64),
        ('Dr1', ctypes.c_uint64), ('Dr2', ctypes.c_uint64), ('Dr3', ctypes.c_uint64), ('Dr6', ctypes.c_uint64),
        ('Dr7', ctypes.c_uint64), ('Rax', ctypes.c_uint64), ('Rcx', ctypes.c_uint64), ('Rdx', ctypes.c_uint64),
        ('Rbx', ctypes.c_uint64), ('Rsp', ctypes.c_uint64), ('Rbp', ctypes.c_uint64), ('Rsi', ctypes.c_uint64),
        ('Rdi', ctypes.c_uint64), ('R8', ctypes.c_uint64), ('R9', ctypes.c_uint64), ('R10', ctypes.c_uint64),
        ('R11', ctypes.c_uint64), ('R12', ctypes.c_uint64), ('R13', ctypes.c_uint64), ('R14', ctypes.c_uint64),
        ('R15', ctypes.c_uint64), ('Rip', ctypes.c_uint64), ('DUMMYUNIONNAME', DUMMYUNIONNAME), ('VectorRegister', M128A * 26),
        ('VectorControl', ctypes.c_uint64), ('DebugControl', ctypes.c_uint64), ('LastBranchToRip', ctypes.c_uint64),
        ('LastBranchFromRip', ctypes.c_uint64), ('LastExceptionToRip', ctypes.c_uint64), ('LastExceptionFromRip', ctypes.c_uint64)
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
        ('GlblcntUsage', wintypes.DWORD), ('ProccntUsage', wintypes.DWORD), ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
        ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HMODULE), ('szModule', wintypes.WCHAR * 256),
        ('szExePath', wintypes.WCHAR * wintypes.MAX_PATH)
    ]


class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ('bKeyDown', wintypes.BOOL), ('wRepeatCount', wintypes.WORD), ('wVirtualKeyCode', wintypes.WORD),
        ('wVirtualScanCode', wintypes.WORD), ('UnicodeChar', wintypes.WCHAR), ('dwControlKeyState', wintypes.DWORD)
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [('KeyEvent', KEY_EVENT_RECORD)]


class INPUT_RECORD(ctypes.Structure):
    _anonymous_ = ('Event',)
    _fields_ = [('EventType', wintypes.WORD), ('Event', INPUT_UNION)]


def create_process(path):
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer(f'"{path}"')
    ok = kernel32.CreateProcessW(None, cmdline, None, None, False, CREATE_NEW_CONSOLE | CREATE_UNICODE_ENVIRONMENT, None, os.path.dirname(path) or None, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return pi


def module_base(pid, name):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        me = MODULEENTRY32W()
        me.dwSize = ctypes.sizeof(me)
        if not kernel32.Module32FirstW(snap, ctypes.byref(me)):
            raise ctypes.WinError(ctypes.get_last_error())
        while True:
            if me.szModule.lower() == name.lower():
                return ctypes.addressof(me.modBaseAddr.contents), me.modBaseSize
            if not kernel32.Module32NextW(snap, ctypes.byref(me)):
                break
    finally:
        kernel32.CloseHandle(snap)
    raise RuntimeError('module not found')


def open_console_input(pid):
    kernel32.FreeConsole()
    if not kernel32.AttachConsole(pid):
        raise ctypes.WinError(ctypes.get_last_error())
    h = kernel32.CreateFileW('CONIN$', GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    return h


def send_text(handle, text):
    recs = []
    for ch in text + '\r':
        for down in (True, False):
            ir = INPUT_RECORD()
            ir.EventType = 0x0001
            ir.bKeyDown = down
            ir.wRepeatCount = 1
            ir.wVirtualKeyCode = VK_RETURN if ch == '\r' else 0
            ir.wVirtualScanCode = 0
            ir.UnicodeChar = ch
            ir.dwControlKeyState = 0
            recs.append(ir)
    arr = (INPUT_RECORD * len(recs))(*recs)
    written = wintypes.DWORD()
    if not kernel32.WriteConsoleInputW(handle, arr, len(recs), ctypes.byref(written)):
        raise ctypes.WinError(ctypes.get_last_error())


def patch_memory(hproc, addr, data):
    old = wintypes.DWORD()
    if not kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        written = ctypes.c_size_t()
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        if not kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(written)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        restore = wintypes.DWORD()
        kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(restore))


def read_memory(hproc, addr, size):
    buf = (ctypes.c_ubyte * size)()
    read = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
        raise ctypes.WinError(ctypes.get_last_error())
    return bytes(buf[:read.value])


def wait_for_materialization(hproc, addr, size, timeout):
    end = time.time() + timeout
    last = b""
    while time.time() < end:
        try:
            last = read_memory(hproc, addr, size)
        except OSError:
            last = b""
        if last and any(b != 0 for b in last):
            return last
        time.sleep(0.01)
    return last


def parse_patch(spec):
    rva_text, hex_bytes = spec.split(':', 1)
    return int(rva_text, 16), bytes.fromhex(hex_bytes)


def ctx_record(ctx):
    names = ('Rip', 'Rax', 'Rbx', 'Rcx', 'Rdx', 'Rsi', 'Rdi', 'R8', 'R9', 'R10', 'R11', 'EFlags')
    return {name.lower(): hex(int(getattr(ctx, name))) for name in names}


def run_once(args, user_input, patches):
    pi = create_process(args.exe)
    try:
        time.sleep(args.start_delay)
        base, size = module_base(pi.dwProcessId, os.path.basename(args.exe))
        for rva, raw in patches:
            wait_for_materialization(pi.hProcess, base + rva, len(raw), max(0.5, args.start_delay + args.input_delay + 1.5))
            patch_memory(pi.hProcess, base + rva, raw)
        hcon = open_console_input(pi.dwProcessId)
        try:
            time.sleep(args.input_delay)
            send_text(hcon, user_input)
            targets = set(args.targets)
            counts = {}
            hits = []
            end = time.time() + args.timeout
            while time.time() < end:
                if kernel32.WaitForSingleObject(pi.hProcess, 0) != WAIT_TIMEOUT:
                    break
                if kernel32.SuspendThread(pi.hThread) == 0xFFFFFFFF:
                    raise ctypes.WinError(ctypes.get_last_error())
                try:
                    ctx = CONTEXT()
                    ctx.ContextFlags = CONTEXT_FULL
                    if not kernel32.GetThreadContext(pi.hThread, ctypes.byref(ctx)):
                        raise ctypes.WinError(ctypes.get_last_error())
                    rva = int(ctx.Rip) - base
                    if rva in targets:
                        counts[rva] = counts.get(rva, 0) + 1
                        if counts[rva] <= args.max_hits:
                            rec = {'input': user_input, 'rva': hex(rva), 'hit': counts[rva]}
                            rec.update(ctx_record(ctx))
                            hits.append(rec)
                finally:
                    kernel32.ResumeThread(pi.hThread)
                if args.interval:
                    time.sleep(args.interval)
            exit_code = wintypes.DWORD(0)
            kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
            return {
                'input': user_input,
                'pid': pi.dwProcessId,
                'base': hex(base),
                'size': hex(size),
                'patches': [{'rva': hex(rva), 'bytes': raw.hex()} for rva, raw in patches],
                'counts': {hex(k): v for k, v in sorted(counts.items())},
                'hits': hits,
                'exit_code': hex(exit_code.value),
            }
        finally:
            kernel32.CloseHandle(hcon)
            kernel32.FreeConsole()
    finally:
        kernel32.TerminateProcess(pi.hProcess, 0)
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)


def main():
    ap = argparse.ArgumentParser(description='Batch tracer for the crackme late-stage validation path.')
    ap.add_argument('--exe', required=True)
    ap.add_argument('--inputs', nargs='+', required=True)
    ap.add_argument('--targets', nargs='+', required=True, type=lambda x: int(x, 16))
    ap.add_argument('--patch', action='append', default=[])
    ap.add_argument('--timeout', type=float, default=8.0)
    ap.add_argument('--interval', type=float, default=0.005)
    ap.add_argument('--max-hits', type=int, default=4)
    ap.add_argument('--start-delay', type=float, default=0.8)
    ap.add_argument('--input-delay', type=float, default=0.4)
    ap.add_argument('--out')
    args = ap.parse_args()

    patches = [parse_patch(spec) for spec in args.patch]
    results = [run_once(args, item, patches) for item in args.inputs]
    payload = {'targets': [hex(x) for x in args.targets], 'results': results}
    text = json.dumps(payload, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(text)
    print(text)


if __name__ == '__main__':
    main()
