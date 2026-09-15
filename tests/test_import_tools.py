import csv

import pytest

from promise_engine.data.import_tools import (
    load_fec_candidates_csv,
    load_house_ratings_csv,
    load_senate_ratings_csv,
    merge_ratings_into_universe,
    normalize_rating_label,
)
from promise_engine.scope import OfficeType, Race


def _write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Toss Up", "toss_up"),
        ("toss-up", "toss_up"),
        ("Lean Democrat", "lean_d"),
        ("Leans Republican", "lean_r"),
        ("Safe Republican", "safe_r"),
        ("Solid D", "solid_d"),
        ("  likely republican  ", "likely_r"),
    ],
)
def test_normalize_rating_label(raw, expected):
    assert normalize_rating_label(raw) == expected


def test_normalize_rating_label_rejects_unknown_label():
    with pytest.raises(ValueError, match="Unrecognized rating label"):
        normalize_rating_label("Probably Fine I Guess")


def test_load_senate_ratings_csv(tmp_path):
    path = tmp_path / "senate.csv"
    _write_csv(
        path,
        [
            {
                "state": "ia",
                "rating": "Toss Up",
                "source_name": "Cook Political Report",
                "source_url": "https://example.org/senate",
                "as_of_date": "2026-08-20",
                "notes": "",
            },
            {"state": "wy", "rating": "", "source_name": "", "source_url": "", "as_of_date": "", "notes": ""},
        ],
        fieldnames=["state", "rating", "source_name", "source_url", "as_of_date", "notes"],
    )
    races = load_senate_ratings_csv(path, cycle=2026)
    assert len(races) == 2

    iowa = next(r for r in races if r.state == "IA")
    assert iowa.office_type == OfficeType.US_SENATE
    assert iowa.competitiveness_rating == "toss_up"
    assert "Cook Political Report" in iowa.competitiveness_source
    assert "2026-08-20" in iowa.competitiveness_source
    assert iowa.race_id == "sen-2026-ia"

    wyoming = next(r for r in races if r.state == "WY")
    assert wyoming.competitiveness_rating is None
    assert wyoming.competitiveness_source is None


def test_load_house_ratings_csv_pads_district_and_records_incumbent(tmp_path):
    path = tmp_path / "house.csv"
    _write_csv(
        path,
        [
            {
                "state": "oh",
                "district": "9",
                "rating": "Toss Up",
                "source_name": "Cook Political Report",
                "source_url": "https://example.org/house",
                "as_of_date": "2026-06-18",
                "incumbent_name": "Marcy Kaptur",
                "incumbent_party": "D",
                "notes": "",
            }
        ],
        fieldnames=[
            "state", "district", "rating", "source_name", "source_url",
            "as_of_date", "incumbent_name", "incumbent_party", "notes",
        ],
    )
    races = load_house_ratings_csv(path, cycle=2026)
    assert len(races) == 1
    race = races[0]
    assert race.district == "09"
    assert race.race_id == "house-2026-oh-09"
    assert "Marcy Kaptur" in race.notes
    assert "(D)" in race.notes


def test_load_fec_candidates_csv(tmp_path):
    path = tmp_path / "candidates.csv"
    _write_csv(
        path,
        [{"fec_candidate_id": "S6IA00123", "name": "Jane Q. Candidate", "party": "DEM", "state": "IA", "national_party": "Democratic"}],
        fieldnames=["fec_candidate_id", "name", "party", "state", "national_party"],
    )
    entities = load_fec_candidates_csv(path)
    assert len(entities) == 1
    assert entities[0].entity_id == "fec-S6IA00123"
    assert entities[0].national_party == "Democratic"
    assert entities[0].official_id == "S6IA00123"


def test_merge_ratings_into_universe_preserves_untouched_fields_and_appends_new():
    from promise_engine.scope import Region

    existing = (
        Race(
            race_id="sen-2026-ia", office_type=OfficeType.US_SENATE, state="IA", cycle=2026,
            region=Region.MIDWEST, competitiveness_rating=None, topics=("agriculture",),
        ),
        Race(race_id="sen-2026-wy", office_type=OfficeType.US_SENATE, state="WY", cycle=2026, region=Region.WEST),
    )
    updates = (
        Race(
            race_id="sen-2026-ia-updated", office_type=OfficeType.US_SENATE, state="IA", cycle=2026,
            competitiveness_rating="toss_up", competitiveness_source="Cook, 2026-08-20",
        ),
        Race(race_id="sen-2026-fl-special", office_type=OfficeType.US_SENATE, state="FL", cycle=2026, competitiveness_rating="safe_r", competitiveness_source="Sabato's, 2026-08-26"),
    )
    merged = merge_ratings_into_universe(existing, updates)
    assert len(merged) == 3  # IA updated in place, WY untouched, FL appended

    iowa = next(r for r in merged if r.state == "IA")
    assert iowa.competitiveness_rating == "toss_up"
    assert iowa.region == Region.MIDWEST  # preserved from the existing record
    assert iowa.topics == ("agriculture",)  # preserved from the existing record

    wyoming = next(r for r in merged if r.state == "WY")
    assert wyoming.competitiveness_rating is None  # untouched

    florida = next(r for r in merged if r.state == "FL")
    assert florida.competitiveness_rating == "safe_r"
