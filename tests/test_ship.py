"""Tests for ship_* — the isolated-worktree maintenance lane (real git, faked gh)."""

import subprocess
from types import SimpleNamespace

from emkeel.init import Config, apply
from emkeel.ship import ship_update


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def _real_git_fake_gh(calls):
    def run(args, stdin=None, timeout=None, capture=True):
        calls.append(" ".join(str(a) for a in args))
        if args and args[0] == "gh":
            j = " ".join(args)
            out = "main" if "default_branch" in j else ("https://github.com/o/r/pull/1" if "pr create" in j else "")
            return SimpleNamespace(returncode=0, stdout=out, stderr="")
        if capture:
            return subprocess.run(args, capture_output=True, text=True)
        return subprocess.run(args, text=True)
    return run


def _seed_repo(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    work = tmp_path / "work"; work.mkdir()
    _git(["init", "-q"], work)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    _git(["config", "user.email", "t@t.co"], work)
    _git(["config", "user.name", "t"], work)
    _git(["config", "commit.gpgsign", "false"], work)
    apply(work, Config(github_repo="o/r"), force=False, dry_run=False)
    return origin, work


def test_ship_update_isolates_working_tree(tmp_path):
    origin, work = _seed_repo(tmp_path)
    (work / "AGENTS.md").write_text("# stale contract\n")     # make origin's wiring out of date
    _git(["add", "-A"], work)
    _git(["commit", "-qm", "init"], work)
    _git(["remote", "add", "origin", str(origin)], work)
    _git(["push", "-q", "-u", "origin", "main"], work)
    (work / "product.txt").write_text("work in progress")     # the user's in-progress product work

    calls = []
    assert ship_update(target=work, run=_real_git_fake_gh(calls)) == 0

    # the user's product work is NEVER touched (still there, still uncommitted)
    assert (work / "product.txt").read_text() == "work in progress"
    st = subprocess.run(["git", "status", "--porcelain"], cwd=work, capture_output=True, text=True).stdout
    assert "product.txt" in st
    # a maintenance branch landed on origin (inspect via the non-bare clone — safe.bareRepository)
    refs = subprocess.run(["git", "-C", str(work), "ls-remote", "origin"], capture_output=True, text=True).stdout
    assert "emkeel-maint/" in refs
    maint = [ln.split("refs/heads/")[1] for ln in refs.splitlines() if "emkeel-maint/" in ln][0]
    subprocess.run(["git", "-C", str(work), "fetch", "-q", "origin", maint], check=True)
    files = subprocess.run(["git", "-C", str(work), "show", "--name-only", "--format=", "FETCH_HEAD"],
                           capture_output=True, text=True).stdout
    assert "AGENTS.md" in files and "product.txt" not in files
    agents = subprocess.run(["git", "-C", str(work), "show", "FETCH_HEAD:AGENTS.md"],
                            capture_output=True, text=True).stdout
    assert "Rules that matter live in CI" in agents          # refreshed to the current template
    j = "\n".join(calls)
    assert "gh pr create" in j and "gh pr merge" in j


# ── in-flight maint PR detection (KEEL-84) ─────────────────────────────────────

from emkeel.ship import inflight_maint_pr


def _gh(returncode=0, stdout=""):
    return lambda args, **k: SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def test_inflight_maint_pr_found():
    out = '[{"number": 7, "headRefName": "emkeel-maint/0.1.69-abc"}]'
    assert inflight_maint_pr("o/r", run=_gh(0, out)) == 7


def test_inflight_maint_pr_ignores_non_maint_prs():
    out = '[{"number": 5, "headRefName": "feat/KEEL-1-x"}, {"number": 6, "headRefName": "fix/KEEL-2-y"}]'
    assert inflight_maint_pr("o/r", run=_gh(0, out)) is None


def test_inflight_maint_pr_degrades_when_gh_fails():
    assert inflight_maint_pr("o/r", run=_gh(returncode=1, stdout="boom")) is None    # gh down → None


def test_inflight_maint_pr_degrades_on_bad_json():
    assert inflight_maint_pr("o/r", run=_gh(0, "not json")) is None


def test_inflight_maint_pr_no_repo():
    assert inflight_maint_pr("", run=_gh(0, "[]")) is None


def test_ship_update_skips_when_pr_in_flight(tmp_path, capsys):
    origin, work = _seed_repo(tmp_path)
    (work / "AGENTS.md").write_text("# stale\n")
    _git(["add", "-A"], work); _git(["commit", "-qm", "init"], work)
    _git(["remote", "add", "origin", str(origin)], work)
    _git(["push", "-q", "-u", "origin", "main"], work)

    calls = []

    def run(args, stdin=None, timeout=None, capture=True):
        calls.append(" ".join(str(a) for a in args))
        if args and args[0] == "gh":
            j = " ".join(args)
            if "auth status" in j:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "pr list" in j:    # a refresh is already in flight
                return SimpleNamespace(returncode=0,
                                       stdout='[{"number": 42, "headRefName": "emkeel-maint/0.1.69-xy"}]', stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return subprocess.run(args, capture_output=True, text=True)

    assert ship_update(target=work, run=run) == 0
    out = capsys.readouterr().out
    assert "Already shipped as PR #42" in out and "git pull" in out
    assert not any("pr create" in c for c in calls)        # did NOT re-push / re-open a PR


def test_ship_update_nothing_when_current(tmp_path):
    origin, work = _seed_repo(tmp_path)                       # apply == current templates
    _git(["add", "-A"], work)
    _git(["commit", "-qm", "init"], work)
    _git(["remote", "add", "origin", str(origin)], work)
    _git(["push", "-q", "-u", "origin", "main"], work)
    calls = []
    assert ship_update(target=work, run=_real_git_fake_gh(calls)) == 0
    assert "gh pr create" not in "\n".join(calls)            # nothing to ship → no PR


def test_default_branch_prefers_gh(tmp_path):
    from emkeel.ship import _default_branch
    run = lambda a, **k: SimpleNamespace(returncode=0, stdout="trunk", stderr="")
    assert _default_branch(run, tmp_path, "o/r") == "trunk"


def test_clean_local_removes_only_emkeel_leftovers(tmp_path):
    from emkeel import connect
    from emkeel.ship import _clean_local
    work = tmp_path / "w"; work.mkdir()
    _git(["init", "-q"], work); _git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    _git(["config", "user.email", "t@t.co"], work); _git(["config", "user.name", "t"], work)
    _git(["config", "commit.gpgsign", "false"], work)
    apply(work, Config(github_repo="o/r"), force=False, dry_run=False)
    template_agents = (work / "AGENTS.md").read_text()
    (work / "AGENTS.md").write_text("# OLD committed\n")          # commit an OLD AGENTS.md
    _git(["add", "-A"], work); _git(["commit", "-qm", "init"], work)
    # the leftovers + the user's stuff, all uncommitted together:
    (work / "AGENTS.md").write_text(template_agents)              # emkeel leftover (== template)
    (work / "product.txt").write_text("mine")                    # the user's product work
    (work / "emkeel.toml").write_text((work / "emkeel.toml").read_text() + "# hand edit\n")  # hand-edited emkeel file
    (work / "emkeel-governance" / "specs" / "ECO-1.md").write_text("my audit spec")           # the user's own artifact

    _clean_local(work, connect._run)

    assert (work / "AGENTS.md").read_text() == "# OLD committed\n"   # emkeel leftover reverted
    assert (work / "product.txt").read_text() == "mine"             # product untouched
    assert "# hand edit" in (work / "emkeel.toml").read_text()      # hand-edited emkeel file left alone
    assert (work / "emkeel-governance" / "specs" / "ECO-1.md").read_text() == "my audit spec"  # user artifact untouched


def test_clean_local_removes_untracked_emkeel_file(tmp_path):
    from emkeel import connect
    from emkeel.ship import _clean_local
    work = tmp_path / "w"; work.mkdir()
    _git(["init", "-q"], work); _git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    _git(["config", "user.email", "t@t.co"], work); _git(["config", "user.name", "t"], work)
    _git(["config", "commit.gpgsign", "false"], work)
    apply(work, Config(github_repo="o/r"), force=False, dry_run=False)
    _git(["add", "-A"], work); _git(["commit", "-qm", "init"], work)
    _git(["rm", "--cached", "-q", "emkeel-governance/strategy/.gitkeep"], work)   # make it untracked
    _git(["commit", "-qm", "untrack"], work)
    assert (work / "emkeel-governance" / "strategy" / ".gitkeep").exists()
    _clean_local(work, connect._run)
    assert not (work / "emkeel-governance" / "strategy" / ".gitkeep").exists()    # untracked emkeel file removed


def test_clean_local_cleans_toml_stamp_only(tmp_path):
    import re

    from emkeel import connect
    from emkeel.ship import _clean_local
    work = tmp_path / "w"; work.mkdir()
    _git(["init", "-q"], work); _git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    _git(["config", "user.email", "t@t.co"], work); _git(["config", "user.name", "t"], work)
    _git(["config", "commit.gpgsign", "false"], work)
    apply(work, Config(jira_project="SCRUM", github_repo="o/r"), force=False, dry_run=False)
    _git(["add", "-A"], work); _git(["commit", "-qm", "init"], work)
    committed = (work / "emkeel.toml").read_text()
    # leftover where ONLY the version stamp differs (the bug: this wasn't getting cleaned)
    (work / "emkeel.toml").write_text(re.sub(r'generated_with = "[^"]*"', 'generated_with = "0.0.1"', committed))
    _clean_local(work, connect._run)
    assert (work / "emkeel.toml").read_text() == committed         # cleaned despite the stamp diff


def test_clean_local_keeps_toml_value_edit(tmp_path):
    from emkeel import connect
    from emkeel.ship import _clean_local
    work = tmp_path / "w"; work.mkdir()
    _git(["init", "-q"], work); _git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    _git(["config", "user.email", "t@t.co"], work); _git(["config", "user.name", "t"], work)
    _git(["config", "commit.gpgsign", "false"], work)
    apply(work, Config(jira_project="SCRUM", github_repo="o/r"), force=False, dry_run=False)
    _git(["add", "-A"], work); _git(["commit", "-qm", "init"], work)
    toml = (work / "emkeel.toml").read_text()
    (work / "emkeel.toml").write_text(toml.replace('project_key = "SCRUM"', 'project_key = "ECO"'))
    _clean_local(work, connect._run)
    assert 'project_key = "ECO"' in (work / "emkeel.toml").read_text()   # real value edit preserved


def test_ship_update_skips_stamp_only_change(tmp_path):
    import re
    origin, work = _seed_repo(tmp_path)
    # origin/main is current EXCEPT for a different version stamp (everything else matches templates)
    toml = (work / "emkeel.toml").read_text()
    (work / "emkeel.toml").write_text(re.sub(r'generated_with = "[^"]*"', 'generated_with = "0.0.1"', toml))
    _git(["add", "-A"], work); _git(["commit", "-qm", "init"], work)
    _git(["remote", "add", "origin", str(origin)], work); _git(["push", "-q", "-u", "origin", "main"], work)
    calls = []
    assert ship_update(target=work, run=_real_git_fake_gh(calls)) == 0
    assert "gh pr create" not in "\n".join(calls)   # only the stamp differs → no empty PR


def _shipped_file(work, ref_file: str) -> str:
    """Content of `ref_file` on the maint branch that ship_* pushed to origin."""
    refs = subprocess.run(["git", "-C", str(work), "ls-remote", "origin"],
                          capture_output=True, text=True).stdout
    maint = [ln.split("refs/heads/")[1] for ln in refs.splitlines() if "emkeel-maint/" in ln][0]
    subprocess.run(["git", "-C", str(work), "fetch", "-q", "origin", maint], check=True)
    return subprocess.run(["git", "-C", str(work), "show", f"FETCH_HEAD:{ref_file}"],
                          capture_output=True, text=True).stdout


def test_ship_update_advances_stamp_on_real_refresh(tmp_path):
    """(a) When the wiring genuinely refreshes (other files change too), the version stamp must NOT be
    reverted — `generated_with` advances to __version__ instead of staying stale at the old value."""
    import re
    from emkeel import __version__
    origin, work = _seed_repo(tmp_path)
    # origin/main is BOTH stale wiring (old AGENTS.md) AND an old stamp — a real refresh is due.
    (work / "AGENTS.md").write_text("# stale contract\n")
    toml = (work / "emkeel.toml").read_text()
    (work / "emkeel.toml").write_text(re.sub(r'generated_with = "[^"]*"', 'generated_with = "0.0.1"', toml))
    _git(["add", "-A"], work); _git(["commit", "-qm", "init"], work)
    _git(["remote", "add", "origin", str(origin)], work); _git(["push", "-q", "-u", "origin", "main"], work)

    calls = []
    assert ship_update(target=work, run=_real_git_fake_gh(calls)) == 0
    assert "gh pr create" in "\n".join(calls)                      # a real refresh shipped a PR

    shipped = _shipped_file(work, "emkeel.toml")
    assert f'generated_with = "{__version__}"' in shipped         # stamp advanced with the refresh…
    assert 'generated_with = "0.0.1"' not in shipped              # …not left stale
    files = subprocess.run(["git", "-C", str(work), "show", "--name-only", "--format=", "FETCH_HEAD"],
                           capture_output=True, text=True).stdout
    assert "AGENTS.md" in files and "emkeel.toml" in files        # PR carries BOTH wiring and stamp


def test_ship_set_ships_non_stamp_field(tmp_path):
    """(c) A real emkeel.toml field edit (not the stamp) is shipped untouched by the noise-revert."""
    from emkeel.ship import ship_set
    origin, work = _seed_repo(tmp_path)
    _git(["add", "-A"], work); _git(["commit", "-qm", "init"], work)
    _git(["remote", "add", "origin", str(origin)], work); _git(["push", "-q", "-u", "origin", "main"], work)

    calls = []
    assert ship_set("jira_project", "ECO", target=work, run=_real_git_fake_gh(calls)) == 0
    assert "gh pr create" in "\n".join(calls)                      # a real field change ships
    assert 'project_key = "ECO"' in _shipped_file(work, "emkeel.toml")   # the edit landed, not reverted
