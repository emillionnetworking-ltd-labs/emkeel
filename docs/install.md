# Installing Emkeel in a repo

`emkeel init` scaffolds a target repo to be governed by Emkeel. It is **non-clobbering**
(existing files are skipped unless `--force`) and **never writes secrets**.

## Run

```bash
# Dry-run first (writes nothing, shows the plan):
python -m emkeel.init /path/to/repo \
  --jira-url https://your.atlassian.net \
  --jira-project KEY \
  --github-repo owner/repo \
  --dry-run

# Then for real:
python -m emkeel.init /path/to/repo --jira-url ... --jira-project KEY --github-repo owner/repo
```

### Install source (private emkeel)

The generated CI runs `pip install <source>`. **Default:** the PyPI package, version-pinned
(`emkeel~=0.1.0`) — `pip install emkeel`, no account, no token.

For a **private fork**, pass a git+token form and add the token as a repo secret:

```bash
python -m emkeel.init /path/to/repo ... \
  --emkeel-source 'git+https://x-access-token:${EMKEEL_INSTALL_TOKEN}@github.com/OWNER/emkeel.git'
```

Then add `EMKEEL_INSTALL_TOKEN` (a fine-grained PAT with READ access to the emkeel repo)
as a GitHub Actions secret in the target repo.

## What it creates

- `emkeel-governance/{specs,adr,records}/` — the single artifact folder (`export-ignore`).
- `.github/workflows/emkeel-ci.yml` — runs the gates on PRs.
- `emkeel.toml` — non-secret config (Jira URL + project key, GitHub repo).
- `.env.example` — secrets template (real `.env` is gitignored, never committed).
- `AGENTS.md` — the agent contract (skipped if one already exists).

## Connect (one-time, printed by the command)

1. **GitHub for Jira** app → install & link the repo (commits/PRs link to tickets).
2. **Branch protection** on `main` → require the `gates` check + a PR.
3. **Secrets** → add `JIRA_TOKEN` (+ `JIRA_EMAIL`) as GitHub Actions secrets.
4. **Local** → `cp .env.example .env` and fill it.
5. **Install source** → until Emkeel is on PyPI, point the CI `Install emkeel` line at your source.
