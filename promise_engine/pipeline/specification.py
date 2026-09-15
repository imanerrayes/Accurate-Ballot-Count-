"""Stage 4a: policy specification construction (Section 9.4, Section 11.2).

Turning free text into structured parameters (amounts, dates, eligibility
rules) is a substantial NLP/human-review problem in its own right and is
out of scope for this reference implementation. This module instead
enforces the *contract*: every field a caller supplies must carry a
provenance type, analyst assumptions are visibly labelled and never counted
as evidence, and the two coverage measures required by Section 9.4 are
computed the same way every time.
"""

from __future__ import annotations

from typing import Mapping

from ..models import FieldValue, PolicySpecification, ProvenanceType, SPECIFICATION_FIELDS, new_id


def build_policy_specification(promise_id: str, fields: Mapping[str, FieldValue]) -> PolicySpecification:
    """Construct a :class:`PolicySpecification` from provenance-tagged fields.

    Raises if a field name is not one of :data:`SPECIFICATION_FIELDS`, so a
    typo in a field name cannot silently fail to count toward coverage.
    """

    unknown = set(fields) - set(SPECIFICATION_FIELDS)
    if unknown:
        raise ValueError(f"not a recognised specification field: {sorted(unknown)}")
    mismatched = [name for name, fv in fields.items() if fv.field != name]
    if mismatched:
        raise ValueError(f"FieldValue.field does not match its key: {mismatched}")

    return PolicySpecification(spec_id=new_id("spec"), promise_id=promise_id, fields=dict(fields))


def field(name: str, value, provenance: ProvenanceType, source_ref: str | None = None, unit: str | None = None) -> FieldValue:
    """Convenience constructor pairing a field name with its provenance."""

    if name not in SPECIFICATION_FIELDS:
        raise ValueError(f"not a recognised specification field: {name}")
    return FieldValue(field=name, value=value, provenance=provenance, source_ref=source_ref, unit=unit)
