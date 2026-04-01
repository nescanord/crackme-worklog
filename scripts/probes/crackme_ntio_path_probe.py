"""Capture console I/O buffers through NtWriteFile or NtReadFile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import runtime_probe


def parse_nt_io_args(session: runtime_probe.ProcessSession, hit: dict) -> dict:
    rsp = int(hit['rsp'], 16)
    qwords = runtime_probe.stack_qwords(session, rsp, 16)
    payload = {
        'rip': hit['rip'],
        'return': hex(qwords[0]),
        'stack_qwords': [hex(v) for v in qwords],
    }
    if len(qwords) >= 10:
        iosb = qwords[5]
        buffer = qwords[6]
        length = qwords[7] & 0xFFFFFFFF
        payload.update(
            {
                'iosb': hex(iosb),
                'buffer': hex(buffer),
                'length': length,
                'byte_offset': hex(qwords[8]),
                'key': hex(qwords[9]),
            }
        )
        if 0 < length <= 0x400:
            try:
                preview = runtime_probe.preview_address(session, buffer, size=length)
                payload['buffer_ascii'] = preview['ascii']
                payload['buffer_hex'] = preview['hex']
            except Exception as exc:
                payload['buffer_error'] = str(exc)
    return payload


def run(args):
    session = runtime_probe.launch_clean(args.exe, start_delay=args.start_delay)
    try:
        runtime_probe.attach_console(session)
        runtime_probe.low.time.sleep(args.pre_hook_delay)

        api_name = 'NtWriteFile' if args.mode == 'write' else 'NtReadFile'
        target_va, original = runtime_probe.patch_remote_api(
            session,
            'ntdll.dll',
            'ntdll.dll',
            api_name,
            runtime_probe.SPIN_STUB,
        )
        if not target_va:
            raise RuntimeError(f'{api_name} was not resolved in the target process')

        runtime_probe.send_password(session, args.input_text, input_delay=args.input_delay)
        hits = []
        for index in range(args.max_hits):
            hit = runtime_probe.wait_hit(session, target_va, timeout=args.timeout, interval=args.interval)
            if not hit:
                exit_code = runtime_probe.low.wintypes.DWORD(0)
                runtime_probe.low.kernel32.GetExitCodeProcess(session.process_info.hProcess, runtime_probe.low.ctypes.byref(exit_code))
                hits.append({'index': index, 'no_hit': True, 'exit_code': hex(exit_code.value)})
                break
            entry = {'index': index, 'api': api_name, **parse_nt_io_args(session, hit)}
            hits.append(entry)
            runtime_probe.restore_remote(session, target_va, original)
            runtime_probe.low.time.sleep(args.rearm_delay)
            runtime_probe.low.patch_memory(session.process_info.hProcess, target_va, runtime_probe.SPIN_STUB)

        return {
            'base': hex(session.base),
            'api': api_name,
            'target_va': hex(target_va),
            'hits': hits,
        }
    finally:
        runtime_probe.close(session)


def main():
    parser = argparse.ArgumentParser(description='Capture console I/O buffers from NtWriteFile or NtReadFile.')
    parser.add_argument('--exe', required=True)
    parser.add_argument('--mode', choices=('write', 'read'), default='write')
    parser.add_argument('--input-text', default='test')
    parser.add_argument('--start-delay', type=float, default=0.8)
    parser.add_argument('--pre-hook-delay', type=float, default=1.5)
    parser.add_argument('--input-delay', type=float, default=0.8)
    parser.add_argument('--timeout', type=float, default=3.0)
    parser.add_argument('--interval', type=float, default=0.005)
    parser.add_argument('--rearm-delay', type=float, default=0.05)
    parser.add_argument('--max-hits', type=int, default=6)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    payload = run(args)
    runtime_probe.write_json(args.out, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
