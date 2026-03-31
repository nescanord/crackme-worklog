# Next Steps

## Immediate Priority

The main line is now password recovery through caller-state reconstruction, not the late trampoline bypass chain.

The active target is:

- the caller that constructs `param_3` for `FUN_1455d8b6f`

## Why this is now the highest-value target

What is already proved:

- `param_2` of `FUN_1455d8b6f` is constant across different passwords
- `param_5` of `FUN_1455d8b6f` is constant across different passwords
- the decoded output region at `crackme.exe + 0x11ec000` is identical across different passwords
- `param_4` and `param_7` do not carry a password buffer or final digest
- `param_3` does change across different passwords

This means the password does not select a different payload. It changes caller state that is handed to the decoder.

## Confirmed Current Choke Points

- `FUN_1455d8b6f`
- `crackme.exe + 0x2d958c5` as the stable decoder stream
- `crackme.exe + 0x11ec000` as the stable decoder output base
- the post-input single-thread timeline inside:
  - `0x55d8xxx`
  - `0x55d9xxx`
- divergent late subzones such as:
  - `0x55d903d`
  - `0x55d9b2d`
  - `0x55d9d54`

## Recommended Work Order

1. Recover the call site that invokes `FUN_1455d8b6f`.
2. Recover how `param_3` is produced.
3. Determine whether `param_3` is a compact selector, a length/state value, or an encoded pointer-sized state word.
4. Re-run candidate testing only after the `param_3` producer is understood.
5. Keep the late bypass chain documented, but treat it as fallback work rather than the front line.

## Concrete Technical Targets

### 1. Decoder caller reconstruction

Capture or infer the immediate caller that sets up:

- `RCX = decoder state struct`
- `RDX = 0x2d958c5`
- `R8  = param_3`
- `R9  = out-param ptr`

The goal is to identify where `R8/param_3` comes from.

### 2. Differential caller-state analysis

Continue comparing controlled inputs, but measure:

- `param_3`
- caller-side return chain
- caller-side stack frame

instead of chasing the constant decoder output blob.

### 3. Runtime range-table follow-up

The runtime range table around `0x145ff7448` still matters because it maps the live block families around the decoder.

Use it to group:

- decoder block
- immediate helper blocks
- caller/continuation blocks

without assuming the whole region is semantically meaningful.

### 4. SHA256 table stays downgraded

The runtime-only `salt + digest + SHA256 + keyauth_*` table stays as a historical clue, not as the primary password path, unless new evidence ties it back to the caller-state line.

## Short-Term Success Criteria

The next pass should achieve at least one of these:

- identify the direct caller of `FUN_1455d8b6f`
- recover the producer of `param_3`
- or prove that `param_3` is derived from a fixed transform that can be inverted offline
