"""Stage 3: segmentation, classification, and atomic promise extraction.

Section 8, step 4 ("segment and classify claims") and Section 9.4 ("promise
certainty"). This is a deterministic, keyword-driven reference
implementation: a production system would apply real OCR, translation, and
a trained classifier. Here, the goal is to make the *data model and
guardrails* concrete and testable — in particular the requirement that an
illustrative example clause never becomes a third promise (AT-05), and
that classification never turns a diagnosis or aspiration into a
commitment.

Because this module does not perform real syntactic parsing, the extracted
``action_or_outcome`` and ``object_`` are both set to the same clause text.
A production extractor would decompose them separately; the simplification
is confined to this module and does not affect any downstream guardrail.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from ..models import (
    AtomicClaim,
    Promise,
    PromiseFindingCode,
    SCOREABLE_PROMISE_FINDING_CODES,
    SourceObject,
    StatementType,
    new_id,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_EXAMPLE_CLAUSE = re.compile(
    r",?\s*(?:for example|for instance|such as|e\.g\.)\b.*$",
    re.IGNORECASE,
)
_COORDINATION_SPLIT = re.compile(
    r",?\s+and\s+(?=will\b|shall\b|commits to\b|pledges to\b)",
    re.IGNORECASE,
)

_COMMITMENT_MARKERS = (
    r"\bwill\b",
    r"\bshall\b",
    r"\bcommits? to\b",
    r"\bpledges? to\b",
    r"\bguarantees?\b",
)
_PROPOSAL_MARKERS = (
    r"\bpropose(?:s|d)?\b",
    r"\bwill consider\b",
    r"\bconsiders?\b",
    r"\bexplores?\b",
    r"\blooks? into\b",
)
_GOAL_MARKERS = (
    r"\baims? to\b",
    r"\bhopes? to\b",
    r"\bwants? to\b",
    r"\bseeks? to\b",
    r"\bstrives? to\b",
)
_DIAGNOSIS_MARKERS = (
    r"\bthe problem is\b",
    r"\bwe believe\b",
    r"\bis broken\b",
    r"\bfaces? a crisis\b",
    r"\bis in crisis\b",
)
_VALUE_MARKERS = (
    r"\bwe value\b",
    r"\bit is wrong\b",
    r"\beveryone deserves\b",
)
_ATTACK_MARKERS = (
    r"\bfailed to\b",
    r"\bhas failed\b",
    r"\bbroke (?:its|their) promise\b",
)
_CONDITION_MARKERS = (
    r"\bif\b",
    r"\bprovided that\b",
    r"\bsubject to\b",
    r"\bconditional on\b",
)


def _matches_any(patterns: Sequence[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def segment_sentences(text: str) -> List[Tuple[str, int, int]]:
    """Split text into sentences, returning (sentence, start, end) offsets."""

    sentences: List[Tuple[str, int, int]] = []
    cursor = 0
    for raw in _SENTENCE_SPLIT.split(text.strip()):
        raw = raw.strip()
        if not raw:
            continue
        start = text.find(raw, cursor)
        if start == -1:
            start = cursor
        end = start + len(raw)
        cursor = end
        sentences.append((raw, start, end))
    return sentences


def classify_statement(clause: str) -> StatementType:
    """Rule-based statement-type classification (Section 8, step 4)."""

    stripped = clause.strip()
    if stripped.endswith("?"):
        return StatementType.QUESTION
    if _matches_any(_ATTACK_MARKERS, stripped):
        return StatementType.ATTACK
    if _matches_any(_COMMITMENT_MARKERS, stripped):
        return StatementType.COMMITMENT
    if _matches_any(_PROPOSAL_MARKERS, stripped):
        return StatementType.PROPOSAL
    if _matches_any(_GOAL_MARKERS, stripped):
        return StatementType.GOAL
    if _matches_any(_DIAGNOSIS_MARKERS, stripped):
        return StatementType.DIAGNOSIS
    if _matches_any(_VALUE_MARKERS, stripped):
        return StatementType.VALUE_STATEMENT
    if re.search(r"\b(is|are|was|were|has|have)\b", stripped, re.IGNORECASE):
        return StatementType.FACTUAL_ASSERTION
    return StatementType.OTHER


def extract_atomic_claims(source: SourceObject, text: str) -> List[AtomicClaim]:
    """Segment ``text`` into atomic claims.

    A trailing illustrative clause ("for example, ...", "such as ...") is
    stripped before classification and never produces its own claim
    (Section 8; AT-05). A sentence containing two independently modalised
    commitments joined by "and" is split into two claims.
    """

    claims: List[AtomicClaim] = []
    for sentence, sent_start, _sent_end in segment_sentences(text):
        example_match = _EXAMPLE_CLAUSE.search(sentence)
        core = sentence[: example_match.start()] if example_match else sentence

        clause_start = 0
        pieces: List[str] = []
        for match in _COORDINATION_SPLIT.finditer(core):
            pieces.append(core[clause_start:match.start()])
            clause_start = match.end()
        pieces.append(core[clause_start:])

        cursor = 0
        for piece in pieces:
            piece_stripped = piece.strip()
            if not piece_stripped:
                continue
            local_start = core.find(piece_stripped, cursor)
            if local_start == -1:
                local_start = cursor
            cursor = local_start + len(piece_stripped)

            statement_type = classify_statement(piece_stripped)
            condition = None
            if _matches_any(_CONDITION_MARKERS, piece_stripped):
                cond_match = re.search(
                    r"(if|provided that|subject to|conditional on)\b.*$",
                    piece_stripped,
                    re.IGNORECASE,
                )
                condition = cond_match.group(0) if cond_match else None

            claims.append(
                AtomicClaim(
                    claim_id=new_id("claim"),
                    source_id=source.source_id,
                    quote=piece_stripped,
                    offset_start=sent_start + local_start,
                    offset_end=sent_start + local_start + len(piece_stripped),
                    statement_type=statement_type,
                    modality=_modality_of(piece_stripped),
                    condition=condition,
                )
            )
    return claims


def _modality_of(clause: str) -> Optional[str]:
    for pattern in _COMMITMENT_MARKERS + _PROPOSAL_MARKERS + _GOAL_MARKERS:
        m = re.search(pattern, clause, re.IGNORECASE)
        if m:
            return m.group(0).lower()
    return None


_FINDING_CODE_BY_TYPE = {
    StatementType.GOAL: PromiseFindingCode.ASPIRATION_OR_GOAL,
    StatementType.DIAGNOSIS: PromiseFindingCode.DIAGNOSIS_OR_VALUE_STATEMENT,
    StatementType.VALUE_STATEMENT: PromiseFindingCode.DIAGNOSIS_OR_VALUE_STATEMENT,
    StatementType.FACTUAL_ASSERTION: PromiseFindingCode.NOT_A_PROMISE,
    StatementType.ATTACK: PromiseFindingCode.NOT_A_PROMISE,
    StatementType.QUESTION: PromiseFindingCode.NOT_A_PROMISE,
    StatementType.OTHER: PromiseFindingCode.NOT_A_PROMISE,
}

def resolve_promise(claim: AtomicClaim, entity_id: Optional[str], election_id: str, actor: Optional[str]) -> Promise:
    """Apply the minimum promise test and produce a :class:`Promise` record.

    A claim is retained as a labelled non-promise comparison item
    (``not_a_promise``) rather than discarded, and an unresolved actor
    always yields ``attribution_uncertain`` regardless of statement type,
    per Section 9.4.
    """

    if not actor or not entity_id:
        finding_code = PromiseFindingCode.ATTRIBUTION_UNCERTAIN
    elif claim.statement_type == StatementType.COMMITMENT:
        finding_code = (
            PromiseFindingCode.CONDITIONAL_COMMITMENT
            if claim.condition
            else PromiseFindingCode.EXPLICIT_COMMITMENT
        )
    elif claim.statement_type == StatementType.PROPOSAL:
        finding_code = PromiseFindingCode.PROPOSAL_FOR_CONSIDERATION
    else:
        finding_code = _FINDING_CODE_BY_TYPE.get(claim.statement_type, PromiseFindingCode.NOT_A_PROMISE)

    return Promise(
        promise_id=new_id("promise"),
        claim_ids=(claim.claim_id,),
        entity_id=entity_id or "unresolved",
        election_id=election_id,
        actor=actor or "unresolved",
        action_or_outcome=claim.quote,
        object_=claim.quote,
        finding_code=finding_code,
        canonical_description=claim.quote,
    )


def is_scoreable(promise: Promise) -> bool:
    return promise.finding_code in SCOREABLE_PROMISE_FINDING_CODES
