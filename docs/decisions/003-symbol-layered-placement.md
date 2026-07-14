# 003. Symbol-level layered placement within an expanded file

Status: proposed
Date: 2026-07-14

## Context

ADR 002 gave files a layered reading — import-depth bands, cycles collapsed
into one band — and explicitly filed "symbol-level layout inside a file box"
as out of scope, to revisit later. That later point is now: once a file is
expanded (its default state whenever it needs review, per ticket 010), fcose
places its functions and classes organically inside the compound box, so the
same illegibility ADR 002 fixed at the file level reappears one level down —
the reviewer can't tell which function calls which just by looking.

This is a direct continuation of Phase 2's "Scale UX" line (docs/04), not a
detour: same problem, same fix, one level deeper.

## Decision

Reuse the file-layering machinery from ADR 002 (Tarjan SCC for cycles +
longest-path depth), scoped to one expanded file's own top-level function
symbols, using intra-file `calls` edges instead of `imports` edges:

- For each expanded file, compute a layer per top-level function from calls
  among that file's own functions only (cross-file calls are ignored for
  this — the ordering is local to "what you see when you open this file",
  not a global call-depth ranking).
- Recursive calls — a function calling itself, or a mutual-recursion cycle —
  collapse into one shared layer via the same SCC step that already handles
  import cycles, so recursion degrades to "same band," never a crash or
  infinite loop.
- Functions sharing a layer get a minimum horizontal gap of 190, the same
  constant just added for same-layer files (ticket 012 follow-up), so the
  convention reads the same at both granularities.
- Cross-layer vertical spacing follows the existing layout's proportions
  (smaller than the 220 used between file bands, since function chips are
  smaller than file boxes) — exact constant is an implementation detail for
  the ticket, not a product decision.

All presentation logic in `static/app.js`, verified from the browser console
the way tickets 011/012 were (no JS test runner exists in this project — see
those tickets' acceptance criteria for the pattern). No backend change.

## Alternatives considered

- **Leave symbol placement to fcose (status quo)** — cheapest, but leaves
  the exact problem ADR 002 fixed at the file level unfixed one level down;
  rejected, inconsistent with why files got this treatment.
- **Global call-depth ranking (cross-file), not scoped to the open file** —
  richer in theory, but ties a function's position to files elsewhere in the
  graph and contradicts the "when you open this file" framing (local,
  self-contained ordering); also complicates recursion handling across file
  boundaries for no clear benefit. Rejected — keep it file-local.
- **Include methods-in-classes and class-vs-class ordering now** — more
  complete, but doubles the scope of one ticket and classes are compound
  nodes themselves (ordering "class vs class" by calls needs its own
  thought). Deferred, mirrors ADR 002's own increment discipline.

## Consequences

- Inside an expanded file, function layout reflects call structure —
  callers above callees — instead of arbitrary fcose placement; recursive/
  mutually-recursive functions cluster into one visible band instead of
  fighting the depth constraint.
- Touches no invariant: presentation-only, `static/app.js`, no backend/API
  change, no new dependency.
- The layering utility (SCC + longest-path) now has two call sites (files,
  symbols) — worth factoring the shared part cleanly rather than copy-paste,
  left to the ticket's judgment since both are small.

## Out of scope

- Methods inside classes, class-vs-class layering — later increment if
  this proves useful, same as ADR 002's own scoping.
- Persisting layout across reloads (already out of scope per ADR 002).
- Any use of cross-file call depth for symbol placement.
