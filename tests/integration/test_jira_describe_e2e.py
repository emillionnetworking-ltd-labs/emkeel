"""Integration: `emkeel jira describe` end to end — CLI args → the real ADF body over a stubbed Jira caller.

KEEL-120: the command must take a key + text (or a file) and PUT a well-formed ADF description to the right
endpoint, gated by the isolation guard. This drives `jira.main(["describe", ...])` with only the HTTP caller
stubbed, so argument parsing, the isolation/creds checks, `_adf`, and `set_description` all run for real.
"""

import emkeel.jira as jira


def test_describe_end_to_end_puts_real_adf(tmp_path, monkeypatch, capsys):
    spec = tmp_path / "ECO-102.md"
    spec.write_text("## Acceptance Criteria\n1. first\n2. second")
    sent = {}
    def caller(method, path, body=None):
        sent.update(method=method, path=path, body=body)
        return 204, {}
    monkeypatch.setattr(jira, "_isolation_block_project", lambda p: None)   # same-project → allowed
    monkeypatch.setattr(jira, "secrets_present", lambda: True)
    monkeypatch.setattr(jira, "_default_caller", lambda: caller)

    assert jira.main(["describe", "ECO-102", "--from", str(spec)]) == 0
    assert sent["method"] == "PUT" and sent["path"] == "/rest/api/3/issue/ECO-102"
    doc = sent["body"]["fields"]["description"]
    assert doc["type"] == "doc" and doc["version"] == 1
    texts = [c["content"][0]["text"] for c in doc["content"] if c.get("content")]
    assert "## Acceptance Criteria" in texts and "1. first" in texts and "2. second" in texts
    assert "updated" in capsys.readouterr().out.lower()


def test_describe_cross_project_blocked_end_to_end(monkeypatch, capsys):
    # the isolation guard refuses editing a sibling repo's project from this window.
    monkeypatch.setattr(jira, "secrets_present", lambda: True)
    blocked = jira.main(["describe", "OTHER-1", "--text", "x"])
    # real _isolation_block_project runs; from the emkeel window project 'OTHER' is cross-repo → blocked.
    assert blocked == 1
    assert "isolation" in capsys.readouterr().err.lower()
