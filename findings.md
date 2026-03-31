# Findings

## Confirmed

- `FUN_1455da550` is not the decisive active-path password check.
- The prompt-side active range is `0x1455da9fd..0x145fe7abc`.
- The post-validation active range is `0x142310f49..0x142d1e00e`.
- `FUN_1455d8b6f` is a real range-decoder style routine in the live prompt path.
- The crackme can be driven without a debugger by writing input events into `CONIN$`.
- The prompt hotspot around `0x57faee8` is real and materially affects downstream execution.
- The stable post-input hotspot sequence is `0x2cf67df -> 0x236fe1a -> 0x23e05cd`.
- `0x5c68c01` is a trampoline that jumps to `0x145c2de89`.
- `FUN_145d24744` is a small helper with `ret 8`, but skipping it naively still breaks execution.
- `RDI` and `R8` remain stable state tables in the post-validation block.
- `RAX`, `RBX`, and `RSI` are the most clearly input-dependent registers in the confirmed validation path.
- The handler around `0x23e05cd` has at least one duplicated template elsewhere in the unpacked module.
- The convergence pair `0x27dd114` and `0x2802257` is real and sits later in the same validation network.
- The VM exit still collapses into two stable result families before transferring to `ntdll.dll`:
  - `RAX=0x28`, `RBX=0`
  - `RAX=0x2a`, `RBX=1`
- `0x14755c736` is a direct caller into `0x147802244`.
- `0x1477aa994 -> 0x14755c714 -> 0x147802244 -> ... -> 0x147901c6c -> 0x1475e525a` is part of the live late-stage chain.
- `RBX` behaves like a heavily mixed late-stage state and changes strongly even for near-identical inputs.
- The late-stage critical zone is now narrowed to:
  - `0x1475ba2e2`
  - `0x1475b9460`
  - `0x1475b9494`
  - `0x1475a3b17`
  - `0x145034f48`

## Runtime Observations

- Wrong-password flow is reproducible without attaching a debugger.
- Main-thread RIP sampling before and after input produces stable hotspot sets.
- Prompt-side sequence observed during clean runs:
  - `0x55d9c83`
  - `0x55d9c1c`
  - `0x5c68c01`
  - `0x5d24729`
- Post-validation sequence observed during clean runs:
  - `0x2cf67df`
  - `0x236fe1a`
  - `0x23e05cd`
- At `0x2cf67df`, captured runs so far still reach the `jne` with the failure-side condition in place; no tested candidate has diverged into a success-like path.
- After the post-validation sequence, execution falls into system-side waiting behavior rather than terminating immediately.
- Later in the same run, repeated convergence occurs around:
  - `0x27dd114`
  - `0x2802257`
- Patching or forcing branches in that late cluster changes local hit counts but has not yet broken the wrong-password route cleanly.
- Forcing `0x1475b9494 -> 0x1475a3b17` changes the convergence counts more than baseline, which confirms that the branch is real and late in the visible validation route.

## Disassembly Notes

- `0x14736fe1a`: `xor esi, ebx ; jmp 0x1473e05c8`
- `0x14736fe06`: `shr esi, 8`
- `0x14736fe0f`: `jbe 0x1475ac56a`
- `0x1473e05c3`: `call 0x14755ce70`
- `0x1473e05e7`: `xor esi, 0xe7a90182`
- `0x1473e05f0`: `call 0x1474c3aa1`
- `0x147cf67df`: `jne 0x147311abb`
- `0x1477dd114`: `xor r8d, 0x6f9eaca4 ; call 0x1478d82bc ; jle 0x1477e8459`
- `0x147853126`: `lea rsp, [rsp + 0x30] ; jne 0x1477aa994`
- `0x1477aa994`: `movzx edx, byte ptr [rdi] ; call 0x14755c714 ; call 0x147901c6c ; ... ; call 0x1475e525a`
- `0x1475e525f`: `jne 0x1475ba298`
- `0x1475ba2e2`: `jne 0x1475b9460`
- `0x1475b948e`: `cmp ebx, 1`
- `0x1475b9494`: `jmp 0x147616360`
- `0x14761637a`: `jae 0x1475a3b17`
- `0x1476163c0`: `jmp rdi`
- `0x1475a3b37`: `jmp 0x145034f48`
- There is another handler-like block around `0x14a7d171e` that reproduces the same `sar ...`, `inc r11`, `push 0x54bdce0b`, `xor esi, 0xe7a90182` pattern.

## Patch Behavior

- NOPing the call at `0x57faee8` changes flow but crashes with `0xC0000005`.
- Replacing `FUN_145c13f7e` with `ret` also crashes with `0xC0000005`.
- Replacing the call at `0x5d2473f` with `add rsp, 8; nop` still crashes.
- NOPing the conditional branch at `0x2cf67df` does not crash immediately and diverts execution away from the normal `0x236fe1a` path.
- Under the `0x2cf67df` branch patch, execution returns transiently to prompt-side offsets near `0x55d8ff7`, then still reaches rejection-side neighborhood later.
- Naively skipping direct calls around `0x23e05cd` does not produce a clean bypass.
- Forcing or skipping the `jle` at `0x1477dd120` does not prevent convergence through `0x27dd114 / 0x2802257`.
- Forcing or skipping the `jne` at `0x14785312b` also fails to produce a clean bypass.
- Forcing `0x1475b9494 -> 0x1475a3b17` changes the route significantly, but does not yet expose a visible success path.

## Strings And Output

Visible output includes:

- `a: auth_login_success`
- `b: https://keyauthh.io/register`
- `Enter password:`
- `Wrong.`
- `Press Enter to exit...`

The strings `Wrong.`, `Detected.`, and `Enter password:` were not found plainly in the checked module dump or the searched private-memory dumps.

## Discarded

- `.pwdprot` as a direct answer source for the active path
- `FUN_1455da550` as the active comparator
- token strings near `auth_login_success` as direct passwords
- standard `bcrypt` and CRT compare APIs as the primary active route
- crude prompt-side call removal as a reliable bypass strategy
- `0x1477dd120` as the terminal success-versus-rejection branch
- `0x14785312b` as the terminal success-versus-rejection branch
- `cmp ebx, 1` as a standalone final gate
