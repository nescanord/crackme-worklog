# Findings

## Confirmed Sample Facts

- Target: `NecrumWin (Reezli challenge)`
- Platform: Windows x64
- Validation is client-side
- The active sample matches the published challenge hashes

## Confirmed Runtime Facts

- The active visible validation route is not controlled by `strcmp`, `memcmp`, `strncmp`, or `wcscmp`.
- The obvious exported `bcrypt.dll` surface does not line up with the visible live validation route.
- Debugger attachment contaminates execution.
- Frida-style aggressive instrumentation was not reliable for this sample.
- Launching the process normally and injecting input through `CONIN$` is the cleanest reproducible dynamic method.

## Confirmed Hotspot Chains

### Prompt side

- `0x55d9c83`
- `0x55d9c1c`
- `0x5c68c01`
- `0x5d24729`
- `0x5d2473f`

### Post-validation side

- `0x2cf67df`
- `0x236fe1a`
- `0x23e05cd`

### Later convergence

- `0x27dd114`
- `0x2802257`

## Register-State Findings

Stable or semi-stable:

- `RCX = 0x3791ca2a`
- `RDX = 0x20000`
- `RDI` behaves like a persistent state object or table pointer
- `R8` behaves like a persistent support/state pointer

Most input-dependent:

- `RAX`
- `RBX`
- `RSI`

Interpretation:

- the crackme carries a derived internal state rather than a plaintext compare buffer

## Late-State Network

Useful late chain:

- `0x1475ba2e2`
- `0x1475b9460`
- `0x1475b9494`
- `0x1475a3b17`
- `0x145034f48`

Notes:

- `cmp ebx, 1` appears in this region
- patching `cmp ebx, 1` alone does not unlock the sample
- forcing `0x1475b9494 -> 0x1475a3b17` materially changes convergence

## Strongest Late Gate Found

- `0x1468d67f8: neg esi`
- `0x1468d67fa: jne 0x1461ec902`

This gate is real and useful, but it is not the root selector.

## Root Selector Above ESI

Recovered chain:

- `test r10w, 0x71ab`
- `sete r8b`
- `add r8d, r8d`
- `call 0x1468d67b5`

Implications:

- `R10` is upstream of `R8`
- `R8` is upstream of late `ESI`
- forcing only `ESI` or only `R8` is usually too late

Selector reduction:

- a preceding `shr r10d, 0x5d` effectively reduces to `shr r10d, 29`
- immediate selector space collapses to `R10D = 0..7`

## R10 Sweep Findings

Forcing `R10D = 0..7` after input:

- can suppress known reject hotspots
- can produce parked/wait states
- does not yet yield stable visible success

Forcing coherent `R10 = 0` before the selector:

- removes known prompt/reject hotspots from traces
- but does not produce success
- instead tends to park the process

Interpretation:

- `R10` is genuinely upstream of the visible late selector
- the valid acceptance state is not the trivial zero state

## Anti-Debug Findings

Basic anti-debug APIs were patched successfully in-process:

- `CheckRemoteDebuggerPresent`
- `IsDebuggerPresent`
- `FindWindowW`

This reduces contamination but does not change acceptance behavior by itself.

## Initialization Error Classification

`Initialization error 2` is currently classified as:

- a bad early-initialization branch
- caused by applying selector patches too early

When equivalent selector patches are delayed until after input:

- `Initialization error 2` disappears

## Popup And Trap Findings

The `bruh` popup is now classified as:

- a modal `#32770` dialog
- title `crackme.exe`
- child `Static = "bruh"`
- system-owned rather than a normal crackme-owned top-level window

When `NtRaiseHardError` is neutralized:

- the popup disappears
- the underlying route terminates as `0xDEADC0DE`

Meaning:

- `bruh` = hard-error presentation
- `0xDEADC0DE` = underlying trap result

## Termination Suppression Finding

When these are neutralized together:

- `NtRaiseHardError`
- `NtTerminateProcess`
- `RtlExitUserProcess`

and an early trap-producing selector route is forced, the process:

- remains alive
- stops showing the trap popup
- changes its console title to `crackme | reezli.vc`

This is not yet a confirmed bypass, but it is the best classified non-reject, non-popup live state discovered so far.

## Downgraded Or Discarded Leads

- `.pwdprot` as the active password source
- `FUN_1455da550` as the decisive validator
- standard compare APIs as the acceptance gate
- common visible `bcrypt.dll` calls as the active validator
- embedded semantic strings as the correct password
- `bruh` as a success clue
- `Initialization error 2` as the main anti-debug result

## Current Solve Posture

- Bypass remains closer than exact-password recovery
- The remaining problem is concentrated around coherent `R10`-side state production and trap avoidance
