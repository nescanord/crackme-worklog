"""Follow Reezli's early main path from SetConsoleTitleA into internal callees."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import runtime_probe


def dump_hit(session: runtime_probe.ProcessSession, hit: dict) -> dict:
    payload = {'hit': hit}
    rsp = int(hit['rsp'], 16)
    payload['stack_qwords'] = [hex(v) for v in runtime_probe.stack_qwords(session, rsp, 12)]
    payload['args'] = runtime_probe.preview_registers(session, hit, size=128)
    return payload


def parse_rvas(values):
    return [int(v, 16) for v in values]


def run(args):
    session = runtime_probe.launch_clean(args.exe, start_delay=args.start_delay)
    try:
        title_va, title_orig = runtime_probe.patch_remote_api(
            session,
            'KERNEL32.DLL',
            'kernel32.dll',
            'SetConsoleTitleA',
            runtime_probe.SPIN_STUB,
        )
        if not title_va:
            raise RuntimeError('SetConsoleTitleA was not resolved in the target process')

        title_hit = runtime_probe.wait_hit(session, title_va, timeout=args.timeout)
        result = {
            'base': hex(session.base),
            'title_va': hex(title_va),
            'title_hit': dump_hit(session, title_hit) if title_hit else None,
            'steps': [],
        }
        if not title_hit:
            return result

        runtime_probe.attach_console(session)
        current_pause = ('SetConsoleTitleA', title_va, title_orig)

        for index, rva in enumerate(parse_rvas(args.chain)):
            target_va = session.base + rva
            observed = runtime_probe.low.wait_for_materialization(session.process_info.hProcess, target_va, 8, args.materialization_timeout)
            step = {
                'index': index,
                'target_rva': hex(rva),
                'target_va': hex(target_va),
                'paused_on': current_pause[0],
                'materialized': bool(observed and any(b != 0 for b in observed)),
                'original_bytes': observed.hex() if observed else None,
            }
            if not step['materialized']:
                result['steps'].append(step)
                break
            runtime_probe.low.patch_memory(session.process_info.hProcess, target_va, runtime_probe.SPIN_STUB)
            runtime_probe.restore_remote(session, current_pause[1], current_pause[2])
            if index == 0:
                runtime_probe.send_password(session, args.input_text, input_delay=args.input_delay)
            hit = runtime_probe.wait_hit(session, target_va, timeout=args.timeout)
            if not hit:
                exit_code = runtime_probe.low.wintypes.DWORD(0)
                runtime_probe.low.kernel32.GetExitCodeProcess(session.process_info.hProcess, runtime_probe.low.ctypes.byref(exit_code))
                step['exit_code'] = hex(exit_code.value)
                result['steps'].append(step)
                break
            step.update(dump_hit(session, hit))
            result['steps'].append(step)
            current_pause = (hex(rva), target_va, observed)

        return result
    finally:
        runtime_probe.close(session)


def main():
    parser = argparse.ArgumentParser(description="Follow Reezli's early main path via SetConsoleTitleA and chained internal RVAs.")
    parser.add_argument('--exe', required=True)
    parser.add_argument('--input-text', default='test')
    parser.add_argument('--chain', nargs='*', default=['210efe7', '26f3352', '1c89828', '283092c'])
    parser.add_argument('--start-delay', type=float, default=0.8)
    parser.add_argument('--input-delay', type=float, default=0.7)
    parser.add_argument('--timeout', type=float, default=6.0)
    parser.add_argument('--materialization-timeout', type=float, default=3.0)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    payload = run(args)
    runtime_probe.write_json(args.out, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
