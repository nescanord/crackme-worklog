# NecrumWin (Reezli challenge) Reverse Engineering Worklog

Technical worklog for a protected Windows x64 console crackme. The project objective is to recover a valid password or, failing that, produce a stable acceptance bypass with the smallest possible patch.

## Verified Target

- Name: `NecrumWin (Reezli challenge)`
- Platform: Windows x64
- Type: native console executable
- Validation model: client-side only
- Author hint: password verification uses cryptographic key derivation

Hashes verified against the challenge:

- `MD5`: `78d8e7061e2db2a51387b501ebbc5586`
- `SHA-1`: `e82e9d93d3bc73c1def281e8f13b3f276d0f5767`
- `SHA-256`: `948089902fbafe0f2333f8a85ac46f81b46375bdcceb141ded697d5b8280cce8`

## Executive Summary

The crackme does not validate through its obvious surface. Standard CRT compares, the visible `bcrypt.dll` import surface, and several plausible helper functions were all tested and downgraded. The real path sits behind runtime-reconstructed code, a VM-like late-state network, and active anti-analysis behavior.

The key strategic pivot was abandoning debugger-driven analysis for the main path. The current workflow launches the process normally, injects input through `CONIN$`, samples thread state externally, and applies focused in-memory patches without attaching a classic debugger.

That workflow recovered:

- a reproducible prompt-side chain
- a reproducible post-validation chain
- a narrower late-state selector centered on `R10 -> R8 -> ESI`
- and a classified trap path whose UI appears as the `bruh` popup

## Current Assessment

- Overall progress: `85%`
- Stable bypass probability: `79%`
- Exact password recovery probability: `40%`

## Confirmed Runtime Chains

Prompt side:

- `0x55d9c83`
- `0x55d9c1c`
- `0x5c68c01`
- `0x5d24729`
- `0x5d2473f`

Post-validation side:

- `0x2cf67df`
- `0x236fe1a`
- `0x23e05cd`

Late convergence:

- `0x27dd114`
- `0x2802257`

## Current Late-State Model

Stable or semi-stable in the late path:

- `RCX = 0x3791ca2a`
- `RDX = 0x20000`
- `RDI` behaves like a state object / table pointer
- `R8` behaves like a support or selector pointer

Strongly input-dependent:

- `RAX`
- `RBX`
- `RSI`

Recovered selector above the late `ESI` gate:

- `test r10w, 0x71ab`
- `sete r8b`
- `add r8d, r8d`
- `call 0x1468d67b5`

Late gate:

- `0x1468d67f8: neg esi`
- `0x1468d67fa: jne 0x1461ec902`

Interpretation:

- `R10` is upstream state
- `R8` is derived from `R10`
- `ESI` is later normalization
- forcing only late state often produces incoherent outcomes

## Anti-Debug And Trap Status

Basic anti-analysis APIs have been patched successfully in-process:

- `CheckRemoteDebuggerPresent`
- `IsDebuggerPresent`
- `FindWindowW`

This reduces contamination but does not unlock the crackme by itself.

`Initialization error 2` is currently classified as:

- an early bad-initialization branch
- triggered by applying selector patches too early

The `bruh` popup is now classified as:

- a modal `#32770` system dialog
- title `crackme.exe`
- child `Static = "bruh"`
- a visible wrapper for a real trap path

When `NtRaiseHardError` is neutralized, the same route exposes its underlying result:

- `exit code = 0xDEADC0DE`

When `NtRaiseHardError`, `NtTerminateProcess`, and `RtlExitUserProcess` are all neutralized during that route, the process remains alive and the console title changes to:

- `crackme | reezli.vc`

That is the best classified non-reject, non-popup live state found so far.

The latest profiling pass compressed the trap problem further. Both the `0xDEADC0DE` route and the `0x80000003` route now converge inside the prompt/decoder family around:

- `0x55d904a`
- `0x55d9057`
- `0x55d90ee`
- `0x55d9107`
- `0x55d912e`
- `0x55d913c`

This is currently the highest-signal local choke window in the whole crackme.

## Repository Layout

- `scripts/`: tracers, popup probes, selector sweep helpers, API guard probes
- `artifacts/`: JSON traces and probe outputs
- `notes/`: synced external summaries
- `findings.md`: concise technical findings
- `timeline.md`: full chronological narrative
- `next-steps.md`: current recommended forward pivots

## Current Direction

The problem is no longer broad exploration. The remaining work is concentrated around:

- coherent `R10`-side state production
- avoiding the `0xDEADC0DE` trap rather than merely silencing its UI
- following the live `crackme | reezli.vc` state toward a stable bypass
- and splitting the two trap outcomes inside the narrowed `0x55d90xx` block
