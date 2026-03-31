# Next Steps

## Immediate Priority

The main line is no longer the old `DEADC0DE` exit path and not even just `xabort`.

The active line is now:

- family-wide patch over the repeated local loop family
- stack-aware bypass of the `xabort` sink
- and progressive unwinding of the late trampoline chain after that sink

That means the active choke point has moved again, from the hard-error trap into a deeper late dispatcher sequence.

## Confirmed Current Choke Points

- `0x55d9f14`
- `0x55d9f27`
- `0x55d9f40`
- `0x55d9f4f`
- `0x1e0ae4c`
- `0x1203bb4`
- `0x5a6c54a`
- `0x55efa2`
- `0x5898a23`
- `0x55da697`
- `0x446f267`

Observed stack on the original `C000001D` path:

- `crackme+0x1e0ae4c`
- `crackme+0x1203bb4`
- `crackme+0x55da8b5`

Observed progression after stack-aware late patches:

- `crackme+0x1e0ae4c`
- `crackme+0x5a6c54a`
- `0x800000023`
- `crackme+0x446f267`

## Recommended Work Order

1. Keep the repeated loop family patch as the reproducible base configuration.
2. Keep the late patch pair that successfully crosses the old sink:
   - `0x1e0ae4c -> ret`
   - `0x1203bb4 -> add rsp, 8 ; ret`
3. Treat every new AV as the next trampoline to unwind, not as a reason to fall back to the old trap line.
4. Prioritize continuation-shape repairs over branch forcing when the dump stack clearly shows `return address -> scratch -> continuation`.
5. Use delayed patching only for late-materialized pages and prearm those patches before input when timing matters.

## Concrete Technical Targets

### 1. Repeated local loop family

Keep the 14-loop family patch as the baseline because it consistently removes the old reject/trap family and exposes the later anti-tamper path.

Key loop RVAs:

- `0x55d8d9d`
- `0x55d8f1a`
- `0x55d8fe7`
- `0x55d91c3`
- `0x55d9324`
- `0x55d9537`
- `0x55d9607`
- `0x55d9789`
- `0x55d989d`
- `0x55d9a09`
- `0x55d9b7b`
- `0x55d9d14`
- `0x55d9dbf`
- `0x55d9f55`

### 2. Reader/writer microblock

The `C0000005` path is still useful because it exposes the reader/writer block:

- `0x55d9f14`
- `0x55d9f27`
- `0x55d9f40`
- `0x55d9f4f`

This is the last coherent local state machine before the anti-tamper branch.

### 3. Late anti-tamper trampolines

The old sink is no longer the end of the line.

Working late patches so far:

- `0x1e0ae4c -> c3 90 90`
- `0x1203bb4 -> 48 83 c4 08 c3`
- `0x5a6c54a -> 66 31 c9 90`
- `0x55efa2 -> c3`
- `0x5898a23 -> c3`
- `0x55da697 -> 48 83 c4 08 c3`

Interpretation:

- the late bypass problem behaves like chained trampolines and state fixups
- not like one final success/reject branch
- each new crash is currently more useful than the old `DEADC0DE` route

### 4. Password route remains secondary

Password recovery remains secondary until a stable non-trap route exists.

## Short-Term Success Criteria

The next pass should achieve at least one of these:

- convert `crackme+0x446f267` into the next unwound continuation
- identify the aligned start of the block that contains `0x446f267`
- or reach a stable post-trampoline state that no longer ends in AV
