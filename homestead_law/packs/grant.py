"""The grant pack — a funder's application and award (L8-grant, wave 8).

A ~$285k grant proposal with BERI's agreed backing if it comes through. Same
rules as every other matter here: track, never draft or file (decision 8,
provisional I-44), UNCERTAIN never guesses, and every date is entered from
the funder's own notice.

**No court, so no computed deadline.** Every other pack that ships a
`TEMPLATES` row anchors on a fact posted somewhere public — a docket, a
confirmed order, a court calendar — and counts a period a rule of procedure
fixes. A grant has none of that: the funder sets its own terms, funder by
funder, program by program, and there is no procedural code this pack could
cite the way `bankruptcy.py` cites FRBP or `custody.py` cites the UCCJEA.
`TEMPLATES` is therefore the empty tuple, not an oversight — see the section
below — and `JURISDICTIONS = ("US-federal",)` is a **placeholder** carried
only so `matter open`/`set_jurisdiction` and the registry's own contract
(decision 1: every matter declares a jurisdiction) have something to read;
it names no forum this pack ever counts a day against.

## The rung ladder, read for a matter with no court

`L1` is not "the smallest fact"; it is **public in this matter's forum**
(step 1), and this matter has no forum. A funder's file is posted nowhere,
so step 1 answers no for everything here except `jurisdiction`, whose value
is a constant of this pack rather than a fact about the household. The dates
are no exception, and this is the audit's own correction to an earlier draft
of this pack that read them as "bare administrative timeline" facts and put
them at `L1` (2026-09-11): a submission deadline, a decision date, an award
date and an award period are facts about the household's finances known to
the funder and the household, and each *reveals that an application or an
award exists* the moment it renders — "a decision is due 2027-03-01" says an
application is pending. An entered date that reveals an application or an
award is at least `L2`.

Two packs in this repo already drew that line. `custody.py`'s `move_date` is
not `L1` on the sentence "nothing makes a family's moving date public in
this forum on its own" — a fact the household may eventually tell a court is
not thereby published. And the ledger's money table puts a transaction's
posting `date` at `L2`, *explicitly not* `L1`, for the same reason, while
its `amount` climbs past it. A grant's dates take the ledger's posture
rather than `move_date`'s `L3`, because they resolve to no one person
(step 2 no) and carry no category of their own (step 3 no): they land on
`new_residence_state`'s rung by `new_residence_state`'s reasoning, which is
where `program`, `status`, `report.period`/`report.kind` and
`disbursement.account_label` already sat.

**`award_date` and `award_period_*` are `L2`, not `L3`, though they sit
beside `award_amount` at `L3`.** Adjacency does not raise a rung —
composition is `max` over a *record* (I-12) and each of these is its own
record — so step 2 decides it: the amount is the household's financial
substance, the date says only when the process moved. That is the line the
ledger already holds between a transaction's `date` and its `amount`, and
`disbursement.received` sits on the same side of it.

Two consequences, both deliberate. A template's `anchor` must be `L1`, so
with no `L1` date here a `TEMPLATES` row cannot be added without first
re-arguing a rung in this docstring — the plan's "no computed deadlines"
made structural. And nothing on any surface moves, because every ceiling in
the crossing table is `L2` or higher; what changes is that the pack no
longer calls a household's private calendar a public record.

Money and names resolve to a party or to the household's finances (step 2
yes) without carrying a protected category of their own (step 3 no) — the
same posture `bankruptcy.py`'s `plan_payment_amount`/`income`/`creditor.name`
already hold, and for the identical reason stated there: a stated figure in
one filed document is financial substance, not case metadata, and law's
money fields sit at `L3` where the ledger's own transaction `amount` sits at
`L4` (Open item 4) because the two are different data about different
things. `allowable_uses`/`restrictions` are `L4`: free-form narrative of what
the award may or must be spent on, which routinely carries the funder's own
programmatic conditions and the household's or business's spending plan
under them — the same over-classify default `custody.py`'s and
`bankruptcy.py`'s `notes` fields already take for narrative content, so the
list surface shows only the derived stand-in and the real text renders on
detail only.

## `status` is a closed set, and the enum value is never the operator's word

The plan's own working vocabulary calls an application still being worked on
"drafting" — that is the household's word for their own state, not a word
this app may use, because a bare enum member spelled `"drafting"` would put
that exact word in a stored value and on every render of it, next to
provisional I-44's own phrase scan. `STATUS_VALUES`
spells the same state `"preparing"` instead: the fact tracked (an
application not yet submitted) is identical, and the scan never sees the
word. `validate_value` refuses any other string, naming the field and the
closed set — never the value that was rejected (I-15).

## The repeatable groups

`milestone`, `report` and `disbursement` are one composed record per
occurrence (decision 2, the `homestead_law.instances` shape every other
pack's repeatable group already uses) — one milestone, one reporting period,
one payment tranche, each addressed by its own `--sub`. `disbursement.
account_label` names a **ledger account instance's own label** (decision 9,
provisional I-43) — never a number, and `validate_value` refuses a label
shaped like one (all-digit, or off the ledger's own alphabet) by name,
without echoing what was typed.

## The Chapter 13 plan-period flag

`award_amount` and the two money-bearing `disbursement` sub-fields
(`disbursement.amount`, `disbursement.received` — the tranche's amount and
the fact that one actually landed) are two of `homestead_law.plan_period
.SIGNAL_FIELDS`: while a bankruptcy instance is confirmed and undischarged,
their mere presence here — never their value — makes
`homestead_law.plan_period.flag` yield one reference line (11 U.S.C.
§§ 541(a)(7), 1306(a), 1329). This pack is a **producer** only: it declares
no dependency on `plan_period` and reads nothing back from it; the consumer
was built and tested against a fake pack before this one existed
(`tests/test_plan_period.py`), and this bite's own `tests/test_grant.py`
proves the wiring against the real pack.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from homestead.keep.rungs import Rung, classify_schema

__all__ = [
    "MATTER", "JURISDICTION", "JURISDICTIONS", "REPEATABLE", "SCHEMA",
    "FIELDS", "NOTICE", "STATUS_VALUES", "InvalidStatus", "InvalidAccountLabel",
    "validate_value", "TEMPLATES",
]

MATTER = "grant"
JURISDICTION = "US-federal"
#: A placeholder, not a forum this pack counts a day under (see the module
#: docstring). A grant has no court; its terms are the funder's own, and
#: `TEMPLATES` below is empty for exactly that reason. Carried only so
#: `matter open`/`set_jurisdiction` and the registry's decision-1 contract
#: (every matter declares a `jurisdiction` field and a non-empty
#: `JURISDICTIONS`) have something to read.
JURISDICTIONS: tuple[str, ...] = ("US-federal",)


def _field(rung: Rung, why: str, *, derived: str | None = None) -> dict[str, Any]:
    decl = {"rung": rung, "matter": MATTER, "jurisdiction": JURISDICTION, "why": why}
    if derived is not None:
        decl["derived"] = derived
    return decl


#: The closed grant schema. See the module docstring's "rung ladder" section
#: for the reasoning shared across the L1 dates and the L2 labels; each
#: field below states its own step-2/step-3 answer rather than repeating it.
SCHEMA: dict[str, dict[str, Any]] = {
    "jurisdiction": _field(
        Rung.L1,
        "a placeholder forum (see the module docstring); the value is one "
        "of JURISDICTIONS, held only so decision 1's per-instance contract "
        "has something to read (step 5). The one field here that is not a "
        "fact about the household at all — a constant of this pack — which "
        "is why it, alone, stays at the rung step 1 would have given it; "
        "this pack computes no date under it (a grant has no court).",
    ),
    # ── L2 — the application/award's own timeline. Household content: each
    #        date reveals that an application or an award exists, resolves to
    #        no one person (step 2 no), carries no category (step 3 no), and
    #        is published by no forum (step 1 no → not L1). See the module
    #        docstring's ladder section for the full ruling. ──────────────────
    "backing_agreed_date": _field(
        Rung.L2,
        "the date a backer agreed to support this application — its "
        "presence says a backed application exists, which is household "
        "content; it resolves to no one person by itself (step 2 no: the "
        "backer is named by `backer`, at L3) and carries no category "
        "(step 3 no). Entered from the backer's own correspondence, "
        "published by no forum (step 1 no).",
    ),
    "submission_deadline": _field(
        Rung.L2,
        "the funder's own stated deadline — the date every other date on "
        "this matter is read against (there is no TEMPLATES row here to "
        "compute one, and at L2 there could not be: see the module "
        "docstring). Its presence says an application is in hand, which is "
        "household content; step 2 no, step 3 no, and no forum publishes a "
        "funder's calendar (step 1 no).",
    ),
    "submitted_date": _field(
        Rung.L2,
        "when the application was actually sent — the same posture as "
        "submission_deadline (step 1/2/3 no), and it reveals one step more: "
        "that the application went out.",
    ),
    "decision_date": _field(
        Rung.L2,
        "when the funder's decision is due or was received — the same "
        "posture as submitted_date (step 1/2/3 no); a decision date on file "
        "says an application is pending, which is why it is not L1.",
    ),
    "award_date": _field(
        Rung.L2,
        "when an award was made. L2 rather than L3 beside award_amount: the "
        "amount is the household's financial substance (step 2 yes), the "
        "date says only when the process moved — the ledger's own line "
        "between a transaction's date (L2) and its amount (see the module "
        "docstring). Step 3 no; no forum publishes it (step 1 no).",
    ),
    "award_period_start": _field(
        Rung.L2,
        "the award's own start date, stated in the award letter — the same "
        "posture as award_date (step 1/2/3 no).",
    ),
    "award_period_end": _field(
        Rung.L2,
        "the award's own end date, stated in the award letter — same "
        "posture as award_period_start (step 1/2/3 no).",
    ),
    # ── L2 — the labels, on the same reasoning as the dates above ─────────
    "program": _field(
        Rung.L2,
        "the funder's program name is a household-content label that does "
        "not by itself resolve to any one person (step 2 no) and carries no "
        "protected category, so it stays at the household rung rather than "
        "climbing to an attributed one — new_residence_state's own posture.",
    ),
    "status": _field(
        Rung.L2,
        "a closed operational state of the application/award — household-"
        "content, unattributed (step 2 no), no category (step 3 no). "
        "STATUS_VALUES is the closed set; validate_value refuses anything "
        "else, and the set spells the operator's own 'not yet submitted' "
        "state as 'preparing' rather than the word the plan uses for it, so "
        "no stored value or rendering of this field can ever carry the word "
        "the I-44 scan bans (see the module docstring).",
    ),
    # ── L3 — resolves to a party or to the household's finances, no
    #        category of its own (step 3 no) ────────────────────────────────
    "funder": _field(
        Rung.L3,
        "names the funding organization — a party to this application, "
        "resolving to the household's dealings with it (step 2 yes); no "
        "protected category attaches to an organization's name by itself "
        "(step 3 no).",
        derived="A funder is named",
    ),
    "backer": _field(
        Rung.L3,
        "names the entity that agreed to back this application (BERI) — "
        "the same posture as funder: a party (step 2 yes), no category of "
        "its own (step 3 no).",
        derived="A backer is named",
    ),
    "program_officer": _field(
        Rung.L3,
        "names a person at the funder handling this application — resolves "
        "to that individual (step 2 yes), no protected category attached to "
        "a name alone (step 3 no).",
        derived="A program officer is named",
    ),
    "amount_requested": _field(
        Rung.L3,
        "the amount asked for — resolves to the household's finances "
        "(step 2 yes), no further protected category (step 3 no); the same "
        "posture bankruptcy.py's plan_payment_amount states at length: a "
        "figure stated in one filed document is financial substance, not "
        "case metadata, so step 1's public-forum argument (which does not "
        "apply here anyway — a grant has no court) would not have raised "
        "this past L3 regardless.",
        derived="An amount requested is on file",
    ),
    "award_amount": _field(
        Rung.L3,
        "the amount actually awarded — same posture as amount_requested "
        "(step 2 yes, step 3 no). One of homestead_law.plan_period."
        "SIGNAL_FIELDS (see the module docstring): its mere presence, never "
        "its value, is read cross-matter by the Chapter 13 plan-period flag.",
        derived="An award amount is on file",
    ),
    # ── L4 — narrative, over-classified the way notes/creditor.note are ─────
    "allowable_uses": _field(
        Rung.L4,
        "free-form narrative of what the award may be spent on — resolves "
        "to the household's or business's financial affairs (step 2 yes) "
        "and routinely carries the funder's own programmatic conditions and "
        "the spending plan under them (step 3's over-classify default, the "
        "same posture notes/creditor.note already hold for narrative "
        "content). Renders on S1_DETAIL only; the list surface shows the "
        "derived stand-in.",
        derived="Allowable uses are on file",
    ),
    "restrictions": _field(
        Rung.L4,
        "free-form narrative of what the award may NOT be spent on or what "
        "conditions attach — the same posture as allowable_uses (step 2 "
        "yes, step 3's over-classify default), for the same reason.",
        derived="Restrictions are on file",
    ),
    "notes": _field(
        Rung.L4,
        "free operator text that may carry any protected category at all — "
        "the same posture every other pack's notes field holds (step 2 "
        "yes, step 3 yes by the over-classify default): a note never "
        "reaches a model prompt (S2, ceiling L2 → derived) or an agent "
        "(I-15).",
        derived="An operator note is on file",
    ),
    # ── repeatable: milestone (decision 2) ───────────────────────────────────
    "milestone.name": _field(
        Rung.L3,
        "a milestone's description resolves to the award's program content "
        "and the household's or business's plan under it (step 2 yes); no "
        "protected category by itself (step 3 no).",
        derived="A milestone is on file",
    ),
    "milestone.due": _field(
        Rung.L2,
        "a milestone's due date, entered from the award terms — the same "
        "posture as submission_deadline (step 1/2/3 no).",
    ),
    "milestone.done": _field(
        Rung.L2,
        "the date a milestone was completed — same posture as milestone.due "
        "(step 1/2/3 no).",
    ),
    # ── repeatable: report (decision 2) ──────────────────────────────────────
    "report.period": _field(
        Rung.L2,
        "the reporting period's own label (e.g. a quarter) — household-"
        "content, unattributed (step 2 no), no category (step 3 no), the "
        "same posture as program.",
    ),
    "report.due": _field(
        Rung.L2,
        "a report's due date, entered from the award terms — same posture "
        "as milestone.due (step 1/2/3 no).",
    ),
    "report.submitted": _field(
        Rung.L2,
        "the date a report actually went to the funder — same posture as "
        "report.due (step 1/2/3 no).",
    ),
    "report.kind": _field(
        Rung.L2,
        "the report's own kind (narrative, financial, …) — household-"
        "content, unattributed (step 2 no), no category (step 3 no), the "
        "same posture as report.period.",
    ),
    # ── repeatable: disbursement (decision 2) ────────────────────────────────
    "disbursement.expected": _field(
        Rung.L2,
        "a tranche's expected date, stated in the award terms — same "
        "posture as award_date (step 1/2/3 no).",
    ),
    "disbursement.amount": _field(
        Rung.L3,
        "a tranche's amount — resolves to the household's finances "
        "(step 2 yes), no further protected category (step 3 no), the same "
        "posture as amount_requested. One of "
        "homestead_law.plan_period.SIGNAL_FIELDS (see the module "
        "docstring): presence, never value, is the signal.",
        derived="A disbursement amount is on file",
    ),
    "disbursement.received": _field(
        Rung.L2,
        "the date a tranche actually arrived — a posting date, and L2 for "
        "the reason the ledger's own posting date is: what arrived is "
        "disbursement.amount, at L3 (step 2 no here, step 3 no, step 1 no). "
        "One of homestead_law.plan_period.SIGNAL_FIELDS: an award can be "
        "entirely silent on disbursement.amount and still mark an asset "
        "having arrived, so this field carries the signal on its own too — "
        "and its rung does not decide that, because the consumer counts a "
        "record that renders *or* derives.",
    ),
    "disbursement.account_label": _field(
        Rung.L2,
        "a ledger account instance's own label (decision 9, provisional "
        "I-43) — a reference, never a number; household-content, "
        "unattributed (step 2 no), no category (step 3 no). validate_value "
        "refuses a value shaped like a number rather than a label.",
    ),
}

#: Classified at import (I-11). This line is the build failure: remove any
#: field's rung above and the process defining the schema dies, naming it.
FIELDS: dict[str, Rung] = classify_schema(SCHEMA)

#: Field names that may carry a sub-id (decision 2) — one composed record per
#: milestone, per reporting period, per disbursement tranche.
REPEATABLE: frozenset[str] = frozenset(
    {
        "milestone.name", "milestone.due", "milestone.done",
        "report.period", "report.due", "report.submitted", "report.kind",
        "disbursement.expected", "disbursement.amount",
        "disbursement.received", "disbursement.account_label",
    }
)

#: Rendered by every surface that opens this matter (decision 8).
NOTICE = (
    "This pack keeps dates and references from the funder's notice; it "
    "drafts nothing and submits nothing."
)

#: The closed set `status` may take. Spelled `"preparing"`, never the plan's
#: own word for the same state — see the module docstring's "status is a
#: closed set" section: the operator's own not-yet-submitted state is a real
#: state this pack tracks, and the word for it is chosen so the I-44 phrase
#: scan never has reason to look at it twice.
STATUS_VALUES: frozenset[str] = frozenset(
    {"preparing", "submitted", "under-review", "awarded", "declined",
     "active", "closed"}
)

#: A ledger account instance's own label shape (decision 9's alphabet,
#: `homestead_law.instances.ID_PATTERN`'s own rule, copied rather than
#: imported so this pack stays a leaf importing only the engine's `rungs` —
#: `custody.py`/`bankruptcy.py`/`workers_comp.py` all take this posture for
#: their own copied id patterns). A label is never a number: the all-digit
#: check below is `_ID_PATTERN`'s own alphabet made stricter by one more
#: rule, because a *label* that happens to satisfy the alphabet by being all
#: digits is exactly the number decision 9 keeps out of a law field.
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


class InvalidStatus(ValueError):
    """A `status` value outside `STATUS_VALUES`.

    Names the field and the closed set — never the value that was rejected
    (I-15): a status the operator mistyped is not itself L3+ content, but
    this refusal treats it with the same discipline every other rejected
    write in this package gets, rather than echoing free text back into an
    error message on the one field this pack most wants kept off that list."""

    def __init__(self, value: object) -> None:
        super().__init__(
            f"status: refused — not one of {sorted(STATUS_VALUES)}. This "
            "refusal does not repeat what was typed."
        )
        self.value_type = type(value).__name__


class InvalidAccountLabel(ValueError):
    """A `disbursement.account_label` value that is not a ledger account
    instance's label — either off the label alphabet, or shaped like a bare
    number, which decision 9 refuses a law field from ever holding.

    Names the field and the required shape only — never the value itself
    (I-15), the same posture `homestead_law.instances.InvalidId` already
    takes for a malformed instance id."""

    def __init__(self) -> None:
        super().__init__(
            "disbursement.account_label: refused — a ledger account "
            f"instance's label matches {_ID_PATTERN.pattern} and is never "
            "all digits (a label is never a number, provisional I-43). "
            "This refusal does not repeat what was typed."
        )


def validate_value(field: str, value: object) -> None:
    """Refuse a `status` outside `STATUS_VALUES`, or a `disbursement.
    account_label` that is not a label — silent for every other field.

    Both writing doors (`cli._cmd_put`, `server._post_store`) already call
    any pack's `validate_value` when one is declared, guarded by
    `hasattr(mt.pack, "validate_value")` (wired by L4-surfaces for
    `workers_comp.py`'s own length cap) — this pack's version is checked
    directly the same way `tests/test_workers_comp.py` checks that one.
    """
    if field == "status":
        if not isinstance(value, str) or value not in STATUS_VALUES:
            raise InvalidStatus(value)
        return
    if field == "disbursement.account_label":
        if not isinstance(value, str) or not _ID_PATTERN.match(value):
            raise InvalidAccountLabel()
        if value.isdigit():
            raise InvalidAccountLabel()
        return


# ── deadline templates — empty, and the shape check that keeps it honest ────
#
# A grant has no court and no procedural code to count a period under (see
# the module docstring); every date on this pack is entered from the
# funder's own notice, never derived. The shape check still runs at import
# — the same posture `workers_comp.py` takes for its own empty TEMPLATES —
# so a row added here later is held to the contract from its first commit
# rather than by habit — and, after the audit's rung ruling, is refused
# outright until a date's rung is re-argued (the docstring's ladder
# section: the only `L1` field left is `jurisdiction`).

_TEMPLATE_KEYS = frozenset(
    {"name", "anchor", "days", "direction", "rule", "mail",
     "jurisdiction", "source", "status", "note"}
)
_DIRECTIONS = frozenset({"forward", "backward"})
_COUNTING_RULES = frozenset(
    {"court_days", "court_days_before", "business_days", "calendar_days"}
)
_STATUSES = frozenset({"VERIFIED", "UNCERTAIN"})
_TEMPLATE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def _check_templates(
    schema: Mapping[str, Any],
    fields: Mapping[str, Rung],
    jurisdictions: tuple[str, ...],
    templates: "tuple[Mapping[str, Any], ...]",
) -> None:
    """The same shape check `bankruptcy.py`/`workers_comp.py` run at import —
    see either module's docstring for the full rationale. Raised at import,
    naming the template and the failure."""
    if not isinstance(templates, tuple):
        raise ValueError(
            f"TEMPLATES must be a tuple of rows, not {type(templates).__name__}"
        )
    seen: set[str] = set()
    for row in templates:
        if not isinstance(row, Mapping) or set(row) != _TEMPLATE_KEYS:
            raise ValueError(
                f"TEMPLATES: keys must be exactly {sorted(_TEMPLATE_KEYS)}, "
                f"not {sorted(row) if isinstance(row, Mapping) else row!r}"
            )
        name = row["name"]
        if not isinstance(name, str) or not _TEMPLATE_NAME.match(name):
            raise ValueError(
                f"TEMPLATES: name {name!r} must match {_TEMPLATE_NAME.pattern}"
            )
        if name in seen:
            raise ValueError(f"TEMPLATES: name {name!r} is declared more than once")
        seen.add(name)
        anchor = row["anchor"]
        if anchor not in fields:
            raise ValueError(
                f"TEMPLATES[{name!r}]: anchor {anchor!r} is not a field of "
                f"this pack — {sorted(fields)}"
            )
        if fields[anchor] is not Rung.L1:
            raise ValueError(
                f"TEMPLATES[{name!r}]: anchor {anchor!r} is "
                f"{fields[anchor].value}, not L1"
            )
        if not isinstance(row["days"], int) or isinstance(row["days"], bool) or row["days"] <= 0:
            raise ValueError(f"TEMPLATES[{name!r}]: days must be a positive int")
        if row["direction"] not in _DIRECTIONS:
            raise ValueError(f"TEMPLATES[{name!r}]: bad direction")
        if row["rule"] not in _COUNTING_RULES:
            raise ValueError(f"TEMPLATES[{name!r}]: bad rule")
        if (row["direction"] == "backward") != (row["rule"] == "court_days_before"):
            raise ValueError(f"TEMPLATES[{name!r}]: direction/rule disagree")
        if not isinstance(row["mail"], bool):
            raise ValueError(f"TEMPLATES[{name!r}]: mail must be a bool")
        if row["jurisdiction"] is not None and row["jurisdiction"] not in jurisdictions:
            raise ValueError(f"TEMPLATES[{name!r}]: jurisdiction not in {jurisdictions}")
        if row["status"] not in _STATUSES:
            raise ValueError(f"TEMPLATES[{name!r}]: bad status")
        for text_key in ("name", "source", "note"):
            if not isinstance(row[text_key], str) or not row[text_key].strip():
                raise ValueError(f"TEMPLATES[{name!r}]: {text_key} must be non-empty")


#: Empty — a grant has no court and no procedural code to count a period
#: under; every date is entered from the funder's own notice (see the
#: module docstring). Not an omission: `_check_templates` still runs, and
#: `tests/test_grant.py` plants a row against a copy of this module to
#: prove it — a check that has never fired has not been shown to check
#: anything.
TEMPLATES: tuple[dict[str, Any], ...] = ()

_check_templates(SCHEMA, FIELDS, JURISDICTIONS, TEMPLATES)
