# 135. Frontend: design-mode dialogue box

Status: ready
Decision: docs/decisions/047-design-scope-guidance-and-dialogue.md

## Goal

Give the user somewhere to see a design-mode session's reply. Scoped
strictly to the Design side of the domain-mode toggle (`static/
index.html`, ticket 130) — Implementation mode's prompt box stays exactly
as ADR 011 specified: input-only, no reply ever rendered.

## Acceptance criteria

- A new dialogue panel in `static/index.html`, hidden unless
  `domainModeView === "design"` (same visibility pattern the toggle
  already drives for graph filtering).
- `static/app.js`'s prompt-submit handler, when `domainModeView ===
  "design"` and the response includes a non-empty `reply`, appends
  `{prompt, reply}` to a client-side, in-memory array and re-renders the
  panel as a scrollable list (most recent last). Implementation mode:
  unchanged, nothing appended, nothing rendered.
- The array resets on a fresh `start()` call (new session) and is
  preserved across `continue_session` calls (same session, next turn) —
  matches how `completedSessionId` already distinguishes a new session
  from a continuation.
- No new backend endpoint, no persistence beyond the page's lifetime — a
  reload clears the panel (consistent with ADR 047's "client-side only"
  decision).
- Switching the toggle from Design to Implementation and back does not
  lose the accumulated array (it's just hidden, not cleared) — only a new
  `start()` clears it.

## Likely files

- `static/index.html` — dialogue panel markup.
- `static/app.js` — accumulation + render, wired into the existing
  `prompt-form` submit handler and `setDomainModeView`.
- `static/style.css` (or wherever existing panel styling lives) — minimal
  styling consistent with the existing session-bar/banner components.

## Out of scope

- Any implementation-mode UI change.
- Streaming/incremental rendering — the reply appears once the turn
  settles (existing polling model).
- Persisting the dialogue server-side (ADR 047, Out of scope).
