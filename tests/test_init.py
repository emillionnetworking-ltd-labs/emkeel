"""Tests for emkeel init. Born with main() coverage (KEEL-2 lesson)."""

from pathlib import Path

from emkeel.init import APPEND_LINES, Config, apply, main, plan

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def _kinds(actions):
    return {a.path: a.kind for a in actions}


def test_plan_on_empty_target_creates_everything(tmp_path):
    k = _kinds(plan(tmp_path, CFG, force=False))
    assert k["emkeel.toml"] == "create"
    assert k[".github/workflows/emkeel-ci.yml"] == "create"
    assert k[".gitattributes"] == "append"
    assert k[".gitignore"] == "append"


def test_plan_is_non_clobbering(tmp_path):
    (tmp_path / "AGENTS.md").write_text("my existing contract")
    k = _kinds(plan(tmp_path, CFG, force=False))
    assert k["AGENTS.md"] == "skip-exists"
    assert k["emkeel.toml"] == "create"  # the rest still planned


def test_force_overwrites(tmp_path):
    (tmp_path / "AGENTS.md").write_text("old")
    k = _kinds(plan(tmp_path, CFG, force=True))
    assert k["AGENTS.md"] == "create"


def test_append_is_idempotent(tmp_path):
    line = APPEND_LINES[".gitignore"]
    (tmp_path / ".gitignore").write_text(f"node_modules\n{line}\n")
    k = _kinds(plan(tmp_path, CFG, force=False))
    assert k[".gitignore"] == "append-skip"


def test_dry_run_writes_nothing(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=True)
    assert list(tmp_path.iterdir()) == []


def test_apply_creates_files_and_is_idempotent(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert (tmp_path / "emkeel.toml").is_file()
    assert (tmp_path / "emkeel-governance/specs/.gitkeep").is_file()
    assert "emkeel-governance/ export-ignore" in (tmp_path / ".gitattributes").read_text()
    assert ".env" in (tmp_path / ".gitignore").read_text()
    # never writes a real secret file
    assert not (tmp_path / ".env").exists()
    # second run is a no-op (no duplicate append lines)
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert (tmp_path / ".gitattributes").read_text().count("emkeel-governance/ export-ignore") == 1


def test_toml_carries_config(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    toml = (tmp_path / "emkeel.toml").read_text()
    assert 'project_key = "DEMO"' in toml and 'repo = "o/r"' in toml


def test_main_smoke(tmp_path, capsys):
    rc = main([str(tmp_path), "--jira-project", "DEMO", "--github-repo", "o/r"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "emkeel init [applied]" in out and "NEXT — connect Emkeel" in out
    assert (tmp_path / "emkeel.toml").is_file()
