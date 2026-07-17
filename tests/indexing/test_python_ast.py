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


def _extract_statements(tmp_path: Path, source: str) -> dict[str, tuple[str, int]]:
    path = tmp_path / "mod.py"
    path.write_text(source)
    return PythonAstExtractor().extract(path, "mod.py").import_statements


def test_multi_module_import_maps_each_module_to_the_statement(tmp_path: Path) -> None:
    statements = _extract_statements(tmp_path, "import a, b\n")

    assert statements == {"a": ("import a, b", 1), "b": ("import a, b", 1)}


def test_from_import_with_alias_keeps_verbatim_statement_text(tmp_path: Path) -> None:
    source = "x = 1\nfrom pkg.mod import name as alias\n"
    statements = _extract_statements(tmp_path, source)

    assert statements == {"pkg.mod": ("from pkg.mod import name as alias", 2)}


def test_parenthesized_multiline_import_is_captured_whole(tmp_path: Path) -> None:
    source = "from pkg import (a,\n    b)\n"
    statements = _extract_statements(tmp_path, source)

    assert statements == {"pkg": ("from pkg import (a,\n    b)", 1)}


def test_module_imported_by_two_statements_keeps_the_first(tmp_path: Path) -> None:
    source = "import pkg.mod\nfrom pkg.mod import Thing\n"
    statements = _extract_statements(tmp_path, source)

    assert statements == {"pkg.mod": ("import pkg.mod", 1)}


def test_type_checking_guarded_import_has_no_statement(tmp_path: Path) -> None:
    source = """
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pkg.port import Port
"""
    statements = _extract_statements(tmp_path, source)

    assert "pkg.port" not in statements
