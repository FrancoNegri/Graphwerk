# 057. Guard `loadGraph()` against overlapping in-flight calls

Status: done
Decision: docs/decisions/011-prompt-box-session-kickoff.md

## Goal

On launch (and any time a poll tick lands while an earlier `/api/graph`
fetch is still pending), the browser should never have more than one
`/api/graph` request in flight at a time.

## Bug

`static/app.js` calls `loadGraph()` from two independent sites: once
directly on page load (~line 699), and once from `pollHashAndSession`'s
hash-mismatch check (~line 686, not awaited). `currentHash` (~line 23)
starts as `null` and is only assigned once a `loadGraph()` call's fetch
resolves (~line 40). If the initial load is still pending when the first
poll tick (or several, back to back) lands — likely on a cold snapshot
cache or a slow LAN link — the comparison `data.hash !== currentHash` keeps
evaluating true against the still-`null`/stale value, so every such tick
fires another concurrent `loadGraph()` call, stacking redundant
`/api/graph` fetches for as long as the pending one is slow.

This is distinct from ticket 045, which only serialized `pollHashAndSession`
against its own previous tick — it never guarded `loadGraph()` itself
against being entered while already in flight.

## Acceptance criteria

- `loadGraph()` is a no-op re-entrantly: if called while a previous call's
  fetch hasn't resolved yet, the new call returns without issuing another
  `/api/graph` request.
- A slow/hanging `/api/graph` response (simulated in a test or manual
  repro) does not cause additional overlapping `/api/graph` fetches from
  either call site (initial load or poll-triggered).
- Existing behavior is preserved: `loadGraph()` still runs once on launch,
  and still runs again on the next poll tick once the hash genuinely
  changes and no call is in flight.

## Likely files

- `static/app.js` — `loadGraph()` (~line 37) and its two call sites
  (~line 686, ~line 699).

## Out of scope

- Any change to `/api/hash` or `/api/session` polling cadence.
- Backoff/retry strategy beyond removing the overlap (same exclusion as
  ticket 045).
