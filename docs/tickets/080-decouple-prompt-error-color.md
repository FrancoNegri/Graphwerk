# 080. Decouple `#prompt-error` from the status palette

Status: done
Decision: docs/decisions/030-status-palette-modified-green-deleted-red.md

## Goal

The inline prompt-error text in the header prompt bar stays red regardless
of what `--modified` is set to. Today it reads `color: var(--modified)`
purely because `--modified` happened to be red — a coincidental coupling
between "error text" and "modified-status color" that ticket 079 breaks
(error text would otherwise turn green).

## Acceptance criteria

- A new `--danger: #ef4444` custom property exists in `:root` in
  `static/style.css`.
- `#prompt-error` reads `color: var(--danger)` instead of
  `var(--modified)`.
- Prompt-error text renders red after ticket 079 lands (i.e. verify by
  triggering a prompt error in the running UI, not just reading the CSS).
- No other selector currently reading `var(--modified)` is touched by this
  ticket (`.dot.modified`, `.chip.modified` are status-palette consumers,
  not this bug).

## Likely files

- `static/style.css` — add `--danger`, repoint `#prompt-error`.

## Out of scope

- `button.danger` already hardcodes its own dark red (`#7f1d1d`) rather
  than reading any custom property — it isn't coupled to `--modified` and
  doesn't need touching.
- Any other palette value (ticket 079, ticket 078).
