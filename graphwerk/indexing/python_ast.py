"""Symbol extraction for Python files using the stdlib ast module.

v1 indexes Python only. The FileIndex/SymbolInfo contract is language-neutral,
so a tree-sitter extractor can slot in later for other languages.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator

from graphwerk.indexing.walk import iter_python_files
from graphwerk.models import FileIndex, SymbolInfo


class PythonAstExtractor:
    """Extracts top-level classes/functions and class methods from one file."""

    def extract(self, file_path: Path, rel_path: str) -> FileIndex:
        index = FileIndex(rel_path=rel_path)
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            index.parse_error = f"{type(exc).__name__}: {exc}"
            return index

        lines = source.splitlines(keepends=True)

        for node in _iter_executable_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                index.imports |= _imported_modules(node)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                index.symbols[node.name] = _symbol(node, node.name, "function", lines)
            elif isinstance(node, ast.ClassDef):
                index.symbols[node.name] = _symbol(node, node.name, "class", lines)
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        qualname = f"{node.name}.{child.name}"
                        index.symbols[qualname] = _symbol(child, qualname, "method", lines)
        return index


def _symbol(node: ast.AST, qualname: str, kind: str, lines: list[str]) -> SymbolInfo:
    start, end = node.lineno, node.end_lineno or node.lineno
    return SymbolInfo(
        qualname=qualname,
        kind=kind,
        lineno=start,
        end_lineno=end,
        source="".join(lines[start - 1 : end]),
        calls=_called_names(node),
    )


def _called_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _imported_modules(node: ast.Import | ast.ImportFrom) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}
    return {node.module} if node.module else set()


def _iter_executable_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """Walk the whole tree, skipping the body of `if TYPE_CHECKING:` blocks
    (that code never runs) while still descending into everything else,
    including their `else` branches."""
    yield node
    if isinstance(node, ast.If) and _is_type_checking_guard(node.test):
        for child in node.orelse:
            yield from _iter_executable_nodes(child)
    else:
        for child in ast.iter_child_nodes(node):
            yield from _iter_executable_nodes(child)


def _is_type_checking_guard(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def index_tree(root: Path) -> dict[str, FileIndex]:
    """Index every Python file under a directory tree."""
    extractor = PythonAstExtractor()
    return {rel: extractor.extract(path, rel) for path, rel in iter_python_files(root)}
