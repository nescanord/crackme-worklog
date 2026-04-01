# NecrumWin (Reezli challenge) Reverse Engineering Worklog

Technical worklog for a protected Windows x64 console crackme.

Primary goal:
- recover a valid password

Secondary goal:
- produce a stable acceptance bypass with the smallest reliable patch set

## Verified Target

- Name: `NecrumWin (Reezli challenge)`
- Platform: Windows x64
- Type: native console executable
- Validation model: client-side only
- Protection surface: VMProtect plus custom anti-analysis and decoys

Hashes verified against the active sample:

- `MD5`: `78d8e7061e2db2a51387b501ebbc5586`
- `SHA-1`: `e82e9d93d3bc73c1def281e8f13b3f276d0f5767`
- `SHA-256`: `948089902fbafe0f2333f8a85ac46f81b46375bdcceb141ded697d5b8280cce8`

## Current Position

The project is no longer treating late trap bypass as the primary intended route.

What is now established:
- the obvious strings and fake auth banners are decoys
- debugger attach and aggressive instrumentation contaminate execution
- the live title path `SetConsoleTitleA("crackme | reezli.vc")` is real
- the visible `Detected.` output was recovered from the real `NtWriteFile` buffer
- the early control path after the title has concrete static anchors in the protected block
- Reezli's clue about the overall shape of `main` is credible and now guides the front line

The main line is therefore:
- follow the early `main` path and prompt path with low-noise probes
- locate the real `auth_verify_password` equivalent in the protected block
- recover the password path first
- keep bypass work as a documented secondary line

## What The Reezli Clue Changed

The clue in `ayuda de reezli!.txt` claims:
- `main` sets the console title to `crackme | reezli.vc`
- a detection branch prints `Detected.`
- fake strings are initialized before the real prompt
- password validation is done by `auth_verify_password`
- the check uses `PBKDF2-HMAC-SHA256`, `100000` iterations, `salt[16]`, and `expected[32]`

What has been validated in the real sample:
- `SetConsoleTitleA("crackme | reezli.vc")` was captured live
- `Detected.` was extracted from the real syscall buffer
- the fake strings are indeed decoys
- the early protected path after the title is real and traceable

What remains unresolved:
- visible traps on `BCrypt*` exports did not fire under the current workflow
- this is treated as a tooling/timing limitation, not as proof that the clue is false

## Confirmed Early Path Anchors

After correcting the static base back to `0x140000000`, the currently anchored early path is:

- title return inside `RVA 0x2d1ffe6..0x2d2095d`
- validated return address: `RVA 0x2d20094`
- chained early callees observed dynamically:
  - `0x210efe7`
  - `0x26f3352`
- later callers fall into the giant protected region:
  - `0x2310f49..0x2d1e00e`

This is the strongest current map of the intended front end of the crackme.

## Confirmed Dynamic Facts

- `strcmp`, `memcmp`, `strncmp`, and `wcscmp` do not control the visible validation route
- the obvious visible `bcrypt.dll` surface is not enough by itself to recover the check path
- Ghidra's old project database is valid and useful; it already contains the analyzed program and runtime-created regions
- the low-noise workflow still matters because thread suspension plus `GetThreadContext` is intrusive enough to push the sample into `Detected.`

## Canonical Workflow

1. Keep Ghidra and the MCP available for static navigation and address translation.
2. Use the canonical runtime helper layer in `scripts/core/runtime_probe.py`.
3. Use the focused probes in `scripts/probes/` for:
   - early `main` path following
   - console read/write buffer capture
4. Treat the historical scripts in `scripts/` as supporting evidence and prior attack surfaces, not as the default entry point.

## Repository Layout

- `scripts/core/`
  - canonical helper layer over the original Win32 runtime primitives
- `scripts/probes/`
  - current focused probes for the Reezli-guided path
- `scripts/`
  - historical exploratory scripts and legacy helpers
- `artifacts/`
  - JSON traces and probe outputs
- `notes/source-clues/`
  - source clue writeups and current assessment
- `findings.md`
  - concise confirmed facts
- `timeline.md`
  - chronological map of the project
- `next-steps.md`
  - current recommended forward path

## Current Assessment

Realistic status:
- password recovery is again the primary route
- bypass remains possible but is no longer treated as the intended shortest path
- the limiting factor is not lack of anchors; it is extracting the password path without triggering the detection surface

## Immediate Direction

- follow the early title-to-prompt path with lower-noise capture
- identify the real password-check routine behind the protected block
- recover `salt`, `expected`, and the password transform if the PBKDF2 clue proves exact
- keep the late trampoline chain documented as fallback only
