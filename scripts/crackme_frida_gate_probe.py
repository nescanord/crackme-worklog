import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes

import frida

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

CREATE_NEW_CONSOLE = 0x00000010
CREATE_UNICODE_ENVIRONMENT = 0x00000400
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
VK_RETURN = 0x0D

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD), ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD), ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD), ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD), ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD), ('lpReserved2', ctypes.POINTER(ctypes.c_byte)), ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE), ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]
class KEY_EVENT_RECORD(ctypes.Structure):
    _fields_ = [('bKeyDown', wintypes.BOOL), ('wRepeatCount', wintypes.WORD), ('wVirtualKeyCode', wintypes.WORD), ('wVirtualScanCode', wintypes.WORD), ('UnicodeChar', wintypes.WCHAR), ('dwControlKeyState', wintypes.DWORD)]
class INPUT_UNION(ctypes.Union):
    _fields_ = [('KeyEvent', KEY_EVENT_RECORD)]
class INPUT_RECORD(ctypes.Structure):
    _anonymous_ = ('Event',)
    _fields_ = [('EventType', wintypes.WORD), ('Event', INPUT_UNION)]


def create_process(path):
    si = STARTUPINFOW(); si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer(f'"{path}"')
    ok = kernel32.CreateProcessW(None, cmdline, None, None, False, CREATE_NEW_CONSOLE | CREATE_UNICODE_ENVIRONMENT, None, os.path.dirname(path) or None, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return pi


def open_console_input(pid):
    kernel32.FreeConsole()
    if not kernel32.AttachConsole(pid):
        raise ctypes.WinError(ctypes.get_last_error())
    h = kernel32.CreateFileW('CONIN$', GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == wintypes.HANDLE(-1).value:
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

JS = r'''
const exeName = "crackme.exe";
const base = Process.getModuleByName(exeName).base;
function h(x) { return ptr(base).add(x); }
function sendState(tag, ctx) {
  send({
    kind: 'state',
    tag: tag,
    rip: ctx.rip.toString(),
    rax: ctx.rax.toString(),
    rbx: ctx.rbx.toString(),
    rcx: ctx.rcx.toString(),
    rdx: ctx.rdx.toString(),
    rsi: ctx.rsi.toString(),
    rdi: ctx.rdi.toString(),
    r8: ctx.r8.toString(),
    r9: ctx.r9.toString(),
    r10: ctx.r10.toString(),
    r11: ctx.r11.toString(),
  });
}
Interceptor.attach(h(0x18d67c3), { onEnter(args) { sendState('mov_rsi_r8', this.context); } });
Interceptor.attach(h(0x18d67d2), { onEnter(args) { sendState('not_sil', this.context); } });
Interceptor.attach(h(0x18d67f8), { onEnter(args) { sendState('neg_esi', this.context); } });
Interceptor.attach(h(0x1ec902), { onEnter(args) { sendState('branch_target_1ec902', this.context); } });
Interceptor.attach(h(0x236fe1a), { onEnter(args) { sendState('hot_236fe1a', this.context); } });
Interceptor.attach(h(0x23e05cd), { onEnter(args) { sendState('hot_23e05cd', this.context); } });
Interceptor.attach(h(0x27dd114), { onEnter(args) { sendState('hot_27dd114', this.context); } });
Interceptor.attach(h(0x2802257), { onEnter(args) { sendState('hot_2802257', this.context); } });
let mba = null;
try {
  mba = Process.getModuleByName('user32.dll').getExportByName('MessageBoxA');
} catch (e) {
  mba = null;
}
if (mba) {
  Interceptor.attach(mba, {
    onEnter(args) {
      const text = args[1].isNull() ? '' : args[1].readCString();
      const caption = args[2].isNull() ? '' : args[2].readCString();
      send({ kind: 'messageboxa', text: text, caption: caption });
    }
  });
}
'''


def run_once(exe, user_input, runtime=5.0):
    pi = create_process(exe)
    records = []
    def on_message(message, data):
        if message.get('type') == 'send':
            records.append(message['payload'])
        else:
            records.append({'kind': 'frida', 'message': message})
    try:
        time.sleep(0.8)
        session = frida.attach(pi.dwProcessId)
        script = session.create_script(JS)
        script.on('message', on_message)
        script.load()
        hcon = open_console_input(pi.dwProcessId)
        try:
            time.sleep(0.4)
            send_text(hcon, user_input)
            time.sleep(runtime)
        finally:
            kernel32.CloseHandle(hcon)
            kernel32.FreeConsole()
            session.detach()
        return {'input': user_input, 'pid': pi.dwProcessId, 'records': records}
    finally:
        try:
            kernel32.TerminateProcess(pi.hProcess, 0)
        except Exception:
            pass
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)


def main():
    exe = r'C:\Users\nesca\Desktop\crackme.exe'
    inputs = sys.argv[1:] or ['test', 'auth_login_success', 'aaaa', 'aaab']
    out = [run_once(exe, item) for item in inputs]
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
