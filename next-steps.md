# Next Steps

## Immediate Priority

The main line is now password recovery through the Reezli-guided early path, not the late trampoline bypass chain.

## Current Front Line

Work from these anchors:
- `SetConsoleTitleA("crackme | reezli.vc")`
- `RVA 0x2d20094`
- function range `0x2d1ffe6..0x2d2095d`
- early callees `0x210efe7` and `0x26f3352`
- giant protected region `0x2310f49..0x2d1e00e`

## Recommended Work Order

1. Reduce observation noise on the early path.
   Replace or minimize thread suspension where possible when following the title and prompt path.

2. Map the early path statically in Ghidra.
   Use the known RVAs to reconstruct the `main`-like front end around the title, detection branch, fake-string init, prompt, and password read.

3. Recover the real password-check routine.
   Identify the routine that corresponds to Reezli's `auth_verify_password`, even if the visible `BCrypt*` exports are not directly trappable yet.

4. Revisit the PBKDF2 hypothesis with better anchors.
   Once the real checker is mapped, extract or capture:
   - `salt[16]`
   - `expected[32]`
   - iteration count
   - the actual password buffer handed into the derivation path

5. Keep the late trap chain only as fallback work.
   The `bruh -> DEADC0DE -> xabort -> trampoline` line is still useful if the password path stalls, but it is no longer the primary intended route.

## Concrete Technical Targets

### Early main path
- verify how `0x2d20094` returns into the prompt path
- map which calls correspond to:
  - anti-analysis and environment checks
  - fake-string init
  - `system("cls")`
  - prompt printing
  - input read

### Console I/O capture
- continue using `NtWriteFile` and `NtReadFile` capture to validate text path assumptions
- adjust timing and capture strategy to avoid converting normal runs into `Detected.`

### Ghidra recovery
- rename functions around `0x2d1ffe6..0x2d2095d`, `0x210efe7`, and `0x26f3352`
- mark known decoy branches separately from the password path

## Short-Term Success Criteria

The next pass should achieve at least one of these:
- identify the protected function that matches `auth_verify_password`
- recover the password-read to checker call transition cleanly
- or extract a stable PBKDF2-related constant set from the live path
