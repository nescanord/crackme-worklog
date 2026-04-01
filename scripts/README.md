# Scripts

This repository treats the script set in three tiers.

## Canonical runtime base

- `crackme_popup_context_probe.py`
  - Original low-level Win32 runtime probing primitives.
  - Source of truth for process launch, memory patching, console injection, thread snapshots, and popup inspection.
- `core/runtime_probe.py`
  - Thin orchestration layer over the original helper.
  - Preferred starting point for new probes.

## Current probes

- `probes/crackme_reezli_main_path_probe.py`
  - Follows Reezli's early `main` path from the verified `SetConsoleTitleA("crackme | reezli.vc")` call into internal callees.
  - Current limitation: early title hits are timing-sensitive because the sample outruns intrusive observation easily.
- `probes/crackme_ntio_path_probe.py`
  - Captures `NtWriteFile` and `NtReadFile` buffers with correct x64 shadow-space argument decoding.
  - Verified to run cleanly and fail gracefully when no hit is captured in the timeout window.

## Historical and exploratory scripts

The rest of the scripts in this folder document earlier attack surfaces:
- decoder path fuzzing
- selector and `R10` sweeps
- popup probing
- trap follow-up sweeps
- bypass experiments

They remain valuable as historical evidence and fallback tooling, but they are no longer the recommended entry point for new work.
