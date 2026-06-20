"""Tests for the shared lane predicates (single source of truth)."""

from emkeel.lanes import (
    DEPENDABOT_PREFIX,
    MAINT_PREFIX,
    is_dependabot_lane,
    is_maint_lane,
)


def test_prefix_is_canonical():
    assert MAINT_PREFIX == "emkeel-maint/"
    assert DEPENDABOT_PREFIX == "dependabot/"


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


def test_is_dependabot_lane():
    assert is_dependabot_lane("dependabot/npm_and_yarn/lodash-4.17.21") is True
    assert is_dependabot_lane(DEPENDABOT_PREFIX) is True
    assert is_dependabot_lane("feat/KEEL-1-x") is False
    assert is_dependabot_lane("emkeel-maint/0.1.71-abc") is False     # the lanes don't overlap
    assert is_dependabot_lane("") is False
    assert is_dependabot_lane(None) is False


def test_all_lane_sites_use_the_shared_predicate():
    # Single source of truth: the gates / ship / jira import the predicates / prefix from lanes,
    # rather than each hardcoding the string. (Guards against the duplication this ticket removed.)
    import emkeel.gates.check_dependabot_scope as dscope
    import emkeel.gates.check_maint_scope as scope
    import emkeel.gates.check_ticket_link as tlink
    import emkeel.jira as jira
    import emkeel.ship as ship
    assert scope.is_maint_lane is is_maint_lane
    assert tlink.is_maint_lane is is_maint_lane and tlink.is_dependabot_lane is is_dependabot_lane
    assert jira.is_maint_lane is is_maint_lane and jira.is_dependabot_lane is is_dependabot_lane
    assert dscope.is_dependabot_lane is is_dependabot_lane
    assert ship.MAINT_PREFIX is MAINT_PREFIX
