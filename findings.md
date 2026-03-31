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
- The active post-input path remains inside a single crackme thread in the `0x55d8xxx-0x55d9xxx` range for at least `2s`.

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

## Local Exit-Gate Findings

Recent spin-capture and local branch work narrowed the trap family further.

Live captures at:

- `0x55d9f55`
- `0x55d9122`
- `0x55d90d7`

showed that the trap route is not random at this stage; it carries concrete state through:

- `R8D`
- `R9`
- `R13`
- `R10D`
- `R14`

Key observations:

- under the strongest local patch family, `0x55d9f55` converges to the same state across multiple inputs
- the practical local bypass condition is not "guess the password here"
- it is "force a coherent decoder/exit state"

The strongest local patch family currently under study is:

- `0x55d9f55 -> 45 31 c0 90 90 90 90`
- `0x55d9f67 -> 4d 39 ed`
- `0x55d8fee -> 90 90 90 90 90 90`
- `0x55d8ff4 -> 4d 39 ed`

Interpretation:

- there are multiple homologous local decoder/exit loops
- patching only one loop is not enough
- the trap is being reached through a repeated family, not a single isolated branch

## Dump-Based Trap Confirmation

Windows Error Reporting local dumps and WinDbg were added to the workflow.

This produced two useful ground truths:

1. The `0x80000003` route under termination suppression is not the main secret path.
   It comes from a trap family that eventually reaches:
   - `kernel32!ExitProcessImplementation+0x10`
   - with `RCX = 0xDEADC0DE`

2. The concrete crackme-side caller identified from the dump is:
   - `crackme+0x5a3628a`

Meaning:

- the sample really does call an exit path with `DEADC0DE`
- this is not merely a UI artifact from the `bruh` popup
- the trap has now been tied to an exact crackme-side call site

## Post-Exit-Call Finding

Skipping the exact `call rax` at `crackme+0x5a3628a` does not solve the crackme.

What it does:

- removes the immediate `DEADC0DE` termination path
- reveals a later `0xC0000005` execute-at-null crash

Interpretation:

- the explicit exit call is real and terminal
- but it sits at the end of a trap path, not at a clean bypass point
- any stable bypass needs to divert before that terminal exit is prepared

## Pre-Exit Branch Finding

The obvious branch immediately before the terminal call:

- `crackme+0x5a3627f`

does materialize in runtime with the expected original bytes:

- `0f 85 d0 f6 ea ff ...`

That rules out the easy explanation that this region is simply absent or rewritten away before execution.

Current interpretation:

- the pre-exit branch exists and is live
- but patching it alone does not dislodge the process from the same terminal caller
- so it is not, by itself, the final select bit for acceptance vs trap

## Password-Recovery Findings

### Decoder semantics

- `FUN_1455d8b6f` is confirmed as a range-decoder / LZMA-like routine.
- Saved arguments recovered from live dumps show:
  - `param_2 = crackme.exe + 0x2d958c5`
  - `param_5 = crackme.exe + 0x11ec000`
- `param_2` is constant across different passwords.
- `param_5` is constant across different passwords.
- The full decoded output region at `crackme.exe + 0x11ec000` is byte-for-byte identical across different passwords.

Interpretation:

- the password does not change the compressed payload
- the password does not change the decoded output blob
- therefore the decoder itself is not the password check

### Decoder out-params

- The saved `param_4` / `param_7` out-params do not hold a password buffer or digest.
- In live dumps they resolve to metadata that includes:
  - `KnownDlls\\ntdll.dll`

Interpretation:

- these outputs belong to a generic runtime subsystem
- they are not the KDF result

### Input-dependent state

- The value that changes with the password is `param_3`.
- Live samples have shown `param_3` values such as:
  - `0x28`
  - `0x30`
  - `0x34`
  - `0x48`
  - `0x5c`

Interpretation:

- the password changes caller state fed into the decoder
- the best current target is the caller that constructs `param_3`

### SHA256 runtime table downgraded

- The runtime-only `salt(16) + digest(32) + UTF-16 "SHA256" + keyauth_*` table is still present in memory.
- It remains useful as a historical clue, but it is now downgraded as the main password hypothesis.
- A focused `PBKDF2-HMAC-SHA256` sweep over strong runtime candidates, with:
  - `ascii`
  - `utf16le`
  - iterations `1..2000`
  produced `0` hits against the embedded 32-byte digest.

Interpretation:

- the obvious `SHA256` table is very likely a decoy or startup/runtime metadata
- the intended password path is elsewhere

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

## Latest Trap Compression

Recent all-thread tracing and RVA profiling compressed the trap analysis further.

For the `0xDEADC0DE` trap family, useful hits and hot RVAs concentrate around:

- `0x55d904a`
- `0x55d9057`
- `0x55d913c`

For the `0x80000003` trap family, useful hits and hot RVAs concentrate around:

- `0x55d90ee`
- `0x55d9107`
- `0x55d912e`

Interpretation:

- both trap outcomes belong to the same local prompt/decoder family
- the important divergence is now inside the narrowed `0x55d90xx` window
- this is currently a better choke region than the broader VM network above it

## Trampoline Unwinding Findings

The newest productive line is not a single branch patch. It is a stack-aware unwinding of late anti-tamper trampolines.

The critical discovery came from dump stack shape on the `xabort` path:

- `crackme+0x1e0ae4c`
- `crackme+0x1203bb4`
- scratch qword
- then a plausible continuation inside the module

That made this patch coherent rather than arbitrary:

- `0x1e0ae4c -> ret`
- `0x1203bb4 -> add rsp, 8 ; ret`

Effect:

- the crash moved from `C000001D` at `xabort` to a new AV at `crackme+0x5a6c54a`

Further productive late patches:

- `0x5a6c54a -> xor cx, cx ; nop`
- `0x55efa2 -> ret`
- `0x5898a23 -> ret`
- `0x55da697 -> add rsp, 8 ; ret`

Observed progression:

1. `crackme+0x1e0ae4c = xabort 0xDC`
2. `crackme+0x5a6c54a`
3. wild target `0x800000023`
4. back into module code at `crackme+0x446f267`

Interpretation:

- the active bypass route is now a late chain of trampolines
- each dump is exposing the next stub in the chain
- this is stronger and more credible than the old idea of one final gate patch

## Current Best Choke Points

- `0x1e0ae4c`
- `0x1203bb4`
- `0x5a6c54a`
- `0x55efa2`
- `0x5898a23`
- `0x55da697`
- `0x446f267`

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
- The newest concrete choke point above the terminal trap is the crackme-side path leading into `crackme+0x5a3628a`
