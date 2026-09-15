"""Tests for the imported 2026 race data (promise_engine.data.races_2026).

These check internal consistency of the import (counts, citation
presence, no duplicate race IDs) — they do not and cannot verify that the
underlying political facts are still current, since races and ratings
change. Re-running the import is the way to check that.
"""

from promise_engine.data.races_2026 import HOUSE_TOSSUPS_2026, SENATE_UNIVERSE_2026
from promise_engine.scope import OfficeType, all_of_office, resolve_scope


def test_senate_universe_has_all_35_seats():
    assert len(SENATE_UNIVERSE_2026) == 35
    assert len({r.race_id for r in SENATE_UNIVERSE_2026}) == 35  # no duplicate IDs
    assert len({r.state for r in SENATE_UNIVERSE_2026}) == 35  # no duplicate states


def test_senate_universe_includes_both_special_elections():
    states = {r.state for r in SENATE_UNIVERSE_2026}
    assert "FL" in states
    assert "OH" in states
    specials = [r for r in SENATE_UNIVERSE_2026 if r.notes and "special election" in r.notes.lower()]
    assert len(specials) == 2


def test_every_rated_race_carries_a_citation():
    """A rating without a source would violate the project's sourcing rule."""

    for race in (*SENATE_UNIVERSE_2026, *HOUSE_TOSSUPS_2026):
        if race.competitiveness_rating is not None:
            assert race.competitiveness_source, f"{race.race_id} has a rating but no citation"


def test_unrated_senate_races_are_not_silently_marked_competitive():
    unrated = [r for r in SENATE_UNIVERSE_2026 if r.competitiveness_rating is None]
    assert unrated  # most of the 35 seats have no cited rating in this import
    assert all(not r.is_competitive for r in unrated)


def test_house_tossups_all_have_a_rating_and_source():
    assert len(HOUSE_TOSSUPS_2026) == 18
    assert all(r.competitiveness_rating == "toss_up" for r in HOUSE_TOSSUPS_2026)
    assert all(r.competitiveness_source for r in HOUSE_TOSSUPS_2026)
    assert all(r.office_type == OfficeType.US_HOUSE for r in HOUSE_TOSSUPS_2026)


def test_house_tossups_have_no_duplicate_districts():
    keys = [(r.state, r.district) for r in HOUSE_TOSSUPS_2026]
    assert len(keys) == len(set(keys))


def test_unverified_house_districts_are_flagged_in_notes():
    """13 of the 18 district numbers were not confirmed by a source
    retrieved this session; each must say so rather than look as solid as
    the 5 that were confirmed."""

    flagged = [r for r in HOUSE_TOSSUPS_2026 if r.notes and "not confirmed via a source retrieved this session" in r.notes]
    confirmed = [r for r in HOUSE_TOSSUPS_2026 if r.notes and "district confirmed" in r.notes.lower()]
    assert len(flagged) == 13
    assert len(confirmed) == 5


def test_resolve_scope_against_real_senate_universe_returns_only_cited_competitive_races():
    result = resolve_scope(all_of_office(OfficeType.US_SENATE, cycle=2026, competitive_only=True), SENATE_UNIVERSE_2026)
    states = {r.state for r in result}
    # Every returned race must actually carry a citation, not an inferred rating.
    assert all(r.competitiveness_source for r in result)
    assert states == {"IA", "TX", "ME", "GA", "MI", "MN", "NC", "NH"}
