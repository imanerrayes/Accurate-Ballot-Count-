"""The eight Feasibility Readiness Vector dimensions (Section 9).

Each module exposes one ``assess(...)`` function returning a single
:class:`promise_engine.models.DimensionResult`. Dimensions are independent:
:mod:`promise_engine.pipeline.orchestrator` runs each one on its own and
never sums, averages, or otherwise nets them into a composite score
(Section 9.12, Section 6).
"""

from . import (
    capacity,
    evidence_quality,
    fiscal,
    historical,
    legal_authority,
    political_dependency,
    promise_certainty,
    timeline,
)

__all__ = [
    "promise_certainty",
    "legal_authority",
    "fiscal",
    "capacity",
    "political_dependency",
    "timeline",
    "evidence_quality",
    "historical",
]
