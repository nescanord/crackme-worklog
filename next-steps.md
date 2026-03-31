# Next Actions

1. Follow the late-stage chain `0x1477aa994 -> 0x14755c714 -> 0x147802244 -> 0x147901c6c -> 0x1475e525a`.
2. Test the `jne` at `0x1475e525f` and determine whether it is closer to the real success-versus-rejection split.
3. Keep using real-console execution plus `CONIN$` injection and `GetThreadContext` sampling as the primary dynamic workflow.
4. Use local dump disassembly for focused pivots instead of broad Ghidra sweeps over the VM.
5. If one of the late-stage branches collapses to a stable success-state selector, pivot immediately to:
   - a minimal bypass patch
   - and an attempt to infer the expected final password-derived state
