"""Integration: the governance-doc-conventions gate end to end + shipped into a scaffolded repo's CI.

Reproduces the lived bug (a localized field key reads as 'absent' silently) as a LOUD failure, proves
bidirectional supersession across files, and confirms `emkeel init` wires the gate into every governed
repo's generated CI — the whole point of ADR-0008 / KEEL-109.
"""

import emkeel.gates.check_doc_conventions as g
from emkeel.init import Config, apply


def _adr_dir(tmp_path):
    d = tmp_path / g.GOVERNANCE_DIR / g.ADR_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _adr(d, n, body):
    (d / f"{n:04d}-x.md").write_text(f"# {n}. x\n\n{body}\n## Context\np\n")


def _doc(tmp_path, subdir, name, body):
    d = tmp_path / g.GOVERNANCE_DIR / subdir
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(body)


def test_localized_key_blocks_and_canonical_passes(tmp_path, monkeypatch):
    d = _adr_dir(tmp_path)
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    # the incident: a localized key — silent false-negative before, a loud FAIL now.
    _adr(d, 1, "- Estado: accepted\n- Date: 2026-01-01\n- Deciders: op\n")
    assert g.main() == 1
    # fix it to the canonical English key → passes.
    _adr(d, 1, "- Status: accepted\n- Date: 2026-01-01\n- Deciders: op\n")
    assert g.main() == 0


def test_language_rule_now_covers_specs_strategy_and_future_types(tmp_path, monkeypatch):
    # THE GENERALIZATION: the localized-key ban reaches every artifact type, not just ADRs —
    # including a brand-new type (playbooks/) that has no per-type gate.
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    _adr(_adr_dir(tmp_path), 1, "- Status: accepted\n- Date: 2026-01-01\n- Deciders: op\n")  # clean ADR
    _doc(tmp_path, "specs", "KEEL-9.md", "# Spec\nEstrategia: none\n")           # localized in a spec
    assert g.main() == 1
    _doc(tmp_path, "specs", "KEEL-9.md", "# Spec\nStrategy: none\n")             # fix the spec
    assert g.main() == 0
    _doc(tmp_path, "playbooks", "deploy.md", "# Playbook\n## Alineación\nx\n")    # localized in a NEW type
    assert g.main() == 1


def test_supersession_must_be_bidirectional_end_to_end(tmp_path, monkeypatch):
    d = _adr_dir(tmp_path)
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    # X supersedes Y, but Y forgets the backlink → FAIL.
    _adr(d, 1, "- Status: accepted\n- Date: 2026-01-01\n- Deciders: op\n")
    _adr(d, 2, "- Status: accepted\n- Date: 2026-02-01\n- Deciders: op\n- Supersedes: ADR-0001\n")
    assert g.main() == 1
    # add Y's backlink + flip Y's status → the graph is coherent → PASS.
    _adr(d, 1, "- Status: superseded\n- Date: 2026-01-01\n- Deciders: op\n- Superseded-by: ADR-0002\n")
    assert g.main() == 0


def test_init_wires_the_gate_into_generated_ci(tmp_path):
    apply(tmp_path, Config(jira_url="https://x", jira_project="DEMO", github_repo="o/r"),
          force=True, dry_run=False)
    ci = (tmp_path / ".github/workflows/emkeel-ci.yml").read_text()
    assert "check_doc_conventions" in ci          # shipped to every governed repo's CI
