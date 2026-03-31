import argparse
import json
import os
import time

import crackme_popup_context_probe as baseprobe

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
except Exception:
    Cs = None


def disasm_blob(addr, data):
    if not Cs:
        return []
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    out = []
    for insn in md.disasm(data, addr):
        out.append(
            {
                "address": hex(insn.address),
                "mnemonic": insn.mnemonic,
                "op_str": insn.op_str,
                "bytes": insn.bytes.hex(),
            }
        )
    return out


def snapshot_threads_with_stack(pid, hproc, stack_qwords):
    out = []
    for rec in baseprobe.snapshot_threads(pid):
        item = dict(rec)
        try:
            rsp = int(rec["rsp"], 16)
            raw = baseprobe.read_memory(hproc, rsp, stack_qwords * 8)
            item["stack_qwords"] = [
                {
                    "offset": i * 8,
                    "value": hex(int.from_bytes(raw[i * 8:(i + 1) * 8], "little")),
                }
                for i in range(len(raw) // 8)
            ]
        except Exception as e:
            item["stack_error"] = str(e)
        out.append(item)
    return out


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

        for rva, raw in args.early_patches:
            baseprobe.wait_for_materialization(pi.hProcess, base + rva, len(raw), max(0.5, args.start_delay + 1.0))
            baseprobe.patch_memory(pi.hProcess, base + rva, raw)

        hcon = baseprobe.open_console_input(pi.dwProcessId)
        time.sleep(args.input_delay)
        baseprobe.send_text(hcon, args.input_text)

        if args.patch_delay > 0:
            time.sleep(args.patch_delay)

        captures = {}
        capture_set = {rva: None for rva in args.capture_rvas}
        pending_late = {rva: raw for rva, raw in args.late_patches}
        late_applied = []
        end = time.time() + args.runtime
        matched_title = None
        popup = None
        global_windows = []
        thread_snapshot = None

        while time.time() < end:
            for rva in list(pending_late):
                raw = pending_late[rva]
                addr = base + rva
                try:
                    before = baseprobe.read_memory(pi.hProcess, addr, len(raw))
                except OSError:
                    continue
                if not before or all(b == 0 for b in before):
                    continue
                try:
                    baseprobe.patch_memory(pi.hProcess, addr, raw)
                    late_applied.append({"rva": hex(rva), "bytes": raw.hex(), "observed_before": before.hex()})
                    pending_late.pop(rva, None)
                except Exception:
                    pass
            for rva in list(capture_set):
                addr = base + rva
                try:
                    blob = baseprobe.read_memory(pi.hProcess, addr - args.pre_bytes, args.pre_bytes + args.post_bytes)
                except OSError:
                    continue
                if not blob or all(b == 0 for b in blob):
                    continue
                captures[hex(rva)] = {
                    "va": hex(addr),
                    "start_va": hex(addr - args.pre_bytes),
                    "blob": blob.hex(),
                    "disasm": disasm_blob(addr - args.pre_bytes, blob),
                }
                capture_set.pop(rva, None)

            popup, global_windows = baseprobe.popup_for_pid(pi.dwProcessId, ("initialization error", "bruh", "detected", "wrong"))
            own_windows = baseprobe.enum_windows(pi.dwProcessId)
            for w in own_windows:
                if args.watch_title and args.watch_title.lower() in (w["text"] or "").lower():
                    matched_title = w
                    break
            if popup or matched_title:
                thread_snapshot = snapshot_threads_with_stack(pi.dwProcessId, pi.hProcess, args.stack_qwords)
                break

            exit_code = baseprobe.wintypes.DWORD(0)
            baseprobe.kernel32.GetExitCodeProcess(pi.hProcess, baseprobe.ctypes.byref(exit_code))
            if exit_code.value != 0x103:
                break
            if not capture_set and args.stop_after_capture:
                thread_snapshot = snapshot_threads_with_stack(pi.dwProcessId, pi.hProcess, args.stack_qwords)
                break
            time.sleep(args.sample_interval)

        exit_code = baseprobe.wintypes.DWORD(0)
        baseprobe.kernel32.GetExitCodeProcess(pi.hProcess, baseprobe.ctypes.byref(exit_code))
        if thread_snapshot is None and (popup or matched_title or exit_code.value == 0x103):
            thread_snapshot = snapshot_threads_with_stack(pi.dwProcessId, pi.hProcess, args.stack_qwords)

        return {
            "pid": pi.dwProcessId,
            "input": args.input_text,
            "base": hex(base),
            "api_patches": api_patches,
            "captures": captures,
            "late_patches": late_applied,
            "late_pending": [hex(rva) for rva in pending_late],
            "pending_captures": [hex(rva) for rva in capture_set],
            "popup": popup,
            "matched_title": matched_title,
            "own_windows": baseprobe.enum_windows(pi.dwProcessId),
            "global_windows": global_windows,
            "thread_snapshot": thread_snapshot,
            "exit_code": hex(exit_code.value),
        }
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
    ap = argparse.ArgumentParser(description="Capture late-materialized code windows around selected RVAs.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--input-text", required=True)
    ap.add_argument("--capture-rva", action="append", default=[])
    ap.add_argument("--early-patch", action="append", default=[])
    ap.add_argument("--late-patch", action="append", default=[])
    ap.add_argument("--patch-harderror", action="store_true")
    ap.add_argument("--patch-terminate", action="store_true")
    ap.add_argument("--patch-exit-user", action="store_true")
    ap.add_argument("--watch-title")
    ap.add_argument("--start-delay", type=float, default=0.8)
    ap.add_argument("--input-delay", type=float, default=0.4)
    ap.add_argument("--patch-delay", type=float, default=0.05)
    ap.add_argument("--runtime", type=float, default=5.0)
    ap.add_argument("--sample-interval", type=float, default=0.005)
    ap.add_argument("--pre-bytes", type=int, default=24)
    ap.add_argument("--post-bytes", type=int, default=40)
    ap.add_argument("--stop-after-capture", action="store_true")
    ap.add_argument("--stack-qwords", type=int, default=12)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    args.capture_rvas = [int(x, 16) for x in args.capture_rva]
    args.early_patches = [baseprobe.parse_patch(x) for x in args.early_patch]
    args.late_patches = [baseprobe.parse_patch(x) for x in args.late_patch]
    payload = run(args)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
