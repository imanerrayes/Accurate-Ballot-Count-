"""Dimension 2: legal authority (Section 9.5).

Distinguishes what the elected actor can actually do, component by
component, using the jurisdiction profile's rule matrix. A conflict
between two rules of equal priority never resolves silently: it returns
``indeterminate`` and requires review (Section 7.3).
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from ...jurisdiction import profile_gate
from ...models import (
    AuthorityCode,
    DimensionName,
    ElectionType,
    EvidenceState,
    JurisdictionProfile,
    LegalRule,
)
from .base import make_result

_CONDITIONS_BY_CODE = {
    AuthorityCode.DIRECT_AUTHORITY: (),
    AuthorityCode.SHARED_OR_CONCURRENT: ("concurrence of another institution or level of government",),
    AuthorityCode.DELEGATED: ("exercise of a delegated power that may be withdrawn or conditioned",),
    AuthorityCode.EXECUTIVE_DISCRETION: ("discretionary act; may be reversed by a successor",),
    AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY: ("passage by the legislature", "assent or promulgation"),
    AuthorityCode.ADVOCACY_OR_NEGOTIATION_ONLY: ("agreement or cooperation by another actor with independent authority",),
    AuthorityCode.AUTHORITY_HELD_ELSEWHERE: ("authority rests with a different office or level of government",),
    AuthorityCode.LEGALLY_PROHIBITED: (),
    AuthorityCode.INDETERMINATE: (),
}

# States where the underlying fact ("who holds authority") is itself
# established, even though delivery is far from guaranteed.
_ESTABLISHED_CODES = frozenset(
    {AuthorityCode.DIRECT_AUTHORITY, AuthorityCode.LEGALLY_PROHIBITED, AuthorityCode.AUTHORITY_HELD_ELSEWHERE}
)
_CONDITIONAL_CODES = frozenset(
    {
        AuthorityCode.SHARED_OR_CONCURRENT,
        AuthorityCode.DELEGATED,
        AuthorityCode.EXECUTIVE_DISCRETION,
        AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
        AuthorityCode.ADVOCACY_OR_NEGOTIATION_ONLY,
    }
)

#: Weights used only for the optional, fully disclosed Authority Coverage
#: Ratio (Section 9.5). Initiative and advocacy are excluded: they do not
#: count as direct delivery authority.
AUTHORITY_COVERAGE_WEIGHTS = {
    AuthorityCode.DIRECT_AUTHORITY: 1.0,
    AuthorityCode.SHARED_OR_CONCURRENT: 0.5,
    AuthorityCode.DELEGATED: 0.5,
    AuthorityCode.EXECUTIVE_DISCRETION: 0.5,
}


def authority_coverage_ratio(component_codes: Sequence[AuthorityCode]) -> Optional[float]:
    """Disclosed weighted share of components with delivery authority.

    Returns ``None`` (not zero) when there are no components to evaluate,
    since a ratio over an empty set is not a finding.
    """

    if not component_codes:
        return None
    total = sum(AUTHORITY_COVERAGE_WEIGHTS.get(code, 0.0) for code in component_codes)
    return total / len(component_codes)


def assess(
    election_type: ElectionType,
    actor_type: str,
    instrument_type: str,
    profile: Optional[JurisdictionProfile],
    as_of: date,
    rule_set_version: Optional[str] = None,
):
    block = profile_gate(profile, election_type, as_of)
    if block is not None:
        return make_result(
            dimension=DimensionName.LEGAL_AUTHORITY,
            finding_code=block.reason,
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding="No effective jurisdiction profile covers this election and instrument.",
            missing_information=block.missing,
            rule_set_version=rule_set_version,
        )

    assert profile is not None  # profile_gate returned None => profile is present
    matches: Sequence[LegalRule] = [
        r
        for r in profile.legal_rules
        if r.election_type == election_type
        and r.actor_type == actor_type
        and r.instrument_type == instrument_type
    ]

    if not matches:
        return make_result(
            dimension=DimensionName.LEGAL_AUTHORITY,
            finding_code=AuthorityCode.INDETERMINATE.value,
            evidence_state=EvidenceState.UNKNOWN_OR_DISPUTED,
            plain_language_finding=(
                "No rule in the jurisdiction profile addresses this actor and "
                "instrument combination. A qualified reviewer must classify it."
            ),
            missing_information=("legal_rule",),
            rule_set_version=profile.version,
        )

    top_priority = max(r.priority for r in matches)
    top = [r for r in matches if r.priority == top_priority]

    if len(top) > 1:
        return make_result(
            dimension=DimensionName.LEGAL_AUTHORITY,
            finding_code=AuthorityCode.INDETERMINATE.value,
            evidence_state=EvidenceState.UNKNOWN_OR_DISPUTED,
            plain_language_finding=(
                "Two rules of equal priority conflict for this actor and "
                "instrument. The module abstains rather than selecting one "
                "implicitly; a review task is required."
            ),
            sources=tuple(r.source for r in top),
            rule_set_version=profile.version,
        )

    rule = top[0]
    code = rule.result_code

    if code in _ESTABLISHED_CODES:
        evidence_state = EvidenceState.ESTABLISHED
    elif code in _CONDITIONAL_CODES:
        evidence_state = EvidenceState.SUPPORTED_BUT_CONDITIONAL
    else:  # INDETERMINATE
        evidence_state = EvidenceState.UNKNOWN_OR_DISPUTED

    return make_result(
        dimension=DimensionName.LEGAL_AUTHORITY,
        finding_code=code.value,
        evidence_state=evidence_state,
        plain_language_finding=_plain_language(code),
        conditions=_CONDITIONS_BY_CODE.get(code, ()),
        sources=(rule.source,),
        review_state=rule.reviewer or "unreviewed",
        rule_set_version=profile.version,
    )


def _plain_language(code: AuthorityCode) -> str:
    return {
        AuthorityCode.DIRECT_AUTHORITY: "The actor holds direct authority to act on this component.",
        AuthorityCode.SHARED_OR_CONCURRENT: "Authority over this component is shared or concurrent with another actor.",
        AuthorityCode.DELEGATED: "This is a delegated power, not an original authority.",
        AuthorityCode.EXECUTIVE_DISCRETION: "This component may be exercised at executive discretion.",
        AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY: "The actor may introduce the measure, but enactment requires additional institutions.",
        AuthorityCode.ADVOCACY_OR_NEGOTIATION_ONLY: "The actor may advocate or negotiate but does not control the outcome.",
        AuthorityCode.AUTHORITY_HELD_ELSEWHERE: "Authority over this component is held by a different office or level of government.",
        AuthorityCode.LEGALLY_PROHIBITED: "The cited rule prohibits this instrument for this actor.",
        AuthorityCode.INDETERMINATE: "Authority could not be determined from the cited rule.",
    }[code]
