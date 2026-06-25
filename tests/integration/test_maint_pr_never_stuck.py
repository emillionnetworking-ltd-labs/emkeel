"""Integration: a maint PR never gets stuck in silence — `emkeel update` refreshes a stale one.

The #467 trap end to end: a maint PR forked before a migration is BEHIND main and therefore FAILING the new
gates. Re-running its CI on the stale branch would fail forever. `emkeel update` (the natural recovery) must
REFRESH it against current main so its CI re-runs fresh — in place, no duplicate, never dead-ended. Only the
gh boundary is faked; the real ship flow runs.
"""

import subprocess
from types import SimpleNamespace

from emkeel.ship import ship_update


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _seeded_with_remote(tmp_path):
    import emkeel.init as init
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(["init", "--bare", "-q"], origin)
    work = tmp_path / "work"
    work.mkdir()
    _git(["init", "-q"], work)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], work)     # force 'main' (CI's git defaults to master)
    _git(["config", "user.email", "t@t"], work)
    _git(["config", "user.name", "t"], work)
    init.apply(work, init.Config(jira_url="https://x", jira_project="ECO", github_repo="o/r"),
               force=True, dry_run=False)
    _git(["add", "-A"], work)
    _git(["commit", "-qm", "init"], work)
    _git(["remote", "add", "origin", str(origin)], work)
    _git(["push", "-q", "-u", "origin", "main"], work)
    return origin, work


def _fake_gh(calls, *, rollup, merge_state, update_rc):
    import json

    def run(args, stdin=None, timeout=None, capture=True):
        calls.append(" ".join(str(a) for a in args))
        if args and args[0] == "gh":
            j = " ".join(args)
            if "auth status" in j:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "update-branch" in j:
                return SimpleNamespace(returncode=update_rc, stdout="",
                                       stderr="" if update_rc == 0 else "up to date")
            if "pr list" in j:
                return SimpleNamespace(returncode=0,
                                       stdout='[{"number": 467, "headRefName": "emkeel-maint/0.1.50-old"}]',
                                       stderr="")
            if "pr view" in j:
                return SimpleNamespace(returncode=0, stdout=json.dumps(
                    {"headRefName": "emkeel-maint/0.1.50-old", "mergeStateStatus": merge_state,
                     "statusCheckRollup": rollup}), stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return subprocess.run(args, capture_output=True, text=True)
    return run


def test_emkeel_update_refreshes_a_stale_failing_maint_pr(tmp_path, capsys):
    _origin, work = _seeded_with_remote(tmp_path)
    calls = []
    gh = _fake_gh(calls, rollup=[{"name": "gates", "conclusion": "FAILURE"}],
                  merge_state="BEHIND", update_rc=0)             # behind + failing, refresh succeeds
    assert ship_update(target=work, run=gh) == 0
    out = capsys.readouterr().out.lower()
    assert any("update-branch" in c for c in calls)             # refreshed against current main
    assert "refreshed" in out and "#467" in out
    assert not any("run rerun" in c for c in calls)             # never re-ran the stale branch
    assert not any("pr create" in c for c in calls)             # no duplicate PR
