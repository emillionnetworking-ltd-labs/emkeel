"""Tests for per-repo agent isolation. Pure decide() — no fs/network. Fail-safe precision is the point."""

import json

from emkeel.isolation import decide, find_identity, main

# Identity of "this" repo: /home/me/projects/emkeel, governed by KEEL + owner/emkeel.
IDENT = {"repo": "owner/emkeel", "project_key": "KEEL", "root": "/home/me/projects/emkeel",
         "jira_host": "me.atlassian.net"}
CWD = "/home/me/projects/emkeel"


def _bash(cmd, cwd=CWD, ident=IDENT):
    return decide("Bash", {"command": cmd}, cwd, ident)


def _edit(path, tool="Edit", cwd=CWD, ident=IDENT):
    return decide(tool, {"file_path": path}, cwd, ident)


# ── allow the normal, in-repo work (fail-safe: must NOT brick) ─────────────────

def test_allows_ordinary_commands():
    for cmd in ("pytest -q", "git status", "git push", "git push origin main",
                "gh pr create --fill", "gh pr list", "gh run watch 123",
                "emkeel jira create --project KEEL --summary x", "ls ../", "cd /tmp/scratch && ls",
                "cd ~ && pwd", "cat /etc/hostname", "grep -r foo src/"):
        assert _bash(cmd)[0] == "allow", cmd


def test_allows_in_repo_edits_and_reads():
    assert _edit("src/emkeel/foo.py")[0] == "allow"
    assert _edit("/home/me/projects/emkeel/src/x.py")[0] == "allow"
    assert _edit("README.md", tool="Read")[0] == "allow"
    assert _edit("/tmp/scratch.txt")[0] == "allow"          # scratch outside parent → allowed


def test_no_identity_allows_everything():
    assert decide("Bash", {"command": "gh -R other/repo pr list"}, CWD, None) == ("allow", "")
    assert decide("Edit", {"file_path": "/anywhere/x"}, CWD, None) == ("allow", "")


# ── deny the unambiguous crossings ─────────────────────────────────────────────

def test_denies_gh_other_repo():
    d, why = _bash("gh -R owner/em-ecosystem pr create --fill")
    assert d == "deny" and "em-ecosystem" in why
    assert _bash("gh pr list --repo owner/em-ecosystem")[0] == "deny"
    assert _bash("gh -R owner/emkeel pr list")[0] == "allow"   # its OWN repo → fine


def test_denies_crossed_jira_project():
    assert _bash("emkeel jira create --project ECO --summary x")[0] == "deny"
    assert _bash("emkeel jira create --project KEEL --summary x")[0] == "allow"   # own project


def test_denies_git_push_to_foreign_url():
    d, why = _bash("git push https://github.com/owner/em-ecosystem.git main")
    assert d == "deny" and "em-ecosystem" in why
    assert _bash("git push git@github.com:owner/emkeel.git main")[0] == "allow"   # own url


def test_denies_cd_into_sibling_repo():
    assert _bash("cd ../em-ecosystem && gh pr create")[0] == "deny"
    assert _bash("cd /home/me/projects/em-ecosystem")[0] == "deny"
    assert _bash("cd src && pytest")[0] == "allow"            # in-repo subdir → fine


def test_denies_edit_into_sibling_repo():
    d, why = _edit("../em-ecosystem/src/app.ts")
    assert d == "deny" and "different repo" in why
    assert _edit("/home/me/projects/em-ecosystem/x.py")[0] == "deny"
    assert _edit("/home/me/projects/em-ecosystem/x.py", tool="Read")[0] == "deny"   # cross read too


# ── raw API bypass (KEEL-92): curl/python straight to Jira/GitHub must be screened too ──

def test_denies_raw_jira_api_foreign_project():
    # the exact bypass: a raw curl to the Jira REST API creating an issue in ANOTHER project.
    cmds = [
        """curl -s me.atlassian.net/rest/api/3/issue -d '{"fields":{"project":{"key":"ECO"}}}'""",
        """python -c "import requests; requests.post('https://me.atlassian.net/rest/api/3/issue', json={'fields':{'project':{'key':'ECO'}}})" """,
        """curl 'https://me.atlassian.net/rest/api/2/search?jql=project=ECO'""",
        """curl -X POST https://me.atlassian.net/rest/api/3/issue/ECO-7/transitions -d '{...}'""",  # transition a foreign issue
    ]
    for c in cmds:
        d, why = _bash(c)
        assert d == "deny" and "ECO" in why, c


def test_allows_raw_jira_api_own_project():
    for c in (
        """curl -s me.atlassian.net/rest/api/3/issue -d '{"fields":{"project":{"key":"KEEL"}}}'""",
        """curl 'https://me.atlassian.net/rest/api/2/search?jql=project=KEEL ORDER BY created'""",
        """curl -X POST https://me.atlassian.net/rest/api/3/issue/KEEL-9/transitions -d '{}'""",
    ):
        assert _bash(c)[0] == "allow", c


def test_denies_raw_github_api_other_repo():
    d, why = _bash("curl -s https://api.github.com/repos/owner/em-ecosystem/pulls -d '{}'")
    assert d == "deny" and "em-ecosystem" in why
    assert _bash("curl https://api.github.com/repos/owner/em-ecosystem/issues")[0] == "deny"


def test_allows_raw_github_api_own_repo():
    assert _bash("curl -s https://api.github.com/repos/owner/emkeel/pulls")[0] == "allow"


def test_raw_api_fail_safe_no_false_positives():
    # no API indicator, or a project word with no foreign key → ALLOW (never brick).
    for c in ("curl https://example.com/data.json",
              "echo project=KEEL",
              "python script.py --project KEEL",                # own project mentioned
              "curl https://api.github.com/repos/owner/emkeel/commits",
              "grep -r project= ."):
        assert _bash(c)[0] == "allow", c


# ── auto-protection: can't edit away the guard ─────────────────────────────────

def test_denies_editing_guard_config():
    for p in (".claude/settings.json", ".claude/settings.local.json", ".claude/hooks/guard.sh",
              "emkeel.toml", "/home/me/projects/emkeel/emkeel.toml"):
        assert _edit(p)[0] == "deny", p
    # reading them is fine (only mutation is protected)
    assert _edit(".claude/settings.json", tool="Read")[0] == "allow"


# ── the entrypoint emits the harness deny JSON, always exit 0 ──────────────────

def test_main_emits_deny_json(monkeypatch, capsys, tmp_path):
    # a governed repo with a crossing command → deny JSON on stdout, exit 0.
    (tmp_path / "emkeel.toml").write_text('[github]\nrepo="owner/emkeel"\n[jira]\nproject_key="KEEL"\n')
    payload = {"tool_name": "Bash", "tool_input": {"command": "gh -R owner/other pr list"},
               "cwd": str(tmp_path)}
    monkeypatch.setattr("sys.stdin.read", lambda: json.dumps(payload))
    assert main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_main_allows_silently(monkeypatch, capsys, tmp_path):
    (tmp_path / "emkeel.toml").write_text('[github]\nrepo="owner/emkeel"\n[jira]\nproject_key="KEEL"\n')
    payload = {"tool_name": "Bash", "tool_input": {"command": "pytest -q"}, "cwd": str(tmp_path)}
    monkeypatch.setattr("sys.stdin.read", lambda: json.dumps(payload))
    assert main() == 0
    assert capsys.readouterr().out.strip() == ""             # allow → no output


def test_main_fail_safe_on_garbage(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.read", lambda: "{ not json")
    assert main() == 0                                        # never bricks
    assert capsys.readouterr().out.strip() == ""


def test_find_identity_reads_toml(tmp_path):
    (tmp_path / "emkeel.toml").write_text(
        '[jira]\nbase_url="https://acme.atlassian.net"\nproject_key="ECO"\n[github]\nrepo="o/r"\n')
    sub = tmp_path / "a" / "b"; sub.mkdir(parents=True)
    ident = find_identity(sub)                                 # walks up to the toml
    assert ident == {"repo": "o/r", "project_key": "ECO", "jira_host": "acme.atlassian.net",
                     "root": str(tmp_path)}


def test_find_identity_none_when_absent(tmp_path):
    assert find_identity(tmp_path) is None
