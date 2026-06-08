"""emkeel sync — bring your local back in shape after the adopt PR merges.

Switches to the default branch, pulls, prunes, and deletes local branches that are already
merged (detected via `--merged` OR an upstream that's `gone` — which catches squash-merges,
where the branch commits aren't ancestors of the default). Safe + idempotent. Bilingual.
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from emkeel.i18n import ask_language, t

T: dict[str, dict[str, str]] = {
    "header":   {"es": "emkeel sync", "en": "emkeel sync"},
    "on":       {"es": "✓ en {db}", "en": "✓ on {db}"},
    "pulled":   {"es": "✓ actualizado (pull)", "en": "✓ pulled"},
    "pull_skip":{"es": "⚠ pull omitido (hazlo a mano: git pull)", "en": "⚠ pull skipped (do it manually: git pull)"},
    "removed":  {"es": "✓ ramas fusionadas borradas: {names}", "en": "✓ removed merged branch(es): {names}"},
    "none":     {"es": "✓ sin ramas fusionadas que limpiar", "en": "✓ no merged branches to clean"},
}


def _run(args: list[str], capture: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return subprocess.run(args, text=True, timeout=timeout)   # inherit the terminal (auth prompts)


def default_branch(run=_run) -> str:
    r = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().rsplit("/", 1)[-1]
    return "main"


def _own(name: str) -> bool:
    return name.split("/", 1)[0] in ("chore", "feat", "fix")


def cleanable_branches(default: str, run=_run) -> list[str]:
    """Local chore/feat/fix branches safe to delete: merged into default, or upstream gone."""
    found: set[str] = set()
    merged = run(["git", "branch", "--merged", default])
    if merged.returncode == 0:
        for ln in merged.stdout.splitlines():
            n = ln.replace("*", "").strip()
            if n and n != default and _own(n):
                found.add(n)
    vv = run(["git", "branch", "-vv"])
    if vv.returncode == 0:
        for ln in vv.stdout.splitlines():
            if ": gone]" in ln:
                n = ln.replace("*", "").strip().split(" ", 1)[0]
                if _own(n):
                    found.add(n)
    return sorted(found)


def sync(run=_run, lang: str = "en") -> list[str]:
    out: list[str] = []
    db = default_branch(run)
    run(["git", "checkout", db], capture=False)
    out.append(t(T, "on", lang).format(db=db))
    p = run(["git", "pull", "--ff-only"], capture=False)
    out.append(t(T, "pulled", lang) if p.returncode == 0 else t(T, "pull_skip", lang))
    run(["git", "fetch", "--prune"])
    gone = cleanable_branches(db, run)
    for b in gone:
        run(["git", "branch", "-D", b])
    out.append(t(T, "removed", lang).format(names=", ".join(gone)) if gone else t(T, "none", lang))
    return out


def wait_for_merge(pr_ref: str, run=_run, tries: int = 20, delay: float = 15.0, sleep=time.sleep) -> bool:
    """Poll until the PR on `pr_ref` (branch or number) is MERGED. Returns False on timeout."""
    for i in range(tries):
        r = run(["gh", "pr", "view", pr_ref, "--json", "state", "-q", ".state"])
        if r.returncode == 0 and r.stdout.strip() == "MERGED":
            return True
        if i < tries - 1:
            sleep(delay)
    return False


def main(argv: list[str] | None = None, inp=input, lang=None) -> int:
    ap = argparse.ArgumentParser(prog="emkeel sync", description="Post-merge local cleanup.")
    ap.add_argument("--lang", choices=["es", "en"], default=None)
    ns = ap.parse_args(argv if argv is not None else None)
    lang = lang or ns.lang
    if lang is None:
        lang = ask_language(inp)
        if lang is None:
            return 0
    print(f"\n  {t(T, 'header', lang)}")
    for line in sync(lang=lang):
        print("  " + line)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
