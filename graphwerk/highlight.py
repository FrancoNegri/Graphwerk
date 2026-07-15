"""Classify Python source into per-line highlight spans via stdlib tokenize."""

import io
import keyword
import tokenize

Span = tuple[int, int, str]

_DEF_INTRODUCERS = {"def", "class"}
_STRING_TOKEN_TYPES = {
    tokenize.STRING,
    tokenize.FSTRING_START,
    tokenize.FSTRING_MIDDLE,
    tokenize.FSTRING_END,
}


def highlight_lines(source: str) -> list[list[Span]]:
    source_lines = source.splitlines()
    try:
        return _spans_from_tokens(source_lines, source)
    except (tokenize.TokenError, SyntaxError):
        # Mid-edit saves often don't tokenize; render plain rather than break.
        return [[] for _ in source_lines]


def _spans_from_tokens(source_lines: list[str], source: str) -> list[list[Span]]:
    line_spans: list[list[Span]] = [[] for _ in source_lines]
    expecting_def_name = False
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NAME:
            if expecting_def_name:
                span_class = "def"
            elif keyword.iskeyword(token.string):
                span_class = "kw"
            else:
                span_class = None
            expecting_def_name = token.string in _DEF_INTRODUCERS
        elif token.type in _STRING_TOKEN_TYPES:
            span_class = "str"
        elif token.type == tokenize.COMMENT:
            span_class = "com"
        elif token.type == tokenize.NUMBER:
            span_class = "num"
        else:
            span_class = None
        if span_class is None:
            continue
        first_row, first_col = token.start[0] - 1, token.start[1]
        last_row, last_col = token.end[0] - 1, token.end[1]
        for row in range(first_row, last_row + 1):
            start_col = first_col if row == first_row else 0
            end_col = last_col if row == last_row else len(source_lines[row])
            line_spans[row].append((start_col, end_col, span_class))
    return line_spans
