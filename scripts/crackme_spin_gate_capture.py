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
TH32CS_SNAPTHREAD = 0x00000004
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
PAGE_EXECUTE_READWRITE = 0x40
WAIT_TIMEOUT = 0x102
VK_RETURN = 0x0D
THREAD_SUSPEND_RESUME = 0x0002
THREAD_GET_CONTEXT = 0x0008
THREAD_QUERY_INFORMATION = 0x0040
CONTEXT_AMD64 = 0x00100000
CONTEXT_CONTROL = CONTEXT_AMD64 | 0x1
CONTEXT_INTEGER = CONTEXT_AMD64 | 0x2
CONTEXT_FLOATING_POINT = CONTEXT_AMD64 | 0x8
CONTEXT_FULL = CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_FLOATING_POINT


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


def try_remote_proc_va(pid, module_name, local_dll, proc_name):
    local_mod = kernel32.GetModuleHandleW(local_dll)
    if not local_mod:
        return None
    proc = kernel32.GetProcAddress(local_mod, proc_name.encode("ascii"))
    if not proc:
        return None
    remote_base, _ = module_base(pid, module_name)
    return remote_base + (int(proc) - int(local_mod))


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


def open_console_input(pid):
    kernel32.FreeConsole()
    check_ok(kernel32.AttachConsole(pid))
    h = kernel32.CreateFileW("CONIN$", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    return h


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
    last = b""
    while time.time() < end:
        try:
            last = read_memory(hproc, addr, 8)
        except OSError:
            last = b""
        if last and any(b != 0 for b in last):
            return last
        time.sleep(0.01)
    return last


def parse_patch(spec):
    rva_text, hex_bytes = spec.split(":", 1)
    return int(rva_text, 16), bytes.fromhex(hex_bytes)


def apply_guard_patches(hproc, pid):
    out = {}
    guard_defs = [
        ("kernel32.dll", "kernel32.dll", "CheckRemoteDebuggerPresent", b"\x31\xC0\xC3"),
        ("kernel32.dll", "kernel32.dll", "IsDebuggerPresent", b"\x31\xC0\xC3"),
        ("user32.dll", "user32.dll", "FindWindowW", b"\x31\xC0\xC3"),
        ("ntdll.dll", "ntdll.dll", "NtRaiseHardError", b"\x31\xC0\xC3"),
    ]
    for mod_name, local_dll, proc_name, patch in guard_defs:
        va = try_remote_proc_va(pid, mod_name, local_dll, proc_name)
        if va:
            patch_memory(hproc, va, patch)
            out[proc_name] = hex(va)
    return out


def run_probe(exe_path, user_input, target_rva, timeout, start_delay, input_delay, patches, patch_after_input):
    pi = create_process(exe_path)
    try:
        time.sleep(start_delay)
        base, size = module_base(pi.dwProcessId, os.path.basename(exe_path))
        target = base + target_rva
        orig = wait_for_materialization(pi.hProcess, target, timeout / 2.0)
        api_patches = apply_guard_patches(pi.hProcess, pi.dwProcessId)
        if not patch_after_input:
            for rva, data in patches:
                patch_memory(pi.hProcess, base + rva, data)
        patch_memory(pi.hProcess, target, b"\xEB\xFE")
        hcon = open_console_input(pi.dwProcessId)
        try:
            time.sleep(input_delay)
            send_text(hcon, user_input)
            if patch_after_input:
                time.sleep(0.05)
                for rva, data in patches:
                    patch_memory(pi.hProcess, base + rva, data)
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
                        except OSError:
                            ctx = None
                        try:
                            if ctx is not None and int(ctx.Rip) == target:
                                captured = {
                                    "input": user_input,
                                    "pid": pi.dwProcessId,
                                    "tid": tid,
                                    "base": hex(base),
                                    "size": hex(size),
                                    "target_rva": hex(target_rva),
                                    "target_va": hex(target),
                                    "api_patches": api_patches,
                                    "patch_after_input": patch_after_input,
                                    "patches": [{"rva": hex(rva), "bytes": data.hex()} for rva, data in patches],
                                    "original_bytes": orig.hex(),
                                    "context": ctx_to_dict(ctx),
                                    "stack_80": read_memory(pi.hProcess, int(ctx.Rsp), 0x80).hex(),
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
                    "api_patches": api_patches,
                    "patch_after_input": patch_after_input,
                    "patches": [{"rva": hex(rva), "bytes": data.hex()} for rva, data in patches],
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
    ap = argparse.ArgumentParser(description="Freeze the crackme at a target RVA and dump live register state with anti-debug guards patched.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--target", required=True, type=lambda x: int(x, 16))
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--start-delay", type=float, default=0.8)
    ap.add_argument("--input-delay", type=float, default=0.4)
    ap.add_argument("--patch", action="append", default=[], help="RVA:HEXBYTES")
    ap.add_argument("--patch-after-input", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    patches = [parse_patch(spec) for spec in args.patch]
    results = []
    for user_input in args.inputs:
        results.append(run_probe(args.exe, user_input, args.target, args.timeout, args.start_delay, args.input_delay, patches, args.patch_after_input))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"target": hex(args.target), "results": results}, f, indent=2)
    print(json.dumps({"target": hex(args.target), "results": results}, indent=2))


if __name__ == "__main__":
    main()
