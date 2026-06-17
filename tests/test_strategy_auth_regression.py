"""Permanent regression guard: em-ecosystem's APPROVED auth.md mixes file:line, real spec URLs
(NIST/FIDO/RFC9700) and an external citation to a frozen out-of-tree repo. Source resolution must keep
PASSING it — its external citations are WARN, never FAIL. If this breaks, the design is wrong (KEEL-78)."""

from emkeel.strategy import _do_check, main, review_strategy

# Replicates the real approved doc's source mix per option.
AUTH_MD = """# Strategy: auth
Status: APPROVED
Strategy: auth

## Goal
Multi-tenant authentication for the em-ecosystem.

## Context
- Current bespoke sessions live in src/em_auth/session.py:42 (rotated cookies).
- NIST 800-63B and OWASP guidance favour short-lived tokens.

## Options
| # | Option | Source | Pros | Cons | Risk |
|---|--------|--------|------|------|------|
| 1 | Rotating JWT + refresh | src/em_auth/session.py:42 | stateless | revocation lag | mid |
| 2 | Server sessions per NIST | https://pages.nist.gov/800-63-3/sp800-63b.html | easy revoke | state | low |
| 3 | Passkeys (FIDO2) | https://fidoalliance.org/specifications/ | phishing-resistant | UX migration | mid |
| 4 | OAuth BCP hardening | https://www.rfc-editor.org/rfc/rfc9700 | standardised | scope creep | low |
| 5 | Reuse em-auth v2 decision | AUTH-v2.md §5 D-002 (frozen em-auth repo) | proven | out of tree | low |

## Recommendation
Option 1 now, migrate toward Option 3 (passkeys) — judgment, approved by a human at the gate.

## Non-goals
- No social login in this phase.
"""


def _make_auth(tmp_path):
    f = tmp_path / "src/em_auth/session.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(f"# session line {i}" for i in range(1, 60)))   # :42 resolves
    d = tmp_path / "emkeel-governance/strategy"
    d.mkdir(parents=True, exist_ok=True)
    (d / "auth.md").write_text(AUTH_MD)


def test_auth_md_real_mix_still_passes(tmp_path):
    _make_auth(tmp_path)
    assert _do_check("auth", tmp_path) == 0           # AC4: the approved doc keeps passing


def test_auth_md_external_citation_is_warn_only(tmp_path):
    _make_auth(tmp_path)
    fails, warns, unverifiable = review_strategy(AUTH_MD, tmp_path)
    assert fails == []                                # no FAIL on the legitimate mix
    assert unverifiable == 1                          # the frozen-repo citation
    assert any("AUTH-v2.md" in w for w in warns)


def test_check_urls_flag_is_warn_only(tmp_path, monkeypatch):
    """--check-urls touches the network (opt-in, local). Unreachable URLs WARN, never FAIL."""
    _make_auth(tmp_path)
    import urllib.request

    def boom(*a, **k):
        raise OSError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    assert main(["check", "auth", "--check-urls"]) == 0   # WARNs only → still passes
