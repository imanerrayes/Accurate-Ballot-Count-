"""Dimension 6: timeline plausibility (Section 9.9).

Calculates an Earliest Indicative Delivery Window from the same mandatory
gates used in the political-dependency dimension, treated as a sequential
critical path. A stage with no defensible, disclosed duration leaves the
window open rather than receiving a fabricated estimate.
"""

from __future__ import annotations

from typing import Optional

from ...models import DimensionName, EvidenceState, JurisdictionProfile, Scenario
from .base import make_result

_SOURCE_LABELS = {"source_backed", "jurisdiction_profile_default", "analyst_assumption"}


def assess(
    profile: Optional[JurisdictionProfile],
    scenario: Optional[Scenario],
    instrument_type: str,
    rule_set_version: Optional[str] = None,
):
    stages = profile.gates_for_instrument(instrument_type) if profile is not None else ()
    if profile is None or not stages:
        return make_result(
            dimension=DimensionName.TIMELINE_PLAUSIBILITY,
            finding_code="timeline_not_modelled",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding=f"No staged gate catalog exists for instrument '{instrument_type}' to build a critical path from.",
            missing_information=(f"mandatory_gate_catalog:{instrument_type}",),
            rule_set_version=rule_set_version,
        )
    if scenario is None:
        return make_result(
            dimension=DimensionName.TIMELINE_PLAUSIBILITY,
            finding_code="scenario_not_frozen",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding="No frozen scenario has been supplied for this assessment.",
            missing_information=("scenario",),
            rule_set_version=rule_set_version,
        )

    durations = scenario.gate_durations_months
    sources = scenario.gate_duration_source

    unknown_stages = [s for s in stages if durations.get(s) is None]
    assumed_stages = [s for s in stages if sources.get(s) == "analyst_assumption"]

    if unknown_stages:
        return make_result(
            dimension=DimensionName.TIMELINE_PLAUSIBILITY,
            finding_code="delivery_window_open",
            evidence_state=EvidenceState.PARTIALLY_SPECIFIED,
            plain_language_finding=(
                "One or more stages have no defensible duration, so the delivery "
                "window remains open rather than receiving a fabricated end date."
            ),
            missing_information=tuple(f"duration:{s}" for s in unknown_stages),
            assumptions=tuple(f"duration:{s}" for s in assumed_stages),
            rule_set_version=rule_set_version,
        )

    central = sum(durations[s] for s in stages)  # type: ignore[misc]
    lower = central * 0.85
    upper = central * 1.25

    evidence_state = (
        EvidenceState.SUPPORTED_BUT_CONDITIONAL if assumed_stages else EvidenceState.ESTABLISHED
    )

    return make_result(
        dimension=DimensionName.TIMELINE_PLAUSIBILITY,
        finding_code="earliest_indicative_delivery_window_computed",
        evidence_state=evidence_state,
        plain_language_finding=(
            f"Indicative earliest delivery window: {lower:.0f}-{upper:.0f} months "
            f"(central estimate {central:.0f} months), assuming every stage proceeds "
            "in sequence under the named scenario."
        ),
        assumptions=tuple(f"duration:{s}" for s in assumed_stages),
        rule_set_version=rule_set_version,
        metrics={"lower_months": lower, "central_months": central, "upper_months": upper},
    )
