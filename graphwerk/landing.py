import subprocess
from pathlib import Path


def commit_all(repo_root: Path, paths: list[str], message: str) -> None:
    """Stages exactly `paths` and commits them with `message`. Raises
    subprocess.CalledProcessError on failure — unlike differ.py's read
    helpers, a failed commit needs to surface to the caller."""
    if not paths:
        return
    subprocess.run(["git", "-C", str(repo_root), "add", "--", *paths], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-m", message],
        capture_output=True, check=True,
    )


def revert_all(repo_root: Path, paths: list[str]) -> None:
    """Stashes exactly `paths` (including untracked), leaving them at
    HEAD's content. Raises subprocess.CalledProcessError on failure."""
    if not paths:
        return
    subprocess.run(
        ["git", "-C", str(repo_root), "stash", "push", "-u", "--", *paths],
        capture_output=True, check=True,
    )
