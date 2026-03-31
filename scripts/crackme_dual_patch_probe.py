import argparse
import ctypes
import json
import os
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, ctypes.c_char_p]
kernel32.GetProcAddress.restype = ctypes.c_void_p
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

CREATE_NEW_CONSOLE = 0x00000010
CREATE_UNICODE_ENVIRONMENT = 0x00000400
TH32CS_SNAPTHREAD = 0x00000004
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
PAGE_EXECUTE_READWRITE = 0x40
VK_RETURN = 0x0D
THREAD_SUSPEND_RESUME = 0x0002
THREAD_GET_CONTEXT = 0x0008
THREAD_QUERY_INFORMATION = 0x0040
CONTEXT_AMD64 = 0x00100000
CONTEXT_CONTROL = CONTEXT_AMD64 | 0x1
CONTEXT_INTEGER = CONTEXT_AMD64 | 0x2
CONTEXT_FULL = CONTEXT_CONTROL | CONTEXT_INTEGER


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
    raise RuntimeError("module not found")


def try_remote_proc_va(pid, module_name, local_dll, proc_name):
    try:
        local_mod = kernel32.GetModuleHandleW(local_dll)
        if not local_mod:
            return None
        proc = kernel32.GetProcAddress(local_mod, proc_name.encode("ascii"))
        if not proc:
            return None
        remote_base, _ = module_base(pid, module_name)
        return remote_base + (int(proc) - int(local_mod))
    except Exception:
        return None


def enum_threads(pid):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snap == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    out = []
    try:
        te = THREADENTRY32()
        te.dwSize = ctypes.sizeof(te)
        if not kernel32.Thread32First(snap, ctypes.byref(te)):
            raise ctypes.WinError(ctypes.get_last_error())
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
    if not kernel32.AttachConsole(pid):
        raise ctypes.WinError(ctypes.get_last_error())
    h = kernel32.CreateFileW("CONIN$", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    return h


def send_text(handle, text):
    recs = []
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
            recs.append(ir)
    arr = (INPUT_RECORD * len(recs))(*recs)
    written = wintypes.DWORD()
    if not kernel32.WriteConsoleInputW(handle, arr, len(recs), ctypes.byref(written)):
        raise ctypes.WinError(ctypes.get_last_error())


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


def patch_memory(hproc, addr, data):
    old = wintypes.DWORD()
    if not kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        written = ctypes.c_size_t()
        if not kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(written)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        restore = wintypes.DWORD()
        kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(restore))


def parse_patch(spec):
    rva_text, hex_bytes = spec.split(":", 1)
    return int(rva_text, 16), bytes.fromhex(hex_bytes)


def get_text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def get_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def enum_windows(pid=None):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lp):
        procid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(procid))
        if pid is not None and procid.value != pid:
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        out.append({
            "hwnd": hex(int(hwnd)),
            "pid": procid.value,
            "class": get_class(hwnd),
            "text": get_text(hwnd),
        })
        return True

    user32.EnumWindows(cb, 0)
    return out


def child_texts(hwnd):
    texts = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(ch, lp):
        text = get_text(ch)
        klass = get_class(ch)
        if text:
            texts.append({"class": klass, "text": text})
        return True

    user32.EnumChildWindows(hwnd, cb, 0)
    return texts


def popup_for_pid(pid, match_texts):
    wins = enum_windows()
    for w in wins:
        text = (w["text"] or "").lower()
        klass = w["class"]
        children = child_texts(int(w["hwnd"], 16)) if klass == "#32770" else []
        child_blob = " ".join(item["text"].lower() for item in children)
        title_match = any(token in text for token in match_texts)
        child_match = any(token in child_blob for token in match_texts)
        if w["pid"] == pid and (klass == "#32770" or title_match):
            w["children"] = children
            return w, wins
        if klass == "#32770" and ("crackme.exe" in text or child_match):
            w["children"] = children
            return w, wins
    return None, wins


def ctx_record(ctx):
    names = ("Rip", "Rax", "Rbx", "Rcx", "Rdx", "Rsi", "Rdi", "R8", "R9", "R10", "R11", "Rsp", "Rbp", "EFlags")
    return {name.lower(): hex(int(getattr(ctx, name))) for name in names}


def snapshot_threads(pid):
    out = []
    for tid in enum_threads(pid):
        hthr = kernel32.OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, False, tid)
        if not hthr:
            continue
        try:
            if kernel32.SuspendThread(hthr) == 0xFFFFFFFF:
                continue
            try:
                ctx = CONTEXT()
                ctx.ContextFlags = CONTEXT_FULL
                if kernel32.GetThreadContext(hthr, ctypes.byref(ctx)):
                    out.append({"tid": tid, **ctx_record(ctx)})
            finally:
                kernel32.ResumeThread(hthr)
        finally:
            kernel32.CloseHandle(hthr)
    return out


def run(args):
    pi = create_process(args.exe)
    hcon = None
    try:
        time.sleep(args.start_delay)
        base, _ = module_base(pi.dwProcessId, os.path.basename(args.exe))
        api_patches = {}
        api_specs = [
            ("KERNEL32.DLL", "kernel32.dll", "CheckRemoteDebuggerPresent", b"\x31\xC0\xC3"),
            ("KERNEL32.DLL", "kernel32.dll", "IsDebuggerPresent", b"\x31\xC0\xC3"),
            ("USER32.dll", "user32.dll", "FindWindowW", b"\x31\xC0\xC2\x08\x00"),
        ]
        if args.patch_harderror:
            api_specs.append(("ntdll.dll", "ntdll.dll", "NtRaiseHardError", b"\x31\xC0\xC3"))
        if args.patch_terminate:
            api_specs.append(("ntdll.dll", "ntdll.dll", "NtTerminateProcess", b"\x31\xC0\xC3"))
        if args.patch_exit_user:
            api_specs.append(("ntdll.dll", "ntdll.dll", "RtlExitUserProcess", b"\xC3"))
        for module_name, local_dll, proc_name, stub in api_specs:
            va = try_remote_proc_va(pi.dwProcessId, module_name, local_dll, proc_name)
            if va:
                patch_memory(pi.hProcess, va, stub)
                api_patches[proc_name] = hex(va)
        for rva, raw in args.early_patches:
            wait_for_materialization(pi.hProcess, base + rva, len(raw), max(0.5, args.start_delay + 1.0))
            patch_memory(pi.hProcess, base + rva, raw)
        hcon = open_console_input(pi.dwProcessId)
        time.sleep(args.input_delay)
        send_text(hcon, args.input_text)
        if args.late_patches:
            time.sleep(args.patch_delay)
            for rva, raw in args.late_patches:
                wait_for_materialization(pi.hProcess, base + rva, len(raw), max(0.5, args.patch_delay + 1.0))
                patch_memory(pi.hProcess, base + rva, raw)
        end = time.time() + args.runtime
        popup = None
        global_windows = []
        matched_title = None
        while time.time() < end:
            popup, global_windows = popup_for_pid(pi.dwProcessId, ("initialization error", "bruh", "detected", "wrong"))
            own_windows = enum_windows(pi.dwProcessId)
            for w in own_windows:
                if args.watch_title and args.watch_title.lower() in (w["text"] or "").lower():
                    matched_title = w
                    break
            if popup:
                break
            if matched_title:
                break
            time.sleep(args.sample_interval)
        exit_code = wintypes.DWORD(0)
        kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
        payload = {
            "pid": pi.dwProcessId,
            "input": args.input_text,
            "base": hex(base),
            "api_patches": api_patches,
            "early_patches": [{"rva": hex(rva), "bytes": raw.hex()} for rva, raw in args.early_patches],
            "late_patches": [{"rva": hex(rva), "bytes": raw.hex()} for rva, raw in args.late_patches],
            "popup": popup,
            "matched_title": matched_title,
            "own_windows": enum_windows(pi.dwProcessId),
            "global_windows": global_windows,
            "exit_code": hex(exit_code.value),
        }
        if popup or matched_title or exit_code.value == 0x103:
            payload["thread_snapshot"] = snapshot_threads(pi.dwProcessId)
        return payload
    finally:
        if hcon:
            kernel32.CloseHandle(hcon)
            kernel32.FreeConsole()
        try:
            kernel32.TerminateProcess(pi.hProcess, 0)
        except Exception:
            pass
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)


def main():
    ap = argparse.ArgumentParser(description="Trigger popup-producing patch sets and snapshot all thread RIPs when popup appears.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--input-text", required=True)
    ap.add_argument("--early-patch", action="append", default=[])
    ap.add_argument("--late-patch", action="append", default=[])
    ap.add_argument("--patch-delay", type=float, default=0.05)
    ap.add_argument("--patch-harderror", action="store_true")
    ap.add_argument("--patch-terminate", action="store_true")
    ap.add_argument("--patch-exit-user", action="store_true")
    ap.add_argument("--watch-title")
    ap.add_argument("--start-delay", type=float, default=0.8)
    ap.add_argument("--input-delay", type=float, default=0.4)
    ap.add_argument("--runtime", type=float, default=4.0)
    ap.add_argument("--sample-interval", type=float, default=0.05)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    args.early_patches = [parse_patch(x) for x in args.early_patch]
    args.late_patches = [parse_patch(x) for x in args.late_patch]
    payload = run(args)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
