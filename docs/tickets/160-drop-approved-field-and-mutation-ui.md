# 160. Drop `GraphNode.approved` and the approve/commit/discard UI

Status: done
Decision: docs/decisions/058-retire-worktree-single-directory-review.md

## Goal

The snapshot payload and the frontend stop referencing approval, apply,
commit, or discard. The sidebar and session bar keep the read-only review
surface (diff, rationale, code view) and the prompt box, but lose every
affordance that used to write to disk.

## Acceptance criteria

- `GraphNode` no longer has an `approved` field; `/api/graph` payloads
  omit it.
- The sidebar no longer renders an Approve/Unapprove toggle.
- The session bar no longer renders a commit-message box, commit button,
  or discard button, and no longer polls for approved-file counts.
- The prompt box and busy/checks status indicator are unaffected.
- No leftover client-side JS references `approved`, `apply`, `unapprove`,
  `commit`, or `discard`.

## Likely files

- `graphwerk/models.py` — drop `approved` from `GraphNode`.
- `graphwerk/service.py` — drop `ApprovalStore` wiring from
  `GraphService.snapshot()`.
- `static/app.js` — remove approve-toggle, commit-bar, and discard-button
  logic and their fetch calls.
- `static/index.html` (or wherever the sidebar/session-bar markup lives)
  — remove the corresponding DOM elements.

## Out of scope

- Any change to the diff/rationale/code-view rendering itself.
