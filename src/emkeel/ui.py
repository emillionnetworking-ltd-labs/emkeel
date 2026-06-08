"""Tiny terminal spinner for the quick configuration steps.

`spin(label)` is a context manager: on a TTY it animates "⠋ label…" while the wrapped step
runs, then clears the line; off a TTY (CI, pipes, tests) it's a no-op so logs stay clean.
Never wrap the git push with this — that output must stay visible (a pre-push hook / auth
prompt needs the terminal).
"""

from __future__ import annotations

import itertools
import sys
import threading
import time
from contextlib import contextmanager

_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


@contextmanager
def spin(label: str, stream=None):
    stream = stream or sys.stdout
    if not getattr(stream, "isatty", lambda: False)():
        yield                                   # non-TTY → no animation, no noise
        return
    stop = threading.Event()

    def _run():
        for ch in itertools.cycle(_FRAMES):
            if stop.is_set():
                break
            stream.write(f"\r  {ch} {label}…")
            stream.flush()
            time.sleep(0.08)

    th = threading.Thread(target=_run, daemon=True)
    th.start()
    try:
        yield
    finally:
        stop.set()
        th.join()
        stream.write("\r" + " " * (len(label) + 6) + "\r")
        stream.flush()
