from datetime import date

import pytest

from promise_engine.models import (
    AuthorityCode,
    ElectionType,
    FiscalBaseline,
    GateState,
    JurisdictionProfile,
    LegalRule,
    Scenario,
)

AS_OF = date(2026, 9, 15)


@pytest.fixture
def presidential_profile() -> JurisdictionProfile:
    return JurisdictionProfile(
        profile_id="profile-test-federal",
        version="1.0.0",
        jurisdiction="Test Federal Republic",
        election_types=(ElectionType.PRESIDENTIAL,),
        effective_from=date(2026, 1, 1),
        effective_to=date(2030, 12, 31),
        approver="governance-board",
        government_system="presidential",
        legal_rules=(
            LegalRule(
                rule_id="rule-tax-001",
                election_type=ElectionType.PRESIDENTIAL,
                actor_type="president",
                instrument_type="national_tax",
                power_type="appropriate_or_raise_revenue",
                priority=1,
                result_code=AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
                source="Test Constitution Art. IV, sec. 2",
                reviewer="legal_reviewer_1",
            ),
        ),
        fiscal_baseline=FiscalBaseline(
            baseline_id="baseline-test",
            currency="USD",
            fiscal_year="FY2027",
            budget_boundary="general_government",
            accounting_basis="cash",
            price_basis="nominal",
            horizon_years=5,
        ),
        mandatory_gate_catalog=("legislative_passage", "appropriation", "assent"),
    )


@pytest.fixture
def municipal_profile() -> JurisdictionProfile:
    return JurisdictionProfile(
        profile_id="profile-test-municipal",
        version="1.0.0",
        jurisdiction="Test Municipality",
        election_types=(ElectionType.MUNICIPAL,),
        effective_from=date(2026, 1, 1),
        effective_to=date(2030, 12, 31),
        approver="governance-board",
        government_system="direct_executive",
        legal_rules=(
            LegalRule(
                rule_id="rule-municipal-tax-001",
                election_type=ElectionType.MUNICIPAL,
                actor_type="mayor",
                instrument_type="national_tax",
                power_type="appropriate_or_raise_revenue",
                priority=1,
                result_code=AuthorityCode.AUTHORITY_HELD_ELSEWHERE,
                source="Test State Local Government Act sec. 9",
                reviewer="legal_reviewer_1",
            ),
        ),
    )


@pytest.fixture
def frozen_scenario() -> Scenario:
    return Scenario(
        scenario_id="scenario-test-minority",
        election_id="election-test",
        government_status="minority",
        gates={
            "legislative_passage": GateState.UNMET,
            "appropriation": GateState.CONDITIONAL,
            "assent": GateState.SATISFIED_IN_SCENARIO,
        },
        gate_durations_months={"legislative_passage": 9.0, "appropriation": 3.0, "assent": 1.0},
        gate_duration_source={
            "legislative_passage": "jurisdiction_profile_default",
            "appropriation": "jurisdiction_profile_default",
            "assent": "source_backed",
        },
    )
