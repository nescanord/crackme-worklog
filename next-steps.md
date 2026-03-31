# Next Steps

## Immediate Priority

Turn the known trap route into a useful live path instead of merely silencing its UI.

Why:

- `bruh` is now classified as a hard-error wrapper
- `0xDEADC0DE` is the underlying trap result
- suppressing `NtRaiseHardError` alone only removes the popup
- suppressing termination as well keeps the process alive and yields `crackme | reezli.vc`

That makes the trap path the cleanest current place to push forward.

## Recommended Work Order

1. Follow the live `crackme | reezli.vc` state after hard-error and termination suppression.
2. Identify where that state parks or loops once the trap cannot complete.
3. Move one step upward from the trap exit and patch the trap-selection logic, not the OS-facing hard-error APIs.
4. Keep selector patches delayed until after input when testing `R10`-side branches to avoid `Initialization error 2`.

## Concrete Technical Targets

### 1. Trap-to-live transition

Use the popup-context probe and thread snapshots to identify the exact module RVA where the trap-producing route remains alive after:

- `NtRaiseHardError -> ret`
- `NtTerminateProcess -> ret`
- `RtlExitUserProcess -> ret`

Primary clue:

- console title changes to `crackme | reezli.vc`

### 2. Upstream trap selection

Attack the route above the hard-error instead of the hard-error itself.

Key areas:

- `0x55d905a`
- `0x55d9103`
- the surrounding prompt/decoder block
- the late `R10 -> R8 -> ESI` selector chain

Goal:

- avoid entering the trap route at all
- preserve a coherent live state

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

- a run that avoids both reject and `0xDEADC0DE` without external API suppression
- a stable parked state deeper than `crackme | reezli.vc`
- or a patch point above the trap that changes outcome without causing `Initialization error 2`
