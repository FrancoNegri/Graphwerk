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
