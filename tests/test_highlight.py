from graphwerk.highlight import highlight_lines


def spans_by_class(line_spans: list[tuple[int, int, str]]) -> dict[str, list[tuple[int, int]]]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for start_col, end_col, cls in line_spans:
        grouped.setdefault(cls, []).append((start_col, end_col))
    return grouped


def test_keywords_and_def_names():
    source = "def greet(name):\n    return name\n"
    lines = highlight_lines(source)

    assert len(lines) == 2
    assert (0, 3, "kw") in lines[0]
    assert (4, 9, "def") in lines[0]
    assert (4, 10, "kw") in lines[1]


def test_class_name_classified_as_def():
    source = "class Greeter:\n    pass\n"
    lines = highlight_lines(source)

    assert (0, 5, "kw") in lines[0]
    assert (6, 13, "def") in lines[0]


def test_single_line_string():
    lines = highlight_lines('greeting = "hello"\n')

    assert lines[0] == [(11, 18, "str")]


def test_fstring_parts_are_strings_and_interpolations_keep_their_class():
    lines = highlight_lines('message = f"total is {count} items"\n')

    grouped = spans_by_class(lines[0])
    covered = set()
    for start_col, end_col in grouped["str"]:
        covered.update(range(start_col, end_col))
    assert {10, 11} <= covered  # f" prefix
    assert set(range(12, 21)) <= covered  # literal text before the interpolation
    assert set(range(28, 35)) <= covered  # literal text after, plus closing quote
    assert covered.isdisjoint(range(22, 27))  # `count` is not string-classified


def test_multiline_string_spans_every_line_it_covers():
    source = 'doc = """first\nsecond line\nlast"""\n'
    lines = highlight_lines(source)

    assert lines[0] == [(6, 14, "str")]
    assert lines[1] == [(0, 11, "str")]
    assert lines[2] == [(0, 7, "str")]


def test_comments_and_numbers():
    lines = highlight_lines("limit = 42  # answer\nratio = 3.5e-2\n")

    assert (8, 10, "num") in lines[0]
    assert (12, 20, "com") in lines[0]
    assert (8, 14, "num") in lines[1]


def test_unclassified_text_gets_no_span():
    lines = highlight_lines("value = other\n")

    assert lines == [[]]


def test_unterminated_string_returns_empty_spans_for_all_lines():
    source = 'def broken():\n    text = "unterminated\n'

    assert highlight_lines(source) == [[], []]


def test_bad_indentation_returns_empty_spans_for_all_lines():
    source = "if x:\n    a = 1\n  b = 2\n"

    assert highlight_lines(source) == [[], [], []]


def test_binary_junk_never_raises():
    source = "\x00\x01\x02 not python \xff\n\x00\n"

    assert highlight_lines(source) == [[], []]


def test_empty_source():
    assert highlight_lines("") == []
