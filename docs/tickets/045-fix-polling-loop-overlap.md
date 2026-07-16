# 045. Fix unbounded overlap in the hash/session polling loop

Status: done
Decision: docs/decisions/011-prompt-box-session-kickoff.md

## Goal

Stop the browser from piling up requests until Chrome kills the tab with
`net::ERR_INSUFFICIENT_RESOURCES` (observed at `app.js:573`, the
`/api/hash` fetch).

## Bug

`static/app.js`'s `setInterval(async () => {...}, 1500)` (~line 571) fires
every 1500ms regardless of whether the previous tick's two `await fetch`
calls (`/api/hash` then `/api/session`) have resolved yet. `setInterval`
doesn't wait for its callback to finish, so if either request is ever
slower than 1500ms — a slow LAN link, a busy server during a spawned
session (ticket 038-040 added the second fetch into this same tick) — the
next tick fires anyway and queues more requests on top, compounding every
1500ms with no ceiling until the browser's per-tab connection/request
limit is hit.

## Acceptance criteria

- The polling loop never has more than one `/api/hash` + `/api/session`
  round-trip in flight at a time — e.g. an in-flight guard flag, or
  replacing `setInterval` with a self-scheduling `setTimeout` chain that
  only queues the next tick after the current one settles (success or
  catch).
- A slow/hanging fetch (simulated in a test or manual repro) does not
  cause additional overlapping fetches to queue up.
- Existing behavior is preserved: still polls roughly every 1500ms when
  requests are fast, still catches and silently retries on a fetch error
  ("server briefly unreachable").

## Likely files

- `static/app.js` — the polling `setInterval` block (~lines 571-581).

## Out of scope

- Any backoff/retry strategy beyond removing the overlap (e.g. exponential
  backoff on repeated failures) — file separately if dogfooding shows a
  need.
- Server-side changes to `/api/hash` or `/api/session`.
