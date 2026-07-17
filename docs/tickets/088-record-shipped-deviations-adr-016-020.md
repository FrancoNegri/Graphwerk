# 088. Record shipped deviations in ADR 016/020 and tickets 049/058

Status: done
Decision: docs/audit/runs/001-2026-07-17.md

## Goal

Two deliberate implementation deviations exist only in commit messages and
code comments, so the decision docs now contradict the code they describe
(audit findings F-003/F-004). Both docs get amended in place — the code is
the correct side in F-003, and presumed correct in F-004 pending a
one-question confirmation.

1. ADR 016 / ticket 049: the "affected source → unchanged target ⇒ edge
   status AFFECTED" rule was removed as an over-tagging bug (commit
   cfb4832, pinned by
   `test_calls_edge_to_unrelated_target_from_affected_source_has_unchanged_status`).
2. ADR 020 / ticket 058: `wheelSensitivity` shipped as `5`
   (`static/app.js:280`), not the "lowered to ~0.15–0.2" both docs
   specify.

## Acceptance criteria

- ADR 016 gains a short amendment note (same style as ADR 029's) stating
  the affected-edge branch was removed, why, and which test pins it; the
  no-edge-is-ever-affected behavior is described as current.
- Ticket 049's acceptance criteria are corrected to the shipped rule.
- Confirm with the user that `wheelSensitivity: 5` is the intended feel;
  if yes, amend ADR 020 and ticket 058 to record the shipped value and
  that tuning went up, not down; if no, note that in the docs and file a
  follow-up code ticket instead of changing app.js here.
- No code or test changes (unless the F-004 confirmation says the value
  is wrong — which still only produces a follow-up ticket, not a fix here).

## Likely files

- `docs/decisions/016-call-edge-status.md` — amendment note (doc is the
  wrong side).
- `docs/tickets/049-call-edge-status-model.md` — corrected criteria.
- `docs/decisions/020-edge-hover-reveal-and-zoom-feel.md`,
  `docs/tickets/058-wheel-zoom-feel.md` — record the shipped value.

## Out of scope

- Re-litigating either decision — this records what shipped, it doesn't
  reopen the design.
- Any change to `service.py` or `static/app.js`.
