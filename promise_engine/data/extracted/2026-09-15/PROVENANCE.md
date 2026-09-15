# Extraction batch: 2026-09-15

Manually extracted by the repository owner (not the assistant — WebFetch is
blocked in the assistant's environment; see README.md, "How to get me more
data") and handed back as three CSVs, saved here verbatim as the
immutable source-of-record for this batch.

- **`senate_ratings.csv`** — Cook Political Report, Senate Race Ratings,
  print snapshot dated 2026-08-20 (https://www.cookpolitical.com/print/ratings/races/senate).
  26 of the 26 previously-blank Senate races (see the prior session's
  `senate_ratings_template.csv`), completing Cook coverage for all 35
  seats up in 2026 when combined with the assistant's own earlier
  8-race, WebSearch-sourced import.
- **`house_ratings.csv`** — Cook Political Report, House Race Ratings,
  print snapshot dated 2026-09-11 (https://www.cookpolitical.com/print/ratings/races/house).
  70 races across five tiers (Likely D, Lean D, Toss Up, Lean R, Likely R).
  Supersedes the assistant's prior 18-race, June-18-snapshot import — every
  one of those 18 races reappears here, several with an updated rating
  (e.g. NE-02 and ME-02 moved from Toss Up to Lean/Likely once their
  incumbents' retirements were reflected).
- **`fec_senate_candidates.csv`** — FEC candidate filings for Senate
  (https://www.fec.gov/data/candidates/?election_year=2026&office=S).
  674 rows, as filed — duplicates, historical carryover registrations, and
  at least two apparent multi-state nuisance-filer patterns included
  verbatim. See `promise_engine/data/entities_2026.py` for how those are
  flagged rather than silently treated as real per-state candidacies, and
  for the limitation this file does not carry an `election_year` column
  per row, so "registered for this state's Senate race at some point" and
  "on the 2026 ballot" are not the same claim from this file alone.

Nothing in this directory is edited after being saved here — a
correction means adding a new dated batch directory, per the engine's own
append-only evidence rule (Section 11.2 of the requirements
specification).
