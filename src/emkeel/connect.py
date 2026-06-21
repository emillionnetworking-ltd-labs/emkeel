"""emkeel connect — automate the GitHub side via `gh`.

Leaves only one manual step: creating the Jira API token (on Atlassian). You paste it into a
hidden prompt here — it never goes through an AI chat. Everything is confirmed before it runs.

- **New project** (not on GitHub yet): create + push the repo, then branch protection + secrets.
- **Existing repo**: branch protection + secrets. (Pushing the adopt branch stays manual — a
  pre-push hook could hang; that belongs to the AI-interpreter, not a deterministic command.)

`--dry-run` prints the gh commands without running anything. If gh isn't available/authed, it
points you to the web links (same as `emkeel doctor`). Bilingual (es/en) via `--lang` or a prompt.
"""

from __future__ import annotations

import argparse
import getpass as _getpass
import json
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from emkeel.i18n import ask_language, is_yes, t
from emkeel.ui import spin

TOKEN_LINK = "https://id.atlassian.net/manage-profile/security/api-tokens"
# Fine-grained PAT scoped to ONE repo (Settings → Developer settings → Fine-grained tokens).
PAT_LINK = "https://github.com/settings/personal-access-tokens/new"


def write_env(target: Path, values: dict[str, str]) -> Path:
    """Upsert KEY=value lines into `target/.env`, PRESERVING any other vars the user has, then chmod 600.

    This is the per-repo scoped-credential file (gitignored). Idempotent: re-writing the same values is a
    content no-op. Never clobbers unrelated lines — only the keys in `values` are replaced/appended."""
    path = target / ".env"
    existing = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    out, seen = [], set()
    for ln in existing:
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", ln)
        if m and m.group(1) in values:
            out.append(f"{m.group(1)}={values[m.group(1)]}")
            seen.add(m.group(1))
        else:
            out.append(ln)
    for k, v in values.items():
        if k not in seen:
            out.append(f"{k}={v}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)                                  # local secrets are owner-only
    return path

T: dict[str, dict[str, str]] = {
    "no_toml":   {"es": "  No hay emkeel.toml aquí — corre `emkeel setup` primero.",
                  "en": "  No emkeel.toml here — run `emkeel setup` first."},
    "header":    {"es": "emkeel connect → conectar GitHub", "en": "emkeel connect → wire up GitHub"},
    "dry_intro": {"es": "  Ejecutaría (gh):", "en": "  Would run (gh):"},
    "dry_create":{"es": "    • gh repo create {repo} --private --source=. --push   (solo si aún no está en GitHub)",
                  "en": "    • gh repo create {repo} --private --source=. --push   (only if not on GitHub yet)"},
    "dry_prot":  {"es": "    • gh api -X PUT repos/{repo}/branches/{branch}/protection   (exigir 'gates' + PR)",
                  "en": "    • gh api -X PUT repos/{repo}/branches/{branch}/protection   (require 'gates' + PR)"},
    "dry_sec":   {"es": "    • gh secret set JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN --repo {repo}",
                  "en": "    • gh secret set JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN --repo {repo}"},
    "dry_ship":  {"es": "    • (rama de adopción) git push -u origin HEAD ; gh pr create --fill ; gh pr merge --auto --squash",
                  "en": "    • (adopt branch) git push -u origin HEAD ; gh pr create --fill ; gh pr merge --auto --squash"},
    "dry_manual":{"es": "  Manual (solo tú): crea el token de Jira → {link}",
                  "en": "  Manual (only you): create the Jira token → {link}"},
    "no_gh":     {"es": "  gh no está autenticado. Corre `gh auth login` y reintenta — o usa los enlaces web de `emkeel doctor`.",
                  "en": "  gh isn't authenticated. Run `gh auth login` and retry — or use the web links from `emkeel doctor`."},
    "q_create":  {"es": "  El repo aún no está en GitHub. ¿Crearlo (privado) y subir? [S/n] ",
                  "en": "  Repo isn't on GitHub yet. Create it (private) and push? [Y/n] "},
    "ok_create": {"es": "  ✓ repo creado + subido", "en": "  ✓ repo created + pushed"},
    "fail_create":{"es": "     Créalo a mano:  gh repo create {repo} --private --source=. --push\n     Luego:  emkeel connect",
                   "en": "     Create it manually:  gh repo create {repo} --private --source=. --push\n     Then re-run:  emkeel connect"},
    "q_protect": {"es": "  ¿Exigir el check 'gates' + PRs en '{branch}'? [S/n] ",
                  "en": "  Require the 'gates' check + PRs on '{branch}'? [Y/n] "},
    "ok_protect":{"es": "  ✓ branch protection activada", "en": "  ✓ branch protection on"},
    "fail_protect":{"es": "  ✗ {msg}\n     (¿necesitas permisos de admin? hazlo por la web)",
                    "en": "  ✗ {msg}\n     (need admin rights? do it via the web link)"},
    "q_secrets": {"es": "  ¿Configurar los secrets de Jira ahora? (pegarás el token, oculto) [S/n] ",
                  "en": "  Set the Jira secrets now? (you'll paste the token, hidden) [Y/n] "},
    "tok_first": {"es": "  Crea el token primero si no lo tienes: {link}",
                  "en": "  Create the token first if you haven't: {link}"},
    "email_q":   {"es": "  Email de Atlassian: ", "en": "  Atlassian email: "},
    "token_q":   {"es": "  Token de Jira (oculto): ", "en": "  Jira API token (hidden): "},
    "jira_ok":   {"es": "  ✓ Credenciales de Jira verificadas ({detail})",
                  "en": "  ✓ Jira credentials verified ({detail})"},
    "jira_bad":  {"es": "  ✗ Login de Jira falló ({detail}) — no se guarda. Revisa el email/token.",
                  "en": "  ✗ Jira login failed ({detail}) — not saving. Check the email/token."},
    "q_retry":   {"es": "  ¿Reintentar? [S/n] ", "en": "  Try again? [Y/n] "},
    "sec_skip":  {"es": "  Secrets omitidos — config luego con `emkeel connect` (o en Settings del repo).",
                  "en": "  Skipped secrets — set them later with `emkeel connect` (or in repo Settings)."},
    "dry_local": {"es": "    • escribir .env (chmod 600) con GH_TOKEN (PAT fine-grained de ESTE repo) + creds Jira; activar carga por-repo (direnv allow / source .envrc)",
                  "en": "    • write .env (chmod 600) with GH_TOKEN (fine-grained PAT scoped to THIS repo) + Jira creds; activate per-repo loading (direnv allow / source .envrc)"},
    "q_local":   {"es": "  ¿Aislar la credencial LOCAL? (PAT fine-grained de este repo → .env oculto+600) [S/n] ",
                  "en": "  Isolate the LOCAL credential? (fine-grained PAT for this repo → hidden .env, 600) [Y/n] "},
    "pat_guide": {"es": ("  Crea un GitHub fine-grained PAT acotado a ESTE repo:\n"
                         "    {link}\n"
                         "    • Repository access → Only select repositories → {repo}\n"
                         "    • Permissions (mínimos): Contents = Read and write · Pull requests = Read and write · Metadata = Read"),
                  "en": ("  Create a GitHub fine-grained PAT scoped to THIS repo:\n"
                         "    {link}\n"
                         "    • Repository access → Only select repositories → {repo}\n"
                         "    • Permissions (minimum): Contents = Read and write · Pull requests = Read and write · Metadata = Read")},
    "pat_q":     {"es": "  Pega el PAT (oculto, no pasa por el chat): ", "en": "  Paste the PAT (hidden, never via chat): "},
    "env_written":{"es": "  ✓ .env escrito (chmod 600, gitignored) — {keys}", "en": "  ✓ wrote .env (chmod 600, gitignored) — {keys}"},
    "env_activate":{"es": "  Actívalo en ESTA ventana (carga solo este .env):  direnv allow   (o:  source .envrc)",
                    "en": "  Activate it in THIS window (loads only this .env):  direnv allow   (or:  source .envrc)"},
    "env_empty": {"es": "  Nada que escribir (sin PAT ni creds Jira) — re-corre `emkeel connect`.",
                  "en": "  Nothing to write (no PAT or Jira creds) — re-run `emkeel connect`."},
    "w_env":     {"es": "Escribiendo .env (600)", "en": "Writing .env (600)"},
    "q_finish":  {"es": "  Terminar la adopción — subir '{cur}', abrir PR y auto-merge al pasar los gates? [s/N] ",
                  "en": "  Finish the adopt — push '{cur}', open a PR and auto-merge when gates pass? [y/N] "},
    "pushing":   {"es": "  Subiendo… (verás la salida de git; un pre-push hook puede tardar — Ctrl-C para saltar)",
                  "en": "  Pushing… (you'll see git's output; a pre-push hook may take a moment — Ctrl-C to skip)"},
    "push_fail": {"es": "  ✗ push: {msg}\n     Hazlo a mano:  git push -u origin HEAD  &&  gh pr create --fill  &&  gh pr merge --auto --squash",
                  "en": "  ✗ push: {msg}\n     Do it manually:  git push -u origin HEAD  &&  gh pr create --fill  &&  gh pr merge --auto --squash"},
    "pushed":    {"es": "  ✓ subido", "en": "  ✓ pushed"},
    "pr_ok":     {"es": "  ✓ PR abierto — {out}", "en": "  ✓ PR opened — {out}"},
    "pr_fail":   {"es": "  ✗ gh pr create: {out}", "en": "  ✗ gh pr create: {out}"},
    "am_ok":     {"es": "  ✓ auto-merge activo — se fusiona al pasar los gates",
                  "en": "  ✓ auto-merge on — merges when the gates pass"},
    "am_fail":   {"es": "  ⚠ auto-merge: {msg}\n     El PR está abierto — mergéalo al ponerse verde, o activa 'Allow auto-merge' en Settings y reintenta.",
                  "en": "  ⚠ auto-merge: {msg}\n     The PR is open — merge it once the gates are green, or enable 'Allow auto-merge' in repo Settings and re-run."},
    "q_sync":    {"es": "  ¿Espero a que se fusione y sincronizo tu local (checkout main + pull + borrar esta rama)? [s/N] ",
                  "en": "  Wait for it to merge and sync your local (checkout default + pull + remove this branch)? [y/N] "},
    "waiting":   {"es": "  Esperando el merge (Ctrl-C para saltar)…", "en": "  Waiting for the merge (Ctrl-C to skip)…"},
    "not_merged":{"es": "  ⏱ aún sin fusionar — corre `emkeel sync` luego para terminar.",
                  "en": "  ⏱ not merged yet — run `emkeel sync` later to finish."},
    "sync_skip": {"es": "\n  Saltado — corre `emkeel sync` cuando se fusione.",
                  "en": "\n  Skipped — run `emkeel sync` once it merges."},
    "sync_later":{"es": "  Cuando se fusione, corre:  emkeel sync", "en": "  When it merges, run:  emkeel sync"},
    "done":      {"es": "\n  Listo. Comprueba con: emkeel doctor", "en": "\n  Done. Check with: emkeel doctor"},
    "w_create":  {"es": "Creando + subiendo el repo", "en": "Creating + pushing the repo"},
    "w_protect": {"es": "Configurando branch protection", "en": "Setting branch protection"},
    "w_verify":  {"es": "Verificando credenciales de Jira", "en": "Verifying Jira credentials"},
    "w_secrets": {"es": "Guardando secrets", "en": "Saving secrets"},
    "w_am":      {"es": "Activando auto-merge", "en": "Enabling auto-merge"},
}


def _run(args: list[str], stdin: str | None = None, timeout: float | None = None,
         capture: bool = True) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(args, capture_output=True, text=True, input=stdin, timeout=timeout)
    return subprocess.run(args, text=True, timeout=timeout)   # inherit the terminal (prompts/hooks visible)


@dataclass
class Cfg:
    repo: str
    base_url: str


def load_config(target: Path) -> Cfg | None:
    p = target / "emkeel.toml"
    if not p.is_file():
        return None
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    return Cfg(repo=data.get("github", {}).get("repo", ""),
               base_url=data.get("jira", {}).get("base_url", ""))


def protection_body(checks=("gates",)) -> dict:
    """Classic branch-protection body: require the checks + a PR; solo-friendly (0 approvals)."""
    return {
        "required_status_checks": {"strict": False, "contexts": list(checks)},
        "enforce_admins": False,
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "restrictions": None,
    }


def gh_ok(run=_run) -> bool:
    return run(["gh", "auth", "status"]).returncode == 0


def repo_exists(repo: str, run=_run) -> bool:
    return run(["gh", "repo", "view", repo]).returncode == 0


def do_create_push(repo: str, run=_run):
    r = run(["gh", "repo", "create", repo, "--private", "--source=.", "--push"])
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def do_protect(repo: str, branch: str, run=_run):
    r = run(["gh", "api", "-X", "PUT", f"repos/{repo}/branches/{branch}/protection", "--input", "-"],
            stdin=json.dumps(protection_body()))
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def do_secret(repo: str, name: str, value: str, run=_run):
    r = run(["gh", "secret", "set", name, "--repo", repo, "--body", value])
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def _jira_fetch(base_url: str, email: str, token: str) -> tuple[bool, str]:
    import base64 as _b64
    import json as _json
    import urllib.error
    import urllib.request
    auth = _b64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(base_url.rstrip("/") + "/rest/api/3/myself")
    req.add_header("Authorization", "Basic " + auth)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = _json.loads(r.read().decode())
            return True, (d.get("displayName") or d.get("emailAddress") or "ok")
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # network/DNS/timeout
        return False, str(e)[:60]


def verify_jira(base_url: str, email: str, token: str, fetch=None) -> tuple[bool, str]:
    """Confirm the email+token actually authenticate to Jira (GET /myself), so we never store
    silently-wrong credentials. Returns (ok, detail). `_jira_fetch` is resolved at call time."""
    return (fetch or _jira_fetch)(base_url, email, token)


def current_branch(run=_run) -> str:
    r = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return r.stdout.strip() if r.returncode == 0 else ""


def do_push(run=_run):
    """Push HEAD inheriting the terminal, so a pre-push hook / SSH passphrase / credential prompt
    is visible and answerable (capturing it would hang silently). Ctrl-C cancels cleanly."""
    try:
        r = run(["git", "push", "-u", "origin", "HEAD"], capture=False)
    except subprocess.TimeoutExpired:
        return False, "timed out (a pre-push hook may be hanging)"
    except KeyboardInterrupt:
        return False, "cancelled (Ctrl-C)"
    return r.returncode == 0, (getattr(r, "stderr", "") or "").strip()


def do_pr_create(run=_run):
    r = run(["gh", "pr", "create", "--fill"])
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def allow_auto_merge(repo: str, run=_run) -> bool:
    """Turn on the repo's 'Allow auto-merge' setting (required before `gh pr merge --auto`)."""
    return run(["gh", "api", "-X", "PATCH", f"repos/{repo}", "-F", "allow_auto_merge=true"]).returncode == 0


def do_auto_merge(run=_run):
    """Enable GitHub's native auto-merge: merges WHEN required checks pass (gates) + approvals met."""
    r = run(["gh", "pr", "merge", "--auto", "--squash"])
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def main(argv=None, inp=input, getpass=_getpass.getpass, run=_run, lang=None) -> int:
    ap = argparse.ArgumentParser(prog="emkeel connect", description="Automate the GitHub side via gh.")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lang", choices=["es", "en"], default=None)
    ns = ap.parse_args(argv if argv is not None else None)
    lang = lang or ns.lang

    cfg = load_config(Path("."))
    if cfg is None or not cfg.repo:
        print(t(T, "no_toml", lang or "en"))
        return 1
    repo, branch = cfg.repo, ns.branch

    if ns.dry_run:
        lang = lang or "en"
        print(f"\n  {t(T, 'header', lang)} → {repo}\n  " + "─" * 26)
        print(t(T, "dry_intro", lang))
        print(t(T, "dry_create", lang).format(repo=repo))
        print(t(T, "dry_prot", lang).format(repo=repo, branch=branch))
        print(t(T, "dry_sec", lang).format(repo=repo))
        print(t(T, "dry_local", lang))
        print(t(T, "dry_ship", lang))
        print(t(T, "dry_manual", lang).format(link=TOKEN_LINK))
        return 0

    if lang is None:                     # standalone → ask; from setup → inherited
        lang = ask_language(inp)
        if lang is None:
            return 0
    print(f"\n  {t(T, 'header', lang)} → {repo}\n  " + "─" * 26)

    if not gh_ok(run):
        print(t(T, "no_gh", lang))
        return 1

    # 1) New project? establish the GitHub connection first (safe: a fresh repo has no hooks).
    if not repo_exists(repo, run):
        if is_yes(inp(t(T, "q_create", lang))):
            with spin(t(T, "w_create", lang)):
                ok, msg = do_create_push(repo, run)
            print(t(T, "ok_create", lang) if ok else f"  ✗ {msg}")
            if not ok:
                print(t(T, "fail_create", lang).format(repo=repo))
                return 1

    # 2) Branch protection — require the gates check + PRs
    if is_yes(inp(t(T, "q_protect", lang).format(branch=branch))):
        with spin(t(T, "w_protect", lang)):
            ok, msg = do_protect(repo, branch, run)
        print(t(T, "ok_protect", lang) if ok else t(T, "fail_protect", lang).format(msg=msg))

    # 3) Secrets — token via hidden prompt; verified before saving; never in chat/logs
    email = token = ""          # also reused below for the per-repo .env (scoped local credential)
    if is_yes(inp(t(T, "q_secrets", lang))):
        print(t(T, "tok_first", lang).format(link=TOKEN_LINK))
        while True:
            email = inp(t(T, "email_q", lang)).strip()
            token = getpass(t(T, "token_q", lang)).strip()
            with spin(t(T, "w_verify", lang)):
                ok, detail = verify_jira(cfg.base_url, email, token)
            if ok:
                print(t(T, "jira_ok", lang).format(detail=detail))
                break
            print(t(T, "jira_bad", lang).format(detail=detail))
            if not is_yes(inp(t(T, "q_retry", lang))):
                print(t(T, "sec_skip", lang))
                email = token = ""
                break
        if email and token:
            with spin(t(T, "w_secrets", lang)):
                results = [(name, *do_secret(repo, name, val, run))
                           for name, val in (("JIRA_BASE_URL", cfg.base_url), ("JIRA_EMAIL", email), ("JIRA_TOKEN", token))]
            for name, ok, msg in results:
                print(f"  {'✓' if ok else '✗'} {name}" + ("" if ok else f": {msg}"))

    # 3b) Scoped LOCAL credential — a fine-grained GitHub PAT for THIS repo, written to .env (600).
    # This is the per-window isolation: the agent's gh/git in this repo uses a token that can't touch
    # another repo. The PAT is pasted HIDDEN (never via chat); .env is gitignored + chmod 600.
    if is_yes(inp(t(T, "q_local", lang))):
        print(t(T, "pat_guide", lang).format(repo=repo, link=PAT_LINK))
        pat = getpass(t(T, "pat_q", lang)).strip()
        env_vals: dict[str, str] = {}
        if pat:
            env_vals["GH_TOKEN"] = pat
        if email and token:     # reuse the Jira creds collected above for the per-repo .env
            env_vals.update({"JIRA_BASE_URL": cfg.base_url, "JIRA_EMAIL": email, "JIRA_TOKEN": token})
        if env_vals:
            with spin(t(T, "w_env", lang)):
                write_env(Path("."), env_vals)
            print(t(T, "env_written", lang).format(keys=", ".join(env_vals)))
            print(t(T, "env_activate", lang))
        else:
            print(t(T, "env_empty", lang))

    # 4) Finish the adopt — push, PR, auto-merge (the adoption PR only; normal changes stay human-merged).
    cur = current_branch(run)
    if cur and cur != branch:
        if is_yes(inp(t(T, "q_finish", lang).format(cur=cur))):
            print(t(T, "pushing", lang))
            ok, msg = do_push(run)
            if not ok:
                print(t(T, "push_fail", lang).format(msg=msg))
            else:
                print(t(T, "pushed", lang))
                okp, out = do_pr_create(run)
                print(t(T, "pr_ok", lang).format(out=out) if okp else t(T, "pr_fail", lang).format(out=out))
                if okp:
                    with spin(t(T, "w_am", lang)):
                        allow_auto_merge(repo, run)
                        okm, outm = do_auto_merge(run)
                    print(t(T, "am_ok", lang) if okm else t(T, "am_fail", lang).format(msg=outm))
                    if okm and is_yes(inp(t(T, "q_sync", lang))):
                        from emkeel.sync import sync, wait_for_merge
                        print(t(T, "waiting", lang))
                        try:
                            if wait_for_merge(cur, run):
                                for line in sync(run, lang=lang):
                                    print("  " + line)
                            else:
                                print(t(T, "not_merged", lang))
                        except KeyboardInterrupt:
                            print(t(T, "sync_skip", lang))
                    elif okm:
                        print(t(T, "sync_later", lang))

    print(t(T, "done", lang))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
