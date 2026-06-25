"""Tests for check_doc_conventions — canonical English field names across ALL governed artifacts +
bidirectional ADR supersession (ADR-0008, generalized in KEEL-110)."""

import emkeel.gates.check_doc_conventions as g

CANON = "- Status: accepted\n- Date: 2026-06-25\n- Deciders: operator\n"


def _gov(tmp_path, subdir):
    d = tmp_path / g.GOVERNANCE_DIR / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _adr(tmp_path, n, body):
    (_gov(tmp_path, g.ADR_SUBDIR) / f"{n:04d}-x.md").write_text(f"# {n}. x\n\n{body}\n## Context\nprose\n")


def _doc(tmp_path, subdir, name, body):
    (_gov(tmp_path, subdir) / name).write_text(body)


def _run(tmp_path, monkeypatch):
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    return g.main()


# ── dormant + happy path ────────────────────────────────────────────────────────

def test_dormant_without_governance_dir(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch) == 0


def test_dormant_when_no_docs(tmp_path, monkeypatch):
    _gov(tmp_path, g.ADR_SUBDIR)
    assert _run(tmp_path, monkeypatch) == 0


def test_canonical_artifacts_pass(tmp_path, monkeypatch):
    _adr(tmp_path, 1, CANON)
    _doc(tmp_path, "specs", "KEEL-1.md", "# Spec\nStrategy: none\n## Acceptance Criteria\n- a\n")
    assert _run(tmp_path, monkeypatch) == 0


# ── ADR structural rules (unchanged, still ADR-scoped) ──────────────────────────

def test_missing_required_field_fails(tmp_path, monkeypatch, capsys):
    _adr(tmp_path, 1, "- Status: accepted\n- Date: 2026-06-25\n")              # no Deciders
    assert _run(tmp_path, monkeypatch) == 1
    assert "Deciders" in capsys.readouterr().err


def test_status_out_of_enum_fails(tmp_path, monkeypatch, capsys):
    _adr(tmp_path, 1, "- Status: yolo\n- Date: 2026-06-25\n- Deciders: op\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "enum" in capsys.readouterr().err


def test_specs_do_not_get_adr_structural_rules(tmp_path, monkeypatch):
    # a spec has no Status/Date/Deciders — that's fine; the structural rules are ADR-only.
    _doc(tmp_path, "specs", "KEEL-1.md", "# Spec\nStrategy: none\n## Acceptance Criteria\n- a\n")
    assert _run(tmp_path, monkeypatch) == 0


# ── the UNIVERSAL language rule — localized keys/headings banned in EVERY artifact type ──

def test_localized_key_in_adr_fails_loud(tmp_path, monkeypatch, capsys):
    _adr(tmp_path, 1, "- Estado: accepted\n- Date: 2026-06-25\n- Deciders: op\n")
    assert _run(tmp_path, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "Estado:" in err and "Status:" in err


def test_localized_strategy_key_in_spec_fails(tmp_path, monkeypatch, capsys):
    # THE GAP this PR closes: a localized inline field key in a SPEC (not an ADR) → loud FAIL.
    _doc(tmp_path, "specs", "KEEL-1.md", "# Spec\nEstrategia: none\n## Acceptance Criteria\n- a\n")
    assert _run(tmp_path, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "Estrategia:" in err and "Strategy:" in err


def test_localized_heading_in_spec_fails(tmp_path, monkeypatch, capsys):
    # a localized SECTION HEADING in a spec → loud FAIL (was silently 'absent' before).
    _doc(tmp_path, "specs", "KEEL-1.md", "# Spec\nStrategy: none\n## Criterios de Aceptación\n- a\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "Acceptance Criteria" in capsys.readouterr().err


def test_localized_key_in_strategy_doc_fails(tmp_path, monkeypatch, capsys):
    _doc(tmp_path, "strategy", "auth.md", "# Strategy: auth\nEstado: DRAFT\n## Goal\nx\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "Status:" in capsys.readouterr().err


def test_accent_insensitive_match(tmp_path, monkeypatch):
    # 'Alineación' and 'Alineacion' both map to the canonical heading.
    assert g._norm("Alineación") == "alineacion"
    assert g._norm("Alineacion") in g.BANNED_HEADINGS


# ── FUTURE-PROOF: a brand-new artifact TYPE is covered with NO code change ───────

def test_new_artifact_type_is_covered_by_default(tmp_path, monkeypatch, capsys):
    # a subdir that doesn't exist today (no per-type gate) — the recursive scan still catches it.
    _doc(tmp_path, "playbooks", "deploy.md", "# Playbook\nEstrategia: rollback\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "Strategy:" in capsys.readouterr().err


# ── bidirectional supersession (ADR-scoped) ─────────────────────────────────────

def test_bidirectional_supersession_passes(tmp_path, monkeypatch):
    _adr(tmp_path, 1, "- Status: superseded\n- Date: 2026-01-01\n- Deciders: op\n- Superseded-by: ADR-0002\n")
    _adr(tmp_path, 2, "- Status: accepted\n- Date: 2026-02-01\n- Deciders: op\n- Supersedes: ADR-0001\n")
    assert _run(tmp_path, monkeypatch) == 0


def test_one_way_supersede_fails(tmp_path, monkeypatch, capsys):
    _adr(tmp_path, 1, "- Status: superseded\n- Date: 2026-01-01\n- Deciders: op\n")
    _adr(tmp_path, 2, "- Status: accepted\n- Date: 2026-02-01\n- Deciders: op\n- Supersedes: ADR-0001\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "one-way link" in capsys.readouterr().err


def test_refs_parses_adr_forms_and_ignores_stray_numbers():
    assert g._refs("ADR-0007") == {7}
    assert g._refs("ADR-7, 0009") == {7, 9}
    assert g._refs("3 reasons to supersede ADR-0012") == {12}


def test_language_problems_is_reusable_per_doc():
    probs = g.language_problems("- Estado: x\n## Alineación\n", "specs/KEEL-9.md")
    assert len(probs) == 2 and all("specs/KEEL-9.md" in p for p in probs)
