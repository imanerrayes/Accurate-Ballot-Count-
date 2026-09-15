"""Dimension 5: political dependency (Section 9.8).

Builds a scenario ledger of required approvals, not a partisan forecast.
The Gate Completion Ratio applies only to the supplied scenario and is
never described as a probability of success.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ...models import DimensionName, EvidenceState, GateState, JurisdictionProfile, Scenario
from .base import make_result


def assess(
    profile: Optional[JurisdictionProfile],
    scenario: Optional[Scenario],
    coordinating_institutions: Sequence[str] = (),
    rule_set_version: Optional[str] = None,
):
    if profile is None or not profile.mandatory_gate_catalog:
        return make_result(
            dimension=DimensionName.POLITICAL_DEPENDENCY,
            finding_code="dependency_route_not_orderable",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding="The jurisdiction profile does not declare a mandatory gate catalog for this instrument.",
            missing_information=("mandatory_gate_catalog",),
            rule_set_version=rule_set_version,
        )

    if scenario is None:
        return make_result(
            dimension=DimensionName.POLITICAL_DEPENDENCY,
            finding_code="scenario_not_frozen",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding="No frozen political scenario has been supplied for this assessment.",
            missing_information=("scenario",),
            rule_set_version=rule_set_version,
        )

    mandatory_gates = profile.mandatory_gate_catalog
    gate_states = {gate: scenario.gates.get(gate, GateState.UNKNOWN) for gate in mandatory_gates}

    satisfied = [g for g, s in gate_states.items() if s == GateState.SATISFIED_IN_SCENARIO]
    unmet = [g for g, s in gate_states.items() if s == GateState.UNMET]
    unknown = [g for g, s in gate_states.items() if s == GateState.UNKNOWN]
    conditional = [g for g, s in gate_states.items() if s == GateState.CONDITIONAL]

    gate_completion_ratio = len(satisfied) / len(mandatory_gates)
    coordination_load = len(set(coordinating_institutions))

    if unknown:
        evidence_state = EvidenceState.UNKNOWN_OR_DISPUTED
    elif unmet:
        evidence_state = EvidenceState.SUPPORTED_BUT_CONDITIONAL
    elif conditional:
        evidence_state = EvidenceState.SUPPORTED_BUT_CONDITIONAL
    else:
        evidence_state = EvidenceState.ESTABLISHED

    return make_result(
        dimension=DimensionName.POLITICAL_DEPENDENCY,
        finding_code="dependency_ledger_computed",
        evidence_state=evidence_state,
        plain_language_finding=(
            f"{len(satisfied)} of {len(mandatory_gates)} identified mandatory gates are satisfied "
            f"under the '{scenario.scenario_id}' scenario. This ratio describes the named scenario "
            "only; it is not a probability of enactment."
        ),
        conditions=tuple(conditional),
        blocking_gates=tuple(unmet),
        missing_information=tuple(unknown),
        rule_set_version=rule_set_version,
        metrics={
            "gate_completion_ratio": gate_completion_ratio,
            "coordination_load": float(coordination_load),
        },
    )
