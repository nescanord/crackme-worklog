# Findings

## Confirmed Sample Facts

- Target: `NecrumWin (Reezli challenge)`
- Platform: Windows x64
- Validation is client-side only
- The active sample matches the published challenge hashes exactly
- Ghidra's older project database is valid enough to continue static work; there is no need to re-import the sample

## Confirmed Decoys And False Leads

- The fake auth strings and URLs are real decoys and not the password
- `.pwdprot` and several earlier static surfaces did not produce the real validation route
- `FUN_1455da550` does not control the visible post-input validation path
- obvious CRT compare APIs do not control the visible validation route

## Confirmed Dynamic Constraints

- Classic debugger attach contaminates execution
- Frida-style aggressive instrumentation was not reliable for this sample
- thread suspension plus `GetThreadContext` is itself intrusive enough to drive some runs into `Detected.`
- launching normally and injecting through `CONIN$` remains the cleanest reproducible workflow

## Confirmed Reezli Clue Facts

The clue file on the Desktop is now treated as a high-value source because several parts were validated directly:

- `SetConsoleTitleA("crackme | reezli.vc")` was captured live
- `Detected.` was recovered from the actual `NtWriteFile` buffer
- fake strings are indeed initialized as decoys before the prompt
- the protected block after the title is real and reachable

The PBKDF2 claim is still unresolved:
- direct visible traps on `BCryptOpenAlgorithmProvider`, `BCryptDeriveKeyPBKDF2`, and `BCryptCloseAlgorithmProvider` did not fire under the current workflow
- this is not treated as a disproof yet, only as a capture limitation

## Confirmed Early Path Anchors

After correcting the static base to `0x140000000`, the following early anchors are now solid:

- return site around `0x2d20094`
- containing function range `0x2d1ffe6..0x2d2095d`
- chained internal callees observed live:
  - `0x210efe7`
  - `0x26f3352`
- the path later enters the larger protected region `0x2310f49..0x2d1e00e`

## Confirmed Historical Late-State Facts

These remain true as historical context, but they are no longer the main intended route:

- prompt side hotspots:
  - `0x55d9c83`
  - `0x55d9c1c`
  - `0x5c68c01`
  - `0x5d24729`
  - `0x5d2473f`
- post-validation hotspots:
  - `0x2cf67df`
  - `0x236fe1a`
  - `0x23e05cd`
- later convergence:
  - `0x27dd114`
  - `0x2802257`
- root selector recovered above late `ESI`:
  - `test r10w, 0x71ab`
  - `sete r8b`
  - `add r8d, r8d`
  - `call 0x1468d67b5`
- late gate:
  - `0x1468d67f8: neg esi`
  - `0x1468d67fa: jne 0x1461ec902`

## Confirmed Trap Classification

- `bruh` is a trap presentation, not a success path
- neutralizing `NtRaiseHardError` exposed the underlying trap result `0xDEADC0DE`
- later bypass work showed `xabort 0xDC` and a late trampoline family beyond that trap
- this line remains useful as fallback bypass knowledge, but it is now secondary to password recovery

## Current Working Hypothesis

The strongest current hypothesis is:
- Reezli's `main` outline is materially correct
- the real password check still sits behind the early title-to-prompt path
- the remaining challenge is extracting that path with less intrusive observation, not rediscovering the whole binary from scratch
