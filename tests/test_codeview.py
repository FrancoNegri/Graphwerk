from graphwerk.codeview import CodeLine, build_code_view, merge_lines


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


def test_changed_string_shows_old_spans_on_del_and_new_spans_on_add():
    base = 'msg = "bye"\n'
    staged = 'msg = "hello there"\n'

    del_line, add_line = build_code_view(base, staged)
    assert del_line["op"] == "del"
    assert del_line["spans"] == [[6, 11, "str"]]
    assert add_line["op"] == "add"
    assert add_line["spans"] == [[6, 19, "str"]]


def test_del_spans_looked_up_beyond_staged_length():
    base = "x = 1\ny = 2\nz = 3\n"
    staged = "x = 1\n"

    view = build_code_view(base, staged)
    assert [entry["op"] for entry in view] == ["ctx", "del", "del"]
    assert view[1]["spans"] == [[4, 5, "num"]]
    assert view[2]["spans"] == [[4, 5, "num"]]


def test_syntax_error_text_keeps_diff_ops_with_empty_spans():
    base = 'value = "closed"\n'
    staged = 'value = "unterminated\nextra = 1\n'

    view = build_code_view(base, staged)
    assert [entry["op"] for entry in view] == ["del", "add", "add"]
    assert view[0]["spans"] == [[8, 16, "str"]]  # base still highlights
    assert view[1]["spans"] == []
    assert view[2]["spans"] == []


def test_unchanged_node_view_is_all_context_and_highlighted():
    text = "def greet():\n    return 1\n"

    assert build_code_view(text, text) == [
        {
            "text": "def greet():",
            "op": "ctx",
            "line": 1,
            "spans": [[0, 3, "kw"], [4, 9, "def"]],
        },
        {
            "text": "    return 1",
            "op": "ctx",
            "line": 2,
            "spans": [[4, 10, "kw"], [11, 12, "num"]],
        },
    ]
