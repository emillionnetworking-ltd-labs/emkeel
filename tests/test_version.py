"""Tests for emkeel version + the PyPI update check."""

from emkeel import __version__
from emkeel.version import latest_on_pypi, main, update_line


def test_update_line_when_newer():
    line = update_line("0.1.0", "0.2.0")
    assert line and "pipx upgrade emkeel" in line


def test_no_update_line_when_current_or_older():
    assert update_line("0.1.8", "0.1.8") is None
    assert update_line("0.1.8", "0.1.7") is None


def test_no_update_line_when_unknown():
    assert update_line("0.1.8", None) is None


def test_latest_on_pypi_silent_on_failure():
    def boom():
        raise RuntimeError("network down")
    assert latest_on_pypi(fetch=boom) is None


def test_latest_on_pypi_parses_injected():
    assert latest_on_pypi(fetch=lambda: {"info": {"version": "9.9.9"}}) == "9.9.9"


def test_main_prints_installed_version(capsys, monkeypatch):
    monkeypatch.setenv("EMKEEL_NO_UPDATE_CHECK", "1")  # no network in tests
    assert main([]) == 0
    assert __version__ in capsys.readouterr().out
