import argparse
import ctypes
import json
import os
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

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
TH32CS_SNAPTHREAD = 0x00000004
THREAD_SUSPEND_RESUME = 0x0002
THREAD_GET_CONTEXT = 0x0008
THREAD_QUERY_INFORMATION = 0x0040


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD), ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)), ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE)
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE), ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


class M128A(ctypes.Structure):
    _fields_ = [("Low", ctypes.c_uint64), ("High", ctypes.c_int64)]


class XMM_SAVE_AREA32(ctypes.Structure):
    _fields_ = [
        ("ControlWord", wintypes.WORD), ("StatusWord", wintypes.WORD), ("TagWord", ctypes.c_byte), ("Reserved1", ctypes.c_byte),
        ("ErrorOpcode", wintypes.WORD), ("ErrorOffset", wintypes.DWORD), ("ErrorSelector", wintypes.WORD), ("Reserved2", wintypes.WORD),
        ("DataOffset", wintypes.DWORD), ("DataSelector", wintypes.WORD), ("Reserved3", wintypes.WORD),
        ("MxCsr", wintypes.DWORD), ("MxCsr_Mask", wintypes.DWORD), ("FloatRegisters", M128A * 8),
        ("XmmRegisters", M128A * 16), ("Reserved4", ctypes.c_byte * 96)
    ]


class DUMMYUNIONNAME(ctypes.Union):
    _fields_ = [("FltSave", XMM_SAVE_AREA32), ("Q", M128A * 16)]


class CONTEXT(ctypes.Structure):
    _anonymous_ = ("DUMMYUNIONNAME",)
    _fields_ = [
        ("P1Home", ctypes.c_uint64), ("P2Home", ctypes.c_uint64), ("P3Home", ctypes.c_uint64), ("P4Home", ctypes.c_uint64),
        ("P5Home", ctypes.c_uint64), ("P6Home", ctypes.c_uint64), ("ContextFlags", wintypes.DWORD), ("MxCsr", wintypes.DWORD),
        ("SegCs", wintypes.WORD), ("SegDs", wintypes.WORD), ("SegEs", wintypes.WORD), ("SegFs", wintypes.WORD),
        ("SegGs", wintypes.WORD), ("SegSs", wintypes.WORD), ("EFlags", wintypes.DWORD), ("Dr0", ctypes.c_uint64),
        ("Dr1", ctypes.c_uint64), ("Dr2", ctypes.c_uint64), ("Dr3", ctypes.c_uint64), ("Dr6", ctypes.c_uint64),
        ("Dr7", ctypes.c_uint64), ("Rax", ctypes.c_uint64), ("Rcx", ctypes.c_uint64), ("Rdx", ctypes.c_uint64),
        ("Rbx", ctypes.c_uint64), ("Rsp", ctypes.c_uint64), ("Rbp", ctypes.c_uint64), ("Rsi", ctypes.c_uint64),
        ("Rdi", ctypes.c_uint64), ("R8", ctypes.c_uint64), ("R9", ctypes.c_uint64), ("R10", ctypes.c_uint64),
        ("R11", ctypes.c_uint64), ("R12", ctypes.c_uint64), ("R13", ctypes.c_uint64), ("R14", ctypes.c_uint64),
        ("R15", ctypes.c_uint64), ("Rip", ctypes.c_uint64), ("DUMMYUNIONNAME", DUMMYUNIONNAME), ("VectorRegister", M128A * 26),
        ("VectorControl", ctypes.c_uint64), ("DebugControl", ctypes.c_uint64), ("LastBranchToRip", ctypes.c_uint64),
        ("LastBranchFromRip", ctypes.c_uint64), ("LastExceptionToRip", ctypes.c_uint64), ("LastExceptionFromRip", ctypes.c_uint64)
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD), ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE), ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * wintypes.MAX_PATH)
    ]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD), ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG), ("dwFlags", wintypes.DWORD)
    ]


class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bKeyDown", wintypes.BOOL), ("wRepeatCount", wintypes.WORD), ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD), ("UnicodeChar", wintypes.WCHAR), ("dwControlKeyState", wintypes.DWORD)
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("KeyEvent", KEY_EVENT_RECORD)]


class INPUT_RECORD(ctypes.Structure):
    _anonymous_ = ("Event",)
    _fields_ = [("EventType", wintypes.WORD), ("Event", INPUT_UNION)]


def check_ok(ok):
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())


def create_process(path):
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer(f'"{path}"')
    ok = kernel32.CreateProcessW(
        None, cmdline, None, None, False,
        CREATE_NEW_CONSOLE | CREATE_UNICODE_ENVIRONMENT,
        None, os.path.dirname(path) or None,
        ctypes.byref(si), ctypes.byref(pi)
    )
    check_ok(ok)
    return pi


def module_base(pid, name):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        me = MODULEENTRY32W()
        me.dwSize = ctypes.sizeof(me)
        check_ok(kernel32.Module32FirstW(snap, ctypes.byref(me)))
        while True:
            if me.szModule.lower() == name.lower():
                return ctypes.addressof(me.modBaseAddr.contents), me.modBaseSize
            if not kernel32.Module32NextW(snap, ctypes.byref(me)):
                break
    finally:
        kernel32.CloseHandle(snap)
    raise RuntimeError("module not found")


def open_console_input(pid):
    kernel32.FreeConsole()
    check_ok(kernel32.AttachConsole(pid))
    h = kernel32.CreateFileW("CONIN$", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    return h


def enum_threads(pid):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snap == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    out = []
    try:
        te = THREADENTRY32()
        te.dwSize = ctypes.sizeof(te)
        check_ok(kernel32.Thread32First(snap, ctypes.byref(te)))
        while True:
            if te.th32OwnerProcessID == pid:
                out.append(te.th32ThreadID)
            if not kernel32.Thread32Next(snap, ctypes.byref(te)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return out


def send_text(handle, text):
    records = []
    for ch in text + "\r":
        for down in (True, False):
            ir = INPUT_RECORD()
            ir.EventType = 0x0001
            ir.bKeyDown = down
            ir.wRepeatCount = 1
            ir.wVirtualKeyCode = VK_RETURN if ch == "\r" else 0
            ir.wVirtualScanCode = 0
            ir.UnicodeChar = ch
            ir.dwControlKeyState = 0
            records.append(ir)
    arr = (INPUT_RECORD * len(records))(*records)
    written = wintypes.DWORD()
    check_ok(kernel32.WriteConsoleInputW(handle, arr, len(records), ctypes.byref(written)))


def patch_memory(hproc, addr, data):
    old = wintypes.DWORD()
    check_ok(kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old)))
    try:
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        written = ctypes.c_size_t()
        check_ok(kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(written)))
    finally:
        restore = wintypes.DWORD()
        kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(restore))


def read_memory(hproc, addr, size):
    buf = (ctypes.c_ubyte * size)()
    read = ctypes.c_size_t()
    check_ok(kernel32.ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)))
    return bytes(buf[:read.value])


def get_context(hthread):
    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL
    check_ok(kernel32.GetThreadContext(hthread, ctypes.byref(ctx)))
    return ctx


def ctx_to_dict(ctx):
    names = ("Rip", "Rax", "Rbx", "Rcx", "Rdx", "Rsp", "Rbp", "Rsi", "Rdi", "R8", "R9", "R10", "R11", "R12", "R13", "R14", "R15", "EFlags")
    return {name.lower(): hex(int(getattr(ctx, name))) for name in names}


def wait_for_materialization(hproc, addr, timeout):
    end = time.time() + timeout
    while time.time() < end:
        try:
            data = read_memory(hproc, addr, 8)
        except OSError:
            data = b""
        if data and any(b != 0 for b in data):
            return data
        time.sleep(0.01)
    return read_memory(hproc, addr, 8)


def run_probe(exe_path, user_input, target_rva, timeout, start_delay, input_delay):
    pi = create_process(exe_path)
    try:
        time.sleep(start_delay)
        base, size = module_base(pi.dwProcessId, os.path.basename(exe_path))
        target = base + target_rva
        orig = wait_for_materialization(pi.hProcess, target, timeout / 2.0)
        patch_memory(pi.hProcess, target, b"\xEB\xFE")
        hcon = open_console_input(pi.dwProcessId)
        try:
            time.sleep(input_delay)
            send_text(hcon, user_input)
            deadline = time.time() + timeout
            captured = None
            while time.time() < deadline:
                if kernel32.WaitForSingleObject(pi.hProcess, 0) != WAIT_TIMEOUT:
                    break
                for tid in enum_threads(pi.dwProcessId):
                    hthread = kernel32.OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, False, tid)
                    if not hthread:
                        continue
                    try:
                        if kernel32.SuspendThread(hthread) == 0xFFFFFFFF:
                            continue
                        try:
                            ctx = get_context(hthread)
                            if int(ctx.Rip) == target:
                                captured = {
                                    "input": user_input,
                                    "pid": pi.dwProcessId,
                                    "tid": tid,
                                    "base": hex(base),
                                    "size": hex(size),
                                    "target_rva": hex(target_rva),
                                    "target_va": hex(target),
                                    "original_bytes": orig.hex(),
                                    "context": ctx_to_dict(ctx),
                                    "stack_40": read_memory(pi.hProcess, int(ctx.Rsp), 0x40).hex(),
                                }
                                break
                        finally:
                            kernel32.ResumeThread(hthread)
                    finally:
                        kernel32.CloseHandle(hthread)
                if captured is not None:
                    break
                time.sleep(0.001)
            if captured is None:
                exit_code = wintypes.DWORD(0)
                kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
                captured = {
                    "input": user_input,
                    "pid": pi.dwProcessId,
                    "base": hex(base),
                    "size": hex(size),
                    "target_rva": hex(target_rva),
                    "target_va": hex(target),
                    "original_bytes": orig.hex(),
                    "context": None,
                    "exit_code": hex(exit_code.value),
                }
            return captured
        finally:
            kernel32.CloseHandle(hcon)
            kernel32.FreeConsole()
    finally:
        kernel32.TerminateProcess(pi.hProcess, 0)
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)


def main():
    ap = argparse.ArgumentParser(description="Freeze the crackme at a target RVA with a tight jmp loop and dump registers.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--target", required=True, type=lambda x: int(x, 16))
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--start-delay", type=float, default=0.8)
    ap.add_argument("--input-delay", type=float, default=0.4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    results = []
    for user_input in args.inputs:
        results.append(run_probe(args.exe, user_input, args.target, args.timeout, args.start_delay, args.input_delay))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"target": hex(args.target), "results": results}, f, indent=2)
    print(json.dumps({"target": hex(args.target), "results": results}, indent=2))


if __name__ == "__main__":
    main()
