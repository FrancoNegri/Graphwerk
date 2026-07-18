#!/usr/bin/env python3
"""Wrap a pytest invocation to also write graphwerk's .graphwerk-check.json.

Operator-side glue for ADR 044: graphwerk's check gate auto-detects a
`.graphwerk-check.json` summary written by the check command itself.
Pytest doesn't write one natively, so this wraps any pytest launcher
(`pytest`, `uv run pytest`, `.venv/bin/python -m pytest`, ...), asks it to
also emit a JUnit XML report (a pytest core feature, no extra plugin), and
turns that into the summary graphwerk reads. Exit code passes through
unchanged so the check gate's pass/fail is exactly pytest's own verdict.

Usage: point --check at this script followed by the real pytest command, e.g.
    --check "python3 scripts/pytest_check_summary.py uv run pytest"
    --check "python3 scripts/pytest_check_summary.py .venv/bin/python -m pytest -q"
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

SUMMARY_FILENAME = ".graphwerk-check.json"


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: pytest_check_summary.py <pytest-launcher-and-args...>", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp_dir:
        junit_path = Path(tmp_dir) / "junit.xml"
        exit_code = subprocess.call([*argv, f"--junit-xml={junit_path}"])
        summary = _parse_junit(junit_path)
    Path(SUMMARY_FILENAME).write_text(json.dumps(summary))
    return exit_code


def _parse_junit(junit_path: Path) -> dict:
    if not junit_path.exists():
        return {}
    root = ET.parse(junit_path).getroot()
    suite = root.find("testsuite") if root.tag == "testsuites" else root
    if suite is None:
        return {}
    total = int(suite.get("tests", 0))
    failed = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    failures = [
        f'{case.get("classname")}::{case.get("name")}'
        for case in suite.findall("testcase")
        if case.find("failure") is not None or case.find("error") is not None
    ]
    return {
        "passed": total - failed - skipped,
        "failed": failed,
        "total": total,
        "failures": failures,
    }


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
