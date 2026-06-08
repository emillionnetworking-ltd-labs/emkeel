"""emkeel setup — interactive, deterministic setup wizard (no AI).

Run `emkeel setup` (or one-shot: `pipx run emkeel setup`). It asks a few questions in your
language, then does the local setup (branch + scaffold + commit) and prints clear next steps.
Plain Python + git — no AI deciding anything, so the wizard can't be "talked out of" its steps.
Already set up? It detects `emkeel.toml` and refuses to re-run (use `emkeel eject` first).
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from emkeel.init import Config, apply, connection_checklist

KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
CANCEL_WORDS = {"c", "q", "cancel", "cancelar", "salir", "quit"}

# --- minimal i18n (es / en) ------------------------------------------------
T: dict[str, dict[str, str]] = {
    "scenario":  {"es": "¿Repo existente o proyecto nuevo?", "en": "Existing repo or new project?"},
    "existing":  {"es": "Repo existente", "en": "Existing repo"},
    "new":       {"es": "Proyecto nuevo", "en": "New project"},
    "detected":  {"es": "Datos (Enter = aceptar, o escribe para cambiar):",
                  "en": "Details (Enter = accept, or type to change):"},
    "ghrepo":    {"es": "Repo de GitHub (owner/repo)", "en": "GitHub repo (owner/repo)"},
    "jiraurl":   {"es": "URL de Jira", "en": "Jira URL"},
    "jiraproj":  {"es": "Proyecto Jira (clave)", "en": "Jira project (key)"},
    "jirakey":   {"es": "Clave Jira para la rama (ej. SCRUM-123)", "en": "Jira key for the branch (e.g. SCRUM-123)"},
    "plan":      {"es": "Voy a hacer (local, no toca tu main):", "en": "I'll do (local, won't touch your main):"},
    "p_branch":  {"es": "crear la rama", "en": "create branch"},
    "p_init":    {"es": "git init (carpeta nueva)", "en": "git init (new folder)"},
    "p_files":   {"es": "crear los archivos de Emkeel + commit", "en": "create Emkeel's files + commit"},
    "continue":  {"es": "¿Continuar? [s/N] ", "en": "Continue? [y/N] "},
    "cancelled": {"es": "Cancelado — no se cambió nada.", "en": "Cancelled — nothing changed."},
    "working":   {"es": "Trabajando…", "en": "Working…"},
    "done":      {"es": "Listo. Tu repo está preparado.", "en": "Done. Your repo is scaffolded."},
    "nextyou":   {"es": "Ahora tú (solo tú puedes):", "en": "Now you (only you can):"},
    "n_push":    {"es": "Subir y abrir un PR:", "en": "Push and open a PR:"},
    "n_create":  {"es": "Crear el repo en GitHub y subir:", "en": "Create the GitHub repo and push:"},
    "secrets":   {"es": "Conexión (token Jira → GitHub Secrets, 🔒 nunca en texto plano):",
                  "en": "Connect (Jira token → GitHub Secrets, 🔒 never in plain text):"},
    "undo":      {"es": "Para deshacer todo:  emkeel eject", "en": "To undo everything:  emkeel eject"},
    "connect_q": {"es": "¿Conectar ahora con GitHub (branch protection + secrets)? [s/N] ",
                  "en": "Connect to GitHub now (branch protection + secrets)? [y/N] "},
    "already":   {"es": "Emkeel ya está configurado en este repo (existe emkeel.toml).\n  "
                        "Para reconfigurar, quítalo primero:  emkeel eject",
                  "en": "Emkeel is already set up here (emkeel.toml exists).\n  "
                        "To reconfigure, remove it first:  emkeel eject"},
    "warn_isrepo_q": {"es": "⚠ Detecté un repo git con historial aquí. ¿Cómo lo configuro?",
                      "en": "⚠ This is already a git repo with history. How should I set it up?"},
    "opt_existing":  {"es": "Repo existente (rama + PR) — recomendado",
                      "en": "Existing repo (branch + PR) — recommended"},
    "opt_new_risky": {"es": "Proyecto nuevo (commiteará a tu rama actual)",
                      "en": "New project (will commit to your current branch)"},
    "warn_norepo_q": {"es": "⚠ No hay un repo git con commits aquí. ¿Estás en la carpeta correcta?",
                      "en": "⚠ There's no git repo with commits here. Are you in the right folder?"},
    "opt_make_new":  {"es": "Crear un proyecto nuevo aquí (git init)",
                      "en": "Create a new project here (git init)"},
}


def t(key: str, lang: str) -> str:
    return T[key].get(lang, T[key]["en"])


@dataclass
class Answers:
    lang: str = "en"
    scenario: str = "existing"   # "existing" | "new"
    github_repo: str = ""
    jira_url: str = ""
    jira_project: str = ""
    jira_key: str = ""           # branch key (existing repo)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)


def derive_defaults(cwd: Path) -> dict[str, str]:
    """Best-effort defaults from the repo. Empty strings when not found / not a repo."""
    d = {"github_repo": "", "jira_url": "", "jira_project": ""}
    r = _run(["git", "remote", "get-url", "origin"], cwd)
    if r.returncode == 0:
        m = re.search(r"github\.com[:/]+([^/]+/[^/.\s]+)", r.stdout.strip())
        if m:
            d["github_repo"] = m.group(1)
    log = _run(["git", "log", "--oneline", "-30"], cwd)
    if log.returncode == 0:
        keys = KEY_RE.findall(log.stdout)
        if keys:
            d["jira_project"] = Counter(k.split("-")[0] for k in keys).most_common(1)[0][0]
    g = _run(["git", "grep", "-hoIE", r"https://[a-zA-Z0-9.-]+\.atlassian\.net"], cwd)
    if g.returncode == 0 and g.stdout.strip():
        d["jira_url"] = sorted(set(g.stdout.split()))[0]
    return d


def is_existing_repo(target: Path) -> bool:
    """True if `target` is already a git repo with at least one commit."""
    return _run(["git", "rev-parse", "--verify", "HEAD"], target).returncode == 0


def branch_name(key: str) -> str:
    return f"chore/{key}-adopt-emkeel"


def plan_lines(a: Answers) -> list[str]:
    lines = [t("plan", a.lang)]
    if a.scenario == "new":
        lines.append(f"  • {t('p_init', a.lang)}")
    else:
        lines.append(f"  • {t('p_branch', a.lang)} {branch_name(a.jira_key)}")
    lines.append(f"  • {t('p_files', a.lang)}")
    return lines


def run_setup(target: Path, a: Answers) -> list[str]:
    """Do the local setup. Returns result lines. Raises RuntimeError on a hard failure."""
    out: list[str] = []
    cfg = Config(jira_url=a.jira_url, jira_project=a.jira_project, github_repo=a.github_repo)
    if a.scenario == "new":
        if not (target / ".git").exists():
            r = _run(["git", "init", "-q"], target)
            if r.returncode != 0:
                raise RuntimeError(f"git init: {r.stderr.strip()}")
            out.append("✓ git init")
    else:
        br = branch_name(a.jira_key)
        r = _run(["git", "checkout", "-b", br], target)
        if r.returncode != 0:
            raise RuntimeError(f"git checkout -b {br}: {r.stderr.strip()}")
        out.append(f"✓ {br}")
    actions = apply(target, cfg, force=False, dry_run=False)
    out.append("✓ files")
    to_stage = [act.path for act in actions if act.kind in ("create", "append")]
    if to_stage:
        _run(["git", "add", *to_stage], target)
        msg = f"chore(emkeel): adopt governance scaffold ({a.jira_key or 'setup'})"
        c = _run(["git", "commit", "-m", msg], target)
        out.append("✓ commit" if c.returncode == 0 else f"⚠ commit: {(c.stderr or c.stdout).strip()}")
    return out


def next_steps(a: Answers) -> str:
    cfg = Config(jira_url=a.jira_url, jira_project=a.jira_project, github_repo=a.github_repo)
    lines = ["", t("nextyou", a.lang)]
    if a.scenario == "existing":
        lines.append(f"  • {t('n_push', a.lang)}  git push -u origin HEAD  →  PR")
    else:  # new project — the repo doesn't exist on GitHub yet; create + push it first
        repo = a.github_repo or "OWNER/REPO"
        lines.append(f"  • {t('n_create', a.lang)}  gh repo create {repo} --private --source=. --push")
    lines.append("")
    lines.append("  " + t("secrets", a.lang))
    lines.append(connection_checklist(cfg))
    lines.append(f"  {t('undo', a.lang)}")
    return "\n".join(lines)


# --- interactive layer ----------------------------------------------------

def _choice(prompt: str, options: list[tuple[str, str]], inp=input) -> str | None:
    """Numbered choice. Enter → first option (default). 'c'/'q' → None (cancel)."""
    while True:
        print(prompt)
        for i, (_, label) in enumerate(options, 1):
            print(f"  [{i}] {label}" + ("  (Enter)" if i == 1 else ""))
        print("  [c] Cancelar / Cancel")
        raw = inp("  > ").strip().lower()
        if raw == "":
            return options[0][0]
        if raw in CANCEL_WORDS:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]


def _field(label: str, default: str, inp=input) -> str:
    shown = f"  {label} [{default}]: " if default else f"  {label}: "
    return inp(shown).strip() or default


def _cancel(lang: str = "en") -> int:
    print("  " + t("cancelled", lang))
    return 0


def main(argv: list[str] | None = None, inp=input) -> int:
    target = Path(".")
    if (target / "emkeel.toml").is_file():       # already set up → don't re-run
        print("\n  " + t("already", "es"))
        print("  " + t("already", "en"))
        return 0

    print("\n  Emkeel · setup\n  " + "─" * 14)
    lang = _choice("  Idioma / Language:", [("es", "Español"), ("en", "English")], inp)
    if lang is None:
        return _cancel("en")
    a = Answers(lang=lang)

    a.scenario = _choice("\n  " + t("scenario", lang),
                         [("existing", t("existing", lang)), ("new", t("new", lang))], inp)
    if a.scenario is None:
        return _cancel(lang)

    # Cross-check the answer against reality (don't silently trust a wrong answer):
    # "new" inside a repo with history would commit straight to your branch — tell the user
    # and let them choose (existing is the safe default).
    real = is_existing_repo(target)
    if a.scenario == "new" and real:
        print("\n  " + t("warn_isrepo_q", lang))
        choice = _choice("", [("existing", t("opt_existing", lang)), ("new", t("opt_new_risky", lang))], inp)
        if choice is None:
            return _cancel(lang)
        a.scenario = choice
    elif a.scenario == "existing" and not real:
        # No repo here — maybe the wrong folder. Inform + let them create-new or cancel.
        print("\n  " + t("warn_norepo_q", lang))
        choice = _choice("", [("new", t("opt_make_new", lang))], inp)
        if choice is None:
            return _cancel(lang)
        a.scenario = "new"

    d = derive_defaults(target)
    print("\n  " + t("detected", lang))
    a.github_repo = _field(t("ghrepo", lang), d["github_repo"], inp)
    a.jira_url = _field(t("jiraurl", lang), d["jira_url"], inp)
    a.jira_project = _field(t("jiraproj", lang), d["jira_project"], inp)
    if a.scenario == "existing":
        a.jira_key = _field(t("jirakey", lang), f"{a.jira_project}-1" if a.jira_project else "", inp)

    print()
    for line in plan_lines(a):
        print("  " + line)
    if inp("\n  " + t("continue", lang)).strip().lower() not in ("s", "y", "si", "yes"):
        return _cancel(lang)

    print("\n  " + t("working", lang))
    try:
        for line in run_setup(target, a):
            print("  " + line)
    except RuntimeError as e:
        print(f"  ✗ {e}")
        return 1
    print("\n  " + t("done", lang))
    print(next_steps(a))
    _maybe_connect(lang, inp)
    return 0


def _maybe_connect(lang: str, inp) -> None:
    """Guide the GitHub connection (branch protection + secrets) right here, if gh is available."""
    from emkeel import connect
    if not connect.gh_ok():
        return
    if inp("\n  " + t("connect_q", lang)).strip().lower() in ("s", "y", "si", "yes"):
        connect.main([], inp=inp)


if __name__ == "__main__":
    import sys
    sys.exit(main())
