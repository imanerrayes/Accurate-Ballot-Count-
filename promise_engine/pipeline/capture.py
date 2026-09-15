"""Stage 2b: immutable source capture (Section 8, step 2; COL-004, COL-005)."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Optional

from ..evidence_store import EvidenceStore
from ..models import SourceObject, SourceTier, new_id


def _hash_payload(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def capture_source(
    store: EvidenceStore,
    canonical_url: str,
    payload: bytes,
    source_tier: SourceTier,
    retrieval_date: date,
    publication_date: Optional[date] = None,
    rights_or_access: Optional[str] = None,
    existing_source_id: Optional[str] = None,
) -> SourceObject:
    """Capture a source document as a new, immutable version.

    If ``existing_source_id`` names a source already in the store, a
    re-crawl never overwrites it: this creates a new version and marks the
    prior version as superseded (COL-005), preserving both.
    """

    content_hash = _hash_payload(payload)

    if existing_source_id is not None:
        prior = store.sources.get_latest(existing_source_id)
        if prior is not None and prior.content_hash == content_hash:
            # No change since the last capture; do not create a spurious version.
            return prior
        version = (prior.version + 1) if prior else 1
        source = SourceObject(
            source_id=existing_source_id,
            canonical_url=canonical_url,
            retrieval_date=retrieval_date,
            content_hash=content_hash,
            source_tier=source_tier,
            version=version,
            publication_date=publication_date,
            rights_or_access=rights_or_access,
        )
        store.sources.put(existing_source_id, source)
        return source

    source_id = new_id("src")
    source = SourceObject(
        source_id=source_id,
        canonical_url=canonical_url,
        retrieval_date=retrieval_date,
        content_hash=content_hash,
        source_tier=source_tier,
        publication_date=publication_date,
        rights_or_access=rights_or_access,
    )
    store.sources.put(source_id, source)
    return source
