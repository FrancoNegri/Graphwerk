# 009. Rationale fails loudly: source status in the payload + misplaced-session hint

Status: proposed
Date: 2026-07-15

## Context

First real dogfood of the rationale pipeline on agendabot (July 2026): the
reviewer saw no "why" on any changed node and had no way to tell why. Root
cause was wiring, not mining — `graphwerk start` created the staging
worktree and printed `cd <staging> && claude`, but the session was run in
the main repo anyway. The agent's edits landed in the *base* tree, the
worktree stayed clean, statuses rendered inverted (a newly added test showed
as deleted), and transcript discovery — which only probes the staged root's
encoded project dir under `~/.claude/projects/` — found nothing. Every part
of that failed **silently**: no server log, no payload field, no UI hint.
(The scripted demo, which uses a sidecar, still shows rationale — the
mining code from ADR 006 is healthy.)

Per-node rationale is a core pillar of the product concept (docs/02), and
Phase 2's exit criterion (docs/04) is reviewing a real session end to end.
A pipeline that degrades to nothing without a signal blocks that criterion:
the human can't distinguish "the session had no narration" from "graphwerk
never found the session".

## Decision

Make the rationale pipeline report what it found, end to end, and hint at
the one failure mode dogfooding has already produced:

1. **Snapshot meta.** The snapshot payload gains a `meta.rationale` block:
   which sidecar (if any) was loaded, which transcript path (if any) was
   discovered or passed, how many rationale entries were mined, and an
   optional human-readable `warning`. `RationaleStore` exposes this after
   `reload()`; `GraphService` copies it into the snapshot.
2. **Misplaced-session hint.** When no transcript exists for the staged
   root, discovery additionally probes the *base* root's project dir. If a
   transcript there has edit events resolving inside the base tree, the
   meta warning says so plainly: the session edited the base tree — run the
   agent in the staging worktree (or check whether `--base`/`--staged` are
   swapped). The base-tree transcript is *never* silently adopted as a
   rationale source; it only powers the warning.
3. **UI banner.** When changed nodes exist but no rationale source was
   found — or a warning is present — the UI shows a one-line status banner
   rendering the server-provided message. The JS only displays payload
   fields (ADR 005 split); all detection logic and wording live in Python.

## Alternatives considered

- **Document the flow harder (README/start output) and change nothing** —
  zero code, but `start` already prints the correct instruction and the
  dogfood run skipped it anyway; silence is the defect. Rejected.
- **Auto-widen discovery: scan all `~/.claude/projects/` dirs for a
  transcript whose edits fall inside the staged root** — magic recovery,
  but can latch onto the wrong session, and in the observed failure the
  session's edits are in the *base* tree, so widening would have found
  nothing anyway (or worse, mined a stale session). The deterministic
  subset that explains the observed failure — probe the base root, warn —
  is kept; the rest is rejected.
- **Refuse to serve when the wiring looks wrong** — a swapped setup still
  renders a useful graph (diffs, blast radius); blocking punishes partial
  use. Warn, don't block. Rejected.

## Consequences

- "No rationale" becomes a diagnosable state: the payload says what was
  probed and what was found, and the UI says it in one line instead of
  silently hiding the why-section.
- The observed dogfood failure (session run in the main repo) produces an
  explicit, actionable message on the very first snapshot.
- The snapshot payload grows a `meta` block — additive, no existing field
  changes; the state-hash/polling contract is untouched.
- Touches no invariant: worktree flow is reinforced (the warning steers the
  agent back into it), logic stays in Python, JS stays a consumer, no new
  dependency.

## Out of scope

- Auto-adopting a base-tree transcript as the rationale source (never —
  it would legitimize the inverted flow the warning exists to correct).
- Detecting swapped `--base`/`--staged` from tree timestamps or git state
  (heuristic, git-dependent; the transcript-based hint covers the observed
  case deterministically).
- Post-hoc summarization of weak narration (roadmap Phase 5, per ADR 006).
- Agent activity indicator fed by transcript tailing (roadmap Phase 3).
