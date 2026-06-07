"""emkeel version — show the installed version and whether a newer one is on PyPI.

PyPI is the public source of truth (the repo may be private). The check is best-effort:
short timeout, silent on any failure, and skippable via EMKEEL_NO_UPDATE_CHECK=1.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

from emkeel import __version__

PYPI_JSON = "https://pypi.org/pypi/emkeel/json"


def _parse(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split(".")[:3])


def latest_on_pypi(fetch=None) -> str | None:
    """Return the latest version string on PyPI, or None on any failure."""
    try:
        if fetch is None:
            with urllib.request.urlopen(PYPI_JSON, timeout=3) as r:
                data = json.loads(r.read().decode())
        else:
            data = fetch()
        return data["info"]["version"]
    except Exception:
        return None


def update_line(installed: str, latest: str | None) -> str | None:
    """The 'update available' line, or None if up to date / unknown."""
    if latest and _parse(latest) > _parse(installed):
        return f"update available: {installed} -> {latest}  (run: pipx upgrade emkeel)"
    return None


def main(argv: list[str] | None = None) -> int:
    print(f"emkeel {__version__}")
    if os.environ.get("EMKEEL_NO_UPDATE_CHECK"):
        return 0
    line = update_line(__version__, latest_on_pypi())
    if line:
        print(line, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
