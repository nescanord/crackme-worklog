# Detailed Timeline

## 1. Initial Context And Triage

The project started from an already opened Ghidra session and prior notes indicating that the target was a Windows x64 console crackme with local-only validation and an author clue about cryptographic key derivation. The initial task was to verify the context against the actual sample rather than trust prior assumptions.

Early checks confirmed:

- The binary was the expected `crackme.exe`.
- The sample was loaded in Ghidra.
- Supporting artifacts such as live dumps and region maps already existed.

The first phase focused on verifying whether any of the earlier hypotheses were grounded in the actual active path.

## 2. Early Hypotheses That Failed

Several plausible explanations were tested and eliminated:

- The `.pwdprot` section did not directly explain the active password path.
- `FUN_1455da550`, while interesting and compare-like, was not the decisive validator for the visible console route.
- Direct token guesses from nearby strings such as `auth_login_success` did not unlock the sample.
- Standard compare APIs and obvious `bcrypt.dll` surfaces were not the real active route.

This was the first sign that the crackme was deliberately structured to waste time on believable but secondary logic.

## 3. Anti-Debug Evidence And Strategy Change

Initial debugger-oriented tests changed program behavior and led to detection. The user also reported visible warnings during those experiments, which matched the anti-debug hypothesis.

That forced a strategic pivot:

- Stop relying on a traditional debugger for the main runtime path.
- Drive the sample through a normal console session.
- Observe it indirectly through thread context, memory reads, and module inspection.

This was the most important methodology change in the whole project.

## 4. Ghidra/MCP Stabilization And Mixed Workflow

The Ghidra MCP bridge was usable but inconsistent on heavy functions and some larger queries. Timeout adjustments improved decompilation reliability, but the project still needed a mixed workflow:

- use Ghidra for focused static pivots,
- use runtime dumps for raw disassembly and byte confirmation,
- use custom Python tooling for dynamic observation.

This combination ended up outperforming either Ghidra-only or debugger-only approaches.

## 5. Real Console Instrumentation

The next stage was to reproduce the visible console path without debugger attachment.

A runtime workflow was built around:

- `CreateProcessW(..., CREATE_NEW_CONSOLE)`
- attaching to the process console,
- writing keystrokes into `CONIN$`,
- suspending the main thread,
- sampling `GetThreadContext` and selected memory.

This immediately produced cleaner results than pipe-based input or debugger-driven stepping.

## 6. Prompt-Side Path Recovery

With the clean console workflow in place, the first reproducible prompt-side sequence emerged:

- `0x55d9c83`
- `0x55d9c1c`
- `0x5c68c01`
- `0x5d24729`

At the same time, `FUN_1455d8b6f` was identified as a real range-decoder / decompression component in the prompt path. This established that the crackme reconstructs or decodes meaningful code/data at runtime.

The prompt-side hotspot around `0x57faee8` was then identified as a real transition point. NOPing its call altered control flow, confirming its importance, but the patch crashed the process, so this was not a clean bypass point.

## 7. Post-Validation Chain Recovery

Once input was fed cleanly, the main thread repeatedly entered a stable post-validation chain:

- `0x2cf67df`
- `0x236fe1a`
- `0x23e05cd`

This changed the shape of the problem. The project no longer depended on guesswork about imports or string references; it had a live chain to follow.

## 8. Register-State Analysis

Captures at `0x236fe1a` and `0x23e05cd` revealed a useful split between stable and input-dependent state.

Stable:

- `RCX = 0x3791ca2a`
- `RDX = 0x20000`
- `RDI`
- `R8`

Input-dependent:

- `RAX`
- `RBX`
- `RSI`

This strongly suggested that the crackme was operating over a derived state object or VM state rather than comparing plaintext buffers.

## 9. Late Convergence Discovery

Further along the same path, repeated execution converged on:

- `0x27dd114`
- `0x2802257`

These points were important because they sat later than the first visible validation loop and still responded to input-dependent state. At this stage, the project also observed two collapsed result families before handoff toward `ntdll.dll`:

- `RAX=0x28`, `RBX=0`
- `RAX=0x2a`, `RBX=1`

This made `RBX` a central late-stage signal worth tracking.

## 10. Batch Tracing

Manual inspection was too slow once the late-state space became narrow. To accelerate, `crackme_batch_trace.py` was created.

That script made it possible to:

- run multiple test inputs in sequence,
- patch specific RVAs in memory,
- sample only selected hotspots,
- compare state across input clusters.

The first important result of batch tracing was that `RBX` changed strongly even for near-identical inputs, which argued against a tiny incremental state machine and in favor of a heavily mixed late-stage state.

## 11. Late-Branch Elimination

The next phase focused on late branches that looked terminal.

Several candidates were tested and then discarded:

- `0x1477dd120`
- `0x14785312b`
- isolated `cmp ebx, 1`

Each of these altered local execution, but none produced a clean visible acceptance path.

## 12. Late-Stage Chain Narrowed

The remaining strong chain became:

- `0x1475ba2e2`
- `0x1475b9460`
- `0x1475b9494`
- `0x1475a3b17`
- `0x145034f48`

Forcing `0x1475b9494 -> 0x1475a3b17` changed convergence more than previous patches, proving this part of the network was genuinely late and significant.

## 13. Discovery Of The `neg esi` / `jne` Gate

The next decisive improvement came from disassembling and testing the block around:

- `0x1468d67f8: neg esi`
- `0x1468d67fa: jne 0x1461ec902`

This branch was more meaningful than earlier candidates because:

- it sits late,
- it depends on derived state,
- and changing it materially alters whether the sample keeps visiting the classic rejection loop.

## 14. Triple Patch Experiments

A strong patch family was assembled:

- `0x5b9494 -> e9 7e f6 fe ff`
- `0x34f63 -> e9 04 53 1c 01 90`
- `0x18d67fa -> 90 90 90 90 90`

This did not solve the crackme, but it proved that the analysis had reached a real late gate. Under some inputs the classic reject-chain disappeared from the sampled execution profile.

## 15. GUI Divergence And The `bruh` Popup

At this stage a new output began to appear: a GUI dialog displaying `bruh`.

This mattered because it proved the late-stage patches were reaching a path other than the normal `Wrong.` route. A popup probe was written to automate this, and runtime checks confirmed that GUI-related modules such as `USER32.dll` were indeed loaded in those runs.

However, the popup was not stable enough to serve as the main lead, and it did not look like a clean success path. It was therefore treated as an alternate or exceptional branch rather than the main solve direction.

## 16. Cleaner ESI Forcing

To avoid brute NOPing the late conditional branch, a cleaner test was run by forcing `ESI = 0` immediately before `neg esi`:

- `0x18d67f8 -> 31 f6 90`

combined with:

- `0x5b9494 -> e9 7e f6 fe ff`
- `0x34f63 -> e9 04 53 1c 01 90`

This produced the best late result so far:

- `test`: reject-chain disappeared and only prompt-side execution remained.
- `aaaa`: reject-chain disappeared, but the process ended at `0xdeadc0de`, indicating a trap or exceptional termination.
- `auth_login_success`: reject-chain still reappeared.

This established that the late ESI-based split is real, but neither side of it has yet been reduced to a universal success path.

## 17. Current State

The project is now far removed from generic exploration. The active unknowns are concentrated in a small late-state network.

Most likely solve order from the current position:

1. Derive a stable bypass from the late-state gate.
2. Use that stabilized route to recover the exact password if needed.
