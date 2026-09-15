"""Source-agnostic ingestion for race and candidate data.

This module does not care whether a row came from a human copying a table
off Cook Political Report, a CSV exported from a spreadsheet, or JSON
returned by an API connector (``promise_engine.data.connectors``): every
loader here normalizes into the same :class:`~promise_engine.scope.Race`
or :class:`~promise_engine.models.PoliticalEntity` records the rest of the
engine already uses. That is the point — one ingestion path regardless of
where the data physically came from.

Rating labels are normalized and validated against a known vocabulary
(:func:`normalize_rating_label`) rather than accepted as free text, so a
typo or an unrecognised label fails loudly at import time instead of
silently becoming an uncited or mis-scoped rating.
"""

from __future__ import annotations

import csv
import dataclasses
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple, Union

from ..models import PoliticalEntity
from ..scope import OfficeType, Race

PathLike = Union[str, Path]

# ---------------------------------------------------------------------------
# Rating label normalization
# ---------------------------------------------------------------------------

#: Human-readable labels (as Cook Political Report, Sabato's Crystal Ball,
#: and Inside Elections each phrase them) mapped to the fixed internal
#: vocabulary promise_engine.scope.Race.is_competitive understands.
#: Add an alias here rather than guessing at parse time.
_RATING_ALIASES: Dict[str, str] = {
    "solid democrat": "solid_d", "solid democratic": "solid_d", "solid d": "solid_d",
    "safe democrat": "safe_d", "safe democratic": "safe_d", "safe d": "safe_d",
    "likely democrat": "likely_d", "likely democratic": "likely_d", "likely d": "likely_d",
    "lean democrat": "lean_d", "lean democratic": "lean_d", "leans democratic": "lean_d", "lean d": "lean_d",
    "toss up": "toss_up", "toss-up": "toss_up", "tossup": "toss_up",
    "tilt democratic": "toss_up", "tilt republican": "toss_up",
    "lean republican": "lean_r", "leans republican": "lean_r", "lean r": "lean_r",
    "likely republican": "likely_r", "likely r": "likely_r",
    "solid republican": "solid_r", "solid r": "solid_r",
    "safe republican": "safe_r", "safe r": "safe_r",
}


def normalize_rating_label(raw: str) -> str:
    """Map a rater's own wording to the internal rating vocabulary.

    Raises ``ValueError`` on anything not in the known alias table, rather
    than guessing — an unrecognised label almost always means either a
    transcription error or a rater phrasing this module hasn't seen yet,
    and either way it should stop the import, not silently produce an
    uncategorised rating.
    """

    key = raw.strip().lower()
    if key not in _RATING_ALIASES:
        raise ValueError(
            f"Unrecognized rating label {raw!r}. Known labels: {sorted(set(_RATING_ALIASES))}. "
            "Add an alias to import_tools._RATING_ALIASES if this is a legitimate rater phrasing."
        )
    return _RATING_ALIASES[key]


def _read_rows(path: PathLike) -> Iterable[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("state", "").strip().startswith("#"):
                continue  # allow comment rows in a hand-edited template
            yield {k: (v or "").strip() for k, v in row.items()}


def _citation(row: Dict[str, str]) -> Optional[str]:
    source_name = row.get("source_name", "")
    source_url = row.get("source_url", "")
    as_of_date = row.get("as_of_date", "")
    if not source_name:
        return None
    parts = [source_name]
    if as_of_date:
        parts.append(f"as of {as_of_date}")
    citation = ", ".join(parts)
    if source_url:
        citation += f" ({source_url})"
    return citation


# ---------------------------------------------------------------------------
# Senate and House ratings CSV loaders
# ---------------------------------------------------------------------------


def load_senate_ratings_csv(path: PathLike, cycle: int) -> Tuple[Race, ...]:
    """Load Senate ratings from a CSV with columns:

    ``state, rating, source_name, source_url, as_of_date, notes`` (notes optional).
    ``race_id`` is auto-generated as ``sen-<cycle>-<state>``; add a
    ``race_id`` column to override it (needed for a special election, e.g.
    ``sen-2026-fl-special``).
    """

    races = []
    for row in _read_rows(path):
        state = row["state"].upper()
        rating = normalize_rating_label(row["rating"]) if row.get("rating") else None
        races.append(
            Race(
                race_id=row.get("race_id") or f"sen-{cycle}-{state.lower()}",
                office_type=OfficeType.US_SENATE,
                state=state,
                cycle=cycle,
                competitiveness_rating=rating,
                competitiveness_source=_citation(row) if rating else None,
                notes=row.get("notes") or None,
            )
        )
    return tuple(races)


def load_house_ratings_csv(path: PathLike, cycle: int) -> Tuple[Race, ...]:
    """Load House ratings from a CSV with columns:

    ``state, district, rating, source_name, source_url, as_of_date,
    incumbent_name, incumbent_party, notes`` (incumbent_* and notes optional).
    ``district`` should be a zero-padded two-digit string (e.g. ``"09"``).
    """

    races = []
    for row in _read_rows(path):
        state = row["state"].upper()
        district = row["district"].zfill(2)
        rating = normalize_rating_label(row["rating"]) if row.get("rating") else None
        incumbent = row.get("incumbent_name")
        notes_parts = []
        if incumbent:
            party = row.get("incumbent_party", "")
            notes_parts.append(f"Incumbent: {incumbent}" + (f" ({party})" if party else ""))
        if row.get("notes"):
            notes_parts.append(row["notes"])
        races.append(
            Race(
                race_id=row.get("race_id") or f"house-{cycle}-{state.lower()}-{district}",
                office_type=OfficeType.US_HOUSE,
                state=state,
                cycle=cycle,
                district=district,
                competitiveness_rating=rating,
                competitiveness_source=_citation(row) if rating else None,
                notes="; ".join(notes_parts) or None,
            )
        )
    return tuple(races)


def load_fec_candidates_csv(path: PathLike) -> Tuple[PoliticalEntity, ...]:
    """Load candidate entities from a CSV with columns:

    ``fec_candidate_id, name, party, state, national_party`` (national_party
    optional; falls back to ``party`` verbatim if not given a normalized
    value).
    """

    entities = []
    for row in _read_rows(path):
        entities.append(
            PoliticalEntity(
                entity_id=f"fec-{row['fec_candidate_id']}",
                name=row["name"],
                jurisdiction=row.get("state", ""),
                official_id=row["fec_candidate_id"],
                national_party=row.get("national_party") or row.get("party") or None,
            )
        )
    return tuple(entities)


# ---------------------------------------------------------------------------
# Merging a fresh extraction into an existing universe
# ---------------------------------------------------------------------------


def _race_key(race: Race) -> Tuple:
    return (race.office_type, race.state, race.district, race.cycle)


def merge_ratings_into_universe(universe: Sequence[Race], updates: Sequence[Race]) -> Tuple[Race, ...]:
    """Apply fresh ratings on top of an existing race universe.

    For a race already in ``universe``, only ``competitiveness_rating``,
    ``competitiveness_source``, and ``notes`` are overwritten — every other
    field (region, entity_ids, topics) is preserved from the existing
    record. A race in ``updates`` with no match in ``universe`` is appended
    as a new record, so this also covers extending House coverage past
    whatever subset was previously imported.
    """

    by_key = {_race_key(r): r for r in universe}
    for update in updates:
        key = _race_key(update)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = update
        else:
            by_key[key] = dataclasses.replace(
                existing,
                competitiveness_rating=update.competitiveness_rating,
                competitiveness_source=update.competitiveness_source,
                notes=update.notes or existing.notes,
            )
    return tuple(by_key.values())
