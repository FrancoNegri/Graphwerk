# 054. Deleted- and added-caller `calls` edges report the source's status, not just the target's

Status: proposed
Date: 2026-07-20

*Amended 2026-07-20:* widened from "source deleted" to "source deleted or
added," after dogfooding the same edge shape in the opposite direction —
`agendabot`'s `_load_business → render_stable_prompt` (new `business.py`
calling unchanged `prompt.py`) read `unchanged` for the identical reason.
`ADDED` is the mirror-image terminal fact to `DELETED`: an added symbol's
calls didn't exist in base at all, just as a deleted symbol's calls no
longer exist in staged. Ticket 150 shipped the `DELETED` half only, as
literally scoped at the time; ticket 152 covers the `ADDED` half under this
same amended decision rather than a new ADR, since the rule and its
rationale are identical, just doubled.

## Context

Dogfooding a split of `webhook.py` into `webhook.py` + `templates.py`
surfaced a `calls` edge, `_build_context → Templates.get`, that read
`unchanged` even though `_build_context` itself was deleted in the split.

`GraphService._mark_edge_status` (ADR 016) computes a `calls` edge's status
purely from its **target**: if the target's status is `MODIFIED`, `ADDED`,
or `DELETED`, the edge takes that status; otherwise it stays `UNCHANGED`.
The source's own status was never consulted — ADR 016 tried exactly that
once, propagating `AFFECTED` source status onto edges, and reverted it
during the same phase as an over-tagging bug: it painted *every* outgoing
edge of an affected node, including calls with no bearing on the change.

`_build_context`'s case is a different shape than the one that was
reverted. `AFFECTED` is diffuse — a node several hops from any real change,
where most outgoing edges genuinely carry no signal. `DELETED` on the
*source* of a `calls` edge is a direct, terminal fact: the call site no
longer exists in staged at all, full stop, for every edge sourced there.
There's no "unrelated call from a deleted node" case the way there was for
`AFFECTED` — every edge out of a deleted symbol represents a call
relationship that's gone.

`ADDED` sources are the same shape, inverted: `_load_business` only exists
in staged (`business.py` is a wholly new file), so every call it makes is
one that didn't exist in base either — equally terminal, equally
unconditional, for the same reason. `MODIFIED` sources deliberately don't
get this treatment: a modified symbol existed in both trees, so any given
call inside it may or may not itself be new, and telling which would need
hunk-to-symbol mapping — the thing CLAUDE.md's differ invariant explicitly
rules out. `DELETED` and `ADDED` need no such mapping because the whole
symbol, and therefore every call it makes, is unconditionally on one side
of the diff only.

Separately, `_add_call_edges` already special-cases a deleted caller: its
`allowed_target_statuses` includes `UNCHANGED` specifically so these edges
keep rendering at all (ADR 032, "reconstruct the old file's former internal
wiring... confirmed during dogfooding that this reading is correct and
useful"). So the edge existing isn't the bug — its label is. The `ADDED`
side has no analogous filter to check: an added caller's calls already come
from `staged_info`, and `allowed_target_statuses` for a non-deleted caller
already includes `UNCHANGED` (service.py's existing `else` branch) — the
edge already renders, only the label is wrong.

This serves docs/02's "blast radius for humans" the same way node status
does: the reviewer shouldn't have to notice on their own that an edge's
source disappeared.

## Decision

`_mark_edge_status` gains a second branch: after the existing
target-status check, if the target isn't itself changed, and the *source*
node's status is `DELETED` or `ADDED`, the edge takes the source's status.

```python
target_status = status_by_id.get(edge.target)
if target_status in CHANGED:
    edge.status = target_status
elif status_by_id.get(edge.source) in {Status.DELETED, Status.ADDED}:
    edge.status = status_by_id[edge.source]
```

Target status still wins when it's itself changed. `MODIFIED` sources are
deliberately excluded (see Context). `imports` edges are untouched (out of
scope per ADR 016).

## Alternatives considered

- **Remove the edge entirely when caller is deleted and target is
  unchanged** — no mislabeling risk since nothing is drawn, but reverses
  ADR 032's deliberate call to keep exactly these edges: they're how the
  graph shows what deleted code used to depend on, independent of whether
  the target itself changed. Cutting only the `deleted → unchanged` subset
  is also an inconsistent carve-out against the `deleted → deleted` /
  `deleted → modified` edges that stay. Rejected — trades away real
  structural-context information to fix what is only a labeling bug.
- **New `Status` value distinct from `DELETED`** for "this relationship is
  severed" vs. "this endpoint is deleted" — more precise, but the
  reviewer's actionable takeaway ("ignore this call, it's gone") is
  identical either way. Adds an enum member and a new `app.js` color
  mapping for no behavioral gain, against CLAUDE.md's minimal-dependency,
  no-speculative-abstraction bias. Rejected.
- **Rely on the source node's own color, no edge change** — zero cost, but
  doesn't fix what was actually reported: clicking a `calls` edge is a
  first-class review action (ADR 016 §3), and the edge's own color is what
  a reviewer reads there, independent of container-collapsed node color.
  Rejected.
- **Also propagate `MODIFIED` source status onto edges** — tempting for
  consistency, but not the same fact: a `MODIFIED` symbol's calls-list
  mixes calls that were already there with any that are genuinely new, and
  distinguishing them needs hunk-to-symbol mapping, which CLAUDE.md rules
  out for this differ. `DELETED`/`ADDED` need no such mapping (see
  Context). Rejected — would silently overclaim precision the differ
  doesn't have.

## Consequences

- A `calls` edge can now become `DELETED` or `ADDED` via two independent
  paths per status: target changed (existing), or source itself
  deleted/added with a non-changed target (new). Each needs its own test
  distinct from the existing target-based ones.
- `test_calls_edge_to_unrelated_target_from_affected_source_has_unchanged_status`
  (the AFFECTED case ADR 016 pinned) is untouched — `AFFECTED` sources
  still get no special edge treatment, only `DELETED`/`ADDED` do.
- No API/model shape change — `GraphEdge.status` already exists.

## Out of scope

- The collapsed-representative-edge status picker
  (`static/app.js` `toElements`, keeps whichever raw call it sees first
  rather than the most severe, unlike node status's
  `strongestDescendantStatusByAncestor`) — a related but separate gap,
  found during this same pass, deferred to its own later north-star pass.
