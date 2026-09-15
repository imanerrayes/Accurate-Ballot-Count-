"""Stage 5-6: run the eight dimensions and assemble the FRV (Section 9.12).

``run_assessment`` is the only place that combines dimension results, and
it combines them by collecting them into a tuple — never by summing,
averaging, or otherwise netting them into a single score (Section 6,
Section 9.12: "It shall not compute a public scalar score.").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Mapping, Optional, Sequence

from .. import canonical
from ..evidence_store import EvidenceStore
from ..jurisdiction import check_hard_preconditions
from ..models import (
    AssessmentResult,
    AtomicClaim,
    DependencyEdge,
    DependencyNode,
    ElectionType,
    FiscalBaseline,
    GateState,
    HistoricalOutcomeRecord,
    JurisdictionProfile,
    PolicySpecification,
    Promise,
    ProvenanceType,
    Scenario,
    SourceObject,
    new_id,
)
from .dimensions import (
    capacity,
    evidence_quality,
    fiscal,
    historical,
    legal_authority,
    political_dependency,
    promise_certainty,
    timeline,
)


@dataclass(frozen=True)
class AssessmentInputs:
    """Everything one frozen assessment run needs. Every field here is part
    of the canonical input manifest (Section 15.1) except ``store``."""

    promise: Promise
    claims: Sequence[AtomicClaim]
    sources: Sequence[Optional[SourceObject]]
    spec: Optional[PolicySpecification]
    profile: Optional[JurisdictionProfile]
    scenario: Optional[Scenario]
    election_type: ElectionType
    actor_type: str
    instrument_type: str
    as_of: date
    rule_set_version: Optional[str]
    fiscal_baseline: Optional[FiscalBaseline] = None
    capacity_readiness_evidence: Mapping[str, ProvenanceType] = field(default_factory=dict)
    coordinating_institutions: Sequence[str] = ()
    historical_corpus: Sequence[HistoricalOutcomeRecord] = ()
    historical_government_status: Optional[str] = None
    historical_coalition_form: Optional[str] = None
    historical_topic: Optional[str] = None
    primary_claim: Optional[AtomicClaim] = None
    primary_source: Optional[SourceObject] = None
    evidence_review_state: str = "unreviewed"


def _build_dependency_graph(profile: Optional[JurisdictionProfile], scenario: Optional[Scenario], instrument_type: str):
    gates = profile.gates_for_instrument(instrument_type) if profile is not None else ()
    if profile is None or scenario is None or not gates:
        return (), ()

    nodes = tuple(
        DependencyNode(
            node_id=gate,
            label=gate,
            responsible_institution="unspecified",
            status=scenario.gates.get(gate, GateState.UNKNOWN),
        )
        for gate in gates
    )
    edges = tuple(
        DependencyEdge(from_node=a.node_id, to_node=b.node_id)
        for a, b in zip(nodes, nodes[1:])
    )
    return nodes, edges


def run_assessment(inputs: AssessmentInputs, store: Optional[EvidenceStore] = None) -> AssessmentResult:
    block = check_hard_preconditions(
        promise=inputs.promise,
        claims=inputs.claims,
        sources=inputs.sources,
        profile=inputs.profile,
        election_type=inputs.election_type,
        as_of=inputs.as_of,
        rule_set_version=inputs.rule_set_version,
    )

    scenario_id = inputs.scenario.scenario_id if inputs.scenario else "no_scenario"
    profile_id = inputs.profile.profile_id if inputs.profile else "no_profile"
    profile_version = inputs.profile.version if inputs.profile else "n/a"

    if block is not None:
        result = AssessmentResult(
            result_id=new_id("result"),
            promise_id=inputs.promise.promise_id,
            profile_id=profile_id,
            profile_version=profile_version,
            scenario_id=scenario_id,
            dimension_results=(),
            dependency_graph=((), ()),
            publication_block=block,
        )
        return _finalize(result, store)

    primary_claim = inputs.primary_claim or (inputs.claims[0] if inputs.claims else None)
    primary_source = inputs.primary_source or (inputs.sources[0] if inputs.sources else None)

    dimension_results = (
        promise_certainty.assess(inputs.promise, inputs.spec, inputs.rule_set_version),
        legal_authority.assess(
            inputs.election_type,
            inputs.actor_type,
            inputs.instrument_type,
            inputs.profile,
            inputs.as_of,
            inputs.rule_set_version,
        ),
        fiscal.assess(inputs.spec, inputs.fiscal_baseline, rule_set_version=inputs.rule_set_version),
        capacity.assess(inputs.capacity_readiness_evidence, inputs.rule_set_version),
        political_dependency.assess(
            inputs.profile, inputs.scenario, inputs.instrument_type, inputs.coordinating_institutions, inputs.rule_set_version
        ),
        timeline.assess(inputs.profile, inputs.scenario, inputs.instrument_type, inputs.rule_set_version),
        evidence_quality.assess(
            primary_source, primary_claim, inputs.evidence_review_state, rule_set_version=inputs.rule_set_version
        ),
        historical.assess(
            jurisdiction=inputs.profile.jurisdiction if inputs.profile else "",
            corpus=inputs.historical_corpus,
            government_status=inputs.historical_government_status,
            coalition_form=inputs.historical_coalition_form,
            topic=inputs.historical_topic,
            rule_set_version=inputs.rule_set_version,
        ),
    )

    nodes, edges = _build_dependency_graph(inputs.profile, inputs.scenario, inputs.instrument_type)

    result = AssessmentResult(
        result_id=new_id("result"),
        promise_id=inputs.promise.promise_id,
        profile_id=profile_id,
        profile_version=profile_version,
        scenario_id=scenario_id,
        dimension_results=dimension_results,
        dependency_graph=(nodes, edges),
    )
    return _finalize(result, store)


def _finalize(result: AssessmentResult, store: Optional[EvidenceStore]) -> AssessmentResult:
    """Attach the canonical hash, computed over everything except itself,
    then optionally persist the versioned record."""

    manifest = {
        "promise_id": result.promise_id,
        "profile_id": result.profile_id,
        "profile_version": result.profile_version,
        "scenario_id": result.scenario_id,
        "dimension_results": result.dimension_results,
        "dependency_graph": result.dependency_graph,
        "publication_block": result.publication_block,
    }
    hashed = AssessmentResult(
        result_id=result.result_id,
        promise_id=result.promise_id,
        profile_id=result.profile_id,
        profile_version=result.profile_version,
        scenario_id=result.scenario_id,
        dimension_results=result.dimension_results,
        dependency_graph=result.dependency_graph,
        publication_block=result.publication_block,
        result_hash=canonical.result_hash(manifest),
    )
    if store is not None:
        store.results.put(hashed.result_id, hashed)
    return hashed
