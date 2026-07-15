from graphwerk.codeview import CodeLine, merge_lines


def test_identical_texts_are_all_context():
    text = "def greet():\n    return 1\n"

    assert merge_lines(text, text) == [
        CodeLine("def greet():", "ctx", 1),
        CodeLine("    return 1", "ctx", 2),
    ]


def test_mid_file_modification_interleaves_removed_line_in_place():
    base = "a = 1\nb = 2\nc = 3\n"
    staged = "a = 1\nb = 20\nc = 3\n"

    assert merge_lines(base, staged) == [
        CodeLine("a = 1", "ctx", 1),
        CodeLine("b = 2", "del", 2),
        CodeLine("b = 20", "add", 2),
        CodeLine("c = 3", "ctx", 3),
    ]


def test_origin_line_numbers_diverge_after_an_insertion():
    base = "a = 1\nz = 9\n"
    staged = "a = 1\nnew = 5\nother = 6\nz = 9\n"

    assert merge_lines(base, staged) == [
        CodeLine("a = 1", "ctx", 1),
        CodeLine("new = 5", "add", 2),
        CodeLine("other = 6", "add", 3),
        CodeLine("z = 9", "ctx", 4),
    ]


def test_pure_deletion_keeps_base_numbering_on_removed_lines():
    base = "a = 1\ngone = 0\nalso_gone = 0\nz = 9\n"
    staged = "a = 1\nz = 9\n"

    assert merge_lines(base, staged) == [
        CodeLine("a = 1", "ctx", 1),
        CodeLine("gone = 0", "del", 2),
        CodeLine("also_gone = 0", "del", 3),
        CodeLine("z = 9", "ctx", 2),
    ]


def test_replace_block_emits_all_dels_then_all_adds():
    base = "keep\nold_one\nold_two\nkeep_end\n"
    staged = "keep\nnew_one\nnew_two\nnew_three\nkeep_end\n"

    ops = [(line.op, line.text) for line in merge_lines(base, staged)]
    assert ops == [
        ("ctx", "keep"),
        ("del", "old_one"),
        ("del", "old_two"),
        ("add", "new_one"),
        ("add", "new_two"),
        ("add", "new_three"),
        ("ctx", "keep_end"),
    ]


def test_missing_base_is_all_added():
    expected = [CodeLine("a = 1", "add", 1), CodeLine("b = 2", "add", 2)]

    assert merge_lines(None, "a = 1\nb = 2\n") == expected
    assert merge_lines("", "a = 1\nb = 2\n") == expected


def test_missing_staged_is_all_removed():
    expected = [CodeLine("a = 1", "del", 1), CodeLine("b = 2", "del", 2)]

    assert merge_lines("a = 1\nb = 2\n", None) == expected
    assert merge_lines("a = 1\nb = 2\n", "") == expected


def test_both_empty_is_empty():
    assert merge_lines(None, None) == []
    assert merge_lines("", "") == []
