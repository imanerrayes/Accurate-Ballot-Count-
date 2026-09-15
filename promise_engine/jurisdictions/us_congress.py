"""Jurisdiction profile for the U.S. House of Representatives and Senate.

Unlike the synthetic "Demo Federal Republic" fixtures used in tests and
the CLI walkthrough, every rule here cites a real, checkable source: the
Constitution, a Senate standing rule, or a public law. It still is not a
substitute for qualified legal review before any public claim is
published (Section 7.3 requires a named reviewer on every rule, and the
``reviewer`` field below is left ``None`` until one signs off).

Scope: this profile covers the legislative powers of an individual
Senator or Representative acting alone. It does not model committee
chairmanship, leadership positions, or party-conference procedural rules,
all of which can change a specific member's practical influence without
changing the constitutional or standing-rule baseline modelled here.

Primary sources cited below:

- U.S. Const. art. I, § 7, cl. 2-3 (Presentment Clause: passage by both
  chambers, presentment to the President, veto and two-thirds override).
- U.S. Const. art. I, § 7, cl. 1 (Origination Clause: revenue bills must
  originate in the House).
- U.S. Const. art. I, § 5, cl. 2 (each chamber may determine its own
  rules of proceedings — the constitutional basis for Senate Rule XXII).
- Senate Standing Rules, Rule XXII (cloture: three-fifths of Senators
  duly chosen and sworn, i.e. 60 of 100, to end debate on most
  legislation).
- Congressional Budget Act of 1974, Pub. L. 93-344, as amended (creates
  the budget reconciliation process, under which a qualifying bill is not
  subject to a Senate filibuster and passes with a simple majority,
  subject to the Byrd Rule's scope limits).
- U.S. Const. art. I, § 8 (enumerated legislative powers of Congress, as
  a body — not of any single member).
- U.S. Const. art. V (proposing a constitutional amendment requires
  two-thirds of both chambers; ratification requires three-fourths of
  the states and is not an act Congress can complete alone).
- U.S. Const. art. I, § 1 and art. II, § 1 (legislative power is vested
  in Congress; rulemaking implementation of enacted law is an executive
  function, not a legislative one — the basis for treating "direct an
  agency to issue a regulation" as outside any single member's authority).
"""

from __future__ import annotations

from datetime import date

from ..models import (
    AuthorityCode,
    ElectionType,
    JurisdictionProfile,
    LegalRule,
)

#: Instrument type identifiers used throughout this profile and by callers
#: constructing AssessmentInputs for a federal congressional promise.
FEDERAL_LEGISLATION = "federal_legislation"
FEDERAL_TAX_OR_SPENDING = "federal_tax_or_spending"
FEDERAL_BUDGET_RECONCILIATION = "federal_budget_reconciliation"
FEDERAL_REGULATORY_DIRECTIVE = "federal_regulatory_directive"
FEDERAL_CONSTITUTIONAL_AMENDMENT = "federal_constitutional_amendment"

SENATOR = "senator"
REPRESENTATIVE = "representative"

_CONST = "U.S. Const."


def _rule(rule_id: str, actor_type: str, instrument_type: str, power_type: str, result_code: AuthorityCode, source: str) -> LegalRule:
    return LegalRule(
        rule_id=rule_id,
        election_type=ElectionType.LEGISLATIVE_SEAT,
        actor_type=actor_type,
        instrument_type=instrument_type,
        power_type=power_type,
        priority=1,
        result_code=result_code,
        source=source,
        reviewer=None,  # requires qualified legal review before any public claim (Section 7.3)
    )


def build_us_congress_profile(
    congress_number: int,
    effective_from: date,
    effective_to: date | None = None,
    approver: str = "unreviewed_draft",
) -> JurisdictionProfile:
    """Build the jurisdiction profile for one numbered Congress.

    ``congress_number`` is the ordinal Congress this profile covers (the
    119th Congress runs January 2025 - January 2027 and decides the rules
    in force for the 2026 midterm cycle's assessments). Callers should set
    ``effective_to`` to the constitutionally fixed end of that term (the
    Twentieth Amendment fixes the start of each Congress at noon on
    January 3) and re-issue a new profile version each Congress, since the
    House re-adopts its rules package at the start of every term and the
    Senate can amend its standing rules at any time.

    ``approver`` defaults to a placeholder: per Section 7.3 a profile "may
    be published only after its conformance fixtures pass" and a named,
    qualified approver signs off — this function does not itself confer
    that approval.
    """

    rules = (
        # Ordinary legislation: passage requires both chambers plus
        # presentment; an individual member's power is limited to
        # introduction and voting (art. I, § 7, cl. 2-3).
        _rule(
            "us-congress-senator-legislation",
            SENATOR,
            FEDERAL_LEGISLATION,
            "propose_or_introduce",
            AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
            f"{_CONST} art. I, § 7, cl. 2-3",
        ),
        _rule(
            "us-congress-representative-legislation",
            REPRESENTATIVE,
            FEDERAL_LEGISLATION,
            "propose_or_introduce",
            AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
            f"{_CONST} art. I, § 7, cl. 2-3",
        ),
        # Revenue and appropriations measures: the Origination Clause
        # requires these to originate in the House. A Senator may only
        # propose or concur in amendments to a House-originated measure,
        # not originate one.
        _rule(
            "us-congress-senator-tax-or-spending",
            SENATOR,
            FEDERAL_TAX_OR_SPENDING,
            "appropriate_or_raise_revenue",
            AuthorityCode.ADVOCACY_OR_NEGOTIATION_ONLY,
            f"{_CONST} art. I, § 7, cl. 1",
        ),
        _rule(
            "us-congress-representative-tax-or-spending",
            REPRESENTATIVE,
            FEDERAL_TAX_OR_SPENDING,
            "appropriate_or_raise_revenue",
            AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
            f"{_CONST} art. I, § 7, cl. 1",
        ),
        # Budget reconciliation: a distinct legislative vehicle under the
        # Congressional Budget Act that is not subject to the Senate
        # filibuster. Still requires ordinary bicameral passage and
        # presentment; an individual member's authority is unchanged.
        _rule(
            "us-congress-senator-reconciliation",
            SENATOR,
            FEDERAL_BUDGET_RECONCILIATION,
            "appropriate_or_raise_revenue",
            AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
            "Congressional Budget Act of 1974, Pub. L. 93-344, as amended",
        ),
        _rule(
            "us-congress-representative-reconciliation",
            REPRESENTATIVE,
            FEDERAL_BUDGET_RECONCILIATION,
            "appropriate_or_raise_revenue",
            AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
            "Congressional Budget Act of 1974, Pub. L. 93-344, as amended",
        ),
        # Directing an executive agency to issue a regulation is an
        # executive-branch rulemaking act, not a legislative one. A member
        # of Congress may request, pressure, or conduct oversight, but
        # cannot issue the directive.
        _rule(
            "us-congress-senator-regulatory-directive",
            SENATOR,
            FEDERAL_REGULATORY_DIRECTIVE,
            "regulate",
            AuthorityCode.AUTHORITY_HELD_ELSEWHERE,
            f"{_CONST} art. I, § 1; art. II, § 1",
        ),
        _rule(
            "us-congress-representative-regulatory-directive",
            REPRESENTATIVE,
            FEDERAL_REGULATORY_DIRECTIVE,
            "regulate",
            AuthorityCode.AUTHORITY_HELD_ELSEWHERE,
            f"{_CONST} art. I, § 1; art. II, § 1",
        ),
        # A constitutional amendment requires two-thirds of both chambers
        # to propose, and three-fourths of the states to ratify. No member
        # of Congress, and no Congress as a whole, can finally adopt one.
        _rule(
            "us-congress-senator-constitutional-amendment",
            SENATOR,
            FEDERAL_CONSTITUTIONAL_AMENDMENT,
            "legislate",
            AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
            f"{_CONST} art. V",
        ),
        _rule(
            "us-congress-representative-constitutional-amendment",
            REPRESENTATIVE,
            FEDERAL_CONSTITUTIONAL_AMENDMENT,
            "legislate",
            AuthorityCode.LEGISLATIVE_INITIATIVE_ONLY,
            f"{_CONST} art. V",
        ),
    )

    mandatory_gate_catalog = {
        FEDERAL_LEGISLATION: (
            "house_passage",
            "senate_passage",
            "senate_cloture",
            "presidential_signature_or_veto_override",
        ),
        FEDERAL_TAX_OR_SPENDING: (
            "house_origination_and_passage",
            "senate_passage",
            "senate_cloture",
            "presidential_signature_or_veto_override",
        ),
        FEDERAL_BUDGET_RECONCILIATION: (
            "house_passage",
            "senate_passage_simple_majority",
            "byrd_rule_compliance",
            "presidential_signature_or_veto_override",
        ),
        FEDERAL_REGULATORY_DIRECTIVE: (
            "executive_agency_rulemaking_notice_and_comment",
        ),
        FEDERAL_CONSTITUTIONAL_AMENDMENT: (
            "two_thirds_house_passage",
            "two_thirds_senate_passage",
            "three_fourths_state_ratification",
        ),
    }

    return JurisdictionProfile(
        profile_id=f"profile-us-congress-{congress_number}th",
        version="1.0.0",
        jurisdiction="United States (Congress)",
        election_types=(ElectionType.LEGISLATIVE_SEAT,),
        effective_from=effective_from,
        effective_to=effective_to,
        approver=approver,
        government_system="presidential",
        legal_rules=rules,
        fiscal_baseline=None,  # a Congressional Budget Office baseline must be supplied per assessment; not fabricated here
        mandatory_gate_catalog=mandatory_gate_catalog,
    )
