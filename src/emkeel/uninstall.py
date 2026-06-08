"""emkeel eject — reverse `emkeel init` in a repo (command: `emkeel eject`; alias: `emkeel uninstall`).

Interactive by default (asks language first, then per category, then confirms). Removes the wiring
Emkeel added (workflows, emkeel.toml, .env.example, AGENTS.md, CLAUDE.md). For
.gitattributes/.gitignore it removes the file **only if Emkeel created it** — it NEVER strips a
line you already had. **Keeps emkeel-governance/** unless you remove it. `--yes` for scripts.

With `--remote` it also finishes on GitHub: drops branch protection (so removing the gates
workflow doesn't deadlock), commits + pushes the removal, and drops the Jira secrets.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from emkeel.i18n import ask_language, is_yes, t
from emkeel.init import APPEND_LINES
from emkeel.ui import spin

WIRING_FILES = [
    ".github/workflows/emkeel-ci.yml",
    ".github/workflows/jira-transition.yml",
    "emkeel.toml",
    ".env.example",
    "AGENTS.md",
    "CLAUDE.md",
]
GOVERNANCE_DIR = "emkeel-governance"

T: dict[str, dict[str, str]] = {
    "header":   {"es": "emkeel eject — quitar Emkeel de este repo", "en": "emkeel eject — remove Emkeel from this repo"},
    "q_wiring": {"es": "  ¿Quitar el cableado de Emkeel (workflows, emkeel.toml, AGENTS/CLAUDE)? [S/n] ",
                 "en": "  Remove Emkeel's wiring (workflows, emkeel.toml, AGENTS/CLAUDE)? [Y/n] "},
    "q_gov":    {"es": "  ¿Quitar también emkeel-governance/ (tus ADR/specs/records)? [s/N] ",
                 "en": "  Also remove emkeel-governance/ (your ADRs/specs/records)? [y/N] "},
    "q_remote": {"es": "  ¿Quitar también el lado GitHub (protección + secrets + push del borrado)? [s/N] ",
                 "en": "  Also remove the GitHub side (branch protection + secrets + push the removal)? [y/N] "},
    "about":    {"es": "\n  ⚠ Voy a quitar: {summary}", "en": "\n  ⚠ About to remove: {summary}"},
    "q_proceed":{"es": "  ¿Proceder? [s/N] ", "en": "  Proceed? [y/N] "},
    "cancelled":{"es": "  Cancelado — no se cambió nada.", "en": "  Cancelled — nothing changed."},
    "removed":  {"es": "quitado", "en": "removed"},
    "clean":    {"es": "  (no hay archivos locales de Emkeel que quitar — ya está limpio)",
                 "en": "  (no local Emkeel files to remove — already clean)"},
    "kept":     {"es": "\nConservado {dir}/ (tu historial).", "en": "\nKept {dir}/ (your history)."},
    "finishing":{"es": "\nTerminando en GitHub ({repo}):", "en": "\nFinishing on GitHub ({repo}):"},
    "skip_gh":  {"es": "\n--remote omitido: gh no está autenticado (corre `gh auth login`).",
                 "en": "\n--remote skipped: gh isn't authenticated (run `gh auth login`)."},
    "skip_norepo":{"es": "\n--remote omitido: no se encontró remoto de GitHub.",
                   "en": "\n--remote skipped: no GitHub remote found."},
    "teardown": {"es": "\nEsto solo desgobernó el repo. Para quitar la herramienta de tu máquina:\n  pipx uninstall emkeel",
                 "en": "\nThis only un-governed the repo. To remove the emkeel tool from your machine:\n  pipx uninstall emkeel"},
    "dry_note": {"es": "\n(no se cambió nada — corre `emkeel eject` para elegir interactivo, o añade --yes)",
                 "en": "\n(nothing changed — run `emkeel eject` to choose interactively, or add --yes)"},
    "non_tty":  {"es": "emkeel eject: shell no interactivo — reejecuta con --yes (+ --purge/--remote/--all) o en una terminal.",
                 "en": "emkeel eject: non-interactive shell — re-run with --yes (+ --purge/--remote/--all) or in a terminal."},
    "s_wiring": {"es": "cableado", "en": "wiring"},
    "s_remote": {"es": "lado GitHub", "en": "GitHub side"},
    # remote_cleanup steps
    "r_pushing":{"es": "  Subiendo el borrado… (salida de git abajo; Ctrl-C para saltar)",
                 "en": "  Pushing the removal… (git output below; Ctrl-C to skip)"},
    "r_protect":{"es": "protección de rama quitada", "en": "branch protection cleared"},
    "r_commit": {"es": "commit del borrado", "en": "commit removal"},
    "r_push":   {"es": "push hecho", "en": "pushed"},
    "r_push_fail":{"es": "push FALLÓ — hazlo a mano: git push", "en": "push FAILED — do it manually: git push"},
    "r_push_to":{"es": "push se colgó (¿hook?) — hazlo a mano: git push", "en": "push timed out (hook?) — do it manually: git push"},
    "r_push_cx":{"es": "push cancelado — hazlo a mano: git push", "en": "push cancelled — do it manually: git push"},
    "r_secrets":{"es": "secrets de Jira borrados", "en": "Jira secrets removed"},
    "w_protect":{"es": "Quitando branch protection", "en": "Dropping branch protection"},
    "w_secrets":{"es": "Borrando secrets", "en": "Deleting secrets"},
}


@dataclass
class Action:
    path: str
    kind: str  # "remove" | "remove-dir" | "keep" | "leave" | "absent"


def plan_uninstall(target: Path, purge: bool) -> list[Action]:
    actions: list[Action] = []
    for rel in WIRING_FILES:
        actions.append(Action(rel, "remove" if (target / rel).is_file() else "absent"))
    for rel, line in APPEND_LINES.items():
        p = target / rel
        if not p.is_file():
            actions.append(Action(rel, "absent"))
            continue
        nonblank = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        actions.append(Action(rel, "remove" if nonblank == [line] else "leave"))
    gov = target / GOVERNANCE_DIR
    if gov.is_dir():
        actions.append(Action(GOVERNANCE_DIR, "remove-dir" if purge else "keep"))
    return actions


def apply_uninstall(target: Path, purge: bool, dry_run: bool) -> list[Action]:
    actions = plan_uninstall(target, purge)
    if dry_run:
        return actions
    for a in actions:
        p = target / a.path
        if a.kind == "remove":
            p.unlink(missing_ok=True)
        elif a.kind == "remove-dir":
            shutil.rmtree(p, ignore_errors=True)
    return actions


def _run(args: list[str], timeout: float | None = None, capture: bool = True) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return subprocess.run(args, text=True, timeout=timeout)   # inherit the terminal


def repo_from_git(target: Path, run=_run) -> str:
    """owner/repo from the GitHub remote (emkeel.toml may already be deleted by the eject)."""
    r = run(["git", "-C", str(target), "remote", "get-url", "origin"])
    if r.returncode == 0:
        m = re.search(r"github\.com[:/]+([^/]+/[^/.\s]+)", r.stdout.strip())
        if m:
            return m.group(1)
    return ""


def remote_cleanup(repo: str, branch: str, removed_paths: list[str], run=_run, lang: str = "en") -> list[tuple[str, bool]]:
    """Finish the un-govern on GitHub: drop branch protection (so removing the gates workflow
    doesn't deadlock), commit + push the removals, and drop the Jira secrets."""
    steps: list[tuple[str, bool]] = []
    with spin(t(T, "w_protect", lang)):
        run(["gh", "api", "-X", "DELETE", f"repos/{repo}/branches/{branch}/protection"])
    steps.append((t(T, "r_protect", lang), True))   # 404 (already none) is fine too
    if removed_paths:
        run(["git", "add", *removed_paths])         # stage only Emkeel's deletions (not your files)
        c = run(["git", "commit", "-m", "chore(emkeel): remove governance (eject)"])
        steps.append((t(T, "r_commit", lang), c.returncode == 0))
        try:
            print(t(T, "r_pushing", lang))
            p = run(["git", "push"], capture=False)
            steps.append((t(T, "r_push", lang) if p.returncode == 0 else t(T, "r_push_fail", lang), p.returncode == 0))
        except subprocess.TimeoutExpired:
            steps.append((t(T, "r_push_to", lang), False))
        except KeyboardInterrupt:
            steps.append((t(T, "r_push_cx", lang), False))
    with spin(t(T, "w_secrets", lang)):
        for name in ("JIRA_TOKEN", "JIRA_EMAIL", "JIRA_BASE_URL"):
            run(["gh", "secret", "delete", name, "--repo", repo])
    steps.append((t(T, "r_secrets", lang), True))
    return steps


def _do_eject(target: Path, purge: bool, remote: bool, lang: str) -> int:
    actions = apply_uninstall(target, purge, dry_run=False)
    removed = [a for a in actions if a.kind in ("remove", "remove-dir")]
    print(f"\nemkeel eject -> {target}")
    if removed:
        for a in removed:
            print(f"  {t(T, 'removed', lang)}   {a.path}")
    else:
        print(t(T, "clean", lang))
    if not purge and (target / GOVERNANCE_DIR).is_dir():
        print(t(T, "kept", lang).format(dir=GOVERNANCE_DIR))
    if remote:
        from emkeel.connect import gh_ok
        repo = repo_from_git(target)
        if not gh_ok():
            print(t(T, "skip_gh", lang))
        elif not repo:
            print(t(T, "skip_norepo", lang))
        else:
            print(t(T, "finishing", lang).format(repo=repo))
            paths = [a.path for a in actions if a.kind in ("remove", "remove-dir")]
            for label, ok in remote_cleanup(repo, "main", paths, lang=lang):
                print(f"  {'✓' if ok else '✗'} {label}")
    print(t(T, "teardown", lang))
    return 0


def main(argv: list[str] | None = None, inp=input, lang=None) -> int:
    ap = argparse.ArgumentParser(prog="emkeel eject",
                                 description="Remove Emkeel from this repo. Interactive by default.")
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--purge", action="store_true", help="also remove emkeel-governance/ (your artifacts)")
    ap.add_argument("--remote", action="store_true", help="also remove the GitHub side (protection + secrets + push)")
    ap.add_argument("--all", action="store_true", help="wiring + governance + GitHub side")
    ap.add_argument("--yes", action="store_true", help="apply without prompts (for scripts/CI)")
    ap.add_argument("--dry-run", action="store_true", help="preview only, change nothing")
    ap.add_argument("--lang", choices=["es", "en"], default=None)
    ns = ap.parse_args(argv)
    target = Path(ns.path)
    purge, remote = ns.purge or ns.all, ns.remote or ns.all
    lang = lang or ns.lang

    if ns.dry_run:
        actions = apply_uninstall(target, purge, dry_run=True)
        print(f"emkeel eject [dry-run] -> {target}")
        for a in actions:
            print(f"  {a.kind:11} {a.path}")
        print(t(T, "dry_note", lang or "en"))
        return 0

    if ns.yes:                       # non-interactive: scripts/CI opted out of prompts
        return _do_eject(target, purge, remote, lang or "en")

    if inp is input and not sys.stdin.isatty():
        print(t(T, "non_tty", lang or "en"))
        return 1

    if lang is None:
        lang = ask_language(inp)
        if lang is None:
            return 0

    print(f"\n  {t(T, 'header', lang)}\n  " + "─" * 43)
    if not is_yes(inp(t(T, "q_wiring", lang))):
        print(t(T, "cancelled", lang))
        return 0
    if (target / GOVERNANCE_DIR).is_dir():
        purge = is_yes(inp(t(T, "q_gov", lang)))
    remote = is_yes(inp(t(T, "q_remote", lang)))
    summary = t(T, "s_wiring", lang) + (f" + {GOVERNANCE_DIR}/" if purge else "") + (f" + {t(T, 's_remote', lang)}" if remote else "")
    print(t(T, "about", lang).format(summary=summary))
    if not is_yes(inp(t(T, "q_proceed", lang))):
        print(t(T, "cancelled", lang))
        return 0
    return _do_eject(target, purge, remote, lang)


if __name__ == "__main__":
    sys.exit(main())
