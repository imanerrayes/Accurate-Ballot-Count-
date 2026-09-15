"""Dimension 7: evidence quality (Section 9.10).

Reports the evidence attributes behind an assessment; it never becomes a
single averaged confidence number. Multiple weak sources cannot compensate
for a missing controlling source: any mandatory field that is absent blocks
a "verified" label, however many optional fields are present.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ...models import AtomicClaim, DimensionName, EvidenceState, SourceObject
from .base import make_result

_MANDATORY_FOR_VERIFIED = (
    "payload_available",
    "content_hash",
    "exact_anchor",
    "retrieval_date",
    "source_tier",
)


def assess(
    source: Optional[SourceObject],
    claim: Optional[AtomicClaim],
    review_state: str = "unreviewed",
    conflicting_sources: Sequence[str] = (),
    rule_set_version: Optional[str] = None,
):
    if source is None or claim is None:
        return make_result(
            dimension=DimensionName.EVIDENCE_QUALITY,
            finding_code="evidence_profile_incomplete",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding="No source object and atomic claim are both linked to this promise.",
            missing_information=("source_object", "atomic_claim"),
            rule_set_version=rule_set_version,
        )

    attributes = {
        "payload_available": source.payload_available,
        "content_hash": bool(source.content_hash),
        "exact_anchor": claim.offset_start != claim.offset_end,
        "retrieval_date": source.retrieval_date is not None,
        "source_tier": source.source_tier is not None,
        "review_state": review_state not in ("unreviewed", ""),
    }
    missing = [k for k in _MANDATORY_FOR_VERIFIED if not attributes.get(k)]

    if conflicting_sources:
        evidence_state = EvidenceState.UNKNOWN_OR_DISPUTED
        finding_code = "conflicting_sources"
    elif not missing:
        evidence_state = EvidenceState.ESTABLISHED
        finding_code = "verified"
    else:
        evidence_state = EvidenceState.PARTIALLY_SPECIFIED
        finding_code = "provenance_incomplete"

    return make_result(
        dimension=DimensionName.EVIDENCE_QUALITY,
        finding_code=finding_code,
        evidence_state=evidence_state,
        plain_language_finding=(
            "This dimension reports confidence in the assessment evidence, not the "
            "promise's quality or the party's integrity."
        ),
        missing_information=tuple(missing),
        sources=(source.source_id, *conflicting_sources),
        review_state=review_state,
        rule_set_version=rule_set_version,
        metrics={"mandatory_provenance_completeness": 1.0 - (len(missing) / len(_MANDATORY_FOR_VERIFIED))},
    )
