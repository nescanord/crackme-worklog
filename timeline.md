# Timeline

## 1. Environment And Sample Verification

The project started from a Windows setup built around Ghidra, GhidraMCP, and a live imported `crackme.exe`. The sample was later hash-verified against the public challenge values, confirming that the active file is the intended `NecrumWin (Reezli challenge)` binary.

## 2. Early Static Surface

The first pass followed the normal crackme playbook:
- inspect strings
- inspect imports
- inspect sections
- inspect obvious compare and crypto surfaces

This identified many fake sections, fake signatures, and suspicious strings, but did not yield a working validation function.

## 3. Obvious Validation Surfaces Downgraded

The project then tested and downgraded the most plausible straightforward leads:
- `.pwdprot`
- `FUN_1455da550`
- `strcmp`, `memcmp`, `strncmp`, `wcscmp`
- visible `bcrypt.dll` imports
- the obvious fake auth strings

These were plausible, but none matched the real visible post-input route.

## 4. Debugger Contamination Confirmed

Classic debugger-driven work visibly altered behavior. The user also saw detection-style windows during those runs. That forced a major strategic pivot:
- stop relying on a classic debugger for the main path
- launch the process normally
- inject input through `CONIN$`
- observe it externally through thread state, memory reads, and selective runtime patching

## 5. Clean Runtime Tooling Built

A custom no-debugger workflow was built around Win32 primitives:
- `CreateProcessW(..., CREATE_NEW_CONSOLE)`
- `AttachConsole`
- `CONIN$`
- `WriteConsoleInputW`
- targeted `ReadProcessMemory` and `WriteProcessMemory`

That workflow became the foundation for most later probes.

## 6. Prompt-Side And Post-Validation Chains Recovered

With the clean console workflow, several stable hotspot families were recovered.

Prompt-side chain:
- `0x55d9c83`
- `0x55d9c1c`
- `0x5c68c01`
- `0x5d24729`
- `0x5d2473f`

Post-validation chain:
- `0x2cf67df`
- `0x236fe1a`
- `0x23e05cd`

Later convergence:
- `0x27dd114`
- `0x2802257`

## 7. Late-State And Trap Work

A long middle phase focused on the late selector and trap network:
- `R10 -> R8 -> ESI`
- `0x1468d67f8 / 0x1468d67fa`
- `bruh`
- `0xDEADC0DE`
- `xabort 0xDC`
- late trampolines and stack-fix bypass attempts

This work was real and productive because it classified several trap families and proved that the sample is heavily protected. But it did not reach a stable acceptance path.

## 8. Project Organization And Canonical Worklog

As the session grew, the Desktop project was reorganized under:
- `NecrumWin-Reezli`
- `analysis/scripts`
- `analysis/traces`
- `analysis/notes`
- `analysis/worklog/crackme-worklog`

A canonical repo-backed memory flow was added so the project would stop relying on stale chat memory.

## 9. Reezli Clue Appears

A new Desktop file, `ayuda de reezli!.txt`, provided a direct clue from the crackme author. It described:
- a rough shape of `main`
- fake strings and anti-debug threads
- a detection branch printing `Detected.`
- a password check called `auth_verify_password`
- a PBKDF2-HMAC-SHA256 check with `100000` iterations, `salt[16]`, and `expected[32]`

This clue materially changed the priority of the project.

## 10. Reezli Clue Partially Validated

The project then switched from treating the clue as anecdotal to testing it directly.

What was validated:
- `SetConsoleTitleA("crackme | reezli.vc")` was captured live
- the real syscall output buffer contained `Detected.
`
- the fake auth strings were already known decoys

This moved the front line away from the late trap chain and back toward the intended password path.

## 11. Static Base Correction

An important address-base mistake was corrected during this phase. The static base was reset to `0x140000000`, which aligned the dynamic RVAs correctly.

This anchored the early path more cleanly:
- return address around `0x2d20094`
- enclosing function `0x2d1ffe6..0x2d2095d`
- internal chained callees `0x210efe7` and `0x26f3352`
- later entry into the protected region `0x2310f49..0x2d1e00e`

## 12. Ghidra Reopened And Revalidated

Ghidra was reopened and the older analyzed project was retained. MCP checks confirmed:
- the project is on the right sample
- `entry` is present and navigable
- the database already contains the required analysis state

This avoided a costly and noisy re-import.

## 13. Canonical Runtime Probes Added

To professionalize the workflow, the repo gained a cleaner runtime helper layer and focused probes:
- `scripts/core/runtime_probe.py`
- `scripts/probes/crackme_reezli_main_path_probe.py`
- `scripts/probes/crackme_ntio_path_probe.py`

These do not magically solve the crackme, but they formalize the current approach and replace ad-hoc one-off scripts as the default entry point.

## 14. Current Position

The current project position is:
- password recovery is again the primary route
- bypass work remains documented but secondary
- the main technical obstacle is observing the early title-to-prompt path without tripping the detection surface
- the next meaningful win is to recover the real `auth_verify_password` equivalent or its PBKDF2 buffers from the protected block
