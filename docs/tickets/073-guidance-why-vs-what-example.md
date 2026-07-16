# 073. Sharpen SESSION_GUIDANCE with a why-vs-what contrastive example

Status: ready
Decision: docs/decisions/027-rationale-must-justify-not-describe.md

## Goal

`SESSION_GUIDANCE` already states the rule ("why... not what the code
does") but the agent doesn't reliably apply it across a long bullet list.
Add a contrastive example — a "describes" line and a "justifies" line for
the same hypothetical file — so the failure mode is shown directly, not
just stated.

## Acceptance criteria

- `SESSION_GUIDANCE` includes a second example pair: one bullet that only
  describes what a file/symbol does, and one that justifies why the
  change serves the request, for the same hypothetical file — clearly
  labeled so the agent can see the difference, not just read two similar
  examples.
- Existing round-trip test (ticket 041) still passes; the guidance string
  is still parseable by `parse_guidance_bullet` from the primary example.

## Likely files

- `graphwerk/rationale/guidance.py` — `SESSION_GUIDANCE`.

## Out of scope

- Detecting whether a *real* bullet actually complies (ticket 074) — this
  ticket only changes what's asked for.
