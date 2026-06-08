"""Tests for emkeel uninstall (reverse init)."""

from emkeel.init import Config, apply
from emkeel.uninstall import apply_uninstall, main

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def _governed(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    return tmp_path


def test_uninstall_removes_wiring_keeps_governance(tmp_path):
    _governed(tmp_path)
    apply_uninstall(tmp_path, purge=False, dry_run=False)
    assert not (tmp_path / "emkeel.toml").exists()
    assert not (tmp_path / ".github/workflows/emkeel-ci.yml").exists()
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "emkeel-governance").is_dir()  # history kept
    # emkeel created both here (fresh tmp → each holds only emkeel's line) → removed entirely
    assert not (tmp_path / ".gitattributes").exists()
    assert not (tmp_path / ".gitignore").exists()


def test_uninstall_preserves_user_gitignore(tmp_path):
    # The user already had a .gitignore (with their own .env) before Emkeel.
    (tmp_path / ".gitignore").write_text("node_modules/\n.env\ndist/\n")
    apply(tmp_path, CFG, force=False, dry_run=False)        # init: .env present → append-skip
    apply_uninstall(tmp_path, purge=False, dry_run=False)
    gi = (tmp_path / ".gitignore").read_text()
    assert "node_modules/" in gi and ".env" in gi and "dist/" in gi  # untouched, not stripped


def test_purge_also_removes_governance(tmp_path):
    _governed(tmp_path)
    apply_uninstall(tmp_path, purge=True, dry_run=False)
    assert not (tmp_path / "emkeel-governance").exists()


def test_dry_run_changes_nothing(tmp_path):
    _governed(tmp_path)
    apply_uninstall(tmp_path, purge=True, dry_run=True)
    assert (tmp_path / "emkeel.toml").exists()
    assert (tmp_path / "emkeel-governance").is_dir()


def test_cli_dry_run_changes_nothing(tmp_path, capsys):
    _governed(tmp_path)
    assert main([str(tmp_path), "--dry-run"]) == 0
    assert (tmp_path / "emkeel.toml").exists()  # nothing removed
    assert "dry-run" in capsys.readouterr().out


def test_interactive_eject_wiring_plus_governance(tmp_path):
    _governed(tmp_path)
    # wiring? Y · governance? y · GitHub side? n · proceed? y
    answers = iter(["y", "y", "n", "y"])
    assert main([str(tmp_path)], inp=lambda *_: next(answers), lang="en") == 0
    assert not (tmp_path / "emkeel.toml").exists()
    assert not (tmp_path / "emkeel-governance").exists()   # purge confirmed interactively


def test_interactive_eject_final_confirm_cancels(tmp_path):
    _governed(tmp_path)
    answers = iter(["y", "n", "n", "n"])   # wiring y, gov n, remote n, PROCEED -> no
    assert main([str(tmp_path)], inp=lambda *_: next(answers), lang="en") == 0
    assert (tmp_path / "emkeel.toml").exists()             # cancelled → nothing removed


def test_interactive_eject_decline_wiring_aborts(tmp_path):
    _governed(tmp_path)
    assert main([str(tmp_path)], inp=lambda *_: "n", lang="en") == 0  # decline at the first question
    assert (tmp_path / "emkeel.toml").exists()


def test_repo_from_git():
    from types import SimpleNamespace
    from emkeel.uninstall import repo_from_git

    def run(args, timeout=None, capture=True):
        return SimpleNamespace(returncode=0, stdout="git@github.com:acme/web.git\n", stderr="")

    assert repo_from_git(__import__("pathlib").Path("."), run=run) == "acme/web"


def test_remote_cleanup_runs_expected_commands():
    from types import SimpleNamespace
    from emkeel.uninstall import remote_cleanup
    ran = []

    def run(args, timeout=None, capture=True):
        ran.append(" ".join(args))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    steps = remote_cleanup("acme/web", "main", ["emkeel.toml", "AGENTS.md"], run=run)
    joined = "\n".join(ran)
    assert "api -X DELETE repos/acme/web/branches/main/protection" in joined   # drop protection
    assert "git add emkeel.toml AGENTS.md" in joined                            # stage only our deletions
    assert "commit" in joined and "git push" in joined                          # commit + push
    assert "secret delete JIRA_TOKEN --repo acme/web" in joined                 # drop secrets
    assert any(ok for label, ok in steps if "push" in label.lower())


def test_remote_cleanup_handles_push_timeout():
    import subprocess
    from emkeel.uninstall import remote_cleanup

    def run(args, timeout=None, capture=True):
        from types import SimpleNamespace
        if args[:2] == ["git", "push"]:
            raise subprocess.TimeoutExpired(cmd="git push", timeout=180)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    steps = remote_cleanup("acme/web", "main", ["emkeel.toml"], run=run)
    assert any("timed out" in label for label, _ in steps)


def test_eject_nothing_to_remove_is_honest(tmp_path, capsys):
    # Not governed → don't pretend to remove things.
    assert main([str(tmp_path), "--yes"]) == 0
    out = capsys.readouterr().out.lower()
    assert "no local emkeel files" in out
    assert "removed   emkeel.toml" not in out


def test_eject_json_canonical(tmp_path):
    from emkeel.uninstall import eject_json
    j = eject_json(tmp_path)
    assert j["engine"] == "emkeel"
    vals = [s["value"] for s in j["scopes"]]
    assert vals == ["default", "purge", "all"]
    # bilingual labels (the AI translates from these — never invents)
    assert j["scopes"][0]["label"]["es"] and j["scopes"][0]["label"]["en"]
    assert j["scopes"][2]["flags"] == ["--all", "--yes"]


def test_main_json_flag(tmp_path, capsys):
    import json
    assert main([str(tmp_path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["engine"] == "emkeel" and len(data["scopes"]) == 3
