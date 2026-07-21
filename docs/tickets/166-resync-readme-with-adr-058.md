# 166. Resync README.md with ADR 058 (and the reject-UI removal before it)

Status: done
Decision: docs/audit/runs/002-2026-07-21.md

## Goal

`README.md` describes graphwerk as it works today: a review lens over the
developer's own git working directory, not a staging layer with apply/
reject/worktree machinery (audit finding F-011).

## Acceptance criteria

- Intro paragraph no longer says changes "land in the graph first ...
  instead of on disk" or are "applied ... node by node" — per ADR 058,
  changes are on disk directly; there's no apply step.
- Quickstart no longer says to "Reject it with a comment" — that UI was
  removed by ticket 156, independent of ADR 058.
- Quickstart's `serve`/`start` examples use `--repo`/`--base-ref`, not
  `--base`/`--staged` (removed by ticket 158).
- The Layout section's `staging/` line no longer calls it a "shadow
  workspace (git worktree)".
- The Status section reflects the current state (ADR 058 retired the
  worktree/apply/commit/discard engine; docs/04's Phase 4 is retired, not
  pending).

## Likely files

- `README.md` — all of the above; it's the doc that's wrong, not the code.

## Out of scope

- Rewriting the Quickstart's description of Apply/Reject buttons in the
  demo screenshot-equivalent walkthrough to match whatever ticket 159
  leaves behind — ticket 159 (deletes the mutation engines and endpoints)
  is still `ready`/unimplemented, so describe today's actual behavior
  only; a follow-up doc pass after ticket 159 lands is expected, not a
  reason to guess at it now.
