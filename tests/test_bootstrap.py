from fastapi import FastAPI

from graphwerk.bootstrap import build_app


def test_build_app_wires_a_real_app_against_base_and_staged_trees(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    staged.mkdir()

    app = build_app(base, staged, None, None, "acceptEdits")

    assert isinstance(app, FastAPI)


def test_build_app_wires_session_guidance_into_the_runner(monkeypatch, tmp_path):
    from graphwerk.rationale.guidance import SESSION_GUIDANCE

    runners = []

    class RecordingSessionRunner:
        def __init__(self, staged_root, permission_mode="acceptEdits", system_prompt=""):
            self.staged_root = staged_root
            self.permission_mode = permission_mode
            self.system_prompt = system_prompt
            runners.append(self)

    import graphwerk.bootstrap as bootstrap
    monkeypatch.setattr(bootstrap, "SessionRunner", RecordingSessionRunner)

    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    staged.mkdir()

    build_app(base, staged, None, None, "acceptEdits")

    assert runners[0].system_prompt == SESSION_GUIDANCE
