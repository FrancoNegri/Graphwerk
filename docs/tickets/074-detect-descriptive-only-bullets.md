# 074. Detect purely-descriptive guidance bullets

Status: ready
Decision: docs/decisions/027-rationale-must-justify-not-describe.md

## Goal

A guidance-bullet or prose-mention rationale (already `why_confident`)
whose reason text has no causal/justifying connective is very likely
describing the code rather than justifying the change. Detect this and
expose it as a separate node-level signal, distinct from attribution
confidence.

## Acceptance criteria

- A function checks a reason string for at least one justifying connective
  (case-insensitive, whole-word/phrase): `because`, `since`, `so that`,
  `so it`, `in order to`, `to avoid`, `given that`, `which lets`, `which
  allows`. Present → justifies; absent → describes-only.
- Only evaluated when the rationale is already confident (a real bullet or
  mention) — not applied to proximity-fallback text, which is already
  flagged low-confidence for a different reason.
- `RationaleStore` (or the attribution layer) exposes this per entry;
  `GraphNode` carries it alongside `why`/`why_confident` (e.g.
  `why_justifies: bool | None`, `None` when there's no confident why to
  evaluate).
- Regression cases from the dogfood session: `deps.py`'s "FastAPI
  dependency-injection providers." → `why_justifies: False`. `flags.py`'s
  "shared env-derived flags, split out since several other modules need
  them." → `why_justifies: True`.

## Likely files

- `graphwerk/rationale/attribution.py` or `graphwerk/rationale/miner.py` —
  the connective-detection function.
- `graphwerk/models.py` — `GraphNode`.
- `graphwerk/service.py` — wiring at both `why=` call sites.
- `tests/rationale/test_attribution.py` (or `test_miner.py`).

## Out of scope

- UI rendering (ticket 075).
- The guidance-text change (ticket 073).
- Any LLM-based judgment of rationale quality (deferred per ADR 027).
