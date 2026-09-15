"""FEC Senate candidate filings for the 2026 cycle.

Source: ``data/extracted/2026-09-15/fec_senate_candidates.csv``, the
repository owner's manual export from
https://www.fec.gov/data/candidates/?election_year=2026&office=S — 674
rows, as filed. Two real limitations shape everything in this module:

1. **The export has no per-row election-year/cycle column.** FEC
   candidate IDs are permanent once assigned and stay on record across
   every cycle a person has ever filed in; nothing in this CSV format
   distinguishes "registered for the 2026 Senate race in this state" from
   "registered for a Senate race in this state at some point in FEC
   history and still on file." So ``RAW_SENATE_CANDIDATES_2026`` and
   ``candidates_by_state`` below answer "who has an FEC Senate filing on
   record for this state," not "who is on the 2026 ballot" — that
   narrower claim needs either the FEC API's ``election_year`` filter
   (``promise_engine.data.connectors.fec.fetch_candidates``) or a
   per-candidate check against https://www.fec.gov/data/candidate/<id>/.

2. **The export contains at least two multi-state nuisance-filer
   patterns.** "SOLOMON, GAVIN" appears as a Republican Senate filer in
   roughly 60 different states and territories; "CARLSON, OWEN NICHOLAS"
   appears in about 15, under a different party label in nearly every
   one. Real candidates do not simultaneously run for a single state's
   Senate seat in dozens of states — this is a well-documented FEC
   pattern of a person filing paperwork nationwide, not 60 real
   candidacies. ``detect_multi_state_filers`` flags any name appearing in
   more states than a threshold, and ``clean_senate_candidates`` excludes
   them rather than silently treating them as legitimate per-state
   entries (Section 6: "missing information is visible" — the same
   principle applies to information that is present but not credible).

Neither of these is merged into ``races_2026.Race.entity_ids`` here. Doing
that responsibly needs the cycle confirmation in point 1 first.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Sequence, Tuple

from ..models import PoliticalEntity
from .import_tools import load_fec_candidates_csv

_EXTRACTED_DIR = Path(__file__).parent / "extracted" / "2026-09-15"

#: Every row of the FEC export, unfiltered — duplicates, historical
#: carryover registrations, and nuisance-filer patterns all included.
RAW_SENATE_CANDIDATES_2026: Tuple[PoliticalEntity, ...] = load_fec_candidates_csv(
    _EXTRACTED_DIR / "fec_senate_candidates.csv"
)

#: Names occurring so rarely that a same-name mismatch is more likely a
#: coincidence than a data problem, versus a multi-state filer whose name
#: appears across an implausible number of separate state Senate races.
DEFAULT_MULTI_STATE_THRESHOLD = 4


def detect_multi_state_filers(
    entities: Sequence[PoliticalEntity], min_states: int = DEFAULT_MULTI_STATE_THRESHOLD
) -> Dict[str, Tuple[str, ...]]:
    """Flag names filed for Senate in an implausible number of states.

    Returns a mapping of normalized name to the sorted tuple of distinct
    states that name appears under, for every name at or above
    ``min_states`` — the same normalization ``clean_senate_candidates``
    uses to exclude them.
    """

    states_by_name: Dict[str, set] = defaultdict(set)
    for entity in entities:
        states_by_name[entity.name.strip().upper()].add(entity.jurisdiction)

    return {
        name: tuple(sorted(states))
        for name, states in states_by_name.items()
        if len(states) >= min_states
    }


def clean_senate_candidates(
    entities: Sequence[PoliticalEntity] = RAW_SENATE_CANDIDATES_2026,
    min_states: int = DEFAULT_MULTI_STATE_THRESHOLD,
) -> Tuple[PoliticalEntity, ...]:
    """All candidates except those matching a detected multi-state pattern.

    This still is not "confirmed 2026 candidates" (see limitation 1 in the
    module docstring) — it only removes entries this data itself makes
    implausible, rather than adding a confirmation the source doesn't
    provide.
    """

    flagged_names = set(detect_multi_state_filers(entities, min_states=min_states))
    return tuple(e for e in entities if e.name.strip().upper() not in flagged_names)


def candidates_by_state(state: str, entities: Sequence[PoliticalEntity] = RAW_SENATE_CANDIDATES_2026) -> Tuple[PoliticalEntity, ...]:
    """All recorded Senate filers for one state, from the raw (unfiltered) export."""

    return tuple(e for e in entities if e.jurisdiction == state.upper())
