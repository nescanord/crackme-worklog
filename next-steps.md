# Next Steps

## Immediate Priority

Move one step above the exact `DEADC0DE` exit preparation instead of only suppressing UI or process termination.

Why:

- `bruh` is now classified as a hard-error wrapper
- `0xDEADC0DE` is the underlying trap result
- WinDbg tied that trap to a concrete crackme-side exit caller:
  - `crackme+0x5a3628a`
- skipping that exact call only reveals a later null-execute crash, which proves it is terminal trap code, not the correct bypass point

That makes the pre-exit path above `0x5a3628a` the best current place to push forward.

## Recommended Work Order

1. Walk upward from `crackme+0x5a3628a` and identify the last branch or selector that chooses the terminal `DEADC0DE` exit path.
2. Keep using local spin-capture on the homologous exit loops to recover coherent state at:
   - `0x55d9f55`
   - `0x55d8fee`
   - `0x55d9122`
   - `0x55d90d7`
3. Prefer rerouting pre-exit state rather than NOPing terminal exits.
4. Keep selector patches delayed until after input when testing `R10`-side branches to avoid `Initialization error 2`.

## Concrete Technical Targets

### 1. Pre-exit trap selector

Use dump-guided reversing around:

- `crackme+0x5a3627f`
- `crackme+0x5a3628a`

Goal:

- identify the last coherent selector before the `DEADC0DE` exit is invoked
- patch the selector, not the exit call itself

### 2. Homologous local exit loops

Attack the repeated local decoder/exit family rather than isolated one-off branches.

Key areas:

- `0x55d9f55`
- `0x55d9f67`
- `0x55d8fee`
- `0x55d8ff4`
- `0x55d9122`
- `0x55d90d7`

Goal:

- find the repeated condition that keeps assembling the exit trap
- preserve a coherent live state all the way through those loops

### 3. Coherent selector production

Keep focusing on upstream state rather than only patching downstream branches.

Best current state model:

- `R10` feeds `R8`
- `R8` feeds the late `ESI` gate
- incoherent forcing causes reject, trap, or parked states

### 4. Password route remains secondary

Continue to treat direct password recovery as secondary until a stable non-trap route exists.

Reason:

- obvious semantic candidates already failed
- visible compare and visible crypto APIs were downgraded
- bypass is still closer than password recovery

## Short-Term Success Criteria

The next pass should aim to achieve at least one of these:

- a run that avoids both reject and `0xDEADC0DE` by changing pre-exit selection rather than suppressing `kernel32/ntdll`
- a dump or live capture of the branch immediately above `crackme+0x5a3628a`
- or a repeated local-loop condition that can be patched coherently across `0x55d9f55` and `0x55d8fee`
