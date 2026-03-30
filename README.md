# Crackme Worklog

This repository tracks the reversing process for `crackme.exe`, including confirmed findings, discarded paths, live offsets, and next actions.

## Current Status

- Goal priority: recover the exact password; bypass is the fallback but is also being pursued in parallel.
- The visible runtime path is heavily protected and VM-like.
- `FUN_1455da550` is not the real password check path for the active console flow.
- The real active path has been narrowed to two large runtime blocks:
  - pre/prompt block: `0x1455da9fd..0x145fe7abc`
  - post-validation block: `0x142310f49..0x142d1e00e`
- A real transition point has been identified around hotspot `0x57faee8` on the prompt side.

## Confirmed Findings

- Target binary: `C:\Users\nesca\Documents\GhidraMCP\crackme.exe`
- Architecture: native Windows x64 console binary.
- Protector characteristics: Enigma-style packing/obfuscation with many fake sections and VM-like control flow.
- Imports are intentionally minimal and misleading.
- Typical compare/API routes do not drive the active password check:
  - `strcmp`, `memcmp`, `strncmp`, `wcscmp`
  - typical `bcrypt` exports used for hashing/KDF
  - trivial console/file API breakpoints
- `FUN_1455da550` can be patched cleanly without changing the visible `Wrong.` result, so it is not the decisive compare in the active path.
- Direct debugger usage contaminates behavior and can trigger detection.
- The crackme can be driven through a real console path without attaching a debugger, by writing keyboard events to `CONIN$`.
- Sampling the main thread without a debugger shows:
  - prompt-side execution concentrates in `0x1455da9fd..0x145fe7abc`
  - post-input validation concentrates in `0x142310f49..0x142d1e00e`
- `FUN_1455d8b6f` is a real range-decoder/LZ-style decompression routine used in the live path.
- The live main-thread transition hotspot around the prompt is `0x57faee8`.
- NOPing the call at `0x57faee8` prevents the normal transition into the post-validation hotspot set, which makes it the strongest current control point.

## Dynamic Notes

- Normal output for wrong input:
  - `a: auth_login_success`
  - `b: https://keyauthh.io/register`
  - `Enter password: Wrong.`
  - `Press Enter to exit...`
- The strings `Wrong.`, `Detected.`, `Enter password:` are not present plainly in the on-disk image or the earlier dumps already checked.
- They appear to be constructed or materialized indirectly at runtime.

## Discarded Paths

- `.pwdprot` as a direct stored XOR-hash source for the real password path.
- `FUN_1455da550` as the real active comparator.
- Token tables near `auth_login_success` as direct candidate passwords.
- Simple SHA-256-in-memory hypothesis for the test inputs.
- Standard API-level tracing as the main route to the check.

## Important Offsets

- Entry chain live path root: `FUN_145a4d81c`
- Prompt/runtime block: `0x1455da9fd..0x145fe7abc`
- Decoder block in live prompt path: `FUN_1455d8b6f`
- Prompt hotspot: `0x57faee8`
- Post-validation giant block: `0x142310f49..0x142d1e00e`
- Strong post-validation hotspots observed:
  - `0x2780d1d`
  - `0x23e05cd`
  - `0x236fe1a`
  - `0x2802257`

## Current Assessment

- Estimated progress: 90%
- Bypass probability: 96%
- Exact-password recovery probability: 72%

## Next Steps

1. Work directly around `0x57faee8` to turn the prompt-side control point into a stable bypass.
2. Correlate the prompt-side transition with the post-validation giant block to identify the precise decision edge.
3. Keep extracting runtime structure from the active path rather than from decoy compares or imports.
4. If the decision edge yields state or buffers, pivot back to exact-password recovery.
