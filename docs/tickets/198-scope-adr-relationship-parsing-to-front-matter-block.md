# 198. Scope ADR-relationship parsing to the front-matter block

Status: done
Decision: docs/decisions/065-decision-lineage-graph.md

## Goal

`Supersedes:`/`Amends:`/`Extends:` lines are only parsed from the fixed
three-line block directly under an ADR's `Status:`/`Date:` header — not
from anywhere else in the document body, such as a fenced code-block
example. Right now `_ADR_RELATIONSHIP_LINE` scans the whole file with
`re.MULTILINE`, so ADR 065's own Decision section — which quotes the
convention as a `Supersedes: 037, 050` / `Amends: 058` / `Extends: 005`
example to explain the syntax — gets parsed as ADR 065 declaring those
relationships about itself. This is exactly the "false positive from
prose mentioning an ADR number" failure mode ADR 065's own Alternatives
section rejected; it just crept back in at the implementation level.

Also fix `_repo_root()`, which currently assumes a file's on-disk path
mirrors its repo-relative path. That's only true for `WorkingTreeRevision`
reads; a `GitRefRevision` materializes blob content to a flat temp file
(`_extract_from_bytes` in `differ.py`), so walking up `len(rel_path.parts)`
parents from that temp path lands somewhere bogus and every relationship
target silently fails to resolve (logged as "not found" even though the
file exists). This doesn't corrupt today's default live comparison (staged
is the working tree and wins in `change.staged or change.base`), but it
breaks ADR-lineage edges for any comparison where the ADR file isn't read
from the working tree (ADR 060's any-ref-vs-any-ref), and spams warnings
on every snapshot.

## Acceptance criteria

- Parsing ADR 065's own file produces no `supersedes`/`amends`/`extends`
  edges sourced from it — its fenced-block example text is not treated as
  a real declaration.
- Every currently-real relationship still parses: `015->002`, `030->029`,
  `042->037`, `050->037`, `058->037`, `058->050`, `061->058` (amends),
  `025->009` (extends), `041->005` (extends).
- A `Supersedes:`/`Amends:`/`Extends:`-shaped line inside a fenced code
  block anywhere in an ADR (not just 065's) is ignored, not just the one
  current example — this should be a structural fix (only look at the
  block right after `Status:`/`Date:`), not a special case for 065.
- Resolving a relationship target works identically whether the ADR is
  read via `WorkingTreeRevision` or `GitRefRevision` — no spurious "not
  found" warnings for a target that exists on disk.

## Likely files

- `graphwerk/indexing/markdown.py` — `_extract_adr_relationships` (scope
  the scan to the header block, not the whole `source`), `_repo_root`
  (stop relying on `file_path` mirroring `rel_path`; the extractor already
  receives `rel_path` as ground truth for repo-relative location — resolve
  targets via `INDEXABLE ` repo-relative globbing that doesn't depend on
  `file_path`'s own directory depth).
- `tests/indexing/test_markdown_extractor.py` — add cases: a fenced-block
  example that must not parse as a real relationship; a relationship line
  positioned after the header block that must not parse either (proves the
  fix is structural, not `source.startswith` on the whole file).

## Out of scope

- Any change to which three relationship kinds exist, or their semantics —
  ADR 065 stands as decided.
- Linting/enforcing that ADRs use the convention correctly (ADR 065 already
  left this advisory).
