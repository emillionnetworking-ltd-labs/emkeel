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
