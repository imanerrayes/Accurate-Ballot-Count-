"""Shared helpers for dimension modules."""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from ...models import DimensionName, DimensionResult, EvidenceState


def make_result(
    dimension: DimensionName,
    finding_code: str,
    evidence_state: EvidenceState,
    plain_language_finding: str,
    conditions: Sequence[str] = (),
    missing_information: Sequence[str] = (),
    blocking_gates: Sequence[str] = (),
    sources: Sequence[str] = (),
    assumptions: Sequence[str] = (),
    review_state: str = "unreviewed",
    rule_set_version: Optional[str] = None,
    metrics: Optional[Mapping[str, float]] = None,
) -> DimensionResult:
    return DimensionResult(
        dimension=dimension,
        finding_code=finding_code,
        evidence_state=evidence_state,
        plain_language_finding=plain_language_finding,
        conditions=tuple(conditions),
        missing_information=tuple(missing_information),
        blocking_gates=tuple(blocking_gates),
        sources=tuple(sources),
        assumptions=tuple(assumptions),
        review_state=review_state,
        rule_set_version=rule_set_version,
        metrics=dict(metrics or {}),
    )
