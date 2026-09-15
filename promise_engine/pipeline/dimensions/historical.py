"""Dimension 8: historically comparable outcomes (Section 9.11).

Returns a stratified distribution over rule-based historical records, with
every status class — including ``indeterminate`` — retained and visible.
Abstains rather than displaying a distribution built on too small a
comparable sample.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ...models import DimensionName, EvidenceState, HistoricalOutcomeRecord, HistoricalOutcomeStatus
from .base import make_result

MIN_COMPARABLE_SAMPLE = 5


def assess(
    jurisdiction: str,
    corpus: Sequence[HistoricalOutcomeRecord],
    government_status: Optional[str] = None,
    coalition_form: Optional[str] = None,
    topic: Optional[str] = None,
    min_sample: int = MIN_COMPARABLE_SAMPLE,
    rule_set_version: Optional[str] = None,
):
    # Retrieval hierarchy level 1: same jurisdiction, government status,
    # coalition form, and topic (Section 9.11).
    level_1 = [
        r
        for r in corpus
        if r.jurisdiction == jurisdiction
        and (government_status is None or r.government_status == government_status)
        and (coalition_form is None or r.coalition_form == coalition_form)
        and (topic is None or r.topic == topic)
    ]
    # Retrieval hierarchy level 2: relax topic and coalition form.
    level_2 = [
        r
        for r in corpus
        if r.jurisdiction == jurisdiction and (government_status is None or r.government_status == government_status)
    ]

    if len(level_1) >= min_sample:
        sample, hierarchy_level = level_1, 1
    elif len(level_2) >= min_sample:
        sample, hierarchy_level = level_2, 2
    else:
        return make_result(
            dimension=DimensionName.HISTORICAL_OUTCOMES,
            finding_code="insufficient_comparable_sample",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding=(
                f"The remaining comparable sample ({len(level_2)} records) is below the "
                f"predeclared minimum of {min_sample}. The module abstains."
            ),
            missing_information=("comparable_sample",),
            rule_set_version=rule_set_version,
        )

    counts = {status: 0 for status in HistoricalOutcomeStatus}
    for record in sample:
        counts[record.status] += 1

    return make_result(
        dimension=DimensionName.HISTORICAL_OUTCOMES,
        finding_code="descriptive_base_rate",
        evidence_state=EvidenceState.SUPPORTED_BUT_CONDITIONAL,
        plain_language_finding=(
            f"Among {len(sample)} comparable historical records (hierarchy level {hierarchy_level}), "
            "outcome counts are shown below by status, including indeterminate. This describes "
            "comparable past records; it is not a prediction for this promise."
        ),
        rule_set_version=rule_set_version,
        metrics={
            "sample_size": float(len(sample)),
            "hierarchy_level": float(hierarchy_level),
            **{f"count_{status.value}": float(n) for status, n in counts.items()},
        },
    )
