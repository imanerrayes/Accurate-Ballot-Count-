"""Tests for the imported 2026 race data (promise_engine.data.races_2026).

These check internal consistency of the import (counts, citation
presence, no duplicate race IDs) — they do not and cannot verify that the
underlying political facts are still current, since races and ratings
change. Re-running the import is the way to check that.

The data behind this module is now two merged extraction batches (see
races_2026.py's module docstring and data/extracted/2026-09-15/PROVENANCE.md):
the assistant's own partial WebSearch import, and the repository owner's
manual extraction from Cook Political Report, which completed Senate
coverage and expanded House coverage from 18 Toss-Up-only races to 70
races across five rating tiers.
"""

from promise_engine.data.races_2026 import HOUSE_RATED_RACES_2026, SENATE_UNIVERSE_2026
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

    for race in (*SENATE_UNIVERSE_2026, *HOUSE_RATED_RACES_2026):
        if race.competitiveness_rating is not None:
            assert race.competitiveness_source, f"{race.race_id} has a rating but no citation"


def test_senate_coverage_is_now_complete():
    """The manual extraction batch filled every gap the WebSearch-only
    import left; all 35 Senate races now carry a cited rating."""

    unrated = [r for r in SENATE_UNIVERSE_2026 if r.competitiveness_rating is None]
    assert unrated == []


def test_house_rated_races_span_five_cook_tiers():
    assert len(HOUSE_RATED_RACES_2026) == 70
    assert all(r.competitiveness_source for r in HOUSE_RATED_RACES_2026)
    assert all(r.office_type == OfficeType.US_HOUSE for r in HOUSE_RATED_RACES_2026)
    ratings = {r.competitiveness_rating for r in HOUSE_RATED_RACES_2026}
    assert ratings == {"likely_d", "lean_d", "toss_up", "lean_r", "likely_r"}


def test_house_races_have_no_duplicate_districts():
    keys = [(r.state, r.district) for r in HOUSE_RATED_RACES_2026]
    assert len(keys) == len(set(keys))


def test_every_race_has_a_region_assigned():
    """import_tools' CSV loaders don't set region (it isn't a CSV column);
    races_2026._ensure_region must backfill it for every merged-in race."""

    missing = [r for r in (*SENATE_UNIVERSE_2026, *HOUSE_RATED_RACES_2026) if r.region is None]
    assert missing == []


def test_batch1_house_races_are_all_superseded_not_orphaned():
    """Every one of the original 18 WebSearch-sourced Toss Up races should
    reappear in the 70-race manual extraction (possibly with an updated
    rating), not silently disappear."""

    batch1_keys = {
        ("OH", "09"), ("IA", "01"), ("NE", "02"), ("ME", "02"), ("WA", "03"),
        ("CA", "13"), ("CA", "45"), ("NM", "02"), ("NY", "04"), ("NC", "01"),
        ("OH", "13"), ("TX", "34"), ("AZ", "01"), ("AZ", "06"), ("CO", "08"),
        ("MI", "07"), ("PA", "07"), ("PA", "10"),
    }
    current_keys = {(r.state, r.district) for r in HOUSE_RATED_RACES_2026}
    assert batch1_keys <= current_keys


def test_resolve_scope_against_real_senate_universe_returns_only_cited_competitive_races():
    result = resolve_scope(all_of_office(OfficeType.US_SENATE, cycle=2026, competitive_only=True), SENATE_UNIVERSE_2026)
    states = {r.state for r in result}
    assert all(r.competitiveness_source for r in result)
    assert states == {"AK", "GA", "IA", "KS", "ME", "MI", "MN", "NC", "NE", "NH", "OH", "TX"}
