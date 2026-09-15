"""Tests for the scope/race-selection layer.

The race universe fixture below is illustrative test data only — it is not
a claim about any real 2026 race, competitiveness rating, or candidate.
Real race universes must be imported from an authoritative source (see
README.md, "Scoping real elections").
"""

import pytest

from promise_engine.models import PoliticalEntity
from promise_engine.scope import (
    CollectionPolicy,
    OFFICIAL_PLUS_SPEECHES_AND_SOCIAL,
    OFFICIAL_SOURCES_ONLY,
    OfficeType,
    Race,
    Region,
    ScopeQuery,
    all_federal_congressional,
    all_of_office,
    group_by_national_party,
    issue_across_races,
    one_competitive_race_per_region,
    one_race,
    one_state,
    resolve_scope,
    selected_races,
)
from datetime import date


@pytest.fixture
def universe():
    """Eight illustrative test-fixture races. Not real 2026 data."""

    def r(race_id, office, state, region=None, rating=None, topics=()):
        return Race(
            race_id=race_id,
            office_type=office,
            state=state,
            cycle=2026,
            region=region,
            competitiveness_rating=rating,
            competitiveness_source="TEST FIXTURE - not a real rating" if rating else None,
            topics=topics,
        )

    return [
        r("sen-a", OfficeType.US_SENATE, "AA", Region.NORTHEAST, "toss_up", ("healthcare",)),
        r("sen-b", OfficeType.US_SENATE, "BB", Region.SOUTH, "solid_r", ("immigration",)),
        r("sen-c", OfficeType.US_SENATE, "CC", Region.MIDWEST, "lean_d", ("healthcare", "taxes")),
        r("sen-d", OfficeType.US_SENATE, "DD", Region.WEST, "toss_up", ("climate",)),
        r("house-a1", OfficeType.US_HOUSE, "AA", Region.NORTHEAST, "toss_up", ("housing",)),
        r("house-a2", OfficeType.US_HOUSE, "AA", Region.NORTHEAST, "safe_d", ("education",)),
        r("gov-a", OfficeType.GOVERNOR, "AA", Region.NORTHEAST, "toss_up", ("public_safety",)),
        r("statehouse-a", OfficeType.STATE_LEGISLATURE_LOWER, "AA", Region.NORTHEAST, None, ()),
    ]


def test_scenario_1_one_senate_race(universe):
    result = resolve_scope(one_race("sen-a"), universe)
    assert [r.race_id for r in result] == ["sen-a"]


def test_scenario_4_three_selected_senate_races(universe):
    result = resolve_scope(selected_races(["sen-a", "sen-b", "sen-c"]), universe)
    assert {r.race_id for r in result} == {"sen-a", "sen-b", "sen-c"}


def test_scenario_6_one_states_senate_and_house(universe):
    result = resolve_scope(one_state("AA", cycle=2026), universe)
    race_ids = {r.race_id for r in result}
    assert race_ids == {"sen-a", "house-a1", "house-a2"}


def test_scenario_7_one_states_federal_and_state_level(universe):
    query = one_state(
        "AA",
        cycle=2026,
        office_types=frozenset(
            {OfficeType.US_SENATE, OfficeType.US_HOUSE, OfficeType.GOVERNOR, OfficeType.STATE_LEGISLATURE_LOWER}
        ),
    )
    result = resolve_scope(query, universe)
    race_ids = {r.race_id for r in result}
    assert race_ids == {"sen-a", "house-a1", "house-a2", "gov-a", "statehouse-a"}


def test_scenario_8_all_competitive_senate_races(universe):
    result = resolve_scope(all_of_office(OfficeType.US_SENATE, cycle=2026, competitive_only=True), universe)
    race_ids = {r.race_id for r in result}
    assert race_ids == {"sen-a", "sen-c", "sen-d"}  # sen-b is solid_r, excluded
    assert "sen-b" not in race_ids


def test_scenario_10_all_senate_races(universe):
    result = resolve_scope(all_of_office(OfficeType.US_SENATE, cycle=2026), universe)
    assert len(result) == 4


def test_scenario_12_all_federal_congressional_races(universe):
    result = resolve_scope(all_federal_congressional(cycle=2026), universe)
    assert len(result) == 6  # 4 Senate + 2 House


def test_scenario_3_one_competitive_race_per_region(universe):
    result = resolve_scope(one_competitive_race_per_region(OfficeType.US_SENATE, cycle=2026), universe)
    regions = {r.region for r in result}
    # sen-b (South) is solid_r, i.e. not competitive, so the South has no
    # representative in the result even though it has a Senate race.
    assert regions == {Region.NORTHEAST, Region.MIDWEST, Region.WEST}
    assert all(r.is_competitive for r in result)


def test_scenario_13_one_issue_across_all_races(universe):
    result = resolve_scope(issue_across_races(["healthcare"], cycle=2026), universe)
    race_ids = {r.race_id for r in result}
    assert race_ids == {"sen-a", "sen-c"}


def test_scenario_14_one_issue_across_selected_states(universe):
    result = resolve_scope(issue_across_races(["healthcare"], cycle=2026, states=["CC"]), universe)
    assert [r.race_id for r in result] == ["sen-c"]


def test_scenario_9_11_generic_all_of_office_house(universe):
    result = resolve_scope(all_of_office(OfficeType.US_HOUSE, cycle=2026), universe)
    assert len(result) == 2
    competitive = resolve_scope(all_of_office(OfficeType.US_HOUSE, cycle=2026, competitive_only=True), universe)
    assert [r.race_id for r in competitive] == ["house-a1"]


def test_race_with_no_rating_is_not_competitive(universe):
    statehouse = next(r for r in universe if r.race_id == "statehouse-a")
    assert statehouse.is_competitive is False


def test_collection_policy_official_sources_only_scenario_20():
    from promise_engine.models import SourceTier

    assert OFFICIAL_SOURCES_ONLY.source_allowed(SourceTier.PARTY_POLICY_PAGE)
    assert not OFFICIAL_SOURCES_ONLY.source_allowed(SourceTier.SPEECH_OR_LEAFLET)
    assert not OFFICIAL_SOURCES_ONLY.source_allowed(SourceTier.SOCIAL_MEDIA_POST)


def test_collection_policy_official_plus_speeches_and_social_scenario_22():
    from promise_engine.models import SourceTier

    assert OFFICIAL_PLUS_SPEECHES_AND_SOCIAL.source_allowed(SourceTier.SOCIAL_MEDIA_POST)
    assert OFFICIAL_PLUS_SPEECHES_AND_SOCIAL.source_allowed(SourceTier.INTERVIEW)


def test_collection_policy_post_nomination_window_scenario_24():
    policy = CollectionPolicy(
        allowed_source_tiers=OFFICIAL_SOURCES_ONLY.allowed_source_tiers,
        only_after_nomination=True,
        nomination_dates={"entity-1": date(2026, 6, 1)},
    )
    assert not policy.collection_allowed("entity-1", date(2026, 3, 1))
    assert policy.collection_allowed("entity-1", date(2026, 7, 1))
    # No recorded nomination date means the window can never open for that entity.
    assert not policy.collection_allowed("entity-2", date(2026, 9, 1))


def test_group_by_national_party_scenario_16():
    entities = [
        PoliticalEntity("e1", "Candidate A", "US-AA", national_party="Democratic"),
        PoliticalEntity("e2", "Candidate B", "US-AA", national_party="Republican"),
        PoliticalEntity("e3", "Candidate C", "US-BB", national_party="Democratic"),
        PoliticalEntity("e4", "Candidate D", "US-BB"),  # unresolved party, must not be dropped
    ]
    grouped = group_by_national_party(entities)
    assert {e.entity_id for e in grouped["Democratic"]} == {"e1", "e3"}
    assert {e.entity_id for e in grouped["Republican"]} == {"e2"}
    assert {e.entity_id for e in grouped["unknown"]} == {"e4"}
