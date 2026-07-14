# 005. Layer computation moves server-side; the JS layer stays thin

Status: accepted
Date: 2026-07-14

## Context

ADRs 002/003 placed layer assignment (import depth for files, call depth for
symbols) in `static/app.js`, verified from the browser console, because the
project has no JS test runner. Implementing ticket 014 that way already
required a node harness with stubbed browser globals just to exercise the
logic, and ticket 015 was heading down the same path. The user rejected that
direction during review: harness scaffolding for browser JS is the wrong
cost, while Python already has pytest and real coverage.

## Decision

- **Graph computation lives in Python.** New `graphwerk/layout.py` assigns
  `GraphNode.layer` as part of `GraphService.snapshot()`: files by import
  depth, top-level functions by intra-file call depth, cycles collapsed to a
  shared layer via (iterative) Tarjan SCC. The `/api/graph` payload carries
  `layer` on every node (`null` for classes, methods, and anything else
  without a band).
- **`static/app.js` is presentation-only.** It maps `node.layer` plus current
  visibility to fcose banding constraints and never re-derives graph
  structure. The Tarjan/longest-path JS from tickets 011/014 is deleted,
  along with the `window.fileLayersByImportDepth` /
  `window.symbolLayersByCallDepth` debug hooks (curl `/api/graph` instead).
- **Testing split.** pytest covers all layer/graph logic (algorithm-level in
  `tests/test_layout.py`, wiring-level via `GraphService.snapshot()`). The
  browser layer is verified visually by the user — no node-side test
  scaffolding for `app.js`, ever.

This supersedes the "all in app.js, verified from the browser console"
placement in ADRs 002/003 and the console-verifiability acceptance criteria
in tickets 011/014. The visual outcomes those ADRs specify are unchanged.

## Alternatives considered

- **Keep logic in JS, add a real JS test runner (vitest/jest)** — introduces
  a Node-side toolchain, contradicting the standing "Python everywhere; JS
  only in `static/` as browser glue" rule, and creates a second test
  ecosystem for one file. Rejected.
- **Keep logic in JS, test through a node harness with stubbed browser
  globals** — works, but is brittle ceremony around code that could simply
  live where the tests are. Rejected by the user in review.

## Consequences

- `node.layer` is now part of the API contract: an integer for files and
  top-level functions, `null` otherwise. New languages/extractors get file
  layering for free; symbol layering follows once their symbols emit `calls`
  edges.
- Layer behavior changes now require a server restart to observe (Python is
  loaded in memory), unlike pure `static/` edits which reload per request.
- Future graph-derived features default to Python-side computation exposed
  as payload fields, with pytest coverage; app.js consumes, the user eyeballs.
