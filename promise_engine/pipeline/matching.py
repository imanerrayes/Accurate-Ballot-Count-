"""Stage 4b: comparison matching (Section 10, CMP-001 through CMP-006).

Candidate retrieval is scoped first (jurisdiction, election, topic) and
ranked by a naive lexical-similarity score. The similarity score is only
ever a *retrieval aid*: no relationship becomes "comparable" without an
explicit reviewer confirmation (CMP-002, CMP-003).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Sequence

from ..models import Promise


class RelationshipType(str, Enum):
    EQUIVALENT = "equivalent_instrument_and_scope"
    SAME_OBJECTIVE_DIFFERENT_INSTRUMENT = "same_objective_different_instrument"
    OVERLAPPING = "overlapping"
    BROADER_OR_NARROWER = "broader_or_narrower"
    CONFLICTING = "conflicting"
    NOT_COMPARABLE = "not_comparable"


_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set:
    return set(_TOKEN.findall(text.lower()))


def lexical_similarity(a: str, b: str) -> float:
    """Jaccard token overlap. A stand-in for a multilingual embedding model
    (Section 10; CMP-002 permits either, but forbids treating the score
    alone as a confirmed relationship)."""

    tokens_a, tokens_b = _tokens(a), _tokens(b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


@dataclass(frozen=True)
class CandidateMatch:
    promise: Promise
    similarity: float


def candidate_matches(
    promise: Promise,
    corpus: Sequence[Promise],
    election_id: str,
    min_similarity: float = 0.2,
) -> List[CandidateMatch]:
    """Retrieve in-scope candidates ranked by similarity (CMP-001).

    Scope is restricted to the same election before similarity is
    calculated at all, and the source promise is never matched against
    itself.
    """

    candidates = [
        CandidateMatch(promise=other, similarity=lexical_similarity(promise.canonical_description, other.canonical_description))
        for other in corpus
        if other.promise_id != promise.promise_id and other.election_id == election_id
    ]
    ranked = [c for c in candidates if c.similarity >= min_similarity]
    ranked.sort(key=lambda c: c.similarity, reverse=True)
    return ranked


@dataclass(frozen=True)
class ConfirmedRelationship:
    promise_a: str
    promise_b: str
    relationship: RelationshipType
    reviewer: str


def confirm_relationship(
    promise_a: Promise,
    promise_b: Promise,
    relationship: RelationshipType,
    reviewer: str,
) -> ConfirmedRelationship:
    """Record a reviewer's confirmed relationship between two promises.

    A relationship type may not be assigned automatically: CMP-003 requires
    a named reviewer for every confirmation, including "not comparable".
    """

    if not reviewer:
        raise ValueError("a comparison relationship requires a named reviewer (CMP-003)")
    return ConfirmedRelationship(
        promise_a=promise_a.promise_id,
        promise_b=promise_b.promise_id,
        relationship=relationship,
        reviewer=reviewer,
    )
