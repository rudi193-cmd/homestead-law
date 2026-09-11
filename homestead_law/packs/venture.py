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
form/incorporate/file-with-the-state phrase. `NOTICE` is the sentence a
surface renders when it opens this matter — `app/panes.py`'s
`bankruptcy_pane` does exactly that for the pack beside this one, and the
venture pane that will do it here is `L8-surfaces`' bite, not this one: until
it lands, `pane_for` falls back to `generic_pane`, which renders rows and no
notice. The sentence is declared, tested and unused by a surface, in that
order.

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

**One venture instance per grant**, and that is the documented answer to the
follow-on question rather than an omission. `grant_date` is one top-level
field, so one instance carries one grant date and therefore one computed
`election-83b`; a second founder whose stock was transferred on a different
day needs a second instance (`--id founders-2026-09`, say), not a second
anchor. The alternative — teaching `rules.compute` to address
`(matter, anchor, instance.sub)` — is an engine-shaped change to a shared
module that every other pack's templates would inherit, and this bite does
not make it. For a two-founder company whose stock is usually transferred on
one day at formation, one instance is the ordinary case and two is the
outside one; `instances_of` already lists them and the queue already names
matter+instance on every line, so nothing downstream needs to know why there
are two. Entered dates are unaffected either way:
`founder.election_83b_deadline` is `REPEATABLE`, so every founder's own
confirmed date fits in one instance regardless.

## Every entered date here is `L2`. `grant_date` is the one exception

~~Why so much of this pack is `L1` with no public docket behind it~~ —
corrected by audit, 2026-09-12, to the ruling the parallel `L8-grant` audit
settled on the identical question. `Rung.L1` is *"public in this matter's
forum"*, and **this matter has no forum**: there is no court, no docket and
no case number, and a Secretary of State's corporate register is not one
either — it is a register the company files into, the same relation the
household has to its bank. So step 1 never reaches `L1` here. A date that
reveals an application, a formation or an award *exists* is household
metadata, which is `L2` — the rung custody gives `move_date` and the ledger
gives a posting date — and every entered date in this pack now sits there:
the three application dates, the compliance dates
(`benefit_report_due`/`formation_date`/`foreign_qualification_date`/
`annual_report_due`/`franchise_tax_due`/`business_license_due`/
`registration.due`/`registration.done`), the private-instrument dates
(`founder.vesting_start`/`founder.election_83b_deadline`/`safe.signed`/
`equity_grant.granted`) and `revenue_start`. Nothing downstream moves:
`S1_LIST` renders `L1` and `L2` alike, the queue shows a date for `L1`-`L3`,
and `plan_period.flag` reads presence through the gate.

The one exception is **`grant_date`**, which stays `L1` because
`rules.validate_templates` refuses any anchor that is not, and
`election-83b` is the one computed template this pack has. Its own `why`
states the exception and the narrowest argument for it rather than dressing
it up; `tests/test_venture.py::test_grant_date_is_the_only_l1_date_and_why`
pins that it is the only one, so the exception cannot quietly become a
habit. `jurisdiction` stays `L1` too and is not a date: it is a constant of
the pack (decision 1), not a fact about the household.

Step 3 does the rest. A field that names a person/entity (`legal_name`,
`registered_agent`, `founder.name`, `safe.investor`, `equity_grant.grantee`,
`advisor.name`) or an argue-up figure (`founder.equity_pct`,
`safe.amount`/`valuation_cap`/`discount`, `equity_grant.amount`) sits at
`L3`/`L4` — custody's `opposing_party`/bankruptcy's `creditor.name`
reasoning — and `ein` is sealed at `L5`.

## The plan-period interaction flag

`plan_period.flag` scans every other matter for `SIGNAL_FIELDS` presence.
This bite corrects the two field names this pack can actually produce a
record under: `safe.amount`/`equity_grant.amount`, not the bare
`"safe"`/`"equity_grant"` the frozenset held before — both groups are
`REPEATABLE`, so every field either stores is dotted. `revenue_start` needed
no change: this pack's one top-level, non-repeatable signal field. The
frozenset is written sorted, one name per line, and carries `L8-grant`'s two
`disbursement.*` names alongside this pack's: two Wave 8 bites edit that one
literal in parallel, and a sorted one-per-line set merges as a plain union
where a packed line is a conflict inside a line.
"""
from __future__ import annotations

import re
from typing import Any

from homestead.keep.rungs import Rung, classify_schema

__all__ = [
    "MATTER", "JURISDICTION", "JURISDICTIONS", "REPEATABLE", "SCHEMA",
    "FIELDS", "NOTICE", "TEMPLATES",
    "APPLICATION_STATUSES", "ENTITY_TYPES", "REGISTRATION_KINDS",
    "InvalidChoice", "InvalidEin", "InvalidLabel", "validate_value",
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
        Rung.L2,
        "entered off the program's own correspondence, not a docket: an "
        "accelerator has no forum, so the date is not public anywhere "
        "(step 1 no) and L1 is unavailable to it. It names no party and no "
        "protected category (steps 2/3 no), which lands it at L2 — "
        "household metadata, the rung the ledger gives a posting date and "
        "custody gives move_date. What it reveals is that an application "
        "exists at all, and that is exactly the household fact L2 covers.",
    ),
    "interview_date": _field(
        Rung.L2, "same no-forum posture as application_submitted (step 1 "
        "no, steps 2/3 no).",
    ),
    "decision_date": _field(
        Rung.L2, "same no-forum posture as application_submitted; the "
        "decision's content is application_status, entered separately "
        "(step 1 no, steps 2/3 no).",
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
        Rung.L2,
        "the biennial report's due date (8 Del. C. § 366(b)) is entered "
        "from the certificate/bylaws cadence — the statute fixes only a "
        "floor, so there is no period to count. § 366(b) runs the report "
        "to STOCKHOLDERS; § 366(c) makes publication optional, so the date "
        "is not public in any forum (step 1 no) and names no party or "
        "category (steps 2/3 no) — L2.",
    ),
    "formation_state": _field(
        Rung.L2, "the state of incorporation — coarse geography, no party "
        "resolved (step 2 no).",
    ),
    "formation_date": _field(
        Rung.L2,
        "the certificate is on file with the Delaware Secretary of State, "
        "but a corporate registry is not *this matter's forum* — there is "
        "no court and no docket here, so step 1 does not reach L1 (the "
        "ruling the L8-grant audit settled for every entered date in a "
        "forumless matter). No party, no category (steps 2/3 no) — L2.",
    ),
    "grant_date": _field(
        Rung.L1,
        "THE PACK'S ONE L1 FIELD THAT IS A DATE, AND A DELIBERATE "
        "EXCEPTION. Every other entered date here is L2 (no forum). This "
        "one is L1 because `rules.validate_templates` refuses any anchor "
        "that is not — 'a deadline template may only anchor on a field "
        "public in this matter's forum' — and `election-83b` is the one "
        "computed template the plan gives this pack. The narrowest reading "
        "that supports it: the date alone reveals only that an equity "
        "grant was made, the same bare fact equity_grant.granted carries, "
        "and it is the date written on the 83(b) election filed with the "
        "IRS. That is a filing, not a public forum (26 U.S.C. § 6103 seals "
        "returns), so the exception is recorded here rather than argued "
        "away: raising it to L2 would delete this pack's only computed "
        "deadline, which is a decision for the anchor rule, not for a "
        "pack. See tests/test_venture.py::test_grant_date_is_the_only_l1_"
        "date_and_why.",
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
        Rung.L2, "same posture as formation_date — a Secretary of State's "
        "register is not this matter's forum (step 1 no), no party, no "
        "category (steps 2/3 no).",
    ),
    "annual_report_due": _field(
        Rung.L2,
        "Delaware's fixed statutory annual-report date — entered, never "
        "computed (a fixed calendar date is not a period to count). The "
        "statute is public; *this company's* due date on file is household "
        "metadata in a matter with no forum (step 1 no, steps 2/3 no) — L2.",
    ),
    "franchise_tax_due": _field(
        Rung.L2, "the Delaware franchise tax due date — same statutory, "
        "no-forum posture as annual_report_due (step 1 no, steps 2/3 no).",
    ),
    "business_license_due": _field(
        Rung.L2, "an Oregon or local business-license renewal date — same "
        "no-forum posture (step 1 no, steps 2/3 no).",
    ),
    "bank_account_label": _field(
        Rung.L2,
        "references the company's own ledger account instance (decision "
        "9) — a coarse label, no party named (step 2 no); shape-checked by "
        "validate_value so the account NUMBER never lives here.",
    ),
    "revenue_start": _field(
        Rung.L2,
        "the date revenue was first recognized — an internal accounting "
        "milestone, public nowhere (step 1 no), naming no party and no "
        "category (steps 2/3 no). This pack's one top-level plan-period "
        "signal field (see the module docstring); the flag reads presence "
        "through the gate, and L2 renders on S1_LIST exactly as L1 did, so "
        "the rung change moves no line.",
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
        Rung.L2,
        "when vesting began — a private stock agreement's own date, public "
        "nowhere (step 1 no), naming no party once separated from "
        "founder.name and no category (steps 2/3 no). Cannot anchor "
        "election-83b for a second reason as well (see the module "
        "docstring): it is REPEATABLE.",
    ),
    "founder.cliff_months": _field(
        Rung.L2, "the cliff length in months — a coarse structural term "
        "(step 2 no).",
    ),
    "founder.election_83b_deadline": _field(
        Rung.L2,
        "one founder's own confirmed 83(b) date, entered directly — a "
        "federal tax filing is not a public forum (26 U.S.C. § 6103; step "
        "1 no), and the date names no party or category once separated "
        "from founder.name (steps 2/3 no). The computed template anchors "
        "on grant_date instead.",
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
        Rung.L2,
        "the date one SAFE was signed — a private contract's own date, "
        "public nowhere (step 1 no), no party or category once separated "
        "from the investor and the amounts above (steps 2/3 no).",
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
        Rung.L2,
        "the date a grant was made — a private board action, public "
        "nowhere (step 1 no), no party or category once separated from the "
        "grantee's name and the amount (steps 2/3 no).",
    ),
    # ── repeatable: registration ─────────────────────────────────────────
    "registration.kind": _field(
        Rung.L2, "one of REGISTRATION_KINDS — a closed tag, no party named "
        "(step 2 no).",
    ),
    "registration.due": _field(
        Rung.L2, "one registration's own due date — the issuing authority "
        "is not this matter's forum (step 1 no), no party, no category "
        "(steps 2/3 no).",
    ),
    "registration.done": _field(
        Rung.L2, "the date a registration was completed — same no-forum "
        "posture as registration.due (step 1 no, steps 2/3 no).",
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

#: …and one thing the shared pattern alone does not stop. `12345678` matches
#: `_LABEL_PATTERN` and is exactly what an account *number* looks like, which
#: is the one value this field's own `why` promises can never live here — a
#: label is a name the operator chose, and an all-digit string is never that.
#: Refused separately so the refusal can say which of the two rules was
#: broken without echoing the value (I-15), and so the mirrored
#: `instances.ID_PATTERN` equality above stays exact.
_ALL_DIGITS = re.compile(r"^[0-9]+$")

#: `ein`'s shape. An EIN is `NN-NNNNNNN` — two digits, a hyphen, seven digits
#: (IRS Pub. 1635's own layout). **Validating the shape of an L5 value is not
#: reading it**: `validate_value` is handed the candidate by the door that is
#: about to store it, decides yes or no, and returns `None` either way; the
#: refusal names the field and the shape — this pack's own published data —
#: and never the digits typed (I-15). The check exists because L5 has no
#: override and no derived form: nothing downstream will ever render an `ein`
#: for a human to notice it was typed into the wrong box, so entry is the
#: only moment a transposed or misfiled value can be caught at all (I-11 —
#: absence of a check is not permission, and a sealed field is the last place
#: to leave one out).
_EIN_PATTERN = re.compile(r"^[0-9]{2}-[0-9]{7}$")


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

    def __init__(self, field: str, *, because: str = "") -> None:
        super().__init__(
            f"{field}: refused — a label matches {_LABEL_PATTERN.pattern} "
            "(lowercase letters, digits and hyphens, 1-40 characters, "
            "starting with a letter or digit) and is never all digits"
            f"{because}. This refusal does not repeat what was typed (I-15)."
        )
        self.field = field


class InvalidEin(ValueError):
    """`ein` given a value that is not `NN-NNNNNNN`. Names the field and the
    shape, never the digits — the field is `L5`, so echoing the value back in
    an error string would be the one surface a sealed rung has none of."""

    def __init__(self, field: str) -> None:
        super().__init__(
            f"{field}: refused — an EIN matches {_EIN_PATTERN.pattern} "
            "(two digits, a hyphen, seven digits). This refusal does not "
            "repeat what was typed (I-15), and this field is sealed at L5: "
            "it renders on no surface and has no derived form."
        )
        self.field = field


def validate_value(field: str, value: object) -> None:
    """Refuse a closed-set field given a value outside its set,
    `bank_account_label` given a non-label-shaped or all-digit value, or
    `ein` given a value that is not `NN-NNNNNNN`; silent otherwise.

    **Both writing doors call this.** `cli._cmd_put` and `server._post_store`
    each do `hasattr(mt.pack, "validate_value")` and call it before building
    the `Classified` they would store — wired by `L4-surfaces` (wave 4) for
    `workers_comp.py`'s own cap, and picked up by this pack for free the day
    it registered. ~~"Not yet called by any door"~~ was true of the shape
    `workers_comp.py` shipped in wave 3 and is not true now;
    `tests/test_workers_comp.py::test_the_doors_call_validate_value` is the
    pin, and `tests/test_venture.py`'s own two door tests are this pack's.

    Every refusal names the field and this pack's own published rule, never
    the value offered (I-15)."""
    if field in _CLOSED_SETS:
        allowed = _CLOSED_SETS[field]
        if value not in allowed:
            raise InvalidChoice(field, allowed)
        return
    if field == "bank_account_label":
        if not isinstance(value, str) or not _LABEL_PATTERN.match(value):
            raise InvalidLabel(field)
        if _ALL_DIGITS.match(value):
            raise InvalidLabel(
                field,
                because=" — an all-digit string is an account number, not a "
                "label the operator chose",
            )
        return
    if field == "ein":
        if not isinstance(value, str) or not _EIN_PATTERN.match(value):
            raise InvalidEin(field)


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
