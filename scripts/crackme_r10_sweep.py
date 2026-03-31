import argparse
import json
import os
import subprocess
import sys
import tempfile


REJECT_TARGETS = [
    0x55D9076,
    0x5D24729,
    0x5D2473F,
    0x236FE1A,
    0x23E05CD,
    0x27DD114,
    0x2802257,
]


def build_patch(r10_value: int) -> str:
    if not (0 <= r10_value <= 0xFFFFFFFF):
        raise ValueError("r10_value out of range")
    # Replace only the 6-byte `test r10w, 0x71ab` with `mov r10d, imm32`.
    # The original `sete r8b` and `add r8d, r8d` remain intact.
    raw = b"\x41\xBA" + r10_value.to_bytes(4, "little")
    return f"0x11fa329:{raw.hex()}"


def run_case(batch_trace: str, exe: str, user_input: str, patch_spec: str, timeout: float, interval: float) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        out_path = tmp.name
    try:
        cmd = [
            sys.executable,
            batch_trace,
            "--exe",
            exe,
            "--inputs",
            user_input,
            "--targets",
            *[hex(t) for t in REJECT_TARGETS],
            "--patch",
            patch_spec,
            "--patch-after-input",
            "--patch-delay",
            "0.05",
            "--timeout",
            str(timeout),
            "--interval",
            str(interval),
            "--max-hits",
            "4",
            "--out",
            out_path,
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:
            return {
                "input": user_input,
                "counts": {},
                "exit_code": hex(exc.returncode & 0xFFFFFFFF),
                "error": f"batch_trace_failed:{exc.returncode}",
            }
        payload = json.loads(open(out_path, "r", encoding="utf-8").read())
        return payload["results"][0]
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def summarize_result(label: str, result: dict) -> dict:
    counts = {int(k, 16): v for k, v in result.get("counts", {}).items()}
    reject_hits = sum(counts.get(t, 0) for t in REJECT_TARGETS)
    return {
        "label": label,
        "input": result["input"],
        "exit_code": result["exit_code"],
        "reject_hits": reject_hits,
        "counts": result.get("counts", {}),
    }


def main():
    ap = argparse.ArgumentParser(description="Sweep coherent R10/R8 selector states against the crackme late path.")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--batch-trace", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--interval", type=float, default=0.005)
    args = ap.parse_args()

    cases = [
        ("r10d_0", 0x00000000),
        ("r10d_1", 0x00000001),
        ("r10d_2", 0x00000002),
        ("r10d_3", 0x00000003),
        ("r10d_4", 0x00000004),
        ("r10d_5", 0x00000005),
        ("r10d_6", 0x00000006),
        ("r10d_7", 0x00000007),
    ]

    inputs = ["test", "auth_login_success", "aaaa"]
    results = []

    for label, r10_value in cases:
        patch_spec = build_patch(r10_value)
        for user_input in inputs:
            result = run_case(args.batch_trace, args.exe, user_input, patch_spec, args.timeout, args.interval)
            summary = summarize_result(label, result)
            summary["r10_value"] = hex(r10_value)
            results.append(summary)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, indent=2)

    ranked = sorted(results, key=lambda r: (r["reject_hits"], r["exit_code"], r["label"], r["input"]))
    for item in ranked:
        print(
            f"{item['label']:16} {item['input']:5} r10={item['r10_value']:>10} "
            f"reject_hits={item['reject_hits']:>4} exit={item['exit_code']}"
        )


if __name__ == "__main__":
    main()
