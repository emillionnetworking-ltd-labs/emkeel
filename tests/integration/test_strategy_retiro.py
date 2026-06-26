"""Integration: retiring a governed strategy end to end, through the REAL `git diff` plumbing.

KEEL-115: the `check_strategy_process` gate must let a strategy be RETIRED — its `<topic>.md` and
`<topic>.process.json` deleted together as a pair — without FAILing on "process state missing". This drives
a real git repo (commit a driven strategy, then delete it on a branch) so the gate's `--diff-filter=D`
deletion detection is exercised for real, not monkeypatched: a clean retiro PASSES, an orphan FAILS.
"""

import subprocess

import emkeel.gates.check_strategy_process as gate
from emkeel.process import advance_on_disk
from emkeel.strategy import strategy_process

SDIR = "emkeel-governance/strategy"
TS = "2026-06-26T00:00:00Z"
KC = ["the pilot rejects it", "worse than the baseline"]
REALITY = {"case": "ECO-71", "method": "applied to one real case",
           "outcome": "pass", "evidence_ref": "https://example.com/pilot"}
CRIT = {"lens_discovery": "no sitemap; invisible to search", "lens_legal": "no cookie banner; GDPR risk",
        "lens_calibration": "thin vs the real render", "completeness": "no a11y lens — add it"}


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _drive_validated(repo, topic):
    p = repo / SDIR / f"{topic}.process.json"
    s = strategy_process()
    advance_on_disk(s, p, "scaffolded", {"topic": topic, "kill_criteria": KC}, timestamp=TS)
    advance_on_disk(s, p, "researched", {"internal_only": True}, timestamp=TS)
    advance_on_disk(s, p, "proposed", {"options": ["a", "b"]}, timestamp=TS)
    advance_on_disk(s, p, "critiqued", CRIT, timestamp=TS)
    advance_on_disk(s, p, "checked", {"check_passed": True}, timestamp=TS)
    advance_on_disk(s, p, "validated", REALITY, timestamp=TS)
    return p


def _repo_with_committed_strategy(tmp_path, topic="satellites"):
    repo = tmp_path / "repo"
    (repo / SDIR).mkdir(parents=True)
    _git(repo, "init", "-q"); _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
    (repo / SDIR / f"{topic}.md").write_text(f"# Strategy: {topic}\n")
    _drive_validated(repo, topic)
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "add strategy")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")   # origin/main = the base the gate diffs
    _git(repo, "checkout", "-qb", "strategy/KEEL-115-retire")
    return repo


def _run_gate(repo, monkeypatch):
    monkeypatch.chdir(repo)                                  # changed_files/deleted_files diff in cwd
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(repo))
    monkeypatch.delenv("EMKEEL_STRATEGY_DIR", raising=False)
    return gate.main()


def test_clean_retiro_passes_through_real_git(tmp_path, monkeypatch, capsys):
    repo = _repo_with_committed_strategy(tmp_path, "satellites")
    (repo / SDIR / "satellites.md").unlink()                 # delete the PAIR
    (repo / SDIR / "satellites.process.json").unlink()
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "retire satellites")
    assert _run_gate(repo, monkeypatch) == 0                 # real `git diff --diff-filter=D` sees the pair
    assert "retired" in capsys.readouterr().out.lower()


def test_orphan_retiro_fails_through_real_git(tmp_path, monkeypatch, capsys):
    repo = _repo_with_committed_strategy(tmp_path, "satellites")
    (repo / SDIR / "satellites.md").unlink()                 # delete the doc only — sidecar survives
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "delete doc, orphan the process")
    assert _run_gate(repo, monkeypatch) == 1
    assert "orphan" in capsys.readouterr().err.lower()
