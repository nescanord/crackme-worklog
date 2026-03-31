import argparse
import json
import shutil
import subprocess
from pathlib import Path


LOOP_RVAS = [
    0x55D8D9D,
    0x55D8F1A,
    0x55D8FE7,
    0x55D91C3,
    0x55D9324,
    0x55D9537,
    0x55D9607,
    0x55D9789,
    0x55D989D,
    0x55D9A09,
    0x55D9B7B,
    0x55D9D14,
    0x55D9DBF,
    0x55D9F55,
]

CMP_SITES = [
    0x55D8DAF,
    0x55D8F2C,
    0x55D8FF4,
    0x55D91D5,
    0x55D9336,
    0x55D9544,
    0x55D9619,
    0x55D979B,
    0x55D98AF,
    0x55D9A1B,
    0x55D9B88,
    0x55D9D21,
    0x55D9DD1,
    0x55D9F67,
]

BASE_PATCHES = [
    (0x5B9494, "e97ef6feff"),
    (0x34F63, "e904531c0190"),
    (0x18D67FA, "9090909090"),
]

PATCH_READ_ZERO = (0x55D9F14, "4531db9090")
PATCH_NOP_WRITE = (0x55D9F36, "9090909090")
PATCH_BREAK_LOOP = (0x55D9F4F, "909090909090")
PATCH_FORCE_SUCCESSRET = (0x55D9F40, "e9eb00000090")


def patch_args(patches):
    out = []
    for rva, hex_bytes in patches:
        out += ["--patch", f"0x{rva:x}:{hex_bytes}"]
    return out


def family_patches():
    patches = []
    for rva in LOOP_RVAS:
        patches.append((rva, "4531c090909090"))
    for rva in CMP_SITES:
        patches.append((rva, "4d39ed"))
    return patches


def dumps_after(dump_dir):
    return {p.name for p in dump_dir.glob("*.dmp")}


def run_variant(exe, probe_script, input_text, out_dir, dump_dir, name, extra_patches, noexit):
    before = dumps_after(dump_dir)
    out_file = out_dir / f"{name}.json"
    cmd = [
        "python",
        str(probe_script),
        "--exe",
        str(exe),
        "--input-text",
        input_text,
        "--patch-harderror",
        "--runtime",
        "5.0",
        "--sample-interval",
        "0.002",
        "--out",
        str(out_file),
    ]
    if noexit:
        cmd += ["--patch-terminate", "--patch-exit-user"]
    cmd += patch_args(BASE_PATCHES + extra_patches)
    subprocess.run(cmd, check=True)
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    after = dumps_after(dump_dir)
    new_dumps = sorted(after - before)
    return {
        "name": name,
        "noexit": noexit,
        "exit_code": payload.get("exit_code"),
        "popup": payload.get("popup"),
        "matched_title": payload.get("matched_title"),
        "own_windows": payload.get("own_windows", []),
        "patch_count": len(payload.get("patches", [])),
        "file": out_file.name,
        "new_dumps": new_dumps,
    }


def main():
    ap = argparse.ArgumentParser(description="Sweep second-stage family bypass variants around crackme+0x55d9f14.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--input-text", default="test")
    ap.add_argument("--probe-script", default=r"C:\Users\nesca\Desktop\NecrumWin-Reezli\analysis\scripts\crackme_popup_context_probe.py")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dump-dir", default=r"C:\Users\nesca\Desktop\NecrumWin-Reezli\analysis\dumps")
    ap.add_argument("--clear-dumps", action="store_true")
    args = ap.parse_args()

    exe = Path(args.exe)
    probe_script = Path(args.probe_script)
    out_dir = Path(args.out_dir)
    dump_dir = Path(args.dump_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_dir.mkdir(parents=True, exist_ok=True)

    if args.clear_dumps:
        for p in dump_dir.glob("*.dmp"):
            p.unlink()

    base = family_patches()
    variants = [
        ("family14_readzero", base + [PATCH_READ_ZERO]),
        ("family14_readzero_nopwrite", base + [PATCH_READ_ZERO, PATCH_NOP_WRITE]),
        ("family14_readzero_breakloop", base + [PATCH_READ_ZERO, PATCH_BREAK_LOOP]),
        ("family14_readzero_breakloop_nopwrite", base + [PATCH_READ_ZERO, PATCH_BREAK_LOOP, PATCH_NOP_WRITE]),
        ("family14_breakloop", base + [PATCH_BREAK_LOOP]),
        ("family14_breakloop_nopwrite", base + [PATCH_BREAK_LOOP, PATCH_NOP_WRITE]),
        ("family14_readzero_force_successret", base + [PATCH_READ_ZERO, PATCH_FORCE_SUCCESSRET]),
        ("family14_breakloop_force_successret", base + [PATCH_BREAK_LOOP, PATCH_FORCE_SUCCESSRET]),
    ]

    summary = {"input": args.input_text, "results": []}
    for name, patches in variants:
        for noexit in (False, True):
            summary["results"].append(
                run_variant(exe, probe_script, args.input_text, out_dir, dump_dir, f"{name}_{'noexit' if noexit else 'normal'}", patches, noexit)
            )

    out_file = out_dir / "family_bypass_sweep2_summary.json"
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
