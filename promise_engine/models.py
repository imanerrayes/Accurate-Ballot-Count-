"""Core data model for the Political Promise Comparison and Feasibility Engine.

This module defines the versioned, evidence-first entities described in the
product and technical requirements specification: source material, atomic
claims, promises, policy specifications, jurisdiction profiles, dimension
results, and assessment/execution records.

Design rules encoded here (see requirements Section 6, "Core product
principles"):

- Original text controls. Derivatives (OCR text, translations, policy
  specifications) are linked, never a replacement for the source.
- Every material field carries a provenance type. Analyst assumptions are
  never counted as "stated" evidence.
- Records are append-only. Corrections create a new version with an explicit
  supersession link rather than mutating history.
- Missing information is represented explicitly (``None`` / dedicated enum
  members) rather than defaulted to a value that could be mistaken for a
  finding.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Mapping, Optional, Sequence, Tuple


def new_id(prefix: str) -> str:
    """Generate a stable, human-legible identifier for a new entity."""

    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Controlled vocabularies (Section 7.3)
# ---------------------------------------------------------------------------


class ProvenanceType(str, Enum):
    STATED = "stated"
    AUTHORITATIVE_EXTERNAL = "authoritative_external"
    ANALYST_ASSUMPTION = "analyst_assumption"
    DERIVED = "derived"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class SourceTier(str, Enum):
    MANIFESTO_OR_PROGRAMME = "manifesto_or_programme"
    PARTY_POLICY_PAGE = "party_policy_page"
    FORMALLY_ADOPTED_PROGRAMME = "formally_adopted_programme"
    SPEECH_OR_LEAFLET = "speech_or_leaflet"
    INTERVIEW = "interview"
    THIRD_PARTY_SUMMARY = "third_party_summary"


class RosterDisposition(str, Enum):
    COLLECTED = "collected"
    UNAVAILABLE = "unavailable"
    EXCLUDED = "excluded"
    UNRESOLVED = "unresolved"


class StatementType(str, Enum):
    COMMITMENT = "commitment"
    PROPOSAL = "proposal"
    GOAL = "goal"
    DIAGNOSIS = "diagnosis"
    VALUE_STATEMENT = "value_statement"
    FACTUAL_ASSERTION = "factual_assertion"
    ATTACK = "attack"
    QUESTION = "question"
    OTHER = "other"


class PromiseFindingCode(str, Enum):
    EXPLICIT_COMMITMENT = "explicit_commitment"
    CONDITIONAL_COMMITMENT = "conditional_commitment"
    PROPOSAL_FOR_CONSIDERATION = "proposal_for_consideration"
    ASPIRATION_OR_GOAL = "aspiration_or_goal"
    DIAGNOSIS_OR_VALUE_STATEMENT = "diagnosis_or_value_statement"
    ATTRIBUTION_UNCERTAIN = "attribution_uncertain"
    NOT_A_PROMISE = "not_a_promise"


#: Only these finding codes describe an atomic claim with a recoverable
#: actor, commitment modality, action or outcome, and object — the minimum
#: promise test in Section 9.4. Every other claim is retained as a labelled
#: non-promise comparison item, but is not eligible for the full
#: Feasibility Readiness Vector (Section 9.3).
SCOREABLE_PROMISE_FINDING_CODES = frozenset(
    {PromiseFindingCode.EXPLICIT_COMMITMENT, PromiseFindingCode.CONDITIONAL_COMMITMENT}
)


class AuthorityCode(str, Enum):
    DIRECT_AUTHORITY = "direct_authority"
    SHARED_OR_CONCURRENT = "shared_or_concurrent"
    DELEGATED = "delegated"
    EXECUTIVE_DISCRETION = "executive_discretion"
    LEGISLATIVE_INITIATIVE_ONLY = "legislative_initiative_only"
    ADVOCACY_OR_NEGOTIATION_ONLY = "advocacy_or_negotiation_only"
    AUTHORITY_HELD_ELSEWHERE = "authority_held_elsewhere"
    LEGALLY_PROHIBITED = "legally_prohibited"
    INDETERMINATE = "indeterminate"


class GateState(str, Enum):
    SATISFIED_IN_SCENARIO = "satisfied_in_scenario"
    UNMET = "unmet"
    UNKNOWN = "unknown"
    CONDITIONAL = "conditional"
    NOT_APPLICABLE = "not_applicable"


class EvidenceState(str, Enum):
    """Shared response states (Section 9.2). These are evidence states, not
    grades, and must never be rendered on a good/bad colour scale."""

    ESTABLISHED = "established"
    SUPPORTED_BUT_CONDITIONAL = "supported_but_conditional"
    PARTIALLY_SPECIFIED = "partially_specified"
    UNKNOWN_OR_DISPUTED = "unknown_or_disputed"
    NOT_ASSESSABLE = "not_assessable"


class HistoricalOutcomeStatus(str, Enum):
    FULFILLED = "fulfilled"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    NOT_FULFILLED = "not_fulfilled"
    WITHDRAWN_OR_SUPERSEDED = "withdrawn_or_superseded"
    INDETERMINATE = "indeterminate"


class ElectionType(str, Enum):
    PARLIAMENTARY_GENERAL = "parliamentary_general"
    PRESIDENTIAL = "presidential"
    LEGISLATIVE_SEAT = "legislative_seat"
    REGIONAL_OR_PROVINCIAL = "regional_or_provincial"
    MUNICIPAL = "municipal"
    SUPRANATIONAL = "supranational"
    DIRECTLY_ELECTED_EXECUTIVE = "directly_elected_executive"
    REFERENDUM = "referendum"


class DimensionName(str, Enum):
    PROMISE_CERTAINTY = "promise_certainty"
    LEGAL_AUTHORITY = "legal_authority"
    FISCAL_PLAUSIBILITY = "fiscal_and_economic_plausibility"
    IMPLEMENTATION_CAPACITY = "implementation_capacity"
    POLITICAL_DEPENDENCY = "political_dependency"
    TIMELINE_PLAUSIBILITY = "timeline_plausibility"
    EVIDENCE_QUALITY = "evidence_quality"
    HISTORICAL_OUTCOMES = "historically_comparable_outcomes"


# Applicable policy specification fields (Section 9.4).
SPECIFICATION_FIELDS: Tuple[str, ...] = (
    "policy_change",
    "instrument",
    "target_or_eligibility",
    "quantity_or_rate",
    "start_date",
    "duration",
    "delivery_owner",
    "stated_cost_or_revenue",
    "funding_or_offset",
    "geography",
    "condition",
    "deadline",
)

# Implementation-capacity readiness checklist (Section 9.7).
CAPACITY_CHECKLIST_ITEMS: Tuple[str, ...] = (
    "responsible_delivery_owner_and_mandate",
    "appropriated_or_reliable_funding",
    "staffing_and_skills",
    "operational_data_and_information_systems",
    "procurement_or_contracting_route",
    "implementing_regulations_or_guidance",
    "enforcement_or_inspection_capability",
    "intergovernmental_and_stakeholder_coordination",
    "monitoring_and_evaluation_plan",
    "comparable_prior_delivery_evidence",
)


# ---------------------------------------------------------------------------
# Provenance-carrying field value
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldValue:
    """A single provenance-tagged field, per Section 11.2."""

    field: str
    value: Any
    provenance: ProvenanceType
    source_ref: Optional[str] = None
    unit: Optional[str] = None

    def is_evidenced(self) -> bool:
        """True only for fields an assessment may treat as established fact.

        Analyst assumptions are explicitly excluded: Section 9.4 requires
        that "analyst assumptions shall never be counted as stated or
        supported coverage."
        """

        return self.provenance in (
            ProvenanceType.STATED,
            ProvenanceType.AUTHORITATIVE_EXTERNAL,
        )


# ---------------------------------------------------------------------------
# Source, roster, and entity records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoliticalEntity:
    entity_id: str
    name: str
    jurisdiction: str
    official_id: Optional[str] = None
    aliases: Tuple[str, ...] = ()
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


@dataclass(frozen=True)
class RosterItem:
    election_id: str
    entity_id: str
    disposition: RosterDisposition
    reason: Optional[str] = None
    source_candidates: Tuple[str, ...] = ()
    timestamp: Optional[date] = None


@dataclass(frozen=True)
class SourceObject:
    """An immutable capture of one source document or page.

    A re-crawl of the same canonical URL must never overwrite this record;
    it must create a new ``SourceObject`` with an incremented ``version`` and
    a distinct ``source_id`` (Section 10, COL-005). Use
    :mod:`promise_engine.evidence_store` to enforce this at the store layer.
    """

    source_id: str
    canonical_url: str
    retrieval_date: date
    content_hash: str
    source_tier: SourceTier
    version: int = 1
    publication_date: Optional[date] = None
    rights_or_access: Optional[str] = None
    payload_available: bool = True
    superseded_by: Optional[str] = None


@dataclass(frozen=True)
class AtomicClaim:
    """A single-proposition unit extracted from a source (Section 8, step 4)."""

    claim_id: str
    source_id: str
    quote: str
    offset_start: int
    offset_end: int
    statement_type: StatementType
    entity_id: Optional[str] = None
    actor: Optional[str] = None
    modality: Optional[str] = None
    condition: Optional[str] = None
    topic: Optional[str] = None
    extraction_confidence: float = 1.0
    review_state: str = "unreviewed"


@dataclass(frozen=True)
class Promise:
    """An atomic claim that has passed the minimum promise test (Section 9.4)."""

    promise_id: str
    claim_ids: Tuple[str, ...]
    entity_id: str
    election_id: str
    actor: str
    action_or_outcome: str
    object_: str
    finding_code: PromiseFindingCode
    canonical_description: str
    reviewer: Optional[str] = None
    superseded_by: Optional[str] = None


@dataclass(frozen=True)
class PolicySpecification:
    """Field-value-provenance triples describing the proposed change.

    ``fields`` maps a name drawn from :data:`SPECIFICATION_FIELDS` to a
    :class:`FieldValue`. A field absent from the mapping is treated as
    unknown rather than as evidence of anything.
    """

    spec_id: str
    promise_id: str
    fields: Mapping[str, FieldValue] = field(default_factory=dict)

    def stated_coverage(self) -> float:
        applicable = [f for f in SPECIFICATION_FIELDS if f in self.fields]
        if not applicable:
            return 0.0
        stated = sum(
            1
            for f in applicable
            if self.fields[f].provenance == ProvenanceType.STATED
        )
        return stated / len(applicable)

    def supported_coverage(self) -> float:
        applicable = [f for f in SPECIFICATION_FIELDS if f in self.fields]
        if not applicable:
            return 0.0
        supported = sum(1 for f in applicable if self.fields[f].is_evidenced())
        return supported / len(applicable)


# ---------------------------------------------------------------------------
# Jurisdiction profile and rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LegalRule:
    """One row of the deterministic rule matrix (Section 7.3)."""

    rule_id: str
    election_type: ElectionType
    actor_type: str
    instrument_type: str
    power_type: str
    priority: int
    result_code: AuthorityCode
    source: str
    reviewer: Optional[str] = None
    prerequisites: Tuple[str, ...] = ()
    conflict_behaviour: str = "abstain_on_tie"


@dataclass(frozen=True)
class FiscalBaseline:
    baseline_id: str
    currency: str
    fiscal_year: str
    budget_boundary: str
    accounting_basis: str
    price_basis: str
    horizon_years: int
    indexation: Optional[str] = None
    debt_interest_convention: Optional[str] = None
    source: Optional[str] = None


@dataclass(frozen=True)
class JurisdictionProfile:
    """A versioned, effective-dated collection of rules (Section 7.1-7.3).

    Legal, fiscal, political-dependency, and historical-comparability
    modules must refuse to run without a profile that is present, current,
    and compatible with the requested election context (Section 7.1).
    """

    profile_id: str
    version: str
    jurisdiction: str
    election_types: Tuple[ElectionType, ...]
    effective_from: date
    effective_to: Optional[date]
    approver: str
    government_system: str
    legal_rules: Tuple[LegalRule, ...] = ()
    fiscal_baseline: Optional[FiscalBaseline] = None
    mandatory_gate_catalog: Tuple[str, ...] = ()

    def is_effective(self, as_of: date) -> bool:
        if as_of < self.effective_from:
            return False
        if self.effective_to is not None and as_of > self.effective_to:
            return False
        return True

    def supports_election_type(self, election_type: ElectionType) -> bool:
        return election_type in self.election_types


@dataclass(frozen=True)
class Scenario:
    """Frozen political/institutional context for one assessment run."""

    scenario_id: str
    election_id: str
    government_status: Optional[str] = None
    chamber_composition: Optional[str] = None
    coalition_agreement: bool = False
    gates: Mapping[str, GateState] = field(default_factory=dict)
    gate_durations_months: Mapping[str, Optional[float]] = field(default_factory=dict)
    gate_duration_source: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DependencyNode:
    node_id: str
    label: str
    responsible_institution: str
    status: GateState
    evidence_source: Optional[str] = None


@dataclass(frozen=True)
class DependencyEdge:
    from_node: str
    to_node: str


# ---------------------------------------------------------------------------
# Dimension results and assessment output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionResult:
    dimension: DimensionName
    finding_code: str
    evidence_state: EvidenceState
    plain_language_finding: str
    conditions: Tuple[str, ...] = ()
    missing_information: Tuple[str, ...] = ()
    blocking_gates: Tuple[str, ...] = ()
    sources: Tuple[str, ...] = ()
    assumptions: Tuple[str, ...] = ()
    review_state: str = "unreviewed"
    rule_set_version: Optional[str] = None
    metrics: Mapping[str, float] = field(default_factory=dict)
    result_id: Optional[str] = None


@dataclass(frozen=True)
class PublicationBlock:
    """Returned when a hard precondition fails (Section 9.3).

    Failure of a precondition returns a named publication block. It never
    returns a zero, an empty result, or a silently omitted dimension.
    """

    reason: str
    missing: Tuple[str, ...] = ()


@dataclass(frozen=True)
class HistoricalOutcomeRecord:
    record_id: str
    promise_reference: str
    jurisdiction: str
    term: str
    status: HistoricalOutcomeStatus
    government_status: Optional[str] = None
    coalition_form: Optional[str] = None
    topic: Optional[str] = None
    coder: Optional[str] = None


@dataclass(frozen=True)
class AssessmentResult:
    """Canonical, content-addressed result for one promise (Section 15.1).

    ``result_hash`` is computed from the canonical serialization in
    :mod:`promise_engine.canonical` and excludes volatile fields such as
    timestamps or operator identity, so that re-running the same frozen
    input manifest reproduces the same hash.
    """

    result_id: str
    promise_id: str
    profile_id: str
    profile_version: str
    scenario_id: str
    dimension_results: Tuple[DimensionResult, ...]
    dependency_graph: Tuple[Tuple[DependencyNode, ...], Tuple[DependencyEdge, ...]]
    publication_block: Optional[PublicationBlock] = None
    result_hash: Optional[str] = None

    @property
    def is_published(self) -> bool:
        return self.publication_block is None


@dataclass(frozen=True)
class ExecutionRecord:
    """Volatile operational metadata for one attempt (Section 15.1)."""

    execution_id: str
    result_hash: Optional[str]
    timestamp: str
    environment: str
    operator: str
    status: str


@dataclass(frozen=True)
class AppealCase:
    case_id: str
    record_reference: str
    claimant_type: str
    issue: str
    status: str = "received"
    decision: Optional[str] = None
    correction_links: Tuple[str, ...] = ()
