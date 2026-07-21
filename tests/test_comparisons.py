import json
import subprocess
from pathlib import Path

from graphwerk.comparisons import ComparisonRegistry, WORKING_TREE_TOKEN


def write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, source in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout


def commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=test@graphwerk.local", "-c", "user.name=test",
         "commit", "-q", "-m", message, "--allow-empty")
    return _git(repo, "rev-parse", "HEAD").strip()


def make_two_commit_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """A repo with two commits touching the same symbol, plus a further
    uncommitted change on top so the working tree, HEAD, and the first
    commit are all distinguishable."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    write_tree(repo, {"a.py": "def foo():\n    return 1\n"})
    first = commit(repo, "first")
    write_tree(repo, {"a.py": "def foo():\n    return 2\n"})
    second = commit(repo, "second")
    write_tree(repo, {"a.py": "def foo():\n    return 3\n"})  # uncommitted
    return repo, first, second


def node(snapshot, node_id: str):
    for candidate in snapshot.nodes:
        if candidate.id == node_id:
            return candidate
    raise AssertionError(f"no node {node_id}")


def test_get_builds_a_working_graphservice_for_a_ref_pair(tmp_path):
    repo, first, second = make_two_commit_repo(tmp_path)
    registry = ComparisonRegistry(repo, base_ref=first)

    snapshot = registry.get(first, second).snapshot()

    foo = node(snapshot, "a.py::foo")
    assert "return 2" in foo.source


def test_get_reflects_the_correct_diff_for_each_distinct_pair(tmp_path):
    repo, first, second = make_two_commit_repo(tmp_path)
    registry = ComparisonRegistry(repo, base_ref=first)

    live_snapshot = registry.get(first, WORKING_TREE_TOKEN).snapshot()
    historical_snapshot = registry.get(first, second).snapshot()

    assert "return 3" in node(live_snapshot, "a.py::foo").source
    assert "return 2" in node(historical_snapshot, "a.py::foo").source


def test_get_caches_the_same_instance_for_a_repeat_pair(tmp_path):
    repo, first, second = make_two_commit_repo(tmp_path)
    registry = ComparisonRegistry(repo, base_ref=first)

    first_call = registry.get(first, second)
    second_call = registry.get(first, second)

    assert first_call is second_call


def test_get_caches_distinct_instances_for_distinct_pairs(tmp_path):
    repo, first, second = make_two_commit_repo(tmp_path)
    registry = ComparisonRegistry(repo, base_ref=first)

    live = registry.get(first, WORKING_TREE_TOKEN)
    historical = registry.get(first, second)

    assert live is not historical


def test_non_live_pair_has_no_why_even_when_a_real_source_exists(tmp_path):
    repo, first, second = make_two_commit_repo(tmp_path)
    sidecar_path = repo / "rationale.json"
    sidecar_path.write_text(json.dumps({"a.py": "explains the bump"}))
    registry = ComparisonRegistry(repo, base_ref=first, sidecar_path=sidecar_path)

    live_snapshot = registry.get(first, WORKING_TREE_TOKEN).snapshot()
    historical_snapshot = registry.get(first, second).snapshot()

    assert node(live_snapshot, "a.py").why == "explains the bump"
    assert node(historical_snapshot, "a.py").why is None


def test_working_tree_token_recognized_on_the_base_side_too(tmp_path):
    repo, first, second = make_two_commit_repo(tmp_path)
    registry = ComparisonRegistry(repo, base_ref=first)

    # base = working tree, staged = an older commit: a "reverse" comparison,
    # still expected to resolve and produce a usable snapshot.
    snapshot = registry.get(WORKING_TREE_TOKEN, first).snapshot()

    assert "return 1" in node(snapshot, "a.py::foo").source


def test_get_defaults_to_the_registrys_configured_pair(tmp_path):
    repo, first, second = make_two_commit_repo(tmp_path)
    registry = ComparisonRegistry(repo, base_ref=first)

    default_snapshot = registry.get().snapshot()

    assert "return 3" in node(default_snapshot, "a.py::foo").source
    assert registry.get() is registry.get(first, WORKING_TREE_TOKEN)
