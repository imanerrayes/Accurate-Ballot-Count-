"""API connectors that produce normalized records for `import_tools.py` or
direct use with `promise_engine.scope`.

A connector is any callable that returns a tuple of
:class:`~promise_engine.models.PoliticalEntity` or
:class:`~promise_engine.scope.Race` records — the same shape
``import_tools`` loaders produce from a CSV, so callers don't need to care
whether a record came from an API or a hand-filled spreadsheet.

Only one connector exists so far (`fec`), because the FEC is the only
party in this engine's source list with a free, public, documented API.
Cook Political Report, Sabato's Crystal Ball, and Inside Elections publish
no API; getting their ratings requires either manual extraction (see
README.md, "How to get me more data") or a licensed data feed, and no
connector here pretends otherwise.
"""
