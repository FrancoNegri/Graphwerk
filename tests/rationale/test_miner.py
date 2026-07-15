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


def assistant_entry(*blocks) -> dict:
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def edit_block(file_path: Path) -> dict:
    return {"type": "tool_use", "name": "Edit", "input": {"file_path": str(file_path)}}


def write_entries(path: Path, entries: list) -> None:
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def write_transcript(path: Path, staged_root: Path, narration: str, mtime: int) -> None:
    write_entries(path, [
        assistant_entry(text_block(narration), edit_block(staged_root / "foo.py")),
    ])
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


def test_dogfood_shape_yields_distinct_per_file_whys(staged_root, claude_projects_dir):
    write_entries(claude_projects_dir / "session-a.jsonl", [
        assistant_entry(
            text_block("Let me make those changes."),
            edit_block(staged_root / "cli.py"),
            edit_block(staged_root / "models.py"),
        ),
        assistant_entry(text_block(
            "All done:\n"
            "- `cli.py`: added the --version flag\n"
            "- `models.py`: new order field"
        )),
    ])

    store = RationaleStore(staged_root=staged_root)

    assert store.why_for("cli.py") == "- `cli.py`: added the --version flag"
    assert store.why_for("models.py") == "- `models.py`: new order field"


def test_unmentioned_file_falls_back_to_preceding_narration(staged_root, claude_projects_dir):
    write_entries(claude_projects_dir / "session-a.jsonl", [
        assistant_entry(
            text_block("Quick cleanup pass."),
            edit_block(staged_root / "helpers.py"),
        ),
        assistant_entry(text_block("Summary that never names the file.")),
    ])

    store = RationaleStore(staged_root=staged_root)

    assert store.why_for("helpers.py") == "Quick cleanup pass."


def test_symbol_mention_beats_file_why_while_siblings_keep_it(staged_root, claude_projects_dir):
    write_entries(claude_projects_dir / "session-a.jsonl", [
        assistant_entry(
            text_block("Working through payment.py."),
            edit_block(staged_root / "payment.py"),
        ),
        assistant_entry(text_block(
            "Summary:\n"
            "- payment.py: validation and retries\n"
            "- charge now retries three times"
        )),
    ])

    store = RationaleStore(staged_root=staged_root)
    store.reload(changed_symbols={"payment.py": ["Gateway.charge", "Gateway.refund"]})

    assert store.why_for("payment.py", "Gateway.charge") == "- charge now retries three times"
    assert store.why_for("payment.py", "Gateway.refund") == "- payment.py: validation and retries"


def test_why_for_prefers_sidecar_symbol_then_sidecar_file_then_transcript(
        tmp_path, staged_root, claude_projects_dir):
    write_entries(claude_projects_dir / "session-a.jsonl", [
        assistant_entry(
            text_block("Transcript file why for payment.py."),
            edit_block(staged_root / "payment.py"),
        ),
        assistant_entry(text_block("Transcript symbol why: charge retries now.")),
    ])
    changed = {"payment.py": ["Gateway.charge"]}

    def store_with(sidecar_entries):
        sidecar = tmp_path / "rationale.json"
        sidecar.write_text(json.dumps(sidecar_entries), encoding="utf-8")
        store = RationaleStore(sidecar_path=sidecar, staged_root=staged_root)
        store.reload(changed_symbols=changed)
        return store

    full = store_with({"payment.py": "Sidecar file why",
                       "payment.py::Gateway.charge": "Sidecar symbol why"})
    assert full.why_for("payment.py", "Gateway.charge") == "Sidecar symbol why"

    file_only = store_with({"payment.py": "Sidecar file why"})
    assert file_only.why_for("payment.py", "Gateway.charge") == "Sidecar file why"

    no_sidecar = store_with({})
    assert no_sidecar.why_for("payment.py", "Gateway.charge") == \
        "Transcript symbol why: charge retries now."
    assert no_sidecar.why_for("payment.py") == "Transcript file why for payment.py."


def test_status_reports_loaded_sources_and_entry_counts(tmp_path, staged_root, claude_projects_dir):
    transcript = claude_projects_dir / "session-a.jsonl"
    write_transcript(transcript, staged_root, "Refactor the widget", mtime=1000)
    sidecar = tmp_path / "rationale.json"
    sidecar.write_text(json.dumps({"foo.py": "Sidecar why"}), encoding="utf-8")

    store = RationaleStore(sidecar_path=sidecar, staged_root=staged_root)

    assert store.status.sidecar_path == str(sidecar)
    assert store.status.sidecar_entries == 1
    assert store.status.transcript_path == str(transcript)
    assert store.status.transcript_entries == 1


def test_status_reports_no_transcript_when_project_dir_missing(tmp_path, staged_root, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

    store = RationaleStore(staged_root=staged_root)

    assert store.status.sidecar_path is None
    assert store.status.sidecar_entries == 0
    assert store.status.transcript_path is None
    assert store.status.transcript_entries == 0


def test_status_serializes_to_plain_dict(tmp_path, staged_root, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

    store = RationaleStore(staged_root=staged_root)

    assert store.status.to_dict() == {
        "sidecar_path": None,
        "sidecar_entries": 0,
        "transcript_path": None,
        "transcript_entries": 0,
    }


def test_empty_discovery_falls_back_to_sidecar_only(tmp_path, staged_root, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    sidecar = tmp_path / "rationale.json"
    sidecar.write_text(json.dumps({"foo.py": "From the sidecar"}), encoding="utf-8")

    store = RationaleStore(sidecar_path=sidecar, staged_root=staged_root)
    store.reload()

    assert store.why_for("foo.py") == "From the sidecar"
