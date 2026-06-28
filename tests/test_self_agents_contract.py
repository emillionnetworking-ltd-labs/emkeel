"""emkeel must follow its OWN distributed contract — not ship a rule it doesn't itself carry.

The 'How to respond' block lives in `_agents_md()` (the contract every governed repo inherits). emkeel's own
AGENTS.md is hand-maintained (self-exempt from `emkeel update`), so it can silently lack — or drift from —
the very rule it ships. This locks them: the canonical block must appear verbatim in the repo's AGENTS.md.
"""

import pathlib

from emkeel.init import _agents_md

AGENTS_MD = pathlib.Path(__file__).resolve().parents[1] / "AGENTS.md"


def _section(md: str, title: str) -> str:
    """The lines of `## {title}` up to the next `## ` heading (inclusive of the heading)."""
    out, capturing = [], False
    for line in md.splitlines():
        if line.strip() == f"## {title}":
            capturing = True
        elif capturing and line.startswith("## "):
            break
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


# The behavioral rules emkeel distributes AND must itself follow (response style + act-vs-wait).
BEHAVIORAL_SECTIONS = ("How to respond", "When to act vs wait")


def test_canonical_behavioral_sections_exist():
    md = _agents_md()
    assert "conclusion and your recommendation last" in _section(md, "How to respond")
    assert "WAIT for an explicit go-ahead" in _section(md, "When to act vs wait")


def test_self_agents_md_carries_the_distributed_behavioral_contract():
    agents = AGENTS_MD.read_text(encoding="utf-8")
    for title in BEHAVIORAL_SECTIONS:
        block = _section(_agents_md(), title)
        assert block, f"_agents_md() is missing its '## {title}' section"
        assert block in agents, (
            f"emkeel's own AGENTS.md is missing (or has drifted from) the canonical '## {title}' block it "
            f"distributes via _agents_md(). Copy the block verbatim into AGENTS.md.")
