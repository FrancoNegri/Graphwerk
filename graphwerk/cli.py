"""CLI entry points.

  python -m graphwerk demo   [--dir demo_workspace] [--port 8135] [--no-serve]
  python -m graphwerk serve  [--repo PATH] [--base-ref REF]
                         [--rationale FILE] [--transcript FILE] [--port 8135]
  python -m graphwerk start  [--repo PATH] [--base-ref REF]
                         [--host HOST] [--port 8135]
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import uvicorn

from graphwerk import __version__
from graphwerk.bootstrap import build_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="graphwerk")
    parser.add_argument("--version", action="version", version=f"graphwerk {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="build the scripted demo workspace and serve it")
    demo.add_argument("--dir", default="demo_workspace", help="where to create the demo")
    demo.add_argument("--port", type=int, default=8135)
    demo.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow LAN access")
    demo.add_argument("--no-serve", action="store_true", help="only build the workspace")

    serve = sub.add_parser("serve", help="serve one repo directory's working tree against a base ref")
    serve.add_argument("--repo", default=".", help="git repository under review (default: current directory)")
    serve.add_argument("--base-ref", help="git ref to diff the working tree against (default: current HEAD)")
    serve.add_argument("--rationale", help="sidecar rationale JSON (default: <repo>/.graphwerk/rationale.json)")
    serve.add_argument("--transcript", help="Claude Code session transcript JSONL to mine for 'why'")
    serve.add_argument("--port", type=int, default=8135)
    serve.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow LAN access")
    serve.add_argument("--agent-permissions", default="acceptEdits",
                       help="permission mode for sessions spawned via /api/prompt")
    serve.add_argument("--check", default=None,
                       help="shell command to run after each session; unset disables the check gate")
    serve.add_argument("--check-retries", type=int, default=1,
                       help="max automatic resume attempts on check failure (default: 1)")

    start = sub.add_parser("start", help="print the claude invocation and serve the UI against one repo directory")
    start.add_argument("--repo", default=".", help="git repository under review (default: current directory)")
    start.add_argument("--base-ref", help="git ref to diff the working tree against (default: current HEAD)")
    start.add_argument("--port", type=int, default=8135)
    start.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow LAN access")
    start.add_argument("--agent-permissions", default="acceptEdits",
                       help="permission mode for sessions spawned via /api/prompt")
    start.add_argument("--check", default=None,
                       help="shell command to run after each session; unset disables the check gate")
    start.add_argument("--check-retries", type=int, default=1,
                       help="max automatic resume attempts on check failure (default: 1)")

    args = parser.parse_args(argv)

    if args.command == "demo":
        from graphwerk.demo import build_demo

        repo, base_ref, sidecar = build_demo(Path(args.dir).resolve())
        print(f"demo workspace ready: {repo}")
        if args.no_serve:
            return
        _serve(repo, base_ref, sidecar, None, args.host, args.port, "acceptEdits")
    elif args.command == "start":
        _start(args)
    else:
        repo = Path(args.repo).resolve()
        base_ref = args.base_ref or _resolve_head(repo)
        sidecar = Path(args.rationale) if args.rationale else repo / ".graphwerk" / "rationale.json"
        transcript = Path(args.transcript) if args.transcript else None
        _serve(repo, base_ref, sidecar, transcript, args.host, args.port,
               args.agent_permissions, args.check, args.check_retries)


def _start(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    if not _is_git_repo(repo):
        raise SystemExit(f"error: {repo} is not a git repository (graphwerk needs one to diff against a base ref)")
    base_ref = args.base_ref or _resolve_head(repo)
    print(f"repo ready — run the agent there:\n  cd {repo} && claude", flush=True)
    sidecar = repo / ".graphwerk" / "rationale.json"
    _serve(repo, base_ref, sidecar, None, args.host, args.port,
           args.agent_permissions, args.check, args.check_retries)


def _is_git_repo(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _resolve_head(repo: Path) -> str:
    """Fixes the base ref to the concrete commit HEAD points at right now,
    so a commit the developer makes mid-session doesn't move the diff's
    base out from under them (ADR 058: the base ref is fixed for the
    review session's lifetime)."""
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"error: could not resolve HEAD in {repo} — is it a git repository with at least one commit?"
        )
    return result.stdout.strip()


def _serve(repo: Path, base_ref: str, sidecar: Path | None, transcript: Path | None,
           host: str, port: int, agent_permissions: str,
           check_command: str | None = None, check_retries: int = 1) -> None:
    app = build_app(repo, base_ref, sidecar, transcript, agent_permissions,
                    check_command, check_retries)
    shown = "127.0.0.1" if host in ("127.0.0.1", "localhost") else host
    print(f"graphwerk review UI: http://{shown}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
