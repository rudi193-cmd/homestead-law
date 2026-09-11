"""The venture pack — an accelerator application, and the company's own
calendar, if the application converts (L8-venture, Wave 8).

Same posture as `grant.py` beside it: track, never draft, never file, never
compute a tax (decision 8, provisional I-44). Two things share one pack
because the operator picks one matter for both, and open items (b)/(c) of
the Wave 8 plan paragraph (whether the company exists yet) mean neither half
may require the other filled in first: **the application**
(`accelerator`/`batch`/interview/decision/`application_status`) and
**the company's compliance calendar** (formation, registered agent, state
filings, founders, SAFEs, equity grants). `NOTICE` is the sentence every
surface renders; `tests/test_i44_no_drafting.py` is the same guard
`bankruptcy.py` is held to, extended here with a
form/incorporate/file-with-the-state phrase.

## `JURISDICTIONS`, and a correction to the engine's `RULES`

`JURISDICTION="US-DE"`, `JURISDICTIONS=("US-DE","US-OR")` — Delaware, where a
PBC is chartered (8 Del. C. §§ 361-368), and Oregon, where the company does
business. ~~Both rows are absent from `homestead.keep.dates.RULES`~~ —
correction, 2026-09-12: `RULES` (engine 0.11.0) holds `US-federal`, `US-NM`
**and `US-OR`** (added for custody's relocation); only `US-DE` is genuinely
absent. No practical effect: this pack declares no `court_days`/
`court_days_before`/`business_days` template for either jurisdiction — the
one template below is `calendar_days`, which reads no jurisdiction calendar
at all, so nothing here ever reaches `RULES`. A future court-day template
could use Oregon's row; one in Delaware would refuse (I-42) until
`E8-jurisdictions-de-or-corp` adds it — expected to stay `docs:`, since
Delaware's own corporate deadlines (annual report, franchise tax) are fixed
statutory dates, not counting rules, and so are entered here like every
other date.

## Every date is entered, except one

Decision 4's counting rules exist for periods a court or federal statute
measures from an event; nothing else here is that — an accelerator sets its
own dates administratively, state filing deadlines are fixed calendar
dates, and 8 Del. C. § 366(b) fixes only a floor ("no less than biennially")
with the certificate/bylaws setting the cadence. So every one is `L1` and
entered, the shape `workers_comp.py`'s NM rules took when none had a
verifiable count either. The one exception is federal tax law: 26 U.S.C.
§ 83(b)(2)'s 30-day election window after a stock transfer
(`_PROVENANCE_83B`, `TEMPLATES`).

## `founder.vesting_start` cannot anchor a template — `grant_date` does

`rules.compute(store, matter, instance, template_name, ...)` takes no
sub-id: it reads an anchor at `(matter, anchor_field, instance)`, the bare
instance, never `instance.sub`. `founder.vesting_start` is `REPEATABLE`
(decision 2) — one value per founder at `(matter, "founder.vesting_start",
"<instance>.<sub>")`, a key `compute` cannot form — so anchoring there would
not refuse cleanly, it would read the wrong key and answer
`AnchorUnavailable` for every founder ("no grant date" instead of "cannot
address one founder's date"). This bite adds `grant_date`, a top-level `L1`
field: the date stock was transferred to *a* person, entered once per
instance, the anchor `election-83b` actually reads.
`founder.vesting_start`/`founder.election_83b_deadline` stay exactly as the
plan names them — entered, one pair per founder; only the computed template
is single-anchor.

## Why so much of this pack is `L1` with no public docket behind it

Custody/bankruptcy's `L1` fields lean on a public forum (step 1); an
accelerator application has none (a Delaware formation instrument and
registered agent *are* filed with the Secretary of State, which is why the
compliance dates sit at `L1` on that ground). Step 3 classifies the rest: an
application date, a formation date, a vesting start or an entered
compliance deadline names no one's protected circumstance and resolves to
the venture's own calendar — bankruptcy's `plan_payment_due_day` states the
same ("an administrative term ... no protected category attaches to a
day-of-month"). A field that names a person/entity (`legal_name`,
`registered_agent`, `founder.name`, `safe.investor`, `equity_grant.grantee`,
`advisor.name`) or an argue-up figure (`founder.equity_pct`,
`safe.amount`/`valuation_cap`/`discount`, `equity_grant.amount`) sits at
`L3`/`L4` instead — custody's `opposing_party`/bankruptcy's `creditor.name`
reasoning.

## The plan-period interaction flag

`plan_period.flag` scans every other matter for `SIGNAL_FIELDS` presence.
This bite corrects the two field names this pack can actually produce a
record under: `safe.amount`/`equity_grant.amount`, not the bare
`"safe"`/`"equity_grant"` the frozenset held before — both groups are
`REPEATABLE`, so every field either stores is dotted. `revenue_start` needed
no change: this pack's one top-level, non-repeatable signal field.
"""
from __future__ import annotations

import re
from typing import Any

from homestead.keep.rungs import Rung, classify_schema

__all__ = [
    "MATTER", "JURISDICTION", "JURISDICTIONS", "REPEATABLE", "SCHEMA",
    "FIELDS", "NOTICE", "TEMPLATES",
    "APPLICATION_STATUSES", "ENTITY_TYPES", "REGISTRATION_KINDS",
    "InvalidChoice", "InvalidLabel", "validate_value",
]

MATTER = "venture"
JURISDICTION = "US-DE"
#: See the module docstring's "Both JURISDICTIONS rows" section: `US-DE` is
#: genuinely absent from the engine's `RULES`; `US-OR` (added for custody's
#: relocation) is not, though this pack declares no template that would ever
#: reach it.
JURISDICTIONS: tuple[str, ...] = ("US-DE", "US-OR")


def _field(rung: Rung, why: str, *, derived: str | None = None) -> dict[str, Any]:
    decl = {"rung": rung, "matter": MATTER, "jurisdiction": JURISDICTION, "why": why}
    if derived is not None:
        decl["derived"] = derived
    return decl


#: The closed venture schema — the application, then the company. See the
#: module docstring's "Why so much of this pack is L1" section for the
#: general reasoning; each field's own `why` states which step it turns on.
SCHEMA: dict[str, dict[str, Any]] = {
    "jurisdiction": _field(
        Rung.L1,
        "the forum's identity is public in this matter's forum (step 1); "
        "read by deadline arithmetic (decision 1).",
    ),
    # ── the application ──────────────────────────────────────────────────
    "accelerator": _field(
        Rung.L2,
        "which program the household applied to — a coarse organizational "
        "fact, no person resolved (step 2 no).",
    ),
    "batch": _field(
        Rung.L2, "the program's cohort label — same coarse-tag posture as "
        "accelerator (step 2 no).",
    ),
    "application_submitted": _field(
        Rung.L1,
        "an administrative date of the household's own process, no party "
        "or category (step 3 no); see the module docstring.",
    ),
    "interview_date": _field(
        Rung.L1, "same administrative posture as application_submitted "
        "(step 3 no).",
    ),
    "decision_date": _field(
        Rung.L1, "same posture as application_submitted; the decision's "
        "content is application_status, entered separately (step 3 no).",
    ),
    "application_status": _field(
        Rung.L2,
        "one of APPLICATION_STATUSES — a closed tag (step 2 no); "
        "'preparing' names the operator's own readiness, never an act of "
        "drafting or filing (decision 8).",
    ),
    # ── the company ──────────────────────────────────────────────────────
    "legal_name": _field(
        Rung.L3,
        "the company's own name resolves to a specific entity (step 2 "
        "yes), no protected category of its own (step 3 no) — custody's "
        "opposing_party posture.",
        derived="A company name is on file",
    ),
    "entity_type": _field(
        Rung.L2, "one of ENTITY_TYPES — a structural fact, no party named "
        "(step 2 no).",
    ),
    "public_benefit": _field(
        Rung.L3,
        "the certificate's stated purpose (8 Del. C. § 362) resolves to "
        "the company (step 2 yes); specific certificate language, not a "
        "coarse tag, so it sits at L3 rather than L2.",
        derived="A stated public benefit is on file",
    ),
    "benefit_report_due": _field(
        Rung.L1,
        "the biennial report's due date (8 Del. C. § 366(b)) is entered "
        "from the certificate/bylaws cadence — the statute fixes only a "
        "floor, so there is no period to count (step 3 no).",
    ),
    "formation_state": _field(
        Rung.L2, "the state of incorporation — coarse geography, no party "
        "resolved (step 2 no).",
    ),
    "formation_date": _field(
        Rung.L1, "the certificate's filing date is on file with the "
        "Delaware Secretary of State (step 1).",
    ),
    "grant_date": _field(
        Rung.L1,
        "the date stock was transferred to a person — an administrative "
        "equity-calendar fact, no category (step 3 no). The anchor "
        "election-83b reads; see the module docstring for why.",
    ),
    "ein": _field(
        Rung.L5,
        "an EIN is key material — sealed, L5 has no override (step 4). No "
        "derived form: L5 renders nowhere, on no surface, in any form.",
    ),
    "registered_agent": _field(
        Rung.L3,
        "filed with the Delaware Secretary of State (step 1 could argue "
        "L1), but the name resolves to a party (step 2 yes) — kept at L3, "
        "the same posture bankruptcy's attorney field takes.",
        derived="A registered agent is on file",
    ),
    "principal_office_state": _field(
        Rung.L2, "the state the company does business from — coarse "
        "geography, no party resolved (step 2 no).",
    ),
    "foreign_qualification_date": _field(
        Rung.L1, "the date the company qualified to do business in Oregon "
        "is filed with Oregon's Secretary of State (step 1).",
    ),
    "annual_report_due": _field(
        Rung.L1,
        "Delaware's fixed statutory annual-report date, filed with the "
        "state (step 1) — entered, never computed (a fixed calendar date "
        "is not a period to count).",
    ),
    "franchise_tax_due": _field(
        Rung.L1, "the Delaware franchise tax due date — same statutory, "
        "filed-with-the-state posture as annual_report_due (step 1).",
    ),
    "business_license_due": _field(
        Rung.L1, "an Oregon or local business-license renewal date, filed "
        "with the issuing authority (step 1).",
    ),
    "bank_account_label": _field(
        Rung.L2,
        "references the company's own ledger account instance (decision "
        "9) — a coarse label, no party named (step 2 no); shape-checked by "
        "validate_value so the account NUMBER never lives here.",
    ),
    "revenue_start": _field(
        Rung.L1,
        "the date revenue was first recognized — an administrative "
        "milestone, no category (step 3 no). This pack's one top-level "
        "plan-period signal field (see the module docstring).",
    ),
    "notes": _field(
        Rung.L4,
        "free operator text that may carry a protected category once it "
        "names a person or a strategy (step 3 yes) — never reaches a "
        "model prompt (S2, ceiling L2) or an agent (I-15).",
        derived="An operator note is on file",
    ),
    # ── repeatable: founder ──────────────────────────────────────────────
    "founder.name": _field(
        Rung.L4,
        "resolves to one specific person who holds equity (step 2 yes) — "
        "over-classified like custody's child.name (step 3 yes).",
        derived="A founder is named",
    ),
    "founder.role": _field(
        Rung.L2, "a title (CEO, CTO, ...) — coarse, no category once "
        "decoupled from the name (step 2 no).",
    ),
    "founder.equity_pct": _field(
        Rung.L4,
        "resolves to that founder's own stake (step 2 yes); paired with "
        "the name it reveals the company's split — argue-up like "
        "bankruptcy's creditor.amount_scheduled (step 3 yes).",
        derived="An equity percentage is on file",
    ),
    "founder.vesting_start": _field(
        Rung.L1,
        "when vesting began — administrative, no category once separated "
        "from the equity figure (step 3 no); cannot anchor election-83b "
        "(see the module docstring).",
    ),
    "founder.cliff_months": _field(
        Rung.L2, "the cliff length in months — a coarse structural term "
        "(step 2 no).",
    ),
    "founder.election_83b_deadline": _field(
        Rung.L1,
        "one founder's own confirmed 83(b) filing date, entered directly "
        "— the computed template anchors on grant_date instead (step 3 no).",
    ),
    # ── repeatable: safe ─────────────────────────────────────────────────
    "safe.investor": _field(
        Rung.L4,
        "names the investor on one SAFE — a party tied to the cap table "
        "(step 2 yes), over-classified like founder.name (step 3 yes).",
        derived="A SAFE investor is on file",
    ),
    "safe.amount": _field(
        Rung.L4,
        "the invested amount resolves to that investor's own stake (step "
        "2/3 yes) — the signal field plan_period.flag reads for presence "
        "only, never its value.",
        derived="A SAFE amount is on file",
    ),
    "safe.valuation_cap": _field(
        Rung.L4,
        "resolves to the company's negotiated terms with a named investor "
        "(step 2/3 yes) — same posture as safe.amount.",
        derived="A valuation cap is on file",
    ),
    "safe.discount": _field(
        Rung.L4, "the discount rate — same negotiated-term posture as "
        "safe.valuation_cap (step 2/3 yes).",
        derived="A discount rate is on file",
    ),
    "safe.signed": _field(
        Rung.L1,
        "the date one SAFE was signed — administrative, no category once "
        "separated from the investor and the amounts above (step 3 no).",
    ),
    "safe.post_money": _field(
        Rung.L2, "whether the SAFE is post-money — a structural flag, no "
        "party named (step 2 no).",
    ),
    # ── repeatable: equity_grant ─────────────────────────────────────────
    "equity_grant.grantee": _field(
        Rung.L4,
        "names who received a grant — a specific person (step 2 yes), "
        "over-classified like founder.name/safe.investor (step 3 yes).",
        derived="An equity grant recipient is on file",
    ),
    "equity_grant.amount": _field(
        Rung.L4,
        "resolves to that person's own stake (step 2/3 yes) — the other "
        "signal field plan_period.flag reads for presence only.",
        derived="An equity grant amount is on file",
    ),
    "equity_grant.granted": _field(
        Rung.L1,
        "the date a grant was made — administrative, no category once "
        "separated from the grantee's name and the amount (step 3 no).",
    ),
    # ── repeatable: registration ─────────────────────────────────────────
    "registration.kind": _field(
        Rung.L2, "one of REGISTRATION_KINDS — a closed tag, no party named "
        "(step 2 no).",
    ),
    "registration.due": _field(
        Rung.L1, "one registration's own due date — filed with the "
        "issuing authority (step 1).",
    ),
    "registration.done": _field(
        Rung.L1, "the date a registration was completed — same "
        "filed-with-the-authority posture as registration.due (step 1).",
    ),
    # ── repeatable: advisor ──────────────────────────────────────────────
    "advisor.name": _field(
        Rung.L3,
        "names an advisor — a party (step 2 yes), no protected category "
        "of its own (step 3 no) — custody's opposing_party posture.",
        derived="An advisor is named",
    ),
    "advisor.role": _field(
        Rung.L2, "what the advisor advises on — a coarse tag, no party "
        "once separated from advisor.name (step 2 no).",
    ),
}

#: Classified at import (I-11). This line is the build failure: remove any
#: field's rung above and the process defining the schema dies, naming it.
FIELDS: dict[str, Rung] = classify_schema(SCHEMA)

#: Field names that may carry a sub-id (decision 2) — one record per founder,
#: per SAFE, per equity grant, per registration, per advisor.
REPEATABLE: frozenset[str] = frozenset(
    {
        "founder.name", "founder.role", "founder.equity_pct",
        "founder.vesting_start", "founder.cliff_months",
        "founder.election_83b_deadline",
        "safe.investor", "safe.amount", "safe.valuation_cap",
        "safe.discount", "safe.signed", "safe.post_money",
        "equity_grant.grantee", "equity_grant.amount", "equity_grant.granted",
        "registration.kind", "registration.due", "registration.done",
        "advisor.name", "advisor.role",
    }
)

#: `application_status`'s closed set. 'preparing' names the operator's own
#: state of readiness, never an act of drafting (decision 8's own word choice
#: for exactly this field, so the I-44 phrase guard has nothing to catch here).
APPLICATION_STATUSES: frozenset[str] = frozenset(
    {"preparing", "submitted", "interview", "accepted", "declined", "deferred"}
)

#: `entity_type`'s closed set.
ENTITY_TYPES: frozenset[str] = frozenset({"pbc", "c-corp", "llc", "not-formed"})

#: `registration.kind`'s closed set.
REGISTRATION_KINDS: frozenset[str] = frozenset(
    {"state-tax", "city-license", "dba", "foreign-qualification"}
)

#: The closed-set fields, field -> its allowed values. Read by validate_value;
#: not itself a derived-form table (no field -> sentence mapping) and not an
#: enumeration of matter names, so it is not what either registry-relative
#: guard scans for.
_CLOSED_SETS: dict[str, frozenset[str]] = {
    "application_status": APPLICATION_STATUSES,
    "entity_type": ENTITY_TYPES,
    "registration.kind": REGISTRATION_KINDS,
}

#: `bank_account_label`'s shape — the ledger's own account-instance label
#: convention (decision 9): lowercase letters, digits and hyphens, 1-40
#: characters, starting with a letter or digit. Mirrored rather than
#: imported, the way bankruptcy.py mirrors instances.ID_PATTERN: a pack is a
#: leaf that imports only the engine's rungs (custody.py and workers_comp.py
#: do the same), and tests/test_venture.py pins the two patterns equal by
#: comparison so they cannot drift.
_LABEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


class InvalidChoice(ValueError):
    """A closed-set field given a value outside its own set. Names the field
    and the set (this pack's own published data), never the value typed
    (I-15) — the closed set already says what to type instead."""

    def __init__(self, field: str, allowed: frozenset[str]) -> None:
        super().__init__(
            f"{field}: refused — must be one of {sorted(allowed)}. This "
            "refusal does not repeat what was typed (I-15)."
        )
        self.field = field


class InvalidLabel(ValueError):
    """`bank_account_label` given a value that is not a label shape — same
    I-15 posture `instances.InvalidId` takes for an instance id."""

    def __init__(self, field: str) -> None:
        super().__init__(
            f"{field}: refused — a label matches {_LABEL_PATTERN.pattern} "
            "(lowercase letters, digits and hyphens, 1-40 characters, "
            "starting with a letter or digit). This refusal does not "
            "repeat what was typed (I-15)."
        )
        self.field = field


def validate_value(field: str, value: object) -> None:
    """Refuse a closed-set field given a value outside its set, or
    `bank_account_label` given a non-label-shaped value; silent otherwise.

    **Not yet called by any door** — the same gap `workers_comp.py`'s own
    `validate_value` carries until `L8-surfaces` wires it in (I-11: absence
    of a check is not permission)."""
    if field in _CLOSED_SETS:
        allowed = _CLOSED_SETS[field]
        if value not in allowed:
            raise InvalidChoice(field, allowed)
        return
    if field == "bank_account_label":
        if not isinstance(value, str) or not _LABEL_PATTERN.match(value):
            raise InvalidLabel(field)


# ── deadline templates — one row (data only; rules.py does the counting) ────

#: PROVENANCE, 2026-09-12: every host this environment's egress proxy allows
#: for a legal citation was tried and refused (law.cornell.edu,
#: uscode.house.gov, irs.gov, investopedia.com, cooleygo.com,
#: en.wikipedia.org) — the same wall bankruptcy's/workers_comp's own
#: PROVENANCE notes document. `VERIFIED` is claimed narrowly, on the 30-day
#: figure alone: 26 U.S.C. § 83(b)(2) is one of the most stable, least
#: amended, most identically restated provisions in the tax code — "not
#: later than 30 days after the date of such transfer" is quoted verbatim by
#: every major secondary restatement (startup-equity guides, the IRS's own
#: Rev. Proc. 2012-29 model election). What VERIFIED does **not** cover, and
#: the `note` below says so: whether 26 U.S.C. § 7503's general weekend/
#: holiday extension reaches this election window is a genuinely contested
#: question this build could not read a primary source on — so this template
#: counts the plain, unextended 30-day span (never later than the statute's
#: own floor), and the note points at an accountant for that question and
#: the postmark rule alike, rather than picking a side of either.
_PROVENANCE_83B = (
    "26 U.S.C. § 83(b)(2): 'An election under paragraph (1) with respect to "
    "any transfer of property shall be made in such manner as the Secretary "
    "prescribes and shall be made not later than 30 days after the date of "
    "such transfer' (implementing regulation: Treas. Reg. § 1.83-2(b)). "
    "PROVENANCE, 2026-09-12 — see the note on this row and the module-level "
    "note above: every host this build could reach was refused by the "
    "egress proxy; VERIFIED is claimed on the stability and universal "
    "restatement of the 30-day figure alone, not on a fetch performed "
    "during this build."
)

#: One computed template: the 83(b) election window. `anchor` is
#: `grant_date` (top-level, `L1`) rather than the repeatable
#: `founder.vesting_start` — see the module docstring's "founder.vesting_start
#: cannot anchor a template" section. `jurisdiction=None` so the template
#: fits an instance filed at either `US-DE` or `US-OR` (`rules._for_jurisdiction`
#: falls back to a `None`-jurisdiction template when no exact match exists) —
#: correct here because a federal tax election's 30-day clock does not vary
#: by which state the company happens to be chartered or doing business in,
#: and because `rule="calendar_days"` never reaches `homestead.keep.dates.RULES`
#: at all (it is a plain `timedelta`, computed inside `rules.compute` itself),
#: so there is no jurisdiction-keyed lookup for `US-DE`'s absence from `RULES`
#: to ever refuse against.
TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "name": "election-83b",
        "anchor": "grant_date",
        "days": 30,
        "direction": "forward",
        "rule": "calendar_days",
        "mail": False,
        "jurisdiction": None,
        "source": _PROVENANCE_83B,
        "status": "VERIFIED",
        "note": (
            "calendar days, not court days — a plain 30-day span with no "
            "roll off a weekend or holiday (the same calendar_days shape "
            "the bankruptcy pack's first-plan-payment template uses); this "
            "is the conservative, unextended reading of the window, not a "
            "claim that a weekend or holiday landing on day 30 cannot ever "
            "extend it. Whether it does (26 U.S.C. § 7503) and whether a "
            "mailed election is timely by its postmark date rather than its "
            "receipt date (the postmark rule) are both questions to confirm "
            "with your accountant, not something this template resolves."
        ),
    },
)

#: Rendered by every surface that opens this matter (decision 8). This pack
#: forms nothing, files nothing with any state or agency, and computes no
#: tax — it keeps the dates and the references around each.
NOTICE = (
    "This pack keeps dates and references; it forms nothing, files nothing, "
    "and computes no tax."
)
