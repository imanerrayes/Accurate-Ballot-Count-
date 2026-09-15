"""The seven-stage processing pipeline (Section 8, end-to-end operating workflow).

Stage modules, matching the architecture diagram:

1. Election context and jurisdiction profile      -> :mod:`promise_engine.jurisdiction`
2. Party roster and immutable source capture       -> :mod:`.roster`, :mod:`.capture`
3. OCR, translation and atomic promise extraction  -> :mod:`.extraction`
4. Policy specification and comparison matching    -> :mod:`.specification`, :mod:`.matching`
5. Legal/fiscal/capacity/political/timeline/hist.  -> :mod:`.dimensions`
6. Eight-part FRV and explanation packet           -> :mod:`.orchestrator`
7. Human review, publication, appeal and correction -> :mod:`.review`
"""
