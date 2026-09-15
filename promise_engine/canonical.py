"""Canonical serialization and content hashing (Section 15.1).

Reproducibility requires that the same frozen input manifest produce the
same result hash. This module converts dataclasses (including nested
enums, tuples, and mappings) into a deterministic JSON representation and
hashes it. Volatile fields — execution UUID, timestamp, host, operator —
must never be passed in; callers pass only the canonical, frozen inputs
and outputs.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import date
from enum import Enum
from typing import Any


def _default(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not canonicalizable")


def canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization: sorted keys, fixed separators."""

    return json.dumps(
        obj,
        default=_default,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def content_hash(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def result_hash(obj: Any) -> str:
    """Hash a canonical object graph (an assessment result, a manifest, ...)."""

    return content_hash(canonical_json(obj).encode("utf-8"))
