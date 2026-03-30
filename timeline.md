# Timeline

## Session Summary

### Initial triage
- Confirmed the crackme is a Windows x64 console target.
- Confirmed local-only validation and no server-side dependency in the challenge description.
- Located the binary and live dumps used for analysis.

### Wrong assumptions eliminated
- `.pwdprot` as a direct answer source was checked and did not explain the active path.
- `FUN_1455da550` looked like a compare routine but was later shown not to decide the active console flow.
- Standard compares and common CNG hashing exports were probed and did not correspond to the real visible check path.

### Anti-debug observations
- Traditional debugger attachment and breakpoints can trigger detection or alter the flow.
- User-observed alert windows aligned with debugger activity.
- Work shifted to non-debugger observation and patching.

### Ghidra / MCP improvements
- The Ghidra bridge timeout was raised to make heavy decompiles more usable.
- Despite MCP instability, long decompiles eventually revealed the VM/dispatcher shape.

### Live console route
- Real console input was reproduced by writing input events to `CONIN$`.
- This avoided depending only on `stdin` piping and made non-debug runtime observation cleaner.

### Runtime control-flow narrowing
- The main thread was sampled before input and after wrong-password validation.
- Two large active ranges emerged:
  - prompt-side: `0x1455da9fd..0x145fe7abc`
  - post-validation: `0x142310f49..0x142d1e00e`
- The prompt-side hotspot `0x57faee8` now appears to be the most important transition point identified so far.

### Current posture
- Password not recovered yet.
- A clean bypass still looks highly likely.
- The process is now focused on the prompt-side transition rather than on decoy compare routines.
