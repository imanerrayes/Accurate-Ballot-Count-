"""Jurisdiction profile gating and hard preconditions (Sections 7.1, 9.3).

Legal, fiscal, political-dependency, and historical-comparability modules
must refuse to run rather than guess when their prerequisites are not met.
This module centralises that gate so every dimension module applies it the
same way (Section 6, "missing information is visible").
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from .models import (
    AtomicClaim,
    ElectionType,
    JurisdictionProfile,
    Promise,
    PublicationBlock,
    SCOREABLE_PROMISE_FINDING_CODES,
    SourceObject,
)


def profile_gate(
    profile: Optional[JurisdictionProfile],
    election_type: ElectionType,
    as_of: date,
) -> Optional[PublicationBlock]:
    """Return a :class:`PublicationBlock` if the profile cannot be used.

    Returns ``None`` when the profile is present, current, and compatible
    with the requested election type — i.e. the module is clear to run.
    """

    if profile is None:
        return PublicationBlock(
            reason="jurisdiction_profile_missing",
            missing=("jurisdiction_profile",),
        )
    if not profile.is_effective(as_of):
        return PublicationBlock(
            reason="jurisdiction_profile_expired",
            missing=(f"effective_profile_for:{as_of.isoformat()}",),
        )
    if not profile.supports_election_type(election_type):
        return PublicationBlock(
            reason="jurisdiction_profile_incompatible_election_type",
            missing=(f"election_type:{election_type.value}",),
        )
    return None


def check_hard_preconditions(
    promise: Promise,
    claims: Sequence[AtomicClaim],
    sources: Sequence[Optional[SourceObject]],
    profile: Optional[JurisdictionProfile],
    election_type: ElectionType,
    as_of: date,
    rule_set_version: Optional[str],
) -> Optional[PublicationBlock]:
    """Verify the Section 9.3 preconditions before any FRV is computed.

    Failure returns a named block rather than a zero or an empty dimension
    set, matching the requirement that "failure of a precondition returns a
    named publication block. It does not return zero."
    """

    missing = []

    if not claims:
        missing.append("linked_atomic_claim")
    for source in sources:
        if source is None:
            missing.append("source_object")
        elif not source.payload_available:
            missing.append(f"source_payload:{source.source_id}")

    if promise.finding_code not in SCOREABLE_PROMISE_FINDING_CODES:
        return PublicationBlock(
            reason="not_a_scoreable_promise",
            missing=("minimum_promise_test",),
        )

    profile_block = profile_gate(profile, election_type, as_of)
    if profile_block is not None:
        return profile_block

    if rule_set_version is None:
        missing.append("frozen_rule_set_version")

    if missing:
        return PublicationBlock(reason="precondition_evidence_missing", missing=tuple(missing))

    return None


# ---------------------------------------------------------------------------
# Fixture conformance (Section 7.3)
# ---------------------------------------------------------------------------

REQUIRED_FIXTURE_ELECTION_TYPES = frozenset(
    {
        ElectionType.PARLIAMENTARY_GENERAL,  # majority, minority, coalition, opposition
        ElectionType.PRESIDENTIAL,
        ElectionType.LEGISLATIVE_SEAT,
        ElectionType.REGIONAL_OR_PROVINCIAL,
        ElectionType.MUNICIPAL,
        ElectionType.SUPRANATIONAL,
        ElectionType.DIRECTLY_ELECTED_EXECUTIVE,
        ElectionType.REFERENDUM,
    }
)


def missing_fixture_coverage(profile: JurisdictionProfile) -> Sequence[ElectionType]:
    """Election contexts the profile does not yet declare fixtures for.

    A profile "may be published only after its conformance fixtures pass"
    (Section 7.3). This helper reports the gap so a profile draft can be
    completed before publication; it does not itself publish anything.
    """

    return tuple(sorted(
        (et for et in REQUIRED_FIXTURE_ELECTION_TYPES if et not in profile.election_types),
        key=lambda e: e.value,
    ))
