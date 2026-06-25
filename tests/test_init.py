"""Tests for emkeel init. Born with main() coverage (KEEL-2 lesson)."""

import json
from pathlib import Path

from emkeel.init import (
    APPEND_LINES,
    SELF_EXEMPT_WIRING,
    Config,
    _is_generated_skill,
    _settings_with_guard,
    _strategy_skill,
    apply,
    connection_checklist,
    is_self_repo,
    main,
    plan,
    self_exempt,
)

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def _kinds(actions):
    return {a.path: a.kind for a in actions}


# ── isolation hook distribution: merge into .claude/settings.json without clobbering (KEEL-90) ──

def test_settings_merge_creates_when_absent():
    out = json.loads(_settings_with_guard(None))
    matchers = [e["matcher"] for e in out["hooks"]["PreToolUse"]]
    assert "Bash" in matchers and "Edit|Write" in matchers
    assert any(h["command"] == "emkeel guard" for e in out["hooks"]["PreToolUse"] for h in e["hooks"])


def test_settings_merge_preserves_existing_content():
    existing = json.dumps({"model": "opus", "hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "my-own-hook"}]}]}})
    out = json.loads(_settings_with_guard(existing))
    assert out["model"] == "opus"                                  # untouched
    cmds = [h["command"] for e in out["hooks"]["PreToolUse"] for h in e["hooks"]]
    assert "my-own-hook" in cmds and "emkeel guard" in cmds        # both present, not clobbered


def test_settings_merge_is_idempotent():
    once = _settings_with_guard(None)
    assert _settings_with_guard(once) is None                     # already wired → no change


def test_settings_merge_unparseable_is_left_untouched():
    assert _settings_with_guard("{ not json") is None             # never clobber a user's file


def test_apply_merges_settings_and_managed_path(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    s = json.loads((tmp_path / ".claude/settings.json").read_text())
    assert any(h["command"] == "emkeel guard" for e in s["hooks"]["PreToolUse"] for h in e["hooks"])
    # the maint lane may touch the merged settings file
    from emkeel.gates.check_maint_scope import managed_paths
    assert ".claude/settings.json" in managed_paths()


def test_apply_merge_does_not_clobber_user_settings(tmp_path):
    sp = tmp_path / ".claude/settings.json"
    sp.parent.mkdir(parents=True)
    sp.write_text(json.dumps({"permissions": {"deny": ["Bash(rm:*)"]}}))
    apply(tmp_path, CFG, force=False, dry_run=False)
    s = json.loads(sp.read_text())
    assert s["permissions"] == {"deny": ["Bash(rm:*)"]}           # user content preserved
    assert any(h["command"] == "emkeel guard" for e in s["hooks"]["PreToolUse"] for h in e["hooks"])


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


def test_scaffolds_scoped_credential_wiring(tmp_path):
    # KEEL-93: the NON-secret scaffold for per-repo scoped creds (no secrets written by init).
    apply(tmp_path, CFG, force=False, dry_run=False)
    envrc = (tmp_path / ".envrc").read_text()
    assert "source .envrc" in envrc or ". ./.env" in envrc            # the per-repo loader
    example = (tmp_path / ".env.example").read_text()
    assert "GH_TOKEN" in example and "fine-grained" in example.lower()
    assert ".env" in (tmp_path / ".gitignore").read_text().splitlines()   # .env stays gitignored
    assert not (tmp_path / ".env").exists()                          # init NEVER writes the secret .env


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


def test_ci_includes_dependabot_scope_gate(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert "check_dependabot_scope" in ci


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


def test_ci_includes_strategy_process_gate(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert "check_strategy_process" in ci


def test_ci_includes_critical_integration_gate(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert "check_critical_integration" in ci


def test_agents_contract_demands_integration_test_and_self_sufficiency(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "tests/integration/" in agents and "INTEGRATION test" in agents
    assert "self-sufficient" in agents and "direnv" in agents
    assert "2>/dev/null" in agents


def test_strategy_skill_drives_the_engine(tmp_path):
    # KEEL-100: the distributed skill must DRIVE the process engine, not just call new/check.
    apply(tmp_path, CFG, force=False, dry_run=False)
    skill = (tmp_path / ".claude/skills/strategy/SKILL.md").read_text()
    for step in ("scaffolded", "researched", "proposed", "critiqued", "checked", "presented", "approved"):
        assert f"emkeel strategy advance {step}" in skill, step
    assert "internal_only=true" in skill                       # explicit no-market declaration
    assert "process.json" in skill                             # commit the state alongside the doc
    assert "No web access" not in skill                        # the old escape hatch is gone


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


# ── self-repo: apply() must EXEMPT the distributed wiring it doesn't use (KEEL-96) ──
# The KEEL-95 bug: wiring_drift (detection) exempted these, but apply (action) still wrote them
# → `emkeel update` clobbered emkeel's own main. The fix makes BOTH consult is_self_repo + SELF_EXEMPT_WIRING.

def _make_self(tmp_path):
    """A repo that auto-detects as emkeel (ships the package: pyproject name=emkeel)."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "emkeel"\nversion = "9.9.9"\n')


def test_apply_self_repo_does_not_write_exempt_wiring(tmp_path):
    _make_self(tmp_path)
    bespoke = {rel: f"BESPOKE {rel}\n" for rel in SELF_EXEMPT_WIRING}
    for rel, body in bespoke.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(body)
    apply(tmp_path, CFG, force=True, dry_run=False)              # force = the `emkeel update` action
    for rel, body in bespoke.items():
        assert (tmp_path / rel).read_text() == body, f"apply clobbered {rel} in the self-repo"


def test_consumer_apply_writes_distributed_wiring(tmp_path):
    # baseline: a normal consumer (no emkeel package) DOES get the distributed wiring — unchanged.
    apply(tmp_path, CFG, force=True, dry_run=False)
    assert (tmp_path / "AGENTS.md").read_text().startswith("# AGENTS.md")
    assert (tmp_path / ".github/workflows/emkeel-ci.yml").is_file()


def test_detection_equals_action_lock_in_self_repo(tmp_path):
    # THE REGRESSION LOCK: the set apply SKIPS for self == the set wiring_drift EXEMPTS for self.
    # If one logic changes without the other, this fails — the KEEL-95 divergence can't recur.
    _make_self(tmp_path)
    apply(tmp_path, CFG, force=False, dry_run=False)            # scaffold once (writes pyproject-less files…)
    _make_self(tmp_path)                                        # …then mark self
    skipped_by_apply = {a.path for a in plan(tmp_path, CFG, force=True) if a.kind == "skip-self"}
    assert skipped_by_apply == set(SELF_EXEMPT_WIRING)
    # and wiring_drift exempts exactly those: make each distributed file drift, none should be reported.
    from emkeel.update import wiring_drift
    for rel in SELF_EXEMPT_WIRING:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("drifted\n")
    exempted_by_drift = set(SELF_EXEMPT_WIRING) - set(wiring_drift(tmp_path))
    assert exempted_by_drift == set(SELF_EXEMPT_WIRING)         # detection == action


def test_is_self_repo_autodetect_survives_toml_rewrite(tmp_path):
    # robust: auto-detection (pyproject name=emkeel) is primary — survives a clobbered/rewritten emkeel.toml.
    _make_self(tmp_path)
    (tmp_path / "emkeel.toml").write_text('[github]\nrepo = "o/r"\n[emkeel]\ngenerated_with = "9.9.9"\n')  # no self marker
    assert is_self_repo(tmp_path) is True                       # still self, via pyproject


# ── self-repo: GENERATED skills DO install (so emkeel can dogfood its own /strategy) — KEEL-107 ──

def test_self_exempt_skips_hand_source_but_not_generated_skills():
    for src in ("AGENTS.md", "CLAUDE.md", ".github/workflows/emkeel-ci.yml"):
        assert self_exempt(src) is True                         # hand-maintained source → skipped in self repo
    skill = ".claude/skills/strategy/SKILL.md"
    assert _is_generated_skill(skill) is True
    assert self_exempt(skill) is False                          # generated skill → installed, never skipped


def test_generated_skill_rule_is_general():
    # any future generated skill self-installs, not just /strategy
    assert _is_generated_skill(".claude/skills/anything-new/SKILL.md") is True
    assert _is_generated_skill(".github/workflows/emkeel-ci.yml") is False


def test_self_repo_installs_the_generated_strategy_skill(tmp_path):
    # THE FIX: the skill is no longer skipped in the emkeel repo — apply WRITES it so /strategy can run.
    _make_self(tmp_path)
    skill = ".claude/skills/strategy/SKILL.md"
    actions = plan(tmp_path, CFG, force=True)
    kinds = {a.path: a.kind for a in actions}
    assert kinds[skill] != "skip-self"                         # installed, not exempted…
    assert kinds["AGENTS.md"] == "skip-self"                   # …while hand source stays exempt
    apply(tmp_path, CFG, force=True, dry_run=False)
    assert (tmp_path / skill).read_text() == _strategy_skill()  # and it's the generated skill verbatim
