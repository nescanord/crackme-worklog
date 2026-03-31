import argparse
import ctypes
import os
import sys
import time
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400
STARTF_USESTDHANDLES = 0x00000100
HANDLE_FLAG_INHERIT = 0x00000001
PAGE_EXECUTE_READWRITE = 0x40
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


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


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", wintypes.LPVOID), ("bInheritHandle", wintypes.BOOL)]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD), ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE), ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * wintypes.MAX_PATH)
    ]


kernel32.CreatePipe.argtypes = [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.DWORD]
kernel32.CreatePipe.restype = wintypes.BOOL
kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
kernel32.SetHandleInformation.restype = wintypes.BOOL
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32FirstW.restype = wintypes.BOOL
kernel32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32NextW.restype = wintypes.BOOL


def check(ok):
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())


def parse_patch(spec):
    rva_text, hex_bytes = spec.split(':', 1)
    return int(rva_text, 16), bytes.fromhex(hex_bytes)


def create_pipe_pair():
    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(sa)
    sa.bInheritHandle = True
    r = wintypes.HANDLE()
    w = wintypes.HANDLE()
    check(kernel32.CreatePipe(ctypes.byref(r), ctypes.byref(w), ctypes.byref(sa), 0))
    return r, w


def module_base(pid, name, retries=40, delay=0.05):
    for _ in range(retries):
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
        if snap != INVALID_HANDLE_VALUE:
            try:
                me = MODULEENTRY32W()
                me.dwSize = ctypes.sizeof(me)
                if kernel32.Module32FirstW(snap, ctypes.byref(me)):
                    while True:
                        if me.szModule.lower() == name.lower():
                            return ctypes.addressof(me.modBaseAddr.contents)
                        if not kernel32.Module32NextW(snap, ctypes.byref(me)):
                            break
            finally:
                kernel32.CloseHandle(snap)
        time.sleep(delay)
    raise RuntimeError('module not found')


def patch_memory(hproc, addr, data):
    old = wintypes.DWORD()
    check(kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old)))
    try:
        written = ctypes.c_size_t()
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        check(kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(written)))
    finally:
        restore = wintypes.DWORD()
        kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(restore))


def create_process_with_pipes(exe_path):
    stdin_read, stdin_write = create_pipe_pair()
    stdout_read, stdout_write = create_pipe_pair()
    check(kernel32.SetHandleInformation(stdin_write, HANDLE_FLAG_INHERIT, 0))
    check(kernel32.SetHandleInformation(stdout_read, HANDLE_FLAG_INHERIT, 0))

    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    si.dwFlags = STARTF_USESTDHANDLES
    si.hStdInput = stdin_read
    si.hStdOutput = stdout_write
    si.hStdError = stdout_write

    pi = PROCESS_INFORMATION()
    cmdline = ctypes.create_unicode_buffer(f'"{exe_path}"')
    ok = kernel32.CreateProcessW(None, cmdline, None, None, True, CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT, None, os.path.dirname(exe_path) or None, ctypes.byref(si), ctypes.byref(pi))
    try:
        check(ok)
    finally:
        kernel32.CloseHandle(stdin_read)
        kernel32.CloseHandle(stdout_write)
    return pi, stdin_write, stdout_read


def read_available(handle, timeout):
    chunks = []
    start = time.time()
    while time.time() - start < timeout:
        avail = wintypes.DWORD()
        if not kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None):
            break
        if avail.value:
            buf = ctypes.create_string_buffer(avail.value)
            read = wintypes.DWORD()
            check(kernel32.ReadFile(handle, buf, avail.value, ctypes.byref(read), None))
            if read.value:
                chunks.append(buf.raw[:read.value])
                continue
        time.sleep(0.05)
    return b''.join(chunks)


def run_probe(exe_path, user_input, patches, settle, read_timeout):
    pi, stdin_write, stdout_read = create_process_with_pipes(exe_path)
    try:
        prev = kernel32.ResumeThread(pi.hThread)
        if prev == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())

        if patches:
            base = module_base(pi.dwProcessId, os.path.basename(exe_path))
            time.sleep(0.2)
            if kernel32.SuspendThread(pi.hThread) == 0xFFFFFFFF:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                for rva, raw in patches:
                    patch_memory(pi.hProcess, base + rva, raw)
            finally:
                kernel32.ResumeThread(pi.hThread)
        else:
            base = module_base(pi.dwProcessId, os.path.basename(exe_path))

        time.sleep(settle)
        data = (user_input + '\r\n').encode('utf-8', 'ignore')
        written = wintypes.DWORD()
        buf = ctypes.create_string_buffer(data)
        check(kernel32.WriteFile(stdin_write, buf, len(data), ctypes.byref(written), None))
        kernel32.CloseHandle(stdin_write)
        time.sleep(0.3)
        output = read_available(stdout_read, read_timeout)
        exit_code = wintypes.DWORD(0)
        kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
        return {'input': user_input, 'base': hex(base), 'output': output.decode('utf-8', 'replace'), 'output_hex': output.hex(), 'exit_code': hex(exit_code.value)}
    finally:
        kernel32.TerminateProcess(pi.hProcess, 0)
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)
        kernel32.CloseHandle(stdout_read)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--input', required=True)
    ap.add_argument('--patch', action='append', default=[])
    ap.add_argument('--settle', type=float, default=0.8)
    ap.add_argument('--read-timeout', type=float, default=2.0)
    args = ap.parse_args()
    patches = [parse_patch(spec) for spec in args.patch]
    print(run_probe(args.exe, args.input, patches, args.settle, args.read_timeout))


if __name__ == '__main__':
    main()
