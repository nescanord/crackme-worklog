# Timeline

## Initial Triage

- Confirmed the crackme is a Windows x64 console target with local-only validation.
- Located the binary, live dumps, region maps, and the Ghidra project context.

## Wrong Assumptions Eliminated

- `.pwdprot` was checked and did not explain the active path.
- `FUN_1455da550` looked important early because it resembles a compare routine, but later testing showed it is not the decisive active console check.
- Standard compares and common CNG hashing exports were probed and did not drive the real visible validation route.

## Anti-Debug Shift

- Traditional debugger attachment and breakpoints triggered detection or altered behavior.
- User-observed alert windows matched debugger-based experiments.
- The workflow shifted to non-debugger observation and runtime patching.

## Ghidra And MCP Stabilization

- The Ghidra bridge timeout was increased so heavy decompiles became more usable.
- MCP remained unstable on some large functions and string queries, so the analysis started mixing:
  - Ghidra spot decompilation
  - raw-byte inspection from live dumps
  - process-memory scripting

## Real Console Route Established

- The crackme was launched in a real console.
- Input was injected through `CONIN$` instead of relying only on piped stdin.
- This gave a reproducible, debugger-free way to trigger the true visible validation path.

## First Strong Narrowing

- Main-thread RIP sampling before and after wrong-password input revealed two active regions:
  - prompt-side: `0x1455da9fd..0x145fe7abc`
  - post-validation: `0x142310f49..0x142d1e00e`
- `FUN_1455d8b6f` was confirmed as a real range-decoder / decompression routine in the prompt-side live path.

## Prompt-Side Control Point

- Hotspot `0x57faee8` was identified as a key prompt-side transition point.
- NOPing the call at that hotspot changed control flow, proving it was live.
- However, the crude patch crashed the process, so the point is real but not yet directly bypassable.

## Live Execution Chain Recovered

Using the restored `crackme.exe` from the Desktop, the clean no-debugger runtime chain was sampled again and refined.

Prompt-side sequence:

- `0x55d9c83`
- `0x55d9c1c`
- `0x5c68c01`
- `0x5d24729`

Post-validation sequence:

- `0x2cf67df`
- `0x236fe1a`
- `0x23e05cd`

This is the clearest execution path recovered so far.

## Prompt-Side Patch Experiments

- NOP on the call at `0x57faee8`
  - flow changes
  - process crashes with `0xC0000005`
- `ret` patch on `FUN_145c13f7e`
  - also crashes
- replacing the call at `0x5d2473f` with a stack-preserving `add rsp, 8; nop`
  - still crashes

Conclusion:

- the prompt-side helpers are structurally important
- removing them crudely is not enough

## Post-Validation Branch Experiment

- Raw bytes around `0x2cf67df` exposed a conditional branch at the head of the block.
- NOPing that conditional branch produced a real control-flow diversion without immediate crash.
- With that patch:
  - execution no longer went straight into the usual `0x236fe1a` path
  - it briefly returned to prompt-side offsets near `0x55d8ff7`
  - it later still reached rejection-side territory

This made `0x2cf67df` one of the best current branch candidates for a future clean bypass.

## Register-State Capture Phase

- Stable no-debugger captures were collected at `0x236fe1a` and `0x23e05cd`.
- `RCX = 0x3791ca2a`, `RDX = 0x20000`, `RDI`, and `R8` remained stable.
- `RAX`, `RBX`, and `RSI` changed with the tested input strings.
- This shifted the analysis from API hunting to state tracking inside the VM handlers.

## Local Disassembly Phase

- Capstone was installed locally so hotspot bytes could be disassembled directly from `mod_after.bin`.
- The real handler pattern was confirmed around:
  - `0x14736fe1a`
  - `0x1473e05cd`
  - `0x147cf67df`
  - `0x14755ce70`
  - `0x1474c3aa1`
- A duplicated handler template containing the same `xor esi, 0xe7a90182` sequence was found elsewhere in the unpacked code.

## Late Convergence Narrowing

- The later convergence pair `0x27dd114` and `0x2802257` was confirmed as part of the same validation network.
- The crackme-side VM collapses into two stable state families before dropping into `ntdll.dll`:
  - `RAX=0x28`, `RBX=0`
  - `RAX=0x2a`, `RBX=1`
- `0x14755c736` was identified as a direct caller into `0x147802244`.
- The branch at `0x1477dd120` looked promising but forcing or skipping it did not stop convergence through `0x27dd114 / 0x2802257`.
- The next branch at `0x14785312b` also looked terminal at first, but forcing or skipping it likewise failed to produce a clean bypass.

## Current Posture

- The password has not been recovered yet.
- The route to a bypass is still narrow, but the terminal split appears deeper than the first two late-stage branch candidates.
- The strongest current chain is:
  - `0x1477aa994`
  - `0x14755c714`
  - `0x147802244`
  - `0x147901c6c`
  - `0x1475e525a`
- The next branch to test is `0x1475e525f` and its target `0x1475ba298`.
