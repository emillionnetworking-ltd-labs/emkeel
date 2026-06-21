"""Tests for emkeel update (refresh wiring to the installed version)."""

from emkeel.init import Config, apply
from emkeel.update import load_cfg, main

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def test_load_cfg_reads_emkeel_toml(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)        # writes emkeel.toml
    cfg = load_cfg(tmp_path)
    assert cfg.github_repo == "o/r" and cfg.jira_project == "DEMO"
    assert cfg.jira_url == "https://x.atlassian.net"


def test_load_cfg_required_checks_default(tmp_path):
    # absent key → backward-compatible default of just ["gates"].
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert load_cfg(tmp_path).required_checks == ["gates"]


def test_load_cfg_required_checks_declared(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    toml = (tmp_path / "emkeel.toml").read_text()
    toml = toml.replace('repo = "o/r"\n',
                        'repo = "o/r"\nrequired_checks = ["gates", "Security Gate (All Checks)"]\n')
    (tmp_path / "emkeel.toml").write_text(toml)
    assert load_cfg(tmp_path).required_checks == ["gates", "Security Gate (All Checks)"]


def test_load_cfg_missing(tmp_path):
    assert load_cfg(tmp_path) is None


def test_update_refreshes_stale_wiring(tmp_path, monkeypatch):
    apply(tmp_path, CFG, force=False, dry_run=False)
    # simulate an OLD AGENTS.md (adopted on an earlier version, no onboard rule)
    (tmp_path / "AGENTS.md").write_text("# old contract\nno rule here\n")
    (tmp_path / "emkeel-governance" / "specs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "emkeel-governance" / "specs" / "MINE.md").write_text("my spec")
    monkeypatch.chdir(tmp_path)
    assert main(["--no-ship"]) == 0
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "Rules that matter live in CI" in agents and "no rule here" not in agents  # refreshed to current template
    assert (tmp_path / "emkeel-governance" / "specs" / "MINE.md").read_text() == "my spec"  # artifacts untouched


def test_update_without_toml(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main([]) == 1
    assert "emkeel setup" in capsys.readouterr().out


def test_wiring_drift_clean_after_apply(tmp_path):
    from emkeel.update import wiring_drift
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert wiring_drift(tmp_path) == []          # fresh wiring matches current templates


def test_wiring_drift_detects_stale_file(tmp_path):
    from emkeel.update import wiring_drift
    apply(tmp_path, CFG, force=False, dry_run=False)
    (tmp_path / "AGENTS.md").write_text("an old, drifted contract")
    assert "AGENTS.md" in wiring_drift(tmp_path)


def test_wiring_drift_ignores_toml_stamp(tmp_path):
    # emkeel.toml carries a version stamp that differs across versions — never counts as drift.
    from emkeel.update import wiring_drift
    apply(tmp_path, CFG, force=False, dry_run=False)
    (tmp_path / "emkeel.toml").write_text('[github]\nrepo = "o/r"\n[emkeel]\ngenerated_with = "0.0.1"\n')
    assert "emkeel.toml" not in wiring_drift(tmp_path)


# ── distribution consistency: init (scratch) and update (refresh) deliver the SAME wiring (KEEL-91) ──

def test_init_equals_update_managed_files_identical(tmp_path):
    """Lock that the two delivery paths produce byte-identical wiring across ALL three manifests
    (_files + APPEND_LINES + MERGE_FILES). Both funnel through apply(); this guards against future
    divergence (e.g. if someone makes update's `mutate` stop calling apply)."""
    from emkeel.init import APPEND_LINES, MERGE_FILES, _files

    init_dir = tmp_path / "init"; init_dir.mkdir()
    upd_dir = tmp_path / "upd"; upd_dir.mkdir()

    apply(init_dir, CFG, force=False, dry_run=False)              # init: scaffold from scratch

    apply(upd_dir, CFG, force=False, dry_run=False)              # update: an older adoption…
    (upd_dir / "AGENTS.md").write_text("STALE contract\n")       # …that drifted
    (upd_dir / "CLAUDE.md").write_text("STALE\n")
    (upd_dir / ".github/workflows/emkeel-ci.yml").unlink()       # …with a missing file
    (upd_dir / ".gitignore").write_text("node_modules\n")        # …and pre-existing user content
    apply(upd_dir, CFG, force=True, dry_run=False)               # the update refresh (force apply)

    # _files: emkeel owns the WHOLE file → byte-identical after both paths.
    for rel in _files(CFG):
        a, b = init_dir / rel, upd_dir / rel
        assert a.is_file() and b.is_file(), f"missing {rel}"
        assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8"), f"init vs update differ: {rel}"
    # APPEND_LINES: emkeel owns only its LINE (user keeps the rest) → the line is present in both.
    for rel, line in APPEND_LINES.items():
        for d in (init_dir, upd_dir):
            assert line in (d / rel).read_text(encoding="utf-8").splitlines(), f"{rel} missing {line!r}"
    # MERGE_FILES: emkeel owns only its merged entries → already present in both (a re-merge is a no-op).
    for rel, fn in MERGE_FILES.items():
        for d in (init_dir, upd_dir):
            assert fn((d / rel).read_text(encoding="utf-8")) is None, f"{rel} not fully merged"


def test_wiring_drift_detects_missing_append_line(tmp_path):
    # THE GAP: an append-manifest file (.gitignore/.gitattributes) missing its line is drift `update`
    # would fix — but wiring_drift didn't check APPEND_LINES, so `emkeel doctor` stayed silent.
    from emkeel.update import wiring_drift
    apply(tmp_path, CFG, force=False, dry_run=False)
    (tmp_path / ".gitignore").write_text("node_modules\n")       # the `.env` line is gone
    assert ".gitignore" in wiring_drift(tmp_path)


def test_wiring_drift_clean_when_append_lines_present(tmp_path):
    from emkeel.update import wiring_drift
    apply(tmp_path, CFG, force=False, dry_run=False)
    drift = wiring_drift(tmp_path)
    assert ".gitignore" not in drift and ".gitattributes" not in drift   # lines present → no drift


def test_update_noop_when_current(tmp_path, monkeypatch, capsys):
    apply(tmp_path, CFG, force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    from emkeel.update import main as update_main
    assert update_main(["--no-ship"]) == 0
    assert "already current" in capsys.readouterr().out.lower()   # 2nd run = honest no-op


def test_update_reports_only_changed(tmp_path, monkeypatch, capsys):
    apply(tmp_path, CFG, force=False, dry_run=False)
    (tmp_path / "AGENTS.md").write_text("stale")
    monkeypatch.chdir(tmp_path)
    from emkeel.update import main as update_main
    assert update_main(["--no-ship"]) == 0
    out = capsys.readouterr().out
    assert "updated" in out and "AGENTS.md" in out and "already current" in out  # only AGENTS.md changed


def test_load_cfg_preserves_source(tmp_path):
    from emkeel.update import load_cfg
    src = "git+https://x-access-token:${T}@github.com/o/emkeel.git"
    apply(tmp_path, Config(github_repo="o/r", emkeel_source=src), force=False, dry_run=False)
    assert load_cfg(tmp_path).emkeel_source == src


def test_update_ships_by_default(tmp_path, monkeypatch):
    apply(tmp_path, CFG, force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    calls = []
    import emkeel.ship as shipmod
    monkeypatch.setattr(shipmod, "ship_update", lambda target=None: calls.append(1) or 0)
    from emkeel.update import main as update_main
    assert update_main([]) == 0
    assert calls                                          # ships (worktree) with no flag


def test_update_hands_off_to_connect_when_cred_pending(tmp_path, monkeypatch, capsys):
    # KEEL-94: after a successful update, if the scoped credential is missing → tell the user the next step.
    apply(tmp_path, CFG, force=False, dry_run=False)       # no .env written by init
    monkeypatch.chdir(tmp_path)
    import emkeel.ship as shipmod
    monkeypatch.setattr(shipmod, "ship_update", lambda target=None: 0)
    from emkeel.update import main as update_main
    assert update_main([]) == 0
    out = capsys.readouterr().out
    assert "emkeel connect" in out and "GH_TOKEN" in out   # handoff names the command AND the variable


def test_update_no_handoff_when_cred_present(tmp_path, monkeypatch, capsys):
    apply(tmp_path, CFG, force=False, dry_run=False)
    (tmp_path / ".env").write_text("GH_TOKEN=github_pat_x\n")
    monkeypatch.chdir(tmp_path)
    import emkeel.ship as shipmod
    monkeypatch.setattr(shipmod, "ship_update", lambda target=None: 0)
    from emkeel.update import main as update_main
    assert update_main([]) == 0
    assert "emkeel connect" not in capsys.readouterr().out  # nothing pending → no handoff


def test_update_no_ship_leaves_pending(tmp_path, monkeypatch, capsys):
    apply(tmp_path, CFG, force=False, dry_run=False)
    (tmp_path / "AGENTS.md").write_text("stale")
    monkeypatch.chdir(tmp_path)
    calls = []
    import emkeel.ship as shipmod
    monkeypatch.setattr(shipmod, "ship_update", lambda target=None: calls.append(1) or 0)
    from emkeel.update import main as update_main
    assert update_main(["--no-ship"]) == 0
    out = capsys.readouterr().out
    assert calls == [] and "no-ship" in out.lower()
    assert (tmp_path / "AGENTS.md").read_text() != "stale"   # refreshed locally


def _wd_git(args, cwd):
    import subprocess
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def test_wiring_drift_clean_when_origin_current(tmp_path):
    # origin/main is current → a feature branch with OLD local wiring shows NO drift
    import subprocess
    from emkeel.update import wiring_drift
    origin = tmp_path / "o.git"; subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    work = tmp_path / "w"; work.mkdir()
    _wd_git(["init", "-q"], work); _wd_git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    _wd_git(["config", "user.email", "t@t.co"], work); _wd_git(["config", "user.name", "t"], work)
    _wd_git(["config", "commit.gpgsign", "false"], work)
    apply(work, CFG, force=False, dry_run=False)                 # current templates
    _wd_git(["add", "-A"], work); _wd_git(["commit", "-qm", "init"], work)
    _wd_git(["remote", "add", "origin", str(origin)], work); _wd_git(["push", "-q", "-u", "origin", "main"], work)
    _wd_git(["checkout", "-qb", "feat"], work)
    (work / "AGENTS.md").write_text("# OLD on feature\n")        # local feature branch behind
    _wd_git(["add", "-A"], work); _wd_git(["commit", "-qm", "feat"], work)
    assert wiring_drift(work) == []                              # measured vs origin/main → clean


def test_wiring_drift_flags_stale_origin(tmp_path):
    import subprocess
    from emkeel.update import wiring_drift
    origin = tmp_path / "o.git"; subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    work = tmp_path / "w"; work.mkdir()
    _wd_git(["init", "-q"], work); _wd_git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    _wd_git(["config", "user.email", "t@t.co"], work); _wd_git(["config", "user.name", "t"], work)
    _wd_git(["config", "commit.gpgsign", "false"], work)
    apply(work, CFG, force=False, dry_run=False)
    (work / "AGENTS.md").write_text("# stale\n")                 # origin will hold an OLD AGENTS.md
    _wd_git(["add", "-A"], work); _wd_git(["commit", "-qm", "init"], work)
    _wd_git(["remote", "add", "origin", str(origin)], work); _wd_git(["push", "-q", "-u", "origin", "main"], work)
    assert "AGENTS.md" in wiring_drift(work)                     # origin/main behind templates → drift


def test_origin_jira_project_reads_origin(tmp_path):
    # origin/main declares ECO; the local feature branch still declares SCRUM → reads ECO (origin)
    import subprocess
    from emkeel.update import origin_jira_project
    origin = tmp_path / "o.git"; subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    work = tmp_path / "w"; work.mkdir()
    _wd_git(["init", "-q"], work); _wd_git(["symbolic-ref", "HEAD", "refs/heads/main"], work)
    _wd_git(["config", "user.email", "t@t.co"], work); _wd_git(["config", "user.name", "t"], work)
    _wd_git(["config", "commit.gpgsign", "false"], work)
    apply(work, Config(jira_project="ECO", github_repo="o/r"), force=False, dry_run=False)
    _wd_git(["add", "-A"], work); _wd_git(["commit", "-qm", "init"], work)
    _wd_git(["remote", "add", "origin", str(origin)], work); _wd_git(["push", "-q", "-u", "origin", "main"], work)
    _wd_git(["checkout", "-qb", "feat"], work)
    (work / "emkeel.toml").write_text((work / "emkeel.toml").read_text().replace('project_key = "ECO"', 'project_key = "SCRUM"'))
    _wd_git(["add", "-A"], work); _wd_git(["commit", "-qm", "feat"], work)
    assert origin_jira_project(work) == "ECO"           # origin/main, not the local SCRUM


def test_origin_jira_project_local_fallback(tmp_path):
    from emkeel.update import origin_jira_project
    apply(tmp_path, Config(jira_project="LOCAL", github_repo="o/r"), force=False, dry_run=False)
    assert origin_jira_project(tmp_path) == "LOCAL"     # no remote → local emkeel.toml
