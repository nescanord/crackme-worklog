# NecrumWin Reverse Engineering Worklog

Technical worklog for `NecrumWin (Reezli challenge)`, a protected Windows x64 console crackme analyzed with Ghidra, live runtime instrumentation, and no-debugger tracing.

Primary objective: recover the exact password.

Secondary objective: produce a stable acceptance bypass with the minimum possible patch footprint.

## Target Profile

- Challenge: `NecrumWin (Reezli challenge)`
- Format: native Windows console executable
- Architecture: x64
- Claimed toolchain: C++17
- Validation model: fully client-side
- Author hint: password verification uses cryptographic key derivation
- Allowed alternate solve: patch or unwrap the protection so the program accepts

## Executive Summary

This crackme does not validate the password through the obvious route exposed by imports, CRT compares, or the visible CNG surface. The real validation path is hidden behind a VM-like dispatcher and runtime-reconstructed code. Early time was spent eliminating decoys, stabilizing Ghidra/MCP usage, and replacing debugger-based tracing with a clean console-driven instrumentation workflow.

The major strategic pivot was abandoning normal debugger attachment. The sample reacts to debugging, and the user visibly saw anti-debug windows during those tests. From that point onward, the analysis switched to launching the process normally, injecting input into `CONIN$`, sampling RIP and registers from the main thread, diffing memory, and applying targeted runtime patches.

That workflow recovered a reproducible live path through the prompt side and the post-validation side. From there, the search compressed from the whole module down to a small late-stage dispatch network. The current late focus is no longer generic VM exploration, but a narrow family of handlers and branches that materially alter the rejection route.

## Current Assessment

- Overall progress estimate: `82%`
- Stable bypass probability: `74%`
- Exact-password recovery probability: `50%`

These percentages replace the earlier optimistic estimates. The late-state network is correctly localized, but the sample still rejects or deadlocks when that state is forced incoherently.

## What Was Ruled Out Early

The first stage of the project removed several plausible but wrong explanations for the visible password check:

- `.pwdprot` was inspected and did not explain the active path.
- `FUN_1455da550` looked promising because it behaved like a compare routine, but later runtime work showed it is not the decisive console-path validator.
- Standard compares such as `strcmp`, `memcmp`, `strncmp`, and `wcscmp` were tested and did not drive the real rejection path.
- Common `bcrypt.dll` exports and obvious CNG calls were probed and did not line up with the visible validation route.
- Early token strings, including nearby `auth_login_success`, were tested and did not unlock the sample.

This mattered because the crackme is noisy by design: a lot of plausible surface area exists, but much of it is decoy logic, wrappers, or protection scaffolding rather than the real acceptance gate.

## Anti-Debug Pivot

The next major discovery was behavioral contamination caused by debugging. Traditional attachment and breakpoints changed the program's behavior and triggered detection. The user also reported that visible warning windows appeared when these tests were running, which matched the anti-debug hypothesis.

At that point, the workflow changed completely:

1. Launch `crackme.exe` with a real console.
2. Avoid attaching a debugger.
3. Send password input through `CONIN$` by writing console input events.
4. Sample live state through `SuspendThread`, `GetThreadContext`, module enumeration, and targeted memory reads.
5. Use Ghidra only for focused static pivots rather than as the sole source of truth.

That shift was essential. It is the reason the later hotspot chain became reproducible without immediately falling into `Detected.` or other distorted paths.

## Tooling And Infrastructure Built During Analysis

Several helper assets were created to support repeatable runtime work.

### Scripts

- `C:\Users\nesca\Desktop\crackme_batch_trace.py`
  - Batch launcher and tracer.
  - Launches the crackme in a new console.
  - Injects text through `CONIN$`.
  - Applies in-memory patches at given RVAs.
  - Samples the main-thread RIP and registers at selected hotspots.
  - Produces JSON for multi-input comparison.

- `C:\Windows\System32\crackme_pipe_probe.py`
  - Quick probe for redirected stdio paths.
  - Confirmed that simple pipe capture was not enough to observe the real output path.

- `C:\Users\nesca\Desktop\crackme_popup_probe.py`
  - Reproduces the newer GUI-side path under the current late-stage patch set.
  - Enumerates windows owned by the process.
  - Used to determine whether the new `bruh` popup was a success clue or just an alternate exceptional path.

- `C:\Users\nesca\Desktop\crackme_allthread_trace.py`
  - Multi-thread sampler created after confirming that the post-input phase spawns several worker threads.
  - Used to prove that the classic reject path survives outside the original main-thread-only tracer.

- `C:\Users\nesca\Desktop\crackme_spin_probe.py`
  - Attempts to freeze ultra-short-lived runtime-materialized code with a self-loop patch and then dump register state.
  - Helped confirm that some selector blocks only exist in memory after startup.

- `C:\Users\nesca\Desktop\crackme_frida_gate_probe.py`
  - Frida experiment retained for completeness.
  - Downgraded after repeated empty runs (`records = []`) showed that Frida either perturbs the crackme or gets detected early.

### Supporting Artifacts

- `C:\Users\nesca\Documents\GhidraMCP\mod_after.bin`
  - Runtime module dump used for raw disassembly and byte-level verification.

- `C:\Users\nesca\Desktop\crackme_resumen_completo.txt`
  - External summary kept in parallel with the repo.

## Recovery Of The Real Runtime Path

Once the no-debugger console workflow was stable, the main thread could be sampled before and after password submission.

### Prompt-Side Region

The prompt-side active range was narrowed to approximately:

- `0x1455da9fd..0x145fe7abc`

A confirmed prompt-side sequence was repeatedly observed:

- `0x55d9c83`
- `0x55d9c1c`
- `0x5c68c01`
- `0x5d24729`

`FUN_1455d8b6f` was identified as a genuine range-decoder / decompressor in the live prompt path, confirming that runtime decoding is part of the route and that we are not just dealing with static hand-written logic.

### Post-Validation Region

The post-input execution then reliably converged on:

- `0x2cf67df`
- `0x236fe1a`
- `0x23e05cd`

This was the first high-confidence live validation chain. It turned the problem from broad exploration into state analysis.

## Register-State Observations

At `0x236fe1a` and `0x23e05cd`, several registers stayed stable across runs while others changed strongly with input.

Stable or semi-stable:

- `RCX = 0x3791ca2a`
- `RDX = 0x20000`
- `RDI` looked like a stable state object / table pointer
- `R8` also behaved like a stable table or support pointer

Input-dependent:

- `RAX`
- `RBX`
- `RSI`

This was a strong clue that the crackme was carrying a derived internal state, not a plaintext compare buffer.

## VM-Like Convergence

The next useful narrowing came from following the state after the first visible post-validation loop. Two later convergence points turned out to be real and repeatable:

- `0x27dd114`
- `0x2802257`

These nodes are not the final accept/reject instruction by themselves, but they sit later in the same network and collapse VM-side state before handing control out toward system code.

At this stage the runtime consistently showed two collapsed result families before falling into `ntdll.dll`:

- `RAX = 0x28`, `RBX = 0`
- `RAX = 0x2a`, `RBX = 1`

This was the first point where `RBX` started looking like a semantically meaningful late-stage state bit or selector.

## Differential Input Tracing

To accelerate beyond manual probing, batch traces were run with clusters of similar inputs such as:

- `aaaa`
- `aaab`
- `aaac`
- `aaad`

and later:

- `aaaa`
- `aaaab`
- `aaaac`
- `aaaad`

The key result was that `RBX` changed strongly even between near-identical inputs. The changes did not look like a small incremental state machine. They looked more like a heavily mixed state, close to a digest or final derived value.

That pushed the strategy further away from hunting strings or simple compares and deeper into late-stage branch selection.

## Late-Stage Branch Narrowing

After the convergence phase, several apparently terminal branches were tested and discarded.

Discarded as final gates:

- `0x1477dd120`
- `0x14785312b`
- `cmp ebx, 1` used in isolation

The strongest late-stage route that survived repeated testing became:

- `0x1475ba2e2`
- `0x1475b9460`
- `0x1475b9494`
- `0x1475a3b17`
- `0x145034f48`

Important consequences of this stage:

- `cmp ebx, 1` is real, but patching it alone does not open the visible success path.
- Forcing `0x1475b9494 -> 0x1475a3b17` materially changes route convergence, proving that this dispatch is late and meaningful.
- The branch-controlled path does not simply continue into a generic VM loop; it lands in a more specific target family that deserves direct attack.

## Newer Late Gate: `neg esi` / `jne`

A more promising split was then recovered around:

- `0x1468d67f8: neg esi`
- `0x1468d67fa: jne 0x1461ec902`

This is currently the strongest late branch discovered in the project.

Why it matters:

- It is state-based and explicit.
- It sits later than the earlier `cmp ebx, 1` test.
- It materially changes whether execution stays in the classic rejection loop or diverts elsewhere.

### Triple Patch Candidate

The strongest working patch family so far has been:

- `0x5b9494 -> e9 7e f6 fe ff`
- `0x34f63 -> e9 04 53 1c 01 90`
- `0x18d67fa -> 90 90 90 90 90`

This was not accepted as a final bypass, but it did prove that the analysis had reached a meaningful late split. Under some inputs the normal reject-loop hotspots disappeared from sampling.

### Cleaner Variant

A cleaner variant was then tested by setting `ESI` to zero immediately before the `neg`:

- `0x18d67f8 -> 31 f6 90`

Used together with:

- `0x5b9494 -> e9 7e f6 fe ff`
- `0x34f63 -> e9 04 53 1c 01 90`

This produced a better result than brute NOPing the conditional branch:

- For `test`, the reject-chain disappeared and only prompt-side execution remained.
- For `aaaa`, the reject-chain also disappeared, but the process ended at `0xdeadc0de`, which strongly suggests an intentional exceptional or trap path.
- For `auth_login_success`, the reject chain still reappeared.

Conclusion: the fallthrough side of the `neg esi` / `jne` split is not a clean global success path. It is either a trap, a secondary validation path, or a partially successful diversion that still depends on additional state.

## Root Selector Above `ESI`

The most important newer finding is that the `ESI` gate is not the root selector. A smaller selector just above it builds `R8` from `R10`:

- `test r10w, 0x71ab`
- `sete r8b`
- `add r8d, r8d`
- `call 0x1468d67b5`

This matters because forcing `R8` alone is too late. The callee also consumes `R10`, so a clean bypass has to preserve state coherence.

### Coherent-State Patch Tested

A stronger experiment forced the source state rather than the projection:

- `0x11fa329 -> 45 31 d2 90 90 90` (`xor r10d, r10d`)

Result:

- all known prompt/reject hotspots disappear from tracing,
- but no success path appears,
- and the process instead parks in `ntdll` wait-style code.

Conclusion:

- `R10` is definitely above the late selector,
- but `R10 = 0` is not a valid success state,
- so this patch is diagnostic only, not a final bypass.

## Semantic Candidate Sweep

High-value token-like candidates taken from the challenge and visible naming were tested directly:

- `NecrumWin`
- `Reezli`
- `reezli`
- `verify_hwid_pass`
- `keyauthh.io/register`
- `bruh`
- `KeyAuth`
- `auth_login_success`

All of them still fell into the classic rejection profile. No obvious embedded token unlocked the crackme.

## The `bruh` Dialog

A new visible output started to appear during these later patch experiments: a GUI dialog with the text `bruh`.

That observation was important, but only for classification:

- It proves the late-stage patches are reaching a path distinct from the classic `Wrong.` route.
- It does not currently look like the real success path.
- The string `bruh` was not found plainly in the unpacked module dump, although `MessageBoxA` and `USER32.dll` are present in the runtime image.

The popup was not stable enough to use as the primary lead, so it has been demoted behind the stronger late-state branch work.

## What Is Confirmed Right Now

High-confidence current statements:

- The visible password check is not driven by standard CRT compares or obvious CNG exports.
- The sample hashes match the published challenge exactly.
- The sample reacts to debugger-based analysis, so clean no-debugger instrumentation is the correct dynamic approach.
- The real runtime chain is known on both the prompt side and the post-validation side.
- `RBX` behaves like a strongly mixed late-stage validation state.
- The late `ESI`-based split around `0x1468d67f8 / 0x1468d67fa` is real, but a more root-level selector exists above it in `R10 -> R8`.
- The fallthrough side of that late split is not yet a stable success path.
- The branch target side also has not yet been reduced to a single visible success handler.
- The next highest-value target is the producer of `R10`, not more local forcing of `ESI` or `R8`.

## Open Technical Questions

The remaining unsolved questions are narrow compared to the start of the project:

1. What exact producer writes the meaningful late-stage `R10` state before `test r10w, 0x71ab`?
2. What exact condition distinguishes the clean rejection route from the stable acceptance route after the late-state network?
3. Is the final solver state encoded primarily in `RBX`, in `R10`, in flags derived from `ESI`, or in a multi-register bundle?
4. Is the exact password recoverable from the late-state network without first producing a bypassed build?
5. Is the `0xdeadc0de` path a deliberate anti-tamper trap reached by malformed late-state forcing?

## Practical Solve Outlook

At this point, the most realistic resolution order is:

1. Stable bypass.
2. Then, if needed, exact password recovery from the now-deobfuscated or stabilized path.

That ordering is not because password recovery is impossible. It is because the late-state network is already close to yielding a minimal acceptance patch, and a bypassed sample often makes the exact condition much easier to reverse afterward.
