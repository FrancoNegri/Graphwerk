# 068. Track and expose rationale confidence per node

Status: done
Decision: docs/decisions/025-rationale-mention-confidence.md

## Goal

Distinguish, per node, rationale text that came from a guidance bullet
(ticket 066) or an explicit prose mention (ticket 067) from text that came
from the proximity fallback (nearest preceding segment, possibly about a
different file) — and expose that distinction on the node so it isn't
presented with false confidence.

## Acceptance criteria

- `RationaleStore` retains, per rationale entry, whether it came from a
  guidance bullet, an explicit prose mention, or the proximity fallback
  (not just the merged string).
- `RationaleStore.why_for` (or a paired accessor) can report this alongside
  the text.
- `GraphNode` carries the confidence alongside `why` (e.g. `why_confident:
  bool`), included in `to_dict()`.
- `GraphService` wires it through for both file- and symbol-level nodes
  (mirrors the existing `why=self.rationale.why_for(...)` call sites in
  `graphwerk/service.py`).
- Reproduces the dogfood case: `deps.py` (no mention anywhere, inherited
  `business.py`'s text) reports low confidence; a file with a genuine
  mention reports high confidence.

## Likely files

- `graphwerk/rationale/miner.py` — `RationaleStore._mine_transcript`,
  `why_for`.
- `graphwerk/models.py` — `GraphNode`.
- `graphwerk/service.py` — wiring at both `why=` call sites.

## Out of scope

- Sidecar-sourced rationale is always explicit/high-confidence (unchanged)
  — this ticket only adds the distinction on the transcript-mined path.
- UI rendering of the flag (ticket 069).
