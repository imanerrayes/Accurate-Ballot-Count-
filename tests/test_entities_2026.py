"""Tests for the FEC Senate candidate import (promise_engine.data.entities_2026).

These check that known data-quality issues in the raw FEC export are
caught, not that the roster is a complete or currently-accurate candidate
list (see the module's docstring on the missing election_year column).
"""

from promise_engine.data.entities_2026 import (
    RAW_SENATE_CANDIDATES_2026,
    candidates_by_state,
    clean_senate_candidates,
    detect_multi_state_filers,
)


def test_raw_import_has_several_hundred_candidates():
    # A sanity bound, not an exact count this module should hardcode:
    # re-extracting the same source should land in the same ballpark.
    assert 500 < len(RAW_SENATE_CANDIDATES_2026) < 800


def test_detects_the_known_multi_state_nuisance_filers():
    flagged = detect_multi_state_filers(RAW_SENATE_CANDIDATES_2026)
    assert "SOLOMON, GAVIN" in flagged
    assert len(flagged["SOLOMON, GAVIN"]) >= 20
    assert "CARLSON, OWEN NICHOLAS" in flagged
    assert len(flagged["CARLSON, OWEN NICHOLAS"]) >= 10


def test_detect_multi_state_filers_respects_threshold():
    # A very high threshold should catch nobody; a very low one should
    # catch far more than just the two known patterns.
    assert detect_multi_state_filers(RAW_SENATE_CANDIDATES_2026, min_states=100) == {}
    assert len(detect_multi_state_filers(RAW_SENATE_CANDIDATES_2026, min_states=2)) > 2


def test_clean_senate_candidates_excludes_flagged_names_only():
    cleaned = clean_senate_candidates(RAW_SENATE_CANDIDATES_2026)
    cleaned_names = {c.name.strip().upper() for c in cleaned}
    assert "SOLOMON, GAVIN" not in cleaned_names
    assert "CARLSON, OWEN NICHOLAS" not in cleaned_names
    # A real, singly-filed candidate must not be collaterally removed.
    assert "ERNST, JONI K" in cleaned_names
    # Cleaning only removes rows, never invents or alters remaining ones.
    assert len(cleaned) < len(RAW_SENATE_CANDIDATES_2026)
    assert set(cleaned) <= set(RAW_SENATE_CANDIDATES_2026)


def test_candidates_by_state_filters_correctly():
    iowa_candidates = candidates_by_state("IA")
    assert len(iowa_candidates) > 0
    assert all(c.jurisdiction == "IA" for c in iowa_candidates)
    # Case-insensitive on the query, not on stored data.
    assert candidates_by_state("ia") == iowa_candidates


def test_fec_entity_ids_and_official_ids_round_trip():
    sample = RAW_SENATE_CANDIDATES_2026[0]
    assert sample.entity_id == f"fec-{sample.official_id}"
