# Installing Emkeel (manual)

`emkeel init` scaffolds a repo for Emkeel governance: a CI gates workflow, a Jira
auto-transition workflow, the `emkeel-governance/` folder, connection config, and an
`AGENTS.md`. It is **non-clobbering** and **never writes secrets**.

## 1. Prerequisites & install

You need: Python 3.11+, `git`, a GitHub account, and a Jira account + project.

Emkeel is a **zero-dependency** Python CLI. Recommended installer: `pipx`. By platform:

- **Windows:** `py -m pip install --user pipx` → `py -m pipx ensurepath` → `pipx install emkeel`
  (or simply `py -m pip install emkeel` — Windows Python has no PEP 668 restriction).
- **macOS:** `brew install pipx` → `pipx install emkeel`.
- **Linux (Debian/Ubuntu, with sudo):** `sudo apt install pipx` → `pipx install emkeel`
  (`apt` pulls in `python3-venv`, which pipx needs to build the isolated env).
- **Locked-down server (no sudo, no `python3-venv`):**
  `pip install --user --break-system-packages emkeel` — safe, since emkeel has no runtime deps,
  so nothing can conflict in your user site.

> Use **one** method (don't mix pipx with `pip --user`/venv — that shadows installs). `pipx
> install emkeel` detects an existing install and tells you to `pipx upgrade emkeel`.

## 2. Scaffold — pick your scenario

**A) Existing repo** (add governance to a project you already have):

```bash
cd your-repo
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY --dry-run   # preview
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY
```

It won't overwrite existing files (use `--force` only on purpose). On an active repo, keep
the `gates` check **non-required at first** so you don't break your current CI, and adopt
the branch/spec conventions gradually.

**B) New project** (start governed from scratch):

```bash
mkdir my-project && cd my-project && git init
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY
```

## 3. Connect (the command prints these with the exact links)

1. Jira API token — https://id.atlassian.net/manage-profile/security/api-tokens
2. Repo Actions secrets `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_TOKEN` —
   `https://github.com/OWNER/REPO/settings/secrets/actions/new`
3. Branch protection on `main` (require the `gates` check + a PR) —
   `https://github.com/OWNER/REPO/settings/branches`
4. (optional) GitHub for Jira app — https://github.com/marketplace/jira-software-github

## 4. Verify

Open a small PR: the `gates` check runs (ticket link; spec + acceptance criteria for
features; full test suite). Merge → the linked ticket moves to Done.

> Prefer AI-assisted setup? After installing, run `emkeel onboard` and paste its output to
> your AI coding agent — it drives the scaffold + connect steps in your language.

## 5. Updating & uninstalling

- **Check your version:** `emkeel version` (tells you if a newer one is on PyPI).
- **Upgrade the tool:** `pipx upgrade emkeel`.
- **Your repo's CI** pins `emkeel~=0.MINOR.0`, so it auto-takes patches/minors on each run; a
  breaking major (e.g. `0.2.0`) is **opt-in** — bump the pin in `emkeel.toml`/the workflow.
- **Uninstall from a repo:** `emkeel uninstall` (dry-run; add `--yes` to apply). It removes
  the wiring but **keeps** `emkeel-governance/` unless you pass `--purge`.
- **Remove the tool:** `pipx uninstall emkeel`.
