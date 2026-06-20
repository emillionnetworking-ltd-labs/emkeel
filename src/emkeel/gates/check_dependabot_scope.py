"""Gate: the Dependabot lane may touch ONLY dependency files.

Deterministic, runs in CI. The sibling of `check_maint_scope`: it's what makes the no-ticket
`dependabot/*` lane honest. A Dependabot PR that changes anything beyond dependency manifests/lockfiles
(and GitHub Actions workflow bumps) FAILS — so `dependabot/` can't be used to merge real code without a
ticket. For any other branch it's a no-op (N/A).

Needs the workflow to check out full history (`fetch-depth: 0`) so it can diff against the base.
"""

from __future__ import annotations

import os
import sys

from emkeel.gates.check_maint_scope import changed_files   # one source of the base diff
from emkeel.lanes import is_dependabot_lane

# Dependency manifests / lockfiles across the common ecosystems Dependabot supports.
_MANIFEST_NAMES = {
    # JavaScript / npm / yarn / pnpm
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    # Python
    "requirements.txt", "Pipfile", "Pipfile.lock", "poetry.lock", "pyproject.toml",
    "setup.py", "setup.cfg",
    # Ruby
    "Gemfile", "Gemfile.lock",
    # Go
    "go.mod", "go.sum",
    # Rust
    "Cargo.toml", "Cargo.lock",
    # PHP
    "composer.json", "composer.lock",
    # .NET
    "packages.config",
}


def is_dependency_path(path: str) -> bool:
    """True if `path` is something Dependabot legitimately edits: a dependency manifest/lockfile,
    a GitHub Actions workflow (version bumps), or the dependabot config itself."""
    p = path.strip()
    if not p:
        return False
    if p.startswith(".github/workflows/"):                 # github-actions version bumps
        return True
    if p in (".github/dependabot.yml", ".github/dependabot.yaml"):
        return True
    name = p.rsplit("/", 1)[-1]
    if name in _MANIFEST_NAMES:
        return True
    if name.startswith("requirements") and name.endswith(".txt"):   # requirements-dev.txt, etc.
        return True
    if name.endswith((".csproj", ".vbproj", ".fsproj")):            # .NET project files
        return True
    return False


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    if not is_dependabot_lane(branch):
        print(f"OK: '{branch}' is not a dependabot branch; scope check N/A.")
        return 0

    base = os.environ.get("EMKEEL_BASE_REF") or "main"
    files = changed_files(base)
    stray = [f for f in files if not is_dependency_path(f)]
    if stray:
        print("FAIL: a dependabot PR may only touch dependency files (manifests/lockfiles + Actions "
              f"bumps), but it also changes: {', '.join(stray)}. Use a real ticket branch for code "
              "changes.", file=sys.stderr)
        return 1
    print(f"OK: dependabot PR touches {len(files)} file(s), all dependency files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
