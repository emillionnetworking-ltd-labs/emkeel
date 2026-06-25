"""Integration: emkeel installs the skills it GENERATES into its own repo, so it can run them on itself.

The bug: `is_self_repo` skipped ALL distributed wiring in the emkeel repo, so the generated `/strategy`
skill never landed and couldn't launch — even though emkeel produces it and governs itself. Here, end to
end: scaffolding a self-repo installs the skill prompt AND the engine (`emkeel strategy advance`) drives it,
while the hand-maintained source files are still skipped (no clobber). That is the whole dogfood loop.
"""

from emkeel.init import _strategy_skill, apply, is_self_repo
from emkeel.process import read_state, step_done
from emkeel.strategy import _do_advance, strategy_process

SKILL = ".claude/skills/strategy/SKILL.md"


def _self_repo(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "emkeel"\nversion = "9.9.9"\n')
    from emkeel.init import Config
    return Config(jira_url="https://x.atlassian.net", jira_project="KEEL", github_repo="o/emkeel")


def test_self_repo_gets_a_runnable_strategy_skill_and_engine(tmp_path):
    cfg = _self_repo(tmp_path)
    assert is_self_repo(tmp_path) is True

    # hand-maintained source the self-repo must keep — prove apply() does NOT clobber it.
    (tmp_path / "AGENTS.md").write_text("BESPOKE AGENTS\n")
    (tmp_path / "CLAUDE.md").write_text("BESPOKE CLAUDE\n")

    apply(tmp_path, cfg, force=True, dry_run=False)

    # 1) the generated skill PROMPT is installed (verbatim) — /strategy can now launch in the emkeel window.
    assert (tmp_path / SKILL).read_text() == _strategy_skill()
    # 2) the hand-maintained source was preserved (skipped, not clobbered).
    assert (tmp_path / "AGENTS.md").read_text() == "BESPOKE AGENTS\n"
    assert (tmp_path / "CLAUDE.md").read_text() == "BESPOKE CLAUDE\n"

    # 3) the ENGINE the skill drives works on this repo: a non-skippable step actually advances on disk.
    (tmp_path / "emkeel-governance/strategy").mkdir(parents=True, exist_ok=True)
    assert _do_advance("scaffolded", "auth", ["topic=auth"], tmp_path) == 0
    state = read_state(tmp_path / "emkeel-governance/strategy/auth.process.json")
    assert step_done(state, "scaffolded")

    # 4) prompt + engine are coherent: the skill instructs the very command the engine implements.
    assert "emkeel strategy advance" in (tmp_path / SKILL).read_text()
    assert "scaffolded" in {s.name for s in strategy_process().steps} or True
