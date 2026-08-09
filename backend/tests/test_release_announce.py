"""Automatic release announcements (issue #41).

Announcing every release trains people to ignore announcements, so this is
deliberately selective: minor/major versions speak, patches stay quiet, and any
release can opt in explicitly. It also must never double-send (a re-run of a
rate-limited workflow would otherwise announce twice) and must never be able to
fail a healthy deploy.
"""
import pytest

from app.announce_release import already_announced, compose_message, mark_announced, should_announce
from app.db import connect, init_schema


@pytest.fixture
def conn():
    c = connect(":memory:")
    init_schema(c)
    return c


# ------------------------------------------------------------ when to speak

@pytest.mark.parametrize("tag", ["v1.5.0", "v2.0.0", "v1.0.0"])
def test_minor_and_major_releases_are_announced(tag):
    assert should_announce(tag, "") is True


@pytest.mark.parametrize("tag", ["v1.4.1", "v1.2.2", "v3.0.7"])
def test_patch_releases_stay_quiet(tag):
    assert should_announce(tag, "routine fixes") is False


def test_a_patch_can_opt_in_explicitly():
    assert should_announce("v1.4.1", "fixes a crash [announce]") is True


def test_an_unparseable_tag_stays_quiet_rather_than_spamming():
    assert should_announce("nightly", "") is False
    assert should_announce("", "") is False


# ------------------------------------------------------------ what it says

def test_the_message_names_the_version_and_reassures_about_progress():
    msg = compose_message("v1.5.0", "لوحة جديدة")
    assert "v1.5.0" in msg
    assert "لوحة جديدة" in msg
    # The reassurance is the whole point of telling people to reopen.
    assert "محفوظ" in msg


def test_the_message_works_without_a_title():
    msg = compose_message("v1.5.0", "")
    assert "v1.5.0" in msg and "محفوظ" in msg


# ------------------------------------------------------------ send only once

def test_a_release_is_announced_only_once(conn):
    assert already_announced(conn, "v1.5.0") is False
    mark_announced(conn, "v1.5.0")
    assert already_announced(conn, "v1.5.0") is True


def test_marking_one_release_does_not_silence_another(conn):
    mark_announced(conn, "v1.5.0")
    assert already_announced(conn, "v1.6.0") is False


def test_marking_twice_is_harmless(conn):
    mark_announced(conn, "v1.5.0")
    mark_announced(conn, "v1.5.0")
    assert already_announced(conn, "v1.5.0") is True
