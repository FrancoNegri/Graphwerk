import json

import pytest

from graphwerk.hooks.scope_guard import is_allowed, main


@pytest.mark.parametrize("path", [
    "graphwerk/service.py",
    "docs/decisions/046-x.md",
    "src/pkg/nested/module.py",
    "docs/tickets/nested/deep/ticket.md",
])
def test_unscoped_allows_any_path(path):
    assert is_allowed(None, path) is True


@pytest.mark.parametrize("path", ["docs/decisions/046-x.md", "notes.md", "a/b/c/deep.md"])
def test_design_scope_allows_markdown_paths(path):
    assert is_allowed("design", path) is True


@pytest.mark.parametrize("path", ["graphwerk/service.py", "static/app.js", "a/b/c/deep.py"])
def test_design_scope_denies_non_markdown_paths(path):
    assert is_allowed("design", path) is False


@pytest.mark.parametrize("path", ["graphwerk/service.py", "static/app.js", "a/b/c/deep.py"])
def test_implementation_scope_allows_non_markdown_paths(path):
    assert is_allowed("implementation", path) is True


@pytest.mark.parametrize("path", ["docs/decisions/046-x.md", "notes.md", "a/b/c/deep.md"])
def test_implementation_scope_denies_markdown_paths(path):
    assert is_allowed("implementation", path) is False


def _run_main(monkeypatch, capsys, payload, scope=None):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(payload)))
    if scope is None:
        monkeypatch.delenv("GRAPHWERK_SCOPE", raising=False)
    else:
        monkeypatch.setenv("GRAPHWERK_SCOPE", scope)
    main()
    return json.loads(capsys.readouterr().out)


def test_main_allows_a_markdown_edit_in_design_scope(monkeypatch, capsys):
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "/repo/docs/x.md"}}

    output = _run_main(monkeypatch, capsys, payload, scope="design")

    assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_main_denies_a_python_write_in_design_scope_with_a_reason(monkeypatch, capsys):
    payload = {"tool_name": "Write", "tool_input": {"file_path": "/repo/graphwerk/service.py"}}

    output = _run_main(monkeypatch, capsys, payload, scope="design")

    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert output["hookSpecificOutput"]["permissionDecisionReason"]


def test_main_allows_anything_when_no_scope_env_var_is_set(monkeypatch, capsys):
    payload = {"tool_name": "Write", "tool_input": {"file_path": "/repo/graphwerk/service.py"}}

    output = _run_main(monkeypatch, capsys, payload, scope=None)

    assert output["hookSpecificOutput"]["permissionDecision"] == "allow"
