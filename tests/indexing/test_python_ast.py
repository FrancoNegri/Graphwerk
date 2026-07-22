from pathlib import Path

from graphwerk.indexing.python_ast import PythonAstExtractor


def _extract(tmp_path: Path, source: str) -> set[str]:
    path = tmp_path / "mod.py"
    path.write_text(source)
    return PythonAstExtractor().extract(path, "mod.py").imports


def test_top_level_import_is_collected(tmp_path: Path) -> None:
    imports = _extract(tmp_path, "import pkg.mod\n")

    assert imports == {"pkg.mod"}


def test_function_local_import_is_collected(tmp_path: Path) -> None:
    source = """
def f():
    from pkg.mod import Thing
    return Thing
"""
    imports = _extract(tmp_path, source)

    assert imports == {"pkg.mod"}


def test_import_nested_in_method_is_collected(tmp_path: Path) -> None:
    source = """
class C:
    def method(self):
        from pkg.mod import Thing
        return Thing
"""
    imports = _extract(tmp_path, source)

    assert imports == {"pkg.mod"}


def test_import_nested_in_function_inside_function_is_collected(tmp_path: Path) -> None:
    source = """
def outer():
    def inner():
        from pkg.deep import Thing
        return Thing
    return inner
"""
    imports = _extract(tmp_path, source)

    assert imports == {"pkg.deep"}


def test_import_guarded_by_type_checking_name_is_excluded(tmp_path: Path) -> None:
    source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkg.port import Port
"""
    imports = _extract(tmp_path, source)

    assert imports == {"typing"}


def test_import_guarded_by_typing_attribute_is_excluded(tmp_path: Path) -> None:
    source = """
import typing

if typing.TYPE_CHECKING:
    from pkg.port import Port
"""
    imports = _extract(tmp_path, source)

    assert imports == {"typing"}


def test_import_in_plain_conditional_is_still_collected(tmp_path: Path) -> None:
    source = """
import sys

if sys.platform == "win32":
    import pkg.windows_only
"""
    imports = _extract(tmp_path, source)

    assert imports == {"sys", "pkg.windows_only"}


def test_import_in_type_checking_else_branch_is_still_collected(tmp_path: Path) -> None:
    source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkg.port import Port
else:
    import pkg.runtime_fallback
"""
    imports = _extract(tmp_path, source)

    assert imports == {"typing", "pkg.runtime_fallback"}


def test_symbol_extraction_stays_scoped_to_tree_body(tmp_path: Path) -> None:
    source = """
def outer():
    def inner():
        pass
    return inner
"""
    path = tmp_path / "mod.py"
    path.write_text(source)
    index = PythonAstExtractor().extract(path, "mod.py")

    assert set(index.symbols) == {"outer"}


def _extract_symbols(tmp_path: Path, source: str) -> set[str]:
    path = tmp_path / "mod.py"
    path.write_text(source)
    return set(PythonAstExtractor().extract(path, "mod.py").symbols)


def test_function_inside_module_level_if_block_is_indexed(tmp_path: Path) -> None:
    source = """
if TEST_MODE:
    def configure_calendar_slots():
        pass
"""
    assert _extract_symbols(tmp_path, source) == {"configure_calendar_slots"}


def test_class_inside_module_level_if_block_is_indexed_with_method_qualnames(tmp_path: Path) -> None:
    source = """
if TEST_MODE:
    class Config:
        def method(self):
            pass
"""
    assert _extract_symbols(tmp_path, source) == {"Config", "Config.method"}


def test_function_inside_elif_block_is_indexed(tmp_path: Path) -> None:
    source = """
if PLATFORM == "a":
    pass
elif PLATFORM == "b":
    def configure():
        pass
"""
    assert _extract_symbols(tmp_path, source) == {"configure"}


def test_function_inside_else_block_is_indexed(tmp_path: Path) -> None:
    source = """
if PLATFORM == "a":
    pass
else:
    def configure():
        pass
"""
    assert _extract_symbols(tmp_path, source) == {"configure"}


def test_function_inside_nested_if_blocks_is_indexed(tmp_path: Path) -> None:
    source = """
if OUTER:
    if INNER:
        def configure():
            pass
"""
    assert _extract_symbols(tmp_path, source) == {"configure"}


def test_function_inside_type_checking_guard_is_excluded(tmp_path: Path) -> None:
    source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    def only_for_type_checkers():
        pass
"""
    assert _extract_symbols(tmp_path, source) == set()


def test_function_inside_type_checking_else_branch_is_still_indexed(tmp_path: Path) -> None:
    source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    def only_for_type_checkers():
        pass
else:
    def runtime_fallback():
        pass
"""
    assert _extract_symbols(tmp_path, source) == {"runtime_fallback"}


def test_function_defined_inside_an_if_inside_a_function_body_is_not_indexed(tmp_path: Path) -> None:
    """Explicitly out of scope (ticket 168): descending into function/class
    bodies for nested defs would turn closures/local helpers into top-level
    symbols, a different, unscoped change."""
    source = """
def outer():
    if TEST_MODE:
        def inner():
            pass
    return inner
"""
    assert _extract_symbols(tmp_path, source) == {"outer"}


def test_if_nested_function_calls_are_collected(tmp_path: Path) -> None:
    path = tmp_path / "mod.py"
    source = """
if TEST_MODE:
    def configure_calendar_slots():
        return get_calendar()
"""
    path.write_text(source)
    index = PythonAstExtractor().extract(path, "mod.py")

    assert index.symbols["configure_calendar_slots"].calls == {"get_calendar"}


def _extract_statements(tmp_path: Path, source: str) -> dict[str, list[tuple[str, int]]]:
    path = tmp_path / "mod.py"
    path.write_text(source)
    return PythonAstExtractor().extract(path, "mod.py").import_statements


def test_multi_module_import_maps_each_module_to_the_statement(tmp_path: Path) -> None:
    statements = _extract_statements(tmp_path, "import a, b\n")

    assert statements == {"a": [("import a, b", 1)], "b": [("import a, b", 1)]}


def test_from_import_with_alias_keeps_verbatim_statement_text(tmp_path: Path) -> None:
    source = "x = 1\nfrom pkg.mod import name as alias\n"
    statements = _extract_statements(tmp_path, source)

    assert statements == {"pkg.mod": [("from pkg.mod import name as alias", 2)]}


def test_parenthesized_multiline_import_is_captured_whole(tmp_path: Path) -> None:
    source = "from pkg import (a,\n    b)\n"
    statements = _extract_statements(tmp_path, source)

    assert statements == {"pkg": [("from pkg import (a,\n    b)", 1)]}


def test_module_imported_by_two_statements_keeps_both_in_source_order(tmp_path: Path) -> None:
    source = "import pkg.mod\nfrom pkg.mod import Thing\n"
    statements = _extract_statements(tmp_path, source)

    assert statements == {
        "pkg.mod": [("import pkg.mod", 1), ("from pkg.mod import Thing", 2)]
    }


def test_module_imported_at_module_scope_and_inside_two_functions_indexes_three_entries(
    tmp_path: Path,
) -> None:
    source = """import pkg.mod

def one():
    import pkg.mod

def two():
    import pkg.mod
"""
    statements = _extract_statements(tmp_path, source)

    assert statements["pkg.mod"] == [
        ("import pkg.mod", 1),
        ("import pkg.mod", 4),
        ("import pkg.mod", 7),
    ]


def test_class_calls_exclude_method_body_calls(tmp_path: Path) -> None:
    """Ticket 169: a method's own calls shouldn't also be attributed to the
    class symbol, or the same call site produces a duplicate edge."""
    path = tmp_path / "mod.py"
    source = """
class TestOnlyRouter:
    def __init__(self):
        get_calendar()
"""
    path.write_text(source)
    index = PythonAstExtractor().extract(path, "mod.py")

    assert index.symbols["TestOnlyRouter"].calls == set()
    assert index.symbols["TestOnlyRouter.__init__"].calls == {"get_calendar"}


def test_class_body_level_call_is_still_captured_on_the_class_symbol(tmp_path: Path) -> None:
    path = tmp_path / "mod.py"
    source = """
class Config:
    slots = build_default_slots()

    def method(self):
        pass
"""
    path.write_text(source)
    index = PythonAstExtractor().extract(path, "mod.py")

    assert index.symbols["Config"].calls == {"build_default_slots"}
    assert index.symbols["Config.method"].calls == set()


def test_type_checking_guarded_import_has_no_statement(tmp_path: Path) -> None:
    source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkg.port import Port
"""
    statements = _extract_statements(tmp_path, source)

    assert "pkg.port" not in statements


def _extract_index(tmp_path: Path, source: str):
    path = tmp_path / "mod.py"
    path.write_text(source)
    return PythonAstExtractor().extract(path, "mod.py")


def test_module_level_assign_with_simple_name_target_is_a_variable_symbol(tmp_path: Path) -> None:
    index = _extract_index(tmp_path, "_CACHE = {}\n")

    symbol = index.symbols["_CACHE"]
    assert symbol.kind == "variable"
    assert symbol.lineno == 1
    assert symbol.end_lineno == 1
    assert symbol.source == "_CACHE = {}\n"


def test_module_level_annassign_with_simple_name_target_is_a_variable_symbol(tmp_path: Path) -> None:
    index = _extract_index(tmp_path, "TIMEOUT: int = 30\n")

    symbol = index.symbols["TIMEOUT"]
    assert symbol.kind == "variable"
    assert symbol.source == "TIMEOUT: int = 30\n"


def test_module_level_augassign_with_simple_name_target_is_a_variable_symbol(tmp_path: Path) -> None:
    index = _extract_index(tmp_path, "COUNTER += 1\n")

    assert index.symbols["COUNTER"].kind == "variable"


def test_class_level_assign_with_simple_name_target_is_a_variable_symbol(tmp_path: Path) -> None:
    source = """
class Config:
    TIMEOUT = 30

    def method(self):
        pass
"""
    index = _extract_index(tmp_path, source)

    symbol = index.symbols["Config.TIMEOUT"]
    assert symbol.kind == "variable"
    assert symbol.source.strip() == "TIMEOUT = 30"


def test_class_level_annassign_with_simple_name_target_is_a_variable_symbol(tmp_path: Path) -> None:
    source = """
class Config:
    timeout: int = 30
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["Config.timeout"].kind == "variable"


def test_module_level_attribute_assignment_target_is_skipped(tmp_path: Path) -> None:
    assert _extract_symbols(tmp_path, "obj.x = 1\n") == set()


def test_module_level_subscript_assignment_target_is_skipped(tmp_path: Path) -> None:
    assert _extract_symbols(tmp_path, 'd["k"] = 1\n') == set()


def test_module_level_tuple_unpacking_assignment_is_skipped(tmp_path: Path) -> None:
    assert _extract_symbols(tmp_path, "a, b = 1, 2\n") == set()


def test_module_level_list_unpacking_assignment_is_skipped(tmp_path: Path) -> None:
    assert _extract_symbols(tmp_path, "[a, b] = [1, 2]\n") == set()


def test_class_level_attribute_assignment_target_is_skipped(tmp_path: Path) -> None:
    source = """
class C:
    self.x = 1
"""
    assert _extract_symbols(tmp_path, source) == {"C"}


def test_class_level_subscript_assignment_target_is_skipped(tmp_path: Path) -> None:
    source = """
class C:
    d["k"] = 1
"""
    assert _extract_symbols(tmp_path, source) == {"C"}


def test_class_level_tuple_unpacking_assignment_is_skipped(tmp_path: Path) -> None:
    source = """
class C:
    a, b = 1, 2
"""
    assert _extract_symbols(tmp_path, source) == {"C"}


def test_assignment_inside_function_body_does_not_produce_variable_symbol(tmp_path: Path) -> None:
    source = """
def f():
    x = 1
    return x
"""
    assert _extract_symbols(tmp_path, source) == {"f"}


def test_assignment_inside_method_body_does_not_produce_variable_symbol(tmp_path: Path) -> None:
    source = """
class C:
    def method(self):
        x = 1
        return x
"""
    assert _extract_symbols(tmp_path, source) == {"C", "C.method"}


def test_assignment_inside_nested_function_body_does_not_produce_variable_symbol(tmp_path: Path) -> None:
    source = """
def outer():
    def inner():
        y = 1
        return y
    return inner
"""
    assert _extract_symbols(tmp_path, source) == {"outer"}


def test_module_level_function_reading_a_tracked_global_by_name_has_it_in_uses(tmp_path: Path) -> None:
    source = """
_CACHE = {}

def read_cache():
    return _CACHE
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["read_cache"].uses == {"_CACHE"}


def test_module_level_function_mutating_a_tracked_global_via_global_statement_has_it_in_uses(
    tmp_path: Path,
) -> None:
    source = """
_CACHE = {}

def store(key, value):
    global _CACHE
    _CACHE[key] = value
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["store"].uses == {"_CACHE"}


def test_module_level_function_referencing_an_untracked_free_name_has_empty_uses(tmp_path: Path) -> None:
    source = """
def f():
    return unknown_name
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["f"].uses == set()


def test_method_accessing_self_attr_matching_a_class_level_variable_has_it_in_uses(tmp_path: Path) -> None:
    source = """
class Config:
    TIMEOUT = 30

    def get_timeout(self):
        return self.TIMEOUT
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["Config.get_timeout"].uses == {"Config.TIMEOUT"}


def test_method_accessing_a_genuine_instance_attribute_does_not_add_it_to_uses(tmp_path: Path) -> None:
    source = """
class Widget:
    def __init__(self):
        self.name = "x"

    def get_name(self):
        return self.name
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["Widget.get_name"].uses == set()


def test_method_calling_another_method_via_self_does_not_add_it_to_uses(tmp_path: Path) -> None:
    source = """
class Service:
    def helper(self):
        return 1

    def run(self):
        return self.helper()
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["Service.run"].calls == {"helper"}
    assert index.symbols["Service.run"].uses == set()


def test_function_calling_another_function_does_not_add_it_to_uses(tmp_path: Path) -> None:
    source = """
def helper():
    return 1

def run():
    return helper()
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["run"].calls == {"helper"}
    assert index.symbols["run"].uses == set()


def test_variable_symbols_have_empty_uses_by_default(tmp_path: Path) -> None:
    index = _extract_index(tmp_path, "_CACHE = {}\n")

    assert index.symbols["_CACHE"].uses == set()


def test_class_symbol_itself_has_empty_uses(tmp_path: Path) -> None:
    source = """
class Config:
    TIMEOUT = 30
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["Config"].uses == set()


def test_method_uses_combines_own_class_attribute_and_module_level_global(tmp_path: Path) -> None:
    source = """
_LIMIT = 10

class Config:
    TIMEOUT = 30

    def check(self):
        return self.TIMEOUT + _LIMIT
"""
    index = _extract_index(tmp_path, source)

    assert index.symbols["Config.check"].uses == {"Config.TIMEOUT", "_LIMIT"}
