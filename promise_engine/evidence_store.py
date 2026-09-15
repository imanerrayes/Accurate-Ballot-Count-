"""The governed evidence store: append-only versioning and audit log.

This is the "Versioned evidence store, rule registry and audit log" box in
the architecture diagram. It governs and records the party roster and
source-capture stage, and every subsequent stage verifies against it or
writes a correction into it. Nothing in this module ever overwrites a
prior version in place: a "correction" is always a new version plus a
supersession pointer, and every write is mirrored to the audit log.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class AuditEntry:
    sequence: int
    timestamp: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    version: int


class AuditLog:
    """An append-only, time-ordered log of every write to the store."""

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []

    def record(self, actor: str, action: str, entity_type: str, entity_id: str, version: int) -> AuditEntry:
        entry = AuditEntry(
            sequence=len(self._entries),
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            version=version,
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> List[AuditEntry]:
        return list(self._entries)

    def entries_for(self, entity_id: str) -> List[AuditEntry]:
        return [e for e in self._entries if e.entity_id == entity_id]


class VersionedStore(Generic[T]):
    """Append-only, per-entity version history.

    ``put`` always appends a new version; it never replaces an existing one.
    Correction workflows (Section 11.2, REV-005) call ``put`` again with the
    same ``entity_id`` and rely on ``history`` / ``get_version`` to recover
    prior states.
    """

    def __init__(self, entity_type: str, audit_log: AuditLog) -> None:
        self._entity_type = entity_type
        self._audit_log = audit_log
        self._versions: Dict[str, List[T]] = {}

    def put(self, entity_id: str, record: T, actor: str = "system") -> int:
        history = self._versions.setdefault(entity_id, [])
        history.append(record)
        version = len(history)
        self._audit_log.record(actor, "put", self._entity_type, entity_id, version)
        return version

    def get_latest(self, entity_id: str) -> Optional[T]:
        history = self._versions.get(entity_id)
        if not history:
            return None
        return history[-1]

    def get_version(self, entity_id: str, version: int) -> Optional[T]:
        history = self._versions.get(entity_id)
        if not history or version < 1 or version > len(history):
            return None
        return history[version - 1]

    def history(self, entity_id: str) -> List[T]:
        return list(self._versions.get(entity_id, []))

    def all_latest(self) -> Dict[str, T]:
        return {eid: hist[-1] for eid, hist in self._versions.items() if hist}


class EvidenceStore:
    """Container binding every entity's :class:`VersionedStore` to one audit log."""

    def __init__(self) -> None:
        self.audit_log = AuditLog()
        self.sources: VersionedStore = VersionedStore("source_object", self.audit_log)
        self.claims: VersionedStore = VersionedStore("atomic_claim", self.audit_log)
        self.promises: VersionedStore = VersionedStore("promise", self.audit_log)
        self.specifications: VersionedStore = VersionedStore("policy_specification", self.audit_log)
        self.profiles: VersionedStore = VersionedStore("jurisdiction_profile", self.audit_log)
        self.results: VersionedStore = VersionedStore("assessment_result", self.audit_log)
        self.appeals: VersionedStore = VersionedStore("appeal_case", self.audit_log)
