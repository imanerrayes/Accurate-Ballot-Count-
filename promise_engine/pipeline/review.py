"""Stage 7: human review, publication, appeal, and correction (Section 8, 11.2).

Publication requires every mandatory gate to pass; a result blocked by a
hard precondition is never published. Corrections never mutate a published
result in place: they create a new, superseding :class:`AssessmentResult`
and a scoped recomputation diff naming exactly what changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from ..evidence_store import EvidenceStore
from ..models import AppealCase, AssessmentResult, new_id


def can_publish(result: AssessmentResult) -> bool:
    """A result may publish only if it carries no publication block."""

    return result.is_published


def file_appeal(store: EvidenceStore, record_reference: str, claimant_type: str, issue: str) -> AppealCase:
    appeal = AppealCase(
        case_id=new_id("appeal"),
        record_reference=record_reference,
        claimant_type=claimant_type,
        issue=issue,
    )
    store.appeals.put(appeal.case_id, appeal)
    return appeal


def decide_appeal(store: EvidenceStore, case_id: str, decision: str, correction_links: Sequence[str] = ()) -> AppealCase:
    prior = store.appeals.get_latest(case_id)
    if prior is None:
        raise ValueError(f"unknown appeal case: {case_id}")
    decided = AppealCase(
        case_id=prior.case_id,
        record_reference=prior.record_reference,
        claimant_type=prior.claimant_type,
        issue=prior.issue,
        status="decided",
        decision=decision,
        correction_links=tuple(correction_links),
    )
    store.appeals.put(case_id, decided)
    return decided


@dataclass(frozen=True)
class RecomputationDiff:
    """Names every output field affected by a correction (Section 15.1)."""

    prior_result_id: str
    new_result_id: str
    changed_dimensions: Tuple[str, ...]
    changed_metrics: Tuple[str, ...]


def diff_results(prior: AssessmentResult, updated: AssessmentResult) -> RecomputationDiff:
    prior_by_dim = {r.dimension.value: r for r in prior.dimension_results}
    updated_by_dim = {r.dimension.value: r for r in updated.dimension_results}

    changed_dimensions = []
    changed_metrics = []
    for dim in sorted(set(prior_by_dim) | set(updated_by_dim)):
        before = prior_by_dim.get(dim)
        after = updated_by_dim.get(dim)
        if before is None or after is None or before.result_hash != after.result_hash:
            if before is None or after is None or (
                before.finding_code,
                before.evidence_state,
                before.metrics,
            ) != (after.finding_code, after.evidence_state, after.metrics):
                changed_dimensions.append(dim)
                if before is not None and after is not None:
                    for metric in sorted(set(before.metrics) | set(after.metrics)):
                        if before.metrics.get(metric) != after.metrics.get(metric):
                            changed_metrics.append(f"{dim}.{metric}")

    return RecomputationDiff(
        prior_result_id=prior.result_id,
        new_result_id=updated.result_id,
        changed_dimensions=tuple(changed_dimensions),
        changed_metrics=tuple(changed_metrics),
    )
