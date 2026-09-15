"""A real, cited first import of the 2026 U.S. midterm race universe.

Retrieved 2026-09-15, via the assistant's WebSearch tool only. WebFetch
(direct page retrieval) was blocked by this environment's network egress
policy for every domain tried, including Wikipedia, Ballotpedia, Cook
Political Report, and 270toWin — so every fact below comes from
WebSearch's synthesized snippets of those sources, not a direct fetch of
the primary page. That is a real limitation on how much can be trusted
here without a follow-up check:

- The 35-seat Senate universe (33 Class II regular elections plus special
  elections in Florida and Ohio) is corroborated across multiple
  independent search results and is high confidence.
- Only 8 of the 35 Senate races carry a cited competitiveness rating.
  Several other races were repeatedly mentioned as "competitive" in
  search results (e.g. Alaska) without a specific rating tier attached to
  any single snippet, so — consistent with this engine's own
  abstain-rather-than-invent rule — they are left with
  ``competitiveness_rating=None`` rather than guessed.
- The House data covers exactly one rating tier (Cook Political Report's
  18 toss-ups as of its June 18, 2026 print snapshot), not the full set
  of competitive House races. Cook also separately publishes Lean and
  Likely tiers not captured in this import.
- Of the 18 House races, 5 district numbers were independently confirmed
  by a targeted search this session (Ballotpedia/GovTrack/Congress.gov
  results): OH-09, IA-01, NE-02, ME-02, WA-03. The other 13 district
  numbers come from the assistant's pre-existing reference knowledge, not
  a source retrieved this session, and are flagged in ``notes``
  accordingly — verify against the House Clerk's roster or FEC candidate
  filings before relying on them.
- No candidate-level entity resolution (FEC filer IDs, challenger names)
  has been done. ``entity_ids`` is empty on every record here.
- Search results surfaced that at least two of the 18 toss-up incumbents
  (Jared Golden, ME-02; Don Bacon, NE-02) have announced they will not
  seek re-election in 2026, which makes those open-seat races rather than
  incumbent-defense races — noted per record.

Treat this module as a provisional, timestamped snapshot to refresh before
publication, not a maintained feed. A production system would replace it
with a live, scheduled import against FEC filings and a licensed or
publicly published rating feed, per README.md, "Scoping real elections."
"""

from __future__ import annotations

from ..scope import OfficeType, Race, Region

CYCLE = 2026
RETRIEVED = "2026-09-15"

_COOK_SENATE_CITATION = (
    "Cook Political Report, Senate Race Ratings, print snapshot dated Aug 20, 2026 "
    "(https://www.cookpolitical.com/print/ratings/races/senate; "
    "https://www.cookpolitical.com/ratings/senate-race-ratings), "
    f"retrieved via web search {RETRIEVED}"
)
_SABATO_SENATE_CITATION = (
    "Sabato's Crystal Ball, Center for Politics at the University of Virginia, "
    "ratings updated Aug 26, 2026 (https://centerforpolitics.org/crystalball/2026-senate/), "
    f"retrieved via web search {RETRIEVED}"
)
_COOK_HOUSE_CITATION = (
    "Cook Political Report, House Race Ratings, print snapshot dated Jun 18, 2026 "
    "(https://www.cookpolitical.com/print/ratings/races/house), toss-up tier as reported by "
    "The Hill, \"Cook Political Report unveils 18 toss-up House races for 2026\" "
    "(https://thehill.com/homenews/campaign/5130655-cook-political-report-democrats-republicans/), "
    f"retrieved via web search {RETRIEVED}"
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
    "IA": Region.MIDWEST, "KS": Region.MIDWEST, "KY": Region.SOUTH, "LA": Region.SOUTH,
    "ME": Region.NORTHEAST, "MA": Region.NORTHEAST, "MI": Region.MIDWEST, "MN": Region.MIDWEST,
    "MS": Region.SOUTH, "MT": Region.WEST, "NE": Region.MIDWEST, "NH": Region.NORTHEAST,
    "NJ": Region.NORTHEAST, "NM": Region.WEST, "NC": Region.SOUTH, "OK": Region.SOUTH,
    "OR": Region.WEST, "RI": Region.NORTHEAST, "SC": Region.SOUTH, "SD": Region.MIDWEST,
    "TN": Region.SOUTH, "TX": Region.SOUTH, "VA": Region.SOUTH, "WV": Region.SOUTH,
    "WY": Region.WEST, "FL": Region.SOUTH, "OH": Region.MIDWEST, "CA": Region.WEST,
    "NY": Region.NORTHEAST, "AZ": Region.WEST, "PA": Region.NORTHEAST, "WA": Region.WEST,
}

#: Cook Political Report ratings actually cited for a specific 2026 Senate
#: race in this session's search results.
_SENATE_COOK_RATINGS = {
    "IA": "toss_up",
    "TX": "toss_up",
    "ME": "toss_up",
    "GA": "toss_up",
    "MI": "toss_up",
    "MN": "likely_d",
    "NC": "lean_d",
    "NH": "lean_d",
}

#: All 33 states with a Class II Senate seat up in 2026, per corroborating
#: search results (Wikipedia/Ballotpedia-derived synthesis).
_SENATE_CLASS_II_STATES = (
    "AL", "AK", "AR", "CO", "DE", "GA", "ID", "IL", "IA", "KS", "KY", "LA", "ME", "MA",
    "MI", "MN", "MS", "MT", "NE", "NH", "NJ", "NM", "NC", "OK", "OR", "RI", "SC", "SD",
    "TN", "TX", "VA", "WV", "WY",
)

#: The two 2026 Senate special elections, per the same search results.
_SENATE_SPECIAL_STATES = ("FL", "OH")


def _build_senate_universe() -> tuple[Race, ...]:
    races = []
    for state in _SENATE_CLASS_II_STATES:
        rating = _SENATE_COOK_RATINGS.get(state)
        races.append(
            Race(
                race_id=f"sen-2026-{state.lower()}",
                office_type=OfficeType.US_SENATE,
                state=state,
                cycle=CYCLE,
                region=_STATE_REGION[state],
                competitiveness_rating=rating,
                competitiveness_source=_COOK_SENATE_CITATION if rating else None,
                notes=None if rating else "No specific rating tier found in this session's search results.",
            )
        )

    # Florida: special election, rated by Sabato's Crystal Ball (Safe R) in
    # this session's search results, not by the Cook citation above.
    races.append(
        Race(
            race_id="sen-2026-fl-special",
            office_type=OfficeType.US_SENATE,
            state="FL",
            cycle=CYCLE,
            region=_STATE_REGION["FL"],
            competitiveness_rating="safe_r",
            competitiveness_source=_SABATO_SENATE_CITATION,
            notes="Special election, not a Class II regular election.",
        )
    )
    # Ohio: special election; no specific rating tier surfaced this session.
    races.append(
        Race(
            race_id="sen-2026-oh-special",
            office_type=OfficeType.US_SENATE,
            state="OH",
            cycle=CYCLE,
            region=_STATE_REGION["OH"],
            competitiveness_rating=None,
            competitiveness_source=None,
            notes="Special election, not a Class II regular election. No rating tier found in this session's search results.",
        )
    )
    return tuple(races)


#: (state, district, incumbent_name, notes) for the 5 races whose district
#: number was independently confirmed by a targeted search this session.
_HOUSE_CONFIRMED = (
    ("OH", "09", "Marcy Kaptur (D)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved this session."),
    ("IA", "01", "Mariannette Miller-Meeks (R)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved this session."),
    ("NE", "02", "Don Bacon (R)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved this session. "
                                    "Search results indicate Bacon announced he will not seek re-election in 2026 — "
                                    "this is an open-seat race, not incumbent defense; verify current candidate roster."),
    ("ME", "02", "Jared Golden (D)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved this session. "
                                       "Search results indicate Golden announced he will not seek re-election in 2026 — "
                                       "this is an open-seat race, not incumbent defense; verify current candidate roster."),
    ("WA", "03", "Marie Gluesenkamp Perez (D)", "District confirmed via Ballotpedia/GovTrack/Congress.gov, retrieved this session."),
)

#: (state, district, incumbent_name) for the remaining 13 toss-ups, where
#: the district number is from the assistant's pre-existing reference
#: knowledge rather than a source retrieved this session (see
#: _UNVERIFIED_DISTRICT_NOTE).
_HOUSE_UNVERIFIED_DISTRICT = (
    ("CA", "13", "Adam Gray (D)"),
    ("CA", "45", "Derek Tran (D)"),
    ("NM", "02", "Gabe Vasquez (D)"),
    ("NY", "04", "Laura Gillen (D)"),
    ("NC", "01", "Don Davis (D)"),
    ("OH", "13", "Emilia Sykes (D)"),
    ("TX", "34", "Vicente Gonzalez (D)"),
    ("AZ", "01", "David Schweikert (R)"),
    ("AZ", "06", "Juan Ciscomani (R)"),
    ("CO", "08", "Gabe Evans (R)"),
    ("MI", "07", "Tom Barrett (R)"),
    ("PA", "07", "Ryan Mackenzie (R)"),
    ("PA", "10", "Scott Perry (R)"),
)


def _build_house_tossups() -> tuple[Race, ...]:
    races = []
    for state, district, incumbent, note in _HOUSE_CONFIRMED:
        races.append(
            Race(
                race_id=f"house-2026-{state.lower()}-{district}",
                office_type=OfficeType.US_HOUSE,
                state=state,
                cycle=CYCLE,
                district=district,
                region=_STATE_REGION[state],
                competitiveness_rating="toss_up",
                competitiveness_source=_COOK_HOUSE_CITATION,
                notes=f"Incumbent per search results: {incumbent}. {note}",
            )
        )
    for state, district, incumbent in _HOUSE_UNVERIFIED_DISTRICT:
        races.append(
            Race(
                race_id=f"house-2026-{state.lower()}-{district}",
                office_type=OfficeType.US_HOUSE,
                state=state,
                cycle=CYCLE,
                district=district,
                region=_STATE_REGION[state],
                competitiveness_rating="toss_up",
                competitiveness_source=_COOK_HOUSE_CITATION,
                notes=f"Incumbent per search results: {incumbent}. {_UNVERIFIED_DISTRICT_NOTE}",
            )
        )
    return tuple(races)


#: All 35 Senate races up in the 2026 cycle (33 Class II + 2 special).
SENATE_UNIVERSE_2026: tuple[Race, ...] = _build_senate_universe()

#: The 18 House races Cook Political Report rated Toss Up as of its
#: June 18, 2026 snapshot. Not the full set of competitive House races.
HOUSE_TOSSUPS_2026: tuple[Race, ...] = _build_house_tossups()
