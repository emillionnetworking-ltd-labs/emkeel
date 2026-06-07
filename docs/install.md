# Installing Emkeel (manual)

`emkeel init` scaffolds a repo for Emkeel governance: a CI gates workflow, a Jira
auto-transition workflow, the `emkeel-governance/` folder, connection config, and an
`AGENTS.md`. It is **non-clobbering** and **never writes secrets**.

## 1. Prerequisites & install

You need: Python 3.11+ (with `pip`), `git`, a GitHub account, and a Jira account + project.
Then open your repo in your editor and:

```bash
pip install emkeel
```

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

> Prefer AI-assisted? Tell your agent, verbatim: *Install and set up Emkeel in this repo:
> run `pip install emkeel`, then `emkeel onboard`, and follow what it prints. Ask me for my
> GitHub repo, Jira URL, and Jira project key.*
