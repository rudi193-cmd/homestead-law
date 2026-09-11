"""The custody pack — the first real schema in the package (bite 2).

A custody matter, classified at **import**. `classify_schema(SCHEMA)` runs
at module top level, so an author who adds a field and forgets its rung stops the
build with that field named (I-11) — the refusal Phase 2 built and tested against
synthetic schemas, now aimed at a real one. Until this pack existed, that refusal
was, in `DECISION-unclassified-field-instrument.md`'s phrase, *"a lock on an
empty room."*

**The rungs are declared, never inferred from the field name.** A case number is
`L1` in a bankruptcy (dockets are public) and `L3` in a family matter (records
are commonly sealed), so nothing here is keyed on a name — the same field name
takes different rungs in different matters, and only a declaration knows which.
`docs/homestead-rungs.md` § "Classifying a new field" is the procedure; each
field below carries the answer to its five steps in `why`, alongside the matter
and jurisdiction step 5 requires.

**Each field is a mapping, not a bare rung, on purpose.** `classify_schema` reads
the `"rung"` key and ignores the rest, so a pack can carry the matter, the
jurisdiction and the sentence that justifies the rung — the reviewable record a
rung is useless without. A reviewer cannot check `L3` for a case number without
knowing it is a *family* case number, and the field says so.

**What this pack cannot catch, and does not pretend to.** `classify_schema`
checks that a rung was *declared*, not that it was declared *well*: it would
accept `L1` for `ssn` without a murmur. The advisory content check that would
flag a rung shaped wrong for its content — declared `L1`, content shaped like an
SSN — is the next bite, and it may only ever argue a rung *up*, never down.

## The household's move (decision 1, plan wave 2)

This household's custody matter is a New Mexico order being registered
(UCCJEA) in Oregon after the relocation. ~~`JURISDICTION = "US-CA"`~~ (struck
2026-09-11 — the household's actual forum is New Mexico, moving to Oregon; the
rung rationales below do not change on that account: family records are
commonly sealed in both states, the same posture the old `"US-CA"` reasons
already argued). `JURISDICTION` is now `"US-NM"`, the forum the order was
entered in; `JURISDICTIONS` adds `"US-OR"`, the forum the order is being
registered into — `set_jurisdiction` (Wave 3) is what will actually move an
instance between them, and `_validate` (`homestead_law/registry.py`) requires
the default itself be one of the tuple's members.

**`derived` (decision 3).** Every `L3`/`L4` field below now also carries a
`"derived"` sentence — the stand-in text a surface shows in place of the
payload. Where the engine's own 0.3.0 custody pack classifies the same field
name (`case_number`, `docket`, `opposing_party`, `parenting_time`,
`child_name`, `diagnosis`, `notes`), the sentence is copied verbatim from it —
`tests/test_packs.py::test_derived_forms_match_the_engine_pack_where_the_field_exists`
holds the two packs to the same text by comparison, not by promise, so they
cannot drift the way the CLI's and the browser UI's now-deleted copies of this
same table already had (both read `homestead.keep.rungs.derived_of(schema,
field)` instead, as of this bite).

## The relocation (L3-custody-relocation, wave 3)

This bite adds the fields the move itself needs: the custody arrangement and
its order date, the move and the notice given for it, the new state, and the
UCCJEA registration/contest/mediation dates — and it repeats one field that
used to be singular. ~~`child_name`~~ (struck 2026-09-11) assumed one child;
this household has two. A household with more than one minor could not tell
`show custody child_name` which child it meant, and a second `put` silently
overwrote the first — the exact single-slot failure `instances.py`'s
`item_id(instance, sub)` exists to fix, one level down from matter instances,
at *sub-records within one instance*. `child_name` is **kept, not deleted**
(house style: struck through, never removed) — every doorway that already
names it (`cli.py`'s `party_fields`, `server.py`'s intake form, the existing
regression tests) is real, in-scope code and coverage this bite does not touch,
and retiring the field out from under them is a separate, cross-file bite.
What is new: `child.name`, `child.dob` and `child.school` — one record per
child per field, addressed by a sub-id (`--sub c1`, `--sub c2`, …) the operator
composes freely (I-15: a sub-id is a label, never a name) — declared
`REPEATABLE` so `put`'s `--sub` accepts them and `instances.item_id` composes
`"<instance>.<sub>"` for the stored key — and so that `put` *requires* a
`--sub` for them: a repeatable field written without one lands in the single
slot the whole sub-id shape exists to abolish, where the second child
overwrites the first (`cli._cmd_put`/`server._post_store`, both amended by
this bite's audit, 2026-09-11; the refusal names the field, never a value).

**`REPEATABLE` names the three dotted fields, not the bare word `child`.**
`cli._cmd_put` checks `field not in mt.repeatable` against the *exact* string
the operator typed as the field (`"child.name"`, not `"child"` — there is no
CLI syntax that composes a value from three separate field arguments into one
record the way `homestead_health.doses.add_dose` does from a Python caller),
so a `REPEATABLE` naming only `"child"` would make every one of `put custody
child.name … --sub c1` / `child.dob …` / `child.school …` refuse with "not
declared REPEATABLE" — the door decision 2 exists to open. The registry's own
guard (`unknown_repeatable = ... if f not in entry.fields`) reads the same
way: a `"child"` entry would need a bare `"child"` field in `SCHEMA` that
nothing else here defines. Three flat `L4` fields, each independently
addressable by sub-id, is what this pack's own write door can actually drive
end to end. **The plan's `REPEATABLE = {"child"}` shorthand was loose**
(audit, 2026-09-11): decision 2 says a pack "declares `REPEATABLE`", and the
two guards that read it — `cli._cmd_put`'s `field not in mt.repeatable` and
`registry._validate`'s `unknown_repeatable = ... if f not in entry.fields` —
both compare a member against a *field name*, so the contract `REPEATABLE`
actually has is "a set of this pack's own field names", and the bare word
`"child"` is not one. The plan's shorthand named the concept; the frozenset
below names the fields.

## Deadline templates as data (L3-deadline-templates, parallel)

`TEMPLATES` is read-only data for the sibling bite's `rules.py` — this pack
never imports it and never computes a date itself (I-2: arithmetic is the
engine's, one door). Three rules hold every row here, and all three are
checked locally by `tests/test_custody_templates.py` so this pack cannot
become a build failure in the bite that reads it:

1. **Every anchor is an `L1` field of this pack. No exception.** A template
   reads its anchor through the gate and then *names* it in a refusal; only
   the public-in-this-forum rung can survive both. Both rows below anchor on
   `uccjea_registration_date`.
2. **Every `name` is a sub-id** — `^[a-z0-9][a-z0-9-]{0,39}$` (decision 2),
   because `--accept` stores the computed date at `(matter, "deadline",
   "<instance>.<template>")` and `instances.item_id` validates both halves.
   An underscore in a template name is a date that can never be filed.
3. **Every `name` is unique within the pack**, jurisdiction included in the
   name where two forums have the same deadline under different counts. A
   template is looked up by name; the jurisdiction is a property of the
   *instance*, not of the command, so two rows sharing one name would make
   the lookup pick whichever came first and silently count a New Mexico
   period for an Oregon instance.

**~~`relocation_notice` (`move_date`, −60 days, `US-OR`)~~ — struck
2026-09-11.** ORS 107.159 requires "reasonable notice" and fixes no day
count, so there is no period to count and the row's own `status` was
`UNCERTAIN` with a `note` saying the operator enters the date. A computed
template that refuses every call buys nothing, and its anchor (`move_date`,
`L3` two sections below) was the single exception to rule 1 above. Oregon's
relocation notice is **entered, not computed**: the operator files the date
they actually gave notice as `relocation_notice_date`, and the app keeps it
without pretending to have derived it (I-11: refuse by name, never guess —
here the refusal is the absence of a template, which is the honest shape for
a statute that states no number). `move_date` stays `L3`; nothing about a
family's moving date is public in this forum on its own.
"""
from __future__ import annotations

from typing import Any

from homestead.keep.rungs import Rung, classify_schema

__all__ = [
    "MATTER", "JURISDICTION", "JURISDICTIONS", "REPEATABLE", "SCHEMA", "FIELDS",
    "TEMPLATES",
]

MATTER = "custody"
JURISDICTION = "US-NM"
#: Every jurisdiction an instance of this matter may be filed under. `JURISDICTION`
#: is the default a new instance starts with; a matter registered in one of these
#: (`set_jurisdiction`, Wave 3) may move to another, and `_validate` (decision 1)
#: requires the default itself be one of the tuple's members. NM is the order's
#: original forum; OR is where this household's order is being registered after
#: the relocation.
JURISDICTIONS: tuple[str, ...] = ("US-NM", "US-OR")

#: Field names that may carry a sub-id (`homestead_law.instances`, decision 2)
#: — a repeatable sub-record within one instance, e.g. a child of a custody
#: matter, one dose per subject. The three dotted `child.*` fields below, one
#: per child per field (`--sub c1`, `--sub c2`, …) — see the module docstring's
#: "The relocation" section for why this names the three fields themselves
#: rather than the bare word `"child"`: `cli._cmd_put` and the registry's own
#: `unknown_repeatable` guard both check a `REPEATABLE` member against the
#: literal field string, and there is no field literally named `"child"`.
REPEATABLE: frozenset[str] = frozenset({"child.name", "child.dob", "child.school"})


def _field(rung: Rung, why: str, *, derived: str | None = None) -> dict[str, Any]:
    decl = {"rung": rung, "matter": MATTER, "jurisdiction": JURISDICTION, "why": why}
    if derived is not None:
        decl["derived"] = derived
    return decl


#: The closed custody schema. Field → declaration (rung + matter + jurisdiction +
#: reason). Ordered by rung so the ladder reads down the page. Nothing here is
#: keyed on the field name; the rung is a property of the field *in this matter
#: and jurisdiction* (step 5), which is why the same name can sit elsewhere.
SCHEMA: dict[str, dict[str, Any]] = {
    "courthouse": _field(
        Rung.L1,
        "the court's public identity — public in this matter's forum (step 1)",
    ),
    "hearing_date": _field(
        Rung.L1,
        "the hearing's date, time and department — posted on the court calendar, "
        "so public in this matter's forum (step 1). homestead-rungs.md "
        "§ Custody classifies it L1 for that reason; the doc's worked example "
        "is 'Hearing · Aug 15 · 8:30 am · Dept 3 · County Courthouse.'",
    ),
    "jurisdiction": _field(
        Rung.L1,
        "the forum's identity is public in this matter's forum (step 1); the "
        "value is one of JURISDICTIONS and is read by deadline arithmetic "
        "(decision 1).",
    ),
    "case_number": _field(
        Rung.L3,
        "resolves to the parties, no protected category. The model's worked "
        "example: L1 in a bankruptcy where the docket is public, L3 in a family "
        "matter where records are commonly sealed (step 2, then step 4 does not "
        "raise it).",
        derived="A case number is on file",
    ),
    "docket": _field(
        Rung.L3,
        "same posture as the case number in a family matter — resolves to the "
        "parties (step 2), commonly sealed but not itself key material or a "
        "refusal (step 4 does not raise it).",
        derived="A docket entry is on file",
    ),
    "opposing_party": _field(
        Rung.L3,
        "names the co-parent — a person — with no protected category attached to "
        "the name itself (step 2 yes, step 3 no).",
        derived="The other parent is named",
    ),
    "child_name": _field(
        Rung.L4,
        "names a person who is a minor. A minor is a category the law follows "
        "(step 3 yes), and the whole model turns on not rendering it by "
        "default. ~~Superseded 2026-09-11 by the repeatable `child.name`~~ "
        "— struck, never deleted, and still a real classified field: "
        "`cli.py`'s `party_fields`, `server.py`'s intake form and "
        "`app/demo.py` all still address it. ~~**L4-surfaces (wave 4) is the "
        "bite that retires it**, because that is the bite that already "
        "rewrites every door naming it~~ (struck, X7-drift audit, "
        "2026-09-11: L4-surfaces landed and left every door named above "
        "unchanged — retiring `child_name` is a separate, still-open bite, "
        "named `L9-child-name` and tracked in "
        "`docs/PLAN-affairs-face.md`); until it lands, "
        "`tests/test_packs.py::test_child_name_and_child_dot_name_both_exist"
        "_until_l4_surfaces_retires_it` holds both on file so the retirement "
        "is a visible, failing-by-design change rather than a silent one "
        "(step 3 is unchanged by any of this).",
        derived="A minor child is named in this matter",
    ),
    "parenting_time": _field(
        Rung.L3,
        "the parenting schedule — resolves to the child (step 2), which "
        "homestead-rungs.md § Custody classifies L3. The operator sees it on "
        "their own list; a model prompt (S2, ceiling L2) gets only the derived "
        "form. Not L4: it resolves to the child but does not itself carry a "
        "protected category the way a diagnosis does.\n"
        "The doc's worked example of a derived form for this field is 'a "
        "recurring parenting-time obligation on Tue/Thu' (PHASE2-SURFACES.md), "
        "and that sentence is a *record's* stand-in, composed for one schedule "
        "that really does fall on those days. A schema declares one sentence "
        "for every instance of the field, so it may not name the days: on the "
        "household whose schedule is Mon/Wed it would be false, and on the "
        "household whose schedule is Tue/Thu it would restate exactly the "
        "value the derived form exists to withhold. The declaration below "
        "carries the shape of the obligation and nothing that varies.",
        derived="A recurring parenting-time obligation is on file",
    ),
    "diagnosis": _field(
        Rung.L4,
        "a medical category attached to a person (step 3). 'Medical' belongs to "
        "the rung, which carries it at L4; it never reaches a model prompt.",
        derived="A medical category is on file for a person",
    ),
    "notes": _field(
        Rung.L4,
        "free operator text that resolves to a person (step 2) and routinely "
        "carries a protected category (step 3) — substance use, a diagnosis, "
        "an allegation (F-4 was "
        "exactly this content leaking). L4 blocks the F-3/F-4 shape: a note never "
        "reaches a model prompt (S2, ceiling L2 → derived) or an agent (I-15), "
        "and the operator reads their own note in the detail pane. **Kept at L4 "
        "by decision (2026-08-10), against the bite-1-3 audit that argued L5** — "
        "see docs/audits/bites-1-3-remediation.md. The residual the audit named "
        "is real: a note holding L5-worthy content would egress on a "
        "purpose-declared S4 export, past L5's no-egress rule. Closing it needs a "
        "per-field operator-visible / non-exportable split, which the one-rung "
        "model does not express; until that lands the advisory content matcher "
        "(declared L4, content shaped like an L5 datum → raise) is the intended "
        "guard, and v1 is synthetic-data-only. Not L5: a note the operator cannot "
        "read is not a note.",
        derived="An operator note is on file",
    ),
    # ── L3-custody-relocation (wave 3) ───────────────────────────────────────
    "custody_order_date": _field(
        Rung.L1,
        "the date the underlying custody order was entered is a fact of the "
        "court record, posted alongside the hearing and docket — public in "
        "this matter's forum (step 1).",
    ),
    "uccjea_registration_date": _field(
        Rung.L1,
        "the date the order was registered with the receiving forum is a "
        "fact of that forum's own public court record once filed (step 1).",
    ),
    "registration_contest_deadline": _field(
        Rung.L1,
        "the deadline to contest a UCCJEA registration is posted on the "
        "court calendar the same way a hearing date is — public in this "
        "matter's forum (step 1), the same posture as hearing_date.",
    ),
    "mediation_date": _field(
        Rung.L1,
        "a court-ordered mediation session's date and time are posted on "
        "the court calendar alongside the hearing — public in this matter's "
        "forum (step 1), the same posture as hearing_date.",
    ),
    "new_residence_state": _field(
        Rung.L2,
        "the destination state is a household-level fact — a coarse "
        "geography that does not by itself resolve to any one person "
        "(step 2 no) and carries no protected category, so it stays at the "
        "household rung rather than climbing to an attributed one.",
    ),
    "custody_type": _field(
        Rung.L3,
        "the arrangement's shape (sole, joint, legal, physical) resolves to "
        "the family's parenting structure (step 2 yes) but is not itself a "
        "protected category (step 3 no) — the same posture parenting_time "
        "already holds.",
        derived="A custody arrangement type is on file",
    ),
    "move_date": _field(
        Rung.L3,
        "the date of the household's relocation resolves to the child's and "
        "co-parent's whereabouts and schedule (step 2 yes) but is not "
        "itself a protected category (step 3 no) — the same posture as "
        "case_number and parenting_time. Not L1 despite being a fact the "
        "household may eventually tell the court: nothing makes a family's "
        "moving date public in this forum on its own.",
        derived="A move date is on file",
    ),
    "relocation_notice_date": _field(
        Rung.L3,
        "the date notice of the move was given to the other parent resolves "
        "to that party (step 2 yes) but is not itself a protected category "
        "(step 3 no) — the same posture as opposing_party and docket.",
        derived="A relocation notice date is on file",
    ),
    "child.name": _field(
        Rung.L4,
        "resolves to one specific child (step 2), who is a minor — a "
        "category the law follows (step 3 yes); the same posture "
        "~~child_name~~ always carried, now declared per sub-field so a "
        "second child does not overwrite the first (struck 2026-09-11, see "
        "the module docstring).",
        derived="A child's name is on file",
    ),
    "child.dob": _field(
        Rung.L4,
        "resolves to that same minor (step 2); a birth date attached to a "
        "minor is itself protected — the identifying detail a "
        "category-following rule treats as sensitive for a child the same "
        "way a diagnosis is for a health record (step 3 yes).",
        derived="A child's date of birth is on file",
    ),
    "child.school": _field(
        Rung.L4,
        "resolves to that same minor (step 2); the school a child attends "
        "is safety-sensitive content — a minor's daily location is exactly "
        "the kind of category-carrying fact notes and diagnosis already "
        "hold at this rung (step 3 yes).",
        derived="A school is on file",
    ),
    "ssn": _field(
        Rung.L5,
        "key material — sealed, and L5 has no override anywhere (step 4). The "
        "corpus's canonical L5 datum; served on no surface, in any form.",
    ),
}

#: Classified at import (I-11). This line is the build failure: remove any
#: field's rung above and the process defining the schema dies, naming the field.
FIELDS: dict[str, Rung] = classify_schema(SCHEMA)

#: Deadline templates, as data (L3-deadline-templates, parallel bite). Neither
#: pack imports the other; `rules.py`'s `compute()` reads this tuple and this
#: pack's `SCHEMA`/`FIELDS`, never the reverse. Every row obeys the three rules
#: in the module docstring's "Deadline templates as data" section: an `L1`
#: anchor, a `name` that is a legal sub-id, and a `name` unique in this pack.
#: Every `source` carries a citation and, where the primary text could not be
#: read from this build, a dated `PROVENANCE` sentence saying so and naming
#: what was read instead — the engine's own `RuleStatus` docstring is the
#: standard: `VERIFIED` means "checked, and the source says against what", and
#: a row may never be `VERIFIED` on a `source` that does not say where its text
#: came from. `UNCERTAIN` means "not checked", and `compute()` refuses rather
#: than count from it (I-11).
#:
#: No relocation-notice row in either forum: New Mexico has none, and Oregon's
#: (ORS 107.159) states no day count at all — see the module docstring.
TEMPLATES = (
    {
        "name": "nm-registration-contest",
        "anchor": "uccjea_registration_date",
        "days": 20,
        "direction": "forward",
        "rule": "court_days",
        "mail": False,
        "jurisdiction": "US-NM",
        "source": (
            "NMSA 1978 § 40-10A-305 (New Mexico's enactment of UCCJEA § 305): "
            "a person contesting the validity of a registered child-custody "
            "determination must request a hearing within twenty days after "
            "service of the notice, and failure to contest confirms the "
            "determination. PROVENANCE, 2026-09-11 (audit): the primary text "
            "was NOT read here — law.justia.com, nmonesource.com, "
            "codes.findlaw.com, www.womenslaw.org and law.cornell.edu are all "
            "refused by this environment's egress proxy, on the build pass and "
            "again on audit. VERIFIED is claimed on converging restatements "
            "that agree on the number and on the surrounding clauses: the "
            "New Mexico section itself restated with its notice-contents and "
            "contest clauses intact, and four other states' enactments of the "
            "same uniform section (Tex. Fam. Code § 152.305, Minn. Stat. "
            "§ 518D.305, Mont. Code § 40-7-305, W. Va. Code § 48-20-305) all "
            "at twenty days — convergence that is not mere parroting of the "
            "uniform number, since Oregon's enactment of the same section "
            "reads twenty-one and is carried below as UNCERTAIN for exactly "
            "that reason. The pinpoint subsection letter is deliberately NOT "
            "cited: restatements place the count in the notice-contents and "
            "contest subsections ((c) and (d) in the uniform numbering) and "
            "the letter could not be confirmed from here. Read the primary "
            "before relying on this."
        ),
        "status": "VERIFIED",
        "note": (
            "counted from service of the notice, which the operator enters as "
            "the anchor; confirm against the court's own notice"
        ),
    },
    {
        "name": "or-registration-contest",
        "anchor": "uccjea_registration_date",
        "days": 21,
        "direction": "forward",
        "rule": "court_days",
        "mail": False,
        "jurisdiction": "US-OR",
        "source": (
            "ORS 109.787 (Oregon's enactment of UCCJEA § 305). UNCERTAIN, "
            "2026-09-11 (audit): secondary restatements say twenty-one days "
            "after service of the notice, flatly and more than once; the "
            "primary is unread — oregon.public.law, codes.findlaw.com, "
            "www.womenslaw.org, www.oregon.gov and www.courts.oregon.gov are "
            "all refused by this environment's egress proxy. Twenty-one is "
            "carried as `days` so the number on file is the one the "
            "restatements actually give, but the uniform section and every "
            "other enactment read here say twenty, and a one-day divergence "
            "between a uniform act and one state's enactment is precisely the "
            "kind of thing a secondary source gets wrong. Not VERIFIED: the "
            "operator enters the date from the court's own notice until the "
            "primary is quoted here."
        ),
        "status": "UNCERTAIN",
        "note": (
            "secondary sources say 21; primary unread — the operator enters "
            "the date from the notice"
        ),
    },
)
