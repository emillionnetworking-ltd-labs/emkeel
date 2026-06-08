"""Tiny shared i18n for emkeel's interactive commands (connect / eject / sync).

Each command keeps its own bilingual catalog (a dict of key -> {"es": ..., "en": ...}) and
renders strings with `t(catalog, key, lang)`. `ask_language()` shows the same language menu the
setup wizard uses, so every command can be Spanish or English.
"""

from __future__ import annotations

YES = ("y", "yes", "s", "si", "sí")
CANCEL = ("c", "q", "cancel", "cancelar", "salir", "quit")


def t(catalog: dict, key: str, lang: str) -> str:
    entry = catalog.get(key, {})
    return entry.get(lang) or entry.get("en") or key


def is_yes(answer: str) -> bool:
    return answer.strip().lower() in YES


def ask_language(inp=input) -> str | None:
    """Show the language menu; return 'es' | 'en' | None (cancel)."""
    print("\n  Idioma / Language:")
    print("  [1] Español  (Enter)")
    print("  [2] English")
    print("  [c] Cancelar / Cancel")
    while True:
        r = inp("  > ").strip().lower()
        if r in ("", "1", "es", "español", "espanol"):
            return "es"
        if r in ("2", "en", "english"):
            return "en"
        if r in CANCEL:
            return None
