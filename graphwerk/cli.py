"""CLI entry points.

  python -m graphwerk demo   [--dir demo_workspace] [--port 8135] [--no-serve]
  python -m graphwerk serve  --base PATH --staged PATH
                         [--rationale FILE] [--transcript FILE] [--port 8135]
  python -m graphwerk start  [--repo PATH] [--staging PATH] [--branch NAME]
                         [--host HOST] [--port 8135]
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import uvicorn

from graphwerk import __version__
from graphwerk.apply import ApplyEngine
from graphwerk.rationale import RationaleStore
from graphwerk.server import create_app
from graphwerk.service import GraphService
from graphwerk.staging import ShadowWorkspace


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="graphwerk")
    parser.add_argument("--version", action="version", version=f"graphwerk {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="build the scripted demo workspace and serve it")
    demo.add_argument("--dir", default="demo_workspace", help="where to create the demo")
    demo.add_argument("--port", type=int, default=8135)
    demo.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow LAN access")
    demo.add_argument("--no-serve", action="store_true", help="only build the workspace")

    serve = sub.add_parser("serve", help="serve an existing base/staged tree pair")
    serve.add_argument("--base", required=True, help="developer's tree (changes apply here)")
    serve.add_argument("--staged", required=True, help="shadow workspace the agent edits")
    serve.add_argument("--rationale", help="sidecar rationale JSON (default: <staged>/.graphwerk/rationale.json)")
    serve.add_argument("--transcript", help="Claude Code session transcript JSONL to mine for 'why'")
    serve.add_argument("--port", type=int, default=8135)
    serve.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow LAN access")

    start = sub.add_parser("start", help="ensure the staging worktree, print the claude invocation, serve the UI")
    start.add_argument("--repo", default=".", help="git repository under review (default: current directory)")
    start.add_argument("--staging", help="staging worktree (default: sibling <repo-name>-graphwerk-staging)")
    start.add_argument("--branch", default="graphwerk-staging", help="branch for the staging worktree")
    start.add_argument("--port", type=int, default=8135)
    start.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow LAN access")

    args = parser.parse_args(argv)

    if args.command == "demo":
        from graphwerk.demo import build_demo

        base, staged, sidecar = build_demo(Path(args.dir).resolve())
        print(f"demo workspace ready:\n  base:   {base}\n  staged: {staged}")
        if args.no_serve:
            return
        _serve(base, staged, sidecar, None, args.host, args.port)
    elif args.command == "start":
        _start(args)
    else:
        base, staged = Path(args.base).resolve(), Path(args.staged).resolve()
        sidecar = Path(args.rationale) if args.rationale else staged / ".graphwerk" / "rationale.json"
        transcript = Path(args.transcript) if args.transcript else None
        _serve(base, staged, sidecar, transcript, args.host, args.port)


def _start(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    if not _is_git_repo(repo):
        raise SystemExit(f"error: {repo} is not a git repository (graphwerk start needs one for the staging worktree)")
    staging = Path(args.staging).resolve() if args.staging else default_staging_path(repo)
    ShadowWorkspace.ensure(repo, staging, args.branch)
    print(f"staging worktree ready — run the agent there:\n  cd {staging} && claude", flush=True)
    sidecar = staging / ".graphwerk" / "rationale.json"
    _serve(repo, staging, sidecar, None, args.host, args.port)


def default_staging_path(repo: Path) -> Path:
    return repo.parent / f"{repo.name}-graphwerk-staging"


def _is_git_repo(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _serve(base: Path, staged: Path, sidecar: Path | None, transcript: Path | None,
           host: str, port: int) -> None:
    rationale = RationaleStore(sidecar_path=sidecar, transcript_path=transcript, staged_root=staged)
    service = GraphService(base, staged, rationale)
    engine = ApplyEngine(base, staged)
    app = create_app(service, engine)
    shown = "127.0.0.1" if host in ("127.0.0.1", "localhost") else host
    print(f"graphwerk review UI: http://{shown}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
