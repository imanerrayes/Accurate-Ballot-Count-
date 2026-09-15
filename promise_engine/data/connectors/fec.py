"""Connector for the FEC's public openFEC API (api.open.fec.gov).

This is real, working code against a documented, free, public API — not a
stub. It could not be executed from inside this Claude Code session: a
direct connectivity test (``curl https://api.open.fec.gov/...``) returned
a 403 from this environment's egress proxy, meaning ``api.open.fec.gov``
is not on this session's allowed destination list. That is a network
policy fact about this session, not a defect in the code below. Run it:

- from your own machine or notebook, or
- from a Claude Code session/environment whose egress policy allows
  ``api.open.fec.gov``,

and hand the resulting :class:`PoliticalEntity` tuple (or a CSV/JSON dump
of it) back for ``import_tools`` to merge in, or call it directly if your
environment can reach the API.

Get a free key at https://api.data.gov/signup/. ``DEMO_KEY`` also works
for light testing at a much lower rate limit (30/hour, 120/day per the
FEC's published limits at the time this was written — confirm current
limits at https://api.open.fec.gov/developers/ before relying on it).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ...models import PoliticalEntity, new_id

FEC_CANDIDATES_ENDPOINT = "https://api.open.fec.gov/v1/candidates/"

#: FEC party codes (https://api.open.fec.gov/developers/, /v1/candidates/)
#: mapped to the readable strings PoliticalEntity.national_party expects
#: elsewhere in this engine. An unmapped code is passed through verbatim
#: rather than dropped, so an unusual filing (a minor party, "UNK") is
#: still visible instead of silently lost.
FEC_PARTY_MAP = {
    "DEM": "Democratic",
    "REP": "Republican",
    "IND": "Independent",
    "LIB": "Libertarian",
    "GRE": "Green",
    "CON": "Constitution",
}


def _parse_candidate(record: Dict[str, Any]) -> PoliticalEntity:
    """Pure transform from one openFEC candidate record to a PoliticalEntity.

    Kept separate from the network call so it can be unit tested with a
    fixed sample record, without needing live network access.
    """

    party_code = (record.get("party") or "").upper()
    candidate_id = record.get("candidate_id") or new_id("fec-unknown")
    return PoliticalEntity(
        entity_id=f"fec-{candidate_id}",
        name=(record.get("name") or "").strip(),
        jurisdiction=record.get("state") or "",
        official_id=candidate_id,
        national_party=FEC_PARTY_MAP.get(party_code, party_code or None),
    )


def fetch_candidates(
    office: str,
    cycle: int,
    state: Optional[str] = None,
    district: Optional[str] = None,
    api_key: str = "DEMO_KEY",
    max_pages: int = 10,
    timeout_seconds: int = 30,
) -> List[PoliticalEntity]:
    """Fetch registered candidates from openFEC's ``/v1/candidates/`` endpoint.

    ``office``: ``"S"`` (Senate), ``"H"`` (House), or ``"P"`` (President),
    per the FEC API's own vocabulary — not this engine's ``OfficeType``.
    ``cycle``: a two-year election cycle, e.g. ``2026``.
    Raises whatever ``urllib.error.URLError``/``HTTPError`` the request
    raises; this function does not swallow network or API errors.
    """

    entities: List[PoliticalEntity] = []
    page = 1
    while page <= max_pages:
        params = {
            "api_key": api_key,
            "office": office,
            "election_year": cycle,
            "per_page": 100,
            "page": page,
            "sort": "name",
        }
        if state:
            params["state"] = state
        if district:
            params["district"] = district

        url = f"{FEC_CANDIDATES_ENDPOINT}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        entities.extend(_parse_candidate(record) for record in payload.get("results", []))

        pagination = payload.get("pagination", {})
        total_pages = pagination.get("pages", 1)
        if page >= total_pages:
            break
        page += 1

    return entities
