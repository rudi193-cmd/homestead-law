"""The bankruptcy pack — a US-federal Chapter 13 case (L3-bankruptcy-ch13).

The second real pack, proving the registry seam a second time and the one the
model's own canonical contrast is built on: the engine's own bankruptcy pack
(`homestead/packs/bankruptcy.py`, 13 fields) classifies `case_number` **L1**
— public through PACER — where `custody.py` classifies the same field name
**L3**, because family records are commonly sealed. That contrast is step 5
of the classification procedure (`docs/homestead-rungs-procedure.md` § 2), and
this pack is the worked instance of it living beside `custody.py` rather than
only in the engine. Several `why` strings below are reused from the engine
pack verbatim, cited inline as `(engine bankruptcy.py: <field>)`; the rest —
every field the engine's 13 did not carry — apply the same procedure fresh to
a Chapter 13 case's own shape: the plan, its creditors, its deadlines.

**What this pack is not.** It keeps dates and references for a household
already in a Chapter 13 case. It does not decide whether Chapter 13 is the
right filing, does not draft a petition, plan or motion, and does not file
anything — decision 8 of the build-out plan, held here as two things rather
than one promise: the `NOTICE` sentence every surface renders, and an AST
guard (`tests/test_i44_no_drafting.py`, provisional I-44) that fails the build
if `Purpose.DRAFTING` or `Purpose.FILING` is ever referenced anywhere under
`homestead_law/`, and a second guard over the same tree's help text, page
copy, `why` and `derived` strings and every pack's `NOTICE` for a short list
of phrases that would turn a reference into an instruction (the list itself
lives in `tests/test_i44_no_drafting.py`, not repeated here — quoting it in
prose is exactly the shape the guard would have to special-case around).

## The plan-period interaction flag

While a bankruptcy instance is confirmed and not yet discharged, new income or
an asset arising *anywhere else* in the household's affairs is something
11 U.S.C. §§ 541(a)(7), 1306(a) and 1329 make relevant to that plan — not
something this app may evaluate. `homestead_law.plan_period` is the consumer
this bite ships (`flag(store)`), reading `plan_confirmation_date` and
`discharge_date` and scanning every *other* registered matter for a record of
`plan_period.SIGNAL_FIELDS` — Wave 8's still-unbuilt producers
(`award_amount`, `disbursement`, `safe`, `equity_grant`, `revenue_start`).
Nothing here computes from a value; the flag is one reference line, never a
number, never a block.

## Fields not on the engine's 13

`district`, `plan_filed_date`, `first_plan_payment_due`, `claims_bar_date`,
`governmental_claims_bar_date`, `confirmation_hearing_date`,
`objection_deadline`, `plan_confirmation_date`, `plan_length_months`,
`plan_payment_due_day`, `plan_payment_amount`, the repeatable `creditor.*`
group (decision 2 — one composed record per creditor, the way a custody
matter's `child` will be), `plan_modification`, `plan_completion_date`,
`debtor_education_date`. The engine's single aggregate `creditors` (L3) is
this pack's `creditor.*` decomposition of the same judgement — "aggregated
creditor data reveals the debtor's financial posture in full" — applied per
sub-field instead of to one blob, because decision 2's repeatable shape did
not exist when the engine pack was written.

## `account_number` is refused as a field name

`_refuse_account_number` runs at import, beside `classify_schema`. An account
number is ledger content — one L5 record per account instance, behind
`accounts.py`'s own boundary (decision 9, provisional I-43) — never a law
field; a bankruptcy schema that grew one by habit (schedules do list account
numbers) would duplicate L5 key material outside the one place it is allowed
to live, and do so silently, since `classify_schema` only checks that a rung
was declared, not that the field should exist at all.
"""
from __future__ import annotations

from typing import Any, Mapping

from homestead.keep.rungs import Rung, classify_schema

__all__ = [
    "MATTER", "JURISDICTION", "JURISDICTIONS", "REPEATABLE", "SCHEMA",
    "FIELDS", "NOTICE", "TEMPLATES",
]

MATTER = "bankruptcy"
JURISDICTION = "US-federal"
#: A Chapter 13 case is federal by definition (Title 11); nothing about a
#: single case moves it to another forum the way a custody order can be
#: registered in a second state, so the tuple holds one member.
JURISDICTIONS: tuple[str, ...] = ("US-federal",)


def _field(rung: Rung, why: str, *, derived: str | None = None) -> dict[str, Any]:
    decl = {"rung": rung, "matter": MATTER, "jurisdiction": JURISDICTION, "why": why}
    if derived is not None:
        decl["derived"] = derived
    return decl


#: The closed Chapter 13 schema. See the module docstring for which fields
#: are reused from the engine's own bankruptcy pack and which are new to this
#: one; every field's `why` names the step it answers (I-1…I-36's model,
#: `docs/homestead-rungs-procedure.md` § 2).
SCHEMA: dict[str, dict[str, Any]] = {
    # ── L1 — public on the docket or the confirmed plan itself (step 1) ──────
    "jurisdiction": _field(
        Rung.L1,
        "the forum's identity is public in this matter's forum (step 1); the "
        "value is one of JURISDICTIONS and is read by deadline arithmetic "
        "(decision 1) — one member here, since a Chapter 13 case does not "
        "move between forums the way a custody order can.",
    ),
    "district": _field(
        Rung.L1,
        "the federal judicial district a case is filed in is printed on the "
        "docket caption itself — public in this matter's forum (step 1).",
    ),
    "courthouse": _field(
        Rung.L1,
        "the court's public identity — public in any federal forum "
        "(step 1). (engine bankruptcy.py: courthouse)",
    ),
    "case_number": _field(
        Rung.L1,
        "the docket number — public through PACER in a bankruptcy (step 1). "
        "This is the model's worked example: L1 here, L3 for the same field "
        "name in `custody.py`, where family records are commonly sealed "
        "(step 5). (engine bankruptcy.py: case_number)",
    ),
    "chapter": _field(
        Rung.L1,
        "Chapter 7 or 13 — a procedural classification on the public docket "
        "(step 1). (engine bankruptcy.py: chapter)",
    ),
    "trustee": _field(
        Rung.L1,
        "the assigned Chapter 13 trustee is named on the public docket "
        "(step 1). (engine bankruptcy.py: trustee)",
    ),
    "petition_date": _field(
        Rung.L1,
        "the petition date — filed and entered on the public docket, the "
        "case's own trigger event (step 1). It anchors every date-arithmetic "
        "template below (`TEMPLATES`; decision 4's rule table lives in the "
        "engine's `keep.dates`); a computed value inherits L1 for the same "
        "public-forum reason the anchor itself carries, not because it was "
        "derived rather than entered.",
    ),
    "creditor_meeting_date": _field(
        Rung.L1,
        "the § 341 meeting date — posted on the court calendar and docket, "
        "public in this forum (step 1). Never computed by this pack: 11 "
        "U.S.C. § 341(a) and Rule 2003(a) set it administratively, not fewer "
        "than 21 and not more than 50 days after the order for relief, on "
        "the U.S. Trustee's own calendar — a window this pack has no primary "
        "text to count from, so it is entered directly, always. (engine "
        "bankruptcy.py: creditor_meeting_date)",
    ),
    "plan_filed_date": _field(
        Rung.L1,
        "the date the Chapter 13 plan itself was filed — a docketed filing "
        "event, public in this forum (step 1); computable via "
        "TEMPLATES['plan_filed'] and still L1 whether computed or entered, "
        "for the same reason `petition_date` is.",
    ),
    "first_plan_payment_due": _field(
        Rung.L1,
        "the date the first plan payment is due under § 1326(a)(1) — a "
        "procedural deadline of the case, public the way every other docket "
        "deadline in this schema is (step 1); computable via "
        "TEMPLATES['first_plan_payment'].",
    ),
    "claims_bar_date": _field(
        Rung.L1,
        "the general proof-of-claim deadline (FRBP 3002(c)) — a procedural "
        "case deadline, public in this forum (step 1); computable via "
        "TEMPLATES['claims_bar'].",
    ),
    "governmental_claims_bar_date": _field(
        Rung.L1,
        "the governmental-unit proof-of-claim deadline (FRBP 3002(c)(1)) — "
        "same posture as `claims_bar_date` (step 1); computable via "
        "TEMPLATES['governmental_claims_bar'].",
    ),
    "confirmation_hearing_date": _field(
        Rung.L1,
        "the confirmation hearing date and department — posted on the court "
        "calendar, public in this forum (step 1), the same reasoning as "
        "`custody.py`'s `hearing_date`. Entered directly (the clerk sets it, "
        "not this pack); it is the anchor `TEMPLATES['objection']` counts "
        "backward from.",
    ),
    "objection_deadline": _field(
        Rung.L1,
        "the deadline to object to confirmation (FRBP 3015(f)) — a "
        "procedural case deadline, public in this forum (step 1); computable "
        "via TEMPLATES['objection'], the one backward-counted, mail-eligible "
        "template in this pack.",
    ),
    "plan_confirmation_date": _field(
        Rung.L1,
        "the order confirming the plan, entered on the public docket "
        "(step 1). `homestead_law.plan_period.flag` reads this field through "
        "the gate to decide whether an instance is under a confirmed plan.",
    ),
    "plan_length_months": _field(
        Rung.L1,
        "the plan's term (36 or 60 months, § 1325(b)(4)) — a procedural term "
        "stated in the confirmed plan itself, the public order of record "
        "(step 1), the same posture as `chapter` above.",
    ),
    "plan_payment_due_day": _field(
        Rung.L1,
        "which day of the month a plan payment is due — an administrative "
        "term of the confirmed plan order, public the way `plan_length_months` "
        "is (step 1); no protected category attaches to a day-of-month "
        "(step 3 no).",
    ),
    "plan_completion_date": _field(
        Rung.L1,
        "the date the plan's payments were completed — a docketed case "
        "event once the trustee reports it, public in this forum (step 1), "
        "the same posture as `discharge_date` below.",
    ),
    "debtor_education_date": _field(
        Rung.L1,
        "the date the post-petition financial management course certificate "
        "(11 U.S.C. § 1328(g)) was filed — a docketed filing event, public "
        "in this forum (step 1); the course content itself is never a field "
        "here, only the fact and date of the filing.",
    ),
    "discharge_date": _field(
        Rung.L1,
        "the discharge order date — on the public docket once entered "
        "(step 1). `homestead_law.plan_period.flag` reads this field through "
        "the gate; its *absence* is one of the two conditions the flag "
        "requires. (engine bankruptcy.py: discharge_date)",
    ),
    "plan_modification": _field(
        Rung.L1,
        "a plan modification order is itself filed and entered on the "
        "public docket (step 1), the same posture as `chapter` and "
        "`case_number` — procedural case administrivia, not the modified "
        "figure itself. Repeatable (decision 2): one record per "
        "modification, addressed `<instance>.<sub>`.",
    ),
    # ── L2 — household, no identity, no protected category (step 1-2 no) ────
    "attorney": _field(
        Rung.L2,
        "the debtor's attorney — a person, but the name appears on the "
        "public docket as counsel of record. L2 rather than L1: the derived "
        "form masks the direct-dial and email a filing carries (step 2). "
        "(engine bankruptcy.py: attorney)",
        derived="Counsel of record is on file",
    ),
    # ── L3 — resolves to the debtor's financial posture (step 2 yes) ────────
    "plan_payment_amount": _field(
        Rung.L3,
        "resolves to the debtor's household finances (step 2), the posture "
        "`income`/`assets` below share; step 4 does not raise it further. "
        "The step-1 argument against L1: the confirmed plan stating this "
        "figure is a filed, public document, so a docket-public claim is "
        "*available* the way it is for `chapter` — but public availability "
        "of the document is not public availability of this datum's *role*; "
        "a payment figure is financial substance, not case metadata, so "
        "step 1 does not license L1 here the way it does above. This is "
        "also why LAW (L3) and the LEDGER (L4, `docs/homestead-rungs-"
        "procedure.md` § 6) disagree without contradiction (Open item 4): "
        "the ledger's `amount` is a *transaction event's* figure, money as "
        "step 3 there; a plan payment is one *stated figure* in a court "
        "order, not a transaction — a different datum, each pack's model "
        "internally consistent at its own rung.",
        derived="A scheduled plan payment amount is on file",
    ),
    "income": _field(
        Rung.L3,
        "the debtor's household income — resolves to a person's financial "
        "situation (step 2 yes, step 3 no). Filed under seal in some "
        "districts but required for the means test. (engine bankruptcy.py: "
        "income)",
        derived="Household income is on file",
    ),
    "assets": _field(
        Rung.L3,
        "the debtor's asset schedule — resolves to financial position "
        "(step 2). Public on the docket but aggregated here as structured "
        "data. (engine bankruptcy.py: assets)",
        derived="An asset schedule is on file",
    ),
    "creditor.name": _field(
        Rung.L3,
        "a creditor's identity, one of decision 2's repeatable sub-fields — "
        "the per-creditor decomposition of the engine pack's aggregate "
        "`creditors` field: 'the list of creditors and amounts owed — "
        "resolves to the debtor's financial obligations (step 2 yes)... "
        "aggregated creditor data reveals the debtor's financial posture in "
        "full' (engine bankruptcy.py: creditors). One name at a time still "
        "resolves to the same posture; step 4 does not raise it.",
        derived="A creditor is named",
    ),
    "creditor.amount_scheduled": _field(
        Rung.L3,
        "the amount scheduled as owed to one creditor — the same financial-"
        "obligation posture as `creditor.name` (step 2), from the same "
        "engine-pack `creditors` reasoning decomposed per decision 2.",
        derived="A scheduled creditor amount is on file",
    ),
    "creditor.claim_amount": _field(
        Rung.L3,
        "the amount actually claimed once a proof of claim is filed — same "
        "posture as `creditor.amount_scheduled` (step 2); the two can "
        "differ, and both resolve to the debtor's financial obligations "
        "regardless.",
        derived="A claimed amount is on file",
    ),
    # ── L1 — a claim's own docket/register facts (step 1, distinct from the
    #        creditor's name and the amounts above) ──────────────────────────
    "creditor.secured": _field(
        Rung.L1,
        "secured/unsecured status is a procedural classification of the "
        "filed claim, itself part of the public claims register (step 1) — "
        "distinct from the creditor's name and the amounts above, which "
        "resolve to the debtor's financial substance (step 2) rather than "
        "case administrivia.",
    ),
    "creditor.claim_filed_date": _field(
        Rung.L1,
        "the date a proof of claim was filed — a docket event date, public "
        "in this forum (step 1), the same posture as `plan_filed_date` and "
        "every other filing date in this schema.",
    ),
    "creditor.claim_number": _field(
        Rung.L1,
        "the claim's own number on the public claims register — public "
        "through PACER the way `case_number` is (step 1).",
    ),
    # ── L4 — protected: resolves to a person/entity and carries a category
    #        the law follows (step 3) ────────────────────────────────────────
    "creditor.note": _field(
        Rung.L4,
        "free operator text about one creditor — same posture as "
        "`custody.py`'s `notes`: resolves to a party (step 2) and routinely "
        "carries dispute strategy or a protected category the model must "
        "not see (step 3). L4 blocks it from S2 (ceiling L2) and S3.",
        derived="An operator note on a creditor is on file",
    ),
    "notes": _field(
        Rung.L4,
        "free operator text that may carry protected content — same "
        "posture as custody's `notes` field: resolves to a person and "
        "routinely carries categories a model prompt must not see (step 3). "
        "L4 blocks it from S2 (ceiling L2) and S3. (engine bankruptcy.py: "
        "notes)",
        derived="An operator note is on file",
    ),
    # ── L5 — sealed, no override (step 4) ────────────────────────────────────
    "ssn": _field(
        Rung.L5,
        "key material — sealed, and L5 has no override anywhere (step 4). "
        "Bankruptcy filings use the last four digits on the docket; the "
        "full SSN is in the petition, filed under seal. (engine "
        "bankruptcy.py: ssn)",
    ),
}


def _refuse_account_number(schema: Mapping[str, Any]) -> None:
    """Build-time guard: `account_number` may never be a field of this pack.

    An account number belongs to the ledger's own account instance — one L5
    record per account (decision 9, provisional I-43) — never to a matter's
    own schema. `classify_schema` only checks that a declared rung is
    *readable*, not that the field should exist at all (`custody.py`'s own
    words: "a lock on an empty room" for the wrong question), so a field this
    dangerous needs a guard that asks the right one. Raised, not merely
    documented, so a future edit that adds it back fails the build rather
    than shipping a second, unsealed home for the same key material."""
    if "account_number" in schema:
        raise ValueError(
            "bankruptcy pack: 'account_number' is refused as a field name — "
            "an account number is ledger content (one L5 record per account "
            "instance, provisional I-43), never a law field. Track the "
            "creditor and the amount here; the number stays in the ledger's "
            "own account instance."
        )


_refuse_account_number(SCHEMA)

#: Field names that may carry a sub-id (decision 2) — the per-creditor
#: sub-fields, and one modification-order record per entry.
REPEATABLE: frozenset[str] = frozenset(
    {
        "creditor.name",
        "creditor.amount_scheduled",
        "creditor.claim_amount",
        "creditor.secured",
        "creditor.claim_filed_date",
        "creditor.claim_number",
        "creditor.note",
        "plan_modification",
    }
)

#: Classified at import (I-11). This line is the build failure: remove any
#: field's rung above and the process defining the schema dies, naming the
#: field.
FIELDS: dict[str, Rung] = classify_schema(SCHEMA)

#: Rendered by every surface that opens this matter (decision 8). Track,
#: never draft, never file, never diagnose which chapter fits.
NOTICE = (
    "This pack keeps dates and references for a Chapter 13 case. It drafts "
    "nothing, files nothing, and does not say which chapter fits."
)

# ── deadline templates (data only — L3-deadline-templates' rules.py reads
#    this table and does the arithmetic; nothing here imports rules.py or
#    homestead.keep.dates) ────────────────────────────────────────────────────

#: PROVENANCE, 2026-09-11: every primary host this environment could try —
#: law.cornell.edu, uscode.house.gov, govinfo.gov, law.abi.org,
#: federalrulesofbankruptcyprocedure.org, codes.findlaw.com — is refused by
#: this environment's egress proxy, on the build pass (the same wall the
#: engine's own `keep/dates.py` RULES table documents hitting for FRBP 9006).
#: `VERIFIED` below is claimed on **converging independent secondary
#: sources**, reached through the one channel that answered: several current,
#: independent U.S. Bankruptcy Court websites (local rules and guidance
#: pages, not commercial restatements alone) agreeing clause-for-clause on
#: each provision's day count, direction and trigger event, for text that is
#: settled, uncontested federal procedural law. Not a primary quotation read
#: here; replace with one the first time a primary host is reachable, and do
#: not delete this sentence without one.
_PROVENANCE_5015B = (
    "FRBP 3015(b): the debtor 'shall file a plan' with the petition, or if "
    "the case began by conversion, within 14 days after the petition is "
    "filed or the conversion order is entered, extendable only for cause on "
    "notice — cob.uscourts.gov (D. Colo. LBR 3015-1), insb.uscourts.gov "
    "(S.D. Ind. B-3015-1), nvb.uscourts.gov (D. Nev. Local Rule 3015) and "
    "lifebacklaw.com's FRBP text converge on the 14-day figure and the "
    "'petition or conversion' trigger. PROVENANCE, 2026-09-11 — see the "
    "module-level note above."
)
_PROVENANCE_1326A1 = (
    "11 U.S.C. § 1326(a)(1): 'Unless the court orders otherwise, the debtor "
    "shall commence making payments not later than 30 days after the date "
    "of the filing of the plan or the order for relief, whichever is "
    "earlier' — findlaw.com, justia.com, uscourts.gov's Chapter 13 Basics "
    "page and govinfo.gov's USCODE HTML converge on the figure, the "
    "trigger, and the 'whichever is earlier' clause. Anchors on "
    "`petition_date` alone (the voluntary-petition common case, where the "
    "order for relief is the petition date): the clause compares the "
    "plan-filing and order-for-relief triggers, not the payment date "
    "itself, so a plan filed early does not move this date earlier. "
    "PROVENANCE, 2026-09-11 — see the module-level note above."
)
_PROVENANCE_3002C = (
    "FRBP 3002(c): in a voluntary Chapter 13 case, a proof of claim is "
    "timely if filed within 70 days after the order for relief — "
    "lexology.com, kts-law.com, klgates.com and lifebacklaw.com's FRBP text "
    "converge on the 70-day figure for a voluntary Chapter 13/7/12 case. "
    "PROVENANCE, 2026-09-11 — see the module-level note above."
)
_PROVENANCE_3002C1 = (
    "FRBP 3002(c)(1): a governmental unit's proof of claim is timely if "
    "filed within 180 days after the order for relief — kts-law.com, "
    "legalwritingexperts.com and lifebacklaw.com's FRBP text converge on "
    "the 180-day figure and the governmental-unit trigger (a narrower rule, "
    "for a tax-return-based claim under § 1308, is not modelled here). "
    "PROVENANCE, 2026-09-11 — see the module-level note above."
)
_PROVENANCE_3015F = (
    "FRBP 3015(f): an objection to confirmation 'shall be filed and served "
    "on the debtor, the trustee, and any other entity designated by the "
    "court, and shall be transmitted to the United States trustee, within "
    "the time determined by the court' but 'shall be filed and served ... "
    "at least 7 days before the date set for the hearing on confirmation, "
    "unless the court orders otherwise' — cacb.uscourts.gov, "
    "prb.uscourts.gov, neb.uscourts.gov and casb.uscourts.gov's local-rule "
    "pages converge on the 7-day, counted-backward-from-the-hearing shape. "
    "Several districts expand this by local rule (e.g. LBR 3015-1(g)(1)'s "
    "14 days in at least one district found during this search) — this "
    "template encodes the FRBP default only; a local rule that lengthens it "
    "is not modelled and must be checked against the district's own local "
    "rules before relying on this figure. PROVENANCE, 2026-09-11 — see the "
    "module-level note above."
)

#: One row per computable Chapter 13 deadline. Consumed by the sibling
#: L3-deadline-templates bite's `rules.py`, never imported here — this table
#: is data, not arithmetic. Shape: name, anchor (must name an L1 field of
#: this pack — `_check_templates` below enforces it), days, direction
#: ("forward"/"backward"), rule ("court_days"/"court_days_before"/
#: "business_days"/"calendar_days"), mail (bool), jurisdiction (a member of
#: JURISDICTIONS or None), source (a cited, dated PROVENANCE sentence),
#: status ("VERIFIED"/"UNCERTAIN"), note.
TEMPLATES: dict[str, dict[str, Any]] = {
    "plan_filed": {
        "name": "plan_filed",
        "anchor": "petition_date",
        "days": 14,
        "direction": "forward",
        "rule": "court_days",
        "mail": False,
        "jurisdiction": "US-federal",
        "source": _PROVENANCE_5015B,
        "status": "VERIFIED",
        "note": "Extendable only for cause on notice; this template computes "
                "the unextended deadline.",
    },
    "first_plan_payment": {
        "name": "first_plan_payment",
        "anchor": "petition_date",
        "days": 30,
        "direction": "forward",
        "rule": "calendar_days",
        "mail": False,
        "jurisdiction": "US-federal",
        "source": _PROVENANCE_1326A1,
        "status": "VERIFIED",
        "note": "Calendar days, not court days — § 1326(a)(1) does not cite "
                "FRBP 9006(a); 'unless the court orders otherwise' is not "
                "modelled.",
    },
    "claims_bar": {
        "name": "claims_bar",
        "anchor": "petition_date",
        "days": 70,
        "direction": "forward",
        "rule": "court_days",
        "mail": False,
        "jurisdiction": "US-federal",
        "source": _PROVENANCE_3002C,
        "status": "VERIFIED",
        "note": "Voluntary-case figure; an involuntary Chapter 7 case's "
                "90-day figure is not modelled (this pack is Chapter 13).",
    },
    "governmental_claims_bar": {
        "name": "governmental_claims_bar",
        "anchor": "petition_date",
        "days": 180,
        "direction": "forward",
        "rule": "court_days",
        "mail": False,
        "jurisdiction": "US-federal",
        "source": _PROVENANCE_3002C1,
        "status": "VERIFIED",
        "note": "The narrower § 1308 tax-return-claim window is not modelled.",
    },
    "objection": {
        "name": "objection",
        "anchor": "confirmation_hearing_date",
        "days": 7,
        "direction": "backward",
        "rule": "court_days_before",
        "mail": True,
        "jurisdiction": "US-federal",
        "source": _PROVENANCE_3015F,
        "status": "VERIFIED",
        "note": "A local rule may lengthen this (one district's own guidance "
                "found during this search expands it to 14 days) — confirm "
                "against the district's local rules before relying on the "
                "FRBP default this template encodes.",
    },
}

_TEMPLATE_KEYS = frozenset(
    {"name", "anchor", "days", "direction", "rule", "mail", "jurisdiction",
     "source", "status", "note"}
)
_DIRECTIONS = frozenset({"forward", "backward"})
_COUNTING_RULES = frozenset(
    {"court_days", "court_days_before", "business_days", "calendar_days"}
)
_STATUSES = frozenset({"VERIFIED", "UNCERTAIN"})


def _check_templates(
    schema: Mapping[str, Any],
    fields: Mapping[str, Rung],
    jurisdictions: tuple[str, ...],
    templates: Mapping[str, Mapping[str, Any]],
) -> None:
    """The local shape check decision 4/L3-deadline-templates leans on: every
    template in `templates` carries exactly the ten declared keys, each of
    the right shape, and its `anchor` names an **L1** field of this pack —
    the sibling `rules.py` bite reads the anchor through the gate and only an
    L1 field renders unconditionally there. Raised at import, naming the
    template and the failure, the way every other guard in this package
    fails closed rather than deferring to whichever caller reads the table
    first."""
    for template_name, row in templates.items():
        if not isinstance(row, Mapping) or set(row) != _TEMPLATE_KEYS:
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: keys must be exactly "
                f"{sorted(_TEMPLATE_KEYS)}, not {sorted(row) if isinstance(row, Mapping) else row!r}"
            )
        anchor = row["anchor"]
        if anchor not in fields:
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: anchor {anchor!r} is not a "
                f"field of this pack — {sorted(fields)}"
            )
        if fields[anchor] is not Rung.L1:
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: anchor {anchor!r} is "
                f"{fields[anchor].value}, not L1 — an anchor a counting rule "
                "reads must render unconditionally, which only L1 does on "
                "every surface."
            )
        if not isinstance(row["days"], int) or isinstance(row["days"], bool) or row["days"] < 0:
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: days must be a non-negative "
                f"int, not {row['days']!r}"
            )
        if row["direction"] not in _DIRECTIONS:
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: direction {row['direction']!r} "
                f"not in {sorted(_DIRECTIONS)}"
            )
        if row["rule"] not in _COUNTING_RULES:
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: rule {row['rule']!r} not in "
                f"{sorted(_COUNTING_RULES)}"
            )
        if not isinstance(row["mail"], bool):
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: mail must be a bool, not "
                f"{row['mail']!r}"
            )
        if row["jurisdiction"] is not None and row["jurisdiction"] not in jurisdictions:
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: jurisdiction "
                f"{row['jurisdiction']!r} is not None and not in "
                f"{jurisdictions}"
            )
        if row["status"] not in _STATUSES:
            raise ValueError(
                f"TEMPLATES[{template_name!r}]: status {row['status']!r} not "
                f"in {sorted(_STATUSES)}"
            )
        for text_key in ("name", "source", "note"):
            if not isinstance(row[text_key], str) or not row[text_key].strip():
                raise ValueError(
                    f"TEMPLATES[{template_name!r}]: {text_key} must be a "
                    "non-empty string"
                )


_check_templates(SCHEMA, FIELDS, JURISDICTIONS, TEMPLATES)
