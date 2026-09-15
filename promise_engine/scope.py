"""Election scope selection and collection policy.

This module generalizes the product's race-selection and source-policy
options into two composable, queryable objects instead of one code path
per option:

- :class:`ScopeQuery` answers "which races": one race, a state's federal
  delegation, every competitive Senate seat, one race per region, and so
  on.
- :class:`CollectionPolicy` answers "which evidence, and from when":
  official sources only versus official sources plus manifestos, speeches,
  or social media, and whether collection is limited to the post-nomination
  window.

Neither object contains a single hardcoded race, competitiveness rating,
or candidate name. ``Race`` is a plain record the caller populates from an
authoritative source (FEC candidate filings for who is running and which
office; a named rating service such as Cook Political Report, Sabato's
Crystal Ball, or Inside Elections for ``competitiveness_rating``). This
module resolves queries against whatever universe of ``Race`` records the
caller supplies; it does not look anything up on its own. See
``README.md`` for how the real 2026 race universe should be imported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, FrozenSet, Mapping, Optional, Sequence, Tuple

from .models import PoliticalEntity, SourceTier


class OfficeType(str, Enum):
    US_SENATE = "us_senate"
    US_HOUSE = "us_house"
    GOVERNOR = "governor"
    STATE_LEGISLATURE_UPPER = "state_legislature_upper"
    STATE_LEGISLATURE_LOWER = "state_legislature_lower"


#: Office types this repository currently ships a jurisdiction profile
#: for (see ``promise_engine.jurisdictions.us_congress``). A race with any
#: other office type can still be scoped and rostered, but its legal
#: authority dimension will abstain for lack of a profile (Section 7.1)
#: until a matching state or gubernatorial profile is added.
FEDERAL_OFFICE_TYPES: FrozenSet[OfficeType] = frozenset({OfficeType.US_SENATE, OfficeType.US_HOUSE})


class Region(str, Enum):
    """The U.S. Census Bureau's four statistical regions (Census Regions
    and Divisions of the United States). Used only for the "one
    competitive race per region" scenario; it is a fixed, citable
    geographic grouping, not an editorial claim about political
    similarity."""

    NORTHEAST = "northeast"
    MIDWEST = "midwest"
    SOUTH = "south"
    WEST = "west"


#: Competitiveness labels not treated as competitive by default. Any other
#: non-``None`` rating (e.g. "toss_up", "lean_D", "lean_R", "likely_D",
#: "likely_R") is treated as competitive. Callers using a different rating
#: vocabulary should normalise to these labels or filter races directly.
_NON_COMPETITIVE_RATINGS = frozenset({"solid_d", "solid_r", "safe_d", "safe_r"})


@dataclass(frozen=True)
class Race:
    """One contest. Populate every field from an authoritative source;
    this module supplies none of these facts itself.

    ``competitiveness_rating`` and ``competitiveness_source`` must be
    taken verbatim from a named rating service and cited, per this
    project's sourcing requirement — never inferred or guessed.
    """

    race_id: str
    office_type: OfficeType
    state: str  # USPS two-letter code, e.g. "MI"
    cycle: int
    district: Optional[str] = None  # None for a statewide race (Senate, Governor)
    region: Optional[Region] = None
    competitiveness_rating: Optional[str] = None
    competitiveness_source: Optional[str] = None
    entity_ids: Tuple[str, ...] = ()
    topics: Tuple[str, ...] = ()

    @property
    def is_competitive(self) -> bool:
        if self.competitiveness_rating is None:
            return False
        return self.competitiveness_rating.lower() not in _NON_COMPETITIVE_RATINGS


@dataclass(frozen=True)
class ScopeQuery:
    """A composable filter over a race universe.

    Each of the 35 race-selection scenarios in the product brief is a
    particular combination of these fields rather than a distinct code
    path — see README.md, "Scoping real elections", for the mapping.
    """

    cycle: Optional[int] = None
    office_types: Optional[FrozenSet[OfficeType]] = None
    states: Optional[FrozenSet[str]] = None
    race_ids: Optional[FrozenSet[str]] = None
    regions: Optional[FrozenSet[Region]] = None
    competitive_only: bool = False
    topics: Optional[FrozenSet[str]] = None
    one_per_region: bool = False

    def matches(self, race: Race) -> bool:
        if self.cycle is not None and race.cycle != self.cycle:
            return False
        if self.office_types is not None and race.office_type not in self.office_types:
            return False
        if self.states is not None and race.state not in self.states:
            return False
        if self.race_ids is not None and race.race_id not in self.race_ids:
            return False
        if self.regions is not None and race.region not in self.regions:
            return False
        if self.competitive_only and not race.is_competitive:
            return False
        if self.topics is not None and not (set(race.topics) & self.topics):
            return False
        return True


def resolve_scope(query: ScopeQuery, universe: Sequence[Race]) -> Tuple[Race, ...]:
    """Resolve a scope query against a caller-supplied race universe.

    Performs no lookup of its own: ``universe`` must already carry the
    real races, districts, and ratings the caller wants to consider.
    """

    matched = [r for r in universe if query.matches(r)]

    if query.one_per_region:
        picked: Dict[Region, Race] = {}
        for race in matched:
            if race.region is not None and race.region not in picked:
                picked[race.region] = race
        return tuple(picked.values())

    return tuple(matched)


# ---------------------------------------------------------------------------
# Convenience constructors for the named scenarios (README "Scoping real
# elections" maps each of the 35 product options to one of these, or a
# direct ScopeQuery(...) call for the less common combinations).
# ---------------------------------------------------------------------------


def one_race(race_id: str) -> ScopeQuery:
    """Scenarios 1-2: one Senate race, or one House district."""

    return ScopeQuery(race_ids=frozenset({race_id}))


def selected_races(race_ids: Sequence[str]) -> ScopeQuery:
    """Scenarios 4-5: three selected Senate races, five selected House districts."""

    return ScopeQuery(race_ids=frozenset(race_ids))


def one_competitive_race_per_region(office_type: OfficeType, cycle: int) -> ScopeQuery:
    """Scenario 3: one competitive Senate race in each region."""

    return ScopeQuery(office_types=frozenset({office_type}), cycle=cycle, competitive_only=True, one_per_region=True)


def one_state(state: str, cycle: int, office_types: FrozenSet[OfficeType] = FEDERAL_OFFICE_TYPES) -> ScopeQuery:
    """Scenario 6 (a state's Senate and House races) with the default
    ``office_types``; pass a wider set including ``GOVERNOR`` and the
    state-legislature office types for scenario 7 (a state's federal and
    state-level races)."""

    return ScopeQuery(states=frozenset({state}), office_types=frozenset(office_types), cycle=cycle)


def all_of_office(office_type: OfficeType, cycle: int, competitive_only: bool = False) -> ScopeQuery:
    """Scenarios 8-11: all competitive Senate races, all competitive House
    races, all Senate races, all House races."""

    return ScopeQuery(office_types=frozenset({office_type}), cycle=cycle, competitive_only=competitive_only)


def all_federal_congressional(cycle: int, competitive_only: bool = False) -> ScopeQuery:
    """Scenario 12: all federal congressional races (House and Senate)."""

    return ScopeQuery(office_types=FEDERAL_OFFICE_TYPES, cycle=cycle, competitive_only=competitive_only)


def issue_across_races(topics: Sequence[str], cycle: int, states: Optional[Sequence[str]] = None) -> ScopeQuery:
    """Scenarios 13-14: one issue across all races, or across selected
    battleground states."""

    return ScopeQuery(
        cycle=cycle,
        topics=frozenset(topics),
        states=frozenset(states) if states is not None else None,
    )


# ---------------------------------------------------------------------------
# Collection policy (scenarios 20-24: which sources, and from when)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CollectionPolicy:
    """Which source tiers may be collected, and the time window for
    collection. Mirrors Section 10's source hierarchy (COL-002, COL-003):
    a substitute tier is only ever an addition on top of official sources,
    never a replacement for them.
    """

    allowed_source_tiers: FrozenSet[SourceTier]
    window_start: Optional[date] = None
    window_end: Optional[date] = None
    only_after_nomination: bool = False
    nomination_dates: Mapping[str, date] = field(default_factory=dict)

    def source_allowed(self, tier: SourceTier) -> bool:
        return tier in self.allowed_source_tiers

    def collection_allowed(self, entity_id: str, as_of: date) -> bool:
        """Scenarios 23-24: full cycle versus post-nomination only."""

        if self.window_start is not None and as_of < self.window_start:
            return False
        if self.window_end is not None and as_of > self.window_end:
            return False
        if self.only_after_nomination:
            nomination_date = self.nomination_dates.get(entity_id)
            if nomination_date is None or as_of < nomination_date:
                return False
        return True


#: Scenario 20: official campaign websites and party pages only.
OFFICIAL_SOURCES_ONLY = CollectionPolicy(allowed_source_tiers=frozenset({SourceTier.PARTY_POLICY_PAGE}))

#: Scenario 21: official sources plus manifestos and adopted platforms.
OFFICIAL_PLUS_PLATFORMS = CollectionPolicy(
    allowed_source_tiers=frozenset(
        {SourceTier.PARTY_POLICY_PAGE, SourceTier.MANIFESTO_OR_PROGRAMME, SourceTier.FORMALLY_ADOPTED_PROGRAMME}
    )
)

#: Scenario 22: official sources, platforms, plus speeches, interviews, and social media.
OFFICIAL_PLUS_SPEECHES_AND_SOCIAL = CollectionPolicy(
    allowed_source_tiers=frozenset(
        {
            SourceTier.PARTY_POLICY_PAGE,
            SourceTier.MANIFESTO_OR_PROGRAMME,
            SourceTier.FORMALLY_ADOPTED_PROGRAMME,
            SourceTier.SPEECH_OR_LEAFLET,
            SourceTier.INTERVIEW,
            SourceTier.SOCIAL_MEDIA_POST,
        }
    )
)


# ---------------------------------------------------------------------------
# Party-level grouping (scenarios 15-16: platforms rather than candidates,
# Democratic and Republican promises nationally)
# ---------------------------------------------------------------------------


def group_by_national_party(entities: Sequence[PoliticalEntity]) -> Mapping[str, Tuple[PoliticalEntity, ...]]:
    """Group entities by their declared national party affiliation.

    Entities with no ``national_party`` set are grouped under ``"unknown"``
    rather than dropped, so a caller can see and resolve the gap (Section
    6, "missing information is visible") instead of silently undercounting
    one party.
    """

    grouped: Dict[str, list] = {}
    for entity in entities:
        key = entity.national_party or "unknown"
        grouped.setdefault(key, []).append(entity)
    return {key: tuple(value) for key, value in grouped.items()}
