"""Stage 2a: election roster construction (Section 8, step 1; COL-001)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

from ..models import RosterDisposition, RosterItem


@dataclass(frozen=True)
class RosterCoverage:
    total: int
    by_disposition: Dict[str, int]

    def is_complete(self) -> bool:
        """Every eligible entity must receive one of the four dispositions."""

        return sum(self.by_disposition.values()) == self.total


def build_roster(election_id: str, entity_ids: Sequence[str], dispositions: Dict[str, RosterDisposition], reasons: Dict[str, str] | None = None) -> Sequence[RosterItem]:
    """Create one :class:`RosterItem` per eligible entity.

    Every entity in ``entity_ids`` must appear in ``dispositions``; the
    caller cannot silently drop an eligible party (Section 8, step 1 and
    outcome metric "eligible-party roster disposition").
    """

    reasons = reasons or {}
    missing = [eid for eid in entity_ids if eid not in dispositions]
    if missing:
        raise ValueError(f"missing roster disposition for entities: {missing}")

    return tuple(
        RosterItem(
            election_id=election_id,
            entity_id=eid,
            disposition=dispositions[eid],
            reason=reasons.get(eid),
        )
        for eid in entity_ids
    )


def coverage(roster: Sequence[RosterItem]) -> RosterCoverage:
    counts: Dict[str, int] = {}
    for item in roster:
        counts[item.disposition.value] = counts.get(item.disposition.value, 0) + 1
    return RosterCoverage(total=len(roster), by_disposition=counts)
