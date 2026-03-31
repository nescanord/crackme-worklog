import argparse
import json
import subprocess
from pathlib import Path


BASE_PATCHES = [
    (0x5B9494, "e97ef6feff"),
    (0x34F63, "e904531c0190"),
    (0x18D67FA, "9090909090"),
    (0x55D8D9D, "4531c090909090"),
    (0x55D8F1A, "4531c090909090"),
    (0x55D8FE7, "4531c090909090"),
    (0x55D91C3, "4531c090909090"),
    (0x55D9324, "4531c090909090"),
    (0x55D9537, "4531c090909090"),
    (0x55D9607, "4531c090909090"),
    (0x55D9789, "4531c090909090"),
    (0x55D989D, "4531c090909090"),
    (0x55D9A09, "4531c090909090"),
    (0x55D9B7B, "4531c090909090"),
    (0x55D9D14, "4531c090909090"),
    (0x55D9DBF, "4531c090909090"),
    (0x55D9F55, "4531c090909090"),
    (0x55D8DAF, "4d39ed"),
    (0x55D8F2C, "4d39ed"),
    (0x55D8FF4, "4d39ed"),
    (0x55D91D5, "4d39ed"),
    (0x55D9336, "4d39ed"),
    (0x55D9544, "4d39ed"),
    (0x55D9619, "4d39ed"),
    (0x55D979B, "4d39ed"),
    (0x55D98AF, "4d39ed"),
    (0x55D9A1B, "4d39ed"),
    (0x55D9B88, "4d39ed"),
    (0x55D9D21, "4d39ed"),
    (0x55D9DD1, "4d39ed"),
    (0x55D9F67, "4d39ed"),
    (0x55D9F4F, "909090909090"),
]


VARIANTS = [
    ("a8aa_ret", [(0x55DA8AA, "c3")]),
    ("a8aa_xor_eax_ret", [(0x55DA8AA, "31c0c3")]),
    ("a8aa_mov1_ret", [(0x55DA8AA, "b801000000c3")]),
    ("a8aa_nop_calls", [(0x55DA8AB, "9090909090"), (0x55DA8B0, "9090909090")]),
    ("a8aa_skip_jno", [(0x55DA8D9, "909090909090")]),
    ("a8aa_force_jno", [(0x55DA8D9, "e9ed6a77fd90")]),
    ("a8aa_ret_and_xabort_ret", [(0x55DA8AA, "31c0c3"), (0x1E0AE4C, "c39090")]),
    ("a8aa_ret_and_xabort_spin", [(0x55DA8AA, "31c0c3"), (0x1E0AE4C, "ebfe90")]),
]


def main():
    ap = argparse.ArgumentParser(description="Sweep late-patch variants at the aligned trap block start 0x55da8aa.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--probe-script", default=r"C:\Users\nesca\Desktop\NecrumWin-Reezli\analysis\scripts\crackme_live_late_patch_probe.py")
    ap.add_argument("--input-text", default="test")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"input": args.input_text, "results": []}

    for name, late_patches in VARIANTS:
        out_file = out_dir / f"{name}.json"
        cmd = [
            "python",
            args.probe_script,
            "--exe",
            args.exe,
            "--input-text",
            args.input_text,
            "--patch-harderror",
            "--runtime",
            "5.0",
            "--sample-interval",
            "0.002",
            "--out",
            str(out_file),
        ]
        for rva, raw in BASE_PATCHES:
            cmd += ["--early-patch", f"0x{rva:x}:{raw}"]
        for rva, raw in late_patches:
            cmd += ["--late-patch", f"0x{rva:x}:{raw}"]
        subprocess.run(cmd, check=True)
        payload = json.loads(out_file.read_text(encoding="utf-8"))
        summary["results"].append(
            {
                "name": name,
                "exit_code": payload.get("exit_code"),
                "popup": payload.get("popup"),
                "matched_title": payload.get("matched_title"),
                "late_patches": payload.get("late_patches"),
                "late_pending": payload.get("late_pending"),
                "own_windows": payload.get("own_windows", []),
                "file": out_file.name,
            }
        )

    summary_path = out_dir / "late_block_sweep_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
