"""Tests del primer gate. Dogfooding: el gate nace con su test (test-on-fix desde día 1)."""

from emkeel.gates.check_ticket_link import find_ticket_key


def test_finds_key_in_branch():
    assert find_ticket_key("feature/KEEL-12-add-gate", "") == "KEEL-12"


def test_finds_key_in_pr_title():
    assert find_ticket_key("", "PROD-345: fix login") == "PROD-345"


def test_branch_takes_precedence_when_both_present():
    assert find_ticket_key("feature/KEEL-1-x", "KEEL-2: y") == "KEEL-1"


def test_returns_none_when_no_key():
    assert find_ticket_key("feature/no-ticket", "just a title") is None
