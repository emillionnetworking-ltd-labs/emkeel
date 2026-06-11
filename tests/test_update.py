"""Tests for emkeel update (refresh wiring to the installed version)."""

from emkeel.init import Config, apply
from emkeel.update import load_cfg, main

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def test_load_cfg_reads_emkeel_toml(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)        # writes emkeel.toml
    cfg = load_cfg(tmp_path)
    assert cfg.github_repo == "o/r" and cfg.jira_project == "DEMO"
    assert cfg.jira_url == "https://x.atlassian.net"


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


def test_update_noop_when_current(tmp_path, monkeypatch, capsys):
    apply(tmp_path, CFG, force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    from emkeel.update import main as update_main
    assert update_main() == 0
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
    (tmp_path / "AGENTS.md").write_text("stale")          # force a real change
    monkeypatch.chdir(tmp_path)
    calls = []
    import emkeel.ship as shipmod
    monkeypatch.setattr(shipmod, "ship", lambda paths, target=None: calls.append(paths) or 0)
    from emkeel.update import main as update_main
    assert update_main([]) == 0
    assert calls and "AGENTS.md" in calls[0]              # shipped without any flag


def test_update_no_ship_leaves_pending(tmp_path, monkeypatch, capsys):
    apply(tmp_path, CFG, force=False, dry_run=False)
    (tmp_path / "AGENTS.md").write_text("stale")
    monkeypatch.chdir(tmp_path)
    calls = []
    import emkeel.ship as shipmod
    monkeypatch.setattr(shipmod, "ship", lambda paths, target=None: calls.append(paths) or 0)
    from emkeel.update import main as update_main
    assert update_main(["--no-ship"]) == 0
    assert calls == [] and "no-ship" in capsys.readouterr().out.lower()
