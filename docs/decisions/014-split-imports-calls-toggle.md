# 014. Split the combined edge toggle into independent imports/calls checkboxes

Status: proposed
Date: 2026-07-15

## Context

ADR 013 added a single "show deps + calls" checkbox that hides both
`imports` and `calls` edges together, unchecked by default. It explicitly
deferred splitting that into two independent toggles, with a stated
trigger for revisiting: "add only if dogfooding shows one is wanted without
the other."

Today's dogfooding feedback is exactly that trigger: "now I can't see no
deps or calls, I would like to see only calls." The reviewer wants
symbol-to-symbol call structure (docs/02, "structural context") visible
without the denser file-to-file import edges cluttering the same view.

Current phase is still Phase 2 ("Scale UX ... so big repos open
readable") — same legibility goal ADR 013 served, not a detour.

## Decision

Replace the single `show-edges` checkbox with two independent checkboxes,
**"show imports"** and **"show calls"**, both unchecked by default,
alongside the existing `changed-only` / `hide-tests` toggles in
`static/index.html`.

- `static/app.js` replaces the single `showEdgesView` boolean with
  `showImportsView` and `showCallsView` (both default `false`), each with
  its own setter (`setShowImportsView` / `setShowCallsView`) that
  re-renders from the held `graphData` — same shape as the existing
  `setChangedOnlyView` / `setHideTestsView` / `setShowEdgesView` setters.
- The element-building step (`toElements`, where the current
  `showEdgesView && (e.kind === "imports" || e.kind === "calls")` check
  lives) splits into two independent per-kind checks: an edge with
  `kind === "imports"` is included iff `showImportsView`; an edge with
  `kind === "calls"` is included iff `showCallsView`. Nodes stay untouched.
- No server or model change — same as ADR 013, this is a pure client-side
  display filter over data already in the payload.

This mirrors the exact pattern already used for two other independent
boolean view toggles (`changed-only`, `hide-tests`), so it introduces no
new UI control type or state-management approach.

## Alternatives considered

- **Single select/dropdown** (None / Calls only / Imports only / Both) —
  one control instead of two, but every other toggle in the header is an
  independent checkbox; a dropdown would need new event-handling and
  styling code for no real benefit over two checkboxes, and forecloses a
  future "both, dimmed differently" state more awkwardly than two
  independent booleans would. Rejected — inconsistent with the established
  pattern for no real gain.
- **Keep one checkbox, add a second "calls only" checkbox that overrides
  it** — smaller diff (one new checkbox instead of restructuring the
  filter), but produces a 3-state interaction (both off / combined on /
  calls-only on) that's harder to reason about than two independent
  booleans, and doesn't generalize if a future "imports only" need shows
  up. Rejected — the two-independent-checkboxes model is simpler to reason
  about and was already the documented fallback in ADR 013.

## Consequences

- Reviewers can show call edges without import edges (today's ask), or
  vice versa, or both, or neither — same zero-backend-work shape as ADR
  013.
- `showEdgesView` and the single `show-edges` checkbox/setter from ADR 013
  are removed, not kept alongside the new ones — one filtering concept per
  edge kind, no redundant combined flag.
- Still no persistence across reloads, consistent with every other toggle.

## Out of scope

- Persisting toggle state across reloads — none of the existing toggles
  persist; out until that's a real complaint.
- Any change to Phase 4's change-dependency-edges feature (unbuilt,
  unrelated).
- A third combined-state control (e.g. a single three-way selector) —
  two independent checkboxes cover the reported need.
