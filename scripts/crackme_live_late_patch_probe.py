import argparse
import ctypes
import json
import os
import time
from ctypes import wintypes

import crackme_popup_context_probe as baseprobe


def try_patch(hproc, addr, raw):
    try:
        baseprobe.patch_memory(hproc, addr, raw)
        return True, None
    except OSError as e:
        return False, str(e)
    except PermissionError as e:
        return False, str(e)


def run(args):
    pi = baseprobe.create_process(args.exe)
    hcon = None
    try:
        time.sleep(args.start_delay)
        base, _ = baseprobe.module_base(pi.dwProcessId, os.path.basename(args.exe))

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
            va = baseprobe.try_remote_proc_va(pi.dwProcessId, module_name, local_dll, proc_name)
            if va:
                baseprobe.patch_memory(pi.hProcess, va, stub)
                api_patches[proc_name] = hex(va)

        early_applied = []
        for rva, raw in args.early_patches:
            baseprobe.wait_for_materialization(pi.hProcess, base + rva, len(raw), max(0.5, args.start_delay + 1.0))
            baseprobe.patch_memory(pi.hProcess, base + rva, raw)
            early_applied.append({"rva": hex(rva), "bytes": raw.hex()})

        pending = {rva: raw for rva, raw in args.late_patches}
        late_applied = []
        late_errors = []
        matched_title = None
        popup = None
        global_windows = []

        def retry_late_patches():
            for rva in list(pending):
                raw = pending[rva]
                addr = base + rva
                try:
                    buf = baseprobe.read_memory(pi.hProcess, addr, len(raw))
                except OSError:
                    continue
                if not buf or all(b == 0 for b in buf):
                    continue
                ok, err = try_patch(pi.hProcess, addr, raw)
                if ok:
                    late_applied.append({"rva": hex(rva), "bytes": raw.hex(), "observed_before": buf.hex()})
                    pending.pop(rva, None)
                elif err:
                    late_errors.append({"rva": hex(rva), "error": err, "observed_before": buf.hex()})

        if args.prearm_late:
            prearm_end = time.time() + args.prearm_time
            while time.time() < prearm_end and pending:
                retry_late_patches()
                time.sleep(args.sample_interval)

        hcon = baseprobe.open_console_input(pi.dwProcessId)
        time.sleep(args.input_delay)
        baseprobe.send_text(hcon, args.input_text)

        end = time.time() + args.runtime
        while time.time() < end:
            retry_late_patches()

            popup, global_windows = baseprobe.popup_for_pid(pi.dwProcessId, ("initialization error", "bruh", "detected", "wrong"))
            own_windows = baseprobe.enum_windows(pi.dwProcessId)
            for w in own_windows:
                if args.watch_title and args.watch_title.lower() in (w["text"] or "").lower():
                    matched_title = w
                    break
            exit_code = wintypes.DWORD(0)
            baseprobe.kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
            if popup or matched_title or exit_code.value != 0x103:
                break
            time.sleep(args.sample_interval)

        exit_code = wintypes.DWORD(0)
        baseprobe.kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(exit_code))
        payload = {
            "pid": pi.dwProcessId,
            "input": args.input_text,
            "base": hex(base),
            "api_patches": api_patches,
            "early_patches": early_applied,
            "late_patches": late_applied,
            "late_patch_errors": late_errors[-10:],
            "late_pending": [hex(rva) for rva in pending],
            "popup": popup,
            "matched_title": matched_title,
            "own_windows": baseprobe.enum_windows(pi.dwProcessId),
            "global_windows": global_windows,
            "exit_code": hex(exit_code.value),
        }
        if popup or matched_title or exit_code.value == 0x103:
            payload["thread_snapshot"] = baseprobe.snapshot_threads(pi.dwProcessId)
        return payload
    finally:
        if hcon:
            baseprobe.kernel32.CloseHandle(hcon)
            baseprobe.kernel32.FreeConsole()
        try:
            baseprobe.kernel32.TerminateProcess(pi.hProcess, 0)
        except Exception:
            pass
        baseprobe.kernel32.CloseHandle(pi.hThread)
        baseprobe.kernel32.CloseHandle(pi.hProcess)


def main():
    ap = argparse.ArgumentParser(description="Run crackme with early baseline patches and retry late patches as materialized pages appear.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--input-text", required=True)
    ap.add_argument("--early-patch", action="append", default=[])
    ap.add_argument("--late-patch", action="append", default=[])
    ap.add_argument("--patch-harderror", action="store_true")
    ap.add_argument("--patch-terminate", action="store_true")
    ap.add_argument("--patch-exit-user", action="store_true")
    ap.add_argument("--watch-title")
    ap.add_argument("--start-delay", type=float, default=0.8)
    ap.add_argument("--input-delay", type=float, default=0.4)
    ap.add_argument("--runtime", type=float, default=5.0)
    ap.add_argument("--sample-interval", type=float, default=0.005)
    ap.add_argument("--prearm-late", action="store_true")
    ap.add_argument("--prearm-time", type=float, default=1.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    args.early_patches = [baseprobe.parse_patch(x) for x in args.early_patch]
    args.late_patches = [baseprobe.parse_patch(x) for x in args.late_patch]
    payload = run(args)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
