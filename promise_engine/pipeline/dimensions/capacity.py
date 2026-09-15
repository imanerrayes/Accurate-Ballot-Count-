"""Dimension 4: implementation capacity (Section 9.7).

Reports evidence coverage over the readiness checklist, not a judgment
that an institution lacks capacity: absence of public evidence is
explicitly not proof of incapacity.
"""

from __future__ import annotations

from typing import Mapping, Optional

from ...models import CAPACITY_CHECKLIST_ITEMS, DimensionName, EvidenceState, ProvenanceType
from .base import make_result


def assess(
    readiness_evidence: Mapping[str, ProvenanceType],
    rule_set_version: Optional[str] = None,
):
    """``readiness_evidence`` maps a subset of :data:`CAPACITY_CHECKLIST_ITEMS`
    to a :class:`ProvenanceType`. Items absent from the mapping are treated
    as unknown, not as evidence of missing capacity."""

    applicable = [
        item for item in CAPACITY_CHECKLIST_ITEMS
        if readiness_evidence.get(item, ProvenanceType.UNKNOWN) != ProvenanceType.NOT_APPLICABLE
    ]
    if not applicable:
        return make_result(
            dimension=DimensionName.IMPLEMENTATION_CAPACITY,
            finding_code="no_applicable_readiness_items",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding="No readiness items apply to this promise.",
            rule_set_version=rule_set_version,
        )

    evidenced = [
        item
        for item in applicable
        if readiness_evidence.get(item) in (ProvenanceType.STATED, ProvenanceType.AUTHORITATIVE_EXTERNAL)
    ]
    unknown = [item for item in applicable if item not in readiness_evidence]
    coverage = len(evidenced) / len(applicable)

    risk_register = tuple(
        f"unmitigated_risk:{item}" for item in applicable if item not in evidenced
    )

    if coverage >= 1.0:
        evidence_state = EvidenceState.ESTABLISHED
    elif coverage > 0.0:
        evidence_state = EvidenceState.PARTIALLY_SPECIFIED
    else:
        evidence_state = EvidenceState.UNKNOWN_OR_DISPUTED

    return make_result(
        dimension=DimensionName.IMPLEMENTATION_CAPACITY,
        finding_code="capacity_evidence_coverage_computed",
        evidence_state=evidence_state,
        plain_language_finding=(
            f"{len(evidenced)} of {len(applicable)} applicable readiness items have direct "
            "evidence. Missing public evidence for the remaining items is not proof of incapacity."
        ),
        missing_information=tuple(unknown),
        blocking_gates=risk_register,
        rule_set_version=rule_set_version,
        metrics={"capacity_evidence_coverage": coverage},
    )
