import ctypes, json, os, time
from ctypes import wintypes

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)

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
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD), ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD), ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD), ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD), ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD), ('lpReserved2', ctypes.POINTER(ctypes.c_byte)), ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE), ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]
class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD), ('GlblcntUsage', wintypes.DWORD), ('ProccntUsage', wintypes.DWORD), ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)), ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HMODULE), ('szModule', wintypes.WCHAR * 256), ('szExePath', wintypes.WCHAR * wintypes.MAX_PATH)]
class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [('bKeyDown', wintypes.BOOL), ('wRepeatCount', wintypes.WORD), ('wVirtualKeyCode', wintypes.WORD), ('wVirtualScanCode', wintypes.WORD), ('UnicodeChar', wintypes.WCHAR), ('dwControlKeyState', wintypes.DWORD)]
class INPUT_UNION(ctypes.Union):
    _fields_ = [('KeyEvent', KEY_EVENT_RECORD)]
class INPUT_RECORD(ctypes.Structure):
    _anonymous_ = ('Event',)
    _fields_ = [('EventType', wintypes.WORD), ('Event', INPUT_UNION)]

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def create_process(path):
    si = STARTUPINFOW(); si.cb = ctypes.sizeof(si)
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
        me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me)
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
            ir = INPUT_RECORD(); ir.EventType = 0x0001; ir.bKeyDown = down; ir.wRepeatCount = 1; ir.wVirtualKeyCode = VK_RETURN if ch == '\r' else 0; ir.wVirtualScanCode = 0; ir.UnicodeChar = ch; ir.dwControlKeyState = 0; recs.append(ir)
    arr = (INPUT_RECORD * len(recs))(*recs)
    written = wintypes.DWORD()
    if not kernel32.WriteConsoleInputW(handle, arr, len(recs), ctypes.byref(written)):
        raise ctypes.WinError(ctypes.get_last_error())

def get_text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value

def get_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value

def enum_windows_for_pid(pid):
    out = []
    def enum_child_list(parent):
        kids = []
        @EnumWindowsProc
        def ccb(ch, lp):
            kids.append({'hwnd': int(ch), 'class': get_class(ch), 'text': get_text(ch)})
            return True
        user32.EnumChildWindows(parent, ccb, 0)
        return kids
    @EnumWindowsProc
    def cb(hwnd, lp):
        procid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(procid))
        if procid.value == pid:
            out.append({'hwnd': int(hwnd), 'visible': bool(user32.IsWindowVisible(hwnd)), 'class': get_class(hwnd), 'text': get_text(hwnd), 'children': enum_child_list(hwnd)})
        return True
    user32.EnumWindows(cb, 0)
    return out

def enum_modules(pid):
    mods = []
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == INVALID_HANDLE_VALUE:
        return mods
    try:
        me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me)
        if kernel32.Module32FirstW(snap, ctypes.byref(me)):
            while True:
                mods.append(me.szModule)
                if not kernel32.Module32NextW(snap, ctypes.byref(me)):
                    break
    finally:
        kernel32.CloseHandle(snap)
    return mods

def main():
    exe = r'C:\Users\nesca\Desktop\crackme.exe'
    patches = [
        (0x5b9494, bytes.fromhex('e97ef6feff')),
        (0x34f63, bytes.fromhex('e904531c0190')),
        (0x18d67fa, bytes.fromhex('9090909090')),
    ]
    user_input = 'test'
    pi = create_process(exe)
    hcon = None
    samples = []
    try:
        time.sleep(0.8)
        base, size = module_base(pi.dwProcessId, os.path.basename(exe))
        for rva, raw in patches:
            patch_memory(pi.hProcess, base + rva, raw)
        hcon = open_console_input(pi.dwProcessId)
        time.sleep(0.4)
        send_text(hcon, user_input)
        for i in range(40):
            time.sleep(0.15)
            wins = enum_windows_for_pid(pi.dwProcessId)
            if wins:
                samples.append({'t': round((i+1)*0.15,2), 'windows': wins})
        payload = {'pid': pi.dwProcessId, 'base': hex(base), 'size': hex(size), 'modules': enum_modules(pi.dwProcessId), 'samples': samples}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
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

if __name__ == '__main__':
    main()
