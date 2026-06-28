"""Integration: a scaffolded repo inherits emkeel's behavioral contract, end to end through `apply`.

KEEL-119: the behavioral rules emkeel ships in `_agents_md()` (How to respond + When to act vs wait) must
actually land in a governed repo's AGENTS.md. Scaffold a fresh repo and assert both sections, with their
load-bearing lines, are present in the generated file.
"""

from emkeel.init import Config, apply

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def test_scaffolded_repo_inherits_behavioral_contract(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "## How to respond" in agents
    assert "Reserve tables and multi-header layouts" in agents          # the concrete anti-over-structuring rule
    assert "## When to act vs wait" in agents
    assert "WAIT for an explicit go-ahead" in agents                    # the act-vs-wait rule
    assert "restated requirement is NOT approval" in agents
