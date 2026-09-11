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
"""
from __future__ import annotations

from typing import Any

from homestead.keep.rungs import Rung, classify_schema

__all__ = ["MATTER", "JURISDICTION", "JURISDICTIONS", "REPEATABLE", "SCHEMA", "FIELDS"]

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
#: matter, one dose per subject. Empty for now: this bite's custody pack has
#: no repeatable field yet. L3-custody-relocation (Wave 3) is what fills this
#: in, for `child`.
REPEATABLE: frozenset[str] = frozenset()


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
        "(step 3 yes), and the whole model turns on not rendering it by default.",
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
    "ssn": _field(
        Rung.L5,
        "key material — sealed, and L5 has no override anywhere (step 4). The "
        "corpus's canonical L5 datum; served on no surface, in any form.",
    ),
}

#: Classified at import (I-11). This line is the build failure: remove any
#: field's rung above and the process defining the schema dies, naming the field.
FIELDS: dict[str, Rung] = classify_schema(SCHEMA)
