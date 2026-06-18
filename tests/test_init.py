"""Tests for emkeel init. Born with main() coverage (KEEL-2 lesson)."""

from pathlib import Path

from emkeel.init import APPEND_LINES, Config, apply, connection_checklist, main, plan

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def _kinds(actions):
    return {a.path: a.kind for a in actions}


def test_plan_on_empty_target_creates_everything(tmp_path):
    k = _kinds(plan(tmp_path, CFG, force=False))
    assert k["emkeel.toml"] == "create"
    assert k[".github/workflows/emkeel-ci.yml"] == "create"
    assert k[".github/workflows/jira-transition.yml"] == "create"
    assert k["AGENTS.md"] == "create"
    assert k["CLAUDE.md"] == "create"
    assert k[".gitattributes"] == "append"
    assert k[".gitignore"] == "append"


def test_claude_md_imports_agents(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert "@AGENTS.md" in (tmp_path / "CLAUDE.md").read_text()

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


def test_emkeel_source_flows_into_ci_and_toml(tmp_path):
    src = "git+https://x-access-token:${EMKEEL_INSTALL_TOKEN}@github.com/o/emkeel.git"
    cfg = Config(github_repo="o/r", emkeel_source=src)
    apply(tmp_path, cfg, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    jira = (tmp_path / ".github/workflows/jira-transition.yml").read_text()
    toml = (tmp_path / "emkeel.toml").read_text()
    assert f'pip install "{src}"' in ci
    assert f'pip install "{src}"' in jira
    assert f'source = "{src}"' in toml


def test_ci_ticket_link_gets_jira_secrets(tmp_path):
    # KEEL-83: the ticket-link gate is wired to the Jira secrets so it can verify existence.
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    block = ci.split("check_ticket_link")[0]
    assert "JIRA_BASE_URL" in block and "JIRA_TOKEN" in block


def test_jira_transition_has_no_blind_continue_on_error(tmp_path):
    # KEEL-83: real transition failures must surface, not be swallowed.
    apply(tmp_path, CFG, force=False, dry_run=False)
    jira = (tmp_path / ".github/workflows/jira-transition.yml").read_text()
    assert "continue-on-error: true" not in jira      # the blind directive is gone (a comment may mention it)


def test_default_source_is_pypi_version_pinned(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert 'pip install "emkeel~=' in ci        # PyPI, compatible-release pinned
    assert 'pip install "emkeel"' not in ci     # never bare/unpinned


def test_checklist_mentions_token_only_for_private_source():
    private = connection_checklist(Config(emkeel_source="git+https://x-access-token:${EMKEEL_INSTALL_TOKEN}@x/emkeel.git"))
    public = connection_checklist(Config(emkeel_source="emkeel"))
    assert "EMKEEL_INSTALL_TOKEN" in private
    assert "EMKEEL_INSTALL_TOKEN" not in public


def test_main_smoke(tmp_path, capsys):
    rc = main([str(tmp_path), "--jira-project", "DEMO", "--github-repo", "o/r"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "emkeel init [applied]" in out and "NEXT — connect Emkeel" in out
    assert "https://github.com/o/r/settings/secrets/actions/new" in out  # link-rich
    assert (tmp_path / "emkeel.toml").is_file()


def test_toml_stamps_generated_with(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert "generated_with" in (tmp_path / "emkeel.toml").read_text()


def test_scaffolds_strategy_dir(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert (tmp_path / "emkeel-governance/strategy/.gitkeep").is_file()


def test_ci_includes_strategy_gate(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert "check_strategy_link" in (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()


def test_agents_md_mentions_strategy(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    assert "Strategy:" in (tmp_path / "AGENTS.md").read_text()


def test_ci_includes_maint_scope_gate(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert "check_maint_scope" in ci and "fetch-depth: 0" in ci


def test_scaffolds_strategy_skill(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    skill = tmp_path / ".claude/skills/strategy/SKILL.md"
    assert skill.is_file()
    txt = skill.read_text()
    assert "name: strategy" in txt
    assert "emkeel strategy new" in txt and "emkeel strategy check" in txt   # leans on the tested CLI
    assert "human gate" in txt.lower() and "from memory" in txt.lower()      # anti-hallucination rules


def test_ci_includes_strategy_quality_gate(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert "check_strategy_quality" in ci


def test_ci_includes_strategy_change_gate(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert "check_strategy_change" in ci and "EMKEEL_BASE_REF" in ci


def test_ci_includes_strategy_alignment_gate(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert "check_strategy_alignment" in ci


def test_agents_md_documents_strategy_lane(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "strategy/<KEY-123>-slug" in agents and "check_strategy_change" in agents


def test_agents_md_documents_alignment(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "## Alignment" in agents and "check_strategy_alignment" in agents


def test_agents_md_mentions_docs_convention(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "product reference" in agents and "docs/archive/" in agents
