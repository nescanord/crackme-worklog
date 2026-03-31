# Next Steps

## Immediate Priority

The main line is no longer the old `DEADC0DE` exit path.

The current highest-value path is:

- family-wide patch over the repeated local loop family
- new AV at `crackme+0x55d9f14`
- and, once the loop is cut differently, an explicit trap at:
  - `crackme+0x1e0ae4c = xabort 0xDC`

That means the active choke point has moved from the old hard-error exit into a later anti-tamper chain.

## Confirmed Current Choke Points

- `0x55d9f14`
- `0x55d9f27`
- `0x55d9f40`
- `0x55d9f4f`
- `0x55da8b5`
- `0x1203bb4`
- `0x1e0ae4c`

Observed stack on the `C000001D` path:

- `crackme+0x1e0ae4c`
- `crackme+0x1203bb4`
- `crackme+0x55da8b5`

## Recommended Work Order

1. Stop spending time on `kernel32/ntdll` exits for the main line.
2. Treat `0x1e0ae4c` as a trap sink and focus on the dispatch that reaches it.
3. Use the repeated loop family patch as the reproducible base configuration.
4. Walk upward from `0x55da8b5` and identify the selector that dispatches into `0x1203bb4 -> 0x1e0ae4c`.
5. If needed, use delayed patching only for late-materialized pages, but keep the family loop patch early.

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

### 3. Late anti-tamper dispatch

The `C000001D` path shows a stable trap sink:

- `0x55da8b5`
- `0x1203bb4`
- `0x1e0ae4c`

Important finding:

- direct patching of `0x55da8b0`
- direct patching of `0x55da8d9`
- and direct short-circuiting of `0x55da8b5`

all still land in the same `xabort` sink.

That strongly suggests the real selector is above `0x55da8b5`, not inside it.

### 4. Password route remains secondary

Password recovery remains secondary until a stable non-trap route exists.

## Short-Term Success Criteria

The next pass should achieve at least one of these:

- identify the caller or dispatch above `0x55da8b5` that selects `0x1203bb4`
- land in a post-`family14` path that avoids both `C0000005` and `C000001D`
- or capture the late-materialized page that backs `0x1e0ae4c` before the trap fires
