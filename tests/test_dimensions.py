from datetime import date

from promise_engine.models import (
    ElectionType,
    EvidenceState,
    FieldValue,
    HistoricalOutcomeRecord,
    HistoricalOutcomeStatus,
    PolicySpecification,
    ProvenanceType,
)
from promise_engine.pipeline.dimensions import fiscal, historical, legal_authority

AS_OF = date(2026, 9, 15)


def test_at07_presidential_tax_requires_legislative_and_appropriation_gates(presidential_profile):
    result = legal_authority.assess(
        election_type=ElectionType.PRESIDENTIAL,
        actor_type="president",
        instrument_type="national_tax",
        profile=presidential_profile,
        as_of=AS_OF,
    )
    assert result.finding_code == "legislative_initiative_only"
    assert result.evidence_state == EvidenceState.SUPPORTED_BUT_CONDITIONAL
    assert "passage by the legislature" in result.conditions
    assert "assent or promulgation" in result.conditions


def test_at09_municipality_tax_outside_delegated_power(municipal_profile):
    result = legal_authority.assess(
        election_type=ElectionType.MUNICIPAL,
        actor_type="mayor",
        instrument_type="national_tax",
        profile=municipal_profile,
        as_of=AS_OF,
    )
    assert result.finding_code == "authority_held_elsewhere"
    assert result.evidence_state == EvidenceState.ESTABLISHED


def test_legal_authority_abstains_on_missing_profile():
    result = legal_authority.assess(
        election_type=ElectionType.PRESIDENTIAL,
        actor_type="president",
        instrument_type="national_tax",
        profile=None,
        as_of=AS_OF,
    )
    assert result.evidence_state == EvidenceState.NOT_ASSESSABLE
    assert result.finding_code == "jurisdiction_profile_missing"


def test_at13_fiscal_module_abstains_without_baseline_or_spec():
    result = fiscal.assess(spec=None, baseline=None)
    assert result.finding_code == "fiscal_module_disabled"
    assert result.evidence_state == EvidenceState.NOT_ASSESSABLE


def test_at13_incomplete_specification_returns_not_costable(presidential_profile):
    spec = PolicySpecification(spec_id="spec-1", promise_id="promise-1", fields={})
    result = fiscal.assess(spec=spec, baseline=presidential_profile.fiscal_baseline)
    assert result.finding_code == "not_costable_from_public_detail"
    assert result.evidence_state == EvidenceState.NOT_ASSESSABLE


def test_at14_growth_funded_promise_retains_direct_effect_and_flags_funding_unspecified(presidential_profile):
    spec = PolicySpecification(
        spec_id="spec-1",
        promise_id="promise-1",
        fields={
            "target_or_eligibility": FieldValue("target_or_eligibility", 1000, ProvenanceType.STATED),
            "quantity_or_rate": FieldValue("quantity_or_rate", 500.0, ProvenanceType.STATED),
            "start_date": FieldValue("start_date", "2027-01-01", ProvenanceType.STATED),
        },
    )
    result = fiscal.assess(spec=spec, baseline=presidential_profile.fiscal_baseline)
    assert result.finding_code == "static_direct_effect_computed"
    assert "funding_unspecified" in result.conditions
    assert result.metrics["static_direct_effect"] == 500_000.0


def test_at18_historical_distribution_retains_all_five_statuses():
    corpus = [
        HistoricalOutcomeRecord("r1", "p1", "Test Jurisdiction", "term1", HistoricalOutcomeStatus.FULFILLED),
        HistoricalOutcomeRecord("r2", "p2", "Test Jurisdiction", "term1", HistoricalOutcomeStatus.PARTIALLY_FULFILLED),
        HistoricalOutcomeRecord("r3", "p3", "Test Jurisdiction", "term1", HistoricalOutcomeStatus.NOT_FULFILLED),
        HistoricalOutcomeRecord("r4", "p4", "Test Jurisdiction", "term1", HistoricalOutcomeStatus.WITHDRAWN_OR_SUPERSEDED),
        HistoricalOutcomeRecord("r5", "p5", "Test Jurisdiction", "term1", HistoricalOutcomeStatus.INDETERMINATE),
    ]
    result = historical.assess(jurisdiction="Test Jurisdiction", corpus=corpus, min_sample=5)
    assert result.finding_code == "descriptive_base_rate"
    assert result.metrics["count_fulfilled"] == 1.0
    assert result.metrics["count_partially_fulfilled"] == 1.0
    assert result.metrics["count_not_fulfilled"] == 1.0
    assert result.metrics["count_withdrawn_or_superseded"] == 1.0
    assert result.metrics["count_indeterminate"] == 1.0
    assert result.metrics["sample_size"] == 5.0


def test_at20_historical_abstains_below_minimum_sample():
    corpus = [
        HistoricalOutcomeRecord("r1", "p1", "Small Jurisdiction", "term1", HistoricalOutcomeStatus.FULFILLED),
    ]
    result = historical.assess(jurisdiction="Small Jurisdiction", corpus=corpus, min_sample=5)
    assert result.finding_code == "insufficient_comparable_sample"
    assert result.evidence_state == EvidenceState.NOT_ASSESSABLE
