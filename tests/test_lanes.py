"""Tests for the shared maintenance-lane predicate (single source of truth)."""

from emkeel.lanes import MAINT_PREFIX, is_maint_lane


def test_prefix_is_canonical():
    assert MAINT_PREFIX == "emkeel-maint/"


def test_is_maint_lane_true():
    assert is_maint_lane("emkeel-maint/0.1.69-abc123") is True
    assert is_maint_lane(MAINT_PREFIX) is True


def test_is_maint_lane_false():
    assert is_maint_lane("feat/KEEL-1-x") is False
    assert is_maint_lane("fix/ECO-2-y") is False
    assert is_maint_lane("main") is False


def test_is_maint_lane_handles_empty_and_none():
    assert is_maint_lane("") is False
    assert is_maint_lane(None) is False


def test_all_lane_sites_use_the_shared_predicate():
    # Single source of truth: the gates / ship / jira import is_maint_lane or MAINT_PREFIX from lanes,
    # rather than each hardcoding the string. (Guards against the duplication this ticket removed.)
    import emkeel.gates.check_maint_scope as scope
    import emkeel.gates.check_ticket_link as tlink
    import emkeel.jira as jira
    import emkeel.ship as ship
    assert scope.is_maint_lane is is_maint_lane
    assert tlink.is_maint_lane is is_maint_lane
    assert jira.is_maint_lane is is_maint_lane
    assert ship.MAINT_PREFIX is MAINT_PREFIX
