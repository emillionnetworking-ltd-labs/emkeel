"""Tests for the spinner (must be a no-op off a TTY, so CI/tests stay clean)."""

import io

from emkeel.ui import spin


def test_spin_noop_on_non_tty():
    buf = io.StringIO()                 # not a TTY
    ran = []
    with spin("working", stream=buf):
        ran.append(True)
    assert ran == [True]                # body ran
    assert buf.getvalue() == ""         # nothing animated/written off a TTY


def test_spin_passes_through_result():
    buf = io.StringIO()
    with spin("x", stream=buf):
        result = 2 + 2
    assert result == 4
