import argparse
import ctypes
import json
import os
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

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
PAGE_EXECUTE_READWRITE = 0x40
VK_RETURN = 0x0D


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


def build_r10_patch(r10d):
    return b"\x41\xBA" + int(r10d).to_bytes(4, "little")


def enum_windows_for_pid(pid):
    results = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        wnd_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wnd_pid))
        if wnd_pid.value != pid:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        visible = bool(user32.IsWindowVisible(hwnd))
        results.append({
            "hwnd": hex(int(hwnd)),
            "title": buf.value,
            "class": cls.value,
            "visible": visible,
        })
        return True

    user32.EnumWindows(cb, 0)
    return results


def run_case(exe, user_input, r10d, runtime):
    pi = create_process(exe)
    try:
        time.sleep(0.8)
        base, size = module_base(pi.dwProcessId, os.path.basename(exe))
        target = base + 0x11FA329
        wait_for_materialization(pi.hProcess, target, 6, 3.0)
        hcon = open_console_input(pi.dwProcessId)
        try:
            time.sleep(0.4)
            send_text(hcon, user_input)
            time.sleep(0.05)
            patch_memory(pi.hProcess, target, build_r10_patch(r10d))
            time.sleep(runtime)
        finally:
            kernel32.CloseHandle(hcon)
            kernel32.FreeConsole()
        exit_code = wintypes.DWORD(0)
        kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
        return {
            "input": user_input,
            "r10d": hex(r10d),
            "pid": pi.dwProcessId,
            "base": hex(base),
            "size": hex(size),
            "exit_code": hex(exit_code.value),
            "windows": enum_windows_for_pid(pi.dwProcessId),
        }
    finally:
        kernel32.TerminateProcess(pi.hProcess, 0)
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)


def main():
    ap = argparse.ArgumentParser(description="Classify R10 selector states by visible windows/output behavior.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--r10ds", nargs="+", required=True, type=lambda x: int(x, 0))
    ap.add_argument("--runtime", type=float, default=2.5)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    results = []
    for r10d in args.r10ds:
        for user_input in args.inputs:
            results.append(run_case(args.exe, user_input, r10d, args.runtime))

    payload = {"results": results}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
