"""The 2026 U.S. midterm race universe, built from two extraction batches.

Batch 1 (2026-09-15, in-session): the assistant's own WebSearch-sourced
partial import — 9 of 35 Senate races and 18 House Toss Up races, used
here as the base skeleton (it supplies each race's Census region, which
neither extraction batch's CSV carries as a column).

Batch 2 (2026-09-15, manual extraction — see
``data/extracted/2026-09-15/PROVENANCE.md``): the repository owner's own
extraction from Cook Political Report's Senate ratings (Aug 20, 2026
snapshot, filling in the 26 races batch 1 left unrated) and House ratings
(Sep 11, 2026 snapshot, 70 races across five tiers, superseding batch 1's
18-race Toss-Up-only subset), plus a 674-row FEC Senate candidate export
(see ``entities_2026.py`` — not merged into ``Race.entity_ids`` here; see
that module for why).

Combined, Senate coverage is now complete: all 35 races (33 Class II
regular elections plus the Florida and Ohio specials) carry a cited
Cook Political Report or Sabato's Crystal Ball rating. House coverage is
70 races — real, but still a fraction of 435 seats, and only as current
as the Sep 11, 2026 snapshot it was pulled from.

Treat this module as a timestamped snapshot, not a maintained feed:
ratings and candidacies change continuously between now and the November
2026 election. A new manual extraction or API pull should land in a new
dated ``data/extracted/<date>/`` batch and be merged in here, never by
editing a prior batch's files in place.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from .import_tools import load_house_ratings_csv, load_senate_ratings_csv, merge_ratings_into_universe
from ..scope import OfficeType, Race, Region

CYCLE = 2026

_EXTRACTED_DIR = Path(__file__).parent / "extracted" / "2026-09-15"

_COOK_SENATE_CITATION = (
    "Cook Political Report, Senate Race Ratings, print snapshot dated Aug 20, 2026 "
    "(https://www.cookpolitical.com/print/ratings/races/senate), "
    "retrieved via web search 2026-09-15"
)
_SABATO_SENATE_CITATION = (
    "Sabato's Crystal Ball, Center for Politics at the University of Virginia, "
    "ratings updated Aug 26, 2026 (https://centerforpolitics.org/crystalball/2026-senate/), "
    "retrieved via web search 2026-09-15"
)
_COOK_HOUSE_CITATION = (
    "Cook Political Report, House Race Ratings, print snapshot dated Jun 18, 2026 "
    "(https://www.cookpolitical.com/print/ratings/races/house), toss-up tier as reported by "
    "The Hill, \"Cook Political Report unveils 18 toss-up House races for 2026\" "
    "(https://thehill.com/homenews/campaign/5130655-cook-political-report-democrats-republicans/), "
    "retrieved via web search 2026-09-15"
)

_UNVERIFIED_DISTRICT_NOTE = (
    "District number from the assistant's pre-existing reference knowledge, not confirmed "
    "via a source retrieved this session; verify against the House Clerk's roster or FEC "
    "candidate filings before use."
)

#: USPS state code -> US Census Bureau statistical region. Fixed geography,
#: not a political judgment (see promise_engine.scope.Region).
_STATE_REGION = {
    "AL": Region.SOUTH, "AK": Region.WEST, "AR": Region.SOUTH, "CO": Region.WEST,
    "DE": Region.SOUTH, "GA": Region.SOUTH, "ID": Region.WEST, "IL": Region.MIDWEST,
    "IA": Region.MIDWEST, "IN": Region.MIDWEST, "KS": Region.MIDWEST, "KY": Region.SOUTH,
    "LA": Region.SOUTH, "ME": Region.NORTHEAST, "MA": Region.NORTHEAST, "MI": Region.MIDWEST,
    "MN": Region.MIDWEST, "MO": Region.MIDWEST, "MS": Region.SOUTH, "MT": Region.WEST,
    "NE": Region.MIDWEST, "NH": Region.NORTHEAST, "NJ": Region.NORTHEAST, "NM": Region.WEST,
    "NC": Region.SOUTH, "NV": Region.WEST, "OK": Region.SOUTH, "OR": Region.WEST,
    "RI": Region.NORTHEAST, "SC": Region.SOUTH, "SD": Region.MIDWEST, "TN": Region.SOUTH,
    "TX": Region.SOUTH, "VA": Region.SOUTH, "WV": Region.SOUTH, "WY": Region.WEST,
    "FL": Region.SOUTH, "OH": Region.MIDWEST, "CA": Region.WEST, "NY": Region.NORTHEAST,
    "AZ": Region.WEST, "PA": Region.NORTHEAST, "WA": Region.WEST, "WI": Region.MIDWEST,
}

#: Cook Political Report ratings the assistant's own WebSearch-based import
#: (batch 1) found cited for a specific 2026 Senate race, before the
#: manual extraction (batch 2) filled in the rest.
_SEED_SENATE_COOK_RATINGS = {
    "IA": "toss_up", "TX": "toss_up", "ME": "toss_up", "GA": "toss_up", "MI": "toss_up",
    "MN": "likely_d", "NC": "lean_d", "NH": "lean_d",
}

#: All 33 states with a Class II Senate seat up in 2026.
_SENATE_CLASS_II_STATES = (
    "AL", "AK", "AR", "CO", "DE", "GA", "ID", "IL", "IA", "KS", "KY", "LA", "ME", "MA",
    "MI", "MN", "MS", "MT", "NE", "NH", "NJ", "NM", "NC", "OK", "OR", "RI", "SC", "SD",
    "TN", "TX", "VA", "WV", "WY",
)


def _build_senate_seed() -> tuple[Race, ...]:
    """Batch 1: the 35-race skeleton with regions assigned, and whatever
    ratings batch 1 already had cited."""

    races = []
    for state in _SENATE_CLASS_II_STATES:
        rating = _SEED_SENATE_COOK_RATINGS.get(state)
        races.append(
            Race(
                race_id=f"sen-{CYCLE}-{state.lower()}",
                office_type=OfficeType.US_SENATE,
                state=state,
                cycle=CYCLE,
                region=_STATE_REGION[state],
                competitiveness_rating=rating,
                competitiveness_source=_COOK_SENATE_CITATION if rating else None,
            )
        )
    races.append(
        Race(
            race_id="sen-2026-fl-special", office_type=OfficeType.US_SENATE, state="FL", cycle=CYCLE,
            region=_STATE_REGION["FL"], competitiveness_rating="safe_r",
            competitiveness_source=_SABATO_SENATE_CITATION,
            notes="Special election, not a Class II regular election.",
        )
    )
    races.append(
        Race(
            race_id="sen-2026-oh-special", office_type=OfficeType.US_SENATE, state="OH", cycle=CYCLE,
            region=_STATE_REGION["OH"], notes="Special election, not a Class II regular election.",
        )
    )
    return tuple(races)


#: (state, district, incumbent_name, notes) confirmed by a targeted search
#: in batch 1.
_HOUSE_SEED_CONFIRMED = (
    ("OH", "09", "Marcy Kaptur (D)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved batch 1."),
    ("IA", "01", "Mariannette Miller-Meeks (R)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved batch 1."),
    ("NE", "02", "Don Bacon (R)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved batch 1."),
    ("ME", "02", "Jared Golden (D)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved batch 1."),
    ("WA", "03", "Marie Gluesenkamp Perez (D)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved batch 1."),
)
_HOUSE_SEED_UNVERIFIED = (
    ("CA", "13", "Adam Gray (D)"), ("CA", "45", "Derek Tran (D)"), ("NM", "02", "Gabe Vasquez (D)"),
    ("NY", "04", "Laura Gillen (D)"), ("NC", "01", "Don Davis (D)"), ("OH", "13", "Emilia Sykes (D)"),
    ("TX", "34", "Vicente Gonzalez (D)"), ("AZ", "01", "David Schweikert (R)"), ("AZ", "06", "Juan Ciscomani (R)"),
    ("CO", "08", "Gabe Evans (R)"), ("MI", "07", "Tom Barrett (R)"), ("PA", "07", "Ryan Mackenzie (R)"),
    ("PA", "10", "Scott Perry (R)"),
)


def _build_house_seed() -> tuple[Race, ...]:
    """Batch 1: 18 Toss Up races. Every one of these is superseded (some
    with an updated rating) by batch 2's 70-race extraction, but the seed
    still supplies the region field batch 2's CSV loader doesn't set."""

    races = []
    for state, district, incumbent, note in _HOUSE_SEED_CONFIRMED:
        races.append(
            Race(
                race_id=f"house-{CYCLE}-{state.lower()}-{district}", office_type=OfficeType.US_HOUSE,
                state=state, cycle=CYCLE, district=district, region=_STATE_REGION[state],
                competitiveness_rating="toss_up", competitiveness_source=_COOK_HOUSE_CITATION,
                notes=f"Incumbent per batch-1 search results: {incumbent}. {note}",
            )
        )
    for state, district, incumbent in _HOUSE_SEED_UNVERIFIED:
        races.append(
            Race(
                race_id=f"house-{CYCLE}-{state.lower()}-{district}", office_type=OfficeType.US_HOUSE,
                state=state, cycle=CYCLE, district=district, region=_STATE_REGION[state],
                competitiveness_rating="toss_up", competitiveness_source=_COOK_HOUSE_CITATION,
                notes=f"Incumbent per batch-1 search results: {incumbent}. {_UNVERIFIED_DISTRICT_NOTE}",
            )
        )
    return tuple(races)


def _ensure_region(races: tuple[Race, ...]) -> tuple[Race, ...]:
    """Fill in region for any race batch 2 added that the seed didn't have
    (import_tools' CSV loaders don't set region — it isn't a CSV column)."""

    return tuple(
        r if r.region is not None else dataclasses.replace(r, region=_STATE_REGION.get(r.state))
        for r in races
    )


_senate_seed = _build_senate_seed()
_house_seed = _build_house_seed()

_senate_updates = load_senate_ratings_csv(_EXTRACTED_DIR / "senate_ratings.csv", cycle=CYCLE)
_house_updates = load_house_ratings_csv(_EXTRACTED_DIR / "house_ratings.csv", cycle=CYCLE)

#: All 35 Senate races up in the 2026 cycle. Every race now carries a
#: cited rating: 33 Class II races plus the Florida and Ohio specials.
SENATE_UNIVERSE_2026: tuple[Race, ...] = _ensure_region(
    merge_ratings_into_universe(_senate_seed, _senate_updates)
)

#: 70 House races across five Cook Political Report tiers (Likely
#: Democrat, Lean Democrat, Toss Up, Lean Republican, Likely Republican)
#: as of the Sep 11, 2026 snapshot. Not the full set of competitive House
#: races, and nowhere near all 435 seats.
HOUSE_RATED_RACES_2026: tuple[Race, ...] = _ensure_region(
    merge_ratings_into_universe(_house_seed, _house_updates)
)

#: Retained for backward compatibility with code written against the
#: narrower batch-1 name; identical to HOUSE_RATED_RACES_2026.
HOUSE_TOSSUPS_2026 = HOUSE_RATED_RACES_2026
