"""Tests for check_doc_conventions — canonical English fields + bidirectional ADR supersession (ADR-0008)."""

import emkeel.gates.check_doc_conventions as g

CANON = "- Status: accepted\n- Date: 2026-06-25\n- Deciders: operator\n"


def _adr(d, n, body):
    (d / f"{n:04d}-x.md").write_text(f"# {n}. x\n\n{body}\n## Context\nprose\n")


def _dir(tmp_path):
    d = tmp_path / g.ADR_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run(tmp_path, monkeypatch):
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    return g.main()


# ── dormant + happy path ────────────────────────────────────────────────────────

def test_dormant_without_adr_dir(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch) == 0


def test_dormant_when_adr_dir_empty(tmp_path, monkeypatch):
    _dir(tmp_path)
    assert _run(tmp_path, monkeypatch) == 0


def test_canonical_adr_passes(tmp_path, monkeypatch):
    _adr(_dir(tmp_path), 1, CANON)
    assert _run(tmp_path, monkeypatch) == 0


# ── required fields + enum ──────────────────────────────────────────────────────

def test_missing_required_field_fails(tmp_path, monkeypatch, capsys):
    _adr(_dir(tmp_path), 1, "- Status: accepted\n- Date: 2026-06-25\n")   # no Deciders
    assert _run(tmp_path, monkeypatch) == 1
    assert "Deciders" in capsys.readouterr().err


def test_status_out_of_enum_fails(tmp_path, monkeypatch, capsys):
    _adr(_dir(tmp_path), 1, "- Status: yolo\n- Date: 2026-06-25\n- Deciders: op\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "enum" in capsys.readouterr().err


# ── banned localized keys (the precise anti-recurrence rule) ─────────────────────

def test_localized_key_fails_loud(tmp_path, monkeypatch, capsys):
    # the lived incident: a localized key reads as 'absent' silently — here it FAILS loud.
    _adr(_dir(tmp_path), 1, "- Estado: accepted\n- Date: 2026-06-25\n- Deciders: op\n")
    assert _run(tmp_path, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "Estado:" in err and "Status:" in err           # names the localized key + the canonical one


def test_lint_flags_each_banned_key():
    docs = "- Estado: accepted\n- Fecha: 2026-01-01\n- Decisores: op\n- Reemplaza: ADR-0001\n"
    parsed = g.parse_doc(docs)
    assert set(parsed["banned"]) == {"estado", "fecha", "decisores", "reemplaza"}


# ── bidirectional supersession ──────────────────────────────────────────────────

def test_bidirectional_supersession_passes(tmp_path, monkeypatch):
    d = _dir(tmp_path)
    _adr(d, 1, "- Status: superseded\n- Date: 2026-01-01\n- Deciders: op\n- Superseded-by: ADR-0002\n")
    _adr(d, 2, "- Status: accepted\n- Date: 2026-02-01\n- Deciders: op\n- Supersedes: ADR-0001\n")
    assert _run(tmp_path, monkeypatch) == 0


def test_one_way_supersede_missing_backlink_fails(tmp_path, monkeypatch, capsys):
    d = _dir(tmp_path)
    _adr(d, 1, "- Status: superseded\n- Date: 2026-01-01\n- Deciders: op\n")          # no Superseded-by
    _adr(d, 2, "- Status: accepted\n- Date: 2026-02-01\n- Deciders: op\n- Supersedes: ADR-0001\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "one-way link" in capsys.readouterr().err


def test_superseded_target_must_have_superseded_status(tmp_path, monkeypatch, capsys):
    d = _dir(tmp_path)
    _adr(d, 1, "- Status: accepted\n- Date: 2026-01-01\n- Deciders: op\n- Superseded-by: ADR-0002\n")  # not 'superseded'
    _adr(d, 2, "- Status: accepted\n- Date: 2026-02-01\n- Deciders: op\n- Supersedes: ADR-0001\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "not 'superseded'" in capsys.readouterr().err


def test_supersede_nonexistent_adr_fails(tmp_path, monkeypatch, capsys):
    _adr(_dir(tmp_path), 2, "- Status: accepted\n- Date: 2026-02-01\n- Deciders: op\n- Supersedes: ADR-0099\n")
    assert _run(tmp_path, monkeypatch) == 1
    assert "does not exist" in capsys.readouterr().err


def test_refs_parses_adr_forms_and_ignores_stray_numbers():
    assert g._refs("ADR-0007") == {7}
    assert g._refs("ADR-7, 0009") == {7, 9}
    assert g._refs("3 reasons to supersede ADR-0012") == {12}   # bare '3' ignored, ADR-0012 kept
