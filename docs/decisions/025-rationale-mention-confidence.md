# 025. Rationale attribution: prefer the guidance bullet format, tighten the prose fallback, mark confidence

Status: proposed
Date: 2026-07-16

## Context

Dogfooding the agendabot pair (`~/projects/agendabot` /
`agendabot-graphwerk-staging`, see the `agendabot-dogfood-setup` memory)
surfaced a live case of "the why is wrong," diagnosed twice against the
same running session (`482d73ae-...`) as it progressed — the second look,
after the session reached its closing summary, changed the diagnosis.

**First look (session mid-task):** `deps.py`'s `why` was `business.py`'s
text verbatim; `env.py`'s was the content-free opener "Now let's start
building the modules." Neither file was ever named in the narration, so
both silently inherited an unrelated neighbor's text via the proximity
fallback in `RationaleStore._mine_transcript`'s first pass
(`graphwerk/rationale/miner.py:131`).

**Second look (session finished, produced its `SESSION_GUIDANCE` closing
summary — ADR 012 working as designed, one bullet per file):** three
*different* files were now wrong, despite each having a correct, on-topic
bullet sitting right there in the transcript:

| file | shown `why` | its actual (correct, existing) bullet |
|---|---|---|
| `business_cache.py` | test_webhook.py's patch-target note (mentions `` `business_cache._load_business` ``) | "the per-phone TTL cache in front of `_load_business`" |
| `webhook.py` | a trailing "Compatibility note" paragraph that mentions it in passing | "now just the FastAPI `app`, `/health`, and `/webhook/twilio`, wiring the pieces above together" |
| `conversation.py` | the same trailing compatibility note | "pure per-message state/template logic, no I/O" |

Three distinct causes, all inside `attribute_files`/`attribute_symbols`
(`graphwerk/rationale/attribution.py`), which implement ADR 006's rule
"the *latest* segment naming a file is its rationale":

1. **Qualified references count as full mentions.**
   `_distinct_token_pattern` only excludes word-char neighbors, so
   `` `business_cache._load_business` `` matches `business_cache.py` as
   cleanly as a real mention — `business_cache` followed by `.` (a
   non-word char) satisfies the "distinct token" check even though the
   text is about a different file's test patches.
2. **A trailing paragraph outscores the dedicated bullet just by
   appearing later.** `SESSION_GUIDANCE` asks for one bullet per file, but
   agents append prose after the list (a "Compatibility note" mentioning
   several already-covered files again, in passing). "Latest mention wins"
   has no way to prefer the structured, on-topic bullet over trailing
   prose that happens to repeat the filename.
3. **Common English words collide with file stems.** `conversation.py`'s
   stem is `conversation` — an ordinary word, appearing in "the various
   conversation helpers are still re-exported..." with no code-reference
   intent at all. `_distinct_token_pattern`'s word-boundary check doesn't
   distinguish prose usage from a genuine reference.

An initial draft of this ADR proposed excluding qualified references by
requiring the match not be followed by `.<identifier>`. Re-checking it
against the *filename* alternative in `_mention_pattern` (needles include
`rel_path`, `name.name` — e.g. `webhook.py` — and `name.stem`) showed that
fix was itself wrong: `webhook.py`'s own filename **is** "stem, dot,
letters" — indistinguishable from `webhook.get_business` by that rule
alone. Any fix scoped only to the bare-stem alternative, not the
full-filename one, is needed — noted here so the mistake isn't repeated.

`meta.rationale.message` (`RationaleStore.status_message`) stayed `None`
throughout both checks — it only fires on *zero* rationale from *any*
source, so none of this was visible to a reviewer.

Ties back to [02-product-concept.md](../02-product-concept.md)'s per-node
rationale pitch: it lets a reviewer check "does the stated intent match
what the code does" — a *misattributed* why is worse than a missing one,
since it reads as confident and specific while pointing at the wrong
reasoning, and here it happens even when the agent did exactly what
`SESSION_GUIDANCE` asked. In-phase for the same reason ADR 006 and ADR 009
were pulled forward: Phase 2's exit criterion is dogfooding real sessions,
and this is a defect that only shows up by doing that.

## Decision

Layer three changes in `graphwerk/rationale/`, in priority order:

1. **Parse the `SESSION_GUIDANCE` bullet format as the primary rationale
   source.** The format is fixed and known (ADR 012,
   `graphwerk/rationale/guidance.py`): `` - `path/to/file.py` (`Symbol`, ...): reason ``.
   Segments matching it (transcript.py's `_split_segments` already isolates
   list lines as their own segments) are parsed directly into per-file and
   per-symbol rationale — no substring mention-scanning involved, so a
   trailing paragraph that happens to repeat a filename can't outrank the
   file's own bullet. This alone fixes all three second-look cases, since
   every one of those files already had a correct bullet being shadowed.
2. **Tighten the prose-mention fallback**, used only for files with no
   bullet of their own (e.g. mid-session, or an agent that ignores the
   guidance):
   - Scope the qualified-reference exclusion to the bare-stem alternative
     only — a match via the full `name.py` (or full path) alternative is
     always a genuine reference and must not be excluded; only a bare-stem
     match immediately followed by `.<identifier>` is treated as
     incidental.
   - Require the mention to sit inside a backtick-quoted code span.
     Transcript narration consistently backtick-quotes real file/symbol
     references (visible throughout this session's segments) and doesn't
     quote ordinary prose — this directly removes the `conversation`
     common-word collision.
3. **Track and expose per-node rationale confidence**, as originally
   planned: bullet-format and prose-mention attribution both count as
   confident (a segment genuinely names the file); pure proximity fallback
   (no mention anywhere, nearest preceding segment) is marked unconfirmed.
   Surface on `GraphNode` alongside `why` and render as a subdued sidebar
   marker, consuming the field the same way the existing rationale banner
   (ticket 034) consumes `meta.rationale.message` — no new JS logic beyond
   reading the flag.

## Alternatives considered

- **Ignore prose mentions entirely; require the bullet format.** Simpler,
  but the first-look check showed a session with no bullets yet (mid-task,
  retrying after a denied `Bash` call under `acceptEdits` permission mode)
  — a design that only works once the agent reaches the end leaves every
  in-progress session with nothing. Rejected as the sole mechanism; bullet
  parsing is primary but prose fallback stays for the pre-wrap-up window.
- **Do nothing beyond ADR 006, treat this as expected noise.** Rejected —
  the failure now reproduces even when the agent followed
  `SESSION_GUIDANCE` exactly, which is the case this product is supposed
  to handle well.
- **Suppress `why` entirely for proximity-fallback text instead of marking
  confidence.** Throws away real signal (same-batch fallback text is
  sometimes still topically close). Marking confidence keeps "always show
  something" and lets the reviewer judge, consistent with ADR 009's
  fail-loudly philosophy.

## Consequences

- Fixes all three misattributions observed in the completed dogfood
  session, and the two from the mid-session check, without changing
  `SESSION_GUIDANCE` itself.
- Makes the bullet format's structure actually load-bearing — previously
  it was just better-written prose that still went through the same
  mention-scanning as everything else.
- Reviewers get a way to distinguish "the agent said this, about this
  file, specifically" from "nearest available narration" — extends ADR
  009's per-source health signal to per-node granularity.
- Touches `graphwerk/rationale/attribution.py`, `graphwerk/rationale/miner.py`,
  `graphwerk/models.py` (`GraphNode`), `graphwerk/service.py`, and
  `static/app.js` (thin consumption only, per the JS-stays-thin rule).
- Does not touch the differ, apply, or symbol models — no invariant
  conflicts.

## Out of scope

- Sessions that stall before producing any closing summary (the
  mid-session check hit a denied `Bash` call under
  `--agent-permissions acceptEdits`, confirmed in the transcript: "I don't
  have permission to execute test/build commands in this sandbox"; the
  session later recovered and finished on its own). Whether/how to signal
  "this session hasn't finished, rationale may still be in flux" is
  separate — file as a future ticket if it recurs.
- Any change to `SESSION_GUIDANCE`'s requested format (ADR 012) itself.
- Further precision tuning beyond the three concrete false positives found
  here — address if dogfooding turns up more.
