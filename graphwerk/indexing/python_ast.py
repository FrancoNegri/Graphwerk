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
                modules = _imported_modules(node)
                index.imports |= modules
                statement = ast.get_source_segment(source, node)
                if statement is not None:
                    for module in modules:
                        index.import_statements.setdefault(module, []).append((statement, node.lineno))

        index.imported_names = _module_level_imported_names(tree.body, source)

        module_variable_names, class_attribute_names = _collect_variable_names(tree.body)

        for node in _iter_symbol_definitions(tree.body):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                index.symbols[node.name] = _symbol(
                    node, node.name, "function", lines, uses=_used_global_names(node, module_variable_names)
                )
            elif isinstance(node, ast.ClassDef):
                index.symbols[node.name] = _symbol(
                    node, node.name, "class", lines, calls=_class_body_called_names(node)
                )
                own_class_attributes = class_attribute_names.get(node.name, set())
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        qualname = f"{node.name}.{child.name}"
                        uses = _used_global_names(child, module_variable_names) | _used_self_attribute_names(
                            child, node.name, own_class_attributes
                        )
                        index.symbols[qualname] = _symbol(child, qualname, "method", lines, uses=uses)
                    elif isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                        name = _simple_variable_name(child)
                        if name is not None:
                            qualname = f"{node.name}.{name}"
                            index.symbols[qualname] = _symbol(child, qualname, "variable", lines)
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                name = _simple_variable_name(node)
                if name is not None:
                    index.symbols[name] = _symbol(node, name, "variable", lines)
        return index


def _symbol(
    node: ast.AST,
    qualname: str,
    kind: str,
    lines: list[str],
    calls: set[str] | None = None,
    uses: set[str] | None = None,
) -> SymbolInfo:
    start, end = node.lineno, node.end_lineno or node.lineno
    return SymbolInfo(
        qualname=qualname,
        kind=kind,
        lineno=start,
        end_lineno=end,
        source="".join(lines[start - 1 : end]),
        calls=calls if calls is not None else _called_names(node),
        uses=uses if uses is not None else set(),
    )


def _called_names(node: ast.AST) -> set[str]:
    return _names_from_calls(ast.walk(node))


def _class_body_called_names(node: ast.ClassDef) -> set[str]:
    """A class's own `calls` = calls made directly in its body, not inside
    any method (each method already gets its own `SymbolInfo.calls`, so
    descending into method bodies here would double-count every call site
    as two edges — see ADR 059)."""
    return _names_from_calls(
        sub for statement in node.body for sub in _iter_excluding_nested_defs(statement)
    )


def _iter_excluding_nested_defs(node: ast.AST) -> Iterator[ast.AST]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _iter_excluding_nested_defs(child)


def _names_from_calls(nodes: Iterator[ast.AST]) -> set[str]:
    names: set[str] = set()
    for sub in nodes:
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _collect_variable_names(body: list[ast.stmt]) -> tuple[set[str], dict[str, set[str]]]:
    """Pre-scan for the module-level globals and per-class attribute names
    that ticket 180 already extracts as `variable` symbols, so `uses`
    extraction (below) can check membership regardless of whether a
    function is defined before or after the variable it references in the
    file (ADR 062)."""
    module_names: set[str] = set()
    class_attribute_names: dict[str, set[str]] = {}
    for node in _iter_symbol_definitions(body):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            name = _simple_variable_name(node)
            if name is not None:
                module_names.add(name)
        elif isinstance(node, ast.ClassDef):
            attributes: set[str] = set()
            for child in node.body:
                if isinstance(child, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    name = _simple_variable_name(child)
                    if name is not None:
                        attributes.add(name)
            class_attribute_names[node.name] = attributes
    return module_names, class_attribute_names


def _used_global_names(node: ast.AST, known_module_variable_names: set[str]) -> set[str]:
    """Simple names this function/method body references, in any context,
    that match a tracked module-level variable symbol in the same file."""
    return {
        sub.id for sub in ast.walk(node) if isinstance(sub, ast.Name) and sub.id in known_module_variable_names
    }


def _used_self_attribute_names(node: ast.AST, class_name: str, known_class_attributes: set[str]) -> set[str]:
    """`self.<attr>` accesses whose `<attr>` matches a class-level variable
    symbol on this method's own enclosing class — a `self.foo()` call or a
    genuine instance attribute (unmatched `<attr>`) is excluded."""
    return {
        f"{class_name}.{sub.attr}"
        for sub in ast.walk(node)
        if isinstance(sub, ast.Attribute)
        and isinstance(sub.value, ast.Name)
        and sub.value.id == "self"
        and sub.attr in known_class_attributes
    }


def _simple_variable_name(node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> str | None:
    """The assigned name, or None if the target isn't a single simple `Name`
    (attribute/subscript targets, tuple/list unpacking, or chained
    assignment to more than one target are all skipped — ADR 062)."""
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            return None
        target = node.targets[0]
    else:
        target = node.target
    return target.id if isinstance(target, ast.Name) else None


def _iter_module_level_import_nodes(
    statements: list[ast.stmt],
) -> Iterator[ast.Import | ast.ImportFrom]:
    """Yields Import/ImportFrom nodes directly in `statements`, descending
    into `if`/`elif`/`else` blocks (mirroring `_iter_symbol_definitions`)
    but not into function/class bodies — only module-level (depth-0)
    bindings are attributable (ADR 064)."""
    for statement in statements:
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            yield statement
        elif isinstance(statement, ast.If):
            if not _is_type_checking_guard(statement.test):
                yield from _iter_module_level_import_nodes(statement.body)
            yield from _iter_module_level_import_nodes(statement.orelse)


def _module_level_imported_names(body: list[ast.stmt], source: str) -> dict[str, tuple[str, int]]:
    """Bound name -> (verbatim statement text, 1-based line) for every name a
    module-level import/from-import binds. A name rebound by a later
    module-level statement keeps only the later binding, matching real
    Python name resolution (ADR 064)."""
    bindings: dict[str, tuple[str, int]] = {}
    for node in _iter_module_level_import_nodes(body):
        statement = ast.get_source_segment(source, node)
        if statement is None:
            continue
        for name in _bound_names(node):
            bindings[name] = (statement, node.lineno)
    return bindings


def _bound_names(node: ast.Import | ast.ImportFrom) -> list[str]:
    """The real Python name(s) a single import statement binds: a plain
    `import pkg.sub` binds only the top-level `pkg`; `as`-aliases bind their
    alias instead; a wildcard `from x import *` binds no specific name."""
    if isinstance(node, ast.Import):
        return [alias.asname or alias.name.split(".")[0] for alias in node.names]
    return [alias.asname or alias.name for alias in node.names if alias.name != "*"]


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


def _iter_symbol_definitions(
    statements: list[ast.stmt],
) -> Iterator[
    ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Assign | ast.AnnAssign | ast.AugAssign
]:
    """Yields the FunctionDef/AsyncFunctionDef/ClassDef/Assign/AnnAssign/
    AugAssign nodes directly in `statements`, descending into `if`/`elif`/
    `else` blocks (mirroring the imports pass) but not into function/class
    bodies — a def (or assignment) nested inside an `if` is still a real
    top-level symbol, one nested inside a function is a closure/local and
    stays out of scope."""
    for statement in statements:
        if isinstance(
            statement,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign, ast.AugAssign),
        ):
            yield statement
        elif isinstance(statement, ast.If):
            if not _is_type_checking_guard(statement.test):
                yield from _iter_symbol_definitions(statement.body)
            yield from _iter_symbol_definitions(statement.orelse)


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
