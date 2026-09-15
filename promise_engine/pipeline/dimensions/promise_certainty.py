"""Dimension 1: promise certainty (Section 9.4).

A specification test, not an intent assessment: the module reports how
completely the promise is parametrised, never whether the speaker is
sincere.
"""

from __future__ import annotations

from typing import Optional

from ...models import (
    DimensionName,
    EvidenceState,
    PolicySpecification,
    Promise,
    ProvenanceType,
    SPECIFICATION_FIELDS,
)
from ..extraction import is_scoreable
from .base import make_result


def assess(promise: Promise, spec: Optional[PolicySpecification], rule_set_version: Optional[str] = None):
    if not is_scoreable(promise):
        return make_result(
            dimension=DimensionName.PROMISE_CERTAINTY,
            finding_code=promise.finding_code.value,
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding=(
                "This statement does not meet the minimum promise test "
                "(verifiable actor, commitment modality, action or outcome, "
                "and object) and is retained only as a labelled non-promise "
                "comparison item."
            ),
            rule_set_version=rule_set_version,
        )

    if spec is None:
        return make_result(
            dimension=DimensionName.PROMISE_CERTAINTY,
            finding_code=promise.finding_code.value,
            evidence_state=EvidenceState.UNKNOWN_OR_DISPUTED,
            plain_language_finding="No policy specification has been built for this promise yet.",
            missing_information=("policy_specification",),
            rule_set_version=rule_set_version,
        )

    stated = spec.stated_coverage()
    supported = spec.supported_coverage()
    missing = [
        f
        for f in SPECIFICATION_FIELDS
        if f not in spec.fields or spec.fields[f].provenance == ProvenanceType.UNKNOWN
    ]
    assumptions = [
        f for f, fv in spec.fields.items() if fv.provenance == ProvenanceType.ANALYST_ASSUMPTION
    ]

    if supported >= 1.0:
        evidence_state = EvidenceState.ESTABLISHED
    elif supported >= 0.5:
        evidence_state = EvidenceState.SUPPORTED_BUT_CONDITIONAL
    elif supported > 0.0:
        evidence_state = EvidenceState.PARTIALLY_SPECIFIED
    else:
        evidence_state = EvidenceState.UNKNOWN_OR_DISPUTED

    return make_result(
        dimension=DimensionName.PROMISE_CERTAINTY,
        finding_code=promise.finding_code.value,
        evidence_state=evidence_state,
        plain_language_finding=(
            f"{stated:.0%} of applicable parameters are stated in the primary "
            f"source and {supported:.0%} are stated or evidenced overall."
        ),
        missing_information=tuple(missing),
        assumptions=tuple(assumptions),
        rule_set_version=rule_set_version,
        metrics={"stated_coverage": stated, "supported_coverage": supported},
    )
