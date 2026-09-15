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
| 1. Election context and jurisdiction profile | `promise_engine.jurisdiction`, `promise_engine.models.JurisdictionProfile`, `promise_engine.jurisdictions.us_congress`, `promise_engine.scope` |
| 2. Party roster and immutable source capture | `promise_engine.pipeline.roster`, `promise_engine.pipeline.capture` |
| 3. OCR, translation and atomic promise extraction | `promise_engine.pipeline.extraction` |
| 4. Policy specification and comparison matching | `promise_engine.pipeline.specification`, `promise_engine.pipeline.matching` |
| 5. Legal, fiscal, capacity, political, timeline and historical modules | `promise_engine.pipeline.dimensions.*` |
| 6. Eight-part Feasibility Readiness Vector and explanation packet | `promise_engine.pipeline.orchestrator` |
| 7. Human review, publication, appeal and correction | `promise_engine.pipeline.review` |

Governing layer: `promise_engine.evidence_store` (append-only versioning
plus audit log) and `promise_engine.canonical` (deterministic
serialization and content hashing for reproducibility).

Scope selection: `promise_engine.scope` (which races and which sources —
see "Scoping real elections" below) and `promise_engine.jurisdictions.*`
(cited jurisdiction profiles for a real legislature, starting with the
U.S. Congress).

## Scoping real elections

The engine is designed to run against any combination of races, not one
fixed roster. `promise_engine.scope` generalizes race and source-policy
selection into two composable objects instead of a separate code path per
scenario:

- `ScopeQuery` — which races: one race, a state's delegation, every
  competitive Senate seat, one race per region, an issue across races, and
  so on.
- `CollectionPolicy` — which source tiers to collect (official sites only,
  plus platforms, plus speeches and social media) and the collection time
  window (full cycle, or only after each party's nominee is settled).

| # | Scenario | Constructor |
|---|---|---|
| 1-2 | One Senate race / one House district | `scope.one_race(race_id)` |
| 3 | One competitive Senate race per region | `scope.one_competitive_race_per_region(OfficeType.US_SENATE, cycle)` |
| 4-5 | Selected Senate races / House districts | `scope.selected_races([...])` |
| 6 | One state's Senate and House races | `scope.one_state(state, cycle)` |
| 7 | One state's federal and state-level races | `scope.one_state(state, cycle, office_types={...GOVERNOR, STATE_LEGISLATURE_*})` |
| 8-11 | All competitive/all Senate or House races | `scope.all_of_office(office_type, cycle, competitive_only=...)` |
| 12 | All federal congressional races | `scope.all_federal_congressional(cycle, competitive_only=...)` |
| 13-14 | One issue across all races / selected states | `scope.issue_across_races(topics, cycle, states=...)` |
| 15-16 | Party platforms rather than candidates / D vs. R nationally | `scope.group_by_national_party(entities)` over any resolved scope |
| 17 | Track by office level | the `office_types` filter on any `ScopeQuery` |
| 20 | Official campaign websites only | `scope.OFFICIAL_SOURCES_ONLY` |
| 21 | Official sources plus manifestos/platforms | `scope.OFFICIAL_PLUS_PLATFORMS` |
| 22 | Official sources plus speeches, interviews, social media | `scope.OFFICIAL_PLUS_SPEECHES_AND_SOCIAL` |
| 23-24 | Full cycle / only after nomination | `CollectionPolicy(window_start=..., only_after_nomination=True, nomination_dates={...})` |

Scenarios 18-19 (database-first vs. feasibility-engine-first) and 25-35
(product surface: research database, public site, API, dashboard, and so
on) are build-sequencing and deployment decisions, not scope filters —
they're addressed by the build plan below, since every surface is a thin
layer over the same `promise_engine` core.

`Race`, the record `ScopeQuery` filters over, holds no built-in data: its
`competitiveness_rating` and `competitiveness_source` fields exist so a
caller can cite a named rating service (Cook Political Report, Sabato's
Crystal Ball, Inside Elections) verbatim, and `entity_ids` links to
candidates populated from FEC candidate filings. `promise_engine.data.races_2026`
is a first real import against this model — see "The 2026 data import"
below for exactly what it covers and what it doesn't.

## Recommended default scope and build plan

Adopted default: **a national 2026 U.S. midterm promise database covering
all Senate races and selected competitive House races**, collected under
`scope.OFFICIAL_PLUS_PLATFORMS` (official campaign sites, party pages, and
adopted platforms; speeches, interviews, and social media added only as an
explicit, separately-labelled extension per COL-003, never silently
blended in).

Build sequence, matching the specification's own phased delivery plan
(Section 18):

1. **Stage 1 — collect and compare.** Roster, immutable source capture,
   atomic-claim extraction, and side-by-side comparison. No legal, fiscal,
   or historical claim is made yet. This is what `pipeline.roster` through
   `pipeline.matching` already implement.
2. **Stage 2 — legal authority, procedure, budget, and implementation
   dependencies.** `jurisdictions.us_congress` is the first real
   jurisdiction profile for this stage: it encodes actual House and Senate
   procedure (bicameral passage, the Origination Clause, Senate cloture,
   budget reconciliation) with citations, replacing the synthetic "Demo
   Federal Republic" fixture used in tests. A Congressional Budget Office
   baseline still needs to be supplied per assessment (Section 9.6); this
   profile does not fabricate one.
3. **Stage 3 — historical fulfillment and validated feasibility
   estimates.** Requires the governed, dual-coded historical pledge corpus
   described in Section 12.1 before `pipeline.dimensions.historical` has
   real data to run on, and — per the specification's own gating logic —
   the prospective-probability layer (H4) stays disabled regardless, since
   its validation gates (Section 12.3) are a separate research program.

## The 2026 data import

`promise_engine/data/races_2026.py` and `entities_2026.py` are built from
two merged extraction batches, both dated 2026-09-15 — read their module
docstrings and `data/extracted/2026-09-15/PROVENANCE.md` for the full
trail. In summary:

- **Batch 1 (assistant, WebSearch-only):** partial — 9 of 35 Senate races
  rated, 18 House Toss Up races. WebFetch (direct page retrieval) was
  blocked by this environment's network egress policy for every domain
  tried; everything came from WebSearch's synthesized snippets, which is
  lossier than a direct table fetch.
- **Batch 2 (repository owner, manual extraction):** filled the rest.
  **Senate coverage is now complete** — all 35 races (33 Class II plus the
  Florida and Ohio specials) carry a cited Cook Political Report or
  Sabato's Crystal Ball rating, and `resolve_scope(..., competitive_only=True)`
  now correctly returns 12 races (AK, GA, IA, KS, ME, MI, MN, NC, NE, NH,
  OH, TX), not the 8 batch 1 could see. **House coverage expanded** from
  18 Toss-Up-only races to **70 races across five Cook tiers** (Likely D,
  Lean D, Toss Up, Lean R, Likely R) — every one of batch 1's original 18
  reappears here, several with an updated rating once redistricting or a
  retirement (e.g. Bacon in NE-02, Golden in ME-02) was reflected. It is
  still 70 of 435 House seats, not full coverage.
- **New: FEC candidate data.** `entities_2026.py` loads 673 Senate
  candidate filings from a real FEC export. Two real limitations shape
  it, documented in its module docstring: the export carries no
  per-row election-year column, so "filed for this state's Senate race at
  some point in FEC history" and "on the 2026 ballot" are not the same
  claim from this file alone; and the raw data contains at least two
  multi-state nuisance-filer patterns — "Gavin Solomon" filed as a
  Republican Senate candidate in **40 different states**, "Owen Nicholas
  Carlson" in 17, under a different party label in nearly every one.
  `detect_multi_state_filers` catches exactly this (any name in 4+ states)
  and `clean_senate_candidates` excludes it, rather than the engine
  silently treating 40 filings by one person as 40 real candidacies. None
  of this is merged into `Race.entity_ids` yet — that needs the cycle
  confirmation the export doesn't carry.

Treat both modules as a timestamped snapshot, not a maintained feed:
re-import before publishing anything built on them, since ratings and
candidacies change continuously between now and the November 2026
election. A future extraction should land in a new dated
`data/extracted/<date>/` directory and be merged in, never overwrite a
prior batch's files.

## How to get me more data

This session's network policy blocks direct page fetches to every source
site tried (confirmed via both the fetch tool and a raw `curl`, which got
a 403 from the egress proxy — the destination host isn't on this
session's allowed list, not a code problem). Two ways around that:

**Option A — you extract, I ingest.** `promise_engine/data/import_tools.py`
loads plain CSVs into the same `Race`/`PoliticalEntity` records the engine
already uses. The first round (see "The 2026 data import" above) closed
the two biggest gaps — Senate ratings and Senate candidates — so what's
left is narrower:

1. **House coverage beyond 70 races.** `promise_engine/data/templates/house_ratings_template.csv`
   is still the right template; [Cook's House ratings](https://www.cookpolitical.com/ratings/house-race-ratings)
   covers a subset of 435 seats even at its fullest, so this will never
   be "complete" the way Senate now is — just progressively wider.
2. **House candidate filings.** No House equivalent of `entities_2026.py`
   exists yet. Same template and source as before:
   [FEC candidate filings](https://www.fec.gov/data/candidates/?election_year=2026&office=H).
3. **Cycle confirmation on the Senate candidate data.** `entities_2026.py`'s
   673 rows can't distinguish "on the 2026 ballot" from "has an FEC
   Senate filing on record" (see its module docstring) — the export has
   no election-year column. Re-pulling with that column included, or
   spot-checking against https://www.fec.gov/data/candidate/<id>/ for the
   races you care about most, would close that gap.
4. **A second rating source for cross-checking.** Sabato's Crystal Ball
   (https://centerforpolitics.org/crystalball/2026-senate/,
   .../2026-house/) or Inside Elections, run against the same
   `senate_ratings_template.csv` / `house_ratings_template.csv` shape —
   useful wherever Cook and another rater disagree.

Once filled, load and merge a file like this:

```python
from promise_engine.data.import_tools import load_senate_ratings_csv, merge_ratings_into_universe
from promise_engine.data.races_2026 import SENATE_UNIVERSE_2026

updates = load_senate_ratings_csv("senate_ratings_filled.csv", cycle=2026)
universe = merge_ratings_into_universe(SENATE_UNIVERSE_2026, updates)
```

If filling a CSV is more friction than it's worth, just paste the raw
ratings table text from the page and I'll parse it the way I did for this
session's initial import — less reliable than a CSV, so I'll flag
anything ambiguous rather than guess.

**Option B — API, where one actually exists.** The FEC publishes a free,
public, documented API (no API for Cook Political Report, Sabato's, or
Inside Elections exists — those are proprietary products; there is no
"just connect via API" option for them). `promise_engine/data/connectors/fec.py`
is a real, working connector against `api.open.fec.gov` — not a stub —
that this session cannot execute (same egress block as above), but you or
any environment that can reach that host can:

```python
from promise_engine.data.connectors.fec import fetch_candidates

senate_candidates_ia = fetch_candidates(office="S", cycle=2026, state="IA")
```

Get a free key at https://api.data.gov/signup/ (`DEMO_KEY` works for
light testing at a lower rate limit). Hand me the output — as Python
objects if you're running it in a notebook I can read, or dumped to the
`fec_candidates_template.csv` shape — and it merges in the same way.

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
- **Most legal, fiscal, capacity, and dependency rules are illustrative;
  one is real but unreviewed.** Test and demo fixtures use a synthetic
  "Demo Federal Republic." `jurisdictions.us_congress` is a real profile
  for the U.S. House and Senate with citations to the Constitution, Senate
  Standing Rules, and the Congressional Budget Act — but Section 7.3
  requires a named, qualified legal reviewer on every rule before publication,
  and this profile's `reviewer` field is `None` until one signs off. It is
  not a substitute for that review, and it carries no fiscal baseline (a
  Congressional Budget Office baseline must be supplied per assessment).
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
