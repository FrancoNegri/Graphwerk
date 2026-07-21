import subprocess

from graphwerk.demo import build_demo


def _git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def test_build_demo_produces_one_directory_not_two(tmp_path):
    workspace = tmp_path / "demo_workspace"

    repo, base_ref, sidecar = build_demo(workspace)

    assert repo == workspace
    assert repo.is_dir()
    assert not (tmp_path / "demo_workspace" / "staged").exists()
    assert not (workspace.parent / "staged").exists()


def test_build_demo_base_ref_is_the_initial_commit(tmp_path):
    workspace = tmp_path / "demo_workspace"

    repo, base_ref, sidecar = build_demo(workspace)

    assert base_ref == _git(repo, "rev-parse", "HEAD")
    log = _git(repo, "log", "--oneline")
    assert len(log.splitlines()) == 1  # only the initial commit — edits are uncommitted


def test_build_demo_leaves_scripted_edits_uncommitted_on_disk(tmp_path):
    workspace = tmp_path / "demo_workspace"

    repo, base_ref, sidecar = build_demo(workspace)

    status = _git(repo, "status", "--porcelain")
    assert "shop/payment.py" in status
    assert "shop/receipts.py" in status  # new file from the scripted edit
    assert "class PaymentValidator" in (repo / "shop" / "payment.py").read_text()


def test_build_demo_writes_sidecar_inside_repo(tmp_path):
    workspace = tmp_path / "demo_workspace"

    repo, base_ref, sidecar = build_demo(workspace)

    assert sidecar == repo / ".graphwerk" / "rationale.json"
    assert sidecar.is_file()


def test_build_demo_is_idempotent_and_resets_scripted_edits(tmp_path):
    workspace = tmp_path / "demo_workspace"

    repo, base_ref, sidecar = build_demo(workspace)
    (repo / "shop" / "payment.py").write_text("# hand-edited by a user poking at the demo\n")

    repo2, base_ref2, sidecar2 = build_demo(workspace)

    assert "class PaymentValidator" in (repo2 / "shop" / "payment.py").read_text()
    assert base_ref2 == _git(repo2, "rev-parse", "HEAD")
