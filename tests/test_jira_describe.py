"""emkeel jira describe <key> — set/replace an existing ticket's description (so guidance lives on the
ticket/spec, not in an agent's memory)."""

import emkeel.jira as jira


def _recorder():
    calls = []
    def caller(method, path, body=None):
        calls.append((method, path, body))
        return 204, {}
    return calls, caller


def test_adf_splits_lines_into_paragraphs():
    adf = jira._adf("one\n\nthree")
    assert adf["type"] == "doc" and len(adf["content"]) == 3      # text nodes can't hold newlines
    assert adf["content"][0]["content"][0]["text"] == "one"
    assert "content" not in adf["content"][1]                     # blank line → empty paragraph


def test_set_description_puts_adf():
    calls, caller = _recorder()
    ok, msg = jira.set_description("ECO-9", "hello", caller=caller)
    assert ok and "updated" in msg
    method, path, body = calls[0]
    assert method == "PUT" and path == "/rest/api/3/issue/ECO-9"
    assert body["fields"]["description"]["type"] == "doc"


def test_set_description_reports_http_error():
    ok, msg = jira.set_description("ECO-9", "x", caller=lambda m, p, b=None: (403, {}))
    assert not ok and "403" in msg


def _patch(monkeypatch, *, block=None, secrets=True):
    calls, caller = _recorder()
    monkeypatch.setattr(jira, "_isolation_block_project", lambda p: block)
    monkeypatch.setattr(jira, "secrets_present", lambda: secrets)
    monkeypatch.setattr(jira, "_default_caller", lambda: caller)
    return calls


def test_describe_text_via_main(monkeypatch, capsys):
    calls = _patch(monkeypatch)
    assert jira.main(["describe", "ECO-9", "--text", "guidance line"]) == 0
    assert calls[0][0] == "PUT" and "updated" in capsys.readouterr().out.lower()


def test_describe_from_file(tmp_path, monkeypatch):
    f = tmp_path / "d.md"
    f.write_text("from file\nsecond line")
    calls = _patch(monkeypatch)
    assert jira.main(["describe", "ECO-9", "--from", str(f)]) == 0
    texts = [c["content"][0]["text"] for c in calls[0][2]["fields"]["description"]["content"] if c.get("content")]
    assert "from file" in texts and "second line" in texts


def test_describe_isolation_blocked(monkeypatch, capsys):
    _patch(monkeypatch, block="cross-repo refusal")
    assert jira.main(["describe", "FOO-1", "--text", "x"]) == 1
    assert "cross-repo" in capsys.readouterr().err.lower()


def test_describe_no_creds(monkeypatch):
    _patch(monkeypatch, secrets=False)
    assert jira.main(["describe", "ECO-9", "--text", "x"]) == 1


def test_describe_requires_text_or_from(monkeypatch):
    _patch(monkeypatch)
    import pytest
    with pytest.raises(SystemExit):                              # argparse: mutually-exclusive group required
        jira.main(["describe", "ECO-9"])
