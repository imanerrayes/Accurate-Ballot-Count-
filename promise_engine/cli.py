"""A runnable end-to-end demonstration of the pipeline.

This is a reference walkthrough, not a production CLI: it wires together
roster construction, source capture, atomic-claim extraction, a policy
specification, a jurisdiction profile, and a frozen scenario, then prints
the resulting explanation packet for one promise. Run it with::

    python -m promise_engine.cli
"""

from __future__ import annotations

from datetime import date

from .evidence_store import EvidenceStore
from .models import (
    AuthorityCode,
    ElectionType,
    FiscalBaseline,
    GateState,
    JurisdictionProfile,
    LegalRule,
    ProvenanceType,
    RosterDisposition,
    Scenario,
    SourceTier,
)
from .pipeline import capture, extraction, roster
from .pipeline.orchestrator import AssessmentInputs, run_assessment
from .pipeline.specification import build_policy_specification, field as spec_field

MANIFESTO_TEXT = (
    "The President will create a national infrastructure tax to fund transit projects, "
    "for example in coastal cities. The current transit system is unreliable and outdated. "
    "The candidate will also expand broadband access nationwide."
)


def run_demo() -> None:
    store = EvidenceStore()
    as_of = date(2026, 9, 15)

    # Stage 2a: election roster.
    election_id = "election-2026-national"
    entity_id = "entity-northern-party"
    items = roster.build_roster(
        election_id=election_id,
        entity_ids=[entity_id],
        dispositions={entity_id: RosterDisposition.COLLECTED},
    )
    print(f"Roster: {roster.coverage(items)}")

    # Stage 2b: immutable source capture.
    source = capture.capture_source(
        store=store,
        canonical_url="https://example.org/manifesto-2026",
        payload=MANIFESTO_TEXT.encode("utf-8"),
        source_tier=SourceTier.MANIFESTO_OR_PROGRAMME,
        retrieval_date=as_of,
    )
    print(f"Captured source: {source.source_id} (version {source.version})")

    # Stage 3: segmentation, classification, and promise resolution.
    claims = extraction.extract_atomic_claims(source, MANIFESTO_TEXT)
    print(f"\nExtracted {len(claims)} atomic claims:")
    promises = []
    for claim in claims:
        promise = extraction.resolve_promise(claim, entity_id, election_id, actor="The President")
        promises.append(promise)
        print(f"  [{claim.statement_type.value:>17}] {claim.quote!r} -> {promise.finding_code.value}")

    tax_promise = next(p for p in promises if "tax" in p.canonical_description.lower())
    assert extraction.is_scoreable(tax_promise)

    # Stage 4a: policy specification (normally built from further extraction
    # plus human review; supplied directly here for the demonstration).
    spec = build_policy_specification(
        tax_promise.promise_id,
        {
            "target_or_eligibility": spec_field("target_or_eligibility", 2_000_000, ProvenanceType.STATED),
            "quantity_or_rate": spec_field("quantity_or_rate", 150.0, ProvenanceType.STATED),
            "start_date": spec_field("start_date", "2027-01-01", ProvenanceType.STATED),
            "instrument": spec_field("instrument", "national_tax", ProvenanceType.STATED),
        },
    )

    # Section 7.3: jurisdiction profile with an effective-dated legal rule.
    profile = JurisdictionProfile(
        profile_id="profile-demo-federal-2026",
        version="1.0.0",
        jurisdiction="Demo Federal Republic",
        election_types=(ElectionType.PRESIDENTIAL,),
        effective_from=date(2026, 1, 1),
        effective_to=date(2030, 12, 31),
        approver="demo-governance-board",
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
                source="Demo Constitution Art. IV, sec. 2",
                reviewer="legal_reviewer_1",
            ),
        ),
        fiscal_baseline=FiscalBaseline(
            baseline_id="baseline-2026",
            currency="USD",
            fiscal_year="FY2027",
            budget_boundary="general_government",
            accounting_basis="cash",
            price_basis="nominal",
            horizon_years=5,
        ),
        mandatory_gate_catalog={"national_tax": ("legislative_passage", "appropriation", "assent")},
    )
    store.profiles.put(profile.profile_id, profile)

    scenario = Scenario(
        scenario_id="scenario-demo-minority-legislature",
        election_id=election_id,
        government_status="minority",
        gates={
            "legislative_passage": GateState.UNMET,
            "appropriation": GateState.UNKNOWN,
            "assent": GateState.CONDITIONAL,
        },
        gate_durations_months={"legislative_passage": 9.0, "appropriation": 3.0, "assent": 1.0},
        gate_duration_source={
            "legislative_passage": "jurisdiction_profile_default",
            "appropriation": "jurisdiction_profile_default",
            "assent": "source_backed",
        },
    )

    inputs = AssessmentInputs(
        promise=tax_promise,
        claims=[c for c in claims if c.claim_id in tax_promise.claim_ids],
        sources=[source],
        spec=spec,
        profile=profile,
        scenario=scenario,
        election_type=ElectionType.PRESIDENTIAL,
        actor_type="president",
        instrument_type="national_tax",
        as_of=as_of,
        rule_set_version="ruleset-2026.1",
        fiscal_baseline=profile.fiscal_baseline,
        capacity_readiness_evidence={
            "responsible_delivery_owner_and_mandate": ProvenanceType.STATED,
            "appropriated_or_reliable_funding": ProvenanceType.UNKNOWN,
        },
        coordinating_institutions=("national_legislature", "treasury"),
        evidence_review_state="legal_reviewer_approved",
    )

    result = run_assessment(inputs, store=store)
    result_again = run_assessment(inputs, store=None)

    print(f"\nAssessment result: {result.result_id}")
    print(f"Published: {result.is_published}")
    print(f"Result hash: {result.result_hash}")
    print(f"Reproducible (same hash on re-run): {result.result_hash == result_again.result_hash}")

    print("\nExplanation packet (eight independent dimensions, no composite score):")
    for dr in result.dimension_results:
        print(f"\n  Dimension: {dr.dimension.value}")
        print(f"    Finding code:    {dr.finding_code}")
        print(f"    Evidence state:  {dr.evidence_state.value}")
        print(f"    Finding:         {dr.plain_language_finding}")
        if dr.conditions:
            print(f"    Conditions:      {list(dr.conditions)}")
        if dr.missing_information:
            print(f"    Missing:         {list(dr.missing_information)}")
        if dr.blocking_gates:
            print(f"    Blocking gates:  {list(dr.blocking_gates)}")
        if dr.metrics:
            print(f"    Metrics:         {dr.metrics}")

    print("\n--- Abstention example: same promise, no jurisdiction profile ---")
    blocked_inputs = AssessmentInputs(
        promise=tax_promise,
        claims=[c for c in claims if c.claim_id in tax_promise.claim_ids],
        sources=[source],
        spec=spec,
        profile=None,
        scenario=None,
        election_type=ElectionType.PRESIDENTIAL,
        actor_type="president",
        instrument_type="national_tax",
        as_of=as_of,
        rule_set_version="ruleset-2026.1",
    )
    blocked = run_assessment(blocked_inputs)
    print(f"Published: {blocked.is_published}")
    print(f"Publication block: {blocked.publication_block}")


if __name__ == "__main__":
    run_demo()
