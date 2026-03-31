# Findings

## Confirmed Runtime Facts

- The active visible validation route is not driven by `strcmp`, `memcmp`, `strncmp`, `wcscmp`, or the obvious `bcrypt.dll` exports.
- Debugger attachment contaminates execution and can trigger alternate behavior or detection.
- The crackme can be driven reproducibly without a debugger by launching it in a real console and writing keyboard events into `CONIN$`.
- The prompt-side active range is approximately `0x1455da9fd..0x145fe7abc`.
- The post-validation active range is approximately `0x142310f49..0x142d1e00e`.
- `FUN_1455d8b6f` is a real decoder/decompression component in the prompt-side path.

## Confirmed Hotspot Chains

### Prompt Side

Observed repeatedly in clean runs:

- `0x55d9c83`
- `0x55d9c1c`
- `0x5c68c01`
- `0x5d24729`
- `0x5d2473f`

### Post-Validation Side

Observed repeatedly in clean runs:

- `0x2cf67df`
- `0x236fe1a`
- `0x23e05cd`

### Later Convergence

Observed repeatedly in the same validation network:

- `0x27dd114`
- `0x2802257`

## Register-State Findings

Stable or semi-stable in the post-validation path:

- `RCX = 0x3791ca2a`
- `RDX = 0x20000`
- `RDI` behaves like a persistent state/table pointer
- `R8` behaves like a persistent support pointer/table

Most input-dependent:

- `RAX`
- `RBX`
- `RSI`

Interpretation:

- the crackme is carrying a derived late-stage state,
- not simply comparing the input to a plaintext constant.

## RBX Behavior

`RBX` changes strongly even for very similar inputs.

This was confirmed with clustered traces such as:

- `aaaa / aaab / aaac / aaad`
- `aaaa / aaaab / aaaac / aaaad`

The differences do not look like a tiny incremental counter or shallow state machine. `RBX` looks like a heavily mixed late-stage state, close to a digest or strongly transformed result.

## Late-Stage Control Network

The strongest confirmed late chain is:

- `0x1475ba2e2`
- `0x1475b9460`
- `0x1475b9494`
- `0x1475a3b17`
- `0x145034f48`

Important notes:

- `cmp ebx, 1` appears in this region and is meaningful, but patching it alone does not unlock the sample.
- Forcing `0x1475b9494 -> 0x1475a3b17` materially changes the convergence profile and is therefore a valid late-stage branch.

## Strongest Late Gate Found So Far

Current best candidate split:

- `0x1468d67f8: neg esi`
- `0x1468d67fa: jne 0x1461ec902`

This branch is later and more useful than the earlier `cmp ebx, 1` patch point.

## Patch Results

### Crude Prompt-Side Patches

- NOPing the call at `0x57faee8` changes control flow but crashes with `0xC0000005`.
- Replacing `FUN_145c13f7e` with `ret` also crashes.
- Skipping `0x5d2473f` naively breaks execution.

Conclusion: prompt-side blunt patches are not stable.

### Late Triple-Patch Variant A

- `0x5b9494 -> e9 7e f6 fe ff`
- `0x34f63 -> e9 04 53 1c 01 90`
- `0x18d67fa -> 90 90 90 90 90`

Observed effect:

- for some inputs, the classic reject-chain disappeared from sampled hotspots,
- but the behavior was not universal,
- and this did not expose a clean global success path.

### Late Triple-Patch Variant B

- `0x5b9494 -> e9 7e f6 fe ff`
- `0x34f63 -> e9 04 53 1c 01 90`
- `0x18d67f8 -> 31 f6 90`

Observed effect:

- `test`: reject-chain disappeared; only prompt-side remained.
- `aaaa`: reject-chain disappeared; process exited with `0xdeadc0de`.
- `auth_login_success`: reject-chain still reappeared.

Interpretation:

- the `ESI`-based late split is real,
- the fallthrough side is not a universal success path,
- at least one trap or exceptional branch exists in this area.

## GUI Path Findings

- A new GUI dialog with text `bruh` appeared during some late-stage patch experiments.
- `USER32.dll` is loaded in those runs.
- The unpacked module dump contains `MessageBoxA` and `USER32.dll` markers.
- The string `bruh` itself was not found plainly in the dumped module image.

Interpretation:

- the popup is a real alternate branch,
- but not yet useful as the main solve direction,
- and not currently treated as the real success path.

## Explicitly Discarded Or Downgraded Leads

- `.pwdprot` as the direct password source for the active path
- `FUN_1455da550` as the decisive active comparator
- nearby visible strings as direct password candidates
- standard compare APIs as the acceptance gate
- common `bcrypt.dll` exports as the visible live validator
- `0x1477dd120` as the final success/reject split
- `0x14785312b` as the final success/reject split
- `cmp ebx, 1` as a standalone terminal gate
- the `bruh` popup as the main success lead

## Current Solve Posture

- Bypass is closer than exact-password recovery.
- The problem is no longer broad exploration; it is a late-stage state and dispatch problem.
- The highest-value remaining work is around the late ESI-based split and the exact branch/handler that separates stable acceptance from rejection or trap paths.
