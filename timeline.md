# Timeline

## 1. Initial Verification

The project started from an already-opened Ghidra session and inherited notes. The first task was to confirm the real sample and separate confirmed facts from prior assumptions.

The sample was later hash-verified against the public challenge values, confirming that the active file was the intended target.

## 2. Early Static Leads Eliminated

The first hypotheses focused on the most obvious surfaces:

- `.pwdprot`
- `FUN_1455da550`
- visible auth-related strings
- standard compare APIs
- the exposed `bcrypt.dll` import surface

These were all plausible enough to test, but none of them explained the actual visible validation path.

## 3. Debugger Contamination Confirmed

Debugger-oriented tests visibly altered the program's behavior. The user also observed detection-like windows during those runs, which matched the anti-debug hypothesis.

That forced a strategic pivot:

- stop using a classic debugger for the main path
- drive the sample through a normal console
- observe it indirectly through thread context, memory reads, and focused runtime patching

## 4. Clean Console Instrumentation Built

A no-debugger runtime workflow was built around:

- `CreateProcessW(..., CREATE_NEW_CONSOLE)`
- `AttachConsole`
- `CONIN$`
- `WriteConsoleInputW`
- `SuspendThread`
- `GetThreadContext`

This made it possible to launch the crackme cleanly, inject selected inputs, and recover reproducible runtime chains.

## 5. Prompt-Side Path Recovered

The first clean prompt-side sequence emerged:

- `0x55d9c83`
- `0x55d9c1c`
- `0x5c68c01`
- `0x5d24729`
- `0x5d2473f`

Work in this region also confirmed that `FUN_1455d8b6f` is a genuine decoder / decompressor in the live path.

## 6. Post-Validation Path Recovered

After input submission through a real console, a stable post-validation chain was recovered:

- `0x2cf67df`
- `0x236fe1a`
- `0x23e05cd`

This narrowed the problem from broad exploration to a reproducible live validation route.

## 7. Register-State Analysis

Captures at the post-validation hotspots showed:

- stable `RCX` and `RDX`
- stable-looking `RDI` and `R8`
- strongly input-dependent `RAX`, `RBX`, and `RSI`

That supported the idea that the crackme validates through derived internal state rather than a plaintext compare buffer.

## 8. Later Convergence Located

Following the post-validation path deeper uncovered a later convergence pair:

- `0x27dd114`
- `0x2802257`

At this stage the process also exhibited two collapsed result families before entering system code:

- `RAX = 0x28`, `RBX = 0`
- `RAX = 0x2a`, `RBX = 1`

This made `RBX` a useful late-state signal.

## 9. Batch Tracing Introduced

Manual tracing became too slow, so `crackme_batch_trace.py` was created to automate:

- process launch
- input injection
- patch application
- hotspot sampling
- JSON output for differential comparison

Clustered inputs such as `aaaa / aaab / aaac / aaad` showed that `RBX` changed strongly and diffusely, which looked more like a late mixed state or digest than a tiny state machine.

## 10. Several Late Branches Discarded

Multiple branches that looked terminal were tested and ruled out as standalone answers, including:

- `0x1477dd120`
- `0x14785312b`
- isolated `cmp ebx, 1`

They influenced execution, but none opened the visible success path.

## 11. Stronger Late Chain Recovered

The strongest surviving late network became:

- `0x1475ba2e2`
- `0x1475b9460`
- `0x1475b9494`
- `0x1475a3b17`
- `0x145034f48`

Forcing `0x1475b9494 -> 0x1475a3b17` changed convergence significantly, proving that this region is genuinely late and meaningful.

## 12. Discovery Of The ESI Gate

The next major improvement was a stronger late split:

- `0x1468d67f8: neg esi`
- `0x1468d67fa: jne 0x1461ec902`

This branch was later, more stateful, and more responsive than earlier leads.

## 13. Triple-Patch Experiments

The strongest early patch family around this gate became:

- `0x5b9494 -> e9 7e f6 fe ff`
- `0x34f63 -> e9 04 53 1c 01 90`
- `0x18d67fa -> 90 90 90 90 90`

This did not solve the crackme, but it proved that the analysis had reached a meaningful late split because the known reject loop disappeared for some inputs.

## 14. GUI Divergence: `bruh`

Some late-stage patch combinations started producing a GUI dialog showing `bruh`. That route was clearly not the ordinary reject path, but it also did not look like a clean success path.

Later probing showed that:

- the dialog is a modal `#32770`
- title is `crackme.exe`
- the actual text lives in a child `Static` control with value `bruh`

This downgraded `bruh` from a possible success clue to a likely exceptional or trap path.

## 15. Cleaner ESI Forcing

Instead of simply NOPing the late branch, a cleaner patch forced `ESI = 0` immediately before `neg esi`:

- `0x18d67f8 -> 31 f6 90`

combined with:

- `0x5b9494 -> e9 7e f6 fe ff`
- `0x34f63 -> e9 04 53 1c 01 90`

This improved behavior materially:

- some inputs left the reject loop entirely
- one representative case landed in `0xDEADC0DE`

That showed the late split was real, while proving that its fallthrough side was not a universal success path.

## 16. Selector Root Moved Upward

Static work on runtime-materialized code showed that the `ESI` gate was not the root decision point. A smaller selector just above it builds `R8` from `R10`:

- `test r10w, 0x71ab`
- `sete r8b`
- `add r8d, r8d`
- `call 0x1468d67b5`

This shifted the model:

- `R10` is upstream state
- `R8` is derived selector output
- `ESI` is a later normalization layer

## 17. Multi-Thread Tracing

`crackme_allthread_trace.py` was added after it became clear that post-input work was not confined to the original main thread.

That confirmed:

- the crackme spawns multiple workers
- some interesting paths only show up under all-thread sampling
- several earlier visibility problems were tracer limitations rather than path disappearance

## 18. Selector Space Reduced

A useful static observation followed:

- `shr r10d, 0x5d` effectively means `shr r10d, 29`

This reduces the selector immediately before `test r10w, 0x71ab` to only:

- `R10D = 0..7`

## 19. R10 Sweeps

`crackme_r10_sweep.py` and `crackme_r10_window_sweep.py` were created to sweep those selector states, especially when patches were applied after input to avoid corrupting initialization.

Results:

- many forced `R10D` values suppressed known reject hotspots
- none produced clean visible success
- several landed in wait/park states in `ntdll`

This established that forcing the selector alone is not enough; the sample cares about coherent late state.

## 20. Anti-Debug Baseline Neutralized

`crackme_api_guard_probe.py` was expanded and fixed to patch:

- `CheckRemoteDebuggerPresent`
- `IsDebuggerPresent`
- `FindWindowW`

Once the 64-bit `ctypes` handling was corrected, these patches applied successfully. The result was clear:

- basic anti-debug was real
- but neutralizing it alone did not alter acceptance behavior

## 21. Initialization Error Classified

The `Initialization error 2` screenshot and follow-up tests showed that this path appears when selector patches are applied too early.

When equivalent selector patches are delayed until after input:

- `Initialization error 2` disappears

This is currently treated as a bad initialization / integrity side-effect, not as the main anti-debug route.

## 22. Hard-Error Trap Classified

The `bruh` route was then pushed further by neutralizing `NtRaiseHardError`.

That caused the popup to disappear and exposed the true underlying result:

- `exit code = 0xDEADC0DE`

This was an important classification step:

- `bruh` is only the visible hard-error wrapper
- `0xDEADC0DE` is the trap result underneath

## 23. Termination Neutralization

To see what happens beyond the trap, the project neutralized:

- `NtRaiseHardError`
- `NtTerminateProcess`
- `RtlExitUserProcess`

When combined with an early trap-producing selector patch, the process:

- no longer died immediately
- stayed alive
- changed its console title to `crackme | reezli.vc`

This is not yet a clean bypass, but it is the clearest classified non-reject, non-popup live state found so far.

## 24. Current Position

The project is now concentrated around:

- coherent production of late state, especially upstream of `R10`
- conversion of the known `0xDEADC0DE` trap route into a stable non-trap route
- analysis of the live `crackme | reezli.vc` state

The crackme remains unresolved, but the search space has collapsed from the whole module to a small late-state selector and its trap-handling logic.

## 25. Local Exit Family Compressed Further

Additional profiling and branch forcing reduced the active trap family to a repeated local decoder/exit pattern around:

- `0x55d9f55`
- `0x55d9f67`
- `0x55d8fee`
- `0x55d8ff4`
- `0x55d9122`
- `0x55d90d7`

The important insight here was that the trap was not controlled by one isolated branch. Multiple homologous loops feed the same terminal trap behavior.

## 26. Spin-Capture Tool Added

`crackme_spin_gate_capture.py` was added to freeze execution at narrow RVAs and dump live registers without using a classic debugger.

This produced direct captures at:

- `0x55d9f55`
- `0x55d9122`
- `0x55d90d7`

and showed that the local exit family carries real state through:

- `R8D`
- `R9`
- `R13`
- `R10D`
- `R14`

## 27. Stronger Local Exit Rewrites

A stronger local patch family was tested:

- `0x55d9f55 -> 45 31 c0 90 90 90 90`
- `0x55d9f67 -> 4d 39 ed`
- `0x55d8fee -> 90 90 90 90 90 90`
- `0x55d8ff4 -> 4d 39 ed`

This did not solve the crackme, but it materially improved classification:

- the ordinary `DEADC0DE` route could be displaced
- the next visible outcome became `0x80000003`

That proved the project had moved one layer deeper into the trap chain.

## 28. WinDbg And Local Dumps Added

To stop guessing about the new `0x80000003` path, Windows Error Reporting LocalDumps were configured and WinDbg was installed.

This created a non-attach workflow for inspecting the actual terminal exception path.

## 29. Exact `DEADC0DE` Exit Caller Recovered

The first useful dump showed that the `0x80000003` route still reaches:

- `kernel32!ExitProcessImplementation+0x10`

with:

- `RCX = 0xDEADC0DE`

and that the immediate crackme-side caller is:

- `crackme+0x5a3628a`

This was the first exact crackme-side call site tying the trap to a concrete exit path.

## 30. Skipping The Exact Exit Call Was Tested

NOPing the exact `call rax` at `crackme+0x5a3628a` removed the immediate `DEADC0DE` termination, but the process then crashed with:

- `0xC0000005`
- execute at null

This clarified the trap structure:

- the explicit exit call is real and terminal
- but it is not the right bypass point
- the stable bypass must divert before the trap is fully assembled

## 31. `xabort` Was Converted Into A Real Return

The first major breakthrough after the old trap line came from treating `crackme+0x1e0ae4c` as a sink, not a decision point.

Late patch:

- `0x1e0ae4c -> ret`

This alone did not solve the sample, but it changed the nature of the failure and proved the analysis had moved past the original `xabort 0xDC` instruction.

## 32. Stack Repair Above The Sink

Dump inspection showed that the exception stack was not shaped for a direct return. The next slot above the sink was:

- `crackme+0x1203bb4`

followed by:

- a scratch qword
- then a plausible continuation in the module

That led to the first stack-aware repair:

- `0x1203bb4 -> add rsp, 8 ; ret`

With:

- `0x1e0ae4c -> ret`
- `0x1203bb4 -> add rsp, 8 ; ret`

the process no longer died in `C000001D`. The new crash moved forward to:

- `crackme+0x5a6c54a`

This was the clearest sign yet that the bypass path was being unwound, not just suppressed.

## 33. Late Read Neutralization

The new crash at `crackme+0x5a6c54a` came from:

- `mov cx, word ptr [rbx]`

inside a late materialized block.

That read was patched to:

- `xor cx, cx ; nop`

The new result was not success, but another forward move in the chain:

- AV at wild RIP `0x800000023`

This showed that the bad read had been real and that execution had reached a later indirect target.

## 34. First Trampoline Return

The `0x800000023` case produced another useful dump. The stack and surrounding state pointed into:

- `crackme+0x55efa2`

This location sat inside another late stub. Replacing it with:

- `ret`

did not solve the sample but advanced the chain again.

## 35. Second Trampoline Return

The next useful continuation came from:

- `crackme+0x5898a23`

Replacing that stub with:

- `ret`

again shifted the failure forward instead of collapsing back into the old trap route.

## 36. Stack Repair Repeats In The Chain

The next dump showed another stack pattern matching the previous repair shape:

- a continuation-like module address
- a scratch qword
- then another plausible module continuation

That led to another stack-aware patch:

- `0x55da697 -> add rsp, 8 ; ret`

This is the point where the strategy became clear: the late anti-tamper system behaves as a chain of trampolines and stack fixups, not as a single branch gate.

## 37. Latest Front Line

After the trampoline sequence:

- `0x1e0ae4c -> ret`
- `0x1203bb4 -> add rsp, 8 ; ret`
- `0x5a6c54a -> xor cx, cx ; nop`
- `0x55efa2 -> ret`
- `0x5898a23 -> ret`
- `0x55da697 -> add rsp, 8 ; ret`

the crash now lands back inside the crackme module at:

- `crackme+0x446f267`

This is the strongest current result:

- the old `DEADC0DE` route is no longer the front line
- `xabort` is no longer the front line
- the problem is now a deeper late trampoline chain that can be unwound step by step
