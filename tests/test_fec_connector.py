"""Tests for the openFEC connector's parsing logic.

``fetch_candidates`` itself makes a live HTTP call and cannot be tested
without network access, so these tests exercise ``_parse_candidate``
directly with a realistic sample record, and mock ``urlopen`` to check
``fetch_candidates`` builds the request and pagination loop correctly.
"""

import json
from io import BytesIO
from unittest.mock import patch

from promise_engine.data.connectors.fec import FEC_PARTY_MAP, _parse_candidate, fetch_candidates


def test_parse_candidate_maps_known_party_code():
    record = {
        "candidate_id": "S6IA00123",
        "name": "CANDIDATE, JANE Q",
        "party": "DEM",
        "state": "IA",
    }
    entity = _parse_candidate(record)
    assert entity.entity_id == "fec-S6IA00123"
    assert entity.official_id == "S6IA00123"
    assert entity.jurisdiction == "IA"
    assert entity.national_party == "Democratic"


def test_parse_candidate_passes_through_unmapped_party_code():
    record = {"candidate_id": "H8NY00456", "name": "SOMEONE, X", "party": "UNK", "state": "NY"}
    entity = _parse_candidate(record)
    assert entity.national_party == "UNK"


def test_parse_candidate_handles_missing_fields_without_raising():
    entity = _parse_candidate({})
    assert entity.name == ""
    assert entity.jurisdiction == ""
    assert entity.national_party is None


def test_all_fec_party_map_values_are_readable_strings():
    assert FEC_PARTY_MAP["REP"] == "Republican"
    assert all(isinstance(v, str) and v for v in FEC_PARTY_MAP.values())


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_candidates_single_page():
    page = {
        "results": [
            {"candidate_id": "S6IA00123", "name": "A", "party": "DEM", "state": "IA"},
            {"candidate_id": "S6IA00456", "name": "B", "party": "REP", "state": "IA"},
        ],
        "pagination": {"pages": 1},
    }
    with patch("promise_engine.data.connectors.fec.urllib.request.urlopen", return_value=_FakeResponse(page)) as mock_open:
        entities = fetch_candidates(office="S", cycle=2026, state="IA")

    assert len(entities) == 2
    assert {e.national_party for e in entities} == {"Democratic", "Republican"}
    called_url = mock_open.call_args[0][0]
    assert "office=S" in called_url
    assert "election_year=2026" in called_url
    assert "state=IA" in called_url


def test_fetch_candidates_follows_pagination():
    page_1 = {"results": [{"candidate_id": "1", "name": "A", "party": "DEM", "state": "IA"}], "pagination": {"pages": 2}}
    page_2 = {"results": [{"candidate_id": "2", "name": "B", "party": "REP", "state": "IA"}], "pagination": {"pages": 2}}
    with patch(
        "promise_engine.data.connectors.fec.urllib.request.urlopen",
        side_effect=[_FakeResponse(page_1), _FakeResponse(page_2)],
    ):
        entities = fetch_candidates(office="S", cycle=2026, state="IA")

    assert len(entities) == 2
    assert {e.official_id for e in entities} == {"1", "2"}
