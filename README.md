# Political Promise Comparison and Feasibility Engine

`promise_engine/` is a reference implementation of the evidence-first
architecture set out in the supplied product and technical requirements
specification and evidence pack: a jurisdiction-configurable engine that
compares what political parties and candidates have promised and exposes
the conditions that affect delivery. It does not compute a single
"credibility" score, rank parties, or predict voter behaviour.

## Architecture

The package implements the seven-stage pipeline below, governed throughout
by a versioned evidence store, rule registry, and append-only audit log.

| Stage | Module |
|---|---|
| 1. Election context and jurisdiction profile | `promise_engine.jurisdiction`, `promise_engine.models.JurisdictionProfile` |
| 2. Party roster and immutable source capture | `promise_engine.pipeline.roster`, `promise_engine.pipeline.capture` |
| 3. OCR, translation and atomic promise extraction | `promise_engine.pipeline.extraction` |
| 4. Policy specification and comparison matching | `promise_engine.pipeline.specification`, `promise_engine.pipeline.matching` |
| 5. Legal, fiscal, capacity, political, timeline and historical modules | `promise_engine.pipeline.dimensions.*` |
| 6. Eight-part Feasibility Readiness Vector and explanation packet | `promise_engine.pipeline.orchestrator` |
| 7. Human review, publication, appeal and correction | `promise_engine.pipeline.review` |

Governing layer: `promise_engine.evidence_store` (append-only versioning
plus audit log) and `promise_engine.canonical` (deterministic
serialization and content hashing for reproducibility).

## Core design rules encoded in the code

- **Evidence precedes inference.** Every extracted or assessed field
  carries a `ProvenanceType` (stated, authoritative external, analyst
  assumption, derived, unknown, or not applicable). Analyst assumptions are
  never counted toward the stated- or supported-coverage measures
  (`models.PolicySpecification`).
- **Jurisdiction and date are computation inputs.** Legal, fiscal,
  political-dependency, and timeline dimensions refuse to run — returning a
  named `PublicationBlock`, never a zero — when the jurisdiction profile is
  missing, expired, or does not cover the requested election type
  (`jurisdiction.profile_gate`, `jurisdiction.check_hard_preconditions`).
- **Dimensions remain separate.** The eight Feasibility Readiness Vector
  dimensions (`pipeline.dimensions`) are computed independently and are
  never summed, averaged, or blended into a composite score
  (`pipeline.orchestrator.run_assessment`).
- **Missing information is visible.** Dimension modules report
  `missing_information`, `assumptions`, and `blocking_gates` explicitly
  rather than defaulting to a favourable or unfavourable value.
- **Records are append-only.** `evidence_store.VersionedStore` never
  overwrites a prior version; corrections create a new version plus an
  audit-log entry, and `pipeline.review.diff_results` reports exactly which
  dimensions and metrics changed.
- **Results are reproducible.** `canonical.result_hash` computes a
  deterministic hash over the frozen input/output manifest, excluding
  volatile fields (execution ID, timestamp, operator), so re-running the
  same inputs reproduces the same hash.

## Running the demonstration

```bash
python -m promise_engine.cli
```

This wires together an election roster, immutable source capture, atomic
claim extraction and classification, a jurisdiction profile with a legal
rule and fiscal baseline, a frozen political scenario, and prints the
resulting eight-dimension explanation packet for one promise — plus an
abstention example showing publication blocked when no jurisdiction
profile is supplied.

## Running the tests

```bash
pip install pytest
python -m pytest tests/
```

The test suite includes a representative subset of the specification's
acceptance-test catalogue (`tests/test_acceptance.py`), covering source
provenance gating, jurisdiction-profile gating, atomicity of extracted
claims, neutrality across party identity, and reproducibility of the
canonical result hash.

## Scope and limitations of this implementation

This is a reference implementation of the architecture, not the production
system described in the full specification. In particular:

- **Extraction is rule-based, not ML-based.** `pipeline.extraction` uses
  deterministic keyword and regex rules to segment and classify text. It is
  built to make the data model and guardrails testable, not to achieve
  production-grade extraction accuracy across languages and document
  types.
- **Policy specification fields are supplied, not mined.** Turning free
  text into structured cost, timing, and eligibility parameters is a
  substantial NLP and human-review problem in its own right; this
  implementation enforces the provenance *contract* for those fields
  rather than performing the extraction itself.
- **Legal, fiscal, capacity, and dependency rules are illustrative.**
  `JurisdictionProfile` fixtures in this repository are examples for
  testing the gating logic, not maintained legal or fiscal authorities for
  any real jurisdiction.
- **The historical/predictive layer (H4) is out of scope and disabled by
  design.** Only descriptive base rates (H1) are implemented
  (`pipeline.dimensions.historical`); the specification's validation gates
  for a prospective probability (Section 12.3) are not implemented, and no
  code path in this repository produces one.
- **Governance, security, accessibility, and operational requirements**
  (Sections 15–16 of the specification — access control, WCAG 2.2 AA,
  election-sensitive-period freezes, independent oversight) are process and
  deployment requirements outside the scope of this library.

See the requirements specification and evidence pack this implementation is
scoped against for the full product vision, acceptance-test catalogue, and
governance requirements.
