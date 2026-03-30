# Findings

## Confirmed
- `FUN_1455da550` is not the decisive active-path password check.
- The prompt-side active range is `0x1455da9fd..0x145fe7abc`.
- The post-validation active range is `0x142310f49..0x142d1e00e`.
- `FUN_1455d8b6f` is a real range-decoder style routine in the live prompt path.
- The prompt hotspot `0x57faee8` is currently the strongest control-point candidate.

## Runtime observations
- Wrong-password flow is reproducible without a debugger.
- Real console input can be injected with `CONIN$` events.
- Sampling main-thread RIPs before and after input produces stable hotspot sets.

## Discarded
- `.pwdprot` as a direct answer source for the active path.
- `FUN_1455da550` as the active comparator.
- Token strings near `auth_login_success` as direct passwords.
- Standard `bcrypt` / CRT compare APIs as the primary active route.
