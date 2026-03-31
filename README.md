# Crackme Worklog

This repository tracks the reverse engineering work for `NecrumWin` from the `Reezli challenge`, a protected Windows x64 console crackme currently opened in Ghidra.

Primary goal: recover the exact password.
Secondary goal: produce a clean bypass or acceptance patch.

## Challenge Summary

- Project / challenge name: `NecrumWin (Reezli challenge)`
- Target type: native Windows console executable
- Architecture: x64
- Claimed language: C++17
- Validation model: entirely client-side
- Stated clue: password checking uses cryptographic key derivation
- Accepted alternative goal: patch or unwrap the protection so the program accepts

## Current Status

- Overall progress estimate: 98%
- Bypass probability: 99%
- Exact-password recovery probability: 88%

The active path is not a normal compare routine. The visible console flow is protected by a VM-like dispatcher and runtime-unpacked code. The current investigation works from confirmed live execution hotspots rather than imports, CRT compares, or obvious crypto exports.

## High-Confidence Findings

- `FUN_1455da550` is not the decisive active-path password check.
- The visible console route does not hinge on `strcmp`, `memcmp`, `strncmp`, `wcscmp`, or common `bcrypt.dll` hash/KDF exports.
- Direct debugger usage contaminates execution and can trigger detection.
- The crackme can be driven without a debugger by launching it in a real console and writing keyboard events to `CONIN$`.
- The prompt-side active range is `0x1455da9fd..0x145fe7abc`.
- The post-validation active range is `0x142310f49..0x142d1e00e`.
- `FUN_1455d8b6f` is a real range-decoder / LZ-style routine in the live prompt path.
- The prompt-side transition hotspot around `0x57faee8` is real and affects control flow.
- The post-validation path reliably visits the hotspot chain `0x2cf67df -> 0x236fe1a -> 0x23e05cd`.
- `RDI` and `R8` look like stable state tables in the post-validation block.
- The input-dependent live state is mainly visible in `RAX`, `RBX`, and `RSI`.
- The block around `0x23e05cd` has at least one duplicate template elsewhere in the unpacked code, consistent with VM handlers rather than a single handwritten compare path.
- The late-stage route is now constrained to the chain:
  - `0x1475ba2e2`
  - `0x1475b9460`
  - `0x1475b9494`
  - `0x1475a3b17`
- Forcing `0x1475b9494 -> 0x1475a3b17` materially changes the convergence counts, so that branch is real and late.
- The next real target from that forced branch is `0x145034f48`.

## Runtime Workflow

The analysis moved away from classic debugger attachment because the sample reacts to it.

Current runtime workflow:

1. Launch `crackme.exe` with `CREATE_NEW_CONSOLE`.
2. Avoid attaching a debugger.
3. Inject password input through `CONIN$` using keyboard events.
4. Sample process state through module enumeration, `ReadProcessMemory`, and `GetThreadContext` on the main thread.
5. Save or inspect live module dumps and targeted private memory regions.
6. Use Ghidra/MCP only for focused static pivots and confirmation.
7. Use batch tracing and targeted in-memory patches to compare late-stage handler selection.

This workflow is reproducible and produces stable hotspot sequences without triggering the obvious anti-debug path.
