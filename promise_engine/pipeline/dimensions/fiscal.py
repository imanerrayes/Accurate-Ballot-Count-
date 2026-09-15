"""Dimension 3: fiscal and economic plausibility (Section 9.6).

Runs only when the jurisdiction profile supplies a fiscal baseline and the
policy specification supplies enough stated or evidenced parameters for
the static direct effect formula. Everything else — behavioural effects,
administrative cost, financing, and macroeconomic feedback — is reported
as a separate, optionally-populated component; none of them is invented to
fill a gap.
"""

from __future__ import annotations

from typing import Optional

from ...models import (
    DimensionName,
    EvidenceState,
    FiscalBaseline,
    PolicySpecification,
    ProvenanceType,
)
from .base import make_result

_REQUIRED_FIELDS = ("target_or_eligibility", "quantity_or_rate", "start_date")


def _numeric_evidenced(spec: PolicySpecification, field_name: str) -> Optional[float]:
    fv = spec.fields.get(field_name)
    if fv is None or not fv.is_evidenced():
        return None
    try:
        return float(fv.value)
    except (TypeError, ValueError):
        return None


def assess(
    spec: Optional[PolicySpecification],
    baseline: Optional[FiscalBaseline],
    fixed_delivery_cost: float = 0.0,
    participation_rate: float = 1.0,
    rule_set_version: Optional[str] = None,
):
    if baseline is None:
        return make_result(
            dimension=DimensionName.FISCAL_PLAUSIBILITY,
            finding_code="fiscal_module_disabled",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding=(
                "The jurisdiction profile does not supply a fiscal baseline, "
                "accounting basis, and horizon, so no costing can be run."
            ),
            missing_information=("fiscal_baseline",),
            rule_set_version=rule_set_version,
        )

    if spec is None:
        return make_result(
            dimension=DimensionName.FISCAL_PLAUSIBILITY,
            finding_code="not_costable_from_public_detail",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding="No policy specification exists for this promise.",
            missing_information=("policy_specification",),
            rule_set_version=rule_set_version,
        )

    missing = [f for f in _REQUIRED_FIELDS if _numeric_evidenced(spec, f) is None and f != "start_date"]
    start_date_fv = spec.fields.get("start_date")
    if start_date_fv is None or not start_date_fv.is_evidenced():
        missing.append("start_date")

    eligible_units = _numeric_evidenced(spec, "target_or_eligibility")
    unit_amount = _numeric_evidenced(spec, "quantity_or_rate")

    funding_fv = spec.fields.get("funding_or_offset")
    funding_unspecified = funding_fv is None or not funding_fv.is_evidenced()

    if eligible_units is None or unit_amount is None:
        return make_result(
            dimension=DimensionName.FISCAL_PLAUSIBILITY,
            finding_code="not_costable_from_public_detail",
            evidence_state=EvidenceState.NOT_ASSESSABLE,
            plain_language_finding=(
                "Material inputs (eligible population and unit amount) are "
                "not stated or evidenced, so no currency total is produced."
            ),
            missing_information=tuple(missing),
            rule_set_version=rule_set_version,
        )

    static_direct_effect = eligible_units * unit_amount * participation_rate + fixed_delivery_cost

    conditions = []
    if funding_unspecified:
        conditions.append("funding_unspecified")

    metrics = {
        "static_direct_effect": static_direct_effect,
        "direct_behavioural_effect": 0.0,
        "administrative_implementation_effect": fixed_delivery_cost,
        "financing_and_debt_interest_effect": 0.0,
        "macroeconomic_feedback": 0.0,
    }

    evidence_state = (
        EvidenceState.PARTIALLY_SPECIFIED if funding_unspecified else EvidenceState.SUPPORTED_BUT_CONDITIONAL
    )

    return make_result(
        dimension=DimensionName.FISCAL_PLAUSIBILITY,
        finding_code="static_direct_effect_computed",
        evidence_state=evidence_state,
        plain_language_finding=(
            f"Static direct annual effect is {static_direct_effect:,.2f} {baseline.currency} "
            f"under {baseline.accounting_basis} accounting, {baseline.price_basis} prices. "
            "Direct behavioural, financing, and macroeconomic effects are not costed here."
        ),
        conditions=tuple(conditions),
        missing_information=tuple(missing),
        rule_set_version=rule_set_version,
        metrics=metrics,
    )
