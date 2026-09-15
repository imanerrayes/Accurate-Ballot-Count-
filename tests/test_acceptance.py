"""A representative subset of the acceptance-test catalogue (Section 17.1).

Each test is named for the acceptance-test ID it operationalises. This is
not the full fixture suite the specification calls for (Section 17); it
demonstrates that the reference implementation's guardrails hold for the
scenario each test describes.
"""

from datetime import date

from promise_engine.jurisdiction import check_hard_preconditions, profile_gate
from promise_engine.models import ElectionType, SourceObject, SourceTier
from promise_engine.pipeline import extraction
from promise_engine.pipeline.orchestrator import AssessmentInputs, run_assessment

AS_OF = date(2026, 9, 15)


def _source() -> SourceObject:
    return SourceObject(
        source_id="src-test",
        canonical_url="https://example.org/manifesto",
        retrieval_date=date(2026, 9, 1),
        content_hash="sha256:deadbeef",
        source_tier=SourceTier.MANIFESTO_OR_PROGRAMME,
    )


def test_at01_missing_source_blocks_publication(presidential_profile):
    text = "The President will create a national infrastructure tax."
    claims = extraction.extract_atomic_claims(_source(), text)
    promise = extraction.resolve_promise(claims[0], "entity-1", "election-1", actor="The President")

    block = check_hard_preconditions(
        promise=promise,
        claims=claims,
        sources=[None],  # no source object recoverable for this claim
        profile=presidential_profile,
        election_type=ElectionType.PRESIDENTIAL,
        as_of=AS_OF,
        rule_set_version="v1",
    )
    assert block is not None
    assert "source_object" in block.missing


def test_at02_missing_profile_blocks_legal_fiscal_political_modules():
    block = profile_gate(profile=None, election_type=ElectionType.PRESIDENTIAL, as_of=AS_OF)
    assert block is not None
    assert block.reason == "jurisdiction_profile_missing"


def test_at02_expired_profile_blocks(presidential_profile):
    expired_as_of = date(2031, 1, 1)  # profile.effective_to is 2030-12-31
    block = profile_gate(presidential_profile, ElectionType.PRESIDENTIAL, expired_as_of)
    assert block is not None
    assert block.reason == "jurisdiction_profile_expired"


def test_at02_incompatible_election_type_blocks(presidential_profile):
    block = profile_gate(presidential_profile, ElectionType.MUNICIPAL, AS_OF)
    assert block is not None
    assert block.reason == "jurisdiction_profile_incompatible_election_type"


def test_at06_neutrality_identical_text_different_party_names():
    text = "The party will create a national infrastructure tax to fund transit projects."
    source = _source()
    claims_a = extraction.extract_atomic_claims(source, text)
    claims_b = extraction.extract_atomic_claims(source, text)

    promise_a = extraction.resolve_promise(claims_a[0], "entity-north", "election-1", actor="Northern Party")
    promise_b = extraction.resolve_promise(claims_b[0], "entity-south", "election-1", actor="Southern Party")

    # Everything except attribution (entity_id, actor, promise_id, claim_ids)
    # must be identical.
    assert promise_a.finding_code == promise_b.finding_code
    assert promise_a.action_or_outcome == promise_b.action_or_outcome
    assert promise_a.object_ == promise_b.object_
    assert promise_a.canonical_description == promise_b.canonical_description
    assert claims_a[0].statement_type == claims_b[0].statement_type


def test_at16_identical_frozen_inputs_reproduce_identical_result_hash(presidential_profile, frozen_scenario):
    source = _source()
    text = "The President will create a national infrastructure tax."
    claims = extraction.extract_atomic_claims(source, text)
    promise = extraction.resolve_promise(claims[0], "entity-1", "election-1", actor="The President")

    def build_inputs():
        return AssessmentInputs(
            promise=promise,
            claims=claims,
            sources=[source],
            spec=None,
            profile=presidential_profile,
            scenario=frozen_scenario,
            election_type=ElectionType.PRESIDENTIAL,
            actor_type="president",
            instrument_type="national_tax",
            as_of=AS_OF,
            rule_set_version="ruleset-test-1",
        )

    result_1 = run_assessment(build_inputs())
    result_2 = run_assessment(build_inputs())

    assert result_1.result_hash == result_2.result_hash
    assert result_1.result_id != result_2.result_id  # distinct executions, same content


def test_at16_changed_input_changes_the_hash(presidential_profile, frozen_scenario):
    source = _source()
    text = "The President will create a national infrastructure tax."
    claims = extraction.extract_atomic_claims(source, text)
    promise = extraction.resolve_promise(claims[0], "entity-1", "election-1", actor="The President")

    baseline = run_assessment(
        AssessmentInputs(
            promise=promise,
            claims=claims,
            sources=[source],
            spec=None,
            profile=presidential_profile,
            scenario=frozen_scenario,
            election_type=ElectionType.PRESIDENTIAL,
            actor_type="president",
            instrument_type="national_tax",
            as_of=AS_OF,
            rule_set_version="ruleset-test-1",
        )
    )

    from dataclasses import replace

    changed_scenario = replace(
        frozen_scenario,
        gate_durations_months={**frozen_scenario.gate_durations_months, "assent": 6.0},
    )
    changed = run_assessment(
        AssessmentInputs(
            promise=promise,
            claims=claims,
            sources=[source],
            spec=None,
            profile=presidential_profile,
            scenario=changed_scenario,
            election_type=ElectionType.PRESIDENTIAL,
            actor_type="president",
            instrument_type="national_tax",
            as_of=AS_OF,
            rule_set_version="ruleset-test-1",
        )
    )

    assert baseline.result_hash != changed.result_hash


def test_hard_precondition_failure_never_returns_zero_it_returns_a_named_block(presidential_profile, frozen_scenario):
    source = _source()
    text = "This is unrelated background commentary with no clear actor."
    claims = extraction.extract_atomic_claims(source, text)
    promise = extraction.resolve_promise(claims[0], entity_id=None, election_id="election-1", actor=None)

    result = run_assessment(
        AssessmentInputs(
            promise=promise,
            claims=claims,
            sources=[source],
            spec=None,
            profile=presidential_profile,
            scenario=frozen_scenario,
            election_type=ElectionType.PRESIDENTIAL,
            actor_type="president",
            instrument_type="national_tax",
            as_of=AS_OF,
            rule_set_version="ruleset-test-1",
        )
    )

    assert not result.is_published
    assert result.dimension_results == ()
    assert result.publication_block is not None
