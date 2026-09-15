from datetime import date

from promise_engine.models import PromiseFindingCode, SourceObject, SourceTier, StatementType
from promise_engine.pipeline import extraction


def _source() -> SourceObject:
    return SourceObject(
        source_id="src-test",
        canonical_url="https://example.org/manifesto",
        retrieval_date=date(2026, 9, 1),
        content_hash="sha256:deadbeef",
        source_tier=SourceTier.MANIFESTO_OR_PROGRAMME,
    )


def test_at05_two_commitments_one_example_yields_two_claims():
    """AT-05: a sentence with two unrelated commitments and one example
    produces two atomic promises; the example does not become a third."""

    text = (
        "The party will raise the minimum wage and will fund universal "
        "childcare, for example, in urban districts."
    )
    claims = extraction.extract_atomic_claims(_source(), text)

    commitments = [c for c in claims if c.statement_type == StatementType.COMMITMENT]
    assert len(commitments) == 2
    assert all("for example" not in c.quote.lower() for c in claims)


def test_diagnosis_is_never_classified_as_commitment():
    text = "The current transit system is unreliable and outdated."
    claims = extraction.extract_atomic_claims(_source(), text)
    assert len(claims) == 1
    assert claims[0].statement_type == StatementType.FACTUAL_ASSERTION


def test_goal_language_does_not_become_a_scoreable_promise():
    text = "The party aims to improve public health outcomes."
    claims = extraction.extract_atomic_claims(_source(), text)
    promise = extraction.resolve_promise(claims[0], "entity-1", "election-1", actor="The Party")
    assert promise.finding_code == PromiseFindingCode.ASPIRATION_OR_GOAL
    assert not extraction.is_scoreable(promise)


def test_unresolved_actor_yields_attribution_uncertain():
    text = "This will create a national infrastructure fund."
    claims = extraction.extract_atomic_claims(_source(), text)
    promise = extraction.resolve_promise(claims[0], entity_id=None, election_id="election-1", actor=None)
    assert promise.finding_code == PromiseFindingCode.ATTRIBUTION_UNCERTAIN
    assert not extraction.is_scoreable(promise)


def test_conditional_commitment_detected():
    text = "The party will cut the corporate tax rate if the budget surplus exceeds two percent."
    claims = extraction.extract_atomic_claims(_source(), text)
    promise = extraction.resolve_promise(claims[0], "entity-1", "election-1", actor="The Party")
    assert promise.finding_code == PromiseFindingCode.CONDITIONAL_COMMITMENT
