"""Tests for emkeel sync (git is injected — no real calls)."""

from types import SimpleNamespace

from emkeel.sync import cleanable_branches, default_branch, sync, wait_for_merge


def _r(rc=0, out=""):
    return SimpleNamespace(returncode=rc, stdout=out, stderr="")


def test_default_branch():
    assert default_branch(run=lambda *a, **k: _r(0, "refs/remotes/origin/main\n")) == "main"
    assert default_branch(run=lambda *a, **k: _r(1, "")) == "main"   # fallback


def test_cleanable_branches_merged_and_gone():
    def run(args, **k):
        if args[:3] == ["git", "branch", "--merged"]:
            return _r(0, "* main\n  chore/SCRUM-1-adopt-emkeel\n  keepme\n")  # keepme not chore/feat/fix
        if args[:3] == ["git", "branch", "-vv"]:
            return _r(0, "  feat/X-thing  abc123 [origin/feat/X-thing: gone] msg\n  main def [origin/main] x\n")
        return _r()
    got = cleanable_branches("main", run=run)
    assert "chore/SCRUM-1-adopt-emkeel" in got     # merged
    assert "feat/X-thing" in got                    # upstream gone (squash-merge case)
    assert "keepme" not in got and "main" not in got


def test_sync_runs_checkout_pull_prune_delete():
    ran = []
    def run(args, capture=True, timeout=None):
        ran.append(" ".join(args))
        if args[:3] == ["git", "symbolic-ref", "refs/remotes/origin/HEAD"]:
            return _r(0, "refs/remotes/origin/main\n")
        if args[:3] == ["git", "branch", "--merged"]:
            return _r(0, "  chore/SCRUM-1-adopt-emkeel\n")
        if args[:3] == ["git", "branch", "-vv"]:
            return _r(0, "")
        return _r()
    out = sync(run=run)
    j = "\n".join(ran)
    assert "git checkout main" in j and "git pull --ff-only" in j and "git fetch --prune" in j
    assert "git branch -D chore/SCRUM-1-adopt-emkeel" in j
    assert any("removed merged" in line for line in out)


def test_wait_for_merge_polls_until_merged():
    states = iter(["OPEN", "OPEN", "MERGED"])
    slept = []
    def run(args, **k):
        return _r(0, next(states))
    assert wait_for_merge("chore/x", run=run, tries=5, delay=0, sleep=lambda d: slept.append(d)) is True


def test_wait_for_merge_times_out():
    def run(args, **k):
        return _r(0, "OPEN")
    assert wait_for_merge("chore/x", run=run, tries=3, delay=0, sleep=lambda d: None) is False
