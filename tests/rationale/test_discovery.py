import os
from pathlib import Path

from graphwerk.rationale.discovery import find_latest_transcript, project_dir_name


def test_encodes_slashes_and_dots_as_dashes():
    assert project_dir_name(Path("/home/u/my.repo")) == "-home-u-my-repo"


def test_returns_most_recently_modified_jsonl(tmp_path):
    worktree = Path("/home/u/my.repo")
    project_dir = tmp_path / "projects" / "-home-u-my-repo"
    project_dir.mkdir(parents=True)
    older = project_dir / "session-a.jsonl"
    newer = project_dir / "session-b.jsonl"
    older.write_text("{}")
    newer.write_text("{}")
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    assert find_latest_transcript(worktree, claude_dir=tmp_path) == newer


def test_returns_none_when_project_dir_missing(tmp_path):
    assert find_latest_transcript(Path("/home/u/my.repo"), claude_dir=tmp_path) is None


def test_returns_none_when_no_jsonl_files(tmp_path):
    project_dir = tmp_path / "projects" / "-home-u-my-repo"
    project_dir.mkdir(parents=True)
    (project_dir / "notes.txt").write_text("not a transcript")

    assert find_latest_transcript(Path("/home/u/my.repo"), claude_dir=tmp_path) is None
