"""Tests for the cited U.S. Congress jurisdiction profile.

These check that the profile's rules match the constitutional and
procedural provisions cited in its docstring — not that any political
outcome is likely.
"""

from datetime import date

from promise_engine.jurisdictions.us_congress import (
    FEDERAL_BUDGET_RECONCILIATION,
    FEDERAL_CONSTITUTIONAL_AMENDMENT,
    FEDERAL_LEGISLATION,
    FEDERAL_REGULATORY_DIRECTIVE,
    FEDERAL_TAX_OR_SPENDING,
    REPRESENTATIVE,
    SENATOR,
    build_us_congress_profile,
)
from promise_engine.models import AuthorityCode, ElectionType, EvidenceState
from promise_engine.pipeline.dimensions import legal_authority

AS_OF = date(2026, 9, 15)


def _profile():
    return build_us_congress_profile(119, effective_from=date(2025, 1, 3), effective_to=date(2027, 1, 3))


def test_profile_is_effective_during_the_2026_cycle():
    profile = _profile()
    assert profile.is_effective(AS_OF)
    assert profile.supports_election_type(ElectionType.LEGISLATIVE_SEAT)


def test_ordinary_legislation_requires_full_bicameral_and_presentment_gates():
    profile = _profile()
    gates = profile.gates_for_instrument(FEDERAL_LEGISLATION)
    assert "senate_cloture" in gates
    assert "presidential_signature_or_veto_override" in gates


def test_reconciliation_has_no_senate_cloture_gate():
    """Reconciliation bills are not subject to the Senate filibuster
    (Congressional Budget Act of 1974); ordinary legislation is."""

    profile = _profile()
    reconciliation_gates = profile.gates_for_instrument(FEDERAL_BUDGET_RECONCILIATION)
    legislation_gates = profile.gates_for_instrument(FEDERAL_LEGISLATION)
    assert "senate_cloture" not in reconciliation_gates
    assert "senate_cloture" in legislation_gates
    assert "senate_passage_simple_majority" in reconciliation_gates


def test_senator_cannot_originate_a_revenue_bill():
    """Origination Clause (art. I, § 7, cl. 1): revenue measures must
    originate in the House. A Senator's role is advocacy/negotiation on a
    House-originated bill, not initiation."""

    profile = _profile()
    result = legal_authority.assess(
        ElectionType.LEGISLATIVE_SEAT, SENATOR, FEDERAL_TAX_OR_SPENDING, profile, AS_OF
    )
    assert result.finding_code == AuthorityCode.ADVOCACY_OR_NEGOTIATION_ONLY.value


def test_representative_may_initiate_a_revenue_bill():
    profile = _profile()
    result = legal_authority.assess(
        ElectionType.LEGISLATIVE_SEAT, REPRESENTATIVE, FEDERAL_TAX_OR_SPENDING, profile, AS_OF
    )
    assert result.finding_code == AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY.value


def test_no_member_can_unilaterally_direct_agency_rulemaking():
    """Rulemaking under enacted law is an executive function (art. I, § 1;
    art. II, § 1); neither chamber's member holds it directly."""

    profile = _profile()
    for actor in (SENATOR, REPRESENTATIVE):
        result = legal_authority.assess(
            ElectionType.LEGISLATIVE_SEAT, actor, FEDERAL_REGULATORY_DIRECTIVE, profile, AS_OF
        )
        assert result.finding_code == AuthorityCode.AUTHORITY_HELD_ELSEWHERE.value
        assert result.evidence_state == EvidenceState.ESTABLISHED


def test_constitutional_amendment_requires_ratification_gate_congress_cannot_supply_alone():
    profile = _profile()
    gates = profile.gates_for_instrument(FEDERAL_CONSTITUTIONAL_AMENDMENT)
    assert "three_fourths_state_ratification" in gates
    assert "two_thirds_house_passage" in gates
    assert "two_thirds_senate_passage" in gates


def test_profile_has_no_fiscal_baseline_by_default():
    """A real CBO baseline must be supplied per assessment; this profile
    does not fabricate one (Section 9.6 requires a versioned baseline
    release, not a placeholder)."""

    profile = _profile()
    assert profile.fiscal_baseline is None
