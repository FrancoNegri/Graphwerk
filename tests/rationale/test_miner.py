import json
import os
from pathlib import Path

import pytest

from graphwerk.rationale import RationaleStore
from graphwerk.rationale.discovery import project_dir_name


@pytest.fixture
def staged_root(tmp_path):
    staged = tmp_path / "staging"
    staged.mkdir()
    return staged


@pytest.fixture
def claude_projects_dir(tmp_path, staged_root, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    project_dir = home / ".claude" / "projects" / project_dir_name(staged_root)
    project_dir.mkdir(parents=True)
    return project_dir


def write_transcript(path: Path, staged_root: Path, narration: str, mtime: int) -> None:
    entry = {
        "message": {
            "content": [
                {"type": "text", "text": narration},
                {
                    "type": "tool_use",
                    "name": "Edit",
                    "input": {"file_path": str(staged_root / "foo.py")},
                },
            ]
        }
    }
    path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_reload_picks_up_session_created_after_construction(staged_root, claude_projects_dir):
    store = RationaleStore(staged_root=staged_root)
    assert store.why_for("foo.py") is None

    write_transcript(claude_projects_dir / "session-a.jsonl", staged_root,
                     "Refactor the widget", mtime=1000)
    store.reload()

    assert store.why_for("foo.py") == "Refactor the widget"


def test_reload_prefers_the_newer_session(staged_root, claude_projects_dir):
    write_transcript(claude_projects_dir / "session-a.jsonl", staged_root,
                     "Old reasoning", mtime=1000)
    store = RationaleStore(staged_root=staged_root)
    assert store.why_for("foo.py") == "Old reasoning"

    write_transcript(claude_projects_dir / "session-b.jsonl", staged_root,
                     "New reasoning", mtime=2000)
    store.reload()

    assert store.why_for("foo.py") == "New reasoning"


def test_explicit_transcript_path_stays_pinned(staged_root, claude_projects_dir):
    pinned = claude_projects_dir / "session-a.jsonl"
    write_transcript(pinned, staged_root, "Pinned reasoning", mtime=1000)
    store = RationaleStore(staged_root=staged_root, transcript_path=pinned)

    write_transcript(claude_projects_dir / "session-b.jsonl", staged_root,
                     "Newer reasoning", mtime=2000)
    store.reload()

    assert store.why_for("foo.py") == "Pinned reasoning"


def test_empty_discovery_falls_back_to_sidecar_only(tmp_path, staged_root, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    sidecar = tmp_path / "rationale.json"
    sidecar.write_text(json.dumps({"foo.py": "From the sidecar"}), encoding="utf-8")

    store = RationaleStore(sidecar_path=sidecar, staged_root=staged_root)
    store.reload()

    assert store.why_for("foo.py") == "From the sidecar"
